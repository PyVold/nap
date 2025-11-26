"""
Exponential Backoff Utility
Handles device check backoff logic to reduce load on unresponsive devices
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from db_models import DeviceDB
from utils.logger import setup_logger

logger = setup_logger(__name__)


class BackoffManager:
    """Manages exponential backoff for device checks"""

    # Backoff intervals in minutes for each failure count
    # 0 failures: normal (5 min)
    # 1 failure: 5 min
    # 2 failures: 15 min
    # 3 failures: 30 min
    # 4+ failures: 120 min (2 hours)
    BACKOFF_INTERVALS = {
        0: 5,      # Normal check interval
        1: 5,      # First failure - keep checking normally
        2: 15,     # Second failure - back off slightly
        3: 30,     # Third failure - back off more
        4: 120,    # Fourth+ failure - max backoff (2 hours)
    }

    # Maximum backoff interval (2 hours)
    MAX_BACKOFF_MINUTES = 120

    # Failure threshold to start backoff
    BACKOFF_THRESHOLD = 2

    @staticmethod
    def calculate_next_check_time(failures: int) -> datetime:
        """
        Calculate the next check time based on failure count

        Args:
            failures: Number of consecutive failures

        Returns:
            datetime: Next scheduled check time
        """
        # Get backoff interval for failure count
        interval = BackoffManager.BACKOFF_INTERVALS.get(
            failures,
            BackoffManager.MAX_BACKOFF_MINUTES
        )

        next_check = datetime.utcnow() + timedelta(minutes=interval)
        logger.debug(f"Calculated next check time: {next_check} (failures: {failures}, interval: {interval}min)")
        return next_check

    @staticmethod
    def should_check_device(device: DeviceDB) -> bool:
        """
        Determine if a device should be checked now based on backoff state

        Args:
            device: DeviceDB instance

        Returns:
            bool: True if device should be checked, False if backed off
        """
        # If device has no backoff set, check it
        if device.next_check_due is None:
            return True

        # Check if it's time to check the device
        now = datetime.utcnow()
        should_check = now >= device.next_check_due

        if not should_check:
            time_remaining = (device.next_check_due - now).total_seconds() / 60
            logger.debug(
                f"Device {device.hostname} backed off - "
                f"next check in {time_remaining:.1f} minutes "
                f"({device.consecutive_failures} failures)"
            )

        return should_check

    @staticmethod
    def record_failure(db: Session, device: DeviceDB) -> None:
        """
        Record a device check failure and update backoff state

        Args:
            db: Database session
            device: DeviceDB instance
        """
        device.consecutive_failures += 1
        device.last_check_attempt = datetime.utcnow()
        device.next_check_due = BackoffManager.calculate_next_check_time(
            device.consecutive_failures
        )

        logger.info(
            f"Device {device.hostname} check failed - "
            f"consecutive failures: {device.consecutive_failures}, "
            f"next check: {device.next_check_due}"
        )

        db.commit()

    @staticmethod
    def record_success(db: Session, device: DeviceDB) -> None:
        """
        Record a successful device check and reset backoff state

        Args:
            db: Database session
            device: DeviceDB instance
        """
        if device.consecutive_failures > 0:
            logger.info(
                f"Device {device.hostname} check succeeded - "
                f"resetting backoff (was {device.consecutive_failures} failures)"
            )

        device.consecutive_failures = 0
        device.last_check_attempt = datetime.utcnow()
        device.next_check_due = None  # No backoff needed

        db.commit()

    @staticmethod
    def force_check(db: Session, device: DeviceDB) -> None:
        """
        Force an immediate check by clearing backoff state

        Args:
            db: Database session
            device: DeviceDB instance
        """
        logger.info(
            f"Forcing check for device {device.hostname} "
            f"(was backed off with {device.consecutive_failures} failures)"
        )

        device.next_check_due = None
        device.last_check_attempt = datetime.utcnow()
        # Keep consecutive_failures to track history but allow check

        db.commit()

    @staticmethod
    def get_backoff_status(device: DeviceDB) -> Dict[str, Any]:
        """
        Get human-readable backoff status for a device

        Args:
            device: DeviceDB instance

        Returns:
            dict: Backoff status information
        """
        if device.consecutive_failures == 0:
            return {
                "is_backed_off": False,
                "consecutive_failures": 0,
                "status": "normal",
                "message": "Device checks are running normally"
            }

        if device.next_check_due is None:
            return {
                "is_backed_off": False,
                "consecutive_failures": device.consecutive_failures,
                "status": "normal",
                "message": f"Device has {device.consecutive_failures} recent failures but checks continue normally"
            }

        now = datetime.utcnow()
        time_remaining = (device.next_check_due - now).total_seconds()

        if time_remaining <= 0:
            return {
                "is_backed_off": False,
                "consecutive_failures": device.consecutive_failures,
                "status": "ready",
                "message": f"Device check is due now ({device.consecutive_failures} previous failures)"
            }

        minutes_remaining = int(time_remaining / 60)
        return {
            "is_backed_off": True,
            "consecutive_failures": device.consecutive_failures,
            "status": "backed_off",
            "message": f"Next check in {minutes_remaining} minutes (backed off due to {device.consecutive_failures} failures)",
            "next_check_due": device.next_check_due.isoformat() if device.next_check_due else None,
            "minutes_remaining": minutes_remaining
        }
