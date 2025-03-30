"""
Modulo per la definizione delle entità giuridiche riconosciute dal sistema NER-Giuridico.
Questo modulo supporta sia entità statiche (basate su enum) che entità dinamiche.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union, Set, TypeVar, Type


class EntityType(Enum):
    """Enumerazione dei tipi di entità giuridiche riconosciute dal sistema."""
    
    # Riferimenti normativi
    ARTICOLO_CODICE = auto()
    LEGGE = auto()
    DECRETO = auto()
    REGOLAMENTO_UE = auto()
    
    # Riferimenti giurisprudenziali
    SENTENZA = auto()
    ORDINANZA = auto()
    
    # Concetti giuridici
    CONCETTO_GIURIDICO = auto()
    
    @classmethod
    def get_normative_types(cls) -> Set["EntityType"]:
        """Restituisce l'insieme dei tipi di entità normative."""
        return {
            cls.ARTICOLO_CODICE,
            cls.LEGGE,
            cls.DECRETO,
            cls.REGOLAMENTO_UE
        }
    
    @classmethod
    def get_jurisprudence_types(cls) -> Set["EntityType"]:
        """Restituisce l'insieme dei tipi di entità giurisprudenziali."""
        return {
            cls.SENTENZA,
            cls.ORDINANZA
        }
    
    @classmethod
    def get_concept_types(cls) -> Set["EntityType"]:
        """Restituisce l'insieme dei tipi di entità concettuali."""
        return {
            cls.CONCETTO_GIURIDICO
        }
    
    @classmethod
    def from_name(cls, name: str) -> Optional["EntityType"]:
        """
        Ottiene un tipo di entità dal nome.
        
        Args:
            name: Nome del tipo di entità.
        
        Returns:
            Tipo di entità corrispondente o None se non esiste.
        """
        try:
            return getattr(cls, name)
        except AttributeError:
            return None
    
    def get_category(self) -> str:
        """
        Ottiene la categoria del tipo di entità.
        
        Returns:
            Categoria del tipo di entità ("normative", "jurisprudence", "concepts").
        """
        if self in self.get_normative_types():
            return "normative"
        elif self in self.get_jurisprudence_types():
            return "jurisprudence"
        elif self in self.get_concept_types():
            return "concepts"
        else:
            return "custom"


# Tipo per rappresentare un tipo di entità (enum o stringa)
EntityTypeVar = TypeVar('EntityTypeVar', EntityType, str)


@dataclass
class Entity:
    """Classe che rappresenta un'entità giuridica riconosciuta."""
    
    # Informazioni di base dell'entità
    text: str  # Testo originale dell'entità
    type: EntityTypeVar  # Tipo di entità (EntityType o stringa)
    start_char: int  # Posizione di inizio nel testo
    end_char: int  # Posizione di fine nel testo
    
    # Informazioni normalizzate
    normalized_text: Optional[str] = None  # Forma normalizzata dell'entità
    
    # Metadati specifici per tipo di entità
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Inizializza i valori predefiniti dopo la creazione dell'istanza."""
        if self.metadata is None:
            self.metadata = {}
        
        if self.normalized_text is None:
            self.normalized_text = self.text
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte l'entità in un dizionario.
        
        Returns:
            Dizionario rappresentante l'entità.
        """
        # Converti il tipo in stringa
        type_str = self._get_type_str()
        
        return {
            "text": self.text,
            "type": type_str,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "normalized_text": self.normalized_text,
            "metadata": self.metadata
        }
    
    def _get_type_str(self) -> str:
        """
        Converte il tipo dell'entità in stringa.
        
        Returns:
            Stringa rappresentante il tipo dell'entità.
        """
        if isinstance(self.type, EntityType):
            return self.type.name
        elif isinstance(self.type, str):
            return self.type
        else:
            return str(self.type)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        """
        Crea un'entità da un dizionario.
        
        Args:
            data: Dizionario contenente i dati dell'entità.
        
        Returns:
            Istanza di Entity.
        """
        # Determina il tipo di entità
        type_str = data["type"]
        entity_type = EntityType.from_name(type_str)
        
        # Se non è un tipo di entità statico, usa la stringa
        if entity_type is None:
            entity_type = type_str
        
        return cls(
            text=data["text"],
            type=entity_type,
            start_char=data["start_char"],
            end_char=data["end_char"],
            normalized_text=data.get("normalized_text"),
            metadata=data.get("metadata", {})
        )
    
    def get_category(self) -> str:
        """
        Ottiene la categoria dell'entità.
        
        Returns:
            Categoria dell'entità ("normative", "jurisprudence", "concepts", "custom").
        """
        if isinstance(self.type, EntityType):
            return self.type.get_category()
        elif isinstance(self.type, str):
            # Tenta di determinare la categoria dal nome
            if "ARTICOLO" in self.type or "LEGGE" in self.type or "DECRETO" in self.type or "REGOLAMENTO" in self.type:
                return "normative"
            elif "SENTENZA" in self.type or "ORDINANZA" in self.type:
                return "jurisprudence"
            elif "CONCETTO" in self.type:
                return "concepts"
            else:
                return "custom"
        else:
            return "custom"


@dataclass
class NormativeReference:
    """Classe che rappresenta un riferimento normativo normalizzato."""
    
    # Tipo di riferimento normativo
    type: EntityTypeVar
    
    # Informazioni comuni a tutti i riferimenti normativi
    original_text: str
    normalized_text: str
    
    # Campi specifici per tipo di riferimento
    codice: Optional[str] = None  # Per ARTICOLO_CODICE
    articolo: Optional[str] = None  # Per ARTICOLO_CODICE
    numero: Optional[str] = None  # Per LEGGE, DECRETO, REGOLAMENTO_UE
    anno: Optional[str] = None  # Per LEGGE, DECRETO, REGOLAMENTO_UE
    data: Optional[str] = None  # Per LEGGE, DECRETO
    nome_comune: Optional[str] = None  # Per REGOLAMENTO_UE (es. "GDPR")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte il riferimento normativo in un dizionario.
        
        Returns:
            Dizionario rappresentante il riferimento normativo.
        """
        # Converti il tipo in stringa
        type_str = self._get_type_str()
        
        result = {
            "type": type_str,
            "original_text": self.original_text,
            "normalized_text": self.normalized_text
        }
        
        # Aggiungi campi specifici per tipo se presenti
        for field in ["codice", "articolo", "numero", "anno", "data", "nome_comune"]:
            value = getattr(self, field)
            if value is not None:
                result[field] = value
        
        return result
    
    def _get_type_str(self) -> str:
        """
        Converte il tipo del riferimento in stringa.
        
        Returns:
            Stringa rappresentante il tipo del riferimento.
        """
        if isinstance(self.type, EntityType):
            return self.type.name
        elif isinstance(self.type, str):
            return self.type
        else:
            return str(self.type)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NormativeReference":
        """
        Crea un riferimento normativo da un dizionario.
        
        Args:
            data: Dizionario contenente i dati del riferimento.
        
        Returns:
            Istanza di NormativeReference.
        """
        # Determina il tipo di entità
        type_str = data["type"]
        entity_type = EntityType.from_name(type_str)
        
        # Se non è un tipo di entità statico, usa la stringa
        if entity_type is None:
            entity_type = type_str
        
        # Crea l'istanza con i campi comuni
        reference = cls(
            type=entity_type,
            original_text=data["original_text"],
            normalized_text=data["normalized_text"]
        )
        
        # Aggiungi campi specifici se presenti
        for field in ["codice", "articolo", "numero", "anno", "data", "nome_comune"]:
            if field in data:
                setattr(reference, field, data[field])
        
        return reference


@dataclass
class JurisprudenceReference:
    """Classe che rappresenta un riferimento giurisprudenziale normalizzato."""
    
    # Tipo di riferimento giurisprudenziale
    type: EntityTypeVar
    
    # Informazioni comuni a tutti i riferimenti giurisprudenziali
    original_text: str
    normalized_text: str
    
    # Campi specifici per tipo di riferimento
    autorità: Optional[str] = None  # Es. "Cassazione civile", "Tribunale Milano"
    sezione: Optional[str] = None
    numero: Optional[str] = None
    anno: Optional[str] = None
    data: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte il riferimento giurisprudenziale in un dizionario.
        
        Returns:
            Dizionario rappresentante il riferimento giurisprudenziale.
        """
        # Converti il tipo in stringa
        type_str = self._get_type_str()
        
        result = {
            "type": type_str,
            "original_text": self.original_text,
            "normalized_text": self.normalized_text
        }
        
        # Aggiungi campi specifici per tipo se presenti
        for field in ["autorità", "sezione", "numero", "anno", "data"]:
            value = getattr(self, field)
            if value is not None:
                result[field] = value
        
        return result
    
    def _get_type_str(self) -> str:
        """
        Converte il tipo del riferimento in stringa.
        
        Returns:
            Stringa rappresentante il tipo del riferimento.
        """
        if isinstance(self.type, EntityType):
            return self.type.name
        elif isinstance(self.type, str):
            return self.type
        else:
            return str(self.type)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JurisprudenceReference":
        """
        Crea un riferimento giurisprudenziale da un dizionario.
        
        Args:
            data: Dizionario contenente i dati del riferimento.
        
        Returns:
            Istanza di JurisprudenceReference.
        """
        # Determina il tipo di entità
        type_str = data["type"]
        entity_type = EntityType.from_name(type_str)
        
        # Se non è un tipo di entità statico, usa la stringa
        if entity_type is None:
            entity_type = type_str
        
        # Crea l'istanza con i campi comuni
        reference = cls(
            type=entity_type,
            original_text=data["original_text"],
            normalized_text=data["normalized_text"]
        )
        
        # Aggiungi campi specifici se presenti
        for field in ["autorità", "sezione", "numero", "anno", "data"]:
            if field in data:
                setattr(reference, field, data[field])
        
        return reference


@dataclass
class LegalConcept:
    """Classe che rappresenta un concetto giuridico normalizzato."""
    
    # Informazioni di base
    original_text: str
    normalized_text: str
    
    # Metadati opzionali
    categoria: Optional[str] = None
    definizione: Optional[str] = None
    riferimenti_correlati: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte il concetto giuridico in un dizionario.
        
        Returns:
            Dizionario rappresentante il concetto giuridico.
        """
        result = {
            "type": "CONCETTO_GIURIDICO",
            "original_text": self.original_text,
            "normalized_text": self.normalized_text
        }
        
        # Aggiungi campi specifici se presenti
        if self.categoria:
            result["categoria"] = self.categoria
        
        if self.definizione:
            result["definizione"] = self.definizione
        
        if self.riferimenti_correlati:
            result["riferimenti_correlati"] = self.riferimenti_correlati
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LegalConcept":
        """
        Crea un concetto giuridico da un dizionario.
        
        Args:
            data: Dizionario contenente i dati del concetto.
        
        Returns:
            Istanza di LegalConcept.
        """
        # Crea l'istanza con i campi comuni
        concept = cls(
            original_text=data["original_text"],
            normalized_text=data["normalized_text"]
        )
        
        # Aggiungi campi specifici se presenti
        for field in ["categoria", "definizione"]:
            if field in data:
                setattr(concept, field, data[field])
        
        # Aggiungi riferimenti correlati se presenti
        if "riferimenti_correlati" in data:
            concept.riferimenti_correlati = data["riferimenti_correlati"]
        
        return concept


def create_entity_from_dict(data: Dict[str, Any]) -> Entity:
    """
    Factory function per creare entità da un dizionario.
    
    Args:
        data: Dizionario contenente i dati dell'entità.
    
    Returns:
        Istanza di Entity.
    """
    return Entity.from_dict(data)


def create_reference_from_dict(data: Dict[str, Any]) -> Union[NormativeReference, JurisprudenceReference, LegalConcept]:
    """
    Factory function per creare riferimenti da un dizionario.
    
    Args:
        data: Dizionario contenente i dati del riferimento.
    
    Returns:
        Istanza di NormativeReference, JurisprudenceReference o LegalConcept.
    """
    # Determina il tipo di riferimento dalla categoria o dal tipo
    type_str = data.get("type", "")
    
    if "ARTICOLO" in type_str or "LEGGE" in type_str or "DECRETO" in type_str or "REGOLAMENTO" in type_str:
        return NormativeReference.from_dict(data)
    elif "SENTENZA" in type_str or "ORDINANZA" in type_str:
        return JurisprudenceReference.from_dict(data)
    elif "CONCETTO" in type_str:
        return LegalConcept.from_dict(data)
    else:
        # Se non possiamo determinare il tipo, restituisci un Entity generico
        return Entity.from_dict(data)