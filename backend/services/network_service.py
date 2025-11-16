"""
Network service layer.
Contains business logic for network management.
"""

from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.network import Network
from backend.schemas.network import NetworkCreate, NetworkUpdate


class NetworkService:
    """Service class for network operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_networks(
        self, skip: int = 0, limit: int = 50, active_only: bool = True
    ) -> List[Network]:
        """List networks with pagination."""
        query = select(Network)

        if active_only:
            query = query.where(Network.is_active == True)

        query = query.offset(skip).limit(limit).order_by(Network.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_network(self, network_id: int) -> Optional[Network]:
        """Get network by ID."""
        result = await self.db.execute(select(Network).where(Network.id == network_id))
        return result.scalar_one_or_none()

    async def get_network_by_slug(self, slug: str) -> Optional[Network]:
        """Get network by slug."""
        result = await self.db.execute(select(Network).where(Network.slug == slug))
        return result.scalar_one_or_none()

    async def create_network(self, network_data: NetworkCreate) -> Network:
        """Create a new network."""
        # Calculate infrastructure CIDR from network CIDR
        # For /16 network, infrastructure is /23 (10.0.0.0/23)
        network_base = network_data.network_cidr.split("/")[0]
        base_parts = network_base.split(".")
        infrastructure_cidr = f"{base_parts[0]}.{base_parts[1]}.0.0/23"
        client_pool_start = f"{base_parts[0]}.{base_parts[1]}.2.0"

        network = Network(
            name=network_data.name,
            slug=network_data.slug,
            description=network_data.description,
            network_cidr=network_data.network_cidr,
            infrastructure_cidr=infrastructure_cidr,
            client_pool_start=client_pool_start,
            mesh_ssid=network_data.mesh_ssid,
            mesh_password=network_data.mesh_password,
            client_ssid=network_data.client_ssid,
            client_password=network_data.client_password,
        )

        self.db.add(network)
        await self.db.commit()
        await self.db.refresh(network)

        return network

    async def update_network(
        self, network_id: int, network_data: NetworkUpdate
    ) -> Optional[Network]:
        """Update network configuration."""
        network = await self.get_network(network_id)
        if not network:
            return None

        # Update fields
        update_data = network_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(network, field, value)

        await self.db.commit()
        await self.db.refresh(network)

        return network

    async def delete_network(self, network_id: int) -> bool:
        """Delete a network (only if no devices are associated)."""
        network = await self.get_network(network_id)
        if not network:
            return False

        # Check if network has devices
        if network.device_count > 0:
            return False

        await self.db.delete(network)
        await self.db.commit()

        return True
