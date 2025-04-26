#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per pulire in batch i chunk JSON contenuti in una cartella.
Progettato specificamente per il formato dei chunk giuridici.
"""

import os
import sys
import json
import argparse
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm

# Importa il cleaner dal modulo pdf_chunker
try:
    from pdf_chunker.cleaner import TextCleaner
except ImportError:
    print("Errore: impossibile importare pdf_chunker.cleaner")
    print("Assicurati che il modulo pdf_chunker sia installato o nel PYTHONPATH")
    sys.exit(1)

def setup_logging(verbose=False):
    """Configura il sistema di logging"""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("batch_cleaner.log"),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger("BatchCleaner")

def clean_json_file(file_path, output_dir, cleaner, dry_run=False):
    """
    Pulisce un singolo file JSON contenente un chunk.
    
    Args:
        file_path: Percorso del file JSON da pulire
        output_dir: Directory dove salvare il file pulito
        cleaner: Istanza di TextCleaner
        dry_run: Se True, non scrive i file ma solo analizza
        
    Returns:
        Tuple (successo, statistiche)
    """
    try:
        # Leggi il file JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            chunk = json.load(f)
        
        # Verifica che sia un chunk valido
        if not isinstance(chunk, dict) or 'text' not in chunk:
            return (False, {
                'file': file_path,
                'error': 'Formato non valido'
            })
        
        # Backup dei valori originali per le statistiche
        original_text = chunk['text']
        original_tokens = chunk.get('tokens', 0)
        original_chars = chunk.get('chars', 0)
        
        # Applica la pulizia
        cleaned_chunk = cleaner.clean_chunk(chunk)
        
        # Calcola le statistiche
        stats = {
            'file': os.path.basename(file_path),
            'original_chars': original_chars,
            'cleaned_chars': cleaned_chunk.get('chars', 0),
            'original_tokens': original_tokens,
            'cleaned_tokens': cleaned_chunk.get('tokens', 0),
            'document': chunk.get('document', ''),
            'chunk_id': chunk.get('chunk_id', '')
        }
        
        # In modalità dry_run, restituisci solo le statistiche senza scrivere
        if dry_run:
            return (True, stats)
        
        # Crea il percorso di output mantenendo il nome del file originale
        output_path = os.path.join(output_dir, os.path.basename(file_path))
        
        # Scrivi il file pulito
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(cleaned_chunk, f, ensure_ascii=False, indent=2)
        
        return (True, stats)
    
    except Exception as e:
        return (False, {
            'file': file_path,
            'error': str(e)
        })

def clean_text_file(file_path, output_dir, cleaner, dry_run=False):
    """
    Pulisce un singolo file di testo.
    
    Args:
        file_path: Percorso del file di testo da pulire
        output_dir: Directory dove salvare il file pulito
        cleaner: Istanza di TextCleaner
        dry_run: Se True, non scrive i file ma solo analizza
        
    Returns:
        Tuple (successo, statistiche)
    """
    try:
        # Leggi il file di testo
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Backup dei valori originali per le statistiche
        original_text = text
        original_chars = len(text)
        original_tokens = len(text.split())
        
        # Applica la pulizia
        cleaned_text = cleaner.clean_text(text)
        
        # Calcola le statistiche
        stats = {
            'file': os.path.basename(file_path),
            'original_chars': original_chars,
            'cleaned_chars': len(cleaned_text),
            'original_tokens': original_tokens,
            'cleaned_tokens': len(cleaned_text.split())
        }
        
        # In modalità dry_run, restituisci solo le statistiche senza scrivere
        if dry_run:
            return (True, stats)
        
        # Crea il percorso di output mantenendo il nome del file originale
        output_path = os.path.join(output_dir, os.path.basename(file_path))
        
        # Scrivi il file pulito
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_text)
        
        return (True, stats)
    
    except Exception as e:
        return (False, {
            'file': file_path,
            'error': str(e)
        })#!/usr/bin/env python3

def process_directory(input_dir, output_dir, num_workers=0, dry_run=False, verbose=False):
    """
    Processa tutti i file JSON in una directory.
    
    Args:
        input_dir: Directory contenente i file JSON
        output_dir: Directory dove salvare i file puliti
        num_workers: Numero di worker per il processamento parallelo
        dry_run: Se True, non scrive i file ma solo analizza
        verbose: Se True, mostra output dettagliato
        
    Returns:
        Dizionario con le statistiche dell'elaborazione
    """
    logger = logging.getLogger("BatchCleaner")
    
    # Verifica che la directory di input esista
    if not os.path.exists(input_dir):
        logger.error(f"La directory {input_dir} non esiste")
        return None
    
    # Crea la directory di output se non in modalità dry_run
    if not dry_run:
        os.makedirs(output_dir, exist_ok=True)
    
    # Trova tutti i file JSON nella directory
    json_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) 
                 if f.endswith('.json') and os.path.isfile(os.path.join(input_dir, f))]
    
    if not json_files:
        logger.warning(f"Nessun file JSON trovato in {input_dir}")
        return None
    
    # Crea un'istanza del cleaner
    cleaner = TextCleaner()
    
    # Determina il numero di worker
    if num_workers <= 0:
        # Usa tutti i core disponibili tranne uno
        num_workers = max(1, multiprocessing.cpu_count() - 1)
    
    logger.info(f"Elaborazione di {len(json_files)} file JSON in {input_dir}")
    logger.info(f"Utilizzo di {num_workers} worker paralleli")
    
    if dry_run:
        logger.info("Modalità DRY RUN: i file non verranno scritti")
    
    # Statistiche
    stats = {
        'total_files': len(json_files),
        'success': 0,
        'errors': 0,
        'total_original_chars': 0,
        'total_cleaned_chars': 0,
        'file_stats': []
    }
    
    # Elabora i file in parallelo
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        # Crea i task per ogni file
        futures = [executor.submit(clean_json_file, file_path, output_dir, cleaner, dry_run) 
                 for file_path in json_files]
        
        # Processa i risultati man mano che sono disponibili
        for future in tqdm(as_completed(futures), total=len(futures), desc="Pulizia chunk"):
            success, result = future.result()
            
            if success:
                stats['success'] += 1
                stats['total_original_chars'] += result['original_chars']
                stats['total_cleaned_chars'] += result['cleaned_chars']
                stats['file_stats'].append(result)
                
                if verbose:
                    logger.debug(f"File {result['file']} elaborato: "
                                f"{result['original_chars']} → {result['cleaned_chars']} caratteri")
            else:
                stats['errors'] += 1
                logger.error(f"Errore nell'elaborazione di {result['file']}: {result['error']}")
    
    # Calcola la percentuale di riduzione
    if stats['total_original_chars'] > 0:
        stats['reduction_percent'] = ((stats['total_original_chars'] - stats['total_cleaned_chars']) / 
                                   stats['total_original_chars'] * 100)
    else:
        stats['reduction_percent'] = 0
    
    # Crea un report sintetico
    logger.info(f"Elaborazione completata: {stats['success']}/{stats['total_files']} file elaborati con successo")
    logger.info(f"Caratteri totali originali: {stats['total_original_chars']}")
    logger.info(f"Caratteri totali dopo pulizia: {stats['total_cleaned_chars']}")
    logger.info(f"Riduzione: {stats['reduction_percent']:.2f}%")
    
    # Scrivi le statistiche in un file JSON
    stats_file = os.path.join(output_dir if not dry_run else '.', "cleaning_stats.json")
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Statistiche dettagliate salvate in {stats_file}")
    
    return stats

def main():
    """Funzione principale dello script"""
    parser = argparse.ArgumentParser(description='Script per la pulizia in batch di chunk JSON')
    
    parser.add_argument('--input', '-i', required=True, 
                       help='Directory contenente i file JSON dei chunk')
    parser.add_argument('--output', '-o', 
                       help='Directory dove salvare i file puliti')
    parser.add_argument('--workers', '-w', type=int, default=0, 
                       help='Numero di worker per il processamento parallelo (0=auto)')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Mostra output dettagliato')
    parser.add_argument('--dry-run', '-d', action='store_true', 
                       help='Non scrive file, solo analisi')
    
    args = parser.parse_args()
    
    # Se non è specificata una directory di output in dry-run mode, usa quella corrente
    if args.dry_run and not args.output:
        args.output = '.'
    
    # In modalità normale, la directory di output è obbligatoria
    if not args.dry_run and not args.output:
        print("Errore: la directory di output è obbligatoria quando non in modalità dry-run")
        return 1
    
    # Configura il logging
    logger = setup_logging(args.verbose)
    
    # Processa la directory
    try:
        result = process_directory(
            args.input, 
            args.output, 
            num_workers=args.workers, 
            dry_run=args.dry_run,
            verbose=args.verbose
        )
        
        if result is None:
            return 1
        
        return 0
    
    except KeyboardInterrupt:
        logger.warning("Operazione interrotta dall'utente")
        return 1
    except Exception as e:
        logger.error(f"Errore durante l'elaborazione: {str(e)}")
        if args.verbose:
            logger.exception("Traceback completo:")
        return 1

if __name__ == "__main__":
    sys.exit(main())