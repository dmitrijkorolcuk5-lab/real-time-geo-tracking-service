from fastapi import APIRouter

from app.api.v1.geozones import router as geozones_router
from app.api.v1.locations import router as locations_router
from app.api.v1.websocket import router as websocket_router

router = APIRouter()
router.include_router(geozones_router)
router.include_router(locations_router)
router.include_router(websocket_router)

