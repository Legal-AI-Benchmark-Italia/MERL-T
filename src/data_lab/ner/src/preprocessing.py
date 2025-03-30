"""
Modulo per la pipeline di preprocessing del testo per il sistema NER-Giuridico.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple

import spacy
from spacy.language import Language
from spacy.tokens import Doc

from .config import config

logger = logging.getLogger(__name__)

class TextPreprocessor:
    """Classe per il preprocessing del testo prima del riconoscimento delle entità."""
    
    def __init__(self):
        """Inizializza il preprocessore di testo."""
        self.use_spacy = config.get("preprocessing.tokenization.use_spacy", True)
        self.normalize_spaces = config.get("preprocessing.normalization.normalize_spaces", True)
        self.lowercase = config.get("preprocessing.normalization.lowercase", False)
        self.remove_accents = config.get("preprocessing.normalization.remove_accents", False)
        
        # Carica il modello spaCy se necessario
        if self.use_spacy:
            spacy_model = config.get("models.spacy.model_name", "it_core_news_lg")
            disabled_components = config.get("models.spacy.disable", ["ner"])
            
            logger.info(f"Caricamento del modello spaCy {spacy_model}")
            try:
                self.nlp = spacy.load(spacy_model, disable=disabled_components)
                logger.info(f"Modello spaCy {spacy_model} caricato con successo")
            except OSError:
                logger.warning(f"Modello spaCy {spacy_model} non trovato. Installazione in corso...")
                spacy.cli.download(spacy_model)
                self.nlp = spacy.load(spacy_model, disable=disabled_components)
                logger.info(f"Modello spaCy {spacy_model} installato e caricato con successo")
    
    def preprocess(self, text: str) -> Tuple[str, Optional[Doc]]:
        """
        Esegue il preprocessing del testo.
        
        Args:
            text: Testo da preprocessare.
        
        Returns:
            Tupla contenente il testo preprocessato e il documento spaCy (se disponibile).
        """
        # Normalizzazione degli spazi
        if self.normalize_spaces:
            text = self._normalize_spaces(text)
        
        # Conversione in minuscolo (opzionale)
        if self.lowercase:
            text = text.lower()
        
        # Rimozione degli accenti (opzionale)
        if self.remove_accents:
            text = self._remove_accents(text)
        
        # Elaborazione con spaCy
        doc = None
        if self.use_spacy:
            doc = self.nlp(text)
        
        return text, doc
    
    def _normalize_spaces(self, text: str) -> str:
        """
        Normalizza gli spazi nel testo.
        
        Args:
            text: Testo da normalizzare.
        
        Returns:
            Testo con spazi normalizzati.
        """
        # Rimuove spazi multipli
        text = re.sub(r'\s+', ' ', text)
        # Rimuove spazi all'inizio e alla fine
        text = text.strip()
        return text
    
    def _remove_accents(self, text: str) -> str:
        """
        Rimuove gli accenti dal testo.
        
        Args:
            text: Testo da cui rimuovere gli accenti.
        
        Returns:
            Testo senza accenti.
        """
        import unicodedata
        return ''.join(c for c in unicodedata.normalize('NFD', text)
                      if unicodedata.category(c) != 'Mn')
    
    def segment_text(self, text: str) -> List[str]:
        """
        Segmenta il testo in parti più piccole per l'elaborazione.
        
        Args:
            text: Testo da segmentare.
        
        Returns:
            Lista di segmenti di testo.
        """
        use_spacy_segmentation = config.get("preprocessing.segmentation.use_spacy", True)
        max_segment_length = config.get("preprocessing.segmentation.max_segment_length", 512)
        overlap = config.get("preprocessing.segmentation.overlap", 128)
        
        if use_spacy_segmentation and self.use_spacy:
            return self._segment_with_spacy(text, max_segment_length, overlap)
        else:
            return self._segment_by_length(text, max_segment_length, overlap)
    
    def _segment_with_spacy(self, text: str, max_length: int, overlap: int) -> List[str]:
        """
        Segmenta il testo utilizzando spaCy per rispettare i confini delle frasi.
        
        Args:
            text: Testo da segmentare.
            max_length: Lunghezza massima di ogni segmento.
            overlap: Sovrapposizione tra segmenti consecutivi.
        
        Returns:
            Lista di segmenti di testo.
        """
        doc = self.nlp(text)
        segments = []
        current_segment = []
        current_length = 0
        
        for sent in doc.sents:
            sent_text = sent.text
            sent_length = len(sent_text)
            
            # Se la frase è troppo lunga, la dividiamo ulteriormente
            if sent_length > max_length:
                if current_segment:
                    segments.append(' '.join(current_segment))
                    current_segment = []
                    current_length = 0
                
                # Dividi la frase lunga in parti più piccole
                sub_segments = self._segment_by_length(sent_text, max_length, overlap)
                segments.extend(sub_segments)
                continue
            
            # Se aggiungere la frase supera la lunghezza massima, inizia un nuovo segmento
            if current_length + sent_length > max_length and current_segment:
                segments.append(' '.join(current_segment))
                
                # Mantieni alcune frasi per sovrapposizione
                overlap_tokens = []
                overlap_length = 0
                for i in range(len(current_segment) - 1, -1, -1):
                    if overlap_length + len(current_segment[i]) <= overlap:
                        overlap_tokens.insert(0, current_segment[i])
                        overlap_length += len(current_segment[i])
                    else:
                        break
                
                current_segment = overlap_tokens
                current_length = overlap_length
            
            current_segment.append(sent_text)
            current_length += sent_length
        
        # Aggiungi l'ultimo segmento se non è vuoto
        if current_segment:
            segments.append(' '.join(current_segment))
        
        return segments
    
    def _segment_by_length(self, text: str, max_length: int, overlap: int) -> List[str]:
        """
        Segmenta il testo in base alla lunghezza, senza considerare i confini delle frasi.
        
        Args:
            text: Testo da segmentare.
            max_length: Lunghezza massima di ogni segmento.
            overlap: Sovrapposizione tra segmenti consecutivi.
        
        Returns:
            Lista di segmenti di testo.
        """
        segments = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + max_length, text_length)
            
            # Se non siamo alla fine del testo e non siamo a un confine di parola,
            # torniamo indietro fino a trovare uno spazio
            if end < text_length and text[end] != ' ':
                while end > start and text[end] != ' ':
                    end -= 1
                if end == start:  # Nel caso in cui non ci siano spazi
                    end = min(start + max_length, text_length)
            
            segments.append(text[start:end].strip())
            
            # Calcola il nuovo punto di inizio considerando la sovrapposizione
            start = end - overlap if end - overlap > start else end
        
        return segments
