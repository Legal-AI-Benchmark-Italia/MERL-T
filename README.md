# 📚 MERL-T: Sistema di Q&A Giuridico

**MERL-T** è un progetto open-source finalizzato alla creazione di un sistema intelligente di domande e risposte (Q&A) nel settore giuridico. Destinato ad accademici, studenti e cittadini, il progetto combina intelligenza artificiale, knowledge graphs e database vettoriali per offrire risposte affidabili e basate su fonti verificate.

---

## 📌 Struttura del Repository

```
|-- CONTRIBUTING.md
|-- LICENSE
|-- README.md
|-- .gitignore
|-- src
    |-- main.py
    |-- orchestrator/
    |-- prompts/
    |-- utils/
    |-- evaluations/
    |-- data/
        |-- extractor.py
        |-- dottrina/
        |-- giurisprudenza/
        |-- legge/
|-- .venv/
```

---

## 🎯 Obiettivi

* Creare un sistema Q&A giuridico accessibile e rigoroso.
* Sviluppare un Knowledge Graph aperto con dati annotati e verificati.
* Automatizzare l'analisi e il recupero di informazioni normative e giurisprudenziali.

---

## 🛠 Tecnologie Utilizzate

* **Linguaggio** : Python (Flask)
* **ML** : Logistic Regression, Random Forest (scikit-learn)
* **LLM** : OpenAI GPT
* **Database Vettoriale** : ChromaDB (sviluppo) → Weaviate (produzione)
* **Knowledge Graph** : Neo4j
* **Dataset** : JSON annotati

---

## 🚀 Fasi di Sviluppo

### 🟢 **Fase 1: Setup Iniziale (Mesi 1-2)**

* Normalizzazione query utente
* Integrazione API VLEX per il recupero normativo
* Creazione Knowledge Graph iniziale

### 🟢 **Fase 2: Costruzione Dataset e Moduli Core (Mesi 3-5)**

* Annotazione e revisione dati
* Sviluppo di un Intent Classifier ML
* Fine-tuning GPT con dati giuridici

### 🟢 **Fase 3: Lancio e Consolidamento (Mesi 6-12)**

* Beta testing pubblico
* Aggiornamenti trimestrali del Knowledge Graph
* Monitoraggio continuo delle prestazioni

---

## 🔄 Pipeline MERL-T

1. **Input query utente**
2. **Pre-processing** : pulizia, estrazione riferimenti
3. **Classificazione intento** : Principi, Normativa, Mista
4. **Recupero informazioni** da:
   * GPT fine-tuned
   * API VLEX
   * Database vettoriale
   * Knowledge Graph
5. **Post-processing** : strutturazione risposta
6. **Output formattato** per l'utente
7. **Monitoraggio qualità e feedback**

---

## 📈 Metriche di Valutazione

**Qualitative:**

* Accuratezza giuridica
* Comprensibilità delle risposte
* Feedback utenti

**Quantitative:**

* Dimensione del Knowledge Graph
* Precisione del classificatore di intenti
* Numero di query elaborate

---

## 🌐 Open Source & Community

* **Licenze:** MIT (codice) e CC BY-SA (dati)
* **Repository GitHub pubblico** per contributi e feedback
* **Collaborazione aperta** con accademici e sviluppatori
* **Seminari e pubblicazioni** per validazione scientifica

---

## 👥 Ruoli e Responsabilità

* **Coordinatore Generale:** supervisione, gestione community
* **Studenti:** annotazione dati e test
* **Professori:** revisione e validazione scientifica
* **Team Tecnico:** sviluppo AI, gestione database e knowledge graph

---

## 📅 Roadmap Sintetica

| **Fase** | **Durata** | **Obiettivo**                          |
| -------------- | ---------------- | -------------------------------------------- |
| Setup iniziale | 2 mesi           | API, KG, pipeline di base                    |
| Sviluppo ML    | 3-5 mesi         | Classificatore, embeddings, fine-tuning      |
| Beta Testing   | 6-12 mesi        | Test pubblico, miglioramenti, consolidamento |

---

MERL-T è un progetto ambizioso che punta a rivoluzionare l’accesso alle informazioni giuridiche. 🚀 Contribuisci su [GitHub](https://chatgpt.com/g/g-iKdbNE3wQ-readme/c/67d89b51-6b24-800b-bac9-6770078f6522#) o unisciti alla community per supportare lo sviluppo!
