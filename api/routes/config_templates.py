"""
Configuration Templates API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from api.deps import get_db, require_admin_or_operator
from models.config_templates import ConfigTemplate, TemplateDeployment, TemplateCategory
from services.template_deployment_service import TemplateDeploymentService
from utils.logger import setup_logger

router = APIRouter(prefix="/config-templates", tags=["config-templates"])
logger = setup_logger(__name__)


# Pydantic Models
class TemplateVariable(BaseModel):
    name: str
    type: str
    description: str
    default: Optional[str] = None
    required: bool = True


class ConfigTemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    vendor: str
    template_content: str
    xpath: Optional[str] = None  # For Nokia SROS templates
    variables: Optional[List[dict]] = []
    is_builtin: bool = False


class ConfigTemplateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    category: str
    vendor: str
    template_content: str
    xpath: Optional[str]
    variables: Optional[List[dict]]
    is_builtin: bool
    is_active: bool
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class TemplateDeployRequest(BaseModel):
    template_id: int
    device_id: int
    variables: dict
    dry_run: bool = False


class TemplateBulkDeployRequest(BaseModel):
    template_id: int
    device_ids: List[int]
    variables: dict
    dry_run: bool = False


class TemplateGroupDeployRequest(BaseModel):
    template_id: int
    group_ids: List[int]
    variables: dict
    dry_run: bool = False


class DeploymentResponse(BaseModel):
    success: bool
    device_id: int
    device_name: Optional[str] = None
    deployment_id: Optional[int] = None
    status: str
    error: Optional[str] = None
    backup_id: Optional[int] = None
    generated_config: Optional[str] = None
    dry_run: Optional[bool] = False


class BulkDeploymentResponse(BaseModel):
    success: bool
    dry_run: bool
    total_devices: int
    successful: int
    failed: int
    results: List[dict]


# Initialize built-in templates
@router.post("/initialize")
def initialize_builtin_templates(db: Session = Depends(get_db)):
    """Initialize built-in configuration templates"""
    builtin_templates = [
        # Cisco SSH Security Template
        {
            "name": "Cisco SSH v2 Security",
            "description": "Configure SSH version 2 only with strong encryption",
            "category": "security",
            "vendor": "cisco",
            "template_content": """ssh server v2
ssh timeout {{ssh_timeout}}
crypto key generate rsa general-keys modulus {{key_size}}""",
            "variables": [
                {"name": "ssh_timeout", "type": "number", "description": "SSH timeout in seconds", "default": "120", "required": True},
                {"name": "key_size", "type": "number", "description": "RSA key size", "default": "2048", "required": True}
            ],
            "is_builtin": True
        },

        # Cisco AAA Template
        {
            "name": "Cisco AAA Configuration",
            "description": "Basic AAA authentication configuration",
            "category": "security",
            "vendor": "cisco",
            "template_content": """aaa authentication login default group {{auth_group}} local
aaa authentication enable default group {{auth_group}} enable
aaa authorization exec default group {{auth_group}} local
aaa accounting exec default start-stop group {{auth_group}}""",
            "variables": [
                {"name": "auth_group", "type": "string", "description": "Authentication server group (tacacs+/radius)", "default": "tacacs+", "required": True}
            ],
            "is_builtin": True
        },

        # Cisco Login Banner
        {
            "name": "Cisco Login Banner",
            "description": "Configure login banner for security compliance",
            "category": "security",
            "vendor": "cisco",
            "template_content": """banner login {{banner_delimiter}}
{{banner_text}}
{{banner_delimiter}}""",
            "variables": [
                {"name": "banner_delimiter", "type": "string", "description": "Banner delimiter character", "default": "^C", "required": True},
                {"name": "banner_text", "type": "text", "description": "Banner text content", "default": "Authorized access only. All activities are monitored and logged.", "required": True}
            ],
            "is_builtin": True
        },

        # Nokia SSH Configuration
        {
            "name": "Nokia SROS SSH Configuration",
            "description": "Enable and configure SSH on Nokia SROS",
            "category": "security",
            "vendor": "nokia",
            "template_content": """{"admin-state": "enable"}""",
            "xpath": "/configure/system/security/ssh/server",
            "variables": [],
            "is_builtin": True
        },

        # Nokia User Authentication
        {
            "name": "Nokia Local User Configuration",
            "description": "Create local user with authentication",
            "category": "security",
            "vendor": "nokia",
            "template_content": """/configure system security
    user-params
        local-user
            user "{{username}}"
                password "{{password}}"
                access console
                console member "{{access_group}}"
            exit
        exit
    exit
exit""",
            "variables": [
                {"name": "username", "type": "string", "description": "Username", "required": True},
                {"name": "password", "type": "password", "description": "User password (will be hashed)", "required": True},
                {"name": "access_group", "type": "string", "description": "Access group", "default": "administrative", "required": True}
            ],
            "is_builtin": True
        },

        # Nokia NTP Configuration
        {
            "name": "Nokia NTP Configuration",
            "description": "Configure NTP servers for time synchronization",
            "category": "system",
            "vendor": "nokia",
            "template_content": """{"admin-state": "enable", "server": {"{{ntp_server}}": {"admin-state": "enable"}}}""",
            "xpath": "/configure/system/time/ntp",
            "variables": [
                {"name": "ntp_server", "type": "string", "description": "NTP server IP address", "required": True}
            ],
            "is_builtin": True
        },

        # Cisco SNMP v3 Configuration
        {
            "name": "Cisco SNMPv3 Configuration",
            "description": "Configure SNMP v3 with authentication and encryption",
            "category": "system",
            "vendor": "cisco",
            "template_content": """snmp-server group {{group_name}} v3 priv
snmp-server user {{username}} {{group_name}} v3 auth sha {{auth_password}} priv aes 128 {{priv_password}}
snmp-server host {{nms_host}} version 3 priv {{username}}""",
            "variables": [
                {"name": "group_name", "type": "string", "description": "SNMP group name", "default": "network-admin", "required": True},
                {"name": "username", "type": "string", "description": "SNMP username", "required": True},
                {"name": "auth_password", "type": "password", "description": "Authentication password", "required": True},
                {"name": "priv_password", "type": "password", "description": "Privacy password", "required": True},
                {"name": "nms_host", "type": "string", "description": "NMS/Management host IP", "required": True}
            ],
            "is_builtin": True
        },

        # Cisco Interface Configuration
        {
            "name": "Cisco Interface Configuration",
            "description": "Basic interface configuration template",
            "category": "interfaces",
            "vendor": "cisco",
            "template_content": """interface {{interface_name}}
 description {{description}}
 ipv4 address {{ip_address}} {{subnet_mask}}
 no shutdown""",
            "variables": [
                {"name": "interface_name", "type": "string", "description": "Interface name (e.g., GigabitEthernet0/0/0/0)", "required": True},
                {"name": "description", "type": "string", "description": "Interface description", "required": True},
                {"name": "ip_address", "type": "string", "description": "IP address", "required": True},
                {"name": "subnet_mask", "type": "string", "description": "Subnet mask", "required": True}
            ],
            "is_builtin": True
        },
    ]

    added_count = 0
    for template_data in builtin_templates:
        # Check if template already exists
        existing = db.query(ConfigTemplate).filter(
            ConfigTemplate.name == template_data["name"],
            ConfigTemplate.is_builtin == True
        ).first()

        if not existing:
            template = ConfigTemplate(**template_data)
            db.add(template)
            added_count += 1
            logger.info(f"Added built-in template: {template_data['name']}")

    db.commit()

    return {
        "message": f"Initialized {added_count} built-in templates",
        "total_builtin": added_count
    }


@router.get("/", response_model=List[ConfigTemplateResponse])
def list_templates(
    category: Optional[str] = None,
    vendor: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all configuration templates"""
    query = db.query(ConfigTemplate).filter(ConfigTemplate.is_active == True)

    if category:
        query = query.filter(ConfigTemplate.category == category)
    if vendor:
        query = query.filter(ConfigTemplate.vendor == vendor)

    templates = query.order_by(ConfigTemplate.is_builtin.desc(), ConfigTemplate.name).all()
    return templates


@router.post("/", response_model=ConfigTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    template_data: ConfigTemplateCreate,
    db: Session = Depends(get_db)
):
    """Create a new configuration template"""
    template = ConfigTemplate(**template_data.dict())
    db.add(template)
    db.commit()
    db.refresh(template)

    logger.info(f"Created template: {template.name}")
    return template


@router.get("/{template_id}", response_model=ConfigTemplateResponse)
def get_template(template_id: int, db: Session = Depends(get_db)):
    """Get a specific template by ID"""
    template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.put("/{template_id}", response_model=ConfigTemplateResponse)
def update_template(
    template_id: int,
    template_data: ConfigTemplateCreate,
    db: Session = Depends(get_db)
):
    """Update an existing template"""
    template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.is_builtin:
        raise HTTPException(status_code=400, detail="Cannot modify built-in templates")

    for key, value in template_data.dict(exclude_unset=True).items():
        setattr(template, key, value)

    db.commit()
    db.refresh(template)

    logger.info(f"Updated template: {template.name}")
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a template (soft delete)"""
    template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.is_builtin:
        raise HTTPException(status_code=400, detail="Cannot delete built-in templates")

    template.is_active = False
    db.commit()

    logger.info(f"Deleted template: {template.name}")
    return None


@router.post("/deploy")
async def deploy_template(
    deploy_request: TemplateDeployRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """
    Deploy a template to a single device

    **Requires**: admin or operator role

    **Process**:
    1. Validates template and device compatibility
    2. Renders template with provided variables
    3. Creates backup before deployment
    4. Applies configuration to device
    5. Records deployment status

    **Dry Run Mode**:
    - Set dry_run=True to validate without applying
    - Returns rendered configuration for review
    """
    try:
        result = await TemplateDeploymentService.deploy_to_device(
            db=db,
            template_id=deploy_request.template_id,
            device_id=deploy_request.device_id,
            variables=deploy_request.variables,
            dry_run=deploy_request.dry_run,
            deployed_by=current_user.get('username', 'unknown')
        )

        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('error', 'Deployment failed')
            )

        return result

    except Exception as e:
        logger.error(f"Template deployment error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deployment failed: {str(e)}"
        )


@router.post("/deploy/bulk", response_model=BulkDeploymentResponse)
async def deploy_template_bulk(
    deploy_request: TemplateBulkDeployRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """
    Deploy a template to multiple devices at once

    **Requires**: admin or operator role

    **Process**:
    1. Validates template compatibility with all devices
    2. Renders template with provided variables (same for all devices)
    3. Creates backups before deployment
    4. Applies configuration to each device
    5. Returns deployment results for all devices

    **Dry Run Mode**:
    - Set dry_run=True to validate without applying
    - Useful for testing template on multiple devices
    """
    try:
        result = await TemplateDeploymentService.deploy_to_devices(
            db=db,
            template_id=deploy_request.template_id,
            device_ids=deploy_request.device_ids,
            variables=deploy_request.variables,
            dry_run=deploy_request.dry_run,
            deployed_by=current_user.get('username', 'unknown')
        )

        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deployment failed for all devices"
            )

        return result

    except Exception as e:
        logger.error(f"Bulk template deployment error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk deployment failed: {str(e)}"
        )


@router.post("/deploy/groups", response_model=BulkDeploymentResponse)
async def deploy_template_to_groups(
    deploy_request: TemplateGroupDeployRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin_or_operator)
):
    """
    Deploy a template to multiple device groups at once

    **Requires**: admin or operator role

    **Process**:
    1. Collects all devices from specified groups
    2. Removes duplicates (if a device is in multiple groups)
    3. Validates template compatibility with all devices
    4. Renders template with provided variables (same for all devices)
    5. Creates backups before deployment
    6. Applies configuration to each device
    7. Returns deployment results for all devices

    **Dry Run Mode**:
    - Set dry_run=True to validate without applying
    - Useful for testing template on entire device groups
    """
    try:
        result = await TemplateDeploymentService.deploy_to_device_groups(
            db=db,
            template_id=deploy_request.template_id,
            group_ids=deploy_request.group_ids,
            variables=deploy_request.variables,
            dry_run=deploy_request.dry_run,
            deployed_by=current_user.get('username', 'unknown')
        )

        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get('error', 'Deployment failed for all devices')
            )

        return result

    except Exception as e:
        logger.error(f"Group template deployment error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Group deployment failed: {str(e)}"
        )


@router.post("/preview")
def preview_template(
    template_id: int,
    variables: dict,
    db: Session = Depends(get_db)
):
    """
    Preview rendered template without deploying

    Renders the template with provided variables to preview the final configuration
    """
    template = db.query(ConfigTemplate).filter(ConfigTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Validate variables
    is_valid, error_msg = TemplateDeploymentService.validate_variables(template, variables)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    # Render template
    try:
        rendered = TemplateDeploymentService.render_template(template.template_content, variables)
        return {
            "template_id": template_id,
            "template_name": template.name,
            "rendered_config": rendered,
            "variables_used": variables
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/deployments/device/{device_id}")
def get_device_deployments(
    device_id: int,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get deployment history for a specific device"""
    deployments = db.query(TemplateDeployment).filter(
        TemplateDeployment.device_id == device_id
    ).order_by(TemplateDeployment.created_at.desc()).limit(limit).all()

    results = []
    for deployment in deployments:
        template = db.query(ConfigTemplate).filter(
            ConfigTemplate.id == deployment.template_id
        ).first()

        results.append({
            "deployment_id": deployment.id,
            "template_id": deployment.template_id,
            "template_name": template.name if template else "Unknown",
            "status": deployment.status,
            "deployed_at": deployment.deployed_at,
            "deployed_by": deployment.deployed_by,
            "error_message": deployment.error_message,
            "backup_id": deployment.backup_id
        })

    return {
        "device_id": device_id,
        "total_deployments": len(results),
        "deployments": results
    }


@router.get("/deployments/{deployment_id}")
def get_deployment_details(
    deployment_id: int,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific deployment"""
    deployment = db.query(TemplateDeployment).filter(
        TemplateDeployment.id == deployment_id
    ).first()

    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")

    template = db.query(ConfigTemplate).filter(
        ConfigTemplate.id == deployment.template_id
    ).first()

    return {
        "deployment_id": deployment.id,
        "template_id": deployment.template_id,
        "template_name": template.name if template else "Unknown",
        "device_id": deployment.device_id,
        "status": deployment.status,
        "variables_used": deployment.variables_used,
        "generated_config": deployment.generated_config,
        "deployed_at": deployment.deployed_at,
        "deployed_by": deployment.deployed_by,
        "error_message": deployment.error_message,
        "backup_id": deployment.backup_id,
        "rollback_at": deployment.rollback_at
    }


@router.get("/categories/list")
def list_categories(db: Session = Depends(get_db)):
    """List all available template categories"""
    from sqlalchemy import distinct

    categories = db.query(distinct(ConfigTemplate.category)).filter(
        ConfigTemplate.is_active == True
    ).all()

    return {
        "categories": [cat[0] for cat in categories] if categories else [
            "security", "qos", "routing", "interfaces", "system", "monitoring"
        ]
    }
