"""
Knowledge Graph Utilities

Utility functions for manipulating the legal knowledge graph.
"""

import os
import re
import random
from pathlib import Path
import logging
from typing import Dict, Any, List, Optional

from loguru import logger
from merl_t.config import get_config_manager
from merl_t.core.kg.storage import Neo4jGraphStorage
from merl_t.core.annotation.db_manager import AnnotationDBManager

async def apply_kg_changes(proposal_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply changes to the knowledge graph based on an approved proposal.
    
    Args:
        proposal_type: Type of proposal ('add', 'modify', 'delete')
        data: Data for the change (nodes or relationships)
        
    Returns:
        dict: Result of the operation
    """
    try:
        # Initialize the graph storage
        graph_storage = Neo4jGraphStorage()
        await graph_storage.initialize()
        
        result = {"success": False, "message": "", "details": {}}
        
        if proposal_type == 'add':
            # Add nodes or relationships
            if 'nodes' in data:
                # Add nodes
                for node in data['nodes']:
                    node_id = node.get('id')
                    if not node_id:
                        continue
                    await graph_storage.upsert_node(node_id, node)
                result['details']['added_nodes'] = len(data['nodes'])
                result['success'] = True
                
            if 'edges' in data:
                # Add relationships
                for edge in data['edges']:
                    source_id = edge.get('source')
                    target_id = edge.get('target')
                    if not source_id or not target_id:
                        continue
                    await graph_storage.upsert_edge(source_id, target_id, edge)
                result['details']['added_edges'] = len(data['edges'])
                result['success'] = True
                
        elif proposal_type == 'modify':
            # Modify nodes or relationships
            if 'nodes' in data:
                # Modify nodes
                for node in data['nodes']:
                    node_id = node.get('id')
                    if not node_id:
                        continue
                    await graph_storage.upsert_node(node_id, node)
                result['details']['updated_nodes'] = len(data['nodes'])
                result['success'] = True
                
            if 'edges' in data:
                # Modify relationships
                for edge in data['edges']:
                    source_id = edge.get('source')
                    target_id = edge.get('target')
                    if not source_id or not target_id:
                        continue
                    await graph_storage.upsert_edge(source_id, target_id, edge)
                result['details']['updated_edges'] = len(data['edges'])
                result['success'] = True
                
        elif proposal_type == 'delete':
            # Delete nodes or relationships
            if 'nodes' in data:
                # Delete nodes
                for node in data['nodes']:
                    node_id = node.get('id')
                    if not node_id:
                        continue
                    await graph_storage.delete_node(node_id)
                result['details']['deleted_nodes'] = len(data['nodes'])
                result['success'] = True
                
            if 'edges' in data:
                # Delete relationships
                edges_to_delete = []
                for edge in data['edges']:
                    source_id = edge.get('source')
                    target_id = edge.get('target')
                    relation_type = edge.get('type')
                    if not source_id or not target_id:
                        continue
                    edges_to_delete.append((source_id, relation_type, target_id))
                
                if edges_to_delete:
                    await graph_storage.remove_edges(edges_to_delete)
                    result['details']['deleted_edges'] = len(edges_to_delete)
                    result['success'] = True
        else:
            result['message'] = f"Unsupported proposal type: {proposal_type}"
            
        if result['success']:
            result['message'] = "Changes successfully applied to the graph"
        
        # Close connection
        await graph_storage.close()
        
        return result
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Error applying changes to graph: {e}\n{error_details}")
        return {
            "success": False,
            "message": f"Error applying changes: {str(e)}",
            "details": {"error_trace": error_details}
        }

async def create_node_centric_chunks(
    num_chunks: int = 10, 
    seed_label: str = 'Norma', 
    user_id: str = 'system', 
    force_recreate: bool = False
) -> Dict[str, int]:
    """
    Create validation chunks based on 1-hop neighborhood of seed nodes.
    
    Args:
        num_chunks: Number of chunks to create
        seed_label: Label of seed nodes to use
        user_id: User ID to associate with created chunks
        force_recreate: Whether to recreate chunks that already exist
        
    Returns:
        Dict with stats about created chunks
    """
    logger.info(f"Starting creation of {num_chunks} node-centric chunks based on label '{seed_label}'.")
    
    created_count = 0
    skipped_count = 0
    error_count = 0
    
    # Setup connections
    config_manager = get_config_manager()
    neo4j_params = config_manager.get_neo4j_connection_params()
    backup_dir = config_manager.get('database.backup_dir', 'data/backups')
    
    # Use context managers for connections
    graph_storage = Neo4jGraphStorage(**neo4j_params)
    await graph_storage.initialize()
    
    try:
        # Ensure paths are absolute or relative to project root if needed
        project_root = Path(__file__).resolve().parent.parent.parent
        backup_dir = os.path.join(project_root, backup_dir)
        
        # Initialize AnnotationDBManager
        db_manager = AnnotationDBManager()
        
        try:
            # 1. Get potential seed node IDs
            logger.debug(f"Retrieving seed node IDs with label: {seed_label}")
            # Ensure label is safe for query
            safe_seed_label = re.sub(r'[^a-zA-Z0-9_]', '', seed_label)
            if not safe_seed_label:
                logger.error("Invalid seed label after sanitization.")
                return {"created": 0, "skipped": 0, "errors": 1}
                
            seed_query = f"MATCH (n:{safe_seed_label}) RETURN n.id as id"
            seed_records = await graph_storage._execute_read(seed_query)
            all_seed_ids = [record["id"] for record in seed_records if record["id"]]
            
            if not all_seed_ids:
                logger.warning(f"No nodes found with label '{safe_seed_label}' to generate chunks.")
                return {"created": 0, "skipped": 0, "errors": 0}
            
            logger.info(f"Found {len(all_seed_ids)} potential seed nodes.")
            
            # 2. Sample and create chunks
            potential_seeds = random.sample(all_seed_ids, min(num_chunks * 2, len(all_seed_ids)))
            
            for seed_id in potential_seeds:
                if created_count >= num_chunks:
                    break # Reached target number
                    
                try:
                    # 3. Check for existing chunk
                    if not force_recreate and db_manager.check_chunk_exists_for_seed(seed_id):
                        logger.debug(f"Chunk for seed {seed_id} already exists, skipped.")
                        skipped_count += 1
                        continue
                    
                    # 4. Get neighborhood data
                    logger.debug(f"Getting neighborhood for seed: {seed_id}")
                    neighborhood_data = await graph_storage.get_node_neighborhood(seed_id)
                    
                    if not neighborhood_data:
                        logger.warning(f"Could not retrieve neighborhood for {seed_id}, chunk not created.")
                        error_count += 1
                        continue
                        
                    # 5. Format and save chunk
                    seed_node_info = next((n for n in neighborhood_data["nodes"] if n["id"] == seed_id), None)
                    title = f"Neighborhood of {safe_seed_label}: {seed_node_info.get('name', seed_id) if seed_node_info else seed_id}"
                    description = f"Chunk to validate node {seed_id} and its direct connections."
                    
                    chunk_payload = {
                        "title": title,
                        "description": description,
                        "chunk_type": "subgraph",
                        "data": neighborhood_data,
                        "status": "pending",
                        # 'created_by' will be set by save_graph_chunk if user_id is passed
                    }
                    
                    logger.debug(f"Saving chunk for seed: {seed_id}")
                    saved_chunk_id = db_manager.save_graph_chunk(chunk_payload, user_id=user_id, seed_node_id=seed_id)
                    
                    if saved_chunk_id:
                        logger.info(f"Chunk {saved_chunk_id} created for seed {seed_id}")
                        created_count += 1
                    else:
                        logger.error(f"Error saving chunk for seed {seed_id}")
                        error_count += 1
                        
                except Exception as e_inner:
                    logger.error(f"Error creating chunk for seed {seed_id}: {e_inner}")
                    logger.exception(e_inner)
                    error_count += 1
        
        except Exception as e_outer:
            logger.error(f"Error during chunk creation process: {e_outer}")
            logger.exception(e_outer)
            error_count += 1 # Count general errors too
        
    finally:
        # Close the Neo4j connection
        await graph_storage.close()
            
    logger.info(f"Chunk creation completed. Created: {created_count}, Skipped: {skipped_count}, Errors: {error_count}")
    return {"created": created_count, "skipped": skipped_count, "errors": error_count} 