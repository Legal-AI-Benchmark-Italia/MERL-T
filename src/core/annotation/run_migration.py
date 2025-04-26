#!/usr/bin/env python3
"""
Script to manually run database migrations for NER-Giuridico.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("migration_script")

# Determine PROJECT_ROOT based on the script's location
# Assuming this script is in src/core/annotation/, the root is 3 levels up
try:
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
except IndexError:
    logger.error("Could not determine project root. Make sure the script is in the expected location.")
    sys.exit(1)

# Define paths relative to the project root
DB_PATH = PROJECT_ROOT / "src" / "core" / "annotation" / "data" / "annotations.db"

def setup_environment():
    """Add necessary paths to sys.path."""
    current_dir = Path(__file__).resolve().parent
    parent_dir = current_dir.parent
    
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    # Try to find the root of the project
    project_root = parent_dir
    for _ in range(5):
        if (project_root / "ner_giuridico").exists():
            break
        project_root = project_root.parent
        if project_root == project_root.parent:  # Reached filesystem root
            break
    
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    return current_dir, project_root

def main():
    """Run database migrations."""
    current_dir, project_root = setup_environment()
    
    logger.info(f"Current directory: {current_dir}")
    logger.info(f"Project root: {project_root}")
    
    try:
        from .db_migrations import run_migrations
        
        # Percorso fisso del database (ora definito sopra)
        # db_path = "/Users/guglielmo/Desktop/CODE/MERL-T/src/core/annotation/data/annotations.db"
        db_path = DB_PATH # Usa il path dinamico

        # Assicurati che la directory esista
        db_dir = db_path.parent # Usa pathlib per ottenere la directory
        if not db_dir.exists():
            try:
                db_dir.mkdir(parents=True, exist_ok=True) # Usa pathlib per creare directory
                logger.info(f"Creata directory per il database: {db_dir}")
            except OSError as e:
                logger.error(f"Impossibile creare la directory per il database {db_dir}: {e}")
                sys.exit(1)

        logger.info(f"Using database at: {db_path}")
        
        # Run migrations
        run_migrations(db_path)
        logger.info("Migrations completed successfully")
        
    except ImportError as e:
        logger.error(f"Error importing migration module: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()