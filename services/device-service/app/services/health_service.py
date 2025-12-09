
# ============================================================================
# services/health_service.py
# ============================================================================

import subprocess
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from models.device import Device
from models.enums import DeviceStatus
from db_models import HealthCheckDB, DeviceDB
from connectors import NetconfConnector
from shared.logger import setup_logger
from shared.backoff import BackoffManager

logger = setup_logger(__name__)

class HealthService:
    """Service for device health monitoring including ping and NETCONF"""

    def __init__(self):
        pass

    async def check_device_health(self, db: Session, device: Device, force: bool = False) -> Dict[str, Any]:
        """
        Perform comprehensive health check on a device

        Args:
            db: Database session
            device: Device to check
            force: If True, bypass backoff and check immediately
        """
        # Get device from database to access backoff fields
        device_db = db.query(DeviceDB).filter(DeviceDB.id == device.id).first()
        if not device_db:
            logger.error(f"Device {device.hostname} not found in database")
            return {"error": "Device not found"}

        # Check if device should be checked (unless forced)
        if not force and not BackoffManager.should_check_device(device_db):
            backoff_status = BackoffManager.get_backoff_status(device_db)
            logger.info(f"Skipping health check for {device.hostname}: {backoff_status['message']}")
            return {
                "device_id": device.id,
                "device_name": device.hostname,
                "skipped": True,
                "backoff_status": backoff_status
            }

        logger.info(f"Checking health for device: {device.hostname}")

        # Ping check
        ping_status, ping_latency = await self._ping_device(device.ip or device.hostname)

        # NETCONF check
        netconf_status, netconf_message = await self._check_netconf(device)

        # SSH check (port 22)
        ssh_status, ssh_message = await self._check_ssh(device)

        # Determine overall status based on all checks
        if ping_status and netconf_status and ssh_status:
            overall_status = "healthy"
            device_status = DeviceStatus.ONLINE
        elif ping_status and (netconf_status or ssh_status):
            overall_status = "degraded"
            device_status = DeviceStatus.DEGRADED  # Partially functional
        elif ping_status:
            overall_status = "degraded"
            device_status = DeviceStatus.DEGRADED  # Ping works but no management access
        else:
            overall_status = "unreachable"
            device_status = DeviceStatus.OFFLINE

        # Store health check in database
        health_check = HealthCheckDB(
            device_id=device.id,
            timestamp=datetime.utcnow(),
            ping_status=ping_status,
            ping_latency=ping_latency,
            netconf_status=netconf_status,
            netconf_message=netconf_message,
            ssh_status=ssh_status,
            ssh_message=ssh_message,
            overall_status=overall_status
        )
        db.add(health_check)

        # Update device status
        device_db.status = device_status
        device_db.updated_at = datetime.utcnow()

        # Update backoff state based on check result
        if overall_status == "healthy":
            # Fully functional - reset failures
            BackoffManager.record_success(db, device_db)
        else:
            # Any failure (degraded or unreachable) should be recorded
            # This ensures devices with persistent NETCONF/SSH issues will back off
            BackoffManager.record_failure(db, device_db)

        db.commit()

        return {
            "device_id": device.id,
            "device_name": device.hostname,
            "timestamp": datetime.utcnow().isoformat(),
            "ping": {
                "status": ping_status,
                "latency_ms": ping_latency
            },
            "netconf": {
                "status": netconf_status,
                "message": netconf_message
            },
            "ssh": {
                "status": ssh_status,
                "message": ssh_message
            },
            "overall_status": overall_status,
            "backoff_status": BackoffManager.get_backoff_status(device_db)
        }

    async def check_all_devices_health(self, db: Session, devices: list[Device]) -> list[Dict[str, Any]]:
        """Check health for multiple devices concurrently with rate limiting"""
        # Limit concurrent health checks to avoid overwhelming the system
        semaphore = asyncio.Semaphore(10)
        
        async def check_with_semaphore(device: Device):
            async with semaphore:
                return await self.check_device_health(db, device)
        
        tasks = [check_with_semaphore(device) for device in devices]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_results = []
        for result in results:
            if isinstance(result, dict):
                successful_results.append(result)
            else:
                logger.error(f"Health check failed: {result}")

        return successful_results

    async def _ping_device(self, host: str) -> tuple[bool, Optional[float]]:
        """Ping a device and return status and latency"""
        if not host:
            return False, None

        def ping_sync():
            """Synchronous ping operation"""
            try:
                # Run ping command (1 packet, 2 second timeout)
                result = subprocess.run(
                    ["ping", "-c", "1", "-W", "2", host],
                    capture_output=True,
                    text=True,
                    timeout=3
                )

                if result.returncode == 0:
                    # Extract latency from ping output
                    output = result.stdout
                    if "time=" in output:
                        latency_str = output.split("time=")[1].split()[0]
                        latency = float(latency_str)
                        return True, latency
                    return True, None
                return False, None

            except (subprocess.TimeoutExpired, Exception) as e:
                logger.debug(f"Ping failed for {host}: {e}")
                return False, None

        try:
            # Run ping in thread to avoid blocking
            return await asyncio.to_thread(ping_sync)
        except Exception as e:
            logger.debug(f"Async ping failed for {host}: {e}")
            return False, None

    async def _check_netconf(self, device: Device) -> tuple[bool, str]:
        """Check NETCONF connectivity"""
        if not device.ip:
            return False, "No IP address configured"

        try:
            # Use static method directly without instantiating connector
            success = await asyncio.wait_for(
                asyncio.to_thread(
                    NetconfConnector.test_connection,
                    device.ip,
                    device.port,
                    device.username or "admin",
                    device.password or "admin"
                ),
                timeout=10
            )

            if success:
                return True, "NETCONF connection successful"
            else:
                return False, "NETCONF connection failed"

        except asyncio.TimeoutError:
            return False, "NETCONF connection timeout"
        except Exception as e:
            return False, f"NETCONF error: {str(e)[:100]}"

    async def _check_ssh(self, device: Device) -> tuple[bool, str]:
        """Check SSH port 22 connectivity"""
        if not device.ip:
            return False, "No IP address configured"

        try:
            import socket

            def check_ssh_port():
                """Check if SSH port 22 is open"""
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                try:
                    result = sock.connect_ex((device.ip, 22))
                    sock.close()
                    return result == 0
                except Exception:
                    return False

            # Run socket check in thread to avoid blocking
            success = await asyncio.wait_for(
                asyncio.to_thread(check_ssh_port),
                timeout=6
            )

            if success:
                return True, "SSH port 22 is open"
            else:
                return False, "SSH port 22 is closed or unreachable"

        except asyncio.TimeoutError:
            return False, "SSH port check timeout"
        except Exception as e:
            return False, f"SSH check error: {str(e)[:100]}"

    def get_device_health_history(self, db: Session, device_id: int, limit: int = 10) -> list[Dict[str, Any]]:
        """Get health check history for a device"""
        checks = db.query(HealthCheckDB)\
            .filter(HealthCheckDB.device_id == device_id)\
            .order_by(HealthCheckDB.timestamp.desc())\
            .limit(limit)\
            .all()

        return [
            {
                "timestamp": check.timestamp.isoformat(),
                "ping_status": check.ping_status,
                "ping_latency": check.ping_latency,
                "netconf_status": check.netconf_status,
                "netconf_message": check.netconf_message,
                "ssh_status": check.ssh_status,
                "ssh_message": check.ssh_message,
                "overall_status": check.overall_status
            }
            for check in checks
        ]

    def get_health_summary(self, db: Session) -> Dict[str, Any]:
        """Get overall health summary for all devices"""
        # Get latest health check per device
        from sqlalchemy import func

        latest_checks_subquery = db.query(
            HealthCheckDB.device_id,
            func.max(HealthCheckDB.timestamp).label('max_timestamp')
        ).group_by(HealthCheckDB.device_id).subquery()

        latest_checks = db.query(HealthCheckDB).join(
            latest_checks_subquery,
            (HealthCheckDB.device_id == latest_checks_subquery.c.device_id) &
            (HealthCheckDB.timestamp == latest_checks_subquery.c.max_timestamp)
        ).all()

        total_devices = db.query(DeviceDB).count()
        healthy = sum(1 for c in latest_checks if c.overall_status == "healthy")
        degraded = sum(1 for c in latest_checks if c.overall_status == "degraded")
        unreachable = sum(1 for c in latest_checks if c.overall_status == "unreachable")
        unhealthy = sum(1 for c in latest_checks if c.overall_status == "unhealthy")

        return {
            "total_devices": total_devices,
            "monitored_devices": len(latest_checks),
            "healthy": healthy,
            "degraded": degraded,
            "unreachable": unreachable,
            "unhealthy": unhealthy,
            "health_percentage": int((healthy / total_devices * 100)) if total_devices > 0 else 0
        }
