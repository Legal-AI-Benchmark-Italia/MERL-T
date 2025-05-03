#!/usr/bin/env python
"""
Knowledge Graph Server Example

Demonstrates how to use the Knowledge Graph MCP server to query the legal knowledge graph.
"""

import asyncio
import json
import sys
import os
# Non modifichiamo il sys.path, assumiamo che PYTHONPATH includa la radice del progetto
# o che il progetto sia installato correttamente

from merl_t import KnowledgeGraphServer
from merl_t.mcp.protocol import ExecuteToolParams
from merl_t.config import get_config_manager


async def main():
    """Run the example."""
    # Initialize the configuration
    config = get_config_manager()
    
    # Create Knowledge Graph server
    server = KnowledgeGraphServer(
        name="Knowledge Graph Example Server",
        description="Example server for querying the legal knowledge graph",
        version="0.1.0"
    )
    
    # Retrieve server information
    server_info = server.server_info
    print(f"Server: {server_info.name} - {server_info.description} (v{server_info.version})")
    
    # List available tools
    print("\nAvailable tools:")
    for tool_name, tool in server._tools.items():
        print(f"  - {tool_name}: {tool.description}")
    
    # Example of searching for entities
    print("\nSearching for entities...")
    search_params = {
        "name": "search_entities",
        "parameters": {
            "query": "Contratto",
            "entity_type": "ConcettoGiuridico",
            "limit": 5
        }
    }
    
    response = await server.execute_tool(ExecuteToolParams(**search_params))
    
    if response.error:
        print(f"Error: {response.error.message}")
    else:
        results = response.result
        print(f"Found {len(results)} entities:")
        for i, entity in enumerate(results):
            print(f"  {i+1}. {entity.get('name')} ({entity.get('entity_label', 'Unknown')})")
            if entity.get('description'):
                print(f"     {entity.get('description')[:100]}...")
            print()
    
    # Example of retrieving an entity by ID
    # Note: You need to replace 'example_entity_id' with a valid entity ID from your graph
    entity_id = "Contratto"  # Replace with a valid ID
    print(f"\nRetrieving entity with ID '{entity_id}'...")
    entity_params = {
        "name": "get_entity_by_id",
        "parameters": {
            "entity_id": entity_id
        }
    }
    
    response = await server.execute_tool(ExecuteToolParams(**entity_params))
    
    if response.error:
        print(f"Error: {response.error.message}")
    else:
        entity = response.result
        if entity:
            print(f"Entity: {entity.get('name')} ({entity.get('entity_label', 'Unknown')})")
            if entity.get('description'):
                print(f"Description: {entity.get('description')}")
        else:
            print(f"Entity not found: {entity_id}")
    
    # Example of retrieving relationships
    if entity:
        print(f"\nRetrieving relationships for entity '{entity_id}'...")
        rel_params = {
            "name": "get_relationships",
            "parameters": {
                "entity_id": entity_id,
                "limit": 10
            }
        }
        
        response = await server.execute_tool(ExecuteToolParams(**rel_params))
        
        if response.error:
            print(f"Error: {response.error.message}")
        else:
            relationships = response.result
            print(f"Found {len(relationships)} relationships:")
            for i, rel in enumerate(relationships):
                source = rel.get('source')
                target = rel.get('target')
                rel_type = rel.get('type')
                direction = rel.get('direction')
                print(f"  {i+1}. {source} -[{rel_type}]-> {target} ({direction})")
    
    # Example of retrieving a neighborhood subgraph
    if entity:
        print(f"\nRetrieving neighborhood for entity '{entity_id}'...")
        neighborhood_params = {
            "name": "get_neighborhood",
            "parameters": {
                "entity_id": entity_id,
                "depth": 1,
                "limit": 20
            }
        }
        
        response = await server.execute_tool(ExecuteToolParams(**neighborhood_params))
        
        if response.error:
            print(f"Error: {response.error.message}")
        else:
            subgraph = response.result
            nodes = subgraph.get('nodes', [])
            edges = subgraph.get('edges', [])
            is_truncated = subgraph.get('is_truncated', False)
            
            print(f"Subgraph contains {len(nodes)} nodes and {len(edges)} edges")
            print(f"Truncated: {is_truncated}")
            
            print("\nNodes:")
            for i, node in enumerate(nodes[:5]):  # Show only first 5 nodes
                print(f"  {i+1}. {node.get('name')} ({node.get('entity_label', 'Unknown')})")
            
            if len(nodes) > 5:
                print(f"  ... and {len(nodes) - 5} more")
            
            print("\nEdges:")
            for i, edge in enumerate(edges[:5]):  # Show only first 5 edges
                source = edge.get('source')
                target = edge.get('target')
                edge_type = edge.get('type')
                print(f"  {i+1}. {source} -[{edge_type}]-> {target}")
            
            if len(edges) > 5:
                print(f"  ... and {len(edges) - 5} more")


if __name__ == "__main__":
    asyncio.run(main()) 