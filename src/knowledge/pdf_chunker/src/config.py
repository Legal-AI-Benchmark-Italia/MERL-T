#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configurazione per il PDF Chunker.
"""

import logging
import os
from pathlib import Path

# Determine PROJECT_ROOT based on the script's location
# Assuming this script is in src/knowledge/pdf_chunker/, the root is 3 levels up
try:
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
except IndexError:
    # Fallback if the structure is different (e.g., running from root)
    PROJECT_ROOT = Path.cwd()
    # Add a warning or specific handling if needed
    print(f"Warning: Could not determine project root reliably from config.py location. Using current working directory: {PROJECT_ROOT}")

class Config:
    """
    Classe di configurazione per l'applicazione PDF Chunker.
    Contiene tutte le impostazioni configurabili.
    """
    def __init__(self):
        """
        Inizializza un'istanza di Config con i valori predefiniti.
        Questo permette di creare istanze separate per ogni worker.
        """
        pass
    
    # Cartelle di input e output (ora dinamiche)
    INPUT_FOLDER = PROJECT_ROOT  / "knowledge" / "knowledge_base" / "dottrina" / "raw_sources"
    OUTPUT_FOLDER = PROJECT_ROOT  / "knowledge" / "knowledge_base" /  "dottrina" / "raw_text"
    
    # Parametri di chunking
    MIN_CHUNK_SIZE = 3000       # Dimensione minima in caratteri per un chunk
    MAX_CHUNK_SIZE = 5000      # Dimensione massima in caratteri per un chunk
    OVERLAP_SIZE = 500         # Numero di caratteri di sovrapposizione tra i chunk
    USE_SLIDING_WINDOW = False  # True: usa finestra scorrevole, False: divisione per paragrafi
    
    # Lingua per la tokenizzazione
    LANGUAGE = "italian"       # Lingua per la tokenizzazione delle frasi (es. "italian", "english")
    
    # Parametri di processo
    MAX_PAGES_PER_BATCH = 50  # Numero massimo di pagine da elaborare per batch per risparmiare memoria
    TIMEOUT_PER_PAGE = 3       # Timeout in secondi per l'estrazione di una singola pagina
    
    # Parametri di parallelizzazione
    MAX_WORKERS = 5            # Numero di processi paralleli (0=automatico basato sul numero di CPU)
    CPU_LIMIT = 80             # Limite di utilizzo CPU in percentuale
    CPU_CHECK_INTERVAL = 2     # Intervallo in secondi per controllare l'utilizzo della CPU
    THROTTLE_SLEEP = 15         # Tempo di attesa in secondi quando la CPU è troppo utilizzata
    
    # File per tracciare i progressi (relativo alla root)
    PROGRESS_FILE = PROJECT_ROOT / "knowledge" / "knowledge_base" / "dottrina"  / "pdf_chunker_progress.json"
    
    # Configurazione logging
    LOG_LEVEL = logging.DEBUG
    LOG_FORMAT = '%(asctime)s - %(processName)s - %(name)s - %(levelname)s - %(message)s'
    
    # Pattern regex comuni per la pulizia del testo giuridico
    TEXT_PATTERNS = {
        'header_footer': r'(?:\d+/\d+)|(?:pag\.\s*\d+)|(?:Pag\.\s*\d+)',
        'page_numbers': r'^\s*\d+\s*$',
        'multiple_spaces': r'\s{2,}',
        'multiple_newlines': r'\n{3,}',
        'footnotes': r'\[\d+\]|\(\d+\)',
        'references': r'(?:Art\.|Artt\.) \d+(?:[-,]\d+)*',
    }
    
    # Applica pulizia avanzata
    APPLY_CLEANING = True  # Abilita/disabilita la pulizia avanzata dei chunk

# Assicurati che le directory di output esistano
try:
    Config.OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
except Exception as e:
    print(f"Warning: Could not create output directory {Config.OUTPUT_FOLDER}: {e}")

# Esempio di utilizzo:
# config_instance = Config()
# print(config_instance.INPUT_FOLDER)
