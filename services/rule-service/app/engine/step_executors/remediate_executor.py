# ============================================================================
# engine/step_executors/remediate_executor.py
# Remediate Step Executor - Push configurations to devices
# ============================================================================

from typing import Dict, Any
from sqlalchemy.orm import Session

from connectors import DeviceConnector
from shared.logger import setup_logger

logger = setup_logger(__name__)


class RemediateExecutor:
    """Execute remediate steps - push configuration to devices"""

    def __init__(self, db: Session):
        self.db = db

    async def execute(self, step, context) -> Dict[str, Any]:
        """
        Execute a remediate step

        Args:
            step: WorkflowStep with type='remediate'
            context: WorkflowContext

        Returns:
            Remediation result
        """
        device = context.device

        # Get configuration to push
        config_var = context.render_template_string(step.config_source)
        config_data = context.get_step_output(config_var.strip('{}').strip())

        if isinstance(config_data, dict):
            config = config_data.get('rendered_config', str(config_data))
        else:
            config = str(config_data)

        logger.info(f"Remediating device {device.hostname}")

        # Get vendor-specific method
        if step.vendor_specific:
            vendor_config = step.vendor_specific.get(device.vendor.lower())
            if not vendor_config:
                raise ValueError(f"No vendor-specific remediation config for '{device.vendor}'")

            method = vendor_config.get('method', 'netconf')
        else:
            method = 'netconf'

        # Connect to device
        connector = DeviceConnector(device)
        try:
            if method == 'pysros' and device.vendor.lower() == 'nokia':
                # Use pySROS for Nokia
                xpath_ops = step.vendor_specific[device.vendor.lower()].get('xpath_operations', [])
                commit = step.vendor_specific[device.vendor.lower()].get('commit', True)
                commit_comment = step.vendor_specific[device.vendor.lower()].get('commit_comment', 'Workflow remediation')

                result = await connector.push_config_pysros(xpath_ops, commit, commit_comment)

            elif method == 'netconf':
                # Use NETCONF
                vendor_config = step.vendor_specific.get(device.vendor.lower(), {})
                edit_config = vendor_config.get('edit_config', {})
                target = edit_config.get('target', 'candidate')
                operation = edit_config.get('operation', 'merge')
                commit = vendor_config.get('commit', True)

                result = await connector.push_config_netconf(config, target, operation, commit)

            else:
                raise ValueError(f"Unsupported remediation method: {method}")

            logger.info(f"Remediation successful on {device.hostname}")
            return {
                'success': True,
                'method': method,
                'result': result
            }

        except Exception as e:
            logger.error(f"Remediation failed on {device.hostname}: {e}")

            # Rollback if enabled
            if step.rollback_on_error:
                logger.info(f"Attempting rollback on {device.hostname}")
                try:
                    await connector.rollback()
                    logger.info("Rollback successful")
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")

            raise ValueError(f"Remediation failed: {str(e)}")

        finally:
            await connector.disconnect()
