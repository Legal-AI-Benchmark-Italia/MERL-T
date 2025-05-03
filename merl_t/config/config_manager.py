"""
Gestore di configurazione centralizzato per MERL-T.

Carica il file config.yaml e fornisce l'accesso alle configurazioni a tutti i componenti
del sistema con supporto per sostituzione di variabili d'ambiente e validazione.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Configurazione logging
from loguru import logger

class ConfigManager:
    """
    Gestore di configurazione centralizzato.
    
    Implementa il pattern Singleton per garantire un'unica istanza condivisa.
    Carica e fornisce accesso alle configurazioni da config.yaml.
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
        if getattr(self, "_initialized", False):
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
                    # Directory config nel package
                    str(Path(__file__).resolve().parent / "config.yaml"),
                    # Directory config nella cartella del modulo
                    str(Path(__file__).resolve().parent / "defaults.yaml"),
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
        # Verifica le sezioni obbligatorie in base alla nuova struttura
        required_sections = ["general", "mcp", "a2a", "ner"]
        for section in required_sections:
            if section not in self._config:
                logger.warning(f"Sezione '{section}' mancante nella configurazione")
        
        # La presenza di errori non è fatale, potremmo usare configurazioni default
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
    
    # --- Getters specifici per i vari componenti ---
    
    def get_mcp_config(self) -> Dict[str, Any]:
        """
        Ottiene la configurazione per il protocollo MCP.
        
        Returns:
            Configurazione MCP
        """
        return self.get_section("mcp")
    
    def get_a2a_config(self) -> Dict[str, Any]:
        """
        Ottiene la configurazione per il protocollo A2A.
        
        Returns:
            Configurazione A2A
        """
        return self.get_section("a2a")
    
    def get_ner_config(self) -> Dict[str, Any]:
        """
        Ottiene la configurazione per il sistema NER.
        
        Returns:
            Configurazione NER
        """
        return self.get_section("ner")
    
    def get_model_path(self, model_name: str) -> Optional[str]:
        """
        Ottiene il percorso di un modello specifico.
        
        Args:
            model_name: Nome del modello
            
        Returns:
            Percorso del modello o None se non trovato
        """
        models_dir = self.get("general.models_dir", "./models")
        model_config = self.get(f"models.{model_name}")
        
        if not model_config:
            return None
            
        if "path" in model_config:
            return model_config["path"]
        
        # Costruisci il percorso basandoti sulla convenzione
        return os.path.join(models_dir, model_name)
    
    def get_server_config(self, server_type: str) -> Dict[str, Any]:
        """
        Ottiene la configurazione per un tipo di server MCP.
        
        Args:
            server_type: Tipo di server (es. "ner", "kg", "vdb")
            
        Returns:
            Configurazione del server
        """
        return self.get(f"mcp.servers.{server_type}", {})
    
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