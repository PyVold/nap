"""
MCP Integration Hub
Manages connections to external MCP servers and routes tool calls.
"""

import json
import httpx
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from shared.logger import setup_logger

logger = setup_logger(__name__)


class MCPIntegrationHub:
    """Manages external MCP server connections and tool routing"""

    def __init__(self):
        self._connections: Dict[int, dict] = {}  # id -> connection info

    async def register_connection(self, db: Session, name: str, server_url: str,
                                   transport: str = "sse", auth_config: Optional[dict] = None) -> dict:
        """Register a new MCP server connection"""
        from shared.db_models import MCPConnectionDB

        # Test connectivity
        capabilities = await self._discover_capabilities(server_url, transport)

        connection = MCPConnectionDB(
            name=name,
            server_url=server_url,
            transport=transport,
            auth_config=json.dumps(auth_config) if auth_config else None,
            capabilities=capabilities,
            status="connected" if capabilities else "unreachable",
        )
        db.add(connection)
        db.commit()
        db.refresh(connection)

        return {
            "id": connection.id,
            "name": connection.name,
            "status": connection.status,
            "capabilities": capabilities,
        }

    async def list_connections(self, db: Session) -> List[dict]:
        """List all registered MCP connections"""
        from shared.db_models import MCPConnectionDB
        connections = db.query(MCPConnectionDB).all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "server_url": c.server_url,
                "transport": c.transport,
                "status": c.status,
                "capabilities": c.capabilities,
                "last_connected": c.last_connected.isoformat() if c.last_connected else None,
            }
            for c in connections
        ]

    async def remove_connection(self, db: Session, connection_id: int) -> bool:
        """Remove an MCP connection"""
        from shared.db_models import MCPConnectionDB
        connection = db.query(MCPConnectionDB).filter(MCPConnectionDB.id == connection_id).first()
        if connection:
            db.delete(connection)
            db.commit()
            return True
        return False

    async def test_connection(self, db: Session, connection_id: int) -> dict:
        """Test an MCP server connection"""
        from shared.db_models import MCPConnectionDB
        connection = db.query(MCPConnectionDB).filter(MCPConnectionDB.id == connection_id).first()
        if not connection:
            return {"status": "error", "message": "Connection not found"}

        capabilities = await self._discover_capabilities(connection.server_url, connection.transport)
        if capabilities:
            connection.status = "connected"
            connection.capabilities = capabilities
            from datetime import datetime
            connection.last_connected = datetime.utcnow()
        else:
            connection.status = "unreachable"

        db.commit()
        return {"status": connection.status, "capabilities": capabilities}

    async def call_tool(self, db: Session, connection_id: int, tool_name: str, arguments: dict) -> Any:
        """Call a tool on an external MCP server"""
        from shared.db_models import MCPConnectionDB
        connection = db.query(MCPConnectionDB).filter(MCPConnectionDB.id == connection_id).first()
        if not connection:
            return {"error": "Connection not found"}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # SSE transport - POST to the server's tool endpoint
                response = await client.post(
                    f"{connection.server_url}/mcp/tools/call",
                    json={
                        "name": tool_name,
                        "arguments": arguments,
                    },
                    headers=self._get_auth_headers(connection),
                )
                if response.status_code == 200:
                    return response.json()
                return {"error": f"Tool call failed: {response.status_code}"}
        except Exception as e:
            logger.error(f"Error calling tool {tool_name} on {connection.name}: {e}")
            return {"error": str(e)}

    async def get_tools(self, db: Session, connection_id: int) -> List[dict]:
        """Get available tools from an external MCP server"""
        from shared.db_models import MCPConnectionDB
        connection = db.query(MCPConnectionDB).filter(MCPConnectionDB.id == connection_id).first()
        if not connection or not connection.capabilities:
            return []
        return connection.capabilities.get("tools", [])

    async def _discover_capabilities(self, server_url: str, transport: str) -> Optional[dict]:
        """Discover capabilities of an MCP server"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try MCP initialize endpoint
                response = await client.post(
                    f"{server_url}/mcp/initialize",
                    json={
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "NAP-MCP-Hub", "version": "1.0.0"},
                    },
                )
                if response.status_code == 200:
                    return response.json()

                # Fallback: try health endpoint
                response = await client.get(f"{server_url}/health")
                if response.status_code == 200:
                    return {"status": "connected", "health": response.json()}

                return None
        except Exception as e:
            logger.warning(f"Cannot discover capabilities at {server_url}: {e}")
            return None

    def _get_auth_headers(self, connection) -> dict:
        """Build auth headers for MCP server"""
        headers = {"Content-Type": "application/json"}
        if connection.auth_config:
            try:
                auth = json.loads(connection.auth_config) if isinstance(connection.auth_config, str) else connection.auth_config
                if auth.get("type") == "bearer":
                    headers["Authorization"] = f"Bearer {auth['token']}"
                elif auth.get("type") == "api_key":
                    headers[auth.get("header", "X-API-Key")] = auth["key"]
            except (json.JSONDecodeError, KeyError):
                pass
        return headers


# Singleton
mcp_hub = MCPIntegrationHub()
