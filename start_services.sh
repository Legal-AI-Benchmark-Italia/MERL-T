#!/bin/bash

# Script per avviare l'applicazione NER in background
# Aggiornato per usare il dominio diretto
# Creato il: 09/04/2025 (Data originale)
# Modificato il: 23/04/2025 (Data attuale)

echo "Avvio dell'applicazione NER in background..."

# Assicurati di essere nella directory corretta o usa percorsi assoluti
cd /home/ec2-user/MERL-T || exit 1 # Vai alla directory base dell'app, esci se fallisce

echo "Attivazione del virtualenv..."
source .venv/bin/activate
if [ $? -ne 0 ]; then
  echo "Errore: Impossibile attivare il virtualenv."
  exit 1
fi

# Verifica che il file main.py esista
# (Controllo opzionale, -m gestisce l'errore se non trovato)
# if [ ! -f "/Users/guglielmo/Desktop/CODE/MERL-T/src/core/ner_giuridico/main.py" ]; then
#   echo "Errore: File main.py non trovato nel percorso specificato."
#   exit 1
# fi

echo "Avvio di main.py come modulo..."
# Assicurati che la tua app Python ascolti su 0.0.0.0 (tutte le interfacce) e sulla porta desiderata (es. 8080)
# Potrebbe essere necessario modificare main.py per questo.
# Esempio (dipende dal framework, es. Flask): app.run(host='0.0.0.0', port=8080)
nohup python -m src.core.ner_giuridico.main annotate > /home/ec2-user/MERL-T/output.log 2>&1 &
APP_PID=$!

# Verifica se il processo è stato avviato correttamente (controllo base)
sleep 5
if kill -0 $APP_PID > /dev/null 2>&1; then
  echo "Applicazione NER avviata con PID: $APP_PID"
  echo "Controlla i log con: tail -f /home/ec2-user/MERL-T/output.log"
  # Salva il PID per poterlo terminare in seguito
  echo "$APP_PID" > /home/ec2-user/MERL-T/running_pid.txt
  echo "PID salvato in /home/ec2-user/MERL-T/running_pid.txt"
else
  echo "Errore: L'applicazione NER non è stata avviata correttamente. Controlla output.log."
  exit 1
fi

echo "Script completato."
