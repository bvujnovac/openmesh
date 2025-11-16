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
from backend.schemas.firmware import (
    FirmwareBuildCreate,
    FirmwareBuildResponse,
    FirmwareBuildDetailResponse,
    FirmwareBuildListResponse,
    FirmwareBuildTaskResponse,
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
    # Firmware schemas
    "FirmwareBuildCreate",
    "FirmwareBuildResponse",
    "FirmwareBuildDetailResponse",
    "FirmwareBuildListResponse",
    "FirmwareBuildTaskResponse",
]
