"""
Test unitari per il modulo di annotazione.
Esegui con: python -m unittest test_annotator.py
"""

import os
import sys
import json
import shutil
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Assicurati che la directory parent sia nel path
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Import dei moduli da testare
from ner_giuridico.annotation.app import app

class TestAnnotatorApp(unittest.TestCase):
    """Test per l'app Flask di annotazione."""
    
    def setUp(self):
        """Configura l'ambiente di test."""
        # Crea una directory temporanea per i dati di test
        self.test_dir = tempfile.mkdtemp()
        
        # Configura l'app Flask per i test
        app.config['TESTING'] = True
        app.config['DATA_DIR'] = self.test_dir
        self.client = app.test_client()
        
        # Crea file di documenti e annotazioni di test
        self.documents_file = os.path.join(self.test_dir, 'documents.json')
        self.annotations_file = os.path.join(self.test_dir, 'annotations.json')
        
        # Inizializza i file con dati di test
        self.test_documents = [
            {
                "id": "doc_1",
                "title": "Documento di test",
                "text": "Questo è un documento di test per l'annotator."
            }
        ]
        
        self.test_annotations = {
            "doc_1": [
                {
                    "id": "ann_1",
                    "start": 0,
                    "end": 6,
                    "text": "Questo",
                    "type": "CONCETTO_GIURIDICO"
                }
            ]
        }
        
        with open(self.documents_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_documents, f)
            
        with open(self.annotations_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_annotations, f)
    
    def tearDown(self):
        """Pulisce l'ambiente dopo i test."""
        # Rimuovi la directory temporanea
        shutil.rmtree(self.test_dir)
    
    def test_index_page(self):
        """Testa la pagina principale."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Documenti disponibili', response.data)
    
    def test_annotate_page(self):
        """Testa la pagina di annotazione."""
        response = self.client.get('/annotate/doc_1')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Documento di test', response.data)
    
    def test_save_annotation(self):
        """Testa il salvataggio di un'annotazione."""
        new_annotation = {
            "start": 10,
            "end": 15,
            "text": "test",
            "type": "CONCETTO_GIURIDICO"
        }
        
        response = self.client.post(
            '/api/save_annotation',
            json={"doc_id": "doc_1", "annotation": new_annotation}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'success')
        
        # Verifica che l'annotazione sia stata salvata
        with open(self.annotations_file, 'r', encoding='utf-8') as f:
            annotations = json.load(f)
            
        self.assertEqual(len(annotations["doc_1"]), 2)
    
    def test_delete_annotation(self):
        """Testa l'eliminazione di un'annotazione."""
        response = self.client.post(
            '/api/delete_annotation',
            json={"doc_id": "doc_1", "annotation_id": "ann_1"}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'success')
        
        # Verifica che l'annotazione sia stata eliminata
        with open(self.annotations_file, 'r', encoding='utf-8') as f:
            annotations = json.load(f)
            
        self.assertEqual(len(annotations["doc_1"]), 0)
    
    def test_export_annotations(self):
        """Testa l'esportazione delle annotazioni."""
        response = self.client.get('/api/export_annotations?format=spacy')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('data', response.json)
        
        # Verifica che i dati esportati siano corretti
        exported_data = response.json['data']
        self.assertEqual(len(exported_data), 1)
        self.assertEqual(len(exported_data[0]['entities']), 1)
    
    @patch('ner_giuridico.annotation.app.DynamicNERGiuridico')
    def test_recognize_entities(self, mock_ner):
        """Testa il riconoscimento automatico delle entità."""
        # Configura il mock per DynamicNERGiuridico
        mock_instance = MagicMock()
        mock_instance.process.return_value = {
            "entities": [
                {
                    "text": "Questo",
                    "type": "CONCETTO_GIURIDICO",
                    "start_char": 0,
                    "end_char": 6
                }
            ]
        }
        mock_ner.return_value = mock_instance
        
        response = self.client.post(
            '/api/recognize',
            json={"text": "Questo è un documento di test."}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'success')
        self.assertEqual(len(response.json['entities']), 1)
    
    def test_upload_document(self):
        """Testa il caricamento di un documento."""
        from io import BytesIO
        
        # Crea un file di test
        test_file = BytesIO(b"Questo e' un nuovo documento di test.")
        
        # Effettua una richiesta di upload
        response = self.client.post(
            '/api/upload_document',
            data={
                'file': (test_file, 'test_document.txt')
            }
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['status'], 'success')
        
        # Verifica che il documento sia stato salvato
        with open(self.documents_file, 'r', encoding='utf-8') as f:
            documents = json.load(f)
            
        self.assertEqual(len(documents), 2)

if __name__ == '__main__':
    unittest.main()