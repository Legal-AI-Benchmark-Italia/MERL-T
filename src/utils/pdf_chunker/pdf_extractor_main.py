#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Chunker - Script per elaborare documenti PDF giuridici e preparare dataset per LLM.

Questo script principale orchestra le diverse componenti del sistema.
"""

import os
import sys
import signal
import atexit
import argparse
import logging
from datetime import datetime

# Aggiungiamo il percorso root al PYTHONPATH per importare i moduli del progetto
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT_DIR)

# Importa i moduli del progetto
from src.utils.pdf_chunker.src import (
    Config,
    PDFProcessor,
    ParallelExecutor,
    CPUMonitor,
    ProgressTracker,
    OutputManager,
    setup_logging,
    find_pdf_files
)

# Importa il gestore di configurazione centralizzato
from src.core.config import get_config_manager

def parse_arguments():
    """
    Analizza gli argomenti da riga di comando.
    
    Returns:
        Namespace con gli argomenti
    """
    parser = argparse.ArgumentParser(
        description='PDF Chunker - Elabora documenti PDF per dataset LLM',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('--input-dir', required=True,
                        help='Cartella contenente i PDF da processare')
    parser.add_argument('--output-dir', required=True,
                        help='Cartella dove salvare i risultati')
    parser.add_argument('--simple-extract', action='store_true',
                        help='Modalità semplice estrazione: converte PDF in file di testo')
    parser.add_argument('--min-chunk-size', type=int, default=1000,
                        help='Dimensione minima in caratteri per chunk')
    parser.add_argument('--max-chunk-size', type=int, default=2000,
                        help='Dimensione massima in caratteri per chunk')
    parser.add_argument('--overlap', type=int, default=200,
                        help='Sovrapposizione in caratteri tra chunk')
    parser.add_argument('--sliding-window', action='store_true',
                        help='Usa approccio a finestra scorrevole')
    parser.add_argument('--workers', type=int, default=0,
                        help='Numero di worker (0=auto)')
    parser.add_argument('--cpu-limit', type=int, default=80,
                        help='Limite di utilizzo CPU in percentuale')
    parser.add_argument('--language', default='it',
                        help='Lingua per tokenizzazione')
    parser.add_argument('--debug', action='store_true',
                        help='Abilita modalità debug')
    
    return parser.parse_args()

def update_config_from_args(args):
    """
    Aggiorna la configurazione con gli argomenti da riga di comando.
    
    Args:
        args: Argomenti da riga di comando
    """
    # Aggiorna la configurazione locale
    Config.INPUT_FOLDER = args.input_dir
    Config.OUTPUT_FOLDER = args.output_dir
    Config.MIN_CHUNK_SIZE = args.min_chunk_size
    Config.MAX_CHUNK_SIZE = args.max_chunk_size
    Config.OVERLAP_SIZE = args.overlap
    Config.USE_SLIDING_WINDOW = args.sliding_window
    Config.MAX_WORKERS = args.workers
    Config.CPU_LIMIT = args.cpu_limit
    Config.LANGUAGE = args.language
    Config.SIMPLE_EXTRACT = args.simple_extract
    
    if args.debug:
        Config.LOG_LEVEL = logging.DEBUG

def cleanup_handler():
    """
    Handler per la pulizia delle risorse quando il programma termina.
    """
    logger = logging.getLogger("PDFChunker")
    logger.info("Pulizia risorse in corso...")
    
def sigint_handler(sig, frame):
    """
    Gestisce l'interruzione da tastiera (CTRL+C).
    """
    logger = logging.getLogger("PDFChunker")
    logger.warning("Ricevuto segnale di interruzione. Uscita in corso...")
    cleanup_handler()
    sys.exit(0)

def main():
    """
    Funzione principale.
    """
    # Analizza gli argomenti e aggiorna la configurazione
    args = parse_arguments()
    update_config_from_args(args)
    
    # Crea le directory necessarie
    os.makedirs(args.input_dir, exist_ok=True)
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Configura il logging
    log_file = os.path.join(args.output_dir, f"pdf_chunker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    logger = setup_logging(log_file=log_file)
    
    # Registra handler per segnali
    signal.signal(signal.SIGINT, sigint_handler)
    atexit.register(cleanup_handler)
    
    try:
        # Inizializza componenti
        progress_file = os.path.join(args.output_dir, 'progress.json')
        progress_tracker = ProgressTracker(progress_file)
        cpu_monitor = CPUMonitor(Config.CPU_LIMIT, 5)
        output_manager = OutputManager(args.output_dir)
        
        # Avvia il monitoraggio della CPU
        cpu_monitor.start()
        
        # Trova tutti i PDF nella cartella di input
        pdf_files = find_pdf_files(args.input_dir)
        
        if not pdf_files:
            logger.error("Nessun file PDF trovato in %s. Uscita.", args.input_dir)
            return 1
        
        # Recupera i PDF già elaborati e filtra quelli da processare
        processed_pdfs = progress_tracker.get_processed_pdfs()
        pdf_files_to_process = [pdf for pdf in pdf_files if pdf not in processed_pdfs]
        
        if len(pdf_files_to_process) < len(pdf_files):
            logger.info("Saltando %d PDF già elaborati", len(pdf_files) - len(pdf_files_to_process))
        
        if not pdf_files_to_process:
            logger.info("Tutti i PDF sono già stati elaborati. Uscita.")
            return 0
        
        # Configura e avvia l'executor parallelo
        executor = ParallelExecutor(
            num_workers=Config.MAX_WORKERS,
            cpu_monitor=cpu_monitor,
            progress_tracker=progress_tracker
        )
        
        # Processa i PDF in parallelo
        if Config.SIMPLE_EXTRACT:
            executor.simple_extract_pdfs(pdf_files_to_process, Config)
        else:
            executor.process_pdfs(pdf_files_to_process, Config)
        
        # Crea file di output combinati solo se non in modalità semplice estrazione
        if not Config.SIMPLE_EXTRACT:
            output_manager.create_combined_outputs()
        
        logger.info("Elaborazione completata con successo!")
        return 0
        
    except Exception as e:
        logger.exception("Errore nell'elaborazione: %s", str(e))
        return 1
    finally:
        # Ferma il monitoraggio della CPU
        if 'cpu_monitor' in locals():
            cpu_monitor.stop()

if __name__ == "__main__":
    sys.exit(main())