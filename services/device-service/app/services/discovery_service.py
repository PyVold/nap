# ============================================================================
# services/discovery_service.py
# ============================================================================

import asyncio
import ipaddress
import subprocess
import platform
from typing import List, Tuple
from concurrent.futures import ThreadPoolExecutor
from ncclient import manager
from lxml import etree
from models.device import Device
from models.enums import VendorType, DeviceStatus
from shared.logger import setup_logger

logger = setup_logger(__name__)

# Create a dedicated thread pool for blocking I/O operations
# This prevents the default thread pool from being exhausted during discovery
_discovery_executor = ThreadPoolExecutor(
    max_workers=30,  # Enough for concurrent pings + NETCONF
    thread_name_prefix="discovery_"
)

# Try to import pysros, but don't fail if it's not available
try:
    from pysros.management import connect as pysros_connect
    PYSROS_AVAILABLE = True
    logger.info("pysros library is available")
except ImportError:
    PYSROS_AVAILABLE = False
    logger.warning("pysros library not available, will use ncclient for all devices")

class DiscoveryService:
    """Service for discovering devices via subnet scanning (ping + NETCONF)"""

    @staticmethod
    def _ping_host(ip: str, timeout: int = 1) -> bool:
        """Ping a host to check if it's reachable"""
        try:
            # Use platform-specific ping command
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            command = ['ping', param, '1', '-W' if platform.system().lower() != 'windows' else '-w', str(timeout * 1000 if platform.system().lower() == 'windows' else timeout), str(ip)]

            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout + 1
            )
            return result.returncode == 0
        except Exception as e:
            logger.debug(f"Ping failed for {ip}: {str(e)}")
            return False

    @staticmethod
    def _get_device_info_via_netconf_sync(ip: str, port: int, username: str, password: str) -> Tuple[bool, str, VendorType]:
        """
        Connect via NETCONF and get device information (synchronous version)
        Returns: (success, hostname, vendor_type)
        """
        try:
            # Try to connect via NETCONF
            with manager.connect(
                host=ip,
                port=port,
                username=username,
                password=password,
                timeout=10,
                device_params={'name': 'default'},
                hostkey_verify=False,
                allow_agent=False,
                look_for_keys=False
            ) as m:
                # Get hostname from running config
                hostname = None
                vendor = VendorType.CISCO_XR  # default

                # Check capabilities to determine vendor
                capabilities = m.server_capabilities
                is_nokia = any('nokia' in cap.lower() or 'alu' in cap.lower() for cap in capabilities)
                is_cisco = any('cisco' in cap.lower() for cap in capabilities)

                logger.debug(f"Device {ip} capabilities suggest - Nokia: {is_nokia}, Cisco: {is_cisco}")

                # Try Nokia SROS first if capabilities suggest it
                if is_nokia or not is_cisco:
                    # Try pysros first if available
                    if PYSROS_AVAILABLE:
                        try:
                            logger.debug(f"Attempting pysros connection to {ip}")
                            connection_params = {
                                'host': ip,
                                'username': username,
                                'password': password,
                                'port': port,
                                'hostkey_verify': False,
                            }
                            pysros_conn = pysros_connect(**connection_params)

                            # Get hostname using pysros
                            hostname_data = pysros_conn.running.get('/configure/system/name')
                            if hostname_data:
                                hostname = str(hostname_data)
                                vendor = VendorType.NOKIA_SROS
                                pysros_conn.disconnect()
                                logger.info(f"Detected Nokia SROS device at {ip} using pysros: {hostname}")
                                return True, hostname, vendor

                            pysros_conn.disconnect()
                        except Exception as e:
                            logger.debug(f"pysros detection failed for {ip}: {str(e)}")

                    # Fallback to ncclient with XPath for Nokia
                    try:
                        # Nokia SROS: Use XPath with proper namespace declarations
                        xpath_filter = '''
                        <filter type="xpath"
                                xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
                                xmlns:state="urn:nokia.com:sros:ns:yang:sr:state"
                                select="/state:state/state:system/state:name" />
                        '''
                        result = m.get(filter=xpath_filter)
                        root = etree.fromstring(result.data_xml.encode())

                        # Try multiple possible namespace variations
                        namespaces = {
                            'state': 'urn:nokia.com:sros:ns:yang:sr:state',
                            'sros': 'urn:nokia.com:sros:ns:yang:sr',
                        }

                        # Try to find hostname in different possible locations
                        hostname_elem = root.find('.//state:name', namespaces)
                        if hostname_elem is None:
                            hostname_elem = root.find('.//{urn:nokia.com:sros:ns:yang:sr:state}name')
                        if hostname_elem is None:
                            hostname_elem = root.find('.//{urn:nokia.com:sros:ns:yang:sr}name')

                        if hostname_elem is not None and hostname_elem.text:
                            hostname = hostname_elem.text
                            vendor = VendorType.NOKIA_SROS
                            logger.info(f"Detected Nokia SROS device at {ip} using ncclient: {hostname}")
                            return True, hostname, vendor
                    except Exception as e:
                        logger.debug(f"Nokia ncclient detection failed for {ip}: {str(e)}")

                # Try Cisco IOS XR if Nokia failed or capabilities suggest Cisco
                try:
                    filter_cisco = """
                    <System xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-shellutil-oper">
                        <SystemInformation>
                            <Hostname/>
                        </SystemInformation>
                    </System>
                    """
                    result = m.get(filter=('subtree', filter_cisco))
                    root = etree.fromstring(result.data_xml.encode())
                    hostname_elem = root.find('.//{http://cisco.com/ns/yang/Cisco-IOS-XR-shellutil-oper}Hostname')
                    if hostname_elem is not None and hostname_elem.text:
                        hostname = hostname_elem.text
                        vendor = VendorType.CISCO_XR
                        logger.info(f"Detected Cisco XR device at {ip}: {hostname}")
                        return True, hostname, vendor
                except Exception as e:
                    logger.debug(f"Cisco detection failed for {ip}: {str(e)}")

                # If both failed, try to get hostname from get_config as fallback
                try:
                    result = m.get_config(source='running')
                    root = etree.fromstring(result.data_xml.encode())

                    # Try common hostname locations
                    # Cisco: //hostname
                    hostname_elem = root.find('.//hostname')
                    if hostname_elem is not None and hostname_elem.text:
                        hostname = hostname_elem.text
                        vendor = VendorType.CISCO_XR  # Assume Cisco if found this way
                        logger.info(f"Detected device at {ip} via fallback: {hostname}")
                        return True, hostname, vendor
                except Exception as e:
                    logger.debug(f"Fallback hostname detection failed for {ip}: {str(e)}")

                # Final fallback: use IP as hostname
                hostname = f"device-{ip.replace('.', '-')}"
                logger.warning(f"Could not determine vendor/hostname for {ip}, using default: {hostname}")

                # If we got here, we connected but couldn't get specific info
                # Use capabilities to make best guess on vendor
                if is_nokia:
                    vendor = VendorType.NOKIA_SROS
                elif is_cisco:
                    vendor = VendorType.CISCO_XR

                return True, hostname, vendor

        except Exception as e:
            logger.debug(f"NETCONF connection failed for {ip}: {str(e)}")
            return False, "", VendorType.CISCO_XR

    @staticmethod
    async def discover_subnet(subnet: str, username: str, password: str, port: int = 830, excluded_ips: List[str] = None) -> List[Device]:
        """
        Discover devices in a subnet by:
        1. Pinging all IPs in the subnet (excluding specified IPs)
        2. Trying NETCONF connection on responsive IPs
        3. Getting device info via NETCONF

        Args:
            subnet: CIDR notation (e.g., "192.168.1.0/24")
            username: NETCONF username
            password: NETCONF password
            port: NETCONF port (default 830)
            excluded_ips: List of IP addresses to exclude from discovery

        Returns:
            List of discovered Device objects
        """
        discovered_devices = []
        excluded_ips = excluded_ips or []

        try:
            # Parse subnet
            network = ipaddress.ip_network(subnet, strict=False)
            total_ips = network.num_addresses

            logger.info(f"Starting discovery on subnet {subnet} ({total_ips} addresses)")
            if excluded_ips:
                logger.info(f"Excluding IPs: {', '.join(excluded_ips)}")
            
            logger.info("Phase 1: Ping scan initiated...")

            # Step 1: Ping all IPs in subnet
            reachable_ips = []
            loop = asyncio.get_event_loop()

            # Limit concurrent pings to avoid overwhelming the system
            # Reduced from 50 to 25 to prevent thread pool exhaustion
            semaphore = asyncio.Semaphore(25)

            async def ping_with_semaphore(ip_str: str):
                async with semaphore:
                    is_reachable = await loop.run_in_executor(
                        _discovery_executor, DiscoveryService._ping_host, ip_str, 1
                    )
                    if is_reachable:
                        logger.info(f"Host {ip_str} is reachable")
                        return ip_str
                    return None

            # Skip network and broadcast addresses for /24 and smaller
            hosts = list(network.hosts()) if network.num_addresses > 2 else [network.network_address]

            # Filter out excluded IPs
            hosts = [ip for ip in hosts if str(ip) not in excluded_ips]

            # Ping all hosts
            ping_tasks = [ping_with_semaphore(str(ip)) for ip in hosts]
            ping_results = await asyncio.gather(*ping_tasks)
            reachable_ips = [ip for ip in ping_results if ip is not None]

            logger.info(f"Phase 1 complete: Found {len(reachable_ips)} reachable hosts out of {len(hosts)}")
            
            if len(reachable_ips) == 0:
                logger.info("No reachable hosts found. Discovery complete.")
                return []
            
            logger.info(f"Phase 2: Starting NETCONF connection attempts on {len(reachable_ips)} hosts...")

            # Step 2: Try NETCONF connection on reachable IPs
            # Use the dedicated thread pool executor to avoid blocking the event loop
            
            async def try_netconf(ip_str: str):
                # Run the blocking NETCONF operation in a thread pool
                success, hostname, vendor = await loop.run_in_executor(
                    _discovery_executor,
                    DiscoveryService._get_device_info_via_netconf_sync,
                    ip_str, port, username, password
                )
                if success:
                    return Device(
                        hostname=hostname,
                        vendor=vendor,
                        ip=ip_str,
                        port=port,
                        username=username,
                        password=password,
                        status=DeviceStatus.DISCOVERED,
                        compliance=0.0
                    )
                return None

            # Limit concurrent NETCONF connections to avoid overwhelming the system
            # Reduced from 10 to 5 to prevent thread pool exhaustion
            netconf_semaphore = asyncio.Semaphore(5)

            async def netconf_with_semaphore(ip_str: str):
                async with netconf_semaphore:
                    return await try_netconf(ip_str)

            netconf_tasks = [netconf_with_semaphore(ip) for ip in reachable_ips]
            netconf_results = await asyncio.gather(*netconf_tasks)
            discovered_devices = [dev for dev in netconf_results if dev is not None]

            logger.info(f"Phase 2 complete: Successfully discovered {len(discovered_devices)} devices via NETCONF")
            logger.info(f"Discovery scan finished for subnet {subnet}")

        except Exception as e:
            logger.error(f"Error during subnet discovery: {str(e)}")
            raise

        return discovered_devices
