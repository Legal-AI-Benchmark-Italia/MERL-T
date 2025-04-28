"""
Esempio di utilizzo del sistema NER per testi giuridici.
"""

import logging
from pathlib import Path
import json

from .ner_system import NERSystem
from .config import load_config

# Configura il logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("NER-Giuridico.Example")

def process_example():
    """Dimostra l'uso del sistema NER su un testo di esempio."""
    
    # Inizializza il sistema NER
    ner = NERSystem()
    
    logger.info("Sistema NER inizializzato")
    
    # Testo di esempio
    text = """
    L'articolo 1414 c.c. disciplina la simulazione nei contratti.
    
    La legge n. 241 del 1990 regola il procedimento amministrativo.
    
    Secondo la sentenza della Corte di Cassazione n. 12345/2022, il principio di buona fede 
    deve essere rispettato in tutte le fasi della contrattazione.
    
    Il Regolamento UE 2016/679 (GDPR) tutela i dati personali dei cittadini europei.
    """
    
    # Processa il testo
    logger.info("Elaborazione del testo di esempio")
    result = ner.process(text)
    
    # Mostra le entità riconosciute
    logger.info(f"Entità riconosciute: {len(result['entities'])}")
    for i, entity in enumerate(result['entities']):
        logger.info(f"Entità {i+1}:")
        logger.info(f"  Testo: {entity['text']}")
        logger.info(f"  Tipo: {entity['type_id']}")
        logger.info(f"  Posizione: {entity['start_char']}-{entity['end_char']}")
        logger.info(f"  Testo normalizzato: {entity['normalized_text']}")
        if entity['metadata']:
            logger.info(f"  Metadati: {entity['metadata']}")
    
    # Mostra i riferimenti strutturati
    if 'structured_references' in result:
        logger.info("Riferimenti strutturati:")
        for ref_type, refs in result['structured_references'].items():
            logger.info(f"  {ref_type}: {len(refs)} riferimenti")
            for ref in refs:
                logger.info(f"    - {ref}")
    
    # Salva il risultato in un file JSON
    output_file = Path("output") / "example_result.json"
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Risultato salvato in {output_file}")
    
    return result

def train_example():
    """Dimostra come addestrare il modello NER con dati annotati."""
    
    # Inizializza il sistema NER
    ner = NERSystem()
    
    # Dati di addestramento di esempio
    training_data = [
        {
            "text": "L'articolo 1414 c.c. disciplina la simulazione nei contratti.",
            "entities": [
                [0, 19, "ARTICOLO_CODICE"]
            ]
        },
        {
            "text": "La legge n. 241 del 1990 regola il procedimento amministrativo.",
            "entities": [
                [3, 22, "LEGGE"]
            ]
        },
        {
            "text": "Secondo la sentenza della Corte di Cassazione n. 12345/2022, il principio di buona fede.",
            "entities": [
                [8, 53, "SENTENZA"],
                [73, 84, "CONCETTO_GIURIDICO"]
            ]
        }
    ]
    
    # Salva i dati di addestramento in un file JSON
    training_file = Path("output") / "training_data.json"
    training_file.parent.mkdir(exist_ok=True)
    
    with open(training_file, 'w', encoding='utf-8') as f:
        json.dump(training_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Dati di addestramento salvati in {training_file}")
    
    # Per addestrare il modello, è necessario che i dati siano più numerosi
    # Questo è solo un esempio dimostrativo
    logger.info("Per un addestramento reale, utilizzare più dati annotati")
    
    # Esempio di addestramento (commentato)
    """
    # Output directory per il modello addestrato
    model_dir = Path("models") / "transformer" / "example_model"
    model_dir.parent.mkdir(parents=True, exist_ok=True)
    
    # Addestra il modello
    ner.train(training_data, output_dir=str(model_dir))
    
    # Carica il modello addestrato
    ner.load_model(str(model_dir))
    """
    
    return training_data

if __name__ == "__main__":
    # Processo un testo di esempio
    process_example()
    
    # Mostra come addestrare il modello
    train_example() 