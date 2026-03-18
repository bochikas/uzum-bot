from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel


class UserProductSchema(TypedDict):
    user_id: int
    products: list["ProductFetchResultSchema"]


class ProductFetchResultSchema(BaseModel):
    id: int
    title: str | None
    price: float | None
    new_price: float
    checked_at: datetime | None
    url: str


class ProductMinifiedSchema(BaseModel):
    title: str
    price: float
