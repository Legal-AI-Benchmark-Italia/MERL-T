#!/usr/bin/env python3
"""
MERL-T MCP Server

Main entry point for running MERL-T MCP servers.
Supports launching different types of servers via command-line arguments.
"""

import argparse
import asyncio
import os
import sys
from typing import Dict, Any, Optional

from loguru import logger

# Use relative imports since we're within the package
from .mcp import BaseMCPServer
from .mcp.servers import NerServer, VisuaLexServer, KnowledgeGraphServer, AnnotationServer
from .config import get_config_manager


async def run_server(server: BaseMCPServer, transport_type: str, **kwargs):
    """
    Run a server with the specified transport.
    
    Args:
        server: MCP server instance
        transport_type: Type of transport to use
        **kwargs: Additional transport arguments
    """
    logger.info(f"Starting {server.server_info.name} with {transport_type} transport")
    
    if transport_type == "stdio":
        # Run with stdio transport
        await server.run_stdio()
    elif transport_type == "websocket":
        # Run with websocket transport
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 8765)
        await server.run_websocket(host, port)
    elif transport_type == "http":
        # Run with HTTP transport
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 8000)
        await server.run_http(host, port)
    else:
        logger.error(f"Unsupported transport type: {transport_type}")
        sys.exit(1)


def create_server(server_type: str, **kwargs) -> Optional[BaseMCPServer]:
    """
    Create a server of the specified type.
    
    Args:
        server_type: Type of server to create
        **kwargs: Additional server arguments
        
    Returns:
        Server instance or None if type is unsupported
    """
    logger.info(f"Creating {server_type} server")
    
    # Get configuration manager
    config_manager = get_config_manager()
    
    if server_type == "ner":
        # Get NER server configuration
        ner_config = config_manager.get_server_config("ner")
        
        # Override with command line arguments if provided
        model_name = kwargs.get("model_name", ner_config.get("model_name", "dbmdz/bert-base-italian-xxl-cased"))
        spacy_model = kwargs.get("spacy_model", ner_config.get("spacy_model", "it_core_news_lg"))
        use_gpu = kwargs.get("use_gpu", ner_config.get("use_gpu", True))
        
        return NerServer(
            model_name=model_name,
            spacy_model=spacy_model,
            use_gpu=use_gpu
        )
    elif server_type == "visualex":
        # Get VisuaLex server configuration
        visualex_config = config_manager.get_server_config("visualex")
        
        # Create VisuaLex server with config
        return VisuaLexServer(
            name=kwargs.get("name", visualex_config.get("name", "VisuaLex Server")),
            description=kwargs.get("description", visualex_config.get("description", "Retrieves legal documents from official sources")),
            version=kwargs.get("version", visualex_config.get("version", "0.1.0"))
        )
    elif server_type == "knowledge_graph":
        return KnowledgeGraphServer(
            name=kwargs.get("name", "Knowledge Graph Server"),
            description=kwargs.get("description", "Legal knowledge graph access"),
            version=kwargs.get("version", "0.1.0")
        )
    elif server_type == "annotation":
        return AnnotationServer(
            name=kwargs.get("name", "Annotation Server"),
            description=kwargs.get("description", "Entity annotation and knowledge validation system"),
            version=kwargs.get("version", "0.1.0")
        )
    else:
        logger.error(f"Unsupported server type: {server_type}")
        return None


def main():
    """Main entry point."""
    # Configure command-line arguments
    parser = argparse.ArgumentParser(description="Run MERL-T MCP server")
    
    parser.add_argument(
        "--config",
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--server-type",
        choices=["ner", "visualex", "knowledge_graph", "annotation"],
        default="ner",
        help="Type of server to run"
    )
    
    parser.add_argument(
        "--transport",
        choices=["stdio", "websocket", "http"],
        help="Transport method to use"
    )
    
    parser.add_argument(
        "--host",
        help="Host for websocket/http transport"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        help="Port for websocket/http transport"
    )
    
    parser.add_argument(
        "--model-name",
        help="Model name for transformer-based servers"
    )
    
    parser.add_argument(
        "--spacy-model",
        help="spaCy model name"
    )
    
    parser.add_argument(
        "--no-gpu",
        action="store_true",
        help="Disable GPU usage"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config_manager = get_config_manager()
    if args.config:
        config_manager.load_from_file(args.config)
    
    # Configure logging
    log_level = args.log_level or config_manager.get("general.log_level", "INFO")
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Get server configuration
    server_config = config_manager.get_server_config(args.server_type)
    
    # Create server with args overriding config
    server = create_server(
        args.server_type,
        model_name=args.model_name,
        spacy_model=args.spacy_model,
        use_gpu=not args.no_gpu if args.no_gpu is not None else server_config.get("use_gpu", True)
    )
    
    if server is None:
        sys.exit(1)
    
    # Get transport settings with args overriding config
    transport_type = args.transport or config_manager.get("mcp.defaults.transport", "stdio")
    
    # Determine port based on transport type and server type
    default_port = None
    if transport_type == "websocket":
        default_port = server_config.get("websocket_port", 
                      config_manager.get("mcp.defaults.websocket_port", 8765))
    elif transport_type == "http":
        default_port = server_config.get("http_port", 
                      config_manager.get("mcp.defaults.http_port", 8000))
    
    transport_args = {
        "host": args.host or server_config.get("host", 
               config_manager.get("mcp.defaults.host", "localhost")),
        "port": args.port or default_port
    }
    
    try:
        asyncio.run(run_server(server, transport_type, **transport_args))
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 