
# NER-Giuridico User Manual

## Table of Contents

1. [Introduction](https://claude.ai/chat/b37a541e-c6d1-4e39-bb27-49dea763b2fd#introduction)
2. [Installation and Setup](https://claude.ai/chat/b37a541e-c6d1-4e39-bb27-49dea763b2fd#installation-and-setup)
3. [System Architecture](https://claude.ai/chat/b37a541e-c6d1-4e39-bb27-49dea763b2fd#system-architecture)
4. [Using the System](https://claude.ai/chat/b37a541e-c6d1-4e39-bb27-49dea763b2fd#using-the-system)
5. [Entity Types and Recognition](https://claude.ai/chat/b37a541e-c6d1-4e39-bb27-49dea763b2fd#entity-types-and-recognition)
6. [Customizing the System](https://claude.ai/chat/b37a541e-c6d1-4e39-bb27-49dea763b2fd#customizing-the-system)
7. [Training and Fine-tuning](https://claude.ai/chat/b37a541e-c6d1-4e39-bb27-49dea763b2fd#training-and-fine-tuning)
8. [Annotation Interface](https://claude.ai/chat/b37a541e-c6d1-4e39-bb27-49dea763b2fd#annotation-interface)
9. [API Reference](https://claude.ai/chat/b37a541e-c6d1-4e39-bb27-49dea763b2fd#api-reference)
10. [Deployment Guide](https://claude.ai/chat/b37a541e-c6d1-4e39-bb27-49dea763b2fd#deployment-guide)
11. [Troubleshooting](https://claude.ai/chat/b37a541e-c6d1-4e39-bb27-49dea763b2fd#troubleshooting)

## Introduction

NER-Giuridico is a specialized Named Entity Recognition system designed for identifying and normalizing legal entities in Italian texts. Developed as a component of the MERL-T (Multi Expert Retrieval Legal Transformer) project, it processes text to identify, classify, and normalize references to various legal sources.

### Key Features

* Recognition of normative references (code articles, laws, decrees, EU regulations)
* Recognition of jurisprudential references (court decisions, ordinances)
* Recognition of legal concepts
* Rule-based and transformer-based recognition models
* Entity normalization and metadata enrichment
* Integration with knowledge graphs
* Dynamic entity type management
* REST API for easy integration
* Annotation interface for training data creation
* Fine-tuning capabilities for domain-specific models

### Use Cases

* Legal document processing
* Query preprocessing for legal information retrieval
* Automatic tagging of legal documents
* Enhanced legal search functionality
* Relationship extraction between legal entities

## Installation and Setup

### Prerequisites

* Python 3.8+
* Neo4j (optional, for knowledge graph integration)
* Docker (optional, for containerized deployment)

### Hardware Requirements

* CPU: 4+ cores
* RAM: 8+ GB (16+ GB recommended for high workloads)
* Disk Space: 10+ GB
* GPU: Optional but recommended for optimal performance with transformer models

### Installation Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/merl-t/ner-giuridico.git
   cd ner-giuridico
   ```
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Install language models:
   ```bash
   python -m spacy download it_core_news_lg
   ```
5. Run the setup script to configure the system:
   ```bash
   python setup.py --all
   ```

### Configuration

The system uses a YAML configuration file located at `config/config.yaml`. Key configuration sections include:

* `general`: Basic system settings
* `models`: Configuration for transformer, spaCy, and rule-based models
* `entities`: Entity type definitions and settings
* `preprocessing`: Text preprocessing pipeline settings
* `normalization`: Entity normalization settings
* `api`: REST API configuration
* `monitoring`: Prometheus and logging configuration

Example configuration for transformer models:

```yaml
models:
  transformer:
    model_name: "dbmdz/bert-base-italian-xxl-cased"
    max_length: 512
    batch_size: 16
    device: "cuda"  # Use "cpu" if no GPU is available
    quantization: true
```

## System Architecture

NER-Giuridico follows a modular architecture that combines multiple components for entity recognition, normalization, and management.

### Core Components

![NER-Giuridico Architecture](https://claude.ai/chat/architecture-diagram.png)

1. **NERGiuridico** : The main class that coordinates the NER process.
2. **EntityManager** : Manages entity types, their definitions, and properties.
3. **PreProcessor** : Handles text preprocessing, including tokenization and segmentation.
4. **RuleBasedRecognizer** : Identifies entities using regex patterns and gazetteers.
5. **TransformerRecognizer** : Uses transformer models for entity recognition.
6. **EntityNormalizer** : Normalizes recognized entities to canonical forms.
7. **API** : Provides REST API access to the system.

### Processing Pipeline

1. **Preprocessing** : Text is tokenized, normalized, and segmented.
2. **Entity Recognition** :

* Rule-based recognizer identifies entities using patterns.
* Transformer-based recognizer identifies entities using trained models.
* Results are merged and overlapping entities are resolved.

1. **Normalization** : Recognized entities are normalized to canonical forms.
2. **Structured Reference Creation** : Normalized entities are converted to structured references.

### Entity Management

The system supports both static and dynamic entity types:

* **Static Entities** : Defined through the `EntityType` enum in `entities.py`.
* **Dynamic Entities** : Managed by the `DynamicEntityManager` in `entity_manager.py`.

## Using the System

### Command-Line Interface

The system provides a command-line interface for various operations:

#### Server Mode

To start the API server:

```bash
python main.py server --host 0.0.0.0 --port 8000
```

#### Process Mode

To process a single text:

```bash
python main.py process --text "L'articolo 1414 c.c. disciplina la simulazione del contratto."
```

Or from a file:

```bash
python main.py process --file input.txt --output result.json
```

#### Batch Mode

To process multiple files:

```bash
python main.py batch --dir /path/to/input/dir --output /path/to/output/dir --ext txt
```

#### Annotation Mode

To start the annotation interface:

```bash
python main.py annotate --tool label-studio
```

### REST API

The system provides a RESTful API for integration with other applications.

#### Endpoints

* `POST /api/v1/recognize`: Recognizes entities in a text.
* `POST /api/v1/batch`: Processes multiple texts in batch.
* `POST /api/v1/feedback`: Provides feedback on recognized entities.
* `POST /api/v1/moe/preprocess`: Preprocesses a query for the MoE router.
* `GET /api/v1/entities/`: Lists all entity types.
* `GET /api/v1/entities/{entity_name}`: Gets information about a specific entity type.
* `POST /api/v1/entities/`: Creates a new entity type.
* `PUT /api/v1/entities/{entity_name}`: Updates an existing entity type.
* `DELETE /api/v1/entities/{entity_name}`: Deletes an entity type.

#### Example API Request

Recognize entities in a text:

```bash
curl -X POST http://localhost:8000/api/v1/recognize \
  -H "Content-Type: application/json" \
  -d '{"text": "L'\''articolo 1414 c.c. disciplina la simulazione del contratto."}'
```

Example response:

```json
{
  "text": "L'articolo 1414 c.c. disciplina la simulazione del contratto.",
  "entities": [
    {
      "text": "articolo 1414 c.c.",
      "type": "ARTICOLO_CODICE",
      "start_char": 2,
      "end_char": 19,
      "normalized_text": "Articolo 1414 Codice Civile",
      "metadata": {
        "codice": "Codice Civile",
        "articolo": "1414"
      }
    },
    {
      "text": "simulazione",
      "type": "CONCETTO_GIURIDICO",
      "start_char": 32,
      "end_char": 43,
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
        "original_text": "articolo 1414 c.c.",
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
  }
}
```

### Programmatic Usage

You can use the NER-Giuridico system programmatically within your Python applications:

```python
from src.ner import NERGiuridico

# Initialize the NER system
ner = NERGiuridico()

# Process a text
text = "L'articolo 1414 c.c. disciplina la simulazione del contratto."
result = ner.process(text)

# Access the recognized entities
for entity in result["entities"]:
    print(f"Entity: {entity['text']}, Type: {entity['type']}, Normalized: {entity['normalized_text']}")

# Access the structured references
for ref in result["references"]["normative"]:
    print(f"Normative Reference: {ref['normalized_text']}")
```

For dynamic entity support:

```python
from src.ner import DynamicNERGiuridico

# Initialize the dynamic NER system
dynamic_ner = DynamicNERGiuridico()

# Add a custom entity type
dynamic_ner.add_entity_type(
    name="CUSTOM_ENTITY",
    display_name="Custom Entity",
    category="custom",
    color="#FF5733",
    metadata_schema={"field1": "string", "field2": "string"},
    patterns=["custom pattern 1", "custom pattern 2"]
)

# Process a text with the custom entity type
result = dynamic_ner.process(text)
```

## Entity Types and Recognition

### Built-in Entity Types

NER-Giuridico comes with several built-in entity types:

1. **Normative References** :

* `ARTICOLO_CODICE`: References to code articles (e.g., "art. 1414 c.c.")
* `LEGGE`: References to laws (e.g., "legge 241/1990")
* `DECRETO`: References to decrees (e.g., "d.lgs. 50/2016")
* `REGOLAMENTO_UE`: References to EU regulations (e.g., "GDPR")

1. **Jurisprudential References** :

* `SENTENZA`: References to court decisions (e.g., "Cassazione civile n. 12345/2023")
* `ORDINANZA`: References to ordinances (e.g., "ordinanza Tribunale Milano del 15/03/2022")

1. **Legal Concepts** :

* `CONCETTO_GIURIDICO`: Legal concepts (e.g., "simulazione", "buona fede")

### Recognition Methods

The system uses two main methods for entity recognition:

1. **Rule-Based Recognition** :

* Uses regex patterns to identify entities
* Patterns are defined in JSON files in the `data/patterns` directory
* Each entity type has its own set of patterns
* Gazetteers are used for concept recognition

1. **Transformer-Based Recognition** :

* Uses pre-trained or fine-tuned transformer models
* Supports model quantization for better performance on limited hardware
* Can be fine-tuned with domain-specific data

### Entity Normalization

After recognition, entities are normalized to canonical forms:

1. **Normative References** :

* Code articles are normalized to "Articolo X Codice Y"
* Laws are normalized to "Legge n. X/YYYY"
* Decrees are normalized to their full form (e.g., "Decreto Legislativo n. X/YYYY")

1. **Jurisprudential References** :

* Court decisions are normalized to include the court, section, number, and date
* Ordinances are normalized similarly

1. **Legal Concepts** :

* Normalized to lowercase canonical forms

### Knowledge Graph Integration

The system can enrich entities with data from a Neo4j knowledge graph:

1. **Configuration** :

```yaml
   normalization:
     use_knowledge_graph: true
     knowledge_graph:
       url: "bolt://localhost:7687"
       user: "neo4j"
       password: "password"
```

1. **Entity Enrichment** :

* Entities are matched with nodes in the knowledge graph
* Additional metadata from the knowledge graph is added to the entity

## Customizing the System

### Adding Custom Entity Types

You can add custom entity types to the system using the dynamic entity manager:

1. **Programmatically** :

```python
   from src.ner import DynamicNERGiuridico

   ner = DynamicNERGiuridico()
   ner.add_entity_type(
       name="CONTRATTO_SPECIFICO",
       display_name="Contratto Specifico",
       category="custom",
       color="#FF5733",
       metadata_schema={"tipo": "string", "parti": "string"},
       patterns=["contratto di (\w+)", "accordo di (\w+)"]
   )
```

1. **Via API** :

```bash
   curl -X POST http://localhost:8000/api/v1/entities/ \
     -H "Content-Type: application/json" \
     -d '{
       "name": "CONTRATTO_SPECIFICO",
       "display_name": "Contratto Specifico",
       "category": "custom",
       "color": "#FF5733",
       "metadata_schema": {"tipo": "string", "parti": "string"},
       "patterns": ["contratto di (\\w+)", "accordo di (\\w+)"]
     }'
```

### Customizing Recognition Patterns

You can update the patterns used for entity recognition:

1. **Programmatically** :

```python
   ner.update_entity_type(
       name="ARTICOLO_CODICE",
       patterns=["nuovo pattern 1", "nuovo pattern 2"]
   )
```

1. **Via API** :

```bash
   curl -X POST http://localhost:8000/api/v1/entities/ARTICOLO_CODICE/patterns \
     -H "Content-Type: application/json" \
     -d '["nuovo pattern 1", "nuovo pattern 2"]'
```

1. **By editing the pattern files** :
   Edit the JSON files in the `data/patterns` directory.

### Customizing Normalization

You can customize the normalization process by:

1. Updating the canonical forms in the `data/canonical_forms.json` file
2. Updating the abbreviations in the `data/abbreviations.json` file
3. Implementing custom normalizer functions:

```python
from src.normalizer import EntityNormalizer

normalizer = EntityNormalizer()

# Register a custom normalizer
def custom_normalizer(entity):
    entity.normalized_text = f"Custom: {entity.text}"
    return entity

normalizer.register_normalizer("CUSTOM_ENTITY", custom_normalizer)
```

## Training and Fine-tuning

### Creating Training Data

To train or fine-tune the models, you need annotated data. You can create this using the annotation interface:

1. Start the annotation interface:
   ```bash
   python main.py annotate --tool label-studio
   ```
2. Access the interface at `http://localhost:8080`
3. Upload documents for annotation
4. Annotate entities in the documents
5. Export the annotations for training

### Training a New Model

You can train a new model using the `ner_trainer.py` module:

```python
from src.training.ner_trainer import NERTrainer

# Initialize the trainer
trainer = NERTrainer()

# Train from spaCy format
model_path = trainer.train_from_spacy_format(
    spacy_data=annotations,
    output_model_name="my_custom_model"
)

# Or train a transformer model
model_path = trainer.train_transformer_model(
    annotations_file="path/to/annotations.json",
    base_model="dbmdz/bert-base-italian-xxl-cased",
    output_model_name="my_transformer_model"
)

# Integrate the model with the NER system
trainer.integrate_model_with_ner_system(model_path)
```

### Converting Annotation Formats

The system includes utilities for converting between different annotation formats:

```python
from src.utils.converter import convert_annotations_to_spacy_format, save_annotations_for_training

# Convert from label-studio format to spaCy format
spacy_data = convert_annotations_to_spacy_format(annotations, documents)

# Save in multiple formats for training
output_files = save_annotations_for_training(
    annotations=annotations,
    documents=documents,
    output_dir="path/to/output",
    formats=["spacy", "ner", "conll"]
)
```

## Annotation Interface

The system includes a web-based annotation interface for creating training data:

### Starting the Interface

```bash
python main.py annotate --tool label-studio
```

Or use the dedicated script:

```bash
cd src/annotation
./start_annotation.sh
```

### Interface Features

* Document list for selecting texts to annotate
* Entity type selector with color coding
* Annotation area for selecting text spans
* List of existing annotations
* Auto-annotation using the current NER model
* Export annotations in various formats
* Integration with the training pipeline

### Annotation Workflow

1. Upload documents to the system
2. Select a document to annotate
3. Select an entity type from the sidebar
4. Highlight text in the document to create annotations
5. Review and edit annotations as needed
6. Export annotations for training
7. Train the model with the annotations

## API Reference

### Main API Endpoints

#### Entity Recognition

`POST /api/v1/recognize`

* **Description** : Recognizes entities in a text
* **Request Body** :

```json
  {  "text": "Text to analyze",  "options": {} // Optional parameters}
```

* **Query Parameters** :
* `dynamic` (boolean): Use dynamic entity system

#### Batch Processing

`POST /api/v1/batch`

* **Description** : Processes multiple texts
* **Request Body** :

```json
  {  "texts": ["Text 1", "Text 2"],  "options": {} // Optional parameters}
```

#### Entity Management

`GET /api/v1/entities/`

* **Description** : Lists all entity types
* **Query Parameters** :
* `category` (string): Filter by category

`GET /api/v1/entities/{entity_name}`

* **Description** : Gets information about a specific entity type

`POST /api/v1/entities/`

* **Description** : Creates a new entity type
* **Request Body** :

```json
  {  "name": "ENTITY_NAME",  "display_name": "Entity Display Name",  "category": "category",  "color": "#RRGGBB",  "metadata_schema": {},  "patterns": [] // Optional}
```

`PUT /api/v1/entities/{entity_name}`

* **Description** : Updates an existing entity type
* **Request Body** :

```json
  {  "display_name": "New Display Name", // Optional  "color": "#RRGGBB", // Optional  "metadata_schema": {}, // Optional  "patterns": [] // Optional}
```

`DELETE /api/v1/entities/{entity_name}`

* **Description** : Deletes an entity type

### Error Handling

The API returns standard HTTP status codes:

* 200: Success
* 400: Bad Request (invalid parameters)
* 404: Not Found (entity not found)
* 500: Internal Server Error

Error responses include a `detail` field with an error message:

```json
{
  "detail": "Error message"
}
```

## Deployment Guide

### Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t ner-giuridico .
   ```
2. Run the container:
   ```bash
   docker run -d -p 8000:8000 --name ner-giuridico ner-giuridico
   ```

### Docker Compose

1. Create a `docker-compose.yml` file:
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
2. Start the services:
   ```bash
   docker-compose up -d
   ```

### Kubernetes Deployment

1. Create a `deployment.yaml` file:
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
   ```
2. Create a `service.yaml` file:
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
3. Apply the configuration:
   ```bash
   kubectl apply -f deployment.yaml
   kubectl apply -f service.yaml
   ```

### Performance Optimization

For better performance in production:

1. Use a GPU for transformer models:
   ```yaml
   models:
     transformer:
       device: "cuda"
   ```
2. Enable model quantization for CPU deployment:
   ```yaml
   models:
     transformer:
       device: "cpu"
       quantization: true
   ```
3. Adjust batch size and worker count:
   ```yaml
   models:
     transformer:
       batch_size: 32
   api:
     workers: 8
   ```
4. Enable Prometheus monitoring:
   ```yaml
   monitoring:
     prometheus:
       enable: true
       port: 9090
   ```

## Troubleshooting

### Common Issues and Solutions

#### API Server Won't Start

 **Problem** : The API server doesn't start and returns an error.

 **Solution** :

1. Check if the specified port is already in use
2. Check logs for specific errors
3. Verify that all dependencies are correctly installed

#### Memory Errors with Transformer Models

 **Problem** : The system runs out of memory when using transformer models.

 **Solution** :

1. Reduce the batch size in the configuration
2. Enable model quantization
3. Use a machine with more RAM or a GPU

#### Connection Issues with Neo4j

 **Problem** : The system can't connect to Neo4j database.

 **Solution** :

1. Verify that Neo4j is running
2. Check the credentials in the configuration
3. Ensure the firewall isn't blocking the connection

#### Entity Recognition Problems

 **Problem** : The system doesn't recognize expected entities.

 **Solution** :

1. Check the patterns in the `data/patterns` directory
2. Ensure the transformer model is correctly loaded
3. Verify the entity types are correctly configured

#### Slow Performance

 **Problem** : The system is processing texts slowly.

 **Solution** :

1. Use a GPU for transformer models
2. Enable model quantization
3. Increase the batch size
4. Process large texts in parallel using the batch API

### Getting Support

For additional support:

1. Check the complete documentation in the repository
2. Open an issue on GitHub
3. Contact the development team at support@merl-t.org
