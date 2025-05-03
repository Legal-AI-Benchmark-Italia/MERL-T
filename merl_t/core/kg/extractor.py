"""
Knowledge Graph Entity Extractor

Handles extraction of legal entities and relationships from text.
"""

import os
import re
import logging
from typing import Dict, List, Optional, Tuple, Any, Set

from loguru import logger
from merl_t.core.entities.entity_manager import get_entity_manager

def get_dynamic_entity_mapping():
    """Genera il mapping delle entità giuridiche da EntityManager."""
    entity_manager = get_entity_manager()
    mapping = {}
    
    for entity in entity_manager.get_all_entities():
        # Normalizza il nome per la chiave (lowercase, senza underscore)
        key = entity.name.lower().replace("_", "")
        # Usa il nome originale come valore per Neo4j
        mapping[key] = entity.display_name
        
    # Aggiungi fallback per compatibilità con esistente
    default_mappings = {
        "norma": "Norma",
        "concettogiuridico": "ConcettoGiuridico",
        "soggettogiuridico": "SoggettoGiuridico", 
        "attogiudiziario": "AttoGiudiziario",
        "fontediritto": "FonteDiritto",
        "dottrina": "Dottrina",
        "procedura": "Procedura"
    }
    
    # Unisci con priorità alle entità dinamiche
    for key, value in default_mappings.items():
        if key not in mapping:
            mapping[key] = value
            
    return mapping

# Sostituisci la costante statica con una funzione
LEGAL_ENTITY_MAPPING = get_dynamic_entity_mapping()

# Mappatura delle relazioni giuridiche -> tipo relazione Neo4j
LEGAL_RELATIONSHIP_MAPPING = {
    "disciplina": "DISCIPLINA",
    "applica_a": "APPLICA_A",
    "interpreta": "INTERPRETA",
    "commenta": "COMMENTA",
    "cita": "CITA",
    "deroga_a": "DEROGA_A",
    "modifica": "MODIFICA",
    "relazione_concettuale": "RELAZIONE_CONCETTUALE",
    "emesso_da": "EMESSO_DA",
    "fonte": "FONTE"
}

def clean_str(s: str) -> str:
    """Pulisce una stringa rimuovendo spazi extra e virgolette"""
    return s.strip().strip('"').strip("'")

def normalize_extracted_info(info: str, is_entity: bool = False, entity_type: str = None) -> str:
    """
    Normalizza le informazioni estratte in base al tipo di entità giuridica
    """
    info = clean_str(info)
    
    # Preserva il formato originale per norme e riferimenti giuridici
    if entity_type and entity_type.lower() == "norma":
        # Mantiene il formato originale per norme (es. "Art. 1414 c.c.")
        return info
    elif is_entity:
        # Per altri tipi di entità, assicura che la prima lettera sia maiuscola
        if info and len(info) > 0:
            return info[0].upper() + info[1:]
    return info

def is_float_regex(s: str) -> bool:
    """Verifica se una stringa è un numero decimale usando regex"""
    return bool(re.match(r'^[-+]?[0-9]*\.?[0-9]+$', s))

def get_normalized_relationship_type(keywords: str) -> str:
    """
    Ottiene un tipo di relazione normalizzato a partire dalle parole chiave.
    Verifica se corrisponde a una relazione giuridica conosciuta.
    """
    if not keywords:
        return "RELATED_TO"
        
    # Pulisci e converti in maiuscolo
    rel_type = keywords.strip().upper()
    
    # Cerca corrispondenze con le relazioni giuridiche definite
    for legal_rel_key, legal_rel_value in LEGAL_RELATIONSHIP_MAPPING.items():
        if legal_rel_value in rel_type or legal_rel_key.upper() in rel_type:
            return legal_rel_value
    
    # Se non ci sono corrispondenze, crea un tipo valido per Neo4j
    rel_type = re.sub(r'\s+', '_', rel_type)
    rel_type = re.sub(r'[^a-zA-Z0-9_]', '', rel_type)
    
    return rel_type if rel_type else "RELATED_TO"

async def enrich_entity_with_metadata_schema(entity_data):
    """Arricchisce i dati dell'entità con lo schema metadati dall'EntityManager."""
    entity_manager = get_entity_manager()
    entity_type_name = entity_data.get("entity_type_original")
    
    # Cerca l'entità corrispondente
    entity_type = entity_manager.get_entity_by_name(entity_type_name)
    
    if entity_type:
        # Aggiungi schema metadati
        entity_data["metadata_schema"] = entity_type.metadata_schema
        
        # Aggiungi altri attributi utili
        entity_data["display_name"] = entity_type.display_name
        entity_data["default_color"] = entity_type.color
        
        # Aggiungi eventuali pattern di riconoscimento
        if entity_type.patterns:
            entity_data["recognition_patterns"] = entity_type.patterns
    
    return entity_data

async def _handle_single_entity_extraction(
    record_attributes: List[str],
    chunk_key: str,
    source_metadata: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Gestisce l'estrazione di una singola entità giuridica"""
    # Filtra gli attributi vuoti risultanti dallo split
    filtered_attributes = [attr for attr in record_attributes if attr.strip()]

    # Controlla se è effettivamente un record di entità e ha abbastanza parti
    if not filtered_attributes or '"entity"' not in filtered_attributes[0].lower() or len(filtered_attributes) < 4:
        # Logga solo se il primo elemento suggerisce che doveva essere un'entità
        if filtered_attributes and '"entity"' in filtered_attributes[0].lower():
            logger.warning(f"Record entità con formato non valido ({len(filtered_attributes)} attributi dopo filtro), ignorato: {filtered_attributes}")
        return None
    
    # Accedi agli attributi solo dopo aver verificato la lunghezza
    entity_name = clean_str(filtered_attributes[1])
    entity_type_original = clean_str(filtered_attributes[2])
    entity_description = clean_str(filtered_attributes[3])
    
    # Ulteriore controllo: non creare nodi con nome vuoto
    if not entity_name:
        logger.warning(f"Nome entità vuoto nel record, ignorato: {filtered_attributes}")
        return None
    
    logger.debug(f"Entità estratta: nome='{entity_name}', tipo_originale='{entity_type_original}'")
    
    # Normalizza il nome dell'entità in base al tipo
    entity_name = normalize_extracted_info(entity_name, is_entity=True, entity_type=entity_type_original)
    # Normalizza e Mappa il tipo di entità alla label Neo4j
    entity_type_normalized = normalize_extracted_info(entity_type_original)
    mapped_entity_label = LEGAL_ENTITY_MAPPING.get(entity_type_normalized.lower(), entity_type_normalized) # Usa il normalizzato come fallback
    entity_description = normalize_extracted_info(entity_description)
    
    logger.debug(f"Entità normalizzata: nome='{entity_name}', tipo_norm='{entity_type_normalized}', label_neo4j='{mapped_entity_label}'")
    
    # Gestione specifica per entità giuridiche
    entity_data = {
        "name": entity_name,
        "entity_label": mapped_entity_label, # Label per Neo4j
        "entity_type_original": entity_type_original, # Tipo originale per riferimento
        "description": entity_description,
        # Includi i metadati della fonte
        "source_doc_path": source_metadata.get("source_doc_path", "unknown_source"),
        "chunk_id": source_metadata.get("chunk_id", "unknown_chunk"),
    }
    
    # Aggiungiamo informazioni specifiche in base al tipo di entità
    if mapped_entity_label == "Norma": # Controlla usando la label mappata
        # Estrai informazioni aggiuntive per le norme (se disponibili)
        # Es. riconoscimento di articoli e codici
        match = re.search(r'Art\.\s*(\d+[a-z]*)\s+(c\.\s*c\.|c\.\s*p\.|COST\.)', entity_name, re.IGNORECASE)
        if match:
            entity_data["article_number"] = match.group(1)
            entity_data["code"] = match.group(2).replace(".", "").replace(" ", "").upper()
    
    elif mapped_entity_label == "AttoGiudiziario":
        # Estrai informazioni per sentenze/provvedimenti
        match = re.search(r'(\w+)\s+n\.\s*(\d+[\/\\]\d+)', entity_name, re.IGNORECASE)
        if match:
            entity_data["type"] = match.group(1)  # Es. "Sentenza"
            entity_data["number"] = match.group(2)  # Es. "5134/2008"
    
    # Dopo aver estratto i dati di base, arricchisci con EntityManager
    if entity_data:
        entity_data = await enrich_entity_with_metadata_schema(entity_data)
    
    return entity_data

async def _handle_single_relationship_extraction(
    record_attributes: List[str],
    chunk_key: str,
    source_metadata: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Gestisce l'estrazione di una singola relazione giuridica"""
    # Filtra gli attributi vuoti dopo lo split
    filtered_attributes = [attr for attr in record_attributes if attr.strip()]
    
    # Controlla se è effettivamente un record di relazione e ha abbastanza parti
    if not filtered_attributes or '"relationship"' not in filtered_attributes[0].lower() or len(filtered_attributes) < 5:
        # Logga solo se il primo elemento suggerisce che doveva essere una relazione
        if filtered_attributes and '"relationship"' in filtered_attributes[0].lower():
            logger.warning(f"Record relazione con formato non valido ({len(filtered_attributes)} attributi dopo filtro), ignorato: {filtered_attributes}")
        return None
    
    # Accedi agli attributi solo dopo aver verificato la lunghezza
    source_entity = clean_str(filtered_attributes[1])
    target_entity = clean_str(filtered_attributes[2])
    rel_type_original = clean_str(filtered_attributes[3])
    rel_description = clean_str(filtered_attributes[4]) if len(filtered_attributes) > 4 else ""
    
    # Ulteriore controllo: non creare relazioni con entità sorgente o destinazione vuote
    if not source_entity or not target_entity:
        logger.warning(f"Entità sorgente o destinazione vuote nel record, ignorato: {filtered_attributes}")
        return None
    
    logger.debug(f"Relazione estratta: sorgente='{source_entity}', destinazione='{target_entity}', tipo='{rel_type_original}'")
    
    # Normalizza il tipo di relazione
    normalized_rel_type = get_normalized_relationship_type(rel_type_original)
    
    # Costruisci i dati della relazione
    edge_data = {
        "legal_relation_type": normalized_rel_type,  # Tipo normalizzato per Neo4j (tipo effettivo)
        "relation_type_original": rel_type_original,  # Tipo originale per riferimento
        "description": rel_description,
        # Includi i metadati della fonte
        "source_doc_path": source_metadata.get("source_doc_path", "unknown_source"),
        "chunk_id": source_metadata.get("chunk_id", "unknown_chunk")
    }
    
    # Non ritorniamo l'ID qui, solo i dati necessari per costruire la relazione
    return {
        "source_entity": source_entity,
        "target_entity": target_entity,
        "edge_data": edge_data
    }

async def extract_entities(
    text: str,
    source_metadata: Dict[str, Any],
    knowledge_graph_inst,
    global_config: Dict[str, Any],
    llm_func: callable
) -> Dict[str, Any]:
    """
    Estrae entità e relazioni da un testo usando un LLM e le aggiunge al grafo.
    
    Args:
        text: Il testo da analizzare
        source_metadata: Metadati sulla fonte del testo (documento, chunk, ecc.)
        knowledge_graph_inst: Istanza di Neo4jGraphStorage
        global_config: Configurazione globale
        llm_func: Funzione per chiamare l'LLM
        
    Returns:
        Dizionario con statistiche sull'estrazione
    """
    logger.info(f"Estrazione entità dal testo di {len(text)} caratteri")
    
    # Verifica che il grafo sia inizializzato
    if not knowledge_graph_inst:
        logger.error("Istanza di storage del grafo non inizializzata")
        return {"error": "Grafo non inizializzato"}
        
    try:
        # Estrai i parametri di configurazione
        entity_types = global_config.get("entity_types", ["Norma", "ConcettoGiuridico"])
        
        # Usa direttamente i prompt predefiniti come parte della richiesta
        prompt = f"""
        Analizza il seguente testo giuridico ed estrai:
        1. Entità giuridiche dei seguenti tipi: {', '.join(entity_types)}
        2. Relazioni tra le entità
        
        Formatta le entità come: "entity"|"nome entità"|"tipo entità"|"descrizione"
        Formatta le relazioni come: "relationship"|"entità sorgente"|"entità destinazione"|"tipo relazione"|"descrizione"
        
        Testo da analizzare:
        {text}
        
        Estrazione:
        """
        
        # Chiamata all'LLM
        logger.debug("Chiamata all'LLM per estrazione entità")
        llm_response = await llm_func(prompt)
        
        if not llm_response:
            logger.error("Nessuna risposta dall'LLM")
            return {"error": "Nessuna risposta dall'LLM"}
            
        # Inizializza contatori
        nodes_count = 0
        edges_count = 0
        
        # Prepara strutture dati per entità e relazioni
        entities = {}
        relationships = []
        
        # Processa la risposta
        logger.debug("Elaborazione risposta dell'LLM")
        lines = llm_response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Elabora record (entità o relazione)
            record_attributes = line.strip().split('|')
            
            # Genera una chiave univoca per questo chunk
            chunk_key = f"{source_metadata.get('source_doc_path', 'unknown')}_{source_metadata.get('chunk_id', '0')}"
            
            if '"entity"' in line.lower() or "'entity'" in line.lower():
                # Estrai dati entità
                entity_data = await _handle_single_entity_extraction(record_attributes, chunk_key, source_metadata)
                
                if entity_data:
                    # Usa il nome dell'entità come chiave
                    entity_name = entity_data["name"]
                    
                    # Crea ID univoco per l'entità
                    entity_id = entity_name.lower().replace(" ", "_").replace(".", "_")
                    entity_data["id"] = entity_id
                    
                    # Aggiungi alla mappa delle entità
                    entities[entity_id] = entity_data
                    
            elif '"relationship"' in line.lower() or "'relationship'" in line.lower():
                # Estrai dati relazione
                relationship_data = await _handle_single_relationship_extraction(record_attributes, chunk_key, source_metadata)
                
                if relationship_data:
                    # Aggiungi alla lista delle relazioni
                    relationships.append(relationship_data)
        
        # Inserisci entità nel grafo
        for entity_id, entity_data in entities.items():
            try:
                await knowledge_graph_inst.upsert_node(entity_id, entity_data)
                nodes_count += 1
            except Exception as e:
                logger.error(f"Errore nell'inserimento dell'entità {entity_id}: {e}")
        
        # Inserisci relazioni nel grafo
        for relationship in relationships:
            try:
                source_name = relationship["source_entity"]
                target_name = relationship["target_entity"]
                edge_data = relationship["edge_data"]
                
                # Crea ID univoci per entità sorgente e destinazione
                source_id = source_name.lower().replace(" ", "_").replace(".", "_")
                target_id = target_name.lower().replace(" ", "_").replace(".", "_")
                
                # Inserisci relazione
                await knowledge_graph_inst.upsert_edge(source_id, target_id, edge_data)
                edges_count += 1
            except Exception as e:
                logger.error(f"Errore nell'inserimento della relazione da {source_name} a {target_name}: {e}")
        
        # Restituisci statistiche
        return {
            "nodes_count": nodes_count,
            "edges_count": edges_count
        }
        
    except Exception as e:
        logger.error(f"Errore durante l'estrazione delle entità: {e}")
        return {"error": str(e)} 