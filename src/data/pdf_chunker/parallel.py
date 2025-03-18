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

from pdf_chunker.processor import PDFProcessor
from pdf_chunker.output_manager import OutputManager
from pdf_chunker.progress_tracker import ProgressTracker
from pdf_chunker.cpu_monitor import CPUMonitor

# Variabili globali per i worker
_cpu_monitor = None
_throttle_sleep = 1.0
_config = None

def _process_single_pdf(data_with_config: Tuple[str, str, Dict[str, Any]]) -> bool:
    """
    Funzione worker per processare un singolo PDF.
    
    Args:
        data_with_config: Tupla contenente (pdf_path, pdf_name, config_dict)
        
    Returns:
        True se l'elaborazione è andata a buon fine, False altrimenti
    """
    global _cpu_monitor, _throttle_sleep
    
    pdf_path, pdf_name, config_dict = data_with_config
    
    # Inizializza logger locale
    logger = logging.getLogger("PDFChunker.Worker")
    logger.info(f"Elaborazione PDF: {pdf_path}")
    
    try:
        # Crea una configurazione locale dal dizionario
        from pdf_chunker.config import Config
        local_config = Config()
        for key, value in config_dict.items():
            setattr(local_config, key, value)
        
        # Output manager
        output_manager = OutputManager(local_config.OUTPUT_FOLDER)
        
        # Pulisci eventuali elaborazioni parziali
        output_manager.cleanup_partial_output(pdf_name)
        
        # Crea il processore
        processor = PDFProcessor(local_config)
        
        # Processa il PDF con controllo dell'utilizzo della CPU
        start_time = time.time()
        
        # Estrai e pulisci il testo
        if _cpu_monitor and _cpu_monitor.is_throttling_active():
            logger.info("Throttling attivo, attendere...")
            _cpu_monitor.check_and_throttle(local_config.THROTTLE_SLEEP)
            
        raw_text = processor.extract_text_from_pdf(pdf_path)
        
        if _cpu_monitor and _cpu_monitor.is_throttling_active():
            logger.info("Throttling attivo, attendere...")
            _cpu_monitor.check_and_throttle(local_config.THROTTLE_SLEEP)
            
        clean_text = processor.clean_text(raw_text)
        
        # Crea i chunk
        if _cpu_monitor and _cpu_monitor.is_throttling_active():
            logger.info("Throttling attivo, attendere...")
            _cpu_monitor.check_and_throttle(local_config.THROTTLE_SLEEP)
            
        chunks = processor.process_text_to_chunks(clean_text)
        
        # Salva i chunks
        if _cpu_monitor and _cpu_monitor.is_throttling_active():
            logger.info("Throttling attivo, attendere...")
            _cpu_monitor.check_and_throttle(local_config.THROTTLE_SLEEP)
            
        output_manager.save_chunks(chunks, pdf_name)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Completato PDF: {pdf_path} in {elapsed_time:.2f} secondi")
        
        # Aggiorna il progresso (gestito dal chiamante)
        return True
        
    except KeyboardInterrupt:
        logger.warning(f"Interruzione dell'utente durante l'elaborazione di {pdf_path}")
        return False
    except Exception as e:
        logger.error(f"Errore nell'elaborazione di {pdf_path}: {str(e)}")
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
            config: Configurazione
            
        Returns:
            True se l'elaborazione è andata a buon fine, False altrimenti
        """
        global _cpu_monitor
        
        # Imposta la variabile globale per il monitor CPU
        _cpu_monitor = self.cpu_monitor
        
        # Converti config in dizionario per poterlo passare ai worker
        config_dict = {key: getattr(config, key) for key in dir(config) 
                      if not key.startswith('__') and not callable(getattr(config, key))}
        
        self.logger.info(f"Avvio elaborazione parallela con {self.num_workers} worker")
        
        # Prepara i dati per i worker
        pdf_data_list = []
        for pdf_path in pdf_files:
            pdf_name = os.path.splitext(os.path.basename(pdf_path))[0]
            # Passa anche la configurazione come parte dei dati
            pdf_data_list.append((pdf_path, pdf_name, config_dict))
        
        try:
            # Processa i PDF in parallelo
            with Pool(processes=self.num_workers) as pool:
                results = pool.map_async(_process_single_pdf, pdf_data_list)
                pool.close()
                
                # Attendi il completamento e aggiorna il progresso
                results_list = results.get()
                
                # Aggiorna il progresso
                if self.progress_tracker:
                    for i, success in enumerate(results_list):
                        if success:
                            pdf_path = pdf_data_list[i][0]
                            self.progress_tracker.mark_as_processed(pdf_path)
                
                pool.join()
            
            self.logger.info("Elaborazione parallela completata")
            return True
            
        except KeyboardInterrupt:
            self.logger.warning("Interruzione dell'utente. Terminazione dei processi...")
            return False
        except Exception as e:
            self.logger.error(f"Errore durante l'elaborazione parallela: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False