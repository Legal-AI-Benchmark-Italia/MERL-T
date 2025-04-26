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

**6. `graph_extractor/extractor.py`**

Questo è il cuore logico dell'estrazione:

* Funzioni helper:
  * `clean_str(s)`: Rimuove spazi bianchi e virgolette iniziali/finali da una stringa.
  * `normalize_extracted_info(info, is_entity)`: Pulisce una stringa e, se è un nome di entità, mette in maiuscolo la prima lettera di ogni parola.
  * `is_float_regex(s)`: Controlla se una stringa rappresenta un numero decimale.
  * `_handle_single_entity_extraction(record_attributes, ...)`: Prende gli attributi di un record estratto dall'LLM, verifica se è un'entità, estrae nome, tipo e descrizione, li normalizza e li restituisce come dizionario.
  * `_handle_single_relationship_extraction(record_attributes, ...)`: Simile alla precedente, ma per le relazioni. Estrae sorgente, destinazione, descrizione, parole chiave e forza (peso), li normalizza e restituisce un dizionario.
* **`extract_entities(text, knowledge_graph_inst, global_config, llm_func, ...)`** : La funzione principale (asincrona) che orchestra l'estrazione.

1. Recupera la configurazione (numero massimo di passaggi di "gleaning", lingua, tipi di entità) dal dizionario `global_config`.
2. Prepara il contesto per i prompt sostituendo i placeholder (delimitatori, lingua, tipi di entità) nei template di `prompt.py`.
3. Formatta il prompt iniziale `entity_extraction` con il testo di input.
4. Chiama la funzione `llm_func` (passata come argomento, rappresenta la chiamata all'API OpenAI o OpenRouter configurata in `graph_main.py`) con il prompt iniziale.
5. Salva la coppia prompt/risposta nella `history`.
6. Elabora la risposta dell'LLM: divide la risposta in record usando `DEFAULT_RECORD_DELIMITER`, ogni record in attributi usando `DEFAULT_TUPLE_DELIMITER`, e usa `_handle_single_entity_extraction` e `_handle_single_relationship_extraction` per parsare i dati, memorizzandoli in dizionari `nodes` e `edges`.
7. Esegue un ciclo per i passaggi aggiuntivi ("gleaning"):
   * Chiama `llm_func` con il prompt `entity_continue_extraction` e la `history` precedente.
   * Aggiunge la nuova coppia prompt/risposta alla `history`.
   * Elabora la risposta del "gleaning" nello stesso modo, aggiungendo nuovi nodi/archi ai dizionari.
8. Itera sui nodi e archi raccolti:
   * Per ogni entità (nodo), prepara un dizionario `node_properties` (includendo etichetta, descrizione, ecc.) e chiama `knowledge_graph_inst.upsert_node()`. Usa il nome dell'entità normalizzato come `node_id`. L'etichetta principale per Neo4j viene presa dal primo tipo estratto per quell'entità.
   * Per ogni relazione (arco), prepara un dizionario `edge_properties`. Il tipo di relazione Neo4j (`relation_type`) viene derivato dalle `keywords` estratte (convertite in maiuscolo, con spazi sostituiti da `_`, e caratteri non validi rimossi) o impostato a 'RELATED_TO' di default. Chiama `knowledge_graph_inst.upsert_edge()`.
9. Registra il numero di nodi e archi aggiornati.

**7. `graph_main.py`**

Lo script principale che esegue l'intero processo:

* Importa le librerie necessarie e le classi definite negli altri moduli (`extract_entities`, `Neo4jGraphStorage`, `PROMPTS`).
* Configura il logging di base.
* `DEFAULT_CONFIG`: Un dizionario che definisce la configurazione predefinita (lingua, tipi di entità, parametri LLM, credenziali Neo4j, directory input/output).
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
* **`process_text(text, config, graph_storage, llm_func)`** : Funzione asincrona semplice che chiama `extract_entities` passando tutti i parametri necessari.
* **`main()`** : La funzione asincrona principale.
* Usa `argparse` per gestire argomenti da linea di comando (`--config`, `--text`, `--file`) per permettere all'utente di specificare un file di configurazione alternativo, passare il testo direttamente, o specificare un file da cui leggere il testo.
* Carica la configurazione: parte da `DEFAULT_CONFIG` e la aggiorna con il contenuto del file JSON specificato da `--config`, se presente.
* Determina il testo di input leggendolo dall'argomento `--text` o dal file specificato da `--file`. Esce se non viene fornito testo.
* Chiama `setup_llm_client` per ottenere la funzione `llm_func` configurata.
* Inizializza l'istanza di `Neo4jGraphStorage` con le credenziali dalla configurazione.
* Usa un blocco `try...finally`:
  * Chiama `storage.initialize()` per connettersi a Neo4j.
  * Chiama `process_text` per eseguire l'estrazione e l'aggiornamento del grafo.
  * Stampa alcune statistiche (es., le etichette presenti nel grafo) chiamando `storage.get_all_labels()`.
  * Nella clausola `finally`, chiama `storage.close()` per assicurarsi che la connessione a Neo4j venga chiusa, anche in caso di errori.
* Il blocco `if __name__ == "__main__":` esegue la funzione `main()` usando `asyncio.run()`.

**Flusso di Esecuzione Principale**

1. L'utente esegue `python graph_main.py` fornendo testo tramite `--text "..."` o `--file percorso/al/file.txt`, e opzionalmente una configurazione con `--config config.json`.
2. Lo script `graph_main.py` carica la configurazione (default + utente).
3. Inizializza il client LLM (OpenAI/OpenRouter) e l'istanza di `Neo4jGraphStorage`.
4. Stabilisce la connessione a Neo4j.
5. Chiama `extract_entities` nel modulo `extractor`.
6. `extract_entities` formatta i prompt usando i template da `prompt.py` e il testo di input.
7. `extract_entities` chiama ripetutamente la funzione `llm_func` (ottenuta da `setup_llm_client`) per ottenere le estrazioni dall'LLM.
8. `extract_entities` analizza le risposte dell'LLM, normalizza i dati e identifica nodi e archi.
9. `extract_entities` chiama i metodi `upsert_node` e `upsert_edge` dell'istanza `Neo4jGraphStorage` per salvare i dati nel database Neo4j.
10. Al termine, `graph_main.py` stampa eventuali statistiche e chiude la connessione a Neo4j.
