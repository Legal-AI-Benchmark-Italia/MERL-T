#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulo per la pulizia avanzata dei chunk di testo.
Ottimizzato per dataset giuridico e produzione industriale di alto livello istituzionale.

Questo modulo fornisce strumenti avanzati per la pulizia, normalizzazione e ottimizzazione
di testi giuridici, con particolare attenzione alla qualità del testo finale e alle
esigenze di produzione in ambiente istituzionale.

Caratteristiche principali:
- Pulizia configurabile e personalizzabile
- Elaborazione multi-thread per elevate performance
- Gestione intelligente delle newline e della formattazione
- Post-processing per uniformare lo stile
- Monitoraggio dettagliato e reportistica
- Interfaccia da linea di comando per l'integrazione in pipeline di produzione

Versione: 2.0.0
Autore: Enhanced by Claude
Data ultima modifica: 2025-03-18
"""

import re
import logging
import time
import os
import json
import sys
import datetime
from typing import List, Dict, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import re
import logging
import time
import os
from typing import List, Dict, Any, Optional, Tuple, Set, Union
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path


@dataclass
class CleaningStatistics:
    """
    Dataclass per tenere traccia delle statistiche di pulizia.
    Utile per il monitoraggio delle performance e la generazione di report.
    """
    original_chars: int = 0
    cleaned_chars: int = 0
    original_tokens: int = 0
    cleaned_tokens: int = 0
    chunks_processed: int = 0
    chunks_modified: int = 0
    processing_time: float = 0.0
    
    def calculate_percentages(self) -> Dict[str, float]:
        """
        Calcola le percentuali di riduzione per caratteri e token.
        
        Returns:
            Dict[str, float]: Percentuali di riduzione.
        """
        chars_removed = self.original_chars - self.cleaned_chars
        tokens_removed = self.original_tokens - self.cleaned_tokens
        
        char_percentage = (chars_removed / self.original_chars * 100) if self.original_chars > 0 else 0.0
        token_percentage = (tokens_removed / self.original_tokens * 100) if self.original_tokens > 0 else 0.0
        
        return {
            "char_reduction_percentage": char_percentage,
            "token_reduction_percentage": token_percentage
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte le statistiche in un dizionario per la serializzazione.
        
        Returns:
            Dict[str, Any]: Statistiche in formato dizionario.
        """
        stats_dict = {
            "original_chars": self.original_chars,
            "cleaned_chars": self.cleaned_chars,
            "original_tokens": self.original_tokens,
            "cleaned_tokens": self.cleaned_tokens,
            "chunks_processed": self.chunks_processed,
            "chunks_modified": self.chunks_modified,
            "processing_time_seconds": round(self.processing_time, 3)
        }
        
        percentages = self.calculate_percentages()
        stats_dict.update(percentages)
        
        return stats_dict


class TextCleanerConfig:
    """
    Classe per la configurazione del TextCleaner.
    Permette di personalizzare il comportamento del cleaner.
    """
    
    def __init__(self, 
                 log_level: int = logging.INFO,
                 preserve_paragraphs: bool = True,
                 max_workers: int = 4,
                 enable_post_processing: bool = True,
                 preserve_newlines_after_patterns: Optional[Set[str]] = None,
                 custom_patterns: Optional[Dict[str, str]] = None):
        """
        Inizializza la configurazione per il TextCleaner.
        
        Args:
            log_level (int): Livello di logging (default: INFO).
            preserve_paragraphs (bool): Se True, preserva la struttura dei paragrafi.
            max_workers (int): Numero massimo di worker per il multithreading.
            enable_post_processing (bool): Se True, abilita il post-processing del testo.
            preserve_newlines_after_patterns (Set[str]): Pattern dopo i quali preservare le newline.
            custom_patterns (Dict[str, str]): Pattern regex personalizzati da aggiungere.
        """
        self.log_level = log_level
        self.preserve_paragraphs = preserve_paragraphs
        self.max_workers = max_workers
        self.enable_post_processing = enable_post_processing
        
        # Pattern predefiniti dopo cui preservare le newline
        self.preserve_newlines_after_patterns = preserve_newlines_after_patterns or {
            r'[.!?]', r':', r';', r'\.\.\.'
        }
        
        # Pattern regex personalizzati
        self.custom_patterns = custom_patterns or {}
        
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'TextCleanerConfig':
        """
        Crea una configurazione da un dizionario.
        
        Args:
            config_dict (Dict[str, Any]): Dizionario di configurazione.
            
        Returns:
            TextCleanerConfig: Istanza di configurazione.
        """
        log_level_str = config_dict.get('log_level', 'INFO')
        log_level = getattr(logging, log_level_str, logging.INFO)
        
        return cls(
            log_level=log_level,
            preserve_paragraphs=config_dict.get('preserve_paragraphs', True),
            max_workers=config_dict.get('max_workers', 4),
            enable_post_processing=config_dict.get('enable_post_processing', True),
            preserve_newlines_after_patterns=set(config_dict.get('preserve_newlines_after_patterns', [])),
            custom_patterns=config_dict.get('custom_patterns', {})
        )
    
    @classmethod
    def from_json_file(cls, file_path: str) -> 'TextCleanerConfig':
        """
        Carica la configurazione da un file JSON.
        
        Args:
            file_path (str): Percorso del file di configurazione.
            
        Returns:
            TextCleanerConfig: Istanza di configurazione.
            
        Raises:
            FileNotFoundError: Se il file non esiste.
            json.JSONDecodeError: Se il file non è un JSON valido.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            return cls.from_dict(config_dict)
        except FileNotFoundError:
            logging.error(f"File di configurazione non trovato: {file_path}")
            raise
        except json.JSONDecodeError:
            logging.error(f"File di configurazione non valido: {file_path}")
            raise
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte la configurazione in un dizionario.
        
        Returns:
            Dict[str, Any]: Configurazione in formato dizionario.
        """
        log_level_name = logging.getLevelName(self.log_level)
        
        return {
            'log_level': log_level_name,
            'preserve_paragraphs': self.preserve_paragraphs,
            'max_workers': self.max_workers,
            'enable_post_processing': self.enable_post_processing,
            'preserve_newlines_after_patterns': list(self.preserve_newlines_after_patterns),
            'custom_patterns': self.custom_patterns
        }
    
    def save_to_json_file(self, file_path: str) -> None:
        """
        Salva la configurazione in un file JSON.
        
        Args:
            file_path (str): Percorso del file di destinazione.
        """
        config_dict = self.to_dict()
        
        # Assicura che la directory esista
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)


class TextCleaner:
    """
    Classe per la pulizia dettagliata dei chunk di testo.
    Rimuove elementi indesiderati e normalizza il formato.
    Ottimizzata per dataset giuridici e per un ambiente di produzione istituzionale.
    
    Caratteristiche principali:
    - Pulizia configurabile e personalizzabile
    - Elaborazione multi-thread per performance elevate
    - Monitoraggio dettagliato delle statistiche
    - Gestione intelligente delle newline e del formato
    - Post-processing per uniformare lo stile
    """
    
    # Versione del cleaner
    VERSION = "2.0.0"
    
    def __init__(self, config: Optional[TextCleanerConfig] = None):
        """
        Inizializza il cleaner di testo, compilando i pattern regex per
        migliorare le performance in fase di pulizia.
        
        Args:
            config (Optional[TextCleanerConfig]): Configurazione personalizzata.
        """
        self.config = config or TextCleanerConfig()
        self.stats = CleaningStatistics()
        
        # Configura il logger
        self._setup_logger()
        
        # Compila i pattern per la pulizia del testo
        self._compile_patterns()
        
        self.logger.info(f"TextCleaner v{self.VERSION} inizializzato con configurazione: "
                         f"{json.dumps(self.config.to_dict(), ensure_ascii=False)}")
    
    def _setup_logger(self) -> None:
        """
        Configura il logger per il TextCleaner.
        """
        self.logger = logging.getLogger("TextCleaner")
        
        # Configura il logger se non è già stato impostato
        if not self.logger.hasHandlers():
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '[%(asctime)s] %(levelname)s - %(name)s: %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        # Imposta il livello di logging dalla configurazione
        self.logger.setLevel(self.config.log_level)
    
    def _compile_patterns(self) -> None:
        """
        Compila tutti i pattern regex utilizzati per la pulizia e il post-processing, 
        aggiungendo una descrizione per ciascun pattern.
        """
        # Pattern base per la pulizia
        base_patterns = {
            # Match newline tra due caratteri di parola (es. "word\nword" diventa "word word")
            'word_break_newline': r'(\w)\n(\w)',
            
            # Match newline dopo un trattino per unire parole divise (es. "word-\nword" diventa "word-word")
            'hyphen_break_newline': r'(\-)\n(\w)',
            
            # Match linee vuote (più newline con eventuali spazi) per uniformare gli spazi tra paragrafi
            'empty_lines': r'\n\s*\n',
            
            # Match due o più spazi consecutivi da normalizzare in un singolo spazio
            'multiple_spaces': r'\s{2,}',
            
            # Match tre o più newline consecutivi per ridurli a doppio newline
            'multiple_newlines': r'\n{3,}',
            
            # Match spazi in eccesso prima della punteggiatura
            'space_before_punctuation': r'\s+([,.;:!?])',
            
            # Match punteggiatura seguita da caratteri non-spazio e non numeri, per aggiungere spazio se mancante
            'no_space_after_punctuation': r'([,.;:!?])([^\s\d])',
            
            # Match punti elenco all'inizio della linea (es. •, -, *, □, ○, ▪)
            'bullet_points': r'^\s*[\•\-\*\□\○\▪]\s*',
            
            # Match numeri seguiti da un punto o parentesi all'inizio della linea (liste numerate)
            'numbered_list': r'^\s*\d+[\.\)]\s*',
            
            # Match tabulazioni da sostituire con spazi
            'tabs_to_spaces': r'\t',
            
            # Match spazi bianchi finali alla fine di ogni riga
            'trailing_whitespace': r'\s+$'
        }
        
        # Pattern per il post-processing
        post_patterns = {
            # Match spazi in eccesso prima della punteggiatura, da rimuovere
            'punctuation_no_space': r'\s+([,.;:!?])',
            
            # Match punteggiatura non seguita da uno spazio (es. ",word") per aggiungere lo spazio
            'punctuation_space_after': r'([,.;:!?])([^\s\d\(\)\[\]])',
            
            # Match un trattino che necessita normalizzazione, rimuovendo spazi indesiderati attorno ad esso
            'dash_normalization': r'([^\s])\-([^\s])',
            
            # Match doppie virgolette con spazi in eccesso, da normalizzare
            'double_quotes': r'"\s*([^"]*?)\s*"',
            
            # Match singole virgolette con spazi in eccesso, da normalizzare
            'single_quotes': r"'\s*([^']*?)\s*'",
            
            # Match parentesi aperte con spazi dopo l'apertura per normalizzare la formattazione
            'open_parenthesis': r'\(\s+',
            
            # Match parentesi chiuse con spazi prima della chiusura per normalizzare la formattazione
            'close_parenthesis': r'\s+\)',
            
            # Match spazi dopo parentesi o altri delimitatori di apertura
            'space_after_open_bracket': r'([\(\[{])\s+',
            
            # Match spazi prima di parentesi o altri delimitatori di chiusura
            'space_before_close_bracket': r'\s+([\)\]}])',
            
            # Match due o più punti consecutivi per convertirli in puntini di sospensione standard
            'multiple_periods': r'\.{2,}'
        }
        
        # Combina i pattern base con quelli personalizzati definiti nella configurazione
        combined_patterns = {**base_patterns, **self.config.custom_patterns}
        
        # Compila i pattern base per la pulizia
        self.compiled_patterns = {
            name: re.compile(pattern, re.MULTILINE)
            for name, pattern in combined_patterns.items()
        }
        
        # Compila i pattern per il post-processing
        self.post_patterns = {
            name: re.compile(pattern, re.MULTILINE)
            for name, pattern in post_patterns.items()
        }
        
        # Compila il pattern per la preservazione delle newline, 
        # mantenendo le newline dopo specifici caratteri (ad es. . ! ? : ; ...)
        self.newline_preserve_pattern = re.compile(
            '(' + '|'.join(self.config.preserve_newlines_after_patterns) + ')\s*\n',
            re.MULTILINE
        )
    def clean_text(self, text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Pulisce il testo rimuovendo elementi indesiderati e normalizzando il formato.
        Include una gestione avanzata delle newline, lasciando solo quelle di fine frase.
        
        Args:
            text (str): Testo da pulire.
            
        Returns:
            Tuple[str, Dict[str, Any]]: Testo pulito e statistiche della pulizia.
        """
        if text is None or text == "":
            return "", {"original_length": 0, "cleaned_length": 0, "chars_removed": 0, "percent_removed": 0.0}
        
        try:
            start_time = time.time()
            
            # Conserva informazioni iniziali per le statistiche
            original_length = len(text)
            original_tokens = len(text.split())
            
            # 1. Normalizza i fine riga (CR+LF -> LF)
            text = text.replace('\r\n', '\n')
            
            # 2. Rimuove newline tra parole (senza spazi prima e dopo)
            text = self.compiled_patterns['word_break_newline'].sub(r'\1 \2', text)
            
            # 3. Rimuove newline dopo trattino (senza spazio dopo)
            text = self.compiled_patterns['hyphen_break_newline'].sub(r'\1\2', text)
            
            # 4. Tabulazioni a spazi
            text = self.compiled_patterns['tabs_to_spaces'].sub(' ', text)
            
            # 5. Normalizza righe vuote (conserva doppio newline)
            text = self.compiled_patterns['empty_lines'].sub('\n\n', text)
            
            # 6. Normalizza spazi multipli in uno singolo
            text = self.compiled_patterns['multiple_spaces'].sub(' ', text)
            
            # 7. Normalizza newline multiple in doppio newline
            text = self.compiled_patterns['multiple_newlines'].sub('\n\n', text)
            
            # 8. Gestione intelligente delle newline basata sui pattern di preservazione
            if self.config.preserve_paragraphs:
                # Marcare temporaneamente le newline da preservare
                marked_text = self.newline_preserve_pattern.sub(r'\1§§PRESERVE§§', text)
                # Sostituire le altre newline con spazi
                marked_text = re.sub(r'\n', ' ', marked_text)
                # Ripristinare le newline preservate
                text = marked_text.replace('§§PRESERVE§§', '\n')
            else:
                # Rimuove tutte le newline sostituendole con spazi
                text = re.sub(r'\n', ' ', text)
            
            # 9. Rimuove spazi prima della punteggiatura
            text = self.compiled_patterns['space_before_punctuation'].sub(r'\1', text)
            
            # 10. Aggiunge spazio dopo la punteggiatura se mancante
            text = self.compiled_patterns['no_space_after_punctuation'].sub(r'\1 \2', text)
            
            # 11. Rimuove spazi alla fine di ogni riga
            text = self.compiled_patterns['trailing_whitespace'].sub('', text)
            
            # 12. Pulizia finale: rimuove spazi superflui all'inizio e alla fine
            text = text.strip()
            
            # 13. Post-processing se abilitato
            if self.config.enable_post_processing:
                text = self.post_process_text(text)
            
            # Calcola statistiche
            end_time = time.time()
            new_length = len(text)
            new_tokens = len(text.split())
            chars_removed = original_length - new_length
            
            percent_removed = (chars_removed / original_length) * 100 if original_length > 0 else 0.0
            
            stats = {
                "original_length": original_length,
                "cleaned_length": new_length,
                "original_tokens": original_tokens,
                "cleaned_tokens": new_tokens,
                "chars_removed": chars_removed,
                "tokens_removed": original_tokens - new_tokens,
                "percent_removed": percent_removed,
                "processing_time": end_time - start_time
            }
            
            # Log delle statistiche solo se è stato rimosso qualcosa
            if chars_removed > 0:
                self.logger.debug(f"Pulizia completata: rimossi {chars_removed} caratteri ({percent_removed:.1f}%).")
                
            return text, stats
            
        except Exception as e:
            self.logger.error(f"Errore durante la pulizia del testo: {str(e)}", exc_info=True)
            # In caso di errore, restituisce il testo originale per preservare i dati
            return text, {"error": str(e), "original_length": len(text), "cleaned_length": len(text)}
    
    def clean_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pulisce un singolo chunk, aggiornando il testo e i metadati.
        
        Args:
            chunk (Dict[str, Any]): Dizionario rappresentante il chunk.
            
        Returns:
            Dict[str, Any]: Chunk pulito.
        """
        if not chunk or 'text' not in chunk:
            self.logger.warning("Chunk non valido o mancante del campo 'text'.")
            return chunk
        
        # Crea una copia per non modificare l'originale
        cleaned_chunk = chunk.copy()
        original_text = chunk.get('text', '')
        
        # Pulisci il testo e ottieni le statistiche
        cleaned_text, stats = self.clean_text(original_text)
        
        # Aggiorna i campi del chunk
        cleaned_chunk['text'] = cleaned_text
        cleaned_chunk['tokens'] = len(cleaned_text.split())
        cleaned_chunk['chars'] = len(cleaned_text)
        
        # Aggiungi le statistiche di pulizia per monitoraggio
        cleaned_chunk['cleaning_stats'] = stats
        
        # Flag che indica se il testo è stato modificato
        cleaned_chunk['modified'] = original_text != cleaned_text
        
        return cleaned_chunk
    
    def clean_chunks(self, chunks: List[Dict[str, Any]], parallel: bool = True) -> Tuple[List[Dict[str, Any]], CleaningStatistics]:
        """
        Pulisce una lista di chunk, opzionalmente in parallelo.
        
        Args:
            chunks (List[Dict[str, Any]]): Lista di chunk.
            parallel (bool): Se True, esegue la pulizia in parallelo.
            
        Returns:
            Tuple[List[Dict[str, Any]], CleaningStatistics]: Lista di chunk puliti e statistiche globali.
        """
        if not chunks:
            self.logger.info("Nessun chunk da pulire.")
            return [], CleaningStatistics()
        
        start_time = time.time()
        
        # Resetta le statistiche
        self.stats = CleaningStatistics()
        
        self.logger.info(f"Inizio pulizia di {len(chunks)} chunk" + 
                         (" in parallelo." if parallel else " in sequenza."))
        
        if parallel and len(chunks) > 1 and self.config.max_workers > 1:
            # Pulizia in parallelo
            cleaned_chunks = []
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                # Sottomette tutti i task
                future_to_chunk = {executor.submit(self.clean_chunk, chunk): chunk for chunk in chunks}
                
                # Raccoglie i risultati man mano che sono completati
                for i, future in enumerate(as_completed(future_to_chunk)):
                    try:
                        cleaned_chunk = future.result()
                        cleaned_chunks.append(cleaned_chunk)
                        
                        # Aggiorna le statistiche
                        self._update_stats_from_chunk(cleaned_chunk)
                        
                        # Log progressivo
                        if (i + 1) % 100 == 0 or (i + 1) == len(chunks):
                            self.logger.info(f"Completati {i + 1}/{len(chunks)} chunk ({((i + 1) / len(chunks) * 100):.1f}%).")
                    
                    except Exception as e:
                        original_chunk = future_to_chunk[future]
                        chunk_id = original_chunk.get('id', i)
                        self.logger.error(f"Errore durante la pulizia del chunk {chunk_id}: {str(e)}", exc_info=True)
                        # Preserva il chunk originale in caso di errore
                        cleaned_chunks.append(original_chunk)
        else:
            # Pulizia sequenziale
            cleaned_chunks = []
            for i, chunk in enumerate(chunks):
                try:
                    cleaned_chunk = self.clean_chunk(chunk)
                    cleaned_chunks.append(cleaned_chunk)
                    
                    # Aggiorna le statistiche
                    self._update_stats_from_chunk(cleaned_chunk)
                    
                    # Log progressivo
                    if (i + 1) % 100 == 0 or (i + 1) == len(chunks):
                        self.logger.info(f"Completati {i + 1}/{len(chunks)} chunk ({((i + 1) / len(chunks) * 100):.1f}%).")
                
                except Exception as e:
                    chunk_id = chunk.get('id', i)
                    self.logger.error(f"Errore durante la pulizia del chunk {chunk_id}: {str(e)}", exc_info=True)
                    # Preserva il chunk originale in caso di errore
                    cleaned_chunks.append(chunk)
        
        # Calcola il tempo totale di elaborazione
        end_time = time.time()
        self.stats.processing_time = end_time - start_time
        
        # Log finale con le statistiche
        percentages = self.stats.calculate_percentages()
        self.logger.info(
            f"Pulizia completata in {self.stats.processing_time:.2f} secondi. "
            f"Rimossi {self.stats.original_chars - self.stats.cleaned_chars} caratteri "
            f"({percentages['char_reduction_percentage']:.1f}%) e "
            f"{self.stats.original_tokens - self.stats.cleaned_tokens} token "
            f"({percentages['token_reduction_percentage']:.1f}%)."
        )
        
        return cleaned_chunks, self.stats
    
    def _update_stats_from_chunk(self, chunk: Dict[str, Any]) -> None:
        """
        Aggiorna le statistiche globali con i dati di un chunk.
        
        Args:
            chunk (Dict[str, Any]): Chunk processato.
        """
        stats = chunk.get('cleaning_stats', {})
        
        self.stats.original_chars += stats.get('original_length', 0)
        self.stats.cleaned_chars += stats.get('cleaned_length', 0)
        self.stats.original_tokens += stats.get('original_tokens', 0)
        self.stats.cleaned_tokens += stats.get('cleaned_tokens', 0)
        self.stats.chunks_processed += 1
        
        if chunk.get('modified', False):
            self.stats.chunks_modified += 1
    
    def post_process_text(self, text: str) -> str:
        """
        Esegue operazioni di post-processing sul testo per uniformare la punteggiatura
        e altri segni, garantendo la coerenza stilistica.
        
        Args:
            text (str): Testo da processare.
            
        Returns:
            str: Testo processato.
        """
        if text is None or text == "":
            return ""
        
        try:
            processed = text
            
            # Rimuove spazi prima dei segni di punteggiatura
            processed = self.post_patterns['punctuation_no_space'].sub(r'\1', processed)
            
            # Aggiunge uno spazio dopo la punteggiatura se mancante
            processed = self.post_patterns['punctuation_space_after'].sub(r'\1 \2', processed)
            
            # Normalizza i trattini rimuovendoli, unendo le parole adiacenti
            processed = self.post_patterns['dash_normalization'].sub(r'\1\2', processed)
            
            # Normalizza i puntini di sospensione
            processed = self.post_patterns['multiple_periods'].sub('...', processed)
            
            # Normalizza le virgolette
            processed = self.post_patterns['double_quotes'].sub(r'"\1"', processed)
            processed = self.post_patterns['single_quotes'].sub(r"'\1'", processed)
            
            # Normalizza le parentesi e le parentesi quadre
            processed = self.post_patterns['open_parenthesis'].sub('(', processed)
            processed = self.post_patterns['close_parenthesis'].sub(')', processed)
            processed = self.post_patterns['space_after_open_bracket'].sub(r'\1', processed)
            processed = self.post_patterns['space_before_close_bracket'].sub(r'\1', processed)
            
            return processed
            
        except Exception as e:
            self.logger.error(f"Errore durante il post-processing: {str(e)}", exc_info=True)
            # In caso di errore, restituisce il testo originale
            return text
    
    def extract_and_merge_paragraphs(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Estrae paragrafi dai chunk e li ricombina per migliorare la coerenza semantica.
        Implementazione avanzata che utilizza euristiche di identificazione dei paragrafi.
        
        Args:
            chunks (List[Dict[str, Any]]): Lista di chunk.
            
        Returns:
            List[Dict[str, Any]]: Lista di chunk con paragrafi ricombinati.
        """
        if not chunks:
            return []
        
        self.logger.info(f"Inizio estrazione e fusione dei paragrafi da {len(chunks)} chunk.")
        
        try:
            # Strategia di fusione dei paragrafi:
            # 1. Identifica i chunk che terminano con frasi incomplete
            # 2. Unisci questi chunk con quelli successivi
            
            # Indicatori di fine frase incompleta
            incomplete_sentence_indicators = [
                r'[,;:]$',  # Termina con virgola, punto e virgola o due punti
                r'\b(e|ed|o|oppure|ma|però|quindi|inoltre|infatti|tuttavia|perché|poiché|sebbene|benché|come)$',  # Congiunzioni finali
                r'\b(il|lo|la|i|gli|le|un|uno|una)$',  # Articoli finali
                r'\b(in|con|per|tra|fra|su|di|da|a|al|alla|ai|alle|del|dello|della|dei|degli|delle)$'  # Preposizioni finali
            ]
            
            # Compila i pattern
            incomplete_patterns = [re.compile(pattern) for pattern in incomplete_sentence_indicators]
            
            # Lista dei chunk risultanti
            merged_chunks = []
            current_chunk = None
            
            for i, chunk in enumerate(chunks):
                if current_chunk is None:
                    current_chunk = chunk.copy()
                    continue
                
                current_text = current_chunk['text'].strip()
                
                # Verifica se il chunk corrente termina con una frase incompleta
                is_incomplete = False
                for pattern in incomplete_patterns:
                    if pattern.search(current_text):
                        is_incomplete = True
                        break
                
                # Se non termina con una frase completa e non è l'ultimo chunk
                if is_incomplete:
                    # Unisci con il chunk successivo
                    current_chunk['text'] = current_text + ' ' + chunk['text'].strip()
                    current_chunk['tokens'] = len(current_chunk['text'].split())
                    current_chunk['chars'] = len(current_chunk['text'])
                    current_chunk['merged'] = True
                    current_chunk['merged_ids'] = current_chunk.get('merged_ids', [current_chunk.get('id', f'chunk_{i-1}')]) + [chunk.get('id', f'chunk_{i}')]
                else:
                    # Aggiungi il chunk corrente ai risultati e inizia uno nuovo
                    merged_chunks.append(current_chunk)
                    current_chunk = chunk.copy()
            
            # Aggiungi l'ultimo chunk se esiste
            if current_chunk is not None:
                merged_chunks.append(current_chunk)
            
            self.logger.info(f"Fusione completata. Ridotti da {len(chunks)} a {len(merged_chunks)} chunk.")
            
            return merged_chunks
            
        except Exception as e:
            self.logger.error(f"Errore durante l'estrazione e fusione dei paragrafi: {str(e)}", exc_info=True)
            # In caso di errore, restituisce i chunk originali
            return chunks
    
    def process_directory(self, input_dir: str, output_dir: str, file_pattern: str = "*.json") -> Dict[str, Any]:
        """
        Elabora tutti i file in una directory che corrispondono al pattern specificato.
        
        Args:
            input_dir (str): Directory di input.
            output_dir (str): Directory di output.
            file_pattern (str): Pattern per filtrare i file (default: "*.json").
            
        Returns:
            Dict[str, Any]: Statistiche globali dell'elaborazione.
        """
        start_time = time.time()
        
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        # Crea la directory di output se non esiste
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Trova tutti i file che corrispondono al pattern
        files = list(input_path.glob(file_pattern))
        
        if not files:
            self.logger.warning(f"Nessun file trovato in {input_dir} con pattern {file_pattern}")
            return {"files_processed": 0, "processing_time": 0, "success": False}
        
        self.logger.info(f"Trovati {len(files)} file da elaborare in {input_dir}")
        
        # Statistiche globali
        global_stats = {
            "files_processed": 0,
            "files_failed": 0,
            "chunks_processed": 0,
            "chunks_modified": 0,
            "original_chars": 0,
            "cleaned_chars": 0,
            "original_tokens": 0,
            "cleaned_tokens": 0,
            "file_details": []
        }
        
        # Elabora ogni file
        for file_path in files:
            try:
                file_stats = self._process_single_file(file_path, output_path)
                
                # Aggiorna le statistiche globali
                global_stats["files_processed"] += 1
                global_stats["chunks_processed"] += file_stats.get("chunks_processed", 0)
                global_stats["chunks_modified"] += file_stats.get("chunks_modified", 0)
                global_stats["original_chars"] += file_stats.get("original_chars", 0)
                global_stats["cleaned_chars"] += file_stats.get("cleaned_chars", 0)
                global_stats["original_tokens"] += file_stats.get("original_tokens", 0)
                global_stats["cleaned_tokens"] += file_stats.get("cleaned_tokens", 0)
                
                # Aggiungi i dettagli del file
                global_stats["file_details"].append({
                    "file": str(file_path.name),
                    "status": "success",
                    **file_stats
                })
                
                self.logger.info(f"Elaborato: {file_path.name} - {file_stats.get('chunks_processed', 0)} chunk")
                
            except Exception as e:
                global_stats["files_failed"] += 1
                global_stats["file_details"].append({
                    "file": str(file_path.name),
                    "status": "failed",
                    "error": str(e)
                })
                self.logger.error(f"Errore nell'elaborazione del file {file_path}: {str(e)}", exc_info=True)
        
        # Calcola il tempo totale di elaborazione
        end_time = time.time()
        processing_time = end_time - start_time
        global_stats["processing_time"] = processing_time
        
        # Calcola le percentuali di riduzione
        if global_stats["original_chars"] > 0:
            char_reduction = global_stats["original_chars"] - global_stats["cleaned_chars"]
            global_stats["char_reduction_percentage"] = (char_reduction / global_stats["original_chars"]) * 100
        else:
            global_stats["char_reduction_percentage"] = 0.0
            
        if global_stats["original_tokens"] > 0:
            token_reduction = global_stats["original_tokens"] - global_stats["cleaned_tokens"]
            global_stats["token_reduction_percentage"] = (token_reduction / global_stats["original_tokens"]) * 100
        else:
            global_stats["token_reduction_percentage"] = 0.0
        
        # Log delle statistiche globali
        self.logger.info(
            f"Elaborazione completata in {processing_time:.2f} secondi. "
            f"File elaborati: {global_stats['files_processed']}. "
            f"File falliti: {global_stats['files_failed']}. "
            f"Chunk elaborati: {global_stats['chunks_processed']}. "
            f"Riduzione caratteri: {global_stats['char_reduction_percentage']:.1f}%."
        )
        
        # Esporta le statistiche in un file JSON nella directory di output
        stats_path = output_path / "cleaning_stats.json"
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(global_stats, f, indent=2, ensure_ascii=False)
            
        return global_stats
    
    def _process_single_file(self, file_path: Path, output_dir: Path) -> Dict[str, Any]:
        """
        Elabora un singolo file di chunk.
        
        Args:
            file_path (Path): Percorso del file da elaborare.
            output_dir (Path): Directory di output.
            
        Returns:
            Dict[str, Any]: Statistiche dell'elaborazione.
            
        Raises:
            Exception: Se si verifica un errore durante l'elaborazione.
        """
        try:
            # Leggi il file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            
            # Estrai i chunk (gestisci diversi formati possibili)
            chunks = []
            if isinstance(content, list):
                chunks = content
            elif isinstance(content, dict) and 'chunks' in content:
                chunks = content['chunks']
            elif isinstance(content, dict) and 'data' in content and isinstance(content['data'], list):
                chunks = content['data']
            else:
                raise ValueError(f"Formato file non riconosciuto: {file_path}")
            
            if not chunks:
                self.logger.warning(f"Nessun chunk trovato nel file {file_path}")
                return {"chunks_processed": 0, "chunks_modified": 0}
            
            # Pulisci i chunk
            cleaned_chunks, stats = self.clean_chunks(chunks)
            
            # Prepara il contenuto da salvare (mantieni la struttura originale)
            output_content = content
            if isinstance(content, list):
                output_content = cleaned_chunks
            elif isinstance(content, dict) and 'chunks' in content:
                output_content['chunks'] = cleaned_chunks
                output_content['cleaning_stats'] = stats.to_dict()
            elif isinstance(content, dict) and 'data' in content and isinstance(content['data'], list):
                output_content['data'] = cleaned_chunks
                output_content['cleaning_stats'] = stats.to_dict()
            
            # Definisci il percorso di output
            output_path = output_dir / file_path.name
            
            # Salva il file pulito
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_content, f, indent=2, ensure_ascii=False)
            
            return stats.to_dict()
            
        except Exception as e:
            self.logger.error(f"Errore nell'elaborazione del file {file_path}: {str(e)}", exc_info=True)
            raise