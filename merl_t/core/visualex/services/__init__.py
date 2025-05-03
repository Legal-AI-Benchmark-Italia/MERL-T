"""
VisuaLex Services

Service classes for scraping and processing Italian legal documents.
"""

from .brocardi_scraper import BrocardiScraper
from .normattiva_scraper import NormattivaScraper
from .eurlex_scraper import EurlexScraper
from .pdfextractor import extract_pdf

__all__ = ["BrocardiScraper", "NormattivaScraper", "EurlexScraper", "extract_pdf"]
