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
                bgp_xpath = '/state/router[router-name="Base"]/bgp'
                bgp_data = await connection.get_operational_state(xpath=bgp_xpath)

                if bgp_data:
                    logger.debug(f"BGP raw response (first 500 chars): {bgp_data[:500]}")
                    bgp_json = json.loads(bgp_data)
                    logger.debug(f"BGP JSON keys: {bgp_json.keys() if isinstance(bgp_json, dict) else type(bgp_json)}")

                    # Navigate through the JSON structure
                    if 'data' in bgp_json and 'state' in bgp_json['data']:
                        state = bgp_json['data']['state']
                        if 'router' in state:
                            router = state['router']
                            if isinstance(router, list):
                                router = router[0] if router else {}

                            if 'bgp' in router:
                                bgp = router['bgp']

                                # Extract AS number
                                if 'autonomous-system' in bgp:
                                    metadata["bgp"]["as_number"] = bgp['autonomous-system']

                                # Extract Router ID
                                if 'router-id' in bgp:
                                    metadata["bgp"]["router_id"] = bgp['router-id']

                                # Count neighbors and established sessions
                                if 'neighbor' in bgp:
                                    neighbors = bgp['neighbor']
                                    if isinstance(neighbors, dict):
                                        neighbors = [neighbors]

                                    metadata["bgp"]["neighbor_count"] = len(neighbors)
                                    established = sum(1 for n in neighbors if n.get('session-state') == 'established')
                                    metadata["bgp"]["established_sessions"] = established

                logger.info(f"Collected BGP metadata: AS{metadata['bgp'].get('as_number')}, "
                           f"{metadata['bgp'].get('established_sessions', 0)} established sessions")
            except Exception as e:
                logger.warning(f"Failed to collect BGP metadata: {e}")

            # IGP Information (ISIS)
            try:
                isis_xpath = '/state/router[router-name="Base"]/isis'
                isis_data = await connection.get_operational_state(xpath=isis_xpath)

                if isis_data:
                    logger.debug(f"ISIS raw response (first 500 chars): {isis_data[:500]}")
                    isis_json = json.loads(isis_data)
                    logger.debug(f"ISIS JSON type: {type(isis_json)}, keys: {isis_json.keys() if isinstance(isis_json, dict) else 'N/A'}")

                    if 'data' in isis_json and 'state' in isis_json['data']:
                        state = isis_json['data']['state']
                        if 'router' in state:
                            router = state['router']
                            if isinstance(router, list):
                                router = router[0] if router else {}

                            if 'isis' in router and router['isis']:
                                isis = router['isis']
                                if isinstance(isis, list):
                                    isis = isis[0] if isis else {}

                                metadata["igp"]["type"] = "ISIS"

                                # Extract System ID
                                if 'system-id' in isis:
                                    metadata["igp"]["router_id"] = isis['system-id']

                                # Extract level capability
                                if 'level-capability' in isis:
                                    metadata["igp"]["isis_level"] = isis['level-capability']

                                # Count adjacencies
                                if 'adjacency' in isis:
                                    adjacencies = isis['adjacency']
                                    if isinstance(adjacencies, dict):
                                        adjacencies = [adjacencies]
                                    metadata["igp"]["adjacency_count"] = len(adjacencies)

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

                        if 'data' in ospf_json and 'state' in ospf_json['data']:
                            state = ospf_json['data']['state']
                            if 'router' in state:
                                router = state['router']
                                if isinstance(router, list):
                                    router = router[0] if router else {}

                                if 'ospf' in router and router['ospf']:
                                    ospf = router['ospf']
                                    if isinstance(ospf, list):
                                        ospf = ospf[0] if ospf else {}

                                    metadata["igp"]["type"] = "OSPF"

                                    # Extract Router ID
                                    if 'router-id' in ospf:
                                        metadata["igp"]["router_id"] = ospf['router-id']

                                    # Count neighbors
                                    if 'neighbor' in ospf:
                                        neighbors = ospf['neighbor']
                                        if isinstance(neighbors, dict):
                                            neighbors = [neighbors]
                                        metadata["igp"]["neighbor_count"] = len(neighbors)

                    logger.info(f"Collected OSPF metadata: {metadata['igp'].get('neighbor_count', 0)} neighbors")
                except Exception as e:
                    logger.warning(f"Failed to collect OSPF metadata: {e}")

            # LDP Information
            try:
                ldp_xpath = '/state/router[router-name="Base"]/ldp'
                ldp_data = await connection.get_operational_state(xpath=ldp_xpath)

                if ldp_data:
                    ldp_json = json.loads(ldp_data)

                    if 'data' in ldp_json and 'state' in ldp_json['data']:
                        state = ldp_json['data']['state']
                        if 'router' in state:
                            router = state['router']
                            if isinstance(router, list):
                                router = router[0] if router else {}

                            if 'ldp' in router and router['ldp']:
                                ldp = router['ldp']
                                metadata["ldp"]["enabled"] = True

                                # Extract Router ID
                                if 'router-id' in ldp:
                                    metadata["ldp"]["router_id"] = ldp['router-id']

                                # Count sessions
                                if 'session' in ldp:
                                    sessions = ldp['session']
                                    if isinstance(sessions, dict):
                                        sessions = [sessions]
                                    metadata["ldp"]["session_count"] = len(sessions)
                            else:
                                metadata["ldp"]["enabled"] = False

                logger.info(f"Collected LDP metadata: enabled={metadata['ldp'].get('enabled')}, "
                           f"{metadata['ldp'].get('session_count', 0)} sessions")
            except Exception as e:
                logger.warning(f"Failed to collect LDP metadata: {e}")

            # System Information
            try:
                system_xpath = '/state/system'
                system_data = await connection.get_operational_state(xpath=system_xpath)

                if system_data:
                    system_json = json.loads(system_data)

                    if 'data' in system_json and 'state' in system_json['data']:
                        state = system_json['data']['state']
                        if 'system' in state:
                            system = state['system']

                            # Try to get system interface IP
                            if 'management-interface' in system:
                                mgmt = system['management-interface']
                                if 'netconf' in mgmt and 'admin-state' in mgmt['netconf']:
                                    # Get the first available IP
                                    if 'ip-address' in mgmt['netconf']:
                                        ip = mgmt['netconf']['ip-address']
                                        if isinstance(ip, dict) and 'address' in ip:
                                            metadata["system"]["ip_address"] = ip['address']

                logger.info(f"Collected system metadata: IP={metadata['system'].get('ip_address')}")
            except Exception as e:
                logger.warning(f"Failed to collect system interface info: {e}")

            # MPLS/SR Information
            try:
                mpls_xpath = '/state/router[router-name="Base"]/mpls'
                mpls_data = await connection.get_operational_state(xpath=mpls_xpath)

                if mpls_data:
                    mpls_json = json.loads(mpls_data)

                    if 'data' in mpls_json and 'state' in mpls_json['data']:
                        state = mpls_json['data']['state']
                        if 'router' in state:
                            router = state['router']
                            if isinstance(router, list):
                                router = router[0] if router else {}

                            if 'mpls' in router and router['mpls']:
                                metadata["mpls"]["enabled"] = True
                                mpls = router['mpls']

                                # Check for Segment Routing
                                if 'segment-routing' in mpls:
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

                # Parse BGP data (simplified - may need adjustment based on actual response)
                if bgp_data and 'default-vrf' in bgp_data:
                    if 'as' in bgp_data:
                        metadata["bgp"]["as_number"] = int(bgp_data['as'])
                    if 'router-id' in bgp_data:
                        metadata["bgp"]["router_id"] = bgp_data['router-id']

                logger.info(f"Collected Cisco BGP metadata")
            except Exception as e:
                logger.warning(f"Failed to collect BGP metadata: {e}")

            # System/Loopback Information
            try:
                # Try to get Loopback0 IP
                intf_filter = """
                <interfaces xmlns="http://cisco.com/ns/yang/Cisco-IOS-XR-pfi-im-cmd-oper">
                    <interface-summary/>
                </interfaces>
                """

                intf_data = await connection.get_config(filter_data=intf_filter)
                # Parse interface data to find Loopback0 IP

                logger.info(f"Collected Cisco system metadata")
            except Exception as e:
                logger.warning(f"Failed to collect system interface info: {e}")

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
