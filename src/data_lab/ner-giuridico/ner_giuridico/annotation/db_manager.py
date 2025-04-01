#!/usr/bin/env python3
"""
db_manager.py
Sistema di persistenza delle annotazioni basato su SQLite.
"""

import os
import sqlite3
import json
import logging
import datetime
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

# Setup del logger
logger = logging.getLogger("db_manager")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

class DBContextManager:
    def __init__(self, db_path):
        self.db_path = db_path
    
    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        return self.conn, self.cursor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.cursor.close()
        self.conn.close()

class AnnotationDBManager:
    """
    Gestore della persistenza delle annotazioni tramite database SQLite.
    """
    
    def __init__(self, db_path: str = None, backup_dir: str = None):
        """
        Inizializza il gestore del database.
        
        Args:
            db_path: Percorso del file database SQLite. Se None, viene utilizzato il percorso predefinito.
            backup_dir: Directory per i backup. Se None, viene utilizzata la directory predefinita.
        """
        # Percorso predefinito se non specificato
        if db_path is None:
            app_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(app_dir, 'data', 'annotations.db')
        
        # Crea le directory necessarie
        db_dir = os.path.dirname(db_path)
        os.makedirs(db_dir, exist_ok=True)
        
        # Imposta la directory di backup
        if backup_dir is None:
            backup_dir = os.path.join(db_dir, 'backup')
        os.makedirs(backup_dir, exist_ok=True)
        
        self.db_path = db_path
        self.backup_dir = backup_dir
        logger.info(f"Database inizializzato: {self.db_path}")
        logger.info(f"Directory backup: {self.backup_dir}")
        
        # Inizializza il database
        self._init_db()
    
    def _get_db(self) -> DBContextManager:
        """
        Ottiene un context manager per la connessione al database.
        
        Returns:
            DBContextManager instance
        """
        return DBContextManager(self.db_path)
    
    def _init_db(self) -> None:
        """
        Inizializza lo schema del database se necessario.
        """
        with self._get_db() as (conn, cursor):
            # Tabella documenti
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                word_count INTEGER,
                date_created TEXT,
                date_modified TEXT
            )
            ''')
            
            # Tabella annotazioni
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS annotations (
                id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                start INTEGER NOT NULL,
                end INTEGER NOT NULL,
                text TEXT NOT NULL,
                type TEXT NOT NULL,
                metadata TEXT,
                date_created TEXT,
                date_modified TEXT,
                FOREIGN KEY (doc_id) REFERENCES documents(id)
            )
            ''')
            
            conn.commit()
            logger.debug("Schema del database inizializzato")
    
    def create_backup(self) -> str:
        """
        Crea un backup del database.
        
        Returns:
            Percorso del file di backup
        """
        if not os.path.exists(self.db_path):
            logger.warning("Impossibile creare backup: database non esistente")
            return None
        
        timestamp = int(datetime.datetime.now().timestamp())
        backup_file = os.path.join(self.backup_dir, f"annotations_backup_{timestamp}.db")
        
        try:
            import shutil
            shutil.copy2(self.db_path, backup_file)
            logger.info(f"Backup creato: {backup_file}")
            return backup_file
        except Exception as e:
            logger.error(f"Errore nella creazione del backup: {e}")
            return None
    
    def cleanup_backups(self, max_backups: int = 10) -> None:
        """
        Pulisce i vecchi backup mantenendo solo i più recenti.
        
        Args:
            max_backups: Numero massimo di backup da mantenere
        """
        try:
            backup_files = []
            for filename in os.listdir(self.backup_dir):
                if filename.startswith('annotations_backup_') and filename.endswith('.db'):
                    filepath = os.path.join(self.backup_dir, filename)
                    backup_files.append((filepath, os.path.getmtime(filepath)))
            
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            if len(backup_files) > max_backups:
                for filepath, _ in backup_files[max_backups:]:
                    os.remove(filepath)
                    logger.debug(f"Backup rimosso: {filepath}")
        except Exception as e:
            logger.error(f"Errore nella pulizia dei backup: {e}")
    
    # ---- Operazioni sui documenti ----
    
    def get_documents(self) -> List[Dict[str, Any]]:
        """
        Ottiene tutti i documenti dal database.
        
        Returns:
            Lista di documenti
        """
        with self._get_db() as (conn, cursor):
            cursor.execute("SELECT * FROM documents ORDER BY date_created DESC")
            return [dict(row) for row in cursor.fetchall()]
    
    def get_document(self, doc_id: str) -> Dict[str, Any]:
        """
        Ottiene un documento specifico dal database.
        
        Args:
            doc_id: ID del documento
            
        Returns:
            Documento o None se non trovato
        """
        with self._get_db() as (conn, cursor):
            cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def save_document(self, document: Dict[str, Any]) -> bool:
        """
        Salva un documento nel database.
        
        Args:
            document: Documento da salvare
            
        Returns:
            True se salvato con successo, False altrimenti
        """
        try:
            now = datetime.datetime.now().isoformat()
            
            if 'date_created' not in document:
                document['date_created'] = now
            
            document['date_modified'] = now
            
            with self._get_db() as (conn, cursor):
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO documents 
                    (id, title, text, word_count, date_created, date_modified)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        document['id'],
                        document['title'],
                        document['text'],
                        document.get('word_count', 0),
                        document['date_created'],
                        document['date_modified']
                    )
                )
                conn.commit()
                logger.debug(f"Documento salvato: {document['id']}")
                return True
        except Exception as e:
            logger.error(f"Errore nel salvataggio del documento: {e}")
            return False
    
    def delete_document(self, doc_id: str) -> bool:
        """
        Elimina un documento e le sue annotazioni dal database.
        
        Args:
            doc_id: ID del documento
            
        Returns:
            True se eliminato con successo, False altrimenti
        """
        try:
            with self._get_db() as (conn, cursor):
                # Elimina prima le annotazioni associate
                cursor.execute("DELETE FROM annotations WHERE doc_id = ?", (doc_id,))
                # Poi elimina il documento
                cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                conn.commit()
                logger.debug(f"Documento eliminato: {doc_id}")
                return True
        except Exception as e:
            logger.error(f"Errore nell'eliminazione del documento: {e}")
            return False
    
    def update_document(self, doc_id: str, updates: Dict[str, Any]) -> bool:
        """
        Aggiorna un documento esistente.
        
        Args:
            doc_id: ID del documento
            updates: Dizionario con i campi da aggiornare
            
        Returns:
            True se aggiornato con successo, False altrimenti
        """
        try:
            document = self.get_document(doc_id)
            if not document:
                logger.warning(f"Documento non trovato: {doc_id}")
                return False
            
            # Aggiorna i campi
            for key, value in updates.items():
                if key in ['title', 'text', 'word_count']:
                    document[key] = value
            
            document['date_modified'] = datetime.datetime.now().isoformat()
            
            return self.save_document(document)
        except Exception as e:
            logger.error(f"Errore nell'aggiornamento del documento: {e}")
            return False
    
    # ---- Operazioni sulle annotazioni ----
    
    def get_annotations(self, doc_id: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Ottiene le annotazioni, raggruppate per documento.
        
        Args:
            doc_id: Opzionale, filtra per ID documento
            
        Returns:
            Dizionario {doc_id: [annotazioni]}
        """
        with self._get_db() as (conn, cursor):
            if doc_id:
                cursor.execute("SELECT * FROM annotations WHERE doc_id = ? ORDER BY start", (doc_id,))
            else:
                cursor.execute("SELECT * FROM annotations ORDER BY doc_id, start")
            
            rows = cursor.fetchall()
            result = {}
            
            for row in rows:
                row_dict = dict(row)
                doc_id = row_dict['doc_id']
                
                # Converti il metadata da JSON a dizionario
                if row_dict.get('metadata'):
                    try:
                        row_dict['metadata'] = json.loads(row_dict['metadata'])
                    except:
                        row_dict['metadata'] = {}
                else:
                    row_dict['metadata'] = {}
                
                if doc_id not in result:
                    result[doc_id] = []
                result[doc_id].append(row_dict)
            
            return result
    
    def get_document_annotations(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        Ottiene le annotazioni per un documento specifico.
        
        Args:
            doc_id: ID del documento
            
        Returns:
            Lista di annotazioni
        """
        annotations = self.get_annotations(doc_id)
        return annotations.get(doc_id, [])
    
    def save_annotation(self, doc_id: str, annotation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Salva un'annotazione nel database.
        
        Args:
            doc_id: ID del documento
            annotation: Annotazione da salvare
            
        Returns:
            L'annotazione salvata con ID generato se era nuovo
        """
        try:
            now = datetime.datetime.now().isoformat()
            
            # Genera un ID se non presente
            if 'id' not in annotation or not annotation['id']:
                annotation['id'] = f"ann_{doc_id}_{int(datetime.datetime.now().timestamp())}"
            
            # Aggiungi date se non presenti
            if 'date_created' not in annotation:
                annotation['date_created'] = now
            
            annotation['date_modified'] = now
            
            # Converti metadata in JSON se presente
            metadata_json = None
            if 'metadata' in annotation and annotation['metadata']:
                metadata_json = json.dumps(annotation['metadata'])
            
            with self._get_db() as (conn, cursor):
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO annotations
                    (id, doc_id, start, end, text, type, metadata, date_created, date_modified)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        annotation['id'],
                        doc_id,
                        annotation['start'],
                        annotation['end'],
                        annotation['text'],
                        annotation['type'],
                        metadata_json,
                        annotation['date_created'],
                        annotation['date_modified']
                    )
                )
                conn.commit()
                logger.debug(f"Annotazione salvata: {annotation['id']} per doc {doc_id}")
                return annotation
        except Exception as e:
            logger.error(f"Errore nel salvataggio dell'annotazione: {e}")
            return None
    
    def delete_annotation(self, annotation_id: str) -> bool:
        """
        Elimina un'annotazione dal database.
        
        Args:
            annotation_id: ID dell'annotazione
            
        Returns:
            True se eliminata con successo, False altrimenti
        """
        try:
            with self._get_db() as (conn, cursor):
                cursor.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
                conn.commit()
                logger.debug(f"Annotazione eliminata: {annotation_id}")
                return True
        except Exception as e:
            logger.error(f"Errore nell'eliminazione dell'annotazione: {e}")
            return False
    
    def clear_annotations(self, doc_id: str, entity_type: str = None) -> bool:
        """
        Elimina tutte le annotazioni di un documento, opzionalmente filtrando per tipo.
        
        Args:
            doc_id: ID del documento
            entity_type: Opzionale, tipo di entità da eliminare
            
        Returns:
            True se eliminate con successo, False altrimenti
        """
        try:
            with self._get_db() as (conn, cursor):
                if entity_type:
                    cursor.execute("DELETE FROM annotations WHERE doc_id = ? AND type = ?", (doc_id, entity_type))
                    logger.debug(f"Annotazioni di tipo {entity_type} eliminate per doc {doc_id}")
                else:
                    cursor.execute("DELETE FROM annotations WHERE doc_id = ?", (doc_id,))
                    logger.debug(f"Tutte le annotazioni eliminate per doc {doc_id}")
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Errore nell'eliminazione delle annotazioni: {e}")
            return False
    
    # ---- Esportazione dati ----
    
    def export_json(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Esporta tutte le annotazioni in formato JSON.
        
        Returns:
            Dizionario con le annotazioni in formato compatibile con il formato JSON dell'app
        """
        return self.get_annotations()
    
    def export_spacy(self) -> List[Dict[str, Any]]:
        """
        Esporta le annotazioni in formato spaCy.
        
        Returns:
            Lista di documenti con entità in formato spaCy
        """
        spacy_data = []
        annotations = self.get_annotations()
        
        for doc_id, doc_annotations in annotations.items():
            document = self.get_document(doc_id)
            if document:
                text = document['text']
                entities = []
                
                for ann in doc_annotations:
                    entities.append((ann['start'], ann['end'], ann['type']))
                
                spacy_data.append({"text": text, "entities": entities})
        
        return spacy_data
    
    def import_from_json(self, annotations_json: Dict[str, List[Dict[str, Any]]]) -> bool:
        """
        Importa annotazioni da un dizionario in formato JSON.
        
        Args:
            annotations_json: Dizionario {doc_id: [annotazioni]}
            
        Returns:
            True se importate con successo, False altrimenti
        """
        try:
            with self._get_db() as (conn, cursor):
                for doc_id, annotations in annotations_json.items():
                    for annotation in annotations:
                        self.save_annotation(doc_id, annotation)
                
                conn.commit()
                logger.info(f"Importate {sum(len(anns) for anns in annotations_json.values())} annotazioni")
                return True
        except Exception as e:
            logger.error(f"Errore nell'importazione delle annotazioni: {e}")
            return False