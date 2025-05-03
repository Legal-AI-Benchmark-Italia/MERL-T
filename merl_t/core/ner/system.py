"""
Legal NER System

Integrates all NER components into a complete pipeline for legal text analysis.
"""

import json
from typing import Dict, List, Optional, Tuple, Union, Any

from loguru import logger

from .preprocessing import TextPreprocessor
from .transformer import TransformerRecognizer
from .normalizer import EntityNormalizer
from .entity_manager import EntityManager
from .entities import Entity, EntityType


class NERSystem:
    """
    Complete NER system for legal text analysis.
    
    Integrates:
    - Preprocessing
    - Entity recognition
    - Entity normalization
    - Entity management
    """
    
    def __init__(
        self,
        model_name: str = "dbmdz/bert-base-italian-xxl-cased",
        spacy_model: str = "it_core_news_lg",
        use_gpu: bool = True,
        confidence_threshold: float = 0.7,
        canonicalization_enabled: bool = True
    ):
        """
        Initialize the NER system.
        
        Args:
            model_name: Transformer model name or path
            spacy_model: spaCy model name for preprocessing
            use_gpu: Whether to use GPU for transformer inference
            confidence_threshold: Minimum confidence for entity extraction
            canonicalization_enabled: Whether to canonicalize entity text
        """
        logger.info("Initializing NER System")
        
        # Initialize components
        self.preprocessor = TextPreprocessor(
            spacy_model=spacy_model
        )
        
        self.recognizer = TransformerRecognizer(
            model_name=model_name,
            use_gpu=use_gpu,
            confidence_threshold=confidence_threshold
        )
        
        self.normalizer = EntityNormalizer(
            canonicalization_enabled=canonicalization_enabled
        )
        
        self.entity_manager = EntityManager()
        
        logger.info("NER System initialization complete")
    
    def process(self, text: str, doc_id: str = "default") -> Dict[str, Any]:
        """
        Process a text and extract normalized legal entities.
        
        Applies the full NER pipeline:
        1. Preprocessing
        2. Entity recognition
        3. Entity normalization
        4. Entity management
        
        Args:
            text: Input text
            doc_id: Document identifier for entity storage
            
        Returns:
            Dict with processed text, entities, and metadata
        """
        # Clear existing entities for this document
        self.entity_manager.clear_document(doc_id)
        
        # Step 1: Preprocess text
        logger.info(f"Preprocessing text ({len(text)} chars)")
        preproc_result = self.preprocessor.process(text)
        
        normalized_text = preproc_result['normalized_text']
        sentences = preproc_result['sentences']
        legal_references = preproc_result['legal_references']
        
        # Step 2: Recognize entities
        logger.info("Recognizing entities with transformer model")
        recognition_result = self.recognizer.process(normalized_text)
        entities = recognition_result.get('entities', [])
        
        # Step 3: Normalize entities
        logger.info(f"Normalizing {len(entities)} entities")
        normalized_entities = self.normalizer.normalize_all(entities)
        
        # Step 4: Store entities in manager
        entity_ids = self.entity_manager.add_entities(normalized_entities, doc_id)
        
        # Prepare result
        # Map entity_ids to entities for the response
        entity_dict = {
            entity_id: entity.to_dict()
            for entity_id, entity in zip(entity_ids, normalized_entities)
        }
        
        # Group entities by type
        entities_by_type = {}
        for entity_id, entity in zip(entity_ids, normalized_entities):
            entity_type = entity.type.value
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            
            entities_by_type[entity_type].append({
                "id": entity_id,
                **entity.to_dict()
            })
        
        logger.info(f"NER process complete, found {len(normalized_entities)} entities")
        
        return {
            "text": text,
            "normalized_text": normalized_text,
            "sentences": sentences,
            "entity_count": len(normalized_entities),
            "entities": entity_dict,
            "entities_by_type": entities_by_type,
            "legal_references": legal_references,
            "metadata": {
                "doc_id": doc_id,
                "char_count": len(text),
                "sentence_count": len(sentences),
                "model": self.recognizer.model_name,
                "confidence_threshold": self.recognizer.confidence_threshold
            }
        }
    
    def to_json(self, doc_id: str = "default", indent: int = 2) -> str:
        """
        Export entities for a document as JSON.
        
        Args:
            doc_id: Document identifier
            indent: JSON indentation
            
        Returns:
            JSON string with entities
        """
        return self.entity_manager.to_json(doc_id, indent)
    
    def get_entity_by_id(self, entity_id: str, doc_id: str = "default") -> Optional[Dict[str, Any]]:
        """
        Get an entity by ID.
        
        Args:
            entity_id: Entity identifier
            doc_id: Document identifier
            
        Returns:
            Entity as a dictionary, or None if not found
        """
        entity = self.entity_manager.get_entity(entity_id, doc_id)
        return entity.to_dict() if entity else None
    
    def get_entities_by_type(
        self, 
        entity_type: Union[str, EntityType],
        doc_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """
        Get all entities of a specific type.
        
        Args:
            entity_type: Entity type string or enum
            doc_id: Document identifier
            
        Returns:
            List of entity dictionaries
        """
        # Convert string to enum if needed
        if isinstance(entity_type, str):
            try:
                entity_type = EntityType(entity_type)
            except ValueError:
                return []
        
        # Get entities from manager
        entities = self.entity_manager.get_entities_by_type(entity_type, doc_id)
        
        # Convert to dictionaries
        return [
            {"id": entity_id, **entity.to_dict()}
            for entity_id, entity in entities
        ] 