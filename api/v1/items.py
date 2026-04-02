from fastapi import APIRouter
from schemas.item import Item, ItemCreate

router = APIRouter()

@router.get("/", response_model=list[Item])
async def read_items():
    return [{"id": 1, "title": "Foo", "description": "A very nice item"}]

@router.post("/", response_model=Item)
async def create_item(item: ItemCreate):

    print( item)

    return {"id": 2, **item.model_dump()}