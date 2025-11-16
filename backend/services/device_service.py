"""
Device service layer.
Contains business logic for device management.
"""

from datetime import datetime
from typing import Optional, Tuple, List
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.device import Device, DeviceStatus
from backend.models.network import Network
from backend.schemas.device import DeviceCreate, DeviceUpdate, DeviceStatusUpdate, DeviceConfigResponse
from backend.services.config_gen.ip_allocator import IPAllocator
from backend.services.config_gen.uci_generator import UCIGenerator


class DeviceService:
    """Service class for device operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_devices(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[DeviceStatus] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Device], int]:
        """
        List devices with pagination and filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by device status
            search: Search in hostname, MAC, or IP

        Returns:
            Tuple of (devices list, total count)
        """
        # Build query
        query = select(Device)

        # Apply filters
        if status:
            query = query.where(Device.status == status)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Device.hostname.ilike(search_pattern),
                    Device.mac_address.ilike(search_pattern),
                    Device.ip_address.ilike(search_pattern),
                )
            )

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Apply pagination and eager load network relationship
        query = query.options(selectinload(Device.network)).offset(skip).limit(limit).order_by(Device.created_at.desc())

        # Execute query
        result = await self.db.execute(query)
        devices = list(result.scalars().all())

        return devices, total

    async def get_device(self, device_id: int) -> Optional[Device]:
        """Get device by ID."""
        result = await self.db.execute(
            select(Device).options(selectinload(Device.network)).where(Device.id == device_id)
        )
        return result.scalar_one_or_none()

    async def get_device_by_mac(self, mac_address: str) -> Optional[Device]:
        """Get device by MAC address."""
        result = await self.db.execute(select(Device).where(Device.mac_address == mac_address))
        return result.scalar_one_or_none()

    async def create_device(self, device_data: DeviceCreate) -> Device:
        """
        Create a new device.

        Automatically assigns IP address and DHCP pool based on MAC address.
        """
        # Get default network (for now, use first network or create default)
        network = await self._get_or_create_default_network()

        # Allocate IP address and DHCP pool
        allocator = IPAllocator(
            network_cidr=network.network_cidr,
            infrastructure_cidr=network.infrastructure_cidr,
            client_pool_start=network.client_pool_start,
            max_routers=network.max_routers,
            clients_per_router=network.clients_per_router,
        )

        allocation = allocator.allocate_for_mac(device_data.mac_address)

        # Create device
        device = Device(
            mac_address=device_data.mac_address,
            hostname=device_data.hostname,
            ip_address=allocation["router_ip"],
            dhcp_pool_start=allocation["dhcp_start"],
            dhcp_pool_end=allocation["dhcp_end"],
            subnet_id=allocation["subnet_id"],
            hardware_model=device_data.hardware_model,
            location_name=device_data.location_name,
            notes=device_data.notes,
            status=DeviceStatus.PENDING,
        )

        self.db.add(device)
        await self.db.commit()
        await self.db.refresh(device)

        return device

    async def update_device(self, device_id: int, device_data: DeviceUpdate) -> Optional[Device]:
        """Update device information."""
        device = await self.get_device(device_id)
        if not device:
            return None

        # Update fields
        update_data = device_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(device, field, value)

        device.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(device)

        return device

    async def update_device_status(
        self, device_id: int, status_update: DeviceStatusUpdate
    ) -> Optional[Device]:
        """Update device status (called by heartbeat)."""
        device = await self.get_device(device_id)
        if not device:
            return None

        # Update status fields
        update_data = status_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(device, field, value)

        # Update last seen and status
        device.last_seen = datetime.utcnow()
        if device.status == DeviceStatus.PENDING or device.status == DeviceStatus.OFFLINE:
            device.status = DeviceStatus.ONLINE

        await self.db.commit()
        await self.db.refresh(device)

        return device

    async def delete_device(self, device_id: int) -> bool:
        """Delete a device."""
        device = await self.get_device(device_id)
        if not device:
            return False

        await self.db.delete(device)
        await self.db.commit()

        return True

    async def get_device_config(self, device_id: int) -> Optional[DeviceConfigResponse]:
        """
        Get device configuration including UCI defaults script.
        """
        device = await self.get_device(device_id)
        if not device:
            return None

        # Get network configuration
        network = await self._get_or_create_default_network()

        # Generate UCI defaults script
        generator = UCIGenerator(
            router_ip=device.ip_address,
            dhcp_pool_start=device.dhcp_pool_start,
            dhcp_pool_end=device.dhcp_pool_end,
            network_cidr=network.network_cidr,
            infrastructure_cidr=network.infrastructure_cidr,
            mesh_ssid=network.mesh_ssid,
            mesh_password=network.mesh_password or "",
            clients_per_router=network.clients_per_router,
            # Client AP parameters (optional)
            client_ssid=network.client_ssid,
            client_password=network.client_password,
            client_encryption=network.client_encryption or "none",
        )

        config_script = generator.generate()

        return DeviceConfigResponse(
            device_id=device.id,
            mac_address=device.mac_address,
            ip_address=device.ip_address,
            dhcp_pool_start=device.dhcp_pool_start,
            dhcp_pool_end=device.dhcp_pool_end,
            network_cidr=network.network_cidr,
            mesh_ssid=network.mesh_ssid,
            config_script=config_script,
        )

    async def _get_or_create_default_network(self) -> Network:
        """Get or create default network."""
        result = await self.db.execute(select(Network).where(Network.is_active == True).limit(1))
        network = result.scalar_one_or_none()

        if not network:
            # Create default network
            network = Network(
                name="Default Mesh Network",
                slug="default",
                description="Auto-created default mesh network",
                network_cidr="10.0.0.0/16",
                infrastructure_cidr="10.0.0.0/23",
                client_pool_start="10.0.2.0",
                max_routers=508,
                clients_per_router=126,
                mesh_ssid="openmesh",
                routing_protocol="babel",
                is_active=True,
            )
            self.db.add(network)
            await self.db.commit()
            await self.db.refresh(network)

        return network
