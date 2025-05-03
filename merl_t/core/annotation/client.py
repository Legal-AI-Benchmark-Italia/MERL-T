"""
Annotation Client

Client for accessing the annotation system through MCP.
"""

from typing import Dict, List, Any, Optional
import webbrowser
import os
from pathlib import Path

from loguru import logger

from merl_t.mcp import BaseMCPClient


class AnnotationClient:
    """
    Client for interacting with the annotation system.
    
    Provides programmatic access to the annotation system and web interface,
    allowing for:
    - Managing documents and annotations
    - Accessing entity types
    - Validating knowledge graph chunks
    - Retrieving annotation statistics
    """
    
    def __init__(self, client: Optional[BaseMCPClient] = None):
        """
        Initialize the Annotation client.
        
        Args:
            client: An existing MCP client connected to an Annotation server.
                   If None, a new client will be created when needed.
        """
        self._client = client
        self._annotation_url = None
    
    async def _ensure_client(self) -> BaseMCPClient:
        """Ensure a client is available and connected."""
        if self._client is None or not self._client.is_connected():
            from merl_t.mcp import BaseMCPClient
            from merl_t.config import get_config_manager
            
            config = get_config_manager()
            server_name = config.get("servers.annotation.name", "Annotation Server")
            
            logger.info(f"Creating new MCP client for {server_name}")
            self._client = BaseMCPClient()
            await self._client.connect(server_name)
        
        return self._client
    
    async def get_annotation_url(self) -> str:
        """
        Get the URL to access the annotation web interface.
        
        Returns:
            The URL to the annotation web interface.
        """
        client = await self._ensure_client()
        result = await client.execute_tool("get_annotation_url", {})
        
        self._annotation_url = result.get("url")
        return self._annotation_url
    
    async def open_web_interface(self) -> bool:
        """
        Open the annotation web interface in the default browser.
        
        Returns:
            True if the browser was opened successfully, False otherwise.
        """
        url = await self.get_annotation_url()
        
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"Error opening web browser: {e}")
            return False
    
    async def list_documents(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available documents for annotation.
        
        Args:
            status: Filter by document status (pending, completed, etc.)
            
        Returns:
            List of document objects.
        """
        client = await self._ensure_client()
        
        params = {}
        if status:
            params["status"] = status
            
        return await client.execute_tool("list_documents", params)
    
    async def list_entity_types(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available entity types for annotation.
        
        Args:
            category: Filter by entity category
            
        Returns:
            List of entity type objects.
        """
        client = await self._ensure_client()
        
        params = {}
        if category:
            params["category"] = category
            
        return await client.execute_tool("list_entity_types", params)
    
    async def get_annotations(self, document_id: str) -> List[Dict[str, Any]]:
        """
        Get annotations for a specific document.
        
        Args:
            document_id: ID of the document
            
        Returns:
            List of annotation objects.
        """
        client = await self._ensure_client()
        
        params = {"document_id": document_id}
        return await client.execute_tool("get_annotations", params)
    
    async def get_graph_chunks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get knowledge graph chunks for validation.
        
        Args:
            status: Filter by chunk status (pending, validated, etc.)
            
        Returns:
            List of graph chunk objects.
        """
        client = await self._ensure_client()
        
        params = {}
        if status:
            params["status"] = status
            
        return await client.execute_tool("get_graph_chunks", params)
    
    async def get_annotation_stats(self) -> Dict[str, Any]:
        """
        Get statistics about annotations.
        
        Returns:
            Dictionary with annotation statistics.
        """
        client = await self._ensure_client()
        
        return await client.execute_tool("get_annotation_stats", {}) 