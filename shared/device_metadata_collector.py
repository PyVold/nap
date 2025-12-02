"""
Device Metadata Collector

Collects protocol and system metadata from network devices during discovery.
Supports vendor-specific metadata extraction for BGP, IGP, MPLS/LDP, and system info.
"""

import re
from typing import Dict, Any, Optional
from shared.logger import setup_logger

logger = setup_logger(__name__)


class DeviceMetadataCollector:
    """Collect protocol metadata from network devices"""

    @staticmethod
    async def collect_nokia_sros_metadata(connection) -> Dict[str, Any]:
        """
        Collect metadata from Nokia SR OS device

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
                bgp_output = await connection.run_command("show router bgp summary")

                # Extract BGP AS number
                as_match = re.search(r'AS\s+:\s+(\d+)', bgp_output)
                if as_match:
                    metadata["bgp"]["as_number"] = int(as_match.group(1))

                # Extract BGP Router ID
                router_id_match = re.search(r'Router ID\s+:\s+([\d\.]+)', bgp_output)
                if router_id_match:
                    metadata["bgp"]["router_id"] = router_id_match.group(1)

                # Count BGP neighbors
                neighbor_count = len(re.findall(r'^\d+\.\d+\.\d+\.\d+', bgp_output, re.MULTILINE))
                metadata["bgp"]["neighbor_count"] = neighbor_count

                # Count established sessions
                established_count = len(re.findall(r'Established', bgp_output))
                metadata["bgp"]["established_sessions"] = established_count

                logger.info(f"Collected BGP metadata: AS{metadata['bgp'].get('as_number')}, {established_count} sessions")
            except Exception as e:
                logger.warning(f"Failed to collect BGP metadata: {e}")

            # IGP Information (ISIS)
            try:
                isis_output = await connection.run_command("show router isis status")

                if "No ISIS instances configured" not in isis_output:
                    metadata["igp"]["type"] = "ISIS"

                    # Extract ISIS Router ID / System ID
                    system_id_match = re.search(r'System Id\s+:\s+([\w\.:-]+)', isis_output)
                    if system_id_match:
                        metadata["igp"]["router_id"] = system_id_match.group(1)

                    # Extract ISIS level
                    level_match = re.search(r'Level Capability\s+:\s+(\S+)', isis_output)
                    if level_match:
                        metadata["igp"]["isis_level"] = level_match.group(1)

                    # Count ISIS adjacencies
                    adj_output = await connection.run_command("show router isis adjacency")
                    adj_count = len(re.findall(r'Up', adj_output))
                    metadata["igp"]["adjacency_count"] = adj_count

                    logger.info(f"Collected ISIS metadata: {metadata['igp'].get('isis_level')}, {adj_count} adjacencies")
            except Exception as e:
                logger.warning(f"Failed to collect ISIS metadata: {e}")

            # Try OSPF if ISIS not found
            if metadata["igp"].get("type") != "ISIS":
                try:
                    ospf_output = await connection.run_command("show router ospf status")

                    if "No OSPF instances configured" not in ospf_output:
                        metadata["igp"]["type"] = "OSPF"

                        # Extract OSPF Router ID
                        router_id_match = re.search(r'Router Id\s+:\s+([\d\.]+)', ospf_output)
                        if router_id_match:
                            metadata["igp"]["router_id"] = router_id_match.group(1)

                        # Count OSPF neighbors
                        neighbor_output = await connection.run_command("show router ospf neighbor")
                        neighbor_count = len(re.findall(r'Full', neighbor_output))
                        metadata["igp"]["neighbor_count"] = neighbor_count

                        logger.info(f"Collected OSPF metadata: {neighbor_count} neighbors")
                except Exception as e:
                    logger.warning(f"Failed to collect OSPF metadata: {e}")

            # LDP Information
            try:
                ldp_output = await connection.run_command("show router ldp status")

                if "LDP instance not active" not in ldp_output:
                    metadata["ldp"]["enabled"] = True

                    # Extract LDP Router ID
                    router_id_match = re.search(r'Router Id\s+:\s+([\d\.]+)', ldp_output)
                    if router_id_match:
                        metadata["ldp"]["router_id"] = router_id_match.group(1)

                    # Count LDP sessions
                    session_output = await connection.run_command("show router ldp session")
                    session_count = len(re.findall(r'Operational', session_output))
                    metadata["ldp"]["session_count"] = session_count

                    logger.info(f"Collected LDP metadata: {session_count} sessions")
                else:
                    metadata["ldp"]["enabled"] = False
            except Exception as e:
                logger.warning(f"Failed to collect LDP metadata: {e}")
                metadata["ldp"]["enabled"] = False

            # System Interface (Loopback) Information
            try:
                system_output = await connection.run_command("show router interface system")

                # Extract system interface IP
                ip_match = re.search(r'IP Addr/mask\s+:\s+([\d\.]+)/\d+', system_output)
                if ip_match:
                    metadata["system"]["ip_address"] = ip_match.group(1)
                    logger.info(f"Collected system IP: {metadata['system']['ip_address']}")
            except Exception as e:
                logger.warning(f"Failed to collect system interface info: {e}")

            # MPLS/Segment Routing Information
            try:
                mpls_output = await connection.run_command("show router mpls status")
                metadata["mpls"]["enabled"] = "Admin State         : Up" in mpls_output

                # Check for Segment Routing
                try:
                    sr_output = await connection.run_command("show router segment-routing prefix-sids")
                    metadata["mpls"]["segment_routing"] = "Prefix" in sr_output
                except:
                    metadata["mpls"]["segment_routing"] = False

                logger.info(f"Collected MPLS metadata: enabled={metadata['mpls']['enabled']}, SR={metadata['mpls']['segment_routing']}")
            except Exception as e:
                logger.warning(f"Failed to collect MPLS metadata: {e}")

        except Exception as e:
            logger.error(f"Error collecting Nokia SR OS metadata: {e}")

        return metadata

    @staticmethod
    async def collect_cisco_iosxr_metadata(connection) -> Dict[str, Any]:
        """
        Collect metadata from Cisco IOS-XR device

        Collects:
        - BGP AS number and router ID
        - IGP type (OSPF/ISIS) and router ID
        - LDP status and neighbors
        - Loopback0 IP
        - MPLS status
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
                bgp_output = await connection.run_command("show bgp summary")

                # Extract BGP AS number
                as_match = re.search(r'BGP router identifier ([\d\.]+), local AS number (\d+)', bgp_output)
                if as_match:
                    metadata["bgp"]["router_id"] = as_match.group(1)
                    metadata["bgp"]["as_number"] = int(as_match.group(2))

                # Count neighbors
                neighbor_lines = re.findall(r'^\d+\.\d+\.\d+\.\d+', bgp_output, re.MULTILINE)
                metadata["bgp"]["neighbor_count"] = len(neighbor_lines)

                logger.info(f"Collected BGP metadata: AS{metadata['bgp'].get('as_number')}")
            except Exception as e:
                logger.warning(f"Failed to collect BGP metadata: {e}")

            # OSPF Information
            try:
                ospf_output = await connection.run_command("show ospf")

                if "Routing Process" in ospf_output:
                    metadata["igp"]["type"] = "OSPF"

                    # Extract Router ID
                    router_id_match = re.search(r'Router Id: ([\d\.]+)', ospf_output)
                    if router_id_match:
                        metadata["igp"]["router_id"] = router_id_match.group(1)

                    logger.info(f"Collected OSPF metadata")
            except Exception as e:
                logger.warning(f"Failed to collect OSPF metadata: {e}")

            # ISIS Information (if OSPF not found)
            if metadata["igp"].get("type") != "OSPF":
                try:
                    isis_output = await connection.run_command("show isis")

                    if "IS-IS" in isis_output:
                        metadata["igp"]["type"] = "ISIS"

                        # Extract System ID
                        system_id_match = re.search(r'System Id: ([\w\.]+)', isis_output)
                        if system_id_match:
                            metadata["igp"]["router_id"] = system_id_match.group(1)

                        logger.info(f"Collected ISIS metadata")
                except Exception as e:
                    logger.warning(f"Failed to collect ISIS metadata: {e}")

            # LDP Information
            try:
                ldp_output = await connection.run_command("show mpls ldp summary")

                metadata["ldp"]["enabled"] = "LDP instance" in ldp_output or "Neighbors" in ldp_output

                if metadata["ldp"]["enabled"]:
                    # Count LDP neighbors
                    neighbor_count = len(re.findall(r'\d+\.\d+\.\d+\.\d+:\d+', ldp_output))
                    metadata["ldp"]["neighbor_count"] = neighbor_count

                    logger.info(f"Collected LDP metadata: {neighbor_count} neighbors")
            except Exception as e:
                logger.warning(f"Failed to collect LDP metadata: {e}")
                metadata["ldp"]["enabled"] = False

            # Loopback0 IP
            try:
                loopback_output = await connection.run_command("show ipv4 interface loopback0 brief")

                ip_match = re.search(r'Loopback0\s+([\d\.]+)', loopback_output)
                if ip_match:
                    metadata["system"]["loopback0_ip"] = ip_match.group(1)
                    logger.info(f"Collected Loopback0 IP: {metadata['system']['loopback0_ip']}")
            except Exception as e:
                logger.warning(f"Failed to collect Loopback0 info: {e}")

        except Exception as e:
            logger.error(f"Error collecting Cisco IOS-XR metadata: {e}")

        return metadata


    @staticmethod
    async def collect_metadata(vendor: str, connection) -> Optional[Dict[str, Any]]:
        """
        Collect metadata based on device vendor

        Args:
            vendor: Device vendor (nokia_sros, cisco_iosxr, etc.)
            connection: Active device connection

        Returns:
            Dictionary of metadata or None if collection fails
        """
        try:
            if vendor.lower() == "nokia_sros":
                return await DeviceMetadataCollector.collect_nokia_sros_metadata(connection)
            elif vendor.lower() == "cisco_iosxr":
                return await DeviceMetadataCollector.collect_cisco_iosxr_metadata(connection)
            else:
                logger.warning(f"Metadata collection not implemented for vendor: {vendor}")
                return None
        except Exception as e:
            logger.error(f"Failed to collect metadata for {vendor}: {e}")
            return None
