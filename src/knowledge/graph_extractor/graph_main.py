import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
import argparse
import json

# Import delle classi dal modulo graph_extractor
from .src.extractor import extract_entities
from .src.neo4j_storage import Neo4jGraphStorage
from .src.prompt import PROMPTS

# Setup logging con livello DEBUG di default
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurazione per l'LLM e Neo4j
DEFAULT_CONFIG = {
    "language": "Italian",
    "entity_types": ["organizzazione", "persona", "luogo", "evento", "categoria"],
    "entity_extract_max_gleaning": 2,
    "llm": {
        "provider": "openrouter",  # Opzioni: "openai" o "openrouter"
        "model": "google/gemini-2.0-flash-exp:free",
        "temperature": 0.2,
        "max_tokens": 1500
    },
    "neo4j": {
        "uri": "bolt://localhost:7687",
        "user": "neo4j",
        "password": "testtest",  # Modifica con la tua password!
        "database": "neo4j"
    },
    "input_dir": "data/",
    "output_dir": "output/",
}

async def setup_llm_client(config: Dict[str, Any]) -> callable:
    """Inizializza il client LLM (OpenAI o OpenRouter) e restituisce una funzione per chiamare l'API."""
    
    provider = config["llm"]["provider"].lower()
    model = config["llm"]["model"]
    temperature = config["llm"].get("temperature", 0.2)
    max_tokens = config["llm"].get("max_tokens", 1500)
    
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
        
        # Inizializza il client httpx
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
                    "HTTP-Referer": "https://laibit.org" # Sostituisci con un URL reale se disponibile
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
                    
                logger.debug(f"Risposta ricevuta da OpenRouter: {data['choices'][0]['message']['content'][:50]}...")
                return data["choices"][0]["message"]["content"]
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
                logger.error(f"Errore nella chiamata all'API OpenRouter: {e}")
                return ""
        
        return call_llm
    
    else:
        logger.error(f"Provider LLM non supportato: {provider}. Usa 'openai' o 'openrouter'.")
        exit(1)

async def process_text(text: str, config: Dict[str, Any], graph_storage: Neo4jGraphStorage, llm_func: callable) -> None:
    """Elabora un testo per estrarre entità e relazioni e aggiungerle al grafo."""
    logger.info("Elaborazione del testo per l'estrazione di entità e relazioni...")
    logger.debug(f"Lunghezza testo: {len(text)} caratteri, primi 100 caratteri: {text[:100]}...")
    
    # Verifica connessione al database
    try:
        logger.info("Verifica connessione al database Neo4j...")
        connected = await graph_storage._driver.verify_connectivity()
        logger.info(f"Connessione a Neo4j verificata: {connected}")
    except Exception as e:
        logger.error(f"Errore nella verifica della connessione Neo4j: {e}")
        raise
    
    # Estrai entità e relazioni
    try:
        extracted_data = await extract_entities(
            text=text,
            knowledge_graph_inst=graph_storage,
            global_config=config,
            llm_func=llm_func
        )
        logger.info("Elaborazione completata. Grafo aggiornato.")
        
        # Verifica che dati siano stati effettivamente aggiunti
        labels = await graph_storage.get_all_labels()
        logger.info(f"Etichette nel database dopo l'estrazione: {labels}")
        
        # Esegui una query di conteggio per vedere se ci sono nodi
        async with graph_storage._driver.session(database=graph_storage._database) as session:
            count_query = "MATCH (n) RETURN count(n) as node_count"
            result = await session.run(count_query)
            record = await result.single()
            node_count = record["node_count"]
            logger.info(f"Numero totale di nodi nel database: {node_count}")
    
    except Exception as e:
        logger.error(f"Errore durante l'estrazione/inserimento dati: {e}", exc_info=True)
        raise

async def main():
    # Parsing degli argomenti da linea di comando
    parser = argparse.ArgumentParser(description="Estrazione di un grafo di conoscenza da testo usando un LLM")
    parser.add_argument("--config", type=str, help="Percorso al file di configurazione JSON")
    parser.add_argument("--text", type=str, help="Testo da elaborare direttamente")
    parser.add_argument("--file", type=str, help="File di testo da elaborare")
    parser.add_argument("--log-level", type=str, default="DEBUG", 
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Livello di logging (default: DEBUG)")
    args = parser.parse_args()
    
    # Imposta il livello di logging in base all'argomento
    numeric_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(numeric_level, int):
        logger.error(f"Livello di logging non valido: {args.log_level}")
        return
    
    logger.setLevel(numeric_level)
    logger.debug(f"Livello di logging impostato a: {args.log_level}")
    
    # Carica la configurazione
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
    
    # Ottieni il testo da elaborare
    text = ""
    if args.text:
        logger.debug("Utilizzo testo fornito direttamente come argomento")
        text = args.text
    elif args.file:
        try:
            logger.debug(f"Lettura testo dal file: {args.file}")
            with open(args.file, 'r', encoding='utf-8') as f:
                text = f.read()
                logger.debug(f"Letti {len(text)} caratteri dal file")
        except Exception as e:
            logger.error(f"Errore nella lettura del file: {e}")
            return
    else:
        logger.error("Specifica --text o --file per fornire il testo da elaborare")
        return
    
    # Verifica che il testo non sia vuoto
    if not text.strip():
        logger.error("Il testo da elaborare è vuoto")
        return
    
    # Inizializza la funzione LLM
    logger.debug("Inizializzazione funzione LLM")
    llm_func = await setup_llm_client(config)
    
    # Inizializza il Neo4j storage
    neo4j_config = config["neo4j"]
    logger.debug(f"Inizializzazione Neo4j storage con uri={neo4j_config['uri']}, user={neo4j_config['user']}, database={neo4j_config['database']}")
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
        
        # Elabora il testo
        logger.debug("Avvio elaborazione testo")
        await process_text(text, config, storage, llm_func)
        
        # Stampa alcune statistiche
        logger.info("Estrazione e creazione del grafo completata.")
        labels = await storage.get_all_labels()
        logger.info(f"Tipi di entità nel grafo: {', '.join(labels)}")
        
    except Exception as e:
        logger.error(f"Errore durante l'elaborazione: {e}", exc_info=True)
    finally:
        # Chiudi la connessione
        logger.debug("Chiusura connessione Neo4j")
        await storage.close()

if __name__ == "__main__":
    logger.debug("Avvio applicazione")
    asyncio.run(main())
