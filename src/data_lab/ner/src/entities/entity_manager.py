"""
Modulo per la gestione dinamica delle entità nel sistema NER-Giuridico.
Questo modulo permette di aggiungere, modificare e rimuovere tipi di entità
durante l'esecuzione dell'applicazione.
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Union
import os

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
        
        # Carica le entità predefinite
        self._load_default_entities()
        
        # Carica le entità dal file se specificato
        if entities_file:
            self.load_entities(entities_file)
            
    def _load_default_entities(self):
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
                        color: str, metadata_schema: Dict[str, str]) -> bool:
        """
        Aggiunge un nuovo tipo di entità al sistema.
        
        Args:
            name: Nome identificativo dell'entità (in maiuscolo)
            display_name: Nome visualizzato dell'entità
            category: Categoria dell'entità ("normative", "jurisprudence", "concepts" o "custom")
            color: Colore dell'entità in formato esadecimale (#RRGGBB)
            metadata_schema: Schema dei metadati dell'entità
            
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
            self.entity_types[name] = {
                "display_name": display_name,
                "category": category,
                "color": color,
                "metadata_schema": metadata_schema
            }
            
            # Aggiungi alle categorie
            self.entity_categories[category].add(name)
            
            self.logger.info(f"Entità {name} aggiunta con successo nella categoria {category}")
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
            return True
            
        except Exception as e:
            self.logger.error(f"Errore nella rimozione dell'entità {name}: {str(e)}")
            return False
    
    def update_entity_type(self, name: str, display_name: Optional[str] = None, 
                           color: Optional[str] = None, 
                           metadata_schema: Optional[Dict[str, str]] = None) -> bool:
        """
        Aggiorna un tipo di entità esistente.
        
        Args:
            name: Nome identificativo dell'entità
            display_name: Nuovo nome visualizzato (opzionale)
            color: Nuovo colore (opzionale)
            metadata_schema: Nuovo schema dei metadati (opzionale)
            
        Returns:
            True se l'aggiornamento è avvenuto con successo, False altrimenti
        """
        try:
            if name not in self.entity_types:
                self.logger.error(f"L'entità {name} non esiste.")
                return False
                
            # Aggiorna i campi specificati
            if display_name:
                self.entity_types[name]["display_name"] = display_name
                
            if color:
                self.entity_types[name]["color"] = color
                
            if metadata_schema:
                self.entity_types[name]["metadata_schema"] = metadata_schema
                
            self.logger.info(f"Entità {name} aggiornata con successo")
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
                
            # Aggiorna i tipi di entità
            self.entity_types.update(data.get("entity_types", {}))
            
            # Aggiorna le categorie (converte le liste in set)
            for category, entities in data.get("entity_categories", {}).items():
                if category in self.entity_categories:
                    self.entity_categories[category].update(entities)
                else:
                    self.entity_categories[category] = set(entities)
                    
            self.logger.info(f"Definizioni delle entità caricate con successo da {file_path}")
            return True
            
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
        
    def export_entity_types_enum(self, output_file: Optional[str] = None) -> str:
        """
        Genera ed eventualmente salva un file Python contenente un'enumerazione
        Enum con tutti i tipi di entità correnti.
        
        Args:
            output_file: Percorso dove salvare il file (opzionale)
            
        Returns:
            Contenuto del file generato
        """
        enum_code = [
            "from enum import Enum, auto",
            "",
            "class EntityType(Enum):",
            "    \"\"\"Enumerazione dei tipi di entità giuridiche riconosciute dal sistema.\"\"\"",
            ""
        ]
        
        # Aggiungi commenti per le sezioni
        sections = {
            "normative": "# Riferimenti normativi",
            "jurisprudence": "# Riferimenti giurisprudenziali",
            "concepts": "# Concetti giuridici",
            "custom": "# Entità personalizzate"
        }
        
        # Genera il codice con le sezioni
        for category, comment in sections.items():
            entity_types = self.get_entity_types_by_category(category)
            if entity_types:
                enum_code.append(f"    {comment}")
                for entity_type in entity_types:
                    enum_code.append(f"    {entity_type} = auto()")
                enum_code.append("")
        
        # Aggiungi metodi di classe per ottenere i tipi per categoria
        enum_code.extend([
            "    @classmethod",
            "    def get_normative_types(cls) -> set[\"EntityType\"]:",
            "        \"\"\"Restituisce l'insieme dei tipi di entità normative.\"\"\"",
            "        return {",
        ])
        
        # Aggiungi i tipi normativi
        for entity_type in self.get_entity_types_by_category("normative"):
            enum_code.append(f"            cls.{entity_type},")
        enum_code.extend([
            "        }",
            "",
        ])
        
        # Aggiungi metodo per i tipi giurisprudenziali
        enum_code.extend([
            "    @classmethod",
            "    def get_jurisprudence_types(cls) -> set[\"EntityType\"]:",
            "        \"\"\"Restituisce l'insieme dei tipi di entità giurisprudenziali.\"\"\"",
            "        return {",
        ])
        
        for entity_type in self.get_entity_types_by_category("jurisprudence"):
            enum_code.append(f"            cls.{entity_type},")
        enum_code.extend([
            "        }",
            "",
        ])
        
        # Aggiungi metodo per i tipi concettuali
        enum_code.extend([
            "    @classmethod",
            "    def get_concept_types(cls) -> set[\"EntityType\"]:",
            "        \"\"\"Restituisce l'insieme dei tipi di entità concettuali.\"\"\"",
            "        return {",
        ])
        
        for entity_type in self.get_entity_types_by_category("concepts"):
            enum_code.append(f"            cls.{entity_type},")
        enum_code.extend([
            "        }",
            "",
        ])
        
        # Aggiungi metodo per i tipi personalizzati se presenti
        custom_types = self.get_entity_types_by_category("custom")
        if custom_types:
            enum_code.extend([
                "    @classmethod",
                "    def get_custom_types(cls) -> set[\"EntityType\"]:",
                "        \"\"\"Restituisce l'insieme dei tipi di entità personalizzate.\"\"\"",
                "        return {",
            ])
            
            for entity_type in custom_types:
                enum_code.append(f"            cls.{entity_type},")
            enum_code.extend([
                "        }",
                "",
            ])
        
        enum_content = "\n".join(enum_code)
        
        # Salva il file se specificato
        if output_file:
            try:
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(enum_content)
                self.logger.info(f"Enumerazione delle entità salvata in {output_file}")
            except Exception as e:
                self.logger.error(f"Errore nel salvataggio dell'enumerazione delle entità: {str(e)}")
        
        return enum_content
        
# Istanza globale del gestore delle entità
entity_manager = None

def get_entity_manager(entities_file: Optional[str] = None) -> DynamicEntityManager:
    """
    Ottiene l'istanza globale del gestore delle entità o ne crea una nuova se non esiste.
    
    Args:
        entities_file: Percorso al file JSON contenente le definizioni delle entità
        
    Returns:
        Istanza del gestore delle entità
    """
    global entity_manager
    if entity_manager is None:
        entity_manager = DynamicEntityManager(entities_file)
    return entity_manager