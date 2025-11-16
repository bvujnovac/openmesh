"""
Device model for mesh routers.
Stores information about registered mesh network devices.
"""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Integer, Boolean, DateTime, Enum, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Any

from backend.core.database import Base


class DeviceStatus(str, PyEnum):
    """Device operational status."""

    PENDING = "pending"  # Registered but not yet online
    ONLINE = "online"  # Active and reporting metrics
    OFFLINE = "offline"  # Known but currently unreachable
    FAILED = "failed"  # Hardware or configuration failure
    UPGRADING = "upgrading"  # Firmware upgrade in progress
    DECOMMISSIONED = "decommissioned"  # Removed from network


class Device(Base):
    """
    Mesh router device model.

    Stores device registration, network assignment, and hardware information.
    Each device gets a unique IP based on MAC address hashing.
    """

    __tablename__ = "devices"

    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mac_address: Mapped[str] = mapped_column(
        String(17), unique=True, index=True, nullable=False
    )  # Format: AA:BB:CC:DD:EE:FF
    hostname: Mapped[str] = mapped_column(String(255), nullable=False)

    # Network assignment
    network_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("networks.id", ondelete="SET NULL"), nullable=True, index=True
    )  # Network this device belongs to
    ip_address: Mapped[str] = mapped_column(
        String(15), unique=True, index=True, nullable=False
    )  # Infrastructure IP (10.0.0.x or 10.0.1.x)
    dhcp_pool_start: Mapped[str] = mapped_column(
        String(15), nullable=False
    )  # Client pool start IP
    dhcp_pool_end: Mapped[str] = mapped_column(String(15), nullable=False)  # Client pool end IP
    subnet_id: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # Subnet number (2-255 for client pools)

    # Relationships
    network: Mapped[Optional["Network"]] = relationship("Network", back_populates="devices")

    # Hardware information
    hardware_model: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hardware_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cpu_info: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    memory_total_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    flash_size_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Firmware information
    firmware_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    kernel_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    openwrt_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    firmware_build_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # FK to firmware builds

    # Status and monitoring
    status: Mapped[DeviceStatus] = mapped_column(
        Enum(DeviceStatus), default=DeviceStatus.PENDING, nullable=False
    )
    is_gateway: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Has WAN connection
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    uptime_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    load_average: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Babel routing information
    babel_node_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    babel_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    neighbor_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    route_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # WiFi information
    wifi_channels: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # e.g., "1,6" for dual radio
    wifi_ssid_mesh: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    wifi_ssid_client: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Configuration
    config_version: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )  # Increments on config changes
    config_data: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )  # Custom config parameters
    auto_update_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Location (optional)
    location_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    altitude_m: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Notes and metadata
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )  # Flexible key-value tags

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Device {self.hostname} ({self.mac_address}) - {self.ip_address}>"
