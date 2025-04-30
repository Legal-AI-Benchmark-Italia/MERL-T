#!/usr/bin/env python3
"""
db_manager.py
Sistema di persistenza delle annotazioni basato su SQLite.
"""

import os
import sqlite3
import json
import logging
import datetime
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

# Setup del logger
logger = logging.getLogger("db_manager")
logger.setLevel(logging.INFO)

# Verifica se il logger ha già degli handler configurati
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

class DBContextManager:
    def __init__(self, db_path):
        self.db_path = db_path
    
    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        return self.conn, self.cursor
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if (exc_type is None):
            self.conn.commit()
        else:
            self.conn.rollback()
        self.cursor.close()
        self.conn.close()

class AnnotationDBManager:
    """
    Gestore della persistenza delle annotazioni tramite database SQLite.
    """
    
    def __init__(self, db_path: str, backup_dir: str):
        """
        Inizializza il gestore del database.
        
        Args:
            db_path: Percorso del file database SQLite.
            backup_dir: Directory per i backup.
        """
        self.logger = logging.getLogger("db_manager")
        
        # Verifica che i percorsi siano forniti
        if not db_path:
            raise ValueError("Il percorso del database (db_path) è obbligatorio.")
        if not backup_dir:
            raise ValueError("La directory di backup (backup_dir) è obbligatoria.")

        self.db_path = db_path
        self.backup_dir = backup_dir
        
        # Crea le directory necessarie se non esistono
        db_dir = os.path.dirname(self.db_path)
        os.makedirs(db_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        self.logger.info(f"Database inizializzato: {self.db_path}")
        self.logger.info(f"Directory backup: {self.backup_dir}")
        
        # Inizializza il database
        self._init_db()
    
    def _get_db(self) -> DBContextManager:
        """
        Ottiene un context manager per la connessione al database.
        
        Returns:
            DBContextManager instance
        """
        return DBContextManager(self.db_path)
    
    def _init_db(self) -> None:
        """
        Inizializza lo schema del database se necessario.
        """
        logger = logging.getLogger("db_manager")  # Fallback logger if self.logger is not available
        log = getattr(self, 'logger', logger)
        
        with self._get_db() as (conn, cursor):
            # Tabella utenti
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                full_name TEXT,
                role TEXT DEFAULT 'annotator',
                email TEXT,
                active INTEGER DEFAULT 1,
                date_created TEXT,
                date_last_login TEXT
            )
            ''')
            
            # Tabella documenti (now includes metadata column)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                word_count INTEGER,
                date_created TEXT,
                date_modified TEXT,
                created_by TEXT,
                assigned_to TEXT,
                metadata TEXT,
                FOREIGN KEY (created_by) REFERENCES users(id),
                FOREIGN KEY (assigned_to) REFERENCES users(id)
            )
            ''')
            
            # Tabella annotazioni (versione aggiornata con created_by)
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS annotations (
                id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL,
                start INTEGER NOT NULL,
                end INTEGER NOT NULL,
                text TEXT NOT NULL,
                type TEXT NOT NULL,
                metadata TEXT,
                date_created TEXT,
                date_modified TEXT,
                created_by TEXT,
                FOREIGN KEY (doc_id) REFERENCES documents(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            )
            ''')
            
            # Tabella per tracciare le attività degli utenti
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_activity (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                document_id TEXT,
                annotation_id TEXT,
                timestamp TEXT NOT NULL,
                details TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (document_id) REFERENCES documents(id),
                FOREIGN KEY (annotation_id) REFERENCES annotations(id)
            )
            ''')
            
            # Crea indici per migliorare le prestazioni
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_annotations_doc_id ON annotations(doc_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_annotations_created_by ON annotations(created_by)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_annotations_type ON annotations(type)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_user_id ON user_activity(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON user_activity(timestamp)")
            except Exception as e:
                log.warning(f"Impossibile creare alcuni indici: {e}")
            
            conn.commit()
            log.debug("Schema del database inizializzato")
       
    #--- Operazioni di gestione degli utenti ----
    def create_user(self, user_data: dict) -> dict:
        """
        Crea un nuovo utente nel database.
        
        Args:
            user_data: Dizionario con i dati dell'utente
                
        Returns:
            Utente creato con ID generato
        """
        try:
            now = datetime.datetime.now().isoformat()
            
            # Genera un ID se non presente
            if 'id' not in user_data or not user_data['id']:
                user_data['id'] = f"user_{int(datetime.datetime.now().timestamp())}"
            
            # Aggiungi data creazione
            user_data['date_created'] = now
            
            # Hash della password (NOTA: in un ambiente di produzione usare bcrypt o simili)
            # Questa è una implementazione semplificata
            import hashlib
            password = user_data.get('password', '')
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            user_data['password'] = hashed_password
            
            with self._get_db() as (conn, cursor):
                cursor.execute(
                    """
                    INSERT INTO users 
                    (id, username, password, full_name, role, email, active, date_created)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_data['id'],
                        user_data['username'],
                        user_data['password'],
                        user_data.get('full_name', ''),
                        user_data.get('role', 'annotator'),
                        user_data.get('email', ''),
                        user_data.get('active', 1),
                        user_data['date_created']
                    )
                )
                conn.commit()
                logger.debug(f"Utente creato: {user_data['username']}")
                
                # Non restituire la password
                user_data.pop('password', None)
                return user_data
        except Exception as e:
            logger.error(f"Errore nella creazione dell'utente: {e}")
            return None

    def verify_user(self, username: str, password: str) -> dict:
        """
        Verifica le credenziali di un utente.
        
        Args:
            username: Nome utente
            password: Password in chiaro
                
        Returns:
            Dizionario con i dati dell'utente (senza password) o None se autenticazione fallita
        """
        try:
            self.logger.debug(f"Attempting to verify user: {username}")
            
            if not username or not password:
                self.logger.warning("Empty username or password provided")
                return None
            
            # Hash della password per confronto
            import hashlib
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            user = self.get_user_by_username(username)
            if not user:
                self.logger.warning(f"User not found: {username}")
                return None
            
            # Verifica se l'utente è attivo
            if not user.get('active', 1):
                self.logger.warning(f"User account is inactive: {username}")
                return None
            
            if user.get('password') != hashed_password:
                self.logger.warning(f"Invalid password for user: {username}")
                return None
            
            # Aggiorna last login
            now = datetime.datetime.now().isoformat()
            try:
                with self._get_db() as (conn, cursor):
                    cursor.execute(
                        "UPDATE users SET date_last_login = ? WHERE id = ?",
                        (now, user['id'])
                    )
                    conn.commit()
            except Exception as e:
                self.logger.error(f"Error updating last login time: {e}")
                # Non bloccare il login se l'aggiornamento fallisce
            
            # Non restituire la password
            user_copy = dict(user)
            user_copy.pop('password', None)
            self.logger.info(f"User verified successfully: {username}")
            return user_copy
        except Exception as e:
            self.logger.error(f"Unexpected error in verify_user: {e}")
            self.logger.exception(e)
            return None

    def get_all_users(self) -> list:
        """
        Ottiene tutti gli utenti.
        
        Returns:
            Lista di utenti (senza password)
        """
        try:
            with self._get_db() as (conn, cursor):
                cursor.execute("SELECT id, username, full_name, role, email, active, date_created, date_last_login FROM users")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Errore nel recupero degli utenti: {e}")
            return []

    def update_user(self, user_id: str, updates: dict) -> bool:
        """
        Aggiorna un utente esistente.
        
        Args:
            user_id: ID dell'utente
            updates: Dizionario con i campi da aggiornare
                
        Returns:
            True se aggiornato con successo, False altrimenti
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False
            
            # Se c'è una password da aggiornare, hashala
            if 'password' in updates and updates['password']:
                import hashlib
                updates['password'] = hashlib.sha256(updates['password'].encode()).hexdigest()
            
            # Costruisci query dinamica in base ai campi da aggiornare
            set_clauses = []
            values = []
            
            for key, value in updates.items():
                if key in ['username', 'password', 'full_name', 'role', 'email', 'active']:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            if not set_clauses:
                return False  # Nessun campo valido da aggiornare
            
            values.append(user_id)  # Per la clausola WHERE
            
            with self._get_db() as (conn, cursor):
                cursor.execute(
                    f"UPDATE users SET {', '.join(set_clauses)} WHERE id = ?",
                    tuple(values)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Errore nell'aggiornamento dell'utente: {e}")
            return False

    def get_user_by_id(self, user_id: str) -> dict:
        """
        Ottiene un utente dal database tramite ID.
        
        Args:
            user_id: ID dell'utente
                
        Returns:
            Dizionario con i dati dell'utente o None se non trovato
        """
        try:
            self.logger.debug(f"Getting user by ID: {user_id}")
            with self._get_db() as (conn, cursor):
                cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
                row = cursor.fetchone()
                if not row:
                    self.logger.debug(f"User with ID '{user_id}' not found")
                    return None
                self.logger.debug(f"User with ID '{user_id}' found")
                return dict(row)
        except Exception as e:
            self.logger.error(f"Error retrieving user by ID: {e}")
            self.logger.exception(e)
            return None
        
    def log_user_activity(self, user_id: str, action_type: str, document_id: str = None, 
                        annotation_id: str = None, details: str = None) -> bool:
        """
        Registra un'attività utente nel log.
        
        Args:
            user_id: ID dell'utente
            action_type: Tipo di azione (login, create_annotation, delete_annotation, ecc.)
            document_id: ID del documento coinvolto (opzionale)
            annotation_id: ID dell'annotazione coinvolta (opzionale)
            details: Dettagli aggiuntivi (opzionale)
                
        Returns:
            True se registrato con successo, False altrimenti
        """
        try:
            now = datetime.datetime.now().isoformat()
            activity_id = f"act_{int(datetime.datetime.now().timestamp())}"
            
            with self._get_db() as (conn, cursor):
                cursor.execute(
                    """
                    INSERT INTO user_activity 
                    (id, user_id, action_type, document_id, annotation_id, timestamp, details)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        activity_id,
                        user_id,
                        action_type,
                        document_id,
                        annotation_id,
                        now,
                        details
                    )
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Errore nella registrazione dell'attività: {e}")
            return False
    
    def get_user_stats(self, user_id: str = None, days: int = 30) -> dict:
        """
        Ottiene statistiche sull'attività di un utente.
        
        Args:
            user_id: ID dell'utente (opzionale, se None restituisce per tutti gli utenti)
            days: Numero di giorni precedenti da considerare
                
        Returns:
            Dizionario con statistiche
        """
        try:
            with self._get_db() as (conn, cursor):
                # Data limite per il periodo
                date_limit = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
                
                stats = {}
                
                # Query base con il filtro della data
                base_query = f"WHERE timestamp > '{date_limit}'"
                
                # Aggiungi filtro utente se specificato
                if user_id:
                    base_query += f" AND user_id = '{user_id}'"
                
                # Conteggio totale annotazioni
                try:
                    # Check if created_by column exists in annotations table
                    cursor.execute("PRAGMA table_info(annotations)")
                    columns = cursor.fetchall()
                    created_by_exists = any(col[1] == 'created_by' for col in columns)
                    
                    if created_by_exists:
                        query = f"""
                            SELECT COUNT(*) FROM annotations
                            WHERE date_created > '{date_limit}'
                            {"AND created_by = ?" if user_id else ""}
                        """
                        cursor.execute(query, (user_id,) if user_id else ())
                    else:
                        # Fallback if created_by column doesn't exist
                        query = f"""
                            SELECT COUNT(*) FROM annotations
                            WHERE date_created > '{date_limit}'
                        """
                        cursor.execute(query)
                        
                    stats['total_annotations'] = cursor.fetchone()[0]
                except Exception as e:
                    self.logger.error(f"Errore nel conteggio delle annotazioni: {e}")
                    stats['total_annotations'] = 0
                
                # Conteggio per tipo di entità
                try:
                    if created_by_exists and user_id:
                        query = f"""
                            SELECT type, COUNT(*) as count FROM annotations
                            WHERE date_created > '{date_limit}'
                            AND created_by = ?
                            GROUP BY type
                        """
                        cursor.execute(query, (user_id,))
                    else:
                        query = f"""
                            SELECT type, COUNT(*) as count FROM annotations
                            WHERE date_created > '{date_limit}'
                            GROUP BY type
                        """
                        cursor.execute(query)
                        
                    stats['annotations_by_type'] = {row['type']: row['count'] for row in cursor.fetchall()}
                except Exception as e:
                    self.logger.error(f"Errore nel conteggio dei tipi di entità: {e}")
                    stats['annotations_by_type'] = {}
                
                # Attività per giorno
                try:
                    cursor.execute(f"""
                        SELECT substr(timestamp, 1, 10) as day, COUNT(*) as count
                        FROM user_activity
                        {base_query}
                        GROUP BY day
                        ORDER BY day
                    """)
                    stats['activity_by_day'] = {row['day']: row['count'] for row in cursor.fetchall()}
                except Exception as e:
                    self.logger.error(f"Errore nel recupero dell'attività per giorno: {e}")
                    stats['activity_by_day'] = {}
                
                # Conteggio attività per tipo di azione
                try:
                    cursor.execute(f"""
                        SELECT action_type, COUNT(*) as count
                        FROM user_activity
                        {base_query}
                        GROUP BY action_type
                    """)
                    stats['actions_by_type'] = {row['action_type']: row['count'] for row in cursor.fetchall()}
                except Exception as e:
                    self.logger.error(f"Errore nel conteggio dei tipi di azione: {e}")
                    stats['actions_by_type'] = {}
                
                # Documenti modificati
                try:
                    cursor.execute(f"""
                        SELECT COUNT(DISTINCT document_id) as count
                        FROM user_activity
                        WHERE document_id IS NOT NULL
                        AND timestamp > '{date_limit}'
                        {"AND user_id = ?" if user_id else ""}
                    """, (user_id,) if user_id else ())
                    stats['documents_modified'] = cursor.fetchone()[0]
                except Exception as e:
                    self.logger.error(f"Errore nel conteggio dei documenti modificati: {e}")
                    stats['documents_modified'] = 0
                
                # Se richiedono statistiche globali (senza user_id specifico)
                if not user_id:
                    try:
                        # Statistiche per utente
                        # Check if annotations table has created_by column
                        if created_by_exists:
                            cursor.execute(f"""
                                SELECT u.id, u.username, u.full_name, COUNT(a.id) as annotations_count
                                FROM users u
                                LEFT JOIN annotations a ON u.id = a.created_by AND a.date_created > '{date_limit}'
                                GROUP BY u.id
                                ORDER BY annotations_count DESC
                            """)
                        else:
                            # Fallback if created_by column doesn't exist in annotations
                            cursor.execute(f"""
                                SELECT u.id, u.username, u.full_name, 0 as annotations_count
                                FROM users u
                                GROUP BY u.id
                                ORDER BY u.username
                            """)
                        
                        stats['users'] = [dict(row) for row in cursor.fetchall()]
                    except Exception as e:
                        self.logger.error(f"Errore nel recupero delle statistiche per utente: {e}")
                        stats['users'] = []
                
                return stats
        except Exception as e:
            logger.error(f"Errore nel recupero delle statistiche: {e}")
            return {}

    def get_user_assignments(self, user_id: str) -> list:
        """
        Ottiene i documenti assegnati a un utente.
        
        Args:
            user_id: ID dell'utente
                
        Returns:
            Lista di documenti assegnati
        """
        try:
            with self._get_db() as (conn, cursor):
                cursor.execute("""
                    SELECT * FROM documents 
                    WHERE assigned_to = ? 
                    ORDER BY date_modified DESC
                """, (user_id,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Errore nel recupero dei documenti assegnati: {e}")
            return []

    def assign_document(self, doc_id: str, user_id: str, assigner_id: str) -> bool:
        """
        Assegna un documento a un utente.
        
        Args:
            doc_id: ID del documento
            user_id: ID dell'utente a cui assegnare
            assigner_id: ID dell'utente che effettua l'assegnazione
                
        Returns:
            True se assegnato con successo, False altrimenti
        """
        try:
            with self._get_db() as (conn, cursor):
                cursor.execute(
                    "UPDATE documents SET assigned_to = ? WHERE id = ?",
                    (user_id, doc_id)
                )
                conn.commit()
                
                # Log activity
                self.log_user_activity(
                    user_id=assigner_id,
                    action_type="assign_document",
                    document_id=doc_id,
                    details=f"Documento assegnato all'utente {user_id}"
                )
                
                return True
        except Exception as e:
            logger.error(f"Errore nell'assegnazione del documento: {e}")
            return False

    def get_user_by_username(self, username: str) -> dict:
        """
        Ottiene un utente dal database tramite username.
        
        Args:
            username: Nome utente
                
        Returns:
            Dizionario con i dati dell'utente o None se non trovato
        """
        try:
            self.logger.debug(f"Getting user by username: {username}")
            with self._get_db() as (conn, cursor):
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                if not row:
                    self.logger.debug(f"User '{username}' not found")
                    return None
                self.logger.debug(f"User '{username}' found")
                return dict(row)
        except Exception as e:
            self.logger.error(f"Error retrieving user by username: {e}")
            self.logger.exception(e)
            return None
    
    # ---- Operazioni di backup ----
    
    def create_backup(self) -> str:
            """
            Crea un backup del database.
            
            Returns:
                Percorso del file di backup
            """
            if not os.path.exists(self.db_path):
                logger.warning("Impossibile creare backup: database non esistente")
                return None
            
            timestamp = int(datetime.datetime.now().timestamp())
            backup_file = os.path.join(self.backup_dir, f"annotations_backup_{timestamp}.db")
            
            try:
                import shutil
                shutil.copy2(self.db_path, backup_file)
                logger.info(f"Backup creato: {backup_file}")
                return backup_file
            except Exception as e:
                logger.error(f"Errore nella creazione del backup: {e}")
                return None
    
    def cleanup_backups(self, max_backups: int = 10) -> None:
            """
            Pulisce i vecchi backup mantenendo solo i più recenti.
            
            Args:
                max_backups: Numero massimo di backup da mantenere
            """
            try:
                backup_files = []
                for filename in os.listdir(self.backup_dir):
                    if filename.startswith('annotations_backup_') and filename.endswith('.db'):
                        filepath = os.path.join(self.backup_dir, filename)
                        backup_files.append((filepath, os.path.getmtime(filepath)))
                
                backup_files.sort(key=lambda x: x[1], reverse=True)
                
                if len(backup_files) > max_backups:
                    for filepath, _ in backup_files[max_backups:]:
                        os.remove(filepath)
                        logger.debug(f"Backup rimosso: {filepath}")
            except Exception as e:
                logger.error(f"Errore nella pulizia dei backup: {e}")
    
    # ---- Operazioni sui documenti ----
    
    def get_documents(self, status=None, assigned_to=None) -> List[Dict[str, Any]]:
        """
        Ottiene tutti i documenti dal database con filtri opzionali.
        
        Args:
            status: Filtra per stato (pending, completed, skipped)
            assigned_to: Filtra per utente assegnato
        
        Returns:
            Lista di documenti
        """
        try:
            with self._get_db() as (conn, cursor):
                query = "SELECT * FROM documents"
                params = []
                
                # Costruisci la query dinamicamente in base ai filtri
                conditions = []
                if status:
                    conditions.append("status = ?")
                    params.append(status)
                if assigned_to:
                    conditions.append("assigned_to = ?")
                    params.append(assigned_to)
                    
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                    
                query += " ORDER BY date_created DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                documents = []
                for row in rows:
                    doc = dict(row)
                    
                    # Convert metadata from JSON to dictionary if present
                    if 'metadata' in doc and doc['metadata']:
                        try:
                            doc['metadata'] = json.loads(doc['metadata'])
                        except json.JSONDecodeError:
                            self.logger.warning(f"Error decoding metadata for document {doc['id']}")
                            doc['metadata'] = {}
                    else:
                        doc['metadata'] = {}  # Ensure metadata is always a dictionary
                    
                    documents.append(doc)
                    
                return documents
        except Exception as e:
            self.logger.error(f"Error retrieving documents: {e}")
            self.logger.exception(e)
            return []

    def get_document(self, doc_id: str) -> Dict[str, Any]:
        """
        Ottiene un documento specifico dal database.
        
        Args:
            doc_id: ID del documento
            
        Returns:
            Documento o None se non trovato
        """
        try:
            with self._get_db() as (conn, cursor):
                # Verifica se la tabella ha la colonna metadata
                cursor.execute("PRAGMA table_info(documents)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Adatta la query in base alle colonne disponibili
                if 'metadata' in columns:
                    cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
                else:
                    cursor.execute("SELECT id, title, text, word_count, date_created, date_modified, created_by, assigned_to FROM documents WHERE id = ?", (doc_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                    
                doc = dict(row)
                
                # Converti il metadata da JSON a dizionario se presente
                if 'metadata' in doc and doc['metadata']:
                    try:
                        doc['metadata'] = json.loads(doc['metadata'])
                    except json.JSONDecodeError:
                        self.logger.warning(f"Errore nella decodifica dei metadati per il documento {doc_id}")
                        doc['metadata'] = {}
                
                return doc
        except Exception as e:
            self.logger.error(f"Errore nel recupero del documento {doc_id}: {e}")
            self.logger.exception(e)
            return None
    
    def save_document(self, document: Dict[str, Any], user_id: str = None) -> bool:
        """
        Salva un documento nel database.
        
        Args:
            document: Documento da salvare
            user_id: ID dell'utente che sta salvando il documento
                
        Returns:
            True se salvato con successo, False altrimenti
        """
        try:
            now = datetime.datetime.now().isoformat()
            
            if 'date_created' not in document:
                document['date_created'] = now
            
            document['date_modified'] = now
            
            # Gestisci i metadati serializzandoli in JSON se presenti
            metadata_json = None
            if 'metadata' in document and document['metadata']:
                try:
                    # Se è già una stringa JSON, usala così com'è
                    if isinstance(document['metadata'], str):
                        metadata_json = document['metadata']
                    else:
                        # Altrimenti, serializzala
                        metadata_json = json.dumps(document['metadata'])
                except Exception as e:
                    self.logger.warning(f"Errore nella serializzazione dei metadati: {e}")
                    # Se c'è un errore, mettiamo None per evitare problemi nel database
                    metadata_json = None
            
            with self._get_db() as (conn, cursor):
                # Verifica se la tabella ha la colonna metadata
                cursor.execute("PRAGMA table_info(documents)")
                columns = [col[1] for col in cursor.fetchall()]
                
                # Se la colonna metadata esiste
                if 'metadata' in columns:
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO documents 
                        (id, title, text, word_count, date_created, date_modified, created_by, assigned_to, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            document['id'],
                            document['title'],
                            document['text'],
                            document.get('word_count', 0),
                            document['date_created'],
                            document['date_modified'],
                            document.get('created_by', user_id),
                            document.get('assigned_to'),
                            metadata_json
                        )
                    )
                else:
                    # Fallback se la colonna non esiste
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO documents 
                        (id, title, text, word_count, date_created, date_modified, created_by, assigned_to)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            document['id'],
                            document['title'],
                            document['text'],
                            document.get('word_count', 0),
                            document['date_created'],
                            document['date_modified'],
                            document.get('created_by', user_id),
                            document.get('assigned_to')
                        )
                    )
                
                conn.commit()
                self.logger.debug(f"Documento salvato: {document['id']}")
                
                # Log activity
                if user_id:
                    is_new = cursor.rowcount == 1
                    self.log_user_activity(
                        user_id=user_id,
                        action_type="create_document" if is_new else "update_document",
                        document_id=document['id']
                    )
                    
                return True
        except Exception as e:
            self.logger.error(f"Errore nel salvataggio del documento: {e}")
            self.logger.exception(e)
            return False   
        
    def delete_document(self, doc_id: str) -> bool:
        """
        Elimina un documento e le sue annotazioni dal database.
        
        Args:
            doc_id: ID del documento
            
        Returns:
            True se eliminato con successo, False altrimenti
        """
        try:
            with self._get_db() as (conn, cursor):
                # Elimina prima le annotazioni associate
                cursor.execute("DELETE FROM annotations WHERE doc_id = ?", (doc_id,))
                # Poi elimina il documento
                cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
                conn.commit()
                logger.debug(f"Documento eliminato: {doc_id}")
                return True
        except Exception as e:
            logger.error(f"Errore nell'eliminazione del documento: {e}")
            return False
    
    def update_document(self, doc_id: str, updates: Dict[str, Any]) -> bool:
        """
        Aggiorna un documento esistente.
        
        Args:
            doc_id: ID del documento
            updates: Dizionario con i campi da aggiornare
            
        Returns:
            True se aggiornato con successo, False altrimenti
        """
        try:
            document = self.get_document(doc_id)
            if not document:
                logger.warning(f"Documento non trovato: {doc_id}")
                return False
            
            # Aggiorna i campi
            for key, value in updates.items():
                if key in ['title', 'text', 'word_count']:
                    document[key] = value
            
            document['date_modified'] = datetime.datetime.now().isoformat()
            
            return self.save_document(document)
        except Exception as e:
            logger.error(f"Errore nell'aggiornamento del documento: {e}")
            return False
    
    def update_document_status(self, doc_id: str, status: str, user_id: str = None) -> bool:
        """
        Aggiorna lo stato di un documento.
        
        Args:
            doc_id: ID del documento
            status: Nuovo stato (pending, completed, skipped)
            user_id: ID utente che effettua la modifica (opzionale)
                
        Returns:
            True se aggiornato con successo, False altrimenti
        """
        valid_statuses = ['pending', 'completed', 'skipped']
        if status not in valid_statuses:
            self.logger.warning(f"Invalid status '{status}' requested for doc {doc_id}")
            return False
            
        try:
            with self._get_db() as (conn, cursor):
                cursor.execute(
                    "UPDATE documents SET status = ?, date_modified = ? WHERE id = ?",
                    (status, datetime.datetime.now().isoformat(), doc_id)
                )
                success = cursor.rowcount > 0
                
                if success and user_id:
                    # Log the activity
                    self.log_user_activity(
                        user_id=user_id,
                        action_type=f"update_document_status",
                        document_id=doc_id,
                        details=f"Changed status to {status}"
                    )
                    
                return success
        except Exception as e:
            self.logger.error(f"Error updating document status: {e}")
            return False

    def get_next_document(self, current_doc_id: str, user_id: str = None, status: str = 'pending') -> Dict[str, Any]:
        """
        Trova il prossimo documento (in ordine di data) per l'utente specificato.
        
        Args:
            current_doc_id: ID del documento corrente
            user_id: ID dell'utente (filtro opzionale)
            status: Stato dei documenti da considerare (default: pending)
            
        Returns:
            Documento successivo o None se non trovato
        """
        try:
            # Ottieni la data di creazione del documento corrente
            current_doc = self.get_document(current_doc_id)
            if not current_doc:
                return None
                
            current_date = current_doc.get('date_created')
            
            with self._get_db() as (conn, cursor):
                query = """
                    SELECT * FROM documents 
                    WHERE date_created > ? AND status = ?
                """
                params = [current_date, status]
                
                if user_id:
                    query += " AND assigned_to = ?"
                    params.append(user_id)
                    
                query += " ORDER BY date_created ASC LIMIT 1"
                
                cursor.execute(query, params)
                row = cursor.fetchone()
                
                if row:
                    doc = dict(row)
                    # Process metadata like in get_documents
                    if 'metadata' in doc and doc['metadata']:
                        try:
                            doc['metadata'] = json.loads(doc['metadata'])
                        except json.JSONDecodeError:
                            doc['metadata'] = {}
                    else:
                        doc['metadata'] = {}
                        
                    return doc
                    
                # Se non ci sono documenti successivi, prova a ottenere il primo documento
                query = """
                    SELECT * FROM documents 
                    WHERE id != ? AND status = ?
                """
                params = [current_doc_id, status]
                
                if user_id:
                    query += " AND assigned_to = ?"
                    params.append(user_id)
                    
                query += " ORDER BY date_created ASC LIMIT 1"
                
                cursor.execute(query, params)
                row = cursor.fetchone()
                
                if row:
                    doc = dict(row)
                    if 'metadata' in doc and doc['metadata']:
                        try:
                            doc['metadata'] = json.loads(doc['metadata'])
                        except json.JSONDecodeError:
                            doc['metadata'] = {}
                    else:
                        doc['metadata'] = {}
                    return doc
                    
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting next document: {e}")
            return None


    # ---- Operazioni sulle annotazioni ----
    
    def get_annotations(self, doc_id: str = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Ottiene le annotazioni, raggruppate per documento.
        
        Args:
            doc_id: Opzionale, filtra per ID documento
            
        Returns:
            Dizionario {doc_id: [annotazioni]}
        """
        with self._get_db() as (conn, cursor):
            if doc_id:
                cursor.execute("SELECT * FROM annotations WHERE doc_id = ? ORDER BY start", (doc_id,))
            else:
                cursor.execute("SELECT * FROM annotations ORDER BY doc_id, start")
            
            rows = cursor.fetchall()
            result = {}
            
            for row in rows:
                row_dict = dict(row)
                doc_id = row_dict['doc_id']
                
                # Converti il metadata da JSON a dizionario
                if row_dict.get('metadata'):
                    try:
                        row_dict['metadata'] = json.loads(row_dict['metadata'])
                    except:
                        row_dict['metadata'] = {}
                else:
                    row_dict['metadata'] = {}
                
                if doc_id not in result:
                    result[doc_id] = []
                result[doc_id].append(row_dict)
            
            return result
    
    def get_document_annotations(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        Ottiene le annotazioni per un documento specifico.
        
        Args:
            doc_id: ID del documento
            
        Returns:
            Lista di annotazioni
        """
        annotations = self.get_annotations(doc_id)
        return annotations.get(doc_id, [])
    
    def save_annotation(self, doc_id: str, annotation: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        """
        Salva un'annotazione nel database.
        
        Args:
            doc_id: ID del documento
            annotation: Annotazione da salvare
            user_id: ID dell'utente che sta salvando l'annotazione
                
        Returns:
            L'annotazione salvata con ID generato se era nuovo
        """
        try:
            now = datetime.datetime.now().isoformat()
            
            # Genera un ID se non presente
            if 'id' not in annotation or not annotation['id']:
                annotation['id'] = f"ann_{doc_id}_{int(datetime.datetime.now().timestamp())}"
            
            # Aggiungi date se non presenti
            if 'date_created' not in annotation:
                annotation['date_created'] = now
            
            annotation['date_modified'] = now
            
            # Converti metadata in JSON se presente
            metadata_json = None
            if 'metadata' in annotation and annotation['metadata']:
                metadata_json = json.dumps(annotation['metadata'])
            
            # Aggiungi user_id
            if user_id and 'created_by' not in annotation:
                annotation['created_by'] = user_id
            
            with self._get_db() as (conn, cursor):
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO annotations
                    (id, doc_id, start, end, text, type, metadata, date_created, date_modified, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        annotation['id'],
                        doc_id,
                        annotation['start'],
                        annotation['end'],
                        annotation['text'],
                        annotation['type'],
                        metadata_json,
                        annotation['date_created'],
                        annotation['date_modified'],
                        annotation.get('created_by')
                    )
                )
                conn.commit()
                logger.debug(f"Annotazione salvata: {annotation['id']} per doc {doc_id}")
                
                # Log activity
                if user_id:
                    is_new = cursor.rowcount == 1
                    self.log_user_activity(
                        user_id=user_id,
                        action_type="create_annotation" if is_new else "update_annotation",
                        document_id=doc_id,
                        annotation_id=annotation['id']
                    )
                    
                return annotation
        except Exception as e:
            logger.error(f"Errore nel salvataggio dell'annotazione: {e}")
            return None
        
    def delete_annotation(self, annotation_id: str) -> bool:
        """
        Elimina un'annotazione dal database.
        
        Args:
            annotation_id: ID dell'annotazione
            
        Returns:
            True se eliminata con successo, False altrimenti
        """
        try:
            with self._get_db() as (conn, cursor):
                cursor.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))
                conn.commit()
                logger.debug(f"Annotazione eliminata: {annotation_id}")
                return True
        except Exception as e:
            logger.error(f"Errore nell'eliminazione dell'annotazione: {e}")
            return False
    
    def clear_annotations(self, doc_id: str, entity_type: str = None) -> bool:
        """
        Elimina tutte le annotazioni di un documento, opzionalmente filtrando per tipo.
        
        Args:
            doc_id: ID del documento
            entity_type: Opzionale, tipo di entità da eliminare
            
        Returns:
            True se eliminate con successo, False altrimenti
        """
        try:
            with self._get_db() as (conn, cursor):
                if entity_type:
                    cursor.execute("DELETE FROM annotations WHERE doc_id = ? AND type = ?", (doc_id, entity_type))
                    logger.debug(f"Annotazioni di tipo {entity_type} eliminate per doc {doc_id}")
                else:
                    cursor.execute("DELETE FROM annotations WHERE doc_id = ?", (doc_id,))
                    logger.debug(f"Tutte le annotazioni eliminate per doc {doc_id}")
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Errore nell'eliminazione delle annotazioni: {e}")
            return False
    
    # ---- Esportazione dati ----
    
    def export_json(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Esporta tutte le annotazioni in formato JSON.
        
        Returns:
            Dizionario con le annotazioni in formato compatibile con il formato JSON dell'app
        """
        return self.get_annotations()
    
    def export_spacy(self) -> List[Dict[str, Any]]:
        """
        Esporta le annotazioni in formato spaCy.
        
        Returns:
            Lista di documenti con entità in formato spaCy
        """
        spacy_data = []
        annotations = self.get_annotations()
        
        for doc_id, doc_annotations in annotations.items():
            document = self.get_document(doc_id)
            if document:
                text = document['text']
                entities = []
                
                for ann in doc_annotations:
                    entities.append((ann['start'], ann['end'], ann['type']))
                
                spacy_data.append({"text": text, "entities": entities})
        
        return spacy_data
    
    def import_from_json(self, annotations_json: Dict[str, List[Dict[str, Any]]]) -> bool:
        """
        Importa annotazioni da un dizionario in formato JSON.
        
        Args:
            annotations_json: Dizionario {doc_id: [annotazioni]}
            
        Returns:
            True se importate con successo, False altrimenti
        """
        try:
            with self._get_db() as (conn, cursor):
                for doc_id, annotations in annotations_json.items():
                    for annotation in annotations:
                        self.save_annotation(doc_id, annotation)
                
                conn.commit()
                logger.info(f"Importate {sum(len(anns) for anns in annotations_json.values())} annotazioni")
                return True
        except Exception as e:
            logger.error(f"Errore nell'importazione delle annotazioni: {e}")
            return False
    
    # Metodi per i chunk del grafo
    def get_graph_chunks(self, status=None, assigned_to=None) -> List[Dict[str, Any]]:
        """Ottiene tutti i chunk del grafo con filtri."""
        try:
            with self._get_db() as (conn, cursor):
                query = "SELECT * FROM graph_chunks"
                params = []
                
                # Costruisci la query dinamicamente in base ai filtri
                conditions = []
                if status:
                    conditions.append("status = ?")
                    params.append(status)
                if assigned_to:
                    conditions.append("assigned_to = ?")
                    params.append(assigned_to)
                    
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                    
                query += " ORDER BY date_created DESC"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                chunks = []
                for row in rows:
                    chunk = dict(row)
                    
                    # Converti dati JSON
                    if 'data' in chunk and chunk['data']:
                        try:
                            chunk['data'] = json.loads(chunk['data'])
                        except json.JSONDecodeError:
                            self.logger.warning(f"Error decoding data for chunk {chunk['id']}")
                            chunk['data'] = {}
                    
                    chunks.append(chunk)
                    
                return chunks
        except Exception as e:
            self.logger.error(f"Error retrieving graph chunks: {e}")
            self.logger.exception(e)
            return []

    def get_graph_chunk(self, chunk_id: str) -> Dict[str, Any]:
        """Ottiene un chunk specifico del grafo."""
        try:
            with self._get_db() as (conn, cursor):
                cursor.execute("SELECT * FROM graph_chunks WHERE id = ?", (chunk_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                    
                chunk = dict(row)
                
                # Converti dati JSON
                if 'data' in chunk and chunk['data']:
                    try:
                        chunk['data'] = json.loads(chunk['data'])
                    except json.JSONDecodeError:
                        self.logger.warning(f"Error decoding data for chunk {chunk_id}")
                        chunk['data'] = {}
                
                return chunk
        except Exception as e:
            self.logger.error(f"Error retrieving graph chunk {chunk_id}: {e}")
            self.logger.exception(e)
            return None

    def check_chunk_exists_for_seed(self, seed_node_id: str) -> bool:
        """Verifica se esiste già un chunk per un dato seed node ID."""
        try:
            with self._get_db() as (conn, cursor):
                cursor.execute(
                    "SELECT 1 FROM graph_chunks WHERE seed_node_id = ? LIMIT 1", 
                    (seed_node_id,)
                )
                exists = cursor.fetchone() is not None
                return exists
        except sqlite3.OperationalError as e:
            # Handle case where column might not exist yet (though migration should prevent this)
            if "no such column: seed_node_id" in str(e):
                self.logger.warning("Column seed_node_id not found, assuming chunk does not exist.")
                return False
            else:
                self.logger.error(f"Error checking chunk existence for seed {seed_node_id}: {e}")
                return False # Assume false on error?
        except Exception as e:
            self.logger.error(f"Error checking chunk existence for seed {seed_node_id}: {e}")
            return False # Assume false on error?

    def save_graph_chunk(self, chunk_data: Dict[str, Any], user_id: str = None, seed_node_id: Optional[str] = None) -> str:
        """Salva un chunk del grafo, includendo opzionalmente il seed_node_id."""
        try:
            now = datetime.datetime.now().isoformat()
            
            # Genera un ID se non presente
            chunk_id = chunk_data.get('id')
            if not chunk_id:
                chunk_id = f"chunk_{int(datetime.datetime.now().timestamp())}\""
            
            # Converti dati in JSON
            data_json = json.dumps(chunk_data.get('data', {}))
            
            # Get seed_node_id from chunk_data if not passed explicitly
            if seed_node_id is None:
                seed_node_id = chunk_data.get('seed_node_id')
                
            with self._get_db() as (conn, cursor):
                # Check if seed_node_id column exists
                cursor.execute("PRAGMA table_info(graph_chunks)")
                columns = [col[1] for col in cursor.fetchall()]
                has_seed_col = 'seed_node_id' in columns

                sql = f'''
                INSERT OR REPLACE INTO graph_chunks 
                (id, title, description, chunk_type, data, status, date_created, date_modified, created_by, assigned_to{', seed_node_id' if has_seed_col else ''})
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?{', ?' if has_seed_col else ''})
                '''
                
                params = (
                    chunk_id,
                    chunk_data.get('title', f"Chunk {chunk_id}"),
                    chunk_data.get('description', ''),
                    chunk_data.get('chunk_type', 'subgraph'),
                    data_json,
                    chunk_data.get('status', 'pending'),
                    chunk_data.get('date_created', now),
                    now,
                    chunk_data.get('created_by', user_id),
                    chunk_data.get('assigned_to'),
                )
                
                if has_seed_col:
                    params += (seed_node_id,)
                    
                cursor.execute(sql, params)
                
                # Log activity
                if user_id:
                    self.log_user_activity(
                        user_id=user_id,
                        action_type="create_graph_chunk" if cursor.rowcount == 1 else "update_graph_chunk",
                        document_id=chunk_id
                    )
                
                return chunk_id
        except Exception as e:
            self.logger.error(f"Error saving graph chunk: {e}")
            self.logger.exception(e)
            return None

    # Metodi per le proposte
    def get_graph_proposals(self, chunk_id: str) -> List[Dict[str, Any]]:
        """Ottiene tutte le proposte di modifica per un chunk."""
        try:
            with self._get_db() as (conn, cursor):
                cursor.execute(
                    """
                    SELECT p.*, 
                        COUNT(CASE WHEN v.vote = 'approve' THEN 1 END) as approve_count,
                        COUNT(CASE WHEN v.vote = 'reject' THEN 1 END) as reject_count
                    FROM graph_proposals p
                    LEFT JOIN graph_votes v ON p.id = v.proposal_id
                    WHERE p.chunk_id = ?
                    GROUP BY p.id
                    ORDER BY p.date_created DESC
                    """, 
                    (chunk_id,)
                )
                rows = cursor.fetchall()
                
                proposals = []
                for row in rows:
                    proposal = dict(row)
                    
                    # Converti dati JSON
                    for field in ['original_data', 'proposed_data']:
                        if field in proposal and proposal[field]:
                            try:
                                proposal[field] = json.loads(proposal[field])
                            except json.JSONDecodeError:
                                self.logger.warning(f"Error decoding {field} for proposal {proposal['id']}")
                                proposal[field] = {}
                    
                    # Ottieni i dettagli dei voti
                    cursor.execute(
                        """
                        SELECT v.*, u.username, u.full_name
                        FROM graph_votes v
                        JOIN users u ON v.user_id = u.id
                        WHERE v.proposal_id = ?
                        """, 
                        (proposal['id'],)
                    )
                    votes = [dict(vote) for vote in cursor.fetchall()]
                    proposal['votes'] = votes
                    
                    proposals.append(proposal)
                    
                return proposals
        except Exception as e:
            self.logger.error(f"Error retrieving graph proposals: {e}")
            self.logger.exception(e)
            return []

    def save_graph_proposal(self, proposal_data: Dict[str, Any], user_id: str = None) -> str:
        """Salva una proposta di modifica."""
        try:
            now = datetime.datetime.now().isoformat()
            
            # Genera un ID se non presente
            proposal_id = proposal_data.get('id')
            if not proposal_id:
                proposal_id = f"proposal_{int(datetime.datetime.now().timestamp())}"
            
            # Converti dati in JSON
            original_data_json = json.dumps(proposal_data.get('original_data', {}))
            proposed_data_json = json.dumps(proposal_data.get('proposed_data', {}))
            
            with self._get_db() as (conn, cursor):
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO graph_proposals 
                    (id, chunk_id, proposal_type, original_data, proposed_data, status, votes_required, date_created, date_modified, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        proposal_id,
                        proposal_data.get('chunk_id'),
                        proposal_data.get('proposal_type', 'modify'),
                        original_data_json,
                        proposed_data_json,
                        proposal_data.get('status', 'pending'),
                        proposal_data.get('votes_required', 0),
                        proposal_data.get('date_created', now),
                        now,
                        proposal_data.get('created_by', user_id)
                    )
                )
                
                # Log activity
                if user_id:
                    self.log_user_activity(
                        user_id=user_id,
                        action_type="create_graph_proposal",
                        document_id=proposal_data.get('chunk_id'),
                        details=f"Proposta di tipo {proposal_data.get('proposal_type')}"
                    )
                
                return proposal_id
        except Exception as e:
            self.logger.error(f"Error saving graph proposal: {e}")
            self.logger.exception(e)
            return None

    def update_graph_proposal_status(self, proposal_id: str, status: str, message: Optional[str] = None) -> bool:
        """Aggiorna lo stato di una proposta e opzionalmente aggiunge un messaggio."""
        allowed_statuses = ['pending', 'approved', 'rejected', 'applied', 'failed']
        if status not in allowed_statuses:
            self.logger.error(f"Tentativo di impostare uno stato non valido '{status}' per la proposta {proposal_id}")
            return False
            
        try:
            now = datetime.datetime.now().isoformat()
            with self._get_db() as (conn, cursor):
                # Potremmo voler aggiungere un campo 'message' alla tabella graph_proposals per memorizzare errori o note
                # Per ora, aggiorniamo solo lo stato e la data di modifica.
                cursor.execute(
                    "UPDATE graph_proposals SET status = ?, date_modified = ? WHERE id = ?",
                    (status, now, proposal_id)
                )
                conn.commit()
                success = cursor.rowcount > 0
                if success:
                    self.logger.info(f"Stato della proposta {proposal_id} aggiornato a '{status}' (Messaggio: {message or 'N/A'})")
                else:
                     self.logger.warning(f"Nessuna proposta trovata con ID {proposal_id} per aggiornare lo stato a '{status}'.")
                return success
        except Exception as e:
            self.logger.error(f"Errore nell'aggiornamento dello stato della proposta {proposal_id}: {e}")
            self.logger.exception(e)
            return False
            
    def update_graph_proposal_votes_required(self, proposal_id: str, votes_required: int) -> bool:
        """Aggiorna il numero di voti richiesti per una proposta."""
        try:
            with self._get_db() as (conn, cursor):
                cursor.execute(
                    "UPDATE graph_proposals SET votes_required = ? WHERE id = ?",
                    (votes_required, proposal_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Errore nell'aggiornamento dei voti richiesti per la proposta {proposal_id}: {e}")
            return False

    # Metodi per i voti
    def add_graph_vote(self, vote_data: Dict[str, Any], user_id: str = None) -> Dict[str, Any]:
        """Aggiunge un voto a una proposta di modifica."""
        try:
            now = datetime.datetime.now().isoformat()
            
            # Genera un ID se non presente
            vote_id = vote_data.get('id')
            if not vote_id:
                vote_id = f"vote_{int(datetime.datetime.now().timestamp())}"
            
            proposal_id = vote_data.get('proposal_id')
            vote_value = vote_data.get('vote')
            
            if not proposal_id or not vote_value:
                raise ValueError("proposal_id e vote sono campi obbligatori")
            
            with self._get_db() as (conn, cursor):
                # Verifica se l'utente ha già votato questa proposta
                cursor.execute(
                    "SELECT id, vote FROM graph_votes WHERE proposal_id = ? AND user_id = ?",
                    (proposal_id, user_id)
                )
                existing_vote = cursor.fetchone()
                
                if existing_vote:
                    # Aggiorna il voto esistente
                    cursor.execute(
                        "UPDATE graph_votes SET vote = ?, comment = ?, date_created = ? WHERE id = ?",
                        (vote_value, vote_data.get('comment', ''), now, existing_vote['id'])
                    )
                    vote_id = existing_vote['id']
                    vote_changed = existing_vote['vote'] != vote_value
                else:
                    # Inserisci nuovo voto
                    cursor.execute(
                        """
                        INSERT INTO graph_votes 
                        (id, proposal_id, user_id, vote, comment, date_created)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            vote_id,
                            proposal_id,
                            user_id,
                            vote_value,
                            vote_data.get('comment', ''),
                            now
                        )
                    )
                    vote_changed = True
                
                # Log activity
                if user_id:
                    self.log_user_activity(
                        user_id=user_id,
                        action_type="vote_graph_proposal",
                        details=f"Voto '{vote_value}' per proposta {proposal_id}"
                    )
                
                # Conta i voti per questa proposta
                cursor.execute(
                    """
                    SELECT 
                        COUNT(CASE WHEN vote = 'approve' THEN 1 END) as approve_count,
                        COUNT(CASE WHEN vote = 'reject' THEN 1 END) as reject_count
                    FROM graph_votes
                    WHERE proposal_id = ?
                    """, 
                    (proposal_id,)
                )
                vote_counts = cursor.fetchone()
                
                # Ottieni il numero di voti richiesti per la proposta
                cursor.execute(
                    "SELECT votes_required FROM graph_proposals WHERE id = ?",
                    (proposal_id,)
                )
                proposal = cursor.fetchone()
                votes_required = proposal['votes_required'] if proposal else 0
                
                # Verifica se la proposta deve essere approvata o respinta
                approve_count = vote_counts['approve_count']
                reject_count = vote_counts['reject_count']
                proposal_approved = False
                proposal_rejected = False
                
                # Se il numero di voti approva o rigetta supera la soglia del 51%
                if approve_count >= votes_required:
                    cursor.execute(
                        "UPDATE graph_proposals SET status = 'approved', date_modified = ? WHERE id = ?",
                        (now, proposal_id)
                    )
                    proposal_approved = True
                elif reject_count >= votes_required:
                    cursor.execute(
                        "UPDATE graph_proposals SET status = 'rejected', date_modified = ? WHERE id = ?",
                        (now, proposal_id)
                    )
                    proposal_rejected = True
                
                return {
                    "vote_id": vote_id,
                    "proposal_id": proposal_id,
                    "approve_count": approve_count,
                    "reject_count": reject_count,
                    "votes_required": votes_required,
                    "proposal_approved": proposal_approved,
                    "proposal_rejected": proposal_rejected,
                    "vote_changed": vote_changed
                }
        except Exception as e:
            self.logger.error(f"Error adding graph vote: {e}")
            self.logger.exception(e)
            return {"status": "error", "message": str(e)}

    # Metodi per le assegnazioni dei chunk
    def get_chunk_assignments(self, chunk_id: str) -> List[Dict[str, Any]]:
        """Ottiene le assegnazioni di un chunk."""
        try:
            with self._get_db() as (conn, cursor):
                cursor.execute("""
                    SELECT c.id as chunk_id, u.id as user_id, u.username, u.full_name, c.date_modified as assigned_date 
                    FROM graph_chunks c
                    JOIN users u ON c.assigned_to = u.id
                    WHERE c.id = ?
                """, (chunk_id,))
                
                assignments = []
                for row in cursor.fetchall():
                    assignments.append(dict(row))
                
                return assignments
        except Exception as e:
            self.logger.error(f"Error retrieving chunk assignments: {e}")
            self.logger.exception(e)
            return []

    def assign_chunk_to_user(self, chunk_id: str, user_id: str, assigner_id: str = None) -> bool:
        """Assegna un chunk a un utente."""
        try:
            now = datetime.datetime.now().isoformat()
            
            with self._get_db() as (conn, cursor):
                # Verifica che il chunk esista
                cursor.execute("SELECT id FROM graph_chunks WHERE id = ?", (chunk_id,))
                if not cursor.fetchone():
                    self.logger.warning(f"Chunk {chunk_id} not found for assignment")
                    return False
                
                # Verifica che l'utente esista
                cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))
                if not cursor.fetchone():
                    self.logger.warning(f"User {user_id} not found for assignment")
                    return False
                
                # Assegna il chunk
                cursor.execute(
                    "UPDATE graph_chunks SET assigned_to = ?, date_modified = ? WHERE id = ?",
                    (user_id, now, chunk_id)
                )
                
                # Log activity
                if assigner_id:
                    self.log_user_activity(
                        user_id=assigner_id,
                        action_type="assign_graph_chunk",
                        document_id=chunk_id,
                        details=f"Chunk assegnato all'utente {user_id}"
                    )
                
                return True
        except Exception as e:
            self.logger.error(f"Error assigning chunk: {e}")
            self.logger.exception(e)
            return False

    def remove_chunk_assignment(self, chunk_id: str, user_id: str) -> bool:
        """Rimuove l'assegnazione di un chunk a un utente."""
        try:
            now = datetime.datetime.now().isoformat()
            
            with self._get_db() as (conn, cursor):
                # Verifica che il chunk sia assegnato all'utente specificato
                cursor.execute(
                    "SELECT id FROM graph_chunks WHERE id = ? AND assigned_to = ?", 
                    (chunk_id, user_id)
                )
                if not cursor.fetchone():
                    self.logger.warning(f"Chunk {chunk_id} not assigned to user {user_id}")
                    return False
                
                # Rimuovi l'assegnazione
                cursor.execute(
                    "UPDATE graph_chunks SET assigned_to = NULL, date_modified = ? WHERE id = ?",
                    (now, chunk_id)
                )
                
                return True
        except Exception as e:
            self.logger.error(f"Error removing chunk assignment: {e}")
            self.logger.exception(e)
            return False

    def delete_graph_chunk(self, chunk_id: str) -> bool:
        """Elimina un chunk e tutte le proposte e voti associati."""
        try:
            with self._get_db() as (conn, cursor):
                # Elimina i voti associati alle proposte del chunk
                cursor.execute("""
                    DELETE FROM graph_votes 
                    WHERE proposal_id IN (
                        SELECT id FROM graph_proposals WHERE chunk_id = ?
                    )
                """, (chunk_id,))
                
                # Elimina le proposte associate al chunk
                cursor.execute("DELETE FROM graph_proposals WHERE chunk_id = ?", (chunk_id,))
                
                # Elimina il chunk
                cursor.execute("DELETE FROM graph_chunks WHERE id = ?", (chunk_id,))
                
                return True
        except Exception as e:
            self.logger.error(f"Error deleting graph chunk: {e}")
            self.logger.exception(e)
            return False