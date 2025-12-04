"""
Device Metadata Collector

Collects protocol and system metadata from network devices during discovery.
Uses XPath queries for Nokia SR OS and NETCONF for Cisco IOS-XR.
"""

import re
import json
from typing import Dict, Any, Optional
from shared.logger import setup_logger

logger = setup_logger(__name__)


class DeviceMetadataCollector:
    """Collect protocol metadata from network devices using XPath/NETCONF"""

    @staticmethod
    async def collect_nokia_sros_metadata(connection) -> Dict[str, Any]:
        """
        Collect metadata from Nokia SR OS device using XPath queries

        Collects:
        - BGP AS number and router ID
        - IGP type (ISIS/OSPF) and router ID
        - LDP status and neighbors
        - System interface IP
        - MPLS/SR status
        """
        metadata = {
            "bgp": {},
            "igp": {},
            "ldp": {},
            "mpls": {},
            "system": {}
        }

        try:
            # BGP Information
            try:
                # First get BGP config for router-id and AS number (not in state path)
                bgp_config_xpath = '/configure/router[router-name="Base"]/bgp'
                bgp_config_data = await connection.get_config(xpath=bgp_config_xpath)

                if bgp_config_data:
                    bgp_config_json = json.loads(bgp_config_data)

                    # Extract BGP router-id from config
                    if 'router-id' in bgp_config_json:
                        metadata["bgp"]["router_id"] = bgp_config_json['router-id']

                    # Extract AS number from config (in local-as.as-number)
                    if 'local-as' in bgp_config_json:
                        local_as = bgp_config_json['local-as']
                        if isinstance(local_as, dict) and 'as-number' in local_as:
                            metadata["bgp"]["as_number"] = int(local_as['as-number'])
                    elif 'autonomous-system' in bgp_config_json:
                        metadata["bgp"]["as_number"] = int(bgp_config_json['autonomous-system'])

                # Then get BGP state for neighbor counts
                bgp_state_xpath = '/state/router[router-name="Base"]/bgp'
                bgp_state_data = await connection.get_operational_state(xpath=bgp_state_xpath)

                if bgp_state_data:
                    bgp_json = json.loads(bgp_state_data)

                    # Count neighbors from state
                    if 'neighbor' in bgp_json and isinstance(bgp_json['neighbor'], dict):
                        neighbors = bgp_json['neighbor']
                        metadata["bgp"]["neighbor_count"] = len(neighbors)

                        # Count established sessions
                        established = 0
                        for neighbor_ip, neighbor_data in neighbors.items():
                            if isinstance(neighbor_data, dict):
                                stats = neighbor_data.get('statistics', {})
                                if stats.get('session-state') == 'Established':
                                    established += 1
                        metadata["bgp"]["established_sessions"] = established

                logger.info(f"Collected BGP metadata: router-id={metadata['bgp'].get('router_id')}, "
                           f"AS={metadata['bgp'].get('as_number')}, "
                           f"{metadata['bgp'].get('neighbor_count', 0)} neighbors, "
                           f"{metadata['bgp'].get('established_sessions', 0)} established")
            except Exception as e:
                logger.warning(f"Failed to collect BGP metadata: {e}")

            # IGP Information (ISIS)
            try:
                isis_xpath = '/state/router[router-name="Base"]/isis'
                isis_data = await connection.get_operational_state(xpath=isis_xpath)

                if isis_data:
                    isis_json = json.loads(isis_data)

                    # ISIS returns a dict with instance keys (integers converted to strings)
                    # Get the first instance (usually '0')
                    if isis_json and isinstance(isis_json, dict):
                        # Find the first instance
                        instance_key = next(iter(isis_json.keys())) if isis_json else None
                        if instance_key:
                            instance = isis_json[instance_key]

                            metadata["igp"]["type"] = "ISIS"

                            # Extract System ID
                            if 'oper-system-id' in instance:
                                metadata["igp"]["router_id"] = instance['oper-system-id']

                            # Extract router ID (optional, some use this instead)
                            if 'oper-router-id' in instance:
                                if not metadata["igp"].get("router_id"):
                                    metadata["igp"]["router_id"] = instance['oper-router-id']

                            # Determine level capability from level data
                            if 'level' in instance and isinstance(instance['level'], dict):
                                levels = instance['level']
                                if '1' in levels and '2' in levels:
                                    metadata["igp"]["isis_level"] = "L1/L2"
                                elif '2' in levels:
                                    metadata["igp"]["isis_level"] = "L2"
                                elif '1' in levels:
                                    metadata["igp"]["isis_level"] = "L1"

                            # Count adjacencies by looking at interfaces
                            adjacency_count = 0
                            if 'interface' in instance and isinstance(instance['interface'], dict):
                                for intf_name, intf_data in instance['interface'].items():
                                    if isinstance(intf_data, dict) and 'adjacency' in intf_data:
                                        if isinstance(intf_data['adjacency'], dict):
                                            adjacency_count += len(intf_data['adjacency'])
                            metadata["igp"]["adjacency_count"] = adjacency_count

                logger.info(f"Collected ISIS metadata: {metadata['igp'].get('isis_level')}, "
                           f"{metadata['igp'].get('adjacency_count', 0)} adjacencies")
            except Exception as e:
                logger.warning(f"Failed to collect ISIS metadata: {e}")

            # Try OSPF if ISIS not found
            if metadata["igp"].get("type") != "ISIS":
                try:
                    ospf_xpath = '/state/router[router-name="Base"]/ospf'
                    ospf_data = await connection.get_operational_state(xpath=ospf_xpath)

                    if ospf_data:
                        ospf_json = json.loads(ospf_data)

                        # Similar structure to ISIS
                        if ospf_json and isinstance(ospf_json, dict):
                            instance_key = next(iter(ospf_json.keys())) if ospf_json else None
                            if instance_key:
                                instance = ospf_json[instance_key]

                                metadata["igp"]["type"] = "OSPF"

                                if 'router-id' in instance:
                                    metadata["igp"]["router_id"] = instance['router-id']

                                # Count neighbors
                                neighbor_count = 0
                                if 'neighbor' in instance and isinstance(instance['neighbor'], dict):
                                    neighbor_count = len(instance['neighbor'])
                                metadata["igp"]["neighbor_count"] = neighbor_count

                    logger.info(f"Collected OSPF metadata: {metadata['igp'].get('neighbor_count', 0)} neighbors")
                except Exception as e:
                    logger.warning(f"Failed to collect OSPF metadata: {e}")

            # LDP Information
            try:
                ldp_xpath = '/state/router[router-name="Base"]/ldp'
                ldp_data = await connection.get_operational_state(xpath=ldp_xpath)

                if ldp_data:
                    ldp_json = json.loads(ldp_data)

                    if ldp_json and isinstance(ldp_json, dict):
                        # Check if LDP is configured
                        metadata["ldp"]["enabled"] = True if ldp_json else False

                        # Try to get router ID
                        if 'router-id' in ldp_json:
                            metadata["ldp"]["router_id"] = ldp_json['router-id']

                        # Count sessions
                        if 'session' in ldp_json and isinstance(ldp_json['session'], dict):
                            metadata["ldp"]["session_count"] = len(ldp_json['session'])
                    else:
                        metadata["ldp"]["enabled"] = False

                logger.info(f"Collected LDP metadata: enabled={metadata['ldp'].get('enabled')}, "
                           f"{metadata['ldp'].get('session_count', 0)} sessions")
            except Exception as e:
                logger.warning(f"Failed to collect LDP metadata: {e}")

            # System Information
            try:
                # Use BGP router-id as system router_id (Nokia uses this convention)
                if metadata["bgp"].get("router_id"):
                    metadata["system"]["router_id"] = metadata["bgp"]["router_id"]

                # Get system state for version info and other details
                try:
                    system_xpath = '/state/system/version'
                    system_data = await connection.get_operational_state(xpath=system_xpath)
                    logger.debug(f"Version query response: {system_data}")

                    if system_data:
                        system_json = json.loads(system_data) if isinstance(system_data, str) else system_data

                        # Extract software version - direct response from /state/system/version
                        if isinstance(system_json, dict):
                            if 'version-number' in system_json:
                                metadata["system"]["software_version"] = system_json.get('version-number', '')
                                metadata["system"]["software_version_full"] = system_json.get('version-string', '')
                                logger.info(f"Collected Nokia software version: {metadata['system']['software_version']}")
                            elif 'version' in system_json:
                                # Nested version structure
                                version_info = system_json['version']
                                if isinstance(version_info, dict):
                                    metadata["system"]["software_version"] = version_info.get('version-number', '')
                                    metadata["system"]["software_version_full"] = version_info.get('version-string', '')
                                else:
                                    metadata["system"]["software_version"] = str(version_info)
                                logger.info(f"Collected Nokia software version: {metadata['system'].get('software_version')}")

                except Exception as ver_e:
                    logger.warning(f"Could not get system version info: {ver_e}")

                # Get system name and platform from /state/system
                try:
                    system_info_xpath = '/state/system'
                    system_info_data = await connection.get_operational_state(xpath=system_info_xpath)

                    if system_info_data:
                        system_info_json = json.loads(system_info_data) if isinstance(system_info_data, str) else system_info_data

                        # Extract system name
                        if 'oper-name' in system_info_json:
                            metadata["system"]["system_name"] = system_info_json['oper-name']

                        # Extract platform
                        if 'platform' in system_info_json:
                            metadata["system"]["platform"] = system_info_json['platform']

                except Exception as sys_e:
                    logger.debug(f"Could not get system info: {sys_e}")

                # Try to get system address from system interface (loopback equivalent for Nokia)
                try:
                    system_addr_xpath = '/state/router[router-name="Base"]/interface[interface-name="system"]'
                    system_addr_data = await connection.get_operational_state(xpath=system_addr_xpath)

                    if system_addr_data:
                        system_addr_json = json.loads(system_addr_data)

                        # Extract primary IPv4 address from system interface
                        # Handle both with and without namespace prefix (nokia-conf:ipv4 or ipv4)
                        ipv4_data = None
                        if 'ipv4' in system_addr_json:
                            ipv4_data = system_addr_json['ipv4']
                        elif 'nokia-conf:ipv4' in system_addr_json:
                            ipv4_data = system_addr_json['nokia-conf:ipv4']
                        else:
                            # Try to find any key containing 'ipv4' (handles various namespace prefixes)
                            for key in system_addr_json.keys():
                                if 'ipv4' in key.lower():
                                    ipv4_data = system_addr_json[key]
                                    break

                        if ipv4_data and 'primary' in ipv4_data:
                            primary = ipv4_data['primary']
                            # State path uses 'oper-address', config path uses 'address'
                            addr = primary.get('oper-address') or primary.get('address')
                            if addr:
                                # Remove /32 suffix if present
                                if '/' in addr:
                                    addr = addr.split('/')[0]
                                metadata["system"]["system_address"] = addr
                                logger.info(f"Collected Nokia system interface IP: {addr}")
                except Exception as addr_e:
                    logger.debug(f"Could not get system address: {addr_e}")

                # If router_id not set from BGP, use system_address as fallback
                if not metadata["system"].get("router_id") and metadata["system"].get("system_address"):
                    metadata["system"]["router_id"] = metadata["system"]["system_address"]

                logger.info(f"Collected system metadata: router-id={metadata['system'].get('router_id')}, "
                           f"system-address={metadata['system'].get('system_address')}")
            except Exception as e:
                logger.warning(f"Failed to collect system interface info: {e}")

            # MPLS/SR Information
            try:
                mpls_xpath = '/state/router[router-name="Base"]/mpls'
                mpls_data = await connection.get_operational_state(xpath=mpls_xpath)

                if mpls_data:
                    mpls_json = json.loads(mpls_data)

                    if mpls_json and isinstance(mpls_json, dict):
                        metadata["mpls"]["enabled"] = True

                        # Check for Segment Routing
                        if 'segment-routing' in mpls_json:
                            metadata["mpls"]["segment_routing"] = True
                        else:
                            metadata["mpls"]["segment_routing"] = False
                    else:
                        metadata["mpls"]["enabled"] = False

                logger.info(f"Collected MPLS metadata: enabled={metadata['mpls'].get('enabled')}, "
                           f"SR={metadata['mpls'].get('segment_routing')}")
            except Exception as e:
                logger.warning(f"Failed to collect MPLS metadata: {e}")

        except Exception as e:
            logger.error(f"Error collecting Nokia SROS metadata: {e}")

        return metadata

    @staticmethod
    async def collect_cisco_xr_metadata(connection) -> Dict[str, Any]:
        """
        Collect metadata from Cisco IOS-XR device using NETCONF

        Collects:
        - BGP AS number and router ID
        - OSPF/ISIS router ID
        - LDP neighbors
        - Loopback0 IP
        """
        metadata = {
            "bgp": {},
            "igp": {},
            "ldp": {},
            "system": {}
        }

        try:
            # BGP Information
            try:
                bgp_filter = """
                <bgp xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ipv4-bgp-oper">
                    <instances>
                        <instance>
                            <instance-name>default</instance-name>
                            <instance-active>
                                <default-vrf>
                                    <global-process-info/>
                                </default-vrf>
                            </instance-active>
                        </instance>
                    </instances>
                </bgp>
                """

                bgp_data = await connection.get_config(filter_data=bgp_filter)

                # Parse BGP data
                if bgp_data:
                    # Try to extract from different possible structures
                    if isinstance(bgp_data, dict):
                        # Extract AS number
                        if 'as' in bgp_data:
                            metadata["bgp"]["as_number"] = int(bgp_data['as'])
                        elif 'local-as' in bgp_data:
                            metadata["bgp"]["as_number"] = int(bgp_data['local-as'])

                        # Extract router-id
                        if 'router-id' in bgp_data:
                            metadata["bgp"]["router_id"] = bgp_data['router-id']
                    else:
                        # Try regex parsing for XML/string response
                        import re
                        as_match = re.search(r'<(?:local-)?as>(\d+)</(?:local-)?as>', str(bgp_data))
                        if as_match:
                            metadata["bgp"]["as_number"] = int(as_match.group(1))

                        rid_match = re.search(r'<router-id>([\d.]+)</router-id>', str(bgp_data))
                        if rid_match:
                            metadata["bgp"]["router_id"] = rid_match.group(1)

                logger.info(f"Collected Cisco BGP metadata: AS={metadata['bgp'].get('as_number')}, "
                           f"router-id={metadata['bgp'].get('router_id')}")
            except Exception as e:
                logger.warning(f"Failed to collect BGP metadata: {e}")

            # Software Version Information
            try:
                # Try to get software version using Cisco install manager model
                version_filter = """
                <install xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-installmgr-admin-oper">
                    <software>
                        <alias-devices>
                            <alias-device>
                                <device-name>0/RP0/CPU0</device-name>
                                <aliases>
                                    <alias>
                                        <package-name>active</package-name>
                                    </alias>
                                </aliases>
                            </alias-device>
                        </alias-devices>
                    </software>
                </install>
                """
                try:
                    version_data = await connection.get_operational_state(filter_data=version_filter)
                    if version_data:
                        # Extract version from the active package info
                        version_match = re.search(r'<package-name>([^<]+)</package-name>', version_data)
                        if version_match:
                            package_name = version_match.group(1)
                            # Parse version from package name (e.g., "disk0:asr9k-os-mbi-7.3.2")
                            ver_match = re.search(r'(\d+\.\d+\.\d+)', package_name)
                            if ver_match:
                                metadata["system"]["software_version"] = ver_match.group(1)
                except Exception as e1:
                    logger.debug(f"Install manager version query failed: {e1}")

                # Alternate approach: Try spirit-install-instmgr-oper model
                if not metadata["system"].get("software_version"):
                    try:
                        spirit_filter = """
                        <software-install xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-spirit-install-instmgr-oper">
                            <version/>
                        </software-install>
                        """
                        version_data = await connection.get_operational_state(filter_data=spirit_filter)
                        if version_data:
                            # Extract version string
                            version_match = re.search(r'<version>([^<]+)</version>', version_data)
                            if version_match:
                                metadata["system"]["software_version"] = version_match.group(1)
                    except Exception as e2:
                        logger.debug(f"Spirit install version query failed: {e2}")

                # Alternate approach: Use show version equivalent via system model
                if not metadata["system"].get("software_version"):
                    try:
                        system_filter = """
                        <system-time xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-shellutil-oper">
                            <clock/>
                        </system-time>
                        """
                        # Just to verify we can get system info
                        await connection.get_operational_state(filter_data=system_filter)
                    except:
                        pass

                if metadata["system"].get("software_version"):
                    logger.info(f"Collected Cisco software version: {metadata['system']['software_version']}")

            except Exception as e:
                logger.warning(f"Failed to collect software version: {e}")

            # System/Loopback0 Information
            try:
                # Try multiple approaches to get Loopback0 IP
                loopback0_ip = None

                # Approach 1: Use Cisco native YANG model for IPv4 interface addresses
                try:
                    ipv4_filter = """
                    <ipv4-io-oper xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-ipv4-io-oper">
                        <nodes>
                            <node>
                                <addresses>
                                    <vrf-addresses>
                                        <vrf-address>
                                            <vrf-name>default</vrf-name>
                                            <interface-addresses>
                                                <interface-address>
                                                    <interface-name>Loopback0</interface-name>
                                                </interface-address>
                                            </interface-addresses>
                                        </vrf-address>
                                    </vrf-addresses>
                                </addresses>
                            </node>
                        </nodes>
                    </ipv4-io-oper>
                    """
                    loopback_data = await connection.get_operational_state(filter_data=ipv4_filter)

                    if loopback_data:
                        # Extract IP from Cisco native model response
                        # Look for primary address pattern
                        ip_match = re.search(r'<address>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</address>', loopback_data)
                        if ip_match:
                            loopback0_ip = ip_match.group(1)
                except Exception as e1:
                    logger.debug(f"Cisco native model query failed: {e1}")

                # Approach 2: Use ietf-interfaces model if native model didn't work
                if not loopback0_ip:
                    try:
                        ietf_filter = """
                        <interfaces-state xmlns="urn:ietf:params:xml:ns:yang:ietf-interfaces">
                            <interface>
                                <name>Loopback0</name>
                            </interface>
                        </interfaces-state>
                        """
                        loopback_data = await connection.get_operational_state(filter_data=ietf_filter)

                        if loopback_data:
                            # Try to extract IP address from response
                            ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', loopback_data)
                            if ip_match:
                                loopback0_ip = ip_match.group(1)
                    except Exception as e2:
                        logger.debug(f"IETF interfaces model query failed: {e2}")

                # Approach 3: Fallback using XPath query
                if not loopback0_ip:
                    try:
                        loopback_xpath = '/interfaces-state/interface[name="Loopback0"]'
                        loopback_data = await connection.get_operational_state(xpath=loopback_xpath)

                        if loopback_data:
                            ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', loopback_data)
                            if ip_match:
                                loopback0_ip = ip_match.group(1)
                    except Exception as e3:
                        logger.debug(f"XPath query for Loopback0 failed: {e3}")

                if loopback0_ip:
                    metadata["system"]["loopback0_ip"] = loopback0_ip
                    logger.info(f"Collected Cisco Loopback0 IP: {loopback0_ip}")
                else:
                    logger.warning("Could not retrieve Loopback0 IP address")

            except Exception as e:
                logger.warning(f"Failed to collect Loopback0 interface info: {e}")

        except Exception as e:
            logger.error(f"Error collecting Cisco IOS-XR metadata: {e}")

        return metadata

    @staticmethod
    async def collect_metadata(vendor: str, connection) -> Optional[Dict[str, Any]]:
        """
        Collect metadata for a device based on vendor type

        Args:
            vendor: Device vendor (nokia_sros or cisco_xr)
            connection: Device connection object

        Returns:
            Dictionary containing device metadata, or None if collection failed
        """
        try:
            if vendor.lower() == "nokia_sros":
                return await DeviceMetadataCollector.collect_nokia_sros_metadata(connection)
            elif vendor.lower() == "cisco_xr":
                return await DeviceMetadataCollector.collect_cisco_xr_metadata(connection)
            else:
                logger.warning(f"Unsupported vendor for metadata collection: {vendor}")
                return None
        except Exception as e:
            logger.error(f"Failed to collect metadata: {e}")
            return None
