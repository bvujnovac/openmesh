"""
WebSocket API endpoint for real-time updates.
"""

import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.core.websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for real-time updates.

    Clients can send subscription messages to receive specific updates:
    - {"action": "subscribe", "type": "device", "id": 123}
    - {"action": "subscribe", "type": "network", "id": 1}
    - {"action": "subscribe", "type": "topology"}
    - {"action": "unsubscribe", "type": "device", "id": 123}
    - {"action": "ping"} - Keep-alive ping

    Server sends updates as:
    - {"type": "device_update", "device_id": 123, "data": {...}}
    - {"type": "device_metrics", "device_id": 123, "data": {...}}
    - {"type": "topology_update", "data": {...}}
    - {"type": "network_update", "network_id": 1, "data": {...}}
    - {"type": "pong"} - Response to ping

    Args:
        websocket: WebSocket connection
    """
    await manager.connect(websocket)

    try:
        # Send welcome message
        await manager.send_personal_message(
            {
                "type": "connected",
                "message": "WebSocket connection established",
                "subscriptions": {
                    "available": ["device", "network", "topology"],
                },
            },
            websocket,
        )

        # Listen for messages
        while True:
            data = await websocket.receive_json()

            action = data.get("action")

            if action == "ping":
                # Respond to keep-alive ping
                await manager.send_personal_message({"type": "pong"}, websocket)

            elif action == "subscribe":
                # Handle subscription
                subscription_type = data.get("type")
                subscription_id = data.get("id")

                if subscription_type == "device" and subscription_id:
                    manager.subscribe_device(websocket, subscription_id)
                    await manager.send_personal_message(
                        {
                            "type": "subscribed",
                            "subscription": "device",
                            "device_id": subscription_id,
                        },
                        websocket,
                    )

                elif subscription_type == "network" and subscription_id:
                    manager.subscribe_network(websocket, subscription_id)
                    await manager.send_personal_message(
                        {
                            "type": "subscribed",
                            "subscription": "network",
                            "network_id": subscription_id,
                        },
                        websocket,
                    )

                elif subscription_type == "topology":
                    manager.subscribe_topology(websocket)
                    await manager.send_personal_message(
                        {
                            "type": "subscribed",
                            "subscription": "topology",
                        },
                        websocket,
                    )

                else:
                    await manager.send_personal_message(
                        {
                            "type": "error",
                            "message": f"Invalid subscription type or missing id: {subscription_type}",
                        },
                        websocket,
                    )

            elif action == "unsubscribe":
                # Handle unsubscription
                subscription_type = data.get("type")
                subscription_id = data.get("id")

                if subscription_type == "device" and subscription_id:
                    manager.unsubscribe_device(websocket, subscription_id)
                    await manager.send_personal_message(
                        {
                            "type": "unsubscribed",
                            "subscription": "device",
                            "device_id": subscription_id,
                        },
                        websocket,
                    )

                elif subscription_type == "topology":
                    # Unsubscribe from topology updates
                    manager.topology_subscriptions.discard(websocket)
                    await manager.send_personal_message(
                        {
                            "type": "unsubscribed",
                            "subscription": "topology",
                        },
                        websocket,
                    )

                elif subscription_type == "network" and subscription_id:
                    # Unsubscribe from network updates
                    if subscription_id in manager.network_subscriptions:
                        manager.network_subscriptions[subscription_id].discard(websocket)
                    await manager.send_personal_message(
                        {
                            "type": "unsubscribed",
                            "subscription": "network",
                            "network_id": subscription_id,
                        },
                        websocket,
                    )

                else:
                    await manager.send_personal_message(
                        {
                            "type": "error",
                            "message": f"Invalid unsubscribe request: {subscription_type}",
                        },
                        websocket,
                    )

            else:
                # Unknown action
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "message": f"Unknown action: {action}",
                    },
                    websocket,
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket)
