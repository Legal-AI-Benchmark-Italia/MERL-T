"""
Gestore di configurazione centralizzato per MERL-T.
Legge il file config.yaml e fornisce l'accesso alle configurazioni a tutti i componenti dell'applicazione.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Configurazione logging
logger = logging.getLogger("MERL-T.ConfigManager")

class ConfigManager:
    """
    Gestore di configurazione centralizzato.
    Carica e fornisce l'accesso alle configurazioni da config.yaml.
    Implementa Singleton per garantire un'unica istanza condivisa.
    """
    _instance = None
    _config = {}
    
    def __new__(cls):
        """Implementazione del pattern Singleton."""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Inizializza il gestore di configurazione."""
        if self._initialized:
            return
            
        self._config = {}
        self._config_file = None
        self._initialized = True
    
    def load_from_file(self, config_file: str = None) -> bool:
        """
        Carica la configurazione da un file YAML.
        
        Args:
            config_file: Percorso del file di configurazione YAML
            
        Returns:
            True se il caricamento è avvenuto con successo, False altrimenti
        """
        try:
            # Se non è specificato un file, cerca nei percorsi predefiniti
            if config_file is None:
                # Percorsi candidati in ordine di priorità
                candidates = [
                    # File specificato tramite variabile d'ambiente
                    os.environ.get("MERLT_CONFIG"),
                    # Directory corrente
                    "config.yaml",
                    # Directory config nella cartella del progetto
                    str(Path(__file__).resolve().parent / "config.yaml"),
                    # Directory root del progetto
                    str(Path(__file__).resolve().parent.parent.parent / "config" / "config.yaml"),
                ]
                
                # Cerca il primo file esistente
                for candidate in candidates:
                    if candidate and os.path.exists(candidate):
                        config_file = candidate
                        break
            
            if not config_file or not os.path.exists(config_file):
                logger.error(f"File di configurazione non trovato: {config_file}")
                return False
            
            logger.info(f"Caricamento configurazione da {config_file}")
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            
            self._config_file = config_file
            
            # Sostituisci le variabili d'ambiente
            self._substitute_env_variables()
            
            # Verifica la validità della configurazione
            if not self._validate_config():
                logger.warning("La configurazione caricata contiene errori")
                
            return True
        except Exception as e:
            logger.error(f"Errore nel caricamento della configurazione: {e}")
            return False
    
    def _substitute_env_variables(self):
        """Sostituisce le variabili d'ambiente nella configurazione."""
        def _substitute_in_value(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                env_value = os.environ.get(env_var)
                if env_value:
                    return env_value
                logger.warning(f"Variabile d'ambiente {env_var} non trovata")
            return value
        
        def _process_dict(d):
            for key, value in d.items():
                if isinstance(value, dict):
                    _process_dict(value)
                elif isinstance(value, list):
                    d[key] = [_substitute_in_value(item) if isinstance(item, str) else item for item in value]
                else:
                    d[key] = _substitute_in_value(value)
        
        _process_dict(self._config)
    
    def _validate_config(self) -> bool:
        """
        Verifica la validità della configurazione.
        
        Returns:
            True se la configurazione è valida, False altrimenti
        """
        # Verifica sezioni obbligatorie
        required_sections = ["general", "models", "entities", "annotation"]
        for section in required_sections:
            if section not in self._config:
                logger.error(f"Sezione '{section}' mancante nella configurazione")
                return False
        
        # Verifica validità percorsi
        path_keys = [
            "general.cache_dir", 
            "models.rule_based.patterns_dir",
            "normalization.canonical_forms_file",
            "normalization.abbreviations_file",
            "training.standard.train_data_dir",
            "training.standard.output_dir",
            "training.reinforcement.feedback_dir",
            "training.reinforcement.output_dir",
            "annotation.data_dir",
            "knowledge_graph.data_paths.patterns_dir",
            "knowledge_graph.data_paths.exports_dir",
            "knowledge_graph.data_paths.imports_dir",
            "pdf_chunker.input_folder",
            "pdf_chunker.output_folder",
            "pdf_chunker.tracking.progress_file",
            "pdf_chunker.tracking.log_file"
        ]
        
        for key in path_keys:
            value = self.get(key)
            if value:
                # Verifica solo l'esistenza della directory parent
                parent_dir = os.path.dirname(value)
                if not os.path.exists(parent_dir):
                    logger.warning(f"Directory '{parent_dir}' per '{key}' non esistente")
        
        return True
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Ottiene un valore dalla configurazione usando una notazione a punti.
        
        Args:
            key: Chiave in notazione a punti (es. "general.debug")
            default: Valore predefinito se la chiave non esiste
            
        Returns:
            Il valore della chiave se esiste, altrimenti il valore predefinito
        """
        parts = key.split('.')
        value = self._config
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
        
        return value
    
    def get_full_config(self) -> Dict[str, Any]:
        """
        Ottiene la configurazione completa.
        
        Returns:
            Dizionario con la configurazione completa
        """
        return self._config
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Ottiene una sezione della configurazione.
        
        Args:
            section: Nome della sezione
            
        Returns:
            Dizionario con la sezione richiesta, o dizionario vuoto se la sezione non esiste
        """
        return self._config.get(section, {})
    
    def set(self, key: str, value: Any) -> None:
        """
        Imposta un valore nella configurazione.
        
        Args:
            key: Chiave in notazione a punti (es. "general.debug")
            value: Valore da impostare
        """
        parts = key.split('.')
        config = self._config
        
        for part in parts[:-1]:
            if part not in config:
                config[part] = {}
            config = config[part]
        
        config[parts[-1]] = value
    
    def save(self, file_path: Optional[str] = None) -> bool:
        """
        Salva la configurazione in un file YAML.
        
        Args:
            file_path: Percorso del file, se None usa il file di origine
            
        Returns:
            True se il salvataggio è avvenuto con successo, False altrimenti
        """
        try:
            if file_path is None:
                file_path = self._config_file
            
            if not file_path:
                logger.error("Nessun file di configurazione specificato per il salvataggio")
                return False
            
            # Assicura che la directory esista
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"Configurazione salvata in {file_path}")
            return True
        except Exception as e:
            logger.error(f"Errore nel salvataggio della configurazione: {e}")
            return False
    
    def get_db_path(self, db_type: str) -> str:
        """
        Ottiene il percorso di un database specifico.
        
        Args:
            db_type: Tipo di database ('entities', 'annotations')
            
        Returns:
            Percorso del database
        """
        if db_type == 'entities':
            return self.get('database.entities_db')
        elif db_type == 'annotations':
            return self.get('database.annotations_db')
        else:
            logger.warning(f"Tipo di database sconosciuto: {db_type}")
            return None
    
    def get_model_path(self, model_type: str = 'transformer') -> str:
        """
        Ottiene il percorso del modello.
        
        Args:
            model_type: Tipo di modello ('transformer', 'transformer_feedback')
            
        Returns:
            Percorso del modello
        """
        if model_type == 'transformer':
            return self.get('models.transformer.dir_path')
        elif model_type == 'transformer_feedback':
            return self.get('training.reinforcement.output_dir')
        else:
            logger.warning(f"Tipo di modello sconosciuto: {model_type}")
            return None
    
    def get_feedback_config(self) -> Dict[str, Any]:
        """
        Ottiene la configurazione per il sistema di feedback.
        
        Returns:
            Dizionario con la configurazione del feedback
        """
        return {
            'enabled': self.get('annotation.feedback.enable', True),
            'storage_dir': self.get('annotation.feedback.storage_dir'),
            'auto_train_threshold': self.get('annotation.feedback.auto_train_threshold', 10)
        }
    
    def get_training_config(self, type: str = 'standard') -> Dict[str, Any]:
        """
        Ottiene la configurazione per l'addestramento.
        
        Args:
            type: Tipo di addestramento ('standard', 'reinforcement')
            
        Returns:
            Dizionario con la configurazione dell'addestramento
        """
        if type == 'standard':
            return self.get_section('training').get('standard', {})
        elif type == 'reinforcement':
            return self.get_section('training').get('reinforcement', {})
        else:
            logger.warning(f"Tipo di addestramento sconosciuto: {type}")
            return {}
    
    def get_knowledge_graph_config(self) -> Dict[str, Any]:
        """
        Ottiene la configurazione per il knowledge graph (Neo4j).
        
        Returns:
            Dizionario con la configurazione del knowledge graph
        """
        kg_config = self.get_section('knowledge_graph')
        if not kg_config:
            logger.warning("Configurazione knowledge graph non trovata")
            return {
                'enable': False,
                'connection': {
                    'uri': "bolt://localhost:7687",
                    'user': "neo4j",
                    'password': "neo4j",
                    'database': "neo4j"
                }
            }
        return kg_config
    
    def get_neo4j_connection_params(self) -> Dict[str, str]:
        """
        Ottiene i parametri di connessione per Neo4j.
        
        Returns:
            Dizionario con i parametri di connessione
        """
        connection = self.get('knowledge_graph.connection', {})
        return {
            'uri': connection.get('uri', "bolt://localhost:7687"),
            'user': connection.get('user', "neo4j"),
            'password': connection.get('password', "neo4j"),
            'database': connection.get('database', "neo4j")
        }
    
    def get_pdf_chunker_config(self) -> Dict[str, Any]:
        """
        Ottiene la configurazione per il PDF Chunker.
        
        Returns:
            Dizionario con la configurazione del PDF Chunker
        """
        chunker_config = self.get_section('pdf_chunker')
        if not chunker_config:
            logger.warning("Configurazione PDF Chunker non trovata")
            return {
                'input_folder': "input",
                'output_folder': "output",
                'chunk_size': {
                    'min': 200,
                    'max': 1500,
                    'overlap': 50
                },
                'processing': {
                    'use_sliding_window': True,
                    'max_workers': 0,
                    'cpu_limit': 80
                },
                'language': "it"
            }
        return chunker_config
    
    def get_pdf_chunker_paths(self) -> Dict[str, str]:
        """
        Ottiene i percorsi per il PDF Chunker.
        
        Returns:
            Dizionario con i percorsi del PDF Chunker
        """
        return {
            'input': self.get('pdf_chunker.input_folder'),
            'output': self.get('pdf_chunker.output_folder'),
            'progress': self.get('pdf_chunker.tracking.progress_file'),
            'log': self.get('pdf_chunker.tracking.log_file')
        }
    
    @property
    def config_file(self) -> str:
        """
        Ottiene il percorso del file di configurazione.
        
        Returns:
            Percorso del file di configurazione
        """
        return self._config_file

# Istanza singleton del gestore di configurazione
_config_manager = None

def get_config_manager() -> ConfigManager:
    """
    Ottiene l'istanza del gestore di configurazione.
    
    Returns:
        Istanza del gestore di configurazione
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
        # Carica la configurazione dal file predefinito
        _config_manager.load_from_file()
    return _config_manager 