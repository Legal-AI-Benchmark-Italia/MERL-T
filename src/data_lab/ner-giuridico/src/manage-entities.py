#!/usr/bin/env python3
"""
Script per avviare l'interfaccia di gestione delle entità per il sistema NER-Giuridico.
"""

import os
import sys
import logging
import uvicorn
from pathlib import Path

# Configura il logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('entity_manager.log')
    ]
)

logger = logging.getLogger(__name__)

def find_project_root():
    """Trova la directory root del progetto."""
    current_dir = Path(__file__).resolve().parent
    
    # Se siamo già nella directory src, il parent è la root
    if current_dir.name == 'src':
        return current_dir.parent
    
    # Altrimenti, cerchiamo la directory che contiene sia 'src' che 'config'
    while current_dir != current_dir.parent:
        if (current_dir / 'src').exists() and (current_dir / 'config').exists():
            return current_dir
        current_dir = current_dir.parent
    
    # Se non troviamo una struttura corrispondente, usiamo la directory corrente
    logger.warning("Non è stato possibile determinare la root del progetto. Usando la directory corrente.")
    return Path(__file__).resolve().parent

def setup_template_paths(app):
    """Configura i percorsi per i template e i file statici."""
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    
    # Percorso dei template e dei file statici
    template_dir = Path(__file__).resolve().parent / "entities" / "templates"
    static_dir = Path(__file__).resolve().parent / "entities" / "static"
    
    # Se le directory non esistono, crea directory temporanee
    template_dir.mkdir(parents=True, exist_ok=True)
    static_dir.mkdir(parents=True, exist_ok=True)
    
    # Monta i file statici
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # Restituisci i template
    return Jinja2Templates(directory=str(template_dir))

def copy_admin_template():
    """Copia il template di amministrazione nella directory dei template se necessario."""
    import shutil
    
    source_file = Path(__file__).resolve().parent / "entities" / "entity-admin.html"
    target_dir = Path(__file__).resolve().parent / "entities" / "templates"
    target_file = target_dir / "entity-admin.html"
    
    # Crea la directory dei template se non esiste
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Se il file source esiste e il file target non esiste o è diverso, copialo
    if source_file.exists() and (not target_file.exists() or not files_are_identical(source_file, target_file)):
        shutil.copy2(source_file, target_file)
        logger.info(f"Template di amministrazione copiato in {target_file}")
    elif not source_file.exists():
        # Se il file source non esiste, crea un template di base
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write("""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NER-Giuridico - Gestione Entità</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="/static/css/entity-manager.css" rel="stylesheet">
</head>
<body>
    <div class="container mt-4">
        <h1>Gestione Entità NER-Giuridico</h1>
        <p>Interfaccia di gestione delle entità per il sistema NER-Giuridico.</p>
        
        <div class="alert alert-info">
            <p>Per utilizzare l'interfaccia completa, copia il file entity-admin.html nella directory src/entities/templates.</p>
        </div>
        
        <div class="mb-4">
            <h2>API Endpoints Disponibili</h2>
            <ul>
                <li><code>GET /api/v1/entities/</code> - Lista tutte le entità</li>
                <li><code>GET /api/v1/entities/?category=normative</code> - Filtra le entità per categoria</li>
                <li><code>GET /api/v1/entities/{entity_name}</code> - Dettagli di un'entità specifica</li>
                <li><code>POST /api/v1/entities/</code> - Crea una nuova entità</li>
                <li><code>PUT /api/v1/entities/{entity_name}</code> - Aggiorna un'entità esistente</li>
                <li><code>DELETE /api/v1/entities/{entity_name}</code> - Elimina un'entità</li>
            </ul>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0-alpha1/dist/js/bootstrap.bundle.min.js"></script>
    <script src="/static/js/entity-manager.js"></script>
</body>
</html>""")
        logger.info(f"Creato template di amministrazione base in {target_file}")

def files_are_identical(file1, file2):
    """Verifica se due file sono identici."""
    import filecmp
    return filecmp.cmp(file1, file2)

def setup_api_routes(app):
    """Configura le rotte API per la gestione delle entità."""
    from fastapi import Request, HTTPException
    from fastapi.responses import HTMLResponse
    
    # Ottieni i template configurati
    templates = setup_template_paths(app)
    
    # Endpoint per la pagina di amministrazione delle entità
    @app.get("/admin/entities", response_class=HTMLResponse)
    async def admin_entities(request: Request):
        """Pagina di amministrazione delle entità."""
        return templates.TemplateResponse("entity-admin.html", {"request": request})
    
    # Assicurati che la pagina di amministrazione esista
    copy_admin_template()
    
    # Qui puoi aggiungere tutti gli endpoint API per la gestione delle entità
    # come descritto nella risposta precedente
    
    logger.info("Route API configurate correttamente")

def main():
    """Funzione principale per avviare il server."""
    try:
        # Trova la directory root del progetto
        project_root = find_project_root()
        
        # Assicurati che il percorso del progetto sia nel sys.path
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))
        
        logger.info(f"Directory root del progetto: {project_root}")
        
        # Importa i moduli necessari
        try:
            from api import app as api_app
            logger.info("Modulo API importato correttamente")
            app = api_app
        except ImportError:
            # Se non riesci a importare l'app esistente, crea una nuova app FastAPI
            from fastapi import FastAPI
            logger.warning("Impossibile importare il modulo API esistente. Creazione di una nuova app FastAPI.")
            app = FastAPI(title="NER-Giuridico Entity Manager", description="API per la gestione delle entità giuridiche")
        
        # Configura le rotte API
        setup_api_routes(app)
        
        # Avvia il server
        logger.info("Avvio dell'interfaccia di gestione delle entità...")
        logger.info("Accedi all'interfaccia web all'indirizzo http://localhost:8000/admin/entities")
        
        # Avvia il server uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
        
    except Exception as e:
        logger.error(f"Errore durante l'avvio del server: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()