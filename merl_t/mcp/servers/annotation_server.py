"""
Annotation MCP Server

Provides access to the annotation system for entity tagging and validation.
Exposes annotation capabilities through the MCP protocol.
"""

import asyncio
import json
import os
import sys
import subprocess
import threading
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from merl_t.mcp.base import BaseMCPServer
from merl_t.mcp.protocol import (
    ServerInfo, ServerCapabilities, ToolDefinition,
    ResourceDefinition, JsonRpcResponse, JsonRpcError,
    ExecuteToolParams
)

# Configurazione dei percorsi
ANNOTATION_MODULE_PATH = Path(__file__).resolve().parent.parent.parent / "core" / "annotation"
APP_PATH = ANNOTATION_MODULE_PATH / "app.py"

class AnnotationServer(BaseMCPServer):
    """
    MCP Server that provides access to the annotation system.
    
    Exposes tools for:
    - Annotation management
    - Entity type management
    - Knowledge graph validation
    - Opening web interface
    """
    
    def __init__(
        self,
        name: str = "Annotation Server",
        description: str = "Provides annotation and validation capabilities",
        version: str = "0.1.0"
    ):
        """
        Initialize the Annotation server.
        
        Args:
            name: Display name for the server
            description: Description of the server
            version: Server version
        """
        super().__init__(name, description, version)
        self.flask_process = None
        self.host = "127.0.0.1"
        self.port = 8080
        self.annotation_url = f"http://{self.host}:{self.port}"
        self.stopped = threading.Event()
        
    async def initialize(self) -> None:
        """Initialize the server and start the Flask app."""
        await super().initialize()
        
        # Configura host e porta dall'oggetto config, se disponibile
        try:
            from merl_t.config import get_config_manager
            config = get_config_manager()
            self.host = config.get("annotation.host", self.host)
            self.port = config.get("annotation.port", self.port)
            logger.info(f"Annotation server configured with host={self.host}, port={self.port}")
        except ImportError:
            logger.warning("Config manager not available, using default host/port")
        
        self.annotation_url = f"http://{self.host}:{self.port}"
        
        # Start Flask app in a separate thread
        self._start_flask_app()
        logger.info(f"Annotation server running at {self.annotation_url}")
        
        # Register tools
        self._register_tools()
        
    def _start_flask_app(self):
        """Start the Flask app in a separate process."""
        
        def run_flask_app():
            try:
                logger.info(f"Starting Flask app from {APP_PATH}")
                env = os.environ.copy()
                env["FLASK_APP"] = str(APP_PATH)
                env["FLASK_ENV"] = "development"
                env["FLASK_RUN_HOST"] = self.host
                env["FLASK_RUN_PORT"] = str(self.port)
                
                self.flask_process = subprocess.Popen(
                    [sys.executable, "-m", "flask", "run", "--host", self.host, "--port", str(self.port)],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                logger.info(f"Flask process started with PID {self.flask_process.pid}")
            except Exception as e:
                logger.error(f"Error starting Flask app: {e}")
        
        thread = threading.Thread(target=run_flask_app)
        thread.daemon = True
        thread.start()
        
        # Wait a bit for the Flask app to start
        import time
        time.sleep(2)
    
    def _register_tools(self):
        """Register the annotation tools."""
        
        self.register_tool(
            ToolDefinition(
                name="get_annotation_url",
                description="Get the URL of the annotation web interface",
                parameters=[],
                returns={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL of the annotation web interface"
                        }
                    }
                }
            )
        )
        
        self.register_tool(
            ToolDefinition(
                name="list_documents",
                description="List documents available for annotation",
                parameters=[
                    {
                        "name": "status",
                        "type": "string",
                        "required": False,
                        "description": "Filter by document status (pending, completed, etc.)"
                    }
                ],
                returns={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "status": {"type": "string"},
                            "annotation_count": {"type": "integer"}
                        }
                    }
                }
            )
        )
        
        self.register_tool(
            ToolDefinition(
                name="list_entity_types",
                description="List all entity types available for annotation",
                parameters=[
                    {
                        "name": "category",
                        "type": "string",
                        "required": False,
                        "description": "Filter by entity category"
                    }
                ],
                returns={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "name": {"type": "string"},
                            "display_name": {"type": "string"},
                            "color": {"type": "string"}
                        }
                    }
                }
            )
        )
        
        self.register_tool(
            ToolDefinition(
                name="get_annotations",
                description="Get annotations for a specific document",
                parameters=[
                    {
                        "name": "document_id",
                        "type": "string",
                        "required": True,
                        "description": "ID of the document to get annotations for"
                    }
                ],
                returns={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "start": {"type": "integer"},
                            "end": {"type": "integer"},
                            "text": {"type": "string"},
                            "type": {"type": "string"}
                        }
                    }
                }
            )
        )
        
        self.register_tool(
            ToolDefinition(
                name="get_graph_chunks",
                description="Get graph chunks available for validation",
                parameters=[
                    {
                        "name": "status",
                        "type": "string",
                        "required": False,
                        "description": "Filter by chunk status (pending, validated, etc.)"
                    }
                ],
                returns={
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "status": {"type": "string"},
                            "chunk_type": {"type": "string"}
                        }
                    }
                }
            )
        )
        
        self.register_tool(
            ToolDefinition(
                name="get_annotation_stats",
                description="Get statistics about annotations and validation",
                parameters=[],
                returns={
                    "type": "object",
                    "properties": {
                        "total_documents": {"type": "integer"},
                        "total_annotations": {"type": "integer"},
                        "total_users": {"type": "integer"},
                        "active_users": {"type": "integer"}
                    }
                }
            )
        )
    
    async def execute_tool(self, params: ExecuteToolParams) -> JsonRpcResponse:
        """Execute a tool with the given parameters."""
        try:
            tool_name = params.name
            arguments = params.arguments or {}
            
            if tool_name == "get_annotation_url":
                result = await self._get_annotation_url()
            elif tool_name == "list_documents":
                result = await self._list_documents(arguments)
            elif tool_name == "list_entity_types":
                result = await self._list_entity_types(arguments)
            elif tool_name == "get_annotations":
                result = await self._get_annotations(arguments)
            elif tool_name == "get_graph_chunks":
                result = await self._get_graph_chunks(arguments)
            elif tool_name == "get_annotation_stats":
                result = await self._get_annotation_stats()
            else:
                return JsonRpcResponse.error(
                    error=JsonRpcError(
                        code=-32601,
                        message=f"Tool '{tool_name}' not found"
                    )
                )
            
            return JsonRpcResponse.result(result)
        except Exception as e:
            logger.error(f"Error executing tool {params.name}: {e}")
            return JsonRpcResponse.error(
                error=JsonRpcError(
                    code=-32000,
                    message=f"Error executing tool: {str(e)}"
                )
            )
    
    async def _get_annotation_url(self) -> Dict[str, Any]:
        """Get the URL of the annotation web interface."""
        return {
            "url": self.annotation_url
        }
    
    async def _list_documents(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List documents available for annotation."""
        try:
            # Import the database manager
            sys.path.insert(0, str(ANNOTATION_MODULE_PATH.parent))
            from ...core.annotation.db_manager import AnnotationDBManager
            
            # Create database manager
            db_manager = AnnotationDBManager()
            
            # Get status filter
            status = arguments.get("status")
            
            # Get documents
            documents = db_manager.get_documents(status=status)
            
            # Format response
            results = []
            for doc in documents:
                results.append({
                    "id": doc.get("id", ""),
                    "title": doc.get("title", ""),
                    "status": doc.get("status", "pending"),
                    "annotation_count": doc.get("annotation_count", 0)
                })
            
            return results
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return []
    
    async def _list_entity_types(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List all entity types available for annotation."""
        try:
            # Import the entity manager
            from ...core.entities.entity_manager import get_entity_manager
            
            # Get category filter
            category = arguments.get("category")
            
            # Get entity manager
            entity_manager = get_entity_manager()
            
            # Get all entities
            entities = entity_manager.get_all_entities()
            
            # Filter by category if specified
            if category:
                entities = [e for e in entities if e.category == category]
            
            # Format response
            results = []
            for entity in entities:
                results.append({
                    "id": entity.id,
                    "name": entity.name,
                    "display_name": entity.display_name,
                    "color": entity.color
                })
            
            return results
        except Exception as e:
            logger.error(f"Error listing entity types: {e}")
            return []
    
    async def _get_annotations(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get annotations for a specific document."""
        try:
            # Import the database manager
            from ...core.annotation.db_manager import AnnotationDBManager
            
            # Create database manager
            db_manager = AnnotationDBManager()
            
            # Get document ID
            document_id = arguments.get("document_id")
            if not document_id:
                raise ValueError("document_id is required")
            
            # Get annotations
            annotations = db_manager.get_document_annotations(document_id)
            
            # Format response
            results = []
            for ann in annotations:
                results.append({
                    "id": ann.get("id", ""),
                    "start": ann.get("start_offset", 0),
                    "end": ann.get("end_offset", 0),
                    "text": ann.get("text", ""),
                    "type": ann.get("type", "")
                })
            
            return results
        except Exception as e:
            logger.error(f"Error getting annotations: {e}")
            return []
    
    async def _get_graph_chunks(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get graph chunks available for validation."""
        try:
            # Import the database manager
            from ...core.annotation.db_manager import AnnotationDBManager
            
            # Create database manager
            db_manager = AnnotationDBManager()
            
            # Get status filter
            status = arguments.get("status")
            
            # Get chunks
            chunks = db_manager.get_graph_chunks(status=status)
            
            # Format response
            results = []
            for chunk in chunks:
                results.append({
                    "id": chunk.get("id", ""),
                    "title": chunk.get("title", ""),
                    "status": chunk.get("status", "pending"),
                    "chunk_type": chunk.get("chunk_type", "")
                })
            
            return results
        except Exception as e:
            logger.error(f"Error getting graph chunks: {e}")
            return []
    
    async def _get_annotation_stats(self) -> Dict[str, Any]:
        """Get statistics about annotations and validation."""
        try:
            # Import the database manager
            from ...core.annotation.db_manager import AnnotationDBManager
            
            # Create database manager
            db_manager = AnnotationDBManager()
            
            # Get documents
            documents = db_manager.get_documents()
            total_documents = len(documents)
            
            # Count documents by status
            status_counts = {}
            for doc in documents:
                status = doc.get("status", "pending")
                if status not in status_counts:
                    status_counts[status] = 0
                status_counts[status] += 1
            
            # Total annotations
            all_annotations = db_manager.get_annotations()
            total_annotations = sum(len(anns) for anns in all_annotations.values())
            
            # User stats
            users = db_manager.get_all_users()
            active_users = [u for u in users if u.get("active", 1)]
            
            return {
                "total_documents": total_documents,
                "documents_by_status": status_counts,
                "total_annotations": total_annotations,
                "total_users": len(users),
                "active_users": len(active_users)
            }
        except Exception as e:
            logger.error(f"Error getting annotation stats: {e}")
            return {
                "error": str(e)
            }
    
    async def shutdown(self):
        """Shutdown the server and stop the Flask app."""
        logger.info("Shutting down annotation server...")
        if self.flask_process:
            logger.info(f"Terminating Flask process (PID: {self.flask_process.pid})")
            self.flask_process.terminate()
            try:
                self.flask_process.wait(timeout=5)
                logger.info("Flask process terminated successfully")
            except subprocess.TimeoutExpired:
                logger.warning("Flask process did not terminate gracefully, killing...")
                self.flask_process.kill()
        
        await super().shutdown() 