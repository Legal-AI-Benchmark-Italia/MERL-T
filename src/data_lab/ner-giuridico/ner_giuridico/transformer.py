"""
Modulo per il riconoscimento di entità basato su modelli transformer per il sistema NER-Giuridico.
"""

import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from transformers import (
    AutoTokenizer, 
    AutoModelForTokenClassification,
    pipeline,
    TokenClassificationPipeline
)

from .config import config
from .entities.entities import Entity
from .entities.entity_manager import EntityType


logger = logging.getLogger(__name__)

class TransformerRecognizer:
    """
    Riconoscitore di entità basato su modelli transformer per il sistema NER-Giuridico.
    Utilizza modelli pre-addestrati o fine-tuned per identificare entità giuridiche.
    """
    
    def __init__(self):
        """Inizializza il riconoscitore basato su transformer."""
        self.model_name = config.get("models.transformer.model_name", "dbmdz/bert-base-italian-xxl-cased")
        self.max_length = config.get("models.transformer.max_length", 512)
        self.batch_size = config.get("models.transformer.batch_size", 16)
        #self.device = config.get("models.transformer.device", "cuda" if torch.cuda.is_available() else "cpu")
        self.quantization = config.get("models.transformer.quantization", False)
        
        # Mappa delle etichette del modello ai tipi di entità
        self.label_map = {
            "B-ARTICOLO_CODICE": EntityType.ARTICOLO_CODICE,
            "I-ARTICOLO_CODICE": EntityType.ARTICOLO_CODICE,
            "B-LEGGE": EntityType.LEGGE,
            "I-LEGGE": EntityType.LEGGE,
            "B-DECRETO": EntityType.DECRETO,
            "I-DECRETO": EntityType.DECRETO,
            "B-REGOLAMENTO_UE": EntityType.REGOLAMENTO_UE,
            "I-REGOLAMENTO_UE": EntityType.REGOLAMENTO_UE,
            "B-SENTENZA": EntityType.SENTENZA,
            "I-SENTENZA": EntityType.SENTENZA,
            "B-ORDINANZA": EntityType.ORDINANZA,
            "I-ORDINANZA": EntityType.ORDINANZA,
            "B-CONCETTO_GIURIDICO": EntityType.CONCETTO_GIURIDICO,
            "I-CONCETTO_GIURIDICO": EntityType.CONCETTO_GIURIDICO
        }
        
        # Carica il modello e il tokenizer
        self._load_model()
    
    def _load_model(self):
        """
        Carica il modello transformer e il tokenizer.
        Se il modello fine-tuned esiste localmente, lo carica, altrimenti carica il modello base.
        """
        try:
            # Controlla se esiste un modello fine-tuned
            base_dir = Path(__file__).parent.parent
            model_dir = base_dir / "models" / "transformer"
            
            if model_dir.exists():
                logger.info(f"Caricamento del modello fine-tuned da {model_dir}")
                self.tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
                
                # Configura le opzioni di quantizzazione se richiesto
                if self.quantization and self.device == "cpu":
                    logger.info("Applicazione della quantizzazione al modello")
                    self.model = AutoModelForTokenClassification.from_pretrained(
                        str(model_dir),
                        quantization_config={"load_in_8bit": True}
                    )
                else:
                    self.model = AutoModelForTokenClassification.from_pretrained(str(model_dir))
                
                self.model.to(self.device)
                
                # Crea la pipeline di NER
                self.ner_pipeline = pipeline(
                    "token-classification",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    aggregation_strategy="simple",
                    device=0 if self.device == "cuda" else -1
                )
                
                logger.info("Modello fine-tuned caricato con successo")
            else:
                # Carica il modello base
                logger.info(f"Modello fine-tuned non trovato. Caricamento del modello base {self.model_name}")
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                
                # Configura le opzioni di quantizzazione se richiesto
                if self.quantization and self.device == "cpu":
                    logger.info("Applicazione della quantizzazione al modello")
                    self.model = AutoModelForTokenClassification.from_pretrained(
                        self.model_name,
                        quantization_config={"load_in_8bit": True}
                    )
                else:
                    self.model = AutoModelForTokenClassification.from_pretrained(self.model_name)
                
                self.model.to(self.device)
                
                # Crea la pipeline di NER
                self.ner_pipeline = pipeline(
                    "token-classification",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    aggregation_strategy="simple",
                    device=0 if self.device == "cuda" else -1
                )
                
                logger.warning("Modello base caricato. Le prestazioni potrebbero non essere ottimali per il riconoscimento di entità giuridiche.")
                logger.info("Si consiglia di eseguire il fine-tuning del modello con dati specifici del dominio giuridico.")
        
        except Exception as e:
            logger.error(f"Errore nel caricamento del modello: {e}")
            logger.warning("Riconoscitore transformer disabilitato a causa di errori nel caricamento del modello.")
            self.ner_pipeline = None
    
    def recognize(self, text: str) -> List[Entity]:
        """
        Riconosce le entità giuridiche nel testo utilizzando il modello transformer.
        
        Args:
            text: Testo in cui cercare le entità.
        
        Returns:
            Lista di entità riconosciute.
        """
        if self.ner_pipeline is None:
            logger.warning("Riconoscitore transformer non disponibile.")
            return []
        
        entities = []
        
        try:
            # Gestione di testi lunghi
            if len(text) > self.max_length * 4:  # Se il testo è molto lungo
                # Dividi il testo in segmenti più piccoli
                segments = self._segment_text(text)
                
                # Processa ogni segmento
                offset = 0
                for segment in segments:
                    segment_entities = self._process_segment(segment, offset)
                    entities.extend(segment_entities)
                    offset += len(segment)
            else:
                # Processa il testo direttamente
                entities = self._process_segment(text, 0)
        
        except Exception as e:
            logger.error(f"Errore nel riconoscimento delle entità con il modello transformer: {e}")
        
        return entities
    
    def _segment_text(self, text: str) -> List[str]:
        """
        Divide il testo in segmenti più piccoli per l'elaborazione.
        
        Args:
            text: Testo da segmentare.
        
        Returns:
            Lista di segmenti di testo.
        """
        max_length = self.max_length * 4  # Lunghezza massima in caratteri (approssimativa)
        overlap = 100  # Sovrapposizione tra segmenti
        
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
            
            segments.append(text[start:end])
            
            # Calcola il nuovo punto di inizio considerando la sovrapposizione
            start = end - overlap if end - overlap > start else end
        
        return segments
    
    def _process_segment(self, text: str, offset: int) -> List[Entity]:
        """
        Processa un segmento di testo con il modello transformer.
        
        Args:
            text: Segmento di testo da processare.
            offset: Offset del segmento nel testo originale.
        
        Returns:
            Lista di entità riconosciute nel segmento.
        """
        if not text.strip():
            return []
        
        entities = []
        
        # Esegui la pipeline NER
        results = self.ner_pipeline(text)
        
        # Converti i risultati in entità
        for result in results:
            # Estrai le informazioni dal risultato
            entity_text = result["word"]
            start_char = result["start"] + offset
            end_char = result["end"] + offset
            label = result["entity"]
            score = result["score"]
            
            # Mappa l'etichetta al tipo di entità
            if label in self.label_map:
                entity_type = self.label_map[label]
                
                # Crea l'entità
                entity = Entity(
                    text=entity_text,
                    type=entity_type,
                    start_char=start_char,
                    end_char=end_char,
                    normalized_text=None,  # Sarà normalizzato in seguito
                    metadata={
                        "label": label,
                        "score": score
                    }
                )
                
                entities.append(entity)
        
        return entities
    
    def fine_tune(self, training_data_path: str, validation_data_path: Optional[str] = None, 
                 epochs: int = 3, learning_rate: float = 5e-5, save_dir: Optional[str] = None):
        """
        Esegue il fine-tuning del modello con dati specifici del dominio giuridico.
        
        Args:
            training_data_path: Percorso al file di training in formato CoNLL.
            validation_data_path: Percorso al file di validazione in formato CoNLL.
            epochs: Numero di epoche di training.
            learning_rate: Learning rate per l'ottimizzatore.
            save_dir: Directory dove salvare il modello fine-tuned.
        """
        # Implementazione del fine-tuning
        # Questa è una funzionalità avanzata che richiede dati annotati
        # e sarà implementata in una versione futura
        logger.info("Fine-tuning del modello non ancora implementato.")
        pass
