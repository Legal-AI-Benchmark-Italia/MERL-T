"""
Knowledge Graph Client

Client for accessing the legal knowledge graph stored in Neo4j.
Adapts the original Neo4jGraphStorage class to the new architecture.
"""

import asyncio
from typing import List, Dict, Any, Optional, Union, Tuple

from loguru import logger

from merl_t.config import get_config_manager
from .models import KnowledgeGraphNode, KnowledgeGraphEdge, KnowledgeSubgraph


class KnowledgeGraphClient:
    """
    Client for accessing the legal knowledge graph.
    
    Provides methods to:
    - Search for entities by name and type
    - Get entity details by ID
    - Get relationships for an entity
    - Get subgraphs and neighborhoods
    """
    
    def __init__(self):
        """Initialize the Knowledge Graph client."""
        self.config = get_config_manager()
        
        # Neo4j storage instance will be initialized lazily
        self._storage = None
        
        # Configure cache parameters
        self.cache_enabled = self.config.get("knowledge_graph.cache.enabled", True)
        self.cache_ttl = self.config.get("knowledge_graph.cache.ttl", 3600)  # 1 hour by default
        
        # In-memory cache
        self._cache = {}
    
    async def _get_storage(self):
        """
        Get or create a Neo4jGraphStorage instance.
        
        Returns:
            Neo4jGraphStorage instance
        """
        if self._storage is None:
            # Import here to avoid circular imports
            from merl_t.core.kg.storage import Neo4jGraphStorage
            
            # Get connection parameters from config
            neo4j_params = self.config.get_neo4j_connection_params()
            
            # Create instance
            self._storage = Neo4jGraphStorage(
                uri=neo4j_params.get('uri'),
                user=neo4j_params.get('user'),
                password=neo4j_params.get('password'),
                database=neo4j_params.get('database')
            )
            
            # Initialize
            await self._storage.initialize()
        
        return self._storage
    
    async def close(self):
        """Close the client and Neo4j connection."""
        if self._storage:
            await self._storage.close()
            self._storage = None
    
    async def search_entities(
        self, 
        query: str, 
        entity_type: Optional[str] = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for entities by name.
        
        Args:
            query: Search query (entity name or part of it)
            entity_type: Entity type to filter by
            limit: Maximum number of results
            
        Returns:
            List of entity data
        """
        # Check cache
        cache_key = f"search_entities_{query}_{entity_type}_{limit}"
        if self.cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]
        
        storage = await self._get_storage()
        
        try:
            # Use the legal_entity_by_name method from Neo4jGraphStorage
            entities = await storage.get_legal_entity_by_name(query, entity_type)
            
            # Limit results
            results = entities[:limit]
            
            # Cache results
            if self.cache_enabled:
                self._cache[cache_key] = results
            
            return results
        except Exception as e:
            logger.error(f"Error searching entities: {e}")
            return []
    
    async def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an entity by ID.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Entity data or None if not found
        """
        # Check cache
        cache_key = f"entity_{entity_id}"
        if self.cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]
        
        storage = await self._get_storage()
        
        try:
            # Use the get_node method from Neo4jGraphStorage
            node = await storage.get_node(entity_id)
            
            if node:
                # Cache result
                if self.cache_enabled:
                    self._cache[cache_key] = node
                
                return node
            
            return None
        except Exception as e:
            logger.error(f"Error getting entity {entity_id}: {e}")
            return None
    
    async def get_relationships(
        self, 
        entity_id: str, 
        relationship_type: Optional[str] = None,
        direction: str = "both",
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get relationships for an entity.
        
        Args:
            entity_id: Entity ID
            relationship_type: Relationship type filter
            direction: Direction of relationships ("incoming", "outgoing", "both")
            limit: Maximum number of relationships
            
        Returns:
            List of relationship data
        """
        # Check cache
        cache_key = f"relationships_{entity_id}_{relationship_type}_{direction}_{limit}"
        if self.cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]
        
        storage = await self._get_storage()
        
        try:
            # For outgoing relationships, use get_node_edges
            outgoing = []
            if direction in ["outgoing", "both"]:
                edges = await storage.get_node_edges(entity_id, relationship_type)
                for merl_t_id, rel_type, tgt_id in edges:
                    edge_data = await storage.get_edge(merl_t_id, tgt_id, rel_type)
                    if edge_data:
                        outgoing.append({
                            "source": merl_t_id,
                            "target": tgt_id,
                            "type": rel_type,
                            "direction": "outgoing",
                            **edge_data
                        })
            
            # For incoming relationships, use a custom query
            incoming = []
            if direction in ["incoming", "both"]:
                # We need to use a custom query since get_node_edges only returns outgoing
                if relationship_type:
                    query = f"""
                    MATCH (n2)-[r:{relationship_type}]->(n1 {{id: $node_id}})
                    RETURN n2.id AS source_id, type(r) as relation_type, n1.id AS target_id
                    """
                else:
                    query = """
                    MATCH (n2)-[r]->(n1 {id: $node_id})
                    RETURN n2.id AS source_id, type(r) as relation_type, n1.id AS target_id
                    """
                
                result = await storage._execute_read(query, {"node_id": entity_id})
                
                for record in result:
                    merl_t_id = record["source_id"]
                    rel_type = record["relation_type"]
                    tgt_id = record["target_id"]
                    
                    edge_data = await storage.get_edge(merl_t_id, tgt_id, rel_type)
                    if edge_data:
                        incoming.append({
                            "source": merl_t_id,
                            "target": tgt_id,
                            "type": rel_type,
                            "direction": "incoming",
                            **edge_data
                        })
            
            # Combine outgoing and incoming
            relationships = outgoing + incoming
            
            # Sort by weight if available
            relationships.sort(key=lambda x: x.get("weight", 0), reverse=True)
            
            # Limit results
            results = relationships[:limit]
            
            # Cache results
            if self.cache_enabled:
                self._cache[cache_key] = results
            
            return results
        except Exception as e:
            logger.error(f"Error getting relationships for entity {entity_id}: {e}")
            return []
    
    async def get_neighborhood(
        self, 
        entity_id: str, 
        depth: int = 1, 
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get a neighborhood subgraph for an entity.
        
        Args:
            entity_id: Entity ID
            depth: Maximum path length (1 = direct neighbors only)
            limit: Maximum number of nodes
            
        Returns:
            Subgraph data (nodes and edges)
        """
        # Check cache
        cache_key = f"neighborhood_{entity_id}_{depth}_{limit}"
        if self.cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]
        
        storage = await self._get_storage()
        
        try:
            if depth == 1:
                # For depth 1, we can use the get_node_neighborhood method
                neighborhood = await storage.get_node_neighborhood(entity_id)
                
                if not neighborhood:
                    return {"nodes": [], "edges": [], "is_truncated": False}
                
                # Limit the results if needed
                nodes = neighborhood["nodes"]
                edges = neighborhood["edges"]
                
                if len(nodes) > limit:
                    # Keep the seed node and limit the neighbors
                    seed_node = next((n for n in nodes if n["id"] == entity_id), None)
                    other_nodes = [n for n in nodes if n["id"] != entity_id]
                    
                    limited_nodes = [seed_node] if seed_node else []
                    limited_nodes.extend(other_nodes[:limit - 1] if seed_node else other_nodes[:limit])
                    
                    # Keep only edges between nodes in the limited set
                    node_ids = {n["id"] for n in limited_nodes}
                    limited_edges = [e for e in edges if e["source"] in node_ids and e["target"] in node_ids]
                    
                    return {
                        "nodes": limited_nodes,
                        "edges": limited_edges,
                        "is_truncated": True
                    }
                
                # Cache results
                if self.cache_enabled:
                    self._cache[cache_key] = neighborhood
                
                return neighborhood
            else:
                # For larger depths, we need to use the get_knowledge_graph method
                paths = await storage.get_knowledge_graph(
                    node_label=None,  # We'll start from a specific node, not a label
                    depth=depth,
                    limit=limit
                )
                
                # Process the subgraph to include only paths containing our seed node
                subgraph = KnowledgeSubgraph()
                nodes_set = set()
                edges_set = set()
                
                for path in paths:
                    # Check if this path contains our seed node
                    path_nodes = path.get("nodes", [])
                    path_rels = path.get("relationships", [])
                    
                    has_seed = any(n["id"] == entity_id for n in path_nodes)
                    
                    if has_seed:
                        # Add nodes
                        for node_data in path_nodes:
                            if node_data["id"] not in nodes_set:
                                nodes_set.add(node_data["id"])
                                
                                # Create a node object
                                node = KnowledgeGraphNode(
                                    id=node_data["id"],
                                    name=node_data.get("name", node_data["id"]),
                                    entity_label=node_data.get("_labels", ["Node"])[0],
                                    description=node_data.get("description", ""),
                                    properties=node_data
                                )
                                
                                subgraph.add_node(node)
                        
                        # Add relationships
                        for rel_data in path_rels:
                            merl_t_id = rel_data["start_node"]["id"]
                            tgt_id = rel_data["end_node"]["id"]
                            rel_type = rel_data["type"]
                            
                            edge_key = f"{merl_t_id}-{rel_type}-{tgt_id}"
                            
                            if edge_key not in edges_set:
                                edges_set.add(edge_key)
                                
                                # Create an edge object
                                edge = KnowledgeGraphEdge(
                                    source_id=merl_t_id,
                                    target_id=tgt_id,
                                    relationship_type=rel_type,
                                    description=rel_data.get("description", ""),
                                    weight=rel_data.get("weight", 1.0),
                                    properties=rel_data["properties"]
                                )
                                
                                subgraph.add_edge(edge)
                
                # Convert to dictionary
                subgraph_dict = subgraph.to_dict()
                
                # Set truncated flag if we hit the limit
                subgraph_dict["is_truncated"] = len(paths) >= limit
                
                # Cache results
                if self.cache_enabled:
                    self._cache[cache_key] = subgraph_dict
                
                return subgraph_dict
        except Exception as e:
            logger.error(f"Error getting neighborhood for entity {entity_id}: {e}")
            return {"nodes": [], "edges": [], "is_truncated": False} 