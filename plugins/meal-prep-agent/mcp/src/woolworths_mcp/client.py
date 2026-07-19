"""Woolworths browser session and resilient API client."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import urlsplit, urlunsplit

import httpx
from platformdirs import user_cache_path
from playwright.async_api import (
    Browser,
    Cookie,
    Page,
    Playwright,
    async_playwright,
)
from pydantic import BaseModel, ConfigDict

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://www.woolworths.com.au"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
JsonObject = dict[str, Any]


class EndpointKey(StrEnum):
    SEARCH = "search_products"
    PRODUCT = "product_detail"
    SPECIALS = "browse_category"
    CATEGORIES = "categories"
    TROLLEY_UPDATE = "trolley_update"
    TROLLEY_GET = "trolley_get"
    FULFILMENT = "fulfilment"
    DELIVERY_INFO = "delivery_info"


@dataclass(frozen=True, slots=True)
class Endpoint:
    url: str
    method: Literal["GET", "POST"]
    patterns: tuple[str, ...]
    discovery_page: str


ENDPOINTS: dict[EndpointKey, Endpoint] = {
    EndpointKey.SEARCH: Endpoint(
        f"{BASE_URL}/apis/ui/Search/products",
        "POST",
        ("search/products",),
        f"{BASE_URL}/shop/search/products?searchTerm=milk",
    ),
    EndpointKey.PRODUCT: Endpoint(
        f"{BASE_URL}/apis/ui/product/detail",
        "GET",
        ("product/detail",),
        f"{BASE_URL}/shop/productdetails/123456/product",
    ),
    EndpointKey.SPECIALS: Endpoint(
        f"{BASE_URL}/apis/ui/browse/category",
        "GET",
        ("browse/category",),
        f"{BASE_URL}/shop/browse/specials",
    ),
    EndpointKey.CATEGORIES: Endpoint(
        f"{BASE_URL}/apis/ui/PiesCategoriesWithSpecials",
        "GET",
        ("categorieswithspecials",),
        f"{BASE_URL}/shop/browse",
    ),
    EndpointKey.TROLLEY_UPDATE: Endpoint(
        f"{BASE_URL}/api/v3/ui/trolley/update",
        "POST",
        ("trolley/update",),
        f"{BASE_URL}/shop/mylist",
    ),
    EndpointKey.TROLLEY_GET: Endpoint(
        f"{BASE_URL}/apis/ui/Trolley", "GET", ("ui/trolley",), f"{BASE_URL}/shop/mylist"
    ),
    EndpointKey.FULFILMENT: Endpoint(
        f"{BASE_URL}/apis/ui/Fulfilment",
        "POST",
        ("ui/fulfilment",),
        f"{BASE_URL}/shop/checkout",
    ),
    EndpointKey.DELIVERY_INFO: Endpoint(
        f"{BASE_URL}/apis/ui/Delivery/DeliveryInfo",
        "GET",
        ("delivery/deliveryinfo",),
        f"{BASE_URL}/shop/checkout",
    ),
}


class CachedEndpoint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str
    method: Literal["GET", "POST"]
    discovered_at: datetime


class ApiError(RuntimeError):
    """An actionable Woolworths API failure."""


class WoolworthsClient:
    """Own browser/cookies and recover when Woolworths moves an endpoint."""

    def __init__(self, cache_file: Path | None = None) -> None:
        self.cookies: list[Cookie] = []
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.page: Page | None = None
        self.cache_file = (
            cache_file or user_cache_path("woolworths-mcp") / "endpoints.json"
        )
        self.cache: dict[EndpointKey, CachedEndpoint] = self._load_cache()
        self._discovery_locks = {key: asyncio.Lock() for key in EndpointKey}

    def _load_cache(self) -> dict[EndpointKey, CachedEndpoint]:
        try:
            raw = json.loads(self.cache_file.read_text(encoding="utf-8"))
            return {
                EndpointKey(key): CachedEndpoint.model_validate(value)
                for key, value in raw.items()
            }
        except (FileNotFoundError, OSError, ValueError):
            return {}

    def _save_cache(self) -> None:
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            key.value: value.model_dump(mode="json")
            for key, value in self.cache.items()
        }
        self.cache_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    async def open_browser(self, *, headless: bool = False) -> str:
        if self.browser is not None:
            raise ApiError("Browser is already open; close it first.")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless)
        context = await self.browser.new_context(
            user_agent=USER_AGENT, viewport={"width": 1280, "height": 800}
        )
        self.page = await context.new_page()
        await self.page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60_000)
        return self.page.url

    async def navigate(self, url: str) -> tuple[str, str]:
        if self.page is None:
            raise ApiError("Browser is not open; use woolworths_open_browser first.")
        if not self._is_woolworths_url(url):
            raise ApiError("Navigation is restricted to woolworths.com.au URLs.")
        await self.page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        return self.page.url, await self.page.title()

    async def capture_cookies(self) -> list[Cookie]:
        if self.page is None:
            raise ApiError("Browser is not open; use woolworths_open_browser first.")
        self.cookies = await self.page.context.cookies()
        return self.cookies

    async def close_browser(self) -> bool:
        if self.browser is None:
            return False
        await self.browser.close()
        if self.playwright is not None:
            await self.playwright.stop()
        self.browser = self.page = self.playwright = None
        return True

    async def request(
        self,
        key: EndpointKey,
        *,
        suffix: str = "",
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> Any:
        if not self.cookies:
            raise ApiError(
                "No session cookies available; open the browser and capture "
                "cookies first."
            )
        endpoint = self.cache.get(key)
        url = (endpoint.url if endpoint else ENDPOINTS[key].url) + suffix
        method = endpoint.method if endpoint else ENDPOINTS[key].method
        response = await self._send(method, url, params=params, json_body=json_body)
        failure = self._classify(key, response)
        if failure == "ok":
            return response.json()
        if failure == "auth_required":
            raise ApiError(
                "Woolworths rejected the session; capture fresh cookies and retry."
            )
        if failure == "transient":
            raise ApiError(
                f"Woolworths is temporarily unavailable (HTTP {response.status_code})."
            )
        async with self._discovery_locks[key]:
            recovered = await self._recover(
                key, suffix=suffix, params=params, json_body=json_body
            )
        if recovered is None:
            raise ApiError(
                f"Endpoint recovery failed for {key.value} "
                f"(HTTP {response.status_code})."
            )
        return recovered

    async def _send(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Mapping[str, Any] | None = None,
    ) -> httpx.Response:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            "Accept-Language": "en-AU,en;q=0.9",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/",
        }
        cookie_jar = {
            str(cookie["name"]): str(cookie["value"]) for cookie in self.cookies
        }
        async with httpx.AsyncClient(
            headers=headers, cookies=cookie_jar, timeout=30, follow_redirects=True
        ) as client:
            return await client.request(method, url, params=params, json=json_body)

    def _classify(self, key: EndpointKey, response: httpx.Response) -> str:
        if response.status_code in {401, 403}:
            return "auth_required"
        if response.status_code == 429 or response.status_code >= 500:
            return "transient"
        if response.status_code == 404:
            return "endpoint_moved"
        if response.status_code == 400:
            return "schema_changed"
        if response.is_success:
            try:
                data = response.json()
            except ValueError:
                return "schema_changed"
            return "ok" if self._valid_shape(key, data) else "schema_changed"
        return "endpoint_moved"

    @staticmethod
    def _valid_shape(key: EndpointKey, data: Any) -> bool:
        if key == EndpointKey.SEARCH:
            return isinstance(data, dict) and (
                "Products" in data or "SearchResultsCount" in data
            )
        if key == EndpointKey.PRODUCT:
            return isinstance(data, dict) and any(
                name in data for name in ("Product", "Stockcode", "Name", "DisplayName")
            )
        if key == EndpointKey.SPECIALS:
            return isinstance(data, dict) and any(
                name in data for name in ("Products", "Bundles", "TotalRecordCount")
            )
        if key == EndpointKey.FULFILMENT:
            return isinstance(data, dict) and "IsSuccessful" in data
        if key == EndpointKey.DELIVERY_INFO:
            return isinstance(data, dict) and (
                "DeliveryMethod" in data or "Address" in data
            )
        return isinstance(data, (dict, list))

    async def _recover(
        self,
        key: EndpointKey,
        *,
        suffix: str,
        params: Mapping[str, Any] | None,
        json_body: Mapping[str, Any] | None,
    ) -> Any | None:
        base = ENDPOINTS[key]
        candidates = self._mutations(base.url)
        discovered = await self._discover(key)
        if discovered and discovered not in candidates:
            candidates.append(discovered)
        for candidate in candidates:
            response = await self._send(
                base.method, candidate + suffix, params=params, json_body=json_body
            )
            if self._classify(key, response) == "ok":
                self.cache[key] = CachedEndpoint(
                    url=candidate, method=base.method, discovered_at=datetime.now(UTC)
                )
                self._save_cache()
                return response.json()
        return None

    @staticmethod
    def _mutations(url: str) -> list[str]:
        replacements = (
            ("/apis/ui/", "/api/v3/ui/"),
            ("/apis/ui/", "/api/v4/ui/"),
            ("/api/v3/ui/", "/api/v2/ui/"),
            ("/api/v3/ui/", "/apis/ui/"),
            ("/api/v3/ui/", "/api/v4/ui/"),
        )
        results: list[str] = []
        for old, new in replacements:
            if old in url:
                candidate = url.replace(old, new)
                if candidate != url and candidate not in results:
                    results.extend([candidate, candidate.lower()])
        return list(dict.fromkeys(results))

    async def _discover(self, key: EndpointKey) -> str | None:
        config = ENDPOINTS[key]
        playwright = await async_playwright().start()
        browser: Browser | None = None
        try:
            browser = await playwright.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=USER_AGENT)
            if self.cookies:
                await context.add_cookies(cast("Any", self.cookies))
            page = await context.new_page()
            matches: list[str] = []
            page.on(
                "request",
                lambda request: (
                    matches.append(request.url)
                    if request.resource_type in {"xhr", "fetch"}
                    and any(
                        pattern in request.url.lower() for pattern in config.patterns
                    )
                    else None
                ),
            )
            await page.goto(
                config.discovery_page, wait_until="networkidle", timeout=30_000
            )
            for url in matches:
                if self._is_woolworths_url(url):
                    parts = urlsplit(url)
                    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
            return None
        except Exception:  # Browser discovery is a best-effort fallback.
            LOGGER.exception("Browser endpoint discovery failed for %s", key)
            return None
        finally:
            if browser is not None:
                await browser.close()
            await playwright.stop()

    @staticmethod
    def _is_woolworths_url(url: str) -> bool:
        hostname = (urlsplit(url).hostname or "").lower()
        return hostname == "woolworths.com.au" or hostname.endswith(
            ".woolworths.com.au"
        )
