from pydantic import BaseModel, RootModel


class UserProductSchema(RootModel[dict[int, list["UpdatedProductSchema"]]]):
    pass


class UpdatedProductSchema(BaseModel):
    id: int
    title: str | None
    price: float | None
    new_price: float
    url: str


class ProductMinifiedSchema(BaseModel):
    title: str
    price: float
