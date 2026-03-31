"""
MCP Protocol Routes
Implements the MCP (Model Context Protocol) server endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from shared.database import get_db
from shared.deps import get_current_user
from shared.logger import setup_logger
from models.schemas import MCPConnectionCreate, MCPToolCall

logger = setup_logger(__name__)
router = APIRouter(prefix="/mcp")


# ============================================================================
# MCP Server Endpoints (NAP as MCP Server)
# ============================================================================

@router.post("/initialize")
async def mcp_initialize(request: dict = None):
    """MCP protocol initialization"""
    from services.mcp_server import MCP_TOOLS, MCP_RESOURCES, MCP_PROMPTS

    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {"listChanged": False},
            "resources": {"subscribe": False, "listChanged": False},
            "prompts": {"listChanged": False},
        },
        "serverInfo": {
            "name": "NAP-MCP-Server",
            "version": "1.0.0",
        },
    }


@router.get("/tools")
async def list_tools():
    """List available MCP tools"""
    from services.mcp_server import MCP_TOOLS
    return {"tools": MCP_TOOLS}


@router.post("/tools/call")
async def call_tool(request: MCPToolCall):
    """Execute an MCP tool"""
    from services.mcp_server import execute_tool, MCP_TOOLS

    # Validate tool exists
    tool_names = [t["name"] for t in MCP_TOOLS]
    if request.tool_name not in tool_names:
        raise HTTPException(status_code=404, detail=f"Tool not found: {request.tool_name}")

    result = await execute_tool(request.tool_name, request.arguments)

    return {
        "content": [
            {
                "type": "text",
                "text": result if isinstance(result, str) else str(result),
            }
        ],
        "isError": isinstance(result, dict) and "error" in result,
    }


@router.get("/resources")
async def list_resources():
    """List available MCP resources"""
    from services.mcp_server import MCP_RESOURCES
    return {"resources": MCP_RESOURCES}


@router.post("/resources/read")
async def read_resource(request: dict):
    """Read an MCP resource"""
    from services.mcp_server import read_resource as mcp_read

    uri = request.get("uri")
    if not uri:
        raise HTTPException(status_code=400, detail="URI required")

    result = await mcp_read(uri)

    return {
        "contents": [
            {
                "uri": uri,
                "mimeType": "application/json",
                "text": str(result),
            }
        ]
    }


@router.get("/prompts")
async def list_prompts():
    """List available MCP prompts"""
    from services.mcp_server import MCP_PROMPTS
    return {"prompts": MCP_PROMPTS}


@router.post("/prompts/get")
async def get_prompt(request: dict):
    """Get an MCP prompt with arguments"""
    from services.mcp_server import get_prompt as mcp_get_prompt

    name = request.get("name")
    arguments = request.get("arguments", {})

    if not name:
        raise HTTPException(status_code=400, detail="Prompt name required")

    messages = await mcp_get_prompt(name, arguments)
    return {"messages": messages}


# ============================================================================
# MCP Hub Endpoints (NAP as MCP Client)
# ============================================================================

@router.get("/hub/connections")
async def list_mcp_connections(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all registered MCP server connections"""
    from services.mcp_hub import mcp_hub
    return await mcp_hub.list_connections(db)


@router.post("/hub/connections")
async def register_mcp_connection(
    connection: MCPConnectionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Register a new external MCP server connection"""
    from services.mcp_hub import mcp_hub
    try:
        result = await mcp_hub.register_connection(
            db, connection.name, connection.server_url,
            connection.transport, connection.auth_config,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/hub/connections/{connection_id}")
async def remove_mcp_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Remove an MCP server connection"""
    from services.mcp_hub import mcp_hub
    removed = await mcp_hub.remove_connection(db, connection_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Connection not found")
    return {"status": "removed"}


@router.post("/hub/connections/{connection_id}/test")
async def test_mcp_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Test an MCP server connection"""
    from services.mcp_hub import mcp_hub
    return await mcp_hub.test_connection(db, connection_id)


@router.get("/hub/connections/{connection_id}/tools")
async def get_connection_tools(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get available tools from an external MCP server"""
    from services.mcp_hub import mcp_hub
    return await mcp_hub.get_tools(db, connection_id)


@router.post("/hub/connections/{connection_id}/tools/call")
async def call_external_tool(
    connection_id: int,
    request: MCPToolCall,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Call a tool on an external MCP server"""
    from services.mcp_hub import mcp_hub
    return await mcp_hub.call_tool(db, connection_id, request.tool_name, request.arguments)
