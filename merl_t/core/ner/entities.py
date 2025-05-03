"""
Legal Entity Definitions

Defines the entity types and structures for legal NER.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union, Any


class EntityType(str, Enum):
    """Legal entity types recognized by the NER system."""
    
    # Riferimenti normativi
    ARTICOLO_CODICE = "ARTICOLO_CODICE"        # Es. "art. 2043 c.c."
    ARTICOLO_LEGGE = "ARTICOLO_LEGGE"          # Es. "art. 5 della legge 241/1990"
    LEGGE = "LEGGE"                           # Es. "legge 241/1990"
    DECRETO = "DECRETO"                       # Es. "d.lgs. 50/2016"
    
    # Giurisprudenza
    SENTENZA = "SENTENZA"                     # Es. "Cass. civ. 1234/2020"
    PRECEDENTE = "PRECEDENTE"                 # Es. "come stabilito in Cass. 1234/2020"
    
    # Concetti giuridici
    PRINCIPIO_GIURIDICO = "PRINCIPIO_GIURIDICO"  # Es. "legittimo affidamento"
    ISTITUTO_GIURIDICO = "ISTITUTO_GIURIDICO"    # Es. "responsabilità extracontrattuale"
    BENE_GIURIDICO = "BENE_GIURIDICO"            # Es. "diritto alla salute"
    
    # Parti processuali
    PARTE_PROCESSUALE = "PARTE_PROCESSUALE"    # Es. "attore", "convenuto", "ricorrente"
    ORGANO_GIUDIZIARIO = "ORGANO_GIUDIZIARIO"  # Es. "Tribunale di Milano", "Corte d'Appello"
    
    # Altro
    TERMINE_GIURIDICO = "TERMINE_GIURIDICO"    # Es. termini giuridici specialistici
    DATA_GIURIDICA = "DATA_GIURIDICA"          # Es. "entro il 31 dicembre 2023"


@dataclass
class Entity:
    """Base class for legal entities."""
    
    text: str                          # Text span
    type: EntityType                   # Entity type
    start_char: int                    # Character offset start
    end_char: int                      # Character offset end
    score: float = 1.0                 # Confidence score (0.0-1.0)
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entity to dictionary."""
        return {
            "text": self.text,
            "type": self.type.value,
            "start_char": self.start_char,
            "end_char": self.end_char,
            "score": self.score,
            "metadata": self.metadata
        }
    
    def get_span(self) -> Tuple[int, int]:
        """Get the character span as a tuple."""
        return (self.start_char, self.end_char)
    
    def __str__(self) -> str:
        """String representation of the entity."""
        return f"{self.type.value}: '{self.text}' ({self.score:.2f})"


@dataclass
class ArticoloCodice(Entity):
    """Entity representing a code article reference."""
    
    numero: str = ""                     # Article number
    codice: str = ""                     # Code type (e.g., "civile", "penale")
    comma: Optional[str] = None         # Paragraph number, if specified
    
    def __post_init__(self):
        """Additional initialization after creation."""
        self.type = EntityType.ARTICOLO_CODICE
        
        # Add structured data to metadata
        self.metadata.update({
            "numero": self.numero,
            "codice": self.codice,
            "comma": self.comma
        })


@dataclass
class RiferimentoLegge(Entity):
    """Entity representing a law reference."""
    
    anno: str = ""                       # Year
    numero: str = ""                     # Law number
    tipo: str = "legge"                  # Type of legislation
    articolo: Optional[str] = None       # Article number, if specified
    
    def __post_init__(self):
        """Additional initialization after creation."""
        self.type = EntityType.LEGGE if not self.articolo else EntityType.ARTICOLO_LEGGE
        
        # Add structured data to metadata
        self.metadata.update({
            "anno": self.anno,
            "tipo": self.tipo,
            "articolo": self.articolo,
            "numero": self.numero
        })


@dataclass
class Sentenza(Entity):
    """Entity representing a court decision reference."""
    
    anno: str = ""                        # Year
    organo: str = ""                      # Court (e.g., "Cassazione")
    numero: str = ""                      # Decision number
    sezione: Optional[str] = None         # Section, if specified
    
    def __post_init__(self):
        """Additional initialization after creation."""
        self.type = EntityType.SENTENZA
        
        # Add structured data to metadata
        self.metadata.update({
            "anno": self.anno,
            "organo": self.organo,
            "sezione": self.sezione,
            "numero": self.numero
        })


@dataclass
class ConcettoGiuridico(Entity):
    """Entity representing a legal concept."""
    
    definizione: Optional[str] = None    # Definition, if available
    categoria: Optional[str] = None      # Category, if known
    
    def __post_init__(self):
        """Additional initialization after creation."""
        # Determine the specific type based on category
        if self.categoria == "principio":
            self.type = EntityType.PRINCIPIO_GIURIDICO
        elif self.categoria == "istituto":
            self.type = EntityType.ISTITUTO_GIURIDICO
        elif self.categoria == "bene":
            self.type = EntityType.BENE_GIURIDICO
        else:
            self.type = EntityType.TERMINE_GIURIDICO
        
        # Add structured data to metadata
        if self.categoria:
            self.metadata["categoria"] = self.categoria
        if self.definizione:
            self.metadata["definizione"] = self.definizione 