"""
Script principale per l'avvio del sistema NER-Giuridico.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Aggiungi la directory del progetto al path
project_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(project_dir))

from src.config import config
from src.api import start_server
from src.annotation import AnnotationInterface
from src.ner import NERGiuridico

# Configurazione del logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(project_dir, 'ner_giuridico.log'))
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Funzione principale per l'avvio del sistema NER-Giuridico."""
    parser = argparse.ArgumentParser(description='NER-Giuridico: Sistema di riconoscimento di entità giuridiche')
    
    # Definizione dei comandi
    subparsers = parser.add_subparsers(dest='command', help='Comando da eseguire')
    
    # Comando 'server'
    server_parser = subparsers.add_parser('server', help='Avvia il server API')
    server_parser.add_argument('--host', type=str, help='Host del server')
    server_parser.add_argument('--port', type=int, help='Porta del server')
    
    # Comando 'annotate'
    annotate_parser = subparsers.add_parser('annotate', help='Avvia l\'interfaccia di annotazione')
    annotate_parser.add_argument('--tool', type=str, choices=['label-studio', 'doccano', 'prodigy', 'custom'],
                               help='Strumento di annotazione da utilizzare')
    
    # Comando 'process'
    process_parser = subparsers.add_parser('process', help='Processa un testo')
    process_parser.add_argument('--text', type=str, help='Testo da processare')
    process_parser.add_argument('--file', type=str, help='File contenente il testo da processare')
    process_parser.add_argument('--output', type=str, help='File di output per i risultati')
    
    # Comando 'batch'
    batch_parser = subparsers.add_parser('batch', help='Processa un batch di testi')
    batch_parser.add_argument('--dir', type=str, required=True, help='Directory contenente i file da processare')
    batch_parser.add_argument('--output', type=str, required=True, help='Directory di output per i risultati')
    batch_parser.add_argument('--ext', type=str, default='txt', help='Estensione dei file da processare')
    
    # Comando 'convert'
    convert_parser = subparsers.add_parser('convert', help='Converti dati annotati da un formato all\'altro')
    convert_parser.add_argument('--input', type=str, required=True, help='File di input')
    convert_parser.add_argument('--output', type=str, required=True, help='File di output')
    convert_parser.add_argument('--input-format', type=str, required=True, choices=['json', 'jsonl'],
                              help='Formato del file di input')
    convert_parser.add_argument('--output-format', type=str, required=True, choices=['spacy', 'conll'],
                              help='Formato del file di output')
    
    # Parsing degli argomenti
    args = parser.parse_args()
    
    # Esecuzione del comando specificato
    if args.command == 'server':
        # Aggiorna la configurazione se sono stati specificati host e porta
        if args.host:
            config.set('api.host', args.host)
        if args.port:
            config.set('api.port', args.port)
        
        logger.info("Avvio del server API NER-Giuridico")
        start_server()
    
    elif args.command == 'annotate':
        # Aggiorna la configurazione se è stato specificato lo strumento
        if args.tool:
            config.set('annotation.tool', args.tool)
        
        logger.info(f"Configurazione dell'interfaccia di annotazione con lo strumento {config.get('annotation.tool')}")
        annotation_interface = AnnotationInterface()
        annotation_interface.setup()
        logger.info("Configurazione dell'interfaccia di annotazione completata")
    
    elif args.command == 'process':
        if not args.text and not args.file:
            parser.error("È necessario specificare --text o --file")
        
        # Inizializza il sistema NER
        ner = NERGiuridico()
        
        # Processa il testo
        if args.text:
            logger.info("Elaborazione del testo fornito")
            result = ner.process(args.text)
        else:
            logger.info(f"Elaborazione del testo dal file {args.file}")
            with open(args.file, 'r', encoding='utf-8') as f:
                text = f.read()
            result = ner.process(text)
        
        # Salva o stampa i risultati
        if args.output:
            import json
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            logger.info(f"Risultati salvati in {args.output}")
        else:
            import json
            print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == 'batch':
        import json
        import glob
        import os
        
        # Verifica che la directory di input esista
        if not os.path.isdir(args.dir):
            parser.error(f"La directory {args.dir} non esiste")
        
        # Crea la directory di output se non esiste
        os.makedirs(args.output, exist_ok=True)
        
        # Inizializza il sistema NER
        ner = NERGiuridico()
        
        # Trova tutti i file con l'estensione specificata
        files = glob.glob(os.path.join(args.dir, f"*.{args.ext}"))
        logger.info(f"Trovati {len(files)} file da processare")
        
        # Processa ogni file
        for file_path in files:
            file_name = os.path.basename(file_path)
            logger.info(f"Elaborazione del file {file_name}")
            
            # Leggi il testo dal file
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Processa il testo
            result = ner.process(text)
            
            # Salva i risultati
            output_file = os.path.join(args.output, f"{os.path.splitext(file_name)[0]}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Risultati salvati in {output_file}")
        
        logger.info(f"Elaborazione batch completata. Risultati salvati in {args.output}")
    
    elif args.command == 'convert':
        logger.info(f"Conversione dei dati da {args.input_format} a {args.output_format}")
        annotation_interface = AnnotationInterface()
        annotation_interface.convert_data(args.input, args.output, args.input_format, args.output_format)
        logger.info(f"Conversione completata. Risultati salvati in {args.output}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
