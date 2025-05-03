"""
Main Orchestrator Implementation

Implements the central coordinator that manages all MERL-T components.
"""

import asyncio
from typing import Dict, List, Optional, Any

from loguru import logger

from merl_t.mcp import BaseMCPHost
from merl_t.a2a import BaseAgent
from merl_t.config import get_config_manager
from merl_t.mcp.servers import NerServer, VisuaLexServer


class Orchestrator(BaseMCPHost, BaseAgent):
    """
    MERL-T Orchestrator
    
    Acts as both an MCP Host (managing MCP servers) and an A2A Agent
    (communicating with other agents). Responsible for routing queries
    to appropriate components and aggregating responses.
    """
    
    def __init__(
        self,
        name: str = None,
        description: str = None,
        version: str = None,
        config_file: str = None
    ):
        """
        Initialize the orchestrator.
        
        Args:
            name: Name of the orchestrator (optional, defaults to config)
            description: Description of the orchestrator (optional, defaults to config)
            version: Version string (optional, defaults to config)
            config_file: Path to configuration file (optional)
        """
        # Load configuration
        self.config_manager = get_config_manager()
        if config_file:
            self.config_manager.load_from_file(config_file)
        
        # Get settings from config with fallbacks
        config = self.config_manager.get_section("orchestrator")
        name = name or config.get("name", "MERL-T Orchestrator")
        description = description or config.get("description", "Coordinatore centrale del sistema MERL-T")
        version = version or config.get("version", "0.1.0")
        
        # Initialize as A2A Agent
        BaseAgent.__init__(
            self,
            name=name,
            description=description,
            version=version
        )
        
        # Initialize as MCP Host  
        BaseMCPHost.__init__(self)
        
        logger.info(f"Orchestrator {name} initialized")
        
        # Will contain connected servers
        self._servers = {}
        
        # Will contain various components (servers, models, etc.)
        self._components = {}
        
        # Initialize components based on configuration
        self._initialize_components()
        
    def _initialize_components(self):
        """Initialize components based on configuration."""
        # Get enabled server types
        server_types = self.config_manager.get("orchestrator.server_types", [])
        if not server_types:
            logger.warning("No server types specified in configuration")
            return
            
        logger.info(f"Configured server types: {server_types}")
        
        # Start connection tasks for each server type
        # Will be properly implemented in future versions to connect to all configured servers
        
    async def handle_message(self, message, session_id):
        """
        Handle an incoming A2A message.
        
        This is a required implementation from BaseAgent.
        
        Args:
            message: The incoming message
            session_id: The session ID
            
        Returns:
            List of messages and artifacts to respond with
        """
        # Placeholder implementation
        logger.info(f"Received message in session {session_id}")
        return []
        
    async def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a legal query through the MERL-T system.
        
        Args:
            query: The legal query to process
            
        Returns:
            Processed results
        """
        try:
            logger.info(f"Processing query: {query}")
            
            # Connect to required servers if not already connected
            results = {}
            
            # Connect to the NER server if necessary
            ner_server_id = self._servers.get("ner")
            if not ner_server_id:
                try:
                    ner_server_id = await self.connect_to_server("ner")
                    if ner_server_id:
                        self._servers["ner"] = ner_server_id
                    else:
                        logger.warning("Failed to connect to NER server")
                except Exception as e:
                    logger.error(f"Error connecting to NER server: {str(e)}")
            
            # Connect to the VisuaLex server if necessary
            visualex_server_id = self._servers.get("visualex")
            if not visualex_server_id:
                try:
                    visualex_server_id = await self.connect_to_server("visualex")
                    if visualex_server_id:
                        self._servers["visualex"] = visualex_server_id
                    else:
                        logger.warning("Failed to connect to VisuaLex server")
                except Exception as e:
                    logger.error(f"Error connecting to VisuaLex server: {str(e)}")
            
            # This will be implemented to:
            # 1. Extract entities with NERServer
            # 2. Use VisuaLexServer to retrieve relevant legislation
            # 3. Route to appropriate expert agents
            # 4. Retrieve context from KG and VDB
            # 5. Synthesize a response
            
            return {
                "query": query,
                "status": "not_implemented",
                "message": "La funzionalità completa sarà implementata in versioni future",
                "connected_servers": list(self._servers.keys())
            }
        except Exception as e:
            logger.exception(f"Unexpected error processing query: {str(e)}")
            return {
                "query": query,
                "status": "error",
                "error": str(e),
                "message": "Si è verificato un errore durante l'elaborazione della query"
            }
        
    async def connect_to_server(self, server_type: str) -> Optional[str]:
        """
        Connect to a MCP server based on configuration.
        
        Args:
            server_type: Type of server to connect to
            
        Returns:
            Server ID if connected successfully, None otherwise
        """
        try:
            # Get server configuration
            server_config = self.config_manager.get_server_config(server_type)
            if not server_config:
                logger.error(f"No configuration found for server type {server_type}")
                return None
                
            if not server_config.get("enabled", False):
                logger.warning(f"Server {server_type} is disabled in configuration")
                return None
                
            # Determine connection parameters
            host = server_config.get("host", self.config_manager.get("mcp.defaults.host", "localhost"))
            port = server_config.get("websocket_port", self.config_manager.get("mcp.defaults.websocket_port", 8765))
            url = f"ws://{host}:{port}"
            
            try:
                # Connect to server
                server_id = await self.connect_server(url, server_type, "websocket")
                logger.info(f"Connected to {server_type} server at {url}")
                return server_id
            except asyncio.TimeoutError:
                logger.error(f"Connection timeout when connecting to {server_type} server at {url}")
                return None
            except ConnectionRefusedError:
                logger.error(f"Connection refused when connecting to {server_type} server at {url}")
                return None
            except Exception as e:
                logger.error(f"Failed to connect to {server_type} server at {url}: {e}")
                return None
        except Exception as e:
            logger.exception(f"Unexpected error in connect_to_server for {server_type}: {e}")
            return None 