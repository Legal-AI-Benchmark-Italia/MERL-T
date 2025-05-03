# PDF Chunker Module Documentation

## Panoramica

Il modulo `pdf_chunker` è progettato per elaborare documenti PDF, in particolare quelli di natura giuridica, estraendo il testo, dividendolo in "chunk" (segmenti) di dimensioni gestibili e salvando questi chunk in vari formati. L\'obiettivo principale è preparare i dati testuali per l\'addestramento o l\'utilizzo con Large Language Models (LLM).

Il modulo è strutturato per essere configurabile, robusto e capace di gestire l\'elaborazione parallela di un gran numero di documenti, monitorando al contempo l\'utilizzo delle risorse di sistema (CPU).

## Struttura del Modulo

Il modulo è composto dai seguenti file Python principali, ognuno con una responsabilità specifica:

* **`extractor.py`**:
  * Script principale e punto di ingresso del modulo.
  * Gestisce l\'analisi degli argomenti da riga di comando.
  * Orchestra l\'intero processo: inizializza i componenti, trova i file PDF, gestisce l\'esecuzione parallela e finalizza l\'output.
* **`config.py`**:
  * Definisce la classe `Config` che centralizza tutte le impostazioni configurabili del modulo.
  * Include percorsi di input/output, parametri di chunking (dimensione min/max, sovrapposizione), impostazioni di parallelizzazione (numero di worker, limite CPU), lingua, configurazione del logging e pattern per la pulizia del testo.
  * Calcola dinamicamente i percorsi relativi alla radice del progetto.
* **`processor.py`**:
  * Contiene la classe `PDFProcessor`.
  * Responsabile della logica di elaborazione di un *singolo* file PDF:
    * Estrae il testo grezzo dalle pagine utilizzando `pdfplumber`, gestendo l'elaborazione in batch per risparmiare memoria e timeout per pagina.
    * Applica una pulizia preliminare del testo (rimozione di header/footer, numeri di pagina, spazi multipli, etc.) basata sui pattern definiti in `Config`.
    * Divide il testo pulito in chunk utilizzando una delle due strategie configurabili:
        * **Semantica (paragrafi):** Divide il testo in paragrafi e li raggruppa cercando di rispettare i limiti di dimensione (`MIN_CHUNK_SIZE`, `MAX_CHUNK_SIZE`). Se un paragrafo è troppo grande, viene ulteriormente suddiviso in frasi (usando `custom_tokenizer`) o blocchi più piccoli.
        * **Finestra Scorrevo le (`sliding_window`):** Tokenizza il testo in frasi (usando `custom_tokenizer`) e crea chunk sovrapposti (`OVERLAP_SIZE`) di un numero approssimativo di frasi per rispettare `MAX_CHUNK_SIZE`. Include fallback per testi senza frasi o tokenizzazione fallita.
    * Applica una pulizia avanzata ai chunk generati utilizzando la classe `TextCleaner` (se `APPLY_CLEANING` è True in `Config`), aggiornando il testo e i metadati del chunk (token, caratteri).
    * Restituisce una lista di dizionari, ognuno rappresentante un chunk con i suoi metadati (`chunk_id`, `text`, `tokens`, `chars`, `index`).
* **`output_manager.py`**:
  * Contiene la classe `OutputManager`.
  * Gestisce il salvataggio dei chunk elaborati e dei relativi metadati.
  * Crea una struttura di cartelle organizzata all\'interno della directory di output specificata, replicando la struttura della directory di input.
  * Salva i chunk in più formati per ogni PDF:
    * Un file JSON contenente tutti i chunk.
    * Un file JSONL (JSON Lines), con un chunk per riga.
    * File di testo separati per ogni chunk (`chunks/`).
    * File JSON separati per ogni chunk (`json_chunks/`).
    * Un file CSV con i metadati principali dei chunk.
  * Fornisce funzionalità per la pulizia di output parziali in caso di errori.
  * Crea file combinati (`all_chunks.jsonl`, `documents_metadata.json`) che aggregano i risultati di tutti i PDF elaborati.
* **`parallel.py`**:
  * Contiene la classe `ParallelExecutor`.
  * Gestisce l'esecuzione parallela dell'elaborazione dei PDF utilizzando un pool di processi worker (`multiprocessing.Pool`). Il numero di worker è configurabile o determinato automaticamente.
  * Definisce la funzione `_process_single_pdf` che viene eseguita da ciascun worker. Questa funzione:
    * Riceve il percorso del PDF, il prefisso relativo per l'output e la configurazione.
    * Istanzia `Config`, `OutputManager` e `PDFProcessor` localmente.
    * Chiama `processor.process_pdf` per elaborare il documento.
    * Chiama `output_manager.save_chunks` per salvare i risultati.
    * Interagisce con `CPUMonitor` (tramite variabile globale `_cpu_monitor`) per mettere in pausa l'esecuzione (`check_and_throttle`) se la CPU è sovraccarica.
  * `ParallelExecutor` prepara l'elenco dei task per i worker, includendo il calcolo dei percorsi relativi (`relative_output_prefix`) per mantenere la struttura delle cartelle nell'output.
  * Gestisce l'avvio e l'attesa del pool di processi.
  * Aggiorna `ProgressTracker` al termine dell'elaborazione di ciascun PDF.
* **`progress_tracker.py`**:
  * Contiene la classe `ProgressTracker`.
  * Gestisce un file JSON (`Config.PROGRESS_FILE`) per tenere traccia dei file PDF che sono già stati elaborati con successo.
  * Utilizza un `multiprocessing.Lock` per garantire l'accesso sicuro al file di stato da parte di processi multipli (worker).
  * Fornisce metodi per:
    * Caricare l'elenco dei PDF già processati (`_load_progress`, `get_processed_pdfs`).
    * Salvare l'elenco aggiornato (`_save_progress`).
    * Marcare un nuovo PDF come completato (`mark_as_processed`).
* **`cpu_monitor.py`**:
  * Contiene la classe `CPUMonitor`.
  * Monitora l'utilizzo percentuale della CPU del sistema a intervalli regolari (`check_interval`) utilizzando la libreria `psutil`.
  * Esegue il monitoraggio in un thread separato (`threading.Thread`) per non bloccare l'elaborazione principale.
  * Utilizza un `multiprocessing.Value` condiviso (`throttling`) per segnalare se l'utilizzo della CPU supera la soglia definita (`cpu_limit` in `Config`). `1` indica throttling attivo, `0` inattivo.
  * Fornisce metodi per avviare (`start`) e fermare (`stop`) il thread di monitoraggio.
  * Fornisce metodi per verificare lo stato del throttling (`is_throttling_active`) e per mettere in pausa il processo chiamante se il throttling è attivo (`check_and_throttle`).
* **`utils.py`**:
  * Contiene funzioni di utilità generiche usate in altri moduli:
    * `setup_logging`: Configura il logging su file e console basandosi sui parametri in `Config`.
    * `find_pdf_files`: Cerca ricorsivamente tutti i file `.pdf` nella directory di input specificata utilizzando `glob`.
    * `initialize_nltk`: Funzione deprecata (non più utilizzata).
    * `fallback_sent_tokenize`: Un semplice tokenizer basato su regex per dividere il testo in frasi, usato come fallback dal `custom_tokenizer` o direttamente se NLTK non è disponibile/fallisce. Tenta diverse strategie (punti, punti e virgola, virgole, newline, blocchi fissi).
  *(Nota: `custom_tokenizer.py` e `cleaner.py` non erano inclusi negli snippet precedenti ma sono referenziati e quindi parte del modulo)*.

## Flusso di Lavoro

1. L\'utente esegue `extractor.py`, opzionalmente fornendo argomenti da riga di comando per sovrascrivere le impostazioni predefinite in `config.py`.
2. `extractor.py` inizializza `Config`, il logger, `ProgressTracker`, `CPUMonitor` e `OutputManager`.
3. Vengono cercati tutti i file PDF nella cartella di input (`Config.INPUT_FOLDER`).
4. `ProgressTracker` viene consultato per determinare quali PDF sono già stati elaborati; questi vengono esclusi dall\'elaborazione corrente.
5. `CPUMonitor` avvia il monitoraggio in background.
6. `ParallelExecutor` viene creato e configurato con il numero desiderato di worker.
7. `ParallelExecutor` distribuisce i PDF rimanenti ai processi worker.
8. Ogni worker esegue (presumibilmente) un\'istanza di `PDFProcessor` per un dato PDF:
   * Il testo viene estratto.
   * Il testo viene diviso in chunk.
   * I chunk vengono puliti.
9. Al termine dell\'elaborazione di un PDF, il worker (o `ParallelExecutor`) invia i chunk risultanti a `OutputManager`.
10. `OutputManager` salva i chunk nei vari formati all\'interno di una sottocartella specifica per quel PDF nella directory di output (`Config.OUTPUT_FOLDER`).
11. `ProgressTracker` viene aggiornato per registrare il completamento del PDF.
12. `ParallelExecutor` gestisce il throttling basato sull\'output di `CPUMonitor`.
13. Una volta processati tutti i PDF, `extractor.py` chiama `output_manager.create_combined_outputs()` per generare i file aggregati (`all_chunks.jsonl` e `documents_metadata.json`).
14. `CPUMonitor` viene fermato.
15. Il programma termina.

## Configurazione

La configurazione principale avviene tramite la classe `Config` nel file `src/knowledge/pdf_chunker/src/config.py`. Le impostazioni possono essere modificate direttamente lì o sovrascritte tramite argomenti da riga di comando passati a `extractor.py`.

## Struttura dell\'Output

L\'`OutputManager` crea una struttura di cartelle nella directory di output specificata (`--output-dir` o `Config.OUTPUT_FOLDER`). Per ogni file PDF di input (es. `input_dir/subdir/documento.pdf`), viene creata una directory corrispondente nell\'output (es. `output_dir/subdir/documento/`). All\'interno di questa directory specifica del documento, vengono generati i seguenti file:

* `documento_chunks.json`: Tutti i chunk del documento in formato JSON.
* `documento_chunks.jsonl`: Tutti i chunk, uno per riga, in formato JSONL.
* `documento_chunks_metadata.csv`: Metadati dei chunk in formato CSV.
* `chunks/`: Una sottocartella contenente ogni chunk come file `.txt` separato.
* `json_chunks/`: Una sottocartella contenente ogni chunk come file `.json` separato (include metadati aggiuntivi).

Inoltre, nella directory di output principale, vengono creati due file aggregati:

* `all_chunks.jsonl`: Contiene tutti i chunk di *tutti* i documenti elaborati, in formato JSONL.
* `documents_metadata.json`: Contiene metadati riassuntivi per ogni documento elaborato.

## Come Eseguire

Lo script può essere eseguito dalla radice del progetto o dalla directory `src/knowledge/pdf_chunker/`. Assumendo di essere nella radice del progetto:

```bash
python src/knowledge/pdf_chunker/extractor.py [OPZIONI]
```

Alcune opzioni comuni (vedi `python src/knowledge/pdf_chunker/extractor.py --help` per l\'elenco completo):

* `--input-dir PATH`: Specifica la cartella contenente i PDF.
* `--output-dir PATH`: Specifica la cartella dove salvare i risultati.
* `--workers NUM`: Imposta il numero di processi paralleli.
* `--debug`: Abilita il logging a livello DEBUG.

Esempio:

```bash
python src/knowledge/pdf_chunker/extractor.py \
    --input-dir ./knowledge/knowledge_base/dottrina/raw_sources \
    --output-dir ./knowledge/knowledge_base/dottrina/raw_text \
    --workers 4
```
