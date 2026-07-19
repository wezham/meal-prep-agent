"""FastMCP tool definitions."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

from fastmcp import FastMCP

from woolworths_mcp.client import EndpointKey, WoolworthsClient
from woolworths_mcp.models import (
    BrowserResult,
    Cart,
    CartItem,
    CartItemInput,
    CartResult,
    CategoriesResult,
    CookieInfo,
    CookiesResult,
    DeliveryInfoResult,
    FulfilmentResult,
    NavigateInput,
    OpenBrowserInput,
    Product,
    ProductDetailsInput,
    ProductResult,
    RemoveCartItemInput,
    SearchProductsInput,
    SearchResult,
    SetFulfilmentInput,
    SpecialsInput,
    SpecialsResult,
    ToolResult,
    UpdateCartItemInput,
)

mcp = FastMCP(
    "Woolworths Australia",
    instructions=(
        "Open a browser, let the user sign in if needed, capture cookies, then use "
        "catalogue and trolley tools. Cart and fulfilment tools change the user's "
        "Woolworths session and should only be called when requested."
    ),
)
client = WoolworthsClient()
DEFAULT_OPEN_BROWSER_INPUT = OpenBrowserInput()
DEFAULT_SPECIALS_INPUT = SpecialsInput()


def _error(exc: Exception) -> str:
    return str(exc)


def _product(raw: dict[str, Any]) -> Product:
    return Product(
        stockcode=raw.get("Stockcode"),
        name=raw.get("DisplayName") or raw.get("Name"),
        price=raw.get("Price"),
        was_price=raw.get("WasPrice")
        if raw.get("WasPrice") != raw.get("Price")
        else None,
        cup_string=raw.get("CupString"),
        is_on_special=raw.get("IsOnSpecial"),
        is_available=raw.get("IsAvailable"),
        package_size=raw.get("PackageSize"),
        unit=raw.get("Unit"),
        quantity_in_trolley=raw.get("QuantityInTrolley"),
    )


def _products(raw: Any) -> list[Product]:
    if not isinstance(raw, list):
        return []
    items: list[Product] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        nested = item.get("Products")
        if isinstance(nested, list):
            items.extend(_product(value) for value in nested if isinstance(value, dict))
        else:
            items.append(_product(item))
    return items


def _cart(raw: dict[str, Any]) -> Cart:
    raw_totals = raw.get("Totals")
    totals: dict[str, Any] = raw_totals if isinstance(raw_totals, dict) else {}
    raw_delivery_fee = raw.get("DeliveryFee")
    delivery_fee: dict[str, Any] = (
        raw_delivery_fee if isinstance(raw_delivery_fee, dict) else {}
    )
    raw_updated = raw.get("UpdatedItems")
    updated: list[Any] = raw_updated if isinstance(raw_updated, list) else []
    return Cart(
        total_items=raw.get("TotalTrolleyItemQuantity"),
        subtotal=totals.get("SubTotal"),
        total=totals.get("Total"),
        delivery_fee=delivery_fee.get("Total"),
        savings=totals.get("TotalSavings") or 0,
        updated_items=[
            CartItem(
                stockcode=item.get("Stockcode"),
                name=item.get("DisplayName"),
                quantity=item.get("QuantityInTrolley", item.get("Quantity")),
                price=item.get("SalePrice", item.get("ListPrice")),
                is_available=item.get("IsAvailable"),
            )
            for item in updated
            if isinstance(item, dict)
        ],
    )


def _trolley_body(stockcode: int, quantity: int) -> dict[str, Any]:
    return {
        "items": [
            {
                "stockcode": stockcode,
                "quantity": quantity,
                "source": "ProductDetail",
                "diagnostics": "0",
                "searchTerm": None,
                "evaluateRewardPoints": False,
                "offerId": None,
                "profileId": None,
                "priceLevel": None,
            }
        ]
    }


@mcp.tool(name="woolworths_open_browser")
async def open_browser(
    request: OpenBrowserInput = DEFAULT_OPEN_BROWSER_INPUT,
) -> BrowserResult:
    """Open Woolworths in Chromium to establish or sign in to a session."""
    try:
        url = await client.open_browser(headless=request.headless)
        return BrowserResult(
            success=True,
            message="Browser opened. Sign in if needed, then capture cookies.",
            url=url,
        )
    except Exception as exc:
        return BrowserResult(success=False, error=_error(exc))


@mcp.tool(name="woolworths_navigate")
async def navigate(request: NavigateInput) -> BrowserResult:
    """Navigate the open browser to a Woolworths URL."""
    try:
        url, title = await client.navigate(str(request.url))
        return BrowserResult(success=True, url=url, title=title)
    except Exception as exc:
        return BrowserResult(success=False, error=_error(exc))


@mcp.tool(name="woolworths_get_cookies")
async def get_cookies() -> CookiesResult:
    """Capture cookies from the browser session for subsequent API tools."""
    try:
        cookies = await client.capture_cookies()
        public = [
            CookieInfo(
                name=str(c["name"]),
                domain=str(c.get("domain", "")),
                path=str(c.get("path", "/")),
                secure=bool(c.get("secure")),
                http_only=bool(c.get("httpOnly")),
            )
            for c in cookies
        ]
        return CookiesResult(
            success=True, message=f"Captured {len(cookies)} cookies.", cookies=public
        )
    except Exception as exc:
        return CookiesResult(success=False, error=_error(exc))


@mcp.tool(name="woolworths_close_browser")
async def close_browser() -> ToolResult:
    """Close the browser while preserving captured cookies in memory."""
    closed = await client.close_browser()
    return ToolResult(
        success=closed,
        message="Browser closed; cookies preserved."
        if closed
        else "Browser is not open.",
    )


@mcp.tool(name="woolworths_search_products")
async def search_products(request: SearchProductsInput) -> SearchResult:
    """Search the Woolworths catalogue using the captured session."""
    try:
        body = {
            "searchTerm": request.search_term,
            "pageNumber": request.page_number,
            "pageSize": request.page_size,
            "sortType": request.sort_type,
            "location": (
                "/shop/search/products?searchTerm=" + quote(request.search_term)
            ),
            "formatObject": json.dumps({"name": request.search_term}),
            "isSpecial": request.is_special,
            "isBundle": False,
            "isMobile": False,
            "filters": [],
            "groupEdmVariants": False,
        }
        data = await client.request(EndpointKey.SEARCH, json_body=body)
        return SearchResult(
            success=True,
            search_term=request.search_term,
            total_results=data.get("SearchResultsCount", 0),
            products=_products(data.get("Products")),
        )
    except Exception as exc:
        return SearchResult(
            success=False, search_term=request.search_term, error=_error(exc)
        )


@mcp.tool(name="woolworths_get_product_details")
async def get_product_details(request: ProductDetailsInput) -> ProductResult:
    """Get slim product details by stockcode."""
    try:
        data = await client.request(EndpointKey.PRODUCT, suffix=f"/{request.stockcode}")
        raw = data.get("Product", data)
        return ProductResult(success=True, product=_product(raw))
    except Exception as exc:
        return ProductResult(success=False, error=_error(exc))


@mcp.tool(name="woolworths_get_specials")
async def get_specials(
    request: SpecialsInput = DEFAULT_SPECIALS_INPUT,
) -> SpecialsResult:
    """List current specials, optionally filtered by category."""
    category = request.category or "all"
    try:
        params = {
            "category": request.category or "specials",
            "pageSize": request.page_size,
        }
        if request.category:
            params["filter"] = "Specials"
        data = await client.request(EndpointKey.SPECIALS, params=params)
        return SpecialsResult(
            success=True,
            category=category,
            total_results=data.get("TotalRecordCount", 0),
            products=_products(data.get("Products") or data.get("Bundles")),
        )
    except Exception as exc:
        return SpecialsResult(success=False, category=category, error=_error(exc))


@mcp.tool(name="woolworths_get_categories")
async def get_categories() -> CategoriesResult:
    """Get Woolworths browse categories."""
    try:
        return CategoriesResult(
            success=True, categories=await client.request(EndpointKey.CATEGORIES)
        )
    except Exception as exc:
        return CategoriesResult(success=False, error=_error(exc))


async def _change_cart(
    request: CartItemInput | UpdateCartItemInput, quantity: int
) -> CartResult:
    try:
        data = await client.request(
            EndpointKey.TROLLEY_UPDATE,
            json_body=_trolley_body(request.stockcode, quantity),
        )
        return CartResult(success=True, cart=_cart(data))
    except Exception as exc:
        return CartResult(success=False, error=_error(exc))


@mcp.tool(name="woolworths_add_to_cart")
async def add_to_cart(request: CartItemInput) -> CartResult:
    """Add a product quantity to the trolley; this changes the user's cart."""
    return await _change_cart(request, request.quantity)


@mcp.tool(name="woolworths_get_cart")
async def get_cart() -> CartResult:
    """Get a compact summary of the current trolley."""
    try:
        return CartResult(
            success=True, cart=_cart(await client.request(EndpointKey.TROLLEY_GET))
        )
    except Exception as exc:
        return CartResult(success=False, error=_error(exc))


@mcp.tool(name="woolworths_remove_from_cart")
async def remove_from_cart(request: RemoveCartItemInput) -> CartResult:
    """Remove a product from the trolley by setting its quantity to zero."""
    return await _change_cart(
        UpdateCartItemInput(stockcode=request.stockcode, quantity=0), 0
    )


@mcp.tool(name="woolworths_update_cart_quantity")
async def update_cart_quantity(request: UpdateCartItemInput) -> CartResult:
    """Set a trolley product to an exact quantity."""
    return await _change_cart(request, request.quantity)


@mcp.tool(name="woolworths_get_delivery_info")
async def get_delivery_info() -> DeliveryInfoResult:
    """Get the current delivery address, store, dates, and fulfilment method."""
    try:
        data = await client.request(EndpointKey.DELIVERY_INFO)
        return DeliveryInfoResult(
            success=True,
            delivery_method=data.get("DeliveryMethod"),
            address=data.get("Address"),
            current_date=data.get("CurrentDateAtFulfilmentStore"),
            reserved_date=data.get("ReservedDate"),
            reserved_time=data.get("ReservedTime"),
            is_express=data.get("IsExpress"),
            can_leave_unattended=data.get("CanLeaveUnattended"),
            delivery_instructions=data.get("DeliveryInstructions"),
        )
    except Exception as exc:
        return DeliveryInfoResult(success=False, error=_error(exc))


@mcp.tool(name="woolworths_set_fulfilment")
async def set_fulfilment(request: SetFulfilmentInput) -> FulfilmentResult:
    """Set delivery, pickup, or direct-to-boot fulfilment for an address."""
    try:
        data = await client.request(
            EndpointKey.FULFILMENT,
            json_body={
                "addressId": request.address_id,
                "fulfilmentMethod": request.fulfilment_method,
            },
        )
        success = data.get("IsSuccessful") is True
        return FulfilmentResult(
            success=success,
            message=data.get("Message")
            or ("Fulfilment updated." if success else "Fulfilment update failed."),
            is_non_serviced=data.get("IsNonServiced"),
        )
    except Exception as exc:
        return FulfilmentResult(success=False, error=_error(exc))


def main() -> None:
    """Run the installed stdio MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
