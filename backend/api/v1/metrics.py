"""
Metrics API endpoints for querying time-series data.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.database import get_db
from backend.models.device import Device
from backend.models.network import Network
from backend.services.monitoring.influxdb_client import get_influx_client

router = APIRouter()


@router.get("/devices/{device_id}")
async def get_device_metrics(
    device_id: int,
    start: str = Query("-1h", description="Start time (e.g. -1h, -24h, -7d)"),
    end: str = Query("now()", description="End time"),
    metrics: str = Query(
        "uptime_seconds,load_1min,memory_total_mb",
        description="Comma-separated list of metrics",
    ),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get time-series metrics for a specific device.

    Args:
        device_id: Device ID
        start: Start time (InfluxDB format: -1h, -24h, -7d, or RFC3339 timestamp)
        end: End time (InfluxDB format: now() or RFC3339 timestamp)
        metrics: Comma-separated list of metric names
        db: Database session

    Returns:
        dict: Metrics data
    """
    # Verify device exists
    result = await db.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    try:
        influx = get_influx_client()
        metric_list = [m.strip() for m in metrics.split(",")]

        # Build InfluxDB query
        fields_filter = " or ".join([f'r._field == "{m}"' for m in metric_list])

        query = f'''
        from(bucket: "{influx.bucket}")
            |> range(start: {start}, stop: {end})
            |> filter(fn: (r) => r._measurement == "device_health")
            |> filter(fn: (r) => r.device_id == "{device_id}")
            |> filter(fn: (r) => {fields_filter})
            |> sort(columns: ["_time"])
        '''

        result = influx.query_api.query(query, org=influx.org)

        # Transform results
        data_points = []
        for table in result:
            for record in table.records:
                data_points.append(
                    {
                        "time": record.get_time().isoformat(),
                        "field": record.get_field(),
                        "value": record.get_value(),
                    }
                )

        return {
            "device_id": device_id,
            "device_hostname": device.hostname,
            "start": start,
            "end": end,
            "metrics": metric_list,
            "data": data_points,
            "count": len(data_points),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to query metrics: {str(e)}"
        )


@router.get("/networks/{network_id}")
async def get_network_metrics(
    network_id: int,
    start: str = Query("-1h", description="Start time"),
    end: str = Query("now()", description="End time"),
    aggregate: str = Query("mean", description="Aggregation function (mean, max, min)"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Get aggregated metrics for all devices in a network.

    Args:
        network_id: Network ID
        start: Start time
        end: End time
        aggregate: Aggregation function
        db: Database session

    Returns:
        dict: Aggregated network metrics
    """
    # Verify network exists
    result = await db.execute(select(Network).where(Network.id == network_id))
    network = result.scalar_one_or_none()

    if not network:
        raise HTTPException(status_code=404, detail="Network not found")

    # Get all devices in network
    devices_result = await db.execute(
        select(Device).where(Device.network_id == network_id)
    )
    devices = list(devices_result.scalars().all())

    try:
        influx = get_influx_client()

        # Query aggregated data for network
        query = f'''
        from(bucket: "{influx.bucket}")
            |> range(start: {start}, stop: {end})
            |> filter(fn: (r) => r._measurement == "device_health")
            |> filter(fn: (r) => r.network_id == "{network_id}")
            |> group(columns: ["_field"])
            |> {aggregate}()
            |> yield(name: "{aggregate}")
        '''

        result = influx.query_api.query(query, org=influx.org)

        # Transform results
        aggregated_metrics = {}
        for table in result:
            for record in table.records:
                field = record.get_field()
                value = record.get_value()
                aggregated_metrics[field] = value

        return {
            "network_id": network_id,
            "network_name": network.name,
            "device_count": len(devices),
            "start": start,
            "end": end,
            "aggregate": aggregate,
            "metrics": aggregated_metrics,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to query network metrics: {str(e)}"
        )


@router.get("/system")
async def get_system_metrics(
    start: str = Query("-1h", description="Start time"),
    end: str = Query("now()", description="End time"),
) -> Dict[str, Any]:
    """
    Get system-wide metrics summary.

    Args:
        start: Start time
        end: End time

    Returns:
        dict: System metrics summary
    """
    try:
        influx = get_influx_client()

        # Query system-wide stats
        query = f'''
        from(bucket: "{influx.bucket}")
            |> range(start: {start}, stop: {end})
            |> filter(fn: (r) => r._measurement == "device_health")
            |> group(columns: ["_field"])
            |> count()
            |> yield(name: "data_points")
        '''

        result = influx.query_api.query(query, org=influx.org)

        # Count data points per metric
        data_point_counts = {}
        for table in result:
            for record in table.records:
                field = record.get_field()
                count = record.get_value()
                data_point_counts[field] = count

        return {
            "start": start,
            "end": end,
            "data_points": data_point_counts,
            "total_data_points": sum(data_point_counts.values()),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to query system metrics: {str(e)}"
        )
