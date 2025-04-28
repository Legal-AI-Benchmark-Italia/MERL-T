**Struttura Generale del Progetto**

Questo codice è progettato per estrarre entità giuridiche e le relazioni tra di esse da un testo fornito, utilizzando un Large Language Model (LLM) accessibili tramite OpenRouter. Le entità e le relazioni estratte vengono poi memorizzate in un database a grafo Neo4j.

**1. `requirements.txt`** ^^

Questo file elenca le librerie Python necessarie per eseguire il codice:

* **openai** : Per interagire con l'API di OpenAI.
* **neo4j** : Il driver ufficiale per interagire con il database Neo4j.
* **python-dotenv** : Per caricare variabili d'ambiente (come le API keys) da un file `.env`.
* **pandas, numpy** : Librerie per la manipolazione e l'analisi dei dati (potenzialmente usate per elaborazioni future o analisi del grafo, anche se non direttamente nel flusso principale mostrato).
* **tqdm** : Per mostrare barre di avanzamento (utile per processi lunghi, anche se non esplicitamente usata nel codice fornito).
* **loguru** : Una libreria per un logging più semplice e potente (anche se il codice principale usa il modulo standard `logging`).

**2. `graph_extractor/types.py`**

Questo file definisce le strutture dati fondamentali per rappresentare il grafo della conoscenza:

* **`KnowledgeGraphNode`** : Una `dataclass` per rappresentare un nodo (entità) nel grafo. Contiene:
* `id`: Identificatore univoco del nodo (tipicamente il nome normalizzato dell'entità).
* `labels`: Una lista di etichette che categorizzano il nodo (es., ["Person", "Employee"]).
* `properties`: Un dizionario contenente attributi aggiuntivi del nodo (es., {"description": "...", "source_id": "..."}).
* **`KnowledgeGraphEdge`** : Una `dataclass` per rappresentare un arco (relazione) nel grafo. Contiene:
* `id`: Identificatore univoco dell'arco.
* `type`: Il tipo di relazione (es., "WORKS_AT", "LOCATED_IN").
* `source`: L'ID del nodo di origine.
* `target`: L'ID del nodo di destinazione.
* `properties`: Un dizionario con attributi dell'arco (es., {"description": "...", "weight": 1.0}).
* **`KnowledgeGraph`** : Una `dataclass` che aggrega nodi e archi per rappresentare l'intero grafo o un suo sottografo. Contiene:
* `nodes`: Una lista di oggetti `KnowledgeGraphNode`.
* `edges`: Una lista di oggetti `KnowledgeGraphEdge`.
* `is_truncated`: Un flag booleano (non usato nel codice fornito, ma potrebbe indicare se il grafo è incompleto).

**3. `graph_extractor/base.py`**

Questo file definisce una classe base astratta per l'archiviazione del grafo:

* **`BaseGraphStorage`** : Specifica l'interfaccia che qualsiasi implementazione di storage per il grafo deve seguire. Definisce metodi astratti (che devono essere implementati dalle sottoclassi) per operazioni comuni come:
* `initialize()`: Inizializzare la connessione allo storage.
* `has_node(node_id)`, `has_edge(source, target)`: Verificare l'esistenza di nodi/archi.
* `get_node(node_id)`, `get_edge(source, target)`: Recuperare dati di nodi/archi.
* `get_node_edges(source_node_id)`: Recuperare gli archi collegati a un nodo.
* `upsert_node(node_id, data)`, `upsert_edge(source, target, data)`: Inserire o aggiornare nodi/archi (Upsert = Update or Insert).
* `delete_node(node_id)`, `remove_nodes(nodes)`, `remove_edges(edges)`: Eliminare nodi/archi.
* `get_all_labels()`: Ottenere tutte le etichette dei nodi.
* `get_knowledge_graph(...)`: Estrarre un sottografo.
* `index_done_callback()`: Funzione chiamata dopo un'operazione di indicizzazione (il significato esatto dipende dall'implementazione).
* `drop()`: Eliminare tutti i dati dal grafo.

**4. `graph_extractor/neo4j_storage.py`**

Questa è l'implementazione concreta di `BaseGraphStorage` per Neo4j:

* **`Neo4jGraphStorage`** : Eredita da `BaseGraphStorage` e implementa tutti i suoi metodi astratti usando il driver `neo4j` per interagire con un database Neo4j.
* `__init__(uri, user, password, database)`: Inizializza la classe con i dettagli di connessione a Neo4j.
* `initialize()`: Stabilisce la connessione asincrona al database usando `AsyncGraphDatabase.driver` e verifica la connettività. Chiama anche `_create_constraints` per creare indici/constraint.
* `_create_constraints()`: Tenta di creare un constraint sull'unicità della proprietà `id` dei nodi per migliorare le prestazioni delle query `MERGE`.
* `close()`: Chiude la connessione al driver Neo4j.
* `_execute_read(query, params)`, `_execute_write(query, params)`: Metodi helper interni (privati) per eseguire query Cypher di lettura e scrittura in modo asincrono.
* Le implementazioni dei metodi `has_node`, `get_node`, `upsert_node`, `upsert_edge`, ecc., traducono le operazioni richieste in query Cypher specifiche (es., `MATCH`, `MERGE`, `DELETE`) e le eseguono usando i metodi `_execute_read` o `_execute_write`.
* `upsert_node` e `upsert_edge` usano `MERGE` per creare il nodo/arco se non esiste, o aggiornarne le proprietà (`SET n += $props`) se esiste già. Gestiscono anche l'estrazione della `label` (per i nodi) o del `relation_type` (per gli archi) dai dati forniti, usando dei valori predefiniti ('Node', 'RELATED_TO') se non specificati.
* **Importante:** Grazie alla logica di aggregazione in `extractor.py`, questi metodi ora ricevono proprietà che possono essere liste (es., `source_doc_paths`, `chunk_ids`). La strategia `SET += $props` sovrascrive le proprietà nel database con quelle aggiornate e aggregate fornite da `extractor.py`.
* `get_knowledge_graph(...)`: Recupera un sottografo eseguendo una query Cypher che cerca percorsi (`MATCH p=(n)-[...]-(m)`) fino a una certa profondità e restituisce i dati dei percorsi trovati.
* `drop()`: Esegue `MATCH (n) DETACH DELETE n` per cancellare tutti i nodi e le relazioni nel database specificato (operazione pericolosa!).
* Implementa `__aenter__` e `__aexit__` per permettere l'uso con `async with`, garantendo che la connessione venga inizializzata e chiusa correttamente.
* Include una funzione `main()` di esempio (commentata di default) per dimostrare come usare la classe.

**5. `graph_extractor/prompt.py`**

Questo file definisce i template dei prompt inviati all'LLM:

* Contiene costanti per i delimitatori usati nella formattazione dell'output dell'LLM (`DEFAULT_TUPLE_DELIMITER`, `DEFAULT_RECORD_DELIMITER`, `DEFAULT_COMPLETION_DELIMITER`).
* `PROMPTS`: Un dizionario che contiene le stringhe dei prompt.
  * `entity_extraction`: Il prompt principale. Spiega all'LLM l'obiettivo (estrarre entità e relazioni), i tipi di entità da cercare (`{entity_types}`), i passi da seguire, il formato di output richiesto (usando i delimitatori), e la lingua (`{language}`). Include placeholders per il testo di input (`{input_text}`) e potenziali esempi (`{examples}`, anche se non forniti nel codice).
  * `entity_continue_extraction`: Un prompt più breve per chiedere all'LLM di continuare l'estrazione dallo stesso testo, cercando elementi mancanti, usando lo stesso formato.
  * `entity_if_loop_extraction`: Un prompt per chiedere all'LLM se ci sono altri elementi da estrarre (sembra meno centrale nel flusso attuale).
* `PROMPTS_TEMPLATES`: Un dizionario che contiene le *template strings* per i prompt. Queste stringhe includono placeholder come `{language}`, `{entity_types_str}`, `{relationship_keywords_str}`, `{tuple_delimiter}`, `{record_delimiter}`, `{completion_delimiter}`, `{input_text}`, ecc.
* `get_formatted_prompt(prompt_key, config, **kwargs)`: Una funzione che prende la chiave di un template (es. "entity_extraction"), un dizionario di configurazione (`config`), e argomenti opzionali. Recupera il template corrispondente, estrae i valori necessari (lingua, tipi di entità, parole chiave delle relazioni, delimitatori) dalla configurazione, formatta il template sostituendo i placeholder, e restituisce la stringa del prompt completa e pronta per essere inviata all'LLM.
* I tipi di entità, le parole chiave delle relazioni e i delimitatori non sono più hardcoded qui, ma vengono forniti dinamicamente tramite l'oggetto `config`.

**6. `graph_extractor/extractor.py`**

Questo è il cuore logico dell'estrazione:

* Funzioni helper:
  * `clean_str(s)`: Rimuove spazi bianchi e virgolette iniziali/finali da una stringa.
  * `normalize_extracted_info(info, is_entity)`: Pulisce una stringa e, se è un nome di entità, mette in maiuscolo la prima lettera di ogni parola.
  * `is_float_regex(s)`: Controlla se una stringa rappresenta un numero decimale.
  * `_handle_single_entity_extraction(record_attributes, ...)`: Prende gli attributi di un record estratto dall'LLM, verifica se è un'entità, estrae nome, tipo e descrizione, li normalizza e li restituisce come dizionario.
  * `_handle_single_relationship_extraction(record_attributes, ...)`: Simile alla precedente, ma per le relazioni. Estrae sorgente, destinazione, descrizione, parole chiave e forza (peso), li normalizza e restituisce un dizionario.
* **`extract_entities(text, knowledge_graph_inst, global_config, llm_func, ...)`** : La funzione principale (asincrona) che orchestra l'estrazione.

*   **Firma Modificata:** Accetta ora un argomento `source_metadata` (un dizionario) contenente informazioni sulla fonte del `text` (es., `source_doc_path`, `chunk_id`). Restituisce un dizionario con statistiche sull'estrazione.
1.  Recupera la configurazione (numero massimo di passaggi di "gleaning", lingua, tipi di entità, parole chiave relazioni, delimitatori) dal dizionario `global_config`.
2.  Usa la funzione `get_formatted_prompt` (importata da `prompt.py`) per generare dinamicamente i prompt necessari ("entity_extraction", "entity_continue_extraction"), passando `global_config` per popolare i placeholder.
3.  Chiama la funzione `llm_func` (passata come argomento, rappresenta la chiamata all'API OpenAI o OpenRouter configurata in `graph_main.py`) con i prompt generati dinamicamente.
4.  Salva la coppia prompt/risposta nella `history`.
5.  **Elaborazione e Aggregazione:** Elabora le risposte dell'LLM (sia iniziale che dai cicli di gleaning):
    *   Divide la risposta in record e attributi usando i delimitatori dalla configurazione.
    *   Chiama `_handle_single_entity_extraction` e `_handle_single_relationship_extraction`, passando anche i `source_metadata` del chunk corrente.
    *   **Aggrega** i dati estratti in dizionari interni (`aggregated_nodes`, `aggregated_edges`). Se un'entità o relazione viene trovata più volte (anche da cicli di gleaning diversi *nello stesso chunk*), le sue informazioni vengono arricchite:
        *   Le proprietà di tracciabilità (`source_doc_paths`, `chunk_ids`) vengono memorizzate come **liste** contenenti tutti i riferimenti univoci ai chunk da cui l'informazione proviene.
        *   Altre proprietà (es. `description`, `weight`) vengono aggiornate secondo una strategia definita (es. mantieni la prima descrizione, prendi il peso massimo).
6.  Esegue un ciclo per i passaggi aggiuntivi ("gleaning"):
    * Genera il prompt `entity_continue_extraction` usando `get_formatted_prompt`.
    * Chiama `llm_func` con il prompt generato e la `history` precedente.
    * Aggiunge la nuova coppia prompt/risposta alla `history`.
    * Elabora la risposta del "gleaning", aggregando le informazioni nei dizionari `aggregated_nodes` e `aggregated_edges` come descritto al punto 5.
7.  **Aggiornamento Grafo:** Al termine dell'elaborazione del chunk (inclusi i cicli di gleaning), itera sui dizionari `aggregated_nodes` e `aggregated_edges`:
    * Per ogni entità (nodo), prepara un dizionario `node_properties` (usando la label Neo4j già mappata) e chiama `knowledge_graph_inst.upsert_node()`. Usa il nome dell'entità normalizzato come `node_id`.
    * Per ogni relazione (arco), prepara un dizionario `edge_properties`. Il tipo di relazione Neo4j (`relation_type`) viene preso dal tipo normalizzato precedentemente (`legal_relation_type`). Chiama `knowledge_graph_inst.upsert_edge()`.
    * **Importante:** Ai metodi `upsert_node` e `upsert_edge` viene passato l'intero dizionario *aggregato*, contenente le liste complete per la tracciabilità (`source_doc_paths`, `chunk_ids`).
8.  Restituisce statistiche sull'estrazione per il chunk processato.

**7. `graph_main.py`**

Lo script principale che esegue l'intero processo:

* Importa le librerie necessarie e le classi definite negli altri moduli (`extract_entities`, `Neo4jGraphStorage`, `PROMPTS`).
* Configura il logging di base.
* `DEFAULT_CONFIG`: Un dizionario che definisce la configurazione predefinita (lingua, tipi di entità, parametri LLM, credenziali Neo4j, directory input/output).
  * **Importante:** Questo dizionario ora contiene anche la definizione dello schema (`entity_types`, `relationship_keywords`) e i `delimiters` usati dai prompt e dal parsing, centralizzando la configurazione.
* **`setup_llm_client(config)`** : Funzione asincrona cruciale.
* Legge la configurazione LLM (`provider`, `model`, `temperature`, `max_tokens`).
* In base al `provider` ("openai" o "openrouter"):
  * Importa la libreria necessaria (`openai` o `httpx`).
  * Recupera la chiave API corrispondente dalle variabili d'ambiente (`OPENAI_API_KEY` o `OPENROUTER_API_KEY`). Esce se la chiave non è impostata.
  * Inizializza il client appropriato (`AsyncOpenAI` o indirettamente tramite `httpx.AsyncClient`).
  * Definisce e restituisce una funzione interna asincrona `call_llm(prompt, history)`. Questa funzione:
    * Prende un prompt e una cronologia opzionale.
    * Formatta i messaggi nel formato richiesto dall'API specifica (lista di dizionari con `role` e `content`).
    * Effettua la chiamata API asincrona (`client.chat.completions.create` per OpenAI, `client.post` a `openrouter.ai` per OpenRouter).
    * Estrae e restituisce il contenuto della risposta dell'LLM.
    * Gestisce eventuali eccezioni durante la chiamata API.
* Esce se il provider non è supportato.
* **`process_chunk(chunk_data, config, graph_storage, llm_func)`** : Nuova funzione asincrona che:
    * Riceve i dati di un singolo chunk (un dizionario parsato dal JSONL).
    * Estrae il testo (`text`), l'ID del chunk (`chunk_id`), e il percorso del documento sorgente (`source_doc_path`).
    * Crea un dizionario `source_metadata`.
    * Chiama `extract_entities` passando il testo e i `source_metadata`.
    * Gestisce eccezioni specifiche per l'elaborazione del chunk.
* **`main()`** : La funzione asincrona principale.
* Usa `argparse` per gestire argomenti da linea di comando.
    * **Modificato:** Accetta `--input-jsonl` (obbligatorio) invece di `--text` o `--file`.
* Carica la configurazione: parte da `DEFAULT_CONFIG` e la aggiorna con il contenuto del file JSON specificato da `--config`, se presente.
* **Modificato:** Non legge più un singolo testo, ma apre il file specificato da `--input-jsonl`.
* Chiama `setup_llm_client` per ottenere la funzione `llm_func` configurata.
* Inizializza l'istanza di `Neo4jGraphStorage` con le credenziali dalla configurazione.
* Passa l'intero oggetto `config` (che contiene lo schema e i parametri) alla funzione `process_chunk` e quindi a `extract_entities`.
* Usa un blocco `try...finally`:
  * Chiama `storage.initialize()` per connettersi a Neo4j.
  * **Modificato:** Entra in un ciclo che legge il file JSONL riga per riga.
      * Per ogni riga, la decodifica come JSON.
      * Chiama `await process_chunk()` per elaborare i dati del chunk.
      * Gestisce errori di decodifica JSON o errori durante l'elaborazione del chunk.
  * Stampa alcune statistiche (es., le etichette presenti nel grafo) chiamando `storage.get_all_labels()`. Nota: le statistiche dettagliate per chunk vengono loggate da `process_chunk`.
  * Nella clausola `finally`, chiama `storage.close()` per assicurarsi che la connessione a Neo4j venga chiusa, anche in caso di errori.
* Il blocco `if __name__ == "__main__":` esegue la funzione `main()` usando `asyncio.run()`.

**Flusso di Esecuzione Principale**

1. L'utente esegue `python -m src.knowledge.graph_extractor.graph_main --input-jsonl percorso/al/all_chunks.jsonl`, e opzionalmente una configurazione con `--config config.json`.
2. Lo script `graph_main.py` carica la configurazione (default + utente).
3. Inizializza il client LLM (OpenAI/OpenRouter) e l'istanza di `Neo4jGraphStorage`.
4. Stabilisce la connessione a Neo4j.
5. Entra in un ciclo, leggendo ogni riga (chunk) dal file `--input-jsonl`.
6. Per ogni chunk, chiama `process_chunk`.
7. `process_chunk` chiama `extract_entities` nel modulo `extractor`, passando il testo del chunk, i metadati della fonte (`source_doc_path`, `chunk_id`), e l'oggetto `config`.
8. `extract_entities` usa `get_formatted_prompt` (da `prompt.py`) e `config` per generare dinamicamente i prompt.
9. `extract_entities` chiama ripetutamente la funzione `llm_func` per ottenere le estrazioni dall'LLM per il chunk corrente.
10. `extract_entities` analizza le risposte, normalizza i dati, mappa i tipi, e **aggrega** le informazioni per nodi e relazioni, includendo le liste di tracciabilità (`source_doc_paths`, `chunk_ids`).
11. `extract_entities` chiama i metodi `upsert_node` e `upsert_edge` dell'istanza `Neo4jGraphStorage`, passando i dati aggregati per aggiornare/creare nodi e relazioni nel grafo.
12. Il ciclo in `graph_main.py` continua con il chunk successivo.
13. Al termine del ciclo, `graph_main.py` stampa statistiche finali e chiude la connessione a Neo4j.
