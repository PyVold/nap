# ============================================================================
# connectors/netconf_connector.py
# ============================================================================

import asyncio
import os
from typing import Optional, Dict, Any
from ncclient import manager
from ncclient.operations import RPCError
from models.device import Device
from models.enums import VendorType
from connectors.base_connector import BaseConnector
from utils.logger import setup_logger
from utils.exceptions import DeviceConnectionError

logger = setup_logger(__name__)

# Security: Hostkey verification is configurable via environment variable
# Default to False for backward compatibility (lab/development environments)
# Set HOSTKEY_VERIFY=true in production with proper known_hosts configured
HOSTKEY_VERIFY = os.getenv("HOSTKEY_VERIFY", "false").lower() == "true"

class NetconfConnector(BaseConnector):
    """NETCONF connector implementation"""

    def __init__(self, device: Device):
        self.device = device
        self.connection = None

    async def connect(self) -> bool:
        """Establish NETCONF connection"""
        try:
            loop = asyncio.get_event_loop()
            device_params = self._get_device_params()

            self.connection = await loop.run_in_executor(
                None,
                lambda: manager.connect(
                    host=self.device.ip or self.device.hostname,
                    port=self.device.port,
                    username=self.device.username,
                    password=self.device.password,
                    device_params=device_params,
                    hostkey_verify=HOSTKEY_VERIFY,
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

            logger.info(f"Connected to {self.device.hostname}")
            return True

        except Exception as e:
            logger.error(f"Connection failed to {self.device.hostname}: {str(e)}")
            raise DeviceConnectionError(f"Failed to connect to {self.device.hostname}: {str(e)}")
    
    def _get_device_params(self) -> Dict[str, Any]:
        """Get vendor-specific device parameters"""
        if self.device.vendor == VendorType.CISCO_XR:
            return {'name': 'iosxr'}
        elif self.device.vendor == VendorType.NOKIA_SROS:
            # Use default handler - more generic and may avoid device-specific XPath formatting issues
            return {'name': 'default'}
        return {'name': 'default'}
    
    async def get_config(self, source: str = 'running', filter_data: Optional[str] = None, xpath: Optional[str] = None) -> str:
        """Retrieve device configuration"""
        if not self.connection:
            raise DeviceConnectionError("Not connected to device")

        try:
            loop = asyncio.get_event_loop()

            # Use XPath when provided (typically for Nokia SROS)
            if xpath:
                logger.debug(f"Getting config from {self.device.hostname} with XPath: {xpath}")
                # Nokia SROS: Use <get> operation with proper XML filter including namespaces
                # Nokia returns configuration data via <get> when using XPath
                if self.device.vendor == VendorType.NOKIA_SROS:
                    logger.info(f"Using <get> operation for Nokia SROS with XPath")
                    # Create proper XML filter with namespace declarations for Nokia
                    # Nokia SROS uses specific namespaces in their YANG models
                    xml_filter = f'''
                    <filter type="xpath"
                            xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
                            xmlns:sros="urn:nokia.com:sros:ns:yang:sr"
                            select="{xpath}" />
                    '''
                    result = await loop.run_in_executor(
                        None,
                        lambda: self.connection.get(filter=xml_filter)
                    )
                else:
                    result = await loop.run_in_executor(
                        None,
                        lambda: self.connection.get_config(source=source, filter=('xpath', xpath))
                    )
            elif filter_data:
                # Cisco XR and others use subtree filter
                logger.debug(f"Getting config from {self.device.hostname} with filter: {filter_data[:100]}...")
                result = await loop.run_in_executor(
                    None,
                    lambda: self.connection.get_config(source=source, filter=('subtree', filter_data))
                )
            else:
                # No filter specified
                logger.debug(f"Getting full config from {self.device.hostname}")
                result = await loop.run_in_executor(
                    None,
                    lambda: self.connection.get_config(source=source)
                )

            # Nokia SROS may return data in JSON format within XML envelope
            # Extract the actual data content
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
        """Retrieve operational state data"""
        if not self.connection:
            raise DeviceConnectionError("Not connected to device")

        # If no filter is specified, we can't retrieve operational state safely
        # (full operational state can be huge and cause XML parsing issues)
        if not xpath and not filter_data:
            logger.warning(f"No filter specified for get operation on {self.device.hostname}, skipping")
            raise ValueError("Filter or XPath must be specified for get operations")

        try:
            loop = asyncio.get_event_loop()

            if xpath:
                # Nokia SROS uses XPath
                result = await loop.run_in_executor(
                    None,
                    lambda: self.connection.get(filter=('xpath', xpath))
                )
            else:
                # Cisco uses subtree filter
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
        For Cisco: Returns full running configuration (equivalent to 'show running-config')

        Returns:
            Configuration as string
        """
        if not self.connection:
            raise DeviceConnectionError("Not connected to device")

        try:
            loop = asyncio.get_event_loop()
            logger.debug(f"Getting CLI config from {self.device.hostname}")

            # For Cisco and other NETCONF devices, get full running config
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
            config_xml: XML configuration to apply
            target: Target datastore ('candidate' or 'running')
            validate: Whether to validate before committing
            xpath: Not used for NETCONF (only for Nokia SROS pysros)
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
                logger.info(f"Disconnected from {self.device.hostname}")
            except Exception as e:
                logger.error(f"Error disconnecting from {self.device.hostname}: {str(e)}")

    @staticmethod
    def test_connection(host: str, port: int, username: str, password: str) -> bool:
        """Test NETCONF connectivity to a device"""
        try:
            connection = manager.connect(
                host=host,
                port=port,
                username=username,
                password=password,
                hostkey_verify=HOSTKEY_VERIFY,
                timeout=10,
                device_params={'name': 'default'}
            )
            connection.close_session()
            return True
        except Exception as e:
            logger.debug(f"NETCONF test connection failed to {host}: {str(e)}")
            return False
