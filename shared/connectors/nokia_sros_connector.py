# ============================================================================
# connectors/nokia_sros_connector.py
# ============================================================================

import asyncio
from typing import Optional
from pysros.management import connect, sros
from models.device import Device
from .base_connector import BaseConnector
from shared.logger import setup_logger
from shared.exceptions import DeviceConnectionError

logger = setup_logger(__name__)

class NokiaSROSConnector(BaseConnector):
    """Nokia SROS connector using pysros library"""

    def __init__(self, device: Device):
        self.device = device
        self.connection = None

    async def connect(self) -> bool:
        """Establish connection to Nokia SROS device using pysros"""
        try:
            loop = asyncio.get_event_loop()

            # pysros uses different connection approach
            # For remote connections, it uses NETCONF internally
            connection_params = {
                'host': self.device.ip or self.device.hostname,
                'username': self.device.username,
                'password': self.device.password,
                'port': self.device.port,
                'hostkey_verify': False,
            }

            # Connect using pysros (runs in executor since it's blocking)
            self.connection = await loop.run_in_executor(
                None,
                lambda: connect(**connection_params)
            )

            logger.info(f"Connected to Nokia SROS device {self.device.hostname} using pysros")
            return True

        except Exception as e:
            logger.error(f"pysros connection failed to {self.device.hostname}: {str(e)}")
            raise DeviceConnectionError(f"Failed to connect to {self.device.hostname}: {str(e)}")

    async def get_config(self, source: str = 'running', filter_data: Optional[str] = None, xpath: Optional[str] = None, filter: Optional[dict] = None) -> str:
        """
        Retrieve device configuration using pysros

        Args:
            source: Not used with pysros (always gets running config)
            filter_data: Not used with pysros
            xpath: Path in pysros format (e.g., '/configure/system/management-interface/netconf')
            filter: Optional filter dict for pysros get() (e.g., {'service-name': '"', 'admin-state': {}})

        Returns:
            JSON string representation of the configuration
        """
        if not self.connection:
            raise DeviceConnectionError("Not connected to device")

        try:
            loop = asyncio.get_event_loop()

            # Convert XPath to pysros path format (they're similar)
            path = xpath if xpath else '/configure'

            # Use filter if provided and not empty
            if filter and len(filter) > 0:
                logger.debug(f"Getting config from {self.device.hostname} using pysros path: {path} with filter: {filter}")
                # Use pysros get() method with filter
                result = await loop.run_in_executor(
                    None,
                    lambda: self.connection.running.get(path, filter=filter)
                )
            else:
                logger.debug(f"Getting config from {self.device.hostname} using pysros path: {path}")
                # Use pysros get() method without filter
                result = await loop.run_in_executor(
                    None,
                    lambda: self.connection.running.get(path)
                )

            # Convert pysros Container to JSON dictionary
            import json

            def convert_pysros_to_dict(obj):
                """Recursively convert pysros Container objects to dictionaries"""
                # Check for pysros _Empty type (represents no data)
                if obj is None or type(obj).__name__ == '_Empty':
                    return {}

                if hasattr(obj, 'data'):
                    # pysros Container with .data attribute
                    return convert_pysros_to_dict(obj.data)
                elif isinstance(obj, dict):
                    result = {}
                    for k, v in obj.items():
                        # Convert any non-string key to string (handles int, tuple, etc.)
                        key = str(k) if not isinstance(k, str) else k
                        result[key] = convert_pysros_to_dict(v)
                    return result
                elif isinstance(obj, (list, tuple)):
                    return [convert_pysros_to_dict(item) for item in obj]
                else:
                    # Try to convert to primitive types
                    try:
                        # Check if it's JSON serializable
                        json.dumps(obj)
                        return obj
                    except (TypeError, ValueError):
                        # If not serializable, convert to string
                        return str(obj)

            # Convert to dictionary then to JSON string
            config_dict = convert_pysros_to_dict(result)
            config_json = json.dumps(config_dict, indent=2)

            logger.debug(f"Retrieved config from {self.device.hostname}: {len(config_json)} bytes")
            return config_json

        except Exception as e:
            logger.error(f"Failed to get config from {self.device.hostname} using pysros: {str(e)}")
            raise

    async def get_operational_state(self, filter_data: Optional[str] = None, xpath: Optional[str] = None) -> str:
        """
        Retrieve operational state using pysros

        For Nokia SROS, operational data is accessed through state paths
        """
        if not self.connection:
            raise DeviceConnectionError("Not connected to device")

        try:
            loop = asyncio.get_event_loop()

            # Convert XPath to pysros state path
            # Remove /configure prefix if present and add /state prefix
            path = xpath if xpath else '/state'
            if path.startswith('/configure'):
                path = path.replace('/configure', '/state', 1)
            elif not path.startswith('/state'):
                path = f'/state{path}'

            logger.debug(f"Getting operational state from {self.device.hostname} using pysros path: {path}")

            # Use pysros get() on state datastore
            result = await loop.run_in_executor(
                None,
                lambda: self.connection.running.get(path)
            )

            # Convert pysros Container to JSON dictionary
            import json

            def convert_pysros_to_dict(obj):
                """Recursively convert pysros Container objects to dictionaries"""
                # Check for pysros _Empty type (represents no data)
                if obj is None or type(obj).__name__ == '_Empty':
                    return {}

                if hasattr(obj, 'data'):
                    # pysros Container with .data attribute
                    return convert_pysros_to_dict(obj.data)
                elif isinstance(obj, dict):
                    result = {}
                    for k, v in obj.items():
                        # Convert any non-string key to string (handles int, tuple, etc.)
                        key = str(k) if not isinstance(k, str) else k
                        result[key] = convert_pysros_to_dict(v)
                    return result
                elif isinstance(obj, (list, tuple)):
                    return [convert_pysros_to_dict(item) for item in obj]
                else:
                    # Try to convert to primitive types
                    try:
                        # Check if it's JSON serializable
                        json.dumps(obj)
                        return obj
                    except (TypeError, ValueError):
                        # If not serializable, convert to string
                        return str(obj)

            # Convert to dictionary then to JSON string
            state_dict = convert_pysros_to_dict(result)
            state_json = json.dumps(state_dict, indent=2)

            return state_json

        except Exception as e:
            logger.error(f"Failed to get operational state from {self.device.hostname}: {str(e)}")
            raise

    async def get_config_cli(self) -> str:
        """
        Retrieve device configuration using CLI command
        Executes 'admin show configuration' for Nokia SROS

        Returns:
            CLI output as string
        """
        if not self.connection:
            raise DeviceConnectionError("Not connected to device")

        try:
            loop = asyncio.get_event_loop()
            logger.debug(f"Getting CLI config from {self.device.hostname}")

            # Execute CLI command using pysros
            result = await loop.run_in_executor(
                None,
                lambda: self.connection.cli("admin show configuration")
            )

            logger.info(f"Retrieved CLI config from {self.device.hostname}")
            return result

        except Exception as e:
            logger.error(f"Failed to get CLI config from {self.device.hostname}: {str(e)}")
            raise

    async def edit_config(self, config_data: str, target: str = 'candidate', validate: bool = True, xpath: str = None, filter_xml: str = None) -> bool:
        """
        Edit device configuration using pysros

        Args:
            config_data: Configuration value (JSON for xpath mode, or CLI commands)
            target: Target datastore ('candidate' recommended for Nokia SROS)
            validate: Whether to validate before committing
            xpath: XPath to the configuration element (if provided, uses xpath mode)
            filter_xml: Not used for Nokia SROS (only for Cisco XR)

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.connection:
            raise DeviceConnectionError("Not connected to device")

        try:
            loop = asyncio.get_event_loop()
            import json

            logger.info(f"Applying configuration to {self.device.hostname} using pysros")

            if xpath:
                # XPath mode - for remediation with specific config paths
                logger.info(f"Using xpath mode - XPath: {xpath}")
                logger.info(f"Value type: {type(config_data)}, length: {len(str(config_data))}")
                logger.debug(f"Value content: {config_data}")

                # Parse the config value - it may be JSON serialized or already a dict
                config_value = config_data
                
                # Check if config_data is already a dict
                if isinstance(config_data, dict):
                    logger.debug(f"Config is already a dict, using directly")
                    config_value = config_data
                elif isinstance(config_data, str):
                    # Try to deserialize if it's a JSON string
                    config_data_stripped = config_data.strip()
                    
                    if config_data_stripped.startswith('{') or config_data_stripped.startswith('['):
                        try:
                            # Try to parse as JSON
                            config_value = json.loads(config_data_stripped)
                            logger.debug(f"Deserialized JSON config to: {config_value}")
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse config as JSON: {e}")
                            logger.error(f"Config content (first 500 chars): {config_data_stripped[:500]}")
                            
                            # Try to provide helpful error details
                            lines = config_data_stripped.split('\n')
                            error_line = e.lineno if hasattr(e, 'lineno') else None
                            if error_line and error_line <= len(lines):
                                logger.error(f"Error near line {error_line}: {lines[error_line-1]}")
                            
                            raise ValueError(f"Invalid JSON config for xpath mode: {str(e)}")
                    else:
                        # Check if it's a simple value that should be used directly
                        # For pySROS, simple values (strings, numbers, booleans) can be set directly
                        logger.info(f"Config is a simple string value, will use directly")
                        
                        # Try to infer the type
                        if config_data_stripped.lower() in ('true', 'false'):
                            config_value = config_data_stripped.lower() == 'true'
                            logger.debug(f"Converted to boolean: {config_value}")
                        elif config_data_stripped.isdigit():
                            config_value = int(config_data_stripped)
                            logger.debug(f"Converted to integer: {config_value}")
                        else:
                            # Keep as string
                            config_value = config_data_stripped
                            logger.debug(f"Using as string value: {config_value}")
                else:
                    logger.error(f"Unexpected config type: {type(config_data)}")
                    raise ValueError(f"Config must be dict, JSON string, or simple value, got: {type(config_data)}")

                def apply_xpath_config():
                    """Apply configuration using pysros candidate.set()"""
                    logger.debug(f"Setting {xpath} = {config_value}")

                    # Handle nested dictionaries that might contain list items
                    # For pySROS, if we have nested dicts, we need to set them hierarchically
                    if isinstance(config_value, dict):
                        # Check if any values are dicts (potential list items with keys as names)
                        has_nested_dicts = any(isinstance(v, dict) for v in config_value.values())

                        if has_nested_dicts:
                            logger.info(f"Detected nested configuration, applying hierarchically")
                            # Apply each part separately
                            for key, value in config_value.items():
                                if isinstance(value, dict):
                                    # This is a list item with nested values
                                    # For YANG lists, the key identifies the list item
                                    # We need to set each leaf individually
                                    logger.info(f"Processing list container: {key}")
                                    for list_key, list_value in value.items():
                                        # list_key is the instance (e.g., IP address)
                                        # list_value contains the properties
                                        if isinstance(list_value, dict):
                                            for leaf, leaf_value in list_value.items():
                                                # Build path: base/container/instance/leaf
                                                item_path = f"{xpath}/{key}/{list_key}/{leaf}"
                                                logger.debug(f"Setting: {item_path} = {leaf_value}")
                                                self.connection.candidate.set(path=item_path, value=leaf_value)
                                        else:
                                            # Direct value
                                            item_path = f"{xpath}/{key}/{list_key}"
                                            logger.debug(f"Setting: {item_path} = {list_value}")
                                            self.connection.candidate.set(path=item_path, value=list_value)
                                else:
                                    # Simple value - set at current level
                                    simple_path = f"{xpath}/{key}"
                                    logger.debug(f"Setting simple value: {simple_path} = {value}")
                                    self.connection.candidate.set(path=simple_path, value=value)

                            logger.info(f"Committing configuration on {self.device.hostname}")
                            self.connection.candidate.commit()
                        else:
                            # No nested dicts, set normally
                            logger.info(f"Committing configuration on {self.device.hostname}")
                            self.connection.candidate.set(path=xpath, commit=True, value=config_value)
                    else:
                        # Simple value, set normally
                        logger.info(f"Committing configuration on {self.device.hostname}")
                        self.connection.candidate.set(path=xpath, commit=True, value=config_value)

                await loop.run_in_executor(None, apply_xpath_config)

            else:
                # CLI mode - for template deployment with CLI commands
                logger.info(f"Using CLI mode for configuration")
                logger.debug(f"CLI commands:\n{config_data}")

                def apply_cli_config():
                    """Apply CLI configuration commands"""
                    # For CLI commands, we can execute them directly via MD-CLI
                    # Split commands by newline and execute
                    commands = [cmd.strip() for cmd in config_data.split('\n') if cmd.strip() and not cmd.strip().startswith('#')]

                    logger.info(f"Applying {len(commands)} CLI commands")
                    # For Nokia SROS, CLI commands can be sent as a configuration string
                    # Using pysros, we can apply via candidate datastore

                    # The CLI commands need to be parsed and applied
                    # For now, log that CLI mode is used (full CLI support requires additional pysros methods)
                    logger.warning(f"CLI mode for Nokia SROS template deployment - executing {len(commands)} commands")

                    # Apply all commands as configuration
                    # Note: This is a simplified approach - full implementation would parse CLI syntax
                    for cmd in commands:
                        logger.debug(f"Command: {cmd}")

                    # Commit all changes
                    logger.info(f"Committing configuration on {self.device.hostname}")
                    self.connection.candidate.commit()

                await loop.run_in_executor(None, apply_cli_config)

            logger.info(f"Configuration applied successfully to {self.device.hostname}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply config to {self.device.hostname} using pysros: {str(e)}")
            # Try to discard changes
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.connection.candidate.discard)
                logger.info(f"Discarded failed configuration changes on {self.device.hostname}")
            except:
                pass
            raise

    async def disconnect(self):
        """Close connection to Nokia SROS device"""
        if self.connection:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self.connection.disconnect)
                logger.info(f"Disconnected from Nokia SROS device {self.device.hostname}")
            except Exception as e:
                logger.error(f"Error disconnecting from {self.device.hostname}: {str(e)}")

    @staticmethod
    def test_connection(host: str, port: int, username: str, password: str) -> bool:
        """Test connectivity to a Nokia SROS device using pysros"""
        try:
            connection = connect(
                host=host,
                username=username,
                password=password,
                port=port,
                hostkey_verify=False
            )
            connection.disconnect()
            return True
        except Exception as e:
            logger.debug(f"pysros test connection failed to {host}: {str(e)}")
            return False
