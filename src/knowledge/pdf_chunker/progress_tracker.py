#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulo per il tracciamento del progresso dell'elaborazione.
"""

import os
import json
import logging
from typing import List, Dict, Set
from multiprocessing import Lock

class ProgressTracker:
    """
    Classe per il tracciamento del progresso nell'elaborazione dei PDF.
    """
    
    def __init__(self, progress_file: str):
        """
        Inizializza il tracker di progresso.
        
        Args:
            progress_file: Percorso del file dove salvare lo stato di avanzamento
        """
        self.progress_file = progress_file
        self.lock = Lock()
        self.logger = logging.getLogger("PDFChunker.ProgressTracker")
    
    def get_processed_pdfs(self) -> Set[str]:
        """
        Ottiene l'insieme dei PDF già elaborati.
        
        Returns:
            Set di percorsi ai PDF già elaborati
        """
        progress = self._load_progress()
        return set(progress.get("processed_pdfs", []))
    
    def mark_as_processed(self, pdf_path: str) -> bool:
        """
        Marca un PDF come elaborato.
        
        Args:
            pdf_path: Percorso del PDF elaborato
            
        Returns:
            True se il salvataggio è andato a buon fine, False altrimenti
        """
        with self.lock:
            try:
                progress = self._load_progress()
                processed_pdfs = set(progress.get("processed_pdfs", []))
                processed_pdfs.add(pdf_path)
                progress["processed_pdfs"] = list(processed_pdfs)
                return self._save_progress(progress)
            except Exception as e:
                self.logger.error(f"Errore nel marcare {pdf_path} come elaborato: {str(e)}")
                return False
    
    def _load_progress(self) -> Dict:
        """
        Carica lo stato di avanzamento da file.
        
        Returns:
            Dizionario con i PDF già elaborati
        """
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Errore nel caricamento del file di progresso: {str(e)}")
        
        return {"processed_pdfs": []}
    
    def _save_progress(self, progress: Dict) -> bool:
        """
        Salva lo stato di avanzamento su file.
        
        Args:
            progress: Dizionario con i PDF già elaborati
            
        Returns:
            True se il salvataggio è andato a buon fine, False altrimenti
        """
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Errore nel salvataggio del file di progresso: {str(e)}")
            return False