import os
import re
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from .types import KnowledgeGraph, KnowledgeGraphNode, KnowledgeGraphEdge
from .base import BaseGraphStorage
from .prompt import get_formatted_prompt
from src.core.entities.entity_manager import get_entity_manager

# Configurazione di logging
logger = logging.getLogger(__name__)

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
    """Gestisce l'estrazione di una singola relazione tra entità giuridiche"""
    # Filtra gli attributi vuoti risultanti dallo split
    filtered_attributes = [attr for attr in record_attributes if attr.strip()]

    # Controlla se è effettivamente un record di relazione e ha abbastanza parti
    if not filtered_attributes or '"relationship"' not in filtered_attributes[0].lower() or len(filtered_attributes) < 5:
        # Logga solo se il primo elemento suggerisce che doveva essere una relazione
        if filtered_attributes and '"relationship"' in filtered_attributes[0].lower():
            logger.warning(f"Record relazione con formato non valido ({len(filtered_attributes)} attributi dopo filtro), ignorato: {filtered_attributes}")
        return None
    
    # Accedi agli attributi solo dopo aver verificato la lunghezza
    source = clean_str(filtered_attributes[1])
    target = clean_str(filtered_attributes[2])
    edge_description = normalize_extracted_info(filtered_attributes[3])
    edge_keywords = clean_str(filtered_attributes[4]).strip('"').strip("'")
    
    # Controlli aggiuntivi: source e target non devono essere vuoti
    if not source or not target:
        logger.warning(f"Source o Target vuoto nel record relazione, ignorato: {filtered_attributes}")
        return None
    
    logger.debug(f"Relazione estratta: sorgente='{source}', destinazione='{target}'")
    
    # Normalizza le entità di origine e destinazione
    source = normalize_extracted_info(source, is_entity=True)
    target = normalize_extracted_info(target, is_entity=True)
    
    edge_source_id = chunk_key
    
    logger.debug(f"Parole chiave relazione: '{edge_keywords}'")
    
    # Determina il peso, gestendo il caso in cui l'indice sia fuori range dopo il filtro
    weight = 1.0
    if len(filtered_attributes) >= 6 and is_float_regex(filtered_attributes[5].strip('"').strip("'")):
        try:
            weight = float(filtered_attributes[5].strip('"').strip("'"))
        except ValueError:
            logger.warning(f"Impossibile convertire il peso in float nel record relazione: {filtered_attributes}")
            weight = 1.0 # Fallback a 1.0
    
    logger.debug(f"Peso relazione: {weight}")
    
    # Identifica il tipo di relazione legale (DISCIPLINA, INTERPRETA, ecc.)
    legal_rel_type = get_normalized_relationship_type(edge_keywords)
    logger.debug(f"Tipo relazione giuridica identificato: {legal_rel_type}")
    
    return dict(
        src_id=source,
        tgt_id=target,
        weight=weight,
        description=edge_description,
        keywords=edge_keywords,
        legal_relation_type=legal_rel_type,  # Aggiungiamo il tipo di relazione legale normalizzato
        source_id=edge_source_id,
        # Includi i metadati della fonte
        source_doc_path=source_metadata.get("source_doc_path", "unknown_source"),
        chunk_id=source_metadata.get("chunk_id", "unknown_chunk"),
    )

async def extract_entities(
    text: str,
    source_metadata: Dict[str, Any],
    knowledge_graph_inst: BaseGraphStorage,
    global_config: Dict[str, Any],
    llm_func: callable,
    llm_response_cache: Optional[Any] = None,
) -> Dict[str, Any]:
    """Estrae entità e relazioni giuridiche dal testo usando LLM"""
    logger.info("Inizio estrazione entità e relazioni giuridiche dal testo")
    logger.debug(f"Lunghezza testo: {len(text)} caratteri")
    logger.debug(f"Metadati sorgente: {source_metadata}")
    
    if not text or len(text.strip()) < 10:
        logger.warning(f"Testo troppo breve per l'estrazione: '{text}'")
        return {}
    
    # Get configuration
    entity_extract_max_gleaning = global_config.get("entity_extract_max_gleaning", 3)
    language = global_config.get("language", "Italian") # Default language se non in config
    entity_types = global_config.get("entity_types", []) # Recupera dalla config
    delimiters = global_config.get("delimiters", {})
    tuple_delimiter = delimiters.get("tuple", "<|>")
    record_delimiter = delimiters.get("record", "##")
    completion_delimiter = delimiters.get("completion", "<|COMPLETE|>")
    
    logger.debug(f"Configurazione: language={language}, entity_types={entity_types}, max_gleaning={entity_extract_max_gleaning}")
    logger.debug(f"Delimitatori: tuple='{tuple_delimiter}', record='{record_delimiter}', completion='{completion_delimiter}'")
    
    # Estrazione iniziale
    logger.debug("Preparazione prompt per estrazione iniziale")
    hint_prompt = get_formatted_prompt(
        "entity_extraction",
        global_config,
        input_text=text
    )
    
    logger.debug("Chiamata al modello LLM per estrazione iniziale")
    try:
        final_result = await llm_func(hint_prompt)
        logger.debug(f"Risposta LLM ricevuta: {len(final_result)} caratteri")
        if len(final_result) < 20:
            logger.warning(f"Risposta LLM troppo breve, potrebbe non contenere entità: '{final_result}'")
    except Exception as e:
        logger.error(f"Errore durante la chiamata al modello LLM: {e}")
        return {}
    
    history = [(hint_prompt, final_result)]
    
    # Elabora estrazione iniziale
    aggregated_nodes: Dict[str, Dict[str, Any]] = {}
    aggregated_edges: Dict[str, Dict[str, Any]] = {}
    
    # Generiamo un ID per il chunk corrente
    chunk_key = f"chunk_{hash(text)}"
    logger.debug(f"ID chunk generato: {chunk_key}")
    
    # Stampa la risposta completa per debugging
    logger.debug(f"Risposta LLM completa: '{final_result}'")
    
    # Traccia le entità e relazioni estratte per statistiche
    entity_types_found: Set[str] = set()
    relationship_types_found: Set[str] = set()
    
    logger.debug("Elaborazione risultati estrazione iniziale")
    for record in final_result.split(record_delimiter):
        record = record.strip()
        if not record:
            continue
            
        logger.debug(f"Elaborazione record: '{record}'")
        record_attributes = record.split(tuple_delimiter)
        logger.debug(f"Attributi record: {record_attributes}")
        
        # Gestione estrazione entità
        try:
            entity_data = await _handle_single_entity_extraction(record_attributes, chunk_key, source_metadata)
            if entity_data:
                entity_name = entity_data["name"]
                entity_type = entity_data["entity_type_original"]
                
                # --- Logica di Aggregazione Nodi --- 
                if entity_name not in aggregated_nodes:
                    # Nodo nuovo per questa esecuzione: inizializza proprietà lista
                    aggregated_nodes[entity_name] = entity_data
                    aggregated_nodes[entity_name]["source_doc_paths"] = [entity_data["source_doc_path"]]
                    aggregated_nodes[entity_name]["chunk_ids"] = [entity_data["chunk_id"]]
                    aggregated_nodes[entity_name]["all_entity_types_original"] = [entity_data["entity_type_original"]]
                    # Rimuovi le chiavi singole ora che sono nelle liste
                    del aggregated_nodes[entity_name]["source_doc_path"]
                    del aggregated_nodes[entity_name]["chunk_id"]
                    # entity_type_original rimane per ora, poi aggregata
                else:
                    # Nodo già visto: arricchisci
                    existing_node = aggregated_nodes[entity_name]
                    # Aggiungi source e chunk se non presenti
                    if entity_data["source_doc_path"] not in existing_node["source_doc_paths"]:
                        existing_node["source_doc_paths"].append(entity_data["source_doc_path"])
                    if entity_data["chunk_id"] not in existing_node["chunk_ids"]:
                        existing_node["chunk_ids"].append(entity_data["chunk_id"])
                    # Aggiorna tipi originali
                    if entity_data["entity_type_original"] not in existing_node["all_entity_types_original"]:
                        existing_node["all_entity_types_original"].append(entity_data["entity_type_original"])
                    # Decidi strategia per descrizione (es. mantieni la prima)
                    existing_node["description"] = existing_node.get("description", entity_data["description"])

                # Traccia tipi di entità (usa label mappata)
                entity_types_found.add(entity_data.get("entity_label", "Unknown"))

                logger.debug(f"Entità processata/aggregata: {entity_name} (Label: {entity_data.get('entity_label', 'Unknown')})")
        except Exception as e:
            logger.error(f"Errore durante l'estrazione dell'entità giuridica dal record '{record_attributes}': {e}", exc_info=True)
            
        # Gestione estrazione relazione
        try:
            relationship_data = await _handle_single_relationship_extraction(record_attributes, chunk_key, source_metadata)
            if relationship_data:
                src_id = relationship_data['src_id']
                tgt_id = relationship_data['tgt_id']
                legal_relation_type = relationship_data.get('legal_relation_type', 'RELATED_TO')
                
                # --- Logica di Aggregazione Relazioni --- 
                edge_key = f"{src_id}-{legal_relation_type}-{tgt_id}" # Chiave più specifica
                if edge_key not in aggregated_edges:
                     # Relazione nuova: inizializza liste
                    aggregated_edges[edge_key] = relationship_data
                    aggregated_edges[edge_key]["source_doc_paths"] = [relationship_data["source_doc_path"]]
                    aggregated_edges[edge_key]["chunk_ids"] = [relationship_data["chunk_id"]]
                    # Rimuovi chiavi singole
                    del aggregated_edges[edge_key]["source_doc_path"]
                    del aggregated_edges[edge_key]["chunk_id"]
                else:
                    # Relazione già vista: arricchisci
                    existing_edge = aggregated_edges[edge_key]
                    if relationship_data["source_doc_path"] not in existing_edge["source_doc_paths"]:
                        existing_edge["source_doc_paths"].append(relationship_data["source_doc_path"])
                    if relationship_data["chunk_id"] not in existing_edge["chunk_ids"]:
                        existing_edge["chunk_ids"].append(relationship_data["chunk_id"])
                    # Aggiorna altre proprietà (es. peso medio? ultima descrizione?)
                    existing_edge["description"] = relationship_data["description"] # Sovrascrivi con ultima descrizione
                    existing_edge["weight"] = max(existing_edge.get("weight", 0.0), relationship_data.get("weight", 0.0)) # Esempio: prendi peso massimo

                # Traccia tipi di relazione per statistiche
                relationship_types_found.add(legal_relation_type)

                logger.debug(f"Relazione processata/aggregata: {src_id} -> {tgt_id} ({legal_relation_type})")
        except Exception as e:
            logger.error(f"Errore durante l'estrazione della relazione giuridica dal record '{record_attributes}': {e}", exc_info=True)
    
    logger.info(f"Estrazione iniziale completata: {len(aggregated_nodes)} entità giuridiche, {len(aggregated_edges)} relazioni aggregate")
    logger.info(f"Tipi di entità trovati: {entity_types_found}")
    logger.info(f"Tipi di relazione trovati: {relationship_types_found}")
    
    # Processo di gleaning (estrazione aggiuntiva)
    for gleaning_round in range(entity_extract_max_gleaning):
        logger.info(f"Avvio gleaning round {gleaning_round+1}/{entity_extract_max_gleaning}")
        nodes_before_gleaning = len(aggregated_nodes)
        edges_before_gleaning = len(aggregated_edges)

        logger.debug("Preparazione prompt per gleaning")
        
        # Usa la nuova funzione per il prompt di continuazione
        glean_prompt = get_formatted_prompt(
            "entity_continue_extraction",
            global_config
        )
        
        glean_result = await llm_func(
            glean_prompt,
            history=history
        )
        logger.debug(f"Risposta gleaning ricevuta: {len(glean_result)} caratteri")
        
        history.append((glean_prompt, glean_result))
        
        # Elabora risultato gleaning
        new_entities = 0
        new_relationships = 0
        
        # Genera un ID per il round di gleaning corrente
        gleaning_chunk_key = f"{chunk_key}_gleaning_{gleaning_round}"
        logger.debug(f"ID chunk gleaning generato: {gleaning_chunk_key}")
        
        logger.debug("Elaborazione risultati gleaning")
        for record in glean_result.split(record_delimiter):
            record = record.strip()
            if not record:
                continue
                
            record_attributes = record.split(tuple_delimiter)
            
            # Gestione estrazione entità nel gleaning (USA LA STESSA LOGICA DI AGGREGAZIONE)
            entity_data = await _handle_single_entity_extraction(record_attributes, gleaning_chunk_key, source_metadata)
            if entity_data:
                entity_name = entity_data["name"]
                entity_type = entity_data["entity_type_original"]
                
                if entity_name not in aggregated_nodes:
                    # Stessa logica di aggregazione dell'estrazione iniziale
                    aggregated_nodes[entity_name] = entity_data
                    aggregated_nodes[entity_name]["source_doc_paths"] = [entity_data["source_doc_path"]]
                    aggregated_nodes[entity_name]["chunk_ids"] = [entity_data["chunk_id"]]
                    aggregated_nodes[entity_name]["all_entity_types_original"] = [entity_data["entity_type_original"]]
                    del aggregated_nodes[entity_name]["source_doc_path"]
                    del aggregated_nodes[entity_name]["chunk_id"]
                    new_entities += 1
                else:
                    # Arricchisci nodo esistente (stessa logica di prima)
                    existing_node = aggregated_nodes[entity_name]
                    if entity_data["source_doc_path"] not in existing_node["source_doc_paths"]:
                        existing_node["source_doc_paths"].append(entity_data["source_doc_path"])
                    if entity_data["chunk_id"] not in existing_node["chunk_ids"]:
                        existing_node["chunk_ids"].append(entity_data["chunk_id"])
                    if entity_data["entity_type_original"] not in existing_node["all_entity_types_original"]:
                        existing_node["all_entity_types_original"].append(entity_data["entity_type_original"])
                    existing_node["description"] = existing_node.get("description", entity_data["description"])

                entity_types_found.add(entity_data.get("entity_label", "Unknown"))
                logger.debug(f"Gleaning: Entità processata/aggregata: {entity_name} (Label: {entity_data.get('entity_label', 'Unknown')})")
                
            # Gestione estrazione relazione nel gleaning
            relationship_data = await _handle_single_relationship_extraction(record_attributes, gleaning_chunk_key, source_metadata)
            if relationship_data:
                src_id = relationship_data['src_id']
                tgt_id = relationship_data['tgt_id']
                legal_relation_type = relationship_data.get('legal_relation_type', 'RELATED_TO')
                
                edge_key = f"{src_id}-{legal_relation_type}-{tgt_id}"
                
                if edge_key not in aggregated_edges:
                    # Stessa logica di aggregazione dell'estrazione iniziale
                    aggregated_edges[edge_key] = relationship_data
                    aggregated_edges[edge_key]["source_doc_paths"] = [relationship_data["source_doc_path"]]
                    aggregated_edges[edge_key]["chunk_ids"] = [relationship_data["chunk_id"]]
                    del aggregated_edges[edge_key]["source_doc_path"]
                    del aggregated_edges[edge_key]["chunk_id"]
                    new_relationships += 1
                else:
                    # Arricchisci relazione esistente (stessa logica di prima)
                    existing_edge = aggregated_edges[edge_key]
                    if relationship_data["source_doc_path"] not in existing_edge["source_doc_paths"]:
                        existing_edge["source_doc_paths"].append(relationship_data["source_doc_path"])
                    if relationship_data["chunk_id"] not in existing_edge["chunk_ids"]:
                        existing_edge["chunk_ids"].append(relationship_data["chunk_id"])
                    existing_edge["description"] = relationship_data["description"]
                    existing_edge["weight"] = max(existing_edge.get("weight", 0.0), relationship_data.get("weight", 0.0))

                relationship_types_found.add(legal_relation_type)
                logger.debug(f"Gleaning: Relazione processata/aggregata: {src_id} -> {tgt_id} ({legal_relation_type})")
        
        new_entities_count = len(aggregated_nodes) - nodes_before_gleaning
        new_relationships_count = len(aggregated_edges) - edges_before_gleaning

        logger.info(f"Gleaning round {gleaning_round+1} completato: trovate {new_entities_count} nuove entità, {new_relationships_count} nuove relazioni")

        # Se non abbiamo trovato nuove entità o relazioni in questo round, interrompi il gleaning
        if new_entities_count == 0 and new_relationships_count == 0:
            logger.info(f"Nessuna nuova entità o relazione trovata nel round {gleaning_round+1}, interrompo gleaning")
            break
    
    # Aggiornamento del knowledge graph
    logger.info(f"Aggiornamento knowledge graph con {len(aggregated_nodes)} entità e {len(aggregated_edges)} relazioni aggregate")
    
    # Aggiunta nodi al grafo
    for node_id, node_data in aggregated_nodes.items():
        logger.debug(f"Aggiunta/aggiornamento nodo: {node_id}")
        
        # Ora passiamo direttamente il dizionario aggregato (node_data) a upsert_node
        # Assicurati che `upsert_node` in `neo4j_storage.py` gestisca correttamente
        # le chiavi come `source_doc_paths` e `chunk_ids`.

        logger.debug(f"Proprietà nodo: {node_data}")
        await knowledge_graph_inst.upsert_node(
            node_id, # L'ID è la chiave del dizionario aggregated_nodes
            node_data # Passiamo il dizionario aggregato
        )

    # Aggiunta archi al grafo
    for edge_key, edge_data in aggregated_edges.items():
        # Prendiamo i dati dal primo elemento estratto per questo arco
        src_id = edge_data['src_id']
        tgt_id = edge_data['tgt_id']

        logger.debug(f"Aggiunta/aggiornamento arco: {src_id} -> {tgt_id}")

        # Usa il tipo di relazione giuridica normalizzato
        relation_type = edge_data.get("legal_relation_type", "RELATED_TO")
        
        # Verifica se l'entità di origine e destinazione esistono
        src_exists = await knowledge_graph_inst.has_node(src_id)
        tgt_exists = await knowledge_graph_inst.has_node(tgt_id)
        
        if not src_exists:
            logger.warning(f"Entità origine '{src_id}' non trovata nel grafo. Creazione di un nodo placeholder.")
            await knowledge_graph_inst.upsert_node(
                src_id, 
                {"label": "Node", "name": src_id, "description": "Entità estratta implicitamente da relazione", "is_placeholder": True}
            )
            
        if not tgt_exists:
            logger.warning(f"Entità destinazione '{tgt_id}' non trovata nel grafo. Creazione di un nodo placeholder.")
            await knowledge_graph_inst.upsert_node(
                tgt_id, 
                {"label": "Node", "name": tgt_id, "description": "Entità estratta implicitamente da relazione", "is_placeholder": True}
            )

        edge_properties = {
            # Passiamo direttamente il dizionario aggregato edge_data.
            # Il `relation_type` per la query MERGE verrà preso da edge_data["legal_relation_type"]
            # Assicurati che `upsert_edge` gestisca questo.
        }

        logger.debug(f"Proprietà arco: {edge_properties}")
        await knowledge_graph_inst.upsert_edge(
            src_id,
            tgt_id,
            edge_data # Passiamo il dizionario aggregato
        )

    # Statistiche finali
    nodes_count = len(aggregated_nodes)
    edges_count = len(aggregated_edges)
    logger.info(f"Knowledge graph giuridico aggiornato con successo per questo chunk:")
    logger.info(f"- {nodes_count} nodi totali processati/aggregati in questo chunk")
    logger.info(f"- {edges_count} relazioni totali processate/aggregate in questo chunk")
    logger.info(f"- Tipi di entità trovati: {entity_types_found}")
    logger.info(f"- Tipi di relazione trovati: {relationship_types_found}")
    
    return {
        "nodes_count": nodes_count,
        "edges_count": edges_count,
        "entity_types": list(entity_types_found),
        "relationship_types": list(relationship_types_found)
    }