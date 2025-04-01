/**
 * annotate.js - Script migliorato per la funzionalità di annotazione v2.4.0
 *
 * Gestisce le interazioni utente per l'annotazione di documenti: selezione testo,
 * creazione/eliminazione/visualizzazione annotazioni, filtri, zoom, modalità clean.
 * Applica best practice per efficienza, manutenibilità e UX.
 *
 * @version 2.4.0
 * @author NER-Giuridico Team (Revisione: AI Assistant)
 */

// === Costanti Configurabili ===
const ANNOTATOR_CONSTANTS = {
    API_SAVE: '/api/save_annotation',
    API_DELETE: '/api/delete_annotation',
    API_RECOGNIZE: '/api/recognize',
    API_CLEAR: '/api/clear_annotations',
    DEBOUNCE_SEARCH_MS: 300,
    STATUS_MESSAGE_TIMEOUT_MS: 5000,
    HIGHLIGHT_FLASH_DURATION_MS: 800,
    HIGHLIGHT_FADE_DURATION_MS: 300,
    SHORTCUT_HIGHLIGHT_DURATION_MS: 500,
    ZOOM_STEP: 0.1,
    MAX_ZOOM: 2.0,
    MIN_ZOOM: 0.8,
    DEFAULT_ZOOM: 1.05, // rem
    // Selettori CSS (centralizzati per facilitare la manutenzione)
    SELECTOR_TEXT_CONTENT: '#text-content',
    SELECTOR_ENTITY_TYPE: '.entity-type',
    SELECTOR_CLEAR_SELECTION_BTN: '#clear-selection',
    SELECTOR_AUTO_ANNOTATE_BTN: '#auto-annotate',
    SELECTOR_ANNOTATIONS_CONTAINER: '#annotations-container',
    SELECTOR_SEARCH_ANNOTATIONS: '#search-annotations',
    SELECTOR_ANNOTATION_STATUS: '#annotation-status',
    SELECTOR_ANNOTATION_COUNT: '#annotation-count',
    SELECTOR_VISIBLE_COUNT: '#visible-count',
    SELECTOR_ANNOTATION_PROGRESS: '#annotation-progress',
    SELECTOR_NO_ANNOTATIONS_MSG: '#no-annotations',
    SELECTOR_CLEAN_MODE_TOGGLE: '#clean-mode-toggle',
    SELECTOR_ZOOM_IN_BTN: '#zoom-in',
    SELECTOR_ZOOM_OUT_BTN: '#zoom-out',
    SELECTOR_RESET_ZOOM_BTN: '#reset-zoom',
    SELECTOR_ANNOTATION_ITEM: '.annotation-item',
    SELECTOR_ENTITY_HIGHLIGHT: '.entity-highlight',
    SELECTOR_DELETE_ANNOTATION_BTN: '.delete-annotation',
    SELECTOR_JUMP_TO_ANNOTATION_BTN: '.jump-to-annotation',
    SELECTOR_SORT_ANNOTATIONS_BTN: '.sort-annotations',
    // Classi CSS
    CLASS_SELECTED: 'selected',
    CLASS_FOCUSED: 'focused',
    CLASS_HIGHLIGHT: 'highlight',
    CLASS_D_NONE: 'd-none', // Bootstrap 'display: none'
    CLASS_FADE_OUT: 'fade-out',
    CLASS_REMOVING: 'removing',
    CLASS_OVERLAP: 'overlap',
    CLASS_LOADING: 'loading',
    CLASS_CLEAN_MODE: 'clean-mode',
    CLASS_SHORTCUT_HIGHLIGHT: 'shortcut-highlight',
};

/**
 * Sistema di logging migliorato per l'applicazione di annotazione.
 */
const AnnotationLogger = {
    debugMode: window.location.search.includes('debug=true'), // Abilita con ?debug=true nell'URL

    _log: function(level, message, data) {
        const prefix = `[Annotator]`;
        const icons = { info: 'ℹ️', debug: '🔍', warn: '⚠️', error: '❌' };
        const logFn = console[level] || console.log;

        if (level === 'debug' && !this.debugMode) return;

        if (data) {
            logFn(`${icons[level]} ${prefix} ${message}`, data);
        } else {
            logFn(`${icons[level]} ${prefix} ${message}`);
        }
    },

    info: function(message, data) { this._log('info', message, data); },
    debug: function(message, data) { this._log('debug', message, data); },
    warn: function(message, data) { this._log('warn', message, data); },
    error: function(message, error) {
        this._log('error', message, error);
        if (error instanceof Error && error.stack) {
            console.error(error.stack);
        }
    },

    startOperation: function(operation) {
        if (this.debugMode) {
            this.debug(`Iniziata operazione: ${operation}`);
            console.time(`⏱️ [Annotator] ${operation}`);
        }
    },

    endOperation: function(operation) {
        if (this.debugMode) {
            console.timeEnd(`⏱️ [Annotator] ${operation}`);
            this.debug(`Completata operazione: ${operation}`);
        }
    }
};

// Namespace per la gestione delle annotazioni
const AnnotationManager = {
    // Stato principale dell'applicazione - fonte di verità
    state: {
        // Dati persistenti
        selectedType: null,
        annotations: [], // Array di oggetti { id, text, type, start, end, color }
        docId: null,
        docText: '',
        originalTextSize: ANNOTATOR_CONSTANTS.DEFAULT_ZOOM,
        currentTextSize: ANNOTATOR_CONSTANTS.DEFAULT_ZOOM,
        isCleanMode: localStorage.getItem('ner-clean-mode') === 'true', // Carica stato da localStorage

        // Stato temporaneo UI
        pendingOperations: 0,
        highlightedAnnotationId: null, // ID dell'annotazione evidenziata nel testo
        selectedAnnotationId: null,  // ID dell'annotazione selezionata nella lista
        lastSavedAt: null,
        statusTimeoutId: null, // ID del timeout per nascondere il messaggio di stato

        // Prefiltro per le annotazioni visibili
        filterText: '',
        filterEntityType: null, // Non implementato nel codice originale, ma presente nello stato
        currentSortBy: 'position', // Criterio di ordinamento corrente
    },

    // Cache elementi DOM
    elements: {},

    // Utility esterna (assumiamo sia globale)
    utils: window.NERGiuridico || { // Fallback di base se NERGiuridico non è definito
        debounce: (func, wait) => {
            let timeout;
            return function executedFunction(...args) {
                const later = () => {
                    clearTimeout(timeout);
                    func.apply(this, args);
                };
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
            };
        },
        showNotification: (message, type) => console.log(`[${type}] ${message}`),
        showConfirmation: (title, message, callback) => { if (confirm(`${title}\n${message}`)) callback(); },
        showLoading: (element, text) => { if(element) element.textContent = text || 'Loading...'; element.disabled = true; },
        hideLoading: (element, originalText) => { if(element) element.textContent = originalText || 'Submit'; element.disabled = false; },
        isOverlapping: (start1, end1, start2, end2) => (start1 < end2 && end1 > start2),
    },

    /**
     * Inizializza il gestore delle annotazioni.
     */
    init: function() {
        AnnotationLogger.startOperation('inizializzazione');

        if (!this.cacheDOMElements()) {
            AnnotationLogger.error('Inizializzazione fallita: elementi DOM essenziali mancanti.');
            return; // Interrompe l'inizializzazione se mancano elementi chiave
        }

        this.state.docId = this.elements.textContent?.dataset.docId;
        this.state.docText = this.elements.textContent?.textContent ?? ''; // Usa textContent per il testo puro

        if (!this.state.docId) {
            AnnotationLogger.error('ID documento mancante (data-doc-id). Funzionalità limitate.');
        }

        this.loadInitialAnnotations(); // Carica da DOM o da altra fonte se necessario
        this.setupEventHandlers();
        this.addDynamicStyles(); // Aggiunge stili CSS necessari
        this.applyInitialUISettings(); // Applica zoom, clean mode, etc.
        this.highlightAnnotations(); // Evidenzia le annotazioni caricate
        this.updateUI(); // Aggiorna contatori, progress bar, etc.

        AnnotationLogger.info('Annotation Manager inizializzato con successo.');
        AnnotationLogger.debug(`Documento ID: ${this.state.docId}, ${this.state.annotations.length} annotazioni caricate.`);
        AnnotationLogger.endOperation('inizializzazione');
    },

    /**
     * Memorizza gli elementi DOM principali nella cache.
     * @returns {boolean} True se gli elementi essenziali sono stati trovati, altrimenti False.
     */
    cacheDOMElements: function() {
        this.elements = {
            textContent: document.querySelector(ANNOTATOR_CONSTANTS.SELECTOR_TEXT_CONTENT),
            entityTypes: document.querySelectorAll(ANNOTATOR_CONSTANTS.SELECTOR_ENTITY_TYPE),
            clearSelectionBtn: document.querySelector(ANNOTATOR_CONSTANTS.SELECTOR_CLEAR_SELECTION_BTN),
            autoAnnotateBtn: document.querySelector(ANNOTATOR_CONSTANTS.SELECTOR_AUTO_ANNOTATE_BTN),
            annotationsContainer: document.querySelector(ANNOTATOR_CONSTANTS.SELECTOR_ANNOTATIONS_CONTAINER),
            searchAnnotations: document.querySelector(ANNOTATOR_CONSTANTS.SELECTOR_SEARCH_ANNOTATIONS),
            annotationStatus: document.querySelector(ANNOTATOR_CONSTANTS.SELECTOR_ANNOTATION_STATUS),
            annotationCount: document.querySelector(ANNOTATOR_CONSTANTS.SELECTOR_ANNOTATION_COUNT),
            visibleCount: document.querySelector(ANNOTATOR_CONSTANTS.SELECTOR_VISIBLE_COUNT),
            annotationProgress: document.querySelector(ANNOTATOR_CONSTANTS.SELECTOR_ANNOTATION_PROGRESS),
            noAnnotationsMsg: document.querySelector(ANNOTATOR_CONSTANTS.SELECTOR_NO_ANNOTATIONS_MSG),
            cleanModeToggle: document.querySelector(ANNOTATOR_CONSTANTS.SELECTOR_CLEAN_MODE_TOGGLE),
            zoomInBtn: document.querySelector(ANNOTATOR_CONSTANTS.SELECTOR_ZOOM_IN_BTN),
            zoomOutBtn: document.querySelector(ANNOTATOR_CONSTANTS.SELECTOR_ZOOM_OUT_BTN),
            resetZoomBtn: document.querySelector(ANNOTATOR_CONSTANTS.SELECTOR_RESET_ZOOM_BTN),
        };

        // Verifica elementi essenziali
        if (!this.elements.textContent || !this.elements.annotationsContainer) {
            AnnotationLogger.error('Elementi DOM essenziali (#text-content o #annotations-container) non trovati.');
            return false;
        }
        return true;
    },

    /**
     * Applica le impostazioni iniziali dell'interfaccia utente (zoom, clean mode).
     */
    applyInitialUISettings: function() {
        // Applica zoom iniziale
        this.elements.textContent.style.fontSize = `${this.state.currentTextSize}rem`;

        // Applica clean mode iniziale
        if (this.state.isCleanMode) {
            document.body.classList.add(ANNOTATOR_CONSTANTS.CLASS_CLEAN_MODE);
            this.updateCleanModeButton(true);
        }

        // Imposta il pulsante di ordinamento attivo iniziale
        document.querySelector(`${ANNOTATOR_CONSTANTS.SELECTOR_SORT_ANNOTATIONS_BTN}[data-sort="${this.state.currentSortBy}"]`)?.classList.add('active');
    },


    /**
     * Carica le annotazioni iniziali (attualmente dal DOM, potrebbe essere da API).
     */
    loadInitialAnnotations: function() {
        AnnotationLogger.startOperation('loadInitialAnnotations');
        this.state.annotations = [];
        const items = this.elements.annotationsContainer?.querySelectorAll(ANNOTATOR_CONSTANTS.SELECTOR_ANNOTATION_ITEM) ?? [];

        AnnotationLogger.debug(`Trovati ${items.length} elementi annotazione nel DOM.`);

        items.forEach((item, index) => {
            try {
                const id = item.dataset.id;
                const text = item.querySelector('.annotation-text')?.textContent ?? '';
                const type = item.dataset.type;
                const start = parseInt(item.dataset.start, 10);
                const end = parseInt(item.dataset.end, 10);
                const color = item.querySelector('.annotation-type')?.style.backgroundColor ?? this.getEntityColorById(type); // Prendi colore da badge o ricalcola

                if (!id || !type || isNaN(start) || isNaN(end)) {
                    throw new Error(`Dati mancanti o non validi nell'elemento #${index + 1}`);
                }

                this.state.annotations.push({ id, text, type, start, end, color });
                AnnotationLogger.debug(`Caricata annotazione #${index + 1}`, { id, type, start, end });

            } catch (error) {
                AnnotationLogger.error(`Errore nel caricamento dell'annotazione #${index + 1} dal DOM`, error);
            }
        });

        // Ordina sempre per posizione all'inizio
        this.state.annotations = this.sortAnnotationsByPosition(this.state.annotations);

        AnnotationLogger.debug(`Caricate ${this.state.annotations.length} annotazioni valide.`);
        AnnotationLogger.endOperation('loadInitialAnnotations');
    },

    /**
     * Configura tutti gli event handlers.
     */
    setupEventHandlers: function() {
        AnnotationLogger.debug('Configurazione event handlers');

        // --- Tipi di Entità ---
        this.elements.entityTypes?.forEach(entityType => {
            entityType.addEventListener('click', () => this.selectEntityType(entityType));
        });

        // --- Selezione Testo ---
        this.elements.textContent?.addEventListener('mouseup', (e) => this.handleTextSelection(e));
        // Aggiunta gestione click su highlight esistenti (delegato)
        this.elements.textContent?.addEventListener('click', (e) => this.handleHighlightClick(e));

        // --- Pulsanti Azione ---
        this.elements.clearSelectionBtn?.addEventListener('click', () => this.clearSelection());
        this.elements.autoAnnotateBtn?.addEventListener('click', () => this.performAutoAnnotation());
        this.elements.cleanModeToggle?.addEventListener('click', () => this.toggleCleanMode());

        // --- Zoom ---
        this.elements.zoomInBtn?.addEventListener('click', () => this.zoomIn());
        this.elements.zoomOutBtn?.addEventListener('click', () => this.zoomOut());
        this.elements.resetZoomBtn?.addEventListener('click', () => this.resetZoom());

        // --- Lista Annotazioni (Delegato) ---
        this.elements.annotationsContainer?.addEventListener('click', (e) => this.handleAnnotationContainerClick(e));

        // --- Ricerca Annotazioni ---
        if (this.elements.searchAnnotations) {
            const debouncedSearch = this.utils.debounce(() => this.filterAnnotations(), ANNOTATOR_CONSTANTS.DEBOUNCE_SEARCH_MS);
            this.elements.searchAnnotations.addEventListener('input', debouncedSearch);
        }

        // --- Ordinamento Annotazioni (Delegato su document) ---
        document.addEventListener('click', (e) => {
            const sortBtn = e.target.closest(ANNOTATOR_CONSTANTS.SELECTOR_SORT_ANNOTATIONS_BTN);
            if (sortBtn) {
                const sortBy = sortBtn.dataset.sort;
                if (sortBy && sortBy !== this.state.currentSortBy) {
                    this.sortAnnotationList(sortBy);
                    // Aggiorna stato UI pulsanti
                    document.querySelectorAll(ANNOTATOR_CONSTANTS.SELECTOR_SORT_ANNOTATIONS_BTN).forEach(btn => btn.classList.remove('active'));
                    sortBtn.classList.add('active');
                    this.state.currentSortBy = sortBy;
                }
            }
        });

        // --- Scorciatoie da Tastiera ---
        document.addEventListener('keydown', (e) => this.handleKeyDown(e));

        // Focus su ricerca con '/'
        document.addEventListener('keydown', (e) => {
            if (e.key === '/' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') {
                e.preventDefault();
                this.elements.searchAnnotations?.focus();
            }
        });
    },

    /**
     * Gestisce i click all'interno del contenitore delle annotazioni (delegato).
     * @param {Event} e - L'evento click.
     */
    handleAnnotationContainerClick: function(e) {
        const deleteBtn = e.target.closest(ANNOTATOR_CONSTANTS.SELECTOR_DELETE_ANNOTATION_BTN);
        const jumpBtn = e.target.closest(ANNOTATOR_CONSTANTS.SELECTOR_JUMP_TO_ANNOTATION_BTN);
        const annotationItem = e.target.closest(ANNOTATOR_CONSTANTS.SELECTOR_ANNOTATION_ITEM);

        if (deleteBtn) {
            const annotationId = deleteBtn.dataset.id;
            if (annotationId) this.deleteAnnotation(annotationId);
            return;
        }

        if (jumpBtn) {
            const annotationId = jumpBtn.dataset.id;
            if (annotationId) this.jumpToAnnotationInText(annotationId);
            return;
        }

        if (annotationItem) {
            const annotationId = annotationItem.dataset.id;
            if (!annotationId) return;

            const isSelected = annotationItem.classList.contains(ANNOTATOR_CONSTANTS.CLASS_SELECTED);

            // Deseleziona tutti gli altri
            this.elements.annotationsContainer?.querySelectorAll(`${ANNOTATOR_CONSTANTS.SELECTOR_ANNOTATION_ITEM}.${ANNOTATOR_CONSTANTS.CLASS_SELECTED}`)
                .forEach(item => item.classList.remove(ANNOTATOR_CONSTANTS.CLASS_SELECTED));

            // Seleziona/Deseleziona questo
            if (!isSelected) {
                annotationItem.classList.add(ANNOTATOR_CONSTANTS.CLASS_SELECTED);
                this.state.selectedAnnotationId = annotationId;
                this.jumpToAnnotationInText(annotationId); // Salta anche nel testo quando si seleziona dalla lista
            } else {
                this.state.selectedAnnotationId = null;
                // Opzionale: rimuovere focus dal testo se si deseleziona dalla lista
                this.removeTextFocus();
            }
        }
    },

    /**
     * Gestisce il click su un'evidenziazione nel testo (delegato).
     * @param {Event} e - L'evento click.
     */
    handleHighlightClick: function(e) {
        const highlight = e.target.closest(ANNOTATOR_CONSTANTS.SELECTOR_ENTITY_HIGHLIGHT);
        if (!highlight) {
            // Se si clicca fuori da un highlight, rimuovi il focus
            this.removeTextFocus();
            return;
        }

        const annotationId = highlight.dataset.id;
        if (!annotationId) return;

        // Rimuovi focus da altri highlight
        this.removeTextFocus(highlight); // Passa l'elemento corrente per non rimuovere il focus da esso

        // Aggiungi focus a questo
        highlight.classList.add(ANNOTATOR_CONSTANTS.CLASS_FOCUSED);
        this.state.highlightedAnnotationId = annotationId;

        // Seleziona e scorri nella lista laterale
        this.jumpToAnnotationInList(annotationId);
    },

    /** Rimuove la classe 'focused' da tutti gli highlight nel testo, eccetto uno opzionale. */
    removeTextFocus: function(excludeElement = null) {
        this.elements.textContent?.querySelectorAll(`${ANNOTATOR_CONSTANTS.SELECTOR_ENTITY_HIGHLIGHT}.${ANNOTATOR_CONSTANTS.CLASS_FOCUSED}`)
            .forEach(el => {
                if (el !== excludeElement) {
                    el.classList.remove(ANNOTATOR_CONSTANTS.CLASS_FOCUSED);
                }
            });
        if (!excludeElement) {
            this.state.highlightedAnnotationId = null;
        }
    },

    /**
     * Gestisce la pressione dei tasti per le scorciatoie.
     * @param {KeyboardEvent} e - L'evento keydown.
     */
    handleKeyDown: function(e) {
        // Ignora se l'utente sta scrivendo in input/textarea
        const activeEl = document.activeElement;
        if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA')) {
            // Permetti Escape anche negli input per cancellare la selezione tipo
            if (e.key === 'Escape') {
                 this.clearSelection();
            }
            return;
        }

        switch (e.key) {
            case 'Escape':
                this.clearSelection();
                this.removeTextFocus(); // Rimuove anche il focus dall'highlight nel testo
                // Deseleziona anche l'elemento nella lista
                const selectedItem = this.elements.annotationsContainer?.querySelector(`.${ANNOTATOR_CONSTANTS.CLASS_SELECTED}`);
                selectedItem?.classList.remove(ANNOTATOR_CONSTANTS.CLASS_SELECTED);
                this.state.selectedAnnotationId = null;
                break;

            case 'a': // Alt+A per Auto-Annotate
                if (e.altKey) {
                    e.preventDefault();
                    this.elements.autoAnnotateBtn?.click();
                }
                break;

            case 'f': // Cmd/Ctrl+F per Clean Mode
                 if (e.metaKey || e.ctrlKey) {
                    e.preventDefault();
                    this.elements.cleanModeToggle?.click();
                }
                break;

            case 'ArrowUp':
            case 'ArrowDown': // Shift + Frecce per navigare nella lista annotazioni
                if (e.shiftKey) {
                    e.preventDefault();
                    this.navigateAnnotationList(e.key === 'ArrowUp' ? 'prev' : 'next');
                }
                break;
        }

        // Cmd/Ctrl + Numero per selezionare tipo entità
        if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '9') {
            e.preventDefault();
            const index = parseInt(e.key, 10) - 1;
            const entityType = this.elements.entityTypes?.[index];
            if (entityType) {
                this.selectEntityType(entityType);
                // Feedback visivo
                entityType.classList.add(ANNOTATOR_CONSTANTS.CLASS_SHORTCUT_HIGHLIGHT);
                setTimeout(() => {
                    entityType.classList.remove(ANNOTATOR_CONSTANTS.CLASS_SHORTCUT_HIGHLIGHT);
                }, ANNOTATOR_CONSTANTS.SHORTCUT_HIGHLIGHT_DURATION_MS);
            }
        }
    },

    /**
     * Naviga tra gli elementi visibili nella lista delle annotazioni.
     * @param {'prev' | 'next'} direction - Direzione della navigazione.
     */
    navigateAnnotationList: function(direction) {
        const visibleItems = Array.from(
            this.elements.annotationsContainer?.querySelectorAll(`${ANNOTATOR_CONSTANTS.SELECTOR_ANNOTATION_ITEM}:not(.${ANNOTATOR_CONSTANTS.CLASS_D_NONE})`) ?? []
        );
        if (visibleItems.length === 0) return;

        let currentIndex = -1;
        if (this.state.selectedAnnotationId) {
            currentIndex = visibleItems.findIndex(item => item.dataset.id === this.state.selectedAnnotationId);
        }

        let newIndex;
        if (direction === 'prev') {
            newIndex = currentIndex <= 0 ? visibleItems.length - 1 : currentIndex - 1;
        } else { // next
            newIndex = currentIndex === -1 || currentIndex === visibleItems.length - 1 ? 0 : currentIndex + 1;
        }

        const newItem = visibleItems[newIndex];
        if (newItem) {
            // Simula un click sull'elemento per selezionarlo e fare lo scroll/jump
            // Questo riutilizza la logica di handleAnnotationContainerClick
            newItem.click();
             // Assicurati che sia visibile nella viewport della lista
            newItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    },

    /**
     * Seleziona un tipo di entità.
     * @param {HTMLElement} entityTypeElement - L'elemento DOM del tipo di entità cliccato.
     */
    selectEntityType: function(entityTypeElement) {
        const type = entityTypeElement.dataset.type;
        const name = entityTypeElement.querySelector('.entity-name')?.textContent ?? type;

        // Deseleziona altri tipi
        this.elements.entityTypes?.forEach(et => et.classList.remove(ANNOTATOR_CONSTANTS.CLASS_SELECTED));

        // Seleziona questo tipo
        entityTypeElement.classList.add(ANNOTATOR_CONSTANTS.CLASS_SELECTED);
        this.state.selectedType = type;

        this.updateStatus(`Tipo selezionato: ${name}. Seleziona il testo da annotare.`);
        AnnotationLogger.debug(`Tipo entità selezionato: ${type} (${name})`);
    },

    /**
     * Annulla la selezione del tipo di entità e la selezione del testo.
     */
    clearSelection: function() {
        if (this.state.selectedType) {
            this.elements.entityTypes?.forEach(et => et.classList.remove(ANNOTATOR_CONSTANTS.CLASS_SELECTED));
            this.state.selectedType = null;
            window.getSelection()?.removeAllRanges(); // Usa optional chaining
            this.updateStatus('Selezione tipo annullata.');
            AnnotationLogger.debug('Selezione tipo annullata');
        }
        // Rimuove anche la selezione del testo se presente
        window.getSelection()?.removeAllRanges();
    },

    /**
     * Gestisce la selezione del testo da parte dell'utente.
     * @param {MouseEvent} e - L'evento mouseup.
     */
    handleTextSelection: async function(e) { // Resa async per await potenziale
        // Ignora se si sta modificando il testo (se mai implementato)
        if (this.elements.textContent?.contentEditable === 'true') return;

        const selection = window.getSelection();
        const selectedText = selection?.toString().trim() ?? '';

        // Se non c'è testo selezionato o nessun tipo è attivo, esci
        if (selectedText === '') return;

        if (!this.state.selectedType) {
            this.utils.showNotification('Seleziona prima un tipo di entità dalla lista a sinistra.', 'warning');
            this.updateStatus('ERRORE: Seleziona un tipo di entità prima di annotare!', true);
            selection?.removeAllRanges(); // Rimuovi la selezione visiva
            return;
        }

        try {
            const range = selection.getRangeAt(0);

            // Calcola offset assoluti nel textContent
            const { start, end } = this.getAbsoluteOffsets(range);

            if (start === -1 || end === -1 || start >= end) {
                AnnotationLogger.error('Impossibile calcolare offset validi per la selezione.', { range });
                this.updateStatus('Errore nel calcolo della posizione della selezione.', true);
                selection?.removeAllRanges();
                return;
            }

            const actualSelectedText = this.state.docText.substring(start, end);
            AnnotationLogger.debug(`Nuova selezione: "${actualSelectedText}" (${start}-${end}), Tipo: ${this.state.selectedType}`);

            // Verifica sovrapposizioni
            const overlappingAnnotations = this.state.annotations.filter(ann =>
                this.utils.isOverlapping(start, end, ann.start, ann.end)
            );

            if (overlappingAnnotations.length > 0) {
                AnnotationLogger.warn(`Sovrapposizione rilevata con ${overlappingAnnotations.length} annotazioni esistenti.`);
                // Usa Promise per gestire la conferma in modo asincrono
                const confirmed = await new Promise((resolve) => {
                     this.utils.showConfirmation(
                        'Sovrapposizione Rilevata',
                        `La selezione si sovrappone con ${overlappingAnnotations.length} annotazione/i esistente/i: ${overlappingAnnotations.map(a => `"${a.text}" (${a.type})`).join(', ')}. Continuare comunque?`,
                        () => resolve(true), // Callback per 'Conferma'
                        'Continua',
                        'btn-warning',
                        () => resolve(false) // Callback per 'Annulla' (aggiunto a showConfirmation se non presente)
                    );
                 });

                if (!confirmed) {
                    AnnotationLogger.debug('Creazione annotazione annullata dall\'utente a causa di sovrapposizione.');
                    selection?.removeAllRanges(); // Rimuovi selezione visiva
                    this.updateStatus('Creazione annullata.');
                    return;
                }
                AnnotationLogger.debug('Utente ha confermato la creazione nonostante la sovrapposizione.');
            }

            // Crea l'annotazione (passa alla funzione che chiama l'API)
            this.createAnnotation(start, end, actualSelectedText, this.state.selectedType);

        } catch (error) {
            AnnotationLogger.error("Errore durante la gestione della selezione del testo:", error);
            this.updateStatus('Errore imprevisto durante la selezione.', true);
        } finally {
             // Pulisci sempre la selezione del testo dopo il tentativo, tranne se annullato per mancanza di tipo
             if (this.state.selectedType) {
                 selection?.removeAllRanges();
             }
        }
    },

    /**
     * Calcola gli offset di inizio e fine assoluti di un Range rispetto a textContent.
     * @param {Range} range - L'oggetto Range della selezione.
     * @returns {{start: number, end: number}} Oggetto con offset di inizio e fine (-1 se errore).
     */
    getAbsoluteOffsets: function(range) {
        const container = this.elements.textContent;
        if (!container) return { start: -1, end: -1 };

        const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
        let charCount = 0;
        let start = -1;
        let end = -1;
        let node;

        // Trova l'offset di inizio
        while ((node = walker.nextNode()) && start === -1) {
            if (node === range.startContainer) {
                start = charCount + range.startOffset;
            } else {
                charCount += node.textContent?.length ?? 0;
            }
        }

        // Resetta e trova l'offset di fine
        walker.currentNode = container; // Resetta il walker all'inizio
        charCount = 0;
        while ((node = walker.nextNode()) && end === -1) {
            if (node === range.endContainer) {
                end = charCount + range.endOffset;
            } else {
                 charCount += node.textContent?.length ?? 0;
            }
        }

        // Caso speciale: la selezione potrebbe iniziare e finire nello stesso nodo Text
        if (start !== -1 && end === -1 && range.startContainer === range.endContainer) {
             end = start + (range.endOffset - range.startOffset);
        }

        // Caso speciale: la selezione attraversa nodi non-text (es. <br> o span esistenti)
        // Questo metodo basato su TreeWalker(SHOW_TEXT) conta solo i caratteri testuali.
        // Se la selezione attraversa elementi non testuali, gli offset potrebbero non corrispondere
        // perfettamente al `range.toString().length`. Usiamo il testo estratto da `substring` come testo reale.

        return { start, end };
    },


    /**
     * Prepara e avvia il salvataggio di una nuova annotazione.
     * @param {number} start - Offset di inizio.
     * @param {number} end - Offset di fine.
     * @param {string} text - Testo annotato.
     * @param {string} type - Tipo di entità.
     */
    createAnnotation: function(start, end, text, type) {
        AnnotationLogger.debug(`Preparazione creazione annotazione: ${type}, "${text}" (${start}-${end})`);
        const annotationData = { start, end, text, type };
        this.updateStatus('Salvataggio annotazione in corso...');
        this.saveAnnotation(annotationData); // Chiama la funzione asincrona
    },

    /**
     * Salva una nuova annotazione tramite API (usando async/await).
     * @param {object} annotationData - Dati dell'annotazione da salvare {start, end, text, type}.
     */
    saveAnnotation: async function(annotationData) {
        AnnotationLogger.startOperation('saveAnnotation');
        this.startPendingOperation();

        try {
            AnnotationLogger.debug('Invio richiesta salvataggio annotazione', annotationData);
            const response = await fetch(ANNOTATOR_CONSTANTS.API_SAVE, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify({
                    doc_id: this.state.docId,
                    annotation: annotationData
                })
            });

            const data = await response.json(); // Legge il corpo della risposta solo una volta

            if (!response.ok) {
                // Lancia un errore per essere catturato dal blocco catch
                throw new Error(data.message || `Errore HTTP: ${response.status}`);
            }

            if (data.status === 'success' && data.annotation) {
                AnnotationLogger.info('Annotazione salvata con successo', data.annotation);

                // Aggiungi colore all'annotazione ricevuta (se non già presente)
                if (!data.annotation.color) {
                    data.annotation.color = this.getEntityColorById(data.annotation.type);
                }

                // Aggiungi alla lista interna e riordina
                this.state.annotations.push(data.annotation);
                this.state.annotations = this.sortAnnotationsByPosition(this.state.annotations);

                // Aggiorna UI (lista e highlighting)
                this.addAnnotationToDOM(data.annotation); // Aggiunge alla lista visibile
                this.highlightAnnotations(); // Ridisegna le evidenziazioni nel testo
                this.updateUI(); // Aggiorna contatori, etc.

                this.utils.showNotification('Annotazione salvata!', 'success');
                this.updateStatus('Annotazione salvata con successo.');
                this.state.lastSavedAt = new Date();

            } else {
                // Errore logico dal backend
                throw new Error(data.message || 'Risposta API non valida o fallita.');
            }

        } catch (error) {
            AnnotationLogger.error('Errore durante il salvataggio dell\'annotazione', error);
            this.utils.showNotification(`Errore salvataggio: ${error.message}`, 'danger');
            this.updateStatus(`ERRORE: ${error.message}`, true);
            // Considerare se è necessario un rollback dello stato qui
        } finally {
            this.endPendingOperation();
            AnnotationLogger.endOperation('saveAnnotation');
        }
    },

    /**
     * Elimina un'annotazione tramite API (usando async/await e UI ottimistica).
     * @param {string} annotationId - L'ID dell'annotazione da eliminare.
     */
    deleteAnnotation: async function(annotationId) {
        AnnotationLogger.debug(`Richiesta eliminazione annotazione ID: ${annotationId}`);

        const annotationIndex = this.state.annotations.findIndex(a => a.id === annotationId);
        if (annotationIndex === -1) {
            AnnotationLogger.warn(`Tentativo di eliminare annotazione non trovata nello stato: ${annotationId}`);
            return;
        }
        const annotationToRemove = this.state.annotations[annotationIndex];

        // Conferma utente (asincrona)
        const confirmed = await new Promise((resolve) => {
            this.utils.showConfirmation(
                'Elimina Annotazione',
                `Sei sicuro di voler eliminare l'annotazione "${annotationToRemove.text}" (${annotationToRemove.type})?`,
                () => resolve(true),
                'Elimina',
                'btn-danger',
                 () => resolve(false)
            );
        });

        if (!confirmed) {
            AnnotationLogger.debug('Eliminazione annullata dall\'utente.');
            return;
        }

        AnnotationLogger.startOperation('deleteAnnotation');
        this.startPendingOperation();

        // --- UI Ottimistica ---
        // 1. Rimuovi dalla lista interna
        this.state.annotations.splice(annotationIndex, 1);

        // 2. Rimuovi dalla lista nel DOM con animazione
        const annotationItem = this.elements.annotationsContainer?.querySelector(`${ANNOTATOR_CONSTANTS.SELECTOR_ANNOTATION_ITEM}[data-id="${annotationId}"]`);
        if (annotationItem) {
            annotationItem.classList.add(ANNOTATOR_CONSTANTS.CLASS_FADE_OUT);
            setTimeout(() => {
                annotationItem.remove();
                this.updateVisibleCount(); // Aggiorna solo il contatore visibile dopo la rimozione
            }, ANNOTATOR_CONSTANTS.HIGHLIGHT_FADE_DURATION_MS);
        }

        // 3. Rimuovi (o marca per rimozione) l'highlight nel testo
        //    Ridisegnare tutto è più semplice e garantisce coerenza dopo la rimozione
        this.highlightAnnotations(); // Ridisegna senza l'annotazione rimossa

        // 4. Aggiorna contatori generali (dopo la rimozione dallo stato)
        this.updateUI(); // Aggiorna tutti i contatori e la progress bar

        this.updateStatus('Annotazione eliminata (in attesa conferma server)...');
        // --- Fine UI Ottimistica ---

        try {
            AnnotationLogger.debug(`Invio richiesta eliminazione per ID: ${annotationId}`);
            const response = await fetch(ANNOTATOR_CONSTANTS.API_DELETE, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify({
                    doc_id: this.state.docId,
                    annotation_id: annotationId
                })
            });

            const data = await response.json();

            if (!response.ok || data.status !== 'success') {
                 throw new Error(data.message || `Errore API durante l'eliminazione (HTTP ${response.status})`);
            }

            // Successo confermato dal server
            AnnotationLogger.info(`Eliminazione confermata dal server per ID: ${annotationId}`);
            this.utils.showNotification('Annotazione eliminata definitivamente.', 'success');
            this.updateStatus('Annotazione eliminata con successo.');
            // Lo stato è già aggiornato ottimisticamente

        } catch (error) {
            AnnotationLogger.error('Errore durante l\'eliminazione definitiva dell\'annotazione', error);
            this.utils.showNotification(`Errore eliminazione: ${error.message}. Ripristino stato.`, 'danger');
            this.updateStatus(`ERRORE: ${error.message}. Tentativo di ripristino.`, true);

            // --- Rollback dell'UI Ottimistica ---
            // Ricarica le annotazioni dallo stato precedente (o ricarica tutto per sicurezza)
            // Qui scegliamo di ricaricare tutto per semplicità, assumendo che `loadInitialAnnotations`
            // possa essere chiamato di nuovo o che ci sia un modo per ottenere lo stato aggiornato dal server.
            // Se `loadInitialAnnotations` legge solo dal DOM iniziale, questo non funzionerà.
            // Un approccio migliore sarebbe salvare lo stato prima dell'operazione ottimistica.
            // Per ora, ricarichiamo e ridisegnamo:
            AnnotationLogger.warn('Tentativo di rollback ricaricando le annotazioni...');
            this.loadInitialAnnotations(); // Ricarica dal DOM (potrebbe non essere lo stato server attuale!)
            this.highlightAnnotations();
            this.renderAnnotationList(); // Ridisegna l'intera lista
            this.updateUI();
            // --- Fine Rollback ---

        } finally {
            this.endPendingOperation();
            AnnotationLogger.endOperation('deleteAnnotation');
        }
    },

    /**
     * Esegue il riconoscimento automatico delle entità (async/await).
     */
    performAutoAnnotation: async function() {
        if (!this.elements.autoAnnotateBtn || this.elements.autoAnnotateBtn.disabled) return;

        const textToAnnotate = this.state.docText;
        if (!textToAnnotate) {
            this.utils.showNotification('Nessun testo da analizzare.', 'warning');
            return;
        }

        // Conferma utente
        const confirmed = await new Promise((resolve) => {
            this.utils.showConfirmation(
                'Riconoscimento Automatico',
                'Vuoi eseguire il riconoscimento automatico delle entità nel testo? Le annotazioni trovate verranno aggiunte a quelle esistenti. Il processo potrebbe richiedere alcuni secondi.',
                () => resolve(true),
                'Procedi',
                'btn-primary',
                 () => resolve(false)
            );
        });

        if (!confirmed) {
            AnnotationLogger.debug('Auto-annotazione annullata dall\'utente.');
            return;
        }

        AnnotationLogger.startOperation('autoAnnotation');
        this.startPendingOperation();
        const originalButtonText = this.elements.autoAnnotateBtn.innerHTML; // Salva testo originale bottone
        this.utils.showLoading(this.elements.autoAnnotateBtn, 'Analisi...');
        this.updateStatus('Riconoscimento automatico in corso...');

        try {
            const response = await fetch(ANNOTATOR_CONSTANTS.API_RECOGNIZE, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify({ text: textToAnnotate, doc_id: this.state.docId }) // Invia anche doc_id se utile al backend
            });

            const data = await response.json();

            if (!response.ok || data.status !== 'success') {
                throw new Error(data.message || `Errore API durante il riconoscimento (HTTP ${response.status})`);
            }

            const entities = data.entities || [];
            AnnotationLogger.info(`Riconosciute ${entities.length} entità automaticamente.`);

            if (entities.length === 0) {
                this.utils.showNotification('Nessuna nuova entità riconosciuta automaticamente.', 'info');
                this.updateStatus('Nessuna entità riconosciuta.');
                this.utils.hideLoading(this.elements.autoAnnotateBtn, originalButtonText);
                this.endPendingOperation(); // Termina operazione qui se non ci sono entità
                AnnotationLogger.endOperation('autoAnnotation');
                return; // Esce dalla funzione
            }

            // Filtra entità che non si sovrappongono *esattamente* a quelle esistenti
            // (Potrebbe essere più complesso: permettere sovrapposizioni parziali? Ignorarle?)
            // Qui, per semplicità, aggiungiamo solo quelle che non hanno un match esatto start/end/type
            const existingSignatures = new Set(this.state.annotations.map(a => `${a.start}-${a.end}-${a.type}`));
            const newEntities = entities.filter(e => !existingSignatures.has(`${e.start}-${e.end}-${e.type}`));

            if (newEntities.length === 0) {
                 this.utils.showNotification('Nessuna *nuova* entità unica riconosciuta (potrebbero esserci duplicati).', 'info');
                 this.updateStatus('Nessuna nuova entità trovata.');
                 this.utils.hideLoading(this.elements.autoAnnotateBtn, originalButtonText);
                 this.endPendingOperation();
                 AnnotationLogger.endOperation('autoAnnotation');
                 return;
            }

            AnnotationLogger.debug(`Filtrate ${newEntities.length} nuove entità uniche da salvare.`);
            this.updateStatus(`Riconosciute ${entities.length} entità. Salvataggio di ${newEntities.length} nuove in corso...`);

            // Salva le nuove annotazioni una per una (o in batch se l'API lo supporta)
            let savedCount = 0;
            const totalToSave = newEntities.length;

            // Usiamo un loop for...of con await per salvare sequenzialmente
            // Questo è più semplice da leggere di Promise.all o catene .then
            // e previene potenziali race condition se l'ordine conta
            for (const entity of newEntities) {
                this.utils.showLoading(this.elements.autoAnnotateBtn, `<span class="spinner-border spinner-border-sm me-2"></span>Salvataggio ${savedCount + 1}/${totalToSave}...`);
                try {
                    const annotationData = {
                        start: entity.start,
                        end: entity.end,
                        text: entity.text, // Usa il testo dall'entità riconosciuta
                        type: entity.type
                    };
                    // Riutilizza la funzione saveAnnotation esistente
                    await this.saveAnnotation(annotationData); // saveAnnotation gestisce già l'aggiunta allo stato e UI
                    savedCount++;
                } catch (saveError) {
                    // Se un salvataggio fallisce, logga l'errore e continua con gli altri
                    AnnotationLogger.error(`Errore salvataggio entità automatica: ${entity.text}`, saveError);
                    this.utils.showNotification(`Errore salvataggio "${entity.text}". Continuo con le altre.`, 'warning');
                    // Non incrementare savedCount
                }
            }

            AnnotationLogger.info(`Salvate ${savedCount} / ${newEntities.length} nuove annotazioni automatiche.`);
            this.utils.hideLoading(this.elements.autoAnnotateBtn, originalButtonText);

            // L'UI (highlighting, lista, contatori) è già stata aggiornata da saveAnnotation
            // Riordina la lista nel DOM se necessario (saveAnnotation aggiunge in cima)
            this.sortAnnotationList(this.state.currentSortBy);

            this.utils.showNotification(`Aggiunte ${savedCount} nuove annotazioni automatiche.`, 'success');
            this.updateStatus(`Completato: aggiunte ${savedCount} nuove annotazioni.`);

        } catch (error) {
            AnnotationLogger.error('Errore durante il processo di auto-annotazione', error);
            this.utils.showNotification(`Errore auto-annotazione: ${error.message}`, 'danger');
            this.updateStatus(`ERRORE auto-annotazione: ${error.message}`, true);
            this.utils.hideLoading(this.elements.autoAnnotateBtn, originalButtonText);
        } finally {
            // Assicurati che endPendingOperation sia chiamato solo una volta
            // Se ci sono state entità, viene chiamato qui. Se non ce n'erano, è stato chiamato prima.
            if (this.state.pendingOperations > 0 && AnnotationLogger.debugMode) { // Controlla se è ancora > 0
                 this.endPendingOperation();
                 AnnotationLogger.endOperation('autoAnnotation');
            } else if (this.state.pendingOperations > 0) {
                 this.endPendingOperation();
            }
        }
    },

    /**
     * Aggiunge un elemento annotazione alla lista nel DOM.
     * @param {object} annotation - L'oggetto annotazione completo {id, text, type, start, end, color}.
     */
    addAnnotationToDOM: function(annotation) {
        if (!this.elements.annotationsContainer) return;

        AnnotationLogger.debug(`Aggiunta annotazione alla lista DOM: ${annotation.id}`, annotation);

        // Nascondi messaggio "nessuna annotazione"
        this.elements.noAnnotationsMsg?.classList.add(ANNOTATOR_CONSTANTS.CLASS_D_NONE);

        // Crea l'elemento HTML
        const annotationItem = document.createElement('div');
        annotationItem.className = `${ANNOTATOR_CONSTANTS.SELECTOR_ANNOTATION_ITEM.substring(1)} card mb-2`; // Usa la costante per la classe base
        annotationItem.dataset.id = annotation.id;
        annotationItem.dataset.start = annotation.start;
        annotationItem.dataset.end = annotation.end;
        annotationItem.dataset.type = annotation.type;
        // Aggiungi attributo per ricerca/filtro testo
        annotationItem.dataset.text = annotation.text.toLowerCase();

        const entityName = this.getEntityNameById(annotation.type);
        const entityColor = annotation.color || this.getEntityColorById(annotation.type); // Usa colore passato o ricalcola

        annotationItem.innerHTML = `
            <div class="card-body p-2">
                <div class="d-flex align-items-start mb-2">
                    <span class="annotation-type badge me-2" style="background-color: ${entityColor}; color: ${this.getContrastColor(entityColor)};">
                        ${this.escapeHtml(entityName)}
                    </span>
                    <span class="annotation-text flex-grow-1 small" title="${this.escapeHtml(annotation.text)}">${this.escapeHtml(this.truncateText(annotation.text, 100))}</span>
                </div>
                <div class="annotation-actions d-flex justify-content-end">
                    <button class="btn btn-sm btn-outline-secondary ${ANNOTATOR_CONSTANTS.SELECTOR_JUMP_TO_ANNOTATION_BTN.substring(1)} me-1" data-id="${annotation.id}" title="Vai al testo (Shift+Click per selezionare)">
                        <i class="fas fa-crosshairs"></i> <!-- Icona più adatta per 'jump to' -->
                    </button>
                    <button class="btn btn-sm btn-outline-danger ${ANNOTATOR_CONSTANTS.SELECTOR_DELETE_ANNOTATION_BTN.substring(1)}" data-id="${annotation.id}" title="Elimina annotazione">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            </div>
        `;

        // Aggiungi all'inizio o in base all'ordinamento corrente?
        // Per ora, aggiungiamo all'inizio e poi riordiniamo se necessario.
        this.elements.annotationsContainer.prepend(annotationItem);

        // Evidenzia brevemente il nuovo elemento
        annotationItem.classList.add(ANNOTATOR_CONSTANTS.CLASS_HIGHLIGHT);
        setTimeout(() => {
            annotationItem.classList.remove(ANNOTATOR_CONSTANTS.CLASS_HIGHLIGHT);
        }, 2000);

        // Riordina la lista nel DOM se l'ordinamento non è per posizione (o sempre per coerenza)
        this.sortAnnotationList(this.state.currentSortBy);

        // Non chiamare updateUI() qui, viene chiamato dopo save/delete/load
    },

    /** Ridisegna l'intera lista di annotazioni nel DOM basandosi sullo stato corrente. */
    renderAnnotationList: function() {
        if (!this.elements.annotationsContainer) return;
        AnnotationLogger.debug('Rendering completo della lista annotazioni');

        // Svuota container
        this.elements.annotationsContainer.innerHTML = '';

        // Ordina le annotazioni nello stato secondo il criterio corrente
        const sortedAnnotations = this.sortAnnotationsInState(this.state.annotations, this.state.currentSortBy);

        // Aggiungi ogni annotazione
        if (sortedAnnotations.length > 0) {
            sortedAnnotations.forEach(ann => this.addAnnotationToDOM(ann)); // addAnnotationToDOM ora non riordina più
            this.elements.noAnnotationsMsg?.classList.add(ANNOTATOR_CONSTANTS.CLASS_D_NONE);
        } else {
            this.elements.noAnnotationsMsg?.classList.remove(ANNOTATOR_CONSTANTS.CLASS_D_NONE);
        }
        // Applica filtri correnti
        this.filterAnnotations();
        // Aggiorna contatori (fatto da updateUI chiamato esternamente)
    },


    /**
     * Evidenzia le annotazioni nel testo. Ottimizzato per performance e gestione sovrapposizioni.
     */
    highlightAnnotations: function() {
        AnnotationLogger.startOperation('highlightAnnotations');
        if (!this.elements.textContent) {
            AnnotationLogger.warn('Elemento #text-content non trovato, impossibile evidenziare.');
            AnnotationLogger.endOperation('highlightAnnotations');
            return;
        }

        const text = this.state.docText; // Usa il testo dallo stato

        // Se non ci sono annotazioni o testo, resetta e esci
        if (this.state.annotations.length === 0 || !text) {
            this.elements.textContent.innerHTML = this.escapeHtml(text); // Mostra testo puro
            AnnotationLogger.debug('Nessuna annotazione o testo da evidenziare.');
            AnnotationLogger.endOperation('highlightAnnotations');
            return;
        }

        try {
            // 1. Ordina le annotazioni per posizione (start asc, end desc per sovrapposizioni)
            //    Questo assicura che le annotazioni più lunghe che iniziano prima vengano processate prima.
            const sortedAnnotations = this.sortAnnotationsByPosition(this.state.annotations);

            // 2. Crea i segmenti di testo
            //    Un segmento è una porzione di testo con un array delle annotazioni che lo coprono.
            const segments = this.createTextSegments(text, sortedAnnotations);

            // 3. Costruisci l'HTML
            let htmlContent = '';
            segments.forEach(segment => {
                if (segment.annotations.length === 0) {
                    // Segmento di testo normale
                    htmlContent += this.escapeHtml(segment.text);
                } else {
                    // Segmento coperto da una o più annotazioni
                    // Scegli l'annotazione "primaria" da visualizzare (es. la prima nell'array, che è la più esterna/lunga)
                    const primaryAnnotation = segment.annotations[0];
                    const entityName = this.getEntityNameById(primaryAnnotation.type);
                    const entityColor = primaryAnnotation.color || this.getEntityColorById(primaryAnnotation.type);
                    const contrastColor = this.getContrastColor(entityColor);

                    // Marca se ci sono sovrapposizioni in questo segmento
                    const isOverlap = segment.annotations.length > 1 ? ANNOTATOR_CONSTANTS.CLASS_OVERLAP : '';
                    // Controlla se questa è l'annotazione attualmente "focused"
                    const isFocused = primaryAnnotation.id === this.state.highlightedAnnotationId ? ANNOTATOR_CONSTANTS.CLASS_FOCUSED : '';

                    // Costruisci lo span di evidenziazione
                    // Usiamo data-* attributi per tutte le info necessarie
                    htmlContent += `<span class="${ANNOTATOR_CONSTANTS.SELECTOR_ENTITY_HIGHLIGHT.substring(1)} ${isOverlap} ${isFocused}"
                                          style="background-color: ${entityColor}; color: ${contrastColor}; border-color: ${entityColor};"
                                          data-id="${primaryAnnotation.id}"
                                          data-type="${primaryAnnotation.type}"
                                          data-start="${primaryAnnotation.start}"
                                          data-end="${primaryAnnotation.end}"
                                          title="${this.escapeHtml(entityName)}: ${this.escapeHtml(primaryAnnotation.text)}">`;
                    // Tooltip interno (opzionale, il title è spesso sufficiente)
                    // htmlContent += `<span class="tooltip">${this.escapeHtml(entityName)}: ${this.escapeHtml(primaryAnnotation.text)}</span>`;
                    htmlContent += `${this.escapeHtml(segment.text)}`; // Testo del segmento
                    htmlContent += `</span>`;
                }
            });

            // 4. Aggiorna il DOM (in un colpo solo per performance)
            this.elements.textContent.innerHTML = htmlContent;

            AnnotationLogger.debug(`Evidenziate ${this.state.annotations.length} annotazioni nel testo.`);

            // 5. Post-rendering (opzionale, es. per controlli visivi complessi)
            // this.optimizeTextDisplay(); // La funzione checkForOverlappingHighlights originale usava getBoundingClientRect, che è costoso. L'approccio a segmenti dovrebbe già gestire bene le sovrapposizioni logiche.

        } catch (error) {
            AnnotationLogger.error("Errore critico nell'evidenziazione delle annotazioni:", error);
            // Fallback: mostra testo semplice
            this.elements.textContent.innerHTML = this.escapeHtml(text);
        }

        AnnotationLogger.endOperation('highlightAnnotations');
    },

    /**
     * Crea segmenti di testo basati sulle annotazioni. Gestisce sovrapposizioni.
     * @param {string} text - Il testo completo.
     * @param {Array} sortedAnnotations - Annotazioni ordinate per posizione (start asc, end desc).
     * @returns {Array<{text: string, annotations: Array<object>}>} Array di segmenti.
     */
    createTextSegments: function(text, sortedAnnotations) {
        const segments = [];
        let currentIndex = 0; // Indice corrente nel testo originale
        const activeAnnotations = []; // Stack di annotazioni attive

        // Crea una lista di "eventi": inizio o fine di un'annotazione
        const events = [];
        sortedAnnotations.forEach(ann => {
            events.push({ type: 'start', position: ann.start, annotation: ann });
            events.push({ type: 'end', position: ann.end, annotation: ann });
        });

        // Ordina gli eventi per posizione, poi end prima di start a parità di posizione
        events.sort((a, b) => {
            if (a.position !== b.position) return a.position - b.position;
            if (a.type === 'end' && b.type === 'start') return -1; // Fine prima di inizio
            if (a.type === 'start' && b.type === 'end') return 1;  // Inizio dopo fine
            // Se stesso tipo e stessa posizione (improbabile per start, possibile per end),
            // ordina per lunghezza decrescente dell'annotazione associata (per coerenza)
            const lenA = a.annotation.end - a.annotation.start;
            const lenB = b.annotation.end - b.annotation.start;
            return lenB - lenA;
        });

        // Processa gli eventi per creare i segmenti
        events.forEach(event => {
            // Se c'è testo tra l'indice corrente e la posizione dell'evento
            if (event.position > currentIndex) {
                const segmentText = text.substring(currentIndex, event.position);
                // Aggiungi segmento con le annotazioni attualmente attive (copia dello stack)
                segments.push({ text: segmentText, annotations: [...activeAnnotations] });
                currentIndex = event.position; // Aggiorna indice corrente
            }

            // Aggiorna lo stack di annotazioni attive
            if (event.type === 'start') {
                // Aggiungi l'annotazione allo stack (in cima)
                activeAnnotations.unshift(event.annotation);
            } else { // type === 'end'
                // Rimuovi l'annotazione dallo stack
                const indexToRemove = activeAnnotations.findIndex(a => a.id === event.annotation.id);
                if (indexToRemove !== -1) {
                    activeAnnotations.splice(indexToRemove, 1);
                } else {
                     AnnotationLogger.warn(`Tentativo di rimuovere annotazione non attiva dallo stack: ${event.annotation.id}`);
                }
            }
        });

        // Aggiungi l'eventuale testo rimanente dopo l'ultimo evento
        if (currentIndex < text.length) {
            segments.push({ text: text.substring(currentIndex), annotations: [] });
        }

        // Filtra segmenti vuoti (potrebbero crearsi se start == end o per eventi consecutivi alla stessa posizione)
        return segments.filter(segment => segment.text.length > 0);
    },

    /**
     * Aggiorna il messaggio di stato nell'UI.
     * @param {string} message - Il messaggio da mostrare.
     * @param {boolean} [isError=false] - Se true, mostra come messaggio di errore.
     */
    updateStatus: function(message, isError = false) {
        if (!this.elements.annotationStatus) return;

        // Cancella timeout precedente se esiste
        if (this.state.statusTimeoutId) {
            clearTimeout(this.state.statusTimeoutId);
            this.state.statusTimeoutId = null;
        }

        if (!message) {
            this.elements.annotationStatus.classList.add(ANNOTATOR_CONSTANTS.CLASS_D_NONE);
            return;
        }

        AnnotationLogger.debug(`Stato UI: ${message} ${isError ? '(Errore)' : ''}`);

        this.elements.annotationStatus.textContent = message;
        this.elements.annotationStatus.className = `alert ${isError ? 'alert-danger' : 'alert-info'} mt-2`; // Rimuove d-none e imposta classi alert

        // Nascondi automaticamente dopo un po' (solo se non è un errore persistente?)
        // Manteniamo il timeout per tutti i messaggi per ora.
        this.state.statusTimeoutId = setTimeout(() => {
            this.elements.annotationStatus?.classList.add('fade'); // Usa fade out di Bootstrap se disponibile
             setTimeout(() => { // Attendi fine animazione fade
                 this.elements.annotationStatus?.classList.add(ANNOTATOR_CONSTANTS.CLASS_D_NONE);
                 this.elements.annotationStatus?.classList.remove('fade');
             }, 150); // Durata standard fade Bootstrap
            this.state.statusTimeoutId = null;
        }, ANNOTATOR_CONSTANTS.STATUS_MESSAGE_TIMEOUT_MS);
    },

    /** Aggiorna il contatore totale delle annotazioni. */
    updateAnnotationCount: function() {
        const count = this.state.annotations.length;
        if (this.elements.annotationCount) {
            this.elements.annotationCount.textContent = `(${count})`;
        }
        AnnotationLogger.debug(`Conteggio annotazioni totali: ${count}`);
    },

    /** Aggiorna i contatori per ogni tipo di entità. */
    updateEntityCounters: function() {
        const counts = this.state.annotations.reduce((acc, ann) => {
            acc[ann.type] = (acc[ann.type] || 0) + 1;
            return acc;
        }, {});

        document.querySelectorAll('.entity-counter').forEach(counter => {
            const type = counter.dataset.type;
            counter.textContent = counts[type] || '0';
        });
        AnnotationLogger.debug('Contatori per tipo aggiornati', counts);
    },

    /** Aggiorna la barra di progresso (stima). */
    updateAnnotationProgress: function() {
        if (!this.elements.annotationProgress || !this.elements.textContent) return;

        // Usa una metrica più stabile, es. caratteri annotati / caratteri totali
        const totalChars = this.state.docText.length;
        if (totalChars === 0) {
            this.elements.annotationProgress.style.width = '0%';
            this.elements.annotationProgress.className = 'progress-bar';
            return;
        }

        // Calcola i caratteri unici coperti dalle annotazioni
        const coveredRanges = this.state.annotations.map(a => ({ start: a.start, end: a.end }));
        // Unisci intervalli sovrapposti per contare i caratteri unici
        coveredRanges.sort((a, b) => a.start - b.start);
        const mergedRanges = [];
        if (coveredRanges.length > 0) {
            let currentRange = { ...coveredRanges[0] };
            for (let i = 1; i < coveredRanges.length; i++) {
                const nextRange = coveredRanges[i];
                if (nextRange.start < currentRange.end) { // Sovrapposizione o adiacenza
                    currentRange.end = Math.max(currentRange.end, nextRange.end);
                } else {
                    mergedRanges.push(currentRange);
                    currentRange = { ...nextRange };
                }
            }
            mergedRanges.push(currentRange);
        }
        const coveredChars = mergedRanges.reduce((sum, range) => sum + (range.end - range.start), 0);
        const coverage = totalChars > 0 ? Math.min((coveredChars / totalChars) * 100, 100) : 0;


        this.elements.annotationProgress.style.width = `${coverage.toFixed(1)}%`;
        this.elements.annotationProgress.setAttribute('aria-valuenow', coverage.toFixed(1)); // Per accessibilità

        // Aggiorna colore
        this.elements.annotationProgress.className = 'progress-bar'; // Reset classi colore
        if (coverage < 30) this.elements.annotationProgress.classList.add('bg-danger');
        else if (coverage < 70) this.elements.annotationProgress.classList.add('bg-warning');
        else this.elements.annotationProgress.classList.add('bg-success');

        AnnotationLogger.debug(`Progresso annotazione (copertura caratteri): ${coverage.toFixed(1)}%`);

        // Aggiorna indicatore globale se esiste
        if (typeof window.updateGlobalProgressIndicator === 'function') {
            window.updateGlobalProgressIndicator();
        }
    },

    /** Aggiorna il contatore delle annotazioni visibili nella lista. */
    updateVisibleCount: function() {
        if (!this.elements.visibleCount || !this.elements.annotationsContainer) return;

        const total = this.state.annotations.length;
        const visible = this.elements.annotationsContainer.querySelectorAll(`${ANNOTATOR_CONSTANTS.SELECTOR_ANNOTATION_ITEM}:not(.${ANNOTATOR_CONSTANTS.CLASS_D_NONE})`).length;

        this.elements.visibleCount.textContent = (visible === total) ? `${total}` : `${visible}/${total}`;

        // Mostra/nascondi messaggio "Nessuna annotazione"
        if (this.elements.noAnnotationsMsg) {
            const showNoAnnotations = total === 0;
            const showNoResults = total > 0 && visible === 0;

            this.elements.noAnnotationsMsg.classList.toggle(ANNOTATOR_CONSTANTS.CLASS_D_NONE, !showNoAnnotations && !showNoResults);

            if (showNoAnnotations) {
                this.elements.noAnnotationsMsg.textContent = "Nessuna annotazione presente.";
            } else if (showNoResults) {
                this.elements.noAnnotationsMsg.textContent = "Nessuna annotazione corrisponde ai filtri.";
            }
        }
        AnnotationLogger.debug(`Conteggio visibili aggiornato: ${visible}/${total}`);
    },

    /** Aggiorna tutti gli elementi principali dell'UI. */
    updateUI: function() {
        AnnotationLogger.startOperation('updateUI');
        this.updateAnnotationCount();
        this.updateEntityCounters();
        this.updateAnnotationProgress();
        this.updateVisibleCount(); // Chiamato anche da filterAnnotations e renderAnnotationList
        AnnotationLogger.endOperation('updateUI');
    },

    /** Filtra la lista delle annotazioni in base al testo di ricerca. */
    filterAnnotations: function() {
        if (!this.elements.searchAnnotations || !this.elements.annotationsContainer) return;

        const query = this.elements.searchAnnotations.value.trim().toLowerCase();
        this.state.filterText = query;
        AnnotationLogger.debug(`Filtraggio annotazioni con query: "${query}"`);

        let visibleCount = 0;
        this.elements.annotationsContainer.querySelectorAll(ANNOTATOR_CONSTANTS.SELECTOR_ANNOTATION_ITEM).forEach(item => {
            const itemText = item.dataset.text || ''; // Usa data-text pre-calcolato
            const itemType = item.dataset.type?.toLowerCase() || '';
            const entityName = this.getEntityNameById(item.dataset.type).toLowerCase();

            // Corrisponde se la query è nel testo O nel nome del tipo O nell'ID del tipo
            const matches = query === '' || itemText.includes(query) || entityName.includes(query) || itemType.includes(query);

            item.classList.toggle(ANNOTATOR_CONSTANTS.CLASS_D_NONE, !matches);
            if (matches) {
                visibleCount++;
            }
        });

        // Aggiorna il contatore visibile e il messaggio no-results
        this.updateVisibleCount();
    },

    /**
     * Ordina gli elementi annotazione nel DOM.
     * @param {'position' | 'type' | 'text'} sortBy - Criterio di ordinamento.
     */
    sortAnnotationList: function(sortBy) {
        if (!this.elements.annotationsContainer) return;
        AnnotationLogger.debug(`Ordinamento lista DOM per: ${sortBy}`);

        const items = Array.from(this.elements.annotationsContainer.querySelectorAll(ANNOTATOR_CONSTANTS.SELECTOR_ANNOTATION_ITEM));
        if (items.length < 2) return; // Non serve ordinare

        items.sort((a, b) => {
            switch (sortBy) {
                case 'position':
                    // Ordina per start, poi per end (più corte prima a parità di start?)
                    const startA = parseInt(a.dataset.start, 10);
                    const startB = parseInt(b.dataset.start, 10);
                    if (startA !== startB) return startA - startB;
                    const endA = parseInt(a.dataset.end, 10);
                    const endB = parseInt(b.dataset.end, 10);
                    return endA - endB; // Annotazioni più corte prima se iniziano uguale
                case 'type':
                    const typeA = this.getEntityNameById(a.dataset.type);
                    const typeB = this.getEntityNameById(b.dataset.type);
                    const typeCompare = typeA.localeCompare(typeB);
                    if (typeCompare !== 0) return typeCompare;
                    // Se stesso tipo, ordina per posizione
                    return parseInt(a.dataset.start, 10) - parseInt(b.dataset.start, 10);
                case 'text': // Aggiunto ordinamento per testo
                    const textA = a.dataset.text || '';
                    const textB = b.dataset.text || '';
                    const textCompare = textA.localeCompare(textB);
                     if (textCompare !== 0) return textCompare;
                     // Se stesso testo, ordina per posizione
                     return parseInt(a.dataset.start, 10) - parseInt(b.dataset.start, 10);
                default:
                    return 0;
            }
        });

        // Riaggiungi elementi ordinati al container
        // Usare DocumentFragment per performance potenziale su liste lunghe
        const fragment = document.createDocumentFragment();
        items.forEach(item => fragment.appendChild(item));
        this.elements.annotationsContainer.appendChild(fragment); // Appende tutti in una volta

        AnnotationLogger.debug(`Ordinamento DOM completato.`);
    },

     /**
     * Ordina un array di annotazioni in memoria.
     * @param {Array<object>} annotations - L'array di annotazioni.
     * @param {'position' | 'type' | 'text'} sortBy - Criterio di ordinamento.
     * @returns {Array<object>} L'array ordinato.
     */
    sortAnnotationsInState: function(annotations, sortBy) {
        return [...annotations].sort((a, b) => {
             switch (sortBy) {
                case 'position':
                    if (a.start !== b.start) return a.start - b.start;
                    return a.end - b.end;
                case 'type':
                    const typeA = this.getEntityNameById(a.type);
                    const typeB = this.getEntityNameById(b.type);
                    const typeCompare = typeA.localeCompare(typeB);
                    if (typeCompare !== 0) return typeCompare;
                    return a.start - b.start; // Fallback a posizione
                case 'text':
                    const textCompare = (a.text || '').localeCompare(b.text || '');
                    if (textCompare !== 0) return textCompare;
                    return a.start - b.start; // Fallback a posizione
                default:
                    return 0;
            }
        });
    },

    /**
     * Salta all'annotazione corrispondente nel testo e la evidenzia.
     * @param {string} annotationId - L'ID dell'annotazione.
     */
    jumpToAnnotationInText: function(annotationId) {
        AnnotationLogger.debug(`Salto nel testo all'annotazione ID: ${annotationId}`);
        const highlight = this.elements.textContent?.querySelector(`${ANNOTATOR_CONSTANTS.SELECTOR_ENTITY_HIGHLIGHT}[data-id="${annotationId}"]`);

        if (highlight) {
            // Rimuovi focus da altri
            this.removeTextFocus(highlight); // Passa highlight per non rimuovere focus da sé stesso

            // Aggiungi focus a questo
            highlight.classList.add(ANNOTATOR_CONSTANTS.CLASS_FOCUSED);
            this.state.highlightedAnnotationId = annotationId;

            // Scroll nel testo
            highlight.scrollIntoView({ behavior: 'smooth', block: 'center' });

            // Effetto flash (opzionale, può essere fastidioso)
            /*
            highlight.style.transition = 'outline 0.1s ease-in-out';
            highlight.classList.add('flash-highlight'); // Aggiungi una classe per il flash
            setTimeout(() => {
                highlight.classList.remove('flash-highlight');
                highlight.style.transition = '';
            }, ANNOTATOR_CONSTANTS.HIGHLIGHT_FLASH_DURATION_MS);
            */
        } else {
            AnnotationLogger.warn(`Highlight non trovato nel testo per ID: ${annotationId}. Potrebbe essere necessario ridisegnare.`);
            // Potrebbe essere utile forzare un re-highlighting se l'elemento non si trova
            // this.highlightAnnotations();
        }
    },

    /**
     * Seleziona l'annotazione corrispondente nella lista laterale e scorre ad essa.
     * @param {string} annotationId - L'ID dell'annotazione.
     */
    jumpToAnnotationInList: function(annotationId) {
        if (!this.elements.annotationsContainer) return;
        AnnotationLogger.debug(`Salto nella lista all'annotazione ID: ${annotationId}`);

        const annotationItem = this.elements.annotationsContainer.querySelector(`${ANNOTATOR_CONSTANTS.SELECTOR_ANNOTATION_ITEM}[data-id="${annotationId}"]`);

        if (annotationItem) {
            // Deseleziona altri elementi nella lista
             this.elements.annotationsContainer.querySelectorAll(`.${ANNOTATOR_CONSTANTS.CLASS_SELECTED}`)
                .forEach(item => item.classList.remove(ANNOTATOR_CONSTANTS.CLASS_SELECTED));

            // Seleziona questo elemento
            annotationItem.classList.add(ANNOTATOR_CONSTANTS.CLASS_SELECTED);
            this.state.selectedAnnotationId = annotationId;

            // Scrolla l'elemento nella vista (all'interno del suo container)
            annotationItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); // 'nearest' è meno invasivo di 'center'

            // Evidenziazione temporanea (opzionale)
            /*
            annotationItem.classList.add(ANNOTATOR_CONSTANTS.CLASS_HIGHLIGHT);
            setTimeout(() => {
                annotationItem.classList.remove(ANNOTATOR_CONSTANTS.CLASS_HIGHLIGHT);
            }, 2000);
            */
        } else {
            AnnotationLogger.warn(`Elemento annotazione non trovato nella lista per ID: ${annotationId}`);
        }
    },

    /** Attiva/disattiva la modalità clean (senza distrazioni). */
    toggleCleanMode: function() {
        this.state.isCleanMode = !this.state.isCleanMode;
        document.body.classList.toggle(ANNOTATOR_CONSTANTS.CLASS_CLEAN_MODE, this.state.isCleanMode);
        this.updateCleanModeButton(this.state.isCleanMode);

        AnnotationLogger.debug(`Modalità clean ${this.state.isCleanMode ? 'attivata' : 'disattivata'}`);

        // Salva preferenza
        localStorage.setItem('ner-clean-mode', this.state.isCleanMode);

        // Notifica utente
        this.utils.showNotification(
            this.state.isCleanMode
                ? 'Modalità Concentrazione Attivata. Passa il mouse sui bordi per i pannelli.'
                : 'Modalità Concentrazione Disattivata.',
            'info'
        );
    },

    /** Aggiorna icona e tooltip del pulsante Clean Mode. */
    updateCleanModeButton: function(isClean) {
         if (!this.elements.cleanModeToggle) return;
         const icon = this.elements.cleanModeToggle.querySelector('i');
         if (icon) {
            icon.className = isClean ? 'fas fa-compress-arrows-alt' : 'fas fa-expand-arrows-alt'; // Icone più chiare
         }
         this.elements.cleanModeToggle.title = isClean ? 'Esci da Modalità Concentrazione (Ctrl+F)' : 'Attiva Modalità Concentrazione (Ctrl+F)';
    },

    /** Incrementa lo zoom del testo. */
    zoomIn: function() {
        this.setZoom(Math.min(this.state.currentTextSize + ANNOTATOR_CONSTANTS.ZOOM_STEP, ANNOTATOR_CONSTANTS.MAX_ZOOM));
    },

    /** Decrementa lo zoom del testo. */
    zoomOut: function() {
        this.setZoom(Math.max(this.state.currentTextSize - ANNOTATOR_CONSTANTS.ZOOM_STEP, ANNOTATOR_CONSTANTS.MIN_ZOOM));
    },

    /** Reimposta lo zoom del testo al valore originale. */
    resetZoom: function() {
        this.setZoom(this.state.originalTextSize);
    },

    /**
     * Imposta il livello di zoom del testo.
     * @param {number} newSize - Nuova dimensione in rem.
     */
    setZoom: function(newSize) {
        this.state.currentTextSize = parseFloat(newSize.toFixed(2)); // Arrotonda per evitare errori float
        if (this.elements.textContent) {
            this.elements.textContent.style.fontSize = `${this.state.currentTextSize}rem`;
        }
        AnnotationLogger.debug(`Zoom impostato a ${this.state.currentTextSize}rem`);
        // Potrebbe essere utile salvare lo zoom in localStorage
        // localStorage.setItem('ner-text-zoom', this.state.currentTextSize);
    },

    /**
     * Ottiene il colore associato a un tipo di entità (dal DOM).
     * @param {string} entityType - L'ID (tipo) dell'entità.
     * @returns {string} Colore CSS (es. 'rgb(R, G, B)' o '#HEX'). Default grigio.
     */
    getEntityColorById: function(entityType) {
        const entityElement = document.querySelector(`${ANNOTATOR_CONSTANTS.SELECTOR_ENTITY_TYPE}[data-type="${entityType}"]`);
        // Prova a prendere il colore dal background, altrimenti da una variabile CSS se definita
        return entityElement?.style.backgroundColor || getComputedStyle(entityElement || document.body).getPropertyValue(`--entity-color-${entityType}`) || '#CCCCCC'; // Fallback grigio
    },

    /**
     * Ottiene il nome visualizzato di un tipo di entità (dal DOM).
     * @param {string} entityType - L'ID (tipo) dell'entità.
     * @returns {string} Nome visualizzato o l'ID stesso se non trovato.
     */
    getEntityNameById: function(entityType) {
        const entityElement = document.querySelector(`${ANNOTATOR_CONSTANTS.SELECTOR_ENTITY_TYPE}[data-type="${entityType}"]`);
        return entityElement?.querySelector('.entity-name')?.textContent?.trim() || entityType;
    },

    /**
     * Calcola un colore di testo (bianco o nero) che contrasti bene con un colore di sfondo.
     * @param {string} bgColor - Colore di sfondo (es. 'rgb(R,G,B)', '#RRGGBB', 'red').
     * @returns {'#FFFFFF' | '#000000'} Bianco o nero.
     */
    getContrastColor: function(bgColor) {
        if (!bgColor) return '#000000'; // Default nero se non c'è colore

        // Converte il colore in RGB
        let r, g, b;
        const tempDiv = document.createElement('div');
        tempDiv.style.color = bgColor;
        document.body.appendChild(tempDiv); // Necessario per computedStyle
        const rgbColor = window.getComputedStyle(tempDiv).color;
        document.body.removeChild(tempDiv);

        const match = rgbColor.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
        if (match) {
            [, r, g, b] = match.map(Number);
        } else {
            return '#000000'; // Fallback se non riesce a parsare
        }

        // Formula per luminanza (YIQ)
        const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
        return (yiq >= 128) ? '#000000' : '#FFFFFF'; // Nero su chiaro, Bianco su scuro
    },


    /**
     * Ordina le annotazioni per posizione: prima per inizio (asc), poi per fine (desc).
     * Utile per il rendering e la gestione delle sovrapposizioni.
     * @param {Array<object>} annotations - Array di annotazioni.
     * @returns {Array<object>} Array ordinato.
     */
    sortAnnotationsByPosition: function(annotations) {
        return [...annotations].sort((a, b) => {
            if (a.start !== b.start) {
                return a.start - b.start; // Prima per inizio crescente
            }
            // Se iniziano uguale, metti prima quella che finisce dopo (più lunga)
            return b.end - a.end;
        });
    },

    /** Incrementa il contatore delle operazioni in corso e mostra indicatore globale. */
    startPendingOperation: function() {
        this.state.pendingOperations++;
        if (this.state.pendingOperations === 1) {
            document.body.classList.add(ANNOTATOR_CONSTANTS.CLASS_LOADING);
        }
        // Disabilita pulsanti critici durante operazioni lunghe?
        // this.elements.autoAnnotateBtn?.setAttribute('disabled', 'true');
    },

    /** Decrementa il contatore delle operazioni e nasconde indicatore globale se finite. */
    endPendingOperation: function() {
        this.state.pendingOperations = Math.max(0, this.state.pendingOperations - 1);
        if (this.state.pendingOperations === 0) {
            document.body.classList.remove(ANNOTATOR_CONSTANTS.CLASS_LOADING);
            // Riabilita pulsanti
             // this.elements.autoAnnotateBtn?.removeAttribute('disabled');
        }
    },

    /** Aggiunge stili CSS dinamici necessari per l'annotatore. */
    addDynamicStyles: function() {
        let styleEl = document.getElementById('annotator-dynamic-styles');
        if (!styleEl) {
            styleEl = document.createElement('style');
            styleEl.id = 'annotator-dynamic-styles';
            document.head.appendChild(styleEl);
        }

        // CSS migliorato e organizzato
        styleEl.textContent = `
            /* === Animazioni === */
            @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
            @keyframes fadeOut { from { opacity: 1; } to { opacity: 0; transform: scale(0.95); } }

            .${ANNOTATOR_CONSTANTS.CLASS_FADE_OUT} {
                animation: fadeOut ${ANNOTATOR_CONSTANTS.HIGHLIGHT_FADE_DURATION_MS / 1000}s ease-out forwards;
            }
            .${ANNOTATOR_CONSTANTS.CLASS_HIGHLIGHT} { /* Evidenziazione temporanea nuovi elementi */
                animation: fadeIn 0.5s ease-in;
                box-shadow: 0 0 10px 2px var(--bs-warning, yellow); /* Usa variabile Bootstrap o fallback */
            }
            .${ANNOTATOR_CONSTANTS.CLASS_SHORTCUT_HIGHLIGHT} { /* Feedback scorciatoia tipo entità */
                 outline: 2px solid var(--bs-primary, blue);
                 transition: outline 0.1s ease-in-out;
            }

            /* === Evidenziazioni nel Testo === */
            .${ANNOTATOR_CONSTANTS.SELECTOR_ENTITY_HIGHLIGHT.substring(1)} {
                display: inline; /* Cruciale per il flusso del testo */
                padding: 0.1em 0.2em;
                margin: 0 0.1em; /* Piccolo spazio laterale */
                border-radius: 3px;
                line-height: inherit; /* Usa line-height del parent */
                box-decoration-break: clone; /* Gestisce wrap su più linee */
                -webkit-box-decoration-break: clone;
                cursor: pointer;
                border: 1px solid transparent; /* Bordo per focus/hover */
                transition: all 0.15s ease-in-out;
                white-space: pre-wrap; /* Mantiene spazi interni */
                /* Colore testo e sfondo impostati inline */
            }
            .${ANNOTATOR_CONSTANTS.SELECTOR_ENTITY_HIGHLIGHT.substring(1)}:hover {
                filter: brightness(1.1); /* Leggermente più luminoso */
                border-color: rgba(0,0,0,0.5);
            }
            .${ANNOTATOR_CONSTANTS.SELECTOR_ENTITY_HIGHLIGHT.substring(1)}.${ANNOTATOR_CONSTANTS.CLASS_FOCUSED} {
                outline: 2px solid var(--bs-primary, #0d6efd); /* Blu primario Bootstrap o fallback */
                outline-offset: 1px;
                filter: brightness(1.15);
                z-index: 2; /* Sopra gli altri */
                position: relative; /* Necessario per z-index */
            }
            .${ANNOTATOR_CONSTANTS.SELECTOR_ENTITY_HIGHLIGHT.substring(1)}.${ANNOTATOR_CONSTANTS.CLASS_OVERLAP} {
                /* Stile per sovrapposizioni (es. tratteggio o bordo diverso) */
                 box-shadow: inset 0 0 0 1px rgba(255, 165, 0, 0.7); /* Ombra interna arancione */
                 /* text-decoration: underline wavy rgba(255, 165, 0, 0.7); */ /* Sottolineatura ondulata */
            }
            /* Stile per flash (se riattivato) */
            /*
            .flash-highlight {
                 outline: 3px solid yellow !important;
                 outline-offset: 2px;
            }
            */

            /* === Lista Annotazioni === */
            .${ANNOTATOR_CONSTANTS.SELECTOR_ANNOTATION_ITEM.substring(1)} {
                transition: background-color 0.2s ease, border-left-color 0.2s ease;
                border-left: 4px solid transparent;
            }
            .${ANNOTATOR_CONSTANTS.SELECTOR_ANNOTATION_ITEM.substring(1)}:hover {
                background-color: #f8f9fa; /* Grigio chiaro Bootstrap */
            }
            .${ANNOTATOR_CONSTANTS.SELECTOR_ANNOTATION_ITEM.substring(1)}.${ANNOTATOR_CONSTANTS.CLASS_SELECTED} {
                background-color: #e7f1ff; /* Blu chiaro */
                border-left-color: var(--bs-primary, #0d6efd);
            }

            /* === Indicatore Caricamento Globale === */
            body.${ANNOTATOR_CONSTANTS.CLASS_LOADING}::before {
                content: '';
                position: fixed;
                top: 0; left: 0; right: 0;
                height: 3px;
                background: linear-gradient(90deg, transparent, var(--bs-primary, #0d6efd), transparent);
                animation: loadingBar 1.5s infinite linear;
                z-index: 10000; /* Sopra tutto */
                pointer-events: none;
            }
            @keyframes loadingBar {
                0% { transform: translateX(-100%); }
                50% { transform: translateX(100%); }
                100% { transform: translateX(100%); } /* Pausa alla fine */
            }

            /* === Modalità Clean === */
            body.${ANNOTATOR_CONSTANTS.CLASS_CLEAN_MODE} .entity-sidebar,
            body.${ANNOTATOR_CONSTANTS.CLASS_CLEAN_MODE} .annotations-sidebar {
                position: fixed; /* Usa fixed per rimanere visibile allo scroll */
                top: 0; bottom: 0; /* Altezza piena */
                width: 40px; /* Larghezza ridotta */
                overflow: hidden;
                background-color: #fff;
                box-shadow: 0 0 15px rgba(0,0,0,0.15);
                z-index: 1050; /* Sopra il contenuto ma sotto eventuali modal */
                transition: width 0.3s ease-in-out, opacity 0.3s ease-in-out;
                opacity: 0.85; /* Leggermente trasparente quando chiuso */
                padding: 1rem 0; /* Padding verticale per icone/trigger */
                display: flex;
                flex-direction: column;
                align-items: center;
            }
             body.${ANNOTATOR_CONSTANTS.CLASS_CLEAN_MODE} .entity-sidebar { left: 0; }
             body.${ANNOTATOR_CONSTANTS.CLASS_CLEAN_MODE} .annotations-sidebar { right: 0; }

             /* Nascondi contenuto interno quando chiuso */
             body.${ANNOTATOR_CONSTANTS.CLASS_CLEAN_MODE} .entity-sidebar > *:not(.sidebar-toggle-icon),
             body.${ANNOTATOR_CONSTANTS.CLASS_CLEAN_MODE} .annotations-sidebar > *:not(.sidebar-toggle-icon) {
                 opacity: 0;
                 transition: opacity 0.1s ease;
             }
             /* Aggiungi un'icona o handle visibile */
             .sidebar-toggle-icon { /* Da aggiungere nel HTML delle sidebar */
                 display: block;
                 padding: 10px;
                 cursor: pointer;
                 color: #6c757d; /* Grigio Bootstrap */
             }

             body.${ANNOTATOR_CONSTANTS.CLASS_CLEAN_MODE} .entity-sidebar:hover,
             body.${ANNOTATOR_CONSTANTS.CLASS_CLEAN_MODE} .annotations-sidebar:hover {
                 width: 280px; /* Larghezza aperta standard */
                 opacity: 1;
                 overflow-y: auto; /* Scroll se necessario */
             }
             /* Mostra contenuto interno quando aperto */
             body.${ANNOTATOR_CONSTANTS.CLASS_CLEAN_MODE} .entity-sidebar:hover > *,
             body.${ANNOTATOR_CONSTANTS.CLASS_CLEAN_MODE} .annotations-sidebar:hover > * {
                 opacity: 1;
                 transition: opacity 0.2s ease 0.1s; /* Ritardo per apparire dopo apertura */
             }
             /* Adatta il contenuto principale per non sovrapporsi */
             body.${ANNOTATOR_CONSTANTS.CLASS_CLEAN_MODE} .main-content-area { /* Assumendo una classe per l'area centrale */
                 padding-left: 50px; /* Spazio per sidebar chiusa */
                 padding-right: 50px;
                 transition: padding 0.3s ease-in-out;
             }
             /* Stile per elementi rimossi (feedback visivo) */
             .${ANNOTATOR_CONSTANTS.CLASS_REMOVING} {
                 opacity: 0.5 !important;
                 background-color: rgba(220, 38, 38, 0.3) !important; /* Rosso trasparente */
                 transition: none !important; /* Sovrascrive altre transizioni */
             }
        `;
    },

    /**
     * Esegue l'escape di caratteri HTML speciali in una stringa.
     * @param {string} str - La stringa da elaborare.
     * @returns {string} La stringa con escape HTML.
     */
    escapeHtml: function(str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    },

    /**
     * Tronca una stringa a una lunghezza massima, aggiungendo '...'.
     * @param {string} text - Il testo da troncare.
     * @param {number} maxLength - La lunghezza massima.
     * @returns {string} Il testo troncato o originale.
     */
    truncateText: function(text, maxLength) {
        if (!text || text.length <= maxLength) {
            return text;
        }
        return text.substring(0, maxLength) + '...';
    }
};

// === Inizializzazione ===
document.addEventListener('DOMContentLoaded', () => {
    AnnotationManager.init();

    // === Esposizione Globale (per retrocompatibilità o debugging) ===
    // NOTA: Evitare l'esposizione globale in produzione se possibile.
    // Considerare un sistema di moduli (ESM) o un bus di eventi.
    window.AnnotationManager = AnnotationManager; // Esponi l'intero manager per debug
   
    // Vecchie funzioni globali (mappate alle nuove se necessario)
    window.updateAnnotationCount = () => AnnotationManager.updateAnnotationCount();
    window.addAnnotationToList = (annotation) => AnnotationManager.addAnnotationToDOM(annotation);
    window.highlightExistingAnnotations = () => AnnotationManager.highlightAnnotations();
    window.jumpToAnnotation = (annotationId) => AnnotationManager.jumpToAnnotationInText(annotationId); // O jumpToAnnotationInList? Scegliere uno
    window.deleteAnnotation = (annotationId) => AnnotationManager.deleteAnnotation(annotationId);
    window.updateStatus = (message, isError) => AnnotationManager.updateStatus(message, isError);
    window.clearAnnotations = async (docId, entityType = null) => { // Resa async
        AnnotationLogger.warn('Chiamata alla funzione globale deprecata clearAnnotations');
        if (docId !== AnnotationManager.state.docId) {
             AnnotationLogger.error('clearAnnotations chiamata con docId errato!');
             AnnotationManager.utils.showNotification('Errore: ID documento non corrispondente.', 'danger');
             return Promise.reject(new Error('ID documento non corrispondente'));
        }

        const title = entityType ? `Elimina annotazioni di tipo "${AnnotationManager.getEntityNameById(entityType)}"` : 'Elimina TUTTE le annotazioni';
        const message = `Sei sicuro di voler eliminare ${entityType ? `tutte le annotazioni di tipo "${AnnotationManager.getEntityNameById(entityType)}"` : 'TUTTE le annotazioni per questo documento'}? L'azione è irreversibile.`;

        const confirmed = await new Promise(resolve => {
             AnnotationManager.utils.showConfirmation(title, message, () => resolve(true), 'Elimina', 'btn-danger', () => resolve(false));
        });

        if (!confirmed) return Promise.resolve(false); // Risolve a false se annullato

        AnnotationManager.startPendingOperation();
        try {
            const response = await fetch(ANNOTATOR_CONSTANTS.API_CLEAR, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
                body: JSON.stringify({ doc_id: docId, entity_type: entityType }) // entity_type può essere null
            });
            const data = await response.json();
            if (!response.ok || data.status !== 'success') {
                throw new Error(data.message || `Errore API clearAnnotations (HTTP ${response.status})`);
            }
            AnnotationManager.utils.showNotification(data.message || 'Annotazioni eliminate con successo.', 'success');
            // Ricarica la pagina o aggiorna lo stato localmente
            AnnotationManager.state.annotations = entityType
                ? AnnotationManager.state.annotations.filter(a => a.type !== entityType)
                : [];
            AnnotationManager.highlightAnnotations();
            AnnotationManager.renderAnnotationList();
            AnnotationManager.updateUI();
            // setTimeout(() => window.location.reload(), 1500); // Ricaricare è più semplice ma interrompe il flusso
            return Promise.resolve(true); // Risolve a true in caso di successo
        } catch (error) {
            AnnotationLogger.error('Errore nella richiesta clear_annotations', error);
            AnnotationManager.utils.showNotification(`Errore eliminazione: ${error.message}`, 'danger');
            return Promise.reject(error); // Rigetta la promise in caso di errore
        } finally {
            AnnotationManager.endPendingOperation();
        }
    };
});