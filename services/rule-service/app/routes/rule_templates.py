# ============================================================================
# api/routes/rule_templates.py
# ============================================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from api.deps import get_db
from db_models import RuleTemplateDB, AuditRuleDB
from services.rule_template_service import RuleTemplateService

router = APIRouter(prefix="/rule-templates", tags=["rule-templates"])


# ============================================================================
# Pydantic Models
# ============================================================================

class RuleTemplateResponse(BaseModel):
    id: int
    name: str
    description: str
    category: str
    vendors: List[str]
    severity: str
    checks: List[Dict[str, Any]]
    framework: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class RuleTemplateCreate(BaseModel):
    name: str
    description: str
    category: str
    vendors: List[str]
    severity: str
    checks: List[Dict[str, Any]]
    framework: Optional[str] = None
    tags: Optional[Dict[str, Any]] = None


class ApplyTemplateRequest(BaseModel):
    template_id: int
    custom_name: Optional[str] = None


class ApplyFrameworkRequest(BaseModel):
    framework: str
    vendor: str


class RuleResponse(BaseModel):
    id: int
    name: str
    description: str
    severity: str
    enabled: bool
    vendors: List[str]
    category: Optional[str]

    class Config:
        from_attributes = True


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/initialize")
async def initialize_builtin_templates(db: Session = Depends(get_db)):
    """Initialize built-in rule templates (CIS, PCI-DSS, NIST, Best Practices)"""
    try:
        count = RuleTemplateService.initialize_builtin_templates(db)
        return {
            "message": f"Initialized {count} built-in templates",
            "templates_created": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[RuleTemplateResponse])
async def list_templates(
    vendor: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    framework: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List all rule templates with optional filtering"""
    templates = RuleTemplateService.get_all_templates(
        db, vendor=vendor, category=category, framework=framework
    )
    return templates


@router.get("/categories")
async def get_categories(db: Session = Depends(get_db)):
    """Get list of all available template categories"""
    categories = RuleTemplateService.get_available_categories(db)
    return {"categories": categories}


@router.get("/frameworks")
async def get_frameworks(db: Session = Depends(get_db)):
    """Get list of all available compliance frameworks"""
    frameworks = RuleTemplateService.get_available_frameworks(db)
    return {"frameworks": frameworks}


@router.get("/{template_id}", response_model=RuleTemplateResponse)
async def get_template(template_id: int, db: Session = Depends(get_db)):
    """Get a specific rule template by ID"""
    template = RuleTemplateService.get_template_by_id(db, template_id)

    if not template:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    return template


@router.post("/", response_model=RuleTemplateResponse)
async def create_template(
    template: RuleTemplateCreate,
    db: Session = Depends(get_db)
):
    """Create a custom rule template"""
    try:
        created_template = RuleTemplateService.create_custom_template(
            db, template.dict()
        )
        return created_template
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply", response_model=RuleResponse)
async def apply_template(
    request: ApplyTemplateRequest,
    db: Session = Depends(get_db)
):
    """Apply a template to create an audit rule"""
    try:
        rule = RuleTemplateService.apply_template_to_rule(
            db, request.template_id, request.custom_name
        )
        return rule
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/apply-framework", response_model=List[RuleResponse])
async def apply_framework(
    request: ApplyFrameworkRequest,
    db: Session = Depends(get_db)
):
    """Apply all templates from a compliance framework for a vendor"""
    try:
        rules = RuleTemplateService.apply_compliance_framework(
            db, request.framework, request.vendor
        )
        return rules
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{template_id}")
async def delete_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a custom rule template"""
    success = RuleTemplateService.delete_template(db, template_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Template {template_id} not found")

    return {"message": f"Template {template_id} deleted successfully"}


@router.get("/vendor/{vendor}")
async def get_templates_by_vendor(
    vendor: str,
    db: Session = Depends(get_db)
):
    """Get all templates for a specific vendor with grouping by framework"""
    templates = RuleTemplateService.get_all_templates(db, vendor=vendor)

    # Group by compliance framework
    grouped = {}
    for template in templates:
        framework = template.compliance_framework
        if framework not in grouped:
            grouped[framework] = []

        grouped[framework].append({
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "severity": template.severity,
            "category": template.category
        })

    return {
        "vendor": vendor,
        "total_templates": len(templates),
        "by_framework": grouped
    }
