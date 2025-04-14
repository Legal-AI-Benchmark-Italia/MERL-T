import logging
import re
import os
from typing import Optional, Tuple, Union, Dict, Any, List

import aiohttp
import asyncio
import requests
from bs4 import BeautifulSoup
from aiocache import cached, Cache
from aiocache.serializers import JsonSerializer

from ..tools.map import BROCARDI_CODICI
from ..tools.norma import NormaVisitata
from ..tools.text_op import normalize_act_type
from ..tools.sys_op import BaseScraper

# Configurazione del logger di modulo
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
file_handler = logging.FileHandler("brocardi_scraper.log")
file_handler.setFormatter(formatter)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

# Costante per il base URL
BASE_URL: str = "https://brocardi.it"


class BrocardiScraper(BaseScraper):
    def __init__(self) -> None:
        logger.info("Initializing BrocardiScraper")
        self.knowledge: List[Dict[str, Any]] = [BROCARDI_CODICI]

    @cached(ttl=86400, cache=Cache.MEMORY, serializer=JsonSerializer())
    async def do_know(self, norma_visitata: NormaVisitata) -> Optional[Tuple[str, str]]:
        logger.info(f"Checking if knowledge exists for norma: {norma_visitata}")

        norma_str: Optional[str] = self._build_norma_string(norma_visitata)
        if norma_str is None:
            logger.error("Invalid norma format")
            raise ValueError("Invalid norma format")

        search_str = norma_str.lower()
        for txt, link in self.knowledge[0].items():
            if search_str in txt.lower():
                logger.info(f"Knowledge found for norma: {norma_visitata}")
                return txt, link

        logger.warning(f"No knowledge found for norma: {norma_visitata}")
        return None

    @cached(ttl=86400, cache=Cache.MEMORY, serializer=JsonSerializer())
    async def look_up(self, norma_visitata: NormaVisitata) -> Optional[str]:
        logger.info(f"Looking up norma: {norma_visitata}")

        norma_info = await self.do_know(norma_visitata)
        if not norma_info:
            return None

        link: str = norma_info[1]
        # Recupera il contenuto della pagina principale
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            try:
                logger.info(f"Requesting main link: {link}")
                async with session.get(link) as response:
                    response.raise_for_status()
                    html_text: str = await response.text()
                    soup: BeautifulSoup = BeautifulSoup(html_text, 'html.parser')
            except aiohttp.ClientError as e:
                logger.error(f"Failed to retrieve content for norma link: {link}: {e}")
                return None

        numero_articolo: Optional[str] = (
            norma_visitata.numero_articolo.replace('-', '')
            if norma_visitata.numero_articolo else None
        )
        if numero_articolo:
            article_link = await self._find_article_link(soup, BASE_URL, numero_articolo)
            return article_link
        logger.info("No article number provided")
        return None

    async def _find_article_link(self, soup: BeautifulSoup, base_url: str, numero_articolo: str) -> Optional[str]:
        pattern = re.compile(rf'href=["\']([^"\']*art{re.escape(numero_articolo)}\.html)["\']')
        logger.info("Searching for target link in the main page content")

        matches = pattern.findall(str(soup))
        if matches:
            target_link = requests.compat.urljoin(base_url, matches[0])
            logger.info(f"Direct match found: {target_link}")
            return target_link

        logger.info("No direct match found, searching in 'section-title' divs")
        section_titles = soup.find_all('div', class_='section-title')
        
        async def check_sub_link(a_tag, session: aiohttp.ClientSession) -> Optional[str]:
            sub_link = requests.compat.urljoin(base_url, a_tag.get('href', ''))
            if not sub_link:
                return None
                
            try:
                # Assicurati che la sessione sia valida
                if session.closed:
                    logger.warning(f"Session closed for sub-link {sub_link}, skipping")
                    return None
                    
                async with session.get(sub_link, timeout=15) as sub_response:
                    if sub_response.status == 200:
                        sub_html = await sub_response.text()
                        sub_soup = BeautifulSoup(sub_html, 'html.parser')
                        sub_matches = pattern.findall(str(sub_soup))
                        if sub_matches:
                            return requests.compat.urljoin(base_url, sub_matches[0])
            except Exception as e:
                logger.error(f"Error processing sub-link {sub_link}: {str(e)}", exc_info=True)
            return None

        async with aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False, limit=10),
            timeout=aiohttp.ClientTimeout(total=30)
        ) as session:
            tasks = []
            for section in section_titles:
                for a_tag in section.find_all('a', href=True):
                    tasks.append(check_sub_link(a_tag, session))

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, str):  # Valid result
                        return result
                    
        logger.info(f"No matching article found for article number: {numero_articolo}")
        return None
    
    async def get_info(self, norma_visitata: NormaVisitata) -> Tuple[Optional[str], Dict[str, Any], Optional[str]]:
        logger.info(f"Getting info for norma: {norma_visitata}")

        norma_link = await self.look_up(norma_visitata)
        if not norma_link:
            return None, {}, None

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
            try:
                async with session.get(norma_link) as response:
                    response.raise_for_status()
                    html_text = await response.text()
                    soup = BeautifulSoup(html_text, 'html.parser')
            except aiohttp.ClientError as e:
                logger.error(f"Failed to retrieve content for norma link: {norma_link}: {e}")
                return None, {}, None

        info: Dict[str, Any] = {}
        info['Position'] = self._extract_position(soup)
        self._extract_sections(soup, info)
        return info.get('Position'), info, norma_link

    def _extract_position(self, soup: BeautifulSoup) -> Optional[str]:
        position_tag = soup.find('div', id='breadcrumb', recursive=True)
        if position_tag:
            # Mantiene la logica originale di slicing
            return position_tag.get_text(strip=False).replace('\n', '').replace('  ', '')[17:]
        logger.warning("Breadcrumb position not found")
        return None

    def _extract_sections(self, soup: BeautifulSoup, info: Dict[str, Any]) -> None:
        corpo = soup.find('div', class_='panes-condensed panes-w-ads content-ext-guide content-mark', recursive=True)
        if not corpo:
            logger.warning("Main content section not found")
            return

        brocardi_sections = corpo.find_all('div', class_='brocardi-content')
        if brocardi_sections:
            info['Brocardi'] = [section.get_text(strip=False) for section in brocardi_sections]

        ratio_section = corpo.find('div', class_='container-ratio')
        if ratio_section:
            ratio_text = ratio_section.find('div', class_='corpoDelTesto')
            if ratio_text:
                info['Ratio'] = ratio_text.get_text(strip=False)

        spiegazione_header = corpo.find('h3', string=lambda text: text and "Spiegazione dell'art" in text)
        if spiegazione_header:
            spiegazione_content = spiegazione_header.find_next_sibling('div', class_='text')
            if spiegazione_content:
                info['Spiegazione'] = spiegazione_content.get_text(strip=False)

        massime_header = corpo.find('h3', string=lambda text: text and "Massime relative all'art" in text)
        if massime_header:
            massime_content = massime_header.find_next_sibling('div', class_='text')
            if massime_content:
                info['Massime'] = [massima.get_text(strip=False) for massima in massime_content]

    def _build_norma_string(self, norma_visitata: Union[NormaVisitata, str]) -> Optional[str]:
        if isinstance(norma_visitata, NormaVisitata):
            norma = norma_visitata.norma
            tipo_norm = normalize_act_type(norma.tipo_atto_str, True, 'brocardi')
            components = [tipo_norm]
            if norma.data:
                components.append(f"{norma.data},")
            if norma.numero_atto:
                components.append(f"n. {norma.numero_atto}")
            return " ".join(components).strip()
        elif isinstance(norma_visitata, str):
            return norma_visitata.strip()
        return None
