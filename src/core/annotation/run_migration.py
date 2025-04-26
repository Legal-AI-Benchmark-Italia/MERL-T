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
        from ner_giuridico.annotation.db_migrations import run_migrations
        
        # Percorso fisso del database
        db_path = "/home/ec2-user/MERL-T/src/core/annotation/data/annotations.db"

        # Assicurati che la directory esista
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir)
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