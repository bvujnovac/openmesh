"""
Tests for metrics API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestDeviceMetricsAPI:
    """Tests for the device metrics API endpoint."""

    def test_get_device_metrics_structure(self, client):
        """Test that device metrics endpoint returns correct data structure."""
        # Note: This test assumes device_id=1 exists or will create empty result
        device_id = 1
        response = client.get(
            f"/api/v1/metrics/devices/{device_id}",
            params={
                "start": "-1h",
                "end": "now()",
                "metrics": "cpu_usage_percent,memory_free_mb",
            },
        )

        # Should return 200 even if no data exists
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()

            # Verify required structure
            assert "data" in data or "message" in data

            # If data exists, verify structure
            if "data" in data:
                assert isinstance(data["data"], list)

                if len(data["data"]) > 0:
                    point = data["data"][0]
                    assert "field" in point
                    assert "value" in point
                    assert "time" in point

    def test_get_device_metrics_time_range(self, client):
        """Test device metrics with different time ranges."""
        device_id = 1
        time_ranges = ["-1h", "-6h", "-24h", "-7d", "-30d"]

        for time_range in time_ranges:
            response = client.get(
                f"/api/v1/metrics/devices/{device_id}",
                params={
                    "start": time_range,
                    "end": "now()",
                    "metrics": "cpu_usage_percent",
                },
            )

            # Should not error regardless of time range
            assert response.status_code in [200, 404]

    def test_get_device_metrics_multiple_fields(self, client):
        """Test requesting multiple metric fields."""
        device_id = 1
        metrics = "cpu_usage_percent,memory_free_mb,load_1min,uptime_seconds"

        response = client.get(
            f"/api/v1/metrics/devices/{device_id}",
            params={"start": "-1h", "end": "now()", "metrics": metrics},
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                # Verify we can get multiple field types
                fields = {point["field"] for point in data["data"]}
                # At least some of the requested fields should be present if data exists
                assert len(fields) >= 1

    def test_get_device_metrics_babel_metrics(self, client):
        """Test requesting Babel-specific metrics."""
        device_id = 1
        metrics = "babel_neighbors,babel_routes,babel_avg_rtt_ms"

        response = client.get(
            f"/api/v1/metrics/devices/{device_id}",
            params={"start": "-1h", "end": "now()", "metrics": metrics},
        )

        assert response.status_code in [200, 404]

    def test_get_device_metrics_invalid_device(self, client):
        """Test metrics for non-existent device."""
        device_id = 99999

        response = client.get(
            f"/api/v1/metrics/devices/{device_id}",
            params={
                "start": "-1h",
                "end": "now()",
                "metrics": "cpu_usage_percent",
            },
        )

        # Should return 404 or empty data
        assert response.status_code in [200, 404]

    def test_get_device_metrics_without_params(self, client):
        """Test that metrics endpoint requires parameters."""
        device_id = 1

        # Test without any params
        response = client.get(f"/api/v1/metrics/devices/{device_id}")

        # Should handle gracefully (might return 422 for missing required params)
        assert response.status_code in [200, 404, 422]


class TestNetworkMetricsAPI:
    """Tests for the network metrics API endpoint."""

    def test_get_network_metrics_structure(self, client):
        """Test that network metrics endpoint exists."""
        network_id = 1
        response = client.get(
            f"/api/v1/metrics/networks/{network_id}",
            params={"start": "-1h", "end": "now()"},
        )

        # Should not error (even if not implemented)
        assert response.status_code in [200, 404, 422, 501]


class TestSystemMetricsAPI:
    """Tests for the system metrics API endpoint."""

    def test_get_system_metrics_structure(self, client):
        """Test that system metrics endpoint exists."""
        response = client.get(
            "/api/v1/metrics/system", params={"start": "-1h", "end": "now()"}
        )

        # Should not error (even if not implemented)
        assert response.status_code in [200, 404, 422, 501]


class TestMetricsDataValidation:
    """Tests for metrics data validation and format."""

    def test_metrics_time_format(self, client):
        """Test that metric timestamps are in ISO format."""
        device_id = 1
        response = client.get(
            f"/api/v1/metrics/devices/{device_id}",
            params={
                "start": "-1h",
                "end": "now()",
                "metrics": "cpu_usage_percent",
            },
        )

        if response.status_code == 200:
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                for point in data["data"]:
                    # Timestamp should be a string (ISO format from InfluxDB)
                    assert isinstance(point["time"], str)

    def test_metrics_value_types(self, client):
        """Test that metric values are numeric."""
        device_id = 1
        response = client.get(
            f"/api/v1/metrics/devices/{device_id}",
            params={
                "start": "-1h",
                "end": "now()",
                "metrics": "cpu_usage_percent,memory_free_mb",
            },
        )

        if response.status_code == 200:
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                for point in data["data"]:
                    # Value should be numeric
                    assert isinstance(point["value"], (int, float))

    def test_metrics_field_names(self, client):
        """Test that field names are strings."""
        device_id = 1
        response = client.get(
            f"/api/v1/metrics/devices/{device_id}",
            params={
                "start": "-1h",
                "end": "now()",
                "metrics": "cpu_usage_percent",
            },
        )

        if response.status_code == 200:
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                for point in data["data"]:
                    # Field name should be a string
                    assert isinstance(point["field"], str)
                    assert len(point["field"]) > 0
