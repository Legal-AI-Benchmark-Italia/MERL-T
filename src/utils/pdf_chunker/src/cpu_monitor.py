#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulo per il monitoraggio dell'utilizzo della CPU.
"""

import time
import threading
import logging
import psutil
from multiprocessing import Value

class CPUMonitor:
    """
    Classe per il monitoraggio dell'utilizzo della CPU.
    """
    
    def __init__(self, cpu_limit: int = 70, check_interval: float = 2.0):
        """
        Inizializza il monitor della CPU.
        
        Args:
            cpu_limit: Limite di utilizzo CPU in percentuale
            check_interval: Intervallo di controllo in secondi
        """
        self.cpu_limit = cpu_limit
        self.check_interval = check_interval
        self.throttling = Value('i', 0)
        self.running = Value('i', 0)
        self.monitor_thread = None
        self.logger = logging.getLogger("PDFChunker.CPUMonitor")
    
    def _monitor_cpu_usage(self):
        """
        Funzione interna per monitorare l'utilizzo della CPU.
        """
        self.logger.info(f"Avvio monitoraggio CPU con limite al {self.cpu_limit}%")
        
        while self.running.value:
            try:
                # Ottieni l'utilizzo della CPU
                cpu_percent = psutil.cpu_percent(interval=0.5)
                
                # Imposta il flag di throttling
                if cpu_percent > self.cpu_limit:
                    if self.throttling.value == 0:  # Logga solo quando cambia da 0 a 1
                        self.logger.warning(f"CPU al {cpu_percent}%, superiore al limite del {self.cpu_limit}%. Attivazione throttling.")
                    self.throttling.value = 1
                else:
                    if self.throttling.value == 1:  # Logga solo quando cambia da 1 a 0
                        self.logger.info(f"CPU al {cpu_percent}%, inferiore al limite del {self.cpu_limit}%. Disattivazione throttling.")
                    self.throttling.value = 0
                    
                # Attendi l'intervallo specificato
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Errore nel monitoraggio della CPU: {str(e)}")
                time.sleep(self.check_interval * 2)  # Attendi un po' più a lungo in caso di errore
    
    def start(self):
        """
        Avvia il monitoraggio della CPU in un thread separato.
        """
        if self.monitor_thread is None or not self.monitor_thread.is_alive():
            self.running.value = 1
            self.monitor_thread = threading.Thread(target=self._monitor_cpu_usage)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
    
    def stop(self):
        """
        Ferma il monitoraggio della CPU.
        """
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.running.value = 0
            self.monitor_thread.join(timeout=3)
            if self.monitor_thread.is_alive():
                self.logger.warning("Il thread di monitoraggio CPU non si è fermato in tempo")
    
    def is_throttling_active(self) -> bool:
        """
        Controlla se il throttling è attivo.
        
        Returns:
            True se il throttling è attivo, False altrimenti
        """
        return self.throttling.value == 1
    
    def check_and_throttle(self, sleep_time: float = 1.0) -> bool:
        """
        Controlla il flag di throttling e introduce un ritardo se necessario.
        
        Args:
            sleep_time: Tempo di attesa in secondi quando il throttling è attivo
            
        Returns:
            True se è stato necessario throttling, False altrimenti
        """
        if self.throttling.value == 1:
            time.sleep(sleep_time)
            return True
        return False