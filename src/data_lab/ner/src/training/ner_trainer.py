"""
Modulo per l'addestramento del sistema NER con i dati annotati.
"""

import os
import json
import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple

# Configurazione del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NERTrainer:
    """
    Classe per addestrare il sistema NER con i dati annotati.
    """
    
    def __init__(self, model_dir: Optional[str] = None):
        """
        Inizializza il trainer NER.
        
        Args:
            model_dir: Directory dove salvare i modelli addestrati.
        """
        self.model_dir = model_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                                 "..", "models", "transformer")
        
        # Crea la directory se non esiste
        os.makedirs(self.model_dir, exist_ok=True)
        
        logger.info(f"Trainer NER inizializzato con model_dir: {self.model_dir}")
    
    def train_from_spacy_format(self, spacy_data: List[Dict[str, Any]], 
                              output_model_name: Optional[str] = None) -> str:
        """
        Addestra un modello NER utilizzando i dati in formato spaCy.
        
        Args:
            spacy_data: Dati di addestramento in formato spaCy.
            output_model_name: Nome del modello addestrato.
            
        Returns:
            Percorso del modello addestrato.
        """
        try:
            import spacy
            from spacy.tokens import DocBin
            from spacy.training import Example
            
            logger.info(f"Inizio addestramento con {len(spacy_data)} documenti")
            
            # Nome del modello
            output_model_name = output_model_name or f"ner_giuridico_model"
            output_dir = os.path.join(self.model_dir, output_model_name)
            
            # Crea un DocBin per memorizzare i documenti di addestramento
            doc_bin = DocBin()
            nlp = spacy.blank("it")
            
            # Prepara i dati di addestramento
            for example in spacy_data:
                text = example["text"]
                doc = nlp.make_doc(text)
                
                # Aggiungi le entità al documento
                ents = []
                for start, end, label in example["entities"]:
                    span = doc.char_span(start, end, label=label)
                    if span is not None:
                        ents.append(span)
                
                doc.ents = ents
                doc_bin.add(doc)
            
            # Salva i dati di addestramento
            with tempfile.NamedTemporaryFile(suffix=".spacy", delete=False) as f:
                train_file = f.name
                doc_bin.to_disk(train_file)
            
            logger.info(f"Dati di addestramento salvati in {train_file}")
            
            # Crea la configurazione di addestramento
            config = {
                "paths": {
                    "train": train_file,
                    "dev": train_file  # Usiamo lo stesso file per semplicità
                },
                "system": {
                    "gpu_allocator": "pytorch" if spacy.prefer_gpu() else None
                },
                "nlp": {
                    "lang": "it",
                    "pipeline": ["ner"],
                    "batch_size": 128
                },
                "components": {
                    "ner": {
                        "factory": "ner",
                        "moves": None,
                        "update_with_oracle_cut_size": 100
                    }
                },
                "training": {
                    "dev_corpus": "corpora.dev",
                    "train_corpus": "corpora.train",
                    "seed": 1,
                    "gpu_allocator": "pytorch",
                    "accumulate_gradient": 1,
                    "patience": 1600,
                    "max_epochs": 0,
                    "max_steps": 20000,
                    "eval_frequency": 200,
                    "frozen_components": [],
                    "before_to_disk": None,
                    "batcher": {
                        "@batchers": "spacy.batch_by_words.v1",
                        "discard_oversize": False,
                        "tolerance": 0.2,
                        "get_length": None,
                        "size": {
                            "@schedules": "compounding.v1",
                            "start": 100,
                            "stop": 1000,
                            "compound": 1.001,
                            "t": 0.0
                        }
                    },
                    "logger": {
                        "@loggers": "spacy.ConsoleLogger.v1",
                        "progress_bar": True
                    },
                    "optimizer": {
                        "@optimizers": "Adam.v1",
                        "beta1": 0.9,
                        "beta2": 0.999,
                        "L2_is_weight_decay": True,
                        "L2": 0.01,
                        "grad_clip": 1.0,
                        "use_averages": False,
                        "eps": 1e-08
                    },
                    "score_weights": {
                        "ents_f": 1.0,
                        "ents_p": 0.0,
                        "ents_r": 0.0,
                        "ents_per_type": None
                    }
                }
            }
            
            # Salva la configurazione
            config_path = os.path.join(self.model_dir, "config.cfg")
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Configurazione di addestramento salvata in {config_path}")
            
            try:
                # Addestra il modello
                logger.info(f"Inizio addestramento...")
                spacy.cli.train(config_path, output_dir, overrides={"paths.train": train_file, "paths.dev": train_file})
                
                logger.info(f"Addestramento completato. Modello salvato in {output_dir}")
                
                # Rimuovi il file temporaneo
                os.unlink(train_file)
                
                return output_dir
                
            except Exception as e:
                logger.error(f"Errore durante l'addestramento: {e}")
                raise
        
        except ImportError as e:
            logger.error(f"Libreria mancante: {e}")
            logger.error("Assicurati di aver installato spacy con 'pip install spacy'")
            raise
        except Exception as e:
            logger.error(f"Errore nell'addestramento del modello: {e}")
            raise
    
    def train_transformer_model(self, annotations_file: str, 
                              base_model: str = "dbmdz/bert-base-italian-xxl-cased",
                              output_model_name: Optional[str] = None) -> str:
        """
        Addestra un modello transformer per NER utilizzando i dati annotati.
        
        Args:
            annotations_file: Percorso al file delle annotazioni in formato JSON.
            base_model: Modello base da utilizzare per il fine-tuning.
            output_model_name: Nome del modello addestrato.
            
        Returns:
            Percorso del modello addestrato.
        """
        try:
            from transformers import (
                AutoTokenizer, 
                AutoModelForTokenClassification,
                Trainer, 
                TrainingArguments,
                DataCollatorForTokenClassification
            )
            from datasets import Dataset
            import torch
            import numpy as np
            
            logger.info(f"Inizio addestramento transformer con file {annotations_file}")
            
            # Nome del modello
            output_model_name = output_model_name or f"ner_transformer_model"
            output_dir = os.path.join(self.model_dir, output_model_name)
            
            # Carica le annotazioni
            with open(annotations_file, 'r', encoding='utf-8') as f:
                annotations = json.load(f)
            
            logger.info(f"Caricati {len(annotations)} documenti annotati")
            
            # Carica il tokenizer
            tokenizer = AutoTokenizer.from_pretrained(base_model)
            
            # Prepara i dati di addestramento
            train_examples = []
            
            for doc in annotations:
                text = doc["text"]
                entities = doc.get("entities", [])
                
                # Ordina le entità per posizione
                entities = sorted(entities, key=lambda e: e[0] if isinstance(e, tuple) else e.get("start_char", 0))
                
                # Crea le etichette IOB
                labels = ["O"] * len(text)
                
                for entity in entities:
                    if isinstance(entity, tuple):
                        start, end, label = entity
                    else:
                        start = entity.get("start_char", 0)
                        end = entity.get("end_char", 0)
                        label = entity.get("type", "UNKNOWN")
                    
                    # Marca il primo token con B-
                    if start < len(labels):
                        labels[start] = f"B-{label}"
                    
                    # Marca i token successivi con I-
                    for i in range(start + 1, end):
                        if i < len(labels):
                            labels[i] = f"I-{label}"
                
                train_examples.append({
                    "text": text,
                    "labels": labels
                })
            
            # Converti in Dataset
            train_dataset = Dataset.from_dict({
                "text": [ex["text"] for ex in train_examples],
                "labels": [ex["labels"] for ex in train_examples]
            })
            
            # Funzione di tokenizzazione e allineamento delle etichette
            def tokenize_and_align_labels(examples):
                tokenized_inputs = tokenizer(
                    examples["text"],
                    padding="max_length",
                    truncation=True,
                    return_tensors="pt"
                )
                
                labels = []
                for i, label in enumerate(examples["labels"]):
                    word_ids = tokenized_inputs.word_ids(batch_index=i)
                    previous_word_idx = None
                    label_ids = []
                    
                    for word_idx in word_ids:
                        if word_idx is None:
                            label_ids.append(-100)
                        elif word_idx != previous_word_idx:
                            label_ids.append(label[word_idx])
                        else:
                            label_ids.append(-100)
                        previous_word_idx = word_idx
                    
                    labels.append(label_ids)
                
                tokenized_inputs["labels"] = labels
                return tokenized_inputs
            
            # Applica la tokenizzazione
            tokenized_train_dataset = train_dataset.map(
                tokenize_and_align_labels,
                batched=True,
                remove_columns=train_dataset.column_names
            )
            
            # Crea il modello
            model = AutoModelForTokenClassification.from_pretrained(
                base_model,
                num_labels=len(train_dataset.unique("labels"))
            )
            
            # Configura l'addestramento
            training_args = TrainingArguments(
                output_dir=output_dir,
                learning_rate=2e-5,
                per_device_train_batch_size=8,
                per_device_eval_batch_size=8,
                num_train_epochs=3,
                weight_decay=0.01,
                save_strategy="epoch",
                save_total_limit=2,
            )
            
            # Crea il trainer
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=tokenized_train_dataset,
                tokenizer=tokenizer,
                data_collator=DataCollatorForTokenClassification(tokenizer)
            )
            
            # Addestra il modello
            trainer.train()
            
            # Salva il modello
            trainer.save_model(output_dir)
            tokenizer.save_pretrained(output_dir)
            
            logger.info(f"Addestramento transformer completato. Modello salvato in {output_dir}")
            
            return output_dir
            
        except ImportError as e:
            logger.error(f"Libreria mancante: {e}")
            logger.error("Assicurati di aver installato transformers e datasets con 'pip install transformers datasets'")
            raise
        except Exception as e:
            logger.error(f"Errore nell'addestramento del modello transformer: {e}")
            raise
    
    def integrate_model_with_ner_system(self, model_path: str) -> bool:
        """
        Integra il modello addestrato con il sistema NER.
        
        Args:
            model_path: Percorso al modello addestrato.
            
        Returns:
            True se l'integrazione è avvenuta con successo, False altrimenti.
        """
        try:
            from src.ner import DynamicNERGiuridico
            
            logger.info(f"Integrazione del modello {model_path} con il sistema NER")
            
            # Qui dovresti integrare il modello con il sistema NER
            # Questo è solo un esempio concettuale, l'implementazione effettiva
            # dipenderà dall'architettura specifica del sistema NER
            
            # Ad esempio, potresti registrare il percorso del modello in una
            # configurazione o direttamente aggiornare il modello nel sistema NER
            
            # Per ora, possiamo solo simulare l'integrazione
            logger.info(f"Modello integrato con successo (simulazione)")
            
            return True
            
        except ImportError as e:
            logger.error(f"Errore di importazione: {e}")
            return False
        except Exception as e:
            logger.error(f"Errore nell'integrazione del modello: {e}")
            return False


def train_from_annotations(annotations_file: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Funzione di utilità per addestrare un modello NER dalle annotazioni.
    
    Args:
        annotations_file: Percorso al file delle annotazioni.
        output_dir: Directory di output per il modello addestrato.
        
    Returns:
        Dizionario con i risultati dell'addestramento.
    """
    try:
        # Inizializza il trainer
        trainer = NERTrainer(output_dir)
        
        # Carica le annotazioni
        with open(annotations_file, 'r', encoding='utf-8') as f:
            annotations = json.load(f)
        
        logger.info(f"Addestramento con {len(annotations)} documenti")
        
        # Determina il tipo di dati
        is_spacy_format = False
        if annotations and isinstance(annotations, list):
            first_item = annotations[0]
            if "text" in first_item and "entities" in first_item:
                # Controlla se entities è una lista di tuple (spaCy) o di dict (NER)
                if first_item["entities"] and isinstance(first_item["entities"][0], tuple):
                    is_spacy_format = True
        
        if is_spacy_format:
            # Addestra con i dati spaCy
            model_path = trainer.train_from_spacy_format(annotations)
        else:
            # Converti in spaCy e addestra
            logger.info("Conversione dei dati in formato spaCy")
            
            spacy_data = []
            for doc in annotations:
                text = doc["text"]
                entities = []
                
                for entity in doc.get("entities", []):
                    if isinstance(entity, dict):
                        start = entity.get("start_char", 0)
                        end = entity.get("end_char", 0)
                        label = entity.get("type", "UNKNOWN")
                        entities.append((start, end, label))
                
                spacy_data.append({
                    "text": text,
                    "entities": entities
                })
            
            model_path = trainer.train_from_spacy_format(spacy_data)
        
        # Integra il modello con il sistema NER
        integration_success = trainer.integrate_model_with_ner_system(model_path)
        
        return {
            "success": True,
            "model_path": model_path,
            "integration_success": integration_success
        }
        
    except Exception as e:
        logger.error(f"Errore nell'addestramento: {e}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    # Test di esempio
    example_annotations = [
        {
            "text": "L'articolo 1414 c.c. disciplina la simulazione del contratto.",
            "entities": [
                (0, 20, "ARTICOLO_CODICE"),
                (32, 43, "CONCETTO_GIURIDICO")
            ]
        }
    ]
    
    # Salva le annotazioni in un file temporaneo
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(example_annotations, f)
        temp_file = f.name
    
    print(f"Annotazioni salvate in {temp_file}")
    
    try:
        # Addestra un modello con le annotazioni
        result = train_from_annotations(temp_file)
        print(f"Risultato dell'addestramento: {result}")
    except Exception as e:
        print(f"Errore durante il test: {e}")
    finally:
        # Rimuovi il file temporaneo
        os.unlink(temp_file)