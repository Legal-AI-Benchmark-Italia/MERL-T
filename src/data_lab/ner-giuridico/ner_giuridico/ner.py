"""
Modulo principale unificato per il riconoscimento di entità giuridiche (NER-Giuridico).
Implementa la pipeline completa di riconoscimento e normalizzazione con supporto
per entità dinamiche.
"""

import logging
from typing import List, Dict, Any, Optional, Union, Tuple, Type, Protocol

from .config import config
from .entities.entities import Entity
from .preprocessing import TextPreprocessor
from .rule_based import RuleBasedRecognizer
from .transformer import TransformerRecognizer
from .normalizer import EntityNormalizer
from .entities.entity_manager import get_entity_manager, EntityType

logger = logging.getLogger(__name__)

class NERCore(Protocol):
    """Protocollo per la funzionalità core di un sistema NER"""
    def process(self, text: str) -> Dict[str, Any]:
        """Processa un testo"""
        ...
        
    def batch_process(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Processa un batch di testi"""
        ...

class BaseNERGiuridico:
    """
    Classe base per il riconoscimento di entità giuridiche.
    Implementa la pipeline generica di preprocessing, riconoscimento e normalizzazione.
    """
    
    def __init__(self, preprocessor=None, rule_recognizer=None, 
                transformer_recognizer=None, normalizer=None, entity_manager=None):
        """
        Inizializza il sistema NER-Giuridico con componenti configurabili.
        
        Args:
            preprocessor: Preprocessore di testo (opzionale)
            rule_recognizer: Riconoscitore basato su regole (opzionale)
            transformer_recognizer: Riconoscitore basato su transformer (opzionale)
            normalizer: Normalizzatore di entità (opzionale)
            entity_manager: Gestore delle entità (opzionale)
        """
        logger.info("Inizializzazione del sistema NER-Giuridico base")
        
        # Inizializza i componenti
        self.preprocessor = preprocessor or TextPreprocessor()
        self.rule_based_recognizer = rule_recognizer or self._create_rule_recognizer()
        self.transformer_recognizer = transformer_recognizer or self._create_transformer_recognizer()
        self.normalizer = normalizer or self._create_normalizer()
        
        logger.info("Sistema NER-Giuridico base inizializzato con successo")
    
    def _create_rule_recognizer(self) -> RuleBasedRecognizer:
        """
        Factory method per il riconoscitore basato su regole.
        
        Returns:
            Istanza di RuleBasedRecognizer
        """
        return RuleBasedRecognizer()
        
    def _create_transformer_recognizer(self) -> TransformerRecognizer:
        """
        Factory method per il riconoscitore basato su transformer.
        
        Returns:
            Istanza di TransformerRecognizer
        """
        return TransformerRecognizer()
        
    def _create_normalizer(self) -> EntityNormalizer:
        """
        Factory method per il normalizzatore di entità.
        
        Returns:
            Istanza di EntityNormalizer
        """
        return EntityNormalizer()
    
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
        structured_references = self._create_structured_references(normalized_entities)
        
        # Prepara il risultato
        result = {
            "text": text,
            "entities": [entity.to_dict() for entity in normalized_entities],
            "references": structured_references
        }
        
        logger.info(f"Riconosciute {len(normalized_entities)} entità")
        
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
        if not transformer_entities:
            return rule_entities
        if not rule_entities:
            return transformer_entities
        
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
    
    def _create_structured_references(self, entities: List[Entity]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Crea riferimenti strutturati dalle entità normalizzate.
        Questa implementazione base delega al normalizzatore.
        
        Args:
            entities: Lista di entità normalizzate.
            
        Returns:
            Dizionario di riferimenti strutturati per categoria.
        """
        # Delega al normalizzatore per creare riferimenti strutturati
        if hasattr(self.normalizer, 'create_structured_references'):
            structured_refs = self.normalizer.create_structured_references(entities)
            
            # Converti in dizionari serializzabili
            result = {}
            for category, refs in structured_refs.items():
                result[category] = [ref.to_dict() if hasattr(ref, 'to_dict') else ref for ref in refs]
            return result
        
        # Implementazione di fallback
        references = {
            "normative": [],
            "jurisprudence": [],
            "concepts": []
        }
        
        for entity in entities:
            entity_dict = entity.to_dict()
            entity_type = getattr(entity.type, "name", str(entity.type))
            
            # Classifica in base al tipo
            if hasattr(EntityType, "get_normative_types") and entity.type in EntityType.get_normative_types():
                references["normative"].append(entity_dict)
            elif hasattr(EntityType, "get_jurisprudence_types") and entity.type in EntityType.get_jurisprudence_types():
                references["jurisprudence"].append(entity_dict)
            elif hasattr(EntityType, "get_concept_types") and entity.type in EntityType.get_concept_types():
                references["concepts"].append(entity_dict)
            else:
                # Aggiungi alla categoria appropriata in base al nome del tipo
                if "ARTICOLO" in entity_type or "LEGGE" in entity_type or "DECRETO" in entity_type or "REGOLAMENTO" in entity_type:
                    references["normative"].append(entity_dict)
                elif "SENTENZA" in entity_type or "ORDINANZA" in entity_type:
                    references["jurisprudence"].append(entity_dict)
                elif "CONCETTO" in entity_type:
                    references["concepts"].append(entity_dict)
                else:
                    # Se non è possibile determinare la categoria, aggiungi a "custom"
                    if "custom" not in references:
                        references["custom"] = []
                    references["custom"].append(entity_dict)
        
        return references
        
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


class NERGiuridico(BaseNERGiuridico):
    """
    Classe principale per il riconoscimento di entità giuridiche.
    Implementa la pipeline completa con supporto per `EntityType` statico.
    """
    
    def __init__(self, **kwargs):
        """Inizializza il sistema NER con supporto per EntityType."""
        logger.info("Inizializzazione del sistema NER-Giuridico standard")
        
        super().__init__(**kwargs)
        
        logger.info("Sistema NER-Giuridico standard inizializzato con successo")


class DynamicNERGiuridico(BaseNERGiuridico):
    """
    Versione della classe NERGiuridico che utilizza il DynamicEntityManager
    per gestire i tipi di entità in modo dinamico.
    """
    
    def __init__(self, entities_file: Optional[str] = None, **kwargs):
        """
        Inizializza il sistema NER-Giuridico con gestione dinamica delle entità.
        
        Args:
            entities_file: Percorso al file JSON contenente le definizioni delle entità
            **kwargs: Argomenti addizionali per la classe base
        """
        logger.info("Inizializzazione del sistema NER-Giuridico con gestione dinamica delle entità")
        
        # Inizializza il gestore delle entità
        self.entity_manager = kwargs.pop('entity_manager', None) or get_entity_manager(entities_file)
        
        # Passa il gestore delle entità ai componenti se supportato
        rule_recognizer = kwargs.get('rule_recognizer')
        if not rule_recognizer and hasattr(RuleBasedRecognizer, '__init__') and 'entity_manager' in RuleBasedRecognizer.__init__.__code__.co_varnames:
            kwargs['rule_recognizer'] = RuleBasedRecognizer(entity_manager=self.entity_manager)
            
        normalizer = kwargs.get('normalizer')
        if not normalizer and hasattr(EntityNormalizer, '__init__') and 'entity_manager' in EntityNormalizer.__init__.__code__.co_varnames:
            kwargs['normalizer'] = EntityNormalizer(entity_manager=self.entity_manager)
        
        # Inizializza la classe base
        super().__init__(**kwargs)
        
        # Cache per le entità dinamiche
        self._entity_cache = {}
        
        logger.info("Sistema NER-Giuridico con gestione dinamica delle entità inizializzato con successo")
    
    def _create_rule_recognizer(self) -> RuleBasedRecognizer:
        """
        Factory method per il riconoscitore basato su regole.
        
        Returns:
            Istanza di RuleBasedRecognizer configurata con il gestore delle entità
        """
        if hasattr(RuleBasedRecognizer, '__init__') and 'entity_manager' in RuleBasedRecognizer.__init__.__code__.co_varnames:
            return RuleBasedRecognizer(entity_manager=self.entity_manager)
        return RuleBasedRecognizer()
    
    def _create_normalizer(self) -> EntityNormalizer:
        """
        Factory method per il normalizzatore di entità.
        
        Returns:
            Istanza di EntityNormalizer configurata con il gestore delle entità
        """
        if hasattr(EntityNormalizer, '__init__') and 'entity_manager' in EntityNormalizer.__init__.__code__.co_varnames:
            return EntityNormalizer(entity_manager=self.entity_manager)
        return EntityNormalizer()
    
    def add_entity_type(self, name: str, display_name: str, category: str, 
                       color: str, metadata_schema: Dict[str, str], patterns: List[str] = None) -> bool:
        """
        Aggiunge un nuovo tipo di entità al sistema.
        
        Args:
            name: Nome identificativo dell'entità (in maiuscolo)
            display_name: Nome visualizzato dell'entità
            category: Categoria dell'entità
            color: Colore dell'entità in formato esadecimale
            metadata_schema: Schema dei metadati dell'entità
            patterns: Pattern regex per il riconoscimento (opzionale)
            
        Returns:
            True se l'aggiunta è avvenuta con successo, False altrimenti
        """
        # Aggiungi l'entità al gestore
        success = self.entity_manager.add_entity_type(
            name=name,
            display_name=display_name,
            category=category,
            color=color,
            metadata_schema=metadata_schema,
            patterns=patterns
        )
        
        if success:
            # Invalida la cache
            if name in self._entity_cache:
                del self._entity_cache[name]
            
            # Aggiorna i pattern nel riconoscitore basato su regole se supportato
            if patterns and hasattr(self.rule_based_recognizer, 'update_patterns'):
                self.rule_based_recognizer.update_patterns(name, patterns)
        
        return success
    
    def update_entity_type(self, name: str, display_name: Optional[str] = None, 
                          color: Optional[str] = None, 
                          metadata_schema: Optional[Dict[str, str]] = None,
                          patterns: Optional[List[str]] = None) -> bool:
        """
        Aggiorna un tipo di entità esistente.
        
        Args:
            name: Nome identificativo dell'entità
            display_name: Nuovo nome visualizzato (opzionale)
            color: Nuovo colore (opzionale)
            metadata_schema: Nuovo schema dei metadati (opzionale)
            patterns: Nuovi pattern regex (opzionale)
            
        Returns:
            True se l'aggiornamento è avvenuto con successo, False altrimenti
        """
        # Aggiorna l'entità nel gestore
        success = self.entity_manager.update_entity_type(
            name=name,
            display_name=display_name,
            color=color,
            metadata_schema=metadata_schema,
            patterns=patterns
        )
        
        if success:
            # Invalida la cache
            if name in self._entity_cache:
                del self._entity_cache[name]
            
            # Aggiorna i pattern nel riconoscitore basato su regole se supportato
            if patterns and hasattr(self.rule_based_recognizer, 'update_patterns'):
                self.rule_based_recognizer.update_patterns(name, patterns)
        
        return success
    
    def remove_entity_type(self, name: str) -> bool:
        """
        Rimuove un tipo di entità dal sistema.
        
        Args:
            name: Nome identificativo dell'entità
            
        Returns:
            True se la rimozione è avvenuta con successo, False altrimenti
        """
        # Rimuovi l'entità dal gestore
        success = self.entity_manager.remove_entity_type(name)
        
        if success:
            # Invalida la cache
            if name in self._entity_cache:
                del self._entity_cache[name]
            
            # Rimuovi i pattern dal riconoscitore basato su regole se supportato
            if hasattr(self.rule_based_recognizer, 'update_patterns'):
                self.rule_based_recognizer.update_patterns(name, [])
        
        return success
    
    def get_entity_types(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Ottiene tutti i tipi di entità, opzionalmente filtrati per categoria.
        
        Args:
            category: Categoria delle entità (opzionale)
            
        Returns:
            Lista di dizionari con informazioni sui tipi di entità
        """
        result = []
        
        if category:
            # Filtra per categoria
            entity_names = self.entity_manager.get_entity_types_by_category(category)
            for name in entity_names:
                entity_info = self.entity_manager.get_entity_type(name)
                if entity_info:
                    result.append({
                        "name": name,
                        **entity_info
                    })
        else:
            # Ottieni tutte le entità
            for name, info in self.entity_manager.get_all_entity_types().items():
                result.append({
                    "name": name,
                    **info
                })
        
        return result