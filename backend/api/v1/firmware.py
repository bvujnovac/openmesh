"""
Firmware build management API endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pathlib import Path

from backend.core.database import get_db
from backend.schemas.firmware import (
    FirmwareBuildCreate,
    FirmwareBuildResponse,
    FirmwareBuildDetailResponse,
    FirmwareBuildListResponse,
    FirmwareBuildTaskResponse,
)
from backend.models.firmware import FirmwareBuild, BuildStatus
from backend.models.network import Network
from backend.workers.tasks.firmware import build_firmware
from backend.services.image_builder.builder import get_default_packages
from backend.services.config_gen.uci_generator import UCIGenerator
from backend.services.image_builder.package_sets import PACKAGE_SETS, get_package_set
from backend.services.image_builder.profile_discovery import (
    discover_profiles,
    search_profiles,
    get_common_targets,
)
from datetime import datetime

router = APIRouter()


@router.get("/package-sets")
async def list_package_sets():
    """
    List all available package sets for firmware builds.

    Returns:
        List of package sets with descriptions and requirements
    """
    return {
        "package_sets": [
            {
                "key": key,
                "name": pkg_set.name,
                "description": pkg_set.description,
                "packages": pkg_set.packages,
                "remove_packages": pkg_set.remove_packages,
                "min_flash_mb": pkg_set.min_flash_mb,
                "min_ram_mb": pkg_set.min_ram_mb,
                "recommended_for": pkg_set.recommended_for,
            }
            for key, pkg_set in PACKAGE_SETS.items()
        ]
    }


@router.get("/targets")
async def list_targets():
    """
    List common OpenWrt targets and subtargets.

    Returns:
        List of common targets with descriptions
    """
    return {
        "targets": get_common_targets()
    }


@router.get("/profiles/{target}/{subtarget}")
async def list_profiles(
    target: str,
    subtarget: str,
    search: str = Query(None, description="Search query for filtering profiles"),
    version: str = Query("23.05.2", description="OpenWrt version"),
):
    """
    List available device profiles for a target/subtarget.

    This queries the OpenWrt ImageBuilder to discover all supported devices.

    Args:
        target: OpenWrt target (e.g., "ath79")
        subtarget: OpenWrt subtarget (e.g., "generic")
        search: Optional search query to filter profiles
        version: OpenWrt version (default: "23.05.2")

    Returns:
        List of available device profiles

    Example:
        GET /api/v1/firmware/profiles/ath79/generic?search=ubiquiti
    """
    if search:
        profiles = search_profiles(target, subtarget, search, version)
    else:
        profiles = discover_profiles(target, subtarget, version)

    return {
        "target": target,
        "subtarget": subtarget,
        "version": version,
        "count": len(profiles),
        "profiles": profiles,
    }


@router.get("", response_model=FirmwareBuildListResponse)
async def list_firmware_builds(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: BuildStatus | None = None,
    db: AsyncSession = Depends(get_db),
) -> FirmwareBuildListResponse:
    """
    List firmware builds with pagination and filtering.

    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by build status
        db: Database session

    Returns:
        FirmwareBuildListResponse: Paginated list of builds
    """
    query = select(FirmwareBuild)

    if status:
        query = query.where(FirmwareBuild.status == status)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(FirmwareBuild.created_at.desc())

    result = await db.execute(query)
    builds = list(result.scalars().all())

    return FirmwareBuildListResponse(
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit,
        builds=[FirmwareBuildResponse.model_validate(b) for b in builds],
    )


@router.get("/{build_id}", response_model=FirmwareBuildDetailResponse)
async def get_firmware_build(
    build_id: int, db: AsyncSession = Depends(get_db)
) -> FirmwareBuildDetailResponse:
    """
    Get firmware build details by ID.

    Args:
        build_id: Build ID
        db: Database session

    Returns:
        FirmwareBuildDetailResponse: Build details

    Raises:
        HTTPException: If build not found
    """
    result = await db.execute(select(FirmwareBuild).where(FirmwareBuild.id == build_id))
    build = result.scalar_one_or_none()

    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    return FirmwareBuildDetailResponse.model_validate(build)


@router.post("", response_model=FirmwareBuildTaskResponse, status_code=202)
async def create_firmware_build(
    build_data: FirmwareBuildCreate, db: AsyncSession = Depends(get_db)
) -> FirmwareBuildTaskResponse:
    """
    Create and start a new firmware build.

    Args:
        build_data: Build configuration
        db: Database session

    Returns:
        FirmwareBuildTaskResponse: Task ID and build ID

    Raises:
        HTTPException: If network not found
    """
    # If package_set is provided, apply package configuration
    if build_data.package_set:
        package_set = get_package_set(build_data.package_set)
        if not package_set:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown package set: {build_data.package_set}"
            )

        # Use packages from package set if not specified
        if not build_data.base_packages:
            build_data.base_packages = package_set.packages.copy()
        if not build_data.removed_packages:
            build_data.removed_packages = package_set.remove_packages.copy()

    # Verify network exists if specified
    if build_data.network_id:
        result = await db.execute(
            select(Network).where(Network.id == build_data.network_id)
        )
        network = result.scalar_one_or_none()
        if not network:
            raise HTTPException(status_code=404, detail="Network not found")
    else:
        # Get default network
        result = await db.execute(select(Network).where(Network.is_active == True).limit(1))
        network = result.scalar_one_or_none()
        if not network:
            raise HTTPException(status_code=400, detail="No active network found")

    # Generate build number
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    build_number = f"build-{timestamp}"

    # Prepare packages
    packages = build_data.base_packages if build_data.base_packages else get_default_packages()

    # Generate UCI defaults script if requested
    uci_script = None
    if build_data.include_uci_defaults:
        # Generate a generic UCI defaults script (device-specific config added later)
        generator = UCIGenerator(
            router_ip="10.0.0.1",  # Placeholder, will be customized per device
            dhcp_pool_start="10.0.2.1",
            dhcp_pool_end="10.0.2.126",
            network_cidr=network.network_cidr,
            infrastructure_cidr=network.infrastructure_cidr,
            mesh_ssid=network.mesh_ssid,
            mesh_password=network.mesh_password or "",
            clients_per_router=network.clients_per_router,
        )
        uci_script = generator.generate()

    # Create build record
    build = FirmwareBuild(
        build_number=build_number,
        name=build_data.name,
        openwrt_version=build_data.openwrt_version,
        target=build_data.target,
        subtarget=build_data.subtarget,
        profile=build_data.profile,
        network_id=network.id,
        network_cidr=network.network_cidr,
        mesh_ssid=network.mesh_ssid,
        base_packages=packages,
        custom_packages=build_data.custom_packages,
        removed_packages=build_data.removed_packages,
        uci_defaults_script=uci_script,
        status=BuildStatus.PENDING,
        notes=build_data.notes,
    )

    db.add(build)
    await db.commit()
    await db.refresh(build)

    # Start Celery task
    task = build_firmware.delay(build.id)

    return FirmwareBuildTaskResponse(
        task_id=task.id, build_id=build.id, message=f"Build {build_number} started"
    )


@router.get("/{build_id}/download")
async def download_firmware(build_id: int, db: AsyncSession = Depends(get_db)) -> FileResponse:
    """
    Download firmware image.

    Args:
        build_id: Build ID
        db: Database session

    Returns:
        FileResponse: Firmware image file

    Raises:
        HTTPException: If build not found or not successful
    """
    result = await db.execute(select(FirmwareBuild).where(FirmwareBuild.id == build_id))
    build = result.scalar_one_or_none()

    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    if build.status != BuildStatus.SUCCESS:
        raise HTTPException(status_code=400, detail="Build not successful")

    if not build.image_path:
        raise HTTPException(status_code=404, detail="Image file not found")

    image_path = Path(build.image_path)
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found on disk")

    # Increment download count
    build.download_count += 1
    await db.commit()

    return FileResponse(
        path=image_path,
        filename=build.image_filename,
        media_type="application/octet-stream",
    )


@router.delete("/{build_id}", status_code=204)
async def delete_firmware_build(build_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """
    Delete a firmware build.

    Args:
        build_id: Build ID
        db: Database session

    Raises:
        HTTPException: If build not found or is default
    """
    result = await db.execute(select(FirmwareBuild).where(FirmwareBuild.id == build_id))
    build = result.scalar_one_or_none()

    if not build:
        raise HTTPException(status_code=404, detail="Build not found")

    if build.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete default build")

    # Delete image file if exists
    if build.image_path:
        image_path = Path(build.image_path)
        if image_path.exists():
            image_path.unlink()

    await db.delete(build)
    await db.commit()
