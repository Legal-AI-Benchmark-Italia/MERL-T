import os
import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from .types import KnowledgeGraph, KnowledgeGraphNode, KnowledgeGraphEdge
from .base import BaseGraphStorage
# Importa la nuova classe Neo4jStorage se necessario (anche se l'istanza viene passata)
# from .neo4j_storage import Neo4jGraphStorage
from .prompt import PROMPTS

# Configurazione di logging
logger = logging.getLogger(__name__)

def clean_str(s: str) -> str:
    """Clean a string by removing extra spaces and quotes"""
    return s.strip().strip('"').strip("'")

def normalize_extracted_info(info: str, is_entity: bool = False) -> str:
    """Normalize extracted information"""
    info = clean_str(info)
    if is_entity:
        # Capitalize first letter of each word for entities
        return " ".join(word.capitalize() for word in info.split())
    return info

def is_float_regex(s: str) -> bool:
    """Check if a string is a float using regex"""
    return bool(re.match(r'^[-+]?[0-9]*\.?[0-9]+$', s))

async def _handle_single_entity_extraction(
    record_attributes: List[str],
    chunk_key: str,
    file_path: str = "unknown_source",
) -> Optional[Dict[str, Any]]:
    """Handle extraction of a single entity"""
    logger.debug(f"Elaborazione entità con attributi: {record_attributes}")
    
    if len(record_attributes) < 4 or '"entity"' not in record_attributes[0]:
        logger.debug("Record non valido per un'entità, ignorato")
        return None
    
    entity_name = clean_str(record_attributes[1])
    entity_type = clean_str(record_attributes[2])
    entity_description = clean_str(record_attributes[3])
    
    logger.debug(f"Entità estratta: nome='{entity_name}', tipo='{entity_type}'")
    
    # Normalize entity name
    entity_name = normalize_extracted_info(entity_name, is_entity=True)
    entity_type = normalize_extracted_info(entity_type)
    entity_description = normalize_extracted_info(entity_description)
    
    logger.debug(f"Entità normalizzata: nome='{entity_name}', tipo='{entity_type}'")
    
    return dict(
        name=entity_name,
        entity_type=entity_type,
        description=entity_description,
        source_id=chunk_key,
        file_path=file_path,
    )

async def _handle_single_relationship_extraction(
    record_attributes: List[str],
    chunk_key: str,
    file_path: str = "unknown_source",
) -> Optional[Dict[str, Any]]:
    """Handle extraction of a single relationship"""
    logger.debug(f"Elaborazione relazione con attributi: {record_attributes}")
    
    if len(record_attributes) < 5 or '"relationship"' not in record_attributes[0]:
        logger.debug("Record non valido per una relazione, ignorato")
        return None
    
    source = clean_str(record_attributes[1])
    target = clean_str(record_attributes[2])
    
    logger.debug(f"Relazione estratta: sorgente='{source}', destinazione='{target}'")
    
    # Normalize source and target entity names
    source = normalize_extracted_info(source, is_entity=True)
    target = normalize_extracted_info(target, is_entity=True)
    
    edge_description = clean_str(record_attributes[3])
    edge_description = normalize_extracted_info(edge_description)
    
    edge_keywords = clean_str(record_attributes[4]).strip('"').strip("'")
    edge_source_id = chunk_key
    
    logger.debug(f"Parole chiave relazione: '{edge_keywords}'")
    
    weight = (
        float(record_attributes[-1].strip('"').strip("'"))
        if is_float_regex(record_attributes[-1].strip('"').strip("'"))
        else 1.0
    )
    
    logger.debug(f"Peso relazione: {weight}")
    
    return dict(
        src_id=source,
        tgt_id=target,
        weight=weight,
        description=edge_description,
        keywords=edge_keywords,
        source_id=edge_source_id,
        file_path=file_path,
    )

async def extract_entities(
    text: str,
    knowledge_graph_inst: BaseGraphStorage,
    global_config: Dict[str, Any],
    llm_func: callable,
    llm_response_cache: Optional[Any] = None,
) -> None:
    """Extract entities and relationships from text using LLM"""
    logger.info("Inizio estrazione entità e relazioni dal testo")
    logger.debug(f"Lunghezza testo: {len(text)} caratteri")
    
    if not text or len(text.strip()) < 10:
        logger.warning(f"Testo troppo breve per l'estrazione: '{text}'")
        return []
    
    # Get configuration
    entity_extract_max_gleaning = global_config.get("entity_extract_max_gleaning", 3)
    language = global_config.get("language", PROMPTS["DEFAULT_LANGUAGE"])
    entity_types = global_config.get("entity_types", PROMPTS["DEFAULT_ENTITY_TYPES"])
    
    logger.debug(f"Configurazione: language={language}, entity_types={entity_types}, max_gleaning={entity_extract_max_gleaning}")
    
    # Prepare context for prompts
    context_base = dict(
        tuple_delimiter=PROMPTS["DEFAULT_TUPLE_DELIMITER"],
        record_delimiter=PROMPTS["DEFAULT_RECORD_DELIMITER"],
        completion_delimiter=PROMPTS["DEFAULT_COMPLETION_DELIMITER"],
        entity_types=",".join(entity_types),
        language=language,
        examples=PROMPTS.get("examples", "")  # Aggiunto il parametro examples con fallback a stringa vuota
    )
    
    # Get initial extraction
    logger.debug("Preparazione prompt per estrazione iniziale")
    hint_prompt = PROMPTS["entity_extraction"].format(
        **{**context_base, "input_text": text}
    )
    
    logger.debug("Chiamata al modello LLM per estrazione iniziale")
    try:
        final_result = await llm_func(hint_prompt)
        logger.debug(f"Risposta LLM ricevuta: {len(final_result)} caratteri")
        if len(final_result) < 20:
            logger.warning(f"Risposta LLM troppo breve, potrebbe non contenere entità: '{final_result}'")
    except Exception as e:
        logger.error(f"Errore durante la chiamata al modello LLM: {e}")
        return []
    
    history = [(hint_prompt, final_result)]
    
    # Process initial extraction
    nodes = {}
    edges = {}
    
    # Generiamo un ID per il chunk corrente
    chunk_key = f"chunk_{hash(text)}"
    logger.debug(f"ID chunk generato: {chunk_key}")
    
    # Stampa la risposta completa per debugging
    logger.debug(f"Risposta LLM completa: '{final_result}'")
    
    logger.debug("Elaborazione risultati estrazione iniziale")
    for record in final_result.split(PROMPTS["DEFAULT_RECORD_DELIMITER"]):
        record = record.strip()
        if not record:
            continue
            
        logger.debug(f"Elaborazione record: '{record}'")
        record_attributes = record.split(PROMPTS["DEFAULT_TUPLE_DELIMITER"])
        logger.debug(f"Attributi record: {record_attributes}")
        
        # Handle entity extraction
        try:
            entity_data = await _handle_single_entity_extraction(record_attributes, chunk_key)
            if entity_data:
                entity_name = entity_data["name"]
                if entity_name not in nodes:
                    nodes[entity_name] = []
                nodes[entity_name].append(entity_data)
                logger.debug(f"Entità trovata: {entity_name} ({entity_data['entity_type']})")
        except Exception as e:
            logger.error(f"Errore durante l'estrazione dell'entità: {e}")
            
        # Handle relationship extraction
        try:
            relationship_data = await _handle_single_relationship_extraction(record_attributes, chunk_key)
            if relationship_data:
                edge_key = f"{relationship_data['src_id']}-{relationship_data['tgt_id']}"
                if edge_key not in edges:
                    edges[edge_key] = []
                edges[edge_key].append(relationship_data)
                logger.debug(f"Relazione trovata: {relationship_data['src_id']} -> {relationship_data['tgt_id']} ({relationship_data['keywords']})")
        except Exception as e:
            logger.error(f"Errore durante l'estrazione della relazione: {e}")
    
    logger.info(f"Estrazione iniziale completata: {len(nodes)} entità, {len(edges)} relazioni")
    
    # Process additional gleaning results
    for gleaning_round in range(entity_extract_max_gleaning):
        logger.info(f"Avvio gleaning round {gleaning_round+1}/{entity_extract_max_gleaning}")
        logger.debug("Preparazione prompt per gleaning")
        
        glean_result = await llm_func(
            PROMPTS["entity_continue_extraction"].format(**context_base),
            history=history
        )
        logger.debug(f"Risposta gleaning ricevuta: {len(glean_result)} caratteri")
        
        history.append((PROMPTS["entity_continue_extraction"].format(**context_base), glean_result))
        
        # Process gleaning result
        new_entities = 0
        new_relationships = 0
        
        # Genera un ID per il round di gleaning corrente
        gleaning_chunk_key = f"{chunk_key}_gleaning_{gleaning_round}"
        logger.debug(f"ID chunk gleaning generato: {gleaning_chunk_key}")
        
        logger.debug("Elaborazione risultati gleaning")
        for record in glean_result.split(PROMPTS["DEFAULT_RECORD_DELIMITER"]):
            record = record.strip()
            if not record:
                continue
                
            record_attributes = record.split(PROMPTS["DEFAULT_TUPLE_DELIMITER"])
            
            # Handle entity extraction
            entity_data = await _handle_single_entity_extraction(record_attributes, gleaning_chunk_key)
            if entity_data:
                entity_name = entity_data["name"]
                if entity_name not in nodes:
                    nodes[entity_name] = []
                    new_entities += 1
                nodes[entity_name].append(entity_data)
                logger.debug(f"Gleaning: nuova entità trovata: {entity_name} ({entity_data['entity_type']})")
                
            # Handle relationship extraction
            relationship_data = await _handle_single_relationship_extraction(record_attributes, gleaning_chunk_key)
            if relationship_data:
                edge_key = f"{relationship_data['src_id']}-{relationship_data['tgt_id']}"
                if edge_key not in edges:
                    edges[edge_key] = []
                    new_relationships += 1
                edges[edge_key].append(relationship_data)
                logger.debug(f"Gleaning: nuova relazione trovata: {relationship_data['src_id']} -> {relationship_data['tgt_id']} ({relationship_data['keywords']})")
        
        logger.info(f"Gleaning round {gleaning_round+1} completato: trovate {new_entities} nuove entità, {new_relationships} nuove relazioni")
    
    # Update knowledge graph
    logger.info(f"Aggiornamento knowledge graph con {len(nodes)} entità e {len(edges)} relazioni")
    
    # Aggiunta nodi al grafo
    for entity_name, entities in nodes.items():
        logger.debug(f"Aggiunta/aggiornamento nodo: {entity_name}")
        
        # Prendi il primo tipo di entità come label principale per Neo4j
        # Assicurati che 'entity_type' sia una stringa e non una lista qui
        # Potrebbe essere necessario aggiustare _handle_single_entity_extraction se restituisce una lista
        first_entity_type = entities[0].get("entity_type", "Node") # Usa 'Node' come fallback
        if isinstance(first_entity_type, list):
            first_entity_type = first_entity_type[0] if first_entity_type else "Node"

        node_properties = {
            # Passiamo il tipo di entità come label
            "label": first_entity_type,
            # Conserviamo la lista completa dei tipi come proprietà
            "all_entity_types": list(set(e["entity_type"] for e in entities)),
            "description": entities[0]["description"],
            # Potresti voler aggregare source_id e file_path se provengono da chunk diversi
            "source_ids": list(set(e["source_id"] for e in entities)),
            "file_paths": list(set(e["file_path"] for e in entities)),
            # Aggiungi altre proprietà aggregate se necessario
            "name": entity_name # Assicurati che l'ID/nome sia incluso se non gestito da upsert_node
        }

        logger.debug(f"Proprietà nodo: {node_properties}")
        await knowledge_graph_inst.upsert_node(
            entity_name, # Usa entity_name come ID univoco del nodo
            node_properties
        )

    # Aggiunta archi al grafo
    for edge_key, edge_data_list in edges.items():
        # Assicurati che src_id e tgt_id siano corretti (potrebbero essere stati normalizzati)
        # Prendiamo i dati dal primo elemento estratto per questo arco
        first_edge_data = edge_data_list[0]
        src_id = first_edge_data['src_id']
        tgt_id = first_edge_data['tgt_id']

        logger.debug(f"Aggiunta/aggiornamento arco: {src_id} -> {tgt_id}")

        # Usa le keywords come tipo di relazione, altrimenti default
        relation_type = first_edge_data.get("keywords")
        # Pulisci e formatta le keywords per essere un tipo di relazione valido
        if relation_type:
            relation_type = re.sub(r'\s+', '_', relation_type.strip().upper())
            relation_type = re.sub(r'[^a-zA-Z0-9_]', '', relation_type) # Rimuovi caratteri non validi
        else:
            relation_type = 'RELATED_TO' # Default se non ci sono keywords
        
        logger.debug(f"Tipo relazione: {relation_type}")

        edge_properties = {
            "relation_type": relation_type, # Passa il tipo di relazione
            "description": first_edge_data["description"],
            "keywords_original": first_edge_data.get("keywords", ""), # Conserva le keywords originali
            "weight": first_edge_data["weight"],
            # Aggrega source_id e file_path
            "source_ids": list(set(e["source_id"] for e in edge_data_list)),
            "file_paths": list(set(e["file_path"] for e in edge_data_list)),
        }

        logger.debug(f"Proprietà arco: {edge_properties}")
        await knowledge_graph_inst.upsert_edge(
            src_id,
            tgt_id,
            edge_properties
        )

    # Save changes (index_done_callback potrebbe non essere necessario qui
    # se gli upsert sono transazionali, dipende dall'implementazione)
    # await knowledge_graph_inst.index_done_callback()
    logger.info(f"Knowledge graph aggiornato con {len(nodes)} nodi e {len(edges)} archi.") 