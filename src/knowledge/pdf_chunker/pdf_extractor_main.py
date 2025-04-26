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

# Importa i moduli del progetto
from src.config import Config
from src.processor import PDFProcessor
from src.parallel import ParallelExecutor
from src.cpu_monitor import CPUMonitor
from src.progress_tracker import ProgressTracker
from src.output_manager import OutputManager
from src.utils import setup_logging, find_pdf_files

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
    
    parser.add_argument('--input-dir', default=Config.INPUT_FOLDER,
                        help='Cartella contenente i PDF da processare')
    parser.add_argument('--output-dir', default=Config.OUTPUT_FOLDER,
                        help='Cartella dove salvare i risultati')
    parser.add_argument('--min-chunk-size', type=int, default=Config.MIN_CHUNK_SIZE,
                        help='Dimensione minima in caratteri per chunk')
    parser.add_argument('--max-chunk-size', type=int, default=Config.MAX_CHUNK_SIZE,
                        help='Dimensione massima in caratteri per chunk')
    parser.add_argument('--overlap', type=int, default=Config.OVERLAP_SIZE,
                        help='Sovrapposizione in caratteri tra chunk')
    parser.add_argument('--sliding-window', action='store_true', default=Config.USE_SLIDING_WINDOW,
                        help='Usa approccio a finestra scorrevole')
    parser.add_argument('--workers', type=int, default=Config.MAX_WORKERS,
                        help='Numero di worker (0=auto)')
    parser.add_argument('--cpu-limit', type=int, default=Config.CPU_LIMIT,
                        help='Limite di utilizzo CPU in percentuale')
    parser.add_argument('--language', default=Config.LANGUAGE,
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
    Config.INPUT_FOLDER = args.input_dir
    Config.OUTPUT_FOLDER = args.output_dir
    Config.MIN_CHUNK_SIZE = args.min_chunk_size
    Config.MAX_CHUNK_SIZE = args.max_chunk_size
    Config.OVERLAP_SIZE = args.overlap
    Config.USE_SLIDING_WINDOW = args.sliding_window
    Config.MAX_WORKERS = args.workers
    Config.CPU_LIMIT = args.cpu_limit
    Config.LANGUAGE = args.language
    
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
    
    # Configura il logging
    logger = setup_logging()
    
    # Registra handler per segnali
    signal.signal(signal.SIGINT, sigint_handler)
    atexit.register(cleanup_handler)
    
    try:
        # Inizializza componenti
        progress_tracker = ProgressTracker(Config.PROGRESS_FILE)
        cpu_monitor = CPUMonitor(Config.CPU_LIMIT, Config.CPU_CHECK_INTERVAL)
        output_manager = OutputManager(Config.OUTPUT_FOLDER)
        
        # Avvia il monitoraggio della CPU
        cpu_monitor.start()
        
        # Trova tutti i PDF nella cartella di input
        pdf_files = find_pdf_files(Config.INPUT_FOLDER)
        
        if not pdf_files:
            logger.error("Nessun file PDF trovato. Uscita.")
            return 1
        
        # Recupera i PDF già elaborati e filtra quelli da processare
        processed_pdfs = progress_tracker.get_processed_pdfs()
        pdf_files_to_process = [pdf for pdf in pdf_files if pdf not in processed_pdfs]
        
        if len(pdf_files_to_process) < len(pdf_files):
            logger.info(f"Saltando {len(pdf_files) - len(pdf_files_to_process)} PDF già elaborati")
        
        if not pdf_files_to_process:
            logger.info("Tutti i PDF sono già stati elaborati. Uscita.")
            return 0
        
        # Crea la cartella di output
        os.makedirs(Config.OUTPUT_FOLDER, exist_ok=True)
        
        # Configura e avvia l'executor parallelo
        executor = ParallelExecutor(
            num_workers=Config.MAX_WORKERS,
            cpu_monitor=cpu_monitor,
            progress_tracker=progress_tracker
        )
        
        # Processa i PDF in parallelo
        executor.process_pdfs(pdf_files_to_process, Config)
        
        # Crea file di output combinati
        output_manager.create_combined_outputs()
        
        logger.info("Elaborazione completata con successo!")
        return 0
        
    except Exception as e:
        logger.exception(f"Errore nell'elaborazione: {str(e)}")
        return 1
    finally:
        # Ferma il monitoraggio della CPU
        if 'cpu_monitor' in locals():
            cpu_monitor.stop()

if __name__ == "__main__":
    sys.exit(main())