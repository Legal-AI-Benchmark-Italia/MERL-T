#!/usr/bin/env python3
"""
Script to ensure the metadata column exists in the documents table.
Run this script to fix document display issues with multiple uploads.
"""

import os
import sqlite3
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('db_fix')

def find_db_path():
    """Find the database path in the project."""
    # Common paths to check
    potential_paths = [
        'data/annotations.db',
        'ner_giuridico/annotation/data/annotations.db',
        'src/data_lab/ner-giuridico/ner_giuridico/annotation/data/annotations.db'
    ]
    
    for path in potential_paths:
        if os.path.exists(path):
            return path
    
    # Recursive search up to 3 levels up
    current_dir = Path.cwd()
    for _ in range(4):
        for root, dirs, files in os.walk(current_dir):
            for file in files:
                if file == 'annotations.db':
                    return os.path.join(root, file)
        
        parent = current_dir.parent
        if parent == current_dir:  # Reached root directory
            break
        current_dir = parent
    
    return None

def check_column_exists(conn, table, column):
    """Check if a column exists in a table."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    for col in columns:
        if col[1] == column:
            return True
    return False

def add_metadata_column(db_path):
    """Add the metadata column to the documents table."""
    logger.info(f"Working with database at: {db_path}")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the documents table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'")
        if not cursor.fetchone():
            logger.error("The 'documents' table doesn't exist in the database")
            conn.close()
            return False
        
        # Check if metadata column already exists
        if check_column_exists(conn, 'documents', 'metadata'):
            logger.info("The 'metadata' column already exists in the 'documents' table")
            conn.close()
            return True
        
        # Add the metadata column
        cursor.execute("ALTER TABLE documents ADD COLUMN metadata TEXT")
        conn.commit()
        
        # Verify the column was added
        if check_column_exists(conn, 'documents', 'metadata'):
            logger.info("Successfully added 'metadata' column to the 'documents' table")
            conn.close()
            return True
        else:
            logger.error("Error adding the 'metadata' column")
            conn.close()
            return False
            
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def main():
    # Find the database path
    db_path = find_db_path()
    
    if not db_path:
        logger.error("Database not found. The application must be initialized first.")
        sys.exit(1)
    
    if not os.path.exists(db_path):
        logger.error(f"The database file doesn't exist: {db_path}")
        sys.exit(1)
    
    logger.info(f"Found database at: {db_path}")
    
    # Add the metadata column
    success = add_metadata_column(db_path)
    
    if success:
        logger.info("✅ Database migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Database migration failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()