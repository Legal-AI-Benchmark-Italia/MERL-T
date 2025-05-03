"""
VisuaLex MCP Server

Provides legal document retrieval capabilities through the MCP protocol.
Exposes various tools for accessing Normattiva, Brocardi, and EUR-Lex.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional

from loguru import logger

from ..base import BaseMCPServer
from ..protocol import (
    ServerInfo, ServerCapabilities, ToolDefinition,
    ResourceDefinition, JsonRpcResponse, JsonRpcError,
    ExecuteToolParams
)

from ...core.visualex import VisuaLexClient, Norma, NormaVisitata


class VisuaLexServer(BaseMCPServer):
    """
    MCP Server that provides access to Italian legal documents.
    
    Exposes tools for retrieving legislation from multiple sources,
    including Normattiva, Brocardi, and EUR-Lex.
    """
    
    def __init__(
        self,
        name: str = "VisuaLex Server",
        description: str = "Retrieves legal documents from official sources",
        version: str = "0.1.0"
    ):
        """
        Initialize the VisuaLex server.
        
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
        
        # Initialize VisuaLex client
        self.client = VisuaLexClient()
        
        # Define tools
        self._tools = {
            "fetch_article": ToolDefinition(
                name="fetch_article",
                description="Retrieves a specific article from Italian legislation",
                parameters={
                    "type": "object",
                    "properties": {
                        "act_type": {
                            "type": "string",
                            "description": "Type of act (e.g., 'legge', 'decreto legislativo')"
                        },
                        "act_number": {
                            "type": "string",
                            "description": "Number of the act (e.g., '241')"
                        },
                        "act_date": {
                            "type": "string",
                            "description": "Date of the act (e.g., '7 agosto 1990')"
                        },
                        "article_number": {
                            "type": "string",
                            "description": "Article number (e.g., '1' or '1-3,5')"
                        },
                        "version_date": {
                            "type": "string",
                            "description": "Date for a specific version (optional)",
                            "default": "current"
                        }
                    },
                    "required": ["act_type", "act_number", "act_date", "article_number"]
                },
                return_type="object"
            ),
            "fetch_commentary": ToolDefinition(
                name="fetch_commentary",
                description="Retrieves legal commentary from Brocardi.it",
                parameters={
                    "type": "object",
                    "properties": {
                        "act_type": {
                            "type": "string",
                            "description": "Type of act (e.g., 'codice civile', 'codice penale')"
                        },
                        "article_number": {
                            "type": "string",
                            "description": "Article number (e.g., '2043')"
                        }
                    },
                    "required": ["act_type", "article_number"]
                },
                return_type="object"
            ),
            "fetch_eu_legislation": ToolDefinition(
                name="fetch_eu_legislation",
                description="Retrieves European legislation from EUR-Lex",
                parameters={
                    "type": "object",
                    "properties": {
                        "celex_number": {
                            "type": "string",
                            "description": "CELEX number (e.g., '32016R0679')"
                        },
                        "language": {
                            "type": "string",
                            "description": "Language code",
                            "default": "IT"
                        }
                    },
                    "required": ["celex_number"]
                },
                return_type="object"
            ),
            "search_legislation": ToolDefinition(
                name="search_legislation",
                description="Searches for legislation by keywords",
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (e.g., 'protezione dati personali')"
                        },
                        "source": {
                            "type": "string",
                            "description": "Source to search (normattiva, brocardi, eurlex)",
                            "default": "normattiva"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                },
                return_type="array"
            )
        }
        
        # Define resources
        self._resources = {
            "legislation_sources": ResourceDefinition(
                name="legislation_sources",
                description="Available sources for legal documents",
                content=[
                    {
                        "id": "normattiva",
                        "name": "Normattiva",
                        "description": "Official portal for Italian legislation",
                        "url": "https://www.normattiva.it/"
                    },
                    {
                        "id": "brocardi",
                        "name": "Brocardi.it",
                        "description": "Legal commentary and interpretation",
                        "url": "https://www.brocardi.it/"
                    },
                    {
                        "id": "eurlex",
                        "name": "EUR-Lex",
                        "description": "European Union legislation",
                        "url": "https://eur-lex.europa.eu/"
                    }
                ]
            ),
            "common_act_types": ResourceDefinition(
                name="common_act_types",
                description="Common types of legislative acts",
                content=[
                    {
                        "id": "legge",
                        "name": "Legge",
                        "description": "Law approved by Parliament"
                    },
                    {
                        "id": "decreto_legislativo",
                        "name": "Decreto Legislativo",
                        "description": "Legislative decree"
                    },
                    {
                        "id": "decreto_legge",
                        "name": "Decreto Legge",
                        "description": "Decree-law"
                    },
                    {
                        "id": "codice_civile",
                        "name": "Codice Civile",
                        "description": "Civil Code"
                    },
                    {
                        "id": "codice_penale",
                        "name": "Codice Penale",
                        "description": "Criminal Code"
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
            if tool_name == "fetch_article":
                result = await self._fetch_article(tool_params)
            elif tool_name == "fetch_commentary":
                result = await self._fetch_commentary(tool_params)
            elif tool_name == "fetch_eu_legislation":
                result = await self._fetch_eu_legislation(tool_params)
            elif tool_name == "search_legislation":
                result = await self._search_legislation(tool_params)
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
    
    async def _fetch_article(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch a specific article from legislation.
        
        Args:
            params: Tool parameters
            
        Returns:
            Article data
        """
        act_type = params.get("act_type")
        act_number = params.get("act_number")
        act_date = params.get("act_date")
        article_number = params.get("article_number")
        version_date = params.get("version_date", "current")
        
        norma = NormaVisitata(
            tipo_atto=act_type,
            numero_atto=act_number,
            data=act_date,
            numero_articolo=article_number,
            data_versione=version_date if version_date != "current" else None
        )
        
        article_data = await self.client.fetch_article_text(norma)
        return article_data
    
    async def _fetch_commentary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch legal commentary from Brocardi.
        
        Args:
            params: Tool parameters
            
        Returns:
            Commentary data
        """
        act_type = params.get("act_type")
        article_number = params.get("article_number")
        
        commentary = await self.client.fetch_brocardi_info(act_type, article_number)
        return commentary
    
    async def _fetch_eu_legislation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch EU legislation from EUR-Lex.
        
        Args:
            params: Tool parameters
            
        Returns:
            EU legislation data
        """
        celex_number = params.get("celex_number")
        language = params.get("language", "IT")
        
        eu_legislation = await self.client.fetch_eurlex_document(celex_number, language)
        return eu_legislation
    
    async def _search_legislation(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search for legislation by keywords.
        
        Args:
            params: Tool parameters
            
        Returns:
            List of search results
        """
        query = params.get("query")
        source = params.get("source", "normattiva")
        max_results = params.get("max_results", 5)
        
        search_results = await self.client.search(query, source, max_results)
        return search_results 