#!/usr/bin/env python3
import importlib
import os
import json
import sys
import logging
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename

# Import from the package
from ner_giuridico.entities.entity_manager import get_entity_manager
from ner_giuridico.ner import DynamicNERGiuridico

# Configure specific logger
annotation_logger = logging.getLogger("annotator")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
annotation_logger.addHandler(handler)
annotation_logger.setLevel(logging.DEBUG)

# Print current Python path for debugging
print("\nCurrent sys.path:")
for p in sys.path:
    print(f"  - {p}")

# Find the project structure by trying to locate key files
def find_module_paths():
    # Start with the current file's directory
    current_dir = Path(__file__).resolve().parent
    
    # Print debug info
    print(f"\nCurrent directory: {current_dir}")
    
    # Try to find project structure by looking for key directories
    possible_project_roots = []
    
    # Walk up the directory tree looking for possible project roots
    dir_to_check = current_dir
    for _ in range(10):  # Limit to 10 levels up to avoid infinite loops
        # Check if this could be a project root
        if (dir_to_check / "ner_giuridico").exists() or (dir_to_check / "ner-giuridico").exists():
            possible_project_roots.append(dir_to_check)
        
        # Move up one directory
        parent = dir_to_check.parent
        if parent == dir_to_check:  # Reached the filesystem root
            break
        dir_to_check = parent
    
    # Print possible project roots for debugging
    print("\nPossible project roots found:")
    for root in possible_project_roots:
        print(f"  - {root}")
    
    return possible_project_roots

# Try to import the NER components dynamically
def import_ner_modules():
    possible_paths = find_module_paths()
    
    # Add each possible path to sys.path
    for path in possible_paths:
        sys.path.insert(0, str(path))
    
    # Try importing from various possible module paths
    possible_import_paths = [
        # Direct imports
        ("ner", "DynamicNERGiuridico"),
        ("entities.entity_manager", "get_entity_manager"),
        
        # With ner_giuridico.prefix
        ("ner_giuridico.ner", "DynamicNERGiuridico"),
        ("ner_giuridico.entities.entity_manager", "get_entity_manager"),
        
        # With data_lab prefix
        ("data_lab.ner.ner_giuridico.ner", "DynamicNERGiuridico"),
        ("data_lab.ner.ner_giuridico.entities.entity_manager", "get_entity_manager"),
        
        # Other possibilities
        ("ner_giuridico.data_lab.ner.ner_giuridico.ner", "DynamicNERGiuridico"),
        ("ner_giuridico.data_lab.ner.ner_giuridico.entities.entity_manager", "get_entity_manager"),
    ]
    
    # Try each import path
    imported_modules = {}
    
    for module_path, obj_name in possible_import_paths:
        try:
            module = importlib.import_module(module_path)
            if hasattr(module, obj_name):
                imported_modules[obj_name] = getattr(module, obj_name)
                print(f"Successfully imported {obj_name} from {module_path}")
        except ImportError as e:
            print(f"Could not import {obj_name} from {module_path}: {e}")
        except Exception as e:
            print(f"Error importing {obj_name} from {module_path}: {e}")
    
    return imported_modules

# Try to import the NER components
imported_modules = import_ner_modules()

# Extract the imported modules
DynamicNERGiuridico = imported_modules.get("DynamicNERGiuridico")
get_entity_manager = imported_modules.get("get_entity_manager")

# Check if we have successfully imported the modules
if DynamicNERGiuridico is None or get_entity_manager is None:
    print("\nCould not import NER components, using default entity types")
    
    # Define fallback entity types
    ENTITY_TYPES = [
        {"id": "ARTICOLO_CODICE", "name": "Articolo di Codice", "color": "#FFA39E"},
        {"id": "LEGGE", "name": "Legge", "color": "#D4380D"},
        {"id": "DECRETO", "name": "Decreto", "color": "#FFC069"},
        {"id": "REGOLAMENTO_UE", "name": "Regolamento UE", "color": "#AD8B00"},
        {"id": "SENTENZA", "name": "Sentenza", "color": "#D3F261"},
        {"id": "ORDINANZA", "name": "Ordinanza", "color": "#389E0D"},
        {"id": "CONCETTO_GIURIDICO", "name": "Concetto Giuridico", "color": "#5CDBD3"}
    ]
    
    # Define dummy classes for graceful degradation
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
    
    # Replace with dummy implementations
    if DynamicNERGiuridico is None:
        DynamicNERGiuridico = DummyNER
    if get_entity_manager is None:
        _dummy_entity_manager = DummyEntityManager()
        get_entity_manager = lambda: _dummy_entity_manager
else:
    print("\nSuccessfully imported NER components")

# Try to initialize the entity manager
try:
    entity_manager = get_entity_manager()
    
    # Debug entity manager state
    annotation_logger.debug("Entity manager inizializzato")
    annotation_logger.debug(f"Database path: {entity_manager.db_path}")
    
    # Check if database exists
    if os.path.exists(entity_manager.db_path):
        annotation_logger.debug(f"Il database delle entità esiste: {entity_manager.db_path}")
        # Count entities in database
        with entity_manager._get_db() as (conn, cursor):
            cursor.execute("SELECT COUNT(*) FROM entities")
            count = cursor.fetchone()[0]
            annotation_logger.debug(f"Numero di entità nel database: {count}")
    else:
        annotation_logger.debug(f"Il database delle entità non esiste: {entity_manager.db_path}")
    
    # Print default entities
    annotation_logger.debug(f"Entità gestite: {entity_manager.entity_types.keys()}")
    
    # Get entity types from the manager
    ENTITY_TYPES = []
    for name, info in entity_manager.get_all_entity_types().items():
        ENTITY_TYPES.append({
            "id": name,
            "name": info.get("display_name", name),
            "color": info.get("color", "#CCCCCC")
        })
    
    annotation_logger.debug(f"Caricati {len(ENTITY_TYPES)} tipi di entità dall'entity manager")
    
except Exception as e:
    annotation_logger.error(f"Errore nell'inizializzazione dell'entity manager: {e}")
    annotation_logger.exception(e)
    print("Using default entity types")
    # Fallback to default entity types
    ENTITY_TYPES = [
        {"id": "ARTICOLO_CODICE", "name": "Articolo di Codice", "color": "#FFA39E"},
        {"id": "LEGGE", "name": "Legge", "color": "#D4380D"},
        {"id": "DECRETO", "name": "Decreto", "color": "#FFC069"},
        {"id": "REGOLAMENTO_UE", "name": "Regolamento UE", "color": "#AD8B00"},
        {"id": "SENTENZA", "name": "Sentenza", "color": "#D3F261"},
        {"id": "ORDINANZA", "name": "Ordinanza", "color": "#389E0D"},
        {"id": "CONCETTO_GIURIDICO", "name": "Concetto Giuridico", "color": "#5CDBD3"}
    ]

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

# Configuration
DATA_DIR = 'data'
os.makedirs(DATA_DIR, exist_ok=True)

def load_documents():
    documents = []
    try:
        documents_file = os.path.join(DATA_DIR, 'documents.json')
        if os.path.exists(documents_file):
            with open(documents_file, 'r', encoding='utf-8') as f:
                documents = json.load(f)
    except Exception as e:
        print(f"Error loading documents: {e}")
    return documents

def save_documents(documents):
    try:
        documents_file = os.path.join(DATA_DIR, 'documents.json')
        with open(documents_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving documents: {e}")

def load_annotations():
    annotations = {}
    try:
        annotations_file = os.path.join(DATA_DIR, 'annotations.json')
        if os.path.exists(annotations_file):
            with open(annotations_file, 'r', encoding='utf-8') as f:
                annotations = json.load(f)
    except Exception as e:
        print(f"Error loading annotations: {e}")
    return annotations

def save_annotations(annotations):
    try:
        annotations_file = os.path.join(DATA_DIR, 'annotations.json')
        with open(annotations_file, 'w', encoding='utf-8') as f:
            json.dump(annotations, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving annotations: {e}")

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
        return jsonify({"status": "error", "message": "Missing data"}), 400
    
    annotations = load_annotations()
    
    if doc_id not in annotations:
        annotations[doc_id] = []
    
    # Add or update the annotation
    annotation_id = annotation.get('id')
    if annotation_id:
        # Update an existing annotation
        for i, ann in enumerate(annotations[doc_id]):
            if ann.get('id') == annotation_id:
                annotations[doc_id][i] = annotation
                break
    else:
        # Add a new annotation
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
        return jsonify({"status": "error", "message": "Missing data"}), 400
    
    annotations = load_annotations()
    
    if doc_id in annotations:
        annotations[doc_id] = [ann for ann in annotations[doc_id] if ann.get('id') != annotation_id]
        save_annotations(annotations)
    
    return jsonify({"status": "success"})

@app.route('/api/upload_document', methods=['POST'])
def upload_document():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file uploaded"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "No file selected"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_content = file.read().decode('utf-8')
        
        documents = load_documents()
        
        # Create a new document
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
        # Convert to spaCy format
        spacy_data = []
        for doc_id, doc_annotations in annotations.items():
            # Find the corresponding document
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
        
        # Save the data to a file
        output_file = os.path.join(DATA_DIR, 'spacy_annotations.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(spacy_data, f, indent=2, ensure_ascii=False)
            
        return jsonify({"status": "success", "file": output_file, "data": spacy_data})
    else:
        # Default JSON format
        return jsonify(annotations)

@app.route('/api/recognize', methods=['POST'])
def recognize_entities():
    data = request.json
    text = data.get('text')
    
    if not text:
        return jsonify({"status": "error", "message": "Missing text"}), 400
    
    try:
        # Initialize NER system
        ner = DynamicNERGiuridico()
        
        # Recognize entities
        result = ner.process(text)
        
        # Convert entities to labeler format
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
        print(f"Error recognizing entities: {e}")
        return jsonify({"status": "error", "message": f"Error recognizing entities: {str(e)}"}), 500

@app.route('/api/train_model', methods=['POST'])
def train_model():
    try:
        # Export annotations in a format compatible with the NER system
        annotations = load_annotations()
        documents = load_documents()
        
        # Create spaCy format data
        ner_data = []
        for doc_id, doc_annotations in annotations.items():
            # Find the corresponding document
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
        
        # Save the data to a file
        output_file = os.path.join(DATA_DIR, 'ner_training_data.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(ner_data, f, indent=2, ensure_ascii=False)
        
        # Here you would implement a call to the training method
        # of the NER system with the saved data
        
        return jsonify({
            "status": "success", 
            "message": "Training data exported successfully",
            "file": output_file
        })
    except Exception as e:
        print(f"Error exporting training data: {e}")
        return jsonify({"status": "error", "message": f"Error: {str(e)}"}), 500

if __name__ == '__main__':
    # Make sure the data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Create empty files if they don't exist
    if not os.path.exists(os.path.join(DATA_DIR, 'documents.json')):
        with open(os.path.join(DATA_DIR, 'documents.json'), 'w', encoding='utf-8') as f:
            json.dump([], f)
    
    if not os.path.exists(os.path.join(DATA_DIR, 'annotations.json')):
        with open(os.path.join(DATA_DIR, 'annotations.json'), 'w', encoding='utf-8') as f:
            json.dump({}, f)
    
    # Print a confirmation that we're ready to start
    print("\nAnnotation interface initialized and ready to start")
    print(f"Using entity types: {', '.join(entity['id'] for entity in ENTITY_TYPES)}")
    
    app.run(host='0.0.0.0', port=8080, debug=True)