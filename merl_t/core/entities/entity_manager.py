"""
Entity Manager

Manages entity types for annotation and NER tasks.
"""

import os
import json
import sqlite3
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
import logging

# Configure logging
logger = logging.getLogger("entity_manager")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

@dataclass
class EntityType:
    """Entity type for annotation and NER."""
    id: str
    name: str
    display_name: str
    color: str
    category: str = "default"
    description: str = ""

class EntityManager:
    """Manager for entity types."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the entity manager.
        
        Args:
            db_path: Path to the SQLite database
        """
        if db_path is None:
            # Default path: merl_t/data/entities/entities.db
            project_root = Path(__file__).resolve().parents[3]
            db_path = str(project_root / "merl_t" / "data" / "entities" / "entities.db")
        
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        # Default entity types
        self.default_entity_types = [
            EntityType(
                id="ARTICOLO_CODICE",
                name="Articolo di Codice",
                display_name="Articolo di Codice",
                color="#FFA39E",
                category="legal_source",
                description="Articolo di un codice (civile, penale, etc.)"
            ),
            EntityType(
                id="LEGGE",
                name="Legge",
                display_name="Legge",
                color="#D4380D",
                category="legal_source",
                description="Legge dello Stato"
            ),
            EntityType(
                id="DECRETO",
                name="Decreto",
                display_name="Decreto",
                color="#FFC069",
                category="legal_source",
                description="Decreto (legislativo, legge, ministeriale, etc.)"
            ),
            EntityType(
                id="REGOLAMENTO_UE",
                name="Regolamento UE",
                display_name="Regolamento UE",
                color="#AD8B00",
                category="legal_source",
                description="Regolamento dell'Unione Europea"
            ),
            EntityType(
                id="SENTENZA",
                name="Sentenza",
                display_name="Sentenza",
                color="#D3F261",
                category="case_law",
                description="Sentenza di un organo giudiziario"
            ),
            EntityType(
                id="ORDINANZA",
                name="Ordinanza",
                display_name="Ordinanza",
                color="#389E0D",
                category="case_law",
                description="Ordinanza di un organo giudiziario"
            ),
            EntityType(
                id="CONCETTO_GIURIDICO",
                name="Concetto Giuridico",
                display_name="Concetto Giuridico",
                color="#5CDBD3",
                category="legal_concept",
                description="Concetto giuridico (es. prescrizione, responsabilità, etc.)"
            )
        ]
        
        # Add default entity types if they don't exist
        self._add_default_entity_types()
    
    def _get_db(self):
        """Get a connection to the database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn, conn.cursor()
    
    def _init_db(self):
        """Initialize the database schema."""
        conn, cursor = self._get_db()
        try:
            # Create entity types table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    color TEXT NOT NULL,
                    category TEXT DEFAULT 'default',
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
        finally:
            conn.close()
    
    def _add_default_entity_types(self):
        """Add default entity types to the database."""
        for entity_type in self.default_entity_types:
            # Skip if entity type already exists
            if self.entity_type_exists(entity_type.id):
                continue
            
            # Add entity type
            self.add_entity_type(entity_type)
    
    def add_entity_type(self, entity_type: EntityType) -> bool:
        """
        Add a new entity type.
        
        Args:
            entity_type: Entity type to add
            
        Returns:
            True if added successfully, False otherwise
        """
        conn, cursor = self._get_db()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO entities (id, name, display_name, color, category, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                entity_type.id,
                entity_type.name,
                entity_type.display_name,
                entity_type.color,
                entity_type.category,
                entity_type.description
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error adding entity type: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def get_entity_type(self, entity_id: str) -> Optional[EntityType]:
        """
        Get an entity type by ID.
        
        Args:
            entity_id: Entity type ID
            
        Returns:
            Entity type or None if not found
        """
        conn, cursor = self._get_db()
        try:
            cursor.execute('SELECT * FROM entities WHERE id = ?', (entity_id,))
            row = cursor.fetchone()
            if row:
                return EntityType(
                    id=row['id'],
                    name=row['name'],
                    display_name=row['display_name'],
                    color=row['color'],
                    category=row['category'],
                    description=row['description']
                )
            return None
        except Exception as e:
            logger.error(f"Error getting entity type: {e}")
            return None
        finally:
            conn.close()
    
    def entity_type_exists(self, entity_id: str) -> bool:
        """
        Check if an entity type exists.
        
        Args:
            entity_id: Entity type ID
            
        Returns:
            True if exists, False otherwise
        """
        conn, cursor = self._get_db()
        try:
            cursor.execute('SELECT 1 FROM entities WHERE id = ?', (entity_id,))
            return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking entity type existence: {e}")
            return False
        finally:
            conn.close()
    
    def get_all_entity_types(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all entity types.
        
        Returns:
            Dictionary of entity types mapped by ID
        """
        conn, cursor = self._get_db()
        try:
            cursor.execute('SELECT * FROM entities ORDER BY category, name')
            rows = cursor.fetchall()
            
            entity_types = {}
            for row in rows:
                entity_types[row['id']] = {
                    'name': row['name'],
                    'display_name': row['display_name'],
                    'color': row['color'],
                    'category': row['category'],
                    'description': row['description']
                }
            
            return entity_types
        except Exception as e:
            logger.error(f"Error getting all entity types: {e}")
            return {}
        finally:
            conn.close()
    
    def get_all_entities(self) -> List[EntityType]:
        """
        Get all entity types as a list.
        
        Returns:
            List of entity types
        """
        conn, cursor = self._get_db()
        try:
            cursor.execute('SELECT * FROM entities ORDER BY category, name')
            rows = cursor.fetchall()
            
            entities = []
            for row in rows:
                entities.append(EntityType(
                    id=row['id'],
                    name=row['name'],
                    display_name=row['display_name'],
                    color=row['color'],
                    category=row['category'],
                    description=row['description']
                ))
            
            return entities
        except Exception as e:
            logger.error(f"Error getting all entities: {e}")
            return []
        finally:
            conn.close()
    
    def update_entity_type(self, entity_type: EntityType) -> bool:
        """
        Update an entity type.
        
        Args:
            entity_type: Entity type to update
            
        Returns:
            True if updated successfully, False otherwise
        """
        if not self.entity_type_exists(entity_type.id):
            return False
        
        return self.add_entity_type(entity_type)
    
    def delete_entity_type(self, entity_id: str) -> bool:
        """
        Delete an entity type.
        
        Args:
            entity_id: Entity type ID
            
        Returns:
            True if deleted successfully, False otherwise
        """
        conn, cursor = self._get_db()
        try:
            cursor.execute('DELETE FROM entities WHERE id = ?', (entity_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting entity type: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

# Singleton instance
_entity_manager_instance = None

def get_entity_manager() -> EntityManager:
    """
    Get the entity manager instance.
    
    Returns:
        Entity manager instance
    """
    global _entity_manager_instance
    if _entity_manager_instance is None:
        try:
            from merl_t.config import get_config_manager
            config = get_config_manager()
            db_path = config.get("entities.database.path")
            _entity_manager_instance = EntityManager(db_path)
        except (ImportError, AttributeError):
            _entity_manager_instance = EntityManager()
            
    return _entity_manager_instance 