"""
Network model for managing mesh network configurations.
Supports multiple independent mesh networks.
"""

from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, Any, List

from backend.core.database import Base


class Network(Base):
    """
    Mesh network configuration model.

    Defines network-wide settings like CIDR, SSID, routing protocol config.
    Allows managing multiple independent mesh networks.
    """

    __tablename__ = "networks"

    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False
    )  # URL-safe identifier

    # Network addressing
    network_cidr: Mapped[str] = mapped_column(
        String(18), nullable=False
    )  # e.g., "10.0.0.0/16"
    infrastructure_cidr: Mapped[str] = mapped_column(
        String(18), nullable=False
    )  # e.g., "10.0.0.0/23"
    client_pool_start: Mapped[str] = mapped_column(
        String(15), nullable=False
    )  # e.g., "10.0.2.0"
    max_routers: Mapped[int] = mapped_column(Integer, default=508, nullable=False)
    clients_per_router: Mapped[int] = mapped_column(Integer, default=126, nullable=False)

    # Routing configuration
    routing_protocol: Mapped[str] = mapped_column(
        String(50), default="babel", nullable=False
    )  # babel, olsr, batman-adv
    babel_port: Mapped[int] = mapped_column(Integer, default=33123, nullable=False)
    babel_hello_interval: Mapped[int] = mapped_column(
        Integer, default=20, nullable=False
    )  # seconds
    babel_update_interval: Mapped[int] = mapped_column(
        Integer, default=60, nullable=False
    )  # seconds

    # WiFi mesh configuration
    mesh_ssid: Mapped[str] = mapped_column(String(32), nullable=False)
    mesh_encryption: Mapped[str] = mapped_column(
        String(50), default="sae", nullable=False
    )  # none, wep, psk, sae
    mesh_password: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # Encrypted in production
    mesh_frequency: Mapped[str] = mapped_column(
        String(10), default="5ghz", nullable=False
    )  # 2.4ghz, 5ghz, both
    mesh_channel: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # Auto if null

    # Client WiFi configuration
    client_ssid: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    client_encryption: Mapped[str] = mapped_column(String(50), default="psk2", nullable=False)
    client_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Monitoring settings
    metrics_interval: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False
    )  # seconds
    alert_latency_threshold_ms: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    alert_node_down_timeout_sec: Mapped[int] = mapped_column(Integer, default=300, nullable=False)

    # Firmware settings
    default_openwrt_version: Mapped[str] = mapped_column(String(50), default="23.05.2", nullable=False)
    auto_update_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    update_schedule: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # Cron expression

    # Additional configuration
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    config_data: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )  # Custom parameters

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    device_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )  # Cached count

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    devices: Mapped[List["Device"]] = relationship("Device", back_populates="network")

    def __repr__(self) -> str:
        return f"<Network {self.name} ({self.network_cidr}) - {self.device_count} devices>"
