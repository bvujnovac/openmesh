"""
Device management API endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.schemas.device import (
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceDetailResponse,
    DeviceListResponse,
    DeviceConfigResponse,
    DeviceRegister,
    DeviceStatusUpdate,
)
from backend.services.device_service import DeviceService
from backend.services.monitoring.influxdb_client import get_influx_client
from backend.models.device import DeviceStatus

router = APIRouter()


@router.get("", response_model=DeviceListResponse)
async def list_devices(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: DeviceStatus | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> DeviceListResponse:
    """
    List all devices with pagination and filtering.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by device status
        search: Search in hostname, MAC address, or IP
        db: Database session

    Returns:
        DeviceListResponse: Paginated list of devices
    """
    service = DeviceService(db)
    devices, total = await service.list_devices(
        skip=skip, limit=limit, status=status, search=search
    )

    return DeviceListResponse(
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
        devices=[DeviceResponse.model_validate(d) for d in devices],
    )


@router.get("/{device_id}", response_model=DeviceDetailResponse)
async def get_device(device_id: int, db: AsyncSession = Depends(get_db)) -> DeviceDetailResponse:
    """
    Get device details by ID.

    Args:
        device_id: Device ID
        db: Database session

    Returns:
        DeviceDetailResponse: Device details

    Raises:
        HTTPException: If device not found
    """
    service = DeviceService(db)
    device = await service.get_device(device_id)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return DeviceDetailResponse.model_validate(device)


@router.post("", response_model=DeviceResponse, status_code=201)
async def create_device(
    device_data: DeviceCreate, db: AsyncSession = Depends(get_db)
) -> DeviceResponse:
    """
    Register a new device.

    Args:
        device_data: Device creation data
        db: Database session

    Returns:
        DeviceResponse: Created device

    Raises:
        HTTPException: If MAC address already exists
    """
    service = DeviceService(db)

    # Check if device already exists
    existing = await service.get_device_by_mac(device_data.mac_address)
    if existing:
        raise HTTPException(status_code=409, detail="Device with this MAC address already exists")

    device = await service.create_device(device_data)
    return DeviceResponse.model_validate(device)


@router.post("/register", response_model=DeviceConfigResponse, status_code=201)
async def register_device(
    registration: DeviceRegister, db: AsyncSession = Depends(get_db)
) -> DeviceConfigResponse:
    """
    Device self-registration endpoint.

    Called by mesh routers to register themselves and get configuration.

    Args:
        registration: Device registration data
        db: Database session

    Returns:
        DeviceConfigResponse: Device configuration including IP, DHCP pools, and config script
    """
    service = DeviceService(db)

    # Check if device exists
    device = await service.get_device_by_mac(registration.mac_address)

    if device:
        # Update existing device
        await service.update_device_status(
            device.id,
            DeviceStatusUpdate(
                firmware_version=registration.firmware_version,
                uptime_seconds=0,  # Just rebooted
            ),
        )
    else:
        # Create new device
        device = await service.create_device(
            DeviceCreate(
                mac_address=registration.mac_address,
                hostname=registration.hostname,
                hardware_model=registration.hardware_model,
            )
        )

    # Get device configuration
    config = await service.get_device_config(device.id)
    return config


@router.patch("/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: int, device_data: DeviceUpdate, db: AsyncSession = Depends(get_db)
) -> DeviceResponse:
    """
    Update device information.

    Args:
        device_id: Device ID
        device_data: Device update data
        db: Database session

    Returns:
        DeviceResponse: Updated device

    Raises:
        HTTPException: If device not found
    """
    service = DeviceService(db)
    device = await service.update_device(device_id, device_data)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    return DeviceResponse.model_validate(device)


@router.post("/{device_id}/heartbeat", status_code=204)
async def device_heartbeat(
    device_id: int, status_update: DeviceStatusUpdate, db: AsyncSession = Depends(get_db)
) -> None:
    """
    Device heartbeat endpoint.

    Called periodically by mesh routers to report status.
    Updates device status in SQLite and writes metrics to InfluxDB.

    Args:
        device_id: Device ID
        status_update: Status update data
        db: Database session

    Raises:
        HTTPException: If device not found
    """
    service = DeviceService(db)
    device = await service.update_device_status(device_id, status_update)

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    # Write metrics to InfluxDB (async, non-blocking)
    try:
        influx = get_influx_client()

        # Prepare metrics dict from status update
        metrics = {}
        if status_update.uptime_seconds is not None:
            metrics["uptime_seconds"] = status_update.uptime_seconds
        if status_update.load_average:
            # Parse load average (e.g., "0.5, 0.4, 0.3")
            loads = [float(x.strip()) for x in status_update.load_average.split(",")]
            if len(loads) >= 3:
                metrics["load_1min"] = loads[0]
                metrics["load_5min"] = loads[1]
                metrics["load_15min"] = loads[2]
        if status_update.memory_total_mb is not None:
            metrics["memory_total_mb"] = status_update.memory_total_mb
        if status_update.memory_free_mb is not None:
            metrics["memory_free_mb"] = status_update.memory_free_mb
        if status_update.cpu_usage_percent is not None:
            metrics["cpu_usage_percent"] = status_update.cpu_usage_percent
        if status_update.neighbor_count is not None:
            metrics["neighbor_count"] = status_update.neighbor_count
        if status_update.route_count is not None:
            metrics["route_count"] = status_update.route_count
        if status_update.installed_route_count is not None:
            metrics["installed_route_count"] = status_update.installed_route_count
        if status_update.xroute_count is not None:
            metrics["xroute_count"] = status_update.xroute_count
        if status_update.avg_rtt_ms is not None:
            metrics["avg_rtt_ms"] = status_update.avg_rtt_ms

        # Write to InfluxDB
        if metrics:
            influx.write_device_metric(
                device_id=device.id, device_mac=device.mac_address, metrics=metrics
            )
    except Exception as e:
        # Log error but don't fail the heartbeat
        print(f"Warning: Failed to write metrics to InfluxDB: {e}")


@router.delete("/{device_id}", status_code=204)
async def delete_device(device_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """
    Delete a device.

    Args:
        device_id: Device ID
        db: Database session

    Raises:
        HTTPException: If device not found
    """
    service = DeviceService(db)
    success = await service.delete_device(device_id)

    if not success:
        raise HTTPException(status_code=404, detail="Device not found")


@router.get("/{device_id}/config", response_model=DeviceConfigResponse)
async def get_device_config(
    device_id: int, db: AsyncSession = Depends(get_db)
) -> DeviceConfigResponse:
    """
    Get device configuration.

    Returns UCI defaults script and network configuration.

    Args:
        device_id: Device ID
        db: Database session

    Returns:
        DeviceConfigResponse: Device configuration

    Raises:
        HTTPException: If device not found
    """
    service = DeviceService(db)
    config = await service.get_device_config(device_id)

    if not config:
        raise HTTPException(status_code=404, detail="Device not found")

    return config
