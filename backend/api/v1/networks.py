"""
Network management API endpoints.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.schemas.network import (
    NetworkCreate,
    NetworkUpdate,
    NetworkResponse,
    NetworkDetailResponse,
    NetworkListResponse,
)
from backend.services.network_service import NetworkService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=NetworkListResponse)
async def list_networks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
) -> NetworkListResponse:
    """
    List all networks with pagination.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        active_only: Only return active networks
        db: Database session

    Returns:
        NetworkListResponse: Paginated list of networks
    """
    service = NetworkService(db)
    networks = await service.list_networks(skip=skip, limit=limit, active_only=active_only)
    total = await service.count_networks(active_only=active_only)

    return NetworkListResponse(
        total=total,
        page=(skip // limit) + 1,
        page_size=limit,
        networks=[NetworkResponse.model_validate(n) for n in networks],
    )


@router.get("/{network_id}", response_model=NetworkDetailResponse)
async def get_network(
    network_id: int, db: AsyncSession = Depends(get_db)
) -> NetworkDetailResponse:
    """
    Get network details by ID.

    Args:
        network_id: Network ID
        db: Database session

    Returns:
        NetworkDetailResponse: Network details

    Raises:
        HTTPException: If network not found
    """
    service = NetworkService(db)
    network = await service.get_network(network_id)

    if not network:
        raise HTTPException(status_code=404, detail="Network not found")

    return NetworkDetailResponse.model_validate(network)


@router.post("", response_model=NetworkResponse, status_code=201)
async def create_network(
    network_data: NetworkCreate, db: AsyncSession = Depends(get_db)
) -> NetworkResponse:
    """
    Create a new mesh network.

    Args:
        network_data: Network creation data
        db: Database session

    Returns:
        NetworkResponse: Created network

    Raises:
        HTTPException: If network with slug already exists
    """
    try:
        logger.info(f"API: Creating network '{network_data.name}' with slug '{network_data.slug}'")
        service = NetworkService(db)

        # Check if network with slug exists
        existing = await service.get_network_by_slug(network_data.slug)
        if existing:
            logger.warning(f"Network with slug '{network_data.slug}' already exists")
            raise HTTPException(status_code=409, detail="Network with this slug already exists")

        network = await service.create_network(network_data)
        logger.info(f"API: Network '{network.name}' created successfully (id: {network.id})")
        return NetworkResponse.model_validate(network)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"API: Failed to create network: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create network: {str(e)}")


@router.patch("/{network_id}", response_model=NetworkResponse)
async def update_network(
    network_id: int, network_data: NetworkUpdate, db: AsyncSession = Depends(get_db)
) -> NetworkResponse:
    """
    Update network configuration.

    Args:
        network_id: Network ID
        network_data: Network update data
        db: Database session

    Returns:
        NetworkResponse: Updated network

    Raises:
        HTTPException: If network not found
    """
    service = NetworkService(db)
    network = await service.update_network(network_id, network_data)

    if not network:
        raise HTTPException(status_code=404, detail="Network not found")

    return NetworkResponse.model_validate(network)


@router.delete("/{network_id}", status_code=204)
async def delete_network(network_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """
    Delete a network.

    Note: This will fail if there are devices associated with this network.

    Args:
        network_id: Network ID
        db: Database session

    Raises:
        HTTPException: If network not found or has associated devices
    """
    service = NetworkService(db)
    success = await service.delete_network(network_id)

    if not success:
        raise HTTPException(
            status_code=400, detail="Cannot delete network with associated devices"
        )
