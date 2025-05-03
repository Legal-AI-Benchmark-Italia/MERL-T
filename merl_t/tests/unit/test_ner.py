"""
Unit tests for the NER (Named Entity Recognition) system.
"""

import unittest
from unittest.mock import patch, MagicMock

import pytest

from merl_t.core.ner import TextPreprocessor, EntityNormalizer
from merl_t.core.ner.entities import LegalEntity


class TestTextPreprocessor(unittest.TestCase):
    """Tests for TextPreprocessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.preprocessor = TextPreprocessor()
    
    def test_clean_text_removes_extra_whitespace(self):
        """Test that clean_text removes extra whitespace."""
        text = "  This   has  extra   spaces  "
        cleaned = self.preprocessor.clean_text(text)
        self.assertEqual(cleaned, "This has extra spaces")
    
    def test_clean_text_handles_empty_string(self):
        """Test that clean_text handles empty string."""
        self.assertEqual(self.preprocessor.clean_text(""), "")
    
    def test_clean_text_handles_none(self):
        """Test that clean_text handles None."""
        with self.assertRaises(TypeError):
            self.preprocessor.clean_text(None)
    
    @patch('merl_t.core.ner.preprocessing.nltk')
    def test_normalize_text_applies_transformations(self, mock_nltk):
        """Test that normalize_text applies expected transformations."""
        # Mock the sentence tokenizer
        mock_nltk.sent_tokenize.return_value = ["This is a test sentence.", "This is another one."]
        
        text = "This is a test sentence. This is another one."
        normalized = self.preprocessor.normalize_text(text)
        
        # Verify that sentence tokenization was called
        mock_nltk.sent_tokenize.assert_called_once_with(text)
        
        # Assuming the implementation just joins the sentences again
        self.assertEqual(normalized, text)


class TestEntityNormalizer(unittest.TestCase):
    """Tests for EntityNormalizer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.normalizer = EntityNormalizer()
    
    def test_normalize_legal_reference_article(self):
        """Test normalization of an article reference."""
        text = "art. 123 c.p."
        expected = "articolo 123 codice penale"
        self.assertEqual(self.normalizer.normalize_legal_reference(text), expected)
    
    def test_normalize_legal_reference_law(self):
        """Test normalization of a law reference."""
        text = "l. 241/1990"
        expected = "legge 241/1990"
        self.assertEqual(self.normalizer.normalize_legal_reference(text), expected)
    
    def test_normalize_date_italian_format(self):
        """Test normalization of a date in Italian format."""
        text = "01/01/2020"
        expected = "2020-01-01"
        self.assertEqual(self.normalizer.normalize_date(text), expected)
    
    def test_normalize_court_abbreviation(self):
        """Test normalization of a court abbreviation."""
        text = "Cass. civ."
        expected = "Corte di Cassazione civile"
        self.assertEqual(self.normalizer.normalize_court_name(text), expected)


@pytest.mark.asyncio
class TestNERSystem:
    """Tests for NERSystem using pytest-asyncio."""
    
    async def test_process_text(self):
        """Test processing text through the NER system."""
        from merl_t.core.ner import NERSystem
        
        # Create a mock transformer recognizer
        mock_recognizer = MagicMock()
        mock_recognizer.process.return_value = [
            LegalEntity(
                id="test-id",
                text="art. 123 c.p.",
                type="ARTICOLO_CODICE",
                start_char=10,
                end_char=22,
                confidence=0.95
            )
        ]
        
        # Create system with mocked components
        ner_system = NERSystem()
        ner_system._transformer_recognizer = mock_recognizer
        ner_system._preprocessor = TextPreprocessor()
        ner_system._normalizer = EntityNormalizer()
        
        # Mock entity_manager to avoid DB interactions
        mock_entity_manager = MagicMock()
        mock_entity_type = MagicMock()
        mock_entity_type.id = "ARTICOLO_CODICE"
        mock_entity_manager.get_entity.return_value = mock_entity_type
        ner_system._entity_manager = mock_entity_manager
        
        result = await ner_system.process_text("This text contains art. 123 c.p. as a legal reference.")
        
        assert len(result) == 1
        assert result[0].text == "art. 123 c.p."
        assert result[0].type == "ARTICOLO_CODICE"
        
        # Verify normalizer was called
        mock_recognizer.process.assert_called_once()
    
    async def test_process_text_empty(self):
        """Test processing empty text."""
        from merl_t.core.ner import NERSystem
        
        ner_system = NERSystem()
        
        # Mock dependencies to avoid actual processing
        ner_system._transformer_recognizer = MagicMock()
        ner_system._transformer_recognizer.process.return_value = []
        ner_system._preprocessor = MagicMock()
        ner_system._preprocessor.normalize_text.return_value = ""
        ner_system._normalizer = MagicMock()
        
        result = await ner_system.process_text("")
        
        assert len(result) == 0
        
        # Verify preprocess was called but not recognizer
        ner_system._preprocessor.normalize_text.assert_called_once_with("")
        ner_system._transformer_recognizer.process.assert_not_called() 