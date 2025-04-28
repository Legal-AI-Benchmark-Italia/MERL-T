"""
Sistema NER unificato per il riconoscimento delle entità giuridiche.
Supporta l'addestramento con documenti nel formato Spacy e l'integrazione nella fase di preprocessing.
"""

import logging
import json
import uuid
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Union, Tuple

import spacy
from spacy.tokens import Doc
from spacy.training import Example

# Aggiungiamo il percorso root al PYTHONPATH
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)

from src.core.config import get_config_manager
from src.core.entities.entity_manager import get_entity_manager, EntityType
from src.core.entities.entities import Entity
from .preprocessing import TextPreprocessor
from .transformer import TransformerRecognizer
from .normalizer import EntityNormalizer

class NERSystem:
    """
    Sistema NER unificato per il riconoscimento delle entità giuridiche.
    Utilizza un modello transformer e supporta l'addestramento con dati annotati.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Inizializza il sistema NER.
        
        Args:
            db_path: Percorso al file del database SQLite (opzionale)
        """
        self.logger = logging.getLogger("NER-Giuridico.NERSystem")
        
        # Ottieni la configurazione dal ConfigManager
        self.config_manager = get_config_manager()
        
        # Ottieni il gestore delle entità
        self.entity_manager = get_entity_manager(db_path)
        
        # Inizializza i componenti
        self._init_components()
        
        self.logger.info("Sistema NER inizializzato con successo")
    
    def _init_components(self):
        """Inizializza i componenti del sistema."""
        # Preprocessore per il testo
        self.preprocessor = TextPreprocessor()
        
        # Riconoscitore basato su transformer
        try:
            self.transformer_recognizer = TransformerRecognizer(entity_manager=self.entity_manager)
        except Exception as e:
            self.logger.error(f"Impossibile inizializzare il riconoscitore transformer: {e}")
            self.transformer_recognizer = None
        
        # Normalizzatore per le entità
        self.normalizer = EntityNormalizer(self.entity_manager)
    
    def process(self, text: str) -> Dict[str, Any]:
        """
        Processa un testo per riconoscere entità giuridiche.
        
        Args:
            text: Testo da processare
            
        Returns:
            Risultati del riconoscimento
        """
        self.logger.info(f"Elaborazione di un testo di {len(text)} caratteri")
        
        # Preprocessa il testo
        preprocessed_text, doc = self.preprocessor.preprocess(text)
        
        # Riconosci le entità con il riconoscitore transformer
        entities = []
        if self.transformer_recognizer:
            entities = self.transformer_recognizer.recognize(preprocessed_text)
        else:
            self.logger.warning("Riconoscitore transformer non disponibile")
        
        # Rimuovi le entità sovrapposte
        entities = self._remove_overlapping_entities(entities)
        
        # Normalizza le entità
        normalized_entities = self.normalizer.normalize(entities)
        
        # Crea riferimenti strutturati
        structured_references = self.normalizer.create_structured_references(normalized_entities)
        
        # Formatta il risultato
        result = {
            "text": text,
            "entities": [entity.to_dict() for entity in normalized_entities],
            "structured_references": structured_references
        }
        
        return result
    
    def _remove_overlapping_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        Rimuove le entità sovrapposte, mantenendo quelle con il punteggio di confidenza più alto.
        
        Args:
            entities: Lista di entità (potenzialmente sovrapposte)
            
        Returns:
            Lista di entità senza sovrapposizioni
        """
        if not entities:
            return []
        
        # Ordina le entità per punteggio di confidenza (decrescente)
        sorted_entities = sorted(entities, key=lambda e: e.confidence, reverse=True)
        
        # Utilizza un array per tracciare i caratteri occupati
        text_length = max(entity.end_char for entity in entities) + 1
        occupied = [False] * text_length
        
        # Lista delle entità non sovrapposte
        non_overlapping_entities = []
        
        for entity in sorted_entities:
            # Verifica se l'entità si sovrappone a entità già selezionate
            overlap = False
            for i in range(entity.start_char, entity.end_char):
                if i < len(occupied) and occupied[i]:
                    overlap = True
                    break
            
            # Se non c'è sovrapposizione, aggiungi l'entità
            if not overlap:
                non_overlapping_entities.append(entity)
                
                # Marca i caratteri come occupati
                for i in range(entity.start_char, entity.end_char):
                    if i < len(occupied):
                        occupied[i] = True
        
        # Ordina le entità per posizione nel testo
        non_overlapping_entities.sort(key=lambda e: e.start_char)
        
        return non_overlapping_entities
    
    def batch_process(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Processa un batch di testi.
        
        Args:
            texts: Lista di testi da processare
            
        Returns:
            Lista di risultati
        """
        results = []
        for text in texts:
            result = self.process(text)
            results.append(result)
        
        return results
    
    def train(self, training_data: List[Dict[str, Any]], output_dir: str, 
              epochs: int = 5, batch_size: int = 16) -> bool:
        """
        Addestra il modello transformer con dati annotati nel formato Spacy.
        
        Args:
            training_data: Lista di documenti annotati nel formato Spacy
                          (ogni documento è un dizionario con 'text' e 'entities')
            output_dir: Directory dove salvare il modello addestrato
            epochs: Numero di epoche di addestramento
            batch_size: Dimensione del batch
            
        Returns:
            True se l'addestramento è avvenuto con successo, False altrimenti
        """
        if not self.transformer_recognizer:
            self.logger.error("Impossibile addestrare: riconoscitore transformer non disponibile")
            return False
        
        try:
            self.logger.info(f"Inizio addestramento con {len(training_data)} documenti")
            
            # Crea il modello spaCy per l'addestramento
            nlp = spacy.blank("it")
            
            # Aggiungi il componente NER
            ner = nlp.add_pipe("ner")
            
            # Aggiungi le etichette
            for doc in training_data:
                for _, _, label in doc["entities"]:
                    ner.add_label(label)
            
            # Prepara i dati di addestramento
            train_examples = []
            for doc_data in training_data:
                text = doc_data["text"]
                entities = doc_data["entities"]
                
                # Crea il Doc con le entità
                doc = nlp.make_doc(text)
                
                # Aggiungi le entità al doc
                ents = []
                for start, end, label in entities:
                    span = doc.char_span(start, end, label=label)
                    if span:
                        ents.append(span)
                
                doc.ents = ents
                
                # Crea l'esempio
                example = Example.from_dict(doc, {"entities": entities})
                train_examples.append(example)
            
            # Configura l'addestramento
            optimizer = nlp.create_optimizer()
            
            # Esegui l'addestramento
            for epoch in range(epochs):
                losses = {}
                
                # Mescola gli esempi
                import random
                random.shuffle(train_examples)
                
                # Addestra in batch
                for i in range(0, len(train_examples), batch_size):
                    batch = train_examples[i:i+batch_size]
                    nlp.update(batch, drop=0.5, losses=losses, sgd=optimizer)
                
                self.logger.info(f"Epoca {epoch+1}/{epochs}, Loss: {losses}")
            
            # Crea la directory di output se non esiste
            os.makedirs(output_dir, exist_ok=True)
            
            # Salva il modello
            nlp.to_disk(output_dir)
            
            self.logger.info(f"Modello salvato con successo in {output_dir}")
            
            # Aggiorna il riconoscitore transformer con il nuovo modello
            self.transformer_recognizer = TransformerRecognizer(model_path=output_dir, entity_manager=self.entity_manager)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Errore nell'addestramento del modello: {e}")
            return False
    
    def load_training_data(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Carica i dati di addestramento da un file JSON nel formato Spacy.
        
        Args:
            file_path: Percorso al file JSON
            
        Returns:
            Lista di documenti annotati
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Verifica il formato dei dati
            if not isinstance(data, list):
                self.logger.error(f"Formato dati non valido in {file_path}")
                return []
            
            # Verifica che ogni documento abbia le chiavi necessarie
            for doc in data:
                if "text" not in doc or "entities" not in doc:
                    self.logger.error(f"Documento senza testo o entità in {file_path}")
                    return []
            
            self.logger.info(f"Caricati {len(data)} documenti da {file_path}")
            return data
            
        except Exception as e:
            self.logger.error(f"Errore nel caricamento dei dati: {e}")
            return []
    
    def save_model(self, output_dir: str) -> bool:
        """
        Salva il modello trasformer corrente.
        
        Args:
            output_dir: Directory dove salvare il modello
            
        Returns:
            True se il salvataggio è avvenuto con successo, False altrimenti
        """
        if not self.transformer_recognizer or not self.transformer_recognizer.model:
            self.logger.error("Nessun modello transformer disponibile per il salvataggio")
            return False
        
        try:
            # Crea la directory di output se non esiste
            os.makedirs(output_dir, exist_ok=True)
            
            # Salva il modello e il tokenizer
            self.transformer_recognizer.model.save_pretrained(output_dir)
            self.transformer_recognizer.tokenizer.save_pretrained(output_dir)
            
            self.logger.info(f"Modello salvato con successo in {output_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Errore nel salvataggio del modello: {e}")
            return False
    
    def load_model(self, model_dir: str) -> bool:
        """
        Carica un modello transformer salvato.
        
        Args:
            model_dir: Directory contenente il modello
            
        Returns:
            True se il caricamento è avvenuto con successo, False altrimenti
        """
        try:
            # Ricrea il riconoscitore transformer con il modello specifico
            self.transformer_recognizer = TransformerRecognizer(model_path=model_dir, entity_manager=self.entity_manager)
            
            self.logger.info(f"Modello caricato con successo da {model_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Errore nel caricamento del modello: {e}")
            return False 