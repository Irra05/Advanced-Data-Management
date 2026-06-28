from typing import Optional

from pydantic import BaseModel, ConfigDict


class Equipment(BaseModel):
    model_config = ConfigDict(extra='allow')
    

    asset_id: str

    equipment_type: str

    name: str

    manufacturer: Optional[str] = None

    model: Optional[str] = None

    status: Optional[str] = "active"


class EquipmentUpdate(BaseModel):
    model_config = ConfigDict(extra='allow')


    manufacturer: Optional[str] = None

    model: Optional[str] = None

    status: Optional[str] = None