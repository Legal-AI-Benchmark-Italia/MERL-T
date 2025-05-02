import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
import argparse
import json
import random # Importa il modulo random per lo shuffle
import re
from pathlib import Path

# Import delle classi dal modulo graph_extractor
from .src.extractor import extract_entities
from .src.neo4j_storage import Neo4jGraphStorage
# Rimuoviamo l'importazione diretta di PROMPTS qui se non serve più globalmente
# from .src.prompt import PROMPTS 

from src.core.entities.entity_manager import get_entity_manager
from src.core.annotation.db_manager import AnnotationDBManager # Assuming db_manager is accessible
from src.core.config import get_config_manager # For DB paths

# Setup logging con livello INFO di default
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurazione per l'LLM e Neo4j adattata al dominio giuridico
DEFAULT_CONFIG = {
    "language": "Italian",
    "entity_types": [
        "Norma", 
        "ConcettoGiuridico", 
        "SoggettoGiuridico", 
        "AttoGiudiziario", 
        "FonteDiritto", 
        "Dottrina", 
        "Procedura"
    ],
    "entity_extract_max_gleaning": 3,  # Aumentato per migliore estrazione del dominio giuridico
    "llm": {
        "provider": "openrouter",  # Opzioni: "openai" o "openrouter"
        "model": "google/gemini-2.5-flash-preview",  # Modello predefinito
        "temperature": 0.3,  # Ridotto per maggiore precisione nelle estrazioni giuridiche
        "max_tokens": 5000  # Aumentato per gestire risposte più complete
    },
    "neo4j": {
        "uri": "bolt://localhost:7687",
        "user": "neo4j",
        "password": "testtest",  # Modifica con la tua password!
        "database": "neo4j"
    },
    "input_dir": "data/",
    "output_dir": "output/",
    "legal_domain": {
        "enable_legal_validation": True,  # Validazione specifica per dominio giuridico
        "sources_tracking": True,  # Tracciamento delle fonti per trasparenza
        "normative_references": ["Codice Civile", "Codice Penale", "Costituzione", "Codice di procedura civile", "Codice di procedura penale", "Codice del consumo", "Codice dei contratti pubblici"]  # Fonti di base
    },
    # Aggiungiamo i tipi di relazione qui
    "relationship_keywords": [
        "DISCIPLINA", 
        "APPLICA_A", 
        "INTERPRETA", 
        "COMMENTA", 
        "CITA", 
        "DEROGA_A", 
        "MODIFICA", 
        "RELAZIONE_CONCETTUALE", 
        "EMESSO_DA", 
        "FONTE"
    ],
    # Definiamo anche i delimitatori qui per coerenza
    "delimiters": {
        "tuple": "<|>",
        "record": "##",
        "completion": "<|COMPLETE|>"
    }
}

# Funzione per elaborare un singolo chunk di dati
async def process_chunk(
    chunk_data: Dict[str, Any], 
    config: Dict[str, Any], 
    graph_storage: Neo4jGraphStorage, 
    llm_func: callable
) -> None:
    """Elabora un singolo chunk per estrarre entità e relazioni e aggiungerle al grafo."""

    text = chunk_data.get("text")
    chunk_id = chunk_data.get("chunk_id", "unknown_chunk")
    source_doc_path = chunk_data.get("relative_path", "unknown_source")

    if not text or len(text.strip()) < 10: # Soglia minima per evitare testi troppo corti
        logger.warning(f"Chunk {chunk_id} da {source_doc_path} ignorato perché il testo è troppo corto o mancante.")
        return

    logger.info(f"Elaborazione chunk {chunk_id} dal documento {source_doc_path}...")
    logger.debug(f"Lunghezza testo chunk: {len(text)} caratteri")

    source_metadata = {
        "source_doc_path": source_doc_path,
        "chunk_id": chunk_id
    }

    # Verifica connessione al database (potrebbe essere ottimizzato facendolo una sola volta)
    try:
        await graph_storage._driver.verify_connectivity()
    except Exception as e:
        logger.error(f"Errore nella verifica della connessione Neo4j prima di elaborare il chunk {chunk_id}: {e}")
        # Decidere se sollevare l'eccezione o solo loggare e continuare
        raise # Rilancia l'errore per fermare l'elaborazione se il DB non è raggiungibile

    # Estrai entità e relazioni dal testo del chunk
    try:
        # Modifica la chiamata a extract_entities per includere source_metadata
        # Nota: extract_entities dovrà essere modificata per accettare questo nuovo argomento
        extraction_stats = await extract_entities(
            text=text,
            source_metadata=source_metadata, 
            knowledge_graph_inst=graph_storage,
            global_config=config,
            llm_func=llm_func
        )
        if extraction_stats:
             logger.info(f"Chunk {chunk_id} elaborato: {extraction_stats.get('nodes_count', 0)} nodi, {extraction_stats.get('edges_count', 0)} relazioni aggiornate/inserite.")
        else:
             logger.info(f"Chunk {chunk_id} elaborato, nessuna estrazione significativa.")
            
    except Exception as e:
        logger.error(f"Errore durante l'estrazione/inserimento dati per chunk {chunk_id} da {source_doc_path}: {e}", exc_info=True)
        # Decidere se continuare con il prossimo chunk o fermarsi
        # Per ora, logghiamo e continuiamo

# --- Funzioni per Checkpointing --- 

def get_checkpoint_filename(input_jsonl_path: str) -> str:
    """Genera il nome del file di checkpoint basato sul file di input."""
    return input_jsonl_path + ".processed"

def load_processed_chunks(checkpoint_file: str) -> set:
    """Carica il set di chunk_id processati dal file di checkpoint."""
    processed_ids = set()
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    processed_ids = set(data)
                    logger.info(f"Caricati {len(processed_ids)} chunk ID processati da {checkpoint_file}")
                else:
                    logger.warning(f"File di checkpoint {checkpoint_file} non contiene una lista valida. Inizio da zero.")
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Errore durante la lettura o decodifica del file di checkpoint {checkpoint_file}: {e}. Inizio da zero.")
    else:
        logger.info("Nessun file di checkpoint trovato. Inizio elaborazione da zero.")
    return processed_ids

def save_processed_chunks(processed_ids: set, checkpoint_file: str):
    """Salva il set di chunk_id processati nel file di checkpoint."""
    try:
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(list(processed_ids), f) # Salva come lista JSON
        # logger.debug(f"Checkpoint salvato in {checkpoint_file} con {len(processed_ids)} ID.") # Log frequente, forse meglio INFO ogni N chunk?
    except IOError as e:
        logger.error(f"Errore durante il salvataggio del file di checkpoint {checkpoint_file}: {e}")

async def setup_llm_client(config: Dict[str, Any]) -> callable:
    """Inizializza il client LLM (OpenAI o OpenRouter) e restituisce una funzione per chiamare l'API."""
    
    provider = config["llm"]["provider"].lower()
    model = config["llm"]["model"]
    temperature = config["llm"].get("temperature", 0.1)  # Default più basso per precisione giuridica
    max_tokens = config["llm"].get("max_tokens", 2000)  # Default più alto per contenuti giuridici
    
    logger.debug(f"Inizializzazione client LLM: provider={provider}, model={model}")
    
    if provider == "openai":
        try:
            from openai import AsyncOpenAI
        except ImportError:
            logger.error("OpenAI non è installato. Esegui: pip install openai")
            exit(1)
        
        # Verifica che l'API key sia impostata
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY non è impostata. Imposta la variabile d'ambiente.")
            exit(1)
        
        # Inizializza il client OpenAI
        logger.debug("Inizializzazione client AsyncOpenAI")
        client = AsyncOpenAI(api_key=api_key)
        
        # Funzione per chiamare l'API OpenAI
        async def call_llm(prompt: str, history: Optional[List] = None) -> str:
            try:
                messages = []
                
                # Aggiungi la cronologia se presente
                if history:
                    logger.debug(f"Utilizzando cronologia con {len(history)} scambi precedenti")
                    for prev_prompt, prev_response in history:
                        messages.append({"role": "user", "content": prev_prompt})
                        messages.append({"role": "assistant", "content": prev_response})
                
                # Aggiungi il prompt corrente
                logger.debug(f"Aggiunta prompt corrente: {prompt[:50]}...")
                messages.append({"role": "user", "content": prompt})
                
                # Chiama l'API OpenAI
                logger.debug(f"Chiamata API OpenAI con modello {model}")
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                logger.debug(f"Risposta ricevuta: {response.choices[0].message.content[:50]}...")
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"Errore nella chiamata all'API OpenAI: {e}")
                return ""
        
        return call_llm
    
    elif provider == "openrouter":
        try:
            import httpx
        except ImportError:
            logger.error("httpx non è installato. Esegui: pip install httpx")
            exit(1)
        
        # Verifica che l'API key sia impostata
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            logger.error("OPENROUTER_API_KEY non è impostata. Imposta la variabile d'ambiente.")
            exit(1)
        
        # Funzione per chiamare l'API OpenRouter
        async def call_llm(prompt: str, history: Optional[List] = None) -> str:
            try:
                messages = []
                
                # Aggiungi la cronologia se presente
                if history:
                    logger.debug(f"Utilizzando cronologia con {len(history)} scambi precedenti")
                    for prev_prompt, prev_response in history:
                        messages.append({"role": "user", "content": prev_prompt})
                        messages.append({"role": "assistant", "content": prev_response})
                
                # Aggiungi il prompt corrente
                logger.debug(f"Aggiunta prompt corrente: {prompt[:50]}...")
                messages.append({"role": "user", "content": prompt})
                
                # Prepara i dati per la richiesta OpenRouter
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://laibit.org"  # Sito web del progetto
                }
                
                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                
                # Chiama l'API OpenRouter
                logger.debug("Invio richiesta a OpenRouter API")
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    
                    response.raise_for_status()
                    data = response.json()
                    
                # Controlla la presenza della chiave 'choices' prima di accedervi
                if "choices" in data and data["choices"]:
                    content = data["choices"][0]["message"]["content"]
                    logger.debug(f"Risposta ricevuta da OpenRouter: {content[:50]}...")
                    return content
                else:
                    # Logga l'intera risposta se 'choices' manca o è vuota
                    logger.error(f"Risposta inattesa da OpenRouter (manca 'choices' o è vuota): {data}")
                    # Potresti voler restituire un errore specifico o una stringa vuota
                    # a seconda di come vuoi gestire l'errore a monte.
                    # Per ora, restituiamo stringa vuota per coerenza con altri errori.
                    return ""
            except httpx.HTTPStatusError as e:
                logger.error(f"Errore HTTP nella chiamata all'API OpenRouter: {e.response.status_code} - {e.response.text}")
                return ""
            except httpx.RequestError as e:
                logger.error(f"Errore di rete nella chiamata all'API OpenRouter: {e}")
                return ""
            except json.JSONDecodeError as e:
                logger.error(f"Errore nel decodificare la risposta JSON da OpenRouter: {e}")
                return ""
            except Exception as e:
                # Aggiungi exc_info=True per ottenere il traceback completo per errori generici
                logger.error(f"Errore generico nella chiamata all'API OpenRouter: {e}", exc_info=True)
                return ""
        
        return call_llm
    
    else:
        logger.error(f"Provider LLM non supportato: {provider}. Usa 'openai' o 'openrouter'.")
        exit(1)

def update_config_from_entity_manager(config):
    """Aggiorna la configurazione del knowledge graph con i dati dell'EntityManager."""
    entity_manager = get_entity_manager()
    
    # Ottieni tutte le entità
    entities = entity_manager.get_all_entities()
    
    # Aggiorna tipi di entità nella configurazione
    entity_types = [entity.name for entity in entities]
    if entity_types:
        config["entity_types"] = entity_types
    
    # Aggiorna le categorie di entità
    categories = entity_manager.get_categories()
    if categories:
        config["entity_categories"] = categories
    
    # Aggiorna anche le relazioni se disponibili
    # Nota: questo richiederebbe una estensione dell'EntityManager
    # per supportare la definizione di relazioni
    
    return config

async def apply_changes_to_graph(proposal_type, data):
    """
    Applica modifiche al grafo basate su una proposta approvata.
    
    Args:
        proposal_type: Tipo di proposta ('add', 'modify', 'delete')
        data: Dati per la modifica (nodi o relazioni)
        
    Returns:
        dict: Risultato dell'operazione
    """
    try:
        from src.retrival.knowledge_graph.src.neo4j_storage import Neo4jGraphStorage
        
        # Inizializza il graph storage
        graph_storage = Neo4jGraphStorage()
        await graph_storage.initialize()
        
        result = {"success": False, "message": "", "details": {}}
        
        if proposal_type == 'add':
            # Aggiunta di nodi o relazioni
            if 'nodes' in data:
                # Aggiunta nodi
                added_nodes = await graph_storage.add_nodes(data['nodes'])
                result['details']['added_nodes'] = len(added_nodes)
                result['success'] = True
                
            if 'edges' in data:
                # Aggiunta relazioni
                added_edges = await graph_storage.add_relationships(data['edges'])
                result['details']['added_edges'] = len(added_edges)
                result['success'] = True
                
        elif proposal_type == 'modify':
            # Modifica nodi o relazioni
            if 'nodes' in data:
                # Modifica nodi
                updated_nodes = await graph_storage.update_nodes(data['nodes'])
                result['details']['updated_nodes'] = len(updated_nodes)
                result['success'] = True
                
            if 'edges' in data:
                # Modifica relazioni
                updated_edges = await graph_storage.update_relationships(data['edges'])
                result['details']['updated_edges'] = len(updated_edges)
                result['success'] = True
                
        elif proposal_type == 'delete':
            # Eliminazione nodi o relazioni
            if 'nodes' in data:
                # Elimina nodi
                deleted_nodes = await graph_storage.delete_nodes([node['id'] for node in data['nodes']])
                result['details']['deleted_nodes'] = len(deleted_nodes)
                result['success'] = True
                
            if 'edges' in data:
                # Elimina relazioni
                deleted_edges = await graph_storage.delete_relationships([edge['id'] for edge in data['edges']])
                result['details']['deleted_edges'] = len(deleted_edges)
                result['success'] = True
        else:
            result['message'] = f"Tipo di proposta non supportato: {proposal_type}"
            
        if result['success']:
            result['message'] = "Modifiche applicate con successo al grafo"
        
        # Chiudi la connessione
        await graph_storage.close()
        
        return result
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Errore nell'applicazione delle modifiche al grafo: {e}\n{error_details}")
        return {
            "success": False,
            "message": f"Errore nell'applicazione delle modifiche: {str(e)}",
            "details": {"error_trace": error_details}
        }

async def create_node_centric_chunks(
    num_chunks: int = 10, 
    seed_label: str = 'Norma', 
    user_id: str = 'system', 
    force_recreate: bool = False
) -> Dict[str, int]:
    """Crea chunk di validazione basati sul vicinato a 1 hop dei nodi seed."""
    logger.info(f"Avvio creazione di {num_chunks} chunk node-centric basati su label '{seed_label}'.")
    
    created_count = 0
    skipped_count = 0
    error_count = 0
    
    # Setup connections
    config_manager = get_config_manager()
    neo4j_params = config_manager.get_neo4j_connection_params()
    # Retrieve DB params directly using get()
    backup_dir = config_manager.get('database.backup_dir', 'data/backups') # Provide a default path
    
    # Use context managers for connections
    async with Neo4jGraphStorage(**neo4j_params) as neo4j_storage:
        # Ensure paths are absolute or relative to project root if needed
        # (This logic might be better placed within AnnotationDBManager or config manager)
        project_root = Path(__file__).resolve().parent.parent.parent # Adjust based on graph_main.py location
        backup_dir = os.path.join(project_root, backup_dir)
        
        # Initialize AnnotationDBManager without arguments
        # It will now read PostgreSQL connection details from the config manager internally
        db_manager = AnnotationDBManager()
        
        try:
            # 1. Get potential seed node IDs
            logger.debug(f"Recupero ID dei nodi seed con label: {seed_label}")
            # Ensure label is safe for query
            safe_seed_label = re.sub(r'[^a-zA-Z0-9_]', '', seed_label)
            if not safe_seed_label:
                logger.error("Label seme non valida dopo sanificazione.")
                return {"created": 0, "skipped": 0, "errors": 1}
                
            seed_query = f"MATCH (n:{safe_seed_label}) RETURN n.id as id"
            seed_records = await neo4j_storage._execute_read(seed_query)
            all_seed_ids = [record["id"] for record in seed_records if record["id"]]
            
            if not all_seed_ids:
                logger.warning(f"Nessun nodo trovato con label '{safe_seed_label}' per generare chunk.")
                return {"created": 0, "skipped": 0, "errors": 0}
            
            logger.info(f"Trovati {len(all_seed_ids)} potenziali nodi seed.")
            
            # 2. Sample and create chunks
            potential_seeds = random.sample(all_seed_ids, min(num_chunks * 2, len(all_seed_ids))) # Sample more to account for skips
            
            for seed_id in potential_seeds:
                if created_count >= num_chunks:
                    break # Reached target number
                    
                try:
                    # 3. Check for existing chunk
                    if not force_recreate and db_manager.check_chunk_exists_for_seed(seed_id):
                        logger.debug(f"Chunk per seed {seed_id} già esistente, saltato.")
                        skipped_count += 1
                        continue
                    
                    # 4. Get neighborhood data
                    logger.debug(f"Recupero vicinato per seed: {seed_id}")
                    neighborhood_data = await neo4j_storage.get_node_neighborhood(seed_id)
                    
                    if not neighborhood_data:
                        logger.warning(f"Impossibile recuperare il vicinato per {seed_id}, chunk non creato.")
                        error_count += 1
                        continue
                        
                    # 5. Format and save chunk
                    seed_node_info = next((n for n in neighborhood_data["nodes"] if n["id"] == seed_id), None)
                    title = f"Vicinato di {safe_seed_label}: {seed_node_info.get('name', seed_id) if seed_node_info else seed_id}"
                    description = f"Chunk per validare il nodo {seed_id} e le sue connessioni dirette."
                    
                    chunk_payload = {
                        "title": title,
                        "description": description,
                        "chunk_type": "subgraph",
                        "data": neighborhood_data,
                        "status": "pending",
                        # 'created_by' will be set by save_graph_chunk if user_id is passed
                    }
                    
                    logger.debug(f"Salvataggio chunk per seed: {seed_id}")
                    saved_chunk_id = db_manager.save_graph_chunk(chunk_payload, user_id=user_id, seed_node_id=seed_id)
                    
                    if saved_chunk_id:
                        logger.info(f"Chunk {saved_chunk_id} creato per seed {seed_id}")
                        created_count += 1
                    else:
                        logger.error(f"Errore nel salvataggio del chunk per seed {seed_id}")
                        error_count += 1
                        
                except Exception as e_inner:
                    logger.error(f"Errore durante la creazione del chunk per seed {seed_id}: {e_inner}")
                    logger.exception(e_inner)
                    error_count += 1
        
        except Exception as e_outer:
            logger.error(f"Errore durante il processo di creazione chunk: {e_outer}")
            logger.exception(e_outer)
            error_count += 1 # Count general errors too
        
    # Ensure db_manager connection is implicitly closed by its context manager if it had one
    # Neo4j connection is closed by the async with block
            
    logger.info(f"Creazione chunk completata. Creati: {created_count}, Saltati: {skipped_count}, Errori: {error_count}")
    return {"created": created_count, "skipped": skipped_count, "errors": error_count}

async def main():
    # Parsing degli argomenti da linea di comando
    parser = argparse.ArgumentParser(description="Estrazione di un grafo di conoscenza giuridica da testo usando un LLM")
    parser.add_argument("--config", type=str, help="Percorso al file di configurazione JSON")
    parser.add_argument("--input-jsonl", type=str, required=True, 
                        help="Percorso al file JSONL contenente i chunk di testo (output del pdf_chunker)")
    parser.add_argument("--log-level", type=str, default="INFO", 
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Livello di logging (default: INFO)")
    parser.add_argument("--limit", type=int, default=None, 
                        help="Limita l'elaborazione ai primi N chunk (dopo shuffle se applicato).")
    parser.add_argument("--shuffle", action="store_true", 
                        help="Elabora i chunk in ordine casuale.")
    args = parser.parse_args()
    
    # Imposta il livello di logging in base all'argomento
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        logger.error(f"Livello di logging non valido: {args.log_level}")
        return
    
    logger.setLevel(numeric_level)
    logger.debug(f"Livello di logging impostato a: {args.log_level}")
    
    # Carica la configurazione base
    config = DEFAULT_CONFIG.copy()
    if args.config:
        try:
            logger.debug(f"Caricamento configurazione da file: {args.config}")
            with open(args.config, 'r') as f:
                user_config = json.load(f)
                config.update(user_config)
                logger.debug(f"Configurazione aggiornata: {config}")
        except Exception as e:
            logger.error(f"Errore nel caricamento del file di configurazione: {e}")
        return
    
    # Aggiorna con i dati dell'EntityManager
    config = update_config_from_entity_manager(config)
    
    # Inizializza la funzione LLM
    logger.info("Inizializzazione funzione LLM...")
    llm_func = await setup_llm_client(config)
    
    # Inizializza il Neo4j storage
    neo4j_config = config.get("neo4j", {})
    logger.info(f"Inizializzazione Neo4j storage per database '{neo4j_config.get('database', 'N/A')}' su uri '{neo4j_config.get('uri', 'N/A')}'")
    storage = Neo4jGraphStorage(
        uri=neo4j_config["uri"],
        user=neo4j_config["user"],
        password=neo4j_config["password"],
        database=neo4j_config["database"]
    )
    
    try:
        # Inizializza la connessione
        logger.debug("Inizializzazione connessione Neo4j")
        await storage.initialize()
        
        # La logica di input ora legge dal file JSONL
        input_jsonl_path = args.input_jsonl
        if not os.path.exists(input_jsonl_path):
            logger.error(f"File di input JSONL non trovato: {input_jsonl_path}")
            return
        
        # Carica i chunk già processati
        checkpoint_file = get_checkpoint_filename(input_jsonl_path)
        processed_chunk_ids = load_processed_chunks(checkpoint_file)
        
        # Elabora il testo
        logger.info(f"Inizio elaborazione chunk dal file: {input_jsonl_path}")
        processed_chunks = 0
        chunks_skipped = 0
        try:
            with open(input_jsonl_path, 'r', encoding='utf-8') as f:
                # 1. Leggi tutti i chunk in memoria
                all_chunks_data = []
                logger.info(f"Lettura di tutti i chunk da {input_jsonl_path}...")
                for line in f:
                    try:
                        chunk_data = json.loads(line)
                        all_chunks_data.append(chunk_data)
                    except json.JSONDecodeError as json_err:
                         logger.error(f"Errore nel decodificare la riga JSON durante la lettura iniziale: {json_err}. Riga saltata: {line.strip()[:100]}...")
                logger.info(f"Letti {len(all_chunks_data)} chunk totali.")

                # 2. Shuffle (se richiesto)
                if args.shuffle:
                    logger.info("Randomizzazione dell'ordine dei chunk...")
                    random.shuffle(all_chunks_data)
                    logger.info("Ordine dei chunk randomizzato.")

                # 3. Limita (se richiesto)
                chunks_to_process = all_chunks_data
                if args.limit is not None and args.limit > 0:
                    logger.info(f"Applicazione limite: verranno elaborati al massimo {args.limit} chunk.")
                    chunks_to_process = all_chunks_data[:args.limit]
                else:
                    logger.info("Nessun limite applicato, elaborazione di tutti i chunk letti (o shuffled).")

                # 4. Ciclo di elaborazione sulla lista filtrata/shuffled
                total_to_process = len(chunks_to_process)
                logger.info(f"Inizio elaborazione di {total_to_process} chunk...")
                for i, chunk_data in enumerate(chunks_to_process):
                    try:
                        chunk_id = chunk_data.get("chunk_id")

                        # >>> Checkpoint Check <<<
                        if chunk_id and chunk_id in processed_chunk_ids:
                            # logger.debug(f"Chunk {chunk_id} già processato, saltato.") # Potrebbe essere troppo verboso
                            chunks_skipped += 1
                            if (processed_chunks + chunks_skipped) % 100 == 0: # Logga progresso anche per skipped
                                logger.info(f"Progresso: {processed_chunks} processati, {chunks_skipped} saltati di {total_to_process} previsti.")
                            continue

                        # Elabora il chunk se non è stato saltato
                        await process_chunk(chunk_data, config, storage, llm_func)

                        # >>> Checkpoint Save <<<
                        if chunk_id:
                            processed_chunk_ids.add(chunk_id)
                            save_processed_chunks(processed_chunk_ids, checkpoint_file)
                            if (processed_chunks + 1) % 100 == 0: # Logga progresso meno frequentemente?
                                logger.info(f"Progresso: {processed_chunks + 1} processati, {chunks_skipped} saltati di {total_to_process} previsti. Checkpoint salvato.")

                        processed_chunks += 1 # Incrementa solo dopo successo

                    except Exception as chunk_err:
                        logger.error(f"Errore imprevisto durante l'elaborazione del chunk {chunk_id or '(ID mancante)'}: {chunk_err}", exc_info=True)
                        # Si potrebbe aggiungere logica per riprovare o fermare l'intero processo
        except Exception as file_err:
            logger.error(f"Errore durante la lettura del file JSONL {input_jsonl_path}: {file_err}")
            return # Interrompi se non possiamo leggere il file
        
        # Salva lo stato finale (anche se potrebbe essere già stato salvato dopo l'ultimo chunk)
        checkpoint_file = get_checkpoint_filename(input_jsonl_path)
        save_processed_chunks(processed_chunk_ids, checkpoint_file)
        logger.info(f"Checkpoint finale salvato.")

        logger.info(f"Elaborazione completata. Chunk processati in questa esecuzione: {processed_chunks}. Chunk saltati (già processati): {chunks_skipped}.")
        
        # Stampa alcune statistiche
        logger.info("Statistiche finali del grafo:")
        labels = await storage.get_all_labels()
        logger.info(f"Tipi di entità nel knowledge graph: {', '.join(labels)}")
        
    except Exception as e:
        logger.error(f"Errore durante l'elaborazione: {e}", exc_info=True)
    finally:
        # Chiudi la connessione
        logger.debug("Chiusura connessione Neo4j")
        await storage.close()

if __name__ == "__main__":
    logger.debug("Avvio applicazione MERL-T Knowledge Graph Extractor")
    asyncio.run(main())