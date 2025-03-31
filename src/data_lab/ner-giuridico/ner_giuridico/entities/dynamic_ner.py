"""
Modulo per l'integrazione della gestione dinamica delle entità nel sistema NER.
Questo modulo modifica la classe NERGiuridico per utilizzare il nuovo 
DynamicEntityManager invece dell'enumerazione EntityType fissa.

Funzionalità principali:
- Sostituzione dell'enumerazione EntityType con la classe DynamicEntity
- Integrazione con DynamicEntityManager per la gestione delle entità
- Conversione tra il sistema basato su enum e il sistema dinamico
- Supporto per l'aggiunta, modifica e rimozione di entità a runtime
"""

import logging
from typing import List, Dict, Any, Optional, Union, Set

from .entity_manager import get_entity_manager
from .entities import Entity
from ..preprocessing import TextPreprocessor
from ..rule_based import RuleBasedRecognizer
from ..transformer import TransformerRecognizer
from ..normalizer import EntityNormalizer

class DynamicEntity:
    """
    Classe sostitutiva per l'enumerazione EntityType, che rappresenta
    un'entità come un oggetto con attributi anziché come un valore enum.
    """
    
    def __init__(self, name: str, display_name: str, category: str, color: str):
        """
        Inizializza un'entità dinamica.
        
        Args:
            name: Nome identificativo dell'entità (es. "ARTICOLO_CODICE")
            display_name: Nome visualizzato dell'entità (es. "Articolo di Codice")
            category: Categoria dell'entità (es. "normative")
            color: Colore dell'entità in formato esadecimale (es. "#FFA39E")
        """
        self.name = name
        self.display_name = display_name
        self.category = category
        self.color = color
    
    def __eq__(self, other):
        """
        Confronta due entità.
        
        Args:
            other: Entità da confrontare
            
        Returns:
            True se le entità sono uguali, False altrimenti
        """
        if isinstance(other, DynamicEntity):
            return self.name == other.name
        elif isinstance(other, str):
            return self.name == other
        return False
    
    def __hash__(self):
        """
        Calcola l'hash dell'entità.
        
        Returns:
            Hash dell'entità
        """
        return hash(self.name)
    
    def __str__(self):
        """
        Restituisce la rappresentazione testuale dell'entità.
        
        Returns:
            Nome dell'entità
        """
        return self.name
    
    def __repr__(self):
        """
        Restituisce la rappresentazione dell'entità.
        
        Returns:
            Rappresentazione dell'entità
        """
        return f"DynamicEntity({self.name}, {self.category})"

class DynamicNERGiuridico:
    """
    Versione della classe NERGiuridico che utilizza il DynamicEntityManager
    per gestire i tipi di entità in modo dinamico.
    
    Questa classe estende il sistema NER originale consentendo di:
    - Aggiungere nuovi tipi di entità a runtime
    - Modificare le proprietà dei tipi di entità esistenti
    - Utilizzare configurazioni di entità caricate da file JSON
    - Supportare pipeline di riconoscimento flessibili
    """
    
    def __init__(self, entities_file: Optional[str] = None):
        """
        Inizializza il sistema NER-Giuridico con gestione dinamica delle entità.
        
        Args:
            entities_file: Percorso al file JSON contenente le definizioni delle entità
        """
        self.logger = logging.getLogger("NER-Giuridico.DynamicNER")
        self.logger.info("Inizializzazione del sistema NER-Giuridico con gestione dinamica delle entità")
        
        # Inizializza il gestore delle entità
        self.entity_manager = get_entity_manager(entities_file)
        
        # Inizializza i componenti della pipeline
        self.preprocessor = TextPreprocessor()
        self.rule_based_recognizer = self._initialize_rule_recognizer()
        self.transformer_recognizer = self._initialize_transformer_recognizer()
        self.normalizer = self._initialize_normalizer()
        
        # Cache per le DynamicEntity
        self._entity_cache = {}
        
        self.logger.info("Sistema NER-Giuridico inizializzato con successo")
    
    def _initialize_rule_recognizer(self) -> RuleBasedRecognizer:
        """
        Inizializza il riconoscitore basato su regole con il supporto per le entità dinamiche.
        
        Returns:
            Istanza di RuleBasedRecognizer configurata
        """
        # Qui puoi estendere il RuleBasedRecognizer per supportare le entità dinamiche
        # Per ora, utilizziamo il riconoscitore standard
        return RuleBasedRecognizer()
    
    def _initialize_transformer_recognizer(self) -> TransformerRecognizer:
        """
        Inizializza il riconoscitore basato su transformer con il supporto per le entità dinamiche.
        
        Returns:
            Istanza di TransformerRecognizer configurata
        """
        # Qui puoi estendere il TransformerRecognizer per supportare le entità dinamiche
        # Per ora, utilizziamo il riconoscitore standard
        return TransformerRecognizer()
    
    def _initialize_normalizer(self) -> EntityNormalizer:
        """
        Inizializza il normalizzatore di entità con il supporto per le entità dinamiche.
        
        Returns:
            Istanza di EntityNormalizer configurata
        """
        # Qui puoi estendere l'EntityNormalizer per supportare le entità dinamiche
        # Per ora, utilizziamo il normalizzatore standard
        return EntityNormalizer()
    
    def _get_entity_type(self, name: str) -> DynamicEntity:
        """
        Ottiene un'istanza di DynamicEntity dal nome.
        
        Args:
            name: Nome del tipo di entità
            
        Returns:
            Istanza di DynamicEntity
        """
        # Verifica se l'entità è già in cache
        if name in self._entity_cache:
            return self._entity_cache[name]
        
        # Altrimenti, ottieni l'entità dal gestore
        entity_info = self.entity_manager.get_entity_type(name)
        if not entity_info:
            # Se l'entità non esiste, restituisci un'entità predefinita
            self.logger.warning(f"L'entità {name} non esiste, utilizzo entità predefinita")
            entity = DynamicEntity(
                name=name,
                display_name=name,
                category="custom",
                color="#CCCCCC"
            )
        else:
            entity = DynamicEntity(
                name=name,
                display_name=entity_info.get("display_name", name),
                category=entity_info.get("category", "custom"),
                color=entity_info.get("color", "#CCCCCC")
            )
        
        # Aggiungi l'entità alla cache
        self._entity_cache[name] = entity
        
        return entity
    
    def process(self, text: str) -> Dict[str, Any]:
        """
        Processa un testo per riconoscere e normalizzare entità giuridiche.
        
        Args:
            text: Testo da processare.
        
        Returns:
            Dizionario con i risultati del riconoscimento.
        """
        self.logger.info(f"Elaborazione di un testo di {len(text)} caratteri")
        
        # Preprocessing del testo
        preprocessed_text, doc = self.preprocessor.preprocess(text)
        
        # Segmentazione del testo (per testi lunghi)
        segments = self.preprocessor.segment_text(preprocessed_text)
        
        # Riconoscimento delle entità
        all_entities = []
        
        for segment in segments:
            # Riconoscimento basato su regole
            rule_entities = self.rule_based_recognizer.recognize(segment)
            
            # Converti le entità dal formato vecchio al formato nuovo
            rule_entities = [self._convert_entity(entity) for entity in rule_entities]
            
            # Riconoscimento basato su transformer
            transformer_entities = self.transformer_recognizer.recognize(segment)
            
            # Converti le entità dal formato vecchio al formato nuovo
            transformer_entities = [self._convert_entity(entity) for entity in transformer_entities]
            
            # Unisci le entità riconosciute
            segment_entities = self._merge_entities(rule_entities, transformer_entities)
            
            # Aggiungi le entità del segmento alla lista completa
            all_entities.extend(segment_entities)
        
        # Rimuovi le entità duplicate o sovrapposte
        unique_entities = self._remove_overlapping_entities(all_entities)
        
        # Normalizzazione delle entità
        normalized_entities = self._normalize_entities(unique_entities)
        
        # Crea riferimenti strutturati
        structured_references = self._create_structured_references(normalized_entities)
        
        # Prepara il risultato
        result = {
            "text": text,
            "entities": [entity.to_dict() for entity in normalized_entities],
            "references": {
                "normative": [ref.to_dict() for ref in structured_references["normative"]],
                "jurisprudence": [ref.to_dict() for ref in structured_references["jurisprudence"]],
                "concepts": [concept.to_dict() for concept in structured_references["concepts"]],
                "custom": [concept.to_dict() for concept in structured_references.get("custom", [])]
            }
        }
        
        self.logger.info(f"Riconosciute {len(normalized_entities)} entità: "
                       f"{len(structured_references['normative'])} normative, "
                       f"{len(structured_references['jurisprudence'])} giurisprudenziali, "
                       f"{len(structured_references['concepts'])} concetti, "
                       f"{len(structured_references.get('custom', []))} personalizzate")
        
        return result
    
    def _convert_entity(self, entity: Entity) -> Entity:
        """
        Converte un'entità dal formato vecchio (con EntityType enum) 
        al formato nuovo (con DynamicEntity).
        
        Args:
            entity: Entità da convertire
            
        Returns:
            Entità convertita
        """
        # Se l'entità è già nel nuovo formato, restituiscila così com'è
        if isinstance(entity.type, DynamicEntity):
            return entity
        
        # Converti il tipo di entità
        entity_type_name = getattr(entity.type, "name", str(entity.type))
        dynamic_entity_type = self._get_entity_type(entity_type_name)
        
        # Crea una nuova entità con il tipo convertito
        return Entity(
            text=entity.text,
            type=dynamic_entity_type,
            start_char=entity.start_char,
            end_char=entity.end_char,
            normalized_text=entity.normalized_text,
            metadata=entity.metadata
        )
    
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
    
    def _normalize_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        Normalizza le entità utilizzando il normalizzatore.
        Adatta la funzione della classe originale per supportare le entità dinamiche.
        
        Args:
            entities: Lista di entità da normalizzare.
            
        Returns:
            Lista di entità normalizzate.
        """
        # Per ora, utilizziamo il normalizzatore standard
        # In futuro, potremmo implementare un normalizzatore personalizzato
        normalized_entities = self.normalizer.normalize(entities)
        
        # Converti le entità normalizzate al formato dinamico
        normalized_entities = [self._convert_entity(entity) for entity in normalized_entities]
        
        return normalized_entities
    
    def _create_structured_references(self, entities: List[Entity]) -> Dict[str, List[Any]]:
        """
        Crea riferimenti strutturati dalle entità normalizzate.
        
        Args:
            entities: Lista di entità normalizzate.
            
        Returns:
            Dizionario di riferimenti strutturati per categoria.
        """
        # Per ora, utilizziamo il normalizzatore standard per creare i riferimenti strutturati
        # In futuro, potremmo implementare un creatore di riferimenti personalizzato
        structured_references = self.normalizer.create_structured_references(entities)
        
        # Aggiungi una categoria "custom" se non esiste
        if "custom" not in structured_references:
            structured_references["custom"] = []
        
        return structured_references
        
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
    
    def add_entity_type(self, name: str, display_name: str, category: str, 
                       color: str, metadata_schema: Dict[str, str]) -> bool:
        """
        Aggiunge un nuovo tipo di entità al sistema.
        
        Args:
            name: Nome identificativo dell'entità (in maiuscolo)
            display_name: Nome visualizzato dell'entità
            category: Categoria dell'entità
            color: Colore dell'entità in formato esadecimale
            metadata_schema: Schema dei metadati dell'entità
            
        Returns:
            True se l'aggiunta è avvenuta con successo, False altrimenti
        """
        # Aggiungi l'entità al gestore
        success = self.entity_manager.add_entity_type(
            name=name,
            display_name=display_name,
            category=category,
            color=color,
            metadata_schema=metadata_schema
        )
        
        if success:
            # Invalida la cache
            if name in self._entity_cache:
                del self._entity_cache[name]
                
            # Salva le entità
            self.entity_manager.save_entities("config/entities.json")
        
        return success
    
    def update_entity_type(self, name: str, display_name: Optional[str] = None, 
                        category: Optional[str] = None, color: Optional[str] = None, 
                        metadata_schema: Optional[Dict[str, str]] = None,
                        patterns: Optional[List[str]] = None) -> bool:
        """
        Aggiorna un tipo di entità esistente.
        
        Args:
            name: Nome identificativo dell'entità
            display_name: Nuovo nome visualizzato (opzionale)
            category: Nuova categoria (opzionale)
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
            category=category,
            color=color,
            metadata_schema=metadata_schema,
            patterns=patterns
        )
        
        if success:
            # Invalida la cache
            if name in self._entity_cache:
                del self._entity_cache[name]
                
            # Salva le entità
            self.entity_manager.save_entities("config/entities.json")
        
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
                
            # Salva le entità
            self.entity_manager.save_entities("config/entities.json")
        
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