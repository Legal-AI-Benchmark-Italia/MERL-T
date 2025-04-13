#!/usr/bin/env python3
"""
Interfaccia web per l'annotazione di entità giuridiche e la gestione dei tipi di entità.
File completo con implementazioni strutturate e robuste, ottimizzato e corretto.
File completo con implementazioni strutturate e robuste, ottimizzato e corretto.
"""

import functools
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
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, session, flash, g, abort, make_response
from werkzeug.utils import secure_filename
import configparser
from pathlib import Path
from .db_manager import AnnotationDBManager
from ..entities.entity_manager import get_entity_manager, EntityType
import uuid

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
    """
    Configura l'ambiente dell'applicazione, aggiungendo i percorsi necessari
    al sys.path e identificando la radice del progetto.
    
    Returns:
        tuple: Directory corrente e root del progetto
    """
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

# Configurazione dell'app Flask
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'chiave_segreta_predefinita')  # In produzione usa una chiave sicura
app.permanent_session_lifetime = datetime.timedelta(days=1)  # Sessione valida per 1 giorno

# Directory per i dati e i backup
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)
BACKUP_DIR = os.path.join(DATA_DIR, 'backup')
os.makedirs(BACKUP_DIR, exist_ok=True)

# --- Funzioni di supporto per l'autenticazione ---

# Assicura che esista un utente amministratore
def ensure_admin_exists(db_manager):
    """
    Verifica che esista almeno un utente amministratore nel database.
    Se non esiste, ne crea uno predefinito.
    """
    try:
        annotation_logger.info("Verifico l'esistenza di un utente amministratore...")
        users = db_manager.get_all_users()
        
        if not users:
            annotation_logger.warning("Nessun utente trovato nel database.")
            create_default_admin(db_manager.db_path)
            return
            
        admin_exists = any(user.get('role') == 'admin' for user in users)
        
        if not admin_exists:
            annotation_logger.warning("Nessun utente amministratore trovato. Creazione utente admin predefinito.")
            create_default_admin(db_manager.db_path)
        else:
            annotation_logger.info("Utente amministratore esistente trovato nel database.")
    except Exception as e:
        annotation_logger.error(f"Errore durante la verifica degli utenti amministratori: {e}")
        annotation_logger.exception(e)

def create_default_admin(db_path):
    """
    Crea un utente amministratore predefinito nel database.
    
    Args:
        db_path: Percorso del database SQLite
    """
    try:
        from .__init_db import create_admin_user
        success = create_admin_user(db_path, username='admin', password='admin')
        if success:
            annotation_logger.info("Utente amministratore predefinito creato con successo.")
        else:
            annotation_logger.error("Impossibile creare l'utente amministratore predefinito.")
    except ImportError:
        annotation_logger.error("Impossibile importare lo script di inizializzazione del database.")
        try:
            # Fallback: crea l'utente direttamente
            import hashlib
            import datetime
            import uuid
            import sqlite3
            
            # Hash della password
            hashed_password = hashlib.sha256('admin'.encode()).hexdigest()
            
            # Dati utente
            user_id = f"user_{str(uuid.uuid4())}"
            now = datetime.datetime.now().isoformat()
            
            # Connetti al database
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Assicurati che la tabella esista
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                full_name TEXT,
                role TEXT DEFAULT 'admin',
                email TEXT,
                active INTEGER DEFAULT 1,
                date_created TEXT,
                date_last_login TEXT
            )
            ''')
            
            # Inserisci utente admin
            cursor.execute(
                """
                INSERT OR IGNORE INTO users 
                (id, username, password, full_name, role, active, date_created)
                VALUES (?, ?, ?, ?, 'admin', 1, ?)
                """,
                (user_id, 'admin', hashed_password, 'Amministratore', now)
            )
            
            conn.commit()
            conn.close()
            
            annotation_logger.info("Utente amministratore predefinito creato con metodo alternativo.")
        except Exception as e:
            annotation_logger.error(f"Errore nella creazione dell'utente amministratore: {e}")
            annotation_logger.exception(e)

def login_required(view):
    """
    Decoratore per richiedere l'accesso a una rotta.
    
    Args:
        view: Funzione vista da decorare
        
    Returns:
        Funzione wrapper che verifica l'autenticazione
    """
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not session.get('user_id'):
            # Memorizza l'URL originale per il redirect post-login
            session['next_url'] = request.url
            annotation_logger.info(f"Accesso negato a {request.path}: utente non autenticato")
            flash('È necessario accedere per visualizzare questa pagina.', 'warning')
            return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view

def admin_required(view):
    """
    Decoratore per richiedere accesso da amministratore.
    
    Args:
        view: Funzione vista da decorare
        
    Returns:
        Funzione wrapper che verifica il ruolo admin
    """
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if not session.get('user_id'):
            session['next_url'] = request.url
            annotation_logger.info(f"Accesso negato a {request.path}: utente non autenticato")
            flash('È necessario accedere per visualizzare questa pagina.', 'warning')
            return redirect(url_for('login'))
        
        if session.get('user_role') != 'admin':
            annotation_logger.warning(f"Accesso negato a {request.path}: l'utente {session.get('username')} non è admin")
            flash('Accesso non autorizzato. È richiesto un account amministratore.', 'danger')
            return redirect(url_for('index'))
        
        return view(**kwargs)
    return wrapped_view

@app.before_request
def load_logged_in_user():
    """
    Carica l'utente in base alla sessione prima di ogni richiesta.
    """
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
        return
    
    try:
        g.user = db_manager.get_user_by_id(user_id)
        
        # Se l'utente non è trovato nel database ma la sessione indica che è loggato
        if g.user is None:
            annotation_logger.warning(f"User with ID {user_id} not found in database but has active session")
            session.clear()
            g.user = None
            flash('La tua sessione è scaduta. Effettua nuovamente l\'accesso.', 'warning')
            return
            
        # Rimuovi la password per sicurezza
        if g.user and 'password' in g.user:
            g.user.pop('password', None)
            
        # Verifica che l'utente sia attivo
        if not g.user.get('active', 1):
            annotation_logger.warning(f"User with ID {user_id} is inactive but has active session")
            session.clear()
            g.user = None
            flash('Il tuo account è stato disattivato. Contatta l\'amministratore.', 'warning')
    except Exception as e:
        annotation_logger.error(f"Error loading user from session: {e}")
        annotation_logger.exception(e)
        # In caso di errore, pulisci la sessione per evitare problemi persistenti
        session.clear()
        g.user = None

# Aggiungi questo decorator a app.py all'inizio del file, dopo le importazioni

def api_error_handler(func):
    """
    Decorator per gestire uniformemente gli errori delle API.
    Converte le eccezioni in risposte JSON con codici di stato appropriati.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            annotation_logger.warning(f"API Validation Error in {func.__name__}: {str(e)}")
            return jsonify({
                "status": "error", 
                "message": str(e), 
                "error_type": "ValidationError"
            }), 400
        except FileNotFoundError as e:
            annotation_logger.warning(f"API Resource Not Found in {func.__name__}: {str(e)}")
            return jsonify({
                "status": "error", 
                "message": str(e), 
                "error_type": "NotFoundError"
            }), 404
        except PermissionError as e:
            annotation_logger.warning(f"API Permission Error in {func.__name__}: {str(e)}")
            return jsonify({
                "status": "error", 
                "message": str(e), 
                "error_type": "PermissionError"
            }), 403
        except Exception as e:
            annotation_logger.error(f"API Unhandled Error in {func.__name__}: {str(e)}", exc_info=True)
            return jsonify({
                "status": "error", 
                "message": "Si è verificato un errore interno nel server", 
                "error_type": type(e).__name__
            }), 500
    
    # Mantenere lo stesso nome della funzione per Flask
    wrapper.__name__ = func.__name__
    return wrapper

# --- API Endpoints ---

@app.route('/api/user_stats')
@login_required
def api_user_stats():
    """
    API per le statistiche utente.
    """
    user_id = request.args.get('user_id')
    days = request.args.get('days', 30, type=int)
    
    # Solo admin possono vedere statistiche di altri utenti
    if user_id and user_id != session.get('user_id') and session.get('user_role') != 'admin':
        return jsonify({"status": "error", "message": "Non autorizzato"}), 403
    
    # Se non è specificato un user_id, usa quello dell'utente corrente
    # a meno che sia admin (in quel caso restituisce statistiche globali)
    if not user_id and session.get('user_role') != 'admin':
        user_id = session.get('user_id')
    
    stats = db_manager.get_user_stats(user_id, days)
    return jsonify(stats)

@app.route('/api/users')
@login_required
@admin_required
def api_get_users():
    """API endpoint per ottenere la lista degli utenti."""
    try:
        users = db_manager.get_all_users()
        
        # Rimuovere campi sensibili come password
        for user in users:
            if 'password' in user:
                user.pop('password', None)
        
        return jsonify({
            "status": "success",
            "users": users
        })
    except Exception as e:
        annotation_logger.error(f"Error fetching users: {e}")
        return jsonify({
            "status": "error",
            "message": f"Errore nel recupero degli utenti: {str(e)}"
        }), 500

@app.route('/assignments')
@login_required
def assignments():
    """Mostra i documenti assegnati all'utente corrente."""
    try:
        user_id = g.user['id']
        status_filter = request.args.get('status')
        
        assigned_docs = db_manager.get_documents(status=status_filter, assigned_to=user_id)
        return render_template('assignments.html', documents=assigned_docs, current_status=status_filter)
    except Exception as e:
        annotation_logger.error(f"Error fetching assignments for user {g.user['id']}: {e}", exc_info=True)
        flash("Si è verificato un errore nel caricamento dei documenti assegnati.", "danger")
        return render_template('assignments.html', documents=[], current_status=status_filter)

@app.route('/api/assign_document', methods=['POST'])
@admin_required
def api_assign_document():
    """
    Assegna un documento a un utente (API).
    """
    data = request.json
    doc_id = data.get('doc_id')
    user_id = data.get('user_id')
    
    if not doc_id or not user_id:
        return jsonify({"status": "error", "message": "Dati mancanti"}), 400
    
    # Verifica che documento e utente esistano
    documents = db_manager.get_documents()  # Rimuovi doc_id come argomento
    document = next((doc for doc in documents if doc['id'] == doc_id), None)
    user = db_manager.get_user_by_id(user_id)
    
    if not document:
        return jsonify({"status": "error", "message": "Documento non trovato"}), 404
    
    if not user:
        return jsonify({"status": "error", "message": "Utente non trovato"}), 404
    
    success = db_manager.assign_document(doc_id, user_id, session.get('user_id'))
    
    if not success:
        return jsonify({"status": "error", "message": "Errore nell'assegnazione del documento"}), 500
    
    return jsonify({
        "status": "success", 
        "message": f"Documento assegnato con successo a {user['username']}"
    })

@app.route('/api/document_status', methods=['POST'])
@login_required
def api_update_document_status():
    """API endpoint per cambiare lo stato di un documento."""
    data = request.json
    doc_id = data.get('doc_id')
    status = data.get('status')
    
    if not doc_id or not status:
        raise ValueError("ID documento ('doc_id') e stato ('status') sono richiesti.")
    
    valid_statuses = ['pending', 'completed', 'skipped']
    if status not in valid_statuses:
        raise ValueError(f"Stato non valido: {status}. Valori accettati: {', '.join(valid_statuses)}")
    
    # Optional: Permission check
    document = db_manager.get_document(doc_id)
    if not document:
        raise FileNotFoundError(f"Documento con ID {doc_id} non trovato.")
    
    # Verifica che l'utente sia assegnato al documento o sia admin
    if document.get('assigned_to') != g.user['id'] and g.user.get('role') != 'admin':
        raise PermissionError("Non hai i permessi per modificare lo stato di questo documento.")
    
    success = db_manager.update_document_status(doc_id, status, g.user['id'])
    if not success:
        raise RuntimeError(f"Errore durante l'aggiornamento dello stato del documento {doc_id}.")
    
    annotation_logger.info(f"User '{g.user['username']}' changed document {doc_id} status to {status}.")
    
    return jsonify({
        "status": "success", 
        "message": f"Stato del documento aggiornato a '{status}'."
    })

@app.route('/api/next_document', methods=['GET'])
@login_required
def api_get_next_document():
    """API endpoint per ottenere il documento successivo da annotare."""
    current_doc_id = request.args.get('current_doc_id')
    status_filter = request.args.get('status', 'pending')
    
    if not current_doc_id:
        raise ValueError("ID del documento corrente ('current_doc_id') è richiesto.")
    
    # Filtra per documenti assegnati all'utente corrente (a meno che non sia admin)
    user_id = g.user['id'] if g.user.get('role') != 'admin' else None
    
    next_doc = db_manager.get_next_document(current_doc_id, user_id, status_filter)
    
    if not next_doc:
        return jsonify({
            "status": "info",
            "message": "Nessun altro documento disponibile.",
            "document": None
        })
    
    return jsonify({
        "status": "success",
        "document": next_doc
    })

@app.route('/api/document_batch_assign', methods=['POST'])
@admin_required
def api_batch_assign_documents():
    """API endpoint per assegnare documenti in batch a un utente."""
    data = request.json
    doc_ids = data.get('doc_ids', [])
    user_id = data.get('user_id')
    
    if not doc_ids or not user_id:
        raise ValueError("Lista di ID documenti ('doc_ids') e ID utente ('user_id') sono richiesti.")
    
    if not isinstance(doc_ids, list):
        raise ValueError("'doc_ids' deve essere una lista di ID documento.")
    
    # Verifica che l'utente esista
    user = db_manager.get_user_by_id(user_id)
    if not user:
        raise FileNotFoundError(f"Utente con ID {user_id} non trovato.")
    
    results = {
        "success": [],
        "failed": []
    }
    
    for doc_id in doc_ids:
        try:
            success = db_manager.assign_document(doc_id, user_id, g.user['id'])
            if success:
                results["success"].append(doc_id)
            else:
                results["failed"].append({"id": doc_id, "reason": "Errore durante l'assegnazione"})
        except Exception as e:
            results["failed"].append({"id": doc_id, "reason": str(e)})
    
    annotation_logger.info(f"Admin '{g.user['username']}' batch assigned {len(results['success'])} documents to user '{user.get('username')}'.")
    
    return jsonify({
        "status": "success" if results["success"] else "error",
        "message": f"{len(results['success'])} documenti assegnati con successo a {user.get('username')}.",
        "results": results
    })

@app.route('/api/entity_types/export', methods=['GET'])
@login_required
@admin_required
def export_entity_types():
    """API per esportare tutti i tipi di entità in formato JSON."""
    try:
        entity_manager = get_entity_manager()
        entities = entity_manager.get_all_entities()
        
        entities_data = []
        for entity in entities:
            entities_data.append({
                "id": entity.id,
                "name": entity.name,
                "display_name": entity.display_name,
                "category": entity.category,
                "color": entity.color,
                "description": entity.description,
                "metadata_schema": entity.metadata_schema,
                "patterns": entity.patterns,
                "system": entity.system
            })
        
        if request.args.get('download', 'false').lower() == 'true':
            # Genera un nome di file con timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"entity_types_export_{timestamp}.json"
            
            # Crea una risposta per il download
            response = make_response(json.dumps(entities_data, indent=2, ensure_ascii=False))
            response.headers.set('Content-Type', 'application/json')
            response.headers.set('Content-Disposition', f'attachment; filename="{filename}"')
            return response
        
        return jsonify({
            "status": "success",
            "message": f"Esportati {len(entities_data)} tipi di entità",
            "entity_types": entities_data
        })
    except Exception as e:
        annotation_logger.error(f"Errore nell'esportazione dei tipi di entità: {e}")
        return jsonify({
            "status": "error",
            "message": f"Errore: {str(e)}"
        }), 500

@app.route('/api/entity_types/import', methods=['POST'])
@login_required
@admin_required
def import_entity_types():
    """API per importare tipi di entità da un file JSON."""
    try:
        if 'file' not in request.files:
            return jsonify({
                "status": "error",
                "message": "Nessun file caricato"
            }), 400
            
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                "status": "error",
                "message": "Nessun file selezionato"
            }), 400
            
        if not file.filename.endswith('.json'):
            return jsonify({
                "status": "error",
                "message": "Il file deve essere in formato JSON"
            }), 400
            
        # Leggi e valida il JSON
        try:
            content = file.read().decode('utf-8')
            entities_data = json.loads(content)
            
            if not isinstance(entities_data, list):
                return jsonify({
                    "status": "error",
                    "message": "Il file JSON deve contenere un array di entità"
                }), 400
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": f"Errore nella lettura del file JSON: {str(e)}"
            }), 400
        
        # Flag per la modalità di importazione
        mode = request.form.get('mode', 'merge')  # 'merge' o 'replace'
        
        entity_manager = get_entity_manager()
        
        if mode == 'replace':
            # Rimuovi tutti i tipi di entità non di sistema
            current_entities = entity_manager.get_all_entities()
            for entity in current_entities:
                if not entity.system:
                    entity_manager.remove_entity(entity.id)
        
        # Importa le entità
        imported = 0
        skipped = 0
        errors = []
        
        for entity_data in entities_data:
            try:
                # Verifica se l'entità ha tutti i campi necessari
                required_fields = ["name", "display_name", "category", "color"]
                for field in required_fields:
                    if field not in entity_data:
                        errors.append(f"Entità {entity_data.get('name', 'unknown')} manca del campo {field}")
                        continue
                
                # Verifica se esiste già un'entità con lo stesso nome
                existing_entity = None
                for e in entity_manager.get_all_entities():
                    if e.name == entity_data["name"]:
                        existing_entity = e
                        break
                
                # Se l'entità esiste già e la modalità è merge, aggiornala
                if existing_entity and mode == 'merge':
                    # Se è un'entità di sistema, non aggiornare
                    if existing_entity.system:
                        skipped += 1
                        continue
                    
                    # Aggiorna i campi tranne l'ID e il flag system
                    entity_id = existing_entity.id
                    system_flag = existing_entity.system
                    
                    entity = EntityType(
                        id=entity_id,
                        name=entity_data["name"],
                        display_name=entity_data["display_name"],
                        category=entity_data["category"],
                        color=entity_data["color"],
                        description=entity_data.get("description", ""),
                        metadata_schema=entity_data.get("metadata_schema", {}),
                        patterns=entity_data.get("patterns", []),
                        system=system_flag
                    )
                    
                    entity_manager.update_entity(entity)
                    imported += 1
                # Se l'entità non esiste o se la modalità è replace, creala
                elif not existing_entity or mode == 'replace':
                    # Genera un nuovo ID e imposta system=False
                    entity = EntityType(
                        id=str(uuid.uuid4()),
                        name=entity_data["name"],
                        display_name=entity_data["display_name"],
                        category=entity_data["category"],
                        color=entity_data["color"],
                        description=entity_data.get("description", ""),
                        metadata_schema=entity_data.get("metadata_schema", {}),
                        patterns=entity_data.get("patterns", []),
                        system=False
                    )
                    
                    entity_manager.add_entity(entity)
                    imported += 1
                # Se l'entità esiste ma non è in modalità merge, saltala
                else:
                    skipped += 1
            except Exception as e:
                errors.append(f"Errore importando {entity_data.get('name', 'unknown')}: {str(e)}")
                skipped += 1
        
        # Prepara la risposta
        status = "success" if imported > 0 else "warning"
        message = f"Importati {imported} tipi di entità"
        if skipped > 0:
            message += f", saltati {skipped} tipi"
        if errors:
            message += f". {len(errors)} errori."
        
        return jsonify({
            "status": status,
            "message": message,
            "imported": imported,
            "skipped": skipped,
            "errors": errors
        })
    except Exception as e:
        annotation_logger.error(f"Errore nell'importazione dei tipi di entità: {e}")
        return jsonify({
            "status": "error",
            "message": f"Errore: {str(e)}"
        }), 500
# --- Rotte per l'autenticazione ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Gestisce il login degli utenti.
    """
    # Log delle informazioni di sessione per debug
    current_session = {k: v for k, v in session.items()}
    annotation_logger.debug(f"Current session before login: {current_session}")
    
    # Utente già autenticato
    if session.get('user_id'):
        annotation_logger.info(f"User already logged in: {session.get('username')}")
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        annotation_logger.info(f"Login attempt for user: {username}")
        
        error = None
        
        if not username:
            error = 'Username richiesto.'
        elif not password:
            error = 'Password richiesta.'
        
        if error is None:
            user = db_manager.verify_user(username, password)
            
            if user:
                session.clear()
                session.permanent = remember
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['user_role'] = user['role']
                
                annotation_logger.info(f"User logged in successfully: {username}")
                annotation_logger.debug(f"Session after login: {dict(session)}")
                
                # Log attività
                db_manager.log_user_activity(
                    user_id=user['id'],
                    action_type='login'
                )
                
                # Redirect alla pagina originale o all'indice
                next_url = session.pop('next_url', None) or url_for('index')
                flash(f'Benvenuto, {user["username"]}!', 'success')
                return redirect(next_url)
            else:
                annotation_logger.warning(f"Invalid credentials for user: {username}")
                error = 'Credenziali non valide.'
        
        flash(error, 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """
    Gestisce il logout dell'utente.
    """
    # Log attività
    if session.get('user_id'):
        db_manager.log_user_activity(
            user_id=session['user_id'],
            action_type='logout'
        )
    
    # Cancella sessione
    session.clear()
    flash('Disconnessione avvenuta con successo.', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Gestisce la registrazione di nuovi utenti (solo admin può accedere).
    """
    # Solo gli amministratori possono registrare nuovi utenti
    if session.get('user_role') != 'admin' and db_manager.get_all_users():
        flash('Solo gli amministratori possono registrare nuovi utenti.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        role = request.form.get('role', 'annotator')
        
        # Validazione
        error = None
        
        if not username:
            error = 'Username richiesto.'
        elif not password:
            error = 'Password richiesta.'
        elif password != confirm_password:
            error = 'Le password non corrispondono.'
        elif db_manager.get_user_by_username(username):
            error = f'L\'utente {username} è già registrato.'
        
        if error is None:
            # Il primo utente registrato diventa admin
            if not db_manager.get_all_users():
                role = 'admin'
            
            # Crea utente
            user = db_manager.create_user({
                'username': username,
                'password': password,
                'full_name': full_name,
                'email': email,
                'role': role,
                'active': 1
            })
            
            if user:
                flash('Utente registrato con successo!', 'success')
                if session.get('user_id'):
                    # Admin che registra un altro utente
                    db_manager.log_user_activity(
                        user_id=session['user_id'],
                        action_type='create_user',
                        details=f"Creato utente {username}"
                    )
                    return redirect(url_for('admin_users'))
                else:
                    # Primo utente o autoiscrizione
                    return redirect(url_for('login'))
            else:
                error = 'Errore durante la registrazione dell\'utente.'
        
        flash(error, 'danger')
    
    return render_template('register.html')

# --- Rotte per la gestione degli utenti (admin) ---

@app.route('/admin/users')
@admin_required
def admin_users():
    """
    Visualizza e gestisce gli utenti (solo admin).
    """
    users = db_manager.get_all_users()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/<user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """
    Modifica un utente esistente (solo admin).
    """
    user = db_manager.get_user_by_id(user_id)
    if not user:
        flash('Utente non trovato.', 'danger')
        return redirect(url_for('admin_users'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        role = request.form.get('role')
        active = request.form.get('active') == 'on'
        
        # Validazione
        error = None
        
        if not username:
            error = 'Username richiesto.'
        elif username != user['username'] and db_manager.get_user_by_username(username):
            error = f'L\'utente {username} è già registrato.'
        
        if error is None:
            # Prepara gli aggiornamenti
            updates = {
                'username': username,
                'full_name': full_name,
                'email': email,
                'role': role,
                'active': 1 if active else 0
            }
            
            # Aggiorna password solo se fornita
            if password:
                updates['password'] = password
            
            if db_manager.update_user(user_id, updates):
                db_manager.log_user_activity(
                    user_id=session['user_id'],
                    action_type='update_user',
                    details=f"Aggiornato utente {username}"
                )
                flash('Utente aggiornato con successo!', 'success')
                return redirect(url_for('admin_users'))
            else:
                error = 'Errore durante l\'aggiornamento dell\'utente.'
        
        flash(error, 'danger')
    
    return render_template('edit_user.html', user=user)

@app.route('/profile')
@login_required
def profile():
    """
    Visualizza e modifica il proprio profilo utente.
    """
    user_id = session.get('user_id')
    user = db_manager.get_user_by_id(user_id)
    
    if not user:
        session.clear()
        flash('Utente non trovato.', 'danger')
        return redirect(url_for('login'))
    
    # Ottieni statistiche dell'utente
    stats = db_manager.get_user_stats(user_id)
    
    # Ensure stats has the expected structure to prevent template errors
    if not isinstance(stats, dict):
        stats = {}
    if 'actions_by_type' not in stats:
        stats['actions_by_type'] = {}
    
    return render_template('profile.html', user=user, stats=stats)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """
    Modifica il proprio profilo utente.
    """
    user_id = session.get('user_id')
    user = db_manager.get_user_by_id(user_id)
    
    if not user:
        session.clear()
        flash('Utente non trovato.', 'danger')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        
        # Validazione
        error = None
        
        # Per cambiare la password serve la password attuale
        if new_password:
            if not current_password:
                error = 'Password attuale richiesta per cambiarla.'
            elif new_password != confirm_password:
                error = 'Le nuove password non corrispondono.'
            else:
                # Verifica password attuale
                import hashlib
                hashed_current = hashlib.sha256(current_password.encode()).hexdigest()
                if user['password'] != hashed_current:
                    error = 'Password attuale non corretta.'
        
        if error is None:
            # Prepara gli aggiornamenti
            updates = {
                'full_name': full_name,
                'email': email
            }
            
            # Aggiorna password solo se fornita e validata
            if new_password:
                updates['password'] = new_password
            
            if db_manager.update_user(user_id, updates):
                db_manager.log_user_activity(
                    user_id=user_id,
                    action_type='update_profile'
                )
                flash('Profilo aggiornato con successo!', 'success')
                return redirect(url_for('profile'))
            else:
                error = 'Errore durante l\'aggiornamento del profilo.'
        
        flash(error, 'danger')
    
    return render_template('edit_profile.html', user=user)

# --- Dashboard per statistiche ---

@app.route('/dashboard')
@login_required
def dashboard():
    """
    Dashboard con statistiche globali e per utente.
    """
    try:
        # Gli admin vedono le statistiche di tutti
        if session.get('user_role') == 'admin':
            stats = db_manager.get_user_stats()
            global_view = True
        else:
            # Gli utenti normali vedono solo le proprie
            user_id = session.get('user_id')
            stats = db_manager.get_user_stats(user_id)
            global_view = False
        
        # Ensure stats has the expected structure to prevent template errors
        if not isinstance(stats, dict):
            stats = {}
        if 'actions_by_type' not in stats:
            stats['actions_by_type'] = {}
        if 'total_annotations' not in stats:
            stats['total_annotations'] = 0
        if 'documents_modified' not in stats:
            stats['documents_modified'] = 0
        if 'annotations_by_type' not in stats:
            stats['annotations_by_type'] = {}
        if 'activity_by_day' not in stats:
            stats['activity_by_day'] = {}
        if 'users' not in stats and global_view:
            stats['users'] = []
        
        # Ottieni tutti gli utenti per il filtro (solo per admin)
        users = []
        if global_view:
            users = db_manager.get_all_users()
        
        return render_template('dashboard.html', stats=stats, global_view=global_view, users=users)
    except Exception as e:
        annotation_logger.error(f"Errore nel caricamento del dashboard: {e}")
        flash('Si è verificato un errore nel caricamento delle statistiche.', 'danger')
        return redirect(url_for('index'))
    
# --- Aggiungi questa sezione dopo la definizione di app Flask ---
# Carica la configurazione
def load_config():
    """
    Carica la configurazione dell'applicazione dal file config.ini o crea una
    configurazione predefinita se non esiste.
    
    Returns:
        ConfigParser: Oggetto configurazione
    """
    config = configparser.ConfigParser()
    config_path = os.environ.get('NER_CONFIG', 'config.ini')
    
    # Crea la configurazione predefinita se non esiste
    if not os.path.exists(config_path):
        config['Database'] = {
            'path': os.path.join(DATA_DIR, 'annotations.db'),
            'backups': os.path.join(BACKUP_DIR),
            'max_backups': '10'
        }
        
        with open(config_path, 'w') as f:
            config.write(f)
        
        annotation_logger.info(f"Creato file di configurazione predefinito: {config_path}")
    
    config.read(config_path)
    return config

# --- Funzioni di supporto per le template ---

@app.context_processor
def utility_processor():
    """
    Aggiunge funzioni di utilità ai template.
    """
    def format_date(date_str):
        """Formatta una data ISO in un formato leggibile."""
        if not date_str:
            return "N/A"
        try:
            date_obj = datetime.datetime.fromisoformat(date_str)
            return date_obj.strftime("%d/%m/%Y %H:%M")
        except:
            return date_str
    
    return dict(format_date=format_date)

# Carica la configurazione
config = load_config()

# Inizializza il database manager
db_path = config.get('Database', 'path', fallback=os.path.join(DATA_DIR, 'annotations.db'))
backup_dir = config.get('Database', 'backups', fallback=BACKUP_DIR)
max_backups = config.getint('Database', 'max_backups', fallback=10)

try:
    from .db_migrations import run_migrations
except ImportError:
    annotation_logger.warning("Could not import db_migrations module")
    run_migrations = None

# Then modify the section where db_manager is initialized:
annotation_logger.info(f"Utilizzo database in: {db_path}")
annotation_logger.info(f"Directory backup: {backup_dir}")

# Initialize database manager
db_manager = AnnotationDBManager(db_path=db_path, backup_dir=backup_dir)
ensure_admin_exists(db_manager)

# Run migrations before initializing db_manager
if run_migrations:
    try:
        annotation_logger.info(f"Running database migrations on {db_path}")
        run_migrations(db_path)
    except Exception as e:
        annotation_logger.error(f"Error running migrations: {e}")

@app.before_request
def update_context():
    """Aggiorna il contesto dell'applicazione prima di ogni richiesta."""
    # Assicurati che il gestore delle entità sia sempre aggiornato
    app.config['ENTITY_MANAGER'] = get_entity_manager()

# -----------------------------------------------------------------------------
# Funzioni helper per la persistenza dei documenti e delle annotazioni
# -----------------------------------------------------------------------------
def load_documents() -> List[Dict[str, Any]]:
    """
    Carica i documenti dal database.
    
    Returns:
        Lista di documenti
    """
    try:
        return db_manager.get_documents()
    except Exception as e:
        annotation_logger.error(f"Errore nel caricamento dei documenti: {e}")
        return []

def save_documents(documents: List[Dict[str, Any]]) -> bool:
    """
    Salva i documenti nel database.
    
    Args:
        documents: Lista di documenti da salvare
        
    Returns:
        True se salvati con successo, False altrimenti
    """
    try:
        for doc in documents:
            db_manager.save_document(doc)
        return True
    except Exception as e:
        annotation_logger.error(f"Errore nel salvataggio dei documenti: {e}")
        return False
    
def load_annotations() -> Dict[str, List[Dict[str, Any]]]:
    """
    Carica le annotazioni dal database.
    
    Returns:
        Dizionario di annotazioni raggruppate per documento
    """
    try:
        return db_manager.get_annotations()
    except Exception as e:
        annotation_logger.error(f"Errore nel caricamento delle annotazioni: {e}")
        return {}

def save_annotations(annotations: Dict[str, List[Dict[str, Any]]]) -> bool:
    """
    Salva le annotazioni nel database.
    
    Args:
        annotations: Dizionario di annotazioni raggruppate per documento
        
    Returns:
        True se salvate con successo, False altrimenti
    """
    try:
        for doc_id, doc_annotations in annotations.items():
            for annotation in doc_annotations:
                db_manager.save_annotation(doc_id, annotation)
        return True
    except Exception as e:
        annotation_logger.error(f"Errore nel salvataggio delle annotazioni: {e}")
        return False

def cleanup_backups(max_backups: int = None):
    """
    Effettua la pulizia dei backup più vecchi.
    
    Args:
        max_backups: Numero massimo di backup da mantenere
    """
    if max_backups is None:
        max_backups = config.getint('Database', 'max_backups', fallback=10)
    
    try:
        db_manager.cleanup_backups(max_backups)
    except Exception as e:
        annotation_logger.error(f"Errore nella pulizia dei backup: {e}")


# -----------------------------------------------------------------------------
# Gestori di errori e middleware per il logging
# -----------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    """Gestore per errori 404."""
    return jsonify({"status": "error", "message": "Risorsa non trovata"}), 404

@app.errorhandler(500)
def server_error(e):
    """Gestore per errori 500."""
    annotation_logger.error(f"Errore del server: {str(e)}")
    return jsonify({"status": "error", "message": "Errore interno del server"}), 500

@app.before_request
def log_request():
    """Log delle richieste in arrivo."""
    annotation_logger.debug(f"Richiesta: {request.method} {request.path}")

@app.after_request
def log_response(response):
    """Log delle risposte in uscita."""
    annotation_logger.debug(f"Risposta: {response.status_code}")
    return response

# -----------------------------------------------------------------------------
# Endpoints per l'interfaccia di annotazione
# -----------------------------------------------------------------------------
@app.route('/')
@login_required
def index():
    """
    Pagina iniziale dell'applicazione.
    """
    documents = load_documents()
    return render_template('index.html', documents=documents)

@app.route('/annotate/<doc_id>')
@login_required
def annotate(doc_id):
    """
    Pagina di annotazione per un documento specifico.
    
    Args:
        doc_id: ID del documento da annotare
    """
    documents = load_documents()
    annotations = load_annotations()
    document = next((doc for doc in documents if doc['id'] == doc_id), None)
    if document is None:
        return redirect(url_for('index'))
    
    doc_annotations = annotations.get(doc_id, [])
    
    # Utilizza il nuovo EntityManager per ottenere le entità
    entity_manager = get_entity_manager()
    entity_types_raw = entity_manager.get_all_entities()
    
    # Converti nel formato atteso dall'interfaccia di annotazione
    entity_types = []
    for entity in entity_types_raw:
        entity_types.append({
            "id": entity.id,
            "name": entity.display_name,  # Usa display_name per la visualizzazione
            "color": entity.color
        })
    
    return render_template('annotate.html', document=document, annotations=doc_annotations, entity_types=entity_types)

@app.route('/entity_types')
@login_required
def entity_types():
    """
    Pagina di gestione dei tipi di entità.
    """
    return render_template('entity_types.html', entity_types=ENTITY_TYPES)

# --- API per la gestione delle entità ---

@app.route('/api/save_annotation', methods=['POST'])
@login_required
def save_annotation():
    """
    API per salvare un'annotazione.
    """
    try:
        data = request.json
        doc_id = data.get('doc_id')
        annotation = data.get('annotation')
        if not doc_id or not annotation:
            return jsonify({"status": "error", "message": "Dati mancanti"}), 400
        
        # Aggiungi l'ID utente corrente
        user_id = session.get('user_id')
        
        saved_annotation = db_manager.save_annotation(doc_id, annotation, user_id)
        if not saved_annotation:
            return jsonify({"status": "error", "message": "Errore nel salvataggio dell'annotazione"}), 500
        
        cleanup_backups()
        return jsonify({"status": "success", "annotation": saved_annotation})
    except Exception as e:
        annotation_logger.error(f"Errore nel salvataggio dell'annotazione: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/upload_document', methods=['POST'])
@login_required
def upload_document():
    """
    API per caricare un nuovo documento o più documenti.
    Supporta anche file da cartelle preservando la struttura opzionalmente.
    """
    try:
        if 'file' not in request.files:
            return jsonify({"status": "error", "message": "Nessun file caricato"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"status": "error", "message": "Nessun file selezionato"}), 400
        
        # Verifica che il formato del file sia supportato
        allowed_extensions = {'txt', 'md', 'html', 'xml', 'json', 'csv'}
        file_ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
        if file_ext not in allowed_extensions:
            return jsonify({"status": "error", "message": f"Formato file non supportato. Estensioni consentite: {', '.join(allowed_extensions)}"}), 400
        
        # Leggi il contenuto e controlla la dimensione
        try:
            file_content = file.read().decode('utf-8')
            if len(file_content) > 1000000:  # Circa 1MB di testo
                return jsonify({"status": "error", "message": "Il documento è troppo grande. Il limite è di circa 1MB di testo."}), 400
        except UnicodeDecodeError:
            return jsonify({"status": "error", "message": "Impossibile decodificare il file. Assicurati che sia un file di testo valido in formato UTF-8."}), 400
        
        # Gestione del percorso relativo (per upload da cartelle)
        document_title = secure_filename(file.filename)
        relative_path = request.form.get('relative_path', '')
        preserve_path = request.form.get('preserve_path') == 'true'
        
        # Se preserve_path è abilitato e c'è un percorso relativo, aggiungilo al titolo
        if preserve_path and relative_path and relative_path != file.filename:
            # Estrai solo la parte di percorso senza il nome del file
            path_prefix = os.path.dirname(relative_path)
            if path_prefix:
                # Sostituisci gli slash con caratteri sicuri 
                safe_prefix = secure_filename(path_prefix.replace('/', '_'))
                document_title = f"{safe_prefix}_{document_title}"
        
        # Generazione di un ID univoco per il documento
        documents = load_documents()
        timestamp = int(datetime.datetime.now().timestamp())
        doc_id = f"doc_{timestamp}_{len(documents) + 1}"
        
        # Creazione del documento
        document = {
            "id": doc_id,
            "title": document_title,
            "text": file_content,
            "date_created": datetime.datetime.now().isoformat(),
            "word_count": len(file_content.split()),
            "created_by": session.get('user_id')
        }
        
        # Salva anche il percorso relativo originale come metadato, se presente
        if relative_path:
            document["metadata"] = {"relative_path": relative_path}
        
        # Tenta di salvare il documento
        success = db_manager.save_document(document, session.get('user_id'))
        if not success:
            return jsonify({"status": "error", "message": "Errore nel salvataggio del documento"}), 500
        
        # Log di attività per l'audit trail
        annotation_logger.info(f"Utente {session.get('username')} ha caricato un documento: {document_title}")
        
        return jsonify({
            "status": "success", 
            "message": f"Documento '{document_title}' caricato con successo", 
            "document": document
        })
    except Exception as e:
        annotation_logger.error(f"Errore nell'upload del documento: {e}")
        annotation_logger.exception(e)
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/delete_annotation', methods=['POST'])
@login_required
def delete_annotation():
    """
    API per eliminare un'annotazione.
    """
    try:
        data = request.json
        doc_id = data.get('doc_id')
        annotation_id = data.get('annotation_id')
        if not doc_id or not annotation_id:
            return jsonify({"status": "error", "message": "Dati mancanti"}), 400
        
        success = db_manager.delete_annotation(annotation_id)
        if not success:
            return jsonify({"status": "error", "message": "Errore nell'eliminazione dell'annotazione"}), 500
        
        return jsonify({"status": "success"})
    except Exception as e:
        annotation_logger.error(f"Errore nell'eliminazione dell'annotazione: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/update_annotation', methods=['POST'])
@login_required
def update_annotation():
    """
    API per aggiornare un'annotazione esistente.
    """
    try:
        data = request.json
        doc_id = data.get('doc_id')
        annotation = data.get('annotation')
        if not doc_id or not annotation:
            return jsonify({"status": "error", "message": "Dati mancanti"}), 400
        
        annotation_id = annotation.get('id')
        if not annotation_id:
            return jsonify({"status": "error", "message": "ID annotazione mancante"}), 400
        
        saved_annotation = db_manager.save_annotation(doc_id, annotation)
        if not saved_annotation:
            return jsonify({"status": "error", "message": f"Errore nell'aggiornamento dell'annotazione {annotation_id}"}), 500
        
        cleanup_backups()
        return jsonify({"status": "success", "message": "Annotazione aggiornata con successo"})
    except Exception as e:
        annotation_logger.error(f"Errore nell'aggiornamento dell'annotazione: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/delete_document', methods=['POST'])
@login_required
def delete_document():
    """
    API per eliminare un documento.
    """
    try:
        data = request.json
        doc_id = data.get('doc_id')
        if not doc_id:
            return jsonify({"status": "error", "message": "ID documento mancante"}), 400
        
        success = db_manager.delete_document(doc_id)
        if not success:
            return jsonify({"status": "error", "message": f"Errore nell'eliminazione del documento {doc_id}"}), 500
        
        cleanup_backups()
        return jsonify({
            "status": "success", 
            "message": f"Documento {doc_id} e relative annotazioni eliminati con successo"
        })
    except Exception as e:
        annotation_logger.error(f"Errore nell'eliminazione del documento: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/update_document', methods=['POST'])
@login_required
def update_document():
    """
    API per aggiornare un documento esistente.
    """
    try:
        data = request.json
        doc_id = data.get('doc_id')
        new_content = data.get('content')
        new_title = data.get('title')
        
        if not doc_id:
            return jsonify({"status": "error", "message": "ID documento mancante"}), 400
        
        updates = {}
        if new_content is not None:
            updates['text'] = new_content
        if new_title is not None:
            updates['title'] = new_title
        
        success = db_manager.update_document(doc_id, updates)
        if not success:
            return jsonify({"status": "error", "message": f"Errore nell'aggiornamento del documento {doc_id}"}), 500
        
        return jsonify({
            "status": "success", 
            "message": "Documento aggiornato con successo"
        })
    except Exception as e:
        annotation_logger.error(f"Errore nell'aggiornamento del documento: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/documents', methods=['GET'])
@login_required
def api_get_documents():
    """API endpoint per ottenere la lista dei documenti con metadati."""
    # Filtra per stato se specificato
    status = request.args.get('status')
    
    # Admin può vedere tutti i documenti, altrimenti filtra per quelli assegnati
    user_id = None if g.user.get('role') == 'admin' else g.user['id']
    
    documents = db_manager.get_documents(status=status, assigned_to=user_id)
    all_annotations_map = db_manager.get_annotations()  # Fetch all once

    for doc in documents:
        doc_id = doc['id']
        doc_annotations = all_annotations_map.get(doc_id, [])
        doc['annotation_count'] = len(doc_annotations)
        word_count = doc.get('word_count', 0)
        
        # Calcolo progresso annotazioni
        if word_count > 0:
            annotated_chars = sum(ann['end'] - ann['start'] for ann in doc_annotations)
            avg_ann_len = 15  # Stima caratteri medi per annotazione
            estimated_annotated_chars = len(doc_annotations) * avg_ann_len
            progress = min(round((estimated_annotated_chars / (word_count * 5)) * 100), 100) if word_count else 0
            doc['annotated_percent'] = progress
        else:
            doc['annotated_percent'] = 100 if doc['annotation_count'] > 0 else 0
    
    return jsonify({"status": "success", "documents": documents})
      
@app.route('/api/bulk_delete_documents', methods=['POST'])
@login_required
def bulk_delete_documents():
    """
    API per eliminare più documenti in blocco.
    
    Richiede un array di ID di documenti nel body della richiesta.
    """
    try:
        data = request.json
        doc_ids = data.get('doc_ids', [])
        
        if not doc_ids:
            return jsonify({"status": "error", "message": "Nessun ID documento fornito"}), 400
        
        # Controllo di autorizzazione
        if session.get('user_role') != 'admin':
            # Per utenti non-admin, verifica che possano eliminare tutti i documenti richiesti
            # Ad esempio, controlla se sono i creatori o assegnatari
            for doc_id in doc_ids:
                document = db_manager.get_document(doc_id)
                if not document:
                    continue  # Salta i documenti che non esistono
                
                # Se l'utente non è né creatore né assegnatario del documento
                if (document.get('created_by') != session.get('user_id') and 
                    document.get('assigned_to') != session.get('user_id')):
                    return jsonify({
                        "status": "error", 
                        "message": "Non hai l'autorizzazione per eliminare alcuni di questi documenti"
                    }), 403
        
        deleted_count = 0
        errors = []
        
        # Elimina ogni documento
        for doc_id in doc_ids:
            try:
                success = db_manager.delete_document(doc_id)
                if success:
                    deleted_count += 1
                    # Log dell'attività
                    db_manager.log_user_activity(
                        user_id=session.get('user_id'),
                        action_type="delete_document",
                        document_id=doc_id
                    )
                else:
                    errors.append(f"Errore nell'eliminazione del documento {doc_id}")
            except Exception as e:
                errors.append(f"Errore per documento {doc_id}: {str(e)}")
        
        # Esegui pulizia dei backup dopo bulk delete
        cleanup_backups()
        
        # Prepara la risposta
        response = {
            "status": "success",
            "message": f"Eliminati {deleted_count} documenti su {len(doc_ids)} richiesti"
        }
        
        # Aggiungi informazioni sugli errori se presenti
        if errors:
            response["errors"] = errors
            response["message"] += f" con {len(errors)} errori"
            if deleted_count == 0:
                response["status"] = "error"
        
        return jsonify(response)
        
    except Exception as e:
        annotation_logger.error(f"Errore nell'eliminazione in blocco dei documenti: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@app.route('/api/export_annotations', methods=['GET'])
@login_required
def export_annotations():
    """
    API per esportare le annotazioni in vari formati.
    """
    try:
        format_type = request.args.get('format', 'json')
        
        if format_type == 'spacy':
            spacy_data = db_manager.export_spacy()
            output_file = os.path.join(DATA_DIR, 'spacy_annotations.json')
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(spacy_data, f, indent=2, ensure_ascii=False)
            if request.args.get('download', 'false').lower() == 'true':
                return send_file(output_file, as_attachment=True, download_name='spacy_annotations.json')
            return jsonify({"status": "success", "file": output_file, "data": spacy_data})
        else:
            annotations = db_manager.export_json()
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
@login_required
def recognize_entities():
    """
    API per il riconoscimento automatico delle entità.
    """
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
@login_required
def train_model():
    """
    API per esportare dati di addestramento per il modello.
    """
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

@app.route('/api/clear_annotations', methods=['POST'])
@login_required
def clear_annotations():
    """
    API per eliminare tutte le annotazioni di un documento o di un tipo specifico.
    """
    try:
        data = request.json
        doc_id = data.get('doc_id')
        entity_type = data.get('entity_type')  # Opzionale: per eliminare solo annotazioni di un tipo
        
        if not doc_id:
            return jsonify({"status": "error", "message": "ID documento mancante"}), 400
        
        success = db_manager.clear_annotations(doc_id, entity_type)
        if not success:
            return jsonify({"status": "error", "message": f"Errore nell'eliminazione delle annotazioni per {doc_id}"}), 500
        
        if entity_type:
            message = f"Annotazioni di tipo {entity_type} eliminate con successo"
        else:
            message = "Tutte le annotazioni eliminate con successo"
        
        cleanup_backups()
        return jsonify({
            "status": "success", 
            "message": message
        })
    except Exception as e:
        annotation_logger.error(f"Errore nell'eliminazione delle annotazioni: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/annotation_stats', methods=['GET'])
@login_required
def annotation_stats():
    """
    API per ottenere statistiche sulle annotazioni.
    """
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

# -----------------------------------------------------------------------------
# Endpoint API migliorati per la gestione dei tipi di entità
# -----------------------------------------------------------------------------
logger = logging.getLogger("ner_giuridico.entity_api")

def api_endpoint(func):
    """
    Decoratore per standardizzare la gestione degli errori negli endpoint API.
    
    Args:
        func: Funzione endpoint da decorare
        
    Returns:
        Funzione wrapper che gestisce gli errori
    """
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
    """Valida il nome di un'entità."""
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
    """Valida il nome visualizzato di un'entità."""
    if not display_name:
        raise ValueError("Il nome visualizzato dell'entità è obbligatorio")
    if len(display_name) > 100:
        raise ValueError("Il nome visualizzato dell'entità non può superare i 100 caratteri")

def validate_entity_category(category: str) -> None:
    """Valida la categoria di un'entità."""
    valid_categories = ['normative', 'jurisprudence', 'concepts', 'custom']
    if not category:
        raise ValueError("La categoria dell'entità è obbligatoria")
    if category not in valid_categories:
        raise ValueError(f"La categoria dell'entità deve essere una tra: {', '.join(valid_categories)}")

def validate_entity_color(color: str) -> None:
    """Valida il colore di un'entità."""
    if not color:
        raise ValueError("Il colore dell'entità è obbligatorio")
    if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
        raise ValueError("Il colore dell'entità deve essere in formato esadecimale (es. #FF0000)")

def validate_metadata_schema(metadata_schema: Dict[str, str]) -> None:
    """Valida lo schema dei metadati di un'entità."""
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
    """Valida i pattern regex di un'entità."""
    if not isinstance(patterns, list):
        raise ValueError("I pattern devono essere una lista di stringhe")
    for pattern in patterns:
        if not isinstance(pattern, str):
            raise ValueError("Ogni pattern deve essere una stringa")
        try:
            re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Pattern regex non valido: '{pattern}' - {str(e)}")


@app.route('/api/entity_types', methods=['GET'])
@login_required
def get_entity_types():
    """API per ottenere tutti i tipi di entità."""
    try:
        entity_manager = get_entity_manager()
        entities = entity_manager.get_all_entities()
        
        category = request.args.get('category')
        if category:
            entities = [e for e in entities if e.category == category]
        
        # Converti in formato per il frontend
        entities_data = [
            {
                "id": e.id,
                "name": e.name,
                "display_name": e.display_name,
                "category": e.category,
                "color": e.color,
                "description": e.description,
                "metadata_schema": e.metadata_schema,
                "patterns": e.patterns,
                "system": e.system
            }
            for e in entities
        ]
        
        return jsonify({
            "status": "success",
            "entity_types": entities_data
        })
    except Exception as e:
        logger.error(f"Errore nel recupero dei tipi di entità: {e}")
        return jsonify({
            "status": "error",
            "message": f"Errore nel recupero dei tipi di entità: {str(e)}"
        }), 500

@app.route('/api/entity_types/<entity_id>', methods=['GET'])
@login_required
def get_entity_type(entity_id):
    """API per ottenere un tipo di entità specifico."""
    try:
        entity_manager = get_entity_manager()
        entity = entity_manager.get_entity(entity_id)
        
        if not entity:
            return jsonify({
                "status": "error",
                "message": f"Tipo di entità con ID {entity_id} non trovato"
            }), 404
        
        entity_data = {
            "id": entity.id,
            "name": entity.name,
            "display_name": entity.display_name,
            "category": entity.category,
            "color": entity.color,
            "description": entity.description,
            "metadata_schema": entity.metadata_schema,
            "patterns": entity.patterns,
            "system": entity.system
        }
        
        return jsonify({
            "status": "success",
            "entity_type": entity_data
        })
    except Exception as e:
        logger.error(f"Errore nel recupero del tipo di entità: {e}")
        return jsonify({
            "status": "error",
            "message": f"Errore nel recupero del tipo di entità: {str(e)}"
        }), 500

@app.route('/api/entity_types', methods=['POST'])
@login_required
def create_entity_type():
    """API per creare un nuovo tipo di entità."""
    try:
        data = request.json
        
        # Validazione dei dati
        required_fields = ['name', 'display_name', 'category', 'color']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    "status": "error",
                    "message": f"Campo obbligatorio mancante: {field}"
                }), 400
        
        # Verifica formato del nome (maiuscolo senza spazi)
        if not data['name'].isupper() or ' ' in data['name']:
            return jsonify({
                "status": "error",
                "message": "Il nome deve essere in maiuscolo e senza spazi"
            }), 400
        
        # Crea l'entità
        entity = EntityType(
            id=str(uuid.uuid4()),
            name=data['name'],
            display_name=data['display_name'],
            category=data['category'],
            color=data['color'],
            description=data.get('description', ''),
            metadata_schema=data.get('metadata_schema', {}),
            patterns=data.get('patterns', []),
            system=False
        )
        
        # Salva l'entità
        entity_manager = get_entity_manager()
        success = entity_manager.add_entity(entity)
        
        if not success:
            return jsonify({
                "status": "error",
                "message": f"Impossibile creare il tipo di entità '{data['name']}'"
            }), 500
        
        return jsonify({
            "status": "success",
            "message": f"Tipo di entità '{data['name']}' creato con successo",
            "entity_type": {
                "id": entity.id,
                "name": entity.name,
                "display_name": entity.display_name,
                "category": entity.category,
                "color": entity.color,
                "description": entity.description,
                "metadata_schema": entity.metadata_schema,
                "patterns": entity.patterns,
                "system": entity.system
            }
        })
    except Exception as e:
        logger.error(f"Errore nella creazione del tipo di entità: {e}")
        return jsonify({
            "status": "error",
            "message": f"Errore nella creazione del tipo di entità: {str(e)}"
        }), 500

@app.route('/api/entity_types/<entity_id>', methods=['PUT'])
@login_required
def update_entity_type(entity_id):
    """API per aggiornare un tipo di entità esistente."""
    try:
        data = request.json
        entity_manager = get_entity_manager()
        
        # Verifica che l'entità esista
        entity = entity_manager.get_entity(entity_id)
        if not entity:
            return jsonify({
                "status": "error",
                "message": f"Tipo di entità con ID {entity_id} non trovato"
            }), 404
        
        # Non permettere la modifica dell'ID o del flag system
        # (Il name si potrebbe permettere, ma potrebbe causare problemi di riferimento)
        if 'id' in data:
            data.pop('id')
        
        if 'system' in data:
            data.pop('system')
        
        # Aggiorna i campi
        for key, value in data.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        
        # Salva le modifiche
        success = entity_manager.update_entity(entity)
        
        if not success:
            return jsonify({
                "status": "error",
                "message": f"Impossibile aggiornare il tipo di entità '{entity.name}'"
            }), 500
        
        return jsonify({
            "status": "success",
            "message": f"Tipo di entità '{entity.name}' aggiornato con successo",
            "entity_type": {
                "id": entity.id,
                "name": entity.name,
                "display_name": entity.display_name,
                "category": entity.category,
                "color": entity.color,
                "description": entity.description,
                "metadata_schema": entity.metadata_schema,
                "patterns": entity.patterns,
                "system": entity.system
            }
        })
    except Exception as e:
        logger.error(f"Errore nell'aggiornamento del tipo di entità: {e}")
        return jsonify({
            "status": "error",
            "message": f"Errore nell'aggiornamento del tipo di entità: {str(e)}"
        }), 500

@app.route('/api/entity_types/<entity_id>', methods=['DELETE'])
@login_required
def delete_entity_type(entity_id):
    """API per eliminare un tipo di entità."""
    try:
        entity_manager = get_entity_manager()
        
        # Verifica che l'entità esista
        entity = entity_manager.get_entity(entity_id)
        if not entity:
            return jsonify({
                "status": "error",
                "message": f"Tipo di entità con ID {entity_id} non trovato"
            }), 404
        
        # Non permettere l'eliminazione di entità di sistema
        if entity.system:
            return jsonify({
                "status": "error",
                "message": f"Impossibile eliminare l'entità di sistema '{entity.name}'"
            }), 403
        
        # Verifica che l'entità non sia in uso
        # Questa funzione dovrà essere implementata in base alle tue esigenze
        """  if is_entity_in_use(entity_id):
                return jsonify({
                    "status": "error",
                    "message": f"Impossibile eliminare l'entità '{entity.name}' perché è in uso"
                }), 409
            """
        # Elimina l'entità
        success = entity_manager.remove_entity(entity_id)
        
        if not success:
            return jsonify({
                "status": "error",
                "message": f"Impossibile eliminare il tipo di entità '{entity.name}'"
            }), 500
        
        return jsonify({
            "status": "success",
            "message": f"Tipo di entità '{entity.name}' eliminato con successo"
        })
    except Exception as e:
        logger.error(f"Errore nell'eliminazione del tipo di entità: {e}")
        return jsonify({
            "status": "error",
            "message": f"Errore nell'eliminazione del tipo di entità: {str(e)}"
        }), 500

@app.route('/api/entity_categories', methods=['GET'])
@login_required
def get_entity_categories():
    """API per ottenere tutte le categorie di entità."""
    try:
        entity_manager = get_entity_manager()
        categories = entity_manager.get_categories()
        
        return jsonify({
            "status": "success",
            "categories": categories
        })
    except Exception as e:
        logger.error(f"Errore nel recupero delle categorie: {e}")
        return jsonify({
            "status": "error",
            "message": f"Errore nel recupero delle categorie: {str(e)}"
        }), 500

@app.route('/api/test_pattern', methods=['POST'])
@login_required
def test_pattern():
    """API per testare un pattern regex su un testo di esempio."""
    try:
        data = request.json
        pattern = data.get('pattern')
        text = data.get('text')
        
        if not pattern or not text:
            return jsonify({
                "status": "error",
                "message": "Pattern e testo sono richiesti"
            }), 400
        
        # Testa il pattern
        import re
        try:
            regex = re.compile(pattern)
            matches = []
            
            for match in regex.finditer(text):
                matches.append({
                    "text": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                    "groups": [match.group(i) for i in range(1, len(match.groups()) + 1)]
                })
            
            return jsonify({
                "status": "success",
                "matches_count": len(matches),
                "matches": matches
            })
        except re.error as e:
            return jsonify({
                "status": "error",
                "message": f"Pattern regex non valido: {str(e)}"
            }), 400
        
    except Exception as e:
        logger.error(f"Errore nel test del pattern: {e}")
        return jsonify({
            "status": "error",
            "message": f"Errore nel test del pattern: {str(e)}"
        }), 500
  
def check_entity_type_in_use(entity_type_name: str) -> bool:
    """
    Verifica se un tipo di entità è in uso in annotazioni esistenti.
    
    Args:
        entity_type_name: Nome del tipo di entità da verificare
        
    Returns:
        True se l'entità è in uso, False altrimenti
    """
    try:
        DATA_DIR_PATH = Path(__file__).resolve().parent / 'data'
        annotations_file = os.path.join(DATA_DIR_PATH, 'annotations.json')
        
        # Verifica se il file delle annotazioni esiste
        if not os.path.exists(annotations_file):
            logger.debug(f"File delle annotazioni non trovato: {annotations_file}")
            return False
        
        # Carica le annotazioni
        with open(annotations_file, 'r', encoding='utf-8') as f:
            annotations = json.load(f)
        
        # Cerca l'entità nelle annotazioni
        for doc_id, doc_annotations in annotations.items():
            for annotation in doc_annotations:
                if annotation.get('type') == entity_type_name:
                    logger.debug(f"Entità {entity_type_name} in uso nell'annotazione {annotation.get('id')} del documento {doc_id}")
                    return True
        
        logger.debug(f"Entità {entity_type_name} non in uso in nessuna annotazione")
        return False
    except Exception as e:
        logger.error(f"Errore nella verifica dell'uso del tipo di entità '{entity_type_name}': {e}")
        logger.exception(e)
        # In caso di errore, è più sicuro assumere che l'entità sia in uso
        return True
    
@api_endpoint
def test_entity_pattern():
    """
    Testa un pattern regex su un testo di esempio.
    """
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
    """
    Registra tutti gli endpoint API per la gestione dei tipi di entità.
    
    Args:
        app: Istanza dell'applicazione Flask
    """
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