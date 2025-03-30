"""
Modulo per l'aggiornamento dell'API con il supporto per la gestione dinamica delle entità.
"""

import os
import logging
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import app as original_app
from .entity_manager import get_entity_manager
from .dynamic_ner import DynamicNERGiuridico
from .entity_api import entity_router

# Configurazione del logger
logger = logging.getLogger("NER-Giuridico.API")

# Inizializza il sistema NER dinamico
ner_system = DynamicNERGiuridico("config/entities.json")

# Aggiungi il router per la gestione delle entità
original_app.include_router(entity_router)

# Aggiungi un endpoint per ottenere la configurazione di Label Studio
@original_app.get("/api/v1/annotation/config")
async def get_annotation_config(format: str = "label-studio"):
    """
    Ottiene la configurazione per l'annotatore nel formato specificato.
    
    Args:
        format: Formato della configurazione ("label-studio", "doccano", etc.)
        
    Returns:
        Configurazione dell'annotatore
    """
    entity_manager = get_entity_manager()
    config = entity_manager.get_entity_label_config(format)
    return {"config": config}

# Monta l'applicazione di gestione delle entità
try:
    # Verifica se la directory delle pagine statiche esiste
    static_dir = os.path.join(os.path.dirname(__file__), "../static/entity-manager")
    if os.path.exists(static_dir):
        # Monta le pagine statiche
        original_app.mount("/entity-manager", StaticFiles(directory=static_dir, html=True), name="entity-manager")
        logger.info(f"Montata l'applicazione di gestione delle entità da {static_dir}")
except Exception as e:
    logger.error(f"Errore nel montare l'applicazione di gestione delle entità: {e}")

# Sostituisci il sistema NER nell'endpoint di riconoscimento
@original_app.post("/api/v1/recognize")
async def recognize_entities_dynamic(request_body: Dict[str, Any]):
    """
    Riconosce entità giuridiche in un testo utilizzando il sistema NER dinamico.
    
    Args:
        request_body: Dizionario con il testo da analizzare
        
    Returns:
        Risultato del riconoscimento
    """
    try:
        # Estrai il testo dalla richiesta
        text = request_body.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="Il testo è obbligatorio")
        
        # Processa il testo
        result = ner_system.process(text)
        
        return result
    except Exception as e:
        logger.error(f"Errore nel riconoscimento delle entità: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Sostituisci il sistema NER nell'endpoint di riconoscimento batch
@original_app.post("/api/v1/batch")
async def batch_recognize_entities_dynamic(request_body: Dict[str, Any]):
    """
    Riconosce entità giuridiche in più testi utilizzando il sistema NER dinamico.
    
    Args:
        request_body: Dizionario con i testi da analizzare
        
    Returns:
        Lista di risultati del riconoscimento
    """
    try:
        # Estrai i testi dalla richiesta
        texts = request_body.get("texts", [])
        if not texts:
            raise HTTPException(status_code=400, detail="La lista dei testi è obbligatoria")
        
        # Processa i testi
        results = ner_system.batch_process(texts)
        
        return results
    except Exception as e:
        logger.error(f"Errore nel riconoscimento batch delle entità: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Crea un nuovo endpoint per testare il riconoscimento con un'entità specifica
@original_app.post("/api/v1/test-entity-recognition")
async def test_entity_recognition(request_body: Dict[str, Any]):
    """
    Testa il riconoscimento di un'entità specifica.
    
    Args:
        request_body: Dizionario con il testo da analizzare e il tipo di entità da testare
        
    Returns:
        Risultato del riconoscimento filtrato per l'entità specificata
    """
    try:
        # Estrai il testo e il tipo di entità dalla richiesta
        text = request_body.get("text", "")
        entity_type = request_body.get("entity_type", "")
        
        if not text:
            raise HTTPException(status_code=400, detail="Il testo è obbligatorio")
        
        if not entity_type:
            raise HTTPException(status_code=400, detail="Il tipo di entità è obbligatorio")
        
        # Verifica che il tipo di entità esista
        entity_manager = get_entity_manager()
        if not entity_manager.entity_type_exists(entity_type):
            raise HTTPException(status_code=404, detail=f"Il tipo di entità {entity_type} non esiste")
        
        # Processa il testo
        result = ner_system.process(text)
        
        # Filtra le entità per il tipo specificato
        filtered_entities = [
            entity for entity in result["entities"]
            if entity["type"] == entity_type
        ]
        
        # Crea un risultato filtrato
        filtered_result = {
            "text": text,
            "entity_type": entity_type,
            "entities": filtered_entities,
            "count": len(filtered_entities)
        }
        
        return filtered_result
    
    except Exception as e:
        logger.error(f"Errore nel test di riconoscimento dell'entità: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Crea un endpoint per ottenere statistiche sulle entità riconosciute
@original_app.post("/api/v1/entity-statistics")
async def get_entity_statistics(request_body: Dict[str, Any]):
    """
    Ottiene statistiche sulle entità riconosciute in un corpus di testi.
    
    Args:
        request_body: Dizionario con i testi da analizzare
        
    Returns:
        Statistiche sulle entità riconosciute
    """
    try:
        # Estrai i testi dalla richiesta
        texts = request_body.get("texts", [])
        if not texts:
            raise HTTPException(status_code=400, detail="La lista dei testi è obbligatoria")
        
        # Processa i testi
        results = ner_system.batch_process(texts)
        
        # Raccogli le statistiche
        entity_counts = {}
        entity_examples = {}
        total_entities = 0
        
        for i, result in enumerate(results):
            for entity in result["entities"]:
                entity_type = entity["type"]
                
                # Incrementa il contatore per questo tipo di entità
                if entity_type not in entity_counts:
                    entity_counts[entity_type] = 0
                    entity_examples[entity_type] = []
                
                entity_counts[entity_type] += 1
                total_entities += 1
                
                # Aggiungi un esempio se ne abbiamo meno di 5
                if len(entity_examples[entity_type]) < 5:
                    entity_examples[entity_type].append({
                        "text": entity["text"],
                        "normalized_text": entity.get("normalized_text", entity["text"]),
                        "document_index": i
                    })
        
        # Ottieni informazioni sui tipi di entità
        entity_types = {}
        for entity_type in entity_counts.keys():
            info = entity_manager.get_entity_type(entity_type)
            if info:
                entity_types[entity_type] = {
                    "display_name": info.get("display_name", entity_type),
                    "category": info.get("category", "custom"),
                    "color": info.get("color", "#CCCCCC")
                }
            else:
                entity_types[entity_type] = {
                    "display_name": entity_type,
                    "category": "unknown",
                    "color": "#CCCCCC"
                }
        
        # Crea le statistiche
        statistics = {
            "total_documents": len(texts),
            "total_entities": total_entities,
            "entity_counts": entity_counts,
            "entity_types": entity_types,
            "entity_examples": entity_examples,
            "entity_density": total_entities / len(texts) if texts else 0
        }
        
        return statistics
    
    except Exception as e:
        logger.error(f"Errore nel calcolo delle statistiche sulle entità: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint per aggiornare o rigenerare le regole rule-based
@original_app.post("/api/v1/regenerate-rules")
async def regenerate_rules(request_body: Dict[str, Any]):
    """
    Aggiorna o rigenera le regole rule-based per un tipo di entità.
    
    Args:
        request_body: Dizionario con il tipo di entità e i parametri per la generazione
        
    Returns:
        Risultato dell'aggiornamento
    """
    try:
        # Estrai i parametri dalla richiesta
        entity_type = request_body.get("entity_type")
        patterns = request_body.get("patterns", [])
        
        if not entity_type:
            raise HTTPException(status_code=400, detail="Il tipo di entità è obbligatorio")
        
        # Verifica che il tipo di entità esista
        entity_manager = get_entity_manager()
        if not entity_manager.entity_type_exists(entity_type):
            raise HTTPException(status_code=404, detail=f"Il tipo di entità {entity_type} non esiste")
        
        # Ottieni il riconoscitore rule-based
        rule_recognizer = ner_system.rule_based_recognizer
        
        # Aggiorna i pattern per il tipo di entità
        # Nota: questa è una implementazione di esempio, da adattare al tuo riconoscitore
        category = entity_manager.get_entity_type(entity_type).get("category", "custom")
        
        # Determina il sottotipo in base alla categoria e al nome dell'entità
        if category == "normative":
            subtype = entity_type.lower()
        elif category == "jurisprudence":
            subtype = entity_type.lower()
        elif category == "concepts":
            subtype = "concetti_giuridici"
        else:
            subtype = "custom_entities"
        
        # Aggiorna le regole (questo è un esempio generico)
        # Nella realtà, dipende da come è implementato il tuo rule-based recognizer
        updated = False
        
        # Se il riconoscitore ha un attributo per aggiornare i pattern a runtime
        if hasattr(rule_recognizer, 'update_patterns'):
            updated = rule_recognizer.update_patterns(subtype, patterns)
        
        # Restituisci il risultato
        return {
            "entity_type": entity_type,
            "updated": updated,
            "patterns_count": len(patterns) if patterns else 0
        }
    
    except Exception as e:
        logger.error(f"Errore nell'aggiornamento delle regole: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint per l'integrazione con l'annotation tool
@original_app.post("/api/v1/annotation/import")
async def import_annotations(request_body: Dict[str, Any]):
    """
    Importa annotazioni per migliorare il modello NER.
    
    Args:
        request_body: Dizionario con le annotazioni
        
    Returns:
        Risultato dell'importazione
    """
    try:
        # Estrai i parametri dalla richiesta
        annotations = request_body.get("annotations", [])
        
        if not annotations:
            raise HTTPException(status_code=400, detail="Le annotazioni sono obbligatorie")
        
        # Implementazione di esempio: aggiungi entità dinamiche basate sulle annotazioni
        added_entities = []
        
        for annotation in annotations:
            entity_type = annotation.get("entity_type")
            if entity_type and entity_type.startswith("NEW_"):
                # Crea una nuova entità dinamica
                display_name = annotation.get("display_name", entity_type)
                category = annotation.get("category", "custom")
                color = annotation.get("color", "#CCCCCC")
                
                # Crea uno schema di metadati basato sugli attributi annotati
                metadata_schema = {}
                for key, value in annotation.get("attributes", {}).items():
                    # Determina il tipo basato sul valore
                    if isinstance(value, bool):
                        field_type = "boolean"
                    elif isinstance(value, (int, float)):
                        field_type = "number"
                    else:
                        field_type = "string"
                    
                    metadata_schema[key] = field_type
                
                # Aggiungi l'entità al sistema
                if not entity_manager.entity_type_exists(entity_type):
                    success = ner_system.add_entity_type(
                        name=entity_type,
                        display_name=display_name,
                        category=category,
                        color=color,
                        metadata_schema=metadata_schema
                    )
                    
                    if success:
                        added_entities.append(entity_type)
        
        # Restituisci il risultato
        return {
            "imported_annotations": len(annotations),
            "added_entities": added_entities,
            "success": True
        }
    
    except Exception as e:
        logger.error(f"Errore nell'importazione delle annotazioni: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Funzione principale per avviare il server
def start_server():
    """Avvia il server API."""
    # Qui puoi aggiungere ulteriori configurazioni se necessario
    
    # Utilizza la funzione originale per avviare il server
    from .api import start_server as original_start_server
    original_start_server()