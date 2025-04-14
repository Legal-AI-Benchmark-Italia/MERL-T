import asyncio
import logging
import os
from tools.norma_scraper import NormaScraper 

# Configurazione del logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    # Assicurati che esista la directory "data"
    os.makedirs("data", exist_ok=True)
    
    # Inizializzazione dello scraper
    # Modifica l'URL del server se necessario
    scraper = NormaScraper(base_url="http://127.0.0.1:5000/fetch_all_data")
    
    # Configurazione dei parametri per la richiesta
    # Modifica questi valori in base alle tue necessità
    act_type = "Codice Penale"            # Tipo di atto normativo
    date = ""                   # Data dell'atto
    act_number = ""                    # Numero dell'atto
    version = "vigente"                   # Versione dell'atto
    version_date = ""           # Data della versione
    show_brocardi_info = True             # Mostra informazioni aggiuntive
    
    # OPZIONE 1: Specificare articoli singoli come lista
    articles = ["635-quater.1", "615-quater", "635-bis", "617-quater", "615-ter", "640-te", "621", "257"]
    
    # OPZIONE 2: Specificare un intervallo di articoli come tupla
    # articles = (1, 10)  # Recupera gli articoli da 1 a 10
    
    try:
        # Recupero e salvataggio degli articoli
        await scraper.fetch_and_save_articles(
            act_type=act_type,
            date=date,
            act_number=act_number,
            version=version,
            version_date=version_date,
            show_brocardi_info=show_brocardi_info,
            articles=articles,
            atomize=False,  # False = salva in un unico file, True = un file per articolo
            save=True,
            file_name="articoli_cybersecurity.txt"
        )
        
        logging.info("Articoli recuperati e salvati con successo!")
        
    except Exception as e:
        logging.error(f"Si è verificato un errore: {e}")

if __name__ == "__main__":
    asyncio.run(main())