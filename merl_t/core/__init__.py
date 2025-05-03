"""
Core components for MERL-T

Contains the core logic for all MERL-T modules including
NER, Knowledge Graph, Vector Database, and LLM interfaces.
"""

from .ner import NERSystem

__all__ = ['NERSystem'] 