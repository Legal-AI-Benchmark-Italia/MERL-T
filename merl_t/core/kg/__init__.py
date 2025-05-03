"""
Knowledge Graph

Provides access to the legal knowledge graph.
"""

from .client import KnowledgeGraphClient
from .models import KnowledgeGraphNode, KnowledgeGraphEdge, KnowledgeSubgraph
from .storage import Neo4jGraphStorage
from .extractor import extract_entities
from .utils import apply_kg_changes, create_node_centric_chunks

__all__ = [
    "KnowledgeGraphClient",
    "KnowledgeGraphNode",
    "KnowledgeGraphEdge",
    "KnowledgeSubgraph",
    "Neo4jGraphStorage",
    "extract_entities",
    "apply_kg_changes",
    "create_node_centric_chunks"
] 