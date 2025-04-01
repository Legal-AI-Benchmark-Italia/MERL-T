### A. Tipologie di Nodi

1. **Norma**
   * **Descrizione:** Rappresenta atti normativi specifici (es. Articoli di codici, leggi, decreti).
   * **Proprietà:**
     * `node_id`: Identificativo univoco
     * `nome`: Es. "Art. 1414 c.c."
     * `descrizione`: Breve descrizione del contenuto
     * `fonte`: Origine (es. "Codice Civile", "Gazzetta Ufficiale")
     * `data_pubblicazione` (opzionale)
2. **Concetto Giuridico**
   * **Descrizione:** Rappresenta idee astratte o principi (es. "Simulazione", "Buona fede").
   * **Proprietà:**
     * `node_id`
     * `nome`
     * `definizione` (opzionale)
3. **Soggetto Giuridico**
   * **Descrizione:** Entità cui si applica il diritto (es. "Persona fisica", "Società", "Ente Pubblico").
   * **Proprietà:**
     * `node_id`
     * `nome`
     * `tipo` (es. "Persona fisica", "Persona giuridica")
4. **Atto Giudiziario / Provvedimento**
   * **Descrizione:** Decisioni giurisprudenziali o atti amministrativi (es. "Sentenza Cassazione n.1234/2023").
   * **Proprietà:**
     * `node_id`
     * `nome`
     * `descrizione`
     * `organo_emittente`
5. **Fonte del Diritto**
   * **Descrizione:** Categoria che classifica la provenienza normativa (es. "Legge", "Regolamento", "Costituzione").
   * **Proprietà:**
     * `node_id`
     * `nome`
6. **Dottrina / Commentario**
   * **Descrizione:** Testi e opinioni dottrinali che interpretano o commentano norme giuridiche.
   * **Proprietà:**
     * `node_id`
     * `titolo`
     * `autore`
     * `descrizione` (riassunto dei concetti chiave)
7. **Procedura / Processo**
   * **Descrizione:** Sequenze di atti regolati dalla norma (es. "Processo Civile ordinario").
   * **Proprietà:**
     * `node_id`
     * `nome`
     * `descrizione`

---

### B. Tipologie di Relazioni

1. **disciplina**
   * **Definizione:** Collega una Norma a un Concetto, indicando che la norma disciplina quel concetto.
   * **Esempio:** "Art. 1414 c.c." → disciplina → "Simulazione".
2. **applica_a**
   * **Definizione:** Collega una Norma a un Soggetto Giuridico, indicando a chi la norma si applica.
   * **Esempio:** "Art. 3 Costituzione" → applica_a → "Tutti i cittadini".
3. **interpreta**
   * **Definizione:** Collega un Atto Giudiziario a una Norma, indicandone l’interpretazione.
   * **Esempio:** "Sentenza Cass. 1234/2023" → interpreta → "Art. 1414 c.c.".
4. **commenta**
   * **Definizione:** Collega un Dottrina/Commentario a una Norma, per indicare che un testo dottrinale commenta quella norma.
   * **Esempio:** "Commentario al Codice Civile di Tizio" → commenta → "Art. 1414 c.c.".
5. **cita**
   * **Definizione:** Collega tra loro norme, atti o testi dottrinali, quando uno cita l’altro.
   * **Esempio:** "Art. 1414 c.c." → cita → "Art. 1373 c.c.".
6. **deroga_a / modifica**
   * **Definizione:** Indica relazioni di modifica, integrazione o abrogazione tra norme.
   * **Esempio:** "Legge n. X" → abroga → "Art. 1414 c.c. (testo precedente)".
7. **relazione concettuale**
   * **Definizione:** Per relazioni gerarchiche o implicative tra Concetti.
   * **Esempio:** "Simulazione relativa" → è_un_tipo_di → "Simulazione".
8. **emesso_da**
   * **Definizione:** Collega un Atto Giudiziario o Atto Amministrativo all’Organo che lo ha emesso.
   * **Esempio:** "Sentenza n.1234/2023" → emesso_da → "Corte di Cassazione".
9. **fonte**
   * **Definizione:** Collega una Norma a una Fonte del Diritto.
   * **Esempio:** "Art. 1414 c.c." → fonte → "Codice Civile".


---



* **Nodi di tipo Norma** sono collegati ai **Concetti** tramite la relazione "disciplina".
* I **Nodi di Dottrina** si collegano alle norme con "commenta".
* I **Soggetti Giuridici** sono collegati alle norme con "applica_a".
* Gli **Atti Giudiziari** sono collegati alle norme con "interpreta" e agli **Organi** (che possono essere ulteriori nodi, ad es. "Corte di Cassazione") tramite "emesso_da".
* Le **Fonti del Diritto** collegano le norme per indicare la loro origine, mentre i **Concetti** possono avere relazioni gerarchiche tra loro (es. "è_un_tipo_di").
