"""
Pydantic schemas for device API endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from backend.models.device import DeviceStatus


# Base schemas
class DeviceBase(BaseModel):
    """Base device schema with common fields."""

    mac_address: str = Field(..., pattern=r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
    hostname: str = Field(..., min_length=1, max_length=255)
    hardware_model: Optional[str] = Field(None, max_length=255)
    location_name: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None


# Create schemas
class DeviceCreate(DeviceBase):
    """Schema for creating a new device."""

    pass


class DeviceRegister(BaseModel):
    """Schema for device self-registration."""

    mac_address: str = Field(..., pattern=r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$")
    hostname: str = Field(..., min_length=1, max_length=255)
    hardware_model: Optional[str] = None
    firmware_version: Optional[str] = None
    openwrt_version: Optional[str] = None


# Update schemas
class DeviceUpdate(BaseModel):
    """Schema for updating device information."""

    hostname: Optional[str] = Field(None, min_length=1, max_length=255)
    hardware_model: Optional[str] = None
    location_name: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    altitude_m: Optional[float] = None
    notes: Optional[str] = None
    auto_update_enabled: Optional[bool] = None


class DeviceStatusUpdate(BaseModel):
    """Schema for device status updates from the node."""

    firmware_version: Optional[str] = None
    kernel_version: Optional[str] = None
    uptime_seconds: Optional[int] = Field(None, ge=0)
    load_average: Optional[str] = None
    memory_total_mb: Optional[int] = None
    memory_free_mb: Optional[int] = Field(None, ge=0)
    cpu_usage_percent: Optional[float] = Field(None, ge=0, le=100)
    neighbor_count: Optional[int] = Field(None, ge=0)
    route_count: Optional[int] = Field(None, ge=0)
    installed_route_count: Optional[int] = Field(None, ge=0)
    xroute_count: Optional[int] = Field(None, ge=0)
    avg_rtt_ms: Optional[float] = Field(None, ge=0)
    wifi_channels: Optional[str] = None


# Response schemas
class DeviceResponse(DeviceBase):
    """Schema for device responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    ip_address: str
    dhcp_pool_start: str
    dhcp_pool_end: str
    subnet_id: int
    status: DeviceStatus
    is_gateway: bool
    firmware_version: Optional[str] = None
    openwrt_version: Optional[str] = None
    last_seen: Optional[datetime] = None
    uptime_seconds: Optional[int] = None
    neighbor_count: int
    route_count: int
    created_at: datetime
    updated_at: datetime


class DeviceDetailResponse(DeviceResponse):
    """Detailed device response with all fields."""

    hardware_version: Optional[str] = None
    cpu_info: Optional[str] = None
    memory_total_mb: Optional[int] = None
    flash_size_mb: Optional[int] = None
    kernel_version: Optional[str] = None
    firmware_build_id: Optional[int] = None
    load_average: Optional[str] = None
    babel_node_id: Optional[str] = None
    babel_version: Optional[str] = None
    wifi_channels: Optional[str] = None
    wifi_ssid_mesh: Optional[str] = None
    wifi_ssid_client: Optional[str] = None
    config_version: int
    auto_update_enabled: bool
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude_m: Optional[float] = None


class DeviceListResponse(BaseModel):
    """Paginated device list response."""

    total: int
    page: int
    page_size: int
    devices: list[DeviceResponse]


class DeviceConfigResponse(BaseModel):
    """Device configuration response."""

    device_id: int
    mac_address: str
    ip_address: str
    dhcp_pool_start: str
    dhcp_pool_end: str
    network_cidr: str
    mesh_ssid: str
    config_script: str  # UCI defaults script content
