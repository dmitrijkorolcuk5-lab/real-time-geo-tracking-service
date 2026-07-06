from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.geozone_service import GeozoneService
from app.services.location_ingestion_service import LocationIngestionService
from app.services.websocket_manager import WebsocketManager


async def get_session(request: Request) -> AsyncSession:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        yield session


def get_geozone_service(request: Request) -> GeozoneService:
    return request.app.state.geozone_service


def get_location_ingestion_service(request: Request) -> LocationIngestionService:
    return request.app.state.location_ingestion_service


def get_websocket_manager(request: Request) -> WebsocketManager:
    return request.app.state.websocket_manager

