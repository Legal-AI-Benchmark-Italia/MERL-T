
## Pipeline Algoritmo MERL-T

Questa pipeline descrive il flusso di elaborazione di una query utente all'interno del framework MERL-T, dalla ricezione dell'input alla generazione della risposta finale, integrando componenti di routing e sintesi addestrabili secondo il paradigma Mixture of Agents / RLCF.

Input:query_utente (Stringa): testo della domanda posta dall'utente in lingua italiana.

Output:risposta_finale (Stringa): risposta giuridica elaborata, formattata e contenente riferimenti tracciati a fonti normative, dottrinali o giurisprudenziali.

1. Pre-processing e Named Entity Recognition (NER)

* 1.1. Normalizzazione testo:

  * La query_utente viene normalizzata: conversione a lowercase, rimozione caratteri speciali, standardizzazione abbreviazioni e riferimenti canonici.
* 1.2. Named Entity Recognition (NER) giuridico:
* Un modello NER specializzato analizza la query normalizzata estraendo: ENTITA_CONCETTO, ENTITA_NORMA, ENTITA_SENTENZA con i relativi identificatori strutturati.
* Output della fase:query_normalizzata (Stringa), lista_entita_estratte (Lista di tuple).

2. Routing della query (Router MoE Addestrabile)

* 2.1. Analisi input: Il Router MoE Addestrabile (un modello "gating" dedicato) riceve query_normalizzata e lista_entita_estratte.
* 2.2. Logica di instradamento appresa:

  * Il modello Router, addestrato tramite Reinforcement Learning from Community Feedback (RLCF) su dati validati da esperti giuridici, predice l'execution plan più appropriato.
  * Il modello valuta le caratteristiche della query e delle entità per determinare se attivare Modulo Principi, Modulo Regole o una loro combinazione. I pesi di questo modello rappresentano parte del patrimonio intellettuale collettivo di LAIBIT.
* 2.3. Definizione execution plan: Il Router MoE seleziona uno dei piani possibili:
* Piano A: solo Modulo Principi.
* Piano B: solo Modulo Regole.
* Piano C: combinazione Modulo Principi + Modulo Regole.
* Output della fase:execution_plan (Oggetto che definisce moduli e sequenza).

3. Context Augmentation (Recupero Informazioni)

Questa fase avviene in parallelo o sequenza in base all'execution_plan. Si ispira a tecniche GraphRAG (cfr. Guo et al., "LightRAG", arXiv:2410.05779).

* 3.1. Recupero da database vettoriale (se execution_plan include Modulo Regole):

  * Calcolo embedding query e ricerca ANN su DB Vettoriale (Milvus/FAISS).
  * Contenuto DB Vettoriale: Componente personalizzabile/estensibile contenente di base: Codici principali italiani (con commenti open-source), manuali universitari per materie fondamentali, massime giurisprudenziali delle corti interne (Cassazione, CdS, CdC, TAR rilevanti).
    * Materie fondamentali: [Lista materie come versione precedente]
    * Codici principali (URN Normattiva): [Lista URN come versione precedente]
  * Recupero top_K documenti (documenti_vettoriali).
* 3.2. Recupero da Knowledge Graph (se execution_plan richiede contesto concettuale per Modulo Principi o Regole):
* Utilizzo di ENTITA_CONCETTO per interrogare il Knowledge Graph (Neo4j).
* KG come core asset: Questo grafo rappresenta il patrimonio pubblico centrale, strutturato secondo lo schema definito (Nodi: Norma, Concetto, Soggetto, etc.; Relazioni: disciplina, interpreta, etc.) ed evolve dinamicamente grazie al processo RLCF e al contributo della community LAIBIT. La sua manutenzione e il suo arricchimento sono un'attività chiave della community.
* Recupero informazioni strutturate (triplette_kg).
* 3.3. Recupero dinamico via API (se execution_plan include Modulo Regole e NER ha estratto ENTITA_NORMA o ENTITA_SENTENZA interna):
* Chiamata a VisuaLexAPI (norme) e API Sentenze (corti interne).
* Recupero testi specifici aggiornati (testi_api).
* Output della fase:contesto_recuperato (Oggetto contenente documenti_vettoriali, triplette_kg, testi_api).

4. Costruzione dei prompt per LLM

* 4.1. Assemblaggio prompt: Costruzione dei prompt specifici.

  * Prompt Principi: Include query_normalizzata, istruzioni, e triplette_kg rilevanti.
* Sei MERL-T Principi... Domanda: {query_normalizzata}
* --- CONTESTO DAL KNOWLEDGE GRAPH ---
* {triplette_kg relevantes}
* --- FINE CONTESTO KG ---
* Fornisci una spiegazione completa...
* 
* Prompt Regole: Include query_normalizzata, istruzioni, e contesto_recuperato completo, differenziando le fonti.
* Sei MERL-T Regole... Domanda: {query_normalizzata}
* --- CONTESTO RECUPERATO ---
* [Fonte: API Normattiva - Art. X] {testo_api_norma}
* [Fonte: API Sentenze - Cass. Y] {testo_api_sentenza}
* [Fonte: DB Vettoriale - Manuale Z] {documento_vettoriale}
* [Fonte: KG] {triplette_kg}
* --- FINE CONTESTO ---
* Rispondi basandoti ESCLUSIVAMENTE sul contesto...
* 
* Output della fase:prompt_principi (Stringa), prompt_regole (Stringa).

5. Inferenza LLM (Moduli Esperti)

* 5.1. Esecuzione Modulo Principi (se richiesto da execution_plan):

  * Inferenza su Modulo Principi LLM (Componente sostituibile/aggiornabile - API/Locale+LoRA).
  * Corpus fine-tuning: Manuali (materie 3.1), decisioni/ragionamenti Corti Superiori/Principi (Corte Costituzionale, CGUE, CEDU, etc.) o commentari su di esse.
  * Generazione risposta_principi.
* 5.2. Esecuzione Modulo Regole (se richiesto da execution_plan):
* Inferenza su Modulo Regole LLM (Componente sostituibile/aggiornabile, ottimizzato per RAG).
* Generazione risposta_regole.
* Output della fase:risposta_principi (Stringa, opzionale), risposta_regole (Stringa, opzionale).

6. Sintesi e combinazione risposte (Sintetizzatore MoE Addestrabile)

* 6.1. Integrazione risultati: Il Sintetizzatore MoE Addestrabile riceve risposta_principi, risposta_regole, query_normalizzata.
* 6.2. Logica di sintesi appresa:
  * Se execution_plan era A o B, la risposta corrispondente viene selezionata.
  * Se execution_plan era C, il modello Sintetizzatore, addestrato tramite RLCF su validazioni esperte, sceglie ed applica la migliore strategia di combinazione. I pesi di questo modello sono anch'essi parte del patrimonio intellettuale collettivo LAIBIT.
  * Generazione risposta_finale_provvisoria.
* Output della fase:risposta_finale_provvisoria (Stringa).

7. Post-processing e output finale

* 7.1. Formattazione: Formattazione della risposta_finale_provvisoria.
* 7.2. Tracking e citazione fonti:
  * Verifica presenza e chiarezza citazioni.
  * Cruciale: Mantenimento metadati di provenienza per ogni frammento generato (dal KG, DB Vettoriale, API, Modulo Principi), fondamentale per trasparenza, validazione RLCF e modelli EaaS/attribuzione.
* 7.3. Filtri di sicurezza/qualità: Applicazione filtri finali.
* 7.4. Generazione output: Produzione della risposta_finale.
* Output della fase:risposta_finale (Stringa).
