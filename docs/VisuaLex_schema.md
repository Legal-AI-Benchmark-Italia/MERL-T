# VisuaLexWeb API Architecture Blueprint

## Overview

VisuaLexWeb (also called NormaScraper) is an API-driven web application designed to retrieve, process, and display legal documents from multiple sources, including:

* **Normattiva** : Italian legislation database
* **Brocardi** : Legal commentary and interpretation
* **EUR-Lex** : European Union legislation

The application follows an asynchronous architecture using Quart (an ASGI framework) and provides both RESTful API endpoints and a web interface for exploring legal documents.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Client (Browser)                       │
└───────────────────────────────┬─────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                        Web Interface                        │
│    (HTML Templates, JavaScript, CSS, Bootstrap, CKEditor)    │
└───────────────────────────────┬─────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Controller (Quart)                    │
│            Rate Limiting, Middleware, Error Handling        │
└───────┬─────────────────┬────────────────┬─────────┬────────┘
        │                 │                │         │
        ▼                 ▼                ▼         ▼
┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐
│Normattiva    │  │Brocardi      │  │EUR-Lex   │  │PDF       │
│Scraper       │  │Scraper       │  │Scraper   │  │Extractor │
└───────┬──────┘  └───────┬──────┘  └─────┬────┘  └────┬─────┘
        │                 │               │            │
        └─────────────────┼───────────────┼────────────┘
                          │               │
                          ▼               ▼
┌─────────────────────────────┐  ┌────────────────────────────┐
│       External APIs         │  │     Utility Functions      │
│ (Normattiva, Brocardi, etc) │  │(URN Generation, Parsing,   │
└─────────────────────────────┘  │Tree Extraction, etc)       │
                                 └────────────────────────────┘
```

## Core Components

### 1. API Controller (`src/visualex_api/app.py`)

The heart of the application is the `NormaController` class which:

* Initializes the Quart application
* Sets up middleware for rate limiting and logging
* Defines API routes
* Initializes services
* Handles errors
* Processes requests and responses

Key features:

* Asynchronous request handling
* Centralized error handling
* Rate limiting to prevent abuse
* Request/response logging

### 2. Data Models (`src/visualex_api/tools/norma.py`)

Two primary data models:

* **`Norma`** : Represents a legislative act with properties:
* `tipo_atto` (act type)
* `data` (date)
* `numero_atto` (act number)
* `url` (generated URL)
* **`NormaVisitata`** : Extends Norma with additional metadata:
* `numero_articolo` (article number)
* `versione` (version)
* `data_versione` (version date)
* `allegato` (annex)
* `urn` (Uniform Resource Name)

### 3. Service Layer

#### Document Scrapers

* **`NormattivaScraper`** (`src/visualex_api/services/normattiva_scraper.py`):
  * Retrieves Italian legislation
  * Parses HTML from Normattiva website
  * Extracts article text
* **`BrocardiScraper`** (`src/visualex_api/services/brocardi_scraper.py`):
  * Retrieves legal commentary
  * Extracts explanations, interpretations, and case law
* **`EurlexScraper`** (`src/visualex_api/services/eurlex_scraper.py`):
  * Retrieves European legislation
  * Handles EU treaties, regulations, and directives
* **`PDFExtractor`** (`src/visualex_api/services/pdfextractor.py`):
  * Exports legal documents as PDF
  * Uses Selenium WebDriver for headless browsing

### 4. Utility Modules

* **`urngenerator.py`** : Generates URNs for legal documents
* **`treextractor.py`** : Extracts hierarchical structure from legal documents
* **`text_op.py`** : Text processing and normalization functions
* **`sys_op.py`** : System operations and WebDriver management
* **`map.py`** : Mappings between different nomenclatures and sources
* **`config.py`** : Configuration settings

### 5. Web Interface

* **HTML Templates** (`src/templates/`):
  * `index.html`: Main application interface
  * `swagger_ui.html`: API documentation interface
* **Frontend Assets** :
* JavaScript (`src/static/script.js`): Handles user interactions, form submission, and dynamic content updates
* CSS (`src/static/style.css`): Styling with responsive design
* External libraries: Bootstrap, CKEditor, SortableJS

## API Endpoints

The API exposes several RESTful endpoints:

1. `/health` - Health check endpoint
2. `/documents/norm` (`/fetch_norma_data`) - Fetches norm metadata
3. `/documents/article` (`/fetch_article_text`) - Fetches article text
4. `/documents/stream-article` (`/stream_article_text`) - Streams article text as it becomes available
5. `/documents/brocardi` (`/fetch_brocardi_info`) - Fetches legal commentary from Brocardi
6. `/documents/all` (`/fetch_all_data`) - Fetches all data (article text and commentary)
7. `/documents/tree` (`/fetch_tree`) - Fetches document structure
8. `/export/pdf` (`/export_pdf`) - Exports documents as PDF
9. `/history` - Retrieves search history

## Data Flow

### Typical Request Flow

1. **Client sends a request** with parameters:
   * Act type (e.g., "legge", "decreto legislativo")
   * Act number (e.g., "241")
   * Date (e.g., "7 agosto 1990")
   * Article number(s) (e.g., "1-3,5")
   * Version information
2. **API Controller** processes the request:
   * Validates input parameters
   * Creates `NormaVisitata` instances
   * Selects appropriate scraper based on act type
3. **Scraper Service** retrieves the document:
   * Constructs the appropriate URL/URN
   * Makes HTTP request to the source website
   * Parses HTML response
   * Extracts relevant information
4. **API Controller** processes the response:
   * Formats the data
   * Handles any errors
   * Returns JSON response to client
5. **Client renders** the retrieved information:
   * Displays article text
   * Shows legal commentary
   * Provides navigation options

### Streaming Response Pattern

For article text streaming (`/stream_article_text`):

1. Client sends request
2. Server processes article requests one by one
3. Server sends each result as it becomes available
4. Client processes and displays each result incrementally

## Technical Features

### Asynchronous Processing

The application leverages Python's `asyncio` for asynchronous processing:

* Concurrent HTTP requests
* Non-blocking I/O operations
* Efficient handling of multiple simultaneous requests

### Caching

Uses `aiocache` for caching frequently accessed data:

* Document content
* Tree structures
* URN mappings
* API responses

### Rate Limiting

Implements rate limiting to prevent abuse:

* Tracks requests by IP address
* Configurable limits (requests per time window)
* Returns 429 status code when limit exceeded

### Error Handling

Comprehensive error handling:

* Graceful degradation
* Client-friendly error messages
* Detailed server-side logging
* Custom exception classes

### Web Scraping

Sophisticated web scraping techniques:

* HTML parsing with BeautifulSoup
* Headless browsing with Selenium
* Regular expressions for text extraction
* Robust error handling

## Frontend Features

The web interface provides:

1. **Form-based searching** for legal documents
2. **Dynamic results display** with collapsible sections
3. **Tabs for multiple articles** with drag-and-drop reordering
4. **WYSIWYG editing** of article text with CKEditor
5. **Search history** tracking and filtering
6. **PDF export** functionality
7. **Pin/unpin capability** for important articles
8. **Responsive design** for different screen sizes

## Deployment Considerations

The application is designed to be deployed as:

* A standalone ASGI service (using Quart)
* Behind a reverse proxy (like Nginx)
* With optional authentication layer
* In a containerized environment (Docker)

## Dependencies

Major dependencies include:

* **quart/quart_cors** : ASGI web framework
* **aiohttp** : Asynchronous HTTP client
* **aiocache** : Asynchronous caching
* **beautifulsoup4** : HTML parsing
* **selenium/chromium** : Web automation for PDF export
* **structlog** : Structured logging

## Conclusion

VisuaLexWeb is a sophisticated API-driven application for retrieving, processing, and displaying legal documents. Its asynchronous architecture, comprehensive error handling, and modular design make it a robust solution for legal research and document retrieval.

The system effectively bridges multiple data sources through a unified interface, providing both programmatic API access and a user-friendly web interface for exploring legal documents.
