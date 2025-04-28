"""
Modulo per l'addestramento del sistema NER con i dati annotati.
Supporta sia modelli spaCy che modelli transformer, con valutazione e integrazione.
"""

import os
import json
import logging
import tempfile
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple, Callable

import numpy as np
from tqdm import tqdm

# Configurazione del logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class NERTrainer:
    """
    Classe per addestrare il sistema NER con i dati annotati.
    Supporta sia modelli spaCy che modelli transformer, con valutazione e integrazione.
    """
    
    def __init__(self, model_dir: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """
        Inizializza il trainer NER.
        
        Args:
            model_dir: Directory dove salvare i modelli addestrati.
            config: Configurazione aggiuntiva per l'addestramento.
        """
        self.model_dir = model_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                                 "..", "..", "models", "transformer")
        
        # Configurazione predefinita
        self.config = {
            "spacy": {
                "batch_size": 128,
                "dropout": 0.2,
                "epochs": 30,
                "patience": 5,
                "eval_frequency": 200
            },
            "transformer": {
                "batch_size": 16,
                "learning_rate": 2e-5,
                "epochs": 3,
                "weight_decay": 0.01,
                "max_length": 512,
                "warmup_steps": 500
            },
            "evaluation": {
                "split_ratio": 0.2,
                "random_seed": 42
            }
        }
        
        # Aggiorna la configurazione se fornita
        if config:
            self._update_config(config)
        
        # Crea la directory se non esiste
        os.makedirs(self.model_dir, exist_ok=True)
        
        logger.info(f"Trainer NER inizializzato con model_dir: {self.model_dir}")
    
    def _update_config(self, config: Dict[str, Any]) -> None:
        """
        Aggiorna la configurazione di addestramento.
        
        Args:
            config: Nuova configurazione da applicare.
        """
        for section, values in config.items():
            if section in self.config:
                self.config[section].update(values)
            else:
                self.config[section] = values
    
    def train_from_spacy_format(self, spacy_data: List[Dict[str, Any]], 
                               output_model_name: Optional[str] = None,
                               validation_data: Optional[List[Dict[str, Any]]] = None,
                               callbacks: Optional[List[Callable]] = None) -> str:
        """
        Addestra un modello NER utilizzando i dati in formato spaCy.
        
        Args:
            spacy_data: Dati di addestramento in formato spaCy.
            output_model_name: Nome del modello addestrato.
            validation_data: Dati di validazione in formato spaCy.
            callbacks: Lista di funzioni di callback per monitorare l'addestramento.
            
        Returns:
            Percorso del modello addestrato.
        """
        try:
            import spacy
            from spacy.tokens import DocBin
            from spacy.training import Example
            
            logger.info(f"Inizio addestramento con {len(spacy_data)} documenti")
            
            # Nome del modello
            output_model_name = output_model_name or f"ner_model"
            output_dir = os.path.join(self.model_dir, output_model_name)
            
            # Se non ci sono dati di validazione, dividi i dati di addestramento
            if not validation_data and len(spacy_data) > 5:
                logger.info("Divisione dei dati in set di addestramento e validazione")
                train_data, validation_data = self._split_data(spacy_data)
            else:
                train_data = spacy_data
            
            # Crea un DocBin per memorizzare i documenti di addestramento
            train_doc_bin = DocBin()
            nlp = spacy.blank("it")
            
            # Prepara i dati di addestramento
            for example in train_data:
                doc = nlp.make_doc(example["text"])
                
                # Aggiungi le entità al documento
                ents = []
                for start, end, label in example["entities"]:
                    span = doc.char_span(start, end, label=label)
                    if span is not None:
                        ents.append(span)
                    else:
                        logger.warning(f"Impossibile creare span per l'entità {label} ({start}, {end}) nel testo: {example['text']}")
                
                doc.ents = ents
                train_doc_bin.add(doc)
            
            # Salva i dati di addestramento
            with tempfile.NamedTemporaryFile(suffix=".spacy", delete=False) as f:
                train_file = f.name
                train_doc_bin.to_disk(train_file)
            
            logger.info(f"Dati di addestramento salvati in {train_file}")
            
            # Prepara i dati di validazione, se disponibili
            val_file = None
            if validation_data:
                val_doc_bin = DocBin()
                
                for example in validation_data:
                    doc = nlp.make_doc(example["text"])
                    
                    # Aggiungi le entità al documento
                    ents = []
                    for start, end, label in example["entities"]:
                        span = doc.char_span(start, end, label=label)
                        if span is not None:
                            ents.append(span)
                        else:
                            logger.warning(f"Impossibile creare span per l'entità {label} ({start}, {end}) nel testo: {example['text']}")
                    
                    doc.ents = ents
                    val_doc_bin.add(doc)
                
                # Salva i dati di validazione
                with tempfile.NamedTemporaryFile(suffix=".spacy", delete=False) as f:
                    val_file = f.name
                    val_doc_bin.to_disk(val_file)
                
                logger.info(f"Dati di validazione salvati in {val_file}")
            
            # Crea la configurazione di addestramento
            config = {
                "paths": {
                    "train": train_file,
                    "dev": val_file if val_file else train_file
                },
                "system": {
                    "gpu_allocator": "pytorch" if spacy.prefer_gpu() else None
                },
                "nlp": {
                    "lang": "it",
                    "pipeline": ["ner"],
                    "batch_size": self.config["spacy"]["batch_size"]
                },
                "components": {
                    "ner": {
                        "factory": "ner",
                        "moves": None,
                        "update_with_oracle_cut_size": 100,
                        "model": {
                            "@architectures": "spacy.TransitionBasedParser.v2",
                            "state_type": "ner",
                            "extra_state_tokens": False,
                            "hidden_width": 64,
                            "maxout_pieces": 2,
                            "use_upper": True,
                            "nO": None
                        }
                    }
                },
                "training": {
                    "dev_corpus": "corpora.dev",
                    "train_corpus": "corpora.train",
                    "seed": self.config["evaluation"]["random_seed"],
                    "gpu_allocator": "pytorch" if spacy.prefer_gpu() else None,
                    "dropout": self.config["spacy"]["dropout"],
                    "accumulate_gradient": 1,
                    "patience": self.config["spacy"]["patience"],
                    "max_epochs": self.config["spacy"]["epochs"],
                    "max_steps": 20000,
                    "eval_frequency": self.config["spacy"]["eval_frequency"],
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
                spacy.cli.train(config_path, output_dir, overrides={
                    "paths.train": train_file, 
                    "paths.dev": val_file if val_file else train_file
                })
                
                logger.info(f"Addestramento completato. Modello salvato in {output_dir}")
                
                # Valuta il modello, se ci sono dati di validazione
                if validation_data:
                    metrics = self.evaluate_spacy_model(output_dir, validation_data)
                    logger.info(f"Valutazione del modello: {metrics}")
                    
                    # Salva le metriche di valutazione
                    metrics_path = os.path.join(output_dir, "metrics.json")
                    with open(metrics_path, "w", encoding="utf-8") as f:
                        json.dump(metrics, f, indent=2)
                
                # Rimuovi i file temporanei
                if train_file:
                    os.unlink(train_file)
                if val_file:
                    os.unlink(val_file)
                
                return output_dir
                
            except Exception as e:
                logger.error(f"Errore durante l'addestramento: {e}")
                # Rimuovi i file temporanei in caso di errore
                if train_file and os.path.exists(train_file):
                    os.unlink(train_file)
                if val_file and os.path.exists(val_file):
                    os.unlink(val_file)
                raise
        
        except ImportError as e:
            logger.error(f"Libreria mancante: {e}")
            logger.error("Assicurati di aver installato spacy con 'pip install spacy'")
            raise
        except Exception as e:
            logger.error(f"Errore nell'addestramento del modello: {e}")
            raise
    
    def evaluate_spacy_model(self, model_path: str, test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Valuta un modello spaCy su un set di test.
        
        Args:
            model_path: Percorso al modello spaCy.
            test_data: Dati di test in formato spaCy.
            
        Returns:
            Dizionario con le metriche di valutazione.
        """
        try:
            import spacy
            from spacy.scorer import Scorer
            from spacy.training import Example
            
            logger.info(f"Valutazione del modello {model_path} su {len(test_data)} documenti")
            
            # Carica il modello
            nlp = spacy.load(model_path)
            scorer = Scorer(nlp)
            
            # Prepara gli esempi di test
            examples = []
            for example in test_data:
                doc = nlp.make_doc(example["text"])
                
                # Crea le entità di riferimento
                gold_doc = nlp.make_doc(example["text"])
                ents = []
                for start, end, label in example["entities"]:
                    span = gold_doc.char_span(start, end, label=label)
                    if span is not None:
                        ents.append(span)
                
                gold_doc.ents = ents
                
                # Crea l'esempio
                examples.append(Example(doc, gold_doc))
            
            # Calcola le metriche
            scores = scorer.score(examples)
            
            # Estrai le metriche rilevanti
            metrics = {
                "ents_p": scores["ents_p"],
                "ents_r": scores["ents_r"],
                "ents_f": scores["ents_f"],
                "ents_per_type": scores.get("ents_per_type", {})
            }
            
            return metrics
            
        except ImportError as e:
            logger.error(f"Libreria mancante: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Errore nella valutazione del modello: {e}")
            return {"error": str(e)}
    
    def train_transformer_model(self, annotations_file: str, 
                              base_model: str = "dbmdz/bert-base-italian-xxl-cased",
                              output_model_name: Optional[str] = None,
                              validation_split: float = 0.2) -> str:
        """
        Addestra un modello transformer per NER utilizzando i dati annotati.
        
        Args:
            annotations_file: Percorso al file delle annotazioni in formato JSON.
            base_model: Modello base da utilizzare per il fine-tuning.
            output_model_name: Nome del modello addestrato.
            validation_split: Percentuale di dati da utilizzare per la validazione.
            
        Returns:
            Percorso del modello addestrato.
        """
        try:
            from transformers import (
                AutoTokenizer, 
                AutoModelForTokenClassification,
                Trainer, 
                TrainingArguments,
                DataCollatorForTokenClassification,
                EarlyStoppingCallback,
                set_seed
            )
            from datasets import Dataset, DatasetDict
            import evaluate
            import numpy as np
            
            # Imposta il seed per la riproducibilità
            set_seed(self.config["evaluation"]["random_seed"])
            
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
            label_list = set(["O"])  # Inizializza con "O" per i token non etichettati
            
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
                    
                    # Aggiungi l'etichetta alla lista
                    label_list.add(f"B-{label}")
                    label_list.add(f"I-{label}")
                    
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
            
            # Converti la lista di etichette in una lista ordinata
            label_list = sorted(list(label_list))
            id2label = {i: label for i, label in enumerate(label_list)}
            label2id = {label: i for i, label in enumerate(label_list)}
            
            logger.info(f"Etichette trovate: {label_list}")
            
            # Dividi i dati in set di addestramento e validazione
            if validation_split > 0 and len(train_examples) > 5:
                # Mescola i dati
                import random
                random.seed(self.config["evaluation"]["random_seed"])
                random.shuffle(train_examples)
                
                # Calcola la dimensione del set di validazione
                val_size = max(1, int(len(train_examples) * validation_split))
                
                # Dividi i dati
                val_examples = train_examples[:val_size]
                train_examples = train_examples[val_size:]
                
                logger.info(f"Divisione dei dati in {len(train_examples)} esempi di addestramento e {len(val_examples)} esempi di validazione")
                
                # Crea i dataset
                train_dataset = Dataset.from_list(train_examples)
                val_dataset = Dataset.from_list(val_examples)
                
                # Combina in un DatasetDict
                dataset = DatasetDict({
                    "train": train_dataset,
                    "validation": val_dataset
                })
            else:
                # Usa tutti i dati per l'addestramento
                dataset = Dataset.from_list(train_examples)
                
                # Converti in DatasetDict
                dataset = DatasetDict({
                    "train": dataset
                })
            
            # Funzione di tokenizzazione e allineamento delle etichette
            def tokenize_and_align_labels(examples):
                tokenized_inputs = tokenizer(
                    examples["text"],
                    padding="max_length",
                    truncation=True,
                    max_length=self.config["transformer"]["max_length"],
                    return_offsets_mapping=True
                )
                
                labels = []
                offset_mappings = tokenized_inputs.pop("offset_mapping")
                
                for i, label in enumerate(examples["labels"]):
                    label_ids = []
                    offsets = offset_mappings[i]
                    
                    for j, (start, end) in enumerate(offsets):
                        # Special tokens hanno offset (0, 0), li ignoriamo
                        if start == 0 and end == 0:
                            label_ids.append(-100)
                            continue
                            
                        # Ottieni l'etichetta dei caratteri nelle posizioni start..end
                        if start < len(label) and end <= len(label):
                            # Prendi l'etichetta del primo carattere nell'intervallo
                            char_label = label[start]
                            label_ids.append(label2id.get(char_label, label2id["O"]))
                        else:
                            label_ids.append(-100)  # Ignora questo token
                    
                    labels.append(label_ids)
                
                tokenized_inputs["labels"] = labels
                return tokenized_inputs
            
            # Applica la tokenizzazione
            tokenized_dataset = dataset.map(
                tokenize_and_align_labels,
                batched=True,
                remove_columns=dataset["train"].column_names
            )
            
            # Crea il modello
            model = AutoModelForTokenClassification.from_pretrained(
                base_model,
                num_labels=len(label_list),
                id2label=id2label,
                label2id=label2id
            )
            
            # Configura la metrica di valutazione
            seqeval = evaluate.load("seqeval")
            
            def compute_metrics(eval_preds):
                logits, labels = eval_preds
                predictions = np.argmax(logits, axis=-1)
                
                # Rimuovi gli indici speciali (-100)
                true_labels = [[id2label[l] for l in label if l != -100] for label in labels]
                true_predictions = [
                    [id2label[p] for (p, l) in zip(prediction, label) if l != -100]
                    for prediction, label in zip(predictions, labels)
                ]
                
                results = seqeval.compute(predictions=true_predictions, references=true_labels)
                return {
                    "precision": results["overall_precision"],
                    "recall": results["overall_recall"],
                    "f1": results["overall_f1"],
                    "accuracy": results["overall_accuracy"]
                }
            
            # Configura l'addestramento
            training_args = TrainingArguments(
                output_dir=output_dir,
                learning_rate=self.config["transformer"]["learning_rate"],
                per_device_train_batch_size=self.config["transformer"]["batch_size"],
                per_device_eval_batch_size=self.config["transformer"]["batch_size"],
                num_train_epochs=self.config["transformer"]["epochs"],
                weight_decay=self.config["transformer"]["weight_decay"],
                save_strategy="epoch",
                evaluation_strategy="epoch" if "validation" in tokenized_dataset else "no",
                load_best_model_at_end=True if "validation" in tokenized_dataset else False,
                save_total_limit=2,
                report_to="none",
                warmup_steps=self.config["transformer"]["warmup_steps"],
                seed=self.config["evaluation"]["random_seed"]
            )
            
            # Crea il trainer
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=tokenized_dataset["train"],
                eval_dataset=tokenized_dataset["validation"] if "validation" in tokenized_dataset else None,
                tokenizer=tokenizer,
                data_collator=DataCollatorForTokenClassification(tokenizer),
                compute_metrics=compute_metrics,
                callbacks=[EarlyStoppingCallback(early_stopping_patience=3)] if "validation" in tokenized_dataset else None
            )
            
            # Addestra il modello
            logger.info("Inizio addestramento del modello transformer...")
            trainer.train()
            
            # Salva il modello
            trainer.save_model(output_dir)
            tokenizer.save_pretrained(output_dir)
            
            # Salva le etichette
            with open(os.path.join(output_dir, "labels.json"), "w", encoding="utf-8") as f:
                json.dump({"id2label": id2label, "label2id": label2id}, f, indent=2)
            
            logger.info(f"Addestramento transformer completato. Modello salvato in {output_dir}")
            
            # Valuta il modello
            if "validation" in tokenized_dataset:
                eval_results = trainer.evaluate()
                
                # Salva i risultati della valutazione
                with open(os.path.join(output_dir, "eval_results.json"), "w", encoding="utf-8") as f:
                    json.dump(eval_results, f, indent=2)
                
                logger.info(f"Risultati della valutazione: {eval_results}")
            
            return output_dir
            
        except ImportError as e:
            logger.error(f"Libreria mancante: {e}")
            logger.error("Assicurati di aver installato transformers, datasets e evaluate con "
                      "'pip install transformers datasets evaluate'")
            raise
        except Exception as e:
            logger.error(f"Errore nell'addestramento del modello transformer: {e}")
            raise
    
    def evaluate_transformer_model(self, model_path: str, test_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Valuta un modello transformer su un set di test.
        
        Args:
            model_path: Percorso al modello transformer.
            test_data: Dati di test in formato spaCy o dict con lista di entità.
            
        Returns:
            Dizionario con le metriche di valutazione.
        """
        try:
            from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
            import evaluate
            import numpy as np
            
            logger.info(f"Valutazione del modello transformer {model_path}")
            
            # Carica il modello e il tokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForTokenClassification.from_pretrained(model_path)
            
            # Carica la metrica di valutazione
            seqeval = evaluate.load("seqeval")
            
            # Crea la pipeline NER
            nlp = pipeline("token-classification", model=model, tokenizer=tokenizer, aggregation_strategy="simple")
            
            # Prepara i dati di test
            true_entities = []
            pred_entities = []
            
            for example in tqdm(test_data, desc="Valutazione"):
                text = example["text"]
                gold_entities = example.get("entities", [])
                
                # Normalizza le entità gold
                gold_norm = []
                for entity in gold_entities:
                    if isinstance(entity, tuple):
                        start, end, label = entity
                        gold_norm.append({"start": start, "end": end, "entity_group": label})
                    else:
                        start = entity.get("start_char", 0)
                        end = entity.get("end_char", 0)
                        label = entity.get("type", "UNKNOWN")
                        gold_norm.append({"start": start, "end": end, "entity_group": label})
                
                # Predici le entità
                predictions = nlp(text)
                
                # Normalizza le predizioni
                pred_norm = []
                for pred in predictions:
                    pred_norm.append({
                        "start": pred["start"],
                        "end": pred["end"],
                        "entity_group": pred["entity_group"].replace("B-", "").replace("I-", "")
                    })
                
                # Aggiungi alle liste
                true_entities.append(gold_norm)
                pred_entities.append(pred_norm)
            
            # Calcola le metriche
            tp, fp, fn = 0, 0, 0
            
            for gold, pred in zip(true_entities, pred_entities):
                # Converti gold in formato (start, end, label)
                gold_spans = {(e["start"], e["end"], e["entity_group"]) for e in gold}
                
                # Converti pred in formato (start, end, label)
                pred_spans = {(e["start"], e["end"], e["entity_group"]) for e in pred}
                
                # Calcola TP, FP, FN
                tp += len(gold_spans & pred_spans)
                fp += len(pred_spans - gold_spans)
                fn += len(gold_spans - pred_spans)
            
            # Calcola precision, recall, f1
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            metrics = {
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "tp": tp,
                "fp": fp,
                "fn": fn
            }
            
            # Calcola le metriche per entità
            entity_metrics = {}
            for entity_type in set([e["entity_group"] for gold in true_entities for e in gold]):
                tp_entity, fp_entity, fn_entity = 0, 0, 0
                
                for gold, pred in zip(true_entities, pred_entities):
                    # Filtra le entità per tipo
                    gold_spans = {(e["start"], e["end"]) for e in gold if e["entity_group"] == entity_type}
                    pred_spans = {(e["start"], e["end"]) for e in pred if e["entity_group"] == entity_type}
                    
                    # Calcola TP, FP, FN
                    tp_entity += len(gold_spans & pred_spans)
                    fp_entity += len(pred_spans - gold_spans)
                    fn_entity += len(gold_spans - pred_spans)
                
                # Calcola precision, recall, f1
                precision_entity = tp_entity / (tp_entity + fp_entity) if (tp_entity + fp_entity) > 0 else 0
                recall_entity = tp_entity / (tp_entity + fn_entity) if (tp_entity + fn_entity) > 0 else 0
                f1_entity = 2 * precision_entity * recall_entity / (precision_entity + recall_entity) if (precision_entity + recall_entity) > 0 else 0
                
                entity_metrics[entity_type] = {
                    "precision": precision_entity,
                    "recall": recall_entity,
                    "f1": f1_entity,
                    "tp": tp_entity,
                    "fp": fp_entity,
                    "fn": fn_entity
                }
            
            metrics["per_entity"] = entity_metrics
            
            # Salva le metriche
            metrics_path = os.path.join(model_path, "test_metrics.json")
            with open(metrics_path, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2)
            
            logger.info(f"Valutazione completata: {metrics}")
            
            return metrics
            
        except ImportError as e:
            logger.error(f"Libreria mancante: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Errore nella valutazione del modello transformer: {e}")
            return {"error": str(e)}
    
    def fine_tune_transformer(self, model_path: str, annotations_file: str,
                            output_model_name: Optional[str] = None,
                            validation_split: float = 0.2) -> str:
        """
        Esegue il fine-tuning di un modello transformer esistente.
        
        Args:
            model_path: Percorso al modello da fine-tuning.
            annotations_file: Percorso al file delle annotazioni.
            output_model_name: Nome del modello fine-tuned.
            validation_split: Percentuale di dati da utilizzare per la validazione.
            
        Returns:
            Percorso del modello fine-tuned.
        """
        try:
            from transformers import (
                AutoTokenizer, 
                AutoModelForTokenClassification,
                Trainer, 
                TrainingArguments,
                DataCollatorForTokenClassification,
                EarlyStoppingCallback
            )
            from datasets import Dataset, DatasetDict
            import evaluate
            import numpy as np
            
            logger.info(f"Fine-tuning del modello {model_path} con file {annotations_file}")
            
            # Nome del modello
            output_model_name = output_model_name or f"{os.path.basename(model_path)}_finetuned"
            output_dir = os.path.join(self.model_dir, output_model_name)
            
            # Carica il modello e il tokenizer
            tokenizer = AutoTokenizer.from_pretrained(model_path)
            model = AutoModelForTokenClassification.from_pretrained(model_path)
            
            # Carica le etichette
            labels_path = os.path.join(model_path, "labels.json")
            if os.path.exists(labels_path):
                with open(labels_path, "r", encoding="utf-8") as f:
                    label_data = json.load(f)
                    id2label = {int(k): v for k, v in label_data["id2label"].items()}  # Converti le chiavi in int
                    label2id = label_data["label2id"]
                    label_list = list(label2id.keys())
            else:
                # Usa i label mappings dal modello
                id2label = {i: label for i, label in model.config.id2label.items()}
                label2id = {label: i for i, label in model.config.label2id.items()}
                label_list = list(label2id.keys())
            
            logger.info(f"Etichette caricate: {label_list}")
            
            # Carica le annotazioni
            with open(annotations_file, 'r', encoding='utf-8') as f:
                annotations = json.load(f)
            
            # Prepara i dati come nel metodo train_transformer_model, ma usa le etichette esistenti
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
                    
                    # Verifica che le etichette B-/I- esistano
                    b_label = f"B-{label}"
                    i_label = f"I-{label}"
                    
                    if b_label not in label2id or i_label not in label2id:
                        logger.warning(f"Etichetta {label} non presente nel modello esistente, sarà ignorata")
                        continue
                    
                    # Marca il primo token con B-
                    if start < len(labels):
                        labels[start] = b_label
                    
                    # Marca i token successivi con I-
                    for i in range(start + 1, end):
                        if i < len(labels):
                            labels[i] = i_label
                
                train_examples.append({
                    "text": text,
                    "labels": labels
                })
            
            # Dividi i dati se necessario
            if validation_split > 0 and len(train_examples) > 5:
                train_data, val_data = self._split_data(train_examples, validation_split)
                
                # Crea i dataset
                train_dataset = Dataset.from_list(train_data)
                val_dataset = Dataset.from_list(val_data)
                
                dataset = DatasetDict({
                    "train": train_dataset,
                    "validation": val_dataset
                })
            else:
                dataset = DatasetDict({
                    "train": Dataset.from_list(train_examples)
                })
            
            # Usa la stessa funzione di tokenizzazione di train_transformer_model
            def tokenize_and_align_labels(examples):
                tokenized_inputs = tokenizer(
                    examples["text"],
                    padding="max_length",
                    truncation=True,
                    max_length=self.config["transformer"]["max_length"],
                    return_offsets_mapping=True
                )
                
                labels = []
                offset_mappings = tokenized_inputs.pop("offset_mapping")
                
                for i, label in enumerate(examples["labels"]):
                    label_ids = []
                    offsets = offset_mappings[i]
                    
                    for j, (start, end) in enumerate(offsets):
                        # Special tokens hanno offset (0, 0), li ignoriamo
                        if start == 0 and end == 0:
                            label_ids.append(-100)
                            continue
                            
                        # Ottieni l'etichetta dei caratteri nelle posizioni start..end
                        if start < len(label) and end <= len(label):
                            # Prendi l'etichetta del primo carattere nell'intervallo
                            char_label = label[start]
                            label_ids.append(label2id.get(char_label, label2id["O"]))
                        else:
                            label_ids.append(-100)  # Ignora questo token
                    
                    labels.append(label_ids)
                
                tokenized_inputs["labels"] = labels
                return tokenized_inputs
            
            # Applica la tokenizzazione
            tokenized_dataset = dataset.map(
                tokenize_and_align_labels,
                batched=True,
                remove_columns=dataset["train"].column_names
            )
            
            # Configura la metrica di valutazione come in train_transformer_model
            seqeval = evaluate.load("seqeval")
            
            def compute_metrics(eval_preds):
                logits, labels = eval_preds
                predictions = np.argmax(logits, axis=-1)
                
                # Rimuovi gli indici speciali (-100)
                true_labels = [[id2label[l] for l in label if l != -100] for label in labels]
                true_predictions = [
                    [id2label[p] for (p, l) in zip(prediction, label) if l != -100]
                    for prediction, label in zip(predictions, labels)
                ]
                
                results = seqeval.compute(predictions=true_predictions, references=true_labels)
                return {
                    "precision": results["overall_precision"],
                    "recall": results["overall_recall"],
                    "f1": results["overall_f1"],
                    "accuracy": results["overall_accuracy"]
                }
            
            # Configura l'addestramento con parametri di fine-tuning
            training_args = TrainingArguments(
                output_dir=output_dir,
                learning_rate=self.config["transformer"]["learning_rate"] / 2,  # Learning rate ridotto per fine-tuning
                per_device_train_batch_size=self.config["transformer"]["batch_size"],
                per_device_eval_batch_size=self.config["transformer"]["batch_size"],
                num_train_epochs=self.config["transformer"]["epochs"] / 2,  # Meno epoche per fine-tuning
                weight_decay=self.config["transformer"]["weight_decay"],
                save_strategy="epoch",
                evaluation_strategy="epoch" if "validation" in tokenized_dataset else "no",
                load_best_model_at_end=True if "validation" in tokenized_dataset else False,
                save_total_limit=2,
                report_to="none",
                warmup_steps=self.config["transformer"]["warmup_steps"] // 2,
                seed=self.config["evaluation"]["random_seed"]
            )
            
            # Crea il trainer
            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=tokenized_dataset["train"],
                eval_dataset=tokenized_dataset["validation"] if "validation" in tokenized_dataset else None,
                tokenizer=tokenizer,
                data_collator=DataCollatorForTokenClassification(tokenizer),
                compute_metrics=compute_metrics,
                callbacks=[EarlyStoppingCallback(early_stopping_patience=3)] if "validation" in tokenized_dataset else None
            )
            
            # Addestra il modello
            logger.info("Inizio fine-tuning del modello transformer...")
            trainer.train()
            
            # Salva il modello
            trainer.save_model(output_dir)
            tokenizer.save_pretrained(output_dir)
            
            # Salva le etichette
            with open(os.path.join(output_dir, "labels.json"), "w", encoding="utf-8") as f:
                json.dump({"id2label": id2label, "label2id": label2id}, f, indent=2)
            
            logger.info(f"Fine-tuning completato. Modello salvato in {output_dir}")
            
            # Valuta il modello
            if "validation" in tokenized_dataset:
                eval_results = trainer.evaluate()
                
                # Salva i risultati della valutazione
                with open(os.path.join(output_dir, "eval_results.json"), "w", encoding="utf-8") as f:
                    json.dump(eval_results, f, indent=2)
                
                logger.info(f"Risultati della valutazione: {eval_results}")
            
            return output_dir
            
        except ImportError as e:
            logger.error(f"Libreria mancante: {e}")
            raise
        except Exception as e:
            logger.error(f"Errore nel fine-tuning del modello transformer: {e}")
            raise
    
    def integrate_model_with_ner_system(self, model_path: str, model_type: str = "transformer") -> bool:
        """
        Integra il modello addestrato con il sistema NER.
        
        Args:
            model_path: Percorso al modello addestrato.
            model_type: Tipo di modello ("spacy" o "transformer").
            
        Returns:
            True se l'integrazione è avvenuta con successo, False altrimenti.
        """
        try:
            from pathlib import Path
            import yaml
            import shutil
            
            logger.info(f"Integrazione del modello {model_path} di tipo {model_type} con il sistema NER")
            
            # Trova la directory di configurazione del sistema NER
            base_dir = Path(__file__).resolve().parent.parent.parent
            config_file = base_dir / "config" / "config.yaml"
            
            if not config_file.exists():
                logger.error(f"File di configurazione non trovato: {config_file}")
                return False
            
            # Carica la configurazione
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
            
            # Aggiorna la configurazione
            if model_type == "transformer":
                # Per i modelli transformer, aggiorna il percorso del modello
                config_data["models"]["transformer"]["model_name"] = str(model_path)
                
                # Crea un file di configurazione personalizzato
                with open(base_dir / "config" / "config_custom.yaml", "w", encoding="utf-8") as f:
                    yaml.dump(config_data, f, default_flow_style=False)
                
                logger.info(f"Configurazione aggiornata con il nuovo modello transformer: {model_path}")
                
                # Opzionalmente, copia il modello in una directory standard
                target_dir = base_dir / "models" / "transformer" / Path(model_path).name
                if not target_dir.exists() and Path(model_path) != target_dir:
                    shutil.copytree(model_path, target_dir)
                    logger.info(f"Modello copiato in {target_dir}")
                
                return True
                
            elif model_type == "spacy":
                # Per i modelli spaCy, aggiorna il percorso del modello
                config_data["models"]["spacy"] = config_data.get("models", {}).get("spacy", {})
                config_data["models"]["spacy"]["model_name"] = str(model_path)
                
                # Crea un file di configurazione personalizzato
                with open(base_dir / "config" / "config_custom.yaml", "w", encoding="utf-8") as f:
                    yaml.dump(config_data, f, default_flow_style=False)
                
                logger.info(f"Configurazione aggiornata con il nuovo modello spaCy: {model_path}")
                
                # Opzionalmente, crea un symlink per rendere il modello disponibile al sistema
                import os
                target_dir = base_dir / "models" / "spacy" / Path(model_path).name
                if not target_dir.exists() and Path(model_path) != target_dir:
                    # Crea la directory parent se non esiste
                    target_dir.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Crea il symlink o copia il modello
                    try:
                        os.symlink(model_path, target_dir, target_is_directory=True)
                        logger.info(f"Symlink creato: {target_dir} -> {model_path}")
                    except (OSError, NotImplementedError):
                        # Fallback: copia il modello
                        shutil.copytree(model_path, target_dir)
                        logger.info(f"Modello copiato in {target_dir}")
                
                return True
            
            logger.error(f"Tipo di modello non supportato: {model_type}")
            return False
        
        except ImportError as e:
            logger.error(f"Libreria mancante: {e}")
            return False
        except Exception as e:
            logger.error(f"Errore nell'integrazione del modello: {e}")
            return False
    
    def _split_data(self, data: List[Dict[str, Any]], validation_split: float = 0.2) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Divide i dati in set di addestramento e validazione.
        
        Args:
            data: Dati da dividere.
            validation_split: Percentuale di dati da utilizzare per la validazione.
            
        Returns:
            Tupla con (dati_addestramento, dati_validazione).
        """
        import random
        
        # Imposta il seed per la riproducibilità
        random.seed(self.config["evaluation"]["random_seed"])
        
        # Copia i dati
        data_copy = data.copy()
        
        # Mescola i dati
        random.shuffle(data_copy)
        
        # Calcola la dimensione del set di validazione
        val_size = max(1, int(len(data_copy) * validation_split))
        
        # Dividi i dati
        val_data = data_copy[:val_size]
        train_data = data_copy[val_size:]
        
        return train_data, val_data
    
    def export_model(self, model_path: str, output_dir: str, model_type: str = "transformer", 
                   compress: bool = True) -> Optional[str]:
        """
        Esporta un modello addestrato in un formato portatile.
        
        Args:
            model_path: Percorso al modello da esportare.
            output_dir: Directory di output per il modello esportato.
            model_type: Tipo di modello ("spacy" o "transformer").
            compress: Se True, crea un archivio compresso.
            
        Returns:
            Percorso del modello esportato, o None in caso di errore.
        """
        try:
            import shutil
            from pathlib import Path
            
            logger.info(f"Esportazione del modello {model_path} di tipo {model_type}")
            
            # Crea la directory di output
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Nome dell'archivio
            model_name = Path(model_path).name
            archive_name = f"{model_name}_export"
            
            # Directory temporanea per preparare i file
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                model_export_dir = temp_path / model_name
                
                # Copia il modello nella directory temporanea
                shutil.copytree(model_path, model_export_dir)
                
                # Aggiungi metadati
                with open(model_export_dir / "metadata.json", "w", encoding="utf-8") as f:
                    metadata = {
                        "model_name": model_name,
                        "model_type": model_type,
                        "export_date": str(datetime.datetime.now()),
                        "version": "1.0.0",
                        "description": f"Modello {model_type} esportato da NER-Giuridico"
                    }
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                # Crea l'archivio compresso se richiesto
                if compress:
                    archive_path = output_path / f"{archive_name}.zip"
                    shutil.make_archive(
                        str(output_path / archive_name), 
                        'zip', 
                        root_dir=temp_dir,
                        base_dir=model_name
                    )
                    logger.info(f"Modello esportato e compresso in {archive_path}")
                    return str(archive_path)
                else:
                    # Copia la directory
                    final_path = output_path / model_name
                    if final_path.exists():
                        shutil.rmtree(final_path)
                    shutil.copytree(model_export_dir, final_path)
                    logger.info(f"Modello esportato in {final_path}")
                    return str(final_path)
                
        except Exception as e:
            logger.error(f"Errore nell'esportazione del modello: {e}")
            return None
    
    def import_model(self, model_path: str, target_dir: Optional[str] = None, 
                    model_type: Optional[str] = None) -> Optional[str]:
        """
        Importa un modello precedentemente esportato.
        
        Args:
            model_path: Percorso al modello da importare (file o directory).
            target_dir: Directory di destinazione per il modello importato.
            model_type: Tipo di modello ("spacy" o "transformer").
            
        Returns:
            Percorso del modello importato, o None in caso di errore.
        """
        try:
            import shutil
            import zipfile
            from pathlib import Path
            
            logger.info(f"Importazione del modello {model_path}")
            
            # Determina se il modello è un archivio
            path = Path(model_path)
            is_archive = path.suffix.lower() == ".zip"
            
            # Directory di destinazione
            if target_dir is None:
                # Usa la directory dei modelli predefinita in base al tipo
                base_dir = Path(__file__).resolve().parent.parent.parent
                if model_type == "spacy":
                    target_dir = base_dir / "models" / "spacy"
                elif model_type == "transformer":
                    target_dir = base_dir / "models" / "transformer"
                else:
                    target_dir = base_dir / "models" / "imported"
            else:
                target_dir = Path(target_dir)
            
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Estrai o copia il modello
            if is_archive:
                # Estrai l'archivio
                with tempfile.TemporaryDirectory() as temp_dir:
                    with zipfile.ZipFile(path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    # Trova la directory del modello
                    temp_path = Path(temp_dir)
                    model_dirs = [d for d in temp_path.iterdir() if d.is_dir()]
                    
                    if not model_dirs:
                        logger.error("Nessuna directory trovata nell'archivio")
                        return None
                    
                    model_dir = model_dirs[0]
                    
                    # Leggi i metadati, se presenti
                    metadata_file = model_dir / "metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                            
                            # Usa il tipo di modello dai metadati se non specificato
                            if model_type is None and "model_type" in metadata:
                                model_type = metadata["model_type"]
                    
                    # Determina il nome del modello
                    model_name = model_dir.name
                    final_path = target_dir / model_name
                    
                    # Rimuovi la directory di destinazione se esiste
                    if final_path.exists():
                        shutil.rmtree(final_path)
                    
                    # Copia il modello
                    shutil.copytree(model_dir, final_path)
            else:
                # Copia la directory
                model_name = path.name
                final_path = target_dir / model_name
                
                # Rimuovi la directory di destinazione se esiste
                if final_path.exists():
                    shutil.rmtree(final_path)
                
                # Copia il modello
                shutil.copytree(path, final_path)
            
            logger.info(f"Modello importato in {final_path}")
            
            # Integra il modello con il sistema NER se è specificato il tipo
            if model_type in ["spacy", "transformer"]:
                success = self.integrate_model_with_ner_system(str(final_path), model_type)
                if success:
                    logger.info(f"Modello {model_type} integrato con il sistema NER")
                else:
                    logger.warning(f"Impossibile integrare il modello {model_type} con il sistema NER")
            
            return str(final_path)
            
        except Exception as e:
            logger.error(f"Errore nell'importazione del modello: {e}")
            return None


def train_from_annotations(annotations_file: str, output_dir: Optional[str] = None, 
                          model_type: str = "transformer", base_model: Optional[str] = None) -> Dict[str, Any]:
    """
    Funzione di utilità per addestrare un modello NER dalle annotazioni.
    
    Args:
        annotations_file: Percorso al file delle annotazioni.
        output_dir: Directory di output per il modello addestrato.
        model_type: Tipo di modello da addestrare ("spacy" o "transformer").
        base_model: Modello base da utilizzare per il fine-tuning (solo per transformer).
        
    Returns:
        Dizionario con i risultati dell'addestramento.
    """
    try:
        # Importa librerie necessarie
        import datetime
        
        # Inizializza il trainer
        trainer = NERTrainer(output_dir)
        
        # Carica le annotazioni
        with open(annotations_file, 'r', encoding='utf-8') as f:
            annotations = json.load(f)
        
        logger.info(f"Addestramento di tipo {model_type} con {len(annotations)} documenti")
        
        # Timestamp per il nome del modello
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Determina il tipo di dati e addestra il modello appropriato
        if model_type == "spacy":
            # Determina se è nel formato spaCy
            is_spacy_format = False
            if annotations and isinstance(annotations, list):
                first_item = annotations[0]
                if "text" in first_item and "entities" in first_item:
                    # Controlla se entities è una lista di tuple (spaCy) o di dict (NER)
                    if first_item["entities"] and isinstance(first_item["entities"][0], tuple):
                        is_spacy_format = True
            
            if is_spacy_format:
                # Addestra con i dati spaCy
                model_path = trainer.train_from_spacy_format(
                    annotations, 
                    output_model_name=f"ner_spacy_{timestamp}"
                )
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
                        else:
                            entities.append(entity)  # Già una tupla
                    
                    spacy_data.append({
                        "text": text,
                        "entities": entities
                    })
                
                model_path = trainer.train_from_spacy_format(
                    spacy_data, 
                    output_model_name=f"ner_spacy_{timestamp}"
                )
        
        elif model_type == "transformer":
            # Se è una lista, lo convertiamo in un file temporaneo
            if isinstance(annotations, list):
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(annotations, f, ensure_ascii=False)
                    temp_file = f.name
                
                try:
                    # Usa il modello base specificato o quello predefinito
                    model_base = base_model or "dbmdz/bert-base-italian-xxl-cased"
                    
                    # Addestra il modello transformer
                    model_path = trainer.train_transformer_model(
                        temp_file,
                        base_model=model_base,
                        output_model_name=f"ner_transformer_{timestamp}"
                    )
                finally:
                    # Rimuovi il file temporaneo
                    os.unlink(temp_file)
            else:
                # Usa il file direttamente
                model_base = base_model or "dbmdz/bert-base-italian-xxl-cased"
                
                # Addestra il modello transformer
                model_path = trainer.train_transformer_model(
                    annotations_file,
                    base_model=model_base,
                    output_model_name=f"ner_transformer_{timestamp}"
                )
        else:
            logger.error(f"Tipo di modello non supportato: {model_type}")
            return {
                "success": False,
                "error": f"Tipo di modello non supportato: {model_type}"
            }
        
        # Integra il modello con il sistema NER
        integration_success = trainer.integrate_model_with_ner_system(model_path, model_type)
        
        return {
            "success": True,
            "model_path": model_path,
            "model_type": model_type,
            "integration_success": integration_success
        }
        
    except Exception as e:
        logger.error(f"Errore nell'addestramento: {e}")
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import datetime
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Train a NER model from annotated data')
    parser.add_argument('--annotations', type=str, required=True, help='Path to annotations file')
    parser.add_argument('--output-dir', type=str, help='Output directory for the model')
    parser.add_argument('--model-type', type=str, choices=['spacy', 'transformer'], default='transformer',
                      help='Type of model to train')
    parser.add_argument('--base-model', type=str, help='Base model for transformer (optional)')
    
    args = parser.parse_args()
    
    # Train the model
    result = train_from_annotations(
        annotations_file=args.annotations,
        output_dir=args.output_dir,
        model_type=args.model_type,
        base_model=args.base_model
    )
    
    # Print the result
    if result["success"]:
        print(f"Training successful! Model saved at: {result['model_path']}")
        print(f"Integration with NER system: {'Success' if result['integration_success'] else 'Failed'}")
    else:
        print(f"Training failed: {result.get('error', 'Unknown error')}")