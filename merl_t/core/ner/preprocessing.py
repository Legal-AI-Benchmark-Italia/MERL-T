"""
Text Preprocessing for Legal NER

Provides utilities for cleaning and normalizing legal text before NER processing.
"""

import re
from typing import List, Dict, Any, Optional

import spacy
from loguru import logger


class TextPreprocessor:
    """
    Text preprocessing for legal documents.
    
    Handles tasks like:
    - Text cleaning
    - Sentence segmentation
    - Normalization of legal citation formats
    - Standardization of punctuation
    """
    
    def __init__(
        self,
        spacy_model: str = "it_core_news_lg",
        max_length: int = 1000000,
        disable_sentencizer: bool = False
    ):
        """
        Initialize the preprocessor.
        
        Args:
            spacy_model: The spaCy model to use
            max_length: Maximum text length for the spaCy pipeline
            disable_sentencizer: Whether to disable sentence segmentation
        """
        self.patterns = {
            # Leggi, decreti e codici
            "numero_legge": r"(?:legge|decreto|d\.lgs|d\. ?lgs|dlgs)\s+(?:n\.?\s*)?(\d+)(?:\s*del\s*|\s*/\s*|,\s*|\s+)(\d{1,2})(?:/|-|\.)(\d{1,2})(?:/|-|\.)(\d{2,4})",
            "codice": r"(?:art(?:icolo|\.)?\s+(\d+(?:\s*(?:-|,|e)\s*\d+)*))\s+(?:del|c\.?)\s+(?:codice\s+)?(civile|penale|procedura\s+civile|procedura\s+penale|c\.?c\.?|c\.?p\.?|c\.?p\.?c\.?|c\.?p\.?p\.?)",
            
            # Citazioni di sentenze
            "citazione_sentenza": r"(?:Cass(?:azione)?\.?|Corte Suprema|Corte Costituzionale|Consiglio di Stato|TAR)(?:\s+(?:civ\.?|pen\.?|sez\.?\s+(?:un\.?|[IVX]+)))?(?:\s+(?:n\.?\s*)?(\d+))?(?:\s*del\s*|\s+)(\d{1,2})(?:/|-|\.)(\d{1,2})(?:/|-|\.)(\d{2,4})",
            
            # Riferimenti normativi generici
            "riferimento_normativo": r"(?:ai\s+sensi|ex)\s+(?:dell[ao'])?(?:\s+)?(?:art(?:icolo|\.)?)\s+(\d+(?:\s*(?:-|,|e)\s*\d+)*)",
        }
        
        # Compile patterns
        self.compiled_patterns = {name: re.compile(pattern, re.IGNORECASE) 
                                 for name, pattern in self.patterns.items()}
        
        # Initialize spaCy model for text processing
        try:
            logger.info(f"Loading spaCy model {spacy_model}")
            self.nlp = spacy.load(spacy_model)
            self.nlp.max_length = max_length
            
            # Disable components we don't need for preprocessing
            if disable_sentencizer:
                # Keep tokenizer and sentencizer but disable other components
                disabled_components = [pipe for pipe in self.nlp.pipe_names
                                     if pipe not in ["tokenizer", "sentencizer"]]
                self.nlp.disable_pipes(*disabled_components)
            
            logger.info("SpaCy model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load spaCy model: {e}")
            self.nlp = None
            
    def _clean_text(self, text: str) -> str:
        """
        Clean text by removing unnecessary whitespace and normalizing quotes.
        
        Args:
            text: Input text
            
        Returns:
            Cleaned text
        """
        # Replace multiple whitespace with a single space
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize various quote types
        text = re.sub(r'[«»""„‟]', '"', text)
        text = re.sub(r'[''‛‚]', "'", text)
        
        # Normalize dashes and spaces around punctuation
        text = re.sub(r'\s*([.,;:!?)])\s*', r'\1 ', text)
        text = re.sub(r'\s*([(])\s*', r' \1', text)
        text = re.sub(r'\s*-\s*', '-', text)
        
        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def _normalize_citations(self, text: str) -> str:
        """
        Normalize legal citations to a standard format.
        
        Args:
            text: Input text
            
        Returns:
            Text with normalized citations
        """
        # Replace abbreviated citations with full forms
        replacements = {
            # Codes
            r'c\.c\.': 'codice civile',
            r'c\.p\.': 'codice penale',
            r'c\.p\.c\.': 'codice di procedura civile',
            r'c\.p\.p\.': 'codice di procedura penale',
            
            # Decrees
            r'd\.lgs\.': 'decreto legislativo',
            r'd\. ?lgs\.': 'decreto legislativo',
            r'dlgs\.': 'decreto legislativo',
            
            # Courts
            r'Cass\.': 'Cassazione',
            r'Cass\. civ\.': 'Cassazione civile',
            r'Cass\. pen\.': 'Cassazione penale',
            r'Corte Cost\.': 'Corte Costituzionale',
            r'Cons\. Stato': 'Consiglio di Stato',
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            
        return text
    
    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using spaCy's sentence segmentation.
        
        Args:
            text: Text to segment
            
        Returns:
            List of sentences
        """
        if not self.nlp:
            # Fallback if spaCy is not available
            return re.split(r'(?<=[.!?])\s+', text)
        
        doc = self.nlp(text)
        return [sent.text for sent in doc.sents]
    
    def normalize(self, text: str) -> str:
        """
        Apply full text normalization pipeline.
        
        Args:
            text: Raw input text
            
        Returns:
            Normalized text
        """
        # Apply cleaning
        text = self._clean_text(text)
        
        # Normalize citations
        text = self._normalize_citations(text)
        
        return text
    
    def find_legal_references(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract legal references from text using regex patterns.
        
        Args:
            text: Input text
            
        Returns:
            List of legal references with type, text and positions
        """
        references = []
        
        # Apply each pattern and extract matches
        for name, pattern in self.compiled_patterns.items():
            for match in pattern.finditer(text):
                references.append({
                    'type': name,
                    'text': match.group(0),
                    'span': (match.start(), match.end()),
                    'groups': match.groups()
                })
        
        # Sort by position
        references.sort(key=lambda x: x['span'][0])
        
        return references
        
    def process(self, text: str) -> Dict[str, Any]:
        """
        Apply full preprocessing pipeline and return structured results.
        
        Args:
            text: Raw input text
            
        Returns:
            Dict with processed text and metadata
        """
        # Apply normalization
        normalized_text = self.normalize(text)
        
        # Find legal references
        legal_references = self.find_legal_references(normalized_text)
        
        # Split into sentences
        sentences = self.split_into_sentences(normalized_text)
        
        return {
            'original_text': text,
            'normalized_text': normalized_text,
            'sentences': sentences,
            'legal_references': legal_references,
            'metadata': {
                'char_count': len(normalized_text),
                'sentence_count': len(sentences),
                'reference_count': len(legal_references)
            }
        } 