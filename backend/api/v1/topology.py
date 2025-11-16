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

    # In a real implementation, links would come from:
    # 1. Babel routing table (neighbor relationships)
    # 2. WiFi association data
    # 3. LLDP/CDP neighbor discovery
    #
    # For now, we'll create logical links based on subnet proximity
    # This is a placeholder - real mesh links should come from Babel data
    links = []
    subnet_groups: Dict[int, List[Device]] = {}

    # Group devices by subnet for proximity-based linking
    for device in devices:
        if device.subnet_id not in subnet_groups:
            subnet_groups[device.subnet_id] = []
        subnet_groups[device.subnet_id].append(device)

    # Create links between devices (placeholder logic)
    # TODO: Replace with actual Babel routing data
    for i, device1 in enumerate(devices):
        for device2 in devices[i + 1 :]:
            # Create link if devices are "close" (same or adjacent subnet)
            if (
                device1.network_id == device2.network_id
                and abs(device1.subnet_id - device2.subnet_id) <= 1
            ):
                links.append(
                    {
                        "source": str(device1.id),
                        "target": str(device2.id),
                        "type": "mesh",
                        "quality": "good",  # TODO: Get from metrics
                    }
                )

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
