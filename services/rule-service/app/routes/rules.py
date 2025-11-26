

# ============================================================================
# api/routes/rules.py
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from shared.deps import get_db, require_admin_or_operator, require_any_authenticated
from models.rule import AuditRule, AuditRuleCreate, AuditRuleUpdate
from services.rule_service import RuleService
from shared.exceptions import RuleNotFoundError

router = APIRouter()

rule_service = RuleService()

@router.get("/", response_model=List[AuditRule])
async def get_all_rules(db: Session = Depends(get_db)):
    """Get all audit rules"""
    return rule_service.get_all_rules(db)

@router.get("/{rule_id}", response_model=AuditRule)
async def get_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get a specific rule by ID"""
    rule = rule_service.get_rule_by_id(db, rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule with ID {rule_id} not found"
        )
    return rule

@router.post("/", response_model=AuditRule, status_code=status.HTTP_201_CREATED)
async def create_rule(
    rule_create: AuditRuleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """Create a new audit rule (requires admin or operator role)"""
    try:
        return rule_service.create_rule(db, rule_create)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.put("/{rule_id}", response_model=AuditRule)
async def update_rule(
    rule_id: int,
    rule_update: AuditRuleUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """Update an existing rule (requires admin or operator role)"""
    try:
        return rule_service.update_rule(db, rule_id, rule_update)
    except RuleNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """Delete a rule (requires admin or operator role)"""
    try:
        rule_service.delete_rule(db, rule_id)
    except RuleNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.put("/{rule_id}/toggle", response_model=AuditRule)
async def toggle_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """Toggle rule enabled/disabled (requires admin or operator role)"""
    try:
        return rule_service.toggle_rule(db, rule_id)
    except RuleNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

@router.get("/category/{category}", response_model=List[AuditRule])
async def get_rules_by_category(category: str, db: Session = Depends(get_db)):
    """Get rules filtered by category"""
    return rule_service.get_rules_by_category(db, category)

@router.get("/vendor/{vendor}", response_model=List[AuditRule])
async def get_rules_by_vendor(vendor: str, db: Session = Depends(get_db)):
    """Get rules applicable to a specific vendor"""
    return rule_service.get_rules_by_vendor(db, vendor)

