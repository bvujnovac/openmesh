"""
Metrics models for time-series monitoring data.
NOTE: These models are deprecated and kept for reference only.
Metrics are now stored in InfluxDB for better time-series performance.
See backend/services/monitoring/influxdb_client.py for metrics storage.
"""

from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional, Any

from backend.core.database import Base


class DeviceMetric(Base):
    """
    Device health metrics time-series data.

    Stores system health metrics like CPU, memory, uptime.
    Collected periodically from each device.
    """

    __tablename__ = "device_metrics"
    __table_args__ = (
        Index("idx_device_metrics_device_time", "device_id", "timestamp"),
        Index("idx_device_metrics_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # FK to devices

    # System metrics
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    uptime_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    load_1min: Mapped[float] = mapped_column(Float, nullable=False)
    load_5min: Mapped[float] = mapped_column(Float, nullable=False)
    load_15min: Mapped[float] = mapped_column(Float, nullable=False)

    # Memory metrics
    memory_total_kb: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_free_kb: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_available_kb: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_buffers_kb: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_cached_kb: Mapped[int] = mapped_column(Integer, nullable=False)

    # CPU metrics (if available)
    cpu_usage_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cpu_temperature_celsius: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Network interface metrics
    interfaces_data: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )  # tx/rx bytes, packets, errors

    # Client connections
    connected_clients: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    dhcp_leases_active: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<DeviceMetric device={self.device_id} @ {self.timestamp}>"


class BabelMetric(Base):
    """
    Babel routing protocol metrics.

    Stores Babel-specific routing information including
    neighbors, routes, and convergence metrics.
    """

    __tablename__ = "babel_metrics"
    __table_args__ = (
        Index("idx_babel_metrics_device_time", "device_id", "timestamp"),
        Index("idx_babel_metrics_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # FK to devices
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # Babel daemon info
    babel_version: Mapped[str] = mapped_column(String(50), nullable=False)
    node_id: Mapped[str] = mapped_column(String(255), nullable=False)
    my_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Neighbor statistics
    neighbor_count: Mapped[int] = mapped_column(Integer, nullable=False)
    neighbors: Mapped[dict[str, Any]] = mapped_column(
        JSON, nullable=False
    )  # Detailed neighbor info

    # Route statistics
    route_count: Mapped[int] = mapped_column(Integer, nullable=False)
    installed_routes: Mapped[int] = mapped_column(Integer, nullable=False)
    routes: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)  # Detailed route info

    # Interface statistics
    interfaces: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Performance metrics
    avg_rtt_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_metric: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    min_metric: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<BabelMetric device={self.device_id} neighbors={self.neighbor_count} routes={self.route_count}>"


class LinkMetric(Base):
    """
    Mesh link quality metrics.

    Stores link-level metrics between mesh nodes including
    signal strength, throughput, and latency.
    """

    __tablename__ = "link_metrics"
    __table_args__ = (
        Index("idx_link_metrics_devices", "source_device_id", "target_device_id"),
        Index("idx_link_metrics_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_device_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )  # FK to devices
    target_device_id: Mapped[int] = mapped_column(
        Integer, nullable=False, index=True
    )  # FK to devices
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # Link quality
    signal_strength_dbm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    noise_level_dbm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    snr_db: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Babel metrics
    babel_metric: Mapped[int] = mapped_column(Integer, nullable=False)
    babel_rtt_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    babel_reachability: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 to 1.0

    # Throughput (if measured)
    tx_rate_mbps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rx_rate_mbps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    expected_throughput_mbps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Packet statistics
    tx_packets: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rx_packets: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tx_failed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tx_retries: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return f"<LinkMetric {self.source_device_id}->{self.target_device_id} metric={self.babel_metric}>"
