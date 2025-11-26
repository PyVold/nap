# ============================================================================
# services/rule_template_service.py
# ============================================================================

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from db_models import RuleTemplateDB, AuditRuleDB
from models.enums import VendorType, SeverityLevel
from utils.logger import setup_logger

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
