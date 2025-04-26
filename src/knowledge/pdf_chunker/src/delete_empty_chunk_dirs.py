import json
import os
import shutil

METADATA_FILE = "src/knowledge/knowledge_base/dottrina/raw_text/documents_metadata.json"

def delete_directories_with_zero_chunks(metadata_path):
    """
    Legge un file JSON di metadati, identifica i documenti con 0 chunk
    e elimina le directory associate.
    """
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
    except FileNotFoundError:
        print(f"Errore: File non trovato: {metadata_path}")
        return
    except json.JSONDecodeError:
        print(f"Errore: Formato JSON non valido in: {metadata_path}")
        return

    if 'documents' not in metadata:
        print(f"Errore: Chiave 'documents' non trovata nel file JSON.")
        return

    deleted_count = 0
    skipped_count = 0

    for doc in metadata['documents']:
        try:
            chunks = doc.get('chunks')
            output_dir = doc.get('output_directory')

            if chunks == 0 and output_dir:
                if os.path.exists(output_dir):
                    if os.path.isdir(output_dir):
                        print(f"Eliminazione della directory: {output_dir}")
                        try:
                            shutil.rmtree(output_dir)
                            deleted_count += 1
                        except OSError as e:
                            print(f"Errore durante l'eliminazione di {output_dir}: {e}")
                            skipped_count += 1
                    else:
                         print(f"Skipping: {output_dir} non è una directory.")
                         skipped_count += 1
                else:
                    print(f"Skipping: La directory {output_dir} non esiste.")
                    skipped_count += 1
            elif chunks is None:
                 print(f"Skipping: Documento con ID {doc.get('document_id', 'N/A')} non ha la chiave 'chunks'.")
                 skipped_count += 1
            elif output_dir is None:
                 print(f"Skipping: Documento con ID {doc.get('document_id', 'N/A')} non ha la chiave 'output_directory'.")
                 skipped_count += 1

        except Exception as e:
            print(f"Errore nell'elaborazione del documento {doc.get('document_id', 'N/A')}: {e}")
            skipped_count += 1


    print(f"Operazione completata.")
    print(f"Directory eliminate: {deleted_count}")
    print(f"Directory saltate (non trovate, non directory, errori o chunk != 0): {skipped_count + (len(metadata['documents']) - deleted_count - skipped_count)}")


if __name__ == "__main__":
    delete_directories_with_zero_chunks(METADATA_FILE) 