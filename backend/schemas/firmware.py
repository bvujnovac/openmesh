"""
Pydantic schemas for firmware API endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from backend.models.firmware import BuildStatus


class FirmwareBuildBase(BaseModel):
    """Base firmware build schema."""

    name: str = Field(..., min_length=1, max_length=255)
    openwrt_version: str = Field(..., max_length=50)
    target: str = Field(..., max_length=100)
    subtarget: Optional[str] = Field(None, max_length=100)
    profile: Optional[str] = Field(None, max_length=100)


class FirmwareBuildCreate(FirmwareBuildBase):
    """Schema for creating a new firmware build."""

    network_id: Optional[int] = None
    base_packages: List[str] = Field(default_factory=list)
    custom_packages: List[str] = Field(default_factory=list)
    removed_packages: List[str] = Field(default_factory=list)
    include_uci_defaults: bool = True
    notes: Optional[str] = None


class FirmwareBuildResponse(FirmwareBuildBase):
    """Schema for firmware build responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    build_number: str
    status: BuildStatus
    network_id: Optional[int] = None
    image_filename: Optional[str] = None
    image_size_bytes: Optional[int] = None
    image_checksum_sha256: Optional[str] = None
    build_started_at: Optional[datetime] = None
    build_completed_at: Optional[datetime] = None
    build_duration_seconds: Optional[int] = None
    error_message: Optional[str] = None
    is_default: bool
    deployed_count: int
    download_count: int
    created_at: datetime
    updated_at: datetime


class FirmwareBuildDetailResponse(FirmwareBuildResponse):
    """Detailed firmware build response."""

    base_packages: List[str]
    custom_packages: Optional[List[str]] = None
    removed_packages: Optional[List[str]] = None
    build_log: Optional[str] = None
    notes: Optional[str] = None


class FirmwareBuildListResponse(BaseModel):
    """Paginated firmware build list response."""

    total: int
    page: int
    page_size: int
    builds: List[FirmwareBuildResponse]


class FirmwareBuildTaskResponse(BaseModel):
    """Response for starting a firmware build task."""

    task_id: str
    build_id: int
    message: str
