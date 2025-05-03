"""
Neo4j Graph Storage

Provides storage and retrieval functionality for the legal knowledge graph using Neo4j.
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Set, Union
import logging

# Import aioneo4j only if we're not in dry-run mode
try:
    import neo4j
except ImportError:
    neo4j = None

from loguru import logger
from merl_t.config import get_config_manager


class Neo4jGraphStorage:
    """
    Neo4j storage for the legal knowledge graph.
    
    Handles connection, CRUD operations, and graph queries for the legal knowledge graph.
    """
    
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None
    ):
        """
        Initialize the Neo4j storage.
        
        Args:
            uri: Neo4j server URI
            user: Neo4j username
            password: Neo4j password
            database: Neo4j database name
        """
        # Get configuration if not provided
        config = get_config_manager()
        
        self.uri = uri or config.get("neo4j.uri", "neo4j://localhost:7687")
        self.user = user or config.get("neo4j.user", "neo4j")
        self.password = password or config.get("neo4j.password", "neo4j")
        self.database = database or config.get("neo4j.database", "neo4j")
        
        # Will be set in initialize()
        self.driver = None
        self.initialized = False
        
        logger.debug(f"Neo4jGraphStorage initialized with URI: {self.uri}, database: {self.database}")
    
    async def initialize(self) -> None:
        """Initialize the Neo4j connection."""
        if self.initialized:
            return
            
        if neo4j is None:
            raise ImportError("neo4j package is not installed. Please install it with 'pip install neo4j'")
            
        try:
            self.driver = neo4j.GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            
            # Test connection
            await self._test_connection()
            
            self.initialized = True
            logger.info(f"Connected to Neo4j database at {self.uri}")
        except Exception as e:
            logger.error(f"Error connecting to Neo4j: {e}")
            if self.driver:
                self.driver.close()
                self.driver = None
            raise
    
    async def _test_connection(self) -> None:
        """Test the Neo4j connection with a simple query."""
        query = "RETURN 1 AS one"
        
        try:
            result = await self._execute_read(query)
            if not result or result[0]["one"] != 1:
                raise ConnectionError("Connection test failed")
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            raise ConnectionError(f"Failed to connect to Neo4j: {e}")
    
    async def close(self) -> None:
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            self.driver = None
            self.initialized = False
            logger.debug("Neo4j connection closed")
    
    async def _execute_read(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a read-only Cypher query.
        
        Args:
            query: Cypher query
            parameters: Query parameters
            
        Returns:
            Query results as a list of records
        """
        if not self.initialized:
            await self.initialize()
            
        if parameters is None:
            parameters = {}
            
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters)
                records = [dict(record) for record in result]
                return records
        except Exception as e:
            logger.error(f"Error executing read query: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {parameters}")
            raise
    
    async def _execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a write Cypher query.
        
        Args:
            query: Cypher query
            parameters: Query parameters
            
        Returns:
            Query results as a list of records
        """
        if not self.initialized:
            await self.initialize()
            
        if parameters is None:
            parameters = {}
            
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run(query, parameters)
                records = [dict(record) for record in result]
                return records
        except Exception as e:
            logger.error(f"Error executing write query: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {parameters}")
            raise
    
    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a node by ID.
        
        Args:
            node_id: Node ID
            
        Returns:
            Node data or None if not found
        """
        query = """
        MATCH (n {id: $node_id})
        RETURN n
        """
        
        result = await self._execute_read(query, {"node_id": node_id})
        
        if not result:
            return None
            
        return self._process_node_record(result[0]["n"])
    
    def _process_node_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Process a Neo4j node record into a dictionary."""
        # Extract node properties
        node_data = dict(record)
        
        # Add labels if available
        if hasattr(record, "labels"):
            node_data["_labels"] = list(record.labels)
            
        return node_data
    
    async def get_edge(self, source_id: str, target_id: str, relationship_type: str) -> Optional[Dict[str, Any]]:
        """
        Get an edge between two nodes.
        
        Args:
            source_id: Source node ID
            target_id: Target node ID
            relationship_type: Relationship type
            
        Returns:
            Edge data or None if not found
        """
        query = f"""
        MATCH (n1 {{id: $source_id}})-[r:{relationship_type}]->(n2 {{id: $target_id}})
        RETURN r
        """
        
        result = await self._execute_read(query, {
            "source_id": source_id,
            "target_id": target_id
        })
        
        if not result:
            return None
            
        return self._process_relationship_record(result[0]["r"])
    
    def _process_relationship_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Process a Neo4j relationship record into a dictionary."""
        # Extract relationship properties
        rel_data = dict(record)
        
        # Add type if available
        if hasattr(record, "type"):
            rel_data["type"] = record.type
            
        return rel_data
    
    async def get_node_edges(self, node_id: str, relationship_type: Optional[str] = None) -> List[Tuple[str, str, str]]:
        """
        Get outgoing edges for a node.
        
        Args:
            node_id: Node ID
            relationship_type: Optional relationship type filter
            
        Returns:
            List of (source_id, relationship_type, target_id) tuples
        """
        if relationship_type:
            query = f"""
            MATCH (n1 {{id: $node_id}})-[r:{relationship_type}]->(n2)
            RETURN n1.id AS source_id, type(r) as relation_type, n2.id AS target_id
            """
        else:
            query = """
            MATCH (n1 {id: $node_id})-[r]->(n2)
            RETURN n1.id AS source_id, type(r) as relation_type, n2.id AS target_id
            """
        
        result = await self._execute_read(query, {"node_id": node_id})
        
        edges = []
        for record in result:
            source_id = record["source_id"]
            rel_type = record["relation_type"]
            target_id = record["target_id"]
            
            edges.append((source_id, rel_type, target_id))
            
        return edges
    
    async def get_node_neighborhood(self, node_id: str) -> Dict[str, Any]:
        """
        Get the direct neighborhood of a node.
        
        Args:
            node_id: Node ID
            
        Returns:
            Dictionary with nodes and edges
        """
        query = """
        MATCH (n {id: $node_id})
        OPTIONAL MATCH (n)-[r1]->(m1)
        OPTIONAL MATCH (m2)-[r2]->(n)
        RETURN n, collect(distinct r1) as out_rels, collect(distinct m1) as out_nodes,
               collect(distinct r2) as in_rels, collect(distinct m2) as in_nodes
        """
        
        result = await self._execute_read(query, {"node_id": node_id})
        
        if not result:
            return {"nodes": [], "edges": []}
            
        record = result[0]
        
        # Process center node
        center_node = self._process_node_record(record["n"])
        
        # Process outgoing relationships
        out_nodes = []
        out_edges = []
        
        for node in record["out_nodes"]:
            if node is None:
                continue
            out_nodes.append(self._process_node_record(node))
            
        for rel in record["out_rels"]:
            if rel is None:
                continue
            rel_data = self._process_relationship_record(rel)
            source_id = rel.start_id
            target_id = rel.end_id
            
            out_edges.append({
                "source": source_id,
                "target": target_id,
                "type": rel_data.get("type", "RELATED_TO"),
                **rel_data
            })
        
        # Process incoming relationships
        in_nodes = []
        in_edges = []
        
        for node in record["in_nodes"]:
            if node is None:
                continue
            in_nodes.append(self._process_node_record(node))
            
        for rel in record["in_rels"]:
            if rel is None:
                continue
            rel_data = self._process_relationship_record(rel)
            source_id = rel.start_id
            target_id = rel.end_id
            
            in_edges.append({
                "source": source_id,
                "target": target_id,
                "type": rel_data.get("type", "RELATED_TO"),
                **rel_data
            })
        
        # Combine all nodes and edges
        nodes = [center_node] + out_nodes + in_nodes
        edges = out_edges + in_edges
        
        # Deduplicate nodes
        unique_nodes = []
        seen_ids = set()
        
        for node in nodes:
            node_id = node.get("id")
            if node_id not in seen_ids:
                seen_ids.add(node_id)
                unique_nodes.append(node)
        
        # Deduplicate edges
        unique_edges = []
        seen_edges = set()
        
        for edge in edges:
            edge_key = f"{edge['source']}-{edge['type']}-{edge['target']}"
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                unique_edges.append(edge)
        
        return {
            "nodes": unique_nodes,
            "edges": unique_edges
        }
    
    async def get_legal_entity_by_name(self, name: str, entity_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for legal entities by name.
        
        Args:
            name: Entity name or partial name
            entity_type: Optional entity type filter
            
        Returns:
            List of matching entity data
        """
        if entity_type:
            query = f"""
            MATCH (n:{entity_type})
            WHERE n.name CONTAINS $name OR n.id CONTAINS $name
            RETURN n
            LIMIT 10
            """
        else:
            query = """
            MATCH (n)
            WHERE n.name CONTAINS $name OR n.id CONTAINS $name
            RETURN n
            LIMIT 10
            """
        
        result = await self._execute_read(query, {"name": name})
        
        entities = []
        for record in result:
            node_data = self._process_node_record(record["n"])
            entities.append(node_data)
            
        return entities
    
    async def get_all_labels(self) -> List[str]:
        """
        Get all node labels in the graph.
        
        Returns:
            List of label names
        """
        query = """
        CALL db.labels() YIELD label
        RETURN collect(label) AS labels
        """
        
        result = await self._execute_read(query)
        
        if not result:
            return []
            
        return result[0].get("labels", [])
    
    async def get_all_relationship_types(self) -> List[str]:
        """
        Get all relationship types in the graph.
        
        Returns:
            List of relationship type names
        """
        query = """
        CALL db.relationshipTypes() YIELD relationshipType
        RETURN collect(relationshipType) AS types
        """
        
        result = await self._execute_read(query)
        
        if not result:
            return []
            
        return result[0].get("types", [])
    
    async def get_knowledge_graph(
        self,
        node_label: Optional[str] = None,
        depth: int = 2,
        limit: int = 100,
        relation_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get a subgraph by exploring paths from nodes with the given label.
        
        Args:
            node_label: Label to start the exploration from
            depth: Maximum path length
            limit: Maximum number of paths to return
            relation_types: List of relationship types to include
            
        Returns:
            List of paths (each path is a dict with nodes and relationships)
        """
        # Prepare relationship types clause
        rel_clause = ""
        if relation_types:
            rel_types_str = "|".join(f":{rel_type}" for rel_type in relation_types)
            rel_clause = f"[:{rel_types_str}]"
        else:
            rel_clause = ""
        
        # Prepare label clause
        label_clause = f":{node_label}" if node_label else ""
        
        # Query for paths
        query = f"""
        MATCH path = (n{label_clause})-{rel_clause}*1..{depth}-(m)
        RETURN path
        LIMIT {limit}
        """
        
        result = await self._execute_read(query)
        
        paths = []
        for record in result:
            path = record["path"]
            
            # Process nodes and relationships in the path
            nodes = []
            relationships = []
            
            for node in path.nodes:
                nodes.append(self._process_node_record(node))
                
            for rel in path.relationships:
                rel_data = self._process_relationship_record(rel)
                relationships.append({
                    "start_node": {"id": rel.start_node["id"]},
                    "end_node": {"id": rel.end_node["id"]},
                    "type": rel.type,
                    "properties": rel_data
                })
            
            paths.append({
                "nodes": nodes,
                "relationships": relationships
            })
        
        return paths 