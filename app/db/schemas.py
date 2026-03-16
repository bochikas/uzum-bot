from datetime import datetime

from pydantic import BaseModel, RootModel


class UserProductSchema(RootModel[dict[int, list["ProductFetchResultSchema"]]]):
    pass


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
