"""
Modulo per gli endpoint API dedicati alla gestione dinamica delle entità.
"""

import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException, Depends, Body, Query, Path
from .dynamic_ner import get_entity_manager, DynamicEntityManager

# Definizione dei modelli dati per l'API
class MetadataFieldSchema(BaseModel):
    name: str = Field(..., description="Nome del campo metadati")
    field_type: str = Field(..., description="Tipo del campo (string, number, boolean, etc.)")
    description: str = Field("", description="Descrizione del campo")
    required: bool = Field(False, description="Se il campo è obbligatorio")

class EntityTypeCreate(BaseModel):
    name: str = Field(..., description="Nome identificativo dell'entità (in maiuscolo)")
    display_name: str = Field(..., description="Nome visualizzato dell'entità")
    category: str = Field(..., description="Categoria dell'entità (normative, jurisprudence, concepts, custom)")
    color: str = Field(..., description="Colore dell'entità in formato esadecimale (#RRGGBB)")
    metadata_fields: List[MetadataFieldSchema] = Field([], description="Schema dei campi metadati")

class EntityTypeUpdate(BaseModel):
    display_name: Optional[str] = Field(None, description="Nome visualizzato dell'entità")
    color: Optional[str] = Field(None, description="Colore dell'entità in formato esadecimale (#RRGGBB)")
    metadata_fields: Optional[List[MetadataFieldSchema]] = Field(None, description="Schema dei campi metadati")

class EntityTypeInfo(BaseModel):
    name: str = Field(..., description="Nome identificativo dell'entità")
    display_name: str = Field(..., description="Nome visualizzato dell'entità")
    category: str = Field(..., description="Categoria dell'entità")
    color: str = Field(..., description="Colore dell'entità")
    metadata_fields: List[MetadataFieldSchema] = Field([], description="Schema dei campi metadati")

# Creazione del router
entity_router = APIRouter(
    prefix="/api/v1/entities",
    tags=["entities"],
    responses={404: {"description": "Not found"}},
)

# Dipendenza per ottenere il gestore delle entità
def get_entity_manager_dep() -> DynamicEntityManager:
    return get_entity_manager()

@entity_router.get("/", response_model=List[EntityTypeInfo])
async def get_all_entities(
    category: Optional[str] = Query(None, description="Filtra per categoria"),
    entity_manager: DynamicEntityManager = Depends(get_entity_manager_dep)
):
    """Ottiene tutte le definizioni delle entità, opzionalmente filtrate per categoria."""
    result = []
    
    if category:
        # Filtra per categoria
        entity_names = entity_manager.get_entity_types_by_category(category)
        for name in entity_names:
            entity_info = entity_manager.get_entity_type(name)
            if entity_info:
                # Converti dal formato interno al formato API
                metadata_fields = []
                for field_name, field_type in entity_info.get("metadata_schema", {}).items():
                    metadata_fields.append(MetadataFieldSchema(
                        name=field_name, 
                        field_type=field_type,
                        required=False
                    ))
                
                result.append(EntityTypeInfo(
                    name=name,
                    display_name=entity_info.get("display_name", name),
                    category=entity_info.get("category", "custom"),
                    color=entity_info.get("color", "#CCCCCC"),
                    metadata_fields=metadata_fields
                ))
    else:
        # Ottieni tutte le entità
        for name, info in entity_manager.get_all_entity_types().items():
            # Converti dal formato interno al formato API
            metadata_fields = []
            for field_name, field_type in info.get("metadata_schema", {}).items():
                metadata_fields.append(MetadataFieldSchema(
                    name=field_name, 
                    field_type=field_type,
                    required=False
                ))
            
            result.append(EntityTypeInfo(
                name=name,
                display_name=info.get("display_name", name),
                category=info.get("category", "custom"),
                color=info.get("color", "#CCCCCC"),
                metadata_fields=metadata_fields
            ))
    
    return result

@entity_router.get("/{entity_name}", response_model=EntityTypeInfo)
async def get_entity(
    entity_name: str = Path(..., description="Nome identificativo dell'entità"),
    entity_manager: DynamicEntityManager = Depends(get_entity_manager_dep)
):
    """Ottiene la definizione di una specifica entità."""
    entity_info = entity_manager.get_entity_type(entity_name)
    if not entity_info:
        raise HTTPException(status_code=404, detail=f"Entità {entity_name} non trovata")
    
    # Converti dal formato interno al formato API
    metadata_fields = []
    for field_name, field_type in entity_info.get("metadata_schema", {}).items():
        metadata_fields.append(MetadataFieldSchema(
            name=field_name, 
            field_type=field_type,
            required=False
        ))
    
    return EntityTypeInfo(
        name=entity_name,
        display_name=entity_info.get("display_name", entity_name),
        category=entity_info.get("category", "custom"),
        color=entity_info.get("color", "#CCCCCC"),
        metadata_fields=metadata_fields
    )

@entity_router.post("/", response_model=EntityTypeInfo)
async def create_entity(
    entity: EntityTypeCreate = Body(...),
    entity_manager: DynamicEntityManager = Depends(get_entity_manager_dep)
):
    """Crea una nuova definizione di entità."""
    # Converti dal formato API al formato interno
    metadata_schema = {}
    for field in entity.metadata_fields:
        metadata_schema[field.name] = field.field_type
    
    # Verifica se l'entità esiste già
    if entity_manager.entity_type_exists(entity.name):
        raise HTTPException(status_code=409, detail=f"L'entità {entity.name} esiste già")
    
    # Aggiungi l'entità
    success = entity_manager.add_entity_type(
        name=entity.name,
        display_name=entity.display_name,
        category=entity.category,
        color=entity.color,
        metadata_schema=metadata_schema
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Errore nella creazione dell'entità")
    
    # Salva le entità
    entity_manager.save_entities("config/entities.json")
    
    # Restituisci l'entità creata
    return EntityTypeInfo(
        name=entity.name,
        display_name=entity.display_name,
        category=entity.category,
        color=entity.color,
        metadata_fields=entity.metadata_fields
    )

@entity_router.put("/{entity_name}", response_model=EntityTypeInfo)
async def update_entity(
    entity_name: str = Path(..., description="Nome identificativo dell'entità"),
    entity: EntityTypeUpdate = Body(...),
    entity_manager: DynamicEntityManager = Depends(get_entity_manager_dep)
):
    """Aggiorna una definizione di entità esistente."""
    # Verifica se l'entità esiste
    if not entity_manager.entity_type_exists(entity_name):
        raise HTTPException(status_code=404, detail=f"Entità {entity_name} non trovata")
    
    # Converti dal formato API al formato interno (solo se fornito)
    metadata_schema = None
    if entity.metadata_fields is not None:
        metadata_schema = {}
        for field in entity.metadata_fields:
            metadata_schema[field.name] = field.field_type
    
    # Aggiorna l'entità
    success = entity_manager.update_entity_type(
        name=entity_name,
        display_name=entity.display_name,
        color=entity.color,
        metadata_schema=metadata_schema
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Errore nell'aggiornamento dell'entità")
    
    # Salva le entità
    entity_manager.save_entities("config/entities.json")