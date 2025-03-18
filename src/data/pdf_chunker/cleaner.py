#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulo per la pulizia avanzata dei chunk di testo.
"""

import re
import logging
from typing import List, Dict, Union, Optional

class TextCleaner:
    """
    Classe per la pulizia dettagliata dei chunk di testo.
    Rimuove elementi indesiderati e normalizza il formato.
    """
    
    def __init__(self):
        """
        Inizializza il cleaner di testo.
        """
        self.logger = logging.getLogger("PDFChunker.Cleaner")
        
        # Pattern per la pulizia
        self.patterns = {
            # Rimuovi newline tra parole senza spazi prima e dopo (parola\nparola -> parola parola)
            'word_break_newline': r'(\w)\n(\w)',
            
            # Rimuovi newline dopo trattino senza spazio dopo (parola-\nparola -> parola-parola)
            'hyphen_break_newline': r'(\-)\n(\w)',
            
            # Righe che contengono solo spazi
            'empty_lines': r'\n\s*\n',
            
            # Spazi multipli
            'multiple_spaces': r'\s{2,}',
            
            # Newline multipli
            'multiple_newlines': r'\n{3,}'
        }
        
    def clean_text(self, text: str) -> str:
        """
        Pulisce il testo rimuovendo elementi indesiderati.
        
        Args:
            text: Testo da pulire
            
        Returns:
            Testo pulito
        """
        if not text:
            return ""
        
        try:
            # Salva la lunghezza originale per il log
            original_length = len(text)
            
            # Rimuovi newline tra parole (senza spazi prima e dopo)
            text = re.sub(self.patterns['word_break_newline'], r'\1 \2', text)
            
            # Rimuovi newline dopo trattino (senza spazio dopo)
            text = re.sub(self.patterns['hyphen_break_newline'], r'\1\2', text)
            
            # Normalizza righe vuote
            text = re.sub(self.patterns['empty_lines'], '\n\n', text)
            
            # Normalizza spazi multipli
            text = re.sub(self.patterns['multiple_spaces'], ' ', text)
            
            # Normalizza newline multipli
            text = re.sub(self.patterns['multiple_newlines'], '\n\n', text)
            
            # Rimuovi spazi all'inizio e alla fine del testo
            text = text.strip()
            
            # Log delle modifiche
            new_length = len(text)
            chars_removed = original_length - new_length
            if chars_removed > 0:
                self.logger.debug(f"Pulizia completata: rimossi {chars_removed} caratteri ({(chars_removed/original_length)*100:.1f}%)")
                
            return text
            
        except Exception as e:
            self.logger.error(f"Errore durante la pulizia del testo: {str(e)}")
            # In caso di errore, restituisci il testo originale
            return text
    
    def clean_chunk(self, chunk: Dict) -> Dict:
        """
        Pulisce un singolo chunk (dizionario).
        
        Args:
            chunk: Dizionario che rappresenta un chunk
            
        Returns:
            Chunk pulito
        """
        if not chunk or 'text' not in chunk:
            return chunk
        
        # Crea una copia del chunk per non modificare l'originale
        cleaned_chunk = chunk.copy()
        
        # Pulisci il testo
        cleaned_chunk['text'] = self.clean_text(chunk['text'])
        
        # Aggiorna il conteggio di token e caratteri
        cleaned_chunk['tokens'] = len(cleaned_chunk['text'].split())
        cleaned_chunk['chars'] = len(cleaned_chunk['text'])
        
        return cleaned_chunk
    
    def clean_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Pulisce una lista di chunk.
        
        Args:
            chunks: Lista di dizionari che rappresentano i chunk
            
        Returns:
            Lista di chunk puliti
        """
        self.logger.info(f"Pulizia di {len(chunks)} chunk")
        
        cleaned_chunks = []
        for chunk in chunks:
            cleaned_chunks.append(self.clean_chunk(chunk))
            
        self.logger.info(f"Pulizia completata per {len(cleaned_chunks)} chunk")
        return cleaned_chunks
    
    def post_process_text(self, text: str) -> str:
        """
        Esegue operazioni di post-processing sul testo.
        
        Args:
            text: Testo da processare
            
        Returns:
            Testo processato
        """
        if not text:
            return ""
            
        processed = text
        
        # Uniforma i segni di punteggiatura (es. spazi prima/dopo)
        processed = re.sub(r'\s+([,.;:!?])', r'\1', processed)  # Nessuno spazio prima
        processed = re.sub(r'([,.;:!?])([^\s\d])', r'\1 \2', processed)  # Spazio dopo
        
        # Normalizza trattini
        processed = re.sub(r'([^\s])\-([^\s])', r'\1-\2', processed)  # Nessuno spazio intorno
        
        # Normalizza virgolette
        processed = re.sub(r'"\s*([^"]*?)\s*"', r'"\1"', processed)
        processed = re.sub(r"'\s*([^']*?)\s*'", r"'\1'", processed)
        
        # Normalizza le parentesi
        processed = re.sub(r'\(\s+', r'(', processed)  # Nessuno spazio dopo parentesi aperta
        processed = re.sub(r'\s+\)', r')', processed)  # Nessuno spazio prima parentesi chiusa
        
        return processed
        
    def extract_and_merge_paragraphs(self, chunks: List[Dict]) -> List[Dict]:
        """
        Estrae paragrafi dai chunk e li ricombina in modo più coerente.
        Utile quando i chunk hanno diviso male i paragrafi.
        
        Args:
            chunks: Lista di dizionari che rappresentano i chunk
            
        Returns:
            Lista di chunk con paragrafi ricombinati
        """
        # TODO: Implementare questa funzionalità avanzata se necessario
        # Potrebbe essere utile per migliorare la coerenza semantica tra i chunk
        return chunks