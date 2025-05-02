#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulo per l'elaborazione parallela dei PDF.
"""

import os
import time
import logging
import traceback
import multiprocessing
from multiprocessing import Pool
from typing import List, Dict, Tuple, Any
from concurrent.futures import ProcessPoolExecutor, as_completed

# Assicurati che questi import usino percorsi relativi se sono nello stesso pacchetto
from .processor import PDFProcessor
from .output_manager import OutputManager
from .progress_tracker import ProgressTracker
from .cpu_monitor import CPUMonitor
from .config import Config # Importa Config per usarla nella funzione worker se necessario

# Variabili globali per i worker
_cpu_monitor = None

def _process_single_pdf(data_with_config: Tuple[str, str, Dict[str, Any]]) -> bool:
    """
    Funzione worker per processare un singolo PDF.
    
    Args:
        data_with_config: Tupla contenente (pdf_path, relative_output_prefix, config_dict)
        
    Returns:
        True se l'elaborazione è andata a buon fine, False altrimenti
    """
    global _cpu_monitor
    
    pdf_path, relative_output_prefix, config_dict = data_with_config
    
    # Inizializza logger locale
    logger = logging.getLogger("PDFChunker.Worker")
    logger.info(f"Elaborazione PDF: {pdf_path} -> {relative_output_prefix}")
    
    try:
        # Crea una configurazione locale dal dizionario
        local_config = Config()
        for key, value in config_dict.items():
            setattr(local_config, key, value)
        
        # Output manager
        output_manager = OutputManager(local_config.OUTPUT_FOLDER)
        
        # Pulisci usando relative_output_prefix
        output_manager.cleanup_partial_output(relative_output_prefix)
        
        # Crea il processore
        processor = PDFProcessor(local_config)
        
        # Processa il PDF con controllo dell'utilizzo della CPU
        start_time = time.time()
        throttle_sleep = getattr(local_config, 'THROTTLE_SLEEP', 1.0)
        
        # Estrai il testo
        if _cpu_monitor and _cpu_monitor.is_throttling_active():
            logger.info("Throttling attivo, attendere...")
            _cpu_monitor.check_and_throttle(throttle_sleep)
            
        raw_text = processor.extract_text_from_pdf(pdf_path)
        
        if _cpu_monitor and _cpu_monitor.is_throttling_active():
            logger.info("Throttling attivo, attendere...")
            _cpu_monitor.check_and_throttle(throttle_sleep)
            
        clean_text = processor.clean_text(raw_text)
        
        # Modalità semplice estrazione: salva direttamente il testo pulito
        if local_config.SIMPLE_EXTRACT:
            # Crea il percorso di output per il file .txt
            output_path = os.path.join(local_config.OUTPUT_FOLDER, f"{relative_output_prefix}.txt")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Salva il testo pulito
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(clean_text)
            
            logger.info(f"Testo estratto salvato in: {output_path}")
        else:
            # Modalità chunking: crea e salva i chunk
            if _cpu_monitor and _cpu_monitor.is_throttling_active():
                logger.info("Throttling attivo, attendere...")
                _cpu_monitor.check_and_throttle(throttle_sleep)
                
            chunks = processor.process_text_to_chunks(clean_text)
            
            if _cpu_monitor and _cpu_monitor.is_throttling_active():
                logger.info("Throttling attivo, attendere...")
                _cpu_monitor.check_and_throttle(throttle_sleep)
                
            output_manager.save_chunks(chunks, relative_output_prefix)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Completato PDF: {pdf_path} -> {relative_output_prefix} in {elapsed_time:.2f} secondi")
        
        return True
        
    except KeyboardInterrupt:
        logger.warning(f"Interruzione dell'utente durante l'elaborazione di {pdf_path}")
        return False
    except Exception as e:
        logger.error(f"Errore nell'elaborazione di {pdf_path} ({relative_output_prefix}): {str(e)}")
        logger.error(traceback.format_exc())
        return False

class ParallelExecutor:
    """
    Classe per l'esecuzione parallela dell'elaborazione di PDF.
    """
    
    def __init__(self, num_workers: int = 0, cpu_monitor: CPUMonitor = None, progress_tracker: ProgressTracker = None):
        """
        Inizializza l'executor parallelo.
        
        Args:
            num_workers: Numero di worker (0 = auto)
            cpu_monitor: Istanza del monitor CPU
            progress_tracker: Istanza del tracker di progresso
        """
        # Determina il numero di worker
        self.num_workers = num_workers if num_workers > 0 else max(1, multiprocessing.cpu_count() - 1)
        self.cpu_monitor = cpu_monitor
        self.progress_tracker = progress_tracker
        self.logger = logging.getLogger("PDFChunker.Parallel")
    
    def process_pdfs(self, pdf_files: List[str], config) -> bool:
        """
        Processa una lista di PDF in parallelo.
        
        Args:
            pdf_files: Lista di percorsi ai PDF
            config: Configurazione (oggetto Config)
            
        Returns:
            True se l'elaborazione è andata a buon fine, False altrimenti
        """
        global _cpu_monitor
        
        # Imposta la variabile globale per il monitor CPU
        _cpu_monitor = self.cpu_monitor
        
        # Converti config in dizionario per poterlo passare ai worker
        # Assicurati che INPUT_FOLDER sia incluso se non è già una property statica
        config_dict = {key: getattr(config, key) for key in dir(config) 
                      if not key.startswith('__') and not callable(getattr(config, key))}
        config_dict['INPUT_FOLDER'] = config.INPUT_FOLDER # Assicurati che ci sia
        
        self.logger.info(f"Avvio elaborazione parallela con {self.num_workers} worker")
        
        # Prepara i dati per i worker
        pdf_data_list = []
        input_folder_abs = os.path.abspath(config.INPUT_FOLDER) # Usa percorso assoluto per relpath
        
        for pdf_path in pdf_files:
            try:
                pdf_path_abs = os.path.abspath(pdf_path)
                # Modifica: Calcola il percorso relativo rispetto alla cartella di input
                relative_path = os.path.relpath(pdf_path_abs, input_folder_abs)
                # Modifica: Ottieni il prefisso relativo senza estensione
                relative_output_prefix = os.path.splitext(relative_path)[0]
                
                # Modifica: Passa relative_output_prefix invece di pdf_name
                pdf_data_list.append((pdf_path_abs, relative_output_prefix, config_dict))
            except ValueError as e:
                self.logger.error(f"Impossibile calcolare il percorso relativo per {pdf_path} rispetto a {input_folder_abs}: {e}")
                # Potrebbe accadere se i percorsi sono su unità diverse in Windows
                # In questo caso, usiamo un fallback (es. il nome base) ma la struttura non sarà preservata
                pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
                pdf_data_list.append((os.path.abspath(pdf_path), pdf_name, config_dict))
        
        try:
            # Processa i PDF in parallelo
            # Usa initializer per passare le variabili globali se necessario
            with Pool(processes=self.num_workers) as pool:
                results = pool.map_async(_process_single_pdf, pdf_data_list)
                pool.close()
                
                # Attendi il completamento e aggiorna il progresso
                results_list = results.get() # Attende qui
                
                # Aggiorna il progresso
                if self.progress_tracker:
                    processed_count = 0
                    for i, success in enumerate(results_list):
                        if success:
                            # Usa il percorso originale passato per marcare come processato
                            original_pdf_path = pdf_data_list[i][0] 
                            self.progress_tracker.mark_as_processed(original_pdf_path)
                            processed_count += 1
                    self.logger.info(f"Progresso aggiornato per {processed_count}/{len(pdf_files)} file.")

                pool.join() # Assicura che tutti i processi siano terminati
            
            self.logger.info("Elaborazione parallela completata")
            # Controlla se tutti i task hanno avuto successo
            return all(results_list)
            
        except KeyboardInterrupt:
            self.logger.warning("Interruzione dell'utente. Terminazione dei processi...")
            # Qui potresti voler terminare il pool esplicitamente se necessario
            return False
        except Exception as e:
            self.logger.error(f"Errore durante l'elaborazione parallela: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False

    def simple_extract_pdfs(self, pdf_files: List[str], config) -> None:
        """
        Esegue l'estrazione semplice del testo da PDF in parallelo.
        
        Args:
            pdf_files: Lista di percorsi ai file PDF
            config: Configurazione
        """
        self.logger.info(f"Avvio estrazione semplice da {len(pdf_files)} PDF con {self.num_workers} worker")
        
        # Converti config in dizionario per poterlo passare ai worker
        config_dict = {key: getattr(config, key) for key in dir(config) 
                      if not key.startswith('__') and not callable(getattr(config, key))}
        config_dict['INPUT_FOLDER'] = config.INPUT_FOLDER
        
        # Prepara i dati per i worker
        pdf_data_list = []
        input_folder_abs = os.path.abspath(config.INPUT_FOLDER)
        
        for pdf_path in pdf_files:
            try:
                pdf_path_abs = os.path.abspath(pdf_path)
                relative_path = os.path.relpath(pdf_path_abs, input_folder_abs)
                relative_output_prefix = os.path.splitext(relative_path)[0]
                pdf_data_list.append((pdf_path_abs, relative_output_prefix, config_dict))
            except ValueError as e:
                self.logger.error(f"Impossibile calcolare il percorso relativo per {pdf_path}: {e}")
                pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
                pdf_data_list.append((os.path.abspath(pdf_path), pdf_name, config_dict))
        
        with Pool(processes=self.num_workers) as pool:
            results = pool.map_async(_process_single_pdf, pdf_data_list)
            pool.close()
            
            # Attendi il completamento e aggiorna il progresso
            results_list = results.get()
            
            # Aggiorna il progresso
            if self.progress_tracker:
                processed_count = 0
                for i, success in enumerate(results_list):
                    if success:
                        original_pdf_path = pdf_data_list[i][0]
                        self.progress_tracker.mark_as_processed(original_pdf_path)
                        processed_count += 1
                self.logger.info(f"Progresso aggiornato per {processed_count}/{len(pdf_files)} file.")
            
            pool.join()
            
            self.logger.info("Estrazione semplice completata")