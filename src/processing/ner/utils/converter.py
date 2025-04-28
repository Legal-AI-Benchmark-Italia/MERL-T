"""
Modulo per la conversione dei dati di annotazione tra diversi formati.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple, Union

# Configurazione del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def convert_annotations_to_spacy_format(annotations: Dict[str, List[Dict[str, Any]]], 
                                       documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Converte le annotazioni dal formato del labeler al formato spaCy.
    
    Args:
        annotations: Annotazioni nel formato del labeler, organizzate per documento.
        documents: Lista di documenti con testo.
        
    Returns:
        Lista di documenti nel formato spaCy (testo e entità).
    """
    logger.info(f"Conversione di {len(annotations)} set di annotazioni al formato spaCy")
    
    spacy_data = []
    
    for doc_id, doc_annotations in annotations.items():
        # Trova il documento corrispondente
        document = next((doc for doc in documents if doc['id'] == doc_id), None)
        
        if not document:
            logger.warning(f"Documento non trovato per le annotazioni con ID {doc_id}")
            continue
            
        text = document['text']
        entities = []
        
        for ann in doc_annotations:
            try:
                # Formato spaCy standard: (start, end, label)
                entities.append((
                    ann['start'],
                    ann['end'],
                    ann['type']
                ))
            except KeyError as e:
                logger.error(f"Errore nella conversione dell'annotazione: {e}")
                continue
        
        if entities:
            spacy_data.append({
                "text": text,
                "entities": entities
            })
            
    logger.info(f"Convertiti {len(spacy_data)} documenti al formato spaCy")
    return spacy_data

def convert_annotations_to_ner_format(annotations: Dict[str, List[Dict[str, Any]]], 
                                     documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Converte le annotazioni dal formato del labeler al formato del sistema NER.
    
    Args:
        annotations: Annotazioni nel formato del labeler, organizzate per documento.
        documents: Lista di documenti con testo.
        
    Returns:
        Lista di documenti nel formato NER (testo e entità).
    """
    logger.info(f"Conversione di {len(annotations)} set di annotazioni al formato NER")
    
    ner_data = []
    
    for doc_id, doc_annotations in annotations.items():
        # Trova il documento corrispondente
        document = next((doc for doc in documents if doc['id'] == doc_id), None)
        
        if not document:
            logger.warning(f"Documento non trovato per le annotazioni con ID {doc_id}")
            continue
            
        text = document['text']
        entities = []
        
        for ann in doc_annotations:
            try:
                # Formato NER: oggetti Entity come dizionari
                entities.append({
                    "text": ann['text'],
                    "type": ann['type'],
                    "start_char": ann['start'],
                    "end_char": ann['end'],
                    "normalized_text": ann.get('text', '')  # Default al testo originale
                })
            except KeyError as e:
                logger.error(f"Errore nella conversione dell'annotazione: {e}")
                continue
        
        if entities:
            ner_data.append({
                "text": text,
                "entities": entities
            })
            
    logger.info(f"Convertiti {len(ner_data)} documenti al formato NER")
    return ner_data

def convert_spacy_to_conll(spacy_data: List[Dict[str, Any]], output_file: str) -> bool:
    """
    Converte i dati spaCy in formato CoNLL per l'addestramento di modelli NER.
    
    Args:
        spacy_data: Dati nel formato spaCy.
        output_file: Percorso del file di output.
        
    Returns:
        True se la conversione è avvenuta con successo, False altrimenti.
    """
    try:
        logger.info(f"Conversione di {len(spacy_data)} documenti spaCy in formato CoNLL")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for doc in spacy_data:
                text = doc['text']
                entities = doc['entities']
                
                # Ordina le entità per posizione di inizio
                entities = sorted(entities, key=lambda e: e[0])
                
                # Crea una lista di token con i rispettivi tag
                tokens = []
                current_pos = 0
                
                # Crea un vettore di tag IOB per ogni carattere del testo
                iob_tags = ['O'] * len(text)
                
                # Marca le entità nel vettore dei tag
                for start, end, label in entities:
                    # Marca il primo token dell'entità con B-
                    iob_tags[start] = f'B-{label}'
                    
                    # Marca i token successivi con I-
                    for i in range(start + 1, end):
                        if i < len(iob_tags):
                            iob_tags[i] = f'I-{label}'
                
                # Tokenizza il testo (semplice split su spazi)
                # Nota: questa è una tokenizzazione molto semplice
                # In un sistema reale, si dovrebbe usare un tokenizzatore vero e proprio
                raw_tokens = text.split()
                
                # Ricostruisci le posizioni dei token nel testo
                token_pos = 0
                for token in raw_tokens:
                    # Trova la posizione del token
                    token_start = text.find(token, token_pos)
                    if token_start == -1:
                        continue
                        
                    token_end = token_start + len(token)
                    token_pos = token_end
                    
                    # Determina il tag per questo token
                    # Prendi il tag del primo carattere del token
                    tag = iob_tags[token_start]
                    
                    tokens.append((token, tag))
                
                # Scrivi in formato CoNLL
                for token, tag in tokens:
                    f.write(f"{token}\t{tag}\n")
                
                # Aggiungi una riga vuota tra i documenti
                f.write("\n")
                
        logger.info(f"Conversione in formato CoNLL completata: {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Errore nella conversione in formato CoNLL: {e}")
        return False

def save_annotations_for_training(annotations: Dict[str, List[Dict[str, Any]]], 
                                 documents: List[Dict[str, Any]], 
                                 output_dir: str,
                                 formats: List[str] = ['spacy', 'ner', 'conll']) -> Dict[str, str]:
    """
    Salva le annotazioni in vari formati per l'addestramento di modelli NER.
    
    Args:
        annotations: Annotazioni nel formato del labeler.
        documents: Lista di documenti con testo.
        output_dir: Directory dove salvare i file.
        formats: Lista di formati da generare.
        
    Returns:
        Dizionario con i percorsi dei file generati.
    """
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        output_files = {}
        
        # Formato spaCy
        if 'spacy' in formats:
            spacy_data = convert_annotations_to_spacy_format(annotations, documents)
            spacy_file = os.path.join(output_dir, 'annotations_spacy.json')
            
            with open(spacy_file, 'w', encoding='utf-8') as f:
                json.dump(spacy_data, f, indent=2, ensure_ascii=False)
                
            output_files['spacy'] = spacy_file
            logger.info(f"Salvate annotazioni in formato spaCy: {spacy_file}")
            
        # Formato NER
        if 'ner' in formats:
            ner_data = convert_annotations_to_ner_format(annotations, documents)
            ner_file = os.path.join(output_dir, 'annotations_ner.json')
            
            with open(ner_file, 'w', encoding='utf-8') as f:
                json.dump(ner_data, f, indent=2, ensure_ascii=False)
                
            output_files['ner'] = ner_file
            logger.info(f"Salvate annotazioni in formato NER: {ner_file}")
            
        # Formato CoNLL
        if 'conll' in formats and 'spacy' in formats:
            conll_file = os.path.join(output_dir, 'annotations.conll')
            
            if convert_spacy_to_conll(spacy_data, conll_file):
                output_files['conll'] = conll_file
                logger.info(f"Salvate annotazioni in formato CoNLL: {conll_file}")
            
        return output_files
        
    except Exception as e:
        logger.error(f"Errore nel salvataggio delle annotazioni: {e}")
        return {}

if __name__ == "__main__":
    # Test di esempio
    test_annotations = {
        "doc_1": [
            {
                "id": "ann_1",
                "start": 0,
                "end": 10,
                "text": "L'articolo",
                "type": "ARTICOLO_CODICE"
            }
        ]
    }
    
    test_documents = [
        {
            "id": "doc_1",
            "title": "Test",
            "text": "L'articolo 1414 c.c. disciplina la simulazione."
        }
    ]
    
    # Converti in formato spaCy
    spacy_data = convert_annotations_to_spacy_format(test_annotations, test_documents)
    print(f"Dati spaCy: {spacy_data}")
    
    # Converti in formato NER
    ner_data = convert_annotations_to_ner_format(test_annotations, test_documents)
    print(f"Dati NER: {ner_data}")