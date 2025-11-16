"""
Alert model for network monitoring alerts.
"""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, Integer, DateTime, Enum, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from backend.core.database import Base


class AlertSeverity(str, PyEnum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(str, PyEnum):
    """Alert types."""

    DEVICE_OFFLINE = "device_offline"
    DEVICE_DEGRADED = "device_degraded"
    HIGH_LATENCY = "high_latency"
    LINK_DOWN = "link_down"
    LINK_DEGRADED = "link_degraded"
    ROUTE_FLAPPING = "route_flapping"
    HIGH_CPU = "high_cpu"
    HIGH_MEMORY = "high_memory"
    FIRMWARE_UPGRADE_FAILED = "firmware_upgrade_failed"
    CONFIG_SYNC_FAILED = "config_sync_failed"
    CUSTOM = "custom"


class AlertStatus(str, PyEnum):
    """Alert status."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class Alert(Base):
    """
    Network monitoring alert model.

    Tracks alerts and notifications for network events
    requiring operator attention.
    """

    __tablename__ = "alerts"

    # Primary identification
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Alert classification
    alert_type: Mapped[AlertType] = mapped_column(Enum(AlertType), nullable=False, index=True)
    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity), nullable=False, index=True
    )
    status: Mapped[AlertStatus] = mapped_column(
        Enum(AlertStatus), default=AlertStatus.ACTIVE, nullable=False, index=True
    )

    # Related entities
    device_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True
    )  # FK to devices
    network_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # FK to networks
    link_source_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # For link alerts
    link_target_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # For link alerts

    # Alert details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Additional context

    # Thresholds and values
    threshold_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    actual_value: Mapped[Optional[float]] = mapped_column(nullable=True)
    threshold_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Alert lifecycle
    first_occurred_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    last_occurred_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    occurrence_count: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )  # Number of times triggered
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Acknowledgment
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # Username
    acknowledgment_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Notification tracking
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notification_channels: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # email, slack, etc.

    # Auto-resolution
    auto_resolve: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )  # Auto-resolve when condition clears
    auto_resolve_delay_seconds: Mapped[int] = mapped_column(
        Integer, default=300, nullable=False
    )  # Wait before auto-resolve

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Alert {self.alert_type} - {self.severity} - {self.status}>"
