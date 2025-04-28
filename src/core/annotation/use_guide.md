# Guida all'Interfaccia di Annotazione NER-Giuridico

## Introduzione

L'interfaccia di annotazione di NER-Giuridico è uno strumento web che consente di annotare documenti testuali con entità giuridiche rilevanti. Queste annotazioni possono essere utilizzate per addestrare e migliorare il sistema di riconoscimento automatico delle entità (NER).

## Installazione e Avvio

### Prerequisiti

* Python 3.8 o superiore
* Flask 2.3.x o superiore
* Dipendenze del sistema NER-Giuridico

### Avvio dell'interfaccia

```bash
# Dalla directory principale del progetto
python -m ner.scripts.run_annotation

# Oppure
python main.py annotate
```

Per impostazione predefinita, l'interfaccia sarà disponibile all'indirizzo `http://localhost:8080`.

## Panoramica delle Funzionalità

L'interfaccia di annotazione offre le seguenti funzionalità:

1. **Gestione dei documenti**
   * Caricamento di documenti testuali
   * Navigazione tra i documenti esistenti
   * Visualizzazione del contenuto dei documenti
2. **Creazione di annotazioni**
   * Selezione del testo da annotare
   * Assegnazione di un tipo di entità alla selezione
   * Visualizzazione delle annotazioni create
3. **Gestione delle annotazioni**
   * Visualizzazione delle annotazioni esistenti
   * Modifica delle annotazioni
   * Eliminazione delle annotazioni
4. **Riconoscimento automatico**
   * Utilizzo del sistema NER per riconoscere automaticamente le entità
   * Revisione e modifica delle entità riconosciute
5. **Esportazione delle annotazioni**
   * Esportazione in formato JSON
   * Esportazione in formato spaCy
   * Utilizzo per l'addestramento di modelli

## Guida all'Uso

### Pagina Principale

La pagina principale mostra un elenco dei documenti disponibili. Da qui è possibile:

* **Caricare un nuovo documento** : Utilizzare il modulo di upload nella parte superiore della pagina.
* **Visualizzare e annotare un documento esistente** : Fare clic sul pulsante "Annota" accanto al documento.
* **Esportare le annotazioni** : Utilizzare i pulsanti di esportazione nella parte inferiore della pagina.

### Pagina di Annotazione

La pagina di annotazione è l'interfaccia principale per creare e gestire le annotazioni. È composta da tre sezioni:

1. **Tipi di entità** (colonna di sinistra)
   * Elenco dei tipi di entità disponibili
   * Fare clic su un tipo per selezionarlo
2. **Testo del documento** (colonna centrale)
   * Visualizzazione del testo completo del documento
   * Entità annotate evidenziate con il colore corrispondente
   * Per annotare:
     1. Selezionare un tipo di entità dalla colonna di sinistra
     2. Selezionare il testo nel documento
     3. L'annotazione verrà creata automaticamente
3. **Elenco delle annotazioni** (colonna di destra)
   * Visualizzazione di tutte le annotazioni create
   * Possibilità di eliminare annotazioni esistenti
   * Fare clic su un'annotazione per evidenziarla nel testo

### Riconoscimento Automatico

Per utilizzare il riconoscimento automatico delle entità:

1. Aprire un documento nella pagina di annotazione
2. Fare clic sul pulsante "Riconoscimento automatico"
3. Il sistema NER analizzerà il testo e proporrà le entità riconosciute
4. Rivedere le entità, modificarle o eliminarle se necessario

### Esportazione delle Annotazioni

Per esportare le annotazioni:

1. Dalla pagina principale, fare clic su uno dei pulsanti di esportazione:
   * "Esporta in JSON": Formato nativo dell'interfaccia
   * "Esporta in formato spaCy": Formato compatibile con spaCy per l'addestramento
2. Le annotazioni verranno scaricate o visualizzate nel formato selezionato

## Tipi di Entità

L'interfaccia supporta i seguenti tipi di entità preconfigurati:

* **ARTICOLO_CODICE** : Riferimenti a articoli di codici (es. "art. 1414 c.c.")
* **LEGGE** : Riferimenti a leggi (es. "legge 241/1990")
* **DECRETO** : Riferimenti a decreti (es. "d.lgs. 50/2016")
* **REGOLAMENTO_UE** : Riferimenti a regolamenti UE (es. "Regolamento UE 2016/679")
* **SENTENZA** : Riferimenti a sentenze (es. "Cass. civ. 123/2020")
* **ORDINANZA** : Riferimenti a ordinanze (es. "ordinanza Trib. Milano 45/2019")
* **CONCETTO_GIURIDICO** : Concetti giuridici generali (es. "simulazione", "contratto")

Il sistema supporta anche l'aggiunta di tipi di entità personalizzati tramite l'Entity Manager.

## Integrazione con il Sistema NER

L'interfaccia di annotazione è strettamente integrata con il sistema NER-Giuridico:

1. **Riconoscimento automatico** : Utilizza il sistema NER per proporre automaticamente le entità.
2. **Addestramento** : Le annotazioni create possono essere utilizzate per addestrare o migliorare il sistema NER.
3. **Tipi di entità** : I tipi di entità sono sincronizzati con l'Entity Manager del sistema.

## Risoluzione dei Problemi

### L'interfaccia non si avvia

Verifica che:

* Flask sia installato correttamente
* Le dipendenze del sistema NER-Giuridico siano installate
* La porta 8080 non sia già in uso

### Il riconoscimento automatico non funziona

Verifica che:

* Il sistema NER sia installato correttamente
* I modelli necessari siano disponibili
* La connessione tra l'interfaccia e il sistema NER funzioni correttamente

### Le annotazioni non vengono salvate

Verifica che:

* La directory dei dati sia scrivibile
* I file JSON non siano corrotti
* Non ci siano errori nei log dell'applicazione

## Estensione e Personalizzazione

L'interfaccia di annotazione può essere estesa e personalizzata in vari modi:

1. **Aggiunta di nuovi tipi di entità** : Utilizzare l'Entity Manager per configurare nuovi tipi di entità.
2. **Personalizzazione dell'interfaccia** : Modificare i template HTML e i file CSS.
3. **Aggiunta di funzionalità** : Estendere il codice JavaScript per aggiungere nuove funzionalità.
4. **Integrazione con altri sistemi** : Modificare il backend Flask per integrare con altri sistemi.

## Risorse Aggiuntive

* [Documentazione del sistema NER-Giuridico](https://claude.ai/chat/README.md)
* [Guida all&#39;Entity Manager](https://claude.ai/chat/entity_manager.md)
* [Guida all&#39;addestramento del sistema NER](https://claude.ai/chat/training.md)
