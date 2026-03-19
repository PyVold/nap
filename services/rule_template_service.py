# ============================================================================
# services/rule_template_service.py
# ============================================================================

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from db_models import RuleTemplateDB, AuditRuleDB
from models.enums import VendorType, SeverityLevel
from shared.logger import setup_logger

logger = setup_logger(__name__)


class RuleTemplateService:
    """Service for managing rule templates and libraries"""

    # Pre-defined rule templates
    BUILTIN_TEMPLATES = [
        # CIS Benchmarks for Cisco IOS XR
        {
            "name": "CIS: SSH Protocol 2 Only",
            "description": "Ensure SSH is configured to use protocol version 2 only (CIS Benchmark)",
            "category": "CIS Benchmark",
            "vendor": VendorType.CISCO_XR.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/ssh/server",
            "expected_value": "v2",
            "check_type": "contains",
            "framework": "CIS",
            "tags": {"cis": "5.2.4", "category": "access_control"}
        },
        {
            "name": "CIS: Enable AAA Authentication",
            "description": "Ensure AAA authentication is enabled (CIS Benchmark)",
            "category": "CIS Benchmark",
            "vendor": VendorType.CISCO_XR.value,
            "severity": SeverityLevel.CRITICAL.value,
            "xpath": "/aaa/authentication",
            "expected_value": "true",
            "check_type": "exists",
            "framework": "CIS",
            "tags": {"cis": "4.1.1", "category": "authentication"}
        },
        {
            "name": "CIS: Configure Login Banner",
            "description": "Ensure login banner is configured (CIS Benchmark)",
            "category": "CIS Benchmark",
            "vendor": VendorType.CISCO_XR.value,
            "severity": SeverityLevel.MEDIUM.value,
            "xpath": "/banner/login",
            "expected_value": None,
            "check_type": "exists",
            "framework": "CIS",
            "tags": {"cis": "1.1.1", "category": "general"}
        },

        # Nokia SROS CIS Benchmarks
        {
            "name": "CIS: Nokia SSH Configuration",
            "description": "Ensure SSH is properly configured on Nokia SROS (CIS Benchmark)",
            "category": "CIS Benchmark",
            "vendor": VendorType.NOKIA_SROS.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/configure/system/security/ssh",
            "expected_value": None,
            "check_type": "exists",
            "framework": "CIS",
            "tags": {"cis": "5.2", "category": "access_control"}
        },
        {
            "name": "CIS: Nokia User Authentication",
            "description": "Ensure proper user authentication on Nokia SROS (CIS Benchmark)",
            "category": "CIS Benchmark",
            "vendor": VendorType.NOKIA_SROS.value,
            "severity": SeverityLevel.CRITICAL.value,
            "xpath": "/configure/system/security/user-params",
            "expected_value": None,
            "check_type": "exists",
            "framework": "CIS",
            "tags": {"cis": "4.1", "category": "authentication"}
        },
        {
            "name": "CIS: Nokia Login Banner",
            "description": "Ensure login banner is configured on Nokia SROS (CIS Benchmark)",
            "category": "CIS Benchmark",
            "vendor": VendorType.NOKIA_SROS.value,
            "severity": SeverityLevel.MEDIUM.value,
            "xpath": "/configure/system/login-control",
            "expected_value": None,
            "check_type": "exists",
            "framework": "CIS",
            "tags": {"cis": "1.1", "category": "general"}
        },
        {
            "name": "PCI-DSS: Nokia Encryption",
            "description": "Ensure strong encryption is configured (PCI-DSS 8.2.1)",
            "category": "PCI-DSS",
            "vendor": VendorType.NOKIA_SROS.value,
            "severity": SeverityLevel.CRITICAL.value,
            "xpath": "/configure/system/security/tls",
            "expected_value": None,
            "check_type": "exists",
            "framework": "PCI-DSS",
            "tags": {"pci": "8.2.1", "category": "encryption"}
        },
        {
            "name": "Best Practice: Nokia NTP Configuration",
            "description": "Ensure NTP is configured on Nokia SROS for time synchronization",
            "category": "Best Practice",
            "vendor": VendorType.NOKIA_SROS.value,
            "severity": SeverityLevel.MEDIUM.value,
            "xpath": "/configure/system/time/ntp",
            "expected_value": None,
            "check_type": "exists",
            "framework": "Best Practice",
            "tags": {"category": "time_sync"}
        },
        {
            "name": "Best Practice: Nokia SNMP Configuration",
            "description": "Ensure SNMP is properly configured on Nokia SROS",
            "category": "Best Practice",
            "vendor": VendorType.NOKIA_SROS.value,
            "severity": SeverityLevel.MEDIUM.value,
            "xpath": "/configure/system/security/snmp",
            "expected_value": None,
            "check_type": "exists",
            "framework": "Best Practice",
            "tags": {"category": "monitoring"}
        },

        # PCI-DSS Requirements
        {
            "name": "PCI-DSS: Strong Cryptography for Authentication",
            "description": "Use strong cryptography for authentication (PCI-DSS 8.2.1)",
            "category": "PCI-DSS",
            "vendor": VendorType.CISCO_XR.value,
            "severity": SeverityLevel.CRITICAL.value,
            "xpath": "/crypto",
            "expected_value": None,
            "check_type": "exists",
            "framework": "PCI-DSS",
            "tags": {"pci": "8.2.1", "category": "encryption"}
        },
        {
            "name": "PCI-DSS: Logging and Monitoring",
            "description": "Ensure logging is enabled (PCI-DSS 10.1)",
            "category": "PCI-DSS",
            "vendor": VendorType.CISCO_XR.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/logging",
            "expected_value": None,
            "check_type": "exists",
            "framework": "PCI-DSS",
            "tags": {"pci": "10.1", "category": "logging"}
        },

        # NIST Security Controls
        {
            "name": "NIST: Access Control Policy",
            "description": "Verify access control policy implementation (NIST AC-1)",
            "category": "NIST 800-53",
            "vendor": VendorType.CISCO_XR.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/aaa",
            "expected_value": None,
            "check_type": "exists",
            "framework": "NIST",
            "tags": {"nist": "AC-1", "category": "access_control"}
        },
        {
            "name": "NIST: Audit and Accountability",
            "description": "Ensure audit records are generated (NIST AU-2)",
            "category": "NIST 800-53",
            "vendor": VendorType.CISCO_XR.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/logging/audit",
            "expected_value": None,
            "check_type": "exists",
            "framework": "NIST",
            "tags": {"nist": "AU-2", "category": "audit"}
        },

        # Best Practices
        {
            "name": "Best Practice: NTP Configuration",
            "description": "Ensure NTP is configured for time synchronization",
            "category": "Best Practice",
            "vendor": VendorType.CISCO_XR.value,
            "severity": SeverityLevel.MEDIUM.value,
            "xpath": "/ntp/server",
            "expected_value": None,
            "check_type": "exists",
            "framework": "Best Practice",
            "tags": {"category": "time_sync"}
        },
        {
            "name": "Best Practice: SNMP v3 Only",
            "description": "Ensure only SNMPv3 is enabled for security",
            "category": "Best Practice",
            "vendor": VendorType.CISCO_XR.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/snmp/server/v3",
            "expected_value": None,
            "check_type": "exists",
            "framework": "Best Practice",
            "tags": {"category": "monitoring"}
        },

        # ====================================================================
        # Additional Cisco IOS-XR Templates
        # ====================================================================
        {
            "name": "Best Practice: BGP MD5 Authentication",
            "description": "Ensure BGP sessions use MD5 authentication to prevent unauthorized peering",
            "category": "Best Practice",
            "vendor": VendorType.CISCO_XR.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/router/bgp/neighbor/password",
            "expected_value": None,
            "check_type": "exists",
            "framework": "Best Practice",
            "tags": {"category": "routing_security"}
        },
        {
            "name": "Best Practice: Console Timeout",
            "description": "Ensure console line has an idle timeout configured to prevent unauthorized access",
            "category": "Best Practice",
            "vendor": VendorType.CISCO_XR.value,
            "severity": SeverityLevel.MEDIUM.value,
            "xpath": "/line/console/exec-timeout",
            "expected_value": None,
            "check_type": "exists",
            "framework": "Best Practice",
            "tags": {"category": "access_control"}
        },
        {
            "name": "PCI-DSS: ACL Configuration",
            "description": "Ensure access control lists are configured to restrict traffic (PCI-DSS 1.2)",
            "category": "PCI-DSS",
            "vendor": VendorType.CISCO_XR.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/ipv4/access-list",
            "expected_value": None,
            "check_type": "exists",
            "framework": "PCI-DSS",
            "tags": {"pci": "1.2", "category": "firewall"}
        },

        # ====================================================================
        # Additional Nokia SROS Templates
        # ====================================================================
        {
            "name": "Best Practice: Nokia BGP Authentication",
            "description": "Ensure BGP sessions use authentication on Nokia SROS to prevent unauthorized peering",
            "category": "Best Practice",
            "vendor": VendorType.NOKIA_SROS.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/configure/router/bgp/group/auth-keychain",
            "expected_value": None,
            "check_type": "exists",
            "framework": "Best Practice",
            "tags": {"category": "routing_security"}
        },
        {
            "name": "NIST: Nokia Access Control",
            "description": "Verify access control policy implementation on Nokia SROS (NIST AC-1)",
            "category": "NIST 800-53",
            "vendor": VendorType.NOKIA_SROS.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/configure/system/security/profile",
            "expected_value": None,
            "check_type": "exists",
            "framework": "NIST",
            "tags": {"nist": "AC-1", "category": "access_control"}
        },
        {
            "name": "PCI-DSS: Nokia Logging",
            "description": "Ensure logging is properly configured on Nokia SROS (PCI-DSS 10.1)",
            "category": "PCI-DSS",
            "vendor": VendorType.NOKIA_SROS.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/configure/log/log-id",
            "expected_value": None,
            "check_type": "exists",
            "framework": "PCI-DSS",
            "tags": {"pci": "10.1", "category": "logging"}
        },

        # ====================================================================
        # Cisco IOS-XE Templates
        # ====================================================================
        {
            "name": "CIS: SSH v2 Configuration",
            "description": "Ensure SSH version 2 is configured on Cisco IOS-XE (CIS Benchmark)",
            "category": "CIS Benchmark",
            "vendor": VendorType.CISCO_XE.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/native/ip/ssh",
            "expected_value": "2",
            "check_type": "contains",
            "framework": "CIS",
            "tags": {"cis": "5.2.4", "category": "access_control"}
        },
        {
            "name": "CIS: AAA Authentication",
            "description": "Ensure AAA authentication is enabled on Cisco IOS-XE (CIS Benchmark)",
            "category": "CIS Benchmark",
            "vendor": VendorType.CISCO_XE.value,
            "severity": SeverityLevel.CRITICAL.value,
            "xpath": "/native/aaa",
            "expected_value": None,
            "check_type": "exists",
            "framework": "CIS",
            "tags": {"cis": "4.1.1", "category": "authentication"}
        },
        {
            "name": "CIS: Login Banner",
            "description": "Ensure a login banner is configured on Cisco IOS-XE (CIS Benchmark)",
            "category": "CIS Benchmark",
            "vendor": VendorType.CISCO_XE.value,
            "severity": SeverityLevel.MEDIUM.value,
            "xpath": "/native/banner",
            "expected_value": None,
            "check_type": "exists",
            "framework": "CIS",
            "tags": {"cis": "1.1.1", "category": "general"}
        },
        {
            "name": "PCI-DSS: Strong Cryptography",
            "description": "Ensure strong cryptography is configured on Cisco IOS-XE (PCI-DSS 8.2.1)",
            "category": "PCI-DSS",
            "vendor": VendorType.CISCO_XE.value,
            "severity": SeverityLevel.CRITICAL.value,
            "xpath": "/native/ip/ssh",
            "expected_value": "aes256",
            "check_type": "contains",
            "framework": "PCI-DSS",
            "tags": {"pci": "8.2.1", "category": "encryption"}
        },
        {
            "name": "PCI-DSS: Logging and Monitoring",
            "description": "Ensure logging is enabled on Cisco IOS-XE (PCI-DSS 10.1)",
            "category": "PCI-DSS",
            "vendor": VendorType.CISCO_XE.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/native/logging",
            "expected_value": None,
            "check_type": "exists",
            "framework": "PCI-DSS",
            "tags": {"pci": "10.1", "category": "logging"}
        },
        {
            "name": "NIST: Access Control Policy",
            "description": "Verify access control policy implementation on Cisco IOS-XE (NIST AC-1)",
            "category": "NIST 800-53",
            "vendor": VendorType.CISCO_XE.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/native/aaa",
            "expected_value": None,
            "check_type": "exists",
            "framework": "NIST",
            "tags": {"nist": "AC-1", "category": "access_control"}
        },
        {
            "name": "Best Practice: NTP Configuration",
            "description": "Ensure NTP is configured on Cisco IOS-XE for time synchronization",
            "category": "Best Practice",
            "vendor": VendorType.CISCO_XE.value,
            "severity": SeverityLevel.MEDIUM.value,
            "xpath": "/native/ntp",
            "expected_value": None,
            "check_type": "exists",
            "framework": "Best Practice",
            "tags": {"category": "time_sync"}
        },
        {
            "name": "Best Practice: SNMPv3 Only",
            "description": "Ensure only SNMPv3 is enabled on Cisco IOS-XE for security",
            "category": "Best Practice",
            "vendor": VendorType.CISCO_XE.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/native/snmp-server",
            "expected_value": "v3",
            "check_type": "contains",
            "framework": "Best Practice",
            "tags": {"category": "monitoring"}
        },
        {
            "name": "Best Practice: Console Line Timeout",
            "description": "Ensure console line timeout is configured on Cisco IOS-XE to prevent unauthorized access",
            "category": "Best Practice",
            "vendor": VendorType.CISCO_XE.value,
            "severity": SeverityLevel.MEDIUM.value,
            "xpath": "/native/line/con",
            "expected_value": None,
            "check_type": "exists",
            "framework": "Best Practice",
            "tags": {"category": "access_control"}
        },
        {
            "name": "Best Practice: BGP Authentication",
            "description": "Ensure BGP neighbor authentication is configured on Cisco IOS-XE",
            "category": "Best Practice",
            "vendor": VendorType.CISCO_XE.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/native/router/bgp/neighbor/password",
            "expected_value": None,
            "check_type": "exists",
            "framework": "Best Practice",
            "tags": {"category": "routing_security"}
        },

        # ====================================================================
        # Juniper JunOS Templates
        # ====================================================================
        {
            "name": "CIS: SSH Configuration",
            "description": "Ensure SSH is properly configured on Juniper JunOS (CIS Benchmark)",
            "category": "CIS Benchmark",
            "vendor": VendorType.JUNIPER_JUNOS.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/configuration/system/services/ssh",
            "expected_value": "v2",
            "check_type": "contains",
            "framework": "CIS",
            "tags": {"cis": "5.2", "category": "access_control"}
        },
        {
            "name": "CIS: Authentication Order",
            "description": "Ensure proper authentication order is configured on Juniper JunOS (CIS Benchmark)",
            "category": "CIS Benchmark",
            "vendor": VendorType.JUNIPER_JUNOS.value,
            "severity": SeverityLevel.CRITICAL.value,
            "xpath": "/configuration/system/authentication-order",
            "expected_value": None,
            "check_type": "exists",
            "framework": "CIS",
            "tags": {"cis": "4.1", "category": "authentication"}
        },
        {
            "name": "CIS: Login Message",
            "description": "Ensure login message is configured on Juniper JunOS (CIS Benchmark)",
            "category": "CIS Benchmark",
            "vendor": VendorType.JUNIPER_JUNOS.value,
            "severity": SeverityLevel.MEDIUM.value,
            "xpath": "/configuration/system/login/message",
            "expected_value": None,
            "check_type": "exists",
            "framework": "CIS",
            "tags": {"cis": "1.1", "category": "general"}
        },
        {
            "name": "PCI-DSS: Security Policies",
            "description": "Ensure security policies are configured on Juniper JunOS (PCI-DSS 1.2)",
            "category": "PCI-DSS",
            "vendor": VendorType.JUNIPER_JUNOS.value,
            "severity": SeverityLevel.CRITICAL.value,
            "xpath": "/configuration/security",
            "expected_value": None,
            "check_type": "exists",
            "framework": "PCI-DSS",
            "tags": {"pci": "1.2", "category": "firewall"}
        },
        {
            "name": "PCI-DSS: System Logging",
            "description": "Ensure system logging is configured on Juniper JunOS (PCI-DSS 10.1)",
            "category": "PCI-DSS",
            "vendor": VendorType.JUNIPER_JUNOS.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/configuration/system/syslog",
            "expected_value": None,
            "check_type": "exists",
            "framework": "PCI-DSS",
            "tags": {"pci": "10.1", "category": "logging"}
        },
        {
            "name": "NIST: Access Control",
            "description": "Verify access control implementation on Juniper JunOS (NIST AC-1)",
            "category": "NIST 800-53",
            "vendor": VendorType.JUNIPER_JUNOS.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/configuration/system/login",
            "expected_value": None,
            "check_type": "exists",
            "framework": "NIST",
            "tags": {"nist": "AC-1", "category": "access_control"}
        },
        {
            "name": "Best Practice: NTP Configuration",
            "description": "Ensure NTP is configured on Juniper JunOS for time synchronization",
            "category": "Best Practice",
            "vendor": VendorType.JUNIPER_JUNOS.value,
            "severity": SeverityLevel.MEDIUM.value,
            "xpath": "/configuration/system/ntp",
            "expected_value": None,
            "check_type": "exists",
            "framework": "Best Practice",
            "tags": {"category": "time_sync"}
        },
        {
            "name": "Best Practice: SNMP v3",
            "description": "Ensure SNMPv3 is configured on Juniper JunOS for secure monitoring",
            "category": "Best Practice",
            "vendor": VendorType.JUNIPER_JUNOS.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/configuration/snmp",
            "expected_value": "v3",
            "check_type": "contains",
            "framework": "Best Practice",
            "tags": {"category": "monitoring"}
        },
        {
            "name": "Best Practice: BGP Authentication",
            "description": "Ensure BGP authentication is configured on Juniper JunOS",
            "category": "Best Practice",
            "vendor": VendorType.JUNIPER_JUNOS.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/configuration/protocols/bgp",
            "expected_value": "authentication-key",
            "check_type": "contains",
            "framework": "Best Practice",
            "tags": {"category": "routing_security"}
        },
        {
            "name": "Best Practice: Firewall Filter Lo0 Protection",
            "description": "Ensure firewall filter is applied to loopback interface on Juniper JunOS for control plane protection",
            "category": "Best Practice",
            "vendor": VendorType.JUNIPER_JUNOS.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/configuration/interfaces/interface[name='lo0']/unit/family/inet/filter",
            "expected_value": None,
            "check_type": "exists",
            "framework": "Best Practice",
            "tags": {"category": "control_plane_security"}
        },

        # ====================================================================
        # Arista EOS Templates
        # ====================================================================
        {
            "name": "CIS: SSH Configuration",
            "description": "Ensure SSH is properly configured on Arista EOS (CIS Benchmark)",
            "category": "CIS Benchmark",
            "vendor": VendorType.ARISTA_EOS.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/system/ssh-server",
            "expected_value": "v2",
            "check_type": "contains",
            "framework": "CIS",
            "tags": {"cis": "5.2", "category": "access_control"}
        },
        {
            "name": "CIS: AAA Authentication",
            "description": "Ensure AAA authentication is enabled on Arista EOS (CIS Benchmark)",
            "category": "CIS Benchmark",
            "vendor": VendorType.ARISTA_EOS.value,
            "severity": SeverityLevel.CRITICAL.value,
            "xpath": "/system/aaa",
            "expected_value": None,
            "check_type": "exists",
            "framework": "CIS",
            "tags": {"cis": "4.1", "category": "authentication"}
        },
        {
            "name": "CIS: Login Banner",
            "description": "Ensure a login banner is configured on Arista EOS (CIS Benchmark)",
            "category": "CIS Benchmark",
            "vendor": VendorType.ARISTA_EOS.value,
            "severity": SeverityLevel.MEDIUM.value,
            "xpath": "/system/config/login-banner",
            "expected_value": None,
            "check_type": "exists",
            "framework": "CIS",
            "tags": {"cis": "1.1", "category": "general"}
        },
        {
            "name": "PCI-DSS: Encryption Configuration",
            "description": "Ensure strong encryption is configured on Arista EOS (PCI-DSS 8.2.1)",
            "category": "PCI-DSS",
            "vendor": VendorType.ARISTA_EOS.value,
            "severity": SeverityLevel.CRITICAL.value,
            "xpath": "/system/ssh-server",
            "expected_value": "aes256",
            "check_type": "contains",
            "framework": "PCI-DSS",
            "tags": {"pci": "8.2.1", "category": "encryption"}
        },
        {
            "name": "PCI-DSS: Logging Configuration",
            "description": "Ensure logging is properly configured on Arista EOS (PCI-DSS 10.1)",
            "category": "PCI-DSS",
            "vendor": VendorType.ARISTA_EOS.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/system/logging",
            "expected_value": None,
            "check_type": "exists",
            "framework": "PCI-DSS",
            "tags": {"pci": "10.1", "category": "logging"}
        },
        {
            "name": "NIST: Access Control Policy",
            "description": "Verify access control policy implementation on Arista EOS (NIST AC-1)",
            "category": "NIST 800-53",
            "vendor": VendorType.ARISTA_EOS.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/system/aaa",
            "expected_value": None,
            "check_type": "exists",
            "framework": "NIST",
            "tags": {"nist": "AC-1", "category": "access_control"}
        },
        {
            "name": "Best Practice: NTP Configuration",
            "description": "Ensure NTP is configured on Arista EOS for time synchronization",
            "category": "Best Practice",
            "vendor": VendorType.ARISTA_EOS.value,
            "severity": SeverityLevel.MEDIUM.value,
            "xpath": "/system/ntp",
            "expected_value": None,
            "check_type": "exists",
            "framework": "Best Practice",
            "tags": {"category": "time_sync"}
        },
        {
            "name": "Best Practice: SNMP v3",
            "description": "Ensure SNMPv3 is configured on Arista EOS for secure monitoring",
            "category": "Best Practice",
            "vendor": VendorType.ARISTA_EOS.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/system/snmp",
            "expected_value": "v3",
            "check_type": "contains",
            "framework": "Best Practice",
            "tags": {"category": "monitoring"}
        },
        {
            "name": "Best Practice: BGP Authentication",
            "description": "Ensure BGP neighbor authentication is configured on Arista EOS",
            "category": "Best Practice",
            "vendor": VendorType.ARISTA_EOS.value,
            "severity": SeverityLevel.HIGH.value,
            "xpath": "/network-instances/network-instance/protocols/protocol",
            "expected_value": "auth-password",
            "check_type": "contains",
            "framework": "Best Practice",
            "tags": {"category": "routing_security"}
        },
        {
            "name": "Best Practice: MLAG Configuration Check",
            "description": "Ensure MLAG is properly configured on Arista EOS for high availability",
            "category": "Best Practice",
            "vendor": VendorType.ARISTA_EOS.value,
            "severity": SeverityLevel.MEDIUM.value,
            "xpath": "/interfaces/interface",
            "expected_value": "mlag",
            "check_type": "contains",
            "framework": "Best Practice",
            "tags": {"category": "high_availability"}
        },
    ]

    @staticmethod
    def initialize_builtin_templates(db: Session) -> int:
        """
        Initialize built-in rule templates in the database

        Returns:
            Number of templates created
        """
        created_count = 0

        try:
            for template_data in RuleTemplateService.BUILTIN_TEMPLATES:
                # Prepare template data for DB - convert single vendor to vendors list
                db_data = template_data.copy()
                if "vendor" in db_data:
                    db_data["vendors"] = [db_data.pop("vendor")]

                # Create checks JSON from individual fields
                if "xpath" in db_data:
                    db_data["checks"] = [{
                        "xpath": db_data.pop("xpath"),
                        "expected_value": db_data.pop("expected_value", None),
                        "check_type": db_data.pop("check_type", "exists")
                    }]

                # Check if template already exists
                existing = db.query(RuleTemplateDB).filter(
                    RuleTemplateDB.name == db_data["name"]
                ).first()

                if not existing:
                    template = RuleTemplateDB(**db_data)
                    db.add(template)
                    created_count += 1
                    logger.debug(f"Created template: {template_data['name']}")

            db.commit()
            logger.info(f"Initialized {created_count} built-in rule templates")

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to initialize templates: {str(e)}")
            raise

        return created_count

    @staticmethod
    def get_all_templates(
        db: Session,
        vendor: Optional[str] = None,
        category: Optional[str] = None,
        framework: Optional[str] = None
    ) -> List[RuleTemplateDB]:
        """Get all rule templates with optional filtering"""
        query = db.query(RuleTemplateDB)

        if vendor:
            # vendors is a JSON array, so we need to check if it contains the vendor
            query = query.filter(RuleTemplateDB.vendors.contains([vendor]))

        if category:
            query = query.filter(RuleTemplateDB.category == category)

        if framework:
            query = query.filter(RuleTemplateDB.framework == framework)

        return query.all()

    @staticmethod
    def get_template_by_id(db: Session, template_id: int) -> Optional[RuleTemplateDB]:
        """Get a specific template by ID"""
        return db.query(RuleTemplateDB).filter(RuleTemplateDB.id == template_id).first()

    @staticmethod
    def create_custom_template(db: Session, template_data: Dict[str, Any]) -> RuleTemplateDB:
        """Create a custom rule template"""
        try:
            template = RuleTemplateDB(**template_data)
            db.add(template)
            db.commit()
            db.refresh(template)

            logger.info(f"Created custom template: {template.name}")
            return template

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create custom template: {str(e)}")
            raise

    @staticmethod
    def apply_template_to_rule(
        db: Session,
        template_id: int,
        custom_name: Optional[str] = None
    ) -> AuditRuleDB:
        """
        Create an audit rule from a template

        Args:
            db: Database session
            template_id: Template ID to apply
            custom_name: Optional custom name for the rule

        Returns:
            Created AuditRuleDB instance
        """
        template = RuleTemplateService.get_template_by_id(db, template_id)

        if not template:
            raise ValueError(f"Template {template_id} not found")

        try:
            # Create audit rule from template - use checks array directly
            rule_data = {
                "name": custom_name or template.name,
                "description": template.description,
                "severity": template.severity,
                "enabled": True,
                "vendors": template.vendors,
                "checks": template.checks,  # Use checks array directly
                "category": template.category
            }

            rule = AuditRuleDB(**rule_data)
            db.add(rule)
            db.commit()
            db.refresh(rule)

            logger.info(f"Applied template '{template.name}' to create rule '{rule.name}'")
            return rule

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to apply template: {str(e)}")
            raise

    @staticmethod
    def apply_compliance_framework(
        db: Session,
        framework: str,
        vendor: str
    ) -> List[AuditRuleDB]:
        """
        Apply all templates from a compliance framework for a specific vendor

        Args:
            db: Database session
            framework: Compliance framework (CIS, PCI-DSS, NIST, etc.)
            vendor: Vendor type

        Returns:
            List of created audit rules
        """
        templates = db.query(RuleTemplateDB).filter(
            and_(
                RuleTemplateDB.framework == framework,
                RuleTemplateDB.vendors.contains([vendor])
            )
        ).all()

        created_rules = []

        for template in templates:
            try:
                # Check if rule already exists
                existing_rule = db.query(AuditRuleDB).filter(
                    and_(
                        AuditRuleDB.name == template.name,
                        AuditRuleDB.vendors.contains([vendor])
                    )
                ).first()

                if not existing_rule:
                    rule = RuleTemplateService.apply_template_to_rule(db, template.id)
                    created_rules.append(rule)
                else:
                    logger.debug(f"Rule '{template.name}' already exists, skipping")

            except Exception as e:
                logger.error(f"Failed to apply template '{template.name}': {str(e)}")

        logger.info(
            f"Applied {len(created_rules)} rules from {framework} framework for {vendor}"
        )

        return created_rules

    @staticmethod
    def get_available_categories(db: Session) -> List[str]:
        """Get list of all available template categories"""
        from sqlalchemy import distinct

        categories = db.query(distinct(RuleTemplateDB.category)).all()
        return [c[0] for c in categories if c[0]]

    @staticmethod
    def get_available_frameworks(db: Session) -> List[str]:
        """Get list of all available compliance frameworks"""
        from sqlalchemy import distinct

        frameworks = db.query(distinct(RuleTemplateDB.framework)).all()
        return [f[0] for f in frameworks if f[0]]

    @staticmethod
    def delete_template(db: Session, template_id: int) -> bool:
        """Delete a custom template"""
        try:
            template = db.query(RuleTemplateDB).filter(RuleTemplateDB.id == template_id).first()

            if not template:
                return False

            db.delete(template)
            db.commit()

            logger.info(f"Deleted template: {template.name}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete template: {str(e)}")
            return False
