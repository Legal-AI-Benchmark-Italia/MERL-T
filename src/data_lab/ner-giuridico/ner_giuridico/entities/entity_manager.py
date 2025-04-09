"""
Modulo unificato per la gestione delle entità nel sistema NER-Giuridico.
Implementa un sistema entity management flessibile con persistenza su database.
"""

import logging
import json
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Protocol
import sqlite3
from contextlib import contextmanager
import datetime
from dataclasses import dataclass, field, asdict

# --- Definizione base di Entity ---

@dataclass
class EntityType:
    """
    Classe che rappresenta un tipo di entità nel sistema.
    Sostituisce la precedente implementazione basata su enum.
    """
    id: str  # UUID o stringa univoca
    name: str  # Nome identificativo (es. "LEGGE")
    display_name: str  # Nome per visualizzazione (es. "Legge")
    category: str  # Categoria (es. "normative")
    color: str  # Colore in formato esadecimale (es. "#D4380D")
    description: str = ""  # Descrizione opzionale
    metadata_schema: Dict[str, str] = field(default_factory=dict)  # Schema dei metadati
    patterns: List[str] = field(default_factory=list)  # Pattern regex per il riconoscimento
    system: bool = False  # Flag per indicare se è un'entità di sistema
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte l'entità in un dizionario."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EntityType':
        """Crea un'entità da un dizionario."""
        return cls(**data)


# --- Observer Pattern per notificare i cambiamenti ---

class EntityObserver(Protocol):
    """Protocollo per gli osservatori delle modifiche alle entità."""
    
    def entity_added(self, entity: EntityType) -> None:
        """Chiamato quando viene aggiunta un'entità."""
        pass
        
    def entity_updated(self, entity: EntityType) -> None:
        """Chiamato quando viene aggiornata un'entità."""
        pass
        
    def entity_removed(self, entity_id: str) -> None:
        """Chiamato quando viene rimossa un'entità."""
        pass


class EntityManager:
    """
    Gestore unificato delle entità, con supporto per persistenza e notifiche.
    Sostituisce DynamicEntityManager e le funzionalità di entity_types in entities.py.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Inizializza il gestore delle entità.
        
        Args:
            db_path: Percorso al file del database SQLite (opzionale)
        """
        self.logger = logging.getLogger("NER-Giuridico.EntityManager")
        
        # Inizializza strutture dati
        self.entities: Dict[str, EntityType] = {}
        self.categories: Dict[str, Set[str]] = {
            "normative": set(),
            "jurisprudence": set(),
            "concepts": set(),
            "custom": set()
        }
        
        # Lista degli osservatori
        self.observers: List[EntityObserver] = []
        
        # Configura percorso del database
        if db_path:
            self.db_path = db_path
        else:
            # Percorso predefinito
            default_db_path = str(Path(__file__).parent.parent / "data" / "entities.db")
            self.db_path = default_db_path
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Inizializza il database
        self._init_database()
        
        # Carica l'entità predefinita "Legge" se il database è vuoto
        if not self.entities:
            self._add_default_legge_entity()
    
    @contextmanager
    def _get_db(self):
        """Context manager per connessioni al database."""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            yield conn, cursor
        finally:
            if conn:
                conn.close()
    
    def _init_database(self):
        """Inizializza il database e carica le entità esistenti."""
        try:
            # Assicura che la directory del database esista
            db_dir = os.path.dirname(self.db_path)
            if not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            
            # Crea/connette al database
            with self._get_db() as (conn, cursor):
                # Crea tabella entità se non esiste
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    display_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    color TEXT NOT NULL,
                    description TEXT,
                    metadata_schema TEXT,
                    patterns TEXT,
                    system INTEGER DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                )
                """)
                
                # Crea indice per nome
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name)")
                
                # Crea indice per categoria
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_category ON entities(category)")
                
                conn.commit()
                
                # Carica le entità esistenti
                self._load_entities_from_database()
        except Exception as e:
            self.logger.error(f"Errore nell'inizializzazione del database: {e}")
            self.logger.exception(e)
    
    def _add_default_legge_entity(self):
        """Aggiunge l'entità predefinita 'Legge'."""
        legge = EntityType(
            id=str(uuid.uuid4()),
            name="LEGGE",
            display_name="Legge",
            category="normative",
            color="#D4380D",
            description="Atto normativo approvato dal Parlamento",
            metadata_schema={
                "numero": "string", 
                "anno": "string", 
                "data": "string"
            },
            patterns=[
                r"legge\s+(?:n\.\s*)?(\d+)(?:/(\d{4}))?",
                r"l\.\s*(?:n\.\s*)?(\d+)(?:/(\d{4}))?"
            ],
            system=True
        )
        self.add_entity(legge)
        self.logger.info("Aggiunta entità predefinita 'Legge'")
    
    def _load_entities_from_database(self):
        """Carica tutte le entità dal database."""
        try:
            with self._get_db() as (conn, cursor):
                cursor.execute("SELECT * FROM entities")
                rows = cursor.fetchall()
                
                # Ottieni i nomi delle colonne
                column_names = [desc[0] for desc in cursor.description]
                
                # Resetta le strutture dati
                self.entities.clear()
                for category in self.categories:
                    self.categories[category].clear()
                
                # Popola le strutture dati
                for row in rows:
                    # Converti riga in dizionario
                    entity_data = dict(zip(column_names, row))
                    
                    # Converti campi JSON
                    for field in ['metadata_schema', 'patterns']:
                        if field in entity_data and entity_data[field]:
                            try:
                                entity_data[field] = json.loads(entity_data[field])
                            except json.JSONDecodeError:
                                entity_data[field] = {} if field == 'metadata_schema' else []
                        else:
                            entity_data[field] = {} if field == 'metadata_schema' else []
                    
                    # Converti boolean
                    if 'system' in entity_data:
                        entity_data['system'] = bool(entity_data['system'])
                    
                    # Crea oggetto EntityType
                    entity = EntityType.from_dict(entity_data)
                    
                    # Aggiungi alle strutture dati
                    self.entities[entity.id] = entity
                    
                    # Aggiungi alla categoria
                    if entity.category in self.categories:
                        self.categories[entity.category].add(entity.id)
                    else:
                        self.categories[entity.category] = {entity.id}
                
                self.logger.info(f"Caricate {len(self.entities)} entità dal database")
        except Exception as e:
            self.logger.error(f"Errore nel caricamento delle entità dal database: {e}")
            self.logger.exception(e)
    
    def add_observer(self, observer: EntityObserver) -> None:
        """Aggiunge un osservatore delle modifiche alle entità."""
        self.observers.append(observer)
    
    def remove_observer(self, observer: EntityObserver) -> None:
        """Rimuove un osservatore."""
        if observer in self.observers:
            self.observers.remove(observer)
    
    def _notify_entity_added(self, entity: EntityType) -> None:
        """Notifica gli osservatori dell'aggiunta di un'entità."""
        for observer in self.observers:
            observer.entity_added(entity)
    
    def _notify_entity_updated(self, entity: EntityType) -> None:
        """Notifica gli osservatori dell'aggiornamento di un'entità."""
        for observer in self.observers:
            observer.entity_updated(entity)
    
    def _notify_entity_removed(self, entity_id: str) -> None:
        """Notifica gli osservatori della rimozione di un'entità."""
        for observer in self.observers:
            observer.entity_removed(entity_id)
    
    def add_entity(self, entity: EntityType) -> bool:
        """
        Aggiunge una nuova entità al sistema.
        
        Args:
            entity: Entità da aggiungere
            
        Returns:
            True se l'aggiunta è avvenuta con successo, False altrimenti
        """
        try:
            # Verifica che il nome non sia già in uso
            for existing in self.entities.values():
                if existing.name == entity.name:
                    self.logger.warning(f"Entità con nome '{entity.name}' già esistente")
                    return False
            
            # Crea un nuovo ID se non fornito
            if not entity.id:
                entity.id = str(uuid.uuid4())
            
            # Verifica che la categoria sia valida
            if entity.category not in self.categories:
                self.categories[entity.category] = set()
            
            # Aggiorna data di creazione/modifica
            now = datetime.datetime.now().isoformat()
            entity.created_at = now
            entity.updated_at = now
            
            # Aggiungi al database
            with self._get_db() as (conn, cursor):
                # Prepara dati per inserimento
                entity_dict = entity.to_dict()
                
                # Converti campi JSON
                entity_dict['metadata_schema'] = json.dumps(entity_dict['metadata_schema'])
                entity_dict['patterns'] = json.dumps(entity_dict['patterns'])
                
                # Converti boolean
                entity_dict['system'] = 1 if entity_dict['system'] else 0
                
                # Esegui inserimento
                placeholders = ', '.join(['?' for _ in range(len(entity_dict))])
                columns = ', '.join(entity_dict.keys())
                values = tuple(entity_dict.values())
                
                cursor.execute(
                    f"INSERT INTO entities ({columns}) VALUES ({placeholders})", 
                    values
                )
                conn.commit()
            
            # Aggiungi alle strutture dati
            self.entities[entity.id] = entity
            self.categories[entity.category].add(entity.id)
            
            # Notifica gli osservatori
            self._notify_entity_added(entity)
            
            self.logger.info(f"Entità '{entity.name}' aggiunta con successo (ID: {entity.id})")
            return True
        except Exception as e:
            self.logger.error(f"Errore nell'aggiunta dell'entità: {e}")
            self.logger.exception(e)
            return False
    
    def update_entity(self, entity: EntityType) -> bool:
        """
        Aggiorna un'entità esistente.
        
        Args:
            entity: Entità con le modifiche
            
        Returns:
            True se l'aggiornamento è avvenuto con successo, False altrimenti
        """
        try:
            # Verifica che l'entità esista
            if entity.id not in self.entities:
                self.logger.error(f"Entità con ID '{entity.id}' non trovata")
                return False
            
            original_entity = self.entities[entity.id]
            
            # Aggiorna data di modifica
            entity.updated_at = datetime.datetime.now().isoformat()
            
            # Mantieni la data di creazione originale
            entity.created_at = original_entity.created_at
            
            # Aggiorna il database
            with self._get_db() as (conn, cursor):
                # Prepara dati per aggiornamento
                entity_dict = entity.to_dict()
                
                # Converti campi JSON
                entity_dict['metadata_schema'] = json.dumps(entity_dict['metadata_schema'])
                entity_dict['patterns'] = json.dumps(entity_dict['patterns'])
                
                # Converti boolean
                entity_dict['system'] = 1 if entity_dict['system'] else 0
                
                # Costruisci query di aggiornamento
                set_clauses = [f"{key} = ?" for key in entity_dict.keys() if key != 'id']
                values = [entity_dict[key] for key in entity_dict.keys() if key != 'id']
                values.append(entity.id)  # Per la clausola WHERE
                
                query = f"UPDATE entities SET {', '.join(set_clauses)} WHERE id = ?"
                cursor.execute(query, values)
                conn.commit()
            
            # Aggiorna le strutture dati
            # Rimuovi dalla categoria precedente se cambiata
            if original_entity.category != entity.category:
                if original_entity.category in self.categories:
                    self.categories[original_entity.category].discard(entity.id)
                
                # Aggiungi alla nuova categoria
                if entity.category not in self.categories:
                    self.categories[entity.category] = set()
                self.categories[entity.category].add(entity.id)
            
            # Aggiorna l'entità
            self.entities[entity.id] = entity
            
            # Notifica gli osservatori
            self._notify_entity_updated(entity)
            
            self.logger.info(f"Entità '{entity.name}' (ID: {entity.id}) aggiornata con successo")
            return True
        except Exception as e:
            self.logger.error(f"Errore nell'aggiornamento dell'entità: {e}")
            self.logger.exception(e)
            return False
    
    def remove_entity(self, entity_id: str) -> bool:
        """
        Rimuove un'entità.
        
        Args:
            entity_id: ID dell'entità da rimuovere
            
        Returns:
            True se la rimozione è avvenuta con successo, False altrimenti
        """
        try:
            # Verifica che l'entità esista
            if entity_id not in self.entities:
                self.logger.error(f"Entità con ID '{entity_id}' non trovata")
                return False
            
            entity = self.entities[entity_id]
            
            # Non permettere la rimozione di entità di sistema
            if entity.system:
                self.logger.warning(f"Impossibile rimuovere l'entità di sistema '{entity.name}'")
                return False
            
            # Rimuovi dal database
            with self._get_db() as (conn, cursor):
                cursor.execute("DELETE FROM entities WHERE id = ?", (entity_id,))
                conn.commit()
            
            # Rimuovi dalle strutture dati
            if entity.category in self.categories:
                self.categories[entity.category].discard(entity_id)
            del self.entities[entity_id]
            
            # Notifica gli osservatori
            self._notify_entity_removed(entity_id)
            
            self.logger.info(f"Entità '{entity.name}' (ID: {entity_id}) rimossa con successo")
            return True
        except Exception as e:
            self.logger.error(f"Errore nella rimozione dell'entità: {e}")
            self.logger.exception(e)
            return False
    
    def get_entity(self, entity_id: str) -> Optional[EntityType]:
        """
        Ottiene un'entità per ID.
        
        Args:
            entity_id: ID dell'entità
            
        Returns:
            L'entità se trovata, None altrimenti
        """
        return self.entities.get(entity_id)
    
    def get_entity_by_name(self, name: str) -> Optional[EntityType]:
        """
        Ottiene un'entità per nome.
        
        Args:
            name: Nome dell'entità
            
        Returns:
            L'entità se trovata, None altrimenti
        """
        for entity in self.entities.values():
            if entity.name == name:
                return entity
        return None
    
    def get_all_entities(self) -> List[EntityType]:
        """
        Ottiene tutte le entità.
        
        Returns:
            Lista di tutte le entità
        """
        return list(self.entities.values())
    
    def get_entities_by_category(self, category: str) -> List[EntityType]:
        """
        Ottiene tutte le entità di una categoria.
        
        Args:
            category: Categoria delle entità
            
        Returns:
            Lista di entità della categoria specificata
        """
        if category not in self.categories:
            return []
        
        return [self.entities[entity_id] for entity_id in self.categories[category] 
                if entity_id in self.entities]
    
    def get_categories(self) -> List[str]:
        """
        Ottiene tutte le categorie.
        
        Returns:
            Lista di categorie
        """
        return list(self.categories.keys())
    
    def add_category(self, category: str) -> bool:
        """
        Aggiunge una nuova categoria.
        
        Args:
            category: Nome della categoria
            
        Returns:
            True se l'aggiunta è avvenuta con successo, False altrimenti
        """
        if category in self.categories:
            return False
        
        self.categories[category] = set()
        return True
    
    def get_entity_label_config(self, format: str = "label-studio") -> str:
        """
        Genera la configurazione delle etichette per gli strumenti di annotazione.
        
        Args:
            format: Formato della configurazione ("label-studio", "doccano", etc.)
            
        Returns:
            Configurazione delle etichette nel formato specificato
        """
        if format == "label-studio":
            # Genera XML per Label Studio
            xml_parts = ['<View>', '  <Header value="Annotazione di entità giuridiche"/>', '  <Text name="text" value="$text"/>']
            
            # Aggiungi le etichette
            labels_xml = ['  <Labels name="label" toName="text">']
            for entity in self.entities.values():
                labels_xml.append(f'    <Label value="{entity.name}" background="{entity.color}" displayName="{entity.display_name}"/>')
            labels_xml.append('  </Labels>')
            
            xml_parts.extend(labels_xml)
            
            # Aggiungi le relazioni
            xml_parts.extend([
                '  <Relations>',
                '    <Relation value="riferimento" />',
                '    <Relation value="definizione" />',
                '    <Relation value="applicazione" />',
                '  </Relations>',
                '</View>'
            ])
            
            return '\n'.join(xml_parts)
            
        elif format == "doccano":
            # Genera JSON per Doccano
            doccano_config = []
            for i, entity in enumerate(self.entities.values()):
                doccano_config.append({
                    "id": i + 1,
                    "text": entity.display_name,
                    "prefix_key": None,
                    "suffix_key": None,
                    "background_color": entity.color,
                    "text_color": "#ffffff"
                })
            return json.dumps(doccano_config, ensure_ascii=False, indent=2)
            
        else:
            self.logger.warning(f"Formato {format} non supportato.")
            return ""
    
    def export_entities(self, file_path: str) -> bool:
        """
        Esporta le entità in un file JSON.
        
        Args:
            file_path: Percorso del file
            
        Returns:
            True se l'esportazione è avvenuta con successo, False altrimenti
        """
        try:
            entities_data = [entity.to_dict() for entity in self.entities.values()]
            
            # Assicura che la directory esista
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(entities_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Entità esportate con successo in {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Errore nell'esportazione delle entità: {e}")
            self.logger.exception(e)
            return False
    
    def import_entities(self, file_path: str, overwrite: bool = False) -> bool:
        """
        Importa entità da un file JSON.
        
        Args:
            file_path: Percorso del file
            overwrite: Se True, sovrascrive le entità esistenti
            
        Returns:
            True se l'importazione è avvenuta con successo, False altrimenti
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                entities_data = json.load(f)
            
            # Backup delle strutture dati
            old_entities = self.entities.copy()
            old_categories = {category: entities.copy() for category, entities in self.categories.items()}
            
            try:
                for entity_data in entities_data:
                    entity = EntityType.from_dict(entity_data)
                    
                    if entity.id in self.entities and not overwrite:
                        continue
                    
                    self.add_entity(entity)
                
                self.logger.info(f"Entità importate con successo da {file_path}")
                return True
            except Exception as e:
                # Ripristina le strutture dati in caso di errore
                self.entities = old_entities
                self.categories = old_categories
                raise e
        except Exception as e:
            self.logger.error(f"Errore nell'importazione delle entità: {e}")
            self.logger.exception(e)
            return False
        
    def get_entities_for_annotation(self) -> List[Dict[str, Any]]:
        """
        Ottiene le entità in un formato compatibile con l'interfaccia di annotazione.
        
        Returns:
            Lista di entità nel formato atteso dall'interfaccia di annotazione
        """
        entities_data = []
        for entity in self.get_all_entities():
            entities_data.append({
                "id": entity.id,
                "name": entity.display_name,
                "color": entity.color
            })
        return entities_data

# Singleton pattern per EntityManager
_entity_manager = None

def get_entity_manager(db_path: Optional[str] = None) -> EntityManager:
    """
    Ottiene l'istanza globale del gestore delle entità.
    
    Args:
        db_path: Percorso al database (opzionale)
        
    Returns:
        Istanza del gestore delle entità
    """
    global _entity_manager
    if _entity_manager is None:
        _entity_manager = EntityManager(db_path)
    return _entity_manager

def set_entity_manager(manager: EntityManager) -> None:
    """
    Imposta l'istanza globale del gestore delle entità.
    Utile per i test.
    
    Args:
        manager: Istanza del gestore delle entità
    """
    global _entity_manager
    _entity_manager = manager