#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configurazione per il PDF Chunker.
"""

import logging
import os

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
    
    # Cartelle di input e output
    INPUT_FOLDER = "/Users/guglielmo/Desktop/CODE/MERL-T/src/data/dottrina/raw_sources/diritto_civile"  # Cartella contenente i PDF da processare
    OUTPUT_FOLDER = "/Users/guglielmo/Desktop/CODE/MERL-T/src/data/dottrina/raw_txt/diritto_civile"  # Cartella dove salvare i risultati
    
    # Parametri di chunking
    MIN_CHUNK_SIZE = 3000       # Dimensione minima in caratteri per un chunk
    MAX_CHUNK_SIZE = 5000      # Dimensione massima in caratteri per un chunk
    OVERLAP_SIZE = 1500         # Numero di caratteri di sovrapposizione tra i chunk
    USE_SLIDING_WINDOW = True  # True: usa finestra scorrevole, False: divisione per paragrafi
    
    # Lingua per la tokenizzazione
    LANGUAGE = "italian"       # Lingua per la tokenizzazione delle frasi (es. "italian", "english")
    
    # Parametri di processo
    MAX_PAGES_PER_BATCH = 100  # Numero massimo di pagine da elaborare per batch per risparmiare memoria
    TIMEOUT_PER_PAGE = 1       # Timeout in secondi per l'estrazione di una singola pagina
    
    # Parametri di parallelizzazione
    MAX_WORKERS = 0            # Numero di processi paralleli (0=automatico basato sul numero di CPU)
    CPU_LIMIT = 70             # Limite di utilizzo CPU in percentuale
    CPU_CHECK_INTERVAL = 2     # Intervallo in secondi per controllare l'utilizzo della CPU
    THROTTLE_SLEEP = 1         # Tempo di attesa in secondi quando la CPU è troppo utilizzata
    
    # File per tracciare i progressi
    PROGRESS_FILE = "pdf_chunker_progress.json"
    
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
    APPLY_CLEANING = True  # Abilita/disabilita la pulizia avanzata dei chunk#!/usr/bin/env python3
