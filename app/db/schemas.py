from pydantic import BaseModel


class UpdatedProduct(BaseModel):
    id: int
    title: str
    price: float
    url: str
