# ============================================================================
# connectors/device_connector.py
# Unified Device Connector - Wrapper for vendor-specific connectors
# ============================================================================

from typing import Optional, Dict, Any, List
from models.device import Device
from models.enums import VendorType
from connectors.nokia_sros_connector import NokiaSROSConnector
from connectors.netconf_connector import NetconfConnector
from utils.logger import setup_logger
from utils.exceptions import DeviceConnectionError

logger = setup_logger(__name__)


class DeviceConnector:
    """
    Unified device connector that automatically selects the appropriate
    vendor-specific connector based on device type.
    """

    def __init__(self, device: Device):
        self.device = device
        self.connector = None
        self._select_connector()

    def _select_connector(self):
        """Select appropriate connector based on device vendor"""
        if self.device.vendor == VendorType.NOKIA_SROS:
            # Try pySROS first for Nokia
            try:
                self.connector = NokiaSROSConnector(self.device)
                logger.debug(f"Selected NokiaSROSConnector for {self.device.hostname}")
            except ImportError:
                # Fall back to NETCONF if pysros not available
                logger.warning(f"pySROS not available, using NETCONF for {self.device.hostname}")
                self.connector = NetconfConnector(self.device)
        else:
            # Use NETCONF for all other vendors
            self.connector = NetconfConnector(self.device)
            logger.debug(f"Selected NetconfConnector for {self.device.hostname}")

    async def connect(self) -> bool:
        """Establish connection to device"""
        return await self.connector.connect()

    async def disconnect(self):
        """Close connection to device"""
        await self.connector.disconnect()

    async def execute_command(self, command: str, xpath: Optional[str] = None, filter_data: Optional[str] = None) -> str:
        """
        Execute a command or query on the device

        Args:
            command: Command type ('get-config' or 'get-state')
            xpath: XPath filter (for Nokia)
            filter_data: XML filter (for Cisco)

        Returns:
            Command output as string
        """
        if command == 'get-config':
            return await self.connector.get_config(xpath=xpath, filter_data=filter_data)
        elif command == 'get-state':
            return await self.connector.get_operational_state(xpath=xpath, filter_data=filter_data)
        else:
            raise ValueError(f"Unknown command type: {command}")

    async def push_config_pysros(
        self,
        xpath_operations: List[Dict[str, Any]],
        commit: bool = True,
        commit_comment: str = ""
    ) -> Dict[str, Any]:
        """
        Push configuration using pySROS (Nokia only)

        Args:
            xpath_operations: List of XPath operations
                [{'action': 'update', 'xpath': '/path', 'value': {...}}]
            commit: Whether to commit changes
            commit_comment: Commit comment

        Returns:
            Result dictionary
        """
        if not isinstance(self.connector, NokiaSROSConnector):
            raise ValueError("pySROS method only available for Nokia devices")

        try:
            for operation in xpath_operations:
                action = operation.get('action', 'update')
                xpath = operation.get('xpath')
                value = operation.get('value')

                logger.info(f"Applying {action} to {xpath}")

                # For pySROS, we use edit_config with xpath
                await self.connector.edit_config(
                    config_data=str(value),
                    xpath=xpath,
                    target='candidate'
                )

            return {
                'success': True,
                'message': f'Configuration applied via pySROS',
                'operations_count': len(xpath_operations)
            }

        except Exception as e:
            logger.error(f"pySROS config push failed: {e}")
            raise

    async def push_config_netconf(
        self,
        config_xml: str,
        target: str = 'candidate',
        operation: str = 'merge',
        commit: bool = True
    ) -> Dict[str, Any]:
        """
        Push configuration using NETCONF

        Args:
            config_xml: XML configuration to push
            target: Target datastore ('candidate' or 'running')
            operation: NETCONF operation ('merge', 'replace', 'create', 'delete')
            commit: Whether to commit changes

        Returns:
            Result dictionary
        """
        try:
            # Wrap config in proper NETCONF edit-config envelope
            config_envelope = f'''
            <config>
                {config_xml}
            </config>
            '''

            await self.connector.edit_config(
                config_xml=config_envelope,
                target=target,
                validate=True
            )

            return {
                'success': True,
                'message': f'Configuration applied via NETCONF',
                'target': target,
                'operation': operation
            }

        except Exception as e:
            logger.error(f"NETCONF config push failed: {e}")
            raise

    async def rollback(self):
        """
        Rollback configuration changes

        For NETCONF: discard_changes
        For pySROS: candidate.discard
        """
        try:
            if hasattr(self.connector, 'connection') and self.connector.connection:
                if isinstance(self.connector, NokiaSROSConnector):
                    # pySROS rollback
                    import asyncio
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        self.connector.connection.candidate.discard
                    )
                    logger.info(f"Rolled back configuration on {self.device.hostname}")
                else:
                    # NETCONF rollback
                    import asyncio
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(
                        None,
                        self.connector.connection.discard_changes
                    )
                    logger.info(f"Rolled back configuration on {self.device.hostname}")
        except Exception as e:
            logger.error(f"Rollback failed on {self.device.hostname}: {e}")
            raise
