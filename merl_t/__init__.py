"""
MERL-T: Multi-Expert Retrieval Legal Transformer

A framework AI specializzato per il diritto italiano,
che integra componenti come Knowledge Graph, database vettoriali
e API esterne utilizzando architetture MCP e A2A.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("merl-t")
except PackageNotFoundError:
    # package is not installed
    __version__ = "0.1.0.dev"

# Import key components for easier access
from .core.ner import NERSystem
from .core.visualex import VisuaLexClient, Norma, NormaVisitata
from .core.kg import KnowledgeGraphClient, KnowledgeGraphNode, KnowledgeGraphEdge
from .core.annotation import AnnotationClient
from .mcp import BaseMCPServer, BaseMCPHost
from .mcp.servers import NerServer, VisuaLexServer, KnowledgeGraphServer, AnnotationServer
from .a2a import BaseAgent
from .orchestrator import Orchestrator

__all__ = [
    'NERSystem', 'BaseMCPServer', 'BaseMCPHost', 
    'NerServer', 'VisuaLexServer', 'KnowledgeGraphServer', 'BaseAgent', 'Orchestrator',
    'VisuaLexClient', 'Norma', 'NormaVisitata',
    'KnowledgeGraphClient', 'KnowledgeGraphNode', 'KnowledgeGraphEdge'
] 