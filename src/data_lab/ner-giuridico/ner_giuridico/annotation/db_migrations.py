#!/usr/bin/env python3
"""
Database migration system for NER-Giuridico annotation tool.
Handles schema updates while preserving existing data.
"""

import os
import sqlite3
import logging
import datetime
from pathlib import Path
from typing import List, Dict, Callable, Any

# Setup logger
logger = logging.getLogger("db_migrations")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

class MigrationManager:
    """
    Manages database migrations to keep the schema updated.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the migration manager.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.migrations = []
        
        # Register all migrations
        self._register_migrations()
    
    def _register_migrations(self):
        """Register all available migrations in order."""
        # Add migrations in sequence
        self.migrations.append({
            "version": "001_add_created_by_to_annotations",
            "description": "Add created_by column to annotations table",
            "function": self._migration_001_add_created_by_to_annotations
        })
        # Add more migrations here as needed
    
    def _create_migrations_table(self):
        """Create the migrations tracking table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS db_migrations (
                id INTEGER PRIMARY KEY,
                version TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL,
                description TEXT
            )
            ''')
            conn.commit()
            logger.debug("Migrations table created or already exists")
    
    def _get_applied_migrations(self) -> List[str]:
        """
        Get a list of migration versions that have already been applied.
        
        Returns:
            List of applied migration version strings
        """
        applied_migrations = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT version FROM db_migrations ORDER BY id")
                applied_migrations = [row[0] for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            # Table might not exist yet
            pass
        return applied_migrations
    
    def _record_migration(self, version: str, description: str = None):
        """
        Record that a migration has been applied.
        
        Args:
            version: Migration version identifier
            description: Optional description of the migration
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            now = datetime.datetime.now().isoformat()
            cursor.execute(
                "INSERT INTO db_migrations (version, applied_at, description) VALUES (?, ?, ?)",
                (version, now, description)
            )
            conn.commit()
    
    def run_migrations(self):
        """Run all pending migrations in order."""
        logger.info(f"Checking for pending migrations in {self.db_path}")
        
        # Create migrations table if needed
        self._create_migrations_table()
        
        # Get already applied migrations
        applied_migrations = self._get_applied_migrations()
        logger.info(f"Found {len(applied_migrations)} previously applied migrations")
        
        # Count pending migrations
        pending_count = sum(1 for m in self.migrations if m['version'] not in applied_migrations)
        if pending_count == 0:
            logger.info("No pending migrations found. Database schema is up to date.")
            return
        
        logger.info(f"Found {pending_count} pending migrations to apply")
        
        # Apply pending migrations
        for migration in self.migrations:
            version = migration['version']
            if version not in applied_migrations:
                logger.info(f"Applying migration: {version} - {migration['description']}")
                try:
                    # Run the migration function
                    migration['function']()
                    # Record the migration as applied
                    self._record_migration(version, migration['description'])
                    logger.info(f"Migration {version} applied successfully")
                except Exception as e:
                    logger.error(f"Error applying migration {version}: {e}")
                    raise
        
        logger.info("All migrations applied successfully")
    
    # Migration implementations
    
    def _migration_001_add_created_by_to_annotations(self):
        """Add created_by column to the annotations table."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if column already exists
            cursor.execute("PRAGMA table_info(annotations)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'created_by' not in columns:
                logger.info("Adding created_by column to annotations table")
                try:
                    # Add the column
                    cursor.execute("ALTER TABLE annotations ADD COLUMN created_by TEXT")
                    
                    # Optional: Update existing records with a default value or NULL
                    # cursor.execute("UPDATE annotations SET created_by = NULL")
                    
                    conn.commit()
                    logger.info("Column added successfully")
                except sqlite3.OperationalError as e:
                    # Handle potential errors (e.g., table doesn't exist)
                    logger.error(f"Error adding column: {e}")
                    raise
            else:
                logger.info("Column created_by already exists in annotations table")


def run_migrations(db_path: str):
    """
    Run database migrations for the given database.
    
    Args:
        db_path: Path to the SQLite database file
    """
    manager = MigrationManager(db_path)
    manager.run_migrations()


if __name__ == "__main__":
    # This allows running migrations directly from the command line
    import argparse
    
    parser = argparse.ArgumentParser(description="Run database migrations for NER-Giuridico")
    parser.add_argument("--db", type=str, required=True, help="Path to the SQLite database file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    run_migrations(args.db)