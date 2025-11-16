"""
Tests for WebSocket functionality.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.core.websocket import ConnectionManager


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def connection_manager():
    """Create a fresh connection manager for each test."""
    return ConnectionManager()


class TestConnectionManager:
    """Tests for the ConnectionManager class."""

    def test_manager_initialization(self, connection_manager):
        """Test that ConnectionManager initializes correctly."""
        assert len(connection_manager.active_connections) == 0
        assert len(connection_manager.device_subscriptions) == 0
        assert len(connection_manager.network_subscriptions) == 0
        assert len(connection_manager.topology_subscriptions) == 0

    def test_subscribe_device(self, connection_manager):
        """Test device subscription."""
        # Create a mock websocket
        mock_ws = object()
        device_id = 123

        connection_manager.subscribe_device(mock_ws, device_id)

        assert device_id in connection_manager.device_subscriptions
        assert mock_ws in connection_manager.device_subscriptions[device_id]

    def test_unsubscribe_device(self, connection_manager):
        """Test device unsubscription."""
        mock_ws = object()
        device_id = 123

        # Subscribe first
        connection_manager.subscribe_device(mock_ws, device_id)
        assert mock_ws in connection_manager.device_subscriptions[device_id]

        # Then unsubscribe
        connection_manager.unsubscribe_device(mock_ws, device_id)
        assert mock_ws not in connection_manager.device_subscriptions[device_id]

    def test_subscribe_network(self, connection_manager):
        """Test network subscription."""
        mock_ws = object()
        network_id = 456

        connection_manager.subscribe_network(mock_ws, network_id)

        assert network_id in connection_manager.network_subscriptions
        assert mock_ws in connection_manager.network_subscriptions[network_id]

    def test_subscribe_topology(self, connection_manager):
        """Test topology subscription."""
        mock_ws = object()

        connection_manager.subscribe_topology(mock_ws)

        assert mock_ws in connection_manager.topology_subscriptions

    def test_disconnect_removes_all_subscriptions(self, connection_manager):
        """Test that disconnect removes connection from all subscriptions."""
        mock_ws = object()
        device_id = 123
        network_id = 456

        # Add to active connections
        connection_manager.active_connections.add(mock_ws)

        # Subscribe to multiple things
        connection_manager.subscribe_device(mock_ws, device_id)
        connection_manager.subscribe_network(mock_ws, network_id)
        connection_manager.subscribe_topology(mock_ws)

        # Verify subscriptions exist
        assert mock_ws in connection_manager.active_connections
        assert mock_ws in connection_manager.device_subscriptions[device_id]
        assert mock_ws in connection_manager.network_subscriptions[network_id]
        assert mock_ws in connection_manager.topology_subscriptions

        # Disconnect
        connection_manager.disconnect(mock_ws)

        # Verify all subscriptions removed
        assert mock_ws not in connection_manager.active_connections
        assert mock_ws not in connection_manager.device_subscriptions.get(device_id, set())
        assert mock_ws not in connection_manager.network_subscriptions.get(network_id, set())
        assert mock_ws not in connection_manager.topology_subscriptions


class TestWebSocketEndpoint:
    """Tests for the WebSocket endpoint."""

    def test_websocket_connection(self, client):
        """Test that WebSocket connection can be established."""
        with client.websocket_connect("/api/v1/ws") as websocket:
            # Receive welcome message
            data = websocket.receive_json()
            assert data["type"] == "connected"
            assert "subscriptions" in data

    def test_websocket_ping_pong(self, client):
        """Test ping/pong keep-alive mechanism."""
        with client.websocket_connect("/api/v1/ws") as websocket:
            # Skip welcome message
            websocket.receive_json()

            # Send ping
            websocket.send_json({"action": "ping"})

            # Receive pong
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_websocket_subscribe_device(self, client):
        """Test device subscription via WebSocket."""
        with client.websocket_connect("/api/v1/ws") as websocket:
            # Skip welcome message
            websocket.receive_json()

            # Subscribe to device
            device_id = 123
            websocket.send_json({"action": "subscribe", "type": "device", "id": device_id})

            # Receive subscription confirmation
            data = websocket.receive_json()
            assert data["type"] == "subscribed"
            assert data["subscription"] == "device"
            assert data["device_id"] == device_id

    def test_websocket_subscribe_network(self, client):
        """Test network subscription via WebSocket."""
        with client.websocket_connect("/api/v1/ws") as websocket:
            # Skip welcome message
            websocket.receive_json()

            # Subscribe to network
            network_id = 456
            websocket.send_json({"action": "subscribe", "type": "network", "id": network_id})

            # Receive subscription confirmation
            data = websocket.receive_json()
            assert data["type"] == "subscribed"
            assert data["subscription"] == "network"
            assert data["network_id"] == network_id

    def test_websocket_subscribe_topology(self, client):
        """Test topology subscription via WebSocket."""
        with client.websocket_connect("/api/v1/ws") as websocket:
            # Skip welcome message
            websocket.receive_json()

            # Subscribe to topology
            websocket.send_json({"action": "subscribe", "type": "topology"})

            # Receive subscription confirmation
            data = websocket.receive_json()
            assert data["type"] == "subscribed"
            assert data["subscription"] == "topology"

    def test_websocket_unsubscribe_device(self, client):
        """Test device unsubscription via WebSocket."""
        with client.websocket_connect("/api/v1/ws") as websocket:
            # Skip welcome message
            websocket.receive_json()

            device_id = 123

            # Subscribe first
            websocket.send_json({"action": "subscribe", "type": "device", "id": device_id})
            websocket.receive_json()  # Skip confirmation

            # Unsubscribe
            websocket.send_json({"action": "unsubscribe", "type": "device", "id": device_id})

            # Receive unsubscription confirmation
            data = websocket.receive_json()
            assert data["type"] == "unsubscribed"
            assert data["subscription"] == "device"
            assert data["device_id"] == device_id

    def test_websocket_invalid_action(self, client):
        """Test handling of invalid action."""
        with client.websocket_connect("/api/v1/ws") as websocket:
            # Skip welcome message
            websocket.receive_json()

            # Send invalid action
            websocket.send_json({"action": "invalid_action"})

            # Receive error
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "invalid_action" in data["message"].lower()

    def test_websocket_invalid_subscription_type(self, client):
        """Test handling of invalid subscription type."""
        with client.websocket_connect("/api/v1/ws") as websocket:
            # Skip welcome message
            websocket.receive_json()

            # Send invalid subscription type
            websocket.send_json({"action": "subscribe", "type": "invalid_type"})

            # Receive error
            data = websocket.receive_json()
            assert data["type"] == "error"


@pytest.mark.asyncio
async def test_broadcast_device_update(connection_manager):
    """Test broadcasting device updates."""
    # This test would need async WebSocket mocks
    # Placeholder for future implementation with proper async testing
    device_id = 123
    data = {"status": "online", "last_seen": "2024-01-01T00:00:00"}

    # The broadcast method should not raise errors
    await connection_manager.broadcast_device_update(device_id, data)


@pytest.mark.asyncio
async def test_broadcast_device_metrics(connection_manager):
    """Test broadcasting device metrics."""
    device_id = 123
    metrics = {"cpu_usage_percent": 50.0, "memory_free_mb": 512}

    # The broadcast method should not raise errors
    await connection_manager.broadcast_device_metrics(device_id, metrics)


@pytest.mark.asyncio
async def test_broadcast_topology_update(connection_manager):
    """Test broadcasting topology updates."""
    topology_data = {"nodes": [], "links": []}

    # The broadcast method should not raise errors
    await connection_manager.broadcast_topology_update(topology_data)


@pytest.mark.asyncio
async def test_broadcast_network_update(connection_manager):
    """Test broadcasting network updates."""
    network_id = 456
    data = {"name": "Test Network", "status": "active"}

    # The broadcast method should not raise errors
    await connection_manager.broadcast_network_update(network_id, data)
