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
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)

# Importa i moduli del progetto
from src.config import Config
from src.processor import PDFProcessor
from src.parallel import ParallelExecutor
from src.cpu_monitor import CPUMonitor
from src.progress_tracker import ProgressTracker
from src.output_manager import OutputManager
from src.utils import setup_logging, find_pdf_files

# Importa il gestore di configurazione centralizzato
from src.core.config import get_config_manager

def parse_arguments():
    """
    Analizza gli argomenti da riga di comando.
    
    Returns:
        Namespace con gli argomenti
    """
    # Ottieni le configurazioni predefinite dal ConfigManager
    config_manager = get_config_manager()
    pdf_config = config_manager.get_pdf_chunker_config()
    pdf_paths = config_manager.get_pdf_chunker_paths()
    
    parser = argparse.ArgumentParser(
        description='PDF Chunker - Elabora documenti PDF per dataset LLM',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('--input-dir', default=pdf_paths.get('input', Config.INPUT_FOLDER),
                        help='Cartella contenente i PDF da processare')
    parser.add_argument('--output-dir', default=pdf_paths.get('output', Config.OUTPUT_FOLDER),
                        help='Cartella dove salvare i risultati')
    parser.add_argument('--min-chunk-size', type=int, 
                        default=pdf_config.get('chunk_size', {}).get('min', Config.MIN_CHUNK_SIZE),
                        help='Dimensione minima in caratteri per chunk')
    parser.add_argument('--max-chunk-size', type=int, 
                        default=pdf_config.get('chunk_size', {}).get('max', Config.MAX_CHUNK_SIZE),
                        help='Dimensione massima in caratteri per chunk')
    parser.add_argument('--overlap', type=int, 
                        default=pdf_config.get('chunk_size', {}).get('overlap', Config.OVERLAP_SIZE),
                        help='Sovrapposizione in caratteri tra chunk')
    parser.add_argument('--sliding-window', action='store_true', 
                        default=pdf_config.get('processing', {}).get('use_sliding_window', Config.USE_SLIDING_WINDOW),
                        help='Usa approccio a finestra scorrevole')
    parser.add_argument('--workers', type=int, 
                        default=pdf_config.get('processing', {}).get('max_workers', Config.MAX_WORKERS),
                        help='Numero di worker (0=auto)')
    parser.add_argument('--cpu-limit', type=int, 
                        default=pdf_config.get('processing', {}).get('cpu_limit', Config.CPU_LIMIT),
                        help='Limite di utilizzo CPU in percentuale')
    parser.add_argument('--language', default=pdf_config.get('language', Config.LANGUAGE),
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
    
    # Ottieni il gestore configurazione e aggiorna le configurazioni globali
    config_manager = get_config_manager()
    
    # Aggiorna le configurazioni nel ConfigManager
    config_manager.set('pdf_chunker.input_folder', args.input_dir)
    config_manager.set('pdf_chunker.output_folder', args.output_dir)
    config_manager.set('pdf_chunker.chunk_size.min', args.min_chunk_size)
    config_manager.set('pdf_chunker.chunk_size.max', args.max_chunk_size)
    config_manager.set('pdf_chunker.chunk_size.overlap', args.overlap)
    config_manager.set('pdf_chunker.processing.use_sliding_window', args.sliding_window)
    config_manager.set('pdf_chunker.processing.max_workers', args.workers)
    config_manager.set('pdf_chunker.processing.cpu_limit', args.cpu_limit)
    config_manager.set('pdf_chunker.language', args.language)
    
    if args.debug:
        Config.LOG_LEVEL = logging.DEBUG
        config_manager.set('general.log_level', 'DEBUG')

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
    # Ottieni il ConfigManager
    config_manager = get_config_manager()
    pdf_config = config_manager.get_pdf_chunker_config()
    pdf_paths = config_manager.get_pdf_chunker_paths()
    
    # Analizza gli argomenti e aggiorna la configurazione
    args = parse_arguments()
    update_config_from_args(args)
    
    # Configura il logging
    log_file = pdf_paths.get('log', 'pdf_chunker.log')
    logger = setup_logging(log_file=log_file)
    
    # Registra handler per segnali
    signal.signal(signal.SIGINT, sigint_handler)
    atexit.register(cleanup_handler)
    
    try:
        # Ottieni i percorsi dalla configurazione centralizzata
        input_folder = pdf_paths.get('input')
        output_folder = pdf_paths.get('output')
        progress_file = pdf_paths.get('progress', 'progress.json')
        
        # Ottieni le configurazioni di processing
        cpu_limit = pdf_config.get('processing', {}).get('cpu_limit', 80)
        cpu_check_interval = pdf_config.get('processing', {}).get('cpu_check_interval', 5)
        max_workers = pdf_config.get('processing', {}).get('max_workers', 0)
        
        # Inizializza componenti
        progress_tracker = ProgressTracker(progress_file)
        cpu_monitor = CPUMonitor(cpu_limit, cpu_check_interval)
        output_manager = OutputManager(output_folder)
        
        # Avvia il monitoraggio della CPU
        cpu_monitor.start()
        
        # Trova tutti i PDF nella cartella di input
        pdf_files = find_pdf_files(input_folder)
        
        if not pdf_files:
            logger.error(f"Nessun file PDF trovato in {input_folder}. Uscita.")
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
        os.makedirs(output_folder, exist_ok=True)
        
        # Configura e avvia l'executor parallelo
        executor = ParallelExecutor(
            num_workers=max_workers,
            cpu_monitor=cpu_monitor,
            progress_tracker=progress_tracker
        )
        
        # Configura i parametri di chunking dalla configurazione centralizzata
        chunking_config = pdf_config.get('chunk_size', {})
        Config.MIN_CHUNK_SIZE = chunking_config.get('min', Config.MIN_CHUNK_SIZE)
        Config.MAX_CHUNK_SIZE = chunking_config.get('max', Config.MAX_CHUNK_SIZE)
        Config.OVERLAP_SIZE = chunking_config.get('overlap', Config.OVERLAP_SIZE)
        Config.USE_SLIDING_WINDOW = pdf_config.get('processing', {}).get('use_sliding_window', Config.USE_SLIDING_WINDOW)
        
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