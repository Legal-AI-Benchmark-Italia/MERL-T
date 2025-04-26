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
            output_folder: Cartella di output principale
        """
        # Salva il percorso assoluto per coerenza
        self.output_folder = os.path.abspath(output_folder)
        self.logger = logging.getLogger("PDFChunker.OutputManager")
        
        # Crea la cartella di output principale se non esiste
        os.makedirs(self.output_folder, exist_ok=True)
    
    def save_chunks(self, chunks: List[Dict], relative_output_prefix: str) -> bool:
        """
        Salva i chunk in vari formati utili, rispettando la struttura delle cartelle.
        
        Args:
            chunks: Lista di dizionari rappresentanti i chunk
            relative_output_prefix: Percorso relativo del PDF originale rispetto alla
                                   cartella di input, senza estensione (es. 'subdir/doc')
            
        Returns:
            True se il salvataggio è andato a buon fine, False altrimenti
        """
        try:
            # Modifica: Usa relative_output_prefix per creare la struttura di directory completa
            pdf_output_dir = os.path.join(self.output_folder, relative_output_prefix)
            # Crea tutte le directory intermedie necessarie
            os.makedirs(pdf_output_dir, exist_ok=True)
            
            # Modifica: Estrai il nome base del file per i nomi dei file di output
            base_filename = os.path.basename(relative_output_prefix)
            
            # Salva i chunk in formato JSON
            json_path = os.path.join(pdf_output_dir, f"{base_filename}_chunks.json")
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
                    # Modifica: Usa base_filename per il nome del documento
                    chunk_with_metadata['document'] = base_filename 
                    # Modifica: Usa il percorso relativo corretto
                    chunk_with_metadata['source_path'] = relative_output_prefix 
                    json.dump(chunk_with_metadata, f, ensure_ascii=False, indent=2)
            
            # Crea un file jsonl (una riga JSON per chunk)
            jsonl_path = os.path.join(pdf_output_dir, f"{base_filename}_chunks.jsonl")
            with open(jsonl_path, 'w', encoding='utf-8') as f:
                for chunk in chunks:
                    chunk_with_metadata = chunk.copy()
                    # Modifica: Usa base_filename per il nome del documento
                    chunk_with_metadata['document'] = base_filename
                    # Modifica: Aggiungi il percorso relativo come metadato
                    chunk_with_metadata['relative_path'] = relative_output_prefix 
                    f.write(json.dumps(chunk_with_metadata, ensure_ascii=False) + '\n')
            
            # Crea un file CSV con i metadati dei chunk
            csv_path = os.path.join(pdf_output_dir, f"{base_filename}_chunks_metadata.csv")
            with open(csv_path, 'w', encoding='utf-8') as f:
                # Intestazione CSV
                # Modifica: Aggiunto relative_path all'intestazione
                f.write("chunk_id,tokens,chars,index,document,relative_path\n")
                
                # Righe dati
                for chunk in chunks:
                    # Modifica: Aggiunto relative_output_prefix al CSV
                    f.write(f"{chunk['chunk_id']},{chunk['tokens']},{chunk['chars']},{chunk['index']},{base_filename},{relative_output_prefix}\n")
            
            self.logger.info(f"Chunk salvati in {pdf_output_dir}")
            self.logger.info(f"  - JSON: {os.path.basename(json_path)}")
            self.logger.info(f"  - JSONL: {os.path.basename(jsonl_path)}")
            self.logger.info(f"  - JSON individuali: {os.path.basename(json_chunks_dir)}")
            self.logger.info(f"  - CSV metadata: {os.path.basename(csv_path)}")
            self.logger.info(f"  - Testo: {os.path.basename(chunks_dir)}")
            
            return True
            
        except Exception as e:
            # Modifica: Usa relative_output_prefix nel messaggio di errore
            self.logger.error(f"Errore nel salvataggio dei chunk per {relative_output_prefix}: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False
    
    def cleanup_partial_output(self, relative_output_prefix: str) -> bool:
        """
        Rimuove l'output parziale per un PDF, usando il percorso relativo.
        
        Args:
            relative_output_prefix: Percorso relativo del PDF (senza estensione)
            
        Returns:
            True se la pulizia è andata a buon fine, False altrimenti
        """
        try:
            # Modifica: Usa relative_output_prefix per trovare la cartella
            pdf_output_dir = os.path.join(self.output_folder, relative_output_prefix)
            if os.path.exists(pdf_output_dir):
                self.logger.info(f"Rimozione dell'elaborazione parziale precedente per {relative_output_prefix}")
                # Usa shutil.rmtree per rimuovere la cartella e il suo contenuto
                shutil.rmtree(pdf_output_dir)
            return True
        except Exception as e:
            # Modifica: Usa relative_output_prefix nel messaggio di errore
            self.logger.error(f"Errore nella pulizia dell'output per {relative_output_prefix}: {str(e)}")
            return False
    
    def create_combined_outputs(self) -> bool:
        """
        Crea file combinati (JSONL e metadati JSON) attraversando ricorsivamente
        la struttura di output.
        
        Returns:
            True se la creazione è andata a buon fine, False altrimenti
        """
        try:
            # Crea un unico file JSONL con tutti i chunk di tutti i PDF
            combined_jsonl_path = os.path.join(self.output_folder, "all_chunks.jsonl")
            self.logger.info(f"Creazione file combinato di tutti i chunk: {combined_jsonl_path}")
            
            # Crea un dizionario JSON con i metadati di tutti i documenti elaborati
            documents_metadata = {
                "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_documents": 0,
                "documents": []
            }
            
            total_chunks_combined = 0
            
            # Modifica: Usa os.walk per attraversare ricorsivamente la cartella di output
            with open(combined_jsonl_path, 'w', encoding='utf-8') as combined_file:
                for dirpath, dirnames, filenames in os.walk(self.output_folder):
                    # Cerca file _chunks.jsonl e _chunks_metadata.csv nella directory corrente
                    jsonl_file = None
                    csv_file = None
                    base_filename = os.path.basename(dirpath)
                    
                    for filename in filenames:
                        if filename.endswith("_chunks.jsonl") and filename.startswith(base_filename):
                            jsonl_file = os.path.join(dirpath, filename)
                        elif filename.endswith("_chunks_metadata.csv") and filename.startswith(base_filename):
                            csv_file = os.path.join(dirpath, filename)
                    
                    # Se abbiamo trovato entrambi i file, processiamo questo documento
                    if jsonl_file and csv_file:
                        relative_output_prefix = os.path.relpath(dirpath, self.output_folder)
                        self.logger.debug(f"Trovato documento processato in: {relative_output_prefix}")
                        
                        # 1. Aggiungi chunk al file JSONL combinato
                        try:
                            with open(jsonl_file, 'r', encoding='utf-8') as input_file:
                                lines_copied = 0
                                for line in input_file:
                                    combined_file.write(line)
                                    lines_copied += 1
                                total_chunks_combined += lines_copied
                        except Exception as e:
                            self.logger.error(f"Errore nella lettura di {jsonl_file}: {str(e)}")
                            continue # Salta al prossimo documento

                        # 2. Aggiungi metadati al dizionario combinato
                        try:
                            # Leggi il CSV per ottenere il numero di chunk (o usa lines_copied)
                            chunk_count = lines_copied 
                            
                            doc_meta = {
                                # Modifica: Usa relative_output_prefix come identificativo
                                "document_id": relative_output_prefix,
                                "base_name": base_filename,
                                "chunks": chunk_count,
                                "output_directory": dirpath # Usa il percorso assoluto
                            }
                            documents_metadata["documents"].append(doc_meta)
                            documents_metadata["total_documents"] += 1
                        except Exception as e:
                            self.logger.error(f"Errore nella lettura dei metadati per {relative_output_prefix} da {csv_file}: {str(e)}")
            
            self.logger.info(f"File combinato creato: {combined_jsonl_path} ({total_chunks_combined} chunk totali)")
            
            # Salva il dizionario dei metadati
            metadata_path = os.path.join(self.output_folder, "documents_metadata.json")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(documents_metadata, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"File dei metadati creato: {metadata_path} ({documents_metadata['total_documents']} documenti)")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Errore nella creazione dei file combinati: {str(e)}")
            self.logger.error(traceback.format_exc())
            return False