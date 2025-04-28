#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MERL-T: Main application entry point.
Integrazione della pipeline di elaborazione e delle interfacce utente.
"""

import os
import sys
import argparse
import logging
import configparser
from pathlib import Path

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('merl-t.log')
    ]
)

# Configurazione dei logger specifici
for logger_name in ["annotator", "db_manager", "db_migrations", "ner"]:
    specific_logger = logging.getLogger(logger_name)
    # Disabilita la propagazione al root logger per evitare log duplicati
    specific_logger.propagate = False

logger = logging.getLogger('merl-t')

# Aggiungi la directory principale del progetto al PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Importazioni interne
from core.config import get_config_manager
from processing.ner.ner_system import NERSystem
from core.annotation.app import app as annotation_app, register_ner_system

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='MERL-T: Sistema di Machine Learning per il diritto')
    parser.add_argument('--config', type=str, default='config.yaml', help='Path del file di configurazione')
    parser.add_argument('--mode', type=str, choices=['annotation', 'processing', 'api', 'all'], 
                        default='all', help='Modalità di esecuzione')
    parser.add_argument('--port', type=int, default=None, help='Porta su cui avviare il server')
    parser.add_argument('--host', type=str, default=None, help='Host su cui avviare il server')
    parser.add_argument('--debug', action='store_true', help='Avvia in modalità debug')
    return parser.parse_args()

def load_config(config_path):
    """Carica la configurazione dal file specificato."""
    config_manager = get_config_manager()
    
    if config_path and os.path.exists(config_path):
        logger.info(f"Caricamento configurazione da {config_path}")
        config_manager.load_from_file(config_path)
    else:
        if config_path:
            logger.warning(f"File di configurazione {config_path} non trovato. Uso configurazione di default.")
        
        # Il config manager caricherà automaticamente la configurazione predefinita
        
    return config_manager

def run_annotation_interface(config, host, port, debug):
    """Avvia l'interfaccia di annotazione."""
    try:
        # Recupera i valori dalla configurazione se non specificati
        if host is None:
            host = config.get('annotation.host', '127.0.0.1')
        
        if port is None:
            port = config.get('annotation.port', 5000)
            
        logger.info("Creazione dell'istanza di NER per l'interfaccia di annotazione...")
        
        # Inizializza il sistema NER con la configurazione corrente
        ner_system = NERSystem()
        
        # Registra il sistema NER nell'app di annotazione
        register_ner_system(ner_system)
        
        logger.info(f"Avvio dell'interfaccia di annotazione su {host}:{port}")
        annotation_app.run(host=host, port=port, debug=debug)
        return True
    except Exception as e:
        logger.error(f"Errore nell'avvio dell'interfaccia di annotazione: {e}", exc_info=True)
        return False

def run_api_server(config, host, port, debug):
    """Avvia il server API."""
    try:
        from processing.ner.api import app as api_app
        
        # Recupera i valori dalla configurazione se non specificati
        if host is None:
            host = config.get('api.host', '127.0.0.1')
        
        if port is None:
            port = config.get('api.port', 8000)
            
        logger.info(f"Avvio del server API su {host}:{port}")
        import uvicorn
        uvicorn.run(api_app, host=host, port=port, log_level="info")
        return True
    except Exception as e:
        logger.error(f"Errore nell'avvio del server API: {e}", exc_info=True)
        return False

def run_processing_pipeline(config):
    """Esegue la pipeline di elaborazione query."""
    try:
        from processing.pipeline import run_pipeline
        
        logger.info("Avvio della pipeline di elaborazione query")
        result = run_pipeline(config)
        logger.info(f"Pipeline completata con risultato: {result}")
        return result
    except Exception as e:
        logger.error(f"Errore nell'esecuzione della pipeline: {e}", exc_info=True)
        return False

def main():
    """Funzione principale."""
    args = parse_args()
    config = load_config(args.config)
    
    logger.info(f"Avvio di MERL-T in modalità: {args.mode}")
    
    if args.mode in ['annotation', 'all']:
        success = run_annotation_interface(config, args.host, args.port, args.debug)
        if not success and args.mode == 'annotation':
            sys.exit(1)
    
    if args.mode in ['api', 'all']:
        # Se stiamo eseguendo sia l'interfaccia di annotazione che l'API,
        # incrementiamo la porta per l'API per evitare conflitti
        api_port = args.port + 1 if args.mode == 'all' and args.port is not None else args.port
        success = run_api_server(config, args.host, api_port, args.debug)
        if not success and args.mode == 'api':
            sys.exit(1)
    
    if args.mode in ['processing', 'all']:
        success = run_processing_pipeline(config)
        if not success and args.mode == 'processing':
            sys.exit(1)
    
    logger.info("MERL-T terminato con successo")
    return 0

if __name__ == "__main__":
    sys.exit(main())