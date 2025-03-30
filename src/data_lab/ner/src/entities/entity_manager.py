"""
Modulo per la gestione dinamica delle entità nel sistema NER-Giuridico.
Implementa il pattern Observer per notificare i componenti delle modifiche.
"""

import logging
import json
import os
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Union, Protocol


class EntityObserver(Protocol):
    """Protocollo per gli osservatori delle modifiche alle entità"""
    def entity_added(self, name: str, definition: Dict[str, Any]) -> None:
        """Chiamato quando viene aggiunta un'entità"""
        pass
        
    def entity_updated(self, name: str, definition: Dict[str, Any]) -> None:
        """Chiamato quando viene aggiornata un'entità"""
        pass
        
    def entity_removed(self, name: str) -> None:
        """Chiamato quando viene rimossa un'entità"""
        pass


class DynamicEntityManager:
    """
    Gestore dinamico dei tipi di entità, consentendo l'aggiunta, modifica
    e rimozione delle entità durante l'esecuzione.
    """
    
    def __init__(self, entities_file: Optional[str] = None):
        """
        Inizializza il gestore delle entità.
        
        Args:
            entities_file: Percorso al file JSON contenente le definizioni delle entità
        """
        self.logger = logging.getLogger("NER-Giuridico.DynamicEntityManager")
        
        # Inizializza le strutture dati
        self.entity_types = {}  # nome -> attributi
        self.entity_categories = {
            "normative": set(),
            "jurisprudence": set(),
            "concepts": set(),
            "custom": set()
        }
        
        # Lista degli osservatori delle modifiche
        self.observers: List[EntityObserver] = []
        
        # Carica le entità predefinite
        self._load_default_entities()
        
        # Carica le entità dal file se specificato
        if entities_file:
            self.load_entities(entities_file)
            
    def add_observer(self, observer: EntityObserver) -> None:
        """
        Aggiunge un osservatore delle modifiche alle entità.
        
        Args:
            observer: Oggetto che implementa l'interfaccia EntityObserver
        """
        self.observers.append(observer)
        
    def remove_observer(self, observer: EntityObserver) -> None:
        """
        Rimuove un osservatore.
        
        Args:
            observer: Osservatore da rimuovere
        """
        if observer in self.observers:
            self.observers.remove(observer)
            
    def _notify_entity_added(self, name: str, definition: Dict[str, Any]) -> None:
        """
        Notifica gli osservatori dell'aggiunta di un'entità.
        
        Args:
            name: Nome dell'entità aggiunta
            definition: Definizione dell'entità
        """
        for observer in self.observers:
            observer.entity_added(name, definition)
            
    def _notify_entity_updated(self, name: str, definition: Dict[str, Any]) -> None:
        """
        Notifica gli osservatori dell'aggiornamento di un'entità.
        
        Args:
            name: Nome dell'entità aggiornata
            definition: Nuova definizione dell'entità
        """
        for observer in self.observers:
            observer.entity_updated(name, definition)
            
    def _notify_entity_removed(self, name: str) -> None:
        """
        Notifica gli osservatori della rimozione di un'entità.
        
        Args:
            name: Nome dell'entità rimossa
        """
        for observer in self.observers:
            observer.entity_removed(name)
            
    def _load_default_entities(self) -> None:
        """Carica le entità predefinite nel sistema."""
        # Entità normative
        self.add_entity_type(
            name="ARTICOLO_CODICE",
            display_name="Articolo di Codice",
            category="normative",
            color="#FFA39E",
            metadata_schema={"codice": "string", "articolo": "string"}
        )
        self.add_entity_type(
            name="LEGGE",
            display_name="Legge",
            category="normative",
            color="#D4380D",
            metadata_schema={"numero": "string", "anno": "string", "data": "string"}
        )
        self.add_entity_type(
            name="DECRETO",
            display_name="Decreto",
            category="normative",
            color="#FFC069",
            metadata_schema={"tipo_decreto": "string", "numero": "string", "anno": "string", "data": "string"}
        )
        self.add_entity_type(
            name="REGOLAMENTO_UE",
            display_name="Regolamento UE",
            category="normative",
            color="#AD8B00",
            metadata_schema={"tipo": "string", "numero": "string", "anno": "string", "nome_comune": "string"}
        )
        
        # Entità giurisprudenziali
        self.add_entity_type(
            name="SENTENZA",
            display_name="Sentenza",
            category="jurisprudence",
            color="#D3F261",
            metadata_schema={"autorità": "string", "località": "string", "sezione": "string", "numero": "string", "anno": "string", "data": "string"}
        )
        self.add_entity_type(
            name="ORDINANZA",
            display_name="Ordinanza",
            category="jurisprudence",
            color="#389E0D",
            metadata_schema={"autorità": "string", "località": "string", "sezione": "string", "numero": "string", "anno": "string", "data": "string"}
        )
        
        # Concetti giuridici
        self.add_entity_type(
            name="CONCETTO_GIURIDICO",
            display_name="Concetto Giuridico",
            category="concepts",
            color="#5CDBD3",
            metadata_schema={"categoria": "string", "definizione": "string"}
        )
        
    def add_entity_type(self, name: str, display_name: str, category: str, 
                        color: str, metadata_schema: Dict[str, str], patterns: List[str] = None) -> bool:
        """
        Aggiunge un nuovo tipo di entità al sistema.
        
        Args:
            name: Nome identificativo dell'entità (in maiuscolo)
            display_name: Nome visualizzato dell'entità
            category: Categoria dell'entità ("normative", "jurisprudence", "concepts" o "custom")
            color: Colore dell'entità in formato esadecimale (#RRGGBB)
            metadata_schema: Schema dei metadati dell'entità
            patterns: Lista di pattern regex per il riconoscimento (opzionale)
            
        Returns:
            True se l'aggiunta è avvenuta con successo, False altrimenti
        """
        try:
            # Verifica che il nome sia in maiuscolo e non contenga spazi
            if not name.isupper() or ' ' in name:
                self.logger.error(f"Nome entità non valido: {name}. Deve essere in maiuscolo e senza spazi.")
                return False
                
            # Verifica che la categoria sia valida
            if category not in self.entity_categories:
                self.logger.error(f"Categoria non valida: {category}")
                return False
                
            # Verifica che il nome non sia già in uso
            if name in self.entity_types:
                self.logger.warning(f"L'entità {name} esiste già. Aggiornamento in corso...")
            
            # Aggiungi l'entità
            entity_definition = {
                "display_name": display_name,
                "category": category,
                "color": color,
                "metadata_schema": metadata_schema
            }
            
            # Aggiungi i pattern se specificati
            if patterns:
                entity_definition["patterns"] = patterns
                
            self.entity_types[name] = entity_definition
            
            # Aggiungi alle categorie
            self.entity_categories[category].add(name)
            
            self.logger.info(f"Entità {name} aggiunta con successo nella categoria {category}")
            
            # Notifica gli osservatori
            self._notify_entity_added(name, entity_definition)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Errore nell'aggiunta dell'entità {name}: {str(e)}")
            return False
    
    def remove_entity_type(self, name: str) -> bool:
        """
        Rimuove un tipo di entità dal sistema.
        
        Args:
            name: Nome identificativo dell'entità
            
        Returns:
            True se la rimozione è avvenuta con successo, False altrimenti
        """
        try:
            if name not in self.entity_types:
                self.logger.warning(f"L'entità {name} non esiste.")
                return False
                
            # Rimuovi dalle categorie
            category = self.entity_types[name]["category"]
            if name in self.entity_categories[category]:
                self.entity_categories[category].remove(name)
                
            # Rimuovi dall'elenco principale
            del self.entity_types[name]
            
            self.logger.info(f"Entità {name} rimossa con successo")
            
            # Notifica gli osservatori
            self._notify_entity_removed(name)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Errore nella rimozione dell'entità {name}: {str(e)}")
            return False
    
    def update_entity_type(self, name: str, display_name: Optional[str] = None, 
                          color: Optional[str] = None, 
                          metadata_schema: Optional[Dict[str, str]] = None,
                          patterns: Optional[List[str]] = None) -> bool:
        """
        Aggiorna un tipo di entità esistente.
        
        Args:
            name: Nome identificativo dell'entità
            display_name: Nuovo nome visualizzato (opzionale)
            color: Nuovo colore (opzionale)
            metadata_schema: Nuovo schema dei metadati (opzionale)
            patterns: Nuovi pattern regex (opzionale)
            
        Returns:
            True se l'aggiornamento è avvenuto con successo, False altrimenti
        """
        try:
            if name not in self.entity_types:
                self.logger.error(f"L'entità {name} non esiste.")
                return False
                
            # Crea una copia dell'entità esistente
            updated_definition = self.entity_types[name].copy()
                
            # Aggiorna i campi specificati
            if display_name:
                updated_definition["display_name"] = display_name
                
            if color:
                updated_definition["color"] = color
                
            if metadata_schema:
                updated_definition["metadata_schema"] = metadata_schema
                
            if patterns:
                updated_definition["patterns"] = patterns
                
            # Aggiorna l'entità
            self.entity_types[name] = updated_definition
                
            self.logger.info(f"Entità {name} aggiornata con successo")
            
            # Notifica gli osservatori
            self._notify_entity_updated(name, updated_definition)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Errore nell'aggiornamento dell'entità {name}: {str(e)}")
            return False
    
    def get_entity_type(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Ottiene le informazioni di un tipo di entità.
        
        Args:
            name: Nome identificativo dell'entità
            
        Returns:
            Dizionario con le informazioni dell'entità o None se non esiste
        """
        return self.entity_types.get(name)
    
    def get_all_entity_types(self) -> Dict[str, Dict[str, Any]]:
        """
        Ottiene tutte le informazioni sui tipi di entità.
        
        Returns:
            Dizionario con tutte le informazioni sui tipi di entità
        """
        return self.entity_types
    
    def get_entity_types_by_category(self, category: str) -> List[str]:
        """
        Ottiene i nomi dei tipi di entità di una specifica categoria.
        
        Args:
            category: Categoria delle entità
            
        Returns:
            Lista di nomi dei tipi di entità della categoria specificata
        """
        if category not in self.entity_categories:
            self.logger.warning(f"Categoria non valida: {category}")
            return []
            
        return sorted(list(self.entity_categories[category]))
    
    def save_entities(self, file_path: str) -> bool:
        """
        Salva le definizioni delle entità in un file JSON.
        
        Args:
            file_path: Percorso del file dove salvare le definizioni
            
        Returns:
            True se il salvataggio è avvenuto con successo, False altrimenti
        """
        try:
            # Crea la directory se non esiste
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            
            # Converti set in liste per la serializzazione JSON
            serializable_categories = {
                k: list(v) for k, v in self.entity_categories.items()
            }
            
            data_to_save = {
                "entity_types": self.entity_types,
                "entity_categories": serializable_categories
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"Definizioni delle entità salvate con successo in {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Errore nel salvataggio delle definizioni delle entità: {str(e)}")
            return False
    
    def load_entities(self, file_path: str) -> bool:
        """
        Carica le definizioni delle entità da un file JSON.
        
        Args:
            file_path: Percorso del file contenente le definizioni
            
        Returns:
            True se il caricamento è avvenuto con successo, False altrimenti
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Mantieni delle copie per il ripristino in caso di errore
            old_entity_types = self.entity_types.copy()
            old_entity_categories = {k: v.copy() for k, v in self.entity_categories.items()}
            
            try:
                # Aggiorna i tipi di entità
                for name, definition in data.get("entity_types", {}).items():
                    category = definition.get("category", "custom")
                    
                    # Aggiorna o aggiungi l'entità
                    if name in self.entity_types:
                        self.update_entity_type(
                            name=name, 
                            display_name=definition.get("display_name"),
                            color=definition.get("color"),
                            metadata_schema=definition.get("metadata_schema"),
                            patterns=definition.get("patterns")
                        )
                    else:
                        self.add_entity_type(
                            name=name,
                            display_name=definition.get("display_name", name),
                            category=category,
                            color=definition.get("color", "#CCCCCC"),
                            metadata_schema=definition.get("metadata_schema", {}),
                            patterns=definition.get("patterns")
                        )
                        
                self.logger.info(f"Definizioni delle entità caricate con successo da {file_path}")
                return True
                
            except Exception as e:
                # Ripristina lo stato precedente in caso di errore
                self.entity_types = old_entity_types
                self.entity_categories = old_entity_categories
                raise e
                
        except FileNotFoundError:
            self.logger.warning(f"File {file_path} non trovato. Utilizzo delle entità predefinite.")
            return False
        except Exception as e:
            self.logger.error(f"Errore nel caricamento delle definizioni delle entità: {str(e)}")
            return False
    
    def get_entity_label_config(self, format: str = "label-studio") -> str:
        """
        Genera la configurazione delle etichette per gli strumenti di annotazione.
        
        Args:
            format: Formato della configurazione ("label-studio", "doccano", etc.)
            
        Returns:
            Configurazione delle etichette nel formato specifico
        """
        if format == "label-studio":
            # Genera XML per Label Studio
            xml_parts = ['<View>', '  <Header value="Annotazione di entità giuridiche"/>', '  <Text name="text" value="$text"/>']
            
            # Aggiungi le etichette
            labels_xml = ['  <Labels name="label" toName="text">']
            for name, info in self.entity_types.items():
                color = info.get("color", "#CCCCCC")
                display_name = info.get("display_name", name)
                labels_xml.append(f'    <Label value="{name}" background="{color}" displayName="{display_name}"/>')
            labels_xml.append('  </Labels>')
            
            xml_parts.extend(labels_xml)
            
            # Aggiungi le relazioni
            xml_parts.extend([
                '  <Relations>',
                '    <Relation value="riferimento" />',
                '    <Relation value="definizione" />',
                '    <Relation value="applicazione" />',
                '  </Relations>',
                '</View>'
            ])
            
            return '\n'.join(xml_parts)
            
        elif format == "doccano":
            # Genera JSON per Doccano
            doccano_config = []
            for name, info in self.entity_types.items():
                doccano_config.append({
                    "id": len(doccano_config) + 1,
                    "text": info.get("display_name", name),
                    "prefix_key": None,
                    "suffix_key": None,
                    "background_color": info.get("color", "#CCCCCC"),
                    "text_color": "#ffffff"
                })
            return json.dumps(doccano_config, ensure_ascii=False, indent=2)
            
        else:
            self.logger.warning(f"Formato {format} non supportato.")
            return ""
            
    def entity_type_exists(self, name: str) -> bool:
        """
        Verifica se un tipo di entità esiste.
        
        Args:
            name: Nome identificativo dell'entità
            
        Returns:
            True se il tipo di entità esiste, False altrimenti
        """
        return name in self.entity_types

    def get_metadata_fields(self, entity_type: str) -> Dict[str, str]:
        """
        Ottiene i campi dei metadati per un tipo di entità.
        
        Args:
            entity_type: Nome del tipo di entità
            
        Returns:
            Dizionario con i campi dei metadati (nome -> tipo)
        """
        if entity_type not in self.entity_types:
            return {}
            
        return self.entity_types[entity_type].get("metadata_schema", {})
        
    def get_patterns(self, entity_type: str) -> List[str]:
        """
        Ottiene i pattern regex per un tipo di entità.
        
        Args:
            entity_type: Nome del tipo di entità
            
        Returns:
            Lista di pattern regex per il riconoscimento
        """
        if entity_type not in self.entity_types:
            return []
            
        return self.entity_types[entity_type].get("patterns", [])
        
    def update_patterns(self, entity_type: str, patterns: List[str]) -> bool:
        """
        Aggiorna i pattern regex per un tipo di entità.
        
        Args:
            entity_type: Nome del tipo di entità
            patterns: Nuovi pattern regex
            
        Returns:
            True se l'aggiornamento è avvenuto con successo, False altrimenti
        """
        return self.update_entity_type(entity_type, patterns=patterns)


# Istanza globale del gestore delle entità
_entity_manager = None

def get_entity_manager(entities_file: Optional[str] = None) -> DynamicEntityManager:
    """
    Ottiene l'istanza globale del gestore delle entità o ne crea una nuova se non esiste.
    
    Args:
        entities_file: Percorso al file JSON contenente le definizioni delle entità
        
    Returns:
        Istanza del gestore delle entità
    """
    global _entity_manager
    if _entity_manager is None:
        _entity_manager = DynamicEntityManager(entities_file)
    return _entity_manager

def set_entity_manager(manager: DynamicEntityManager) -> None:
    """
    Imposta l'istanza globale del gestore delle entità.
    Utile per i test con mock.
    
    Args:
        manager: Istanza del gestore delle entità
    """
    global _entity_manager
    _entity_manager = manager