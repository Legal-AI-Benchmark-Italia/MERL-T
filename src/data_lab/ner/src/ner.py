"""
Modulo principale per il riconoscimento di entità giuridiche (NER-Giuridico).
Implementa la pipeline completa di riconoscimento e normalizzazione.
"""

import logging
from typing import List, Dict, Any, Optional, Union, Tuple

from .config import config
from .entities.entities import Entity, EntityType, NormativeReference, JurisprudenceReference, LegalConcept
from .preprocessing import TextPreprocessor
from .rule_based import RuleBasedRecognizer
from .transformer import TransformerRecognizer
from .normalizer import EntityNormalizer
from .entities.entity_manager import get_entity_manager

logger = logging.getLogger(__name__)

class NERGiuridico:
    """
    Classe principale per il riconoscimento di entità giuridiche.
    Implementa la pipeline completa di preprocessing, riconoscimento e normalizzazione.
    """
    
    def __init__(self):
        """Inizializza il sistema NER-Giuridico."""
        logger.info("Inizializzazione del sistema NER-Giuridico")
        
        # Inizializza il gestore delle entità dinamiche
        self.entity_manager = get_entity_manager()
        
        # Inizializza i componenti della pipeline
        self.preprocessor = TextPreprocessor()
        self.rule_based_recognizer = RuleBasedRecognizer(self.entity_manager)
        self.transformer_recognizer = TransformerRecognizer()
        self.normalizer = EntityNormalizer()
        
        logger.info("Sistema NER-Giuridico inizializzato con successo")
    
    def process(self, text: str) -> Dict[str, Any]:
        """
        Processa un testo per riconoscere e normalizzare entità giuridiche.
        
        Args:
            text: Testo da processare.
        
        Returns:
            Dizionario con i risultati del riconoscimento.
        """
        logger.info(f"Elaborazione di un testo di {len(text)} caratteri")
        
        # Preprocessing del testo
        preprocessed_text, doc = self.preprocessor.preprocess(text)
        
        # Segmentazione del testo (per testi lunghi)
        segments = self.preprocessor.segment_text(preprocessed_text)
        
        # Riconoscimento delle entità
        all_entities = []
        
        for segment in segments:
            # Riconoscimento basato su regole
            rule_entities = self.rule_based_recognizer.recognize(segment)
            
            # Riconoscimento basato su transformer
            transformer_entities = self.transformer_recognizer.recognize(segment)
            
            # Unisci le entità riconosciute
            segment_entities = self._merge_entities(rule_entities, transformer_entities)
            
            # Aggiungi le entità del segmento alla lista completa
            all_entities.extend(segment_entities)
        
        # Rimuovi le entità duplicate o sovrapposte
        unique_entities = self._remove_overlapping_entities(all_entities)
        
        # Normalizzazione delle entità
        normalized_entities = self.normalizer.normalize(unique_entities)
        
        # Crea riferimenti strutturati
        structured_references = self.normalizer.create_structured_references(normalized_entities)
        
        # Prepara il risultato
        result = {
            "text": text,
            "entities": [entity.to_dict() for entity in normalized_entities],
            "references": {
                "normative": [ref.to_dict() for ref in structured_references["normative"]],
                "jurisprudence": [ref.to_dict() for ref in structured_references["jurisprudence"]],
                "concepts": [concept.to_dict() for concept in structured_references["concepts"]]
            }
        }
        
        logger.info(f"Riconosciute {len(normalized_entities)} entità: "
                   f"{len(structured_references['normative'])} normative, "
                   f"{len(structured_references['jurisprudence'])} giurisprudenziali, "
                   f"{len(structured_references['concepts'])} concetti")
        
        return result
    
    def _merge_entities(self, rule_entities: List[Entity], transformer_entities: List[Entity]) -> List[Entity]:
        """
        Unisce le entità riconosciute dai diversi riconoscitori, dando priorità a quelle
        con punteggio più alto o a quelle riconosciute da regole in caso di conflitto.
        
        Args:
            rule_entities: Entità riconosciute dal riconoscitore basato su regole.
            transformer_entities: Entità riconosciute dal riconoscitore basato su transformer.
        
        Returns:
            Lista unificata di entità.
        """
        # Se uno dei riconoscitori non ha trovato entità, restituisci le entità dell'altro
        if not rule_entities:
            return transformer_entities
        if not transformer_entities:
            return rule_entities
        
        # Crea una mappa delle entità transformer per posizione
        transformer_map = {}
        for entity in transformer_entities:
            key = (entity.start_char, entity.end_char)
            transformer_map[key] = entity
        
        merged_entities = []
        
        # Aggiungi tutte le entità rule-based
        for rule_entity in rule_entities:
            key = (rule_entity.start_char, rule_entity.end_char)
            
            # Se c'è un'entità transformer nella stessa posizione
            if key in transformer_map:
                transformer_entity = transformer_map[key]
                
                # Se i tipi sono diversi, mantieni entrambe
                if rule_entity.type != transformer_entity.type:
                    merged_entities.append(rule_entity)
                    merged_entities.append(transformer_entity)
                else:
                    # Altrimenti, mantieni quella rule-based (più affidabile)
                    merged_entities.append(rule_entity)
                
                # Rimuovi l'entità transformer dalla mappa
                del transformer_map[key]
            else:
                # Se non c'è conflitto, aggiungi l'entità rule-based
                merged_entities.append(rule_entity)
        
        # Aggiungi le entità transformer rimanenti
        merged_entities.extend(transformer_map.values())
        
        return merged_entities
    
    def _remove_overlapping_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        Rimuove le entità sovrapposte, mantenendo quelle con span più lungo
        o con punteggio più alto in caso di conflitto.
        
        Args:
            entities: Lista di entità potenzialmente sovrapposte.
        
        Returns:
            Lista di entità senza sovrapposizioni.
        """
        if not entities:
            return []
        
        # Ordina le entità per posizione di inizio e lunghezza (decrescente)
        sorted_entities = sorted(
            entities,
            key=lambda e: (e.start_char, -len(e.text))
        )
        
        unique_entities = []
        last_end = -1
        
        for entity in sorted_entities:
            # Se l'entità inizia dopo la fine dell'ultima entità aggiunta,
            # non c'è sovrapposizione
            if entity.start_char >= last_end:
                unique_entities.append(entity)
                last_end = entity.end_char
            else:
                # Se c'è sovrapposizione, controlla se l'entità corrente è più lunga
                # dell'ultima entità aggiunta
                if entity.end_char > last_end:
                    # Se l'entità corrente è più lunga, sostituisci l'ultima entità
                    # con quella corrente
                    unique_entities[-1] = entity
                    last_end = entity.end_char
        
        return unique_entities
    
    def batch_process(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Processa un batch di testi.
        
        Args:
            texts: Lista di testi da processare.
        
        Returns:
            Lista di risultati del riconoscimento.
        """
        results = []
        
        for text in texts:
            result = self.process(text)
            results.append(result)
        
        return results
