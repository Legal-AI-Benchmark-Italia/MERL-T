"""
Entity Normalizer for Legal NER

Normalizes and standardizes legal entities, resolving references and adding metadata.
"""

import re
from typing import Dict, List, Optional, Tuple, Union, Any

from loguru import logger

from .entities import (
    Entity, EntityType, ArticoloCodice, RiferimentoLegge, 
    Sentenza, ConcettoGiuridico
)


class EntityNormalizer:
    """
    Normalizes legal entities by standardizing formats and enriching metadata.
    
    Responsibilities:
    - Format normalization (consistent representation)
    - Entity enrichment (metadata, references)
    - Entity specialization (convert generic to specialized classes)
    - Entity validation (consistency checks)
    """
    
    def __init__(self, canonicalization_enabled: bool = True):
        """
        Initialize the entity normalizer.
        
        Args:
            canonicalization_enabled: Whether to canonicalize entity text
        """
        self.canonicalization_enabled = canonicalization_enabled
        
        # Regular expressions for extracting structured information
        self.patterns = {
            # Articolo del codice: "art. 2043 c.c." -> numero=2043, codice=civile
            "articolo_codice": re.compile(
                r"(?:art(?:icolo|\.)?\s+)(\d+(?:\s*(?:,|-|e)\s*\d+)*)"  # numero articolo
                r"(?:\s+comma\s+(\d+))?"  # eventuale comma
                r"(?:\s+(?:del|c\.?)\s+(?:codice\s+)?)?"  # del codice
                r"(civile|penale|procedura\s+civile|procedura\s+penale|c\.?c\.?|c\.?p\.?|c\.?p\.?c\.?|c\.?p\.?p\.?)",  # tipo codice
                re.IGNORECASE
            ),
            
            # Legge: "legge 241/1990" -> numero=241, anno=1990
            "legge": re.compile(
                r"(?P<tipo>legge|decreto|d\.lgs|d\. ?lgs|dlgs)"  # tipo legge
                r"(?:\s+(?:n\.?\s*)?(?P<numero>\d+))?"  # numero legge
                r"(?:\s*(?:del|/)\s*)"  # separatore
                r"(?P<anno>\d{2,4})",  # anno
                re.IGNORECASE
            ),
            
            # Articolo di legge: "art. 5 legge 241/1990" -> articolo=5, numero=241, anno=1990
            "articolo_legge": re.compile(
                r"(?:art(?:icolo|\.)?\s+)(?P<articolo>\d+(?:\s*(?:,|-|e)\s*\d+)*)"  # numero articolo
                r"(?:\s+(?:del(?:la)?|della)\s+)?"  # della
                r"(?P<tipo>legge|decreto|d\.lgs|d\. ?lgs|dlgs)"  # tipo legge
                r"(?:\s+(?:n\.?\s*)?(?P<numero>\d+))?"  # numero legge
                r"(?:\s*(?:del|/)\s*)"  # separatore
                r"(?P<anno>\d{2,4})",  # anno
                re.IGNORECASE
            ),
            
            # Sentenza: "Cass. civ. 1234/2020" -> organo=Cassazione, sezione=civile, numero=1234, anno=2020
            "sentenza": re.compile(
                r"(?P<organo>Cass(?:azione)?\.?|Corte (?:Suprema|Costituzionale|di Cassazione)|"
                r"Consiglio di Stato|TAR)"  # organo
                r"(?:\s+(?P<sezione>civ\.?|pen\.?|sez\.?\s+(?:un\.?|[IVX]+)))?"  # sezione
                r"(?:\s+(?:n\.?\s*)?(?P<numero>\d+))?"  # numero
                r"(?:\s*(?:del|/)\s*)"  # separatore
                r"(?P<anno>\d{2,4})",  # anno
                re.IGNORECASE
            ),
        }
    
    def _normalize_codice(self, codice: str) -> str:
        """
        Normalize code type to standard format.
        
        Args:
            codice: Raw code type
            
        Returns:
            Normalized code type
        """
        # Map abbreviations to full forms
        codice = codice.lower().strip()
        mapping = {
            "c.c.": "civile",
            "c.c": "civile",
            "cc": "civile",
            "c.p.": "penale",
            "c.p": "penale",
            "cp": "penale",
            "c.p.c.": "procedura civile",
            "c.p.c": "procedura civile",
            "cpc": "procedura civile",
            "c.p.p.": "procedura penale",
            "c.p.p": "procedura penale",
            "cpp": "procedura penale",
        }
        
        return mapping.get(codice, codice)
    
    def _normalize_tipo_legge(self, tipo: str) -> str:
        """
        Normalize legislation type to standard format.
        
        Args:
            tipo: Raw legislation type
            
        Returns:
            Normalized legislation type
        """
        tipo = tipo.lower().strip()
        mapping = {
            "d.lgs.": "decreto legislativo",
            "d.lgs": "decreto legislativo",
            "dlgs": "decreto legislativo",
            "d. lgs.": "decreto legislativo",
            "d. lgs": "decreto legislativo",
            "d.l.": "decreto legge",
            "d.l": "decreto legge",
            "dl": "decreto legge",
        }
        
        return mapping.get(tipo, tipo)
    
    def _normalize_organo(self, organo: str) -> str:
        """
        Normalize court name to standard format.
        
        Args:
            organo: Raw court name
            
        Returns:
            Normalized court name
        """
        organo = organo.lower().strip()
        mapping = {
            "cass.": "cassazione",
            "cass": "cassazione",
        }
        
        return mapping.get(organo, organo)
    
    def _format_articolo_codice(self, entity: Entity) -> str:
        """
        Format article code entity to canonical format.
        
        Args:
            entity: Entity to format
            
        Returns:
            Formatted entity text
        """
        if not isinstance(entity, ArticoloCodice):
            return entity.text
            
        comma_text = f" comma {entity.comma}" if entity.comma else ""
        codice_norm = self._normalize_codice(entity.codice)
        
        # Create canonical format
        if codice_norm == "civile":
            return f"art. {entity.numero}{comma_text} c.c."
        elif codice_norm == "penale":
            return f"art. {entity.numero}{comma_text} c.p."
        elif codice_norm == "procedura civile":
            return f"art. {entity.numero}{comma_text} c.p.c."
        elif codice_norm == "procedura penale":
            return f"art. {entity.numero}{comma_text} c.p.p."
        else:
            return f"art. {entity.numero}{comma_text} cod. {codice_norm}"
    
    def _format_riferimento_legge(self, entity: Entity) -> str:
        """
        Format law reference entity to canonical format.
        
        Args:
            entity: Entity to format
            
        Returns:
            Formatted entity text
        """
        if not isinstance(entity, RiferimentoLegge):
            return entity.text
            
        tipo_norm = self._normalize_tipo_legge(entity.tipo)
        articolo_text = f" art. {entity.articolo}" if entity.articolo else ""
        
        # Ensure year is 4 digits
        anno = entity.anno
        if len(anno) == 2:
            # Assume 21st century for years < 23, 20th century otherwise
            prefix = "20" if int(anno) < 23 else "19"
            anno = f"{prefix}{anno}"
        
        # Create canonical format
        return f"{tipo_norm} n. {entity.numero}/{anno}{articolo_text}"
    
    def _format_sentenza(self, entity: Entity) -> str:
        """
        Format court decision entity to canonical format.
        
        Args:
            entity: Entity to format
            
        Returns:
            Formatted entity text
        """
        if not isinstance(entity, Sentenza):
            return entity.text
            
        organo_norm = self._normalize_organo(entity.organo)
        sezione_text = f" {entity.sezione}" if entity.sezione else ""
        
        # Ensure year is 4 digits
        anno = entity.anno
        if len(anno) == 2:
            # Assume 21st century for years < 23, 20th century otherwise
            prefix = "20" if int(anno) < 23 else "19"
            anno = f"{prefix}{anno}"
        
        # Create canonical format
        if organo_norm == "cassazione":
            return f"Cass.{sezione_text} n. {entity.numero}/{anno}"
        else:
            return f"{organo_norm.title()}{sezione_text} n. {entity.numero}/{anno}"
    
    def canonicalize(self, entity: Entity) -> Entity:
        """
        Canonicalize an entity's text to standard format.
        
        Args:
            entity: Entity to canonicalize
            
        Returns:
            Canonicalized entity (possibly a specialized subclass)
        """
        if not self.canonicalization_enabled:
            return entity
        
        # Format based on entity type
        if entity.type == EntityType.ARTICOLO_CODICE:
            if isinstance(entity, ArticoloCodice):
                canonical_text = self._format_articolo_codice(entity)
                entity.text = canonical_text
                return entity
        elif entity.type in (EntityType.LEGGE, EntityType.ARTICOLO_LEGGE):
            if isinstance(entity, RiferimentoLegge):
                canonical_text = self._format_riferimento_legge(entity)
                entity.text = canonical_text
                return entity
        elif entity.type == EntityType.SENTENZA:
            if isinstance(entity, Sentenza):
                canonical_text = self._format_sentenza(entity)
                entity.text = canonical_text
                return entity
                
        # If we can't canonicalize, return as is
        return entity
    
    def specialize(self, entity: Entity) -> Entity:
        """
        Convert a generic Entity to a specialized subclass based on type.
        
        Args:
            entity: Generic entity
            
        Returns:
            Specialized entity if possible, original entity otherwise
        """
        # Skip if already specialized
        if not isinstance(entity, Entity) or type(entity) != Entity:
            return entity
            
        # Try to extract structured information based on entity type
        if entity.type == EntityType.ARTICOLO_CODICE:
            match = self.patterns["articolo_codice"].search(entity.text)
            if match:
                numero, comma, codice = match.groups()
                return ArticoloCodice(
                    text=entity.text,
                    start_char=entity.start_char,
                    end_char=entity.end_char,
                    score=entity.score,
                    metadata=entity.metadata.copy(),
                    numero=numero,
                    codice=self._normalize_codice(codice),
                    comma=comma
                )
        elif entity.type == EntityType.LEGGE:
            match = self.patterns["legge"].search(entity.text)
            if match:
                tipo = match.group("tipo")
                numero = match.group("numero") or ""
                anno = match.group("anno")
                return RiferimentoLegge(
                    text=entity.text,
                    start_char=entity.start_char,
                    end_char=entity.end_char,
                    score=entity.score,
                    metadata=entity.metadata.copy(),
                    numero=numero,
                    anno=anno,
                    tipo=self._normalize_tipo_legge(tipo)
                )
        elif entity.type == EntityType.ARTICOLO_LEGGE:
            match = self.patterns["articolo_legge"].search(entity.text)
            if match:
                articolo = match.group("articolo")
                tipo = match.group("tipo")
                numero = match.group("numero") or ""
                anno = match.group("anno")
                return RiferimentoLegge(
                    text=entity.text,
                    start_char=entity.start_char,
                    end_char=entity.end_char,
                    score=entity.score,
                    metadata=entity.metadata.copy(),
                    numero=numero,
                    anno=anno,
                    tipo=self._normalize_tipo_legge(tipo),
                    articolo=articolo
                )
        elif entity.type == EntityType.SENTENZA:
            match = self.patterns["sentenza"].search(entity.text)
            if match:
                organo = match.group("organo")
                sezione = match.group("sezione")
                numero = match.group("numero") or ""
                anno = match.group("anno")
                return Sentenza(
                    text=entity.text,
                    start_char=entity.start_char,
                    end_char=entity.end_char,
                    score=entity.score,
                    metadata=entity.metadata.copy(),
                    numero=numero,
                    anno=anno,
                    organo=self._normalize_organo(organo),
                    sezione=sezione
                )
        
        # If we can't specialize, return as is
        return entity
    
    def normalize(self, entity: Entity) -> Entity:
        """
        Apply full normalization pipeline to an entity.
        
        Args:
            entity: Entity to normalize
            
        Returns:
            Normalized entity
        """
        # First convert to specialized class if possible
        specialized = self.specialize(entity)
        
        # Then canonicalize the text
        normalized = self.canonicalize(specialized)
        
        return normalized
    
    def normalize_all(self, entities: List[Entity]) -> List[Entity]:
        """
        Normalize a list of entities.
        
        Args:
            entities: List of entities to normalize
            
        Returns:
            List of normalized entities
        """
        return [self.normalize(entity) for entity in entities] 