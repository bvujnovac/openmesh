"""
Tests for device monitoring and auto-offline detection.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
from backend.models.base import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models.device import Device, DeviceStatus
from backend.workers.tasks.device_monitoring import (
    check_offline_devices,
    cleanup_stale_data,
)


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def mock_celery_task():
    """Mock Celery task with database session."""
    task = Mock()
    return task


class TestCheckOfflineDevices:
    """Tests for the check_offline_devices periodic task."""

    def test_marks_stale_devices_offline(self, in_memory_db):
        """Test that devices without recent heartbeats are marked offline."""
        # Create a device that hasn't been seen in 10 minutes (stale)
        stale_device = Device(
            hostname="stale-device",
            mac_address="00:11:22:33:44:55",
            ip_address="10.0.0.100",
            status=DeviceStatus.ONLINE,
            last_seen=datetime.utcnow() - timedelta(minutes=10),
            network_id=1,
        )
        in_memory_db.add(stale_device)
        in_memory_db.commit()

        # Mock the task's db_session property
        with patch("backend.workers.tasks.device_monitoring.DatabaseTask.db_session", in_memory_db):
            # Mock settings
            with patch("backend.workers.tasks.device_monitoring.settings") as mock_settings:
                mock_settings.ALERT_NODE_DOWN_TIMEOUT_SEC = 300  # 5 minutes

                # Mock WebSocket manager to avoid asyncio issues
                with patch("backend.workers.tasks.device_monitoring.ws_manager"):
                    # Create mock task
                    task = Mock()
                    task.db_session = in_memory_db

                    # Run the check
                    result = check_offline_devices(task)

        # Refresh the device from DB
        in_memory_db.refresh(stale_device)

        # Verify device was marked offline
        assert stale_device.status == DeviceStatus.OFFLINE
        assert result["success"] is True
        assert result["devices_marked_offline"] == 1
        assert result["timeout_seconds"] == 300

    def test_does_not_mark_recent_devices_offline(self, in_memory_db):
        """Test that devices with recent heartbeats remain online."""
        # Create a device that was seen 2 minutes ago (recent)
        recent_device = Device(
            hostname="recent-device",
            mac_address="00:11:22:33:44:66",
            ip_address="10.0.0.101",
            status=DeviceStatus.ONLINE,
            last_seen=datetime.utcnow() - timedelta(minutes=2),
            network_id=1,
        )
        in_memory_db.add(recent_device)
        in_memory_db.commit()

        with patch("backend.workers.tasks.device_monitoring.DatabaseTask.db_session", in_memory_db):
            with patch("backend.workers.tasks.device_monitoring.settings") as mock_settings:
                mock_settings.ALERT_NODE_DOWN_TIMEOUT_SEC = 300  # 5 minutes

                with patch("backend.workers.tasks.device_monitoring.ws_manager"):
                    task = Mock()
                    task.db_session = in_memory_db
                    result = check_offline_devices(task)

        # Refresh the device from DB
        in_memory_db.refresh(recent_device)

        # Verify device remains online
        assert recent_device.status == DeviceStatus.ONLINE
        assert result["success"] is True
        assert result["devices_marked_offline"] == 0

    def test_ignores_already_offline_devices(self, in_memory_db):
        """Test that already offline devices are not processed."""
        # Create a device that is already offline
        offline_device = Device(
            hostname="already-offline",
            mac_address="00:11:22:33:44:77",
            ip_address="10.0.0.102",
            status=DeviceStatus.OFFLINE,
            last_seen=datetime.utcnow() - timedelta(minutes=10),
            network_id=1,
        )
        in_memory_db.add(offline_device)
        in_memory_db.commit()

        with patch("backend.workers.tasks.device_monitoring.DatabaseTask.db_session", in_memory_db):
            with patch("backend.workers.tasks.device_monitoring.settings") as mock_settings:
                mock_settings.ALERT_NODE_DOWN_TIMEOUT_SEC = 300

                with patch("backend.workers.tasks.device_monitoring.ws_manager"):
                    task = Mock()
                    task.db_session = in_memory_db
                    result = check_offline_devices(task)

        # Verify no devices were marked offline (it was already offline)
        assert result["success"] is True
        assert result["devices_marked_offline"] == 0

    def test_ignores_pending_devices(self, in_memory_db):
        """Test that pending devices are not marked offline."""
        # Create a pending device
        pending_device = Device(
            hostname="pending-device",
            mac_address="00:11:22:33:44:88",
            ip_address="10.0.0.103",
            status=DeviceStatus.PENDING,
            last_seen=datetime.utcnow() - timedelta(minutes=10),
            network_id=1,
        )
        in_memory_db.add(pending_device)
        in_memory_db.commit()

        with patch("backend.workers.tasks.device_monitoring.DatabaseTask.db_session", in_memory_db):
            with patch("backend.workers.tasks.device_monitoring.settings") as mock_settings:
                mock_settings.ALERT_NODE_DOWN_TIMEOUT_SEC = 300

                with patch("backend.workers.tasks.device_monitoring.ws_manager"):
                    task = Mock()
                    task.db_session = in_memory_db
                    result = check_offline_devices(task)

        # Verify pending device status unchanged
        in_memory_db.refresh(pending_device)
        assert pending_device.status == DeviceStatus.PENDING
        assert result["devices_marked_offline"] == 0

    def test_marks_multiple_stale_devices(self, in_memory_db):
        """Test marking multiple stale devices offline at once."""
        # Create 3 stale devices
        for i in range(3):
            device = Device(
                hostname=f"stale-device-{i}",
                mac_address=f"00:11:22:33:44:{i:02d}",
                ip_address=f"10.0.0.{100+i}",
                status=DeviceStatus.ONLINE,
                last_seen=datetime.utcnow() - timedelta(minutes=10),
                network_id=1,
            )
            in_memory_db.add(device)
        in_memory_db.commit()

        with patch("backend.workers.tasks.device_monitoring.DatabaseTask.db_session", in_memory_db):
            with patch("backend.workers.tasks.device_monitoring.settings") as mock_settings:
                mock_settings.ALERT_NODE_DOWN_TIMEOUT_SEC = 300

                with patch("backend.workers.tasks.device_monitoring.ws_manager"):
                    task = Mock()
                    task.db_session = in_memory_db
                    result = check_offline_devices(task)

        # Verify all 3 devices were marked offline
        assert result["success"] is True
        assert result["devices_marked_offline"] == 3

        # Verify each device in DB
        devices = in_memory_db.query(Device).all()
        for device in devices:
            assert device.status == DeviceStatus.OFFLINE

    def test_websocket_broadcast_called(self, in_memory_db):
        """Test that WebSocket broadcast is called for each offline device."""
        # Create a stale device
        device = Device(
            hostname="test-device",
            mac_address="00:11:22:33:44:99",
            ip_address="10.0.0.200",
            status=DeviceStatus.ONLINE,
            last_seen=datetime.utcnow() - timedelta(minutes=10),
            network_id=1,
        )
        in_memory_db.add(device)
        in_memory_db.commit()

        with patch("backend.workers.tasks.device_monitoring.DatabaseTask.db_session", in_memory_db):
            with patch("backend.workers.tasks.device_monitoring.settings") as mock_settings:
                mock_settings.ALERT_NODE_DOWN_TIMEOUT_SEC = 300

                # Mock WebSocket manager and asyncio
                with patch("backend.workers.tasks.device_monitoring.ws_manager"):
                    with patch("backend.workers.tasks.device_monitoring.asyncio") as mock_asyncio:
                        mock_loop = MagicMock()
                        mock_asyncio.get_event_loop.return_value = mock_loop

                        task = Mock()
                        task.db_session = in_memory_db
                        check_offline_devices(task)

                        # Verify WebSocket broadcast was attempted
                        assert mock_loop.run_until_complete.called

    def test_handles_database_errors_gracefully(self):
        """Test that database errors are caught and returned in result."""
        with patch("backend.workers.tasks.device_monitoring.DatabaseTask.db_session") as mock_db:
            # Make query raise an exception
            mock_db.query.side_effect = Exception("Database connection failed")

            with patch("backend.workers.tasks.device_monitoring.settings") as mock_settings:
                mock_settings.ALERT_NODE_DOWN_TIMEOUT_SEC = 300

                task = Mock()
                task.db_session = mock_db
                result = check_offline_devices(task)

        # Verify error is handled gracefully
        assert result["success"] is False
        assert "error" in result
        assert "Database connection failed" in result["error"]

    def test_respects_custom_timeout_setting(self, in_memory_db):
        """Test that custom timeout settings are respected."""
        # Create device offline for 8 minutes
        device = Device(
            hostname="test-timeout",
            mac_address="00:11:22:33:55:00",
            ip_address="10.0.0.250",
            status=DeviceStatus.ONLINE,
            last_seen=datetime.utcnow() - timedelta(minutes=8),
            network_id=1,
        )
        in_memory_db.add(device)
        in_memory_db.commit()

        with patch("backend.workers.tasks.device_monitoring.DatabaseTask.db_session", in_memory_db):
            # Set timeout to 10 minutes
            with patch("backend.workers.tasks.device_monitoring.settings") as mock_settings:
                mock_settings.ALERT_NODE_DOWN_TIMEOUT_SEC = 600  # 10 minutes

                with patch("backend.workers.tasks.device_monitoring.ws_manager"):
                    task = Mock()
                    task.db_session = in_memory_db
                    result = check_offline_devices(task)

        # Device should still be online (8 minutes < 10 minute timeout)
        in_memory_db.refresh(device)
        assert device.status == DeviceStatus.ONLINE
        assert result["devices_marked_offline"] == 0
        assert result["timeout_seconds"] == 600


class TestCleanupStaleData:
    """Tests for the cleanup_stale_data periodic task."""

    def test_finds_stale_pending_devices(self, in_memory_db):
        """Test that very old pending devices are found."""
        # Create a device that's been pending for 100 days
        old_device = Device(
            hostname="old-pending",
            mac_address="00:11:22:33:66:00",
            ip_address="10.0.1.100",
            status=DeviceStatus.PENDING,
            last_seen=datetime.utcnow() - timedelta(days=100),
            network_id=1,
        )
        in_memory_db.add(old_device)
        in_memory_db.commit()

        with patch("backend.workers.tasks.device_monitoring.DatabaseTask.db_session", in_memory_db):
            task = Mock()
            task.db_session = in_memory_db

            # Run cleanup (currently just logs, doesn't delete)
            result = cleanup_stale_data(task, days=90)

        # Verify result
        assert result["success"] is True
        assert result["found_stale_devices"] == 1
        # Note: Current implementation doesn't delete, just logs
        assert result["deleted_devices"] == 0

    def test_finds_stale_offline_devices(self, in_memory_db):
        """Test that very old offline devices are found."""
        # Create a device that's been offline for 100 days
        old_device = Device(
            hostname="old-offline",
            mac_address="00:11:22:33:66:11",
            ip_address="10.0.1.101",
            status=DeviceStatus.OFFLINE,
            last_seen=datetime.utcnow() - timedelta(days=100),
            network_id=1,
        )
        in_memory_db.add(old_device)
        in_memory_db.commit()

        with patch("backend.workers.tasks.device_monitoring.DatabaseTask.db_session", in_memory_db):
            task = Mock()
            task.db_session = in_memory_db
            result = cleanup_stale_data(task, days=90)

        assert result["success"] is True
        assert result["found_stale_devices"] == 1

    def test_ignores_recent_offline_devices(self, in_memory_db):
        """Test that recently offline devices are not cleaned up."""
        # Create a device offline for only 30 days
        recent_device = Device(
            hostname="recent-offline",
            mac_address="00:11:22:33:66:22",
            ip_address="10.0.1.102",
            status=DeviceStatus.OFFLINE,
            last_seen=datetime.utcnow() - timedelta(days=30),
            network_id=1,
        )
        in_memory_db.add(recent_device)
        in_memory_db.commit()

        with patch("backend.workers.tasks.device_monitoring.DatabaseTask.db_session", in_memory_db):
            task = Mock()
            task.db_session = in_memory_db
            result = cleanup_stale_data(task, days=90)

        # Should not find this device (30 days < 90 day threshold)
        assert result["success"] is True
        assert result["found_stale_devices"] == 0

    def test_ignores_online_devices(self, in_memory_db):
        """Test that online devices are never cleaned up."""
        # Create an old but still online device
        online_device = Device(
            hostname="old-but-online",
            mac_address="00:11:22:33:66:33",
            ip_address="10.0.1.103",
            status=DeviceStatus.ONLINE,
            last_seen=datetime.utcnow() - timedelta(days=100),
            network_id=1,
        )
        in_memory_db.add(online_device)
        in_memory_db.commit()

        with patch("backend.workers.tasks.device_monitoring.DatabaseTask.db_session", in_memory_db):
            task = Mock()
            task.db_session = in_memory_db
            result = cleanup_stale_data(task, days=90)

        # Should not find online devices even if old
        assert result["success"] is True
        assert result["found_stale_devices"] == 0

    def test_handles_cleanup_errors(self):
        """Test that cleanup errors are caught and returned."""
        with patch("backend.workers.tasks.device_monitoring.DatabaseTask.db_session") as mock_db:
            mock_db.query.side_effect = Exception("Cleanup failed")

            task = Mock()
            task.db_session = mock_db
            result = cleanup_stale_data(task, days=90)

        assert result["success"] is False
        assert "error" in result
        assert "Cleanup failed" in result["error"]


class TestDatabaseTask:
    """Tests for the DatabaseTask base class."""

    def test_database_task_creates_session(self):
        """Test that DatabaseTask creates a database session."""
        from backend.workers.tasks.device_monitoring import DatabaseTask

        with patch("backend.workers.tasks.device_monitoring.settings") as mock_settings:
            mock_settings.database_url_sync = "sqlite:///:memory:"

            task = DatabaseTask()
            session = task.db_session

            # Verify session was created
            assert session is not None
            assert task._db_session is not None
            assert task._engine is not None

    def test_database_task_reuses_session(self):
        """Test that DatabaseTask reuses the same session."""
        from backend.workers.tasks.device_monitoring import DatabaseTask

        with patch("backend.workers.tasks.device_monitoring.settings") as mock_settings:
            mock_settings.database_url_sync = "sqlite:///:memory:"

            task = DatabaseTask()
            session1 = task.db_session
            session2 = task.db_session

            # Should be the same session object
            assert session1 is session2
