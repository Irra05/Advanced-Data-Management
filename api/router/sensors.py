from fastapi import APIRouter

router = APIRouter(
    prefix="/sensors",
    tags=["Sensors"]
)