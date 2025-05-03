"""
Entity Manager for Legal NER

Manages the creation, storage, and retrieval of legal entities.
Supports entity deduplication, validation, and normalization.
"""

import json
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Iterator, Callable

from loguru import logger

from .entities import (
    Entity, EntityType, ArticoloCodice, RiferimentoLegge, 
    Sentenza, ConcettoGiuridico
)


class EntityManager:
    """
    Manager for legal entities identified during NER.
    
    Responsibilities:
    - Store and retrieve entities
    - Deduplicate entities
    - Resolve entity conflicts
    - Validate entity structure
    - Normalize entity attributes
    """
    
    def __init__(self):
        """Initialize the entity manager."""
        # Main entity storage, mapping doc_id -> entity_id -> entity
        self._entities: Dict[str, Dict[str, Entity]] = defaultdict(dict)
        
        # Index by type for faster retrieval
        self._type_index: Dict[str, Dict[EntityType, List[str]]] = defaultdict(lambda: defaultdict(list))
        
        # Entity counter for unique IDs
        self._counter = 0
        
        logger.info("EntityManager initialized")
    
    def _generate_entity_id(self) -> str:
        """Generate a unique entity ID."""
        self._counter += 1
        return f"ent_{self._counter}"
    
    def add_entity(
        self,
        entity: Entity,
        doc_id: str = "default",
        dedup: bool = True
    ) -> str:
        """
        Add an entity to the manager.
        
        Args:
            entity: The entity to add
            doc_id: Document identifier
            dedup: Whether to deduplicate against existing entities
            
        Returns:
            The ID of the added entity
        """
        # Check for duplicates if requested
        if dedup and self._is_duplicate(entity, doc_id):
            # Find the duplicate entity
            for ent_id, existing in self._entities[doc_id].items():
                if self._entities_match(entity, existing):
                    logger.debug(f"Skipping duplicate entity: {entity.text} ({entity.type})")
                    return ent_id
        
        # Generate a new ID and store the entity
        entity_id = self._generate_entity_id()
        self._entities[doc_id][entity_id] = entity
        
        # Update the type index
        self._type_index[doc_id][entity.type].append(entity_id)
        
        logger.debug(f"Added entity {entity_id}: {entity.text} ({entity.type})")
        return entity_id
    
    def add_entities(
        self,
        entities: List[Entity],
        doc_id: str = "default",
        dedup: bool = True
    ) -> List[str]:
        """
        Add multiple entities at once.
        
        Args:
            entities: List of entities to add
            doc_id: Document identifier
            dedup: Whether to deduplicate against existing entities
            
        Returns:
            List of entity IDs
        """
        return [self.add_entity(entity, doc_id, dedup) for entity in entities]
    
    def get_entity(self, entity_id: str, doc_id: str = "default") -> Optional[Entity]:
        """
        Get an entity by ID.
        
        Args:
            entity_id: Entity identifier
            doc_id: Document identifier
            
        Returns:
            The entity or None if not found
        """
        return self._entities.get(doc_id, {}).get(entity_id)
    
    def get_entities_by_type(
        self,
        entity_type: EntityType,
        doc_id: str = "default"
    ) -> List[Tuple[str, Entity]]:
        """
        Get all entities of a specific type.
        
        Args:
            entity_type: The entity type to filter by
            doc_id: Document identifier
            
        Returns:
            List of (entity_id, entity) tuples
        """
        entity_ids = self._type_index.get(doc_id, {}).get(entity_type, [])
        return [(ent_id, self._entities[doc_id][ent_id]) for ent_id in entity_ids]
    
    def get_all_entities(self, doc_id: str = "default") -> List[Tuple[str, Entity]]:
        """
        Get all entities for a document.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            List of (entity_id, entity) tuples
        """
        return list(self._entities.get(doc_id, {}).items())
    
    def remove_entity(self, entity_id: str, doc_id: str = "default") -> bool:
        """
        Remove an entity by ID.
        
        Args:
            entity_id: Entity identifier
            doc_id: Document identifier
            
        Returns:
            True if removed, False if not found
        """
        if doc_id not in self._entities or entity_id not in self._entities[doc_id]:
            return False
        
        # Get the entity to remove from the type index
        entity = self._entities[doc_id][entity_id]
        
        # Remove from type index
        if entity.type in self._type_index[doc_id]:
            if entity_id in self._type_index[doc_id][entity.type]:
                self._type_index[doc_id][entity.type].remove(entity_id)
        
        # Remove the entity
        del self._entities[doc_id][entity_id]
        
        logger.debug(f"Removed entity {entity_id}")
        return True
    
    def clear_document(self, doc_id: str = "default") -> int:
        """
        Remove all entities for a document.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Number of entities removed
        """
        count = len(self._entities.get(doc_id, {}))
        if doc_id in self._entities:
            del self._entities[doc_id]
        if doc_id in self._type_index:
            del self._type_index[doc_id]
        
        logger.info(f"Cleared {count} entities for document {doc_id}")
        return count
    
    def _is_duplicate(self, entity: Entity, doc_id: str = "default") -> bool:
        """
        Check if an entity is a duplicate of an existing one.
        
        Args:
            entity: Entity to check
            doc_id: Document identifier
            
        Returns:
            True if a duplicate exists
        """
        for existing in self._entities.get(doc_id, {}).values():
            if self._entities_match(entity, existing):
                return True
        return False
    
    def _entities_match(self, entity1: Entity, entity2: Entity) -> bool:
        """
        Check if two entities match (are duplicates).
        
        Args:
            entity1: First entity
            entity2: Second entity
            
        Returns:
            True if entities match
        """
        # Different types can't match
        if entity1.type != entity2.type:
            return False
        
        # Check for exact span match
        if (entity1.start_char == entity2.start_char and 
            entity1.end_char == entity2.end_char):
            return True
        
        # Check for overlapping spans with same text
        if (entity1.text.lower() == entity2.text.lower() and
            max(entity1.start_char, entity2.start_char) < min(entity1.end_char, entity2.end_char)):
            return True
        
        return False
    
    def to_dict(self, doc_id: str = "default") -> Dict[str, Any]:
        """
        Convert all entities for a document to a dictionary.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Dictionary of entity data
        """
        return {
            entity_id: entity.to_dict() 
            for entity_id, entity in self._entities.get(doc_id, {}).items()
        }
    
    def to_json(self, doc_id: str = "default", indent: int = 2) -> str:
        """
        Convert all entities for a document to JSON.
        
        Args:
            doc_id: Document identifier
            indent: JSON indentation
            
        Returns:
            JSON string
        """
        return json.dumps(self.to_dict(doc_id), indent=indent)
    
    @staticmethod
    def create_entity_from_dict(data: Dict[str, Any]) -> Entity:
        """
        Create an entity from a dictionary.
        
        Args:
            data: Entity data dictionary
            
        Returns:
            Entity instance
        """
        entity_type = EntityType(data["type"])
        
        # Create specialized entity types if we have the necessary data
        if entity_type == EntityType.ARTICOLO_CODICE and "metadata" in data:
            metadata = data.get("metadata", {})
            return ArticoloCodice(
                text=data["text"],
                start_char=data["start_char"],
                end_char=data["end_char"],
                score=data.get("score", 1.0),
                numero=metadata.get("numero", ""),
                codice=metadata.get("codice", ""),
                comma=metadata.get("comma")
            )
        elif entity_type in (EntityType.LEGGE, EntityType.ARTICOLO_LEGGE) and "metadata" in data:
            metadata = data.get("metadata", {})
            return RiferimentoLegge(
                text=data["text"],
                start_char=data["start_char"],
                end_char=data["end_char"],
                score=data.get("score", 1.0),
                anno=metadata.get("anno", ""),
                numero=metadata.get("numero", ""),
                tipo=metadata.get("tipo", "legge"),
                articolo=metadata.get("articolo")
            )
        elif entity_type == EntityType.SENTENZA and "metadata" in data:
            metadata = data.get("metadata", {})
            return Sentenza(
                text=data["text"],
                start_char=data["start_char"],
                end_char=data["end_char"],
                score=data.get("score", 1.0),
                anno=metadata.get("anno", ""),
                organo=metadata.get("organo", ""),
                numero=metadata.get("numero", ""),
                sezione=metadata.get("sezione")
            )
        else:
            # Generic entity
            return Entity(
                text=data["text"],
                type=entity_type,
                start_char=data["start_char"],
                end_char=data["end_char"],
                score=data.get("score", 1.0),
                metadata=data.get("metadata", {})
            )
    
    def from_dict(self, data: Dict[str, Dict[str, Any]], doc_id: str = "default") -> None:
        """
        Load entities from a dictionary.
        
        Args:
            data: Dictionary mapping entity IDs to entity data
            doc_id: Document identifier
        """
        for entity_id, entity_data in data.items():
            entity = self.create_entity_from_dict(entity_data)
            self._entities[doc_id][entity_id] = entity
            self._type_index[doc_id][entity.type].append(entity_id)
        
        logger.info(f"Loaded {len(data)} entities for document {doc_id}")
    
    def from_json(self, json_data: str, doc_id: str = "default") -> None:
        """
        Load entities from a JSON string.
        
        Args:
            json_data: JSON string
            doc_id: Document identifier
        """
        data = json.loads(json_data)
        self.from_dict(data, doc_id)
        
    def __len__(self) -> int:
        """Get the total number of entities across all documents."""
        return sum(len(doc_entities) for doc_entities in self._entities.values())
    
    def document_count(self, doc_id: str = "default") -> int:
        """
        Get the number of entities for a specific document.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Number of entities
        """
        return len(self._entities.get(doc_id, {})) 