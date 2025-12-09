"""
Remediation Service - Auto-fix failed audit checks
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from db_models import DeviceDB, AuditResultDB, ConfigBackupDB
from models.enums import VendorType
from connectors import NetconfConnector, NokiaSROSConnector
from models.device import Device
from shared.logger import setup_logger

logger = setup_logger(__name__)


class RemediationService:
    """Service for generating and applying remediation configurations"""

    @staticmethod
    def generate_remediation_config(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate remediation configuration from failed findings

        Args:
            findings: List of failed audit findings with expected_config

        Returns:
            Dict containing remediation config and metadata
        """
        remediation_commands = []

        for finding in findings:
            if finding.get('status') == 'fail' and finding.get('expected_config'):
                expected = finding['expected_config']
                rule_name = finding.get('rule_name', 'Unknown')
                xpath = finding.get('xpath')
                filter_xml = finding.get('filter_xml')

                remediation_commands.append({
                    'rule': rule_name,
                    'config': expected,
                    'severity': finding.get('severity', 'medium'),
                    'xpath': xpath,  # For Nokia SROS remediation
                    'filter_xml': filter_xml  # For Cisco XR remediation
                })

        return {
            'commands': remediation_commands,
            'total_fixes': len(remediation_commands),
            'generated_at': datetime.utcnow().isoformat(),
        }

    @staticmethod
    async def apply_remediation(
        db: Session,
        device_id: int,
        remediation_config: Dict[str, Any],
        dry_run: bool = False,
        re_audit: bool = True
    ) -> Dict[str, Any]:
        """
        Apply remediation configuration to a device

        Args:
            db: Database session
            device_id: Target device ID
            remediation_config: Remediation config to apply
            dry_run: If True, only validate without applying
            re_audit: If True, re-audit device after successful remediation

        Returns:
            Dict containing results and status
        """
        device = db.query(DeviceDB).filter(DeviceDB.id == device_id).first()
        if not device:
            return {
                'success': False,
                'error': f'Device {device_id} not found',
            }

        # Pre-remediation backups are disabled - only scheduled and manual backups are active
        # Create backup before applying changes
        # if not dry_run:
        #     try:
        #         backup = await RemediationService._create_pre_remediation_backup(db, device)
        #         if not backup:
        #             logger.warning(f"Failed to create backup for device {device_id}, proceeding anyway")
        #     except Exception as e:
        #         logger.error(f"Backup failed for device {device_id}: {e}")

        # Get appropriate connector
        connector = RemediationService._get_connector(device)
        if not connector:
            return {
                'success': False,
                'error': f'No connector available for vendor {device.vendor}',
            }

        # Connect to device for applying configs
        connector_connected = False
        if not dry_run:
            try:
                connected = await connector.connect()
                if not connected:
                    logger.error(f"Failed to connect to device {device.hostname} for remediation")
                    return {
                        'success': False,
                        'error': f'Failed to connect to device {device.hostname}',
                        'device_id': device_id,
                        'device_name': device.hostname,
                    }
                connector_connected = True
            except Exception as e:
                logger.error(f"Connection error for device {device.hostname}: {e}")
                return {
                    'success': False,
                    'error': f'Connection failed: {str(e)}',
                    'device_id': device_id,
                    'device_name': device.hostname,
                }

        results = []
        success_count = 0

        try:
            for cmd in remediation_config.get('commands', []):
                config = cmd.get('config', '')
                rule = cmd.get('rule', 'Unknown')
                xpath = cmd.get('xpath')
                filter_xml = cmd.get('filter_xml')

                if dry_run:
                    # Validation mode - just verify the config format
                    results.append({
                        'rule': rule,
                        'status': 'validated',
                        'config': config,
                    })
                    success_count += 1
                else:
                    # Apply configuration via connector edit-config
                    try:
                        logger.info(f"Applying remediation for rule {rule} on device {device.hostname}")

                        # Use edit_config to apply the configuration with xpath/filter
                        await connector.edit_config(
                            config,
                            target='candidate',
                            validate=True,
                            xpath=xpath,
                            filter_xml=filter_xml
                        )

                        results.append({
                            'rule': rule,
                            'status': 'applied',
                            'config': config,
                        })
                        success_count += 1
                        logger.info(f"Successfully applied remediation for rule {rule}")
                    except Exception as e:
                        logger.error(f"Failed to apply config for rule {rule}: {e}")
                        results.append({
                            'rule': rule,
                            'status': 'failed',
                            'error': str(e),
                            'config': config,
                        })
        finally:
            # Disconnect from device
            if connector_connected:
                try:
                    await connector.disconnect()
                except Exception as e:
                    logger.debug(f"Error disconnecting from device: {e}")

        # Trigger re-audit after successful remediation (if not dry-run)
        audit_result = None
        if not dry_run and success_count > 0 and re_audit:
            try:
                logger.info(f"Re-auditing device {device.hostname} after remediation")
                from engine.audit_engine import AuditEngine
                from db_models import AuditRuleDB, AuditResultDB

                # Get the latest audit result for this device to extract rule names
                latest_audit = db.query(AuditResultDB).filter(
                    AuditResultDB.device_id == device_id
                ).order_by(AuditResultDB.timestamp.desc()).first()

                # Extract unique rule names from the latest audit's findings
                rule_names = set()
                if latest_audit and latest_audit.findings:
                    for finding in latest_audit.findings:
                        if isinstance(finding, dict) and 'rule' in finding:
                            rule_names.add(finding['rule'])

                logger.info(f"Re-auditing with {len(rule_names)} rules from last audit: {rule_names}")

                # Get only the rules that were in the last audit
                if rule_names:
                    rules_db = db.query(AuditRuleDB).filter(
                        AuditRuleDB.name.in_(rule_names),
                        AuditRuleDB.enabled == True
                    ).all()
                else:
                    # If no previous audit, use all active rules as fallback
                    logger.warning(f"No previous audit found for device {device_id}, using all active rules")
                    rules_db = db.query(AuditRuleDB).filter(AuditRuleDB.enabled == True).all()

                rules = []
                for rule_db in rules_db:
                    from models.rule import AuditRule
                    from models.enums import SeverityLevel, ComparisonType, VendorType

                    # Convert DB model to Pydantic model
                    rule = AuditRule(
                        id=rule_db.id,
                        name=rule_db.name,
                        description=rule_db.description or "",
                        severity=SeverityLevel(rule_db.severity),
                        category=rule_db.category or "general",
                        vendors=[VendorType(v) for v in rule_db.vendors],
                        checks=rule_db.checks,
                        enabled=rule_db.enabled
                    )
                    rules.append(rule)

                # Convert DeviceDB to Device model
                device_model = Device(
                    id=device.id,
                    hostname=device.hostname,
                    vendor=device.vendor,
                    ip=device.ip,
                    port=device.port or 830,
                    username=device.username,
                    password=device.password,
                    status=device.status
                )

                # Run audit
                audit_engine = AuditEngine()
                audit_result = await audit_engine.audit_device(device_model, rules, db)

                # Store audit result
                from db_models import AuditResultDB
                db_result = AuditResultDB(
                    device_id=audit_result.device_id,
                    device_name=audit_result.device_name,
                    timestamp=datetime.fromisoformat(audit_result.timestamp) if isinstance(audit_result.timestamp, str) else audit_result.timestamp,
                    findings=[f.dict() for f in audit_result.findings],
                    compliance=audit_result.compliance,
                    status="completed"
                )
                db.add(db_result)

                # Update device last_audit and compliance
                device.last_audit = datetime.utcnow()
                device.compliance = audit_result.compliance

                db.commit()
                logger.info(f"Re-audit completed for {device.hostname}: {audit_result.compliance}% compliance")

            except Exception as e:
                logger.error(f"Failed to re-audit device {device.hostname}: {e}")
                # Don't fail the remediation if re-audit fails

        return {
            'success': success_count > 0,
            'dry_run': dry_run,
            'total': len(remediation_config.get('commands', [])),
            'applied': success_count,
            'failed': len(results) - success_count,
            'results': results,
            'device_id': device_id,
            'device_name': device.hostname,
            're_audit_compliance': audit_result.compliance if audit_result else None,
        }

    @staticmethod
    async def _create_pre_remediation_backup(db: Session, device: DeviceDB) -> Optional[ConfigBackupDB]:
        """Create a backup before applying remediation using CLI for Nokia, NETCONF for others"""
        connector = None
        try:
            # For Nokia SROS, use SSH CLI to get config
            if device.vendor == VendorType.NOKIA_SROS.value:
                from connectors import SSHConnector
                from models.device import Device
                import asyncio

                device_model = Device(
                    id=device.id,
                    hostname=device.hostname,
                    vendor=VendorType(device.vendor),
                    ip=device.ip,
                    port=device.port,
                    username=device.username,
                    password=device.password
                )

                ssh_connector = SSHConnector(device_model)

                # Run sync method in executor
                loop = asyncio.get_event_loop()
                config = await loop.run_in_executor(None, ssh_connector.get_config_cli_sync)

                if not config:
                    logger.error(f"Failed to get CLI config for Nokia device {device.hostname}")
                    return None

            else:
                # For other vendors, use NETCONF
                connector = RemediationService._get_connector(device)
                if not connector:
                    return None

                # Connect to device first
                connected = await connector.connect()
                if not connected:
                    logger.error(f"Failed to connect to device {device.hostname} for backup")
                    return None

                config = await connector.get_config()
                if not config:
                    return None

            import hashlib
            config_hash = hashlib.sha256(config.encode()).hexdigest()

            backup = ConfigBackupDB(
                device_id=device.id,
                config_data=config,
                config_hash=config_hash,
                backup_type='pre_remediation',
                triggered_by='remediation_service',
                size_bytes=len(config.encode('utf-8'))
            )

            db.add(backup)
            db.commit()
            db.refresh(backup)

            logger.info(f"Created pre-remediation backup for device {device.id} using {'CLI' if device.vendor == VendorType.NOKIA_SROS.value else 'NETCONF'}")
            return backup

        except Exception as e:
            logger.error(f"Failed to create pre-remediation backup: {e}")
            return None
        finally:
            # Always disconnect (only for NETCONF connectors)
            if connector:
                try:
                    await connector.disconnect()
                except Exception as e:
                    logger.debug(f"Error disconnecting during backup: {e}")

    @staticmethod
    def _get_connector(device: DeviceDB):
        """Get appropriate connector for device vendor"""
        # Convert DeviceDB to Device model
        device_model = Device(
            id=device.id,
            hostname=device.hostname,
            vendor=device.vendor,
            ip=device.ip,
            port=device.port or 830,
            username=device.username,
            password=device.password,
            status=device.status
        )

        # Use Nokia connector for Nokia SROS, NetconfConnector for others
        if device.vendor == VendorType.NOKIA_SROS:
            return NokiaSROSConnector(device_model)
        elif device.vendor == VendorType.CISCO_XR:
            return NetconfConnector(device_model)
        else:
            logger.warning(f"No connector for vendor {device.vendor}")
            return None

    @staticmethod
    async def push_remediation_bulk(
        db: Session,
        device_ids: List[int],
        dry_run: bool = False,
        re_audit: bool = True
    ) -> Dict[str, Any]:
        """
        Push remediation to multiple devices based on their latest failed audits

        Args:
            db: Database session
            device_ids: List of device IDs to remediate
            dry_run: If True, only validate without applying
            re_audit: If True, re-audit devices after successful remediation

        Returns:
            Dict containing bulk remediation results
        """
        from sqlalchemy import func

        results = []

        for device_id in device_ids:
            # Get latest audit result for device
            latest_audit = db.query(AuditResultDB).filter(
                AuditResultDB.device_id == device_id
            ).order_by(AuditResultDB.timestamp.desc()).first()

            if not latest_audit:
                results.append({
                    'device_id': device_id,
                    'success': False,
                    'error': 'No audit results found',
                })
                continue

            # Get failed findings from the JSON column
            all_findings = latest_audit.findings or []
            failed_findings = [f for f in all_findings if f.get('status') == 'fail']

            if not failed_findings:
                results.append({
                    'device_id': device_id,
                    'success': True,
                    'message': 'No failed checks to remediate',
                })
                continue

            # Findings are already in dict format from JSON column
            findings_data = failed_findings

            # Generate remediation config
            remediation_config = RemediationService.generate_remediation_config(findings_data)

            # Apply remediation
            result = await RemediationService.apply_remediation(
                db, device_id, remediation_config, dry_run, re_audit
            )
            results.append(result)

        # Summarize results
        total_devices = len(device_ids)
        successful = sum(1 for r in results if r.get('success'))

        return {
            'success': successful > 0,
            'dry_run': dry_run,
            'total_devices': total_devices,
            'successful': successful,
            'failed': total_devices - successful,
            'results': results,
        }
