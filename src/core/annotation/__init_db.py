#!/usr/bin/env python3
"""
Script per inizializzare il database con un utente admin predefinito.
Migliorato per garantire la coerenza del percorso del database.
"""

import os
import sys
import argparse
import datetime
import logging
import hashlib
import sqlite3
import uuid
import configparser

# Configurazione logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('db_init')

def create_admin_user(db_path, username='admin', password='admin', full_name='Amministratore'):
    """
    Crea un utente amministratore nel database.
    
    Args:
        db_path: Percorso del database SQLite
        username: Nome utente amministratore (default: admin)
        password: Password amministratore (default: admin)
        full_name: Nome completo (default: Amministratore)
    
    Returns:
        True se creato con successo, False altrimenti
    """
    try:
        logger.info(f"Creazione utente amministratore '{username}' nel database: {db_path}")
        
        # Assicurati che la directory del database esista
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logger.info(f"Creata directory per il database: {db_dir}")
        
        # Hash della password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Dati utente
        user_id = f"user_{str(uuid.uuid4())}"  # Changed to UUID
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
        conn.commit()
        
        # Controlla se l'utente esiste già
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            logger.warning(f"L'utente '{username}' esiste già. Aggiornamento password.")
            cursor.execute(
                "UPDATE users SET password = ?, full_name = ?, role = 'admin', active = 1 WHERE username = ?",
                (hashed_password, full_name, username)
            )
        else:
            # Inserisci utente admin
            cursor.execute(
                """
                INSERT INTO users 
                (id, username, password, full_name, role, active, date_created)
                VALUES (?, ?, ?, ?, 'admin', 1, ?)
                """,
                (user_id, username, hashed_password, full_name, now)
            )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Utente amministratore '{username}' creato/aggiornato con successo.")
        logger.info(f"Username: {username}")
        logger.info(f"Password: {password}")
        logger.info(f"IMPORTANTE: Cambia questa password al primo accesso!")
        
        return True
    except Exception as e:
        logger.error(f"Errore nella creazione dell'utente amministratore: {e}")
        logger.exception(e)
        return False

def create_demo_users(db_path):
    """
    Crea utenti di esempio per testing.
    
    Args:
        db_path: Percorso del database SQLite
    
    Returns:
        True se creati con successo, False altrimenti
    """
    try:
        # Utenti di esempio
        demo_users = [
            {
                'username': 'annotatore1',
                'password': 'password1',
                'full_name': 'Mario Rossi',
                'role': 'annotator',
                'email': 'mario@example.com'
            },
            {
                'username': 'annotatore2',
                'password': 'password2',
                'full_name': 'Giulia Bianchi',
                'role': 'annotator',
                'email': 'giulia@example.com'
            },
            {
                'username': 'supervisore',
                'password': 'password3',
                'full_name': 'Paolo Verdi',
                'role': 'admin',
                'email': 'paolo@example.com'
            }
        ]
        
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
            role TEXT DEFAULT 'annotator',
            email TEXT,
            active INTEGER DEFAULT 1,
            date_created TEXT,
            date_last_login TEXT
        )
        ''')
        conn.commit()
        
        # Inserisci gli utenti di esempio
        now = datetime.datetime.now().isoformat()
        
        for user in demo_users:
            # Hash della password
            hashed_password = hashlib.sha256(user['password'].encode()).hexdigest()
            
            # ID utente
            user_id = f"user_{str(uuid.uuid4())}"  # Changed to UUID
            
            # Controlla se l'utente esiste già
            cursor.execute("SELECT id FROM users WHERE username = ?", (user['username'],))
            existing_user = cursor.fetchone()
            
            if existing_user:
                logger.info(f"L'utente '{user['username']}' esiste già. Salto.")
                continue
            
            # Inserisci utente
            cursor.execute(
                """
                INSERT INTO users 
                (id, username, password, full_name, role, email, active, date_created)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (user_id, user['username'], hashed_password, user['full_name'], 
                 user['role'], user['email'], now)
            )
            logger.info(f"Utente '{user['username']}' creato con successo.")
        
        conn.commit()
        conn.close()
        
        logger.info("Utenti di esempio creati con successo.")
        return True
    except Exception as e:
        logger.error(f"Errore nella creazione degli utenti di esempio: {e}")
        logger.exception(e)
        return False

def get_db_path_from_config(config_path=None):
    """
    Ottiene il percorso del database dalla configurazione.
    
    Args:
        config_path: Percorso del file di configurazione (default: config.ini)
        
    Returns:
        Percorso del database
    """
    if not config_path:
        config_path = os.environ.get('NER_CONFIG', 'config.ini')
    
    # Percorso predefinito
    default_db_path = os.path.join('data', 'annotations.db')
    
    # Se il file di configurazione esiste, leggi il percorso del database
    if os.path.exists(config_path):
        try:
            config = configparser.ConfigParser()
            config.read(config_path)
            if 'Database' in config and 'path' in config['Database']:
                db_path = config['Database']['path']
                logger.info(f"Percorso database dalla configurazione: {db_path}")
                return db_path
        except Exception as e:
            logger.warning(f"Errore nella lettura della configurazione: {e}")
    
    logger.info(f"Usando percorso database predefinito: {default_db_path}")
    return default_db_path

def main():
    parser = argparse.ArgumentParser(description='Inizializza il database con un utente admin')
    parser.add_argument('--config', type=str, 
                        help='Percorso del file di configurazione (default: usa NER_CONFIG o config.ini)')
    parser.add_argument('--db', type=str,
                        help='Percorso del database SQLite (override della configurazione)')
    parser.add_argument('--username', type=str, default='admin',
                        help='Nome utente amministratore (default: admin)')
    parser.add_argument('--password', type=str, default='admin',
                        help='Password amministratore (default: admin)')
    parser.add_argument('--demo', action='store_true',
                        help='Crea anche utenti di esempio per testing')
    
    args = parser.parse_args()
    
    # Ottieni il percorso del database
    db_path = args.db if args.db else get_db_path_from_config(args.config)
    
    # Assicurati che la directory del database esista
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
    
    # Crea utente admin
    success = create_admin_user(db_path, args.username, args.password)
    
    # Crea utenti demo se richiesto
    if success and args.demo:
        create_demo_users(db_path)

if __name__ == '__main__':
    main()