"""
Tests for topology API endpoint.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestTopologyAPI:
    """Tests for the topology API endpoint."""

    def test_get_topology_structure(self, client):
        """Test that topology endpoint returns correct data structure."""
        response = client.get("/api/v1/topology")

        assert response.status_code == 200
        data = response.json()

        # Verify required keys
        assert "nodes" in data
        assert "links" in data
        assert "summary" in data

        # Verify nodes structure
        assert isinstance(data["nodes"], list)
        if len(data["nodes"]) > 0:
            node = data["nodes"][0]
            assert "id" in node
            assert "label" in node
            assert "status" in node

        # Verify links structure
        assert isinstance(data["links"], list)
        if len(data["links"]) > 0:
            link = data["links"][0]
            assert "source" in link
            assert "target" in link

        # Verify summary structure
        summary = data["summary"]
        assert "total_nodes" in summary
        assert "total_links" in summary
        assert "online_nodes" in summary
        assert isinstance(summary["total_nodes"], int)
        assert isinstance(summary["total_links"], int)
        assert isinstance(summary["online_nodes"], int)

    def test_get_topology_with_network_filter(self, client):
        """Test topology endpoint with network filter."""
        response = client.get("/api/v1/topology?network_id=1")

        assert response.status_code == 200
        data = response.json()

        # Should return same structure even with filter
        assert "nodes" in data
        assert "links" in data
        assert "summary" in data

    def test_get_topology_nodes_exclude_decommissioned(self, client):
        """Test that decommissioned devices are excluded from topology."""
        response = client.get("/api/v1/topology")

        assert response.status_code == 200
        data = response.json()

        # Verify no decommissioned devices in nodes
        for node in data["nodes"]:
            assert node["status"] != "decommissioned"

    def test_get_topology_node_attributes(self, client):
        """Test that topology nodes have all required attributes."""
        response = client.get("/api/v1/topology")

        assert response.status_code == 200
        data = response.json()

        if len(data["nodes"]) > 0:
            node = data["nodes"][0]

            # Required attributes
            required_attrs = ["id", "label", "status"]
            for attr in required_attrs:
                assert attr in node, f"Missing required attribute: {attr}"

            # Optional but expected attributes
            expected_attrs = ["ip", "mac", "subnet_id", "network_id"]
            for attr in expected_attrs:
                assert attr in node, f"Missing expected attribute: {attr}"

    def test_get_topology_link_attributes(self, client):
        """Test that topology links have all required attributes."""
        response = client.get("/api/v1/topology")

        assert response.status_code == 200
        data = response.json()

        if len(data["links"]) > 0:
            link = data["links"][0]

            # Required attributes
            required_attrs = ["source", "target"]
            for attr in required_attrs:
                assert attr in link, f"Missing required attribute: {attr}"

            # Optional but expected attributes
            expected_attrs = ["type", "quality"]
            for attr in expected_attrs:
                assert attr in link, f"Missing expected attribute: {attr}"

    def test_get_topology_summary_accuracy(self, client):
        """Test that topology summary counts are accurate."""
        response = client.get("/api/v1/topology")

        assert response.status_code == 200
        data = response.json()

        summary = data["summary"]
        nodes = data["nodes"]
        links = data["links"]

        # Verify counts match actual data
        assert summary["total_nodes"] == len(nodes)
        assert summary["total_links"] == len(links)

        # Verify online count
        online_count = sum(1 for n in nodes if n["status"] == "online")
        assert summary["online_nodes"] == online_count

    def test_get_topology_links_endpoint(self, client):
        """Test the /topology/links endpoint."""
        response = client.get("/api/v1/topology/links")

        assert response.status_code == 200
        data = response.json()

        # Currently returns placeholder message
        assert isinstance(data, list)


class TestTopologyDataIntegrity:
    """Tests for topology data integrity and relationships."""

    def test_link_nodes_exist(self, client):
        """Test that all link source/target nodes exist in nodes list."""
        response = client.get("/api/v1/topology")

        assert response.status_code == 200
        data = response.json()

        node_ids = {node["id"] for node in data["nodes"]}

        for link in data["links"]:
            assert (
                link["source"] in node_ids
            ), f"Link source {link['source']} not found in nodes"
            assert (
                link["target"] in node_ids
            ), f"Link target {link['target']} not found in nodes"

    def test_no_self_referencing_links(self, client):
        """Test that no link connects a node to itself."""
        response = client.get("/api/v1/topology")

        assert response.status_code == 200
        data = response.json()

        for link in data["links"]:
            assert (
                link["source"] != link["target"]
            ), f"Self-referencing link found: {link['source']}"

    def test_node_ids_are_unique(self, client):
        """Test that all node IDs are unique."""
        response = client.get("/api/v1/topology")

        assert response.status_code == 200
        data = response.json()

        node_ids = [node["id"] for node in data["nodes"]]
        unique_ids = set(node_ids)

        assert len(node_ids) == len(unique_ids), "Duplicate node IDs found"
