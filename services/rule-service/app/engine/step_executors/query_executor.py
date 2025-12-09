# ============================================================================
# engine/step_executors/query_executor.py
# Query Step Executor - Execute commands on devices
# ============================================================================

from typing import Dict, Any
from sqlalchemy.orm import Session

from engine.protocol_parsers import get_parser
from connectors import DeviceConnector
from shared.logger import setup_logger

logger = setup_logger(__name__)


class QueryExecutor:
    """Execute query steps - run commands on devices and parse output"""

    def __init__(self, db: Session):
        self.db = db

    async def execute(self, step, context) -> Dict[str, Any]:
        """
        Execute a query step

        Args:
            step: WorkflowStep with type='query'
            context: WorkflowContext

        Returns:
            Parsed command output
        """
        device = context.device

        # Handle vendor-specific commands
        if step.vendor_specific:
            vendor_config = step.vendor_specific.get(device.vendor.lower())
            if not vendor_config:
                raise ValueError(f"No vendor-specific config for vendor '{device.vendor}'")

            command = vendor_config.get('command')
            method = vendor_config.get('method', 'netconf')
            xpath = vendor_config.get('xpath')
            xml_filter = vendor_config.get('filter')
        else:
            # Render command template
            command = context.render_template_string(step.command)
            method = 'netconf'  # Default
            xpath = None
            xml_filter = None

        logger.info(f"Executing query on {device.hostname}: {command}")

        # Connect to device and execute command
        connector = DeviceConnector(device)
        try:
            if method == 'pysros' and device.vendor.lower() == 'nokia':
                # Use pySROS for Nokia
                output = await connector.execute_pysros_get(xpath)
            elif method == 'netconf':
                # Use NETCONF
                if xml_filter:
                    output = await connector.execute_netconf_get(xml_filter)
                else:
                    output = await connector.execute_command(command)
            else:
                # Standard CLI command
                output = await connector.execute_command(command)

            # Parse output if parser specified
            if step.parser:
                parser = get_parser(step.parser)
                parsed_data = parser.parse_summary(output) if hasattr(parser, 'parse_summary') else parser.parse_neighbors(output)
                return parsed_data
            else:
                # Return raw output
                return {'raw_output': output}

        finally:
            await connector.disconnect()
