"""
Modulo per l'interfaccia di annotazione dei dati per il sistema NER-Giuridico.
Fornisce funzionalità per l'annotazione di entità giuridiche nei testi.
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from .config import config

logger = logging.getLogger(__name__)

class AnnotationInterface:
    """
    Classe per la gestione dell'interfaccia di annotazione dei dati.
    Supporta l'integrazione con strumenti di annotazione come Label Studio.
    """
    
    def __init__(self):
        """Inizializza l'interfaccia di annotazione."""
        self.tool = config.get("annotation.tool", "label-studio")
        self.host = config.get("annotation.host", "0.0.0.0")
        self.port = config.get("annotation.port", 8080)
        self.data_dir = config.get("annotation.data_dir", "./data/annotation")
        self.export_format = config.get("annotation.export_format", "spacy")
        self.project_name = config.get("annotation.project_name", "NER-Giuridico")
        
        # Crea la directory dei dati se non esiste
        base_dir = Path(__file__).parent
        self.data_path = base_dir / self.data_dir
        self.data_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Interfaccia di annotazione inizializzata con lo strumento {self.tool}")
    
    def setup(self):
        """
        Configura l'ambiente di annotazione.
        Installa e configura lo strumento di annotazione scelto.
        """
        if self.tool == "label-studio":
            self._setup_label_studio()
        elif self.tool == "doccano":
            self._setup_doccano()
        elif self.tool == "prodigy":
            self._setup_prodigy()
        elif self.tool == "custom":
            self._setup_custom_interface()
        else:
            logger.error(f"Strumento di annotazione non supportato: {self.tool}")
            raise ValueError(f"Strumento di annotazione non supportato: {self.tool}")
    
    def _setup_label_studio(self):
        """
        Configura Label Studio per l'annotazione di entità giuridiche.
        """
        try:
            # Verifica se Label Studio è installato
            try:
                subprocess.run(["label-studio", "--version"], check=True, capture_output=True)
                logger.info("Label Studio è già installato")
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.info("Installazione di Label Studio in corso...")
                subprocess.run(["pip", "install", "label-studio"], check=True)
                logger.info("Label Studio installato con successo")
            
            # Crea la configurazione del progetto
            project_config = {
                "title": self.project_name,
                "description": "Annotazione di entità giuridiche per il sistema NER-Giuridico",
                "label_config": self._create_label_studio_config()
            }
            
            # Salva la configurazione del progetto
            config_path = self.data_path / "label_studio_config.json"
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(project_config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configurazione di Label Studio salvata in {config_path}")
            
            # Crea lo script di avvio
            start_script = self.data_path / "start_label_studio.sh"
            with open(start_script, 'w', encoding='utf-8') as f:
                f.write(f"""#!/bin/bash
export LABEL_STUDIO_BASE_DATA_DIR="{self.data_path}"
label-studio start --host {self.host} --port {self.port} --no-browser
""")
            
            # Rendi lo script eseguibile
            os.chmod(start_script, 0o755)
            
            logger.info(f"Script di avvio di Label Studio creato in {start_script}")
            logger.info(f"Per avviare Label Studio, esegui: {start_script}")
        
        except Exception as e:
            logger.error(f"Errore nella configurazione di Label Studio: {e}")
            raise
    
    def _create_label_studio_config(self) -> str:
        """
        Crea la configurazione XML per Label Studio.
        
        Returns:
            Configurazione XML per Label Studio.
        """
        return """
<View>
  <Header value="Annotazione di entità giuridiche"/>
  <Text name="text" value="$text"/>
  
  <Labels name="label" toName="text">
    <Label value="ARTICOLO_CODICE" background="#FFA39E"/>
    <Label value="LEGGE" background="#D4380D"/>
    <Label value="DECRETO" background="#FFC069"/>
    <Label value="REGOLAMENTO_UE" background="#AD8B00"/>
    <Label value="SENTENZA" background="#D3F261"/>
    <Label value="ORDINANZA" background="#389E0D"/>
    <Label value="CONCETTO_GIURIDICO" background="#5CDBD3"/>
  </Labels>
  
  <Relations>
    <Relation value="riferimento" />
    <Relation value="definizione" />
    <Relation value="applicazione" />
  </Relations>
</View>
"""
    
    def _setup_doccano(self):
        """
        Configura Doccano per l'annotazione di entità giuridiche.
        """
        try:
            # Verifica se Docker è installato
            try:
                subprocess.run(["docker", "--version"], check=True, capture_output=True)
                logger.info("Docker è già installato")
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.error("Docker non è installato. Installare Docker per utilizzare Doccano.")
                raise RuntimeError("Docker non è installato")
            
            # Crea il file docker-compose.yml
            docker_compose_path = self.data_path / "docker-compose.yml"
            with open(docker_compose_path, 'w', encoding='utf-8') as f:
                f.write(f"""version: '3'
services:
  doccano:
    image: doccano/doccano
    ports:
      - "{self.port}:{self.port}"
    environment:
      ADMIN_USERNAME: admin
      ADMIN_PASSWORD: password
      ADMIN_EMAIL: admin@example.com
      PORT: {self.port}
    command: ["--host", "{self.host}", "--port", "{self.port}"]
    volumes:
      - {self.data_path}:/data
""")
            
            # Crea lo script di avvio
            start_script = self.data_path / "start_doccano.sh"
            with open(start_script, 'w', encoding='utf-8') as f:
                f.write(f"""#!/bin/bash
cd "{self.data_path}"
docker-compose up
""")
            
            # Rendi lo script eseguibile
            os.chmod(start_script, 0o755)
            
            logger.info(f"Script di avvio di Doccano creato in {start_script}")
            logger.info(f"Per avviare Doccano, esegui: {start_script}")
            
            # Crea le istruzioni per la configurazione
            instructions_path = self.data_path / "doccano_setup_instructions.md"
            with open(instructions_path, 'w', encoding='utf-8') as f:
                f.write(f"""# Istruzioni per la configurazione di Doccano

1. Avvia Doccano eseguendo lo script `{start_script}`
2. Accedi all'interfaccia web all'indirizzo http://{self.host}:{self.port}
3. Utilizza le seguenti credenziali:
   - Username: admin
   - Password: password
4. Crea un nuovo progetto di tipo "Named Entity Recognition"
5. Configura le seguenti etichette:
   - ARTICOLO_CODICE
   - LEGGE
   - DECRETO
   - REGOLAMENTO_UE
   - SENTENZA
   - ORDINANZA
   - CONCETTO_GIURIDICO
6. Importa i dati da annotare
7. Inizia l'annotazione

Per esportare i dati annotati, utilizza il formato "JSONL" e poi converti i dati nel formato richiesto utilizzando lo script di conversione fornito.
""")
            
            logger.info(f"Istruzioni per la configurazione di Doccano create in {instructions_path}")
        
        except Exception as e:
            logger.error(f"Errore nella configurazione di Doccano: {e}")
            raise
    
    def _setup_prodigy(self):
        """
        Configura Prodigy per l'annotazione di entità giuridiche.
        """
        try:
            # Verifica se Prodigy è installato
            try:
                subprocess.run(["prodigy", "--version"], check=True, capture_output=True)
                logger.info("Prodigy è già installato")
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.error("Prodigy non è installato. Prodigy richiede una licenza commerciale.")
                logger.error("Visita https://prodi.gy/ per acquistare una licenza.")
                raise RuntimeError("Prodigy non è installato")
            
            # Crea la configurazione di Prodigy
            prodigy_config = {
                "theme": "basic",
                "batch_size": 10,
                "port": self.port,
                "host": self.host,
                "cors": True,
                "db": str(self.data_path / "prodigy.db"),
                "custom_theme": {
                    "labels": {
                        "ARTICOLO_CODICE": "#FFA39E",
                        "LEGGE": "#D4380D",
                        "DECRETO": "#FFC069",
                        "REGOLAMENTO_UE": "#AD8B00",
                        "SENTENZA": "#D3F261",
                        "ORDINANZA": "#389E0D",
                        "CONCETTO_GIURIDICO": "#5CDBD3"
                    }
                }
            }
            
            # Salva la configurazione di Prodigy
            config_path = self.data_path / "prodigy.json"
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(prodigy_config, f, indent=2, ensure_ascii=False)
            
            # Crea lo script di avvio
            start_script = self.data_path / "start_prodigy.sh"
            with open(start_script, 'w', encoding='utf-8') as f:
                f.write(f"""#!/bin/bash
export PRODIGY_HOME="{self.data_path}"
prodigy ner.manual {self.project_name} it_core_news_lg {self.data_path}/texts.jsonl --label ARTICOLO_CODICE,LEGGE,DECRETO,REGOLAMENTO_UE,SENTENZA,ORDINANZA,CONCETTO_GIURIDICO
""")
            
            # Rendi lo script eseguibile
            os.chmod(start_script, 0o755)
            
            logger.info(f"Script di avvio di Prodigy creato in {start_script}")
            logger.info(f"Per avviare Prodigy, esegui: {start_script}")
            
            # Crea le istruzioni per la preparazione dei dati
            instructions_path = self.data_path / "prodigy_data_instructions.md"
            with open(instructions_path, 'w', encoding='utf-8') as f:
                f.write(f"""# Istruzioni per la preparazione dei dati per Prodigy

1. Prepara i tuoi testi in formato JSONL con la seguente struttura:
   ```json
   {{"text": "Testo da annotare..."}}
   {{"text": "Altro testo da annotare..."}}
   ```

2. Salva il file come `{self.data_path}/texts.jsonl`

3. Avvia Prodigy eseguendo lo script `{start_script}`

4. Accedi all'interfaccia web all'indirizzo http://{self.host}:{self.port}

5. Inizia l'annotazione

Per esportare i dati annotati, utilizza il comando:
```
prodigy db-out {self.project_name} > {self.data_path}/annotated_data.jsonl
```
""")
            
            logger.info(f"Istruzioni per la preparazione dei dati per Prodigy create in {instructions_path}")
        
        except Exception as e:
            logger.error(f"Errore nella configurazione di Prodigy: {e}")
            raise
    
    def _setup_custom_interface(self):
        """
        Configura un'interfaccia di annotazione personalizzata.
        """
        try:
            # Crea la struttura delle directory
            templates_dir = self.data_path / "templates"
            static_dir = self.data_path / "static"
            data_dir = self.data_path / "data"
            
            templates_dir.mkdir(exist_ok=True)
            static_dir.mkdir(exist_ok=True)
            data_dir.mkdir(exist_ok=True)
            
            # Crea il file app.py per l'interfaccia Flask
            app_path = self.data_path / "app.py"
            with open(app_path, 'w', encoding='utf-8') as f:
                f.write(
                    """#!/usr/bin/env python3
import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Configurazione
DATA_DIR = 'data'
ENTITY_TYPES = [
    {"id": "CODICE", "name": "Codice", "color": "#FFA39E"},
    {"id": "LEGGE", "name": "Legge", "color": "#D4380D"},
    {"id": "DECRETO", "name": "Decreto", "color": "#FFC069"},
    {"id": "REGOLAMENTO_UE", "name": "Regolamento UE", "color": "#AD8B00"},
    {"id": "SENTENZA", "name": "Sentenza", "color": "#D3F261"},
    {"id": "ORDINANZA", "name": "Ordinanza", "color": "#389E0D"},
    {"id": "CONCETTO_GIURIDICO", "name": "Concetto Giuridico", "color": "#5CDBD3"}
]

def load_documents():
    documents = []
    try:
        documents_file = os.path.join(DATA_DIR, 'documents.json')
        if os.path.exists(documents_file):
            with open(documents_file, 'r', encoding='utf-8') as f:
                documents = json.load(f)
    except Exception as e:
        print(f"Errore nel caricamento dei documenti: {e}")
    return documents

def save_documents(documents):
    try:
        documents_file = os.path.join(DATA_DIR, 'documents.json')
        with open(documents_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Errore nel salvataggio dei documenti: {e}")

def load_annotations():
    annotations = {}
    try:
        annotations_file = os.path.join(DATA_DIR, 'annotations.json')
        if os.path.exists(annotations_file):
            with open(annotations_file, 'r', encoding='utf-8') as f:
                annotations = json.load(f)
    except Exception as e:
        print(f"Errore nel caricamento delle annotazioni: {e}")
    return annotations

def save_annotations(annotations):
    try:
        annotations_file = os.path.join(DATA_DIR, 'annotations.json')
        with open(annotations_file, 'w', encoding='utf-8') as f:
            json.dump(annotations, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Errore nel salvataggio delle annotazioni: {e}")

@app.route('/')
def index():
    documents = load_documents()
    return render_template('index.html', documents=documents)

@app.route('/annotate/<doc_id>')
def annotate(doc_id):
    documents = load_documents()
    annotations = load_annotations()
    
    document = None
    for doc in documents:
        if doc['id'] == doc_id:
            document = doc
            break
    
    if document is None:
        return redirect(url_for('index'))
    
    doc_annotations = annotations.get(doc_id, [])
    
    return render_template('annotate.html', 
                          document=document, 
                          annotations=doc_annotations,
                          entity_types=ENTITY_TYPES)

@app.route('/api/save_annotation', methods=['POST'])
def save_annotation():
    data = request.json
    doc_id = data.get('doc_id')
    annotation = data.get('annotation')
    
    if not doc_id or not annotation:
        return jsonify({"status": "error", "message": "Dati mancanti"}), 400
    
    annotations = load_annotations()
    
    if doc_id not in annotations:
        annotations[doc_id] = []
    
    # Aggiungi o aggiorna l'annotazione
    annotation_id = annotation.get('id')
    if annotation_id:
        # Aggiorna un'annotazione esistente
        for i, ann in enumerate(annotations[doc_id]):
            if ann.get('id') == annotation_id:
                annotations[doc_id][i] = annotation
                break
    else:
        # Aggiungi una nuova annotazione
        annotation['id'] = f"ann_{len(annotations[doc_id]) + 1}"
        annotations[doc_id].append(annotation)
    
    save_annotations(annotations)
    
    return jsonify({"status": "success", "annotation": annotation})

@app.route('/api/delete_annotation', methods=['POST'])
def delete_annotation():
    data = request.json
    doc_id = data.get('doc_id')
    annotation_id = data.get('annotation_id')
    
    if not doc_id or not annotation_id:
        return jsonify({"status": "error", "message": "Dati mancanti"}), 400
    
    annotations = load_annotations()
    
    if doc_id in annotations:
        annotations[doc_id] = [ann for ann in annotations[doc_id] if ann.get('id') != annotation_id]
        save_annotations(annotations)
    
    return jsonify({"status": "success"})

@app.route('/api/upload_document', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "Nessun file caricato"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "Nessun file selezionato"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_content = file.read().decode('utf-8')
        
        documents = load_documents()
        
        # Crea un nuovo documento
        doc_id = f"doc_{len(documents) + 1}"
        document = {
            "id": doc_id,
            "title": filename,
            "text": file_content
        }
        
        documents.append(document)
        save_documents(documents)
        
        return jsonify({"status": "success", "document": document})

@app.route('/api/export_annotations', methods=['GET'])
def export_annotations():
    format_type = request.args.get('format', 'json')
    
    annotations = load_annotations()
    documents = load_documents()
    
    if format_type == 'spacy':
        # Converti in formato spaCy
        spacy_data = []
        for doc_id, doc_annotations in annotations.items():
            # Trova il documento corrispondente
            document = None
            for doc in documents:
                if doc['id'] == doc_id:
                    document = doc
                    break
            
            if document:
                text = document['text']
                entities = []
                for ann in doc_annotations:
                    entities.append((
                        ann['start'],
                        ann['end'],
                        ann['type']
                    ))
                
                spacy_data.append({
                    "text": text,
                    "entities": entities
                })
        
        return jsonify(spacy_data)
    else:
        # Formato JSON predefinito
        return jsonify(annotations)

if __name__ == '__main__':
    # Assicurati che la directory dei dati esista
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Crea file vuoti se non esistono
    if not os.path.exists(os.path.join(DATA_DIR, 'documents.json')):
        with open(os.path.join(DATA_DIR, 'documents.json'), 'w', encoding='utf-8') as f:
            json.dump([], f)
    
    if not os.path.exists(os.path.join(DATA_DIR, 'annotations.json')):
        with open(os.path.join(DATA_DIR, 'annotations.json'), 'w', encoding='utf-8') as f:
            json.dump({}, f)
    
    app.run(host='0.0.0.0', port=8080, debug=True)
    """)
                
            
            # Crea i template HTML
            index_template = templates_dir / "index.html"
            with open(index_template, 'w', encoding='utf-8') as f:
                f.write("""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NER-Giuridico - Annotazione</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <header>
        <h1>NER-Giuridico - Interfaccia di Annotazione</h1>
    </header>
    
    <main>
        <section class="upload-section">
            <h2>Carica un nuovo documento</h2>
            <form id="upload-form" enctype="multipart/form-data">
                <input type="file" id="document-file" accept=".txt">
                <button type="submit">Carica</button>
            </form>
        </section>
        
        <section class="documents-section">
            <h2>Documenti disponibili</h2>
            <div class="documents-list">
                {% if documents %}
                    {% for doc in documents %}
                        <div class="document-item">
                            <h3>{{ doc.title }}</h3>
                            <p>{{ doc.text[:100] }}...</p>
                            <a href="{{ url_for('annotate', doc_id=doc.id) }}" class="annotate-btn">Annota</a>
                        </div>
                    {% endfor %}
                {% else %}
                    <p>Nessun documento disponibile. Carica un documento per iniziare.</p>
                {% endif %}
            </div>
        </section>
        
        <section class="export-section">
            <h2>Esporta annotazioni</h2>
            <div class="export-buttons">
                <button id="export-json">Esporta in JSON</button>
                <button id="export-spacy">Esporta in formato spaCy</button>
            </div>
        </section>
    </main>
    
    <footer>
        <p>&copy; 2025 NER-Giuridico</p>
    </footer>
    
    <script src="{{ url_for('static', filename='js/index.js') }}"></script>
</body>
</html>
""")
            
            annotate_template = templates_dir / "annotate.html"
            with open(annotate_template, 'w', encoding='utf-8') as f:
                f.write("""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NER-Giuridico - Annotazione</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <header>
        <h1>NER-Giuridico - Annotazione</h1>
        <nav>
            <a href="{{ url_for('index') }}">Torna alla lista</a>
        </nav>
    </header>
    
    <main>
        <section class="document-info">
            <h2>{{ document.title }}</h2>
        </section>
        
        <section class="annotation-area">
            <div class="entity-types">
                <h3>Tipi di entità</h3>
                <div class="entity-type-list">
                    {% for entity_type in entity_types %}
                        <div class="entity-type" data-type="{{ entity_type.id }}" style="background-color: {{ entity_type.color }}">
                            {{ entity_type.name }}
                        </div>
                    {% endfor %}
                </div>
                <div class="annotation-controls">
                    <button id="clear-selection">Annulla selezione</button>
                </div>
            </div>
            
            <div class="text-container">
                <div id="text-content" data-doc-id="{{ document.id }}">{{ document.text }}</div>
            </div>
            
            <div class="annotations-list">
                <h3>Annotazioni</h3>
                <div id="annotations-container">
                    {% if annotations %}
                        {% for annotation in annotations %}
                            <div class="annotation-item" data-id="{{ annotation.id }}">
                                <span class="annotation-text">{{ annotation.text }}</span>
                                <span class="annotation-type" style="background-color: {{ entity_types|selectattr('id', 'equalto', annotation.type)|map(attribute='color')|first }}">
                                    {{ entity_types|selectattr('id', 'equalto', annotation.type)|map(attribute='name')|first }}
                                </span>
                                <button class="delete-annotation" data-id="{{ annotation.id }}">Elimina</button>
                            </div>
                        {% endfor %}
                    {% else %}
                        <p>Nessuna annotazione presente.</p>
                    {% endif %}
                </div>
            </div>
        </section>
    </main>
    
    <footer>
        <p>&copy; 2025 NER-Giuridico</p>
    </footer>
    
    <script src="{{ url_for('static', filename='js/annotate.js') }}"></script>
</body>
</html>
""")
            
            # Crea i file CSS e JavaScript
            css_dir = static_dir / "css"
            js_dir = static_dir / "js"
            
            css_dir.mkdir(exist_ok=True)
            js_dir.mkdir(exist_ok=True)
            
            style_css = css_dir / "style.css"
            with open(style_css, 'w', encoding='utf-8') as f:
                f.write("""/* Stili generali */
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f8f9fa;
}

header {
    background-color: #343a40;
    color: white;
    padding: 1rem;
    text-align: center;
}

header nav {
    margin-top: 0.5rem;
}

header nav a {
    color: white;
    text-decoration: none;
}

header nav a:hover {
    text-decoration: underline;
}

main {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
}

section {
    margin-bottom: 2rem;
    background-color: white;
    border-radius: 5px;
    padding: 1.5rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

h2 {
    margin-bottom: 1rem;
    color: #343a40;
}

h3 {
    margin-bottom: 0.5rem;
    color: #495057;
}

footer {
    text-align: center;
    padding: 1rem;
    background-color: #343a40;
    color: white;
}

/* Stili per la pagina principale */
.upload-section {
    margin-bottom: 2rem;
}

#upload-form {
    display: flex;
    gap: 1rem;
    align-items: center;
}

button {
    padding: 0.5rem 1rem;
    background-color: #007bff;
    color: white;
    border: none;
    border-radius: 3px;
    cursor: pointer;
    transition: background-color 0.2s;
}

button:hover {
    background-color: #0069d9;
}

.documents-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1rem;
}

.document-item {
    border: 1px solid #dee2e6;
    border-radius: 5px;
    padding: 1rem;
    transition: transform 0.2s;
}

.document-item:hover {
    transform: translateY(-3px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.annotate-btn {
    display: inline-block;
    margin-top: 0.5rem;
    padding: 0.3rem 0.8rem;
    background-color: #28a745;
    color: white;
    text-decoration: none;
    border-radius: 3px;
    transition: background-color 0.2s;
}

.annotate-btn:hover {
    background-color: #218838;
}

.export-buttons {
    display: flex;
    gap: 1rem;
}

/* Stili per la pagina di annotazione */
.annotation-area {
    display: grid;
    grid-template-columns: 250px 1fr 300px;
    gap: 1rem;
}

.entity-types {
    border-right: 1px solid #dee2e6;
    padding-right: 1rem;
}

.entity-type-list {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-bottom: 1rem;
}

.entity-type {
    padding: 0.5rem;
    border-radius: 3px;
    color: white;
    cursor: pointer;
    transition: transform 0.2s;
}

.entity-type:hover {
    transform: translateY(-2px);
}

.entity-type.selected {
    box-shadow: 0 0 0 2px #007bff;
}

.text-container {
    border: 1px solid #dee2e6;
    border-radius: 5px;
    padding: 1rem;
    background-color: #f8f9fa;
    height: 500px;
    overflow-y: auto;
}

#text-content {
    white-space: pre-wrap;
    line-height: 1.8;
}

.highlight {
    background-color: #ffff99;
}

.entity-highlight {
    padding: 2px 0;
    border-radius: 2px;
    color: white;
}

.annotations-list {
    border-left: 1px solid #dee2e6;
    padding-left: 1rem;
}

.annotation-item {
    margin-bottom: 0.5rem;
    padding: 0.5rem;
    border: 1px solid #dee2e6;
    border-radius: 3px;
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
}

.annotation-text {
    font-weight: bold;
}

.annotation-type {
    display: inline-block;
    padding: 0.2rem 0.5rem;
    border-radius: 3px;
    color: white;
    font-size: 0.8rem;
}

.delete-annotation {
    align-self: flex-end;
    padding: 0.2rem 0.5rem;
    background-color: #dc3545;
    color: white;
    border: none;
    border-radius: 3px;
    cursor: pointer;
    font-size: 0.8rem;
}

.delete-annotation:hover {
    background-color: #c82333;
}
""")
            
            index_js = js_dir / "index.js"
            with open(index_js, 'w', encoding='utf-8') as f:
                f.write("""document.addEventListener('DOMContentLoaded', function() {
    // Gestione del form di upload
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('document-file');
    
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const file = fileInput.files[0];
        if (!file) {
            alert('Seleziona un file da caricare');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        
        fetch('/api/upload_document', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Documento caricato con successo');
                window.location.reload();
            } else {
                alert('Errore: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Errore:', error);
            alert('Si è verificato un errore durante il caricamento');
        });
    });
    
    // Gestione dei pulsanti di esportazione
    const exportJsonBtn = document.getElementById('export-json');
    const exportSpacyBtn = document.getElementById('export-spacy');
    
    exportJsonBtn.addEventListener('click', function() {
        window.location.href = '/api/export_annotations?format=json';
    });
    
    exportSpacyBtn.addEventListener('click', function() {
        window.location.href = '/api/export_annotations?format=spacy';
    });
});
""")
            
            annotate_js = js_dir / "annotate.js"
            with open(annotate_js, 'w', encoding='utf-8') as f:
                f.write("""document.addEventListener('DOMContentLoaded', function() {
    const textContent = document.getElementById('text-content');
    const docId = textContent.dataset.docId;
    const entityTypes = document.querySelectorAll('.entity-type');
    const clearSelectionBtn = document.getElementById('clear-selection');
    const annotationsContainer = document.getElementById('annotations-container');
    
    let selectedType = null;
    let selection = null;
    
    // Carica le annotazioni esistenti
    const existingAnnotations = [];
    document.querySelectorAll('.annotation-item').forEach(item => {
        const id = item.dataset.id;
        const text = item.querySelector('.annotation-text').textContent;
        const type = item.querySelector('.annotation-type').textContent;
        existingAnnotations.push({ id, text, type });
    });
    
    // Evidenzia le annotazioni esistenti nel testo
    function highlightExistingAnnotations() {
        // Implementazione dell'evidenziazione delle annotazioni esistenti
    }
    
    // Gestione della selezione del tipo di entità
    entityTypes.forEach(entityType => {
        entityType.addEventListener('click', function() {
            // Rimuovi la selezione precedente
            entityTypes.forEach(et => et.classList.remove('selected'));
            
            // Seleziona il nuovo tipo
            this.classList.add('selected');
            selectedType = this.dataset.type;
        });
    });
    
    // Gestione della selezione del testo
    textContent.addEventListener('mouseup', function() {
        if (!selectedType) {
            alert('Seleziona prima un tipo di entità');
            return;
        }
        
        const selObj = window.getSelection();
        if (selObj.toString().trim() === '') {
            return;
        }
        
        // Ottieni l'intervallo di selezione
        const range = selObj.getRangeAt(0);
        const startOffset = range.startOffset;
        const endOffset = range.endOffset;
        
        // Crea l'annotazione
        const annotation = {
            start: startOffset,
            end: endOffset,
            text: selObj.toString(),
            type: selectedType
        };
        
        // Salva l'annotazione
        saveAnnotation(annotation);
    });
    
    // Funzione per salvare un'annotazione
    function saveAnnotation(annotation) {
        fetch('/api/save_annotation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                doc_id: docId,
                annotation: annotation
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Aggiungi l'annotazione alla lista
                addAnnotationToList(data.annotation);
                
                // Pulisci la selezione
                window.getSelection().removeAllRanges();
            } else {
                alert('Errore: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Errore:', error);
            alert('Si è verificato un errore durante il salvataggio dell\\'annotazione');
        });
    }
    
    // Funzione per aggiungere un'annotazione alla lista
    function addAnnotationToList(annotation) {
        // Trova il colore e il nome del tipo di entità
        let entityColor = '';
        let entityName = '';
        
        entityTypes.forEach(entityType => {
            if (entityType.dataset.type === annotation.type) {
                entityColor = entityType.style.backgroundColor;
                entityName = entityType.textContent.trim();
            }
        });
        
        // Crea l'elemento HTML per l'annotazione
        const annotationItem = document.createElement('div');
        annotationItem.className = 'annotation-item';
        annotationItem.dataset.id = annotation.id;
        
        annotationItem.innerHTML = `
            <span class="annotation-text">${annotation.text}</span>
            <span class="annotation-type" style="background-color: ${entityColor}">
                ${entityName}
            </span>
            <button class="delete-annotation" data-id="${annotation.id}">Elimina</button>
        `;
        
        // Aggiungi l'elemento alla lista
        annotationsContainer.appendChild(annotationItem);
        
        // Aggiungi l'evento per eliminare l'annotazione
        const deleteBtn = annotationItem.querySelector('.delete-annotation');
        deleteBtn.addEventListener('click', function() {
            deleteAnnotation(annotation.id);
        });
    }
    
    // Funzione per eliminare un'annotazione
    function deleteAnnotation(annotationId) {
        fetch('/api/delete_annotation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                doc_id: docId,
                annotation_id: annotationId
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Rimuovi l'annotazione dalla lista
                const annotationItem = document.querySelector(`.annotation-item[data-id="${annotationId}"]`);
                if (annotationItem) {
                    annotationItem.remove();
                }
            } else {
                alert('Errore: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Errore:', error);
            alert('Si è verificato un errore durante l\\'eliminazione dell\\'annotazione');
        });
    }
    
    // Gestione del pulsante per annullare la selezione
    clearSelectionBtn.addEventListener('click', function() {
        entityTypes.forEach(et => et.classList.remove('selected'));
        selectedType = null;
        window.getSelection().removeAllRanges();
    });
    
    // Gestione degli eventi di eliminazione per le annotazioni esistenti
    document.querySelectorAll('.delete-annotation').forEach(btn => {
        btn.addEventListener('click', function() {
            const annotationId = this.dataset.id;
            deleteAnnotation(annotationId);
        });
    });
});
""")
            
            # Crea lo script di avvio
            start_script = self.data_path / "start_custom_interface.sh"
            with open(start_script, 'w', encoding='utf-8') as f:
                f.write(f"""#!/bin/bash
cd "{self.data_path}"
python3 app.py
""")
            
            # Rendi lo script eseguibile
            os.chmod(start_script, 0o755)
            
            logger.info(f"Interfaccia di annotazione personalizzata creata in {self.data_path}")
            logger.info(f"Per avviare l'interfaccia, esegui: {start_script}")
            
            # Crea le istruzioni per l'utilizzo
            instructions_path = self.data_path / "custom_interface_instructions.md"
            with open(instructions_path, 'w', encoding='utf-8') as f:
                f.write(f"""# Istruzioni per l'utilizzo dell'interfaccia di annotazione personalizzata

1. Installa le dipendenze necessarie:
   ```
   pip install flask werkzeug
   ```

2. Avvia l'interfaccia eseguendo lo script `{start_script}`

3. Accedi all'interfaccia web all'indirizzo http://{self.host}:{self.port}

4. Carica un documento di testo da annotare

5. Seleziona un tipo di entità dalla lista a sinistra

6. Seleziona il testo che vuoi annotare

7. L'annotazione verrà salvata automaticamente

8. Per eliminare un'annotazione, clicca sul pulsante "Elimina" accanto all'annotazione

9. Per esportare le annotazioni, torna alla pagina principale e clicca su uno dei pulsanti di esportazione
""")
            
            logger.info(f"Istruzioni per l'utilizzo dell'interfaccia personalizzata create in {instructions_path}")
        
        except Exception as e:
            logger.error(f"Errore nella configurazione dell'interfaccia personalizzata: {e}")
            raise
    
    def convert_data(self, input_file: str, output_file: str, input_format: str, output_format: str):
        """
        Converte i dati annotati da un formato all'altro.
        
        Args:
            input_file: Percorso al file di input.
            output_file: Percorso al file di output.
            input_format: Formato del file di input.
            output_format: Formato del file di output.
        """
        try:
            # Leggi i dati di input
            with open(input_file, 'r', encoding='utf-8') as f:
                if input_format == 'json':
                    data = json.load(f)
                elif input_format == 'jsonl':
                    data = [json.loads(line) for line in f]
                else:
                    raise ValueError(f"Formato di input non supportato: {input_format}")
            
            # Converti i dati
            converted_data = None
            
            if input_format == 'json' and output_format == 'spacy':
                converted_data = self._convert_json_to_spacy(data)
            elif input_format == 'jsonl' and output_format == 'spacy':
                converted_data = self._convert_jsonl_to_spacy(data)
            elif input_format == 'json' and output_format == 'conll':
                converted_data = self._convert_json_to_conll(data)
            elif input_format == 'jsonl' and output_format == 'conll':
                converted_data = self._convert_jsonl_to_conll(data)
            else:
                raise ValueError(f"Conversione da {input_format} a {output_format} non supportata")
            
            # Scrivi i dati di output
            with open(output_file, 'w', encoding='utf-8') as f:
                if output_format == 'spacy':
                    json.dump(converted_data, f, indent=2, ensure_ascii=False)
                elif output_format == 'conll':
                    f.write(converted_data)
            
            logger.info(f"Dati convertiti da {input_format} a {output_format} e salvati in {output_file}")
        
        except Exception as e:
            logger.error(f"Errore nella conversione dei dati: {e}")
            raise
    
    def _convert_json_to_spacy(self, data):
        """
        Converte i dati dal formato JSON al formato spaCy.
        
        Args:
            data: Dati in formato JSON.
        
        Returns:
            Dati in formato spaCy.
        """
        # Implementazione della conversione
        pass
    
    def _convert_jsonl_to_spacy(self, data):
        """
        Converte i dati dal formato JSONL al formato spaCy.
        
        Args:
            data: Dati in formato JSONL.
        
        Returns:
            Dati in formato spaCy.
        """
        # Implementazione della conversione
        pass
    
    def _convert_json_to_conll(self, data):
        """
        Converte i dati dal formato JSON al formato CoNLL.
        
        Args:
            data: Dati in formato JSON.
        
        Returns:
            Dati in formato CoNLL.
        """
        # Implementazione della conversione
        pass
    
    def _convert_jsonl_to_conll(self, data):
        """
        Converte i dati dal formato JSONL al formato CoNLL.
        
        Args:
            data: Dati in formato JSONL.
        
        Returns:
            Dati in formato CoNLL.
        """
        # Implementazione della conversione
        pass
