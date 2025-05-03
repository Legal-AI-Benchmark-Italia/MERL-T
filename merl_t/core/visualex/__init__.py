"""
VisuaLex Module

Provides access to Italian legal documents from various sources.
"""

from .client import VisuaLexClient
from .models import Norma, NormaVisitata, ArticleContent, Commentary, SearchResult
from .api.app import NormaController

__all__ = [
    "VisuaLexClient", 
    "Norma", 
    "NormaVisitata", 
    "ArticleContent", 
    "Commentary", 
    "SearchResult",
    "NormaController"
] 