# Guida all'Installazione del Sistema di Login per NER-Giuridico

Questa guida fornisce istruzioni dettagliate per l'installazione e la configurazione del sistema di login aggiunto all'applicazione NER-Giuridico.

## Prerequisiti

- Python 3.8 o superiore
- Flask 2.3.x o superiore
- SQLite 3

## Passaggi di Installazione

### 1. Installazione delle Dipendenze

Assicurati di aver installato tutte le dipendenze necessarie:

```bash
pip install -r requirements.txt
```

### 2. Configurazione del Database

Il sistema utilizza SQLite come database per le annotazioni e le informazioni utente. Prima di avviare l'applicazione, è necessario inizializzare il database con un utente amministratore:

```bash
# Dalla directory principale del progetto
python init_db.py
```

Questo script creerà un utente amministratore predefinito con le seguenti credenziali:

- Username: `admin`
- Password: `admin`

Per creare un utente amministratore con credenziali personalizzate:

```bash
python init_db.py --username tuonome --password tuapassword
```

Per creare anche utenti di esempio per il testing:

```bash
python init_db.py --demo
```

### 3. Configurazione dell'Applicazione

L'applicazione utilizza una chiave segreta per la gestione delle sessioni. Per sicurezza, dovresti impostare una chiave personalizzata attraverso una variabile d'ambiente:

```bash
export FLASK_SECRET_KEY="chiave_segreta_personalizzata"
```

Se non impostata, verrà utilizzata una chiave predefinita (non sicura per ambienti di produzione).

### 4. Avvio dell'Applicazione

Dopo aver completato la configurazione, puoi avviare l'applicazione:

```bash
# Dalla directory principale del progetto
python -m ner_giuridico.scripts.run_annotation
```

L'applicazione sarà disponibile all'indirizzo `http://localhost:8080`.

## Funzionalità del Sistema di Login

### Autenticazione

Il sistema include le seguenti funzionalità di autenticazione:

- Login/Logout
- Registrazione utenti (solo per amministratori)
- Gestione profili utente
- Gestione ruoli (amministratore e annotatore)

### Tracciamento dell'Attività

Il sistema tiene traccia di:

- Login/Logout degli utenti
- Creazione e modifica di annotazioni
- Creazione e modifica di documenti
- Assegnazione di documenti agli utenti

### Dashboard e Statistiche

Le dashboard forniscono informazioni su:

- Numero totale di annotazioni
- Distribuzione delle annotazioni per tipo di entità
- Attività giornaliera
- Progressi degli annotatori

## Ruoli Utente

### Amministratore

Gli utenti con ruolo `admin` possono:

- Creare nuovi utenti
- Gestire tutti gli utenti
- Assegnare documenti agli annotatori
- Visualizzare statistiche globali

### Annotatore

Gli utenti con ruolo `annotator` possono:

- Annotare i documenti assegnati
- Visualizzare le proprie statistiche
- Modificare il proprio profilo

## Sicurezza

Il sistema implementa una sicurezza di base:

- Le password sono archiviate usando l'hash SHA-256
- Le rotte sono protette con decorator `login_required` e `admin_required`
- La sessione è configurata per durare 1 giorno

**Nota di sicurezza**: Questa implementazione è pensata per un uso interno e di collaborazione. In un ambiente di produzione, si consiglia di:

1. Utilizzare un sistema di hashing più robusto (come bcrypt)
2. Implementare HTTPS
3. Migliorare la gestione delle sessioni
4. Considerare l'utilizzo di un database più robusto per ambienti ad alto carico

## Personalizzazione

### Aggiungere Campi Utente

Se desideri aggiungere campi utente aggiuntivi:

1. Modifica la tabella `users` in `db_manager.py`
2. Aggiorna i metodi `create_user` e `update_user`
3. Aggiorna i template e i form relativi

### Integrare con un Sistema di Autenticazione Esistente

Per integrare con un sistema di autenticazione esterno:

1. Modifica la funzione `verify_user` in `db_manager.py` per connettersi al sistema esterno
2. Aggiusta il flusso di accesso in base al sistema esterno

## Risoluzione dei Problemi

### Problemi di Database

Se riscontri problemi con il database:

```bash
# Ricrea il database da zero
rm data/annotations.db
python init_db.py --demo
```

### Problemi di Login

Se non riesci ad accedere:

1. Verifica che l'utente esista nel database
2. Ripristina la password dell'utente admin:

```bash
python init_db.py --username admin --password nuovapassword
```

### Problemi di Sessione

Se la sessione scade troppo velocemente o hai altri problemi:

1. Verifica che la chiave segreta sia impostata correttamente
2. Modifica la durata della sessione in `app.py` (valore `app.permanent_session_lifetime`)

## Supporto

Per ulteriori informazioni o supporto, contatta il team di sviluppo o apri un issue sul repository.
