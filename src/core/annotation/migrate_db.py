#!/usr/bin/env python3
"""
migrate_db.py

Script per migrare il database delle annotazioni alla versione più recente dello schema.
Aggiunge la colonna 'created_by' alla tabella 'annotations' se non esiste.
"""

import os
import sys
import sqlite3
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('db_migration')

# Definisce il percorso fisso per il database
DB_PATH = "/home/ec2-user/MERL-T/src/core/annotation/data/annotations.db"

def check_column_exists(conn, table, column):
    """
    Verifica se una colonna esiste in una tabella.
    
    Args:
        conn: Connessione SQLite
        table: Nome della tabella
        column: Nome della colonna
        
    Returns:
        bool: True se la colonna esiste, False altrimenti
    """
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    return any(col[1] == column for col in columns)

def add_created_by_column(conn):
    """
    Aggiunge la colonna 'created_by' alla tabella 'annotations'.
    
    Args:
        conn: Connessione SQLite
        
    Returns:
        bool: True se l'operazione è riuscita, False altrimenti
    """
    cursor = conn.cursor()
    try:
        # Check if the annotations table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='annotations'")
        if not cursor.fetchone():
            logger.error("La tabella 'annotations' non esiste nel database")
            return False
        
        # Check if created_by column already exists
        if check_column_exists(conn, 'annotations', 'created_by'):
            logger.info("La colonna 'created_by' esiste già nella tabella 'annotations'")
            return True
        
        # Add the created_by column
        cursor.execute("ALTER TABLE annotations ADD COLUMN created_by TEXT REFERENCES users(id)")
        conn.commit()
        
        logger.info("Colonna 'created_by' aggiunta con successo alla tabella 'annotations'")
        
        # Check if the foreign key was added correctly
        cursor.execute("PRAGMA foreign_key_list(annotations)")
        foreign_keys = cursor.fetchall()
        created_by_fk = any(fk[3] == 'created_by' and fk[2] == 'users' for fk in foreign_keys)
        
        if not created_by_fk:
            logger.warning("Foreign key per 'created_by' non configurato correttamente")
        
        return True
    except sqlite3.Error as e:
        logger.error(f"Errore SQLite durante l'aggiunta della colonna: {e}")
        conn.rollback()
        return False
    except Exception as e:
        logger.error(f"Errore non previsto: {e}")
        conn.rollback()
        return False

def update_existing_annotations(conn):
    """
    Aggiorna le annotazioni esistenti con l'ID dell'utente che ha creato il documento.
    
    Args:
        conn: Connessione SQLite
        
    Returns:
        int: Numero di annotazioni aggiornate
    """
    cursor = conn.cursor()
    try:
        # Get documents with created_by information
        cursor.execute("SELECT id, created_by FROM documents WHERE created_by IS NOT NULL")
        documents = cursor.fetchall()
        
        updated_count = 0
        for doc_id, created_by in documents:
            # Update annotations for this document
            cursor.execute(
                "UPDATE annotations SET created_by = ? WHERE doc_id = ? AND created_by IS NULL",
                (created_by, doc_id)
            )
            updated_count += cursor.rowcount
        
        conn.commit()
        logger.info(f"Aggiornate {updated_count} annotazioni esistenti con l'ID creatore")
        return updated_count
    except sqlite3.Error as e:
        logger.error(f"Errore SQLite durante l'aggiornamento delle annotazioni: {e}")
        conn.rollback()
        return 0

def create_index_if_not_exists(conn):
    """
    Crea indici per migliorare le prestazioni delle query.
    
    Args:
        conn: Connessione SQLite
    """
    cursor = conn.cursor()
    try:
        # Check if index exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_annotations_created_by'")
        if not cursor.fetchone():
            # Create index on created_by column
            cursor.execute("CREATE INDEX idx_annotations_created_by ON annotations(created_by)")
            logger.info("Indice creato su annotations.created_by")
            
        # Check if index exists on doc_id and type
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_annotations_doc_type'")
        if not cursor.fetchone():
            # Create compound index on doc_id and type
            cursor.execute("CREATE INDEX idx_annotations_doc_type ON annotations(doc_id, type)")
            logger.info("Indice creato su annotations(doc_id, type)")
            
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Errore nella creazione degli indici: {e}")
        conn.rollback()

def run_migration():
    """
    Esegue la migrazione del database utilizzando il percorso fisso.
    
    Returns:
        bool: True se la migrazione è riuscita, False altrimenti
    """
    db_path = DB_PATH
    
    if not os.path.exists(os.path.dirname(db_path)):
        try:
            os.makedirs(os.path.dirname(db_path))
            logger.info(f"Creata directory per il database: {os.path.dirname(db_path)}")
        except OSError as e:
            logger.error(f"Impossibile creare la directory per il database {os.path.dirname(db_path)}: {e}")
            return False

    if not os.path.exists(db_path):
        logger.warning(f"Database non trovato in {db_path}. Verrà creato.")
        # La connessione lo creerà se non esiste

    logger.info(f"Utilizzo database: {db_path}")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Add created_by column
        success = add_created_by_column(conn)
        if success:
            # Update existing annotations
            update_existing_annotations(conn)
            
            # Create indexes
            create_index_if_not_exists(conn)
            
            logger.info("Migrazione completata con successo")
        else:
            logger.error("Migrazione fallita")
        
        conn.close()
        return success
    except Exception as e:
        logger.error(f"Errore durante la migrazione: {e}")
        return False

if __name__ == "__main__":
    # Non sono più necessari argomenti da riga di comando per il percorso
    # parser = argparse.ArgumentParser(description="Migra il database delle annotazioni aggiungendo la colonna 'created_by'")
    # parser.add_argument('--db', type=str, help='Percorso del file database SQLite')
    # args = parser.parse_args()
    
    success = run_migration() # Chiama run_migration senza argomenti
    
    if success:
        print("✅ Migrazione completata con successo!")