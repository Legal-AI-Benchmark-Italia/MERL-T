# Guida alla gestione delle entità nel sistema NER-Giuridico

Questa guida descrive come gestire le entità nel sistema NER-Giuridico, in particolare come aggiungere, modificare o eliminare categorie ed entità predefinite.

## 1. Struttura del sistema di gestione entità

Il sistema utilizza un `EntityManager` per gestire tutte le entità e le loro categorie. Le entità sono rappresentate dalla classe `EntityType` e vengono salvate in un database SQLite.

### Principali componenti:

1. **`EntityType`** - Classe che rappresenta un tipo di entità, con attributi come:
   - id: Identificatore univoco
   - name: Nome identificativo (es. "LEGGE")
   - display_name: Nome visualizzato (es. "Legge")
   - category: Categoria (es. "law")
   - color: Colore in formato esadecimale
   - description: Descrizione opzionale
   - metadata_schema: Schema dei metadati associati
   - patterns: Pattern regex per il riconoscimento
   - system: Flag che indica se è un'entità di sistema

2. **`EntityManager`** - Classe che gestisce le entità con persistenza su database.

3. **Categorie predefinite** - Il sistema definisce quattro categorie base:
   - law: Entità normative
   - jurisprudence: Entità giurisprudenziali
   - doctrine: Concetti giuridici
   - custom: Entità personalizzate

## 2. Dove sono definite le entità e le categorie

### Definizione delle categorie

Le categorie sono definite nel costruttore `__init__` della classe `EntityManager`:

```python
def __init__(self, db_path: Optional[str] = None):
    # ... altro codice ...
    self.categories: Dict[str, Set[str]] = {
        "law": set(),
        "jurisprudence": set(),
        "doctrine": set(),
        "custom": set()
    }
    # ... altro codice ...
```

### Definizione dell'entità predefinita "Legge"

L'entità predefinita "Legge" viene creata nel metodo `_add_default_legge_entity`:

```python
def _add_default_legge_entity(self):
    """Aggiunge l'entità predefinita 'Legge'."""
    legge = EntityType(
        id=str(uuid.uuid4()),
        name="LEGGE",
        display_name="Legge",
        category="law",
        color="#D4380D",
        description="Atto normativo approvato dal Parlamento",
        metadata_schema={
            "numero": "string", 
            "anno": "string", 
            "data": "string"
        },
        patterns=[
            r"legge\s+(?:n\.\s*)?(\d+)(?:/(\d{4}))?",
            r"l\.\s*(?:n\.\s*)?(\d+)(?:/(\d{4}))?"
        ],
        system=True
    )
    self.add_entity(legge)
```

### Protezione delle entità di sistema

Le entità di sistema (con `system=True`) sono protette dall'eliminazione nel metodo `remove_entity`:

```python
def remove_entity(self, entity_id: str) -> bool:
    # ... altro codice ...
    entity = self.entities[entity_id]
    
    # Non permettere la rimozione di entità di sistema
    if entity.system:
        self.logger.warning(f"Impossibile rimuovere l'entità di sistema '{entity.name}'")
        return False
    # ... altro codice ...
```

## 3. Come modificare il sistema di entità

### Aggiungere una nuova categoria

1. **Modifica il dizionario `categories` in `EntityManager.__init__`**:

```python
self.categories: Dict[str, Set[str]] = {
    "law": set(),
    "jurisprudence": set(),
    "doctrine": set(),
    "custom": set(),
    "procedural": set()  # Nuova categoria
}
```

2. **Usa il metodo `add_category` per aggiungere categorie a runtime**:

```python
entity_manager = get_entity_manager()
entity_manager.add_category("procedural")
```

3. **Aggiorna la validazione in `app.py` se presente**:

```python
def validate_entity_category(category: str) -> None:
    valid_categories = ['law', 'jurisprudence', 'doctrine', 'custom', 'procedural']
    # Resto della funzione...
```

4. **Aggiorna l'interfaccia utente** se applicabile:

```html
<select id="category" required>
    <option value="custom">Personalizzata</option>
    <option value="law">Normativa</option>
    <option value="jurisprudence">Giurisprudenziale</option>
    <option value="doctrine">Concetto</option>
    <option value="procedural">Procedurale</option>  <!-- Nuova categoria -->
</select>
```

### Aggiungere nuove entità predefinite

Per aggiungere una nuova entità di sistema:

```python
entity_manager = get_entity_manager()

ricorso = EntityType(
    id=str(uuid.uuid4()),
    name="RICORSO",
    display_name="Ricorso",
    category="procedural",  # Categoria nuova o esistente
    color="#81D4FA",
    description="Atto con cui si avvia un procedimento giudiziario",
    metadata_schema={
        "tipo": "string", 
        "foro": "string", 
        "data": "string"
    },
    patterns=[
        r"ricorso\s+(?:al|alla)\s+(\w+)",
        r"ricorso\s+(?:ex|ai\s+sensi)\s+dell[a']?\s+art(?:icolo|\.)\s*(\d+)"
    ],
    system=True  # Imposta come entità di sistema
)

entity_manager.add_entity(ricorso)
```

### Modificare un'entità esistente

Per modificare un'entità esistente:

```python
entity_manager = get_entity_manager()

# Ottieni l'entità esistente
entity = entity_manager.get_entity_by_name("LEGGE")

if entity:
    # Modifica i campi necessari
    entity.display_name = "Norma di Legge"
    entity.color = "#FF5722"
    entity.metadata_schema["tipologia"] = "string"  # Aggiungi nuovo campo allo schema
    
    # Aggiorna l'entità
    entity_manager.update_entity(entity)
```

### Eliminare entità o disabilitare la protezione delle entità di sistema

Se è necessario eliminare o modificare le entità di sistema (non consigliato), puoi modificare il flag `system`:

```python
entity_manager = get_entity_manager()

# Ottieni l'entità
entity = entity_manager.get_entity_by_name("LEGGE")

if entity:
    # Disabilita la protezione
    entity.system = False
    entity_manager.update_entity(entity)
    
    # Ora puoi eliminarla
    entity_manager.remove_entity(entity.id)
```

## 4. Gestione del database delle entità

### Esportare entità

Per esportare tutte le entità in un file JSON:

```python
entity_manager = get_entity_manager()
entity_manager.export_entities("path/to/entities_backup.json")
```

### Importare entità

Per importare entità da un file JSON:

```python
entity_manager = get_entity_manager()
entity_manager.import_entities("path/to/entities_backup.json")
```

### Ricreare il database

Se necessario, per ricreare il database:

```python
import os
from pathlib import Path

# Percorso del database
db_path = str(Path(__file__).parent.parent / "data" / "entities.db")

# Rimuovi il database
if os.path.exists(db_path):
    os.remove(db_path)

# Ricrea il manager (ricreerà il database con le entità predefinite)
from core.entities.entity_manager import get_entity_manager
entity_manager = get_entity_manager()
```

## Note importanti

1. **Backup**: Prima di apportare modifiche alle entità predefinite, crea un backup del database e dei file di configurazione.

2. **Compatibilità**: Assicurati che le modifiche siano coerenti in tutti i punti del codice per evitare comportamenti incoerenti.

3. **Annotazioni esistenti**: Modificare o eliminare entità predefinite potrebbe influire sulle annotazioni esistenti che utilizzano quei tipi di entità.

4. **Sistema a runtime**: È preferibile utilizzare i metodi dell'`EntityManager` per modificare le entità a runtime, piuttosto che modificare direttamente il codice.

5. **Entità di sistema**: Le entità contrassegnate come `system=True` sono protette dall'eliminazione. Modifica questo flag solo se strettamente necessario.
