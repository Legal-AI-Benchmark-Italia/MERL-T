#!/usr/bin/env python3
"""
Interfaccia web per l'annotazione di entità giuridiche e la gestione dei tipi di entità.
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
from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, session, flash, g, abort
from werkzeug.utils import secure_filename
import configparser
from pathlib import Path
from .db_manager import AnnotationDBManager

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

# Configurazione dell'app Flask
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'chiave_segreta_predefinita')  # In produzione usa una chiave sicura
app.permanent_session_lifetime = datetime.timedelta(days=1)  # Sessione valida per 1 giorno

# Directory per i dati e i backup
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DATA_DIR, exist_ok=True)
BACKUP_DIR = os.path.join(DATA_DIR, 'backup')
os.makedirs(BACKUP_DIR, exist_ok=True)

# --- Funzioni di supporto per l'autenticazione ---

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
            flash('È necessario accedere per visualizzare questa pagina.', 'warning')
            return redirect(url_for('login'))
        
        if session.get('user_role') != 'admin':
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
    else:
        g.user = db_manager.get_user_by_id(user_id)
        # Rimuovi la password per sicurezza
        if g.user and 'password' in g.user:
            g.user.pop('password', None)

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

@app.route('/api/documents')
@login_required
def api_get_documents():
    """
    API per ottenere la lista dei documenti.
    """
    documents = load_documents()
    
    # Per ogni documento, aggiungi il conteggio delle annotazioni
    all_annotations = load_annotations()
    for doc in documents:
        doc_id = doc['id']
        doc_annotations = all_annotations.get(doc_id, [])
        doc['annotation_count'] = len(doc_annotations)
        
        # Calcola progresso (esempio semplice: percentuale di parole annotate)
        try:
            word_count = doc.get('word_count', 0)
            if word_count > 0:
                # Assumiamo che ogni annotazione copra in media 2 parole
                annotated_words = min(len(doc_annotations) * 2, word_count)
                doc['annotated_percent'] = round((annotated_words / word_count) * 100)
            else:
                doc['annotated_percent'] = 0
        except Exception as e:
            annotation_logger.error(f"Errore nel calcolo del progresso: {e}")
            doc['annotated_percent'] = 0
    
    return jsonify({"status": "success", "documents": documents})

@app.route('/assignments')
@login_required
def assignments():
    """
    Visualizza i documenti assegnati all'utente corrente.
    """
    user_id = session.get('user_id')
    docs = db_manager.get_user_assignments(user_id)
    return render_template('assignments.html', documents=docs)

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
    document = db_manager.get_document(doc_id)
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

# --- Rotte per l'autenticazione ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Gestisce il login degli utenti.
    """
    # Utente già autenticato
    if session.get('user_id'):
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        error = None
        
        if not username:
            error = 'Username richiesto.'
        elif not password:
            error = 'Password richiesta.'
        
        if error is None:
            user = db_manager.verify_user(username, password)
            
            if user:
                # Configura sessione
                session.clear()
                session.permanent = remember
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['user_role'] = user['role']
                
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

annotation_logger.info(f"Utilizzo database in: {db_path}")
annotation_logger.info(f"Directory backup: {backup_dir}")

db_manager = AnnotationDBManager(db_path=db_path, backup_dir=backup_dir)

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
    return render_template('annotate.html', document=document, annotations=doc_annotations, entity_types=ENTITY_TYPES)

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
    API per caricare un nuovo documento.
    """
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
            "word_count": len(file_content.split()),
            "created_by": session.get('user_id')  # Aggiunto l'utente creatore
        }
        
        success = db_manager.save_document(document, session.get('user_id'))
        if not success:
            return jsonify({"status": "error", "message": "Errore nel salvataggio del documento"}), 500
        
        return jsonify({"status": "success", "message": "Documento caricato con successo", "document": document})
    except UnicodeDecodeError:
        return jsonify({"status": "error", "message": "Impossibile decodificare il file. Assicurati che sia un file di testo valido in formato UTF-8."}), 400
    except Exception as e:
        annotation_logger.error(f"Errore nell'upload del documento: {e}")
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
    """
    Ottiene un tipo di entità specifico.
    
    Args:
        name: Nome del tipo di entità
    """
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
    return jsonify({"status": "success", "entity_types": result})

@api_endpoint
def create_entity_type():
    """
    Crea un nuovo tipo di entità.
    """
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
    """
    Aggiorna un tipo di entità esistente.
    
    Args:
        name: Nome del tipo di entità da aggiornare
    """
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
    """
    Elimina un tipo di entità.
    
    Args:
        name: Nome del tipo di entità da eliminare.
    
    Returns:
        Risultato dell'eliminazione.
    """
    logger.info(f"Ricevuta richiesta di eliminazione per l'entità: {name}")
    
    try:
        from ner_giuridico.entities.entity_manager import get_entity_manager
        entity_manager = get_entity_manager()
        
        # Verifica che l'entità esista
        if not entity_manager.entity_type_exists(name):
            logger.warning(f"Tentativo di eliminare l'entità inesistente: {name}")
            return jsonify({"status": "error", "message": f"Tipo di entità '{name}' non trovato"}), 404
        
        # Ottieni informazioni sull'entità
        entity_type = entity_manager.get_entity_type(name)
        logger.debug(f"Informazioni entità: {entity_type}")
        
        # Verifica che l'entità non sia predefinita
        if entity_type.get("category") != "custom":
            logger.warning(f"Tentativo di eliminare l'entità predefinita: {name}")
            return jsonify({
                "status": "error", 
                "message": f"Non è possibile eliminare il tipo di entità predefinito '{name}'",
                "error_type": "ProtectedEntityError"
            }), 403
        
        # Verifica che l'entità non sia in uso
        has_annotations = check_entity_type_in_use(name)
        if has_annotations:
            logger.warning(f"Impossibile eliminare l'entità {name} perché è in uso in alcune annotazioni")
            return jsonify({
                "status": "error", 
                "message": f"Impossibile eliminare il tipo di entità '{name}' perché è in uso in alcune annotazioni",
                "error_type": "EntityInUseError"
            }), 409  # Conflict
        
        # Elimina l'entità
        success = entity_manager.remove_entity_type(name)
        
        if not success:
            logger.error(f"Errore interno durante l'eliminazione dell'entità {name}")
            return jsonify({
                "status": "error", 
                "message": f"Impossibile eliminare il tipo di entità '{name}' a causa di un errore interno"
            }), 500
        
        # Salva le modifiche nel database
        try:
            entity_manager.save_entities_to_database()
            logger.info(f"Entità {name} eliminata con successo e database aggiornato")
        except Exception as e:
            logger.warning(f"Entità {name} eliminata ma errore nel salvataggio del database: {e}")
        
        return jsonify({
            "status": "success", 
            "message": f"Tipo di entità '{name}' eliminato con successo"
        })
    except Exception as e:
        logger.error(f"Errore non gestito nell'eliminazione dell'entità {name}: {e}")
        logger.exception(e)
        return jsonify({
            "status": "error", 
            "message": f"Errore durante l'eliminazione: {str(e)}",
            "error_type": type(e).__name__
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