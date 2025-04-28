"""
Modulo per il riconoscimento di entità basato su modelli transformer per il sistema NER-Giuridico.
"""

import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import os
import sys

# Aggiungiamo il percorso root al PYTHONPATH
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)

from transformers import (
    AutoTokenizer, 
    AutoModelForTokenClassification,
    pipeline,
    TokenClassificationPipeline
)

from src.core.config import get_config_manager
from src.core.entities.entities import Entity
from src.core.entities.entity_manager import EntityType, get_entity_manager


logger = logging.getLogger(__name__)

class TransformerRecognizer:
    """
    Riconoscitore di entità basato su modelli transformer per il sistema NER-Giuridico.
    Utilizza modelli pre-addestrati o fine-tuned per identificare entità giuridiche.
    """
    
    def __init__(self, model_path: Optional[str] = None, entity_manager=None):
        """
        Inizializza il riconoscitore basato su transformer.
        
        Args:
            model_path: Percorso a un modello personalizzato (opzionale)
            entity_manager: Istanza di EntityManager (opzionale)
        """
        # Ottieni la configurazione dal ConfigManager
        config_manager = get_config_manager()
        
        self.model_name = config_manager.get("models.transformer.model_name", "dbmdz/bert-base-italian-xxl-cased")
        self.max_length = config_manager.get("models.transformer.max_length", 512)
        self.batch_size = config_manager.get("models.transformer.batch_size", 16)
        self.device = config_manager.get("models.transformer.device", -1)  # -1 per CPU, >= 0 per specifico GPU ID
        self.quantization = config_manager.get("models.transformer.quantization", False)
        
        # Ottieni l'entity manager se non fornito
        self.entity_manager = entity_manager or get_entity_manager()
        
        # Costruisci dinamicamente la mappa delle etichette
        self.label_map = self._build_label_map()
        
        # Carica il modello e il tokenizer
        self._load_model(model_path)
    
    def _build_label_map(self) -> Dict[str, Any]:
        """
        Costruisce dinamicamente la mappa delle etichette utilizzando l'entity_manager.
        
        Returns:
            Dizionario che mappa le etichette del modello ai tipi di entità.
        """
        label_map = {}
        
        # Ottieni tutti i tipi di entità dall'entity manager
        entity_types = self.entity_manager.get_all_entities()
        
        for entity_type in entity_types:
            # Crea le etichette B- e I- per ogni tipo di entità
            begin_label = f"B-{entity_type.name}"
            inside_label = f"I-{entity_type.name}"
            
            # Mappa le etichette all'oggetto EntityType
            label_map[begin_label] = entity_type
            label_map[inside_label] = entity_type
        
        logger.info(f"Costruita mappa di etichette dinamica con {len(entity_types)} tipi di entità")
        return label_map
    
    def _load_model(self, model_path: Optional[str] = None):
        """
        Carica il modello transformer e il tokenizer.
        
        Args:
            model_path: Percorso a un modello personalizzato (opzionale)
                       Se fornito, carica il modello da questo percorso
                       altrimenti cerca un modello locale o usa quello base
        """
        config_manager = get_config_manager()
        
        try:
            if model_path:
                # Carica il modello dal percorso specificato
                logger.info(f"Caricamento del modello da {model_path}")
                self.tokenizer = AutoTokenizer.from_pretrained(model_path)
                
                # Configura le opzioni di quantizzazione se richiesto
                if self.quantization and self.device == -1:
                    logger.info("Applicazione della quantizzazione al modello")
                    self.model = AutoModelForTokenClassification.from_pretrained(
                        model_path,
                        quantization_config={"load_in_8bit": True}
                    )
                else:
                    self.model = AutoModelForTokenClassification.from_pretrained(model_path)
                
                # Crea la pipeline di NER
                self.ner_pipeline = pipeline(
                    "token-classification",
                    model=self.model,
                    tokenizer=self.tokenizer,
                    aggregation_strategy="simple",
                    device=self.device
                )
                
                logger.info(f"Modello caricato da {model_path}")
                
            else:
                # Controlla se esiste un modello fine-tuned
                default_model_dir = config_manager.get_model_path('transformer')
                
                if default_model_dir and os.path.exists(default_model_dir):
                    logger.info(f"Caricamento del modello fine-tuned da {default_model_dir}")
                    self.tokenizer = AutoTokenizer.from_pretrained(default_model_dir)
                    
                    # Configura le opzioni di quantizzazione se richiesto
                    if self.quantization and self.device == -1:
                        logger.info("Applicazione della quantizzazione al modello")
                        self.model = AutoModelForTokenClassification.from_pretrained(
                            default_model_dir,
                            quantization_config={"load_in_8bit": True}
                        )
                    else:
                        self.model = AutoModelForTokenClassification.from_pretrained(default_model_dir)
                    
                    # Crea la pipeline di NER
                    self.ner_pipeline = pipeline(
                        "token-classification",
                        model=self.model,
                        tokenizer=self.tokenizer,
                        aggregation_strategy="simple",
                        device=self.device
                    )
                    
                    logger.info("Modello fine-tuned caricato con successo")
                else:
                    # Carica il modello base
                    logger.info(f"Modello fine-tuned non trovato. Caricamento del modello base {self.model_name}")
                    self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                    
                    # Configura le opzioni di quantizzazione se richiesto
                    if self.quantization and self.device == -1:
                        logger.info("Applicazione della quantizzazione al modello")
                        self.model = AutoModelForTokenClassification.from_pretrained(
                            self.model_name,
                            quantization_config={"load_in_8bit": True}
                        )
                    else:
                        self.model = AutoModelForTokenClassification.from_pretrained(self.model_name)
                    
                    # Crea la pipeline di NER
                    self.ner_pipeline = pipeline(
                        "token-classification",
                        model=self.model,
                        tokenizer=self.tokenizer,
                        aggregation_strategy="simple",
                        device=self.device
                    )
                    
                    logger.warning("Modello base caricato. Le prestazioni potrebbero non essere ottimali per il riconoscimento di entità giuridiche.")
                    logger.info("Si consiglia di eseguire il fine-tuning del modello con dati specifici del dominio giuridico.")
        
        except Exception as e:
            logger.error(f"Errore nel caricamento del modello: {e}")
            logger.warning("Riconoscitore transformer disabilitato a causa di errori nel caricamento del modello.")
            self.ner_pipeline = None
            self.model = None
            self.tokenizer = None
    
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
            
            # Ottieni l'ID del tipo di entità
            entity_type_id = None
            
            # Se è un'etichetta riconosciuta nella mappa
            if label in self.label_map:
                entity_type = self.label_map[label]
                # Se entity_type è un oggetto EntityType, ottieni il suo ID
                if hasattr(entity_type, 'id'):
                    entity_type_id = entity_type.id
                else:
                    # Se non è un oggetto EntityType ma una stringa o altro
                    logger.warning(f"Etichetta {label} non corrisponde a un EntityType valido")
                    # Estrai il nome dell'entità dall'etichetta (rimuovendo il prefisso B-/I-)
                    entity_name = label.split('-')[-1]
                    # Cerca l'entità per nome
                    found_entity = self.entity_manager.get_entity_by_name(entity_name)
                    if found_entity:
                        entity_type_id = found_entity.id
                    else:
                        # Salta questa entità se non possiamo trovare un ID valido
                        logger.warning(f"Impossibile trovare un tipo di entità per l'etichetta {label}")
                        continue
            else:
                # Estrai il nome dell'entità dall'etichetta (rimuovendo il prefisso B-/I-)
                entity_name = label.split('-')[-1]
                # Cerca l'entità per nome
                found_entity = self.entity_manager.get_entity_by_name(entity_name)
                if found_entity:
                    entity_type_id = found_entity.id
                else:
                    # Salta questa entità se non possiamo trovare un ID valido
                    logger.warning(f"Impossibile trovare un tipo di entità per l'etichetta {label}")
                    continue
            
            # Crea l'entità
            entity = Entity(
                id=f"ner-{start_char}-{end_char}",
                text=entity_text,
                type_id=entity_type_id,
                start_char=start_char,
                end_char=end_char,
                normalized_text=None,  # Sarà normalizzato in seguito
                metadata={
                    "label": label,
                    "score": score
                },
                confidence=score
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
