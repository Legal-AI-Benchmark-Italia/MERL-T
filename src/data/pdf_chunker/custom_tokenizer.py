#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulo di tokenizzazione custom senza dipendenze da NLTK.
"""

import re
import logging

class CustomTokenizer:
    """
    Tokenizer personalizzato per dividere il testo in frasi.
    Non dipende da NLTK e funziona bene con testi giuridici italiani.
    """
    
    def __init__(self, max_chunk_size=1000):
        """
        Inizializza il tokenizer personalizzato.
        
        Args:
            max_chunk_size: Dimensione massima dei chunk
        """
        self.max_chunk_size = max_chunk_size
        self.logger = logging.getLogger("PDFChunker.CustomTokenizer")
        
        # Pattern regex per individuare confini di frase
        self.base_pattern = r'(?<=[.!?])\s+(?=[A-Z0-9])'
        
        # Abbreviazioni comuni nei testi giuridici italiani da non considerare come fine frase
        self.abbreviations = [
            r'art\.',
            r'artt\.',
            r'n\.',
            r'nn\.',
            r'pag\.',
            r'pp\.',
            r'par\.',
            r'lett\.',
            r'cfr\.',
            r'fig\.',
            r'es\.',
            r'p\.',
            r'cap\.',
            r'doc\.',
            r'cit\.',
            r'op\. cit\.',
            r'sig\.',
            r'dott\.',
            r'prof\.',
            r'avv\.',
            r'dir\.',
            r'c\.d\.',
            r'c\.c\.',
            r'c\.p\.',
            r'c\.p\.c\.',
            r'd\.lgs\.',
            r'c\.p\.p\.',
            r'cost\.',
            r'ecc\.'
        ]

    def tokenize(self, text):
        """
        Divide il testo in frasi utilizzando vari metodi.
        
        Args:
            text: Testo da dividere in frasi
            
        Returns:
            Lista di frasi
        """
        if not text or text.isspace():
            return []
        
        try:
            # Sostituisci temporaneamente le abbreviazioni per evitare false divisioni
            protected_text = text
            placeholders = {}
            
            for i, abbr in enumerate(self.abbreviations):
                placeholder = f"__ABBR{i}__"
                placeholders[placeholder] = abbr
                protected_text = re.sub(abbr, placeholder, protected_text)
            
            # Metodo 1: Trova punti seguiti da spazi e maiuscole
            sentences = re.split(self.base_pattern, protected_text)
            
            # Se abbiamo troppe poche frasi, prova approcci alternativi
            if len(sentences) <= 3 and len(text) > 1000:
                # Metodo 2: Dividi per punti con alcune euristiche
                parts = []
                for part in protected_text.split('.'):
                    part = part.strip()
                    if part:
                        # Controlla se il punto è probabilmente un separatore di frase
                        if part and part[0].isupper() and len(part) > 10:
                            parts.append(part + '.')
                        else:
                            # Concatena con la parte precedente se esiste
                            if parts:
                                parts[-1] = parts[-1] + '. ' + part
                            else:
                                parts.append(part + '.')
                
                sentences = parts if parts else sentences
            
            # Recupera le abbreviazioni originali
            result_sentences = []
            for sent in sentences:
                if sent.strip():
                    for placeholder, abbr in placeholders.items():
                        sent = sent.replace(placeholder, abbr)
                    result_sentences.append(sent.strip())
            
            # Gestisci frasi molto lunghe
            final_sentences = []
            for sent in result_sentences:
                if len(sent) > self.max_chunk_size / 2:
                    final_sentences.extend(self._split_long_sentence(sent))
                else:
                    final_sentences.append(sent)
            
            # Se ancora non abbiamo frasi valide, usa i metodi di fallback
            if not final_sentences:
                return self._fallback_tokenize(text)
                
            return final_sentences
            
        except Exception as e:
            self.logger.error(f"Errore nella tokenizzazione: {str(e)}")
            return self._fallback_tokenize(text)
            
    def _split_long_sentence(self, sentence):
        """
        Divide una frase lunga in parti più piccole.
        
        Args:
            sentence: Frase da dividere
            
        Returns:
            Lista di frasi più piccole
        """
        max_size = int(self.max_chunk_size / 2)
        
        # Prova a dividere per punto e virgola
        if ';' in sentence:
            parts = sentence.split(';')
            result = []
            for i, part in enumerate(parts):
                part = part.strip()
                if part:
                    # Aggiungi il punto e virgola tranne che all'ultima parte
                    if i < len(parts) - 1:
                        result.append(part + ';')
                    else:
                        result.append(part)
            return result
            
        # Prova a dividere per due punti
        if ':' in sentence:
            parts = sentence.split(':')
            result = []
            for i, part in enumerate(parts):
                part = part.strip()
                if part:
                    # Aggiungi i due punti tranne che all'ultima parte
                    if i < len(parts) - 1:
                        result.append(part + ':')
                    else:
                        result.append(part)
            return result
        
        # Prova a dividere per virgole
        if ',' in sentence:
            parts = sentence.split(',')
            result = []
            current = ""
            
            for i, part in enumerate(parts):
                part = part.strip()
                if not part:
                    continue
                    
                # Aggiungi la virgola tranne che all'ultima parte
                if i < len(parts) - 1:
                    part = part + ','
                
                # Se aggiungere questa parte supera la dimensione massima, crea un nuovo chunk
                if len(current) + len(part) > max_size and current:
                    result.append(current.strip())
                    current = part
                else:
                    if current:
                        current += ' ' + part
                    else:
                        current = part
            
            # Aggiungi l'ultima parte
            if current:
                result.append(current.strip())
                
            return result
        
        # Se nessuna delle divisioni precedenti funziona, dividi per spazi
        return self._split_by_spaces(sentence, max_size)
    
    def _split_by_spaces(self, text, max_size):
        """
        Divide il testo negli spazi cercando di rispettare la dimensione massima.
        
        Args:
            text: Testo da dividere
            max_size: Dimensione massima per parte
            
        Returns:
            Lista di parti
        """
        words = text.split()
        result = []
        current = ""
        
        for word in words:
            if len(current) + len(word) + 1 > max_size and current:
                result.append(current.strip())
                current = word
            else:
                if current:
                    current += ' ' + word
                else:
                    current = word
        
        # Aggiungi l'ultima parte
        if current:
            result.append(current.strip())
            
        # Se una parte è ancora troppo lunga, dividi brutalmente
        final_result = []
        for part in result:
            if len(part) > max_size:
                # Dividi in blocchi di testo di lunghezza fissa
                for i in range(0, len(part), max_size):
                    final_result.append(part[i:i+max_size])
            else:
                final_result.append(part)
                
        return final_result
    
    def _fallback_tokenize(self, text):
        """
        Metodo di tokenizzazione di fallback quando tutto il resto fallisce.
        
        Args:
            text: Testo da dividere
            
        Returns:
            Lista di frasi
        """
        self.logger.warning("Uso metodo di tokenizzazione di fallback di emergenza")
        
        # Prova a dividere per paragrafi (linee vuote)
        if '\n\n' in text:
            paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
            if paragraphs:
                result = []
                for p in paragraphs:
                    if len(p) > self.max_chunk_size / 2:
                        result.extend(self._split_by_spaces(p, int(self.max_chunk_size / 2)))
                    else:
                        result.append(p)
                return result
        
        # Prova a dividere per righe
        if '\n' in text:
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            if lines:
                result = []
                current = ""
                
                for line in lines:
                    if len(current) + len(line) + 1 > self.max_chunk_size and current:
                        result.append(current)
                        current = line
                    else:
                        if current:
                            current += '\n' + line
                        else:
                            current = line
                            
                if current:
                    result.append(current)
                    
                return result
        
        # Come ultima risorsa, dividi in blocchi di dimensione fissa
        result = []
        for i in range(0, len(text), int(self.max_chunk_size / 2)):
            chunk = text[i:i + int(self.max_chunk_size / 2)].strip()
            if chunk:
                result.append(chunk)
                
        return result if result else [text.strip()]

def tokenize_sentences(text, max_chunk_size=1000):
    """
    Funzione di utilità per tokenizzare le frasi.
    
    Args:
        text: Testo da dividere in frasi
        max_chunk_size: Dimensione massima dei chunk
        
    Returns:
        Lista di frasi
    """
    tokenizer = CustomTokenizer(max_chunk_size)
    return tokenizer.tokenize(text)