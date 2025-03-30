# NER-Giuridico

Sistema di Named Entity Recognition specializzato per il riconoscimento di entità giuridiche in testi italiani, sviluppato come componente del progetto MERL-T (Multi Expert Retrival Legal Transformer).

## Descrizione

NER-Giuridico è un modulo di preprocessing per il sistema MERL-T che si occupa di identificare e normalizzare riferimenti a fonti giuridiche nel testo delle query, facilitando il routing verso gli esperti appropriati. Il sistema è in grado di riconoscere:

1. **Riferimenti Normativi**:
   - Articoli di codici (es. "art. 1414 c.c.", "articolo 15 codice civile")
   - Leggi (es. "legge 241/1990", "l. n. 241 del 7 agosto 1990")
   - Decreti (es. "d.lgs. 50/2016", "decreto legislativo n. 50 del 2016")
   - Regolamenti UE (es. "Regolamento UE 2016/679", "GDPR")

2. **Riferimenti Giurisprudenziali**:
   - Sentenze (es. "Cassazione civile n. 12345/2023")
   - Ordinanze (es. "ordinanza Tribunale Milano del 15/03/2022")

3. **Concetti Giuridici**:
   - Principi e istituti fondamentali (es. "simulazione", "buona fede")

## Architettura

Il sistema utilizza un approccio ibrido che combina:

- **Riconoscimento basato su regole**: Pattern regex e gazetteer per identificare entità con alta precisione
- **Riconoscimento basato su modelli transformer**: Modelli pre-addestrati o fine-tuned per identificare entità complesse
- **Sistema di normalizzazione**: Converte le entità riconosciute in forme canoniche e arricchisce i metadati
- **Integrazione con knowledge graph**: Arricchisce le entità con dati dal knowledge graph Neo4j

## Struttura del Progetto

```
ner_giuridico/
├── config/
│   └── config.yaml         # Configurazione del sistema
├── data/
│   ├── patterns/           # Pattern regex e gazetteer
│   └── annotation/         # Dati per l'annotazione
├── docs/
│   └── deployment.md       # Documentazione per il deployment
├── models/
│   └── transformer/        # Modelli transformer fine-tuned
├── src/
│   ├── __init__.py
│   ├── api.py              # API FastAPI
│   ├── annotation.py       # Interfaccia di annotazione
│   ├── config.py           # Gestione della configurazione
│   ├── entities.py         # Definizione delle entità
│   ├── ner.py              # Classe principale
│   ├── normalizer.py       # Normalizzazione delle entità
│   ├── preprocessing.py    # Preprocessing del testo
│   ├── rule_based.py       # Riconoscitore basato su regole
│   └── transformer.py      # Riconoscitore basato su transformer
├── tests/                  # Test unitari e di integrazione
├── main.py                 # Script principale
└── requirements.txt        # Dipendenze
```

## Installazione

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

## Utilizzo

### Avvio del Server API

```bash
python main.py server --host 0.0.0.0 --port 8000
```

### Elaborazione di un Testo

```bash
python main.py process --text "L'articolo 1414 c.c. disciplina la simulazione del contratto."
```

### Elaborazione Batch

```bash
python main.py batch --dir /path/to/input/dir --output /path/to/output/dir --ext txt
```

### Interfaccia di Annotazione

```bash
python main.py annotate --tool label-studio
```

## Documentazione

Per informazioni dettagliate sul deployment e l'operatività del sistema, consulta la [Guida al Deployment](docs/deployment.md).

## Licenza

Questo progetto è rilasciato sotto licenza MIT.

## Contatti

Per domande o supporto, contatta il team di sviluppo all'indirizzo info@merl-t.org.
