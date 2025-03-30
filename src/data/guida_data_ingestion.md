# MERL-T: Sistema di Q&A Giuridico - Guida d'Uso

## 1. Introduzione

MERL-T è un sistema open-source di domande e risposte in ambito giuridico progettato per accademici, studenti e cittadini. Combina intelligenza artificiale, knowledge graphs e database vettoriali per fornire risposte affidabili basate su fonti giuridiche verificate. Questa guida offre una panoramica dettagliata dell'architettura del sistema, specificamente concentrandosi sulla parte di elaborazione e ingestione dei dati attualmente implementata.

Il cuore di MERL-T è la sua pipeline di elaborazione dei documenti, progettata per trasformare documenti giuridici in chunk ricercabili e recuperabili.

### 1.1 Estrazione da PDF

Il sistema estrae il testo dai PDF giuridici attraverso il modulo `pdf_chunker`.

**Esempio di Utilizzo:**

```python
from src.data.extractor import main as extract_pdfs

# Esegui l'estrazione PDF con parametri predefiniti
extract_pdfs()

# Oppure con parametri personalizzati
import argparse
args = argparse.Namespace(
    input_dir="/percorso/ai/pdf",
    output_dir="/percorso/all/output",
    min_chunk_size=3000,
    max_chunk_size=5000,
    overlap=1500,
    sliding_window=True,
    workers=4,
    cpu_limit=90,
    language="italian",
    debug=True
)
# Passa gli argomenti all'estrattore
```

**Utilizzo da Riga di Comando:**

```bash
python src/data/extractor.py --input-dir /percorso/ai/pdf --output-dir /percorso/all/output --min-chunk-size 3000 --max-chunk-size 5000 --overlap 1500 --sliding-window --workers 4 --cpu-limit 90 --language italian --debug
```

**Parametri Principali:**

* `input_dir`: Directory contenente i file PDF da elaborare
* `output_dir`: Directory dove salvare il testo estratto e i chunk
* `min_chunk_size`: Numero minimo di caratteri per chunk
* `max_chunk_size`: Numero massimo di caratteri per chunk
* `overlap`: Sovrapposizione di caratteri tra i chunk
* `sliding_window`: Utilizza l'approccio a finestra scorrevole (vs. basato su paragrafi)
* `workers`: Numero di worker paralleli (0=automatico)
* `cpu_limit`: Percentuale massima di utilizzo della CPU
* `language`: Lingua target (predefinito: italiano)

**Formato di Output:**
L'estrattore produce diversi formati di output:

* File JSON con chunk e metadati
* File di testo individuali per ogni chunk
* File JSONL (un oggetto JSON per riga)
* File CSV con metadati dei chunk

### 1.2 Pulizia del Testo

La classe `TextCleaner` fornisce funzionalità avanzate di pulizia per testi giuridici, ottimizzandoli per il recupero e l'analisi.

**Esempio di Utilizzo:**

```python
from src.data.pdf_chunker.cleaner import TextCleaner, TextCleanerConfig

# Crea un cleaner con configurazione predefinita
cleaner = TextCleaner()

# Oppure con configurazione personalizzata
config = TextCleanerConfig(
    log_level=logging.INFO,
    preserve_paragraphs=True,
    max_workers=4,
    enable_post_processing=True
)
cleaner = TextCleaner(config)

# Pulisci un singolo chunk di testo
testo_pulito, statistiche = cleaner.clean_text(testo)

# Pulisci chunk JSON
with open('chunks.json', 'r', encoding='utf-8') as f:
    chunks = json.load(f)
chunks_puliti, statistiche = cleaner.clean_chunks(chunks, parallel=True)

# Elabora un'intera directory
statistiche = cleaner.process_directory(
    input_dir="./chunk_grezzi",
    output_dir="./chunk_puliti",
    file_pattern="*.json",
)
```

**Utilizzo da Riga di Comando:**

```bash
python src/data/cleaner_main.py --input ./chunk_grezzi --output ./chunk_puliti --workers 4 --verbose
```

**Caratteristiche Principali:**

* Normalizza spaziature e interruzioni di riga
* Conserva la struttura dei paragrafi
* Rimuove intestazioni, piè di pagina e numeri di pagina
* Normalizza la punteggiatura
* Elaborazione multi-thread per alte prestazioni
* Statistiche dettagliate sulla riduzione del testo

### 1.3 Strategie di Chunking

MERL-T supporta diverse strategie di chunking attraverso `HybridTokenizer` e `CustomTokenizer`:

1. **Finestra Scorrevole** : Crea chunk sovrapposti di testo basati sul conteggio dei caratteri
2. **Chunking Semantico** : Crea chunk basati su paragrafi e unità semantiche
3. **Tokenizzazione Ibrida** : Crea chunk basati sia sul conteggio dei token che sui confini semantici

**Selezione di una Strategia di Chunking:**
Imposta il parametro `USE_SLIDING_WINDOW` su `True` per l'approccio a finestra scorrevole o `False` per il chunking semantico.

## 2. Architettura del Flusso di Dati

Il flusso di dati in MERL-T segue queste fasi chiave:

1. **Ingestione dei Documenti** :

* I PDF vengono elaborati da `extractor.py`
* Il testo viene estratto utilizzando `pdfplumber`
* Le pagine vengono elaborate in batch per gestire l'uso della memoria

1. **Elaborazione del Testo** :

* Il testo estratto viene pulito da `cleaner.py`
* Il testo viene normalizzato, con intestazioni/piè di pagina rimossi
* La struttura del testo viene preservata per la comprensione semantica

1. **Chunking** :

* Il testo viene diviso in chunk da `processor.py`
* I chunk possono sovrapporsi per preservare il contesto
* Sono disponibili diverse strategie di chunking (finestra scorrevole, semantica)

1. **Generazione dell'Output** :

* I chunk elaborati vengono salvati in diversi formati da `output_manager.py`
* Sono supportati formati JSON, JSONL, TXT e CSV
* I metadati vengono preservati per ogni chunk

## 3. Casi d'Uso Comuni

### 3.1 Elaborazione di una Collezione di Documenti Giuridici

```bash
# 1. Elabora documenti PDF
python src/data/extractor.py --input-dir ./pdf_giuridici --output-dir ./elaborati

# 2. Pulisci il testo estratto
python src/data/cleaner_main.py --input ./elaborati --output ./puliti

# Questo genererà un dataset pronto per l'indicizzazione in un database vettoriale
```

### 3.2 Elaborazione in Batch di Documenti Giuridici

Per l'elaborazione su larga scala, utilizza il `ParallelExecutor`:

```python
from src.data.pdf_chunker.parallel import ParallelExecutor
from src.data.pdf_chunker.config import Config
from src.data.pdf_chunker.cpu_monitor import CPUMonitor
from src.data.pdf_chunker.progress_tracker import ProgressTracker

# Configura l'elaborazione
config = Config()
config.INPUT_FOLDER = "./doc_giuridici"
config.OUTPUT_FOLDER = "./doc_elaborati"
config.MAX_WORKERS = 4

# Inizializza i componenti
cpu_monitor = CPUMonitor(config.CPU_LIMIT, config.CPU_CHECK_INTERVAL)
progress_tracker = ProgressTracker("avanzamento_elaborazione.json")

# Avvia il monitoraggio della CPU
cpu_monitor.start()

# Ottieni l'elenco dei file PDF da elaborare
from src.data.pdf_chunker.utils import find_pdf_files
pdf_files = find_pdf_files(config.INPUT_FOLDER)

# Inizializza l'executor
executor = ParallelExecutor(
    num_workers=config.MAX_WORKERS,
    cpu_monitor=cpu_monitor,
    progress_tracker=progress_tracker
)

# Elabora i PDF in parallelo
executor.process_pdfs(pdf_files, config)

# Ferma il monitoraggio della CPU
cpu_monitor.stop()
```

## 4. Risoluzione dei Problemi

### Problemi Comuni e Soluzioni

1. **Fallimento dell'Estrazione PDF** :

* Assicurati che il PDF non sia protetto da password
* Prova ad aumentare `TIMEOUT_PER_PAGE` nella configurazione
* Prova a ridurre `MAX_PAGES_PER_BATCH` per evitare problemi di memoria

1. **Utilizzo Elevato della CPU Durante l'Elaborazione** :

* Riduci `MAX_WORKERS` nella configurazione
* Aumenta `CPU_LIMIT` per consentire un utilizzo più elevato della CPU
* Prova a elaborare in batch più piccoli

1. **Problemi di Qualità dei Chunk** :

* Regola `MIN_CHUNK_SIZE` e `MAX_CHUNK_SIZE`
* Prova diverse strategie di chunking (`USE_SLIDING_WINDOW`)
* Abilita la pulizia avanzata con `TextCleaner`

### Logging

MERL-T utilizza il modulo di logging di Python in tutto il codice:

* La maggior parte dei moduli scrive su file di log specifici (ad es. `pdf_chunker.log`)
* Usa il flag `--debug` per aumentare la verbosità
* Controlla i file di log per messaggi di errore dettagliati e statistiche di elaborazione

## 5. Configurazione Avanzata

### Personalizzazione di TextCleaner

```python
from src.data.pdf_chunker.cleaner import TextCleanerConfig, TextCleaner

# Crea una configurazione personalizzata
config_personalizzata = TextCleanerConfig(
    preserve_paragraphs=True,
    max_workers=8,
    preserve_newlines_after_patterns={
        r'[.!?]', r':', r';', r'\.\.\.', r'\d\)'  # Aggiungi pattern personalizzati
    },
    custom_patterns={
        'citazioni_legali': r'\[Cass\.\s+\d+\/\d+\]'  # Aggiungi pattern per citazioni legali
    }
)

# Crea un cleaner con configurazione personalizzata
cleaner = TextCleaner(config_personalizzata)

# Salva la configurazione per riutilizzarla
config_personalizzata.save_to_json_file("config_cleaner_legale.json")

# Carica la configurazione in seguito
config_caricata = TextCleanerConfig.from_json_file("config_cleaner_legale.json")
```

### Personalizzazione della Tokenizzazione

Per l'elaborazione specializzata di testi giuridici, puoi personalizzare i tokenizer:

```python
from src.data.pdf_chunker.custom_tokenizer import CustomTokenizer
from src.data.pdf_chunker.hybrid_tokenizer import HybridTokenizer

# Tokenizer personalizzato con abbreviazioni legali specializzate
tokenizer_legale = CustomTokenizer(max_chunk_size=1500)

# Aggiungi abbreviazioni legali per prevenire falsi confini di frase
tokenizer_legale.abbreviations.extend([
    r'op\. cit\.',
    r'ex art\.',
    r'v\. infra',
    r'v\. supra'
])

# Usa hybrid tokenizer per chunking basato su token
tokenizer_ibrido = HybridTokenizer(
    max_tokens_per_chunk=300,
    min_tokens_per_chunk=50,
    overlap_tokens=50,
    abbreviations=tokenizer_legale.abbreviations
)

# Elabora il testo con il tokenizer personalizzato
frasi = tokenizer_legale.tokenize(testo_legale)

# Crea chunk con il tokenizer ibrido
chunks = tokenizer_ibrido.create_overlapping_chunks(testo_legale)
```

## Conclusione

Questa guida si è concentrata sulla componente di ingestione dati di MERL-T, attualmente implementata. Il sistema offre solide capacità di elaborazione per documenti giuridici, permettendo di estrarre, pulire e suddividere i testi in chunk ottimizzati per le successive fasi di elaborazione.

La pipeline di elaborazione dati forma la base del sistema ed è progettata per gestire le peculiarità dei testi giuridici, garantendo che la struttura semantica e le informazioni importanti vengano preservate durante il processo di chunking.

Le fasi successive del progetto includeranno l'implementazione delle funzionalità di recupero, knowledge graph e interfaccia di interrogazione, che sfrutteranno i dati elaborati da questa pipeline per fornire risposte giuridiche precise e contestualizzate.

Per ulteriori informazioni, consultare la documentazione dei singoli moduli o le intestazioni dei file, che contengono commenti dettagliati ed esempi di utilizzo.
