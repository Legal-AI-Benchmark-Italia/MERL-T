#!/usr/bin/env python3
"""
Script di test per verificare l'integrazione tra l'interfaccia di annotazione
e il sistema NER-Giuridico.
"""

import os
import sys
import json
import tempfile
import logging
import argparse
from pathlib import Path
import requests
from typing import Dict, List, Any, Optional, Tuple, Union

# Configurazione del logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_project_root():
    """Trova la directory root del progetto."""
    current_dir = Path(__file__).resolve().parent
    
    # Se siamo già nella directory src, il parent è la root
    if current_dir.name == 'src':
        return current_dir.parent
    
    # Altrimenti, cerchiamo la directory che contiene sia 'src' che 'config'
    while current_dir != current_dir.parent:
        if (current_dir / 'src').exists() and (current_dir / 'config').exists():
            return current_dir
        current_dir = current_dir.parent
    
    # Se non troviamo una struttura corrispondente, usiamo la directory corrente
    logger.warning("Non è stato possibile determinare la root del progetto. Usando la directory corrente.")
    return Path(__file__).resolve().parent

def setup_environment():
    """Configura l'ambiente di esecuzione."""
    # Trova la root del progetto
    project_root = find_project_root()
    
    # Aggiungi la root del progetto al path di Python
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    logger.info(f"Root del progetto: {project_root}")
    return project_root

def create_test_data():
    """
    Crea dati di test per l'interfaccia di annotazione.
    
    Returns:
        Tuple[str, str]: Percorso del file di documenti e file di annotazioni
    """
    # Crea un file temporaneo per i documenti
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        documents = [
            {
                "id": "doc_1",
                "title": "Documento di test",
                "text": "L'articolo 1414 c.c. disciplina la simulazione del contratto. La legge 241/1990 regola il procedimento amministrativo."
            }
        ]
        json.dump(documents, f, indent=2, ensure_ascii=False)
        documents_file = f.name
    
    # Crea un file temporaneo per le annotazioni
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        annotations = {
            "doc_1": [
                {
                    "id": "ann_1",
                    "start": 0,
                    "end": 24,
                    "text": "L'articolo 1414 c.c.",
                    "type": "ARTICOLO_CODICE"
                },
                {
                    "id": "ann_2",
                    "start": 36,
                    "end": 47,
                    "text": "simulazione",
                    "type": "CONCETTO_GIURIDICO"
                },
                {
                    "id": "ann_3",
                    "start": 52,
                    "end": 61,
                    "text": "contratto",
                    "type": "CONCETTO_GIURIDICO"
                },
                {
                    "id": "ann_4",
                    "start": 67,
                    "end": 81,
                    "text": "legge 241/1990",
                    "type": "LEGGE"
                }
            ]
        }
        json.dump(annotations, f, indent=2, ensure_ascii=False)
        annotations_file = f.name
    
    logger.info(f"Dati di test creati: {documents_file}, {annotations_file}")
    return documents_file, annotations_file

def test_entity_manager_integration():
    """
    Testa l'integrazione con il gestore delle entità.
    
    Returns:
        bool: True se il test è passato, False altrimenti
    """
    try:
        from ner_giuridico.entities.entity_manager import get_entity_manager
        
        # Ottieni l'istanza del gestore delle entità
        entity_manager = get_entity_manager()
        
        # Verifica che i tipi di entità predefiniti esistano
        for entity_type in ["ARTICOLO_CODICE", "LEGGE", "DECRETO", "REGOLAMENTO_UE", 
                           "SENTENZA", "ORDINANZA", "CONCETTO_GIURIDICO"]:
            if not entity_manager.entity_type_exists(entity_type):
                logger.error(f"Tipo di entità {entity_type} non trovato nel gestore")
                return False
        
        # Prova ad aggiungere un nuovo tipo di entità
        success = entity_manager.add_entity_type(
            name="TEST_ENTITY",
            display_name="Entità di Test",
            category="custom",
            color="#FF0000",
            metadata_schema={"campo1": "string", "campo2": "number"}
        )
        
        if not success:
            logger.error("Errore nell'aggiunta di una nuova entità")
            return False
        
        # Verifica che l'entità sia stata aggiunta
        if not entity_manager.entity_type_exists("TEST_ENTITY"):
            logger.error("L'entità TEST_ENTITY non è stata aggiunta correttamente")
            return False
        
        # Prova a rimuovere l'entità
        success = entity_manager.remove_entity_type("TEST_ENTITY")
        
        if not success:
            logger.error("Errore nella rimozione dell'entità TEST_ENTITY")
            return False
        
        logger.info("Test dell'integrazione con il gestore delle entità completato con successo")
        return True
    
    except Exception as e:
        logger.error(f"Errore nel test dell'integrazione con il gestore delle entità: {e}")
        return False

def test_ner_system_integration():
    """
    Testa l'integrazione con il sistema NER.
    
    Returns:
        bool: True se il test è passato, False altrimenti
    """
    try:
        from ner_giuridico.ner import DynamicNERGiuridico
        
        # Inizializza il sistema NER
        ner = DynamicNERGiuridico()
        
        # Testo di esempio
        text = "L'articolo 1414 c.c. disciplina la simulazione del contratto."
        
        # Processa il testo
        result = ner.process(text)
        
        # Verifica che il risultato abbia la struttura attesa
        if not isinstance(result, dict):
            logger.error("Il risultato del sistema NER non è un dizionario")
            return False
        
        if "entities" not in result:
            logger.error("Il risultato del sistema NER non contiene la chiave 'entities'")
            return False
        
        if "references" not in result:
            logger.error("Il risultato del sistema NER non contiene la chiave 'references'")
            return False
        
        # Verifica che ci siano entità riconosciute
        entities = result["entities"]
        if not entities:
            logger.warning("Nessuna entità riconosciuta nel testo di esempio")
        
        logger.info(f"Entità riconosciute: {len(entities)}")
        for entity in entities:
            logger.info(f"- {entity['text']} ({entity['type']})")
        
        logger.info("Test dell'integrazione con il sistema NER completato con successo")
        return True
    
    except Exception as e:
        logger.error(f"Errore nel test dell'integrazione con il sistema NER: {e}")
        return False

def test_annotation_interface(base_url="http://localhost:8080"):
    """
    Testa l'interfaccia di annotazione tramite API HTTP.
    
    Args:
        base_url: URL base dell'interfaccia di annotazione
        
    Returns:
        bool: True se il test è passato, False altrimenti
    """
    try:
        # Verifica che l'interfaccia sia attiva
        try:
            response = requests.get(f"{base_url}")
            if response.status_code != 200:
                logger.error(f"L'interfaccia di annotazione non è attiva: {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            logger.error(f"Impossibile connettersi all'interfaccia di annotazione: {base_url}")
            return False
        
        # Crea un documento di test
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt') as f:
            f.write("L'articolo 1414 c.c. disciplina la simulazione del contratto.")
            f.flush()
            
            files = {'file': open(f.name, 'rb')}
            response = requests.post(f"{base_url}/api/upload_document", files=files)
            
            if response.status_code != 200:
                logger.error(f"Errore nel caricamento del documento: {response.status_code}")
                return False
            
            data = response.json()
            if data.get("status") != "success":
                logger.error(f"Errore nel caricamento del documento: {data.get('message')}")
                return False
            
            doc_id = data["document"]["id"]
            logger.info(f"Documento caricato con ID: {doc_id}")
        
        # Crea un'annotazione di test
        annotation = {
            "start": 0,
            "end": 24,
            "text": "L'articolo 1414 c.c.",
            "type": "ARTICOLO_CODICE"
        }
        
        response = requests.post(
            f"{base_url}/api/save_annotation",
            json={"doc_id": doc_id, "annotation": annotation}
        )
        
        if response.status_code != 200:
            logger.error(f"Errore nel salvataggio dell'annotazione: {response.status_code}")
            return False
        
        data = response.json()
        if data.get("status") != "success":
            logger.error(f"Errore nel salvataggio dell'annotazione: {data.get('message')}")
            return False
        
        annotation_id = data["annotation"]["id"]
        logger.info(f"Annotazione salvata con ID: {annotation_id}")
        
        # Verifica il riconoscimento automatico delle entità
        response = requests.post(
            f"{base_url}/api/recognize",
            json={"text": "L'articolo 1414 c.c. disciplina la simulazione del contratto."}
        )
        
        if response.status_code != 200:
            logger.error(f"Errore nel riconoscimento automatico: {response.status_code}")
            return False
        
        data = response.json()
        if data.get("status") != "success":
            logger.error(f"Errore nel riconoscimento automatico: {data.get('message')}")
            return False
        
        entities = data.get("entities", [])
        logger.info(f"Entità riconosciute automaticamente: {len(entities)}")
        for entity in entities:
            logger.info(f"- {entity['text']} ({entity['type']})")
        
        # Esporta le annotazioni
        response = requests.get(f"{base_url}/api/export_annotations?format=spacy")
        
        if response.status_code != 200:
            logger.error(f"Errore nell'esportazione delle annotazioni: {response.status_code}")
            return False
        
        data = response.json()
        if "data" not in data:
            logger.error("L'esportazione delle annotazioni non ha restituito dati")
            return False
        
        logger.info(f"Annotazioni esportate: {len(data['data'])}")
        
        # Elimina l'annotazione
        response = requests.post(
            f"{base_url}/api/delete_annotation",
            json={"doc_id": doc_id, "annotation_id": annotation_id}
        )
        
        if response.status_code != 200:
            logger.error(f"Errore nell'eliminazione dell'annotazione: {response.status_code}")
            return False
        
        data = response.json()
        if data.get("status") != "success":
            logger.error(f"Errore nell'eliminazione dell'annotazione: {data.get('message')}")
            return False
        
        logger.info("Annotazione eliminata con successo")
        
        logger.info("Test dell'interfaccia di annotazione completato con successo")
        return True
    
    except Exception as e:
        logger.error(f"Errore nel test dell'interfaccia di annotazione: {e}")
        return False

def test_converter_module():
    """
    Testa il modulo di conversione.
    
    Returns:
        bool: True se il test è passato, False altrimenti
    """
    try:
        # Importa il modulo di conversione
        sys.path.append(str(find_project_root()))
        from ner_giuridico.utils.converter import (
            convert_annotations_to_spacy_format,
            convert_annotations_to_ner_format,
            save_annotations_for_training
        )
        
        # Crea dati di test
        documents_file, annotations_file = create_test_data()
        
        try:
            # Carica i dati di test
            with open(documents_file, 'r', encoding='utf-8') as f:
                documents = json.load(f)
            
            with open(annotations_file, 'r', encoding='utf-8') as f:
                annotations = json.load(f)
            
            # Converti in formato spaCy
            spacy_data = convert_annotations_to_spacy_format(annotations, documents)
            
            # Verifica che il risultato abbia la struttura attesa
            if not isinstance(spacy_data, list):
                logger.error("Il risultato della conversione a spaCy non è una lista")
                return False
            
            if not spacy_data:
                logger.error("Il risultato della conversione a spaCy è vuoto")
                return False
            
            first_item = spacy_data[0]
            if "text" not in first_item or "entities" not in first_item:
                logger.error("Il risultato della conversione a spaCy non ha la struttura attesa")
                return False
            
            # Converti in formato NER
            ner_data = convert_annotations_to_ner_format(annotations, documents)
            
            # Verifica che il risultato abbia la struttura attesa
            if not isinstance(ner_data, list):
                logger.error("Il risultato della conversione a NER non è una lista")
                return False
            
            if not ner_data:
                logger.error("Il risultato della conversione a NER è vuoto")
                return False
            
            first_item = ner_data[0]
            if "text" not in first_item or "entities" not in first_item:
                logger.error("Il risultato della conversione a NER non ha la struttura attesa")
                return False
            
            # Salva i dati per l'addestramento
            with tempfile.TemporaryDirectory() as temp_dir:
                output_files = save_annotations_for_training(
                    annotations, 
                    documents, 
                    temp_dir,
                    formats=["spacy", "ner"]
                )
                
                logger.info(f"File generati: {output_files}")
                
                # Verifica che i file siano stati creati
                if not output_files:
                    logger.error("Nessun file è stato generato")
                    return False
                
                for format_type, file_path in output_files.items():
                    if not os.path.exists(file_path):
                        logger.error(f"Il file {file_path} non è stato creato")
                        return False
            
            logger.info("Test del modulo di conversione completato con successo")
            return True
            
        finally:
            # Rimuovi i file temporanei
            try:
                os.unlink(documents_file)
                os.unlink(annotations_file)
            except:
                pass
    
    except Exception as e:
        logger.error(f"Errore nel test del modulo di conversione: {e}")
        return False

def test_ner_training_module():
    """
    Testa il modulo di addestramento del sistema NER.
    
    Returns:
        bool: True se il test è passato, False altrimenti
    """
    try:
        # Importa il modulo di addestramento
        sys.path.append(str(find_project_root()))
        from ner_giuridico.training.ner_trainer import NERTrainer, train_from_annotations
        
        # Crea dati di test
        documents_file, annotations_file = create_test_data()
        
        try:
            # Carica i dati di test
            with open(documents_file, 'r', encoding='utf-8') as f:
                documents = json.load(f)
            
            with open(annotations_file, 'r', encoding='utf-8') as f:
                annotations = json.load(f)
            
            # Converti in formato spaCy
            from ner_giuridico.utils.converter import convert_annotations_to_spacy_format
            spacy_data = convert_annotations_to_spacy_format(annotations, documents)
            
            # Salva i dati in un file temporaneo
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(spacy_data, f, indent=2, ensure_ascii=False)
                spacy_file = f.name
            
            try:
                # Inizializza il trainer
                with tempfile.TemporaryDirectory() as temp_dir:
                    trainer = NERTrainer(temp_dir)
                    
                    # Verifica che il trainer sia stato inizializzato correttamente
                    if not trainer:
                        logger.error("Il trainer non è stato inizializzato correttamente")
                        return False
                    
                    # Nota: non eseguiamo l'addestramento effettivo perché richiede risorse
                    # e dipendenze specifiche, ma verifichiamo solo che il modulo sia disponibile
                    logger.info("Test del modulo di addestramento completato con successo")
                    return True
            
            finally:
                # Rimuovi il file temporaneo
                try:
                    os.unlink(spacy_file)
                except:
                    pass
            
        finally:
            # Rimuovi i file temporanei
            try:
                os.unlink(documents_file)
                os.unlink(annotations_file)
            except:
                pass
    
    except Exception as e:
        logger.error(f"Errore nel test del modulo di addestramento: {e}")
        return False

def test_knowledge_graph_integration():
    """Test the integration with Neo4j knowledge graph."""
    try:
        from ner_giuridico.normalizer import EntityNormalizer
        from unittest.mock import MagicMock
        
        # Mock Neo4j driver
        class MockGraphDatabase:
            @staticmethod
            def driver(*args, **kwargs):
                driver = MagicMock()
                session = MagicMock()
                transaction = MagicMock()
                result = MagicMock()
                
                # Mock query results
                result.data.return_value = [{
                    "n": {
                        "id": "art_1414_cc",
                        "text": "Articolo 1414 c.c.",
                        "type": "ARTICOLO_CODICE",
                        "metadata": {
                            "codice": "CODICE_CIVILE",
                            "articolo": "1414"
                        }
                    }
                }]
                
                transaction.run.return_value = result
                session.begin_transaction.return_value = transaction
                driver.session.return_value = session
                return driver
                
        # Test entity enrichment
        normalizer = EntityNormalizer(graph_db=MockGraphDatabase())
        
        entity = {
            "text": "art. 1414 c.c.",
            "type": "ARTICOLO_CODICE"
        }
        
        enriched = normalizer.enrich_entity(entity)
        
        # Verify enrichment
        if not enriched.get("metadata"):
            logger.error("Entity enrichment failed - no metadata")
            return False
            
        if enriched["metadata"].get("codice") != "CODICE_CIVILE":
            logger.error("Entity enrichment failed - wrong metadata")
            return False
            
        logger.info("Knowledge graph integration test passed")
        return True
        
    except Exception as e:
        logger.error(f"Error in knowledge graph integration test: {e}")
        return False

def run_all_tests():
    """
    Esegue tutti i test di integrazione.
    
    Returns:
        Dict[str, bool]: Risultati dei test
    """
    # Configura l'ambiente
    setup_environment()
    
    # Esegui i test
    results = {
        "entity_manager": test_entity_manager_integration(),
        "ner_system": test_ner_system_integration(),
        "converter": test_converter_module(),
        "training": test_ner_training_module(),
        "knowledge_graph": test_knowledge_graph_integration()
    }
    
    # Test dell'interfaccia solo se specificato
    if args.interface:
        results["interface"] = test_annotation_interface(args.url)
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test di integrazione per NER-Giuridico')
    parser.add_argument('--interface', action='store_true', help='Testa anche l\'interfaccia di annotazione')
    parser.add_argument('--url', default='http://localhost:8080', help='URL dell\'interfaccia di annotazione')
    args = parser.parse_args()
    
    # Esegui i test
    results = run_all_tests()
    
    # Stampa i risultati
    logger.info("\n=== Risultati dei Test ===")
    for test, passed in results.items():
        status = "✅ PASSATO" if passed else "❌ FALLITO"
        logger.info(f"{test}: {status}")
    
    # Verifica se tutti i test sono passati
    all_passed = all(results.values())
    
    if all_passed:
        logger.info("\n✅ Tutti i test sono passati!")
        sys.exit(0)
    else:
        logger.error("\n❌ Alcuni test sono falliti!")
        sys.exit(1)