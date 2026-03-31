# ============================================================================
# connectors/arista_connector.py
# NETCONF/eAPI connector for Arista EOS devices
# ============================================================================

import asyncio
from typing import Optional, Dict, Any
from ncclient import manager
from ncclient.operations import RPCError
from models.device import Device
from models.enums import VendorType
from .base_connector import BaseConnector
from shared.logger import setup_logger
from shared.exceptions import DeviceConnectionError

logger = setup_logger(__name__)

class AristaConnector(BaseConnector):
    """NETCONF connector for Arista EOS devices (OpenConfig YANG models)"""

    def __init__(self, device: Device):
        self.device = device
        self.connection = None

    async def connect(self) -> bool:
        """Establish NETCONF connection to Arista EOS device"""
        try:
            loop = asyncio.get_event_loop()

            self.connection = await loop.run_in_executor(
                None,
                lambda: manager.connect(
                    host=self.device.ip or self.device.hostname,
                    port=self.device.port,
                    username=self.device.username,
                    password=self.device.password,
                    device_params={'name': 'default'},
                    hostkey_verify=False,
                    timeout=30,
                    allow_agent=False,
                    look_for_keys=False
                )
            )

            # Configure the parser to be more lenient with XML
            if hasattr(self.connection, '_session') and hasattr(self.connection._session, '_parser'):
                try:
                    self.connection._session._parser.huge_tree = True
                except:
                    pass  # If we can't set it, continue anyway

            logger.info(f"Connected to Arista EOS device {self.device.hostname}")
            return True

        except Exception as e:
            logger.error(f"Connection failed to {self.device.hostname}: {str(e)}")
            raise DeviceConnectionError(f"Failed to connect to {self.device.hostname}: {str(e)}")

    async def get_config(self, source: str = 'running', filter_data: Optional[str] = None, xpath: Optional[str] = None) -> str:
        """
        Retrieve device configuration via NETCONF

        Arista EOS supports OpenConfig YANG models with paths like:
            /interfaces/interface
            /network-instances/network-instance/protocols/protocol

        Args:
            source: Configuration datastore ('running' or 'candidate')
            filter_data: XML subtree filter (OpenConfig XML)
            xpath: XPath filter for OpenConfig paths

        Returns:
            Configuration as XML string
        """
        if not self.connection:
            raise DeviceConnectionError("Not connected to device")

        try:
            loop = asyncio.get_event_loop()

            if xpath:
                # Arista supports XPath filters via NETCONF
                logger.debug(f"Getting config from {self.device.hostname} with XPath: {xpath}")
                result = await loop.run_in_executor(
                    None,
                    lambda: self.connection.get_config(source=source, filter=('xpath', xpath))
                )
            elif filter_data:
                # OpenConfig subtree filter
                logger.debug(f"Getting config from {self.device.hostname} with filter: {filter_data[:100]}...")
                result = await loop.run_in_executor(
                    None,
                    lambda: self.connection.get_config(source=source, filter=('subtree', filter_data))
                )
            else:
                # No filter - full config
                logger.debug(f"Getting full config from {self.device.hostname}")
                result = await loop.run_in_executor(
                    None,
                    lambda: self.connection.get_config(source=source)
                )

            return result.data_xml

        except RPCError as e:
            logger.error(f"NETCONF RPC Error on {self.device.hostname}: {str(e)}")
            if xpath:
                logger.error(f"XPath used: {xpath}")
            if filter_data:
                logger.error(f"Filter used: {filter_data[:200]}")
            raise
        except Exception as e:
            logger.error(f"Failed to get config from {self.device.hostname}: {str(e)}")
            raise

    async def get_operational_state(self, filter_data: Optional[str] = None, xpath: Optional[str] = None) -> str:
        """
        Retrieve operational state data via NETCONF RPC get

        Arista EOS uses OpenConfig paths for operational state, e.g.:
            /interfaces/interface/state
            /network-instances/network-instance/protocols/protocol/state

        Args:
            filter_data: XML subtree filter (OpenConfig XML)
            xpath: XPath filter

        Returns:
            Operational state as XML string
        """
        if not self.connection:
            raise DeviceConnectionError("Not connected to device")

        if not xpath and not filter_data:
            logger.warning(f"No filter specified for get operation on {self.device.hostname}, skipping")
            raise ValueError("Filter or XPath must be specified for get operations")

        try:
            loop = asyncio.get_event_loop()

            if xpath:
                # OpenConfig XPath filter for operational state
                logger.debug(f"Getting operational state from {self.device.hostname} with XPath: {xpath}")
                result = await loop.run_in_executor(
                    None,
                    lambda: self.connection.get(filter=('xpath', xpath))
                )
            else:
                # Subtree filter for operational state
                logger.debug(f"Getting operational state from {self.device.hostname} with subtree filter")
                result = await loop.run_in_executor(
                    None,
                    lambda: self.connection.get(filter=('subtree', filter_data))
                )

            return result.data_xml

        except Exception as e:
            logger.error(f"Failed to get operational state from {self.device.hostname}: {str(e)}")
            raise

    async def get_config_cli(self) -> str:
        """
        Retrieve device configuration in CLI format
        For Arista EOS: Returns full running configuration

        Returns:
            Configuration as string
        """
        if not self.connection:
            raise DeviceConnectionError("Not connected to device")

        try:
            loop = asyncio.get_event_loop()
            logger.debug(f"Getting CLI config from {self.device.hostname}")

            # For Arista EOS, get full running config via NETCONF
            result = await loop.run_in_executor(
                None,
                lambda: self.connection.get_config(source='running').data_xml
            )

            logger.info(f"Retrieved CLI config from {self.device.hostname}")
            return result

        except Exception as e:
            logger.error(f"Failed to get CLI config from {self.device.hostname}: {str(e)}")
            raise

    async def edit_config(self, config_xml: str, target: str = 'candidate', validate: bool = True, xpath: str = None, filter_xml: str = None) -> bool:
        """
        Edit device configuration using NETCONF edit-config

        Args:
            config_xml: XML configuration to apply (OpenConfig YANG format)
            target: Target datastore ('candidate' or 'running')
            validate: Whether to validate before committing
            xpath: Not used for NETCONF edit-config on Arista
            filter_xml: Not used for NETCONF edit-config

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.connection:
            raise DeviceConnectionError("Not connected to device")

        try:
            loop = asyncio.get_event_loop()

            # Edit the configuration
            logger.info(f"Applying configuration to {self.device.hostname}")
            await loop.run_in_executor(
                None,
                lambda: self.connection.edit_config(target=target, config=config_xml)
            )

            # Validate if using candidate datastore
            if target == 'candidate' and validate:
                logger.debug(f"Validating configuration on {self.device.hostname}")
                await loop.run_in_executor(
                    None,
                    self.connection.validate
                )

            # Commit if using candidate datastore
            if target == 'candidate':
                logger.info(f"Committing configuration on {self.device.hostname}")
                await loop.run_in_executor(
                    None,
                    self.connection.commit
                )

            logger.info(f"Configuration applied successfully to {self.device.hostname}")
            return True

        except RPCError as e:
            logger.error(f"NETCONF RPC Error applying config to {self.device.hostname}: {str(e)}")
            # Discard changes if commit failed
            if target == 'candidate':
                try:
                    await loop.run_in_executor(None, self.connection.discard_changes)
                except:
                    pass
            raise
        except Exception as e:
            logger.error(f"Failed to apply config to {self.device.hostname}: {str(e)}")
            raise

    async def disconnect(self):
        """Close NETCONF connection"""
        if self.connection:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.connection.close_session)
                logger.info(f"Disconnected from Arista EOS device {self.device.hostname}")
            except Exception as e:
                logger.error(f"Error disconnecting from {self.device.hostname}: {str(e)}")

    @staticmethod
    def test_connection(host: str, port: int, username: str, password: str) -> bool:
        """Test NETCONF connectivity to an Arista EOS device"""
        try:
            connection = manager.connect(
                host=host,
                port=port,
                username=username,
                password=password,
                hostkey_verify=False,
                timeout=10,
                device_params={'name': 'default'}
            )
            connection.close_session()
            return True
        except Exception as e:
            logger.debug(f"NETCONF test connection failed to {host}: {str(e)}")
            return False
