"""
Pydantic schemas for API validation and serialization.
"""

from backend.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceDetailResponse,
    DeviceListResponse,
    DeviceConfigResponse,
    DeviceRegister,
    DeviceStatusUpdate,
)
from backend.schemas.network import (
    NetworkCreate,
    NetworkUpdate,
    NetworkResponse,
    NetworkDetailResponse,
)

__all__ = [
    # Device schemas
    "DeviceCreate",
    "DeviceUpdate",
    "DeviceResponse",
    "DeviceDetailResponse",
    "DeviceListResponse",
    "DeviceConfigResponse",
    "DeviceRegister",
    "DeviceStatusUpdate",
    # Network schemas
    "NetworkCreate",
    "NetworkUpdate",
    "NetworkResponse",
    "NetworkDetailResponse",
]
