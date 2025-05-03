"""
VisuaLex API Client

Client for accessing Italian legal documents from various sources.
Adapts the original VisuaLex/NormaScraper code to the new architecture.
"""

import asyncio
import re
import json
from typing import Optional, List, Dict, Any, Union
from urllib.parse import quote

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from merl_t.config import get_config_manager
from .models import Norma, NormaVisitata, ArticleContent, Commentary, SearchResult


class VisuaLexClient:
    """
    Client for retrieving Italian legal documents.
    
    Provides methods to:
    - Fetch articles from Normattiva
    - Fetch commentary from Brocardi.it
    - Fetch EU legislation from EUR-Lex
    - Search for legislation by keywords
    """
    
    def __init__(self):
        """Initialize the VisuaLex client."""
        self.config = get_config_manager()
        
        # Initialize session lazily
        self._session = None
        
        # Configure base URLs
        self.base_urls = {
            "normattiva": "https://www.normattiva.it",
            "brocardi": "https://www.brocardi.it",
            "eurlex": "https://eur-lex.europa.eu"
        }
        
        # Configure cache parameters
        self.cache_enabled = self.config.get("visualex.cache.enabled", True)
        self.cache_ttl = self.config.get("visualex.cache.ttl", 3600)  # 1 hour by default
        
        # In-memory cache
        self._cache = {}
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """
        Get or create an aiohttp session.
        
        Returns:
            aiohttp.ClientSession
        """
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7"
                }
            )
        return self._session
    
    async def close(self):
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def fetch_article_text(self, norma: NormaVisitata) -> Dict[str, Any]:
        """
        Fetch the text of a legislative article.
        
        Args:
            norma: The norm to fetch
            
        Returns:
            Dictionary with article information
        """
        # Check cache
        cache_key = f"article_{norma.urn}"
        if self.cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]
        
        session = await self._get_session()
        
        # Determine source based on tipo_atto
        if norma.tipo_atto.lower() in ["regolamento", "direttiva", "decisione", "treaty"] or re.match(r"^3\d{7}[A-Z]\d{4}$", norma.numero_atto):
            # European legislation
            return await self._fetch_eurlex_article(norma, session)
        else:
            # Italian legislation
            return await self._fetch_normattiva_article(norma, session)
    
    async def _fetch_normattiva_article(self, norma: NormaVisitata, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """
        Fetch an article from Normattiva.
        
        Args:
            norma: The norm to fetch
            session: aiohttp client session
            
        Returns:
            Dictionary with article information
        """
        # Build the Normattiva URL
        url = self._build_normattiva_url(norma)
        
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
                
                # Parse the article content
                article_data = self._parse_normattiva_html(html, norma)
                
                # Cache the result
                if self.cache_enabled:
                    cache_key = f"article_{norma.urn}"
                    self._cache[cache_key] = article_data
                
                return article_data
        except Exception as e:
            logger.error(f"Error fetching article from Normattiva: {e}")
            return {
                "error": str(e),
                "url": url,
                "norma": {
                    "tipo": norma.tipo_atto,
                    "numero": norma.numero_atto,
                    "data": norma.data,
                    "articolo": norma.numero_articolo
                }
            }
    
    def _build_normattiva_url(self, norma: NormaVisitata) -> str:
        """
        Build a URL for Normattiva.
        
        Args:
            norma: The norm to build a URL for
            
        Returns:
            URL string
        """
        tipo_atto_map = {
            "legge": "LEGGE",
            "decreto legislativo": "DECRETO LEGISLATIVO",
            "decreto legge": "DECRETO-LEGGE",
            "regio decreto": "REGIO DECRETO",
            "costituzione": "COSTITUZIONE",
            "dlgs": "DECRETO LEGISLATIVO",
            "dl": "DECRETO-LEGGE",
            "dpr": "DECRETO DEL PRESIDENTE DELLA REPUBBLICA"
        }
        
        # Normalize tipo_atto
        tipo_normalizzato = tipo_atto_map.get(norma.tipo_atto.lower(), norma.tipo_atto.upper())
        
        # Format date (assuming it's in the format "day month year")
        date_parts = norma.data.split()
        if len(date_parts) == 3:
            try:
                day = date_parts[0].zfill(2)
                month_map = {
                    "gennaio": "01", "febbraio": "02", "marzo": "03", "aprile": "04",
                    "maggio": "05", "giugno": "06", "luglio": "07", "agosto": "08",
                    "settembre": "09", "ottobre": "10", "novembre": "11", "dicembre": "12"
                }
                month = month_map.get(date_parts[1].lower(), "01")
                year = date_parts[2]
                formatted_date = f"{day}/{month}/{year}"
            except:
                formatted_date = norma.data
        else:
            formatted_date = norma.data
        
        base_url = f"{self.base_urls['normattiva']}/uri-res/N2Ls"
        params = [
            f"urn:nir:stato:legge:{formatted_date};{norma.numero_atto}"
        ]
        
        if norma.numero_articolo:
            params.append(f"article={norma.numero_articolo}")
        
        if norma.data_versione:
            params.append(f"version={norma.data_versione}")
        
        return f"{base_url}?{'&'.join(params)}"
    
    def _parse_normattiva_html(self, html: str, norma: NormaVisitata) -> Dict[str, Any]:
        """
        Parse HTML from Normattiva.
        
        Args:
            html: HTML content
            norma: The norm being parsed
            
        Returns:
            Dictionary with article information
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find article content
        article_div = soup.find('div', {'class': 'articleContentPPDetH'})
        
        if not article_div:
            return {
                "error": "Article content not found",
                "norma": {
                    "tipo": norma.tipo_atto,
                    "numero": norma.numero_atto,
                    "data": norma.data,
                    "articolo": norma.numero_articolo
                }
            }
        
        # Extract article title/rubrica
        title_elem = article_div.find('h2')
        title = title_elem.text.strip() if title_elem else ""
        
        # Extract article text
        text_div = article_div.find('div', {'class': 'articolo'})
        if not text_div:
            text_div = article_div
        
        text = text_div.get_text(separator='\n').strip()
        html_content = str(text_div)
        
        # Extract subarticles/commas if present
        subarticles = []
        comma_elems = text_div.find_all('p', {'class': 'comma'})
        for i, comma in enumerate(comma_elems):
            subarticles.append({
                "number": i + 1,
                "text": comma.get_text().strip(),
                "html": str(comma)
            })
        
        return {
            "tipo": norma.tipo_atto,
            "numero": norma.numero_atto,
            "data": norma.data,
            "articolo": norma.numero_articolo,
            "rubrica": title,
            "testo": text,
            "html": html_content,
            "commi": subarticles,
            "url": norma.url,
            "urn": norma.urn
        }
    
    async def fetch_brocardi_info(self, act_type: str, article_number: str) -> Dict[str, Any]:
        """
        Fetch commentary from Brocardi.it.
        
        Args:
            act_type: Type of act (e.g., "codice civile")
            article_number: Article number
            
        Returns:
            Dictionary with commentary information
        """
        # Check cache
        cache_key = f"brocardi_{act_type}_{article_number}"
        if self.cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]
        
        # Map act types to Brocardi.it paths
        act_type_map = {
            "codice civile": "codice-civile/articoli",
            "codice penale": "codice-penale/articoli",
            "cc": "codice-civile/articoli",
            "cp": "codice-penale/articoli",
            "costituzione": "costituzione/articoli"
        }
        
        # Normalize act type
        path = act_type_map.get(act_type.lower(), act_type.lower())
        
        # Build the URL
        url = f"{self.base_urls['brocardi']}/{path}/art-{article_number}"
        
        session = await self._get_session()
        
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
                
                # Parse the commentary
                commentary_data = self._parse_brocardi_html(html, act_type, article_number)
                
                # Cache the result
                if self.cache_enabled:
                    self._cache[cache_key] = commentary_data
                
                return commentary_data
        except Exception as e:
            logger.error(f"Error fetching commentary from Brocardi: {e}")
            return {
                "error": str(e),
                "url": url,
                "act_type": act_type,
                "article_number": article_number
            }
    
    def _parse_brocardi_html(self, html: str, act_type: str, article_number: str) -> Dict[str, Any]:
        """
        Parse HTML from Brocardi.it.
        
        Args:
            html: HTML content
            act_type: Type of act
            article_number: Article number
            
        Returns:
            Dictionary with commentary information
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find the article title
        title_elem = soup.find('h1')
        title = title_elem.text.strip() if title_elem else f"Articolo {article_number}"
        
        # Find article content
        content_div = soup.find('div', {'class': 'panel-body'})
        if not content_div:
            content_div = soup.find('div', {'class': 'post-content'})
        
        # Extract explanation text
        explanation = ""
        if content_div:
            # Remove "social buttons" and other non-content elements
            for social_div in content_div.find_all('div', {'class': 'social-buttons'}):
                social_div.decompose()
            
            explanation = content_div.get_text(separator='\n').strip()
            
            # Extract only what's before "Related Articles" or similar sections
            if "Articoli correlati" in explanation:
                explanation = explanation.split("Articoli correlati")[0].strip()
        
        # Extract examples if present
        examples = []
        example_div = soup.find('div', {'id': 'esempi'})
        if example_div:
            example_items = example_div.find_all('div', {'class': 'esempio'})
            for item in example_items:
                title_elem = item.find('h3')
                content_elem = item.find('div', {'class': 'esempio-content'})
                
                if title_elem and content_elem:
                    examples.append({
                        "title": title_elem.text.strip(),
                        "content": content_elem.get_text(separator='\n').strip()
                    })
        
        # Extract references if present
        references = []
        ref_div = soup.find('div', {'id': 'riferimenti'})
        if ref_div:
            ref_items = ref_div.find_all('li')
            for item in ref_items:
                ref_text = item.get_text().strip()
                ref_link = item.find('a')
                ref_url = ref_link['href'] if ref_link else ""
                
                if ref_text:
                    references.append({
                        "text": ref_text,
                        "url": ref_url
                    })
        
        return {
            "title": title,
            "explanation": explanation,
            "examples": examples,
            "references": references,
            "act_type": act_type,
            "article_number": article_number,
            "url": f"{self.base_urls['brocardi']}/{act_type.lower()}/articoli/art-{article_number}",
            "source": "Brocardi.it"
        }
    
    async def fetch_eurlex_document(self, celex_number: str, language: str = "IT") -> Dict[str, Any]:
        """
        Fetch a document from EUR-Lex.
        
        Args:
            celex_number: CELEX number of the document
            language: Language code (e.g., "IT" for Italian)
            
        Returns:
            Dictionary with document information
        """
        # Check cache
        cache_key = f"eurlex_{celex_number}_{language}"
        if self.cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]
        
        # Format CELEX number
        celex = celex_number
        if not celex.startswith('3'):
            celex = f"3{celex}"
        
        # Build the URL
        url = f"{self.base_urls['eurlex']}/legal-content/{language}/TXT/HTML/?uri=CELEX:{celex}"
        
        session = await self._get_session()
        
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
                
                # Parse the document
                document_data = self._parse_eurlex_html(html, celex, language)
                
                # Cache the result
                if self.cache_enabled:
                    self._cache[cache_key] = document_data
                
                return document_data
        except Exception as e:
            logger.error(f"Error fetching document from EUR-Lex: {e}")
            return {
                "error": str(e),
                "url": url,
                "celex": celex,
                "language": language
            }
    
    def _parse_eurlex_html(self, html: str, celex: str, language: str) -> Dict[str, Any]:
        """
        Parse HTML from EUR-Lex.
        
        Args:
            html: HTML content
            celex: CELEX number
            language: Language code
            
        Returns:
            Dictionary with document information
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract title
        title_elem = soup.find('p', {'class': 'ti-act'})
        if not title_elem:
            title_elem = soup.find('title')
        title = title_elem.text.strip() if title_elem else f"Document {celex}"
        
        # Extract content
        content_div = soup.find('div', {'id': 'text'})
        if not content_div:
            content_div = soup.find('div', {'class': 'tabContent'})
        
        if not content_div:
            return {
                "error": "Document content not found",
                "celex": celex,
                "language": language,
                "url": f"{self.base_urls['eurlex']}/legal-content/{language}/TXT/HTML/?uri=CELEX:{celex}"
            }
        
        # Extract text and HTML
        text = content_div.get_text(separator='\n').strip()
        html_content = str(content_div)
        
        # Extract metadata if present
        metadata = {}
        info_div = soup.find('div', {'class': 'info'})
        if info_div:
            for dt, dd in zip(info_div.find_all('dt'), info_div.find_all('dd')):
                key = dt.text.strip().lower().replace(' ', '_')
                value = dd.text.strip()
                metadata[key] = value
        
        return {
            "title": title,
            "text": text,
            "html": html_content,
            "metadata": metadata,
            "celex": celex,
            "language": language,
            "url": f"{self.base_urls['eurlex']}/legal-content/{language}/TXT/HTML/?uri=CELEX:{celex}",
            "source": "EUR-Lex"
        }
    
    async def search(self, query: str, source: str = "normattiva", max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for legislation by keywords.
        
        Args:
            query: Search query
            source: Source to search (normattiva, brocardi, eurlex)
            max_results: Maximum number of results
            
        Returns:
            List of search results
        """
        # Check cache
        cache_key = f"search_{source}_{query}_{max_results}"
        if self.cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]
        
        # Normalize source
        source = source.lower()
        if source not in self.base_urls:
            raise ValueError(f"Invalid source: {source}")
        
        # Dispatch to appropriate search method
        if source == "normattiva":
            results = await self._search_normattiva(query, max_results)
        elif source == "brocardi":
            results = await self._search_brocardi(query, max_results)
        elif source == "eurlex":
            results = await self._search_eurlex(query, max_results)
        else:
            results = []
        
        # Cache the results
        if self.cache_enabled:
            self._cache[cache_key] = results
        
        return results
    
    async def _search_normattiva(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Search Normattiva.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of search results
        """
        # Build the search URL
        url = f"{self.base_urls['normattiva']}/do/search?maxHits={max_results}&type=simple&is=false&rastersize=20&reference={quote(query)}"
        
        session = await self._get_session()
        
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
                
                # Parse search results
                return self._parse_normattiva_search_results(html, query)
        except Exception as e:
            logger.error(f"Error searching Normattiva: {e}")
            return []
    
    def _parse_normattiva_search_results(self, html: str, query: str) -> List[Dict[str, Any]]:
        """
        Parse search results from Normattiva.
        
        Args:
            html: HTML content
            query: Original search query
            
        Returns:
            List of search results
        """
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find result items
        result_items = soup.find_all('li', {'class': 'hitItem'})
        
        for item in result_items:
            # Extract title
            title_elem = item.find('p', {'class': 'reference'})
            title = title_elem.text.strip() if title_elem else ""
            
            # Extract URL
            link_elem = item.find('a')
            url = link_elem['href'] if link_elem and 'href' in link_elem.attrs else ""
            if url and not url.startswith('http'):
                url = f"{self.base_urls['normattiva']}{url}"
            
            # Extract description
            desc_elem = item.find('div', {'class': 'dati'})
            description = desc_elem.text.strip() if desc_elem else ""
            
            # Extract metadata
            meta = {}
            tipo_elem = item.find('span', {'class': 'tipo'})
            if tipo_elem:
                meta['tipo'] = tipo_elem.text.strip()
            
            numero_elem = item.find('span', {'class': 'numero'})
            if numero_elem:
                meta['numero'] = numero_elem.text.strip()
            
            date_elem = item.find('span', {'class': 'data'})
            if date_elem:
                meta['data'] = date_elem.text.strip()
            
            # Add to results
            if title and url:
                results.append({
                    "title": title,
                    "description": description,
                    "url": url,
                    "source": "Normattiva",
                    "metadata": meta
                })
        
        return results
    
    async def _search_brocardi(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Search Brocardi.it.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of search results
        """
        # Build the search URL
        url = f"{self.base_urls['brocardi']}/cerca.html?query={quote(query)}"
        
        session = await self._get_session()
        
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
                
                # Parse search results
                results = self._parse_brocardi_search_results(html, query)
                
                # Limit results
                return results[:max_results]
        except Exception as e:
            logger.error(f"Error searching Brocardi.it: {e}")
            return []
    
    def _parse_brocardi_search_results(self, html: str, query: str) -> List[Dict[str, Any]]:
        """
        Parse search results from Brocardi.it.
        
        Args:
            html: HTML content
            query: Original search query
            
        Returns:
            List of search results
        """
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find result items
        result_items = soup.find_all('div', {'class': 'search-result'})
        
        for item in result_items:
            # Extract title
            title_elem = item.find('h3')
            link_elem = title_elem.find('a') if title_elem else None
            
            if link_elem:
                title = link_elem.text.strip()
                url = link_elem['href'] if 'href' in link_elem.attrs else ""
                if url and not url.startswith('http'):
                    url = f"{self.base_urls['brocardi']}{url}"
                
                # Extract description
                desc_elem = item.find('div', {'class': 'result-description'})
                description = desc_elem.text.strip() if desc_elem else ""
                
                # Add to results
                if title and url:
                    results.append({
                        "title": title,
                        "description": description,
                        "url": url,
                        "source": "Brocardi.it"
                    })
        
        return results
    
    async def _search_eurlex(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Search EUR-Lex.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            
        Returns:
            List of search results
        """
        # Build the search URL (using language=IT for Italian)
        url = f"{self.base_urls['eurlex']}/search.html?qid=1623334882171&PROC_NUM={quote(query)}&locale=it"
        
        session = await self._get_session()
        
        try:
            async with session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
                
                # Parse search results
                results = self._parse_eurlex_search_results(html, query)
                
                # Limit results
                return results[:max_results]
        except Exception as e:
            logger.error(f"Error searching EUR-Lex: {e}")
            return []
    
    def _parse_eurlex_search_results(self, html: str, query: str) -> List[Dict[str, Any]]:
        """
        Parse search results from EUR-Lex.
        
        Args:
            html: HTML content
            query: Original search query
            
        Returns:
            List of search results
        """
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        # Find result items
        result_items = soup.find_all('div', {'class': 'SearchResult'})
        
        for item in result_items:
            # Extract title
            title_elem = item.find('span', {'class': 'title'})
            title = title_elem.text.strip() if title_elem else ""
            
            # Extract URL
            link_elem = item.find('a')
            url = link_elem['href'] if link_elem and 'href' in link_elem.attrs else ""
            if url and not url.startswith('http'):
                url = f"{self.base_urls['eurlex']}{url}"
            
            # Extract description
            desc_elem = item.find('span', {'class': 'SearchResultsExtract'})
            description = desc_elem.text.strip() if desc_elem else ""
            
            # Extract metadata
            meta = {}
            celex_elem = item.find('div', {'class': 'ecli'})
            if celex_elem:
                meta['celex'] = celex_elem.text.strip()
            
            date_elem = item.find('span', {'class': 'date'})
            if date_elem:
                meta['date'] = date_elem.text.strip()
            
            # Add to results
            if title and url:
                results.append({
                    "title": title,
                    "description": description,
                    "url": url,
                    "source": "EUR-Lex",
                    "metadata": meta
                })
        
        return results 