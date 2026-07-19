"""Validated MCP input and output models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, PositiveInt

SortType = Literal["TraderRelevance", "PriceAsc", "PriceDesc", "Name"]
FulfilmentMethod = Literal["Courier", "Pickup", "DirectToBoot"]


class StrictModel(BaseModel):
    """Base for tool input models."""

    model_config = ConfigDict(extra="forbid")


class OpenBrowserInput(StrictModel):
    headless: bool = False


class NavigateInput(StrictModel):
    url: HttpUrl


class SearchProductsInput(StrictModel):
    search_term: str = Field(min_length=1, max_length=200)
    page_number: PositiveInt = 1
    page_size: int = Field(default=36, ge=1, le=100)
    sort_type: SortType = "TraderRelevance"
    is_special: bool = False


class ProductDetailsInput(StrictModel):
    stockcode: PositiveInt


class SpecialsInput(StrictModel):
    category: str | None = Field(default=None, max_length=100)
    page_size: int = Field(default=20, ge=1, le=100)


class CartItemInput(StrictModel):
    stockcode: PositiveInt
    quantity: int = Field(default=1, ge=1, le=99)


class RemoveCartItemInput(StrictModel):
    stockcode: PositiveInt


class UpdateCartItemInput(StrictModel):
    stockcode: PositiveInt
    quantity: int = Field(ge=0, le=99)


class SetFulfilmentInput(StrictModel):
    address_id: PositiveInt
    fulfilment_method: FulfilmentMethod = "Courier"


class ToolResult(BaseModel):
    success: bool
    message: str | None = None
    error: str | None = None


class BrowserResult(ToolResult):
    url: str | None = None
    title: str | None = None


class CookieInfo(BaseModel):
    name: str
    domain: str
    path: str
    secure: bool
    http_only: bool


class CookiesResult(ToolResult):
    cookies: list[CookieInfo] = Field(default_factory=list)


class Product(BaseModel):
    stockcode: int | str | None = None
    name: str | None = None
    price: float | None = None
    was_price: float | None = None
    cup_string: str | None = None
    is_on_special: bool | None = None
    is_available: bool | None = None
    package_size: str | None = None
    unit: str | None = None
    quantity_in_trolley: float | None = None


class SearchResult(ToolResult):
    search_term: str
    total_results: int = 0
    products: list[Product] = Field(default_factory=list)


class ProductResult(ToolResult):
    product: Product | None = None


class SpecialsResult(ToolResult):
    category: str
    total_results: int = 0
    products: list[Product] = Field(default_factory=list)


class CategoriesResult(ToolResult):
    categories: Any = None


class CartItem(BaseModel):
    stockcode: int | str | None = None
    name: str | None = None
    quantity: float | None = None
    price: float | None = None
    is_available: bool | None = None


class Cart(BaseModel):
    total_items: float | None = None
    subtotal: float | None = None
    total: float | None = None
    delivery_fee: float | None = None
    savings: float = 0
    updated_items: list[CartItem] = Field(default_factory=list)


class CartResult(ToolResult):
    cart: Cart | None = None


class DeliveryInfoResult(ToolResult):
    delivery_method: Any = None
    address: Any = None
    current_date: Any = None
    reserved_date: Any = None
    reserved_time: Any = None
    is_express: bool | None = None
    can_leave_unattended: bool | None = None
    delivery_instructions: Any = None


class FulfilmentResult(ToolResult):
    is_non_serviced: bool | None = None
