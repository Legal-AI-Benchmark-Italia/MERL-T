#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tokenizer ibrido che combina word tokenization e sentence tokenization.

Questo modulo implementa un sistema di chunking che:
1. Divide il testo in frasi
2. Conta i token (parole) all'interno di ogni frase
3. Raggruppa le frasi in chunk basandosi sul numero massimo di token
4. Garantisce che i chunk terminino sempre a fine frase
"""

import re
import logging
from typing import List, Dict, Set, Tuple

class HybridTokenizer:
    """
    Tokenizer ibrido che crea chunk basati sul numero di parole,
    garantendo che i chunk terminino alla fine di una frase.
    """
    
    # Abbreviazioni comuni in italiano e nei testi giuridici
    COMMON_ABBREVIATIONS = {
        'art.', 'artt.', 'n.', 'nr.', 'pag.', 'p.', 'pp.', 'par.', 'lett.', 'cfr.',
        'fig.', 'es.', 'cap.', 'sez.', 'sig.', 'sigg.', 'dott.', 'prof.', 'avv.',
        'ing.', 'geom.', 'rag.', 'on.', 'sen.', 'dir.', 'amm.', 'v.', 'vs.', 'etc.',
        'i.e.', 'e.g.', 'ca.', 'prot.', 'd.lgs.', 'r.d.', 'c.c.', 'c.p.', 'c.p.c.',
        'c.p.p.', 't.u.', 'g.u.', 'd.p.r.', 'd.m.', 'l.', 'cost.'
    }
    
    def __init__(self, 
                 max_tokens_per_chunk: int = 500,
                 min_tokens_per_chunk: int = 50,
                 overlap_tokens: int = 100,
                 abbreviations: Set[str] = None):
        """
        Inizializza il tokenizer ibrido.
        
        Args:
            max_tokens_per_chunk: Numero massimo approssimativo di token per chunk
            min_tokens_per_chunk: Numero minimo di token per chunk (per evitare chunk troppo piccoli)
            overlap_tokens: Numero di token di sovrapposizione tra chunk
            abbreviations: Set di abbreviazioni personalizzate (opzionale)
        """
        self.max_tokens = max_tokens_per_chunk
        self.min_tokens = min_tokens_per_chunk
        self.overlap_tokens = overlap_tokens
        self.logger = logging.getLogger("PDFChunker.HybridTokenizer")
        
        # Inizializza il set di abbreviazioni
        self.abbreviations = self.COMMON_ABBREVIATIONS.copy()
        if abbreviations:
            self.abbreviations.update(abbreviations)
        
        # Compila le espressioni regolari
        self._compile_regex()
    
    def _compile_regex(self):
        """Compila le espressioni regolari per la tokenizzazione."""
        # Regex per identificare le parole (token)
        self.word_pattern = re.compile(r'\b\w+\b')
        
        # Regex per identificare i confini di frase
        self.sent_end_pattern = re.compile(
            r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<!\s[A-Za-z]\.)'
            r'[.!?][\'\"\)\]]*\s+(?=[A-Z0-9\"])'
        )
        
        # Regex per dividere su punti e virgola, virgole, ecc.
        self.hard_break_pattern = re.compile(r'(?<=[;:])\s+')
        self.soft_break_pattern = re.compile(r'(?<=,)\s+')
        
        # Regex per paragrafi e righe
        self.paragraph_pattern = re.compile(r'\n\s*\n')
        self.line_pattern = re.compile(r'\n')
    
    def count_tokens(self, text: str) -> int:
        """
        Conta il numero di token (parole) in un testo.
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Numero di token
        """
        return len(self.word_pattern.findall(text))
    
    def is_abbreviation(self, word: str) -> bool:
        """
        Controlla se una parola è un'abbreviazione.
        
        Args:
            word: Parola da controllare
            
        Returns:
            True se è un'abbreviazione, False altrimenti
        """
        word = word.strip().lower()
        if word in self.abbreviations:
            return True
        
        # Controlla abbreviazioni tipiche (consonanti seguite da punto)
        if re.match(r'^[bcdfghjklmnpqrstvwxyz]{1,3}\.$', word):
            return True
            
        return False
    
    def split_into_sentences(self, text: str) -> List[str]:
        """
        Divide il testo in frasi.
        
        Args:
            text: Testo da dividere
            
        Returns:
            Lista di frasi
        """
        if not text or text.isspace():
            return []
            
        try:
            # Normalizzazione
            text = text.replace('\r\n', '\n')
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            # Tentativo 1: Divisione per punti seguiti da spazi e maiuscole
            try:
                sentences = []
                last_pos = 0
                
                for match in self.sent_end_pattern.finditer(text):
                    end_pos = match.end()
                    sent = text[last_pos:end_pos].strip()
                    
                    # Controlla se è un'abbreviazione
                    words = sent.split()
                    if len(words) >= 2 and self.is_abbreviation(words[-2]):
                        continue
                    
                    sentences.append(sent)
                    last_pos = end_pos
                
                # Aggiungi l'ultima parte
                if last_pos < len(text):
                    sentences.append(text[last_pos:].strip())
                
                # Se abbiamo ottenuto frasi sensate, utilizziamole
                if len(sentences) > 1:
                    return sentences
            except Exception as e:
                self.logger.warning(f"Prima strategia di tokenizzazione fallita: {str(e)}")
            
            # Tentativo 2: Divisione semplice per punti, esclamazioni e domande
            try:
                raw_sentences = []
                # Separa il testo in base a .!?
                parts = re.split(r'([.!?])', text)
                current = ""
                
                # Ricostruisci le frasi includendo il segno di punteggiatura
                for i in range(0, len(parts)-1, 2):
                    if i+1 < len(parts):
                        current += parts[i] + parts[i+1]
                    else:
                        current += parts[i]
                        
                    # Se l'ultima parola non è un'abbreviazione, è una nuova frase
                    words = current.strip().split()
                    if not words or not self.is_abbreviation(words[-1]):
                        raw_sentences.append(current.strip())
                        current = ""
                
                # Aggiungi l'ultimo pezzo se presente
                if parts and len(parts) % 2 == 1:
                    current += parts[-1]
                
                if current.strip():
                    raw_sentences.append(current.strip())
                
                if len(raw_sentences) > 1:
                    return raw_sentences
            except Exception as e:
                self.logger.warning(f"Seconda strategia di tokenizzazione fallita: {str(e)}")
            
            # Tentativo 3: Divisione per paragrafi
            try:
                paragraphs = [p.strip() for p in self.paragraph_pattern.split(text) if p.strip()]
                if len(paragraphs) > 1:
                    return paragraphs
            except Exception as e:
                self.logger.warning(f"Divisione per paragrafi fallita: {str(e)}")
            
            # Tentativo 4: Divisione per righe
            try:
                lines = [line.strip() for line in self.line_pattern.split(text) if line.strip()]
                if len(lines) > 1:
                    return lines
            except Exception as e:
                self.logger.warning(f"Divisione per righe fallita: {str(e)}")
            
            # Se tutti i tentativi falliscono, ritorna l'intero testo come una singola frase
            return [text]
            
        except Exception as e:
            self.logger.error(f"Errore durante la tokenizzazione in frasi: {str(e)}")
            # Fallback
            return [text]
    
    def create_chunks(self, text: str) -> List[Tuple[str, int]]:
        """
        Crea chunk basati sul numero di token, terminando sempre a fine frase.
        
        Args:
            text: Testo da suddividere in chunk
            
        Returns:
            Lista di tuple (chunk_text, num_tokens)
        """
        if not text or text.isspace():
            return []
        
        # Dividi il testo in frasi
        sentences = self.split_into_sentences(text)
        self.logger.info(f"Testo diviso in {len(sentences)} frasi")
        
        # Se c'è una sola frase, restituiscila come unico chunk
        if len(sentences) <= 1:
            token_count = self.count_tokens(text)
            return [(text, token_count)]
        
        # Calcola il numero di token per ogni frase
        sentences_with_tokens = []
        for sent in sentences:
            tokens = self.count_tokens(sent)
            sentences_with_tokens.append((sent, tokens))
        
        # Crea chunk combinando frasi fino a raggiungere il limite di token
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for sentence, tokens in sentences_with_tokens:
            # Se la singola frase è più grande del limite massimo
            if tokens > self.max_tokens:
                # Se c'è già un chunk in costruzione, finalizzalo
                if current_chunk:
                    chunk_text = " ".join(current_chunk)
                    chunks.append((chunk_text, current_tokens))
                    current_chunk = []
                    current_tokens = 0
                
                # Aggiungi la frase lunga come chunk a sé stante
                chunks.append((sentence, tokens))
                continue
            
            # Se aggiungere questa frase supererebbe il limite
            if current_tokens + tokens > self.max_tokens and current_tokens >= self.min_tokens:
                # Finalizza il chunk corrente
                chunk_text = " ".join(current_chunk)
                chunks.append((chunk_text, current_tokens))
                
                # Inizia un nuovo chunk con questa frase
                current_chunk = [sentence]
                current_tokens = tokens
            else:
                # Aggiungi la frase al chunk corrente
                current_chunk.append(sentence)
                current_tokens += tokens
        
        # Aggiungi l'ultimo chunk se non è vuoto
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append((chunk_text, current_tokens))
        
        self.logger.info(f"Creati {len(chunks)} chunk")
        return chunks
    
    def create_overlapping_chunks(self, text: str) -> List[Dict]:
        """
        Crea chunk sovrapposti basati su token, con metadati completi.
        
        Args:
            text: Testo da suddividere in chunk
            
        Returns:
            Lista di dizionari con testo del chunk e metadati
        """
        # Crea chunk senza sovrapposizione
        basic_chunks = self.create_chunks(text)
        
        if len(basic_chunks) <= 1:
            # Se c'è un solo chunk, non serve creare sovrapposizioni
            single_chunk, token_count = basic_chunks[0]
            return [{
                'text': single_chunk,
                'tokens': token_count,
                'chars': len(single_chunk),
                'index': 0,
                'is_overlapping': False
            }]
        
        # Crea chunk con sovrapposizione
        result_chunks = []
        sentence_cache = {}  # Cache per memorizzare le frasi già suddivise
        
        # Aggiungi i chunk base
        for i, (chunk_text, token_count) in enumerate(basic_chunks):
            result_chunks.append({
                'text': chunk_text,
                'tokens': token_count,
                'chars': len(chunk_text),
                'index': i * 2,  # Gli indici pari sono per i chunk base
                'is_overlapping': False
            })
            
            # Aggiungi un chunk sovrapposto se non è l'ultimo chunk
            if i < len(basic_chunks) - 1:
                # Recupera il chunk corrente e il successivo
                current_chunk = chunk_text
                next_chunk, next_tokens = basic_chunks[i + 1]
                
                # Se il chunk non è già nella cache, dividilo in frasi
                if current_chunk not in sentence_cache:
                    sentence_cache[current_chunk] = self.split_into_sentences(current_chunk)
                
                if next_chunk not in sentence_cache:
                    sentence_cache[next_chunk] = self.split_into_sentences(next_chunk)
                
                current_sentences = sentence_cache[current_chunk]
                next_sentences = sentence_cache[next_chunk]
                
                # Calcola quante frasi prendere da ciascun chunk
                current_token_per_sent = token_count / len(current_sentences) if current_sentences else 0
                next_token_per_sent = next_tokens / len(next_sentences) if next_sentences else 0
                
                # Determina quante frasi prendere alla fine del chunk corrente
                current_sentences_to_take = min(
                    len(current_sentences),
                    int(self.overlap_tokens / (2 * current_token_per_sent)) if current_token_per_sent > 0 else 0
                )
                
                # Determina quante frasi prendere all'inizio del chunk successivo
                next_sentences_to_take = min(
                    len(next_sentences),
                    int(self.overlap_tokens / (2 * next_token_per_sent)) if next_token_per_sent > 0 else 0
                )
                
                # Prendi almeno una frase da ciascun lato se possibile
                current_sentences_to_take = max(current_sentences_to_take, 1) if current_sentences else 0
                next_sentences_to_take = max(next_sentences_to_take, 1) if next_sentences else 0
                
                # Crea il chunk sovrapposto
                overlap_sentences = []
                if current_sentences_to_take > 0:
                    overlap_sentences.extend(current_sentences[-current_sentences_to_take:])
                if next_sentences_to_take > 0:
                    overlap_sentences.extend(next_sentences[:next_sentences_to_take])
                
                overlap_text = " ".join(overlap_sentences)
                overlap_tokens = self.count_tokens(overlap_text)
                
                # Se abbiamo un chunk di sovrapposizione significativo, aggiungilo
                if overlap_tokens >= self.min_tokens:
                    result_chunks.append({
                        'text': overlap_text,
                        'tokens': overlap_tokens,
                        'chars': len(overlap_text),
                        'index': i * 2 + 1,  # Gli indici dispari sono per i chunk sovrapposti
                        'is_overlapping': True
                    })
        
        self.logger.info(f"Creati {len(result_chunks)} chunk totali (inclusi {len(result_chunks) - len(basic_chunks)} chunk sovrapposti)")
        return result_chunks