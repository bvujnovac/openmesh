"""
API v1 router configuration.
"""

from fastapi import APIRouter

from backend.api.v1 import devices, networks, firmware, topology, metrics, websocket

api_router = APIRouter()

# Include sub-routers
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(networks.router, prefix="/networks", tags=["networks"])
api_router.include_router(firmware.router, prefix="/firmware", tags=["firmware"])
api_router.include_router(topology.router, prefix="/topology", tags=["topology"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(websocket.router, tags=["websocket"])

__all__ = ["api_router"]
