#!/usr/bin/env python3
"""
Interfaccia web per l'annotazione di entità giuridiche e la gestione dei tipi di entità.
File completo con implementazioni strutturate e robuste.
"""

import os
import sys
import json
import logging
import datetime
import importlib.util
import re
import time
from functools import wraps
from pathlib import Path
from typing import List, Dict, Any
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from werkzeug.utils import secure_filename

# -----------------------------------------------------------------------------
# Configurazione del logger
# -----------------------------------------------------------------------------
annotation_logger = logging.getLogger("annotator")
annotation_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
annotation_logger.addHandler(handler)

# -----------------------------------------------------------------------------
# Setup dell'ambiente
# -----------------------------------------------------------------------------
def setup_environment():
    current_dir = Path(__file__).resolve().parent
    annotation_logger.debug(f"Directory corrente: {current_dir}")
    annotation_logger.debug(f"sys.path attuale: {sys.path}")
    parent_dir = current_dir.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    project_root = parent_dir
    for _ in range(5):
        if (project_root / "ner_giuridico").exists() or (project_root / "config").exists():
            break
        project_root = project_root.parent
        if project_root == project_root.parent:
            break
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    annotation_logger.info(f"Root del progetto: {project_root}")
    return current_dir, project_root

current_dir, project_root = setup_environment()

# -----------------------------------------------------------------------------
# Importazione dei moduli necessari
# -----------------------------------------------------------------------------
try:
    # Prima prova: import diretto
    try:
        from ner_giuridico.entities.entity_manager import get_entity_manager
        from ner_giuridico.ner import DynamicNERGiuridico
        annotation_logger.info("Moduli importati direttamente")
    except ImportError as e:
        annotation_logger.warning(f"Impossibile importare direttamente: {e}")
        # Prova con importazione relativa
        try:
            from ..entities.entity_manager import get_entity_manager
            from ..ner import DynamicNERGiuridico
            annotation_logger.info("Moduli importati relativamente")
        except (ImportError, ValueError) as e:
            annotation_logger.warning(f"Impossibile importare relativamente: {e}")
            # Ultima risorsa: caricamento diretto dai file
            entity_manager_path = None
            ner_path = None
            for root, dirs, files in os.walk(project_root):
                if "entity_manager.py" in files:
                    entity_manager_path = os.path.join(root, "entity_manager.py")
                if "ner.py" in files:
                    ner_path = os.path.join(root, "ner.py")
            if entity_manager_path and ner_path:
                annotation_logger.info(f"Trovato entity_manager.py in {entity_manager_path}")
                annotation_logger.info(f"Trovato ner.py in {ner_path}")
                spec = importlib.util.spec_from_file_location("entity_manager", entity_manager_path)
                entity_manager_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(entity_manager_module)
                spec = importlib.util.spec_from_file_location("ner", ner_path)
                ner_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(ner_module)
                get_entity_manager = entity_manager_module.get_entity_manager
                DynamicNERGiuridico = ner_module.DynamicNERGiuridico
                annotation_logger.info("Moduli importati direttamente dai file")
            else:
                raise ImportError("Non è stato possibile trovare i moduli necessari")
    # Inizializza l'entity manager e carica i tipi di entità
    try:
        entity_manager = get_entity_manager()
        annotation_logger.info("Entity manager inizializzato con successo")
        if hasattr(entity_manager, 'db_path') and entity_manager.db_path:
            annotation_logger.debug(f"Database path: {entity_manager.db_path}")
            if os.path.exists(entity_manager.db_path):
                annotation_logger.debug(f"Il database delle entità esiste: {entity_manager.db_path}")
                if hasattr(entity_manager, '_get_db'):
                    try:
                        with entity_manager._get_db() as (conn, cursor):
                            cursor.execute("SELECT COUNT(*) FROM entities")
                            count = cursor.fetchone()[0]
                            annotation_logger.debug(f"Numero di entità nel database: {count}")
                    except Exception as e:
                        annotation_logger.warning(f"Errore nel conteggio delle entità: {e}")
            else:
                annotation_logger.debug(f"Il database delle entità non esiste: {entity_manager.db_path}")
        ENTITY_TYPES = []
        for name, info in entity_manager.get_all_entity_types().items():
            ENTITY_TYPES.append({
                "id": name,
                "name": info.get("display_name", name),
                "color": info.get("color", "#CCCCCC")
            })
        annotation_logger.info(f"Caricati {len(ENTITY_TYPES)} tipi di entità")
    except Exception as e:
        annotation_logger.error(f"Errore nell'inizializzazione dell'entity manager: {e}")
        annotation_logger.exception(e)
        # Fallback: tipi di entità predefiniti
        ENTITY_TYPES = [
            {"id": "ARTICOLO_CODICE", "name": "Articolo di Codice", "color": "#FFA39E"},
            {"id": "LEGGE", "name": "Legge", "color": "#D4380D"},
            {"id": "DECRETO", "name": "Decreto", "color": "#FFC069"},
            {"id": "REGOLAMENTO_UE", "name": "Regolamento UE", "color": "#AD8B00"},
            {"id": "SENTENZA", "name": "Sentenza", "color": "#D3F261"},
            {"id": "ORDINANZA", "name": "Ordinanza", "color": "#389E0D"},
            {"id": "CONCETTO_GIURIDICO", "name": "Concetto Giuridico", "color": "#5CDBD3"}
        ]
        annotation_logger.info("Utilizzando tipi di entità predefiniti")
except Exception as e:
    annotation_logger.error(f"Errore critico nell'importazione dei moduli: {e}")
    annotation_logger.exception(e)
    class DummyEntityManager:
        def get_entity_type(self, name):
            for entity in ENTITY_TYPES:
                if entity["id"] == name:
                    return entity
            return None
        def get_all_entity_types(self):
            return {entity["id"]: {"display_name": entity["name"], "color": entity["color"]} for entity in ENTITY_TYPES}
        def entity_type_exists(self, name):
            return any(entity["id"] == name for entity in ENTITY_TYPES)
    class DummyNER:
        def process(self, text):
            return {"entities": []}
    ENTITY_TYPES = [
        {"id": "ARTICOLO_CODICE", "name": "Articolo di Codice", "color": "#FFA39E"},
        {"id": "LEGGE", "name": "Legge", "color": "#D4380D"},
        {"id": "DECRETO", "name": "Decreto", "color": "#FFC069"},
        {"id": "REGOLAMENTO_UE", "name": "Regolamento UE", "color": "#AD8B00"},
        {"id": "SENTENZA", "name": "Sentenza", "color": "#D3F261"},
        {"id": "ORDINANZA", "name": "Ordinanza", "color": "#389E0D"},
        {"id": "CONCETTO_GIURIDICO", "name": "Concetto Giuridico", "color": "#5CDBD3"}
    ]
    DynamicNERGiuridico = DummyNER
    get_entity_manager = lambda: DummyEntityManager()
    annotation_logger.info("Utilizzando implementazioni fittizie a causa di errori di importazione")

# -----------------------------------------------------------------------------
# Inizializzazione dell'app Flask e configurazione
# -----------------------------------------------------------------------------
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

# Directory per i dati e i backup
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)
BACKUP_DIR = os.path.join(DATA_DIR, 'backup')
os.makedirs(BACKUP_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# Funzioni helper per la persistenza dei documenti e delle annotazioni
# -----------------------------------------------------------------------------
def load_documents() -> List[Dict[str, Any]]:
    documents_file = os.path.join(DATA_DIR, 'documents.json')
    if not os.path.exists(documents_file):
        save_documents([])
        return []
    try:
        with open(documents_file, 'r', encoding='utf-8') as f:
            documents = json.load(f)
        annotation_logger.debug(f"Caricati {len(documents)} documenti")
        return documents
    except json.JSONDecodeError:
        annotation_logger.error(f"Errore nella decodifica del file JSON: {documents_file}")
        backup_file = os.path.join(BACKUP_DIR, f'documents_corrupt_{int(datetime.datetime.now().timestamp())}.json')
        try:
            import shutil
            shutil.copy(documents_file, backup_file)
            annotation_logger.info(f"Backup del file corrotto salvato in: {backup_file}")
        except Exception as e:
            annotation_logger.warning(f"Impossibile creare backup: {e}")
        save_documents([])
        return []
    except Exception as e:
        annotation_logger.error(f"Errore nel caricamento dei documenti: {e}")
        return []

def save_documents(documents: List[Dict[str, Any]]) -> bool:
    documents_file = os.path.join(DATA_DIR, 'documents.json')
    if os.path.exists(documents_file):
        backup_file = os.path.join(BACKUP_DIR, f'documents_backup_{int(datetime.datetime.now().timestamp())}.json')
        try:
            import shutil
            shutil.copy(documents_file, backup_file)
            annotation_logger.debug(f"Backup creato: {backup_file}")
        except Exception as e:
            annotation_logger.warning(f"Impossibile creare backup: {e}")
    try:
        temp_file = f"{documents_file}.tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)
        os.replace(temp_file, documents_file)
        annotation_logger.debug(f"Salvati {len(documents)} documenti")
        return True
    except Exception as e:
        annotation_logger.error(f"Errore nel salvataggio dei documenti: {e}")
        return False

def load_annotations() -> Dict[str, List[Dict[str, Any]]]:
    annotations_file = os.path.join(DATA_DIR, 'annotations.json')
    if not os.path.exists(annotations_file):
        save_annotations({})
        return {}
    try:
        with open(annotations_file, 'r', encoding='utf-8') as f:
            annotations = json.load(f)
        total_annotations = sum(len(anns) for anns in annotations.values())
        annotation_logger.debug(f"Caricate {total_annotations} annotazioni per {len(annotations)} documenti")
        return annotations
    except json.JSONDecodeError:
        annotation_logger.error(f"Errore nella decodifica del file JSON: {annotations_file}")
        backup_file = os.path.join(BACKUP_DIR, f'annotations_corrupt_{int(datetime.datetime.now().timestamp())}.json')
        try:
            import shutil
            shutil.copy(annotations_file, backup_file)
            annotation_logger.info(f"Backup del file corrotto salvato in: {backup_file}")
        except Exception as e:
            annotation_logger.warning(f"Impossibile creare backup: {e}")
        save_annotations({})
        return {}
    except Exception as e:
        annotation_logger.error(f"Errore nel caricamento delle annotazioni: {e}")
        return {}

def save_annotations(annotations: Dict[str, List[Dict[str, Any]]]) -> bool:
    annotations_file = os.path.join(DATA_DIR, 'annotations.json')
    if os.path.exists(annotations_file):
        backup_file = os.path.join(BACKUP_DIR, f'annotations_backup_{int(datetime.datetime.now().timestamp())}.json')
        try:
            import shutil
            shutil.copy(annotations_file, backup_file)
            annotation_logger.debug(f"Backup creato: {backup_file}")
        except Exception as e:
            annotation_logger.warning(f"Impossibile creare backup: {e}")
    try:
        temp_file = f"{annotations_file}.tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(annotations, f, indent=2, ensure_ascii=False)
        os.replace(temp_file, annotations_file)
        total_annotations = sum(len(anns) for anns in annotations.values())
        annotation_logger.debug(f"Salvate {total_annotations} annotazioni per {len(annotations)} documenti")
        return True
    except Exception as e:
        annotation_logger.error(f"Errore nel salvataggio delle annotazioni: {e}")
        return False

def cleanup_backups(max_backups: int = 10):
    try:
        backup_files = {'documents': [], 'annotations': []}
        for filename in os.listdir(BACKUP_DIR):
            filepath = os.path.join(BACKUP_DIR, filename)
            if filename.startswith('documents_backup_'):
                backup_files['documents'].append((filepath, os.path.getmtime(filepath)))
            elif filename.startswith('annotations_backup_'):
                backup_files['annotations'].append((filepath, os.path.getmtime(filepath)))
        for key in backup_files:
            backup_files[key].sort(key=lambda x: x[1], reverse=True)
            if len(backup_files[key]) > max_backups:
                for filepath, _ in backup_files[key][max_backups:]:
                    os.remove(filepath)
                    annotation_logger.debug(f"Rimosso backup vecchio: {filepath}")
    except Exception as e:
        annotation_logger.error(f"Errore nella pulizia dei backup: {e}")

# -----------------------------------------------------------------------------
# Gestori di errori e middleware per il logging
# -----------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return jsonify({"status": "error", "message": "Risorsa non trovata"}), 404

@app.errorhandler(500)
def server_error(e):
    annotation_logger.error(f"Errore del server: {str(e)}")
    return jsonify({"status": "error", "message": "Errore interno del server"}), 500

@app.before_request
def log_request():
    annotation_logger.debug(f"Richiesta: {request.method} {request.path}")

@app.after_request
def log_response(response):
    annotation_logger.debug(f"Risposta: {response.status_code}")
    return response

# -----------------------------------------------------------------------------
# Endpoints per l'interfaccia di annotazione
# -----------------------------------------------------------------------------
@app.route('/')
def index():
    documents = load_documents()
    return render_template('index.html', documents=documents)

@app.route('/annotate/<doc_id>')
def annotate(doc_id):
    documents = load_documents()
    annotations = load_annotations()
    document = next((doc for doc in documents if doc['id'] == doc_id), None)
    if document is None:
        return redirect(url_for('index'))
    doc_annotations = annotations.get(doc_id, [])
    return render_template('annotate.html', document=document, annotations=doc_annotations, entity_types=ENTITY_TYPES)

@app.route('/api/save_annotation', methods=['POST'])
def save_annotation():
    try:
        data = request.json
        doc_id = data.get('doc_id')
        annotation = data.get('annotation')
        if not doc_id or not annotation:
            return jsonify({"status": "error", "message": "Dati mancanti"}), 400
        annotations = load_annotations()
        if doc_id not in annotations:
            annotations[doc_id] = []
        annotation_id = annotation.get('id')
        if annotation_id:
            for i, ann in enumerate(annotations[doc_id]):
                if ann.get('id') == annotation_id:
                    annotations[doc_id][i] = annotation
                    break
        else:
            annotation['id'] = f"ann_{len(annotations[doc_id]) + 1}"
            annotations[doc_id].append(annotation)
        save_annotations(annotations)
        cleanup_backups()
        return jsonify({"status": "success", "annotation": annotation})
    except Exception as e:
        annotation_logger.error(f"Errore nel salvataggio dell'annotazione: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/delete_annotation', methods=['POST'])
def delete_annotation():
    try:
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
    except Exception as e:
        annotation_logger.error(f"Errore nell'eliminazione dell'annotazione: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/upload_document', methods=['POST'])
def upload_document():
    try:
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "Nessun file caricato"}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({"status": "error", "message": "Nessun file selezionato"}), 400
        allowed_extensions = {'txt', 'md', 'html', 'xml', 'json', 'csv'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_ext not in allowed_extensions:
            return jsonify({"status": "error", "message": f"Formato file non supportato. Estensioni consentite: {', '.join(allowed_extensions)}"}), 400
        file_content = file.read().decode('utf-8')
        if len(file_content) > 1000000:
            return jsonify({"status": "error", "message": "Il documento è troppo grande. Il limite è di circa 1MB di testo."}), 400
        documents = load_documents()
        doc_id = f"doc_{len(documents) + 1}"
        document = {
            "id": doc_id,
            "title": secure_filename(file.filename),
            "text": file_content,
            "date_created": datetime.datetime.now().isoformat(),
            "word_count": len(file_content.split())
        }
        documents.append(document)
        save_documents(documents)
        return jsonify({"status": "success", "message": "Documento caricato con successo", "document": document})
    except UnicodeDecodeError:
        return jsonify({"status": "error", "message": "Impossibile decodificare il file. Assicurati che sia un file di testo valido in formato UTF-8."}), 400
    except Exception as e:
        annotation_logger.error(f"Errore nell'upload del documento: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/export_annotations', methods=['GET'])
def export_annotations():
    try:
        format_type = request.args.get('format', 'json')
        annotations = load_annotations()
        documents = load_documents()
        if format_type == 'spacy':
            spacy_data = []
            for doc_id, doc_annotations in annotations.items():
                document = next((doc for doc in documents if doc['id'] == doc_id), None)
                if document:
                    text = document['text']
                    entities = []
                    for ann in doc_annotations:
                        entities.append((ann['start'], ann['end'], ann['type']))
                    spacy_data.append({"text": text, "entities": entities})
            output_file = os.path.join(DATA_DIR, 'spacy_annotations.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(spacy_data, f, indent=2, ensure_ascii=False)
            if request.args.get('download', 'false').lower() == 'true':
                return send_file(output_file, as_attachment=True, download_name='spacy_annotations.json')
            return jsonify({"status": "success", "file": output_file, "data": spacy_data})
        else:
            if request.args.get('download', 'false').lower() == 'true':
                output_file = os.path.join(DATA_DIR, 'annotations_export.json')
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(annotations, f, indent=2, ensure_ascii=False)
                return send_file(output_file, as_attachment=True, download_name='annotations_export.json')
            return jsonify(annotations)
    except Exception as e:
        annotation_logger.error(f"Errore nell'esportazione delle annotazioni: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/recognize', methods=['POST'])
def recognize_entities():
    try:
        data = request.json
        text = data.get('text')
        if not text:
            return jsonify({"status": "error", "message": "Testo mancante"}), 400
        ner = DynamicNERGiuridico()
        result = ner.process(text)
        entities = []
        for entity in result.get("entities", []):
            entities.append({
                "start": entity["start_char"],
                "end": entity["end_char"],
                "text": entity["text"],
                "type": entity["type"]
            })
        return jsonify({"status": "success", "entities": entities})
    except Exception as e:
        annotation_logger.error(f"Errore nel riconoscimento delle entità: {e}")
        return jsonify({"status": "error", "message": f"Errore nel riconoscimento delle entità: {str(e)}"}), 500

@app.route('/api/train_model', methods=['POST'])
def train_model():
    try:
        annotations = load_annotations()
        documents = load_documents()
        ner_data = []
        for doc_id, doc_annotations in annotations.items():
            document = next((doc for doc in documents if doc['id'] == doc_id), None)
            if document:
                text = document['text']
                entities = []
                for ann in doc_annotations:
                    entities.append({
                        "text": ann['text'],
                        "type": ann['type'],
                        "start_char": ann['start'],
                        "end_char": ann['end']
                    })
                ner_data.append({"text": text, "entities": entities})
        output_file = os.path.join(DATA_DIR, 'ner_training_data.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(ner_data, f, indent=2, ensure_ascii=False)
        return jsonify({"status": "success", "message": "Dati di addestramento esportati con successo", "file": output_file, "count": len(ner_data)})
    except Exception as e:
        annotation_logger.error(f"Errore nell'esportazione dei dati di addestramento: {e}")
        return jsonify({"status": "error", "message": f"Errore: {str(e)}"}), 500

@app.route('/api/annotation_stats', methods=['GET'])
def annotation_stats():
    try:
        annotations = load_annotations()
        documents = load_documents()
        doc_map = {doc['id']: doc for doc in documents}
        total_documents = len(documents)
        total_annotated = len(annotations)
        total_annotations = sum(len(anns) for anns in annotations.values())
        entity_counts = {}
        for doc_id, doc_annotations in annotations.items():
            for ann in doc_annotations:
                entity_type = ann.get('type')
                if entity_type not in entity_counts:
                    entity_counts[entity_type] = 0
                entity_counts[entity_type] += 1
        doc_stats = []
        for doc_id, doc_annotations in annotations.items():
            if doc_id in doc_map:
                doc = doc_map[doc_id]
                doc_stats.append({
                    "id": doc_id,
                    "title": doc.get('title', 'Documento senza titolo'),
                    "annotation_count": len(doc_annotations),
                    "word_count": doc.get('word_count', 0),
                    "annotation_density": len(doc_annotations) / doc.get('word_count', 1) * 100
                })
        temporal_stats = {}
        for doc in documents:
            if 'date_created' in doc:
                try:
                    date = doc['date_created'].split('T')[0]
                    if date not in temporal_stats:
                        temporal_stats[date] = {"documents": 0, "annotations": 0}
                    temporal_stats[date]["documents"] += 1
                    doc_id = doc['id']
                    if doc_id in annotations:
                        temporal_stats[date]["annotations"] += len(annotations[doc_id])
                except Exception:
                    pass
        return jsonify({
            "general": {
                "total_documents": total_documents,
                "annotated_documents": total_annotated,
                "total_annotations": total_annotations,
                "annotation_coverage": (total_annotated / total_documents * 100) if total_documents > 0 else 0
            },
            "entity_stats": entity_counts,
            "document_stats": doc_stats,
            "temporal_stats": [{"date": k, **v} for k, v in temporal_stats.items()]
        })
    except Exception as e:
        annotation_logger.error(f"Errore nel calcolo delle statistiche: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/entity_types')
def entity_types():
    return render_template('entity_types.html', entity_types=ENTITY_TYPES)

# -----------------------------------------------------------------------------
# Endpoint API migliorati per la gestione dei tipi di entità
# -----------------------------------------------------------------------------
logger = logging.getLogger("ner_giuridico.entity_api")

def api_endpoint(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        request_id = request.headers.get('X-Request-ID', 'unknown')
        logger.info(f"[{request_id}] Richiesta a {func.__name__}: iniziata")
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"[{request_id}] Richiesta a {func.__name__}: completata in {execution_time:.4f}s")
            return result
        except ValueError as e:
            logger.warning(f"[{request_id}] Errore di validazione in {func.__name__}: {str(e)}")
            return jsonify({"status": "error", "message": str(e), "error_type": "ValidationError"}), 400
        except KeyError as e:
            logger.warning(f"[{request_id}] Dati mancanti in {func.__name__}: {str(e)}")
            return jsonify({"status": "error", "message": f"Campo obbligatorio mancante: {str(e)}", "error_type": "MissingFieldError"}), 400
        except Exception as e:
            logger.error(f"[{request_id}] Errore non gestito in {func.__name__}: {str(e)}")
            logger.exception(e)
            return jsonify({"status": "error", "message": "Si è verificato un errore interno nel server", "error_type": type(e).__name__}), 500
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper

def validate_entity_name(name: str, is_update: bool = False) -> None:
    if is_update:
        return
    if not name:
        raise ValueError("Il nome dell'entità è obbligatorio")
    if not name.isupper():
        raise ValueError("Il nome dell'entità deve essere in maiuscolo")
    if ' ' in name:
        raise ValueError("Il nome dell'entità non deve contenere spazi")
    if not re.match(r'^[A-Z0-9_]+$', name):
        raise ValueError("Il nome dell'entità può contenere solo lettere maiuscole, numeri e underscore")

def validate_entity_display_name(display_name: str) -> None:
    if not display_name:
        raise ValueError("Il nome visualizzato dell'entità è obbligatorio")
    if len(display_name) > 100:
        raise ValueError("Il nome visualizzato dell'entità non può superare i 100 caratteri")

def validate_entity_category(category: str) -> None:
    valid_categories = ['normative', 'jurisprudence', 'concepts', 'custom']
    if not category:
        raise ValueError("La categoria dell'entità è obbligatoria")
    if category not in valid_categories:
        raise ValueError(f"La categoria dell'entità deve essere una tra: {', '.join(valid_categories)}")

def validate_entity_color(color: str) -> None:
    if not color:
        raise ValueError("Il colore dell'entità è obbligatorio")
    if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
        raise ValueError("Il colore dell'entità deve essere in formato esadecimale (es. #FF0000)")

def validate_metadata_schema(metadata_schema: Dict[str, str]) -> None:
    if not isinstance(metadata_schema, dict):
        raise ValueError("Lo schema dei metadati deve essere un dizionario")
    valid_types = ['string', 'number', 'boolean', 'date', 'array']
    for key, value in metadata_schema.items():
        if not isinstance(key, str):
            raise ValueError("Le chiavi dello schema dei metadati devono essere stringhe")
        if not isinstance(value, str):
            raise ValueError("I tipi dei metadati devono essere stringhe")
        if value not in valid_types:
            raise ValueError(f"Il tipo '{value}' non è valido. I tipi validi sono: {', '.join(valid_types)}")

def validate_regex_patterns(patterns: List[str]) -> None:
    if not isinstance(patterns, list):
        raise ValueError("I pattern devono essere una lista di stringhe")
    for pattern in patterns:
        if not isinstance(pattern, str):
            raise ValueError("Ogni pattern deve essere una stringa")
        try:
            re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Pattern regex non valido: '{pattern}' - {str(e)}")


@api_endpoint
def get_entity_types():
    """Ottiene la lista dei tipi di entità."""
    try:
        from ner_giuridico.entities.entity_manager import get_entity_manager
        category = request.args.get('category')
        entity_manager = get_entity_manager()
        all_entity_types = entity_manager.get_all_entity_types()
        result = []
        
        # Verifica che all_entity_types sia un dizionario
        if not isinstance(all_entity_types, dict):
            logger.error(f"get_all_entity_types ha restituito un tipo non valido: {type(all_entity_types)}")
            return jsonify({"status": "error", "message": "Formato dei dati non valido"}), 500
        
        for name, info in all_entity_types.items():
            if category and info.get("category") != category:
                continue
            
            # Assicuriamoci che tutte le proprietà siano presenti
            entry = {
                "name": name,
                "display_name": info.get("display_name", name),
                "category": info.get("category", "custom"),
                "color": info.get("color", "#CCCCCC"),
                "metadata_schema": info.get("metadata_schema", {}),
                "patterns": info.get("patterns", [])
            }
            result.append(entry)
        
        # Ordina il risultato per categoria e nome
        result.sort(key=lambda x: (x["category"], x["name"]))
        return jsonify({"status": "success", "entity_types": result})
    except Exception as e:
        logger.error(f"Errore nel caricamento dei tipi di entità: {e}")
        logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500
@api_endpoint
def get_entity_type(name: str):
    from ner_giuridico.entities.entity_manager import get_entity_manager
    entity_manager = get_entity_manager()
    entity_type = entity_manager.get_entity_type(name)
    if not entity_type:
        return jsonify({"status": "error", "message": f"Tipo di entità '{name}' non trovato"}), 404
    result = {
        "name": name,
        "display_name": entity_type.get("display_name", name),
        "category": entity_type.get("category", "custom"),
        "color": entity_type.get("color", "#CCCCCC"),
        "metadata_schema": entity_type.get("metadata_schema", {}),
        "patterns": entity_type.get("patterns", [])
    }
    return jsonify({"status": "success", "entity_type": result})

@api_endpoint
def create_entity_type():
    from ner_giuridico.entities.entity_manager import get_entity_manager
    data = request.json
    if not data:
        raise ValueError("Dati mancanti nella richiesta")
    if not data.get('name'):
        raise ValueError("Nome entità mancante")
    name = data['name']
    display_name = data.get('display_name', name)
    category = data.get('category', 'custom')
    color = data.get('color', '#CCCCCC')
    metadata_schema = data.get('metadata_schema', {})
    patterns = data.get('patterns', [])
    validate_entity_name(name)
    validate_entity_display_name(display_name)
    validate_entity_category(category)
    validate_entity_color(color)
    validate_metadata_schema(metadata_schema)
    validate_regex_patterns(patterns)
    entity_manager = get_entity_manager()
    if entity_manager.entity_type_exists(name):
        raise ValueError(f"Il tipo di entità '{name}' esiste già")
    success = entity_manager.add_entity_type(
        name=name,
        display_name=display_name,
        category=category,
        color=color,
        metadata_schema=metadata_schema,
        patterns=patterns
    )
    if not success:
        raise ValueError(f"Impossibile creare il tipo di entità '{name}'")
    entity_type = entity_manager.get_entity_type(name)
    result = {
        "name": name,
        "display_name": entity_type.get("display_name", name),
        "category": entity_type.get("category", "custom"),
        "color": entity_type.get("color", "#CCCCCC"),
        "metadata_schema": entity_type.get("metadata_schema", {}),
        "patterns": entity_type.get("patterns", [])
    }
    return jsonify({"status": "success", "message": f"Tipo di entità '{name}' creato con successo", "entity_type": result})

@api_endpoint
def update_entity_type(name: str):
    from ner_giuridico.entities.entity_manager import get_entity_manager
    data = request.json
    if not data:
        raise ValueError("Dati mancanti nella richiesta")
    entity_manager = get_entity_manager()
    if not entity_manager.entity_type_exists(name):
        return jsonify({"status": "error", "message": f"Tipo di entità '{name}' non trovato"}), 404
    display_name = data.get('display_name')
    color = data.get('color')
    metadata_schema = data.get('metadata_schema')
    patterns = data.get('patterns')
    current_entity = entity_manager.get_entity_type(name)
    display_name = display_name or current_entity.get('display_name')
    color = color or current_entity.get('color')
    metadata_schema = metadata_schema if metadata_schema is not None else current_entity.get('metadata_schema', {})
    patterns = patterns if patterns is not None else current_entity.get('patterns', [])
    validate_entity_name(name, is_update=True)
    validate_entity_display_name(display_name)
    validate_entity_color(color)
    validate_metadata_schema(metadata_schema)
    validate_regex_patterns(patterns)
    success = entity_manager.update_entity_type(
        name=name,
        display_name=display_name,
        color=color,
        metadata_schema=metadata_schema,
        patterns=patterns
    )
    if not success:
        raise ValueError(f"Impossibile aggiornare il tipo di entità '{name}'")
    entity_type = entity_manager.get_entity_type(name)
    result = {
        "name": name,
        "display_name": entity_type.get("display_name", name),
        "category": entity_type.get("category", "custom"),
        "color": entity_type.get("color", "#CCCCCC"),
        "metadata_schema": entity_type.get("metadata_schema", {}),
        "patterns": entity_type.get("patterns", [])
    }
    return jsonify({"status": "success", "message": f"Tipo di entità '{name}' aggiornato con successo", "entity_type": result})

@api_endpoint
def delete_entity_type(name: str):
    from ner_giuridico.entities.entity_manager import get_entity_manager
    entity_manager = get_entity_manager()
    if not entity_manager.entity_type_exists(name):
        return jsonify({"status": "error", "message": f"Tipo di entità '{name}' non trovato"}), 404
    entity_type = entity_manager.get_entity_type(name)
    if entity_type.get("category") != "custom":
        raise ValueError(f"Non è possibile eliminare il tipo di entità predefinito '{name}'")
    has_annotations = check_entity_type_in_use(name)
    if has_annotations:
        raise ValueError(f"Impossibile eliminare il tipo di entità '{name}' perché è in uso in alcune annotazioni")
    success = entity_manager.remove_entity_type(name)
    if not success:
        raise ValueError(f"Impossibile eliminare il tipo di entità '{name}'")
    return jsonify({"status": "success", "message": f"Tipo di entità '{name}' eliminato con successo"})

def check_entity_type_in_use(entity_type_name: str) -> bool:
    try:
        DATA_DIR_PATH = Path(__file__).resolve().parent / 'data'
        annotations_file = os.path.join(DATA_DIR_PATH, 'annotations.json')
        if not os.path.exists(annotations_file):
            return False
        with open(annotations_file, 'r', encoding='utf-8') as f:
            annotations = json.load(f)
        for doc_id, doc_annotations in annotations.items():
            for annotation in doc_annotations:
                if annotation.get('type') == entity_type_name:
                    return True
        return False
    except Exception as e:
        logger.error(f"Errore nella verifica dell'uso del tipo di entità '{entity_type_name}': {e}")
        return True

@api_endpoint
def test_entity_pattern():
    data = request.json
    if not data:
        raise ValueError("Dati mancanti nella richiesta")
    pattern = data.get('pattern')
    test_text = data.get('text')
    if not pattern:
        raise ValueError("Pattern regex mancante")
    if not test_text:
        raise ValueError("Testo di esempio mancante")
    try:
        regex = re.compile(pattern)
    except re.error as e:
        raise ValueError(f"Pattern regex non valido: {str(e)}")
    matches = []
    for match in regex.finditer(test_text):
        matches.append({
            "text": match.group(0),
            "start": match.start(),
            "end": match.end(),
            "groups": match.groups()
        })
    return jsonify({"status": "success", "pattern": pattern, "matches_count": len(matches), "matches": matches})

def register_entity_api_endpoints(app):
    app.route('/api/entity_types', methods=['GET'])(get_entity_types)
    app.route('/api/entity_types/<name>', methods=['GET'])(get_entity_type)
    app.route('/api/entity_types', methods=['POST'])(create_entity_type)
    app.route('/api/entity_types/<name>', methods=['PUT'])(update_entity_type)
    app.route('/api/entity_types/<name>', methods=['DELETE'])(delete_entity_type)
    app.route('/api/test_pattern', methods=['POST'])(test_entity_pattern)
    logger.info("Endpoint API per la gestione dei tipi di entità registrati con successo")

register_entity_api_endpoints(app)

# -----------------------------------------------------------------------------
# Inizializzazione finale ed esecuzione dell'app
# -----------------------------------------------------------------------------
if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    if not os.path.exists(os.path.join(DATA_DIR, 'documents.json')):
        with open(os.path.join(DATA_DIR, 'documents.json'), 'w', encoding='utf-8') as f:
            json.dump([], f)
    if not os.path.exists(os.path.join(DATA_DIR, 'annotations.json')):
        with open(os.path.join(DATA_DIR, 'annotations.json'), 'w', encoding='utf-8') as f:
            json.dump({}, f)
    annotation_logger.info("Interfaccia di annotazione inizializzata e pronta all'avvio")
    annotation_logger.info(f"Tipi di entità disponibili: {', '.join(entity['id'] for entity in ENTITY_TYPES)}")
    app.run(host='0.0.0.0', port=8080, debug=True)
