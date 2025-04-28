from dataclasses import dataclass
from typing import List, Dict, Any

@dataclass
class KnowledgeGraphNode:
    id: str
    labels: List[str]
    properties: Dict[str, Any]

@dataclass
class KnowledgeGraphEdge:
    id: str
    type: str
    source: str
    target: str
    properties: Dict[str, Any]

@dataclass
class KnowledgeGraph:
    nodes: List[KnowledgeGraphNode] = None
    edges: List[KnowledgeGraphEdge] = None
    is_truncated: bool = False

    def __post_init__(self):
        if self.nodes is None:
            self.nodes = []
        if self.edges is None:
            self.edges = [] 