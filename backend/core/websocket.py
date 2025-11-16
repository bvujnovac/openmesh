"""
WebSocket connection manager for real-time updates.
"""

import json
import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts messages to connected clients.
    """

    def __init__(self):
        # Store active connections
        self.active_connections: Set[WebSocket] = set()

        # Track connections by subscription type
        self.device_subscriptions: Dict[int, Set[WebSocket]] = {}
        self.network_subscriptions: Dict[int, Set[WebSocket]] = {}
        self.topology_subscriptions: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        """
        Accept a new WebSocket connection.

        Args:
            websocket: WebSocket connection to accept
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
        """
        self.active_connections.discard(websocket)

        # Remove from all subscriptions and clean up empty sets to prevent memory leaks
        for device_id in list(self.device_subscriptions.keys()):
            self.device_subscriptions[device_id].discard(websocket)
            if not self.device_subscriptions[device_id]:
                del self.device_subscriptions[device_id]

        for network_id in list(self.network_subscriptions.keys()):
            self.network_subscriptions[network_id].discard(websocket)
            if not self.network_subscriptions[network_id]:
                del self.network_subscriptions[network_id]

        self.topology_subscriptions.discard(websocket)

        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    def subscribe_device(self, websocket: WebSocket, device_id: int):
        """
        Subscribe a connection to device updates.

        Args:
            websocket: WebSocket connection
            device_id: Device ID to subscribe to
        """
        if device_id not in self.device_subscriptions:
            self.device_subscriptions[device_id] = set()
        self.device_subscriptions[device_id].add(websocket)
        logger.debug(f"WebSocket subscribed to device {device_id}")

    def unsubscribe_device(self, websocket: WebSocket, device_id: int):
        """
        Unsubscribe a connection from device updates.

        Args:
            websocket: WebSocket connection
            device_id: Device ID to unsubscribe from
        """
        if device_id in self.device_subscriptions:
            self.device_subscriptions[device_id].discard(websocket)
        logger.debug(f"WebSocket unsubscribed from device {device_id}")

    def subscribe_network(self, websocket: WebSocket, network_id: int):
        """
        Subscribe a connection to network updates.

        Args:
            websocket: WebSocket connection
            network_id: Network ID to subscribe to
        """
        if network_id not in self.network_subscriptions:
            self.network_subscriptions[network_id] = set()
        self.network_subscriptions[network_id].add(websocket)
        logger.debug(f"WebSocket subscribed to network {network_id}")

    def subscribe_topology(self, websocket: WebSocket):
        """
        Subscribe a connection to topology updates.

        Args:
            websocket: WebSocket connection
        """
        self.topology_subscriptions.add(websocket)
        logger.debug("WebSocket subscribed to topology updates")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send a message to a specific client.

        Args:
            message: Message to send (will be JSON encoded)
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict, connections: Set[WebSocket] = None):
        """
        Broadcast a message to multiple clients.

        Args:
            message: Message to send (will be JSON encoded)
            connections: Set of connections to send to (defaults to all active connections)
        """
        if connections is None:
            connections = self.active_connections

        if not connections:
            return

        message_text = json.dumps(message)
        disconnected = set()

        for connection in connections:
            try:
                await connection.send_text(message_text)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_device_update(self, device_id: int, data: dict):
        """
        Broadcast a device update to subscribed clients.

        Args:
            device_id: Device ID
            data: Update data
        """
        message = {
            "type": "device_update",
            "device_id": device_id,
            "data": data,
        }

        # Send to device subscribers
        subscribers = self.device_subscriptions.get(device_id, set())
        await self.broadcast(message, subscribers)

        logger.debug(f"Broadcasted device update for device {device_id} to {len(subscribers)} clients")

    async def broadcast_device_metrics(self, device_id: int, metrics: dict):
        """
        Broadcast device metrics to subscribed clients.

        Args:
            device_id: Device ID
            metrics: Metrics data
        """
        message = {
            "type": "device_metrics",
            "device_id": device_id,
            "data": metrics,
        }

        # Send to device subscribers
        subscribers = self.device_subscriptions.get(device_id, set())
        await self.broadcast(message, subscribers)

        logger.debug(f"Broadcasted metrics for device {device_id} to {len(subscribers)} clients")

    async def broadcast_topology_update(self, topology_data: dict):
        """
        Broadcast topology update to subscribed clients.

        Args:
            topology_data: Topology data
        """
        message = {
            "type": "topology_update",
            "data": topology_data,
        }

        await self.broadcast(message, self.topology_subscriptions)

        logger.debug(f"Broadcasted topology update to {len(self.topology_subscriptions)} clients")

    async def broadcast_network_update(self, network_id: int, data: dict):
        """
        Broadcast network update to subscribed clients.

        Args:
            network_id: Network ID
            data: Update data
        """
        message = {
            "type": "network_update",
            "network_id": network_id,
            "data": data,
        }

        # Send to network subscribers
        subscribers = self.network_subscriptions.get(network_id, set())
        await self.broadcast(message, subscribers)

        logger.debug(f"Broadcasted network update for network {network_id} to {len(subscribers)} clients")


# Global connection manager instance
manager = ConnectionManager()
