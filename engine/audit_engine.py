
# ============================================================================
# engine/audit_engine.py
# ============================================================================

from typing import List, Optional
from datetime import datetime
import json
from sqlalchemy.orm import Session
from models.device import Device
from models.rule import AuditRule
from models.audit import AuditResult, AuditFinding
from models.enums import AuditStatus, SeverityLevel, VendorType
from connectors.netconf_connector import NetconfConnector
from connectors.nokia_sros_connector import NokiaSROSConnector
from engine.rule_executor import RuleExecutor
from services.config_backup_service import ConfigBackupService
from utils.logger import setup_logger

logger = setup_logger(__name__)


def should_backup_on_audit(db: Session) -> bool:
    """Check if backup should be created during audits based on admin settings"""
    try:
        from db_models import SystemConfigDB
        config = db.query(SystemConfigDB).filter(
            SystemConfigDB.key == "backup_config"
        ).first()
        if config:
            settings = json.loads(config.value)
            return settings.get('backupOnAudit', True)
    except Exception as e:
        logger.debug(f"Could not get backup config: {e}")
    return True  # Default to enabled

class AuditEngine:
    """Core audit engine that orchestrates device audits"""

    async def audit_device(
        self,
        device: Device,
        rules: Optional[List[AuditRule]] = None,
        db: Optional[Session] = None
    ) -> AuditResult:
        """Execute audit rules against a device"""

        findings = []

        # Use pysros for Nokia devices, ncclient for others
        if device.vendor == VendorType.NOKIA_SROS:
            logger.info(f"Using pysros connector for Nokia SROS device {device.hostname}")
            connector = NokiaSROSConnector(device)
        else:
            logger.info(f"Using NETCONF connector for {device.vendor.value} device {device.hostname}")
            connector = NetconfConnector(device)

        # Use provided rules or empty list
        rules_to_check = rules if rules else []

        try:
            # Connect to device
            connected = await connector.connect()
            if not connected:
                return AuditResult(
                    device_id=device.id,
                    device_name=device.hostname,
                    device_ip=device.ip,
                    timestamp=datetime.now().isoformat(),
                    findings=[AuditFinding(
                        rule="Connection",
                        status=AuditStatus.ERROR,
                        message="Failed to connect to device",
                        severity=SeverityLevel.CRITICAL
                    )],
                    compliance=0
                )

            # Create automatic configuration backup if db session is provided and enabled
            # Use CLI for Nokia, NETCONF for others
            if db and should_backup_on_audit(db):
                try:
                    logger.info(f"Creating automatic configuration backup for {device.hostname}")

                    # For Nokia, use CLI backup (SSH)
                    if device.vendor == VendorType.NOKIA_SROS:
                        from connectors.ssh_connector import SSHConnector
                        import asyncio

                        ssh_connector = SSHConnector(device)
                        loop = asyncio.get_event_loop()
                        config_data = await loop.run_in_executor(None, ssh_connector.get_config_cli_sync)
                    else:
                        # For other vendors, use NETCONF
                        config_data = await connector.get_config()

                    ConfigBackupService.create_backup_sync(
                        db=db,
                        device=device,
                        config_data=config_data,
                        backup_type="auto",
                        created_by="audit_engine"
                    )
                    logger.debug(f"Configuration backup created for {device.hostname} using {'CLI' if device.vendor == VendorType.NOKIA_SROS else 'NETCONF'}")
                except Exception as e:
                    logger.warning(f"Failed to create backup for {device.hostname}: {str(e)}")
                    # Don't fail the audit if backup fails
            elif db:
                logger.debug(f"Skipping audit backup for {device.hostname} - backupOnAudit is disabled in settings")
            
            # Execute applicable rules
            for rule in rules_to_check:
                if device.vendor not in rule.vendors:
                    continue
                
                try:
                    finding = await RuleExecutor.execute_rule(connector, device, rule)
                    findings.append(finding)
                    
                except Exception as e:
                    logger.error(f"Error executing rule '{rule.name}' on {device.hostname}: {str(e)}")
                    findings.append(AuditFinding(
                        rule=rule.name,
                        status=AuditStatus.ERROR,
                        message=f"Error executing audit: {str(e)}",
                        severity=rule.severity
                    ))
            
            # Calculate compliance score
            passed = len([f for f in findings if f.status == AuditStatus.PASS])
            total = len(findings)
            compliance = int((passed / total * 100)) if total > 0 else 0
            
            return AuditResult(
                device_id=device.id,
                device_name=device.hostname,
                device_ip=device.ip,
                timestamp=datetime.now().isoformat(),
                findings=findings,
                compliance=compliance
            )
            
        finally:
            await connector.disconnect()