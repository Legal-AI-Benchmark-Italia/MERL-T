#!/usr/bin/env python3
import os
import json
import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename

# Aggiungi il percorso del progetto al path di Python
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    # Importa i moduli del sistema NER
    from src.entities.entity_manager import get_entity_manager
    from src.ner import DynamicNERGiuridico
    
    # Inizializza il gestore delle entità
    entity_manager = get_entity_manager()
    
    # Ottieni i tipi di entità dal gestore dinamico
    ENTITY_TYPES = []
    for name, info in entity_manager.get_all_entity_types().items():
        ENTITY_TYPES.append({
            "id": name,
            "name": info.get("display_name", name),
            "color": info.get("color", "#CCCCCC")
        })
    
    print("Integrazione con il sistema NER completata con successo")
except Exception as e:
    print(f"Errore nell'integrazione con il sistema NER: {e}")
    # Fallback ai tipi di entità predefiniti
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

# Configurazione
DATA_DIR = 'data'

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

def convert_annotations_to_ner_format(annotations, documents):
    """
    Converte le annotazioni dal formato del labeler al formato utilizzato dal sistema NER.
    
    Args:
        annotations: Annotazioni nel formato del labeler.
        documents: Documenti annotati.
        
    Returns:
        Dati nel formato utilizzato dal sistema NER.
    """
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
    
    return ner_data

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
        
        # Salva i dati in un file
        output_file = os.path.join(DATA_DIR, 'spacy_annotations.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(spacy_data, f, indent=2, ensure_ascii=False)
            
        return jsonify({"status": "success", "file": output_file, "data": spacy_data})
    else:
        # Formato JSON predefinito
        return jsonify(annotations)

@app.route('/api/recognize', methods=['POST'])
def recognize_entities():
    """
    Endpoint per riconoscere entità in un testo utilizzando il sistema NER-Giuridico.
    """
    data = request.json
    text = data.get('text')
    
    if not text:
        return jsonify({"status": "error", "message": "Testo mancante"}), 400
    
    try:
        # Inizializza il sistema NER
        ner = DynamicNERGiuridico()
        
        # Riconosci le entità
        result = ner.process(text)
        
        # Converti le entità nel formato del labeler
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
        print(f"Errore nel riconoscimento delle entità: {e}")
        return jsonify({"status": "error", "message": f"Errore nel riconoscimento delle entità: {str(e)}"}), 500

@app.route('/api/train_model', methods=['POST'])
def train_model():
    """
    Endpoint per addestrare il modello NER con le annotazioni correnti.
    """
    try:
        # Esporta le annotazioni in formato compatibile con il sistema NER
        annotations = load_annotations()
        documents = load_documents()
        
        ner_data = convert_annotations_to_ner_format(annotations, documents)
        
        # Salva i dati in un file
        output_file = os.path.join(DATA_DIR, 'ner_training_data.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(ner_data, f, indent=2, ensure_ascii=False)
        
        # Qui dovrebbe essere implementata la chiamata al metodo di addestramento
        # del sistema NER con i dati salvati
        
        return jsonify({
            "status": "success", 
            "message": "Dati di addestramento esportati con successo",
            "file": output_file
        })
    except Exception as e:
        print(f"Errore nell'esportazione dei dati di addestramento: {e}")
        return jsonify({"status": "error", "message": f"Errore: {str(e)}"}), 500

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