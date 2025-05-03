"""
Transformer-based NER for Legal Entities

Provides a transformer-based recognizer for legal entities using Hugging Face models.
"""

from typing import Dict, List, Optional, Tuple, Union, Any, Set

import torch
from transformers import (
    AutoTokenizer, AutoModelForTokenClassification, 
    PreTrainedTokenizer, PreTrainedModel,
    pipeline
)
from loguru import logger

from .entities import Entity, EntityType


class TransformerRecognizer:
    """
    NER processor using transformer models from Hugging Face.
    
    Supports:
    - Fine-tuned transformer models for token classification
    - Token-to-entity alignment and reconstruction
    - Confidence scoring and filtering
    """
    
    def __init__(
        self,
        model_name: str = "dbmdz/bert-base-italian-xxl-cased",
        device: str = None,
        confidence_threshold: float = 0.75,
        use_gpu: bool = True,
        max_length: int = 512
    ):
        """
        Initialize the transformer recognizer.
        
        Args:
            model_name: Hugging Face model name or path
            device: Device to run the model on (None for auto-detection)
            confidence_threshold: Minimum confidence score for entity acceptance
            use_gpu: Whether to use GPU if available
            max_length: Maximum sequence length for the model
        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.max_length = max_length
        
        # Determine device
        if device is None:
            device = "cuda" if torch.cuda.is_available() and use_gpu else "cpu"
        self.device = device
        
        # Entity label mapping (transformer label -> EntityType)
        self.label_mapping = {
            "B-LEGGE": EntityType.LEGGE,
            "I-LEGGE": EntityType.LEGGE,
            "B-ARTICOLO_LEGGE": EntityType.ARTICOLO_LEGGE,
            "I-ARTICOLO_LEGGE": EntityType.ARTICOLO_LEGGE,
            "B-ARTICOLO_CODICE": EntityType.ARTICOLO_CODICE,
            "I-ARTICOLO_CODICE": EntityType.ARTICOLO_CODICE,
            "B-SENTENZA": EntityType.SENTENZA,
            "I-SENTENZA": EntityType.SENTENZA,
            "B-PRINCIPIO_GIURIDICO": EntityType.PRINCIPIO_GIURIDICO,
            "I-PRINCIPIO_GIURIDICO": EntityType.PRINCIPIO_GIURIDICO,
            "B-ISTITUTO_GIURIDICO": EntityType.ISTITUTO_GIURIDICO,
            "I-ISTITUTO_GIURIDICO": EntityType.ISTITUTO_GIURIDICO,
            "B-TERMINE_GIURIDICO": EntityType.TERMINE_GIURIDICO,
            "I-TERMINE_GIURIDICO": EntityType.TERMINE_GIURIDICO,
        }
        
        try:
            logger.info(f"Loading transformer model {model_name} on {device}")
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForTokenClassification.from_pretrained(model_name)
            
            # Move model to device
            self.model.to(device)
            
            # Create NER pipeline
            self.ner_pipeline = pipeline(
                "token-classification",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if device == "cuda" else -1,
                aggregation_strategy="simple"  # Merge tokens with same entity
            )
            
            logger.info(f"Transformer model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load transformer model: {e}")
            self.tokenizer = None
            self.model = None
            self.ner_pipeline = None
    
    def is_ready(self) -> bool:
        """Check if the model is ready to use."""
        return self.model is not None and self.tokenizer is not None
    
    def _map_to_entity_type(self, label: str) -> Optional[EntityType]:
        """
        Map a transformer label to an EntityType.
        
        Args:
            label: Label from the transformer model
            
        Returns:
            Corresponding EntityType or None
        """
        # Remove 'B-' or 'I-' prefix if needed
        if "-" in label:
            _, entity_label = label.split("-", 1)
            try:
                return EntityType(entity_label)
            except ValueError:
                return self.label_mapping.get(label)
        else:
            try:
                return EntityType(label)
            except ValueError:
                return None
    
    def process_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Process text with the transformer model and extract entities.
        
        Args:
            text: Input text
            
        Returns:
            List of raw entity dictionaries
        """
        if not self.is_ready():
            logger.error("Transformer model is not initialized")
            return []
        
        try:
            # Process with NER pipeline
            results = self.ner_pipeline(text)
            
            # Filter by confidence threshold
            filtered_results = [
                r for r in results 
                if r.get("score", 0) >= self.confidence_threshold
            ]
            
            logger.debug(f"Transformer identified {len(filtered_results)} entities")
            return filtered_results
        except Exception as e:
            logger.error(f"Error in transformer processing: {e}")
            return []
    
    def _create_entity(
        self, 
        entity_data: Dict[str, Any], 
        text: str
    ) -> Optional[Entity]:
        """
        Create an Entity from transformer output.
        
        Args:
            entity_data: Entity data from transformer
            text: Original text
            
        Returns:
            Entity instance or None on error
        """
        try:
            # Extract entity text and position
            entity_text = entity_data.get("word", "")
            start_idx = entity_data.get("start")
            end_idx = entity_data.get("end")
            score = entity_data.get("score", 1.0)
            
            # Map label to entity type
            label = entity_data.get("entity_group", "")
            entity_type = self._map_to_entity_type(label)
            
            if entity_type is None:
                logger.warning(f"Unknown entity type: {label}")
                return None
            
            # Create entity
            return Entity(
                text=entity_text,
                type=entity_type,
                start_char=start_idx,
                end_char=end_idx,
                score=score
            )
        except Exception as e:
            logger.error(f"Error creating entity: {e}")
            return None
    
    def extract_entities(self, text: str) -> List[Entity]:
        """
        Extract entities from text.
        
        Args:
            text: Input text
            
        Returns:
            List of Entity instances
        """
        # Process text with transformer
        entity_data = self.process_text(text)
        
        # Convert to Entity instances
        entities = []
        for item in entity_data:
            entity = self._create_entity(item, text)
            if entity:
                entities.append(entity)
        
        return entities
    
    def process(self, text: str) -> Dict[str, Any]:
        """
        Process text and return structured results.
        
        Args:
            text: Input text
            
        Returns:
            Dict with extracted entities and metadata
        """
        # Extract entities
        entities = self.extract_entities(text)
        
        # Prepare result
        return {
            "entities": entities,
            "metadata": {
                "model": self.model_name,
                "confidence_threshold": self.confidence_threshold,
                "entity_count": len(entities)
            }
        } 