#!/usr/bin/env python3
"""
add_metadata_column.py

Script per verificare, inizializzare e aggiornare il database per supportare
la colonna 'metadata' nella tabella 'documents', necessaria per l'upload multiplo
e la struttura delle cartelle.
"""

import os
import sys
import sqlite3
import logging
import argparse
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('db_migration')

def find_db_path():
    """Cerca il percorso del database nel progetto."""
    # Percorsi comuni da controllare
    potential_paths = [
        'data/annotations.db',
        'ner_giuridico/annotation/data/annotations.db',
        'src/data_lab/ner-giuridico/ner_giuridico/annotation/data/annotations.db'
    ]
    
    for path in potential_paths:
        if os.path.exists(path):
            return path
    
    # Cerca ricorsivamente
    current_dir = Path.cwd()
    for _ in range(4):  # Controlla fino a 3 livelli sopra
        for root, dirs, files in os.walk(current_dir):
            for file in files:
                if file == 'annotations.db':
                    return os.path.join(root, file)
        
        parent = current_dir.parent
        if parent == current_dir:  # Raggiunta la directory root
            break
        current_dir = parent
    
    return None

def inspect_database(db_path):
    """
    Ispeziona il database per verificare quali tabelle esistono.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Ottieni un elenco di tutte le tabelle
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            logger.info(f"Il database {db_path} non contiene tabelle.")
            return False
        
        logger.info(f"Tabelle nel database {db_path}:")
        for table in tables:
            logger.info(f"- {table[0]}")
            
            # Mostra la struttura di ogni tabella
            cursor.execute(f"PRAGMA table_info({table[0]})")
            columns = cursor.fetchall()
            logger.info("  Colonne:")
            for col in columns:
                logger.info(f"  - {col[1]} ({col[2]})")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Errore durante l'ispezione del database: {e}")
        return False

def check_column_exists(conn, table, column):
    """Verifica se una colonna esiste già nella tabella."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    for col in columns:
        if col[1] == column:
            return True
    return False

def add_metadata_column(db_path):
    """Aggiunge la colonna 'metadata' alla tabella 'documents'."""
    logger.info(f"Lavorando sul database in: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verifica che la tabella documents esista
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
        if not cursor.fetchone():
            logger.error("La tabella 'documents' non esiste nel database")
            conn.close()
            return False
        
        # Verifica se la colonna metadata già esiste
        if check_column_exists(conn, 'documents', 'metadata'):
            logger.info("La colonna 'metadata' esiste già nella tabella 'documents'")
            conn.close()
            return True
        
        # Aggiungi la colonna metadata
        cursor.execute("ALTER TABLE documents ADD COLUMN metadata TEXT")
        conn.commit()
        
        # Verifica che l'aggiunta sia avvenuta con successo
        if check_column_exists(conn, 'documents', 'metadata'):
            logger.info("Colonna 'metadata' aggiunta con successo alla tabella 'documents'")
            conn.close()
            return True
        else:
            logger.error("Errore nell'aggiunta della colonna 'metadata'")
            conn.close()
            return False
    except Exception as e:
        logger.error(f"Errore durante la migrazione: {e}")
        conn.rollback()
        conn.close()
        return False

def ensure_documents_table(db_path):
    """
    Crea la tabella 'documents' se non esiste, includendo già la colonna metadata.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verifica se la tabella esiste
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
        if not cursor.fetchone():
            logger.info("La tabella 'documents' non esiste. Creazione in corso...")
            
            # Crea la tabella documents con la colonna metadata
            cursor.execute('''
            CREATE TABLE documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                word_count INTEGER,
                date_created TEXT,
                date_modified TEXT,
                created_by TEXT,
                assigned_to TEXT,
                metadata TEXT,
                FOREIGN KEY (created_by) REFERENCES users(id),
                FOREIGN KEY (assigned_to) REFERENCES users(id)
            )
            ''')
            
            conn.commit()
            logger.info("Tabella 'documents' creata con successo (inclusa colonna metadata)")
            conn.close()
            return True
        else:
            logger.info("La tabella 'documents' esiste già")
            conn.close()
            # Se la tabella esiste, verifica se la colonna metadata esiste e aggiungila se necessario
            return add_metadata_column(db_path)
    except Exception as e:
        logger.error(f"Errore durante la creazione della tabella: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

def main():
    parser = argparse.ArgumentParser(description="Aggiunge la colonna 'metadata' alla tabella 'documents'")
    parser.add_argument('--db', type=str, help='Percorso del database SQLite (opzionale)')
    parser.add_argument('--init', action='store_true', help='Inizializza la tabella se non esiste')
    parser.add_argument('--inspect', action='store_true', help='Ispeziona il database senza modificarlo')
    
    args = parser.parse_args()
    
    # Trova il percorso del database
    db_path = args.db if args.db else find_db_path()
    
    if not db_path:
        logger.error("Database non trovato. Specificare il percorso con --db")
        sys.exit(1)
    
    if not os.path.exists(db_path):
        logger.error(f"Il file database non esiste: {db_path}")
        sys.exit(1)
    
    logger.info(f"Database trovato: {db_path}")
    
    # Prima ispeziona il database se richiesto
    if args.inspect:
        inspect_database(db_path)
        sys.exit(0)
    
    # Inizializza o aggiorna il database
    if args.init:
        success = ensure_documents_table(db_path)
    else:
        success = add_metadata_column(db_path)
    
    if success:
        logger.info("Operazione completata con successo")
        sys.exit(0)
    else:
        logger.error("Operazione fallita")
        sys.exit(1)

if __name__ == "__main__":
    main()