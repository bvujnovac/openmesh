"""
Celery tasks for firmware building.
"""

from datetime import datetime
from celery import Task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.workers.celery_app import celery_app
from backend.core.config import settings
from backend.models.firmware import FirmwareBuild, BuildStatus
from backend.services.image_builder.builder import ImageBuilder


class DatabaseTask(Task):
    """Base task with database session."""

    _db_session = None
    _engine = None

    @property
    def db_session(self):
        if self._db_session is None:
            # Create synchronous engine for Celery tasks
            if self._engine is None:
                db_url = settings.database_url_sync
                self._engine = create_engine(db_url, pool_pre_ping=True)

            # Create session
            SessionLocal = sessionmaker(bind=self._engine)
            self._db_session = SessionLocal()
        return self._db_session


@celery_app.task(bind=True, base=DatabaseTask, name="firmware.build")
def build_firmware(self, build_id: int) -> dict:
    """
    Build OpenWrt firmware image.

    Args:
        build_id: ID of the FirmwareBuild record

    Returns:
        dict: Build result with status and details
    """
    db = self.db_session

    try:
        # Get build record
        build = db.query(FirmwareBuild).filter(FirmwareBuild.id == build_id).first()
        if not build:
            return {"success": False, "error": f"Build {build_id} not found"}

        # Update status to building
        build.status = BuildStatus.BUILDING
        build.build_started_at = datetime.utcnow()
        db.commit()

        # Create ImageBuilder instance
        builder = ImageBuilder(
            version=build.openwrt_version,
            target=build.target,
            subtarget=build.subtarget,
            profile=build.profile,
        )

        # Add packages
        if build.base_packages:
            for package in build.base_packages:
                builder.add_package(package)

        if build.custom_packages:
            for package in build.custom_packages:
                builder.add_package(package)

        if build.removed_packages:
            for package in build.removed_packages:
                builder.remove_package(package)

        # Add UCI defaults script if provided
        if build.uci_defaults_script:
            builder.add_file(
                "/etc/uci-defaults/99-openmesh-config", build.uci_defaults_script
            )

        # Build the image
        result = builder.build()

        if result["success"]:
            # Update build record with success
            build.status = BuildStatus.SUCCESS
            build.build_completed_at = datetime.utcnow()
            build.build_duration_seconds = (
                build.build_completed_at - build.build_started_at
            ).seconds
            build.image_filename = result["image_filename"]
            build.image_size_bytes = result["image_size"]
            build.image_checksum_sha256 = result["checksum"]
            build.image_path = result["image_path"]
            build.build_log = result.get("log", "")
            db.commit()

            return {
                "success": True,
                "build_id": build_id,
                "image_filename": result["image_filename"],
                "image_size": result["image_size"],
            }
        else:
            # Update build record with failure
            build.status = BuildStatus.FAILED
            build.build_completed_at = datetime.utcnow()
            build.error_message = result.get("error", "Unknown error")
            build.build_log = result.get("log", "")
            db.commit()

            return {"success": False, "build_id": build_id, "error": result.get("error")}

    except Exception as e:
        # Handle unexpected errors
        if build:
            build.status = BuildStatus.FAILED
            build.build_completed_at = datetime.utcnow()
            build.error_message = str(e)
            db.commit()

        return {"success": False, "build_id": build_id, "error": str(e)}

    finally:
        db.close()


@celery_app.task(name="firmware.cleanup_old_builds")
def cleanup_old_builds(days: int = 30) -> dict:
    """
    Clean up old firmware builds.

    Args:
        days: Delete builds older than this many days

    Returns:
        dict: Cleanup results
    """
    from datetime import timedelta
    from pathlib import Path

    db_session = DatabaseTask().db_session

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Find old builds
        old_builds = (
            db_session.query(FirmwareBuild)
            .filter(
                FirmwareBuild.created_at < cutoff_date,
                FirmwareBuild.is_default == False,  # Don't delete default builds
            )
            .all()
        )

        deleted_count = 0
        freed_bytes = 0

        for build in old_builds:
            # Delete image file if exists
            if build.image_path:
                image_path = Path(build.image_path)
                if image_path.exists():
                    freed_bytes += image_path.stat().st_size
                    image_path.unlink()

            # Delete build record
            db_session.delete(build)
            deleted_count += 1

        db_session.commit()

        return {
            "success": True,
            "deleted_builds": deleted_count,
            "freed_bytes": freed_bytes,
            "freed_mb": freed_bytes / (1024 * 1024),
        }

    except Exception as e:
        db_session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db_session.close()
