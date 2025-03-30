"""
Modulo di gestione della configurazione per NER-Giuridico.
Carica e gestisce le configurazioni dal file YAML.
"""

import os
import yaml
from typing import Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class Config:
    """Classe per la gestione della configurazione del sistema NER-Giuridico."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Inizializza l'oggetto di configurazione.
        
        Args:
            config_path: Percorso al file di configurazione YAML. Se None, usa il percorso predefinito.
        """
        if config_path is None:
            # Percorso predefinito relativo alla directory del progetto
            base_dir = Path(__file__).parent.parent
            config_path = os.path.join(base_dir, "config", "config.yaml")
        
        self.config_path = config_path
        self.config_data = self._load_config()
        
        # Configura il logging
        self._setup_logging()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Carica la configurazione dal file YAML.
        
        Returns:
            Dizionario con i dati di configurazione.
        
        Raises:
            FileNotFoundError: Se il file di configurazione non esiste.
            yaml.YAMLError: Se il file YAML non è valido.
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as config_file:
                config_data = yaml.safe_load(config_file)
                logger.info(f"Configurazione caricata da {self.config_path}")
                return config_data
        except FileNotFoundError:
            logger.error(f"File di configurazione non trovato: {self.config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Errore nel parsing del file YAML: {e}")
            raise
    
    def _setup_logging(self) -> None:
        """Configura il sistema di logging in base alle impostazioni nel file di configurazione."""
        log_level = self.get("general.log_level", "INFO")
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            numeric_level = logging.INFO
        
        logging.basicConfig(
            level=numeric_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Ottiene un valore di configurazione dal percorso della chiave.
        
        Args:
            key_path: Percorso della chiave separato da punti (es. "models.transformer.model_name").
            default: Valore predefinito da restituire se la chiave non esiste.
        
        Returns:
            Il valore di configurazione o il valore predefinito se la chiave non esiste.
        """
        keys = key_path.split('.')
        value = self.config_data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Imposta un valore di configurazione al percorso della chiave specificato.
        
        Args:
            key_path: Percorso della chiave separato da punti (es. "models.transformer.model_name").
            value: Valore da impostare.
        """
        keys = key_path.split('.')
        config = self.config_data
        
        # Naviga attraverso la gerarchia delle chiavi
        for i, key in enumerate(keys[:-1]):
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # Imposta il valore
        config[keys[-1]] = value
    
    def save(self, config_path: Optional[str] = None) -> None:
        """
        Salva la configurazione corrente su file.
        
        Args:
            config_path: Percorso dove salvare il file. Se None, usa il percorso corrente.
        """
        save_path = config_path or self.config_path
        
        try:
            with open(save_path, 'w', encoding='utf-8') as config_file:
                yaml.dump(self.config_data, config_file, default_flow_style=False, allow_unicode=True)
                logger.info(f"Configurazione salvata in {save_path}")
        except Exception as e:
            logger.error(f"Errore nel salvataggio della configurazione: {e}")
            raise

# Istanza singleton della configurazione
config = Config()
