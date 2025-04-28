from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class BaseGraphStorage(ABC):
    """Base class for graph storage implementations"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the graph storage"""
        pass

    @abstractmethod
    async def has_node(self, node_id: str) -> bool:
        """Check if a node exists"""
        pass

    @abstractmethod
    async def has_edge(self, source_node_id: str, target_node_id: str) -> bool:
        """Check if an edge exists"""
        pass

    @abstractmethod
    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a node by ID"""
        pass

    @abstractmethod
    async def get_edge(self, source_node_id: str, target_node_id: str) -> Optional[Dict[str, Any]]:
        """Get an edge by source and target node IDs"""
        pass

    @abstractmethod
    async def get_node_edges(self, source_node_id: str) -> Optional[List[tuple[str, str]]]:
        """Get all edges for a node"""
        pass

    @abstractmethod
    async def upsert_node(self, node_id: str, node_data: Dict[str, Any]) -> None:
        """Insert or update a node"""
        pass

    @abstractmethod
    async def upsert_edge(self, source_node_id: str, target_node_id: str, edge_data: Dict[str, Any]) -> None:
        """Insert or update an edge"""
        pass

    @abstractmethod
    async def delete_node(self, node_id: str) -> None:
        """Delete a node"""
        pass

    @abstractmethod
    async def remove_nodes(self, nodes: List[str]) -> None:
        """Delete multiple nodes"""
        pass

    @abstractmethod
    async def remove_edges(self, edges: List[tuple[str, str]]) -> None:
        """Delete multiple edges"""
        pass

    @abstractmethod
    async def get_all_labels(self) -> List[str]:
        """Get all node labels"""
        pass

    @abstractmethod
    async def get_knowledge_graph(self, node_label: str, max_depth: int = 3, max_nodes: int = 1000) -> Any:
        """Get a subgraph of the knowledge graph"""
        pass

    @abstractmethod
    async def index_done_callback(self) -> bool:
        """Callback after indexing is done"""
        pass

    @abstractmethod
    async def drop(self) -> Dict[str, str]:
        """Drop all graph data"""
        pass 