"""
Pydantic schemas for network API endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class NetworkBase(BaseModel):
    """Base network schema."""

    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., pattern=r"^[a-z0-9-]+$", max_length=100)
    description: Optional[str] = None


class NetworkCreate(NetworkBase):
    """Schema for creating a new network."""

    network_cidr: str = Field(..., pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$")
    mesh_ssid: str = Field(..., min_length=1, max_length=32)
    mesh_password: Optional[str] = Field(None, min_length=8)
    client_ssid: Optional[str] = Field(None, max_length=32)
    client_password: Optional[str] = Field(None, min_length=8)


class NetworkUpdate(BaseModel):
    """Schema for updating network configuration."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    mesh_password: Optional[str] = None
    client_ssid: Optional[str] = None
    client_password: Optional[str] = None
    metrics_interval: Optional[int] = Field(None, ge=10, le=300)
    auto_update_enabled: Optional[bool] = None


class NetworkResponse(NetworkBase):
    """Schema for network responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    network_cidr: str
    infrastructure_cidr: str
    client_pool_start: str
    max_routers: int
    clients_per_router: int
    mesh_ssid: str
    routing_protocol: str
    metrics_interval: int
    is_active: bool
    device_count: int
    created_at: datetime
    updated_at: datetime


class NetworkDetailResponse(NetworkResponse):
    """Detailed network response."""

    babel_port: int
    babel_hello_interval: int
    babel_update_interval: int
    mesh_encryption: str
    mesh_frequency: str
    mesh_channel: Optional[int] = None
    client_ssid: Optional[str] = None
    client_encryption: str
    default_openwrt_version: str
    auto_update_enabled: bool
