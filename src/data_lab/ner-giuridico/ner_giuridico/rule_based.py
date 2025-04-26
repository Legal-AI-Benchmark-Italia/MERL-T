"""
Modulo per il riconoscimento di entità basato su regole per il sistema NER-Giuridico.
Supporta configurazione dinamica e gestione delle entità.
"""

import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Pattern, Tuple, Union

from .config import config
from .entities.entities import Entity
from .entities.entity_manager import get_entity_manager, EntityType

logger = logging.getLogger(__name__)

class RuleBasedRecognizer:
    """
    Riconoscitore di entità basato su regole per il sistema NER-Giuridico.
    Utilizza pattern regex e gazetteer per identificare entità giuridiche.
    Supporta l'aggiornamento dinamico dei pattern.
    """
    
    def __init__(self, entity_manager=None):
        """
        Inizializza il riconoscitore basato su regole.
        
        Args:
            entity_manager: Gestore delle entità dinamiche (opzionale)
        """
        self.enabled = config.get("models.rule_based.enable", True)
        
        # Usa il gestore delle entità dinamiche se fornito
        self.entity_manager = entity_manager
        
        if not self.enabled:
            logger.info("Riconoscitore basato su regole disabilitato")
            return
        
        # Carica i pattern per i riferimenti normativi
        self.law_patterns = self._load_patterns("riferimenti_normativi")
        
        # Carica i pattern per i riferimenti giurisprudenziali
        self.jurisprudence_patterns = self._load_patterns("riferimenti_giurisprudenziali")
        
        # Carica il gazetteer per i concetti giuridici
        self.doctrine_gazetteer = self._load_gazetteer("concetti_giuridici")
        
        # Pattern compilati per entità dinamiche
        self.dynamic_patterns = {}
        
        # Compila i pattern delle entità dinamiche se disponibili
        if self.entity_manager:
            self._compile_dynamic_patterns()
        
        logger.info("Riconoscitore basato su regole inizializzato con successo")
    
    def _compile_dynamic_patterns(self):
        """Compila i pattern regex delle entità dinamiche."""
        if not self.entity_manager:
            return
            
        for name, entity_info in self.entity_manager.get_all_entity_types().items():
            patterns = entity_info.get("patterns", [])
            if patterns:
                compiled_patterns = []
                for pattern in patterns:
                    try:
                        compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
                    except re.error as e:
                        logger.warning(f"Pattern non valido per {name}: {pattern} - {e}")
                
                if compiled_patterns:
                    self.dynamic_patterns[name] = compiled_patterns
    
    def _load_patterns(self, entity_type: str) -> Dict[str, List[Pattern]]:
        """
        Carica i pattern regex per un tipo di entità.
        
        Args:
            entity_type: Tipo di entità per cui caricare i pattern.
        
        Returns:
            Dizionario di pattern regex compilati per sottotipo di entità.
        """
        patterns_dir = config.get("models.rule_based.patterns_dir", "../data/patterns")
        patterns_file = config.get(f"entities.{entity_type}.patterns_file", f"patterns_{entity_type}.json")
        
        # Costruisci il percorso completo
        base_dir = Path(__file__).parent.parent
        file_path = base_dir / patterns_dir / patterns_file
        
        patterns = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                pattern_data = json.load(f)
            
            # Compila i pattern regex per ogni sottotipo
            for subtype, subtype_patterns in pattern_data.items():
                patterns[subtype] = [re.compile(p, re.IGNORECASE) for p in subtype_patterns]
            
            logger.info(f"Pattern per {entity_type} caricati da {file_path}")
        except FileNotFoundError:
            logger.warning(f"File dei pattern {file_path} non trovato. Creazione di pattern predefiniti.")
            
            # Crea pattern predefiniti in base al tipo di entità
            if entity_type == "riferimenti_normativi":
                patterns = self._create_default_law_patterns()
            elif entity_type == "riferimenti_giurisprudenziali":
                patterns = self._create_default_jurisprudence_patterns()
            
            # Assicurati che la directory esista
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Salva i pattern predefiniti
            with open(file_path, 'w', encoding='utf-8') as f:
                # Converti i pattern compilati in stringhe per il salvataggio
                serializable_patterns = {
                    subtype: [p.pattern for p in patterns_list]
                    for subtype, patterns_list in patterns.items()
                }
                json.dump(serializable_patterns, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Pattern predefiniti per {entity_type} creati e salvati in {file_path}")
        
        return patterns
    
    def _create_default_law_patterns(self) -> Dict[str, List[Pattern]]:
        """
        Crea pattern predefiniti per i riferimenti normativi.
        
        Returns:
            Dizionario di pattern regex compilati per sottotipo di riferimento normativo.
        """
        patterns = {
            "articoli_codice": [
                re.compile(r'(?:art(?:icolo)?\.?\s*(?:n\.?\s*)?(\d+(?:\s*(?:bis|ter|quater|quinquies|sexies|septies|octies|novies|decies))?)\s+(?:del\s+)?(?:codice\s+)?(?:c(?:ivile)?\.?|p(?:enale)?\.?|c\.?c\.?|c\.?p\.?))', re.IGNORECASE),
                re.compile(r'(?:art(?:icolo)?\.?\s*(?:n\.?\s*)?(\d+(?:\s*(?:bis|ter|quater|quinquies|sexies|septies|octies|novies|decies))?)\s+(?:del\s+)?(?:codice\s+)(?:di\s+)?(?:procedura\s+)(?:civile|penale))', re.IGNORECASE),
                re.compile(r'(?:art(?:icolo)?\.?\s*(?:n\.?\s*)?(\d+(?:\s*(?:bis|ter|quater|quinquies|sexies|septies|octies|novies|decies))?)\s+(?:c\.?p\.?c\.?|c\.?p\.?p\.?))', re.IGNORECASE)
            ],
            "leggi": [
                re.compile(r'(?:legge(?:\s+n\.?)?(?:\s+(\d+))?(?:\s+del)?(?:\s+(\d{1,2}))?(?:\s+(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre))?(?:\s+(\d{4}))?)', re.IGNORECASE),
                re.compile(r'(?:l\.(?:\s+n\.?)?(?:\s+(\d+))(?:/(\d{2,4}))?)', re.IGNORECASE)
            ],
            "decreti": [
                re.compile(r'(?:d(?:ecreto)?\.?\s*(?:leg(?:islativo)?|l(?:egge)?|m(?:inisteriale)?|p(?:residente)?\.?r(?:epubblica)?|p(?:residente)?\.?c(?:onsiglio)?\.?m(?:inistri)?)\.?(?:\s+n\.?)?(?:\s+(\d+))(?:/(\d{2,4}))?)', re.IGNORECASE),
                re.compile(r'(?:d\.?lgs\.?(?:\s+n\.?)?(?:\s+(\d+))(?:/(\d{2,4}))?)', re.IGNORECASE),
                re.compile(r'(?:d\.?l\.?(?:\s+n\.?)?(?:\s+(\d+))(?:/(\d{2,4}))?)', re.IGNORECASE),
                re.compile(r'(?:d\.?p\.?r\.?(?:\s+n\.?)?(?:\s+(\d+))(?:/(\d{2,4}))?)', re.IGNORECASE),
                re.compile(r'(?:d\.?p\.?c\.?m\.?(?:\s+n\.?)?(?:\s+(\d+))(?:/(\d{2,4}))?)', re.IGNORECASE),
                re.compile(r'(?:d\.?m\.?(?:\s+n\.?)?(?:\s+(\d+))(?:/(\d{2,4}))?)', re.IGNORECASE)
            ],
            "regolamenti_ue": [
                re.compile(r'(?:regolamento(?:\s+(?:CE|UE|CEE))?(?:\s+n\.?)?(?:\s+(\d+))(?:/(\d{2,4}))?)', re.IGNORECASE),
                re.compile(r'(?:direttiva(?:\s+(?:CE|UE|CEE))?(?:\s+n\.?)?(?:\s+(\d+))(?:/(\d{2,4}))?)', re.IGNORECASE),
                re.compile(r'(?:GDPR)', re.IGNORECASE)
            ]
        }
        
        return patterns
    
    def _create_default_jurisprudence_patterns(self) -> Dict[str, List[Pattern]]:
        """
        Crea pattern predefiniti per i riferimenti giurisprudenziali.
        
        Returns:
            Dizionario di pattern regex compilati per sottotipo di riferimento giurisprudenziale.
        """
        patterns = {
            "sentenze": [
                re.compile(r'(?:(?:Corte(?:\s+di)?(?:\s+[Cc]assazione|[Cc]ass\.)|[Cc]ass\.)(?:\s+(?:civile|penale|civ\.|pen\.))?(?:\s+(?:sez\.|sezione)(?:\s+(\w+)))?(?:\s+(?:n\.|numero)(?:\s+(\d+)))?(?:/(\d{2,4}))?)', re.IGNORECASE),
                re.compile(r'(?:(?:Corte(?:\s+(?:Costituzionale|[Cc]ost\.|di [Gg]iustizia|[Gg]iust\.|[Dd]\'[Aa]ppello|[Aa]pp\.))(?:\s+(?:sez\.|sezione)(?:\s+(\w+)))?(?:\s+(?:n\.|numero)(?:\s+(\d+)))?(?:/(\d{2,4}))?)', re.IGNORECASE),
                re.compile(r'(?:(?:Tribunale|[Tt]rib\.)(?:\s+(?:di|d\')(?:\s+([A-Za-z\s]+)))?(?:\s+(?:sez\.|sezione)(?:\s+(\w+)))?(?:\s+(?:n\.|numero)(?:\s+(\d+)))?(?:/(\d{2,4}))?)', re.IGNORECASE),
                re.compile(r'(?:(?:TAR|[Tt]ribunale(?:\s+[Aa]mministrativo(?:\s+[Rr]egionale)?))(?:\s+(?:di|d\')(?:\s+([A-Za-z\s]+)))?(?:\s+(?:sez\.|sezione)(?:\s+(\w+)))?(?:\s+(?:n\.|numero)(?:\s+(\d+)))?(?:/(\d{2,4}))?)', re.IGNORECASE),
                re.compile(r'(?:(?:Consiglio(?:\s+di)?(?:\s+[Ss]tato|[Ss]tato))(?:\s+(?:sez\.|sezione)(?:\s+(\w+)))?(?:\s+(?:n\.|numero)(?:\s+(\d+)))?(?:/(\d{2,4}))?)', re.IGNORECASE)
            ],
            "ordinanze": [
                re.compile(r'(?:ordinanza(?:\s+(?:del|dell\'))?(?:\s+(?:Corte(?:\s+di)?(?:\s+[Cc]assazione|[Cc]ass\.)|[Cc]ass\.))?(?:\s+(?:civile|penale|civ\.|pen\.))?(?:\s+(?:sez\.|sezione)(?:\s+(\w+)))?(?:\s+(?:n\.|numero)(?:\s+(\d+)))?(?:/(\d{2,4}))?)', re.IGNORECASE),
                re.compile(r'(?:ordinanza(?:\s+(?:del|dell\'))?(?:\s+(?:Tribunale|[Tt]rib\.))?(?:\s+(?:di|d\')(?:\s+([A-Za-z\s]+)))?(?:\s+(?:sez\.|sezione)(?:\s+(\w+)))?(?:\s+(?:n\.|numero)(?:\s+(\d+)))?(?:/(\d{2,4}))?)', re.IGNORECASE),
                re.compile(r'(?:ordinanza(?:\s+(?:del|dell\'))?(?:\s+(?:Corte(?:\s+(?:Costituzionale|[Cc]ost\.|di [Gg]iustizia|[Gg]iust\.|[Dd]\'[Aa]ppello|[Aa]pp\.)))?(?:\s+(?:sez\.|sezione)(?:\s+(\w+)))?(?:\s+(?:n\.|numero)(?:\s+(\d+)))?(?:/(\d{2,4}))?)', re.IGNORECASE)
            ]
        }
        
        return patterns
    
    def _load_gazetteer(self, entity_type: str) -> Set[str]:
        """
        Carica il gazetteer per un tipo di entità.
        
        Args:
            entity_type: Tipo di entità per cui caricare il gazetteer.
        
        Returns:
            Insieme di termini del gazetteer.
        """
        gazetteer_file = config.get(f"entities.{entity_type}.gazetteer_file", f"{entity_type}.json")
        patterns_dir = config.get("models.rule_based.patterns_dir", "../data/patterns")
        
        # Costruisci il percorso completo
        base_dir = Path(__file__).parent.parent
        file_path = base_dir / patterns_dir / gazetteer_file
        
        gazetteer = set()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                gazetteer_data = json.load(f)
            
            # Aggiungi i termini al gazetteer
            gazetteer = set(gazetteer_data)
            
            logger.info(f"Gazetteer per {entity_type} caricato da {file_path}")
        except FileNotFoundError:
            logger.warning(f"File del gazetteer {file_path} non trovato. Creazione di un gazetteer predefinito.")
            
            # Crea un gazetteer predefinito
            if entity_type == "concetti_giuridici":
                gazetteer = self._create_default_doctrine_gazetteer()
            
            # Assicurati che la directory esista
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Salva il gazetteer predefinito
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(list(gazetteer), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Gazetteer predefinito per {entity_type} creato e salvato in {file_path}")
        
        return gazetteer
    
    def _create_default_doctrine_gazetteer(self) -> Set[str]:
        """
        Crea un gazetteer predefinito per i concetti giuridici.
        
        Returns:
            Insieme di concetti giuridici predefiniti.
        """
        # Lista di concetti giuridici comuni nel diritto italiano
        doctrine = {
            "simulazione", "buona fede", "mala fede", "dolo", "colpa", "colpa grave",
            "responsabilità", "danno", "risarcimento", "indennizzo", "inadempimento",
            "contratto", "obbligazione", "diritto reale", "proprietà", "possesso",
            "usufrutto", "servitù", "ipoteca", "pegno", "prescrizione", "decadenza",
            "nullità", "annullabilità", "rescissione", "risoluzione", "recesso",
            "causa", "oggetto", "forma", "condizione", "termine", "modo",
            "successione", "testamento", "legato", "eredità", "coerede", "legittima",
            "matrimonio", "separazione", "divorzio", "affidamento", "adozione",
            "società", "impresa", "azienda", "fallimento", "concordato preventivo",
            "reato", "dolo specifico", "dolo generico", "colpa cosciente", "preterintenzione",
            "tentativo", "concorso", "circostanza aggravante", "circostanza attenuante",
            "giurisdizione", "competenza", "litispendenza", "connessione", "continenza",
            "preclusione", "giudicato", "esecuzione", "impugnazione", "ricorso",
            "appello", "cassazione", "revocazione", "opposizione", "regolamento di competenza",
            "onere della prova", "presunzione", "confessione", "giuramento", "testimonianza",
            "perizia", "ispezione", "esibizione", "principio del contraddittorio",
            "principio dispositivo", "principio della domanda", "principio di legalità",
            "principio di tassatività", "principio di irretroattività", "principio del giusto processo"
        }
        
        return doctrine
    
    def update_patterns(self, entity_type: str, patterns: List[str]) -> bool:
        """
        Aggiorna i pattern regex per un tipo di entità.
        
        Args:
            entity_type: Nome del tipo di entità
            patterns: Lista di pattern regex
            
        Returns:
            True se l'aggiornamento è avvenuto con successo, False altrimenti
        """
        try:
            # Compila i nuovi pattern
            compiled_patterns = []
            for pattern in patterns:
                try:
                    compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error as e:
                    logger.warning(f"Pattern non valido per {entity_type}: {pattern} - {e}")
            
            # Aggiorna i pattern
            self.dynamic_patterns[entity_type] = compiled_patterns
            
            logger.info(f"Pattern per {entity_type} aggiornati con successo")
            return True
        except Exception as e:
            logger.error(f"Errore nell'aggiornamento dei pattern per {entity_type}: {e}")
            return False
    
    def recognize(self, text: str) -> List[Entity]:
        """
        Riconosce le entità giuridiche nel testo utilizzando regole.
        
        Args:
            text: Testo in cui cercare le entità.
        
        Returns:
            Lista di entità riconosciute.
        """
        if not self.enabled:
            return []
        
        entities = []
        
        # Riconosci riferimenti normativi
        entities.extend(self._recognize_law_references(text))
        
        # Riconosci riferimenti giurisprudenziali
        entities.extend(self._recognize_jurisprudence_references(text))
        
        # Riconosci concetti giuridici
        entities.extend(self._recognize_legal_doctrine(text))
        
        # Riconosci entità dinamiche
        entities.extend(self._recognize_dynamic_entities(text))
        
        # Ordina le entità per posizione nel testo
        entities.sort(key=lambda e: e.start_char)
        
        return entities
    
    def _recognize_law_references(self, text: str) -> List[Entity]:
        """
        Riconosce i riferimenti normativi nel testo.
        
        Args:
            text: Testo in cui cercare i riferimenti normativi.
        
        Returns:
            Lista di entità di tipo riferimento normativo.
        """
        entities = []
        
        # Per ogni sottotipo di riferimento normativo
        for subtype, patterns in self.law_patterns.items():
            # Per ogni pattern del sottotipo
            for pattern in patterns:
                # Cerca tutte le occorrenze del pattern nel testo
                for match in pattern.finditer(text):
                    # Determina il tipo di entità in base al sottotipo
                    entity_type = self._get_entity_type_from_law_subtype(subtype)
                    
                    # Crea l'entità
                    entity = Entity(
                        text=match.group(0),
                        type=entity_type,
                        start_char=match.start(),
                        end_char=match.end(),
                        normalized_text=None,  # Sarà normalizzato in seguito
                        metadata={
                            "subtype": subtype,
                            "groups": match.groups()
                        }
                    )
                    
                    entities.append(entity)
        
        return entities
    
    def _get_entity_type_from_law_subtype(self, subtype: str) -> Union[EntityType, str]:
        """
        Converte un sottotipo di riferimento normativo in un tipo di entità.
        
        Args:
            subtype: Sottotipo di riferimento normativo.
        
        Returns:
            Tipo di entità corrispondente.
        """
        # Mappa dei sottotipi ai tipi di entità
        subtype_to_entity_type = {
            "articoli_codice": "ARTICOLO_CODICE",
            "leggi": "LEGGE",
            "decreti": "DECRETO",
            "regolamenti_ue": "REGOLAMENTO_UE"
        }
        
        # Ottieni il nome del tipo di entità
        entity_type_name = subtype_to_entity_type.get(subtype, "ARTICOLO_CODICE")
        
        # Se c'è un entity manager, usa il nome direttamente
        if self.entity_manager and self.entity_manager.entity_type_exists(entity_type_name):
            return entity_type_name
        
        # Altrimenti, usa l'enumerazione statica se disponibile
        if hasattr(EntityType, entity_type_name):
            return getattr(EntityType, entity_type_name)
        
        # In caso di fallimento, restituisci il nome come stringa
        return entity_type_name
    
    def _recognize_jurisprudence_references(self, text: str) -> List[Entity]:
        """
        Riconosce i riferimenti giurisprudenziali nel testo.
        
        Args:
            text: Testo in cui cercare i riferimenti giurisprudenziali.
        
        Returns:
            Lista di entità di tipo riferimento giurisprudenziale.
        """
        entities = []
        
        # Per ogni sottotipo di riferimento giurisprudenziale
        for subtype, patterns in self.jurisprudence_patterns.items():
            # Per ogni pattern del sottotipo
            for pattern in patterns:
                # Cerca tutte le occorrenze del pattern nel testo
                for match in pattern.finditer(text):
                    # Determina il tipo di entità in base al sottotipo
                    entity_type = self._get_entity_type_from_jurisprudence_subtype(subtype)
                    
                    # Crea l'entità
                    entity = Entity(
                        text=match.group(0),
                        type=entity_type,
                        start_char=match.start(),
                        end_char=match.end(),
                        normalized_text=None,  # Sarà normalizzato in seguito
                        metadata={
                            "subtype": subtype,
                            "groups": match.groups()
                        }
                    )
                    
                    entities.append(entity)
        
        return entities
    
    def _get_entity_type_from_jurisprudence_subtype(self, subtype: str) -> Union[EntityType, str]:
        """
        Converte un sottotipo di riferimento giurisprudenziale in un tipo di entità.
        
        Args:
            subtype: Sottotipo di riferimento giurisprudenziale.
        
        Returns:
            Tipo di entità corrispondente.
        """
        # Mappa dei sottotipi ai tipi di entità
        subtype_to_entity_type = {
            "sentenze": "SENTENZA",
            "ordinanze": "ORDINANZA"
        }
        
        # Ottieni il nome del tipo di entità
        entity_type_name = subtype_to_entity_type.get(subtype, "SENTENZA")
        
        # Se c'è un entity manager, usa il nome direttamente
        if self.entity_manager and self.entity_manager.entity_type_exists(entity_type_name):
            return entity_type_name
        
        # Altrimenti, usa l'enumerazione statica se disponibile
        if hasattr(EntityType, entity_type_name):
            return getattr(EntityType, entity_type_name)
        
        # In caso di fallimento, restituisci il nome come stringa
        return entity_type_name
    
    def _recognize_legal_doctrine(self, text: str) -> List[Entity]:
        """
        Riconosce i concetti giuridici nel testo utilizzando il gazetteer.
        
        Args:
            text: Testo in cui cercare i concetti giuridici.
        
        Returns:
            Lista di entità di tipo concetto giuridico.
        """
        entities = []
        
        # Determina il tipo di entità
        entity_type = self._get_entity_type("CONCETTO_GIURIDICO")
        
        # Per ogni concetto nel gazetteer
        for concept in self.doctrine_gazetteer:
            # Cerca tutte le occorrenze del concetto nel testo (case insensitive)
            for match in re.finditer(r'\b' + re.escape(concept) + r'\b', text, re.IGNORECASE):
                # Crea l'entità
                entity = Entity(
                    text=match.group(0),
                    type=entity_type,
                    start_char=match.start(),
                    end_char=match.end(),
                    normalized_text=concept.lower(),  # Normalizza al concetto originale in minuscolo
                    metadata={
                        "concept": concept
                    }
                )
                
                entities.append(entity)
        
        return entities
    
    def _get_entity_type(self, entity_type_name: str) -> Union[EntityType, str]:
        """
        Ottiene il tipo di entità dal nome.
        
        Args:
            entity_type_name: Nome del tipo di entità
            
        Returns:
            Tipo di entità corrispondente
        """
        # Se c'è un entity manager, usa il nome direttamente
        if self.entity_manager and self.entity_manager.entity_type_exists(entity_type_name):
            return entity_type_name
        
        # Altrimenti, usa l'enumerazione statica se disponibile
        if hasattr(EntityType, entity_type_name):
            return getattr(EntityType, entity_type_name)
        
        # In caso di fallimento, restituisci il nome come stringa
        return entity_type_name
    
    def _recognize_dynamic_entities(self, text: str) -> List[Entity]:
        """
        Riconosce le entità dinamiche utilizzando i pattern definiti.
        
        Args:
            text: Testo in cui cercare le entità.
            
        Returns:
            Lista di entità dinamiche riconosciute
        """
        entities = []
        
        # Se non ci sono pattern dinamici, restituisci una lista vuota
        if not self.dynamic_patterns:
            return entities
        
        # Per ogni tipo di entità dinamica
        for entity_type, patterns in self.dynamic_patterns.items():
            # Per ogni pattern
            for pattern in patterns:
                # Cerca tutte le occorrenze del pattern nel testo
                for match in pattern.finditer(text):
                    # Crea l'entità
                    entity = Entity(
                        text=match.group(0),
                        type=entity_type,
                        start_char=match.start(),
                        end_char=match.end(),
                        normalized_text=None,  # Sarà normalizzato in seguito
                        metadata={
                            "pattern": pattern.pattern,
                            "groups": match.groups()
                        }
                    )
                    
                    entities.append(entity)
        
        return entities