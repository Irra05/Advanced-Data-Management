from fastapi import APIRouter, HTTPException

from db.mongo import get_database

from models.mongo import (
    Equipment,
    EquipmentUpdate
)

router = APIRouter(
    prefix="/equipment",
    tags=["Equipment"]
)


@router.post("/")
async def create_equipment(
    equipment: Equipment
):

    db = get_database()

    collection = db["equipment"]

    existing = await collection.find_one(
        {"asset_id": equipment.asset_id}
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Equipment already exists"
        )

    await collection.insert_one(
        equipment.model_dump()
    )

    return {
        "message": "Equipment created",
        "asset_id": equipment.asset_id
    }


@router.get("/{asset_id}")
async def get_equipment(
    asset_id: str
):

    db = get_database()

    collection = db["equipment"]

    equipment = await collection.find_one(
        {"asset_id": asset_id},
        {"_id": 0}
    )

    if not equipment:
        raise HTTPException(
            status_code=404,
            detail="Equipment not found"
        )

    return equipment


@router.patch("/{asset_id}")
async def update_equipment(
    asset_id: str,
    update: EquipmentUpdate
):

    db = get_database()

    collection = db["equipment"]

    result = await collection.update_one(
        {"asset_id": asset_id},
        {"$set": update.model_dump(exclude_none=True)}
    )

    if result.matched_count == 0:
        raise HTTPException(
            status_code=404,
            detail="Equipment not found"
        )

    return {
        "message": "Equipment updated"
    }