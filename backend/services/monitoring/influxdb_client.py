"""
InfluxDB client for storing and retrieving metrics.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS

from backend.core.config import settings


class InfluxDBMetricsClient:
    """
    InfluxDB client for metrics storage.

    Handles writing and querying time-series metrics data.
    """

    def __init__(self):
        """Initialize InfluxDB client."""
        self.client = InfluxDBClient(
            url=settings.INFLUXDB_URL,
            token=settings.INFLUXDB_TOKEN,
            org=settings.INFLUXDB_ORG,
        )
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()
        self.bucket = settings.INFLUXDB_BUCKET

    def write_device_metric(
        self,
        device_id: int,
        device_mac: str,
        metrics: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Write device metrics to InfluxDB.

        Args:
            device_id: Device ID
            device_mac: Device MAC address
            metrics: Dict of metric values (cpu, memory, etc.)
            timestamp: Optional timestamp (defaults to now)
        """
        point = (
            Point("device_health")
            .tag("device_id", str(device_id))
            .tag("device_mac", device_mac)
        )

        # Add timestamp if provided
        if timestamp:
            point = point.time(timestamp)

        # Add metric fields
        for key, value in metrics.items():
            if value is not None:
                point = point.field(key, value)

        self.write_api.write(bucket=self.bucket, record=point)

    def write_babel_metric(
        self,
        device_id: int,
        device_mac: str,
        neighbor_count: int,
        route_count: int,
        neighbors: List[Dict[str, Any]],
        routes: List[Dict[str, Any]],
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Write Babel routing metrics to InfluxDB.

        Args:
            device_id: Device ID
            device_mac: Device MAC address
            neighbor_count: Number of Babel neighbors
            route_count: Number of routes
            neighbors: List of neighbor details
            routes: List of route details
            timestamp: Optional timestamp
        """
        point = (
            Point("babel_routing")
            .tag("device_id", str(device_id))
            .tag("device_mac", device_mac)
            .field("neighbor_count", neighbor_count)
            .field("route_count", route_count)
        )

        # Calculate aggregate metrics from neighbors
        if neighbors:
            avg_rtt = sum(n.get("rtt_ms", 0) for n in neighbors if n.get("rtt_ms")) / len(
                neighbors
            )
            point = point.field("avg_neighbor_rtt_ms", avg_rtt)

        # Calculate aggregate metrics from routes
        if routes:
            installed = sum(1 for r in routes if r.get("installed", False))
            point = point.field("installed_routes", installed)

        if timestamp:
            point = point.time(timestamp)

        self.write_api.write(bucket=self.bucket, record=point)

    def write_link_metric(
        self,
        source_device_id: int,
        target_device_id: int,
        source_mac: str,
        target_mac: str,
        signal_dbm: Optional[float] = None,
        noise_dbm: Optional[float] = None,
        babel_metric: Optional[int] = None,
        rtt_ms: Optional[float] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Write link quality metrics to InfluxDB.

        Args:
            source_device_id: Source device ID
            target_device_id: Target device ID
            source_mac: Source MAC address
            target_mac: Target MAC address
            signal_dbm: Signal strength in dBm
            noise_dbm: Noise level in dBm
            babel_metric: Babel route metric
            rtt_ms: Round-trip time in milliseconds
            timestamp: Optional timestamp
        """
        point = (
            Point("link_quality")
            .tag("source_device_id", str(source_device_id))
            .tag("target_device_id", str(target_device_id))
            .tag("source_mac", source_mac)
            .tag("target_mac", target_mac)
        )

        if signal_dbm is not None:
            point = point.field("signal_dbm", signal_dbm)
        if noise_dbm is not None:
            point = point.field("noise_dbm", noise_dbm)
            if signal_dbm is not None:
                point = point.field("snr_db", signal_dbm - noise_dbm)
        if babel_metric is not None:
            point = point.field("babel_metric", babel_metric)
        if rtt_ms is not None:
            point = point.field("rtt_ms", rtt_ms)

        if timestamp:
            point = point.time(timestamp)

        self.write_api.write(bucket=self.bucket, record=point)

    def query_device_metrics(
        self, device_id: int, start: str = "-1h", stop: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query device metrics from InfluxDB.

        Args:
            device_id: Device ID
            start: Start time (e.g., "-1h", "-1d", "2025-01-16T00:00:00Z")
            stop: Stop time (defaults to now)

        Returns:
            List of metric records
        """
        query = f"""
            from(bucket: "{self.bucket}")
                |> range(start: {start}{f', stop: {stop}' if stop else ''})
                |> filter(fn: (r) => r["_measurement"] == "device_health")
                |> filter(fn: (r) => r["device_id"] == "{device_id}")
        """

        result = self.query_api.query(query=query)
        return self._parse_query_result(result)

    def query_babel_metrics(
        self, device_id: int, start: str = "-1h", stop: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Query Babel routing metrics."""
        query = f"""
            from(bucket: "{self.bucket}")
                |> range(start: {start}{f', stop: {stop}' if stop else ''})
                |> filter(fn: (r) => r["_measurement"] == "babel_routing")
                |> filter(fn: (r) => r["device_id"] == "{device_id}")
        """

        result = self.query_api.query(query=query)
        return self._parse_query_result(result)

    def query_link_metrics(
        self, source_device_id: int, target_device_id: int, start: str = "-1h"
    ) -> List[Dict[str, Any]]:
        """Query link quality metrics between two devices."""
        query = f"""
            from(bucket: "{self.bucket}")
                |> range(start: {start})
                |> filter(fn: (r) => r["_measurement"] == "link_quality")
                |> filter(fn: (r) => r["source_device_id"] == "{source_device_id}")
                |> filter(fn: (r) => r["target_device_id"] == "{target_device_id}")
        """

        result = self.query_api.query(query=query)
        return self._parse_query_result(result)

    def query_network_topology(self, start: str = "-5m") -> List[Dict[str, Any]]:
        """
        Query recent link metrics to build network topology.

        Args:
            start: Time window for recent data (default: last 5 minutes)

        Returns:
            List of active links with latest metrics
        """
        query = f"""
            from(bucket: "{self.bucket}")
                |> range(start: {start})
                |> filter(fn: (r) => r["_measurement"] == "link_quality")
                |> last()
        """

        result = self.query_api.query(query=query)
        return self._parse_query_result(result)

    def _parse_query_result(self, result) -> List[Dict[str, Any]]:
        """Parse InfluxDB query result into list of dicts."""
        records = []
        for table in result:
            for record in table.records:
                records.append(
                    {
                        "time": record.get_time(),
                        "measurement": record.get_measurement(),
                        **record.values,
                    }
                )
        return records

    def close(self) -> None:
        """Close InfluxDB client."""
        self.client.close()


# Global instance
_influx_client: Optional[InfluxDBMetricsClient] = None


def get_influx_client() -> InfluxDBMetricsClient:
    """Get or create InfluxDB client instance."""
    global _influx_client
    if _influx_client is None:
        _influx_client = InfluxDBMetricsClient()
    return _influx_client
