"""
API FastAPI unificata per il modulo NER-Giuridico.
Gestisce sia il riconoscimento standard che quello dinamico,
supportando entità sia statiche che dinamiche.
"""

import os
import logging
from pathlib import Path
import time
import json
from typing import List, Dict, Any, Optional, Union

from fastapi import Body, FastAPI, HTTPException, BackgroundTasks, Request, APIRouter, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
import uvicorn
from prometheus_client import Counter, Histogram, start_http_server

# Import interni
from .config import config
from .ner import NERGiuridico, DynamicNERGiuridico
from .entities.entity_manager import get_entity_manager

# Configurazione del logger
logger = logging.getLogger(__name__)

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

class EntityRequest(BaseModel):
    name: str = Field(..., description="Nome identificativo dell'entità")
    display_name: str = Field(..., description="Nome visualizzato dell'entità")
    category: str = Field(..., description="Categoria dell'entità (normative, jurisprudence, concepts, custom)")
    color: str = Field(..., description="Colore dell'entità in formato esadecimale")
    metadata_schema: Dict[str, str] = Field(default_factory=dict, description="Schema dei metadati dell'entità")
    patterns: Optional[List[str]] = Field(default=None, description="Pattern regex per il riconoscimento")

class EntityUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, description="Nome visualizzato dell'entità")
    color: Optional[str] = Field(default=None, description="Colore dell'entità in formato esadecimale")
    metadata_schema: Optional[Dict[str, str]] = Field(default=None, description="Schema dei metadati dell'entità")
    patterns: Optional[List[str]] = Field(default=None, description="Pattern regex per il riconoscimento")

# Creazione dell'app e dei router
app = FastAPI(
    title="NER-Giuridico API",
    description="API per il riconoscimento di entità giuridiche in testi legali",
    version="0.1.0"
)

# Router per gli endpoint dell'API
api_router = APIRouter(prefix="/api/v1")

# Router per la gestione delle entità
entity_router = APIRouter(prefix="/api/v1/entities")

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

# Factory per le istanze NER
_ner_standard = None  # Singleton per NERGiuridico
_ner_dynamic = None   # Singleton per DynamicNERGiuridico

def get_ner_standard():
    """Ottiene l'istanza di NERGiuridico standard."""
    global _ner_standard
    if _ner_standard is None:
        _ner_standard = NERGiuridico()
    return _ner_standard

def get_ner_dynamic():
    """Ottiene l'istanza di DynamicNERGiuridico."""
    global _ner_dynamic
    if _ner_dynamic is None:
        entities_file = config.get("entities.entities_file", "config/entities.json")
        _ner_dynamic = DynamicNERGiuridico(entities_file=entities_file)
    return _ner_dynamic

def get_ner_system(dynamic: bool = False):
    """
    Factory method per ottenere il sistema NER appropriato.
    
    Args:
        dynamic: Se True, usa il sistema dinamico, altrimenti usa quello standard
        
    Returns:
        Istanza di NERGiuridico o DynamicNERGiuridico
    """
    if dynamic:
        return get_ner_dynamic()
    return get_ner_standard()

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

# Funzione per aggiornare le metriche delle entità
def update_entity_metrics(result: Dict[str, Any]):
    if not config.get("monitoring.prometheus.enable", True):
        return
    for entity in result.get("entities", []):
        entity_type = entity.get("type", "UNKNOWN")
        ENTITY_COUNT.labels(entity_type=entity_type).inc()

# Endpoints base dell'app
@app.get("/health")
async def health_check():
    """Verifica lo stato del servizio."""
    return {"status": "ok", "version": "0.1.0"}

@app.get("/")
async def root():
    """Pagina principale del servizio."""
    return {
        "name": "NER-Giuridico API",
        "description": "API per il riconoscimento di entità giuridiche in testi legali",
        "version": "0.1.0",
        "endpoints": {
            "api": "/api/v1",
            "documentation": "/docs",
            "entity_management": "/entity-manager"
        }
    }

# Endpoints principali dell'API
@api_router.post("/recognize")
async def recognize_entities(
    request: TextRequest,
    background_tasks: BackgroundTasks,
    dynamic: Optional[bool] = Query(None, description="Usa il sistema dinamico se True")
):
    """
    Riconosce entità giuridiche in un testo.
    
    Args:
        request: Testo da analizzare.
        dynamic: (Opzionale) Se True, usa il sistema dinamico.
    
    Returns:
        Risultato del riconoscimento.
    """
    try:
        logger.info(f"Richiesta di riconoscimento per un testo di {len(request.text)} caratteri")
        # Determina quale sistema NER utilizzare
        use_dynamic = dynamic
        if use_dynamic is None:
            use_dynamic = config.get("ner.dynamic_enabled", False)
            
        ner = get_ner_system(use_dynamic)
        result = ner.process(request.text)
        
        if config.get("monitoring.prometheus.enable", True):
            background_tasks.add_task(update_entity_metrics, result)
            
        return result
    except Exception as e:
        logger.error(f"Errore nel riconoscimento delle entità: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/batch")
async def batch_recognize_entities(
    request: BatchTextRequest,
    background_tasks: BackgroundTasks,
    dynamic: Optional[bool] = Query(None, description="Usa il sistema dinamico se True")
):
    """
    Riconosce entità giuridiche in un batch di testi.
    
    Args:
        request: Lista di testi da analizzare.
        dynamic: (Opzionale) Se True, usa il sistema dinamico.
    
    Returns:
        Lista di risultati del riconoscimento.
    """
    try:
        logger.info(f"Richiesta di riconoscimento batch per {len(request.texts)} testi")
        # Determina quale sistema NER utilizzare
        use_dynamic = dynamic
        if use_dynamic is None:
            use_dynamic = config.get("ner.dynamic_enabled", False)
            
        ner = get_ner_system(use_dynamic)
        results = ner.batch_process(request.texts)
        
        if config.get("monitoring.prometheus.enable", True):
            for result in results:
                background_tasks.add_task(update_entity_metrics, result)
                
        return results
    except Exception as e:
        logger.error(f"Errore nel riconoscimento batch delle entità: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    Riceve e gestisce il feedback sulle entità riconosciute.
    """
    try:
        logger.info(f"Ricevuto feedback per l'entità {feedback.entity_id}")
        # Implementazione del feedback da realizzare
        # TODO: Salvare il feedback e utilizzarlo per migliorare il sistema
        
        return {"status": "success", "message": "Feedback ricevuto con successo"}
    except Exception as e:
        logger.error(f"Errore nella gestione del feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/moe/preprocess")
async def moe_preprocess(
    request: TextRequest,
    dynamic: Optional[bool] = Query(None, description="Usa il sistema dinamico se True")
):
    """
    Preprocessa una query per il router MoE.
    """
    try:
        logger.info(f"Richiesta di preprocessing MoE per un testo di {len(request.text)} caratteri")
        # Determina quale sistema NER utilizzare
        use_dynamic = dynamic
        if use_dynamic is None:
            use_dynamic = config.get("ner.dynamic_enabled", False)
            
        ner = get_ner_system(use_dynamic)
        result = ner.process(request.text)
        
        # Crea il risultato nel formato richiesto da MoE
        moe_result = {
            "original_query": request.text,
            "entities": result.get("entities", []),
            "references": result.get("references", {}),
            "metadata": {"processed_by": "NER-Giuridico", "version": "0.1.0"}
        }
        
        return moe_result
    except Exception as e:
        logger.error(f"Errore nel preprocessing MoE: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/test-entity-recognition")
async def test_entity_recognition(
    text: str = Body(..., description="Testo da analizzare"),
    entity_type: str = Body(..., description="Tipo di entità da testare"),
    dynamic: bool = Body(True, description="Usa il sistema dinamico")
):
    """
    Testa il riconoscimento per un'entità specifica.
    """
    try:
        if not text:
            raise HTTPException(status_code=400, detail="Il testo è obbligatorio")
            
        if not entity_type:
            raise HTTPException(status_code=400, detail="Il tipo di entità è obbligatorio")
            
        # Usa sempre il sistema dinamico per questo test
        ner = get_ner_system(dynamic=True)
        
        # Verifica che il tipo di entità esista
        entity_manager = get_entity_manager()
        if not entity_manager.entity_type_exists(entity_type):
            raise HTTPException(status_code=404, detail=f"Il tipo di entità {entity_type} non esiste")
            
        # Processa il testo
        result = ner.process(text)
        
        # Filtra le entità per il tipo specificato
        filtered_entities = [
            entity for entity in result["entities"]
            if entity["type"] == entity_type
        ]
        
        return {
            "text": text,
            "entity_type": entity_type,
            "entities": filtered_entities,
            "count": len(filtered_entities)
        }
    except Exception as e:
        logger.error(f"Errore nel test di riconoscimento dell'entità: {e}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/entity-statistics")
async def get_entity_statistics(
    texts: List[str] = Body(..., description="Lista di testi da analizzare")
):
    """
    Ottiene statistiche sulle entità riconosciute in un corpus di testi.
    """
    try:
        if not texts:
            raise HTTPException(status_code=400, detail="La lista dei testi è obbligatoria")
            
        # Usa il sistema dinamico per le statistiche
        ner = get_ner_system(dynamic=True)
        results = ner.batch_process(texts)
        
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
        entity_manager = get_entity_manager()
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
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))

# Endpoints per la gestione delle entità
@entity_router.get("/")
async def get_entities(
    category: Optional[str] = Query(None, description="Filtra per categoria")
):
    """
    Ottiene la lista dei tipi di entità.
    
    Args:
        category: (Opzionale) Filtra per categoria (normative, jurisprudence, concepts, custom).
    
    Returns:
        Lista di tipi di entità.
    """
    try:
        # Usa il sistema dinamico per ottenere i tipi di entità
        ner = get_ner_system(dynamic=True)
        entities = ner.get_entity_types(category)
        return entities
    except Exception as e:
        logger.error(f"Errore nell'ottenimento dei tipi di entità: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@entity_router.get("/{entity_name}")
async def get_entity(
    entity_name: str
):
    """
    Ottiene le informazioni di un tipo di entità.
    
    Args:
        entity_name: Nome del tipo di entità.
    
    Returns:
        Informazioni sul tipo di entità.
    """
    try:
        entity_manager = get_entity_manager()
        entity = entity_manager.get_entity_type(entity_name)
        
        if not entity:
            raise HTTPException(status_code=404, detail=f"Entità {entity_name} non trovata")
            
        return {
            "name": entity_name,
            **entity
        }
    except Exception as e:
        logger.error(f"Errore nell'ottenimento dell'entità {entity_name}: {e}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))

@entity_router.post("/")
async def create_entity(
    entity: EntityRequest
):
    """
    Crea un nuovo tipo di entità.
    
    Args:
        entity: Dati del tipo di entità da creare.
    
    Returns:
        Risultato della creazione.
    """
    try:
        ner = get_ner_system(dynamic=True)
        success = ner.add_entity_type(
            name=entity.name,
            display_name=entity.display_name,
            category=entity.category,
            color=entity.color,
            metadata_schema=entity.metadata_schema,
            patterns=entity.patterns
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Impossibile creare l'entità {entity.name}")
            
        # Ottieni l'entità appena creata
        entity_manager = get_entity_manager()
        created_entity = entity_manager.get_entity_type(entity.name)
        
        return {
            "status": "success",
            "message": f"Entità {entity.name} creata con successo",
            "entity": {
                "name": entity.name,
                **created_entity
            }
        }
    except Exception as e:
        logger.error(f"Errore nella creazione dell'entità {entity.name}: {e}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))

@entity_router.put("/{entity_name}")
async def update_entity(
    entity_name: str,
    entity: EntityUpdateRequest
):
    """
    Aggiorna un tipo di entità esistente.
    
    Args:
        entity_name: Nome del tipo di entità da aggiornare.
        entity: Dati dell'entità da aggiornare.
    
    Returns:
        Risultato dell'aggiornamento.
    """
    try:
        ner = get_ner_system(dynamic=True)
        
        # Verifica che l'entità esista
        entity_manager = get_entity_manager()
        if not entity_manager.entity_type_exists(entity_name):
            raise HTTPException(status_code=404, detail=f"Entità {entity_name} non trovata")
            
        # Aggiorna l'entità
        success = ner.update_entity_type(
            name=entity_name,
            display_name=entity.display_name,
            color=entity.color,
            metadata_schema=entity.metadata_schema,
            patterns=entity.patterns
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Impossibile aggiornare l'entità {entity_name}")
            
        # Ottieni l'entità aggiornata
        updated_entity = entity_manager.get_entity_type(entity_name)
        
        return {
            "status": "success",
            "message": f"Entità {entity_name} aggiornata con successo",
            "entity": {
                "name": entity_name,
                **updated_entity
            }
        }
    except Exception as e:
        logger.error(f"Errore nell'aggiornamento dell'entità {entity_name}: {e}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))

@entity_router.delete("/{entity_name}")
async def delete_entity(
    entity_name: str
):
    """
    Elimina un tipo di entità.
    
    Args:
        entity_name: Nome del tipo di entità da eliminare.
    
    Returns:
        Risultato dell'eliminazione.
    """
    try:
        ner = get_ner_system(dynamic=True)
        
        # Verifica che l'entità esista
        entity_manager = get_entity_manager()
        if not entity_manager.entity_type_exists(entity_name):
            raise HTTPException(status_code=404, detail=f"Entità {entity_name} non trovata")
            
        # Verifica che l'entità non sia tra quelle predefinite
        entity_info = entity_manager.get_entity_type(entity_name)
        if entity_info.get("category") != "custom":
            raise HTTPException(status_code=400, detail=f"Non è possibile eliminare l'entità predefinita {entity_name}")
            
        # Elimina l'entità
        success = ner.remove_entity_type(entity_name)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Impossibile eliminare l'entità {entity_name}")
            
        return {
            "status": "success",
            "message": f"Entità {entity_name} eliminata con successo"
        }
    except Exception as e:
        logger.error(f"Errore nell'eliminazione dell'entità {entity_name}: {e}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))

@entity_router.post("/{entity_name}/patterns")
async def update_entity_patterns(
    entity_name: str,
    patterns: List[str] = Body(..., description="Lista di pattern regex")
):
    """
    Aggiorna i pattern regex di un tipo di entità.
    
    Args:
        entity_name: Nome del tipo di entità da aggiornare.
        patterns: Lista di pattern regex.
    
    Returns:
        Risultato dell'aggiornamento.
    """
    try:
        # Verifica che l'entità esista
        entity_manager = get_entity_manager()
        if not entity_manager.entity_type_exists(entity_name):
            raise HTTPException(status_code=404, detail=f"Entità {entity_name} non trovata")
            
        # Aggiorna i pattern
        ner = get_ner_system(dynamic=True)
        success = ner.update_entity_type(name=entity_name, patterns=patterns)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Impossibile aggiornare i pattern dell'entità {entity_name}")
            
        return {
            "status": "success",
            "message": f"Pattern dell'entità {entity_name} aggiornati con successo",
            "patterns_count": len(patterns)
        }
    except Exception as e:
        logger.error(f"Errore nell'aggiornamento dei pattern dell'entità {entity_name}: {e}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/annotation/config")
async def get_annotation_config(
    format: str = Query("label-studio", description="Formato della configurazione (label-studio, doccano)")
):
    """
    Ottiene la configurazione per gli strumenti di annotazione.
    
    Args:
        format: Formato della configurazione (label-studio, doccano).
    
    Returns:
        Configurazione per lo strumento di annotazione.
    """
    try:
        entity_manager = get_entity_manager()
        config = entity_manager.get_entity_label_config(format)
        
        return {
            "config": config
        }
    except Exception as e:
        logger.error(f"Errore nell'ottenimento della configurazione di annotazione: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint per l'interfaccia di gestione delle entità
@app.get("/entity-manager", response_class=HTMLResponse)
async def entity_manager_ui(request: Request):
    """Interfaccia web per la gestione delle entità."""
    # Verifica se esiste un template per l'interfaccia
    try:
        templates_path = Path(__file__).parent / "entities" / "templates"
        if templates_path.exists():
            templates = Jinja2Templates(directory=str(templates_path))
            return templates.TemplateResponse("entity-admin.html", {"request": request})
    except Exception as e:
        logger.error(f"Errore nel caricamento del template dell'interfaccia: {e}")
    
    # Se non esiste, restituisci un HTML basico
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>NER-Giuridico - Gestione Entità</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; }
            h1 { color: #2a5885; }
            a { color: #4a76a8; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1>NER-Giuridico - Gestione Entità</h1>
        <p>L'interfaccia web per la gestione delle entità non è disponibile.</p>
        <p>Puoi utilizzare gli endpoint API per gestire le entità:</p>
        <ul>
            <li><a href="/docs">/docs</a> - Documentazione API</li>
            <li><a href="/api/v1/entities">/api/v1/entities</a> - Lista delle entità</li>
        </ul>
    </body>
    </html>
    """

# Aggiungi i router all'app
app.include_router(api_router)
app.include_router(entity_router)

# Monta i file statici se disponibili
static_path = Path(__file__).parent / "entities" / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

def start_server():
    """Avvia il server API."""
    host = config.get("api.host", "0.0.0.0")
    port = config.get("api.port", 8000)
    workers = config.get("api.workers", 4)
    
    # Avvia il server Prometheus se abilitato
    if config.get("monitoring.prometheus.enable", True):
        prometheus_port = config.get("monitoring.prometheus.port", 9090)
        start_http_server(prometheus_port)
        logger.info(f"Server Prometheus avviato sulla porta {prometheus_port}")
    
    logger.info(f"Avvio del server API su {host}:{port} con {workers} workers")
    uvicorn.run("src.api:app", host=host, port=port, workers=workers)

if __name__ == "__main__":
    start_server()