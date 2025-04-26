#!/bin/bash
# Script per fermare i servizi
# Salva come stop_services.sh

if [ -f running_pid.txt ]; then
    read APP_PID NGROK_PID < running_pid.txt
    echo "Arresto dell'applicazione NER (PID: $APP_PID)..."
    kill $APP_PID
    echo "Arresto di ngrok (PID: $NGROK_PID)..."
    kill $NGROK_PID
    rm running_pid.txt
    echo "Servizi arrestati."
else
    echo "File running_pid.txt non trovato. I servizi potrebbero non essere in esecuzione."
fi