#!/usr/bin/env python3
"""
Script per aggiungere direttamente il campo status alla tabella documents.
Da eseguire una sola volta.
"""

import os
import sqlite3
import logging
import sys
from pathlib import Path

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('db_update')

def find_db_path():
    """Cerca il database in vari percorsi possibili."""
    potential_paths = [
        'data/annotations.db',
        'ner_giuridico/annotation/data/annotations.db',
        'src/data_lab/ner-giuridico/ner_giuridico/annotation/data/annotations.db'
    ]
    
    # Prima controlla i percorsi comuni
    for path in potential_paths:
        if os.path.exists(path):
            return path
    
    # Cerca ricorsivamente se non trovato nei percorsi comuni
    current_dir = Path.cwd()
    for root, dirs, files in os.walk(current_dir):
        for file in files:
            if file == 'annotations.db':
                return os.path.join(root, file)
    
    return None

def add_status_column(db_path):
    """Aggiunge la colonna status alla tabella documents."""
    logger.info(f"Aggiunta della colonna status alla tabella documents in: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verifica se la tabella documents esiste
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
        if not cursor.fetchone():
            logger.error("La tabella 'documents' non esiste nel database")
            return False
        
        # Verifica se la colonna status già esiste
        cursor.execute("PRAGMA table_info(documents)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'status' not in column_names:
            # Aggiungi la colonna status
            logger.info("Aggiunta della colonna 'status' con valore predefinito 'pending'")
            cursor.execute("ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'pending'")
            
            # Aggiorna le righe esistenti
            cursor.execute("UPDATE documents SET status = 'pending' WHERE status IS NULL")
            
            # Crea indice per le query
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)")
            
            conn.commit()
            logger.info("Colonna 'status' aggiunta con successo")
        else:
            logger.info("La colonna 'status' esiste già")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Errore durante l'aggiornamento del database: {e}")
        return False

if __name__ == "__main__":
    db_path = find_db_path()
    
    if not db_path:
        logger.error("Database annotations.db non trovato")
        sys.exit(1)
    
    logger.info(f"Database trovato in: {db_path}")
    
    if add_status_column(db_path):
        logger.info("✅ Aggiornamento completato con successo!")
        sys.exit(0)
    else:
        logger.error("❌ Errore durante l'aggiornamento")
        sys.exit(1)