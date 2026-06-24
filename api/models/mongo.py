from typing import Optional

from pydantic import BaseModel


class Equipment(BaseModel):

    asset_id: str

    equipment_type: str

    name: str

    manufacturer: Optional[str] = None

    model: Optional[str] = None

    status: Optional[str] = "active"


class EquipmentUpdate(BaseModel):

    manufacturer: Optional[str] = None

    model: Optional[str] = None

    status: Optional[str] = None