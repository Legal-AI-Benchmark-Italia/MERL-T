#!/usr/bin/env python3
"""
Interfaccia web per l'annotazione di entità giuridiche.
Consente di caricare documenti, annotare entità e esportare le annotazioni.
Integra con il sistema NER-Giuridico per il riconoscimento automatico.
"""

import os
import sys
import json
import logging
import datetime
import importlib.util
from functools import wraps
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file
from werkzeug.utils import secure_filename

# Configurazione del logger specifico per l'annotator
annotation_logger = logging.getLogger("annotator")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
annotation_logger.addHandler(handler)
annotation_logger.setLevel(logging.INFO)

def setup_environment():
    """Configura correttamente l'ambiente Python per trovare i moduli necessari."""
    current_dir = Path(__file__).resolve().parent
    
    # Stampa informazioni per debug
    annotation_logger.debug(f"Directory corrente: {current_dir}")
    annotation_logger.debug(f"sys.path attuale: {sys.path}")
    
    # Aggiungi directory parent alla path
    parent_dir = current_dir.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    # Cerca la directory root del progetto
    project_root = parent_dir
    for _ in range(5):  # Limita la ricerca a 5 livelli
        if (project_root / "ner_giuridico").exists() or (project_root / "config").exists():
            break
        project_root = project_root.parent
        if project_root == project_root.parent:  # Abbiamo raggiunto la root del filesystem
            break
    
    # Aggiungi la root del progetto al path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    annotation_logger.info(f"Root del progetto: {project_root}")
    return current_dir, project_root

# Configurazione dell'ambiente
current_dir, project_root = setup_environment()

# Tenta di importare i moduli necessari
try:
    # Prima prova l'importazione diretta (caso ideale)
    try:
        from ner_giuridico.entities.entity_manager import get_entity_manager
        from ner_giuridico.ner import DynamicNERGiuridico
        annotation_logger.info("Moduli importati direttamente")
    except ImportError as e:
        annotation_logger.warning(f"Impossibile importare direttamente: {e}")
        
        # Prova con l'importazione relativa (se siamo in un subpackage)
        try:
            from ..entities.entity_manager import get_entity_manager
            from ..ner import DynamicNERGiuridico
            annotation_logger.info("Moduli importati relativamente")
        except (ImportError, ValueError) as e:
            annotation_logger.warning(f"Impossibile importare relativamente: {e}")
            
            # Come ultima risorsa, cerca di risolvere il percorso del modulo
            try:
                # Cerca i moduli nel filesystem
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
                    
                    # Carica i moduli direttamente dai file
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
            except Exception as e:
                annotation_logger.error(f"Impossibile importare i moduli: {e}")
                raise

    # Tenta di inizializzare l'entity_manager
    try:
        entity_manager = get_entity_manager()
        annotation_logger.info("Entity manager inizializzato con successo")
        
        # Debug dello stato dell'entity manager
        if hasattr(entity_manager, 'db_path') and entity_manager.db_path:
            annotation_logger.debug(f"Database path: {entity_manager.db_path}")
            
            # Verifica se il database esiste
            if os.path.exists(entity_manager.db_path):
                annotation_logger.debug(f"Il database delle entità esiste: {entity_manager.db_path}")
                
                # Conta entità nel database se il metodo esiste
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
        
        # Ottieni i tipi di entità
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
        
        # Fallback a tipi di entità predefiniti
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
    
    # Implementazione fittizia per degradazione elegante
    class DummyEntityManager:
        def get_entity_type(self, name):
            for entity in ENTITY_TYPES:
                if entity["id"] == name:
                    return entity
            return None
            
        def get_all_entity_types(self):
            return {entity["id"]: {"display_name": entity["name"], "color": entity["color"]} 
                    for entity in ENTITY_TYPES}
            
        def entity_type_exists(self, name):
            return any(entity["id"] == name for entity in ENTITY_TYPES)
    
    class DummyNER:
        def process(self, text):
            return {"entities": []}
    
    # Definisci tipi di entità predefiniti
    ENTITY_TYPES = [
        {"id": "ARTICOLO_CODICE", "name": "Articolo di Codice", "color": "#FFA39E"},
        {"id": "LEGGE", "name": "Legge", "color": "#D4380D"},
        {"id": "DECRETO", "name": "Decreto", "color": "#FFC069"},
        {"id": "REGOLAMENTO_UE", "name": "Regolamento UE", "color": "#AD8B00"},
        {"id": "SENTENZA", "name": "Sentenza", "color": "#D3F261"},
        {"id": "ORDINANZA", "name": "Ordinanza", "color": "#389E0D"},
        {"id": "CONCETTO_GIURIDICO", "name": "Concetto Giuridico", "color": "#5CDBD3"}
    ]
    
    # Definisci le funzioni fittizie
    DynamicNERGiuridico = DummyNER
    get_entity_manager = lambda: DummyEntityManager()
    
    annotation_logger.info("Utilizzando implementazioni fittizie a causa di errori di importazione")

# Inizializzazione dell'app Flask
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Configurazione
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # Limite dimensione file: 10MB

# Directory per i dati con gestione dei backup
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)

# Directory per i backup
BACKUP_DIR = os.path.join(DATA_DIR, 'backup')
os.makedirs(BACKUP_DIR, exist_ok=True)

# Funzione helper per gestire in modo consistente errori nelle API
def handle_api_error(func):
    """Decoratore per gestire uniformemente gli errori nelle API."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            annotation_logger.error(f"Errore API: {str(e)}")
            annotation_logger.exception(e)
            return jsonify({
                "status": "error", 
                "message": f"Si è verificato un errore: {str(e)}",
                "error_type": type(e).__name__
            }), 500
    return wrapper

# Gestori di errori personalizzati
@app.errorhandler(404)
def not_found(e):
    """Gestore per errori 404."""
    return jsonify({"status": "error", "message": "Risorsa non trovata"}), 404

@app.errorhandler(500)
def server_error(e):
    """Gestore per errori 500."""
    annotation_logger.error(f"Errore del server: {str(e)}")
    return jsonify({"status": "error", "message": "Errore interno del server"}), 500

# Middleware per log delle richieste
@app.before_request
def log_request():
    """Log della richiesta in arrivo."""
    annotation_logger.debug(f"Richiesta: {request.method} {request.path}")

@app.after_request
def log_response(response):
    """Log della risposta in uscita."""
    annotation_logger.debug(f"Risposta: {response.status_code}")
    return response

# Aggiungi questi endpoint dopo gli altri endpoint API esistenti in app.py

@app.route('/api/entity_types', methods=['GET'])
@handle_api_error
def get_entity_types():
    """Ottiene tutti i tipi di entità."""
    try:
        entity_manager = get_entity_manager()
        all_entity_types = entity_manager.get_all_entity_types()
        
        # Converti in un formato più adatto per JSON
        result = []
        for name, info in all_entity_types.items():
            result.append({
                "name": name,
                "display_name": info.get("display_name", name),
                "category": info.get("category", "custom"),
                "color": info.get("color", "#CCCCCC"),
                "metadata_schema": info.get("metadata_schema", {}),
                "patterns": info.get("patterns", [])
            })
        
        return jsonify({"status": "success", "entity_types": result})
    except Exception as e:
        annotation_logger.error(f"Errore nell'ottenimento dei tipi di entità: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/entity_types/<name>', methods=['GET'])
@handle_api_error
def get_entity_type(name):
    """Ottiene un tipo di entità specifico."""
    try:
        entity_manager = get_entity_manager()
        entity_type = entity_manager.get_entity_type(name)
        
        if not entity_type:
            return jsonify({"status": "error", "message": f"Tipo di entità '{name}' non trovato"}), 404
        
        # Converti in un formato adatto per JSON
        result = {
            "name": name,
            "display_name": entity_type.get("display_name", name),
            "category": entity_type.get("category", "custom"),
            "color": entity_type.get("color", "#CCCCCC"),
            "metadata_schema": entity_type.get("metadata_schema", {}),
            "patterns": entity_type.get("patterns", [])
        }
        
        return jsonify({"status": "success", "entity_type": result})
    except Exception as e:
        annotation_logger.error(f"Errore nell'ottenimento del tipo di entità '{name}': {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/entity_types', methods=['POST'])
@handle_api_error
def create_entity_type():
    """Crea un nuovo tipo di entità."""
    try:
        data = request.json
        
        if not data or not data.get('name'):
            return jsonify({"status": "error", "message": "Nome entità mancante"}), 400
        
        name = data['name'].upper()  # Converti in maiuscolo come da convenzione
        display_name = data.get('display_name', name)
        category = data.get('category', 'custom')
        color = data.get('color', '#CCCCCC')
        metadata_schema = data.get('metadata_schema', {})
        patterns = data.get('patterns', [])
        
        # Validazione
        if not name.isupper() or ' ' in name:
            return jsonify({
                "status": "error", 
                "message": "Il nome dell'entità deve essere in maiuscolo e senza spazi"
            }), 400
        
        # Aggiungi il tipo di entità
        entity_manager = get_entity_manager()
        success = entity_manager.add_entity_type(
            name=name,
            display_name=display_name,
            category=category,
            color=color,
            metadata_schema=metadata_schema,
            patterns=patterns
        )
        
        if not success:
            return jsonify({"status": "error", "message": f"Impossibile creare il tipo di entità '{name}'"}), 400
        
        # Ottieni il tipo di entità appena creato per la risposta
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
    except Exception as e:
        annotation_logger.error(f"Errore nella creazione del tipo di entità: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/entity_types/<name>', methods=['PUT'])
@handle_api_error
def update_entity_type(name):
    """Aggiorna un tipo di entità esistente."""
    try:
        data = request.json
        
        if not data:
            return jsonify({"status": "error", "message": "Dati mancanti"}), 400
        
        # Controlla se il tipo di entità esiste
        entity_manager = get_entity_manager()
        if not entity_manager.entity_type_exists(name):
            return jsonify({"status": "error", "message": f"Tipo di entità '{name}' non trovato"}), 404
        
        # Estrai i campi da aggiornare
        display_name = data.get('display_name')
        color = data.get('color')
        metadata_schema = data.get('metadata_schema')
        patterns = data.get('patterns')
        
        # Aggiorna il tipo di entità
        success = entity_manager.update_entity_type(
            name=name,
            display_name=display_name,
            color=color,
            metadata_schema=metadata_schema,
            patterns=patterns
        )
        
        if not success:
            return jsonify({"status": "error", "message": f"Impossibile aggiornare il tipo di entità '{name}'"}), 400
        
        # Ottieni il tipo di entità aggiornato per la risposta
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
    except Exception as e:
        annotation_logger.error(f"Errore nell'aggiornamento del tipo di entità '{name}': {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/entity_types/<name>', methods=['DELETE'])
@handle_api_error
def delete_entity_type(name):
    """Elimina un tipo di entità."""
    try:
        # Controlla se il tipo di entità esiste
        entity_manager = get_entity_manager()
        if not entity_manager.entity_type_exists(name):
            return jsonify({"status": "error", "message": f"Tipo di entità '{name}' non trovato"}), 404
        
        # Impedisci l'eliminazione dei tipi di entità predefiniti
        entity_type = entity_manager.get_entity_type(name)
        if entity_type.get("category") != "custom":
            return jsonify({
                "status": "error", 
                "message": f"Non è possibile eliminare il tipo di entità predefinito '{name}'"
            }), 400
        
        # Elimina il tipo di entità
        success = entity_manager.remove_entity_type(name)
        
        if not success:
            return jsonify({"status": "error", "message": f"Impossibile eliminare il tipo di entità '{name}'"}), 400
        
        return jsonify({"status": "success", "message": f"Tipo di entità '{name}' eliminato con successo"})
    except Exception as e:
        annotation_logger.error(f"Errore nell'eliminazione del tipo di entità '{name}': {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
# Funzioni di persistenza migliorate
def load_documents() -> List[Dict[str, Any]]:
    """Carica i documenti dal file JSON con gestione degli errori migliorata."""
    documents = []
    documents_file = os.path.join(DATA_DIR, 'documents.json')
    
    # Se il file non esiste, crea un file vuoto
    if not os.path.exists(documents_file):
        save_documents([])
        return []
    
    try:
        with open(documents_file, 'r', encoding='utf-8') as f:
            documents = json.load(f)
        annotation_logger.debug(f"Caricati {len(documents)} documenti")
    except json.JSONDecodeError:
        annotation_logger.error(f"Errore nella decodifica del file JSON: {documents_file}")
        # Crea un backup del file corrotto
        backup_file = os.path.join(BACKUP_DIR, f'documents_corrupt_{int(datetime.datetime.now().timestamp())}.json')
        try:
            import shutil
            shutil.copy(documents_file, backup_file)
            annotation_logger.info(f"Backup del file corrotto salvato in: {backup_file}")
        except Exception as e:
            annotation_logger.warning(f"Impossibile creare backup: {e}")
        # Inizializza con un array vuoto
        save_documents([])
    except Exception as e:
        annotation_logger.error(f"Errore nel caricamento dei documenti: {e}")
    
    return documents

def save_documents(documents: List[Dict[str, Any]]) -> bool:
    """Salva i documenti nel file JSON con gestione degli errori migliorata."""
    documents_file = os.path.join(DATA_DIR, 'documents.json')
    
    # Crea un backup prima di salvare
    if os.path.exists(documents_file):
        backup_file = os.path.join(BACKUP_DIR, f'documents_backup_{int(datetime.datetime.now().timestamp())}.json')
        try:
            import shutil
            shutil.copy(documents_file, backup_file)
            annotation_logger.debug(f"Backup creato: {backup_file}")
        except Exception as e:
            annotation_logger.warning(f"Impossibile creare backup: {e}")
    
    try:
        # Salva i documenti in un file temporaneo prima
        temp_file = f"{documents_file}.tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)
        
        # Poi rinomina il file temporaneo (operazione atomica)
        os.replace(temp_file, documents_file)
        
        annotation_logger.debug(f"Salvati {len(documents)} documenti")
        return True
    except Exception as e:
        annotation_logger.error(f"Errore nel salvataggio dei documenti: {e}")
        return False

def load_annotations() -> Dict[str, List[Dict[str, Any]]]:
    """Carica le annotazioni dal file JSON con gestione degli errori migliorata."""
    annotations = {}
    annotations_file = os.path.join(DATA_DIR, 'annotations.json')
    
    # Se il file non esiste, crea un file vuoto
    if not os.path.exists(annotations_file):
        save_annotations({})
        return {}
    
    try:
        with open(annotations_file, 'r', encoding='utf-8') as f:
            annotations = json.load(f)
        
        # Conta il numero totale di annotazioni
        total_annotations = sum(len(anns) for anns in annotations.values())
        annotation_logger.debug(f"Caricate {total_annotations} annotazioni per {len(annotations)} documenti")
    except json.JSONDecodeError:
        annotation_logger.error(f"Errore nella decodifica del file JSON: {annotations_file}")
        # Crea un backup del file corrotto
        backup_file = os.path.join(BACKUP_DIR, f'annotations_corrupt_{int(datetime.datetime.now().timestamp())}.json')
        try:
            import shutil
            shutil.copy(annotations_file, backup_file)
            annotation_logger.info(f"Backup del file corrotto salvato in: {backup_file}")
        except Exception as e:
            annotation_logger.warning(f"Impossibile creare backup: {e}")
        # Inizializza con un dizionario vuoto
        save_annotations({})
    except Exception as e:
        annotation_logger.error(f"Errore nel caricamento delle annotazioni: {e}")
    
    return annotations

def save_annotations(annotations: Dict[str, List[Dict[str, Any]]]) -> bool:
    """Salva le annotazioni nel file JSON con gestione degli errori migliorata."""
    annotations_file = os.path.join(DATA_DIR, 'annotations.json')
    
    # Crea un backup prima di salvare
    if os.path.exists(annotations_file):
        backup_file = os.path.join(BACKUP_DIR, f'annotations_backup_{int(datetime.datetime.now().timestamp())}.json')
        try:
            import shutil
            shutil.copy(annotations_file, backup_file)
            annotation_logger.debug(f"Backup creato: {backup_file}")
        except Exception as e:
            annotation_logger.warning(f"Impossibile creare backup: {e}")
    
    try:
        # Salva le annotazioni in un file temporaneo prima
        temp_file = f"{annotations_file}.tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(annotations, f, indent=2, ensure_ascii=False)
        
        # Poi rinomina il file temporaneo (operazione atomica)
        os.replace(temp_file, annotations_file)
        
        # Conta il numero totale di annotazioni
        total_annotations = sum(len(anns) for anns in annotations.values())
        annotation_logger.debug(f"Salvate {total_annotations} annotazioni per {len(annotations)} documenti")
        return True
    except Exception as e:
        annotation_logger.error(f"Errore nel salvataggio delle annotazioni: {e}")
        return False

def cleanup_backups(max_backups: int = 10):
    """Mantiene solo gli ultimi N backup per tipo."""
    try:
        # Ottieni tutti i file di backup
        import os
        backup_files = {
            'documents': [],
            'annotations': []
        }
        
        for filename in os.listdir(BACKUP_DIR):
            filepath = os.path.join(BACKUP_DIR, filename)
            if filename.startswith('documents_backup_'):
                backup_files['documents'].append((filepath, os.path.getmtime(filepath)))
            elif filename.startswith('annotations_backup_'):
                backup_files['annotations'].append((filepath, os.path.getmtime(filepath)))
        
        # Ordina per data di modifica (più recenti prima)
        for key in backup_files:
            backup_files[key].sort(key=lambda x: x[1], reverse=True)
            
            # Rimuovi i backup in eccesso
            if len(backup_files[key]) > max_backups:
                for filepath, _ in backup_files[key][max_backups:]:
                    os.remove(filepath)
                    annotation_logger.debug(f"Rimosso backup vecchio: {filepath}")
    except Exception as e:
        annotation_logger.error(f"Errore nella pulizia dei backup: {e}")

# Route per la pagina principale
@app.route('/')
def index():
    """Pagina principale con lista dei documenti disponibili."""
    documents = load_documents()
    return render_template('index.html', documents=documents)

# Route per la pagina di annotazione
@app.route('/annotate/<doc_id>')
def annotate(doc_id):
    """Pagina di annotazione per un documento specifico."""
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

# API per salvare un'annotazione
@app.route('/api/save_annotation', methods=['POST'])
@handle_api_error
def save_annotation():
    """Salva una nuova annotazione o aggiorna un'annotazione esistente."""
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
    cleanup_backups()  # Mantieni i file di backup sotto controllo
    
    return jsonify({"status": "success", "annotation": annotation})

# API per eliminare un'annotazione
@app.route('/api/delete_annotation', methods=['POST'])
@handle_api_error
def delete_annotation():
    """Elimina un'annotazione esistente."""
    data = request.json
    doc_id = data.get('doc_id')
    annotation_id = data.get('annotation_id')
    
    if not doc_id or not annotation_id:
        return jsonify({"status": "error", "message": "Dati mancanti"}), 400
    
    annotations = load_annotations()
    
    if doc_id in annotations:
        # Filtra le annotazioni per rimuovere quella con l'ID specificato
        annotations[doc_id] = [ann for ann in annotations[doc_id] if ann.get('id') != annotation_id]
        save_annotations(annotations)
    
    return jsonify({"status": "success"})

# API per caricare un documento
@app.route('/api/upload_document', methods=['POST'])
@handle_api_error
def upload_document():
    """Carica un nuovo documento per l'annotazione."""
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "Nessun file caricato"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "Nessun file selezionato"}), 400
    
    # Controlla l'estensione del file
    allowed_extensions = {'txt', 'md', 'html', 'xml', 'json', 'csv'}
    file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
    
    if file_ext not in allowed_extensions:
        return jsonify({
            "status": "error", 
            "message": f"Formato file non supportato. Estensioni consentite: {', '.join(allowed_extensions)}"
        }), 400
    
    try:
        # Leggi il contenuto del file
        file_content = file.read().decode('utf-8')
        
        # Controlla la dimensione del testo (lunghezza massima ragionevole)
        if len(file_content) > 1000000:  # ~1MB di testo
            return jsonify({
                "status": "error", 
                "message": "Il documento è troppo grande. Il limite è di circa 1MB di testo."
            }), 400
        
        documents = load_documents()
        
        # Crea un nuovo documento
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
        
        return jsonify({
            "status": "success", 
            "message": "Documento caricato con successo",
            "document": document
        })
    except UnicodeDecodeError:
        return jsonify({
            "status": "error", 
            "message": "Impossibile decodificare il file. Assicurati che sia un file di testo valido in formato UTF-8."
        }), 400

# API per esportare le annotazioni
@app.route('/api/export_annotations', methods=['GET'])
@handle_api_error
def export_annotations():
    """Esporta le annotazioni in diversi formati."""
    format_type = request.args.get('format', 'json')
    
    annotations = load_annotations()
    documents = load_documents()
    
    if format_type == 'spacy':
        # Converti in formato spaCy per addestramento
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
        
        # Salva i dati in un file
        output_file = os.path.join(DATA_DIR, 'spacy_annotations.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(spacy_data, f, indent=2, ensure_ascii=False)
        
        # Offri il download del file se richiesto
        if request.args.get('download', 'false').lower() == 'true':
            return send_file(output_file, as_attachment=True, download_name='spacy_annotations.json')
            
        return jsonify({"status": "success", "file": output_file, "data": spacy_data})
    else:
        # Formato JSON nativo
        if request.args.get('download', 'false').lower() == 'true':
            # Crea un file temporaneo
            output_file = os.path.join(DATA_DIR, 'annotations_export.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(annotations, f, indent=2, ensure_ascii=False)
            return send_file(output_file, as_attachment=True, download_name='annotations_export.json')
        
        return jsonify(annotations)

# API per il riconoscimento automatico delle entità
@app.route('/api/recognize', methods=['POST'])
@handle_api_error
def recognize_entities():
    """Riconosce automaticamente le entità in un testo usando il sistema NER."""
    data = request.json
    text = data.get('text')
    
    if not text:
        return jsonify({"status": "error", "message": "Testo mancante"}), 400
    
    try:
        # Inizializza il sistema NER
        ner = DynamicNERGiuridico()
        
        # Riconosci le entità
        result = ner.process(text)
        
        # Converti le entità nel formato dell'annotator
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
        return jsonify({
            "status": "error", 
            "message": f"Errore nel riconoscimento delle entità: {str(e)}"
        }), 500

# API per l'addestramento del modello
@app.route('/api/train_model', methods=['POST'])
@handle_api_error
def train_model():
    """Esporta le annotazioni per l'addestramento del modello NER."""
    try:
        # Esporta le annotazioni in un formato compatibile con il sistema NER
        annotations = load_annotations()
        documents = load_documents()
        
        # Crea i dati in formato spaCy
        ner_data = []
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
                    entities.append({
                        "text": ann['text'],
                        "type": ann['type'],
                        "start_char": ann['start'],
                        "end_char": ann['end']
                    })
                
                ner_data.append({
                    "text": text,
                    "entities": entities
                })
        
        # Salva i dati
        output_file = os.path.join(DATA_DIR, 'ner_training_data.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(ner_data, f, indent=2, ensure_ascii=False)
        
        # Qui si potrebbe implementare una chiamata al modulo di addestramento
        # del sistema NER con i dati appena salvati
        
        return jsonify({
            "status": "success", 
            "message": "Dati di addestramento esportati con successo",
            "file": output_file,
            "count": len(ner_data)
        })
    except Exception as e:
        annotation_logger.error(f"Errore nell'esportazione dei dati di addestramento: {e}")
        return jsonify({"status": "error", "message": f"Errore: {str(e)}"}), 500

# API per le statistiche delle annotazioni
@app.route('/api/annotation_stats', methods=['GET'])
@handle_api_error
def annotation_stats():
    """Restituisce statistiche sulle annotazioni."""
    annotations = load_annotations()
    documents = load_documents()
    
    # Mappa dei documenti per accesso veloce
    doc_map = {doc['id']: doc for doc in documents}
    
    # Statistiche generali
    total_documents = len(documents)
    total_annotated = len(annotations)
    total_annotations = sum(len(anns) for anns in annotations.values())
    
    # Statistiche per tipo di entità
    entity_counts = {}
    for doc_id, doc_annotations in annotations.items():
        for ann in doc_annotations:
            entity_type = ann.get('type')
            if entity_type not in entity_counts:
                entity_counts[entity_type] = 0
            entity_counts[entity_type] += 1
    
    # Statistiche per documento
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
    
    # Statistiche temporali, se disponibili
    temporal_stats = {}
    for doc in documents:
        if 'date_created' in doc:
            try:
                date = doc['date_created'].split('T')[0]  # Solo la data YYYY-MM-DD
                if date not in temporal_stats:
                    temporal_stats[date] = {
                        "documents": 0,
                        "annotations": 0
                    }
                temporal_stats[date]["documents"] += 1
                
                # Aggiungi il conteggio delle annotazioni, se presenti
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
    
@app.route('/entity_types')
def entity_types():
    """Pagina per la gestione dei tipi di entità."""
    return render_template('entity_types.html', entity_types=ENTITY_TYPES)


# Inizializzazione dell'app
if __name__ == '__main__':
    # Assicurati che la directory dei dati esista
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    # Crea file vuoti se non esistono
    if not os.path.exists(os.path.join(DATA_DIR, 'documents.json')):
        with open(os.path.join(DATA_DIR, 'documents.json'), 'w', encoding='utf-8') as f:
            json.dump([], f)
    
    if not os.path.exists(os.path.join(DATA_DIR, 'annotations.json')):
        with open(os.path.join(DATA_DIR, 'annotations.json'), 'w', encoding='utf-8') as f:
            json.dump({}, f)
    
    # Stampa conferma di inizializzazione
    annotation_logger.info("Interfaccia di annotazione inizializzata e pronta all'avvio")
    annotation_logger.info(f"Tipi di entità disponibili: {', '.join(entity['id'] for entity in ENTITY_TYPES)}")
    
    # Avvia l'app Flask
    app.run(host='0.0.0.0', port=8080, debug=True)