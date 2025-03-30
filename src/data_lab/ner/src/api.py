"""
API FastAPI unificata per il modulo NER-Giuridico.
Gestisce sia il riconoscimento standard che quello dinamico,
oltre a fornire endpoint per feedback, statistiche, aggiornamento regole, ecc.
"""

import logging
import time
import os
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn
from prometheus_client import Counter, Histogram, start_http_server

# Import interni
from .config import config
from .ner import NERGiuridico
from .entities.dynamic_ner import DynamicNERGiuridico
from .entities.entity_manager import get_entity_manager
from .entities.entity_api import entity_router

# Configurazione del logger
logger = logging.getLogger(__name__)

# Inizializzazione dell'app FastAPI
app = FastAPI(
    title="NER-Giuridico API",
    description="API per il riconoscimento di entità giuridiche in testi legali",
    version="0.1.0"
)

# Configurazione CORS
cors_origins = config.get("api.cors.allow_origins", ["*"])
cors_methods = config.get("api.cors.allow_methods", ["GET", "POST"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=cors_methods,
    allow_headers=["*"],
)

# Inizializzazione dei sistemi NER (statico e dinamico)
ner_static = NERGiuridico()
ner_dynamic = DynamicNERGiuridico("config/entities.json")

# Metriche Prometheus
if config.get("monitoring.prometheus.enable", True):
    REQUEST_COUNT = Counter(
        'ner_giuridico_request_count', 
        'Numero totale di richieste', 
        ['endpoint', 'method']
    )
    REQUEST_LATENCY = Histogram(
        'ner_giuridico_request_latency_seconds', 
        'Latenza delle richieste in secondi',
        ['endpoint', 'method']
    )
    ENTITY_COUNT = Counter(
        'ner_giuridico_entity_count', 
        'Numero di entità riconosciute',
        ['entity_type']
    )

# Middleware per il monitoraggio
@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    if config.get("monitoring.prometheus.enable", True):
        endpoint = request.url.path
        method = request.method
        REQUEST_COUNT.labels(endpoint=endpoint, method=method).inc()
        start_time = time.time()
        response = await call_next(request)
        REQUEST_LATENCY.labels(endpoint=endpoint, method=method).observe(time.time() - start_time)
        return response
    return await call_next(request)

# Modelli Pydantic per la validazione dei dati
class TextRequest(BaseModel):
    text: str = Field(..., description="Testo da analizzare", min_length=1)
    options: Optional[Dict[str, Any]] = Field(default=None, description="Opzioni di elaborazione")

class BatchTextRequest(BaseModel):
    texts: List[str] = Field(..., description="Lista di testi da analizzare", min_items=1)
    options: Optional[Dict[str, Any]] = Field(default=None, description="Opzioni di elaborazione")

class FeedbackRequest(BaseModel):
    text: str = Field(..., description="Testo originale")
    entity_id: str = Field(..., description="ID dell'entità")
    correct: bool = Field(..., description="Se l'entità è stata riconosciuta correttamente")
    correct_text: Optional[str] = Field(default=None, description="Testo corretto dell'entità")
    correct_type: Optional[str] = Field(default=None, description="Tipo corretto dell'entità")
    notes: Optional[str] = Field(default=None, description="Note aggiuntive")

# Funzione ausiliaria per scegliere il sistema NER da utilizzare
def get_ner_system(dynamic: Optional[bool] = None):
    """
    Se dynamic è True (o se abilitato dalla configurazione) usa il sistema dinamico,
    altrimenti usa quello statico.
    """
    if dynamic is not None:
        return ner_dynamic if dynamic else ner_static
    if config.get("ner.dynamic_enabled", False):
        return ner_dynamic
    return ner_static

# Funzione per aggiornare le metriche delle entità
def update_entity_metrics(result: Dict[str, Any]):
    if not config.get("monitoring.prometheus.enable", True):
        return
    for entity in result.get("entities", []):
        entity_type = entity.get("type", "UNKNOWN")
        ENTITY_COUNT.labels(entity_type=entity_type).inc()

# ---------------------
# Endpoint API unificati
# ---------------------

@app.get("/health")
async def health_check():
    """Verifica lo stato del servizio."""
    return {"status": "ok", "version": "0.1.0"}

@app.post("/api/v1/recognize")
async def recognize_entities(
    request: TextRequest,
    background_tasks: BackgroundTasks,
    dynamic: Optional[bool] = None
):
    """
    Riconosce entità giuridiche in un testo.
    
    Parametri:
      - request: Testo da analizzare.
      - dynamic: (Opzionale) Forza l'uso del sistema dinamico se True.
    
    Restituisce il risultato del riconoscimento.
    """
    try:
        logger.info(f"Richiesta di riconoscimento per un testo di {len(request.text)} caratteri")
        ner = get_ner_system(dynamic)
        result = ner.process(request.text)
        if config.get("monitoring.prometheus.enable", True):
            background_tasks.add_task(update_entity_metrics, result)
        return result
    except Exception as e:
        logger.error(f"Errore nel riconoscimento delle entità: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/batch")
async def batch_recognize_entities(
    request: BatchTextRequest,
    background_tasks: BackgroundTasks,
    dynamic: Optional[bool] = None
):
    """
    Riconosce entità giuridiche in un batch di testi.
    
    Parametri:
      - request: Lista di testi da analizzare.
      - dynamic: (Opzionale) Forza l'uso del sistema dinamico se True.
    
    Restituisce la lista dei risultati.
    """
    try:
        logger.info(f"Richiesta di riconoscimento batch per {len(request.texts)} testi")
        ner = get_ner_system(dynamic)
        results = ner.batch_process(request.texts)
        if config.get("monitoring.prometheus.enable", True):
            for result in results:
                background_tasks.add_task(update_entity_metrics, result)
        return results
    except Exception as e:
        logger.error(f"Errore nel riconoscimento batch delle entità: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    Riceve e gestisce il feedback sulle entità riconosciute.
    """
    try:
        logger.info(f"Ricevuto feedback per l'entità {feedback.entity_id}")
        # Logica per salvare e utilizzare il feedback (da implementare)
        return {"status": "success", "message": "Feedback ricevuto con successo"}
    except Exception as e:
        logger.error(f"Errore nella gestione del feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/moe/preprocess")
async def moe_preprocess(request: TextRequest, dynamic: Optional[bool] = None):
    """
    Preprocessa una query per il router MoE.
    """
    try:
        logger.info(f"Richiesta di preprocessing MoE per un testo di {len(request.text)} caratteri")
        ner = get_ner_system(dynamic)
        result = ner.process(request.text)
        moe_result = {
            "original_query": request.text,
            "entities": result.get("entities", []),
            "references": result.get("references", []),
            "metadata": {"processed_by": "NER-Giuridico", "version": "0.1.0"}
        }
        return moe_result
    except Exception as e:
        logger.error(f"Errore nel preprocessing MoE: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------
# Endpoint specifici per il sistema dinamico e la gestione delle entità
# ---------------------

@app.get("/api/v1/annotation/config")
async def get_annotation_config(format: str = "label-studio"):
    """
    Ottiene la configurazione per l'annotatore nel formato specificato.
    """
    entity_manager = get_entity_manager()
    config_annotation = entity_manager.get_entity_label_config(format)
    return {"config": config_annotation}

# Monta le pagine statiche per la gestione delle entità se la directory esiste
static_dir = os.path.join(os.path.dirname(__file__), "../static/entity-manager")
if os.path.exists(static_dir):
    app.mount("/entity-manager", StaticFiles(directory=static_dir, html=True), name="entity-manager")
    logger.info(f"Montata l'applicazione di gestione delle entità da {static_dir}")

@app.post("/api/v1/test-entity-recognition")
async def test_entity_recognition(request_body: Dict[str, Any]):
    """
    Testa il riconoscimento per un'entità specifica.
    """
    try:
        text = request_body.get("text", "")
        entity_type = request_body.get("entity_type", "")
        if not text:
            raise HTTPException(status_code=400, detail="Il testo è obbligatorio")
        if not entity_type:
            raise HTTPException(status_code=400, detail="Il tipo di entità è obbligatorio")
        entity_manager = get_entity_manager()
        if not entity_manager.entity_type_exists(entity_type):
            raise HTTPException(status_code=404, detail=f"Il tipo di entità {entity_type} non esiste")
        # Utilizza il sistema dinamico per questo test
        result = ner_dynamic.process(text)
        filtered_entities = [entity for entity in result.get("entities", []) if entity.get("type") == entity_type]
        return {
            "text": text,
            "entity_type": entity_type,
            "entities": filtered_entities,
            "count": len(filtered_entities)
        }
    except Exception as e:
        logger.error(f"Errore nel test di riconoscimento dell'entità: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/entity-statistics")
async def get_entity_statistics(request_body: Dict[str, Any]):
    """
    Ottiene statistiche sulle entità riconosciute in un corpus di testi.
    """
    try:
        texts = request_body.get("texts", [])
        if not texts:
            raise HTTPException(status_code=400, detail="La lista dei testi è obbligatoria")
        results = ner_dynamic.batch_process(texts)
        entity_counts = {}
        entity_examples = {}
        total_entities = 0
        for i, result in enumerate(results):
            for entity in result.get("entities", []):
                etype = entity.get("type")
                entity_counts.setdefault(etype, 0)
                entity_examples.setdefault(etype, [])
                entity_counts[etype] += 1
                total_entities += 1
                if len(entity_examples[etype]) < 5:
                    entity_examples[etype].append({
                        "text": entity.get("text"),
                        "normalized_text": entity.get("normalized_text", entity.get("text")),
                        "document_index": i
                    })
        entity_manager = get_entity_manager()
        entity_types = {}
        for etype in entity_counts:
            info = entity_manager.get_entity_type(etype)
            entity_types[etype] = {
                "display_name": info.get("display_name", etype) if info else etype,
                "category": info.get("category", "custom") if info else "unknown",
                "color": info.get("color", "#CCCCCC") if info else "#CCCCCC"
            }
        statistics = {
            "total_documents": len(texts),
            "total_entities": total_entities,
            "entity_counts": entity_counts,
            "entity_types": entity_types,
            "entity_examples": entity_examples,
            "entity_density": total_entities / len(texts)
        }
        return statistics
    except Exception as e:
        logger.error(f"Errore nel calcolo delle statistiche sulle entità: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/regenerate-rules")
async def regenerate_rules(request_body: Dict[str, Any]):
    """
    Aggiorna o rigenera le regole rule-based per un tipo di entità.
    """
    try:
        entity_type = request_body.get("entity_type")
        patterns = request_body.get("patterns", [])
        if not entity_type:
            raise HTTPException(status_code=400, detail="Il tipo di entità è obbligatorio")
        entity_manager = get_entity_manager()
        if not entity_manager.entity_type_exists(entity_type):
            raise HTTPException(status_code=404, detail=f"Il tipo di entità {entity_type} non esiste")
        rule_recognizer = ner_dynamic.rule_based_recognizer
        category = entity_manager.get_entity_type(entity_type).get("category", "custom")
        subtype = (entity_type.lower() if category in ["normative", "jurisprudence"]
                   else "concetti_giuridici" if category == "concepts" else "custom_entities")
        updated = hasattr(rule_recognizer, 'update_patterns') and rule_recognizer.update_patterns(subtype, patterns)
        return {
            "entity_type": entity_type,
            "updated": updated,
            "patterns_count": len(patterns)
        }
    except Exception as e:
        logger.error(f"Errore nell'aggiornamento delle regole: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/annotation/import")
async def import_annotations(request_body: Dict[str, Any]):
    """
    Importa annotazioni per migliorare il modello NER.
    """
    try:
        annotations = request_body.get("annotations", [])
        if not annotations:
            raise HTTPException(status_code=400, detail="Le annotazioni sono obbligatorie")
        added_entities = []
        entity_manager = get_entity_manager()
        for annotation in annotations:
            entity_type = annotation.get("entity_type")
            if entity_type and entity_type.startswith("NEW_"):
                display_name = annotation.get("display_name", entity_type)
                category = annotation.get("category", "custom")
                color = annotation.get("color", "#CCCCCC")
                metadata_schema = {}
                for key, value in annotation.get("attributes", {}).items():
                    if isinstance(value, bool):
                        field_type = "boolean"
                    elif isinstance(value, (int, float)):
                        field_type = "number"
                    else:
                        field_type = "string"
                    metadata_schema[key] = field_type
                if not entity_manager.entity_type_exists(entity_type):
                    success = ner_dynamic.add_entity_type(
                        name=entity_type,
                        display_name=display_name,
                        category=category,
                        color=color,
                        metadata_schema=metadata_schema
                    )
                    if success:
                        added_entities.append(entity_type)
        return {
            "imported_annotations": len(annotations),
            "added_entities": added_entities,
            "success": True
        }
    except Exception as e:
        logger.error(f"Errore nell'importazione delle annotazioni: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Includi il router per la gestione dinamica delle entità (se presente)
app.include_router(entity_router)

# ---------------------
# Funzione per l'avvio del server
# ---------------------
def start_server():
    host = config.get("api.host", "0.0.0.0")
    port = config.get("api.port", 8000)
    workers = config.get("api.workers", 4)
    if config.get("monitoring.prometheus.enable", True):
        prometheus_port = config.get("monitoring.prometheus.port", 9090)
        start_http_server(prometheus_port)
        logger.info(f"Server Prometheus avviato sulla porta {prometheus_port}")
    logger.info(f"Avvio del server API su {host}:{port} con {workers} workers")
    uvicorn.run("ner_giuridico.src.api:app", host=host, port=port, workers=workers)

if __name__ == "__main__":
    start_server()
