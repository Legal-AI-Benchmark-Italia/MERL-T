"""
Modulo per la definizione delle entità giuridiche riconosciute dal sistema NER-Giuridico.
Versione unificata.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from .entity_manager import EntityType
@dataclass
class Entity:
    """Classe che rappresenta un'entità giuridica riconosciuta."""
    
    # Informazioni di base dell'entità
    id: str  # ID univoco per l'entità
    text: str  # Testo originale dell'entità
    type_id: str  # ID del tipo di entità
    start_char: int  # Posizione di inizio nel testo
    end_char: int  # Posizione di fine nel testo
    
    # Informazioni normalizzate
    normalized_text: Optional[str] = None  # Forma normalizzata dell'entità
    
    # Metadati specifici per tipo di entità
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Punteggio di confidenza (utile per il ranking e la visualizzazione)
    confidence: float = 1.0
    
    def __post_init__(self):
        """Inizializza i valori predefiniti dopo la creazione dell'istanza."""
        if self.normalized_text is None:
            self.normalized_text = self.text
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte l'entità in un dizionario.
        
        Returns:
            Dizionario rappresentante l'entità.
        """
        return {
            "id": self.id,
            "text": self.text,
            "type_id": self.type_id,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "normalized_text": self.normalized_text,
            "metadata": self.metadata,
            "confidence": self.confidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        """
        Crea un'entità da un dizionario.
        
        Args:
            data: Dizionario contenente i dati dell'entità.
        
        Returns:
            Istanza di Entity.
        """
        return cls(
            id=data.get("id", ""),
            text=data["text"],
            type_id=data["type_id"],
            start_char=data["start_char"],
            end_char=data["end_char"],
            normalized_text=data.get("normalized_text"),
            metadata=data.get("metadata", {}),
            confidence=data.get("confidence", 1.0)
        )

@dataclass
class LawReference:
    """Classe che rappresenta un riferimento normativo normalizzato."""
    
    # Tipo di riferimento normativo
    type: EntityType
    
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
        result = {
            "type": self.type.name,
            "original_text": self.original_text,
            "normalized_text": self.normalized_text
        }
        
        # Aggiungi campi specifici per tipo se presenti
        for field in ["codice", "articolo", "numero", "anno", "data", "nome_comune"]:
            value = getattr(self, field)
            if value is not None:
                result[field] = value
        
        return result


@dataclass
class JurisprudenceReference:
    """Classe che rappresenta un riferimento giurisprudenziale normalizzato."""
    
    # Tipo di riferimento giurisprudenziale
    type: EntityType
    
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
        result = {
            "type": self.type.name,
            "original_text": self.original_text,
            "normalized_text": self.normalized_text
        }
        
        # Aggiungi campi specifici per tipo se presenti
        for field in ["autorità", "sezione", "numero", "anno", "data"]:
            value = getattr(self, field)
            if value is not None:
                result[field] = value
        
        return result


@dataclass
class LegalConcept:
    """Classe che rappresenta un concetto giuridico normalizzato."""
    
    # Informazioni di base
    original_text: str
    normalized_text: str
    
    # Metadati opzionali
    categoria: Optional[str] = None
    definizione: Optional[str] = None
    riferimenti_correlati: List[str] = None
    
    def __post_init__(self):
        """Inizializza i valori predefiniti dopo la creazione dell'istanza."""
        if self.riferimenti_correlati is None:
            self.riferimenti_correlati = []
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Converte il concetto giuridico in un dizionario.
        
        Returns:
            Dizionario rappresentante il concetto giuridico.
        """
        result = {
            "type": EntityType.CONCETTO_GIURIDICO.name,
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
