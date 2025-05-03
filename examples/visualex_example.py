#!/usr/bin/env python
"""
VisuaLex Server Example

Demonstrates how to use the VisuaLex MCP server to retrieve legal documents.
"""

import asyncio
import json
import sys
import os
# Non modifichiamo il sys.path, assumiamo che PYTHONPATH includa la radice del progetto
# o che il progetto sia installato correttamente

from merl_t import VisuaLexServer
from merl_t.config import get_config_manager


async def main():
    """Run the example."""
    # Initialize the configuration
    config = get_config_manager()
    
    # Create VisuaLex server
    server = VisuaLexServer(
        name="VisuaLex Example Server",
        description="Example server for retrieving legal documents",
        version="0.1.0"
    )
    
    # Retrieve server information
    server_info = server.server_info
    print(f"Server: {server_info.name} - {server_info.description} (v{server_info.version})")
    
    # List available tools
    print("\nAvailable tools:")
    for tool_name, tool in server._tools.items():
        print(f"  - {tool_name}: {tool.description}")
    
    # Example of retrieving an article
    print("\nRetrieving article from Normattiva...")
    fetch_article_params = {
        "name": "fetch_article",
        "parameters": {
            "act_type": "legge",
            "act_number": "241",
            "act_date": "7 agosto 1990",
            "article_number": "1"
        }
    }
    
    from merl_t.mcp.protocol import ExecuteToolParams
    response = await server.execute_tool(ExecuteToolParams(**fetch_article_params))
    
    if response.error:
        print(f"Error: {response.error.message}")
    else:
        result = response.result
        print(f"Article: {result.get('articolo')} - {result.get('rubrica')}")
        print(f"Content: {result.get('testo')[:200]}...")
    
    # Example of retrieving a commentary
    print("\nRetrieving commentary from Brocardi...")
    fetch_commentary_params = {
        "name": "fetch_commentary",
        "parameters": {
            "act_type": "codice civile",
            "article_number": "2043"
        }
    }
    
    response = await server.execute_tool(ExecuteToolParams(**fetch_commentary_params))
    
    if response.error:
        print(f"Error: {response.error.message}")
    else:
        result = response.result
        print(f"Title: {result.get('title')}")
        print(f"Content: {result.get('explanation')[:200]}...")
    
    # Example of searching legislation
    print("\nSearching for legislation...")
    search_params = {
        "name": "search_legislation",
        "parameters": {
            "query": "protezione dati personali",
            "source": "normattiva",
            "max_results": 3
        }
    }
    
    response = await server.execute_tool(ExecuteToolParams(**search_params))
    
    if response.error:
        print(f"Error: {response.error.message}")
    else:
        results = response.result
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results):
            print(f"  {i+1}. {result.get('title')}")
            print(f"     {result.get('description')[:100]}...")
            print()


if __name__ == "__main__":
    asyncio.run(main()) 