"""
Database models for OpenMesh platform.

Note: Metric models (DeviceMetric, BabelMetric, LinkMetric) are deprecated.
Metrics are now stored in InfluxDB for better time-series performance.
They are kept here for backward compatibility with migrations.
"""

from backend.models.device import Device, DeviceStatus
from backend.models.network import Network
from backend.models.firmware import FirmwareBuild, BuildStatus
from backend.models.metric import DeviceMetric, BabelMetric, LinkMetric
from backend.models.alert import Alert, AlertSeverity, AlertType, AlertStatus

__all__ = [
    # Device models
    "Device",
    "DeviceStatus",
    # Network models
    "Network",
    # Firmware models
    "FirmwareBuild",
    "BuildStatus",
    # Metric models (DEPRECATED - use InfluxDB instead)
    "DeviceMetric",
    "BabelMetric",
    "LinkMetric",
    # Alert models
    "Alert",
    "AlertSeverity",
    "AlertType",
    "AlertStatus",
]
