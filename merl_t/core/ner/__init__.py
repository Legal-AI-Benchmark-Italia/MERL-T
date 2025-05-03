"""
Legal Named Entity Recognition (NER) module for MERL-T

Provides tools for extracting, managing, and normalizing legal entities.
"""

from .entities import (
    Entity, EntityType, ArticoloCodice, RiferimentoLegge,
    Sentenza, ConcettoGiuridico
)
from .entity_manager import EntityManager
from .preprocessing import TextPreprocessor
from .transformer import TransformerRecognizer
from .normalizer import EntityNormalizer
from .system import NERSystem

__all__ = [
    'Entity', 'EntityType', 'ArticoloCodice', 'RiferimentoLegge',
    'Sentenza', 'ConcettoGiuridico', 'EntityManager', 'TextPreprocessor',
    'TransformerRecognizer', 'EntityNormalizer', 'NERSystem'
] 