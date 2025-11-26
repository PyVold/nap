"""
Network Topology Discovery & Visualization Models
Discover and map network relationships using LLDP/CDP
"""
from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, Text, Float
from sqlalchemy.sql import func
from database import Base


class TopologyNode(Base):
    __tablename__ = "topology_nodes"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, index=True)  # May be null for discovered-only devices

    # Node identification
    hostname = Column(String, index=True)
    ip_address = Column(String, index=True)
    mac_address = Column(String)
    system_name = Column(String)

    # Device information
    vendor = Column(String)
    model = Column(String)
    platform = Column(String)
    software_version = Column(String)

    # Node type
    node_type = Column(String)  # router, switch, firewall, server, unknown
    role = Column(String)  # core, distribution, access, edge

    # Discovery protocol
    discovered_via = Column(String)  # lldp, cdp, arp, snmp, manual

    # Visualization coordinates
    x_position = Column(Float)
    y_position = Column(Float)
    layer = Column(Integer)  # For hierarchical layout

    # Status
    is_managed = Column(Boolean, default=False)  # Is this device managed by the platform?
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True))

    # Additional details
    capabilities = Column(JSON)  # Router, switch, bridge capabilities
    management_ips = Column(JSON)  # All management IP addresses
    interfaces_count = Column(Integer)

    # Metadata
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TopologyLink(Base):
    __tablename__ = "topology_links"

    id = Column(Integer, primary_key=True, index=True)

    # Source and destination nodes
    source_node_id = Column(Integer, nullable=False, index=True)
    destination_node_id = Column(Integer, nullable=False, index=True)

    # Interface details
    source_interface = Column(String, nullable=False)
    destination_interface = Column(String, nullable=False)

    # Link properties
    link_type = Column(String)  # physical, logical, lag, trunk
    link_speed = Column(String)  # 1G, 10G, 100G, etc.
    duplex = Column(String)  # full, half
    mtu = Column(Integer)

    # Status
    is_active = Column(Boolean, default=True)
    operational_status = Column(String)  # up, down, admin_down

    # Discovery
    discovered_via = Column(String)  # lldp, cdp
    last_seen = Column(DateTime(timezone=True))

    # Traffic stats (if available)
    bandwidth_utilization = Column(Float)  # Percentage
    errors_count = Column(Integer)
    drops_count = Column(Integer)

    # VLAN/tagging
    vlans = Column(JSON)  # VLANs allowed on this link

    # Metadata
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TopologyDiscovery(Base):
    __tablename__ = "topology_discoveries"

    id = Column(Integer, primary_key=True, index=True)

    # Discovery session
    session_id = Column(String, unique=True, index=True)
    discovery_type = Column(String)  # full, incremental, targeted

    # Scope
    seed_devices = Column(JSON)  # Starting device IDs
    max_depth = Column(Integer, default=5)  # How many hops to discover

    # Results
    nodes_discovered = Column(Integer, default=0)
    links_discovered = Column(Integer, default=0)
    new_nodes = Column(Integer, default=0)
    new_links = Column(Integer, default=0)

    # Status
    status = Column(String, nullable=False)  # running, completed, failed, cancelled
    progress_percentage = Column(Integer, default=0)
    current_device = Column(String)

    # Error handling
    errors = Column(JSON)  # List of errors encountered
    warnings = Column(JSON)

    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)

    # Metadata
    initiated_by = Column(String)
    notes = Column(Text)
