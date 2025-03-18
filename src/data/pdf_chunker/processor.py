#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulo per l'elaborazione dei PDF e la creazione di chunk.
"""

import os
import re
import time
import logging
from typing import List, Dict, Optional

import pdfplumber

from pdf_chunker.custom_tokenizer import tokenize_sentences
from pdf_chunker.cleaner import TextCleaner

class PDFProcessor:
    """
    Classe per l'elaborazione dei documenti PDF e la creazione di chunk.
    """
    
    def __init__(self, config):
        """
        Inizializza il processore con i parametri dalla configurazione.
        
        Args:
            config: Oggetto di configurazione
        """
        self.min_chunk_size = config.MIN_CHUNK_SIZE
        self.max_chunk_size = config.MAX_CHUNK_SIZE
        self.overlap_size = config.OVERLAP_SIZE
        self.sliding_window = config.USE_SLIDING_WINDOW
        self.language = config.LANGUAGE
        self.max_pages_per_batch = config.MAX_PAGES_PER_BATCH
        self.timeout_per_page = config.TIMEOUT_PER_PAGE
        self.patterns = config.TEXT_PATTERNS
        self.apply_cleaning = getattr(config, 'APPLY_CLEANING', True)
        
        self.logger = logging.getLogger("PDFChunker.Processor")
        self.cleaner = TextCleaner() if self.apply_cleaning else None
    
    def tokenize_sentences(self, text: str) -> List[str]:
        """
        Tokenizza il testo in frasi utilizzando il tokenizer personalizzato.
        
        Args:
            text: Testo da tokenizzare
            
        Returns:
            Lista di frasi
        """
        if not text or text.isspace():
            self.logger.warning("Tentativo di tokenizzare testo vuoto")
            return []
        
        # Usa direttamente il nostro tokenizer personalizzato
        try:
            return tokenize_sentences(text, self.max_chunk_size)
        except Exception as e:
            self.logger.error(f"Errore nella tokenizzazione: {str(e)}")
            return []
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Estrae il testo da un file PDF.
        
        Args:
            pdf_path: Percorso del file PDF
            
        Returns:
            Testo estratto dal PDF
        """
        self.logger.info(f"Estrazione testo da {pdf_path}")
        all_text = ""
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
                self.logger.info(f"Il documento contiene {total_pages} pagine")
                
                # Elabora il PDF in batch per risparmiare memoria
                for batch_start in range(0, total_pages, self.max_pages_per_batch):
                    batch_end = min(batch_start + self.max_pages_per_batch, total_pages)
                    self.logger.info(f"Elaborazione batch di pagine {batch_start+1}-{batch_end} di {total_pages}")
                    
                    batch_text = ""
                    for i in range(batch_start, batch_end):
                        try:
                            # Imposta un timeout per l'estrazione del testo da una pagina
                            start_time = time.time()
                            page = pdf.pages[i]
                            
                            # Estrai il testo con timeout
                            page_text = ""
                            while time.time() - start_time < self.timeout_per_page:
                                try:
                                    page_text = page.extract_text() or ""
                                    break
                                except Exception as e:
                                    self.logger.warning(f"Errore nell'estrazione del testo dalla pagina {i+1}, riprovo... ({str(e)})")
                                    time.sleep(0.5)
                            
                            batch_text += page_text + "\n\n"
                            
                            if (i - batch_start + 1) % 10 == 0:
                                self.logger.info(f"Elaborazione: {i+1}/{total_pages} pagine ({((i+1)/total_pages)*100:.1f}%)")
                        
                        except Exception as page_error:
                            self.logger.error(f"Errore nell'elaborazione della pagina {i+1}: {str(page_error)}")
                            # Continua con la pagina successiva
                    
                    # Aggiungi il testo di questo batch al testo completo
                    all_text += batch_text
                    
                    # Libera memoria
                    del batch_text
                    
        except Exception as e:
            self.logger.error(f"Errore nell'estrazione del testo: {str(e)}")
            raise
            
        self.logger.info(f"Estratti {len(all_text)} caratteri")
        return all_text
    
    def clean_text(self, text: str) -> str:
        """
        Pulisce il testo rimuovendo elementi indesiderati.
        
        Args:
            text: Testo da pulire
            
        Returns:
            Testo pulito
        """
        self.logger.info("Pulizia del testo")
        
        # Verifica che il testo non sia vuoto
        if not text:
            self.logger.warning("Il testo da pulire è vuoto")
            return ""
        
        try:
            # Rimuove intestazioni e piè di pagina
            text = re.sub(self.patterns['header_footer'], '', text)
            
            # Rimuove numeri di pagina isolati
            text = re.sub(self.patterns['page_numbers'], '', text)
            
            # Normalizza spazi multipli
            text = re.sub(self.patterns['multiple_spaces'], ' ', text)
            
            # Normalizza newline multipli
            text = re.sub(self.patterns['multiple_newlines'], '\n\n', text)
            
            # Rimuove caratteri non stampabili
            text = ''.join(c for c in text if c.isprintable() or c in ['\n', '\t'])
            
            # Rimuove linee vuote o contenenti solo spazi
            lines = [line.strip() for line in text.split('\n')]
            text = '\n'.join(line for line in lines if line)
            
            # Verifica che il testo non sia diventato vuoto dopo la pulizia
            if not text.strip():
                self.logger.warning("Il testo è diventato vuoto dopo la pulizia")
                return ""
                
            self.logger.info(f"Dopo la pulizia: {len(text)} caratteri")
            return text
            
        except Exception as e:
            self.logger.error(f"Errore durante la pulizia del testo: {str(e)}")
            # In caso di errore, restituisci il testo originale
            return text
    
    def split_into_paragraphs(self, text: str) -> List[str]:
        """
        Divide il testo in paragrafi.
        
        Args:
            text: Testo da dividere
            
        Returns:
            Lista di paragrafi
        """
        # Divide sulla base di righe vuote (due o più newline consecutivi)
        paragraphs = re.split(r'\n\s*\n', text)
        # Rimuove eventuali paragrafi vuoti
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        self.logger.info(f"Testo diviso in {len(paragraphs)} paragrafi")
        return paragraphs
    
    def create_semantic_chunks(self, paragraphs: List[str]) -> List[str]:
        """
        Crea chunk semanticamente significativi dai paragrafi.
        
        Args:
            paragraphs: Lista di paragrafi
            
        Returns:
            Lista di chunk di testo
        """
        self.logger.info("Creazione di chunk semantici")
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para_size = len(para)
            
            # Se il paragrafo da solo è troppo grande
            if para_size > self.max_chunk_size:
                # Finalizza il chunk corrente se non è vuoto
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # Dividi il paragrafo grande in frasi
                sentences = self.tokenize_sentences(para)
                sentence_chunk = []
                sentence_size = 0
                
                for sentence in sentences:
                    sent_len = len(sentence)
                    
                    # Se la singola frase è ancora troppo grande
                    if sent_len > self.max_chunk_size:
                        # Finalizza il chunk di frasi corrente
                        if sentence_chunk:
                            chunks.append(' '.join(sentence_chunk))
                            sentence_chunk = []
                            sentence_size = 0
                        
                        # Dividi in parti più piccole (circa max_chunk_size caratteri)
                        parts = []
                        for i in range(0, len(sentence), self.max_chunk_size - 50):
                            part = sentence[i:i + self.max_chunk_size - 50]
                            if part:
                                parts.append(part)
                        
                        for part in parts:
                            chunks.append(part)
                    
                    # Se aggiungere questa frase supera il limite
                    elif sentence_size + sent_len > self.max_chunk_size:
                        chunks.append(' '.join(sentence_chunk))
                        sentence_chunk = [sentence]
                        sentence_size = sent_len
                    else:
                        sentence_chunk.append(sentence)
                        sentence_size += sent_len
                
                # Aggiungi l'ultimo chunk di frasi
                if sentence_chunk:
                    chunks.append(' '.join(sentence_chunk))
            
            # Se aggiungere questo paragrafo supera il limite
            elif current_size + para_size > self.max_chunk_size:
                # Finalizza il chunk corrente
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                
                # Inizia un nuovo chunk con questo paragrafo
                current_chunk = [para]
                current_size = para_size
            else:
                # Aggiungi il paragrafo al chunk corrente
                current_chunk.append(para)
                current_size += para_size
        
        # Aggiungi l'ultimo chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        self.logger.info(f"Creati {len(chunks)} chunk semantici")
        return chunks
    
    def create_sliding_window_chunks(self, text: str) -> List[str]:
        """
        Crea chunk usando una finestra scorrevole con sovrapposizione.
        
        Args:
            text: Testo da dividere in chunk
            
        Returns:
            Lista di chunk di testo
        """
        self.logger.info("Creazione di chunk con finestra scorrevole")
        chunks = []
        
        # Se il testo è vuoto, ritorna una lista vuota
        if not text or text.isspace():
            self.logger.warning("Il testo è vuoto o contiene solo spazi")
            return []
            
        # Prova a dividere in frasi, se fallisce, usa un metodo alternativo
        sentences = self.tokenize_sentences(text)
        
        # Se non ci sono frasi, prova un approccio più semplice basato sui caratteri
        if not sentences:
            self.logger.warning("Nessuna frase trovata nel testo, utilizzo divisione a blocchi")
            # Dividi il testo in blocchi di caratteri di dimensione fissa con sovrapposizione
            chunks = []
            for i in range(0, len(text), self.max_chunk_size - self.overlap_size):
                end = min(i + self.max_chunk_size, len(text))
                chunk = text[i:end]
                if len(chunk) >= self.min_chunk_size or end == len(text):
                    chunks.append(chunk)
            self.logger.info(f"Creati {len(chunks)} chunk con divisione a blocchi")
            return chunks
        
        # Verifica che ci sia almeno una frase con contenuto
        non_empty_sentences = [s for s in sentences if s.strip()]
        if not non_empty_sentences:
            self.logger.warning("Tutte le frasi sono vuote, utilizzo divisione a blocchi")
            # Usa lo stesso metodo di divisione a blocchi definito sopra
            chunks = []
            for i in range(0, len(text), self.max_chunk_size - self.overlap_size):
                end = min(i + self.max_chunk_size, len(text))
                chunk = text[i:end]
                if len(chunk) >= self.min_chunk_size or end == len(text):
                    chunks.append(chunk)
            self.logger.info(f"Creati {len(chunks)} chunk con divisione a blocchi")
            return chunks
            
        # Calcola quante frasi approssimativamente dovrebbero stare in un chunk
        total_chars = sum(len(s) for s in non_empty_sentences)
        
        # Previeni la divisione per zero
        if total_chars == 0 or len(non_empty_sentences) == 0:
            self.logger.warning("Lunghezza media delle frasi è zero, utilizzo valori predefiniti")
            avg_sent_len = 100  # Valore predefinito
        else:
            avg_sent_len = total_chars / len(non_empty_sentences)
            
        target_sents = max(1, int(self.max_chunk_size / avg_sent_len))
        overlap_sents = max(1, int(self.overlap_size / avg_sent_len))
        
        self.logger.info(f"Media di caratteri per frase: {avg_sent_len:.2f}")
        self.logger.info(f"Target di frasi per chunk: {target_sents}")
        self.logger.info(f"Frasi di sovrapposizione: {overlap_sents}")
        
        # Crea chunk con la finestra scorrevole
        i = 0
        while i < len(sentences):
            end_idx = min(i + target_sents, len(sentences))
            chunk_sentences = sentences[i:end_idx]
            chunk_text = ' '.join(chunk_sentences)
            
            # Controlla se il chunk è abbastanza grande
            if len(chunk_text) >= self.min_chunk_size or end_idx == len(sentences):
                chunks.append(chunk_text)
            
            # Avanza la finestra, considerando la sovrapposizione
            step = max(1, target_sents - overlap_sents)
            i += step
        
        self.logger.info(f"Creati {len(chunks)} chunk con finestra scorrevole")
        return chunks
    
    def process_text_to_chunks(self, text: str) -> List[Dict]:
        """
        Processa il testo pulito e lo divide in chunk.
        
        Args:
            text: Testo pulito da processare
            
        Returns:
            Lista di dizionari rappresentanti i chunk con metadati
        """
        all_chunks = []
        
        if self.sliding_window:
            # Metodo con finestra scorrevole
            text_chunks = self.create_sliding_window_chunks(text)
        else:
            # Metodo basato sui paragrafi
            paragraphs = self.split_into_paragraphs(text)
            text_chunks = self.create_semantic_chunks(paragraphs)
        
        # Crea dizionari per ogni chunk
        for i, chunk_text in enumerate(text_chunks):
            # Applica pulizia avanzata se abilitata
            if self.cleaner and chunk_text:
                chunk_text = self.cleaner.clean_text(chunk_text)
            
            # Trova le prime parole per un identificativo più significativo
            first_words = ' '.join(chunk_text.split()[:5]).replace(' ', '_')
            first_words = re.sub(r'[^\w]', '', first_words)
            
            chunk_dict = {
                "chunk_id": f"chunk_{i:04d}_{first_words[:30]}",
                "text": chunk_text,
                "tokens": len(chunk_text.split()),
                "chars": len(chunk_text),
                "index": i
            }
            all_chunks.append(chunk_dict)
        
        return all_chunks
    
    def process_pdf(self, pdf_path: str) -> List[Dict]:
        """
        Processa completamente un PDF e restituisce i chunk.
        
        Args:
            pdf_path: Percorso del file PDF
            
        Returns:
            Lista di dizionari rappresentanti i chunk con metadati
        """
        # Estrai il testo dal PDF
        raw_text = self.extract_text_from_pdf(pdf_path)
        
        # Pulisci il testo
        clean_text = self.clean_text(raw_text)
        
        # Processa il testo in chunk
        chunks = self.process_text_to_chunks(clean_text)
        
        return chunks