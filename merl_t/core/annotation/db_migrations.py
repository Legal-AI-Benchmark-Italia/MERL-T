#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulo per le migrazioni del database dell'annotatore.
Gestisce l'evoluzione dello schema e le trasformazioni dei dati.
"""

import os
import sys
import logging
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
import datetime

# Configurazione logging
logger = logging.getLogger("annotation.migrations")
logger.setLevel(logging.INFO)

# Verifica se il logger ha già degli handler configurati
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

# Ottieni il percorso del database
def get_db_path():
    """
    Ottiene il percorso del database.
    
    Returns:
        str: Percorso del database
    """
    try:
        from ...config import get_config_manager
        config = get_config_manager()
        db_path = config.get("annotation.database.path")
        if db_path:
            return db_path
    except ImportError:
        pass
    
    # Percorso predefinito
    project_root = Path(__file__).resolve().parents[3]
    return str(project_root / "merl_t" / "data" / "annotation" / "annotations.db")

# Ottieni la directory per i backup
def get_backup_dir():
    """
    Ottiene la directory per i backup.
    
    Returns:
        str: Percorso della directory backup
    """
    try:
        from ...config import get_config_manager
        config = get_config_manager()
        backup_dir = config.get("annotation.database.backup_dir")
        if backup_dir:
            return backup_dir
    except ImportError:
        pass
    
    # Percorso predefinito
    project_root = Path(__file__).resolve().parents[3]
    return str(project_root / "merl_t" / "data" / "annotation" / "backup")

class MigrationManager:
    """
    Manages database migrations to keep the SQLite schema updated.
    """

    def __init__(self):
        """
        Initialize the migration manager using SQLite connection parameters.
        """
        self.db_path = get_db_path()
        self.backup_dir = get_backup_dir()
        self.migrations = []
        self._register_migrations()

    def _get_connection(self):
        """Establish a connection to the SQLite database."""
        try:
            conn = sqlite3.connect(self.db_path)
            return conn
        except sqlite3.Error as e:
            logger.error(f"Failed to connect to SQLite for migrations: {e}")
            raise

    def _register_migrations(self):
        """Register all available migrations in order."""
        self.migrations.append({
            "version": "001_add_created_by_to_annotations",
            "description": "Add created_by column to annotations table",
            "function": self._migration_001_add_created_by_to_annotations
        })
        self.migrations.append({
            "version": "002_add_metadata_to_documents",
            "description": "Add metadata column (JSONB) to documents table",
            "function": self._migration_002_add_metadata_to_documents
        })
        self.migrations.append({
            "version": "003_add_status_to_documents",
            "description": "Add a status column (TEXT) to the documents table",
            "function": self._migration_003_add_status_to_documents
        })
        self.migrations.append({
            "version": "004_add_graph_tables",
            "description": "Add tables for graph chunks, proposals, votes (using JSONB)",
            "function": self._migration_004_add_graph_tables
        })
        self.migrations.append({
            "version": "005_add_seed_node_id_to_chunks",
            "description": "Add seed_node_id column (TEXT) to graph_chunks table",
            "function": self._migration_005_add_seed_node_id_to_chunks
        })
        self.migrations.append({
             "version": "006_rename_annotation_columns",
             "description": "Rename annotation columns start->start_offset, end->end_offset",
             "function": self._migration_006_rename_annotation_columns
        })

        logger.debug(f"Registered {len(self.migrations)} migrations.")

    def _check_table_exists(self, cursor, table_name) -> bool:
        """Check if a table exists in SQLite."""
        cursor.execute("""
            SELECT name FROM sqlite_master WHERE type='table' AND name=?;
        """, (table_name,))
        return cursor.fetchone() is not None
    
    def _check_column_exists(self, cursor, table_name, column_name) -> bool:
        """Check if a column exists in a SQLite table."""
        cursor.execute("""
            SELECT name FROM pragma_table_info(?) WHERE name=?;
        """, (table_name, column_name))
        return cursor.fetchone() is not None

    def _create_migrations_table(self):
        """Create the migrations tracking table if it doesn't exist in SQLite."""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS db_migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL UNIQUE,
                    applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
                ''')
                conn.commit()
                logger.debug("Migrations table created or already exists")

    def _get_applied_migrations(self) -> List[str]:
        """Get applied migration versions from SQLite."""
        applied_migrations = []
        try:
            with self._get_connection() as conn:
                 with conn.cursor() as cursor:
                    # Check if table exists first to avoid error on fresh DB
                    if self._check_table_exists(cursor, 'db_migrations'):
                        cursor.execute("SELECT version FROM db_migrations ORDER BY id")
                        applied_migrations = [row[0] for row in cursor.fetchall()]
                    else:
                         logger.info("'db_migrations' table not found, assuming no migrations applied yet.")
        except sqlite3.Error as e:
            logger.error(f"Error fetching applied migrations: {e}")
            # Depending on policy, might want to raise here
        return applied_migrations

    def _record_migration(self, version: str, description: str = None):
        """Record applied migration in SQLite."""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                now = datetime.datetime.now(datetime.timezone.utc)
                cursor.execute(
                    "INSERT INTO db_migrations (version, applied_at, description) VALUES (?, ?, ?)",
                    (version, now, description)
                )
                conn.commit()

    def run_migrations(self):
        """Run all pending migrations on SQLite database."""
        logger.info(f"Checking for pending migrations in SQLite DB: {self.db_path}")
        self._create_migrations_table()
        applied_migrations = self._get_applied_migrations()
        logger.info(f"Found {len(applied_migrations)} previously applied migrations")

        pending_count = sum(1 for m in self.migrations if m['version'] not in applied_migrations)
        if pending_count == 0:
            logger.info("No pending migrations found. Database schema is up to date.")
            return

        logger.info(f"Found {pending_count} pending migrations to apply")

        for migration in self.migrations:
            version = migration['version']
            if version not in applied_migrations:
                logger.info(f"Applying migration: {version} - {migration['description']}")
                try:
                    # Run migration function (these need to be adapted for SQLite)
                    migration['function']()
                    self._record_migration(version, migration['description'])
                    logger.info(f"Migration {version} applied successfully")
                except Exception as e:
                    logger.error(f"Error applying migration {version}: {e}", exc_info=True)
                    # Rollback might happen automatically depending on connection settings,
                    # but explicit rollback or handling is safer.
                    # For now, we raise to stop further migrations on error.
                    raise

        logger.info("All migrations applied successfully")

    # --- Migration Implementations (SQLite Syntax) --- 

    def _migration_001_add_created_by_to_annotations(self):
        """Add created_by column (TEXT) to annotations table in SQLite."""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                if not self._check_column_exists(cursor, 'annotations', 'created_by'):
                    logger.info("Adding created_by column to annotations table")
                    try:
                        # Add column and FK constraint
                        cursor.execute("ALTER TABLE annotations ADD COLUMN created_by TEXT")
                        # Add FK constraint separately for clarity, make it deferrable initially if needed
                        cursor.execute("""
                            ALTER TABLE annotations 
                            ADD CONSTRAINT fk_annotations_created_by FOREIGN KEY (created_by) 
                            REFERENCES users(id) ON DELETE SET NULL
                        """)
                        conn.commit()
                        logger.info("Column created_by and foreign key added successfully")
                    except sqlite3.Error as e:
                        logger.error(f"Error adding created_by column/FK: {e}")
                        conn.rollback()
                        raise
                else:
                    logger.info("Column created_by already exists in annotations table")

    def _migration_002_add_metadata_to_documents(self):
        """Add metadata column (JSONB) to documents table in SQLite."""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                if not self._check_column_exists(cursor, 'documents', 'metadata'):
                    logger.info("Adding metadata (JSONB) column to documents table")
                    try:
                        cursor.execute("ALTER TABLE documents ADD COLUMN metadata TEXT")
                        conn.commit()
                        logger.info("Column metadata (JSONB) added successfully")
                    except sqlite3.Error as e:
                        logger.error(f"Error adding metadata column: {e}")
                        conn.rollback()
                        raise
                else:
                    # Check if existing metadata column is TEXT and needs conversion
                    cursor.execute("""
                        SELECT type FROM pragma_table_info(documents) WHERE name='metadata'
                    """)
                    col_type = cursor.fetchone()
                    if col_type and col_type[0].lower() != 'text':
                         logger.warning("Column metadata exists but is not TEXT. Attempting conversion (requires valid JSON in existing data)...")
                         try:
                              # Conversion might fail if existing data isn't valid JSON
                              cursor.execute("ALTER TABLE documents ALTER COLUMN metadata TYPE TEXT USING metadata::TEXT")
                              conn.commit()
                              logger.info("Column metadata successfully converted to TEXT.")
                         except sqlite3.Error as e:
                              logger.error(f"Failed to convert existing metadata column to TEXT: {e}. Manual intervention may be required.")
                              conn.rollback()
                              # Decide whether to raise or continue
                              # raise # Stop migration if conversion fails
                    else:
                         logger.info("Column metadata (TEXT) already exists in documents table")

    def _migration_003_add_status_to_documents(self):
        """Add status column (TEXT) to documents table in SQLite."""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                 if not self._check_table_exists(cursor, 'documents'):
                      logger.error("Table 'documents' does not exist. Cannot apply migration 003.")
                      raise RuntimeError("Prerequisite table 'documents' missing for migration 003")
                 
                 if not self._check_column_exists(cursor, 'documents', 'status'):
                    logger.info("Adding 'status' column to 'documents' table with default 'pending'")
                    try:
                        cursor.execute("ALTER TABLE documents ADD COLUMN status TEXT DEFAULT 'pending'")
                        # Update existing rows that might be NULL (though default should handle new ones)
                        cursor.execute("UPDATE documents SET status = 'pending' WHERE status IS NULL")
                        # Create index
                        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)")
                        conn.commit()
                        logger.info("Column 'status' and index added successfully.")
                    except sqlite3.Error as e:
                         logger.error(f"Error adding status column/index: {e}")
                         conn.rollback()
                         raise
                 else:
                    logger.info("Column 'status' already exists in 'documents'.")

    def _migration_004_add_graph_tables(self):
        """Ensure graph tables (chunks, proposals, votes) exist."""
        # This migration now effectively just calls _init_db from db_manager,
        # which should create tables if they don't exist. We add logging here.
        logger.info("Running migration 004: Ensure graph tables exist")
        try:
            # We can't directly call the db_manager _init_db easily here.
            # Instead, we execute the CREATE TABLE IF NOT EXISTS commands again.
            # This is idempotent and safe.
            from merl_t.core.annotation.db_manager import AnnotationDBManager # Import locally
            temp_db_manager = AnnotationDBManager() # Create temporary instance to get definitions
            graph_table_defs = { 
                 k: v for k, v in temp_db_manager.table_definitions.items() 
                 if k in ['graph_chunks', 'graph_proposals', 'graph_votes']
            }
            graph_index_defs = [ 
                 d for d in temp_db_manager.index_definitions 
                 if 'graph_' in d # Simple filter for graph related indexes
            ]

            with self._get_connection() as conn:
                 with conn.cursor() as cursor:
                      logger.info("Ensuring graph tables exist...")
                      for name, definition in graph_table_defs.items():
                           logger.debug(f"Executing CREATE TABLE IF NOT EXISTS for {name}...")
                           cursor.execute(definition)
                      logger.info("Ensuring graph indexes exist...")
                      for definition in graph_index_defs:
                            logger.debug(f"Executing CREATE INDEX IF NOT EXISTS: {definition[:60]}...")
                            cursor.execute(definition)
                      conn.commit()
            logger.info("Graph tables and indexes checked/created successfully.")
        except Exception as e:
             logger.error(f"Error ensuring graph tables/indexes: {e}", exc_info=True)
             raise

    def _migration_005_add_seed_node_id_to_chunks(self):
        """Add seed_node_id column (TEXT) to graph_chunks table in SQLite."""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                 if not self._check_table_exists(cursor, 'graph_chunks'):
                      logger.error("Table 'graph_chunks' does not exist. Cannot apply migration 005.")
                      raise RuntimeError("Prerequisite table 'graph_chunks' missing for migration 005")
                 
                 if not self._check_column_exists(cursor, 'graph_chunks', 'seed_node_id'):
                    logger.info("Adding 'seed_node_id' column (TEXT) to 'graph_chunks' table")
                    try:
                        cursor.execute("ALTER TABLE graph_chunks ADD COLUMN seed_node_id TEXT")
                        cursor.execute("CREATE INDEX IF NOT EXISTS idx_graph_chunks_seed_node_id ON graph_chunks(seed_node_id)")
                        conn.commit()
                        logger.info("Column 'seed_node_id' and index added successfully.")
                    except sqlite3.Error as e:
                         logger.error(f"Error adding seed_node_id column/index: {e}")
                         conn.rollback()
                         raise
                 else:
                    logger.info("Column 'seed_node_id' already exists in 'graph_chunks'.")
                    
    def _migration_006_rename_annotation_columns(self):
         """Rename annotation columns start->start_offset and end->end_offset."""
         with self._get_connection() as conn:
            with conn.cursor() as cursor:
                if not self._check_table_exists(cursor, 'annotations'):
                     logger.error("Table 'annotations' does not exist. Cannot apply migration 006.")
                     raise RuntimeError("Prerequisite table 'annotations' missing for migration 006")

                renamed_start = False
                renamed_end = False
                
                # Check and rename 'start' to 'start_offset'
                if self._check_column_exists(cursor, 'annotations', 'start') and \
                   not self._check_column_exists(cursor, 'annotations', 'start_offset'):
                    try:
                         logger.info("Renaming column 'start' to 'start_offset' in 'annotations' table...")
                         cursor.execute("ALTER TABLE annotations RENAME COLUMN start TO start_offset")
                         # Commit immediately after successful rename
                         conn.commit()
                         logger.info("Column 'start' renamed successfully.")
                         renamed_start = True
                    except sqlite3.Error as e:
                         logger.error(f"Error renaming 'start' column: {e}")
                         conn.rollback()
                         raise # Stop if renaming fails
                elif self._check_column_exists(cursor, 'annotations', 'start_offset'):
                     logger.info("Column 'start_offset' already exists or 'start' did not exist.")
                     renamed_start = True # Assume ok if target exists
                # Added else block for clarity if neither condition met     
                else:
                     logger.info("Column 'start' does not exist, skipping rename to 'start_offset'.")
                     
                # Check and rename 'end' to 'end_offset'
                # Corrected the backslash continuation and quoting for "end"
                if self._check_column_exists(cursor, 'annotations', 'end') and \
                   not self._check_column_exists(cursor, 'annotations', 'end_offset'):
                    try:
                         logger.info("Renaming column 'end' to 'end_offset' in 'annotations' table...")
                         # Use double quotes for the potentially reserved keyword "end"
                         cursor.execute('ALTER TABLE annotations RENAME COLUMN "end" TO end_offset') 
                         # Commit immediately after successful rename
                         conn.commit()
                         logger.info("Column 'end' renamed successfully.")
                         renamed_end = True
                    except sqlite3.Error as e:
                         logger.error(f"Error renaming 'end' column: {e}")
                         conn.rollback()
                         raise # Stop if renaming fails
                elif self._check_column_exists(cursor, 'annotations', 'end_offset'):
                     logger.info("Column 'end_offset' already exists or 'end' did not exist.")
                     renamed_end = True # Assume ok if target exists
                # Added else block for clarity
                else:
                    logger.info("Column 'end' does not exist, skipping rename to 'end_offset'.")
                     
                if not renamed_start or not renamed_end:
                     # This is just a warning, migration might still be considered successful overall
                     logger.warning("Migration 006 check: One or both columns ('start_offset', 'end_offset') may not have required renaming or verification.")


def run_migrations_for_sqlite():
    """
    Run database migrations specifically for SQLite.
    Reads connection details from the config manager.
    """
    try:
        logger.info("Inizializzazione migrazione database SQLite...")
        manager = MigrationManager() # Reads config automatically
        
        # Verifica connessione al database
        try:
            with manager._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    logger.info("Connessione al database SQLite verificata.")
        except Exception as e:
            logger.error(f"Errore di connessione al database SQLite: {e}")
            raise
        
        # Esegui le migrazioni
        try:
            manager.run_migrations()
            logger.info("Migrazioni database SQLite completate con successo.")
        except Exception as e:
            logger.error(f"Errore durante l'esecuzione delle migrazioni: {e}")
            raise
            
    except ValueError as e:
        logger.error(f"Errore di configurazione durante le migrazioni: {e}")
        raise
    except sqlite3.Error as e:
        logger.error(f"Errore database durante le migrazioni: {e}")
        raise
    except Exception as e:
        logger.error(f"Errore imprevisto durante le migrazioni: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # This allows running migrations directly from the command line
    import argparse

    # No longer need --db argument as it reads from config
    parser = argparse.ArgumentParser(description="Run SQLite database migrations for MERL-T")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
        # Set other loggers to debug as well if needed
        logging.getLogger("db_manager").setLevel(logging.DEBUG) 
        logger.debug("Verbose logging enabled")

    run_migrations_for_sqlite()