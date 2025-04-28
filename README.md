# MERL-T: Multi-Expert Retrieval Legal Transformer

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Status](https://img.shields.io/badge/status-development-orange)
![Version](https://img.shields.io/badge/version-0.1.0-brightgreen)

## 📖 Overview

**MERL-T** (Multi-Expert Retrieval Legal Transformer) is an advanced artificial intelligence system designed to democratize access to Italian legal knowledge. By combining cutting-edge AI architectures with a deep understanding of the legal domain, MERL-T aims to provide accurate, contextualized, and verifiable answers to legal questions.

### 🌟 Vision

The system aims to address the inherent complexity of the Italian legal system through an innovative approach that combines:
- **Mixture of Experts (MoE) Architecture** - Multiple specialized modules coordinated by an intelligent router
- **Legal Knowledge Graph** - A structured representation of legal knowledge and relationships between concepts
- **Reinforcement Learning from Community Feedback (RLCF)** - A continuous learning mechanism based on feedback from the legal community

## 🏗️ Architecture

MERL-T implements an advanced architecture organized into several key components:

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface                          │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                MoE Router/Orchestrator                      │
└───────┬─────────────────┬────────────────┬─────────┬────────┘
        │                 │                │         │
┌───────▼─────┐   ┌───────▼─────┐   ┌──────▼────┐    ▼
│ Principles  │   │   Rules     │   │Knowledge  │   MoE
│  Module     │   │   Module    │   │Graph      │ Synthesizer
└─────────────┘   └─────────────┘   └───────────┘
```

1. **MoE Router/Orchestrator**: Analyzes queries and directs them to the most appropriate expert modules
2. **Principles Module**: Specialized in doctrinal knowledge and fundamental legal principles
3. **Rules Module**: Handles normative knowledge and current legislation
4. **Knowledge Graph**: Represents relationships between legal concepts, norms, court decisions, and doctrine
5. **MoE Synthesizer**: Integrates responses from different modules into a coherent and comprehensive output

## 🛠️ Implemented Components

Currently, the project has implemented the following components:

### 1. VisuaLex API

VisuaLex is an API that allows the retrieval and processing of legal documents from various sources, including:
- **Normattiva**: For Italian legislation
- **Brocardi**: For legal commentary and interpretations
- **EUR-Lex**: For European Union legislation

#### Basic Usage

```python
from src.utils.visualex_api.app import NormaController

# Initialize the controller
controller = NormaController()

# Example request for a civil code article
response = await controller.fetch_article_text({
    "act_type": "codice civile",
    "article": "1414"
})
```

### 2. NER-Giuridico

A Named Entity Recognition system specialized for the Italian legal domain, capable of identifying and classifying entities such as normative references, jurisprudential references, and legal concepts.

#### Key Features

- Recognition of normative entities (articles, laws, decrees)
- Recognition of jurisprudential entities (court decisions, ordinances)
- Identification of legal concepts
- Support for user-defined dynamic entities
- Integrated annotation interface for creating training datasets

#### Basic Usage

```python
from src.data_lab.ner-giuridico.ner.ner import DynamicNERGiuridico

# Initialize the NER system
ner = DynamicNERGiuridico()

# Process a text
result = ner.process("L'articolo 1414 c.c. disciplina la simulazione del contratto.")
print(result)
```

### 3. PDF Chunker

A module for extracting, cleaning, and chunking text from legal PDF documents, optimized for preparing datasets for language model training.

#### Basic Usage

```python
from src.data_lab.pdf_chunker.extractor import main as extract_pdfs

# Extract text from PDFs
extract_pdfs(input_dir="./legal_pdfs", output_dir="./processed")
```

## 🚀 Installation

### Prerequisites

- Python 3.10+
- pip (Package Installer for Python)
- Git

### Basic Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/MERL-T.git
cd MERL-T

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### Component Configuration

#### VisuaLex API

```bash
# Start the VisuaLex API
cd src/utils/visualex_api
python app.py
```

#### NER-Giuridico

```bash
# Start the NER API
cd src/data_lab/ner-giuridico
python ner/main.py server

# Start the annotation interface
python ner/main.py annotate
```

## 📋 Roadmap

MERL-T development is organized into the following phases:

### Phase 1: Base Infrastructure and Core Components (Current)

- ✅ Development of VisuaLex API for legal document retrieval
- ✅ Implementation of the NER-Giuridico system
- ✅ Creation of document processing tools (PDF Chunker)
- 🔄 Definition of the Knowledge Graph schema

### Phase 2: Router and Expert Modules (Next)

- 🔄 Development of the legal Knowledge Graph
- 🔄 Implementation of the Rules Module (Retrieval-Augmented Generation)
- 🔜 Implementation of the Principles Module
- 🔜 Development of the MoE Router/Orchestrator

### Phase 3: Integration and RLCF (Future)

- 🔜 Implementation of the MoE Synthesizer
- 🔜 Development of the RLCF system
- 🔜 Complete integration of components
- 🔜 System evaluation and optimization

## 📚 Context and LAIBIT Project

MERL-T is part of the **LAIBIT** (Legal AI Benchmark Italia) initiative, a scientific community and development project aimed at promoting the application of artificial intelligence to Italian law according to principles of rigor, ethics, and transparency.

The project adopts a community validation and transparency approach through the RLCF (Reinforcement Learning from Community Feedback) system, in which the intelligence of the system is constantly refined and validated by structured feedback from qualified legal experts.

## 👥 Contributing to the Project

We are open to various types of contributions, particularly:

- Development of core components
- Expansion of the Knowledge Graph
- Annotation of training datasets
- Legal validation of responses
- Documentation and tutorials

To contribute, please:
1. Fork the repository
2. Create a new branch for your changes (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

For more details, see the [CONTRIBUTING.md](CONTRIBUTING.md) file.

## 📄 License

The code is released under the MIT license. Datasets and the Knowledge Graph are available under the CC BY-SA license.

## 📬 Contact

For more information, contact the development team at [guglielmo.puzio@studenti.luiss.it].

---

MERL-T - Making Italian law accessible, understandable, and applicable through artificial intelligence.

# Sistema di Named Entity Recognition per testi giuridici italiani

## Descrizione

Questo sistema è progettato per riconoscere entità giuridiche in testi legali italiani. Il sistema NER (Named Entity Recognition) è in grado di identificare vari tipi di riferimenti normativi e giurisprudenziali, così come concetti giuridici.

## Funzionalità

- **Sistema di NER unificato**: integra riconoscimento basato su regole e modelli transformer
- **Supporto per l'addestramento**: usa dati annotati nel formato Spacy per addestrare modelli personalizzati
- **Configurabile**: sistema flessibile con configurazione tramite file JSON
- **Normalizzazione**: normalizza le entità riconosciute in formati standard
- **Classificazione**: supporta diverse categorie di entità giuridiche

## Tipi di entità supportate

- **Riferimenti normativi**:
  - Articoli del codice
  - Leggi
  - Decreti
  - Regolamenti UE

- **Riferimenti giurisprudenziali**:
  - Sentenze
  - Ordinanze

- **Concetti giuridici**

## Utilizzo

### Inizializzazione

```python
from src.processing.ner import NERSystem

# Inizializza il sistema NER
ner = NERSystem()

# Elabora un testo
result = ner.process("L'articolo 1414 c.c. disciplina la simulazione.")

# Visualizza le entità riconosciute
print(result["entities"])
```

### Addestramento

```python
# Carica i dati di addestramento (formato Spacy)
training_data = ner.load_training_data("path/to/training_data.json")

# Addestra il modello
ner.train(training_data, output_dir="models/my_ner_model")

# Carica un modello addestrato
ner.load_model("models/my_ner_model")
```

## Configurazione

È possibile configurare il sistema tramite un file JSON:

```python
from src.processing.ner import load_config

# Carica la configurazione
load_config("path/to/config.json")
```

Esempio di file di configurazione:

```json
{
  "models": {
    "transformer": {
      "model_name": "dbmdz/bert-base-italian-xxl-cased",
      "device": -1
    }
  },
  "training": {
    "epochs": 10,
    "batch_size": 32
  }
}
```

## Installazione

```bash
pip install -r requirements.txt
```
