# Individuazione dei punti con definizioni hardcoded di entità e categorie

Ho analizzato il codice e ho identificato i principali punti dove sono definite le entità e le categorie predefinite. Ecco dove puoi intervenire:

## 1. Principali definizioni di entità predefinite

### In `entity_manager.py` - Metodo `_load_default_entities`

Questo è il punto principale dove vengono create le entità predefinite:

## 2. Definizione delle categorie predefinite

### In `entity_manager.py` - Costruttore `__init__` della classe `DynamicEntityManager`

Qui vengono definite le categorie disponibili:

## 3. Definizione degli EntityType statici

### In `entities.py` - Classe `EntityType`

Questa è l'enumerazione originale che definisce i tipi di entità nel sistema non dinamico:

## 4. Controlli che proteggono le entità predefinite

### In `entity_manager.py` - Metodo `update_entity_type`

Qui ci sono controlli che impediscono la modifica delle entità predefinite:

## 5. Controlli in app.py per la protezione delle entità

## 6. Validazione delle categorie in app.py

## 7. Controlli nell'interfaccia utente (entity_manager.js)

# Come modificare le entità e le categorie predefinite

Per modificare le entità e le categorie predefinite, ecco come dovresti procedere:

## 1. Aggiungere una nuova categoria

1. **Modifica la struttura `entity_categories` in `entity_manager.py`** :

* Aggiungi la nuova categoria al dizionario `self.entity_categories` nel costruttore `__init__`
* Esempio per aggiungere una categoria "procedural":

```python
   self.entity_categories = {
       "normative": set(),
       "jurisprudence": set(),
       "concepts": set(),
       "custom": set(),
       "procedural": set()  # Nuova categoria
   }
```

1. **Aggiorna la funzione di validazione `validate_entity_category` in `app.py`** :

```python
   def validate_entity_category(category: str) -> None:
       valid_categories = ['normative', 'jurisprudence', 'concepts', 'custom', 'procedural']  # Aggiunta nuova categoria
       # Resto della funzione...
```

1. **Aggiorna il menu a discesa in `entity_types.html`** :

```html
   <select id="category" required>
       <option value="custom">Personalizzata</option>
       <option value="normative">Normativa</option>
       <option value="jurisprudence">Giurisprudenziale</option>
       <option value="concepts">Concetto</option>
       <option value="procedural">Procedurale</option>  <!-- Nuova categoria -->
   </select>
```

1. **Aggiungi un colore per la nuova categoria in `entity_manager.js`** :

```javascript
   #category option[value="procedural"] {
       background-color: #e1f5fe;
   }
```

## 2. Aggiungere o modificare entità predefinite

1. **Modifica il metodo `_load_default_entities` in `entity_manager.py`** :
   Per aggiungere una nuova entità:

```python
   # Aggiungi una nuova entità procedurale
   self.add_entity_type(
       name="RICORSO",
       display_name="Ricorso",
       category="procedural",  # Usa la nuova categoria
       color="#81D4FA",
       metadata_schema={"tipo": "string", "foro": "string", "data": "string"}
   )
```

   Per modificare un'entità esistente:

```python
   # Modifica un'entità esistente (CONCETTO_GIURIDICO)
   self.add_entity_type(
       name="CONCETTO_GIURIDICO",
       display_name="Principio Giuridico",  # Nome modificato
       category="concepts",
       color="#26A69A",  # Colore modificato
       metadata_schema={"categoria": "string", "definizione": "string", "fonte": "string"}  # Schema modificato
   )
```

1. **Aggiorna l'enumerazione `EntityType` in `entities.py` (per compatibilità con il sistema non dinamico)** :

```python
   # Riferimenti processuali (nuova sezione)
   RICORSO = auto()  # Nuova entità
```

1. **Aggiorna i metodi di classificazione in `entities.py`** :

```python
   @classmethod
   def get_procedural_types(cls) -> Set["EntityType"]:
       """Restituisce l'insieme dei tipi di entità processuali."""
       return {
           cls.RICORSO
       }
```

## 3. Rimuovere la protezione per consentire la modifica delle entità predefinite

Se vuoi consentire la modifica delle entità predefinite (scelta rischiosa), puoi modificare i controlli di protezione:

1. **In `entity_manager.py` - Nel metodo `update_entity_type`** :

```python
   # Commenta o rimuovi questo controllo per consentire la modifica della categoria
   # if original_category != "custom" and original_category in ["normative", "jurisprudence", "concepts"]:
   #     self.logger.error(f"Non è possibile cambiare la categoria di un'entità predefinita: {name}")
   #     return False
```

1. **In `app.py` - Nel metodo `update_entity_type`** :

```python
   # Commenta o rimuovi questo controllo
   # if category and current_entity.get('category') != 'custom' and category != current_entity.get('category'):
   #     return jsonify({
   #         "status": "error", 
   #         "message": f"Non è possibile modificare la categoria di un'entità predefinita: {name}",
   #         "error_type": "ProtectedEntityError"
   #     }), 403
```

1. **In `app.py` - Nel metodo `delete_entity_type`** :

```python
   # Commenta o rimuovi questo controllo per consentire l'eliminazione
   # if entity_type.get("category") != "custom":
   #     logger.warning(f"Tentativo di eliminare l'entità predefinita: {name}")
   #     return jsonify({
   #         "status": "error", 
   #         "message": f"Non è possibile eliminare il tipo di entità predefinito '{name}'",
   #         "error_type": "ProtectedEntityError"
   #     }), 403
```

## 4. Modificare i colori predefiniti

I colori delle entità predefinite sono definiti nel metodo `_load_default_entities`. Puoi modificarli in base alle tue preferenze utilizzando codici esadecimali:

```python
self.add_entity_type(
    name="ARTICOLO_CODICE",
    display_name="Articolo di Codice",
    category="normative",
    color="#FF5722",  # Colore modificato
    metadata_schema={"codice": "string", "articolo": "string"}
)
```

## Note importanti

1. **Dopo le modifiche** , è consigliabile ricreare il database delle entità per assicurarsi che le modifiche vengano applicate correttamente. Puoi farlo eliminando il file `entities.db` nella directory `data` e riavviando l'applicazione.
2. **Backup** : Prima di apportare modifiche alle entità predefinite, crea un backup del database e dei file di configurazione.
3. **Compatibilità** : Assicurati che le modifiche siano coerenti in tutti i punti del codice per evitare comportamenti incoerenti.
4. **Annotazioni esistenti** : Modificare o eliminare entità predefinite potrebbe influire sulle annotazioni esistenti che utilizzano quei tipi di entità.

Seguendo queste linee guida, puoi personalizzare le entità e le categorie predefinite nel sistema NER-Giuridico secondo le tue esigenze.
