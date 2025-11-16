"""
Firmware build model for tracking OpenWrt image builds.
"""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Integer, DateTime, Enum, Text, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional, Any

from backend.core.database import Base


class BuildStatus(str, PyEnum):
    """Firmware build status."""

    PENDING = "pending"  # Queued for building
    BUILDING = "building"  # Build in progress
    SUCCESS = "success"  # Build completed successfully
    FAILED = "failed"  # Build failed
    CANCELLED = "cancelled"  # Build cancelled by user


class FirmwareBuild(Base):
    """
    Firmware build tracking model.

    Tracks OpenWrt image builds including configuration,
    packages, and build artifacts.
    """

    __tablename__ = "firmware_builds"

    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    build_number: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )  # e.g., "build-20250116-001"
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Build configuration
    openwrt_version: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "23.05.2"
    target: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "ath79/generic"
    subtarget: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    profile: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # Device profile if specific

    # Network configuration embedded
    network_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # FK to networks
    network_cidr: Mapped[str] = mapped_column(String(18), nullable=False)
    mesh_ssid: Mapped[str] = mapped_column(String(32), nullable=False)

    # Packages
    base_packages: Mapped[list[str]] = mapped_column(JSON, nullable=False)  # Standard packages
    custom_packages: Mapped[Optional[list[str]]] = mapped_column(
        JSON, nullable=True
    )  # Additional packages
    removed_packages: Mapped[Optional[list[str]]] = mapped_column(
        JSON, nullable=True
    )  # Excluded packages

    # Files to include
    files_included: Mapped[Optional[dict[str, str]]] = mapped_column(
        JSON, nullable=True
    )  # path -> content
    uci_defaults_script: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # Auto-config script

    # Build status
    status: Mapped[BuildStatus] = mapped_column(
        Enum(BuildStatus), default=BuildStatus.PENDING, nullable=False
    )
    build_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    build_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    build_duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Build output
    build_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    image_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    image_checksum_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    image_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Deployment tracking
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Default image for new devices
    deployed_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # Number of devices using this
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Metadata
    built_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Username
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    build_config: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )  # Full build config

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<FirmwareBuild {self.build_number} ({self.openwrt_version}/{self.target}) - {self.status}>"
