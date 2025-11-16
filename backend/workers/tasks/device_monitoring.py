"""
Celery tasks for device monitoring and auto-offline detection.
"""

from datetime import datetime, timedelta

from celery import Task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.core.config import settings
from backend.models.device import Device, DeviceStatus
from backend.workers.celery_app import celery_app


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


@celery_app.task(bind=True, base=DatabaseTask, name="device_monitoring.check_offline_devices")
def check_offline_devices(self) -> dict:
    """
    Check for devices that haven't sent heartbeats within the timeout period
    and mark them as OFFLINE.

    This task runs periodically (every 60 seconds) to detect stale devices.
    Uses ALERT_NODE_DOWN_TIMEOUT_SEC from settings (default: 300 seconds = 5 minutes).

    Returns:
        dict: Summary of devices marked offline
    """
    db = self.db_session

    try:
        # Calculate cutoff time based on configured timeout
        timeout_seconds = settings.ALERT_NODE_DOWN_TIMEOUT_SEC
        cutoff_time = datetime.utcnow() - timedelta(seconds=timeout_seconds)

        # Find devices that are marked as ONLINE but haven't been seen recently
        stale_devices = (
            db.query(Device)
            .filter(
                Device.status == DeviceStatus.ONLINE,
                Device.last_seen < cutoff_time,
            )
            .all()
        )

        marked_offline = []

        for device in stale_devices:
            # Calculate how long the device has been offline
            time_since_last_seen = datetime.utcnow() - device.last_seen
            minutes_offline = int(time_since_last_seen.total_seconds() / 60)

            # Mark device as OFFLINE
            device.status = DeviceStatus.OFFLINE
            db.commit()

            # Log the action
            marked_offline.append(
                {
                    "device_id": device.id,
                    "hostname": device.hostname,
                    "last_seen": device.last_seen.isoformat(),
                    "minutes_offline": minutes_offline,
                }
            )

            # Broadcast WebSocket update for device status change
            # Note: This will be imported here to avoid circular dependencies
            try:
                import asyncio

                from backend.core.websocket import manager as ws_manager

                # Create an event loop if needed (Celery runs in sync context)
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                # Broadcast the status change
                loop.run_until_complete(
                    ws_manager.broadcast_device_update(
                        device_id=device.id,
                        data={
                            "status": DeviceStatus.OFFLINE.value,
                            "last_seen": device.last_seen.isoformat(),
                        },
                    )
                )
            except Exception as ws_error:
                # Log WebSocket error but don't fail the task
                print(f"WebSocket broadcast failed for device {device.id}: {ws_error}")

        # Log summary
        if marked_offline:
            print(
                f"Marked {len(marked_offline)} device(s) as OFFLINE: "
                f"{', '.join([d['hostname'] for d in marked_offline])}"
            )

        return {
            "success": True,
            "checked_at": datetime.utcnow().isoformat(),
            "timeout_seconds": timeout_seconds,
            "devices_marked_offline": len(marked_offline),
            "devices": marked_offline,
        }

    except Exception as e:
        # Handle unexpected errors
        print(f"Error in check_offline_devices task: {e}")
        return {
            "success": False,
            "error": str(e),
            "checked_at": datetime.utcnow().isoformat(),
        }

    finally:
        db.close()


@celery_app.task(name="device_monitoring.cleanup_stale_data")
def cleanup_stale_data(days: int = 90) -> dict:
    """
    Clean up very old device records that have been offline for extended periods.

    Args:
        days: Delete devices offline for more than this many days

    Returns:
        dict: Cleanup results
    """
    db_session = DatabaseTask().db_session

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Find devices that have been offline for a very long time
        # and were never registered (PENDING state that never progressed)
        stale_devices = (
            db_session.query(Device)
            .filter(
                Device.status.in_([DeviceStatus.PENDING, DeviceStatus.OFFLINE]),
                Device.last_seen < cutoff_date,
            )
            .all()
        )

        deleted_count = 0

        for device in stale_devices:
            # Only delete if the device has no associated data
            # (check if device has firmware builds, metrics, etc.)
            # For now, we'll just log them
            print(
                f"Found stale device: {device.hostname} "
                f"(last seen: {device.last_seen}, status: {device.status})"
            )
            # Uncomment to actually delete:
            # db_session.delete(device)
            # deleted_count += 1

        # db_session.commit()

        return {
            "success": True,
            "found_stale_devices": len(stale_devices),
            "deleted_devices": deleted_count,
            "cutoff_date": cutoff_date.isoformat(),
        }

    except Exception as e:
        db_session.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db_session.close()
