"""
Knowledge Graph MCP Server

Provides knowledge graph capabilities through the MCP protocol.
Exposes tools for querying and manipulating the legal knowledge graph.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from merl_t.mcp.base import BaseMCPServer
from merl_t.mcp.protocol import (
    ServerInfo, ServerCapabilities, ToolDefinition,
    ResourceDefinition, JsonRpcResponse, JsonRpcError,
    ExecuteToolParams
)

from merl_t.core.kg import KnowledgeGraphClient
from merl_t.core.kg.models import KnowledgeGraphNode, KnowledgeGraphEdge


class KnowledgeGraphServer(BaseMCPServer):
    """
    MCP Server that provides access to the legal knowledge graph.
    
    Exposes tools for querying entities and relationships in the Neo4j database.
    """
    
    def __init__(
        self,
        name: str = "Knowledge Graph Server",
        description: str = "Provides access to the legal knowledge graph",
        version: str = "0.1.0"
    ):
        """
        Initialize the Knowledge Graph server.
        
        Args:
            name: Server name
            description: Server description
            version: Server version
        """
        # Initialize base server
        super().__init__()
        
        # Server info
        self.server_info = ServerInfo(
            name=name,
            description=description,
            version=version,
            vendor="LAIBIT",
        )
        
        # Initialize Knowledge Graph client
        self.client = KnowledgeGraphClient()
        
        # Define tools
        self._tools = {
            "search_entities": ToolDefinition(
                name="search_entities",
                description="Searches for entities in the knowledge graph by name and type",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (entity name or part of it)"
                        },
                        "entity_type": {
                            "type": "string",
                            "description": "Entity type to filter by (e.g., 'Norma', 'ConcettoGiuridico')"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                },
                return_type="array"
            ),
            "get_entity_by_id": ToolDefinition(
                name="get_entity_by_id",
                description="Retrieves a specific entity from the knowledge graph by ID",
                parameters={
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "ID of the entity to retrieve"
                        }
                    },
                    "required": ["entity_id"]
                },
                return_type="object"
            ),
            "get_relationships": ToolDefinition(
                name="get_relationships",
                description="Retrieves relationships for a specific entity",
                parameters={
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "ID of the entity"
                        },
                        "relationship_type": {
                            "type": "string",
                            "description": "Type of relationship to filter by (optional)"
                        },
                        "direction": {
                            "type": "string",
                            "description": "Direction of relationships (incoming, outgoing, both)",
                            "default": "both"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of relationships to return",
                            "default": 20
                        }
                    },
                    "required": ["entity_id"]
                },
                return_type="array"
            ),
            "get_neighborhood": ToolDefinition(
                name="get_neighborhood",
                description="Retrieves a subgraph centered around the specified entity",
                parameters={
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "ID of the central entity"
                        },
                        "depth": {
                            "type": "integer",
                            "description": "Maximum path length (1 = direct neighbors only)",
                            "default": 1
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of nodes to return",
                            "default": 50
                        }
                    },
                    "required": ["entity_id"]
                },
                return_type="object"
            )
        }
        
        # Define resources
        self._resources = {
            "entity_types": ResourceDefinition(
                name="entity_types",
                description="Legal entity types available in the knowledge graph",
                content=[
                    {
                        "id": "Norma",
                        "name": "Norma",
                        "description": "Legal norm or article"
                    },
                    {
                        "id": "ConcettoGiuridico",
                        "name": "Concetto Giuridico",
                        "description": "Legal concept"
                    },
                    {
                        "id": "SoggettoGiuridico",
                        "name": "Soggetto Giuridico",
                        "description": "Legal subject (person, organization, etc.)"
                    },
                    {
                        "id": "AttoGiudiziario",
                        "name": "Atto Giudiziario",
                        "description": "Judicial act"
                    },
                    {
                        "id": "FonteDiritto",
                        "name": "Fonte Diritto",
                        "description": "Source of law"
                    },
                    {
                        "id": "Dottrina",
                        "name": "Dottrina",
                        "description": "Legal doctrine"
                    },
                    {
                        "id": "Procedura",
                        "name": "Procedura",
                        "description": "Legal procedure"
                    }
                ]
            ),
            "relationship_types": ResourceDefinition(
                name="relationship_types",
                description="Types of relationships between legal entities",
                content=[
                    {
                        "id": "DISCIPLINA",
                        "name": "Disciplina",
                        "description": "Regulates or disciplines"
                    },
                    {
                        "id": "APPLICA_A",
                        "name": "Applica a",
                        "description": "Applies to"
                    },
                    {
                        "id": "INTERPRETA",
                        "name": "Interpreta",
                        "description": "Interprets"
                    },
                    {
                        "id": "COMMENTA",
                        "name": "Commenta",
                        "description": "Comments on"
                    },
                    {
                        "id": "CITA",
                        "name": "Cita",
                        "description": "Cites"
                    },
                    {
                        "id": "DEROGA_A",
                        "name": "Deroga a",
                        "description": "Derogates from"
                    },
                    {
                        "id": "MODIFICA",
                        "name": "Modifica",
                        "description": "Modifies"
                    },
                    {
                        "id": "RELAZIONE_CONCETTUALE",
                        "name": "Relazione Concettuale",
                        "description": "Conceptual relationship"
                    },
                    {
                        "id": "EMESSO_DA",
                        "name": "Emesso Da",
                        "description": "Issued by"
                    },
                    {
                        "id": "FONTE",
                        "name": "Fonte",
                        "description": "Source of"
                    }
                ]
            )
        }
    
    async def execute_tool(self, params: ExecuteToolParams) -> JsonRpcResponse:
        """
        Execute a tool with the given parameters.
        
        Args:
            params: Tool execution parameters
            
        Returns:
            JSON-RPC response with the result or error
        """
        tool_name = params.name
        tool_params = params.parameters
        
        try:
            if tool_name == "search_entities":
                result = await self._search_entities(tool_params)
            elif tool_name == "get_entity_by_id":
                result = await self._get_entity_by_id(tool_params)
            elif tool_name == "get_relationships":
                result = await self._get_relationships(tool_params)
            elif tool_name == "get_neighborhood":
                result = await self._get_neighborhood(tool_params)
            else:
                return JsonRpcResponse(
                    error=JsonRpcError(
                        code=-32601,
                        message=f"Tool '{tool_name}' not found"
                    )
                )
            
            return JsonRpcResponse(result=result)
        except Exception as e:
            logger.exception(f"Error executing tool {tool_name}")
            return JsonRpcResponse(
                error=JsonRpcError(
                    code=-32000,
                    message=f"Error executing tool: {str(e)}"
                )
            )
    
    async def _search_entities(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for entities in the knowledge graph.
        
        Args:
            params: Tool parameters
            
        Returns:
            List of entity data
        """
        query = params.get("query", "")
        entity_type = params.get("entity_type")
        limit = params.get("limit", 10)
        
        entities = await self.client.search_entities(query, entity_type, limit)
        return entities
    
    async def _get_entity_by_id(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get an entity by ID.
        
        Args:
            params: Tool parameters
            
        Returns:
            Entity data
        """
        entity_id = params.get("entity_id")
        if not entity_id:
            raise ValueError("entity_id is required")
        
        entity = await self.client.get_entity(entity_id)
        if not entity:
            raise ValueError(f"Entity not found: {entity_id}")
        
        return entity
    
    async def _get_relationships(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get relationships for an entity.
        
        Args:
            params: Tool parameters
            
        Returns:
            List of relationship data
        """
        entity_id = params.get("entity_id")
        relationship_type = params.get("relationship_type")
        direction = params.get("direction", "both")
        limit = params.get("limit", 20)
        
        relationships = await self.client.get_relationships(
            entity_id, 
            relationship_type=relationship_type,
            direction=direction,
            limit=limit
        )
        
        return relationships
    
    async def _get_neighborhood(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a neighborhood subgraph for an entity.
        
        Args:
            params: Tool parameters
            
        Returns:
            Subgraph data (nodes and edges)
        """
        entity_id = params.get("entity_id")
        depth = params.get("depth", 1)
        limit = params.get("limit", 50)
        
        subgraph = await self.client.get_neighborhood(entity_id, depth, limit)
        return subgraph 