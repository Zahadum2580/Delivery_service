from pydantic import BaseModel


class TypeBase(BaseModel):
    name: str


class TypeCreate(TypeBase):
    pass


class TypeOut(TypeBase):
    id: int

    class Config:
        from_attributes = True
