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

# Definisce il percorso fisso per il database
DB_PATH = "/home/ec2-user/MERL-T/src/core/annotation/data/annotations.db"

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
    # Usa direttamente il percorso fisso
    db_path = DB_PATH
    
    if not os.path.exists(os.path.dirname(db_path)):
        logger.error(f"La directory del database {os.path.dirname(db_path)} non esiste. Creala prima di eseguire lo script.")
        sys.exit(1)
        
    if not os.path.exists(db_path):
        logger.error(f"Database annotations.db non trovato in {db_path}")
        sys.exit(1)
    
    logger.info(f"Database trovato in: {db_path}")
    
    if add_status_column(db_path):
        logger.info("✅ Aggiornamento completato con successo!")
        sys.exit(0)
    else:
        logger.error("❌ Errore durante l'aggiornamento")
        sys.exit(1)