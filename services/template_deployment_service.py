"""
Template Deployment Service - Deploy configuration templates to devices
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from jinja2 import Template, TemplateError

from db_models import DeviceDB, ConfigBackupDB, DeviceGroupDB
from models.config_templates import ConfigTemplate, TemplateDeployment
from models.device import Device
from models.enums import VendorType
from connectors.netconf_connector import NetconfConnector
from connectors.nokia_sros_connector import NokiaSROSConnector
from utils.logger import setup_logger

logger = setup_logger(__name__)


class TemplateDeploymentService:
    """Service for deploying configuration templates to devices"""

    @staticmethod
    def render_template(template_content: str, variables: Dict[str, Any]) -> str:
        """
        Render template with variable substitution using Jinja2

        Args:
            template_content: Template string with {{variable}} placeholders
            variables: Dict of variable name -> value

        Returns:
            Rendered configuration string
        """
        try:
            template = Template(template_content)
            rendered = template.render(**variables)
            return rendered
        except TemplateError as e:
            logger.error(f"Template rendering error: {e}")
            raise ValueError(f"Failed to render template: {str(e)}")

    @staticmethod
    def validate_variables(template: ConfigTemplate, provided_variables: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate that all required variables are provided

        Args:
            template: ConfigTemplate with variable definitions
            provided_variables: Dict of provided variable values

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not template.variables:
            return True, None

        required_vars = [var for var in template.variables if var.get('required', True)]

        for var in required_vars:
            var_name = var.get('name')
            if var_name not in provided_variables or provided_variables[var_name] is None:
                return False, f"Required variable '{var_name}' is missing"

        return True, None

    @staticmethod
    async def deploy_to_device(
        db: Session,
        template_id: int,
        device_id: int,
        variables: Dict[str, Any],
        dry_run: bool = False,
        deployed_by: str = "system"
    ) -> Dict[str, Any]:
        """
        Deploy a template to a single device

        Args:
            db: Database session
            template_id: Template to deploy
            device_id: Target device
            variables: Variable values for template
            dry_run: If True, only validate without applying
            deployed_by: User who initiated deployment

        Returns:
            Deployment result dict
        """
        # Get template
        template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
        if not template:
            return {
                'success': False,
                'device_id': device_id,
                'error': f'Template {template_id} not found'
            }

        # Get device
        device = db.query(DeviceDB).filter(DeviceDB.id == device_id).first()
        if not device:
            return {
                'success': False,
                'device_id': device_id,
                'error': f'Device {device_id} not found'
            }

        # Validate vendor match
        template_vendor = template.vendor.lower()
        device_vendor_str = device.vendor.value.lower() if hasattr(device.vendor, 'value') else str(device.vendor).lower()

        if 'cisco' in template_vendor and 'cisco' not in device_vendor_str:
            return {
                'success': False,
                'device_id': device_id,
                'error': f'Template vendor ({template.vendor}) does not match device vendor ({device.vendor})'
            }
        elif 'nokia' in template_vendor and 'nokia' not in device_vendor_str:
            return {
                'success': False,
                'device_id': device_id,
                'error': f'Template vendor ({template.vendor}) does not match device vendor ({device.vendor})'
            }

        # Validate variables
        is_valid, error_msg = TemplateDeploymentService.validate_variables(template, variables)
        if not is_valid:
            return {
                'success': False,
                'device_id': device_id,
                'error': error_msg
            }

        # Render template with variables
        try:
            generated_config = TemplateDeploymentService.render_template(
                template.template_content,
                variables
            )
        except ValueError as e:
            return {
                'success': False,
                'device_id': device_id,
                'error': str(e)
            }

        logger.info(f"Generated config for device {device.hostname}:\n{generated_config}")

        # Create deployment record
        deployment = TemplateDeployment(
            template_id=template_id,
            device_id=device_id,
            variables_used=variables,
            generated_config=generated_config,
            status='pending',
            deployed_by=deployed_by
        )
        db.add(deployment)
        db.commit()
        db.refresh(deployment)

        if dry_run:
            deployment.status = 'validated'
            db.commit()
            return {
                'success': True,
                'device_id': device_id,
                'device_name': device.hostname,
                'deployment_id': deployment.id,
                'status': 'validated',
                'generated_config': generated_config,
                'dry_run': True
            }

        # Get appropriate connector
        connector = TemplateDeploymentService._get_connector(device)
        if not connector:
            deployment.status = 'failed'
            deployment.error_message = f'No connector available for vendor {device.vendor}'
            db.commit()
            return {
                'success': False,
                'device_id': device_id,
                'error': deployment.error_message
            }

        # Create backup before deployment
        backup_id = None
        try:
            backup = await TemplateDeploymentService._create_backup(db, device, connector)
            if backup:
                backup_id = backup.id
                deployment.backup_id = backup_id
                db.commit()
        except Exception as e:
            logger.warning(f"Failed to create backup for device {device.hostname}: {e}")

        # Connect and deploy
        connector_connected = False
        try:
            connected = await connector.connect()
            if not connected:
                deployment.status = 'failed'
                deployment.error_message = f'Failed to connect to device {device.hostname}'
                db.commit()
                return {
                    'success': False,
                    'device_id': device_id,
                    'error': deployment.error_message
                }
            connector_connected = True

            # Apply configuration
            logger.info(f"Deploying template to {device.hostname}")

            # For Nokia SROS, need to handle differently
            if device.vendor == VendorType.NOKIA_SROS:
                # Nokia uses xpath + pysros
                if template.xpath:
                    # Use xpath mode with pysros candidate.set()
                    logger.info(f"Using xpath mode for Nokia SROS: {template.xpath}")
                    await connector.edit_config(
                        generated_config,
                        target='candidate',
                        validate=True,
                        xpath=template.xpath,
                        filter_xml=None
                    )
                else:
                    # Fallback to CLI mode if no xpath specified
                    logger.warning(f"No xpath specified for Nokia SROS template {template.name}, using CLI mode")
                    await connector.edit_config(
                        generated_config,
                        target='candidate',
                        validate=True,
                        xpath=None,
                        filter_xml=None
                    )
            else:
                # Cisco XR - wrap in NETCONF XML if needed
                if not generated_config.strip().startswith('<'):
                    # If not already XML, wrap in config tags
                    config_xml = f"<config>{generated_config}</config>"
                else:
                    config_xml = generated_config

                await connector.edit_config(
                    config_xml,
                    target='candidate',
                    validate=True
                )

            deployment.status = 'success'
            deployment.deployed_at = datetime.utcnow()
            db.commit()

            # Update template usage
            template.usage_count = (template.usage_count or 0) + 1
            template.last_used = datetime.utcnow()
            db.commit()

            logger.info(f"Successfully deployed template to {device.hostname}")

            return {
                'success': True,
                'device_id': device_id,
                'device_name': device.hostname,
                'deployment_id': deployment.id,
                'status': 'success',
                'backup_id': backup_id
            }

        except Exception as e:
            logger.error(f"Failed to deploy template to {device.hostname}: {e}")
            deployment.status = 'failed'
            deployment.error_message = str(e)
            db.commit()

            return {
                'success': False,
                'device_id': device_id,
                'device_name': device.hostname,
                'deployment_id': deployment.id,
                'error': str(e)
            }

        finally:
            if connector_connected:
                try:
                    await connector.disconnect()
                except Exception as e:
                    logger.debug(f"Error disconnecting: {e}")

    @staticmethod
    async def deploy_to_devices(
        db: Session,
        template_id: int,
        device_ids: List[int],
        variables: Dict[str, Any],
        dry_run: bool = False,
        deployed_by: str = "system"
    ) -> Dict[str, Any]:
        """
        Deploy a template to multiple devices

        Args:
            db: Database session
            template_id: Template to deploy
            device_ids: List of target device IDs
            variables: Variable values for template
            dry_run: If True, only validate without applying
            deployed_by: User who initiated deployment

        Returns:
            Bulk deployment result dict
        """
        results = []

        for device_id in device_ids:
            result = await TemplateDeploymentService.deploy_to_device(
                db=db,
                template_id=template_id,
                device_id=device_id,
                variables=variables,
                dry_run=dry_run,
                deployed_by=deployed_by
            )
            results.append(result)

        # Summarize results
        successful = sum(1 for r in results if r.get('success'))
        failed = len(results) - successful

        return {
            'success': successful > 0,
            'dry_run': dry_run,
            'total_devices': len(device_ids),
            'successful': successful,
            'failed': failed,
            'results': results
        }

    @staticmethod
    async def deploy_to_device_groups(
        db: Session,
        template_id: int,
        group_ids: List[int],
        variables: Dict[str, Any],
        dry_run: bool = False,
        deployed_by: str = "system"
    ) -> Dict[str, Any]:
        """
        Deploy a template to multiple device groups

        Args:
            db: Database session
            template_id: Template to deploy
            group_ids: List of device group IDs
            variables: Variable values for template
            dry_run: If True, only validate without applying
            deployed_by: User who initiated deployment

        Returns:
            Bulk deployment result dict
        """
        # Collect all device IDs from all groups
        all_device_ids = set()
        for group_id in group_ids:
            group = db.query(DeviceGroupDB).filter(DeviceGroupDB.id == group_id).first()
            if group and group.devices:
                # group.devices is a list of DeviceGroupMembershipDB objects
                # Each membership has a device_id attribute
                for membership in group.devices:
                    all_device_ids.add(membership.device_id)

        if not all_device_ids:
            return {
                'success': False,
                'dry_run': dry_run,
                'total_devices': 0,
                'successful': 0,
                'failed': 0,
                'results': [],
                'error': 'No devices found in the specified groups'
            }

        # Deploy to all collected devices
        return await TemplateDeploymentService.deploy_to_devices(
            db=db,
            template_id=template_id,
            device_ids=list(all_device_ids),
            variables=variables,
            dry_run=dry_run,
            deployed_by=deployed_by
        )

    @staticmethod
    async def _create_backup(
        db: Session,
        device: DeviceDB,
        connector
    ) -> Optional[ConfigBackupDB]:
        """Create a backup before template deployment"""
        try:
            config = await connector.get_config()
            if not config:
                return None

            import hashlib
            config_hash = hashlib.sha256(config.encode()).hexdigest()

            backup = ConfigBackupDB(
                device_id=device.id,
                config_data=config,
                config_hash=config_hash,
                backup_type='pre_template',
                triggered_by='template_deployment',
                size_bytes=len(config.encode('utf-8'))
            )

            db.add(backup)
            db.commit()
            db.refresh(backup)

            logger.info(f"Created pre-deployment backup for device {device.id}")
            return backup

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

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
