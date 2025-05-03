# MERL-T: Multi-Expert Retrieval Legal Transformer

MERL-T è un framework AI specializzato per il diritto italiano, sviluppato nell'ambito dell'iniziativa LAIBIT (Legal AI Benchmark Italia). Il sistema utilizza un'architettura Mixture of Agents (MoA) che integra componenti come Knowledge Graph, database vettoriali e API esterne.

## Prerequisiti

- Python 3.12 o superiore
- Pip (gestore pacchetti Python)
- Git
- X GB di RAM (consigliati X GB per l'uso di modelli NER su CPU)
- GPU con almeno X GB di memoria VRAM (opzionale, consigliata per performance)
- Connessione Internet (per il download dei modelli e l'integrazione con API)

## Installazione

```bash
# Clona il repository
git clone https://github.com/laibit/merl-t.git
cd merl-t

# Crea e attiva un ambiente virtuale (opzionale ma consigliato)
python -m venv .venv

# Su Windows
.venv\Scripts\activate

# Su macOS/Linux
source .venv/bin/activate

# Installa le dipendenze
pip install -e .
```

### Configurazione ambiente

Il progetto utilizza file di configurazione YAML e variabili d'ambiente:

1. Copia il file di configurazione di esempio:

   ```bash
   cp config/example.env .env
   ```
2. Modifica il file `.env` aggiungendo le tue API key e configurazioni specifiche:

   ```
   # OpenAI API
   OPENAI_API_KEY=your_api_key_here

   # Anthropic API
   ANTHROPIC_API_KEY=your_api_key_here

   # Usa GPU se disponibile
   USE_GPU=true
   ```

## Utilizzo

MERL-T può essere utilizzato in diversi modi:

### 1. Utilizzo dell'API Python

```python
from merl_t import Orchestrator

# Inizializza il sistema
orchestrator = Orchestrator()

# Esegui una query in modo asincrono
import asyncio

async def run_query():
    result = await orchestrator.process_query("Quali sono le differenze tra responsabilità contrattuale ed extracontrattuale?")
    print(result)

asyncio.run(run_query())
```

### 2. Avviare i server MCP

MERL-T implementa il Model Context Protocol (MCP), che permette di esporre funzionalità tramite server:

```bash
# Avvia server NER con transport WebSocket
python -m merl_t.server --server-type ner --transport websocket --port 8765

# Avvia server VisuaLex
python -m merl_t.server --server-type visualex --transport websocket --port 8766

# Avvia server Knowledge Graph
python -m merl_t.server --server-type knowledge_graph --transport websocket --port 8767
```

### 3. Script di avvio rapido

Per avviare tutti i servizi in un unico comando:

```bash
# Avvia tutti i servizi
./start_services.sh

# Ferma tutti i servizi
./stop_services.sh
```

## Esecuzione dei test

Il progetto include una suite di test unitari e di integrazione:

```bash
# Esegui tutti i test
python -m merl_t.tests.run_tests

# Esegui solo i test unitari
python -m merl_t.tests.run_tests --type unit

# Esegui solo i test di integrazione
python -m merl_t.tests.run_tests --type integration

# Genera report di copertura del codice
python -m merl_t.tests.run_tests --coverage
```

## Architettura

MERL-T implementa un'architettura basata sui protocolli:

- **Model Context Protocol (MCP)**: Permette la comunicazione standardizzata tra LLM e servizi esterni
- **Agent-to-Agent Protocol (A2A)**: Abilita la comunicazione tra i diversi agenti specialistici

L'architettura è composta da:

1. **Moduli di pre-processing e NER**: Normalizzazione del testo ed estrazione di entità legali
2. **Router MoE**: Sistema di "gating" che analizza la query e attiva i moduli esperti appropriati
3. **Moduli Esperti**:
   - **Modulo Principi**: Specializzato in dottrina e principi fondamentali
   - **Modulo Regole**: Focalizzato su norme specifiche e giurisprudenza
4. **Componenti di Context Augmentation**:
   - Database Vettoriale (RAG)
   - Knowledge Graph (GraphRAG)
   - API Esterne (VisuaLexAPI, API Sentenze)
5. **Sintetizzatore MoE**: Combina le risposte dei moduli esperti
6. **Infrastruttura RLCF**: Ciclo di feedback per l'addestramento continuo

## Struttura del Repository

- `/merl_t/`
  - `/mcp/`: Implementazione del Model Context Protocol
    - `/base.py`: Classi base BaseMCPServer e BaseMCPHost
    - `/protocol.py`: Strutture dati e messaggi JSON-RPC
    - `/servers/`: Server MCP per diversi componenti
      - `ner_server.py`: Server MCP per Named Entity Recognition
  - `/a2a/`: Implementazione dell'Agent-to-Agent Protocol
    - `/base.py`: Classe base BaseAgent
    - `/protocol.py`: Strutture dati (Task, Artifact, Message, ecc.)
    - `/agents/`: Implementazioni di agenti specializzati
  - `/core/`: Componenti core del sistema
    - `/ner/`: Moduli di Named Entity Recognition
      - `entities.py`: Definizione delle entità legali
      - `entity_manager.py`: Gestione delle entità
      - `preprocessing.py`: Normalizzazione testi legali
      - `transformer.py`: Riconoscimento entità con modelli transformer
      - `normalizer.py`: Standardizzazione formati entità
      - `system.py`: Sistema NER completo
    - `/kg/`: Knowledge Graph (implementazione futura)
    - `/vdb/`: Vector Database (implementazione futura)
    - `/llm/`: Interfacce LLM (implementazione futura)
  - `/orchestrator/`: Coordinatore centrale del sistema
    - `main.py`: Implementazione dell'orchestratore
  - `/utils/`: Utilità generali
  - `/config/`: Gestione configurazione
  - `/tests/`: Unit e integration tests
  - `server.py`: Script di avvio server
  - `requirements.txt`: Dipendenze Python

## Contribuire al progetto

Se desideri contribuire al progetto, consulta il file [CONTRIBUTING.md](CONTRIBUTING.md) per le linee guida e il processo di sviluppo.

## Licenza

[MIT License](LICENSE)
