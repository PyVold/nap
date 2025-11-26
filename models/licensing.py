"""
Licensing Management Models
Track device licenses, software versions, and compliance
"""
from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, Text, Date, Float
from sqlalchemy.sql import func
from database import Base


class License(Base):
    __tablename__ = "licenses"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, nullable=False, index=True)

    # License details
    license_type = Column(String, nullable=False)  # feature, capacity, term
    license_name = Column(String, nullable=False)
    license_key = Column(String)
    feature = Column(String)  # What feature this license enables

    # Vendor-specific
    vendor = Column(String, nullable=False)
    product = Column(String)
    sku = Column(String)

    # License status
    status = Column(String, nullable=False)  # active, expired, expiring_soon, invalid
    is_active = Column(Boolean, default=True)
    is_valid = Column(Boolean, default=True)

    # Dates
    issue_date = Column(Date)
    expiration_date = Column(Date)
    last_verified = Column(DateTime(timezone=True))

    # Capacity tracking (for capacity-based licenses)
    capacity_total = Column(Integer)  # Total licensed capacity
    capacity_used = Column(Integer)  # Currently used capacity
    capacity_unit = Column(String)  # users, ports, bandwidth, etc.

    # Financial
    cost = Column(Float)
    currency = Column(String, default="USD")
    purchase_order = Column(String)
    renewal_cost = Column(Float)

    # Support contract
    support_level = Column(String)  # basic, standard, premium
    support_expires = Column(Date)

    # Contact information
    vendor_contact = Column(String)
    account_manager = Column(String)
    contract_number = Column(String)

    # Alerts
    alert_days_before_expiry = Column(Integer, default=30)
    alert_capacity_threshold = Column(Integer, default=80)  # Percentage

    # Notes
    notes = Column(Text)
    attachments = Column(JSON)  # URLs to license files/documents

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String)


class LicenseAlert(Base):
    __tablename__ = "license_alerts"

    id = Column(Integer, primary_key=True, index=True)
    license_id = Column(Integer, nullable=False)
    device_id = Column(Integer, nullable=False)

    alert_type = Column(String, nullable=False)  # expiring, expired, capacity_warning, invalid
    severity = Column(String, nullable=False)  # info, warning, critical
    message = Column(Text, nullable=False)

    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String)
    acknowledged_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class SoftwareInventory(Base):
    __tablename__ = "software_inventory"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, nullable=False, index=True)

    # Software details
    software_name = Column(String, nullable=False)
    version = Column(String, nullable=False)
    build = Column(String)
    release_date = Column(Date)

    # Type
    software_type = Column(String)  # os, firmware, patch, feature_pack

    # Status
    is_current = Column(Boolean, default=True)
    is_supported = Column(Boolean, default=True)
    is_eol = Column(Boolean, default=False)  # End of Life
    is_eos = Column(Boolean, default=False)  # End of Support

    # Dates
    eol_date = Column(Date)  # End of Life
    eos_date = Column(Date)  # End of Support
    eoa_date = Column(Date)  # End of Availability (can't buy anymore)

    # CVE tracking
    known_cves = Column(JSON)  # List of known CVEs for this version
    cve_count = Column(Integer, default=0)
    critical_cve_count = Column(Integer, default=0)

    # Recommended version
    recommended_version = Column(String)
    upgrade_available = Column(Boolean, default=False)

    # Discovery
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    last_verified = Column(DateTime(timezone=True))

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
