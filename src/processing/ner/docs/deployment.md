# MERLT-NER: Guida al Deployment e all'Operatività

Questa guida fornisce istruzioni dettagliate per il deployment, la configurazione e l'utilizzo del sistema NER-Giuridico, un modulo di Named Entity Recognition specializzato per il riconoscimento di entità giuridiche in testi italiani.

## Indice

1. [Requisiti di Sistema](#requisiti-di-sistema)
2. [Installazione](#installazione)
3. [Configurazione](#configurazione)
4. [Utilizzo](#utilizzo)
5. [Deployment in Produzione](#deployment-in-produzione)
6. [Monitoraggio e Manutenzione](#monitoraggio-e-manutenzione)
7. [Integrazione con MERL-T](#integrazione-con-merl-t)
8. [Risoluzione dei Problemi](#risoluzione-dei-problemi)

## Requisiti di Sistema

### Hardware Consigliato

- **CPU**: 4+ core
- **RAM**: 8+ GB (16+ GB consigliati per carichi di lavoro elevati)
- **Spazio su Disco**: 10+ GB
- **GPU**: Opzionale ma consigliata per prestazioni ottimali con modelli transformer

### Software Richiesto

- **Sistema Operativo**: Linux (Ubuntu 20.04+ consigliato), macOS, o Windows 10+
- **Python**: 3.8+
- **Database**: Neo4j (opzionale, per l'integrazione con il knowledge graph)
- **Docker**: (opzionale, per il deployment containerizzato)

## Installazione

### Installazione da Sorgente

1. Clona il repository:

   ```bash
   git clone https://github.com/merl-t/ner-giuridico.git
   cd ner-giuridico
   ```
2. Crea un ambiente virtuale Python:

   ```bash
   python -m venv venv
   source venv/bin/activate  # Su Windows: venv\Scripts\activate
   ```
3. Installa le dipendenze:

   ```bash
   pip install -r requirements.txt
   ```
4. Installa i modelli linguistici:

   ```bash
   python -m spacy download it_core_news_lg
   ```

### Installazione con Docker

1. Clona il repository:

   ```bash
   git clone https://github.com/merl-t/ner-giuridico.git
   cd ner-giuridico
   ```
2. Costruisci l'immagine Docker:

   ```bash
   docker build -t ner-giuridico .
   ```

## Configurazione

Il sistema NER-Giuridico utilizza un file di configurazione YAML per gestire tutte le impostazioni. Il file di configurazione predefinito si trova in `config/config.yaml`.

### Configurazione di Base

Per modificare la configurazione di base:

1. Copia il file di configurazione predefinito:

   ```bash
   cp config/config.yaml config/config_custom.yaml
   ```
2. Modifica il file `config/config_custom.yaml` secondo le tue esigenze.
3. Specifica il file di configurazione personalizzato all'avvio:

   ```bash
   python main.py --config config/config_custom.yaml server
   ```

### Configurazione dei Modelli

Il sistema supporta diversi modelli per il riconoscimento delle entità:

- **Modello Transformer**: Basato su BERT per l'italiano
- **Modello Rule-Based**: Utilizza pattern regex e gazetteer
- **Ensemble**: Combina i risultati dei diversi modelli

Per configurare i modelli, modifica la sezione `models` nel file di configurazione:

```yaml
models:
  transformer:
    model_name: "dbmdz/bert-base-italian-xxl-cased"
    max_length: 512
    batch_size: 16
    device: "cuda"  # Usa "cpu" se non disponi di GPU
  
  rule_based:
    enable: true
    patterns_dir: "../data/patterns"
```

### Configurazione dell'API

Per configurare l'API REST, modifica la sezione `api` nel file di configurazione:

```yaml
api:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  timeout: 30
  rate_limit: 100
```

### Configurazione dell'Integrazione con Neo4j

Per abilitare l'integrazione con il knowledge graph Neo4j, modifica la sezione `normalization.knowledge_graph` nel file di configurazione:

```yaml
normalization:
  use_knowledge_graph: true
  knowledge_graph:
    url: "bolt://localhost:7687"
    user: "neo4j"
    password: "password"
```

## Utilizzo

Il sistema NER-Giuridico può essere utilizzato in diversi modi:

### Avvio del Server API

Per avviare il server API:

```bash
python main.py server --host 0.0.0.0 --port 8000
```

### Elaborazione di un Singolo Testo

Per elaborare un singolo testo:

```bash
python main.py process --text "L'articolo 1414 c.c. disciplina la simulazione del contratto."
```

Oppure da un file:

```bash
python main.py process --file input.txt --output result.json
```

### Elaborazione Batch

Per elaborare più file in una directory:

```bash
python main.py batch --dir /path/to/input/dir --output /path/to/output/dir --ext txt
```

### Interfaccia di Annotazione

Per configurare e avviare l'interfaccia di annotazione:

```bash
python main.py annotate --tool label-studio
```

### Conversione dei Dati Annotati

Per convertire i dati annotati da un formato all'altro:

```bash
python main.py convert --input annotations.json --output annotations.spacy --input-format json --output-format spacy
```

## Deployment in Produzione

### Deployment con Docker

1. Costruisci l'immagine Docker:

   ```bash
   docker build -t ner-giuridico .
   ```
2. Avvia il container:

   ```bash
   docker run -d -p 8000:8000 --name ner-giuridico ner-giuridico
   ```

### Deployment con Docker Compose

1. Crea un file `docker-compose.yml`:

   ```yaml
   version: '3'
   services:
     ner-giuridico:
       build: .
       ports:
         - "8000:8000"
       volumes:
         - ./config:/app/config
         - ./data:/app/data
         - ./models:/app/models
       environment:
         - LOG_LEVEL=INFO

     neo4j:
       image: neo4j:4.4
       ports:
         - "7474:7474"
         - "7687:7687"
       environment:
         - NEO4J_AUTH=neo4j/password
       volumes:
         - ./neo4j/data:/data
         - ./neo4j/logs:/logs
   ```
2. Avvia i servizi:

   ```bash
   docker-compose up -d
   ```

### Deployment con Kubernetes

1. Crea un file `deployment.yaml`:

   ```yaml
   apiVersion: apps/v1
   kind: Deployment
   metadata:
     name: ner-giuridico
   spec:
     replicas: 3
     selector:
       matchLabels:
         app: ner-giuridico
     template:
       metadata:
         labels:
           app: ner-giuridico
       spec:
         containers:
         - name: ner-giuridico
           image: ner-giuridico:latest
           ports:
           - containerPort: 8000
           resources:
             limits:
               cpu: "1"
               memory: "2Gi"
             requests:
               cpu: "0.5"
               memory: "1Gi"
           volumeMounts:
           - name: config-volume
             mountPath: /app/config
         volumes:
         - name: config-volume
           configMap:
             name: ner-giuridico-config
   ```
2. Crea un file `service.yaml`:

   ```yaml
   apiVersion: v1
   kind: Service
   metadata:
     name: ner-giuridico
   spec:
     selector:
       app: ner-giuridico
     ports:
     - port: 80
       targetPort: 8000
     type: LoadBalancer
   ```
3. Applica le configurazioni:

   ```bash
   kubectl apply -f deployment.yaml
   kubectl apply -f service.yaml
   ```

## Monitoraggio e Manutenzione

### Monitoraggio con Prometheus

Il sistema NER-Giuridico espone metriche Prometheus sulla porta 9090 (configurabile). Per visualizzare queste metriche, puoi utilizzare Prometheus e Grafana.

1. Configura Prometheus per raccogliere le metriche:

   ```yaml
   scrape_configs:
     - job_name: 'ner-giuridico'
       scrape_interval: 15s
       static_configs:
         - targets: ['ner-giuridico:9090']
   ```
2. Configura Grafana per visualizzare le metriche.

### Logging

I log del sistema vengono scritti sia su stdout che su file. Il percorso del file di log predefinito è `ner.log` nella directory principale del progetto.

Per configurare il logging, modifica la sezione `monitoring.logging` nel file di configurazione:

```yaml
monitoring:
  logging:
    file: "/var/log/ner.log"
    rotation: "1 day"
    retention: "30 days"
```

### Backup e Ripristino

È importante eseguire regolarmente il backup dei seguenti dati:

1. File di configurazione
2. Modelli addestrati
3. Dati di annotazione
4. Knowledge graph Neo4j (se utilizzato)

Per eseguire il backup:

```bash
# Backup dei file di configurazione e dei modelli
tar -czvf ner-giuridico-backup.tar.gz config/ models/ data/

# Backup del database Neo4j (se utilizzato)
neo4j-admin dump --database=neo4j --to=/path/to/backup/neo4j.dump
```

Per ripristinare da un backup:

```bash
# Ripristino dei file di configurazione e dei modelli
tar -xzvf ner-giuridico-backup.tar.gz

# Ripristino del database Neo4j (se utilizzato)
neo4j-admin load --from=/path/to/backup/neo4j.dump --database=neo4j --force
```

## Integrazione con MERL-T

Il sistema NER-Giuridico è progettato per integrarsi con il sistema MERL-T (Multi Expert Retrival Legal Transformer) come modulo di preprocessing delle query.

### Configurazione dell'Integrazione

Per configurare l'integrazione con MERL-T, modifica la sezione `moe_integration` nel file di configurazione:

```yaml
moe_integration:
  enable: true
  router_url: "http://localhost:8001/api/v1/route"
  authentication:
    type: "api_key"
    key_name: "X-API-Key"
    key_value: "${MOE_API_KEY}"
```

### Endpoint di Integrazione

L'endpoint `/api/v1/moe/preprocess` è specificamente progettato per l'integrazione con il router MoE di MERL-T. Questo endpoint riceve una query in input, identifica le entità giuridiche e restituisce un risultato strutturato che può essere utilizzato dal router MoE per indirizzare la query agli esperti appropriati.

Esempio di richiesta:

```http
POST /api/v1/moe/preprocess HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "text": "Quali sono le conseguenze della simulazione di un contratto secondo l'articolo 1414 del codice civile?"
}
```

Esempio di risposta:

```json
{
  "original_query": "Quali sono le conseguenze della simulazione di un contratto secondo l'articolo 1414 del codice civile?",
  "entities": [
    {
      "text": "articolo 1414 del codice civile",
      "type": "ARTICOLO_CODICE",
      "start_char": 58,
      "end_char": 89,
      "normalized_text": "Articolo 1414 Codice Civile",
      "metadata": {
        "articolo": "1414",
        "codice": "Codice Civile"
      }
    },
    {
      "text": "simulazione",
      "type": "CONCETTO_GIURIDICO",
      "start_char": 23,
      "end_char": 34,
      "normalized_text": "simulazione",
      "metadata": {
        "concept": "simulazione"
      }
    }
  ],
  "references": {
    "normative": [
      {
        "type": "ARTICOLO_CODICE",
        "original_text": "articolo 1414 del codice civile",
        "normalized_text": "Articolo 1414 Codice Civile",
        "codice": "Codice Civile",
        "articolo": "1414"
      }
    ],
    "jurisprudence": [],
    "concepts": [
      {
        "type": "CONCETTO_GIURIDICO",
        "original_text": "simulazione",
        "normalized_text": "simulazione"
      }
    ]
  },
  "metadata": {
    "processed_by": "NER-Giuridico",
    "version": "0.1.0"
  }
}
```

## Risoluzione dei Problemi

### Problemi Comuni e Soluzioni

#### Il server API non si avvia

**Problema**: Il server API non si avvia e restituisce un errore.

**Soluzione**:

1. Verifica che la porta specificata non sia già in uso
2. Controlla i log per errori specifici
3. Verifica che tutte le dipendenze siano installate correttamente

#### Errori di memoria con modelli transformer

**Problema**: Il sistema va in errore di memoria quando si utilizzano modelli transformer.

**Soluzione**:

1. Riduci il batch size nel file di configurazione
2. Abilita la quantizzazione del modello
3. Utilizza un hardware con più RAM o una GPU

#### Problemi di connessione con Neo4j

**Problema**: Il sistema non riesce a connettersi al database Neo4j.

**Soluzione**:

1. Verifica che Neo4j sia in esecuzione
2. Controlla le credenziali nel file di configurazione
3. Verifica che il firewall non blocchi la connessione

### Come Ottenere Supporto

Per ottenere supporto:

1. Consulta la documentazione completa nel repository
2. Apri una issue su GitHub
3. Contatta il team di sviluppo all'indirizzo support@merl-t.org
