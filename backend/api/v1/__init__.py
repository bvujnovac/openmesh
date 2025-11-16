"""
API v1 router configuration.
"""

from fastapi import APIRouter

from backend.api.v1 import devices, networks, firmware

api_router = APIRouter()

# Include sub-routers
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(networks.router, prefix="/networks", tags=["networks"])
api_router.include_router(firmware.router, prefix="/firmware", tags=["firmware"])

__all__ = ["api_router"]
