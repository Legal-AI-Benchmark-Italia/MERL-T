"""
Modulo per la normalizzazione delle entità giuridiche riconosciute dal sistema NER-Giuridico.
Supporta sia entità statiche che dinamiche.
"""

import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple, Callable

from .config import config
from .entities.entities import (
    Entity, EntityType, NormativeReference, 
    JurisprudenceReference, LegalConcept
)
from .entities.entity_manager import get_entity_manager

logger = logging.getLogger(__name__)

class EntityNormalizer:
    """
    Classe per la normalizzazione delle entità giuridiche riconosciute.
    Converte le entità in forme canoniche e arricchisce i metadati.
    Supporta la gestione dinamica delle entità.
    """
    
    def __init__(self, entity_manager=None):
        """
        Inizializza il normalizzatore di entità.
        
        Args:
            entity_manager: Gestore delle entità dinamiche (opzionale)
        """
        self.enable = config.get("normalization.enable", True)
        self.entity_manager = entity_manager
        
        if not self.enable:
            logger.info("Normalizzazione delle entità disabilitata")
            return
        
        # Carica le forme canoniche
        self.canonical_forms = self._load_canonical_forms()
        
        # Carica le abbreviazioni
        self.abbreviations = self._load_abbreviations()
        
        # Configura l'integrazione con il knowledge graph
        self.use_knowledge_graph = config.get("normalization.use_knowledge_graph", False)
        if self.use_knowledge_graph:
            self._setup_knowledge_graph()
            
        # Registro dei normalizzatori per tipo di entità
        self.normalizers = {}
        
        # Registra i normalizzatori predefiniti
        self._register_default_normalizers()
        
        logger.info("Normalizzatore di entità inizializzato con successo")
    
    def _register_default_normalizers(self):
        """Registra i normalizzatori predefiniti per i tipi di entità standard."""
        # Riferimenti normativi
        self.register_normalizer("ARTICOLO_CODICE", self._normalize_article_reference)
        self.register_normalizer("LEGGE", self._normalize_law_reference)
        self.register_normalizer("DECRETO", self._normalize_decree_reference)
        self.register_normalizer("REGOLAMENTO_UE", self._normalize_eu_regulation_reference)
        
        # Riferimenti giurisprudenziali
        self.register_normalizer("SENTENZA", self._normalize_sentence_reference)
        self.register_normalizer("ORDINANZA", self._normalize_ordinance_reference)
        
        # Concetti giuridici
        self.register_normalizer("CONCETTO_GIURIDICO", self._normalize_legal_concept)
    
    def register_normalizer(self, entity_type: str, normalizer_func: Callable[[Entity], Entity]):
        """
        Registra una funzione di normalizzazione per un tipo di entità.
        
        Args:
            entity_type: Nome del tipo di entità
            normalizer_func: Funzione di normalizzazione
        """
        self.normalizers[entity_type] = normalizer_func
        logger.debug(f"Registrato normalizzatore per {entity_type}")
    
    def _load_canonical_forms(self) -> Dict[str, Dict[str, Any]]:
        """
        Carica le forme canoniche dal file JSON.
        
        Returns:
            Dizionario di forme canoniche per tipo di entità.
        """
        canonical_forms_file = config.get("normalization.canonical_forms_file", "../data/canonical_forms.json")
        
        # Costruisci il percorso completo
        base_dir = Path(__file__).parent.parent
        file_path = base_dir / canonical_forms_file
        
        canonical_forms = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                canonical_forms = json.load(f)
            
            logger.info(f"Forme canoniche caricate da {file_path}")
        except FileNotFoundError:
            logger.warning(f"File delle forme canoniche {file_path} non trovato. Creazione di forme canoniche predefinite.")
            
            # Crea forme canoniche predefinite
            canonical_forms = self._create_default_canonical_forms()
            
            # Assicurati che la directory esista
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Salva le forme canoniche predefinite
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(canonical_forms, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Forme canoniche predefinite create e salvate in {file_path}")
        
        return canonical_forms
    
    def _create_default_canonical_forms(self) -> Dict[str, Dict[str, Any]]:
        """
        Crea forme canoniche predefinite per i tipi di entità.
        
        Returns:
            Dizionario di forme canoniche predefinite.
        """
        return {
            "codici": {
                "c.c.": "Codice Civile",
                "c.p.": "Codice Penale",
                "c.p.c.": "Codice di Procedura Civile",
                "c.p.p.": "Codice di Procedura Penale",
                "cod. civ.": "Codice Civile",
                "cod. pen.": "Codice Penale",
                "cod. proc. civ.": "Codice di Procedura Civile",
                "cod. proc. pen.": "Codice di Procedura Penale",
                "codice civile": "Codice Civile",
                "codice penale": "Codice Penale",
                "codice di procedura civile": "Codice di Procedura Civile",
                "codice di procedura penale": "Codice di Procedura Penale"
            },
            "autorità": {
                "cass.": "Corte di Cassazione",
                "cassazione": "Corte di Cassazione",
                "corte di cassazione": "Corte di Cassazione",
                "corte cost.": "Corte Costituzionale",
                "corte costituzionale": "Corte Costituzionale",
                "cons. stato": "Consiglio di Stato",
                "consiglio di stato": "Consiglio di Stato",
                "trib.": "Tribunale",
                "tribunale": "Tribunale",
                "corte app.": "Corte d'Appello",
                "corte d'appello": "Corte d'Appello",
                "corte di appello": "Corte d'Appello",
                "tar": "Tribunale Amministrativo Regionale",
                "tribunale amministrativo regionale": "Tribunale Amministrativo Regionale"
            },
            "decreti": {
                "d.lgs.": "Decreto Legislativo",
                "decreto legislativo": "Decreto Legislativo",
                "d.l.": "Decreto Legge",
                "decreto legge": "Decreto Legge",
                "d.p.r.": "Decreto del Presidente della Repubblica",
                "decreto del presidente della repubblica": "Decreto del Presidente della Repubblica",
                "d.m.": "Decreto Ministeriale",
                "decreto ministeriale": "Decreto Ministeriale",
                "d.p.c.m.": "Decreto del Presidente del Consiglio dei Ministri",
                "decreto del presidente del consiglio dei ministri": "Decreto del Presidente del Consiglio dei Ministri"
            },
            "regolamenti_ue": {
                "gdpr": "Regolamento UE 2016/679",
                "regolamento generale sulla protezione dei dati": "Regolamento UE 2016/679"
            }
        }
    
    def _load_abbreviations(self) -> Dict[str, str]:
        """
        Carica le abbreviazioni dal file JSON.
        
        Returns:
            Dizionario di abbreviazioni e loro espansioni.
        """
        abbreviations_file = config.get("normalization.abbreviations_file", "../data/abbreviations.json")
        
        # Costruisci il percorso completo
        base_dir = Path(__file__).parent.parent
        file_path = base_dir / abbreviations_file
        
        abbreviations = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                abbreviations = json.load(f)
            
            logger.info(f"Abbreviazioni caricate da {file_path}")
        except FileNotFoundError:
            logger.warning(f"File delle abbreviazioni {file_path} non trovato. Creazione di abbreviazioni predefinite.")
            
            # Crea abbreviazioni predefinite
            abbreviations = self._create_default_abbreviations()
            
            # Assicurati che la directory esista
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Salva le abbreviazioni predefinite
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(abbreviations, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Abbreviazioni predefinite create e salvate in {file_path}")
        
        return abbreviations
    
    def _create_default_abbreviations(self) -> Dict[str, str]:
        """
        Crea abbreviazioni predefinite.
        
        Returns:
            Dizionario di abbreviazioni predefinite.
        """
        return {
            "art.": "articolo",
            "artt.": "articoli",
            "c.c.": "codice civile",
            "c.p.": "codice penale",
            "c.p.c.": "codice di procedura civile",
            "c.p.p.": "codice di procedura penale",
            "d.lgs.": "decreto legislativo",
            "d.l.": "decreto legge",
            "d.p.r.": "decreto del presidente della repubblica",
            "d.m.": "decreto ministeriale",
            "d.p.c.m.": "decreto del presidente del consiglio dei ministri",
            "l.": "legge",
            "n.": "numero",
            "cass.": "cassazione",
            "sez.": "sezione",
            "sent.": "sentenza",
            "ord.": "ordinanza",
            "trib.": "tribunale",
            "app.": "appello",
            "cost.": "costituzionale",
            "gdpr": "regolamento generale sulla protezione dei dati"
        }
    
    def _setup_knowledge_graph(self):
        """Configura la connessione al knowledge graph Neo4j."""
        try:
            from neo4j import GraphDatabase
            
            # Ottieni le configurazioni di connessione
            url = config.get("normalization.knowledge_graph.url", "bolt://localhost:7687")
            user = config.get("normalization.knowledge_graph.user", "neo4j")
            password = config.get("normalization.knowledge_graph.password", "password")
            
            # Crea il driver per la connessione
            self.neo4j_driver = GraphDatabase.driver(url, auth=(user, password))
            
            # Verifica la connessione
            with self.neo4j_driver.session() as session:
                result = session.run("RETURN 1 AS test")
                test_value = result.single()["test"]
                if test_value == 1:
                    logger.info("Connessione al knowledge graph Neo4j stabilita con successo")
                else:
                    logger.warning("Connessione al knowledge graph Neo4j non riuscita")
                    self.use_knowledge_graph = False
        
        except Exception as e:
            logger.error(f"Errore nella configurazione del knowledge graph: {e}")
            logger.warning("Integrazione con il knowledge graph disabilitata")
            self.use_knowledge_graph = False
    
    def normalize(self, entities: List[Entity]) -> List[Entity]:
        """
        Normalizza le entità riconosciute.
        
        Args:
            entities: Lista di entità da normalizzare.
        
        Returns:
            Lista di entità normalizzate.
        """
        if not self.enable:
            return entities
        
        normalized_entities = []
        
        for entity in entities:
            # Ottieni il tipo di entità come stringa
            entity_type = self._get_entity_type_name(entity.type)
            
            # Cerca un normalizzatore registrato per questo tipo di entità
            if entity_type in self.normalizers:
                normalizer = self.normalizers[entity_type]
                normalized_entity = normalizer(entity)
            else:
                # Se non c'è un normalizzatore specifico, usa uno generico
                if hasattr(entity.type, "name"):
                    # Per i tipi di entità statici (enum)
                    normalized_entity = self._normalize_entity_by_type(entity)
                else:
                    # Per i tipi di entità dinamici (stringa)
                    normalized_entity = self._normalize_generic_entity(entity)
            
            # Arricchisci con dati dal knowledge graph se disponibile
            if self.use_knowledge_graph:
                self._enrich_from_knowledge_graph(normalized_entity)
            
            normalized_entities.append(normalized_entity)
        
        return normalized_entities
    
    def _get_entity_type_name(self, entity_type) -> str:
        """
        Ottiene il nome del tipo di entità come stringa.
        
        Args:
            entity_type: Tipo di entità (enum o stringa)
        
        Returns:
            Nome del tipo di entità
        """
        if isinstance(entity_type, str):
            return entity_type
        if hasattr(entity_type, "name"):
            return entity_type.name
        return str(entity_type)
    
    def _normalize_entity_by_type(self, entity: Entity) -> Entity:
        """
        Normalizza un'entità in base al suo tipo (per entità statiche).
        
        Args:
            entity: Entità da normalizzare
        
        Returns:
            Entità normalizzata
        """
        if entity.type in EntityType.get_normative_types():
            return self._normalize_normative_reference(entity)
        elif entity.type in EntityType.get_jurisprudence_types():
            return self._normalize_jurisprudence_reference(entity)
        elif entity.type in EntityType.get_concept_types():
            return self._normalize_legal_concept(entity)
        else:
            # Se non riconosciamo il tipo, restituisci l'entità così com'è
            return entity
    
    def _normalize_generic_entity(self, entity: Entity) -> Entity:
        """
        Normalizza un'entità in base al suo tipo (per entità dinamiche).
        
        Args:
            entity: Entità da normalizzare
        
        Returns:
            Entità normalizzata
        """
        # Se non c'è un entity manager, restituisci l'entità così com'è
        if not self.entity_manager:
            return entity
        
        # Ottieni informazioni sul tipo di entità
        entity_info = self.entity_manager.get_entity_type(entity.type)
        if not entity_info:
            return entity
        
        # Determina la categoria dell'entità
        category = entity_info.get("category", "custom")
        
        # Normalizza in base alla categoria
        if category == "normative":
            return self._normalize_normative_reference(entity)
        elif category == "jurisprudence":
            return self._normalize_jurisprudence_reference(entity)
        elif category == "concepts":
            return self._normalize_legal_concept(entity)
        else:
            # Se la categoria non è riconosciuta, restituisci l'entità così com'è
            entity.normalized_text = entity.text.lower()
            return entity
    
    def _normalize_normative_reference(self, entity: Entity) -> Entity:
        """
        Normalizza un riferimento normativo.
        
        Args:
            entity: Entità di tipo riferimento normativo.
        
        Returns:
            Entità normalizzata.
        """
        # Copia l'entità originale
        normalized_entity = Entity(
            text=entity.text,
            type=entity.type,
            start_char=entity.start_char,
            end_char=entity.end_char,
            metadata=entity.metadata.copy() if entity.metadata else {}
        )
        
        # Normalizza in base al tipo specifico
        entity_type_name = self._get_entity_type_name(entity.type)
        
        if entity_type_name == "ARTICOLO_CODICE":
            normalized_text, metadata = self._normalize_article_reference_data(entity.text, entity.metadata)
        elif entity_type_name == "LEGGE":
            normalized_text, metadata = self._normalize_law_reference_data(entity.text, entity.metadata)
        elif entity_type_name == "DECRETO":
            normalized_text, metadata = self._normalize_decree_reference_data(entity.text, entity.metadata)
        elif entity_type_name == "REGOLAMENTO_UE":
            normalized_text, metadata = self._normalize_eu_regulation_reference_data(entity.text, entity.metadata)
        else:
            normalized_text = entity.text
            metadata = entity.metadata
        
        # Aggiorna l'entità normalizzata
        normalized_entity.normalized_text = normalized_text
        if metadata:
            normalized_entity.metadata.update(metadata)
        
        return normalized_entity
    
    def _normalize_article_reference(self, entity: Entity) -> Entity:
        """
        Normalizza un riferimento a un articolo di codice.
        
        Args:
            entity: Entità da normalizzare
            
        Returns:
            Entità normalizzata
        """
        normalized_text, metadata = self._normalize_article_reference_data(entity.text, entity.metadata)
        
        # Copia l'entità originale
        normalized_entity = Entity(
            text=entity.text,
            type=entity.type,
            start_char=entity.start_char,
            end_char=entity.end_char,
            normalized_text=normalized_text,
            metadata=entity.metadata.copy() if entity.metadata else {}
        )
        
        # Aggiorna i metadati
        if metadata:
            normalized_entity.metadata.update(metadata)
            
        return normalized_entity
    
    def _normalize_article_reference_data(self, text: str, metadata: Optional[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
        """
        Normalizza un riferimento a un articolo di codice.
        
        Args:
            text: Testo originale dell'entità.
            metadata: Metadati dell'entità.
        
        Returns:
            Tupla con il testo normalizzato e i metadati aggiornati.
        """
        # Inizializza i metadati se non esistono
        if metadata is None:
            metadata = {}
        
        # Estrai il numero dell'articolo
        article_match = re.search(r'(\d+(?:\s*(?:bis|ter|quater|quinquies|sexies|septies|octies|novies|decies))?)', text, re.IGNORECASE)
        article_number = article_match.group(1) if article_match else ""
        
        # Estrai il codice
        code_match = re.search(r'(?:codice\s+)?(?:c(?:ivile)?\.?|p(?:enale)?\.?|c\.?c\.?|c\.?p\.?|procedura\s+civile|procedura\s+penale|c\.?p\.?c\.?|c\.?p\.?p\.?)', text, re.IGNORECASE)
        code_text = code_match.group(0) if code_match else ""
        
        # Normalizza il codice
        code = ""
        code_text_lower = code_text.lower()
        for abbr, full_name in self.canonical_forms.get("codici", {}).items():
            if abbr.lower() in code_text_lower or full_name.lower() in code_text_lower:
                code = full_name
                break
        
        if not code and code_text:
            # Se non abbiamo trovato una corrispondenza ma abbiamo un codice, usa il testo originale
            code = code_text
        
        # Costruisci il testo normalizzato
        if article_number and code:
            normalized_text = f"Articolo {article_number} {code}"
        elif article_number:
            normalized_text = f"Articolo {article_number}"
        else:
            normalized_text = text
        
        # Aggiorna i metadati
        metadata.update({
            "articolo": article_number,
            "codice": code
        })
        
        return normalized_text, metadata
    
    def _normalize_law_reference(self, entity: Entity) -> Entity:
        """
        Normalizza un riferimento a una legge.
        
        Args:
            entity: Entità da normalizzare
            
        Returns:
            Entità normalizzata
        """
        normalized_text, metadata = self._normalize_law_reference_data(entity.text, entity.metadata)
        
        # Copia l'entità originale
        normalized_entity = Entity(
            text=entity.text,
            type=entity.type,
            start_char=entity.start_char,
            end_char=entity.end_char,
            normalized_text=normalized_text,
            metadata=entity.metadata.copy() if entity.metadata else {}
        )
        
        # Aggiorna i metadati
        if metadata:
            normalized_entity.metadata.update(metadata)
            
        return normalized_entity
    
    def _normalize_law_reference_data(self, text: str, metadata: Optional[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
        """
        Normalizza un riferimento a una legge.
        
        Args:
            text: Testo originale dell'entità.
            metadata: Metadati dell'entità.
        
        Returns:
            Tupla con il testo normalizzato e i metadati aggiornati.
        """
        # Inizializza i metadati se non esistono
        if metadata is None:
            metadata = {}
        
        # Estrai il numero della legge
        number_match = re.search(r'(?:n\.?\s*)?(\d+)', text)
        number = number_match.group(1) if number_match else ""
        
        # Estrai l'anno
        year_match = re.search(r'(?:del)?\s*(?:(\d{1,2})\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+)?(\d{4})', text)
        year = year_match.group(2) if year_match else ""
        
        if not year:
            # Cerca l'anno nel formato /YYYY o /YY
            year_match = re.search(r'/(\d{2,4})', text)
            if year_match:
                year_str = year_match.group(1)
                # Se l'anno è in formato breve (es. 90), convertilo in formato completo (1990)
                if len(year_str) == 2:
                    year_int = int(year_str)
                    if year_int >= 0 and year_int <= 23:  # Assumiamo che 00-23 si riferisca a 2000-2023
                        year = f"20{year_str}"
                    else:  # Assumiamo che 24-99 si riferisca a 1924-1999
                        year = f"19{year_str}"
                else:
                    year = year_str
        
        # Estrai la data completa
        date_match = re.search(r'(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})', text)
        date = f"{date_match.group(1)} {date_match.group(2)} {date_match.group(3)}" if date_match else ""
        
        # Costruisci il testo normalizzato
        if number and year and date:
            normalized_text = f"Legge n. {number} del {date}"
        elif number and year:
            normalized_text = f"Legge n. {number}/{year}"
        elif number:
            normalized_text = f"Legge n. {number}"
        else:
            normalized_text = text
        
        # Aggiorna i metadati
        metadata.update({
            "numero": number,
            "anno": year,
            "data": date
        })
        
        return normalized_text, metadata
    
    def _normalize_decree_reference(self, entity: Entity) -> Entity:
        """
        Normalizza un riferimento a un decreto.
        
        Args:
            entity: Entità da normalizzare
            
        Returns:
            Entità normalizzata
        """
        normalized_text, metadata = self._normalize_decree_reference_data(entity.text, entity.metadata)
        
        # Copia l'entità originale
        normalized_entity = Entity(
            text=entity.text,
            type=entity.type,
            start_char=entity.start_char,
            end_char=entity.end_char,
            normalized_text=normalized_text,
            metadata=entity.metadata.copy() if entity.metadata else {}
        )
        
        # Aggiorna i metadati
        if metadata:
            normalized_entity.metadata.update(metadata)
            
        return normalized_entity
    
    def _normalize_decree_reference_data(self, text: str, metadata: Optional[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
        """
        Normalizza un riferimento a un decreto.
        
        Args:
            text: Testo originale dell'entità.
            metadata: Metadati dell'entità.
        
        Returns:
            Tupla con il testo normalizzato e i metadati aggiornati.
        """
        # Inizializza i metadati se non esistono
        if metadata is None:
            metadata = {}
        
        # Estrai il tipo di decreto
        decree_type_match = re.search(r'd(?:ecreto)?\.?\s*(?:leg(?:islativo)?|l(?:egge)?|m(?:inisteriale)?|p(?:residente)?\.?r(?:epubblica)?|p(?:residente)?\.?c(?:onsiglio)?\.?m(?:inistri)?)', text, re.IGNORECASE)
        decree_type_text = decree_type_match.group(0) if decree_type_match else ""
        
        # Normalizza il tipo di decreto
        decree_type = ""
        decree_type_lower = decree_type_text.lower()
        for abbr, full_name in self.canonical_forms.get("decreti", {}).items():
            if abbr.lower() in decree_type_lower or full_name.lower() in decree_type_lower:
                decree_type = full_name
                break
        
        if not decree_type and decree_type_text:
            # Se non abbiamo trovato una corrispondenza ma abbiamo un tipo, usa il testo originale
            decree_type = decree_type_text
        
        # Estrai il numero del decreto
        number_match = re.search(r'(?:n\.?\s*)?(\d+)', text)
        number = number_match.group(1) if number_match else ""
        
        # Estrai l'anno
        year_match = re.search(r'(?:del)?\s*(?:(\d{1,2})\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+)?(\d{4})', text)
        year = year_match.group(2) if year_match else ""
        
        if not year:
            # Cerca l'anno nel formato /YYYY o /YY
            year_match = re.search(r'/(\d{2,4})', text)
            if year_match:
                year_str = year_match.group(1)
                # Se l'anno è in formato breve (es. 90), convertilo in formato completo (1990)
                if len(year_str) == 2:
                    year_int = int(year_str)
                    if year_int >= 0 and year_int <= 23:  # Assumiamo che 00-23 si riferisca a 2000-2023
                        year = f"20{year_str}"
                    else:  # Assumiamo che 24-99 si riferisca a 1924-1999
                        year = f"19{year_str}"
                else:
                    year = year_str
        
        # Estrai la data completa
        date_match = re.search(r'(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})', text)
        date = f"{date_match.group(1)} {date_match.group(2)} {date_match.group(3)}" if date_match else ""
        
        # Costruisci il testo normalizzato
        if decree_type and number and year and date:
            normalized_text = f"{decree_type} n. {number} del {date}"
        elif decree_type and number and year:
            normalized_text = f"{decree_type} n. {number}/{year}"
        elif decree_type and number:
            normalized_text = f"{decree_type} n. {number}"
        elif decree_type:
            normalized_text = decree_type
        else:
            normalized_text = text
        
        # Aggiorna i metadati
        metadata.update({
            "tipo_decreto": decree_type,
            "numero": number,
            "anno": year,
            "data": date
        })
        
        return normalized_text, metadata
    
    def _normalize_eu_regulation_reference(self, entity: Entity) -> Entity:
        """
        Normalizza un riferimento a un regolamento UE.
        
        Args:
            entity: Entità da normalizzare
            
        Returns:
            Entità normalizzata
        """
        normalized_text, metadata = self._normalize_eu_regulation_reference_data(entity.text, entity.metadata)
        
        # Copia l'entità originale
        normalized_entity = Entity(
            text=entity.text,
            type=entity.type,
            start_char=entity.start_char,
            end_char=entity.end_char,
            normalized_text=normalized_text,
            metadata=entity.metadata.copy() if entity.metadata else {}
        )
        
        # Aggiorna i metadati
        if metadata:
            normalized_entity.metadata.update(metadata)
            
        return normalized_entity
    
    def _normalize_eu_regulation_reference_data(self, text: str, metadata: Optional[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
        """
        Normalizza un riferimento a un regolamento UE.
        
        Args:
            text: Testo originale dell'entità.
            metadata: Metadati dell'entità.
        
        Returns:
            Tupla con il testo normalizzato e i metadati aggiornati.
        """
        # Inizializza i metadati se non esistono
        if metadata is None:
            metadata = {}
        
        # Controlla se è un riferimento al GDPR
        if "gdpr" in text.lower():
            normalized_text = "Regolamento UE 2016/679 (GDPR)"
            metadata.update({
                "tipo": "Regolamento UE",
                "numero": "679",
                "anno": "2016",
                "nome_comune": "GDPR"
            })
            return normalized_text, metadata
        
        # Estrai il tipo di atto UE
        act_type_match = re.search(r'(regolamento|direttiva)(?:\s+(?:CE|UE|CEE))?', text, re.IGNORECASE)
        act_type = act_type_match.group(1).capitalize() if act_type_match else ""
        
        # Estrai l'organizzazione (CE, UE, CEE)
        org_match = re.search(r'(CE|UE|CEE)', text)
        org = org_match.group(1) if org_match else "UE"  # Default a UE se non specificato
        
        # Estrai il numero
        number_match = re.search(r'(?:n\.?\s*)?(\d+)', text)
        number = number_match.group(1) if number_match else ""
        
        # Estrai l'anno
        year_match = re.search(r'(?:del)?\s*(?:(\d{1,2})\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+)?(\d{4})', text)
        year = year_match.group(2) if year_match else ""
        
        if not year:
            # Cerca l'anno nel formato /YYYY o /YY
            year_match = re.search(r'/(\d{2,4})', text)
            if year_match:
                year_str = year_match.group(1)
                # Se l'anno è in formato breve (es. 90), convertilo in formato completo (1990)
                if len(year_str) == 2:
                    year_int = int(year_str)
                    if year_int >= 0 and year_int <= 23:  # Assumiamo che 00-23 si riferisca a 2000-2023
                        year = f"20{year_str}"
                    else:  # Assumiamo che 24-99 si riferisca a 1924-1999
                        year = f"19{year_str}"
                else:
                    year = year_str
        
        # Costruisci il testo normalizzato
        if act_type and org and number and year:
            normalized_text = f"{act_type} {org} {year}/{number}"
        elif act_type and number and year:
            normalized_text = f"{act_type} {year}/{number}"
        elif act_type and number:
            normalized_text = f"{act_type} n. {number}"
        elif act_type:
            normalized_text = act_type
        else:
            normalized_text = text
        
        # Aggiorna i metadati
        metadata.update({
            "tipo": f"{act_type} {org}" if act_type and org else act_type,
            "numero": number,
            "anno": year
        })
        
        return normalized_text, metadata
    
    def _normalize_jurisprudence_reference(self, entity: Entity) -> Entity:
        """
        Normalizza un riferimento giurisprudenziale.
        
        Args:
            entity: Entità di tipo riferimento giurisprudenziale.
        
        Returns:
            Entità normalizzata.
        """
        # Copia l'entità originale
        normalized_entity = Entity(
            text=entity.text,
            type=entity.type,
            start_char=entity.start_char,
            end_char=entity.end_char,
            metadata=entity.metadata.copy() if entity.metadata else {}
        )
        
        # Normalizza in base al tipo specifico
        entity_type_name = self._get_entity_type_name(entity.type)
        
        if entity_type_name == "SENTENZA":
            normalized_text, metadata = self._normalize_sentence_reference_data(entity.text, entity.metadata)
        elif entity_type_name == "ORDINANZA":
            normalized_text, metadata = self._normalize_ordinance_reference_data(entity.text, entity.metadata)
        else:
            normalized_text = entity.text
            metadata = entity.metadata
        
        # Aggiorna l'entità normalizzata
        normalized_entity.normalized_text = normalized_text
        if metadata:
            normalized_entity.metadata.update(metadata)
        
        return normalized_entity
    
    def _normalize_sentence_reference(self, entity: Entity) -> Entity:
        """
        Normalizza un riferimento a una sentenza.
        
        Args:
            entity: Entità da normalizzare
            
        Returns:
            Entità normalizzata
        """
        normalized_text, metadata = self._normalize_sentence_reference_data(entity.text, entity.metadata)
        
        # Copia l'entità originale
        normalized_entity = Entity(
            text=entity.text,
            type=entity.type,
            start_char=entity.start_char,
            end_char=entity.end_char,
            normalized_text=normalized_text,
            metadata=entity.metadata.copy() if entity.metadata else {}
        )
        
        # Aggiorna i metadati
        if metadata:
            normalized_entity.metadata.update(metadata)
            
        return normalized_entity
    
    def _normalize_sentence_reference_data(self, text: str, metadata: Optional[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
        """
        Normalizza un riferimento a una sentenza.
        
        Args:
            text: Testo originale dell'entità.
            metadata: Metadati dell'entità.
        
        Returns:
            Tupla con il testo normalizzato e i metadati aggiornati.
        """
        # Inizializza i metadati se non esistono
        if metadata is None:
            metadata = {}
        
        # Estrai l'autorità giudiziaria
        authority_match = re.search(r'(Corte(?:\s+di)?(?:\s+[Cc]assazione|[Cc]ass\.)|[Cc]ass\.|Corte(?:\s+(?:Costituzionale|[Cc]ost\.|di [Gg]iustizia|[Gg]iust\.|[Dd]\'[Aa]ppello|[Aa]pp\.))|Tribunale|[Tt]rib\.|TAR|[Tt]ribunale(?:\s+[Aa]mministrativo(?:\s+[Rr]egionale)?)|Consiglio(?:\s+di)?(?:\s+[Ss]tato|[Ss]tato))', text, re.IGNORECASE)
        authority_text = authority_match.group(1) if authority_match else ""
        
        # Normalizza l'autorità
        authority = ""
        authority_text_lower = authority_text.lower()
        for abbr, full_name in self.canonical_forms.get("autorità", {}).items():
            if abbr.lower() in authority_text_lower or full_name.lower() in authority_text_lower:
                authority = full_name
                break
        
        if not authority and authority_text:
            # Se non abbiamo trovato una corrispondenza ma abbiamo un'autorità, usa il testo originale
            authority = authority_text
        
        # Estrai la località (per tribunali e TAR)
        location = ""
        if "tribunale" in authority_text_lower or "trib." in authority_text_lower or "tar" in authority_text_lower:
            location_match = re.search(r'(?:di|d\')(?:\s+([A-Za-z\s]+))', text, re.IGNORECASE)
            location = location_match.group(1).strip() if location_match else ""
        
        # Estrai la sezione
        section_match = re.search(r'(?:sez\.|sezione)(?:\s+([A-Za-z0-9]+))', text, re.IGNORECASE)
        section = section_match.group(1) if section_match else ""
        
        # Estrai il numero
        number_match = re.search(r'(?:n\.|numero)(?:\s+(\d+))', text, re.IGNORECASE)
        number = number_match.group(1) if number_match else ""
        
        # Estrai l'anno
        year_match = re.search(r'(?:del)?\s*(?:(\d{1,2})\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+)?(\d{4})', text)
        year = year_match.group(2) if year_match else ""
        
        if not year:
            # Cerca l'anno nel formato /YYYY o /YY
            year_match = re.search(r'/(\d{2,4})', text)
            if year_match:
                year_str = year_match.group(1)
                # Se l'anno è in formato breve (es. 90), convertilo in formato completo (1990)
                if len(year_str) == 2:
                    year_int = int(year_str)
                    if year_int >= 0 and year_int <= 23:  # Assumiamo che 00-23 si riferisca a 2000-2023
                        year = f"20{year_str}"
                    else:  # Assumiamo che 24-99 si riferisca a 1924-1999
                        year = f"19{year_str}"
                else:
                    year = year_str
        
        # Estrai la data completa
        date_match = re.search(r'(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})', text)
        date = f"{date_match.group(1)} {date_match.group(2)} {date_match.group(3)}" if date_match else ""
        
        # Costruisci il testo normalizzato
        normalized_text = "Sentenza"
        
        if authority:
            if location:
                normalized_text += f" {authority} di {location}"
            else:
                normalized_text += f" {authority}"
        
        if section:
            normalized_text += f", sez. {section}"
        
        if number and year:
            normalized_text += f", n. {number}/{year}"
        elif number:
            normalized_text += f", n. {number}"
        
        if date:
            normalized_text += f" del {date}"
        
        # Aggiorna i metadati
        metadata.update({
            "autorità": authority,
            "località": location,
            "sezione": section,
            "numero": number,
            "anno": year,
            "data": date
        })
        
        return normalized_text, metadata
    
    def _normalize_ordinance_reference(self, entity: Entity) -> Entity:
        """
        Normalizza un riferimento a un'ordinanza.
        
        Args:
            entity: Entità da normalizzare
            
        Returns:
            Entità normalizzata
        """
        normalized_text, metadata = self._normalize_ordinance_reference_data(entity.text, entity.metadata)
        
        # Copia l'entità originale
        normalized_entity = Entity(
            text=entity.text,
            type=entity.type,
            start_char=entity.start_char,
            end_char=entity.end_char,
            normalized_text=normalized_text,
            metadata=entity.metadata.copy() if entity.metadata else {}
        )
        
        # Aggiorna i metadati
        if metadata:
            normalized_entity.metadata.update(metadata)
            
        return normalized_entity
    
    def _normalize_ordinance_reference_data(self, text: str, metadata: Optional[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
        """
        Normalizza un riferimento a un'ordinanza.
        
        Args:
            text: Testo originale dell'entità.
            metadata: Metadati dell'entità.
        
        Returns:
            Tupla con il testo normalizzato e i metadati aggiornati.
        """
        # La normalizzazione delle ordinanze è simile a quella delle sentenze
        normalized_text, metadata = self._normalize_sentence_reference_data(text, metadata)
        
        # Sostituisci "Sentenza" con "Ordinanza"
        normalized_text = normalized_text.replace("Sentenza", "Ordinanza")
        
        return normalized_text, metadata
    
    def _normalize_legal_concept(self, entity: Entity) -> Entity:
        """
        Normalizza un concetto giuridico.
        
        Args:
            entity: Entità da normalizzare
            
        Returns:
            Entità normalizzata
        """
        # Copia l'entità originale
        normalized_entity = Entity(
            text=entity.text,
            type=entity.type,
            start_char=entity.start_char,
            end_char=entity.end_char,
            normalized_text=entity.text.lower().strip(),
            metadata=entity.metadata.copy() if entity.metadata else {}
        )
        
        return normalized_entity
    
    def _enrich_from_knowledge_graph(self, entity: Entity) -> None:
        """
        Arricchisce un'entità con dati dal knowledge graph.
        
        Args:
            entity: Entità da arricchire.
        """
        if not self.use_knowledge_graph or not hasattr(self, 'neo4j_driver'):
            return
        
        try:
            # Ottieni il tipo di entità
            entity_type_name = self._get_entity_type_name(entity.type)
            normalized_text = entity.normalized_text or entity.text
            
            # Costruisci la query in base al tipo di entità
            entity_type_category = self._get_entity_category(entity_type_name)
            
            if entity_type_category == "normative":
                query = """
                MATCH (n:NormativeReference {normalized_text: $normalized_text})
                RETURN n
                """
            elif entity_type_category == "jurisprudence":
                query = """
                MATCH (j:JurisprudenceReference {normalized_text: $normalized_text})
                RETURN j
                """
            elif entity_type_category == "concepts":
                query = """
                MATCH (c:LegalConcept {name: $normalized_text})
                RETURN c
                """
            else:
                # Per tipi di entità personalizzati
                query = """
                MATCH (e:Entity {type: $entity_type, normalized_text: $normalized_text})
                RETURN e
                """
            
            # Esegui la query
            with self.neo4j_driver.session() as session:
                result = session.run(
                    query, 
                    normalized_text=normalized_text, 
                    entity_type=entity_type_name
                )
                record = result.single()
                
                if record:
                    # Estrai i dati dal record
                    node = record[0]
                    
                    # Aggiorna i metadati dell'entità con i dati dal knowledge graph
                    for key, value in node.items():
                        if key != "normalized_text" and key != "name" and key != "type":
                            entity.metadata[f"kg_{key}"] = value
                    
                    logger.debug(f"Entità arricchita con dati dal knowledge graph: {normalized_text}")
        
        except Exception as e:
            logger.error(f"Errore nell'arricchimento dell'entità dal knowledge graph: {e}")
    
    def _get_entity_category(self, entity_type_name: str) -> str:
        """
        Determina la categoria di un tipo di entità.
        
        Args:
            entity_type_name: Nome del tipo di entità
            
        Returns:
            Categoria dell'entità
        """
        # Se c'è un entity manager, usa quello per determinare la categoria
        if self.entity_manager:
            entity_type = self.entity_manager.get_entity_type(entity_type_name)
            if entity_type:
                return entity_type.get("category", "custom")
        
        # Altrimenti, cerca di determinare la categoria dal nome
        if "ARTICOLO" in entity_type_name or "LEGGE" in entity_type_name or "DECRETO" in entity_type_name or "REGOLAMENTO" in entity_type_name:
            return "normative"
        elif "SENTENZA" in entity_type_name or "ORDINANZA" in entity_type_name:
            return "jurisprudence"
        elif "CONCETTO" in entity_type_name:
            return "concepts"
        else:
            return "custom"
    
    def create_structured_references(self, entities: List[Entity]) -> Dict[str, List[Any]]:
        """
        Crea riferimenti strutturati dalle entità normalizzate.
        
        Args:
            entities: Lista di entità normalizzate.
        
        Returns:
            Dizionario di riferimenti strutturati per categoria.
        """
        structured_references = {
            "normative": [],
            "jurisprudence": [],
            "concepts": [],
            "custom": []
        }
        
        for entity in entities:
            # Ottieni il tipo di entità e la sua categoria
            entity_type_name = self._get_entity_type_name(entity.type)
            entity_category = self._get_entity_category(entity_type_name)
            
            # Crea il riferimento strutturato in base alla categoria
            if entity_category == "normative":
                reference = self._create_normative_reference(entity)
                structured_references["normative"].append(reference)
            elif entity_category == "jurisprudence":
                reference = self._create_jurisprudence_reference(entity)
                structured_references["jurisprudence"].append(reference)
            elif entity_category == "concepts":
                reference = self._create_legal_concept(entity)
                structured_references["concepts"].append(reference)
            else:
                # Per tipi di entità personalizzati
                reference = entity.to_dict()
                structured_references["custom"].append(reference)
        
        return structured_references
    
    def _create_normative_reference(self, entity: Entity) -> Union[NormativeReference, Dict[str, Any]]:
        """
        Crea un riferimento normativo strutturato da un'entità.
        
        Args:
            entity: Entità normalizzata.
        
        Returns:
            Riferimento normativo strutturato.
        """
        metadata = entity.metadata or {}
        entity_type = entity.type
        
        # Se NormativeReference è disponibile, usalo
        if 'NormativeReference' in globals():
            # Crea il riferimento normativo
            normative_ref = NormativeReference(
                type=entity_type,
                original_text=entity.text,
                normalized_text=entity.normalized_text or entity.text,
                codice=metadata.get("codice"),
                articolo=metadata.get("articolo"),
                numero=metadata.get("numero"),
                anno=metadata.get("anno"),
                data=metadata.get("data"),
                nome_comune=metadata.get("nome_comune")
            )
            
            return normative_ref
        else:
            # Altrimenti, crea un dizionario
            return {
                "type": self._get_entity_type_name(entity_type),
                "original_text": entity.text,
                "normalized_text": entity.normalized_text or entity.text,
                **{k: v for k, v in metadata.items() if k not in ["subtype", "groups", "pattern"]}
            }
    
    def _create_jurisprudence_reference(self, entity: Entity) -> Union[JurisprudenceReference, Dict[str, Any]]:
        """
        Crea un riferimento giurisprudenziale strutturato da un'entità.
        
        Args:
            entity: Entità normalizzata.
        
        Returns:
            Riferimento giurisprudenziale strutturato.
        """
        metadata = entity.metadata or {}
        entity_type = entity.type
        
        # Se JurisprudenceReference è disponibile, usalo
        if 'JurisprudenceReference' in globals():
            # Crea il riferimento giurisprudenziale
            jurisprudence_ref = JurisprudenceReference(
                type=entity_type,
                original_text=entity.text,
                normalized_text=entity.normalized_text or entity.text,
                autorità=metadata.get("autorità"),
                sezione=metadata.get("sezione"),
                numero=metadata.get("numero"),
                anno=metadata.get("anno"),
                data=metadata.get("data")
            )
            
            return jurisprudence_ref
        else:
            # Altrimenti, crea un dizionario
            return {
                "type": self._get_entity_type_name(entity_type),
                "original_text": entity.text,
                "normalized_text": entity.normalized_text or entity.text,
                **{k: v for k, v in metadata.items() if k not in ["subtype", "groups", "pattern"]}
            }
    
    def _create_legal_concept(self, entity: Entity) -> Union[LegalConcept, Dict[str, Any]]:
        """
        Crea un concetto giuridico strutturato da un'entità.
        
        Args:
            entity: Entità normalizzata.
        
        Returns:
            Concetto giuridico strutturato.
        """
        metadata = entity.metadata or {}
        
        # Se LegalConcept è disponibile, usalo
        if 'LegalConcept' in globals():
            # Crea il concetto giuridico
            concept = LegalConcept(
                original_text=entity.text,
                normalized_text=entity.normalized_text or entity.text,
                categoria=metadata.get("kg_categoria") or metadata.get("categoria"),
                definizione=metadata.get("kg_definizione") or metadata.get("definizione"),
                riferimenti_correlati=metadata.get("kg_riferimenti_correlati") or metadata.get("riferimenti_correlati", [])
            )
            
            return concept
        else:
            # Altrimenti, crea un dizionario
            return {
                "type": self._get_entity_type_name(entity.type),
                "original_text": entity.text,
                "normalized_text": entity.normalized_text or entity.text,
                "categoria": metadata.get("kg_categoria") or metadata.get("categoria"),
                "definizione": metadata.get("kg_definizione") or metadata.get("definizione"),
                "riferimenti_correlati": metadata.get("kg_riferimenti_correlati") or metadata.get("riferimenti_correlati", [])
            }