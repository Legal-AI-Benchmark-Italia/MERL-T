#!/usr/bin/env python3
"""
db_manager.py
Sistema di persistenza delle annotazioni basato su PostgreSQL.
"""

import os
import psycopg2
import psycopg2.extras # Per RealDictCursor e Json
import json
import logging
import datetime
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import hashlib # Moved import here for clarity

# Import ConfigManager
from src.core.config import get_config_manager

# Setup del logger
logger = logging.getLogger("db_manager")
logger.setLevel(logging.INFO)

# Verifica se il logger ha già degli handler configurati
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)

class DBContextManager:
    def __init__(self, db_params):
        self.db_params = db_params
        self.conn = None # Initialize conn to None
        self.cursor = None # Initialize cursor to None
    
    def __enter__(self):
        try:
            # Use connection parameters stored in self.db_params
            self.conn = psycopg2.connect(**self.db_params) 
            # Use RealDictCursor to get results as dictionaries
            self.cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            logger.debug("PostgreSQL connection opened and cursor created.")
            return self.conn, self.cursor
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to PostgreSQL database: {e}")
            # Reraise the error
            raise
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if self.cursor:
                self.cursor.close()
                logger.debug("PostgreSQL cursor closed.")
            
            if self.conn:
                if exc_type is None:
                    # Commit only if no exception occurred
                    self.conn.commit()
                    logger.debug("PostgreSQL transaction committed.")
                else:
                    # Rollback if an exception occurred
                    try:
                        self.conn.rollback()
                        logger.warning("PostgreSQL transaction rolled back due to exception.")
                    except psycopg2.Error as rb_error:
                        logger.error(f"Error during rollback: {rb_error}")
                
                # Always close the connection
                self.conn.close()
                logger.debug("PostgreSQL connection closed.")
        except Exception as close_err:
            # Log errors during cleanup but don't suppress original exception
            logger.error(f"Error during DB context exit cleanup: {close_err}")
        
        # Return False to propagate exceptions if they occurred outside the __exit__ itself
        # If an exception happened *within* __exit__, we might want to handle it differently
        # but for now, propagating the original exception is standard.
        return False

class AnnotationDBManager:
    """
    Gestore della persistenza delle annotazioni tramite database PostgreSQL.
    """
    
    # Definizioni delle tabelle PostgreSQL
    table_definitions = {
        "users": """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                full_name TEXT,
                role TEXT DEFAULT 'annotator',
                email TEXT,
                active INTEGER DEFAULT 1,
                date_created TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                date_last_login TIMESTAMPTZ
            )
        """,
        "documents": """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                text TEXT NOT NULL,
                word_count INTEGER,
                date_created TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                date_modified TIMESTAMPTZ,
                created_by TEXT REFERENCES users(id) ON DELETE SET NULL,
                assigned_to TEXT REFERENCES users(id) ON DELETE SET NULL,
                status TEXT DEFAULT 'pending',
                metadata JSONB
            )
        """,
        "annotations": """
            CREATE TABLE IF NOT EXISTS annotations (
                id TEXT PRIMARY KEY,
                doc_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                start_offset INTEGER NOT NULL,
                end_offset INTEGER NOT NULL,
                text TEXT NOT NULL,
                type TEXT NOT NULL,
                metadata JSONB,
                date_created TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                date_modified TIMESTAMPTZ,
                created_by TEXT REFERENCES users(id) ON DELETE SET NULL
            )
        """,
        "user_activity": """
            CREATE TABLE IF NOT EXISTS user_activity (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                action_type TEXT NOT NULL,
                document_id TEXT,
                annotation_id TEXT,
                timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                details TEXT
            )
        """,
        "graph_chunks": """
            CREATE TABLE IF NOT EXISTS graph_chunks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                chunk_type TEXT NOT NULL,
                data JSONB NOT NULL,
                status TEXT DEFAULT 'pending',
                date_created TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                date_modified TIMESTAMPTZ,
                created_by TEXT REFERENCES users(id) ON DELETE SET NULL,
                assigned_to TEXT REFERENCES users(id) ON DELETE SET NULL,
                seed_node_id TEXT
            )
        """,
        "graph_proposals": """
            CREATE TABLE IF NOT EXISTS graph_proposals (
                id TEXT PRIMARY KEY,
                chunk_id TEXT NOT NULL REFERENCES graph_chunks(id) ON DELETE CASCADE,
                proposal_type TEXT NOT NULL,
                original_data JSONB,
                proposed_data JSONB NOT NULL,
                status TEXT DEFAULT 'pending',
                votes_required INTEGER DEFAULT 0,
                date_created TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                date_modified TIMESTAMPTZ,
                created_by TEXT REFERENCES users(id) ON DELETE SET NULL
            )
        """,
        "graph_votes": """
            CREATE TABLE IF NOT EXISTS graph_votes (
                id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL REFERENCES graph_proposals(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                vote TEXT NOT NULL,
                comment TEXT,
                date_created TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(proposal_id, user_id)
            )
        """
    }
    
    # Definizioni degli indici PostgreSQL
    index_definitions = [
        "CREATE INDEX IF NOT EXISTS idx_annotations_doc_id ON annotations(doc_id)",
        "CREATE INDEX IF NOT EXISTS idx_annotations_created_by ON annotations(created_by)",
        "CREATE INDEX IF NOT EXISTS idx_annotations_type ON annotations(type)",
        "CREATE INDEX IF NOT EXISTS idx_activity_user_id ON user_activity(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_activity_timestamp ON user_activity(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_graph_chunks_status ON graph_chunks(status)",
        "CREATE INDEX IF NOT EXISTS idx_graph_chunks_assigned_to ON graph_chunks(assigned_to)",
        "CREATE INDEX IF NOT EXISTS idx_graph_chunks_seed_node_id ON graph_chunks(seed_node_id)",
        "CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status)",
        "CREATE INDEX IF NOT EXISTS idx_documents_assigned_to ON documents(assigned_to)"
    ]
    
    def __init__(self):
        """
        Inizializza il gestore del database leggendo la configurazione PostgreSQL.
        """
        self.logger = logging.getLogger("db_manager")
        
        config_manager = get_config_manager()
        db_config = config_manager.get_section('database')
        
        if db_config.get('db_type') != 'postgresql':
            raise ValueError("Configurazione del database non impostata su 'postgresql' in config.yaml")

        self.db_params = {
            'host': db_config.get('pg_host', 'localhost'),
            'port': db_config.get('pg_port', 5432),
            'user': db_config.get('pg_user'),
            'password': db_config.get('pg_password'),
            'dbname': db_config.get('pg_dbname')
        }

        if not all(self.db_params.values()):
            raise ValueError("Parametri di connessione PostgreSQL mancanti in config.yaml (pg_host, pg_port, pg_user, pg_password, pg_dbname)")
            
        self.logger.info(f"Gestore DB PostgreSQL inizializzato per db '{self.db_params['dbname']}' su {self.db_params['host']}:{self.db_params['port']}")
        
        # Inizializza lo schema del database
        self._init_db()
    
    def _get_db(self) -> DBContextManager:
        """
        Ottiene un context manager per la connessione al database.
        
        Returns:
            DBContextManager instance using PostgreSQL parameters
        """
        return DBContextManager(self.db_params)
    
    def _init_db(self) -> None:
        """
        Inizializza lo schema del database PostgreSQL se necessario.
        """
        logger = logging.getLogger("db_manager")
        log = getattr(self, 'logger', logger)
        
        try:
            with self._get_db() as (conn, cursor):
                log.info("Creating tables for PostgreSQL...")
                for table_name, definition in self.table_definitions.items():
                    log.debug(f"Creating table {table_name}...")
                    cursor.execute(definition)
                log.info("Tables created successfully.")
                
                log.info("Creating indexes for PostgreSQL...")
                for definition in self.index_definitions:
                    log.debug(f"Creating index: {definition[:60]}...")
                    try:
                        cursor.execute(definition)
                    except psycopg2.Error as e:
                        # Potrebbe fallire se un indice GIN viene creato senza l'estensione necessaria
                        log.warning(f"Could not create index ({definition[:60]}...): {e}")
                        conn.rollback() # Annulla la transazione corrente per l'indice fallito
                        conn.autocommit = True # Evita errori in transazioni successive
                        cursor.execute("SELECT 1") # Esegui una query innocua per resettare lo stato
                        conn.autocommit = False # Ripristina autocommit
                log.info("Indexes created successfully.")
                
        except psycopg2.Error as e:
            log.error(f"Database initialization error: {e}")
            raise
        except Exception as e:
            log.error(f"Unexpected error during DB initialization: {e}")
            raise
       
    #--- Operazioni di gestione degli utenti ----
    def create_user(self, user_data: dict) -> Optional[dict]:
        """
        Crea un nuovo utente nel database PostgreSQL.
        
        Args:
            user_data: Dizionario con i dati dell'utente (username, password obbligatori)
                
        Returns:
            Utente creato (dict) o None in caso di errore.
        """
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            
            # Genera un ID se non presente
            user_id = user_data.get('id', f"user_{int(now.timestamp())}")
            
            # Verifica password
            password = user_data.get('password')
            if not password:
                raise ValueError("La password è obbligatoria per creare un utente")
            
            with self._get_db() as (conn, cursor):
                cursor.execute(
                    """
                    INSERT INTO users 
                    (id, username, password, full_name, role, email, active, date_created)
                    VALUES (%s, %s, crypt(%s, gen_salt('bf')), %s, %s, %s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                    RETURNING id;
                    """,
                    (
                        user_id,
                        user_data['username'],
                        password,
                        user_data.get('full_name'),
                        user_data.get('role', 'annotator'),
                        user_data.get('email'),
                        user_data.get('active', 1),
                        now
                    )
                )
                
                # Verifica se l'inserimento è avvenuto
                inserted_row = cursor.fetchone()
                if not inserted_row:
                    self.logger.warning(f"Username '{user_data['username']}' già esistente o altro errore, utente non creato.")
                    return None

                self.logger.debug(f"Utente creato: {user_data['username']} con ID {inserted_row['id']}")
                
                # Ritorna i dati inseriti (senza password)
                created_user_data = user_data.copy()
                created_user_data['id'] = inserted_row['id']
                created_user_data['date_created'] = now
                created_user_data.pop('password', None)
                return created_user_data
                
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB nella creazione dell'utente: {db_err}")
            return None
        except Exception as e:
            self.logger.error(f"Errore generico nella creazione dell'utente: {e}", exc_info=True)
            return None

    def verify_user(self, username: str, password: str) -> Optional[dict]:
        """
        Verifica le credenziali di un utente usando PostgreSQL.
        """
        try:
            self.logger.debug(f"Tentativo di verifica utente: {username}")
            
            if not username or not password:
                self.logger.warning("Username o password vuoti")
                return None
            
            with self._get_db() as (conn, cursor):
                # Usa la funzione crypt di PostgreSQL per verificare la password
                cursor.execute("""
                    SELECT * FROM users 
                    WHERE username = %s 
                    AND password = crypt(%s, password)
                """, (username, password))
                
                user = cursor.fetchone()
                if not user:
                    self.logger.warning(f"Credenziali non valide per utente: {username}")
                    return None
                
                # Verifica se l'utente è attivo
                if not user.get('active', True):
                    self.logger.warning(f"Account utente inattivo: {username}")
                    return None
                
                # Aggiorna last login
                now = datetime.datetime.now(datetime.timezone.utc)
                try:
                    cursor.execute(
                        "UPDATE users SET date_last_login = %s WHERE id = %s",
                        (now, user['id'])
                    )
                except Exception as e:
                    self.logger.error(f"Errore aggiornamento ultimo login: {e}")
                    # Non bloccare il login se l'aggiornamento fallisce
                
                # Non restituire la password
                user_copy = dict(user)
                user_copy.pop('password', None)
                self.logger.info(f"Utente verificato con successo: {username}")
                return user_copy
                
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB durante la verifica utente: {db_err}")
            return None
        except Exception as e:
            self.logger.error(f"Errore imprevisto in verify_user: {e}", exc_info=True)
            return None

    def get_all_users(self, active_only=False) -> list: # Added active_only flag
        """
        Ottiene tutti gli utenti, opzionalmente solo quelli attivi.
        """
        try:
            with self._get_db() as (conn, cursor):
                query = "SELECT id, username, full_name, role, email, active, date_created, date_last_login FROM users"
                params = []
                if active_only:
                    query += " WHERE active = 1" # Assuming active is 1 for true
                    # If active is boolean: query += " WHERE active = TRUE"
                query += " ORDER BY username"
                
                cursor.execute(query)
                # fetchall() con RealDictCursor restituisce già una lista di dizionari
                return cursor.fetchall() 
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB nel recupero utenti: {db_err}")
            return []
        except Exception as e:
            self.logger.error(f"Errore generico nel recupero utenti: {e}", exc_info=True)
            return []

    def update_user(self, user_id: str, updates: dict) -> bool:
        """
        Aggiorna un utente esistente in PostgreSQL.
        """
        try:
            # Verifica prima se l'utente esiste (opzionale ma buona pratica)
            # user = self.get_user_by_id(user_id)
            # if not user:
            #     self.logger.warning(f"Tentativo di aggiornare utente non esistente: {user_id}")
            #     return False
            
            # Se c'è una password da aggiornare, hashala
            if 'password' in updates and updates['password']:
                updates['password'] = hashlib.sha256(updates['password'].encode()).hexdigest()
            elif 'password' in updates:
                del updates['password'] # Rimuovi la chiave se la password è vuota/None
            
            # Costruisci query dinamica
            set_clauses = []
            values = []
            
            allowed_fields = ['username', 'password', 'full_name', 'role', 'email', 'active']
            for key, value in updates.items():
                if key in allowed_fields:
                    # Convalida il tipo di dato se necessario (es. active è booleano o intero?)
                    # Assuming active is integer 0 or 1
                    if key == 'active': 
                        value = 1 if value else 0
                        
                    set_clauses.append(f"{key} = %s")
                    values.append(value)
            
            if not set_clauses:
                self.logger.warning("Nessun campo valido fornito per l'aggiornamento utente.")
                return False # O True se si considera "successo" non fare nulla
            
            values.append(user_id) # Per la clausola WHERE
            
            with self._get_db() as (conn, cursor):
                query = f"UPDATE users SET {', '.join(set_clauses)} WHERE id = %s"
                cursor.execute(query, tuple(values))
                # rowcount > 0 indica che almeno una riga è stata aggiornata
                updated = cursor.rowcount > 0 
                if updated:
                     self.logger.debug(f"Utente {user_id} aggiornato con successo.")
                else:
                     self.logger.warning(f"Nessun utente trovato con ID {user_id} per l'aggiornamento o dati invariati.")
                return updated
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB nell'aggiornamento utente: {db_err}")
            return False
        except Exception as e:
            self.logger.error(f"Errore generico nell'aggiornamento utente: {e}", exc_info=True)
            return False

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """
        Ottiene un utente da PostgreSQL tramite ID.
        """
        try:
            self.logger.debug(f"Recupero utente per ID: {user_id}")
            with self._get_db() as (conn, cursor):
                cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
                row = cursor.fetchone() # fetchone() con RealDictCursor restituisce un dict o None
                if row:
                    self.logger.debug(f"Utente ID '{user_id}' trovato")
                else:
                    self.logger.debug(f"Utente ID '{user_id}' non trovato")
                return row
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB recupero utente per ID: {db_err}")
            return None
        except Exception as e:
            self.logger.error(f"Errore generico recupero utente per ID: {e}", exc_info=True)
            return None
        
    def get_user_by_username(self, username: str) -> Optional[dict]:
        """
        Ottiene un utente da PostgreSQL tramite username.
        """
        try:
            self.logger.debug(f"Recupero utente per username: {username}")
            with self._get_db() as (conn, cursor):
                cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
                row = cursor.fetchone() # Restituisce dict o None
                if row:
                     self.logger.debug(f"Utente '{username}' trovato")
                else:
                     self.logger.debug(f"Utente '{username}' non trovato")
                return row
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB recupero utente per username: {db_err}")
            return None # Fixed indentation
        except Exception as e:
            self.logger.error(f"Errore generico recupero utente per username: {e}", exc_info=True)
            return None # Fixed indentation
        
    def log_user_activity(self, user_id: str, action_type: str, document_id: str = None, 
                        annotation_id: str = None, details: str = None) -> bool:
        """
        Registra un'attività utente nel log PostgreSQL.
        """
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            activity_id = f"act_{int(now.timestamp())}_{hashlib.sha1(os.urandom(8)).hexdigest()[:6]}" # ID più unico
            
            with self._get_db() as (conn, cursor):
                cursor.execute(
                    """
                    INSERT INTO user_activity 
                    (id, user_id, action_type, document_id, annotation_id, timestamp, details)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        activity_id, user_id, action_type, document_id,
                        annotation_id, now, details
                    )
                )
                return True
        except psycopg2.Error as db_err:
            # Considera un logging meno severo se l'attività fallisce ma non è critica
            self.logger.error(f"Errore DB registrazione attività: {db_err}")
            return False
        except Exception as e:
            self.logger.error(f"Errore generico registrazione attività: {e}", exc_info=True)
            return False
    
    def get_user_stats(self, user_id: str = None, days: int = 30) -> dict:
        """
        Ottiene statistiche sull'attività di un utente da PostgreSQL.
        """
        try:
            with self._get_db() as (conn, cursor):
                # Data limite per il periodo
                date_limit = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
                
                stats = {}
                
                # Conteggio totale annotazioni
                try:
                    query = "SELECT COUNT(*) as total FROM annotations WHERE date_created > %s"
                    params = [date_limit]
                    if user_id:
                        query += " AND created_by = %s"
                        params.append(user_id)
                    cursor.execute(query, tuple(params))
                    stats['total_annotations'] = cursor.fetchone()['total']
                except Exception as e:
                    self.logger.error(f"Errore conteggio annotazioni: {e}")
                    stats['total_annotations'] = 0
                
                # Conteggio per tipo di entità
                try:
                    query = """
                            SELECT type, COUNT(*) as count FROM annotations
                        WHERE date_created > %s 
                        """
                    params = [date_limit]
                    if user_id:
                        query += " AND created_by = %s"
                        params.append(user_id)
                    query += " GROUP BY type"
                    
                    cursor.execute(query, tuple(params))
                    stats['annotations_by_type'] = {row['type']: row['count'] for row in cursor.fetchall()}
                except Exception as e:
                    self.logger.error(f"Errore conteggio tipi entità: {e}")
                    stats['annotations_by_type'] = {}
                
                # Attività per giorno
                try:
                    query = """
                        SELECT DATE(timestamp) as day, COUNT(*) as count
                        FROM user_activity
                        WHERE timestamp > %s
                        """
                    params = [date_limit]
                    if user_id:
                        query += " AND user_id = %s"
                        params.append(user_id)
                    query += " GROUP BY day ORDER BY day"
                    
                    cursor.execute(query, tuple(params))
                    # Converte date object in string YYYY-MM-DD
                    stats['activity_by_day'] = {row['day'].isoformat(): row['count'] for row in cursor.fetchall()}
                except Exception as e:
                    self.logger.error(f"Errore recupero attività per giorno: {e}")
                    stats['activity_by_day'] = {}
                
                # Conteggio attività per tipo di azione
                try:
                    query = """
                        SELECT action_type, COUNT(*) as count
                        FROM user_activity
                        WHERE timestamp > %s
                        """
                    params = [date_limit]
                    if user_id:
                        query += " AND user_id = %s"
                        params.append(user_id)
                    query += " GROUP BY action_type"
                    
                    cursor.execute(query, tuple(params))
                    stats['actions_by_type'] = {row['action_type']: row['count'] for row in cursor.fetchall()}
                except Exception as e:
                    self.logger.error(f"Errore conteggio tipi azione: {e}")
                    stats['actions_by_type'] = {}
                
                # Documenti modificati
                try:
                    query = """
                        SELECT COUNT(DISTINCT document_id) as count
                        FROM user_activity
                        WHERE document_id IS NOT NULL AND timestamp > %s
                        """
                    params = [date_limit]
                    if user_id:
                        query += " AND user_id = %s"
                        params.append(user_id)
                        
                    cursor.execute(query, tuple(params))
                    stats['documents_modified'] = cursor.fetchone()['count']
                except Exception as e:
                    self.logger.error(f"Errore conteggio documenti modificati: {e}")
                    stats['documents_modified'] = 0
                
                # Se richiedono statistiche globali
                if not user_id:
                    try:
                        cursor.execute("""
                            SELECT u.id, u.username, u.full_name, COUNT(a.id) as annotations_count
                            FROM users u
                            LEFT JOIN annotations a ON u.id = a.created_by AND a.date_created > %s
                            GROUP BY u.id, u.username, u.full_name
                            ORDER BY annotations_count DESC
                        """, (date_limit,))
                        stats['users'] = cursor.fetchall() # Lista di dict
                    except Exception as e:
                        self.logger.error(f"Errore recupero statistiche per utente: {e}")
                        stats['users'] = []
                
                return stats
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB recupero statistiche: {db_err}")
            return {}
        except Exception as e:
            self.logger.error(f"Errore generico recupero statistiche: {e}", exc_info=True)
            return {}

    def get_user_assignments(self, user_id: str) -> list:
        """
        Ottiene i documenti assegnati a un utente da PostgreSQL.
        """
        try:
            with self._get_db() as (conn, cursor):
                cursor.execute("""
                    SELECT * FROM documents 
                    WHERE assigned_to = %s 
                    ORDER BY date_modified DESC NULLS LAST, date_created DESC
                """, (user_id,))
                # Processa JSONB in dizionari Python
                documents = []
                for row in cursor.fetchall():
                    doc = dict(row) # row è già un dict
                    # metadata è già un dict/None grazie a JSONB e RealDictCursor
                    if doc.get('metadata') is None:
                         doc['metadata'] = {} 
                    documents.append(doc)
                return documents
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB recupero documenti assegnati: {db_err}")
            return []
        except Exception as e:
            self.logger.error(f"Errore generico recupero documenti assegnati: {e}", exc_info=True)
            return []

    def assign_document(self, doc_id: str, user_id: str, assigner_id: str) -> bool:
        """
        Assegna un documento a un utente in PostgreSQL.
        """
        try:
            with self._get_db() as (conn, cursor):
                cursor.execute(
                    "UPDATE documents SET assigned_to = %s, date_modified = NOW() WHERE id = %s",
                    (user_id, doc_id)
                )
                updated = cursor.rowcount > 0
                if updated:
                     # Log activity (questo ora ha il suo try-except interno)
                    try:
                        self.log_user_activity( # Fixed indentation
                    user_id=assigner_id,
                    action_type="assign_document",
                    document_id=doc_id,
                    details=f"Documento assegnato all'utente {user_id}"
                )
                    except Exception as log_e: # Catch specific exception if possible
                         self.logger.warning(f"Failed to log document assignment activity: {log_e}")
                return updated # Fixed indentation
        except psycopg2.Error as db_err:
            self.logger.error(f"Errore DB assegnazione documento: {db_err}")
            return False
        except Exception as e:
            self.logger.error(f"Errore generico assegnazione documento: {e}", exc_info=True)
            return False

    # ---- Operazioni di backup (Rimosse) ----
    # PostgreSQL backups are handled externally (e.g., pg_dump)
    # def create_backup(self) -> str: ...
    # def cleanup_backups(self, max_backups: int = 10) -> None: ...
    
    # ---- Operazioni sui documenti ----
    
    def get_documents(self, status: Optional[str] = None, assigned_to: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Ottiene documenti da PostgreSQL con filtri opzionali.
        
        Args:
            status: Stato dei documenti da filtrare
            assigned_to: ID dell'utente assegnato
            
        Returns:
            Lista di documenti
        """
        try:
            with self._get_db() as (conn, cursor):
                query = """
                    SELECT d.*, 
                        u_created.username as created_by_username,
                        u_assigned.username as assigned_to_username
                    FROM documents d
                    LEFT JOIN users u_created ON d.created_by = u_created.id
                    LEFT JOIN users u_assigned ON d.assigned_to = u_assigned.id
                """
                params = []
                conditions = []
                
                if status:
                    conditions.append("d.status = %s")
                    params.append(status)
                if assigned_to:
                    conditions.append("d.assigned_to = %s")
                    params.append(assigned_to)
                    
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                    
                query += " ORDER BY d.date_created DESC"
                
                cursor.execute(query, tuple(params))
                
                rows = cursor.fetchall()
                
                documents = []
                for row in rows:
                    doc = dict(row)
                    
                    # Gestisci i metadati
                    if doc.get('metadata') is None:
                        doc['metadata'] = {}
                    
                    # Converti le date in formato ISO
                    if doc.get('date_created'):
                        doc['date_created'] = doc['date_created'].isoformat()
                    if doc.get('date_modified'):
                        doc['date_modified'] = doc['date_modified'].isoformat()
                    
                    documents.append(doc)
                    
                return documents
        except Exception as e:
            self.logger.error(f"Error retrieving documents: {e}")
            self.logger.exception(e)
            return []

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Ottiene un documento specifico dal database.
        
        Args:
            doc_id: ID del documento
            
        Returns:
            Il documento se trovato, None altrimenti
        """
        try:
            with self._get_db() as (conn, cursor):
                # Verifica se la tabella ha la colonna metadata
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'documents' AND column_name = 'metadata'
                """)
                has_metadata = cursor.fetchone() is not None
                
                # Adatta la query in base alle colonne disponibili
                if has_metadata:
                    cursor.execute("""
                        SELECT d.*, 
                            u_created.username as created_by_username,
                            u_assigned.username as assigned_to_username
                        FROM documents d
                        LEFT JOIN users u_created ON d.created_by = u_created.id
                        LEFT JOIN users u_assigned ON d.assigned_to = u_assigned.id
                        WHERE d.id = %s
                    """, (doc_id,))
                else:
                    cursor.execute("""
                        SELECT d.*,
                            u_created.username as created_by_username,
                            u_assigned.username as assigned_to_username
                        FROM documents d
                        LEFT JOIN users u_created ON d.created_by = u_created.id
                        LEFT JOIN users u_assigned ON d.assigned_to = u_assigned.id
                        WHERE d.id = %s
                    """, (doc_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                    
                doc = dict(row)
                
                # Converti i metadati da JSONB a dizionario se presenti
                if 'metadata' in doc and doc['metadata']:
                    try:
                        # psycopg2 gestisce automaticamente la conversione da JSONB a dict
                        if doc['metadata'] is None:
                            doc['metadata'] = {}
                    except json.JSONDecodeError:
                        self.logger.warning(f"Errore nella decodifica dei metadati per il documento {doc_id}")
                        doc['metadata'] = {}
                else:
                    doc['metadata'] = {}
                
                # Converti le date in formato ISO
                if doc.get('date_created'):
                    doc['date_created'] = doc['date_created'].isoformat()
                if doc.get('date_modified'):
                    doc['date_modified'] = doc['date_modified'].isoformat()
                
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
            now = datetime.datetime.now(datetime.timezone.utc)
            
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
                # Verifica se la tabella ha la colonna metadata usando information_schema
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'documents' AND column_name = 'metadata'
                """)
                has_metadata = cursor.fetchone() is not None
                
                # Se la colonna metadata esiste
                if has_metadata:
                    cursor.execute(
                        """
                        INSERT INTO documents 
                        (id, title, text, word_count, date_created, date_modified, created_by, assigned_to, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            text = EXCLUDED.text,
                            word_count = EXCLUDED.word_count,
                            date_modified = EXCLUDED.date_modified,
                            created_by = EXCLUDED.created_by,
                            assigned_to = EXCLUDED.assigned_to,
                            metadata = EXCLUDED.metadata
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
                        INSERT INTO documents 
                        (id, title, text, word_count, date_created, date_modified, created_by, assigned_to)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            title = EXCLUDED.title,
                            text = EXCLUDED.text,
                            word_count = EXCLUDED.word_count,
                            date_modified = EXCLUDED.date_modified,
                            created_by = EXCLUDED.created_by,
                            assigned_to = EXCLUDED.assigned_to
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
        
    def delete_document(self, doc_id: str, user_id: str = None) -> bool:
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
                cursor.execute("DELETE FROM annotations WHERE doc_id = %s", (doc_id,))
                # Poi elimina il documento
                cursor.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
                conn.commit()
                logger.debug(f"Documento eliminato: {doc_id}")
                return True
        except Exception as e:
            logger.error(f"Errore nell'eliminazione del documento: {e}")
            return False
    
    def update_document(self, doc_id: str, updates: Dict[str, Any], user_id: str = None) -> bool:
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
        Aggiorna solo lo stato di un documento in PostgreSQL.
        """
        valid_statuses = ['pending', 'completed', 'skipped']
        if status not in valid_statuses:
            self.logger.warning(f"Stato non valido '{status}' richiesto per doc {doc_id}")
            return False
            
        success = False # Initialize success
        try:
            with self._get_db() as (conn, cursor):
                now = datetime.datetime.now(datetime.timezone.utc)
                cursor.execute(
                    "UPDATE documents SET status = %s, date_modified = %s WHERE id = %s",
                    (status, now, doc_id)
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

    def get_next_document(self, current_doc_id: str, user_id: str = None, status: str = 'pending') -> Optional[Dict[str, Any]]:
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
            if not current_doc or not current_doc.get('date_created'):
                self.logger.warning(f"Documento corrente {current_doc_id} o sua data non trovati.")
                return None
                
            current_date = current_doc['date_created']
            
            with self._get_db() as (conn, cursor):
                query = """
                    SELECT * FROM documents 
                    WHERE date_created > %s AND status = %s
                """
                params = [current_date, status]
                
                if user_id:
                    query += " AND assigned_to = %s"
                    params.append(user_id)
                    
                query += " ORDER BY date_created ASC LIMIT 1"
                
                cursor.execute(query, tuple(params))
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
                    WHERE id != %s AND status = %s
                """
                params = [current_doc_id, status]
                
                if user_id:
                    query += " AND assigned_to = %s"
                    params.append(user_id)
                    
                query += " ORDER BY date_created ASC LIMIT 1"
                
                cursor.execute(query, tuple(params))
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
        try:
            with self._get_db() as (conn, cursor):
                if doc_id:
                    cursor.execute("""
                        SELECT 
                            a.*,
                            d.title as document_title,
                            u.username as created_by_username
                        FROM annotations a
                        LEFT JOIN documents d ON a.doc_id = d.id
                        LEFT JOIN users u ON a.created_by = u.id
                        WHERE a.doc_id = %s 
                        ORDER BY a.start_offset
                    """, (doc_id,))
                else:
                    cursor.execute("""
                        SELECT 
                            a.*,
                            d.title as document_title,
                            u.username as created_by_username
                        FROM annotations a
                        LEFT JOIN documents d ON a.doc_id = d.id
                        LEFT JOIN users u ON a.created_by = u.id
                        ORDER BY a.doc_id, a.start_offset
                    """)
                
                rows = cursor.fetchall()
                result = {}
                
                for row_dict in rows:
                    try:
                        # Converti i campi start_offset e end_offset in start e end per il frontend
                        annotation = dict(row_dict)
                        annotation['start'] = annotation.pop('start_offset')
                        annotation['end'] = annotation.pop('end_offset')
                        
                        # Gestisci i metadati
                        if annotation.get('metadata') is None:
                            annotation['metadata'] = {}
                        
                        # Aggiungi informazioni aggiuntive
                        if 'document_title' in annotation:
                            annotation['document_title'] = annotation.pop('document_title')
                        if 'created_by_username' in annotation:
                            annotation['created_by_username'] = annotation.pop('created_by_username')
                        
                        # Converti le date in formato ISO
                        if annotation.get('date_created'):
                            annotation['date_created'] = annotation['date_created'].isoformat()
                        if annotation.get('date_modified'):
                            annotation['date_modified'] = annotation['date_modified'].isoformat()

                        current_doc_id = annotation['doc_id']
                        if current_doc_id not in result:
                            result[current_doc_id] = []
                        result[current_doc_id].append(annotation)
                    except Exception as meta_err:
                        self.logger.warning(f"Error processing annotation {row_dict.get('id')}: {meta_err}")
                        continue
                
                return result
        except Exception as e:
            self.logger.error(f"Error retrieving annotations: {e}")
            self.logger.exception(e)
            return {}
    
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
    
    def save_annotation(self, doc_id: str, annotation: Dict[str, Any], user_id: str = None) -> Optional[Dict[str, Any]]:
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
            now = datetime.datetime.now(datetime.timezone.utc)
            
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
                # Verifica che il documento esista
                cursor.execute("SELECT id FROM documents WHERE id = %s", (doc_id,))
                if not cursor.fetchone():
                    self.logger.error(f"Documento {doc_id} non trovato")
                    return None

                # Inserisci o aggiorna l'annotazione
                cursor.execute(
                    """
                    INSERT INTO annotations
                    (id, doc_id, start_offset, end_offset, text, type, metadata, date_created, date_modified, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        doc_id = EXCLUDED.doc_id,
                        start_offset = EXCLUDED.start_offset,
                        end_offset = EXCLUDED.end_offset,
                        text = EXCLUDED.text,
                        type = EXCLUDED.type,
                        metadata = EXCLUDED.metadata,
                        date_modified = EXCLUDED.date_modified,
                        created_by = EXCLUDED.created_by
                    RETURNING id
                    """,
                    (
                        annotation['id'],
                        doc_id,
                        annotation['start'],  # Cambiato da start_offset a start
                        annotation['end'],    # Cambiato da end_offset a end
                        annotation['text'],
                        annotation['type'],
                        metadata_json,
                        annotation['date_created'],
                        annotation['date_modified'],
                        annotation.get('created_by')
                    )
                )
                
                result = cursor.fetchone()
                if not result:
                    self.logger.error(f"Errore nel recupero dell'ID dell'annotazione dopo il salvataggio")
                    return None

                self.logger.debug(f"Annotazione salvata: {annotation['id']} per doc {doc_id}")
                
                # Log activity
                if user_id:
                    is_new = cursor.rowcount == 1
                    self.log_user_activity(
                        user_id=user_id,
                        action_type="save_annotation",
                        document_id=doc_id,
                        annotation_id=annotation['id']
                    )
                    
                return annotation
        except Exception as e:
            self.logger.error(f"Errore nel salvataggio dell'annotazione: {e}")
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
                    "UPDATE graph_proposals SET status = %s, date_modified = %s WHERE id = %s",
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
                    "UPDATE graph_proposals SET votes_required = %s WHERE id = %s",
                    (votes_required, proposal_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            self.logger.error(f"Errore nell'aggiornamento dei voti richiesti per la proposta {proposal_id}: {e}")
            return False

    # Metodi per i voti
    def add_graph_vote(self, vote_data: Dict[str, Any], user_id: str = None) -> Optional[Dict[str, Any]]:
        """Aggiunge un voto a una proposta di modifica."""
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            
            # Genera un ID se non presente
            vote_id = vote_data.get('id')
            if not vote_id:
                vote_id = f"vote_{int(now.timestamp())}"
            
            proposal_id = vote_data.get('proposal_id')
            vote_value = vote_data.get('vote')
            
            if not proposal_id or not vote_value:
                raise ValueError("proposal_id e vote sono campi obbligatori")
            
            with self._get_db() as (conn, cursor):
                # Verifica se l'utente ha già votato questa proposta
                cursor.execute(
                    "SELECT id, vote FROM graph_votes WHERE proposal_id = %s AND user_id = %s",
                    (proposal_id, user_id)
                )
                existing_vote = cursor.fetchone()
                
                if existing_vote:
                    # Aggiorna il voto esistente
                    cursor.execute(
                        """
                        UPDATE graph_votes 
                        SET vote = %s, comment = %s, date_created = %s 
                        WHERE id = %s
                        RETURNING id
                        """,
                        (vote_value, vote_data.get('comment', ''), now, existing_vote['id'])
                    )
                    result = cursor.fetchone()
                    if not result:
                        self.logger.error(f"Errore nell'aggiornamento del voto {existing_vote['id']}")
                        return None
                    vote_id = existing_vote['id']
                    vote_changed = existing_vote['vote'] != vote_value
                else:
                    # Inserisci nuovo voto
                    cursor.execute(
                        """
                        INSERT INTO graph_votes 
                        (id, proposal_id, user_id, vote, comment, date_created)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
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
                    result = cursor.fetchone()
                    if not result:
                        self.logger.error(f"Errore nell'inserimento del nuovo voto")
                        return None
                    vote_changed = True
                
                # Log activity
                if user_id:
                    try:
                        self.log_user_activity(
                            user_id=user_id,
                            action_type="vote_graph_proposal",
                            details=f"Voto '{vote_value}' per proposta {proposal_id}"
                        )
                    except Exception as log_e:
                        self.logger.warning(f"Failed to log graph vote activity: {log_e}")
                
                # Conta i voti per questa proposta
                cursor.execute(
                    """
                    SELECT 
                        COUNT(CASE WHEN vote = 'approve' THEN 1 END) as approve_count,
                        COUNT(CASE WHEN vote = 'reject' THEN 1 END) as reject_count
                    FROM graph_votes
                    WHERE proposal_id = %s
                    """, 
                    (proposal_id,)
                )
                vote_counts = cursor.fetchone()
                
                # Ottieni il numero di voti richiesti per la proposta
                cursor.execute(
                    "SELECT votes_required FROM graph_proposals WHERE id = %s",
                    (proposal_id,)
                )
                proposal = cursor.fetchone()
                votes_required = proposal['votes_required'] if proposal else 0
                
                # Verifica se la proposta deve essere approvata o respinta
                approve_count = vote_counts['approve_count']
                reject_count = vote_counts['reject_count']
                proposal_approved = False
                proposal_rejected = False
                
                # Se il numero di voti approva o rigetta supera la soglia richiesta
                if approve_count >= votes_required:
                    cursor.execute(
                        "UPDATE graph_proposals SET status = 'approved', date_modified = %s WHERE id = %s",
                        (now, proposal_id)
                    )
                    proposal_approved = True
                elif reject_count >= votes_required:
                    cursor.execute(
                        "UPDATE graph_proposals SET status = 'rejected', date_modified = %s WHERE id = %s",
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
        """Assegna un chunk a un utente in PostgreSQL."""
        success = False
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            
            with self._get_db() as (conn, cursor):
                # Verifica che il chunk esista
                cursor.execute("SELECT id FROM graph_chunks WHERE id = %s", (chunk_id,))
                if not cursor.fetchone():
                    self.logger.warning(f"Chunk {chunk_id} not found for assignment")
                    return False
                
                # Verifica che l'utente esista
                cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
                if not cursor.fetchone():
                    self.logger.warning(f"User {user_id} not found for assignment")
                    return False
                
                # Assegna il chunk
                cursor.execute(
                    """
                    UPDATE graph_chunks 
                    SET assigned_to = %s, date_modified = %s 
                    WHERE id = %s
                    RETURNING id
                    """,
                    (user_id, now, chunk_id)
                )
                
                result = cursor.fetchone()
                success = result is not None
                
                # Log activity
                if success and assigner_id:
                    try:
                        self.log_user_activity(
                            user_id=assigner_id,
                            action_type="assign_graph_chunk",
                            document_id=chunk_id,
                            details=f"Chunk assegnato all'utente {user_id}"
                        )
                    except Exception as log_e:
                        self.logger.warning(f"Failed to log chunk assignment activity: {log_e}")
                
                return success
        except Exception as e:
            self.logger.error(f"Error assigning chunk: {e}")
            self.logger.exception(e)
            return False

    def remove_chunk_assignment(self, chunk_id: str, user_id: str, remover_id: str = None) -> bool: # Added remover_id
        """Rimuove l'assegnazione di un chunk a un utente in PostgreSQL."""
        success = False # Initialize success
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            
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

    def delete_annotation(self, annotation_id: str, user_id: str = None) -> bool:
        """
        Elimina un'annotazione dal database.
        
        Args:
            annotation_id: ID dell'annotazione
            user_id: ID dell'utente che sta eliminando l'annotazione
            
        Returns:
            True se eliminata con successo, False altrimenti
        """
        try:
            with self._get_db() as (conn, cursor):
                # Prima ottieni l'ID del documento per il logging
                cursor.execute("SELECT doc_id FROM annotations WHERE id = %s", (annotation_id,))
                result = cursor.fetchone()
                if not result:
                    self.logger.warning(f"Annotazione {annotation_id} non trovata")
                    return False
                
                doc_id = result['doc_id']
                
                # Poi elimina l'annotazione
                cursor.execute("DELETE FROM annotations WHERE id = %s RETURNING id", (annotation_id,))
                deleted = cursor.fetchone() is not None
                
                if deleted:
                    self.logger.debug(f"Annotazione {annotation_id} eliminata con successo")
                    
                    # Log activity
                    if user_id:
                        self.log_user_activity(
                            user_id=user_id,
                            action_type="delete_annotation",
                            document_id=doc_id,
                            annotation_id=annotation_id
                        )
                    
                    return True
                else:
                    self.logger.warning(f"Nessuna annotazione trovata con ID {annotation_id}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Errore nell'eliminazione dell'annotazione {annotation_id}: {e}")
            self.logger.exception(e)
            return False

    def get_graph_chunks(self, status: str = None, assigned_to: str = None) -> List[Dict[str, Any]]:
        """
        Recupera i chunk del grafo con filtri opzionali.
        
        Args:
            status: Filtra per stato (pending, completed, etc.)
            assigned_to: Filtra per utente assegnato
            
        Returns:
            Lista di chunk che soddisfano i criteri
        """
        try:
            with self._get_db() as (conn, cursor):
                query = """
                    SELECT c.*, 
                        u_created.username as created_by_username,
                        u_assigned.username as assigned_to_username
                    FROM graph_chunks c
                    LEFT JOIN users u_created ON c.created_by = u_created.id
                    LEFT JOIN users u_assigned ON c.assigned_to = u_assigned.id
                    WHERE 1=1
                """
                params = []
                
                # Aggiungi filtri se specificati
                if status and status != 'all':
                    query += " AND c.status = %s"
                    params.append(status)
                
                if assigned_to:
                    if assigned_to == 'unassigned':
                        query += " AND c.assigned_to IS NULL"
                    else:
                        query += " AND c.assigned_to = %s"
                        params.append(assigned_to)
                
                # Ordina per data di modifica più recente
                query += " ORDER BY c.date_modified DESC NULLS LAST, c.date_created DESC"
                
                cursor.execute(query, tuple(params))
                chunks = []
                
                for row in cursor.fetchall():
                    chunk = dict(row)
                    
                    # Converti i campi JSONB in dizionari Python
                    if chunk.get('data') is not None:
                        chunk['data'] = chunk['data']  # psycopg2 gestisce automaticamente JSONB
                    else:
                        chunk['data'] = {}
                    
                    # Converti le date in formato ISO
                    if chunk.get('date_created'):
                        chunk['date_created'] = chunk['date_created'].isoformat()
                    if chunk.get('date_modified'):
                        chunk['date_modified'] = chunk['date_modified'].isoformat()
                    
                    chunks.append(chunk)
                
                return chunks
                
        except Exception as e:
            self.logger.error(f"Errore nel recupero dei graph chunks: {e}")
            self.logger.exception(e)
            return []

    def save_graph_chunk(self, chunk_data: Dict[str, Any], user_id: str = None, seed_node_id: str = None) -> Optional[str]:
        """
        Salva un chunk del grafo nel database.
        
        Args:
            chunk_data: Dati del chunk da salvare
            user_id: ID dell'utente che sta salvando il chunk
            seed_node_id: ID del nodo seed (opzionale)
            
        Returns:
            ID del chunk salvato se l'operazione ha successo, None altrimenti
        """
        try:
            now = datetime.datetime.now(datetime.timezone.utc)
            
            # Genera un ID se non presente
            chunk_id = chunk_data.get('id', f"chunk_{int(now.timestamp())}")
            
            # Prepara i dati per l'inserimento
            insert_data = {
                'id': chunk_id,
                'title': chunk_data.get('title'),
                'description': chunk_data.get('description'),
                'chunk_type': chunk_data.get('chunk_type', 'subgraph'),
                'data': json.dumps(chunk_data.get('data', {})),  # Converti in JSON
                'status': chunk_data.get('status', 'pending'),
                'date_created': now,
                'date_modified': now,
                'created_by': user_id,
                'assigned_to': chunk_data.get('assigned_to'),
                'seed_node_id': seed_node_id
            }
            
            with self._get_db() as (conn, cursor):
                # Inserisci o aggiorna il chunk
                cursor.execute("""
                    INSERT INTO graph_chunks 
                    (id, title, description, chunk_type, data, status, date_created, date_modified, created_by, assigned_to, seed_node_id)
                    VALUES (%(id)s, %(title)s, %(description)s, %(chunk_type)s, %(data)s::jsonb, %(status)s, 
                            %(date_created)s, %(date_modified)s, %(created_by)s, %(assigned_to)s, %(seed_node_id)s)
                    ON CONFLICT (id) DO UPDATE SET
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        chunk_type = EXCLUDED.chunk_type,
                        data = EXCLUDED.data,
                        status = EXCLUDED.status,
                        date_modified = EXCLUDED.date_modified,
                        assigned_to = EXCLUDED.assigned_to,
                        seed_node_id = EXCLUDED.seed_node_id
                    RETURNING id
                """, insert_data)
                
                result = cursor.fetchone()
                
                if result:
                    self.logger.info(f"Graph chunk {chunk_id} salvato con successo")
                    
                    # Log activity
                    if user_id:
                        self.log_user_activity(
                            user_id=user_id,
                            action_type="save_graph_chunk",
                            details=f"Chunk {chunk_id} salvato"
                        )
                    
                    return result['id']
                else:
                    self.logger.error(f"Errore nel salvataggio del graph chunk {chunk_id}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Errore nel salvataggio del graph chunk: {e}")
            self.logger.exception(e)
            return None

    def check_chunk_exists_for_seed(self, seed_node_id: str) -> bool:
        """
        Verifica se esiste già un chunk per un dato nodo seed.
        
        Args:
            seed_node_id: ID del nodo seed da verificare
            
        Returns:
            True se esiste già un chunk per questo seed, False altrimenti
        """
        try:
            with self._get_db() as (conn, cursor):
                cursor.execute(
                    "SELECT EXISTS(SELECT 1 FROM graph_chunks WHERE seed_node_id = %s)",
                    (seed_node_id,)
                )
                result = cursor.fetchone()
                exists = result[0] if result else False
                
                if exists:
                    self.logger.debug(f"Trovato chunk esistente per seed node {seed_node_id}")
                else:
                    self.logger.debug(f"Nessun chunk esistente per seed node {seed_node_id}")
                    
                return exists
                
        except Exception as e:
            self.logger.error(f"Errore nella verifica dell'esistenza del chunk per seed {seed_node_id}: {e}")
            self.logger.exception(e)
            return False

    def get_graph_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera un singolo chunk del grafo per ID.
        
        Args:
            chunk_id: ID del chunk da recuperare
            
        Returns:
            Dizionario con i dati del chunk se trovato, None altrimenti
        """
        try:
            with self._get_db() as (conn, cursor):
                query = """
                    SELECT c.*, 
                        u_created.username as created_by_username,
                        u_assigned.username as assigned_to_username
                    FROM graph_chunks c
                    LEFT JOIN users u_created ON c.created_by = u_created.id
                    LEFT JOIN users u_assigned ON c.assigned_to = u_assigned.id
                    WHERE c.id = %s
                """
                
                cursor.execute(query, (chunk_id,))
                row = cursor.fetchone()
                
                if not row:
                    self.logger.warning(f"Chunk {chunk_id} non trovato")
                    return None
                
                chunk = dict(row)
                
                # Converti i campi JSONB in dizionari Python
                if chunk.get('data') is not None:
                    chunk['data'] = chunk['data']  # psycopg2 gestisce automaticamente JSONB
                else:
                    chunk['data'] = {}
                
                # Converti le date in formato ISO
                if chunk.get('date_created'):
                    chunk['date_created'] = chunk['date_created'].isoformat()
                if chunk.get('date_modified'):
                    chunk['date_modified'] = chunk['date_modified'].isoformat()
                
                self.logger.debug(f"Chunk {chunk_id} recuperato con successo")
                return chunk
                
        except Exception as e:
            self.logger.error(f"Errore nel recupero del chunk {chunk_id}: {e}")
            self.logger.exception(e)
            return None

    def get_graph_proposals(self, chunk_id: str) -> list:
        """
        Restituisce tutte le proposte di modifica per un chunk, inclusi i voti.
        """
        try:
            with self._get_db() as (conn, cursor):
                # Recupera tutte le proposte per il chunk
                cursor.execute(
                    """
                    SELECT * FROM graph_proposals
                    WHERE chunk_id = %s
                    ORDER BY date_created ASC
                    """,
                    (chunk_id,)
                )
                proposals = []
                for row in cursor.fetchall():
                    proposal = dict(row)
                    # Carica i voti associati a questa proposta
                    cursor.execute(
                        """
                        SELECT v.*, u.username
                        FROM graph_votes v
                        LEFT JOIN users u ON v.user_id = u.id
                        WHERE v.proposal_id = %s
                        ORDER BY v.date_created ASC
                        """,
                        (proposal['id'],)
                    )
                    proposal['votes'] = [dict(vote) for vote in cursor.fetchall()]
                    # Decodifica i campi JSONB
                    for field in ['original_data', 'proposed_data']:
                        if proposal.get(field) is not None:
                            proposal[field] = proposal[field]
                    # Formatta le date
                    for field in ['date_created', 'date_modified']:
                        if proposal.get(field):
                            proposal[field] = proposal[field].isoformat()
                    proposals.append(proposal)
                return proposals
        except Exception as e:
            self.logger.error(f"Errore nel recupero delle proposte per chunk {chunk_id}: {e}")
            self.logger.exception(e)
            return []