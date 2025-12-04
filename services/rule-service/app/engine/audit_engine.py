
# ============================================================================
# engine/audit_engine.py
# ============================================================================

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from models.device import Device
from models.rule import AuditRule
from models.audit import AuditResult, AuditFinding
from models.enums import AuditStatus, SeverityLevel, VendorType
from connectors.netconf_connector import NetconfConnector
from connectors.nokia_sros_connector import NokiaSROSConnector
from engine.rule_executor import RuleExecutor
from shared.logger import setup_logger

logger = setup_logger(__name__)

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

            # Note: Config backups are now handled by the scheduled backup service
            # configured via admin dashboard settings, not during audits

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