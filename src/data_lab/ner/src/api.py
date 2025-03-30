"""
API FastAPI per il modulo NER-Giuridico.
Espone endpoint per il riconoscimento di entità giuridiche.
"""

import logging
import time
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from prometheus_client import Counter, Histogram, start_http_server

from .config import config
from .ner import NERGiuridico

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

# Inizializzazione del sistema NER-Giuridico
ner_giuridico = NERGiuridico()

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

# Middleware per il monitoraggio
@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    if config.get("monitoring.prometheus.enable", True):
        endpoint = request.url.path
        method = request.method
        
        # Incrementa il contatore delle richieste
        REQUEST_COUNT.labels(endpoint=endpoint, method=method).inc()
        
        # Misura la latenza
        start_time = time.time()
        response = await call_next(request)
        latency = time.time() - start_time
        
        REQUEST_LATENCY.labels(endpoint=endpoint, method=method).observe(latency)
        
        return response
    else:
        return await call_next(request)

# Endpoint per il controllo dello stato
@app.get("/health")
async def health_check():
    """Verifica lo stato del servizio."""
    return {"status": "ok", "version": "0.1.0"}

# Endpoint per il riconoscimento di entità in un testo
@app.post("/api/v1/recognize")
async def recognize_entities(request: TextRequest, background_tasks: BackgroundTasks):
    """
    Riconosce entità giuridiche in un testo.
    
    Args:
        request: Richiesta contenente il testo da analizzare.
        
    Returns:
        Risultato del riconoscimento.
    """
    try:
        logger.info(f"Richiesta di riconoscimento per un testo di {len(request.text)} caratteri")
        
        # Processa il testo
        result = ner_giuridico.process(request.text)
        
        # Aggiorna le metriche in background
        if config.get("monitoring.prometheus.enable", True):
            background_tasks.add_task(update_entity_metrics, result)
        
        return result
    
    except Exception as e:
        logger.error(f"Errore nel riconoscimento delle entità: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint per il riconoscimento di entità in batch
@app.post("/api/v1/batch")
async def batch_recognize_entities(request: BatchTextRequest, background_tasks: BackgroundTasks):
    """
    Riconosce entità giuridiche in un batch di testi.
    
    Args:
        request: Richiesta contenente i testi da analizzare.
        
    Returns:
        Lista di risultati del riconoscimento.
    """
    try:
        logger.info(f"Richiesta di riconoscimento batch per {len(request.texts)} testi")
        
        # Processa i testi in batch
        results = ner_giuridico.batch_process(request.texts)
        
        # Aggiorna le metriche in background
        if config.get("monitoring.prometheus.enable", True):
            for result in results:
                background_tasks.add_task(update_entity_metrics, result)
        
        return results
    
    except Exception as e:
        logger.error(f"Errore nel riconoscimento batch delle entità: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint per il feedback
@app.post("/api/v1/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    Riceve feedback sulle entità riconosciute.
    
    Args:
        feedback: Feedback sull'entità riconosciuta.
        
    Returns:
        Conferma di ricezione del feedback.
    """
    try:
        logger.info(f"Ricevuto feedback per l'entità {feedback.entity_id}")
        
        # Qui si potrebbe implementare la logica per salvare il feedback
        # e utilizzarlo per migliorare il modello
        
        return {"status": "success", "message": "Feedback ricevuto con successo"}
    
    except Exception as e:
        logger.error(f"Errore nella gestione del feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint per l'integrazione con il router MoE
@app.post("/api/v1/moe/preprocess")
async def moe_preprocess(request: TextRequest):
    """
    Preprocessa una query per il router MoE, identificando le entità giuridiche.
    
    Args:
        request: Richiesta contenente il testo da preprocessare.
        
    Returns:
        Risultato del preprocessing con entità riconosciute.
    """
    try:
        logger.info(f"Richiesta di preprocessing MoE per un testo di {len(request.text)} caratteri")
        
        # Processa il testo
        result = ner_giuridico.process(request.text)
        
        # Prepara il risultato per il router MoE
        moe_result = {
            "original_query": request.text,
            "entities": result["entities"],
            "references": result["references"],
            "metadata": {
                "processed_by": "NER-Giuridico",
                "version": "0.1.0"
            }
        }
        
        return moe_result
    
    except Exception as e:
        logger.error(f"Errore nel preprocessing MoE: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Funzione per aggiornare le metriche delle entità
def update_entity_metrics(result: Dict[str, Any]):
    """
    Aggiorna le metriche Prometheus per le entità riconosciute.
    
    Args:
        result: Risultato del riconoscimento.
    """
    if not config.get("monitoring.prometheus.enable", True):
        return
    
    for entity in result.get("entities", []):
        entity_type = entity.get("type", "UNKNOWN")
        ENTITY_COUNT.labels(entity_type=entity_type).inc()

# Funzione per avviare il server
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
    
    # Avvia il server API
    logger.info(f"Avvio del server API su {host}:{port} con {workers} workers")
    uvicorn.run("ner_giuridico.src.api:app", host=host, port=port, workers=workers)

if __name__ == "__main__":
    start_server()
