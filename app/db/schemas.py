from pydantic import BaseModel


class UpdatedProductSchema(BaseModel):
    id: int
    title: str
    price: float
    url: str


class ProductMinifiedSchema(BaseModel):
    title: str
    price: float
