
# ============================================================================
# services/rule_service.py
# ============================================================================

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from models.rule import AuditRule, AuditRuleCreate, AuditRuleUpdate
from db_models import AuditRuleDB
from shared.logger import setup_logger
from shared.exceptions import RuleNotFoundError
from shared.validators import validate_xml, validate_xpath

logger = setup_logger(__name__)

class RuleService:
    """Service for audit rule management operations with database persistence"""

    def __init__(self):
        pass

    def get_all_rules(self, db: Session) -> List[AuditRule]:
        """Get all rules"""
        db_rules = db.query(AuditRuleDB).all()
        return [self._to_pydantic(r) for r in db_rules]

    def get_rule_by_id(self, db: Session, rule_id: int) -> Optional[AuditRule]:
        """Get rule by ID"""
        db_rule = db.query(AuditRuleDB).filter(AuditRuleDB.id == rule_id).first()
        return self._to_pydantic(db_rule) if db_rule else None

    def get_enabled_rules(self, db: Session) -> List[AuditRule]:
        """Get all enabled rules"""
        db_rules = db.query(AuditRuleDB).filter(AuditRuleDB.enabled == True).all()
        return [self._to_pydantic(r) for r in db_rules]

    def get_rules_by_category(self, db: Session, category: str) -> List[AuditRule]:
        """Get rules filtered by category"""
        db_rules = db.query(AuditRuleDB).filter(AuditRuleDB.category == category).all()
        return [self._to_pydantic(r) for r in db_rules]

    def get_rules_by_vendor(self, db: Session, vendor: str) -> List[AuditRule]:
        """Get rules applicable to a specific vendor"""
        db_rules = db.query(AuditRuleDB).all()
        matching_rules = []
        for db_rule in db_rules:
            if vendor in db_rule.vendors:
                matching_rules.append(self._to_pydantic(db_rule))
        return matching_rules

    def create_rule(self, db: Session, rule_create: AuditRuleCreate) -> AuditRule:
        """Create a new audit rule"""
        # Validate checks
        for check in rule_create.checks:
            if check.filter_xml and not validate_xml(check.filter_xml):
                raise ValueError(f"Invalid XML in check: {check.name}")
            if check.xpath and not validate_xpath(check.xpath):
                raise ValueError(f"Invalid XPath in check: {check.name}")

        # Convert checks to dict format for JSON storage
        checks_dict = [check.dict() for check in rule_create.checks]

        # Create rule in database
        db_rule = AuditRuleDB(
            name=rule_create.name,
            description=rule_create.description,
            severity=rule_create.severity,
            category=rule_create.category,
            enabled=rule_create.enabled,
            vendors=[v.value if hasattr(v, 'value') else v for v in rule_create.vendors],
            checks=checks_dict
        )

        db.add(db_rule)
        db.commit()
        db.refresh(db_rule)

        logger.info(f"Created rule: {db_rule.name} (ID: {db_rule.id})")

        return self._to_pydantic(db_rule)

    def update_rule(self, db: Session, rule_id: int, rule_update: AuditRuleUpdate) -> AuditRule:
        """Update an existing rule"""
        db_rule = db.query(AuditRuleDB).filter(AuditRuleDB.id == rule_id).first()
        if not db_rule:
            raise RuleNotFoundError(f"Rule with ID {rule_id} not found")

        # Validate checks if provided
        if rule_update.checks:
            for check in rule_update.checks:
                if check.filter_xml and not validate_xml(check.filter_xml):
                    raise ValueError(f"Invalid XML in check: {check.name}")
                if check.xpath and not validate_xpath(check.xpath):
                    raise ValueError(f"Invalid XPath in check: {check.name}")

        # Update fields
        update_data = rule_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == "checks" and value:
                # Handle both RuleCheck objects and dicts
                from models.rule import RuleCheck
                checks = [RuleCheck(**check) if isinstance(check, dict) else check for check in value]
                setattr(db_rule, field, [check.dict() for check in checks])
            elif field == "vendors" and value:
                setattr(db_rule, field, [v.value if hasattr(v, 'value') else v for v in value])
            else:
                setattr(db_rule, field, value)

        db_rule.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_rule)

        logger.info(f"Updated rule: {db_rule.name} (ID: {db_rule.id})")
        return self._to_pydantic(db_rule)

    def delete_rule(self, db: Session, rule_id: int) -> bool:
        """Delete a rule"""
        db_rule = db.query(AuditRuleDB).filter(AuditRuleDB.id == rule_id).first()
        if not db_rule:
            raise RuleNotFoundError(f"Rule with ID {rule_id} not found")

        db.delete(db_rule)
        db.commit()

        logger.info(f"Deleted rule ID: {rule_id}")
        return True

    def toggle_rule(self, db: Session, rule_id: int) -> AuditRule:
        """Toggle rule enabled/disabled"""
        db_rule = db.query(AuditRuleDB).filter(AuditRuleDB.id == rule_id).first()
        if not db_rule:
            raise RuleNotFoundError(f"Rule with ID {rule_id} not found")

        db_rule.enabled = not db_rule.enabled
        db_rule.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_rule)

        logger.info(f"Toggled rule {db_rule.name} to {'enabled' if db_rule.enabled else 'disabled'}")
        return self._to_pydantic(db_rule)

    def _to_pydantic(self, db_rule: AuditRuleDB) -> AuditRule:
        """Convert SQLAlchemy model to Pydantic model"""
        from models.rule import RuleCheck
        from models.enums import VendorType

        # Convert checks from dict to RuleCheck objects
        checks = [RuleCheck(**check) for check in db_rule.checks]

        # Convert vendors from strings to VendorType enums
        vendors = [VendorType(v) if isinstance(v, str) else v for v in db_rule.vendors]

        return AuditRule(
            id=db_rule.id,
            name=db_rule.name,
            description=db_rule.description,
            severity=db_rule.severity,
            category=db_rule.category,
            enabled=db_rule.enabled,
            vendors=vendors,
            checks=checks,
            created_at=db_rule.created_at.isoformat() if db_rule.created_at else None,
            updated_at=db_rule.updated_at.isoformat() if db_rule.updated_at else None
        )
