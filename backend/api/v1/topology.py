"""
Network topology API endpoints.
"""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database import get_db
from backend.models.device import Device
from backend.models.network import Network

router = APIRouter()


@router.get("")
async def get_topology(
    network_id: int | None = Query(None, description="Filter by network ID"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get network topology data.

    Returns nodes (devices) and links (connections) suitable for visualization.

    Args:
        network_id: Optional network ID filter
        db: Database session

    Returns:
        dict: Topology data with nodes and links
    """
    # Build query
    query = select(Device).where(Device.status != "decommissioned")

    if network_id:
        query = query.where(Device.network_id == network_id)

    result = await db.execute(query)
    devices = list(result.scalars().all())

    # Transform devices to nodes
    nodes = []
    for device in devices:
        nodes.append(
            {
                "id": str(device.id),
                "label": device.hostname or f"Device {device.id}",
                "ip": device.ip_address,
                "mac": device.mac_address,
                "status": device.status,
                "subnet_id": device.subnet_id,
                "network_id": device.network_id,
            }
        )

    # Create links between devices
    # In a real implementation, links would come from:
    # 1. Babel routing table (neighbor relationships)
    # 2. WiFi association data
    # 3. LLDP/CDP neighbor discovery
    #
    # For now, create a mesh topology where online devices in the same network
    # are connected based on their neighbor_count to simulate realistic connectivity
    links = []

    # Group devices by network
    network_groups: Dict[int, List[Device]] = {}
    for device in devices:
        if device.network_id and device.status == "online":
            if device.network_id not in network_groups:
                network_groups[device.network_id] = []
            network_groups[device.network_id].append(device)

    # Create mesh links for each network
    for network_id, network_devices in network_groups.items():
        if len(network_devices) < 2:
            continue

        # Sort devices by ID for consistent link generation
        sorted_devices = sorted(network_devices, key=lambda d: d.id)

        # Create links based on each device's neighbor_count
        for i, device in enumerate(sorted_devices):
            # Get the number of neighbors this device should have (from its neighbor_count)
            # Default to 2 if not set
            target_neighbors = min(device.neighbor_count or 2, len(sorted_devices) - 1)

            # Connect to next N devices in a ring pattern
            connected = 0
            for j in range(1, len(sorted_devices)):
                if connected >= target_neighbors:
                    break

                target_idx = (i + j) % len(sorted_devices)
                target_device = sorted_devices[target_idx]

                # Avoid duplicate links (only create if source.id < target.id)
                if device.id < target_device.id:
                    # Determine link quality based on both devices' status and neighbor count
                    quality = "good"
                    if device.neighbor_count >= 3 and target_device.neighbor_count >= 3:
                        quality = "excellent"
                    elif device.neighbor_count <= 1 or target_device.neighbor_count <= 1:
                        quality = "poor"

                    links.append({
                        "source": str(device.id),
                        "target": str(target_device.id),
                        "type": "mesh",
                        "quality": quality,
                    })

                connected += 1

    return {
        "nodes": nodes,
        "links": links,
        "summary": {
            "total_nodes": len(nodes),
            "total_links": len(links),
            "online_nodes": sum(1 for n in nodes if n["status"] == "online"),
        },
    }


@router.get("/links")
async def get_topology_links(
    network_id: int | None = Query(None, description="Filter by network ID"),
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Get topology links (connections between devices).

    Args:
        network_id: Optional network ID filter
        db: Database session

    Returns:
        list: List of links
    """
    # TODO: Implement actual link discovery
    # This would query:
    # - Babel routing daemon for neighbor info
    # - WiFi association tables
    # - Metrics database for link quality

    return [
        {
            "message": "Link discovery not yet implemented",
            "todo": "Integrate with Babel routing daemon to get real mesh links",
        }
    ]
