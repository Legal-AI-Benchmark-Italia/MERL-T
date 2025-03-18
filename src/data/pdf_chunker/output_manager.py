#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulo per la gestione dell'output dell'elaborazione.
"""

import os
import json
import shutil
import logging
import traceback
from typing import List, Dict
from datetime import datetime

class OutputManager:
    """
    Classe per la gestione degli output dell'elaborazione dei PDF.
    """
    
    def __init__(self, output_folder: str):
        """
        Inizializza il gestore di output.
        
        Args:
            output_folder: Cartella di output
        """
        self.output_folder = output_folder
        self.logger = logging.getLogger("PDFChunker.OutputManager")
        
        # Crea la cartella di output se non esiste
        os.makedirs(output_folder, exist_ok=True)
    
    def save_chunks(self, chunks: List[Dict], pdf_name: str) -> bool:
        """
        Salva i chunk in vari formati utili.
        
        Args:
            chunks: Lista di dizionari rappresentanti i chunk
            pdf_name: Nome del PDF originale (senza estensione)
            
        Returns:
            True se il salvataggio è andato a buon fine, False altrimenti
        """
        try:
            # Crea una sottocartella specifica per questo PDF
            pdf_output_dir = os.path.join(self.output_folder, pdf_name)
            os.makedirs(pdf_output_dir, exist_ok=True)
            
            # Salva i chunk in formato JSON
            json_path = os.path.join(pdf_output_dir, f"{pdf_name}_chunks.json")
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)
            
            # Salva ogni chunk come file di testo separato
            chunks_dir = os.path.join(pdf_output_dir, "chunks")
            os.makedirs(chunks_dir, exist_ok=True)
            
            # Salva ogni chunk anche come file JSON individuale
            json_chunks_dir = os.path.join(pdf_output_dir, "json_chunks")
            os.makedirs(json_chunks_dir, exist_ok=True)
            
            for chunk in chunks:
                # Salva come file di testo
                chunk_path = os.path.join(chunks_dir, f"{chunk['chunk_id']}.txt")
                with open(chunk_path, 'w', encoding='utf-8') as f:
                    f.write(chunk['text'])
                    
                # Salva come file JSON individuale
                json_chunk_path = os.path.join(json_chunks_dir, f"{chunk['chunk_id']}.json")
                with open(json_chunk_path, 'w', encoding='utf-8') as f:
                    # Aggiungi informazioni sul documento di origine
                    chunk_with_metadata = chunk.copy()
                    chunk_with_metadata['document'] = pdf_name
                    chunk_with_metadata['source_path'] = os.path.join(self.output_folder, pdf_name)
                    json.dump(chunk_with_metadata, f, ensure_ascii=False, indent=2)
            
            # Crea un file jsonl (una riga JSON per chunk)
            jsonl_path = os.path.join(pdf_output_dir, f"{pdf_name}_chunks.jsonl")
            with open(jsonl_path, 'w', encoding='utf-8') as f:
                for chunk in chunks:
                    chunk_with_metadata = chunk.copy()
                    chunk_with_metadata['document'] = pdf_name
                    f.write(json.dumps(chunk_with_metadata, ensure_ascii=False) + '\n')
            
            # Crea un file CSV con i metadati dei chunk
            csv_path = os.path.join(pdf_output_dir, f"{pdf_name}_chunks_metadata.csv")
            with open(csv_path, 'w', encoding='utf-8') as f:
                # Intestazione CSV
                f.write("chunk_id,tokens,chars,index,document\n")
                
                # Righe dati
                for chunk in chunks:
                    f.write(f"{chunk['chunk_id']},{chunk['tokens']},{chunk['chars']},{chunk['index']},{pdf_name}\n")
            
            self.logger.info(f"Chunk salvati in {pdf_output_dir}")
            self.logger.info(f"  - JSON: {json_path}")
            self.logger.info(f"  - JSONL: {jsonl_path}")
            self.logger.info(f"  - JSON individuali: {json_chunks_dir}")
            self.logger.info(f"  - CSV metadata: {csv_path}")
            self.logger.info(f"  - Testo: {chunks_dir}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Errore nel salvataggio dei chunk per {pdf_name}: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def cleanup_partial_output(self, pdf_name: str) -> bool:
        """
        Rimuove l'output parziale per un PDF.
        
        Args:
            pdf_name: Nome del PDF
            
        Returns:
            True se la pulizia è andata a buon fine, False altrimenti
        """
        try:
            pdf_output_dir = os.path.join(self.output_folder, pdf_name)
            if os.path.exists(pdf_output_dir):
                self.logger.info(f"Rimozione dell'elaborazione parziale precedente per {pdf_name}")
                shutil.rmtree(pdf_output_dir)
            return True
        except Exception as e:
            self.logger.error(f"Errore nella pulizia dell'output per {pdf_name}: {str(e)}")
            return False
    
    def create_combined_outputs(self) -> bool:
        """
        Crea file combinati con tutti i chunk e metadati dei documenti.
        
        Returns:
            True se la creazione è andata a buon fine, False altrimenti
        """
        try:
            # Crea un unico file JSONL con tutti i chunk di tutti i PDF
            combined_jsonl_path = os.path.join(self.output_folder, "all_chunks.jsonl")
            self.logger.info(f"Creazione file combinato di tutti i chunk: {combined_jsonl_path}")
            
            with open(combined_jsonl_path, 'w', encoding='utf-8') as combined_file:
                # Cerca tutti i file JSONL nella cartella di output
                for pdf_dir in [d for d in os.listdir(self.output_folder) if os.path.isdir(os.path.join(self.output_folder, d))]:
                    pdf_dir_path = os.path.join(self.output_folder, pdf_dir)
                    for file in os.listdir(pdf_dir_path):
                        if file.endswith("_chunks.jsonl"):
                            jsonl_path = os.path.join(pdf_dir_path, file)
                            try:
                                # Leggi il file JSONL e aggiungi ogni riga al file combinato
                                with open(jsonl_path, 'r', encoding='utf-8') as input_file:
                                    for line in input_file:
                                        combined_file.write(line)
                            except Exception as e:
                                self.logger.error(f"Errore nella lettura di {jsonl_path}: {str(e)}")
            
            self.logger.info(f"File combinato creato: {combined_jsonl_path}")
            
            # Crea un dizionario JSON con i metadati di tutti i documenti elaborati
            documents_metadata = {
                "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_documents": 0,
                "documents": []
            }
            
            # Aggiungi metadati per ogni documento
            for pdf_dir in [d for d in os.listdir(self.output_folder) if os.path.isdir(os.path.join(self.output_folder, d))]:
                pdf_dir_path = os.path.join(self.output_folder, pdf_dir)
                metadata_path = os.path.join(pdf_dir_path, f"{pdf_dir}_chunks_metadata.csv")
                
                if os.path.exists(metadata_path):
                    try:
                        # Leggi il CSV per ottenere il numero di chunk
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            next(f)  # Salta l'intestazione
                            chunk_count = sum(1 for _ in f)
                        
                        # Aggiungi metadati del documento
                        doc_meta = {
                            "document_name": pdf_dir,
                            "chunks": chunk_count,
                            "output_directory": pdf_dir_path
                        }
                        documents_metadata["documents"].append(doc_meta)
                        documents_metadata["total_documents"] += 1
                    except Exception as e:
                        self.logger.error(f"Errore nella lettura dei metadati per {pdf_dir}: {str(e)}")
            
            # Salva il dizionario dei metadati
            metadata_path = os.path.join(self.output_folder, "documents_metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(documents_metadata, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"File dei metadati creato: {metadata_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Errore nella creazione dei file combinati: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False