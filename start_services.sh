#!/bin/bash

# Script per avviare l'applicazione NER e ngrok in background
# Creato il: 09/04/2025

echo "Avvio dell'applicazione NER in background..."
source .venv/bin/activate
# Assicurati di avere il virtualenv attivo
echo "Attivazione del virtualenv..."

nohup python /home/ec2-user/MERL-T/src/data_lab/ner-giuridico/ner_giuridico/main.py annotate > output.log 2>&1 &
APP_PID=$!
echo "Applicazione NER avviata con PID: $APP_PID"

# Attendi un momento per assicurarti che l'app sia pronta
sleep 10

echo "Avvio di ngrok in background..."
nohup ./ngrok http --url=formally-just-bull.ngrok-free.app 8080 > outputngrok.log 2>&1 &
NGROK_PID=$!
echo "Ngrok avviato con PID: $NGROK_PID"

echo "Entrambi i servizi sono ora in esecuzione in background."
echo "Puoi controllare i log con:"
echo "  - tail -f output.log (per l'app NER)"
echo "  - tail -f outputngrok.log (per ngrok)"

# Salva i PID in un file per poterli terminare in seguito se necessario
echo "$APP_PID $NGROK_PID" > running_pids.txt

echo "I PID sono stati salvati in running_pids.txt"