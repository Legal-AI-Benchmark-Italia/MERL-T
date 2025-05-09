#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility e funzioni helper per PDF Chunker.
"""

import os
import re
import glob
import logging
from datetime import datetime
from typing import List

def setup_logging():
    """
    Configura il logging per l'applicazione.
    
    Returns:
        Logger configurato
    """
    from .config import Config
    
    # Nome del file di log
    log_filename = f"pdf_chunker_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Configurazione logging
    logging.basicConfig(
        level=Config.LOG_LEVEL,
        format=Config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger("PDFChunker")
    logger.info(f"Logging inizializzato. File di log: {log_filename}")
    
    return logger

def find_pdf_files(input_folder: str) -> List[str]:
    """
    Trova tutti i file PDF in una cartella.
    
    Args:
        input_folder: Cartella da scansionare
        
    Returns:
        Lista di percorsi di file PDF
    """
    logger = logging.getLogger("PDFChunker")
    
    # Assicura che la cartella esista
    if not os.path.exists(input_folder):
        logger.error(f"La cartella di input '{input_folder}' non esiste")
        return []
    
    # Trova tutti i file PDF nella cartella
    pdf_pattern = os.path.join(input_folder, "*.pdf")
    pdf_files = glob.glob(pdf_pattern)
    
    # Controlla anche nelle sottocartelle
    subdir_pattern = os.path.join(input_folder, "**/*.pdf")
    pdf_files.extend(glob.glob(subdir_pattern, recursive=True))
    
    # Rimuovi duplicati e ordina
    pdf_files = sorted(set(pdf_files))
    
    logger.info(f"Trovati {len(pdf_files)} file PDF in '{input_folder}'")
    
    return pdf_files

def initialize_nltk():
    """
    Funzione vuota per compatibilità, non utilizziamo più NLTK.
    
    Returns:
        True sempre
    """
    logger = logging.getLogger("PDFChunker")
    logger.info("NLTK non è più necessario, utilizzo tokenizer personalizzato")
    return True

def fallback_sent_tokenize(text, max_chunk_size=1000):
    """
    Tokenizer di fallback nel caso in cui NLTK fallisca.
    Divide il testo in frasi basandosi su pattern comuni come punti seguiti da spazi e maiuscole.
    
    Args:
        text: testo da tokenizzare
        max_chunk_size: dimensione massima del chunk per la suddivisione
        
    Returns:
        lista di frasi
    """
    logger = logging.getLogger("PDFChunker")
    
    # Controllo di base
    if not text or text.isspace():
        return []
    
    try:
        # Metodo 1: Dividi per punti seguiti da spazio e maiuscola
        pattern = r'(?<=[.!?])\s+(?=[A-Z0-9])'
        sentences = re.split(pattern, text)
        
        # Se abbiamo troppe poche frasi, prova un approccio più semplice
        if len(sentences) <= 3 and len(text) > 1000:
            # Metodo 2: Dividi semplicemente per punti
            raw_sentences = text.replace("\n", " ").split(".")
            sentences = [s.strip() + "." for s in raw_sentences if s.strip()]
        
        # Ulteriore suddivisione per frasi molto lunghe
        result = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            if len(sentence) > max_chunk_size / 2:
                # Se la frase è troppo lunga, prova a suddividere su punti e virgola o due punti
                sub_sentences = re.split(r'(?<=[:;])\s+', sentence)
                # Aggiungi solo frasi non vuote
                sub_sentences = [s.strip() for s in sub_sentences if s.strip()]
                
                # Se le sottofrasi sono ancora troppo lunghe, dividi per virgole
                if any(len(s) > max_chunk_size / 2 for s in sub_sentences):
                    all_sub_sentences = []
                    for s in sub_sentences:
                        if len(s) > max_chunk_size / 2:
                            comma_splits = re.split(r'(?<=,)\s+', s)
                            all_sub_sentences.extend([cs.strip() for cs in comma_splits if cs.strip()])
                        else:
                            all_sub_sentences.append(s)
                    result.extend(all_sub_sentences)
                else:
                    result.extend(sub_sentences)
            else:
                result.append(sentence)
        
        # Se ancora non abbiamo frasi, suddividi per paragrafi
        if not result and len(text) > 100:
            result = [p.strip() for p in text.split("\n\n") if p.strip()]
            
        # Se ancora non abbiamo frasi, suddividi per righe
        if not result and len(text) > 50:
            result = [p.strip() for p in text.split("\n") if p.strip()]
            
        # Come ultima risorsa, dividi in blocchi di testo di lunghezza fissa
        if not result and text.strip():
            logger.warning("Metodi standard di tokenizzazione falliti, divisione in blocchi fissi")
            result = []
            current_text = text.strip()
            block_size = int(max_chunk_size / 2)
            while current_text:
                if len(current_text) <= block_size:
                    result.append(current_text)
                    break
                    
                # Cerca l'ultimo spazio entro block_size
                cut_point = block_size
                while cut_point > 0 and current_text[cut_point] != ' ':
                    cut_point -= 1
                    
                # Se non troviamo uno spazio, taglia semplicemente alla lunghezza block_size
                if cut_point == 0:
                    cut_point = min(block_size, len(current_text))
                
                result.append(current_text[:cut_point].strip())
                current_text = current_text[cut_point:].strip()
            
        # Se ancora non abbiamo nulla (improbabile ma possibile), ritorna il testo originale come unica frase
        if not result and text.strip():
            result = [text.strip()]
            
        return result
        
    except Exception as e:
        logger.error(f"Errore nel tokenizer fallback: {str(e)}")
        # In caso di errore, ritorna una lista contenente il testo originale
        if text.strip():
            # Divide il testo in blocchi di dimensione fissa come ultima risorsa
            result = []
            for i in range(0, len(text), max_chunk_size//2):
                result.append(text[i:i + max_chunk_size//2])
            return result if result else [text.strip()]
        return []