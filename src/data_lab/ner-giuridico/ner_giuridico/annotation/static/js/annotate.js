/**
 * annotate.js - Script migliorato per la funzionalità di annotazione
 * 
 * Questo file gestisce tutte le interazioni utente relative all'annotazione di documenti
 * incluse la selezione del testo, la creazione/eliminazione di annotazioni e la
 * visualizzazione delle annotazioni esistenti.
 * 
 * @version 2.2.0
 * @author NER-Giuridico Team
 */

/**
 * Sistema di logging per l'applicazione di annotazione
 * Fornisce funzioni strutturate per il logging con diversi livelli di verbosità
 */
const AnnotationLogger = {
    // Impostare a true per abilitare il logging dettagliato
    debugMode: window.location.search.includes('debug=true'),
    
    info: function(message, data) {
        console.info(`ℹ️ [Annotator] ${message}`, data || '');
    },
    
    debug: function(message, data) {
        if (this.debugMode) {
            console.debug(`🔍 [Annotator] ${message}`, data || '');
        }
    },
    
    warn: function(message, data) {
        console.warn(`⚠️ [Annotator] ${message}`, data || '');
    },
    
    error: function(message, error) {
        console.error(`❌ [Annotator] ${message}`, error || '');
        if (error && error.stack) {
            console.error(error.stack);
        }
    },
    
    startOperation: function(operation) {
        this.debug(`Iniziata operazione: ${operation}`);
        console.time(`⏱️ [Annotator] ${operation}`);
    },
    
    endOperation: function(operation) {
        console.timeEnd(`⏱️ [Annotator] ${operation}`);
        this.debug(`Completata operazione: ${operation}`);
    }
};

// Namespace per la gestione delle annotazioni
const AnnotationManager = {
    // Stato principale dell'applicazione - fonte di verità
    state: {
        // Dati persistenti
        selectedType: null,
        annotations: [],
        docId: null,
        docText: '',
        originalTextSize: 1.05, // rem
        currentTextSize: 1.05,
        isCleanMode: false,
        
        // Stato temporaneo UI
        pendingOperations: 0,
        highlightedAnnotationId: null,
        selectedAnnotationId: null,
        lastSavedAt: null,
        
        // Prefiltro per le annotazioni visibili
        filterText: '',
        filterEntityType: null
    },
    
    /**
     * Inizializza il gestore delle annotazioni
     */
    init: function() {
        AnnotationLogger.startOperation('inizializzazione');
        
        // === Elementi DOM principali ===
        this.elements = {
            textContent: document.getElementById('text-content'),
            entityTypes: document.querySelectorAll('.entity-type'),
            clearSelectionBtn: document.getElementById('clear-selection'),
            autoAnnotateBtn: document.getElementById('auto-annotate'),
            annotationsContainer: document.getElementById('annotations-container'),
            searchAnnotations: document.getElementById('search-annotations'),
            annotationStatus: document.getElementById('annotation-status'),
            annotationCount: document.getElementById('annotation-count'),
            visibleCount: document.getElementById('visible-count'),
            annotationProgress: document.getElementById('annotation-progress'),
            noAnnotationsMsg: document.getElementById('no-annotations'),
            cleanModeToggle: document.getElementById('clean-mode-toggle'),
            zoomInBtn: document.getElementById('zoom-in'),
            zoomOutBtn: document.getElementById('zoom-out'),
            resetZoomBtn: document.getElementById('reset-zoom')
        };
        
        // Verifica degli elementi DOM richiesti
        if (!this.elements.textContent) {
            AnnotationLogger.error('Elemento #text-content non trovato. L\'applicazione potrebbe non funzionare correttamente.');
            return;
        }
        
        // Inizializza lo stato
        this.state.docId = this.elements.textContent ? this.elements.textContent.dataset.docId : null;
        this.state.docText = this.elements.textContent ? this.elements.textContent.textContent : '';
        
        if (!this.state.docId) {
            AnnotationLogger.error('ID documento mancante. L\'applicazione potrebbe non funzionare correttamente.');
        }
        
        // Carica le annotazioni iniziali
        this.loadInitialAnnotations();
        
        // Configura gli event handlers
        this.setupEventHandlers();
        
        // Evidenzia le annotazioni esistenti
        this.highlightAnnotations();
        
        // Sincronizza l'UI
        this.updateUI();
        
        // Aggiungi stili dinamici
        this.addDynamicStyles();
        
        // Logging
        AnnotationLogger.info('Inizializzazione completata con successo');
        AnnotationLogger.debug(`Documento ID: ${this.state.docId}, ${this.state.annotations.length} annotazioni caricate`);
        AnnotationLogger.endOperation('inizializzazione');
    },
    
    /**
     * Carica le annotazioni iniziali dal DOM
     */
    loadInitialAnnotations: function() {
        AnnotationLogger.startOperation('loadInitialAnnotations');
        
        this.state.annotations = [];
        const items = document.querySelectorAll('.annotation-item');
        
        AnnotationLogger.debug(`Trovate ${items.length} annotazioni nel DOM`);
        
        items.forEach((item, index) => {
            try {
                const id = item.dataset.id;
                const text = item.querySelector('.annotation-text').textContent;
                const type = item.dataset.type;
                const start = parseInt(item.dataset.start);
                const end = parseInt(item.dataset.end);
                
                // Trova il colore dall'elemento badge
                const typeElement = item.querySelector('.annotation-type');
                const color = typeElement ? typeElement.style.backgroundColor : "";
                
                this.state.annotations.push({ id, text, type, start, end, color });
                
                AnnotationLogger.debug(`Caricata annotazione #${index+1}`, { id, type, start, end });
            } catch (error) {
                AnnotationLogger.error(`Errore nel caricamento dell'annotazione #${index+1}`, error);
            }
        });
        
        // Ordina per posizione
        this.state.annotations = this.sortAnnotationsByPosition(this.state.annotations);
        
        AnnotationLogger.debug(`Caricate ${this.state.annotations.length} annotazioni in totale`);
        AnnotationLogger.endOperation('loadInitialAnnotations');
    },
    
    /**
     * Configura tutti gli event handlers
     */
    setupEventHandlers: function() {
        AnnotationLogger.debug('Configurazione event handlers');
        
        // === Selezione dei tipi di entità ===
        this.elements.entityTypes.forEach(entityType => {
            entityType.addEventListener('click', () => this.selectEntityType(entityType));
        });
        
        // === Gestione della selezione del testo ===
        if (this.elements.textContent) {
            this.elements.textContent.addEventListener('mouseup', e => this.handleTextSelection(e));
        }
        
        // === Pulsante per annullare la selezione ===
        if (this.elements.clearSelectionBtn) {
            this.elements.clearSelectionBtn.addEventListener('click', () => this.clearSelection());
        }
        
        // === Pulsante per l'annotazione automatica ===
        if (this.elements.autoAnnotateBtn) {
            this.elements.autoAnnotateBtn.addEventListener('click', () => this.performAutoAnnotation());
        }
        
        // === Eventi per gli elementi delle annotazioni (delegato) ===
        if (this.elements.annotationsContainer) {
            this.elements.annotationsContainer.addEventListener('click', e => this.handleAnnotationContainerClick(e));
        }
        
        // === Ricerca nelle annotazioni ===
        if (this.elements.searchAnnotations) {
            const debouncedSearch = NERGiuridico.debounce(() => this.filterAnnotations(), 300);
            this.elements.searchAnnotations.addEventListener('input', debouncedSearch);
        }
        
        // === Zoom del testo ===
        if (this.elements.zoomInBtn) {
            this.elements.zoomInBtn.addEventListener('click', () => this.zoomIn());
        }
        
        if (this.elements.zoomOutBtn) {
            this.elements.zoomOutBtn.addEventListener('click', () => this.zoomOut());
        }
        
        if (this.elements.resetZoomBtn) {
            this.elements.resetZoomBtn.addEventListener('click', () => this.resetZoom());
        }
        
        // === Modalità clean (a schermo intero) ===
        if (this.elements.cleanModeToggle) {
            this.elements.cleanModeToggle.addEventListener('click', () => this.toggleCleanMode());
        }
        
        // === Scorciatoie da tastiera ===
        document.addEventListener('keydown', e => this.handleKeyDown(e));
        
        // === Eventi per gli elementi evidenziati (delegato) ===
        if (this.elements.textContent) {
            this.elements.textContent.addEventListener('click', e => this.handleHighlightClick(e));
        }
        
        // === Controlli di ordinamento (delegato) ===
        document.addEventListener('click', e => {
            if (e.target.closest('.sort-annotations')) {
                const sortBtn = e.target.closest('.sort-annotations');
                const sortBy = sortBtn.dataset.sort;
                this.sortAnnotations(sortBy);
                
                // Aggiorna lo stato dei pulsanti
                document.querySelectorAll('.sort-annotations').forEach(btn => {
                    btn.classList.remove('active');
                });
                sortBtn.classList.add('active');
            }
        });
        
        // Dà il focus automaticamente al campo di ricerca quando si preme "/" (standard UX)
        document.addEventListener('keydown', e => {
            if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && 
                document.activeElement.tagName !== 'TEXTAREA') {
                e.preventDefault();
                if (this.elements.searchAnnotations) {
                    this.elements.searchAnnotations.focus();
                }
            }
        });
    },
    
    /**
     * Gestisce il click all'interno del container delle annotazioni
     * @param {Event} e - L'evento click
     */
    handleAnnotationContainerClick: function(e) {
        // Bottone di eliminazione
        if (e.target.closest('.delete-annotation')) {
            const btn = e.target.closest('.delete-annotation');
            const annotationId = btn.dataset.id;
            this.deleteAnnotation(annotationId);
            return;
        }
        
        // Bottone di salto all'annotazione
        if (e.target.closest('.jump-to-annotation')) {
            const btn = e.target.closest('.jump-to-annotation');
            const annotationId = btn.dataset.id;
            this.jumpToAnnotation(annotationId);
            return;
        }
        
        // Clic su un'annotazione (per evidenziarla)
        const annotationItem = e.target.closest('.annotation-item');
        if (annotationItem) {
            // Deseleziona altri elementi
            document.querySelectorAll('.annotation-item.selected').forEach(item => {
                if (item !== annotationItem) {
                    item.classList.remove('selected');
                }
            });
            
            // Seleziona/deseleziona questo elemento
            annotationItem.classList.toggle('selected');
            
            // Aggiorna lo stato
            const isSelected = annotationItem.classList.contains('selected');
            this.state.selectedAnnotationId = isSelected ? annotationItem.dataset.id : null;
            
            if (isSelected) {
                this.jumpToAnnotation(annotationItem.dataset.id);
            }
        }
    },
    
    /**
     * Gestisce il click su un'evidenziazione nel testo
     * @param {Event} e - L'evento click
     */
    handleHighlightClick: function(e) {
        const highlight = e.target.closest('.entity-highlight');
        if (!highlight) return;
        
        const annotationId = highlight.dataset.id;
        
        // Rimuovi la classe focused da tutte le altre annotazioni
        document.querySelectorAll('.entity-highlight.focused').forEach(el => {
            if (el !== highlight) el.classList.remove('focused');
        });
        
        // Aggiungi la classe focused a questa annotazione
        highlight.classList.add('focused');
        
        // Aggiorna lo stato
        this.state.highlightedAnnotationId = annotationId;
        
        // Trova l'elemento corrispondente nella lista e attivalo
        this.jumpToAnnotationInList(annotationId);
    },
    
    /**
     * Gestisce la pressione dei tasti
     * @param {KeyboardEvent} e - L'evento keydown
     */
    handleKeyDown: function(e) {
        // Escape per annullare la selezione
        if (e.key === 'Escape') {
            this.clearSelection();
        }
        
        // Alt+A per annotazione automatica
        if (e.key === 'a' && e.altKey) {
            e.preventDefault();
            if (this.elements.autoAnnotateBtn && !this.elements.autoAnnotateBtn.disabled) {
                this.elements.autoAnnotateBtn.click();
            }
        }
        
        // Cmd/Ctrl + numero per selezionare un tipo di entità
        if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '9') {
            e.preventDefault();
            
            const index = parseInt(e.key) - 1;
            if (index < this.elements.entityTypes.length) {
                const entityType = this.elements.entityTypes[index];
                this.selectEntityType(entityType);
                
                // Feedback visivo
                entityType.classList.add('shortcut-highlight');
                setTimeout(() => {
                    entityType.classList.remove('shortcut-highlight');
                }, 500);
            }
        }
        
        // Cmd/Ctrl + F per modalità clean
        if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
            e.preventDefault();
            if (this.elements.cleanModeToggle) this.toggleCleanMode();
        }
        
        // Tasti freccia per navigare tra le annotazioni
        if (e.shiftKey && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
            e.preventDefault();
            
            const annotationItems = Array.from(document.querySelectorAll('.annotation-item:not(.d-none)'));
            if (annotationItems.length === 0) return;
            
            let currentIndex = -1;
            if (this.state.selectedAnnotationId) {
                currentIndex = annotationItems.findIndex(item => 
                    item.dataset.id === this.state.selectedAnnotationId);
            }
            
            let newIndex;
            if (e.key === 'ArrowUp') {
                newIndex = currentIndex <= 0 ? annotationItems.length - 1 : currentIndex - 1;
            } else {
                newIndex = currentIndex === annotationItems.length - 1 || currentIndex === -1 ? 0 : currentIndex + 1;
            }
            
            const newItem = annotationItems[newIndex];
            if (newItem) {
                // Deseleziona tutti gli elementi
                annotationItems.forEach(item => item.classList.remove('selected'));
                
                // Seleziona il nuovo elemento
                newItem.classList.add('selected');
                
                // Aggiorna lo stato
                this.state.selectedAnnotationId = newItem.dataset.id;
                
                // Scorri alla nuova annotazione
                newItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
                
                // Evidenzia nel testo
                this.jumpToAnnotation(newItem.dataset.id);
            }
        }
    },
    
    /**
     * Seleziona un tipo di entità
     * @param {HTMLElement} entityType - L'elemento DOM del tipo di entità
     */
    selectEntityType: function(entityType) {
        // Rimuovi la selezione precedente
        this.elements.entityTypes.forEach(et => et.classList.remove('selected'));
        
        // Seleziona il nuovo tipo
        entityType.classList.add('selected');
        
        // Aggiorna lo stato
        this.state.selectedType = entityType.dataset.type;
        
        // Mostra il messaggio di stato
        const entityName = entityType.querySelector('.entity-name').textContent;
        this.updateStatus(`Tipo selezionato: ${entityName}. Seleziona il testo da annotare.`);
        
        AnnotationLogger.debug(`Tipo di entità selezionato: ${this.state.selectedType} (${entityName})`);
    },
    
    /**
     * Pulisce la selezione corrente
     */
    clearSelection: function() {
        this.elements.entityTypes.forEach(et => et.classList.remove('selected'));
        this.state.selectedType = null;
        window.getSelection().removeAllRanges();
        this.updateStatus('Selezione annullata');
        AnnotationLogger.debug('Selezione annullata');
    },
    
    /**
     * Gestisce la selezione del testo
     * @param {MouseEvent} e - L'evento mouseup
     */
    handleTextSelection: function(e) {
        // Se il contenuto è in modalità di modifica, non fare nulla
        if (this.elements.textContent.contentEditable === 'true') return;
        
        const selection = window.getSelection();
        
        // Verifica se c'è del testo selezionato
        if (selection.toString().trim() === '') {
            return;
        }
        
        if (!this.state.selectedType) {
            NERGiuridico.showNotification('Seleziona prima un tipo di entità', 'danger');
            this.updateStatus('Seleziona un tipo di entità prima di annotare', true);
            return;
        }
        
        try {
            const range = selection.getRangeAt(0);
            
            // Calcola l'offset nel testo completo
            const fullText = this.elements.textContent.textContent;
            
            // Ottieni i nodi di inizio e fine della selezione
            const startNode = range.startContainer;
            const endNode = range.endContainer;
            
            // Calcola gli offset nei nodi
            const startOffset = this.getTextNodeOffset(this.elements.textContent, startNode, range.startOffset);
            const endOffset = this.getTextNodeOffset(this.elements.textContent, endNode, range.endOffset);
            
            if (startOffset < 0 || endOffset < 0) {
                AnnotationLogger.error('Impossibile determinare la posizione nel testo', {
                    startNode, endNode, rangeStart: range.startOffset, rangeEnd: range.endOffset
                });
                this.updateStatus('Impossibile determinare la posizione nel testo', true);
                return;
            }
            
            // Verifica che la selezione sia valida
            if (startOffset >= endOffset) {
                this.updateStatus('Selezione non valida', true);
                return;
            }
            
            // Ottieni il testo selezionato
            const selectedText = fullText.substring(startOffset, endOffset);
            
            AnnotationLogger.debug(`Nuova selezione: "${selectedText}" (${startOffset}-${endOffset})`);
            
            // Verifica se l'annotazione si sovrappone con altre esistenti
            let hasOverlap = false;
            let overlappingAnnotations = [];
            
            for (const annotation of this.state.annotations) {
                // Controlla sovrapposizione
                if (NERGiuridico.isOverlapping(startOffset, endOffset, annotation.start, annotation.end)) {
                    hasOverlap = true;
                    overlappingAnnotations.push(annotation);
                    AnnotationLogger.debug(`Sovrapposizione rilevata con annotazione esistente:`, {
                        newSelection: { start: startOffset, end: endOffset, text: selectedText },
                        existing: { id: annotation.id, start: annotation.start, end: annotation.end }
                    });
                }
            }
            
            if (hasOverlap) {
                // Mostra finestra di conferma
                NERGiuridico.showConfirmation(
                    'Sovrapposizione rilevata',
                    `La selezione si sovrappone a ${overlappingAnnotations.length} ${
                        overlappingAnnotations.length === 1 ? 'annotazione' : 'annotazioni'
                    } esistenti. Continuare comunque?`,
                    () => this.createAnnotation(startOffset, endOffset, selectedText, this.state.selectedType),
                    'Continua',
                    'btn-warning'
                );
                return;
            }
            
            // Crea l'annotazione
            this.createAnnotation(startOffset, endOffset, selectedText, this.state.selectedType);
            
        } catch (e) {
            AnnotationLogger.error("Errore nella selezione del testo:", e);
            this.updateStatus('Errore nella selezione del testo', true);
        }
    },
    
    /**
     * Ottiene l'offset reale nel testo
     * @param {Node} container - Il contenitore principale
     * @param {Node} targetNode - Il nodo target
     * @param {number} offset - L'offset nel nodo target
     * @returns {number} - L'offset assoluto nel testo completo
     */
    getTextNodeOffset: function(container, targetNode, offset) {
        if (container === targetNode) {
            return offset;
        }
        
        const walk = document.createTreeWalker(container, NodeFilter.SHOW_TEXT, null, false);
        let node;
        let charCount = 0;
        
        while ((node = walk.nextNode())) {
            if (node === targetNode) {
                return charCount + offset;
            }
            charCount += node.textContent.length;
        }
        
        return -1;
    },
    
    /**
     * Crea una nuova annotazione
     * @param {number} start - Posizione di inizio dell'annotazione nel testo
     * @param {number} end - Posizione di fine dell'annotazione nel testo
     * @param {string} text - Il testo selezionato
     * @param {string} type - Il tipo di entità
     */
    createAnnotation: function(start, end, text, type) {
        AnnotationLogger.debug(`Creazione annotazione: ${type}, "${text}" (${start}-${end})`);
        
        const annotation = {
            start: start,
            end: end,
            text: text,
            type: type
        };
        
        this.updateStatus('Creazione annotazione in corso...');
        
        // Salva l'annotazione
        this.saveAnnotation(annotation);
    },
    
    /**
     * Salva un'annotazione tramite API
     * @param {Object} annotation - L'annotazione da salvare
     */
    saveAnnotation: function(annotation) {
        AnnotationLogger.startOperation('saveAnnotation');
        this.startPendingOperation();
        
        AnnotationLogger.debug('Invio richiesta di salvataggio annotazione', annotation);
        
        fetch('/api/save_annotation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                doc_id: this.state.docId,
                annotation: annotation
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Errore HTTP: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                AnnotationLogger.debug('Annotazione salvata con successo', data.annotation);
                
                // Aggiungi l'annotazione alla struttura dati
                this.state.annotations.push(data.annotation);
                
                // Ordina le annotazioni
                this.state.annotations = this.sortAnnotationsByPosition(this.state.annotations);
                
                // Aggiungi l'annotazione alla lista
                this.addAnnotationToDOM(data.annotation);
                
                // Pulisci la selezione
                window.getSelection().removeAllRanges();
                
                // Riesegui l'highlighting
                this.highlightAnnotations();
                
                // Aggiorna l'UI
                this.updateUI();
                
                // Mostra notifica
                NERGiuridico.showNotification('Annotazione salvata con successo', 'success');
                this.updateStatus('Annotazione salvata con successo');
                
                // Imposta l'ultima data di salvataggio
                this.state.lastSavedAt = new Date();
            } else {
                AnnotationLogger.error(`Errore nel salvataggio: ${data.message}`, data);
                NERGiuridico.showNotification(`Errore: ${data.message}`, 'danger');
                this.updateStatus(`Errore: ${data.message}`, true);
            }
        })
        .catch(error => {
            AnnotationLogger.error('Errore durante il salvataggio dell\'annotazione', error);
            NERGiuridico.showNotification('Errore durante il salvataggio', 'danger');
            this.updateStatus('Errore durante il salvataggio', true);
        })
        .finally(() => {
            this.endPendingOperation();
            AnnotationLogger.endOperation('saveAnnotation');
        });
    },
    
    /**
     * Elimina un'annotazione
     * @param {string} annotationId - L'ID dell'annotazione da eliminare
     */
    deleteAnnotation: function(annotationId) {
        AnnotationLogger.debug(`Richiesta eliminazione annotazione: ${annotationId}`);
        
        // Usa la funzione di conferma centralizzata
        NERGiuridico.showConfirmation(
            'Elimina annotazione',
            'Sei sicuro di voler eliminare questa annotazione?',
            () => {
                AnnotationLogger.startOperation('deleteAnnotation');
                this.startPendingOperation();
                
                // Immediatamente rimuovi l'evidenziazione dal testo per feedback visivo immediato
                const highlightElement = document.querySelector(`.entity-highlight[data-id="${annotationId}"]`);
                if (highlightElement) {
                    highlightElement.classList.add('removing');
                    
                    // Usa un fade-out animato
                    highlightElement.classList.add('fade-out');
                    setTimeout(() => {
                        // Sostituisci l'elemento mantenendo il testo interno
                        const textContent = highlightElement.textContent;
                        const textNode = document.createTextNode(textContent);
                        if (highlightElement.parentNode) {
                            highlightElement.parentNode.replaceChild(textNode, highlightElement);
                        }
                    }, 300);
                }
                
                // Rimuovi l'annotazione dall'array locale (ottimistico)
                const annotationIndex = this.state.annotations.findIndex(a => a.id === annotationId);
                if (annotationIndex !== -1) {
                    this.state.annotations.splice(annotationIndex, 1);
                }
                
                // Rimuovi subito l'elemento dalla lista per feedback immediato
                const annotationItem = document.querySelector(`.annotation-item[data-id="${annotationId}"]`);
                if (annotationItem) {
                    // Aggiungi classe di animazione
                    annotationItem.classList.add('fade-out');
                    setTimeout(() => {
                        if (annotationItem.parentNode) {
                            annotationItem.parentNode.removeChild(annotationItem);
                        }
                        // Aggiorna l'UI dopo la rimozione
                        this.updateUI();
                    }, 300);
                }
                
                fetch('/api/delete_annotation', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        doc_id: this.state.docId,
                        annotation_id: annotationId
                    })
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Errore HTTP: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'success') {
                        AnnotationLogger.debug(`Eliminazione completata per ID: ${annotationId}`);
                        
                        // L'annotazione è già stata rimossa localmente in modo ottimistico
                        
                        // Riesegui l'highlighting completo per assicurare consistenza
                        this.highlightAnnotations();
                        
                        // Aggiorna l'interfaccia
                        this.updateUI();
                        
                        // Mostra notifica
                        NERGiuridico.showNotification('Annotazione eliminata con successo', 'success');
                        this.updateStatus('Annotazione eliminata con successo');
                    } else {
                        // Se c'è un errore, ripristina lo stato originale
                        AnnotationLogger.error(`Errore nell'eliminazione: ${data.message}`, data);
                        NERGiuridico.showNotification(`Errore: ${data.message}`, 'danger');
                        this.updateStatus(`Errore: ${data.message}`, true);
                        
                        // Ricarica tutte le annotazioni
                        this.loadInitialAnnotations();
                        this.highlightAnnotations();
                    }
                })
                .catch(error => {
                    AnnotationLogger.error('Errore durante l\'eliminazione', error);
                    NERGiuridico.showNotification('Errore durante l\'eliminazione', 'danger');
                    this.updateStatus('Errore durante l\'eliminazione', true);
                    
                    // Ricarica tutte le annotazioni
                    this.loadInitialAnnotations();
                    this.highlightAnnotations();
                })
                .finally(() => {
                    this.endPendingOperation();
                    AnnotationLogger.endOperation('deleteAnnotation');
                });
            },
            'Elimina',
            'btn-danger'
        );
    },
    
    /**
     * Esegue il riconoscimento automatico delle entità
     */
    performAutoAnnotation: function() {
        if (!this.elements.autoAnnotateBtn || this.elements.autoAnnotateBtn.disabled) return;
        
        const text = this.elements.textContent.textContent;
        
        // Usa la funzione di conferma centralizzata
        NERGiuridico.showConfirmation(
            'Riconoscimento automatico',
            'Vuoi eseguire il riconoscimento automatico delle entità nel testo? Questo processo potrebbe richiedere alcuni secondi.',
            () => {
                AnnotationLogger.startOperation('autoAnnotation');
                this.startPendingOperation();
                
                // Mostra un indicatore di caricamento
                NERGiuridico.showLoading(this.elements.autoAnnotateBtn, 'Elaborazione...');
                this.updateStatus('Riconoscimento automatico in corso...');
                
                // Richiedi il riconoscimento automatico delle entità
                fetch('/api/recognize', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ text: text })
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Errore HTTP: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'success') {
                        const entities = data.entities;
                        AnnotationLogger.debug(`Riconosciute ${entities.length} entità automaticamente`);
                        
                        if (entities.length === 0) {
                            NERGiuridico.showNotification('Nessuna entità riconosciuta', 'info');
                            this.updateStatus('Nessuna entità riconosciuta');
                            NERGiuridico.hideLoading(this.elements.autoAnnotateBtn);
                            return;
                        }
                        
                        // Per ogni entità riconosciuta, crea un'annotazione
                        let savedCount = 0;
                        const totalToSave = entities.length;
                        
                        this.updateStatus(`Riconosciute ${entities.length} entità. Salvataggio in corso...`);
                        
                        // Funzione per salvare un'annotazione e gestire il conteggio
                        const saveAnnotationWithTracking = (annotation) => {
                            return fetch('/api/save_annotation', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify({
                                    doc_id: this.state.docId,
                                    annotation: annotation
                                })
                            })
                            .then(response => {
                                if (!response.ok) {
                                    throw new Error(`Errore HTTP: ${response.status}`);
                                }
                                return response.json();
                            })
                            .then(data => {
                                if (data.status === 'success') {
                                    savedCount++;
                                    
                                    // Aggiorna il testo del pulsante per mostrare il progresso
                                    this.elements.autoAnnotateBtn.innerHTML = 
                                        `<span class="spinner-border spinner-border-sm me-2"></span>Salvate ${savedCount}/${totalToSave}...`;
                                    this.updateStatus(`Salvate ${savedCount}/${totalToSave} annotazioni...`);
                                    
                                    // Aggiungi l'annotazione alla struttura dati
                                    this.state.annotations.push(data.annotation);
                                    
                                    // Aggiungi l'annotazione alla lista
                                    this.addAnnotationToDOM(data.annotation);
                                }
                                return data;
                            });
                        };
                        
                        // Salva le annotazioni in sequenza per evitare problemi di concorrenza
                        let savePromise = Promise.resolve();
                        
                        entities.forEach(entity => {
                            // Prepara l'annotazione
                            const annotation = {
                                start: entity.start,
                                end: entity.end,
                                text: entity.text,
                                type: entity.type
                            };
                            
                            // Aggiungi alla catena di promise
                            savePromise = savePromise.then(() => saveAnnotationWithTracking(annotation));
                        });
                        
                        // Una volta salvate tutte le annotazioni
                        savePromise.then(() => {
                            AnnotationLogger.debug(`Salvate ${savedCount} annotazioni automatiche`);
                            
                            // Ordina le annotazioni
                            this.state.annotations = this.sortAnnotationsByPosition(this.state.annotations);
                            
                            // Ripristina il pulsante
                            NERGiuridico.hideLoading(this.elements.autoAnnotateBtn);
                            
                            // Aggiorna l'evidenziazione delle annotazioni
                            this.highlightAnnotations();
                            
                            // Aggiorna l'UI
                            this.updateUI();
                            
                            // Mostra notifica
                            NERGiuridico.showNotification(`Salvate ${savedCount} annotazioni automatiche`, 'success');
                            this.updateStatus(`Completato: salvate ${savedCount} annotazioni automatiche`);
                        })
                        .catch(error => {
                            AnnotationLogger.error('Errore durante il salvataggio delle annotazioni automatiche', error);
                            NERGiuridico.hideLoading(this.elements.autoAnnotateBtn);
                            NERGiuridico.showNotification('Errore durante il salvataggio delle annotazioni', 'danger');
                            this.updateStatus('Errore durante il salvataggio delle annotazioni', true);
                        });
                    } else {
                        AnnotationLogger.error(`Errore nel riconoscimento automatico: ${data.message}`, data);
                        NERGiuridico.showNotification(`Errore: ${data.message}`, 'danger');
                        this.updateStatus(`Errore: ${data.message}`, true);
                        NERGiuridico.hideLoading(this.elements.autoAnnotateBtn);
                    }
                })
                .catch(error => {
                    AnnotationLogger.error('Errore durante il riconoscimento automatico', error);
                    NERGiuridico.showNotification('Errore durante il riconoscimento automatico', 'danger');
                    this.updateStatus('Errore durante il riconoscimento automatico', true);
                    NERGiuridico.hideLoading(this.elements.autoAnnotateBtn);
                })
                .finally(() => {
                    this.endPendingOperation();
                    AnnotationLogger.endOperation('autoAnnotation');
                });
            },
            'Procedi',
            'btn-primary'
        );
    },
    
    /**
     * Aggiunge un'annotazione al DOM
     * @param {Object} annotation - L'annotazione da aggiungere
     */
    addAnnotationToDOM: function(annotation) {
        AnnotationLogger.debug(`Aggiunta annotazione alla lista: ${annotation.id}`, annotation);
        
        // Ottieni il colore e il nome del tipo di entità
        const entityColor = this.getEntityColorById(annotation.type);
        const entityName = this.getEntityNameById(annotation.type);
        
        // Nascondi il messaggio "nessuna annotazione"
        if (this.elements.noAnnotationsMsg) this.elements.noAnnotationsMsg.classList.add('d-none');
        
        // Crea l'elemento HTML per l'annotazione
        const annotationItem = document.createElement('div');
        annotationItem.className = 'annotation-item card mb-2';
        annotationItem.dataset.id = annotation.id;
        annotationItem.dataset.start = annotation.start;
        annotationItem.dataset.end = annotation.end;
        annotationItem.dataset.type = annotation.type;
        
        annotationItem.innerHTML = `
            <div class="card-body p-2">
                <div class="d-flex align-items-start mb-2">
                    <span class="annotation-type badge me-2" style="background-color: ${entityColor}">
                        ${entityName || annotation.type}
                    </span>
                    <span class="annotation-text flex-grow-1 small">${annotation.text}</span>
                </div>
                <div class="annotation-actions d-flex justify-content-end">
                    <button class="btn btn-sm btn-outline-primary jump-to-annotation me-1" data-id="${annotation.id}" title="Vai al testo">
                        <i class="fas fa-search"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger delete-annotation" data-id="${annotation.id}" title="Elimina">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            </div>
        `;
        
        // Aggiungi l'elemento all'inizio della lista
        if (this.elements.annotationsContainer) {
            this.elements.annotationsContainer.insertBefore(annotationItem, this.elements.annotationsContainer.firstChild);
        }
        
        // Evidenzia brevemente
        annotationItem.classList.add('highlight');
        setTimeout(() => {
            annotationItem.classList.remove('highlight');
        }, 2000);
        
        // Aggiorna l'UI
        this.updateAnnotationCount();
        this.updateEntityCounters();
        this.updateAnnotationProgress();
        this.updateVisibleCount();
    },
    
    /**
     * Evidenzia le annotazioni esistenti nel testo
     */
    highlightAnnotations: function() {
        AnnotationLogger.startOperation('highlightAnnotations');
        
        if (!this.elements.textContent) {
            AnnotationLogger.warn('Elemento #text-content non trovato, impossibile evidenziare le annotazioni');
            AnnotationLogger.endOperation('highlightAnnotations');
            return;
        }
        
        const text = this.elements.textContent.textContent;
        
        // Se non ci sono annotazioni, mostra solo il testo originale
        if (this.state.annotations.length === 0) {
            this.elements.textContent.innerHTML = this.escapeHtml(text);
            AnnotationLogger.debug('Nessuna annotazione da evidenziare');
            AnnotationLogger.endOperation('highlightAnnotations');
            return;
        }
        
        // Rendirizza il testo evidenziato con le annotazioni
        try {
            // Ordina le annotazioni per posizione
            const annotations = this.sortAnnotationsByPosition(this.state.annotations);
            
            // Creazione di array di segmenti di testo
            // Ogni elemento rappresenta un segmento del testo, con info se fa parte di un'annotazione
            const segments = this.createTextSegments(text, annotations);
            
            // Costruisci l'HTML con i segmenti
            let htmlContent = '';
            
            segments.forEach(segment => {
                if (segment.annotations.length === 0) {
                    // Testo semplice senza annotazioni
                    htmlContent += this.escapeHtml(segment.text);
                } else {
                    // Determina quale annotazione usare (in caso di sovrapposizioni)
                    // Per sovrapposizioni, usiamo la prima nell'ordine (che è quella più lunga)
                    const primaryAnnotation = segment.annotations[0];
                    
                    // Prepara la classe per evidenziare sovrapposizioni
                    const isOverlap = segment.annotations.length > 1 ? 'overlap' : '';
                    
                    // Crea l'elemento di evidenziazione
                    const entityName = this.getEntityNameById(primaryAnnotation.type);
                    htmlContent += `<span class="entity-highlight ${isOverlap}" 
                          style="background-color: ${primaryAnnotation.color};" 
                          data-id="${primaryAnnotation.id}" 
                          data-type="${primaryAnnotation.type}">
                          <span class="tooltip">${entityName}: ${this.escapeHtml(primaryAnnotation.text)}</span>
                          ${this.escapeHtml(segment.text)}
                          </span>`;
                }
            });
            
            // Sostituisci il contenuto
            this.elements.textContent.innerHTML = htmlContent;
            
            // Ottimizza la visualizzazione del testo
            this.optimizeTextDisplay();
            
            AnnotationLogger.debug(`Evidenziate ${annotations.length} annotazioni nel testo`);
        } catch (error) {
            AnnotationLogger.error("Errore nell'evidenziazione delle annotazioni:", error);
            
            // In caso di errore, mostra almeno il testo originale
            this.elements.textContent.innerHTML = this.escapeHtml(text);
        }
        
        AnnotationLogger.endOperation('highlightAnnotations');
    },
    
    /**
     * Crea i segmenti di testo per l'evidenziazione
     * @param {string} text - Il testo completo
     * @param {Array} annotations - Le annotazioni ordinate
     * @returns {Array} - Array di segmenti di testo
     */
    createTextSegments: function(text, annotations) {
        // Creazione di array di segmenti di testo
        // Ogni elemento rappresenta un segmento del testo, con info se fa parte di un'annotazione
        const segments = [];
        
        // Assicuriamoci che le posizioni non si sovrappongano
        const sortedBreakpoints = [];
        
        // Raccogli tutti i punti di inizio e fine
        annotations.forEach(ann => {
            sortedBreakpoints.push({ position: ann.start, isStart: true, annotation: ann });
            sortedBreakpoints.push({ position: ann.end, isStart: false, annotation: ann });
        });
        
        // Ordina i breakpoint per posizione
        sortedBreakpoints.sort((a, b) => {
            if (a.position !== b.position) return a.position - b.position;
            // Se stessa posizione, prima gli endpoint (fine annotazione)
            return a.isStart ? 1 : -1;
        });
        
        // Mantieni traccia delle annotazioni attive
        const activeAnnotations = new Set();
        
        // Processa i breakpoint
        let lastPosition = 0;
        
        sortedBreakpoints.forEach(breakpoint => {
            // Se c'è del testo prima di questo breakpoint, creane un segmento
            if (breakpoint.position > lastPosition) {
                const segmentText = text.substring(lastPosition, breakpoint.position);
                if (segmentText) {
                    segments.push({
                        text: segmentText,
                        annotations: Array.from(activeAnnotations)
                    });
                }
            }
            
            // Aggiorna lo stato delle annotazioni attive
            if (breakpoint.isStart) {
                activeAnnotations.add(breakpoint.annotation);
            } else {
                activeAnnotations.delete(breakpoint.annotation);
            }
            
            // Aggiorna l'ultima posizione
            lastPosition = breakpoint.position;
        });
        
        // Aggiungi il testo rimanente dopo l'ultima annotazione
        if (lastPosition < text.length) {
            segments.push({
                text: text.substring(lastPosition),
                annotations: []
            });
        }
        
        return segments;
    },
    
    /**
     * Ottimizza la visualizzazione del testo dopo il rendering
     */
    optimizeTextDisplay: function() {
        // Verifica e corregge eventuali problemi di visualizzazione dopo il rendering
        setTimeout(() => {
            const highlights = document.querySelectorAll('.entity-highlight');
            AnnotationLogger.debug(`Ottimizzazione di ${highlights.length} elementi di evidenziazione`);
            
            // Verifica se ci sono sovrapposizioni problematiche
            this.checkForOverlappingHighlights();
        }, 100);
    },
    
    /**
     * Verifica e marca le sovrapposizioni problematiche tra annotazioni evidenziate
     */
    checkForOverlappingHighlights: function() {
        const highlights = Array.from(document.querySelectorAll('.entity-highlight'));
        
        // Gruppo le evidenziazioni per linea
        const lineMap = new Map();
        
        highlights.forEach(highlight => {
            const rect = highlight.getBoundingClientRect();
            const lineKey = Math.round(rect.top); // Arrotondato per gestire piccole differenze
            
            if (!lineMap.has(lineKey)) {
                lineMap.set(lineKey, []);
            }
            
            lineMap.get(lineKey).push({
                element: highlight,
                left: rect.left,
                right: rect.right
            });
        });
        
        AnnotationLogger.debug(`Gruppi di linee trovati: ${lineMap.size}`);
        
        // Controllo e gestisco le sovrapposizioni per ogni linea
        let overlapsFound = 0;
        
        lineMap.forEach((line, lineKey) => {
            if (line.length < 2) return; // Nessuna sovrapposizione possibile
            
            // Ordino per posizione da sinistra
            line.sort((a, b) => a.left - b.left);
            
            // Controllo sovrapposizioni orizzontali
            for (let i = 0; i < line.length - 1; i++) {
                const current = line[i];
                const next = line[i + 1];
                
                if (current.right > next.left + 2) { // 2px di tolleranza
                    AnnotationLogger.debug(`Sovrapposizione orizzontale rilevata alla linea ${lineKey}`, {
                        current: current.element.dataset.id,
                        next: next.element.dataset.id
                    });
                    
                    // Aggiungi classe per evidenziare la sovrapposizione
                    current.element.classList.add('overlap');
                    next.element.classList.add('overlap');
                    overlapsFound++;
                }
            }
        });
        
        AnnotationLogger.debug(`Sovrapposizioni trovate: ${overlapsFound}`);
    },
    
    /**
     * Aggiorna lo stato dell'annotazione
     * @param {string} message - Il messaggio da mostrare
     * @param {boolean} isError - Indica se il messaggio è un errore
     */
    updateStatus: function(message, isError = false) {
        if (!this.elements.annotationStatus) return;
        
        if (!message) {
            this.elements.annotationStatus.classList.add('d-none');
            return;
        }
        
        AnnotationLogger.debug(`Stato aggiornato${isError ? ' (errore)' : ''}: ${message}`);
        
        this.elements.annotationStatus.textContent = message;
        this.elements.annotationStatus.classList.remove('d-none', 'alert-info', 'alert-danger');
        this.elements.annotationStatus.classList.add(isError ? 'alert-danger' : 'alert-info');
        
        // Rimuovi il messaggio dopo un po'
        setTimeout(() => {
            if (this.elements.annotationStatus) {
                this.elements.annotationStatus.classList.add('d-none');
            }
        }, 5000);
    },
    
    /**
     * Aggiorna il contatore del numero totale di annotazioni
     */
    updateAnnotationCount: function() {
        const count = this.state.annotations.length;
        if (this.elements.annotationCount) {
            this.elements.annotationCount.textContent = `(${count})`;
        }
        AnnotationLogger.debug(`Conteggio annotazioni aggiornato: ${count}`);
    },
    
    /**
     * Aggiorna i contatori per tipo di entità
     */
    updateEntityCounters: function() {
        // Resetta tutti i contatori
        document.querySelectorAll('.entity-counter').forEach(counter => {
            counter.textContent = '0';
        });
        
        // Conta le annotazioni per tipo
        const counts = {};
        
        this.state.annotations.forEach(annotation => {
            const type = annotation.type;
            counts[type] = (counts[type] || 0) + 1;
        });
        
        // Aggiorna i contatori
        for (const [type, count] of Object.entries(counts)) {
            const counter = document.querySelector(`.entity-counter[data-type="${type}"]`);
            if (counter) {
                counter.textContent = count;
            }
        }
        
        AnnotationLogger.debug('Contatori per tipo aggiornati', counts);
    },
    
    /**
     * Aggiorna la barra di avanzamento dell'annotazione
     */
    updateAnnotationProgress: function() {
        if (!this.elements.annotationProgress) return;
        
        const totalWords = parseInt(this.elements.textContent.dataset.wordCount) || 100;
        const annotationCount = this.state.annotations.length;
        
        // Calcola una stima della copertura (puramente visiva)
        const coverage = Math.min(annotationCount / (totalWords / 20) * 100, 100);
        
        this.elements.annotationProgress.style.width = `${coverage}%`;
        
        // Aggiorna il colore in base alla copertura
        this.elements.annotationProgress.className = 'progress-bar';
        if (coverage < 30) {
            this.elements.annotationProgress.classList.add('bg-danger');
        } else if (coverage < 70) {
            this.elements.annotationProgress.classList.add('bg-warning');
        } else {
            this.elements.annotationProgress.classList.add('bg-success');
        }
        
        AnnotationLogger.debug(`Progresso annotazione aggiornato: ${coverage.toFixed(1)}%`);
        
        // Aggiorna anche il progresso globale se esiste
        if (typeof window.updateGlobalProgressIndicator === 'function') {
            window.updateGlobalProgressIndicator();
        }
    },
    
    /**
     * Aggiorna il contatore di annotazioni visibili
     */
    updateVisibleCount: function() {
        if (!this.elements.visibleCount) return;
        
        const total = this.state.annotations.length;
        const visible = document.querySelectorAll('.annotation-item:not(.d-none)').length;
        
        this.elements.visibleCount.textContent = visible === total ? total : `${visible}/${total}`;
        
        // Mostra/nascondi il messaggio "Nessuna annotazione"
        if (this.elements.noAnnotationsMsg) {
            if (total === 0) {
                this.elements.noAnnotationsMsg.classList.remove('d-none');
            } else {
                this.elements.noAnnotationsMsg.classList.add('d-none');
            }
        }
        
        AnnotationLogger.debug(`Conteggio visibili aggiornato: ${visible}/${total}`);
    },
    
    /**
     * Aggiorna tutti gli elementi dell'interfaccia
     */
    updateUI: function() {
        this.updateAnnotationCount();
        this.updateEntityCounters();
        this.updateAnnotationProgress();
        this.updateVisibleCount();
    },
    
    /**
     * Filtra le annotazioni in base al testo di ricerca
     */
    filterAnnotations: function() {
        if (!this.elements.searchAnnotations) return;
        
        const query = this.elements.searchAnnotations.value.toLowerCase();
        this.state.filterText = query;
        
        document.querySelectorAll('.annotation-item').forEach(item => {
            const text = item.querySelector('.annotation-text').textContent.toLowerCase();
            const type = item.querySelector('.annotation-type').textContent.toLowerCase();
            
            if (text.includes(query) || type.includes(query)) {
                item.classList.remove('d-none');
            } else {
                item.classList.add('d-none');
            }
        });
        
        // Aggiorna il contatore di elementi visibili
        this.updateVisibleCount();
    },
    
    /**
     * Ordina le annotazioni nella lista
     * @param {string} sortBy - Criterio di ordinamento ('position' o 'type')
     */
    sortAnnotations: function(sortBy) {
        AnnotationLogger.debug(`Ordinamento annotazioni per ${sortBy}`);
        
        const container = document.getElementById('annotations-container');
        const items = Array.from(container.querySelectorAll('.annotation-item'));
        
        if (items.length === 0) return;
        
        items.sort((a, b) => {
            if (sortBy === 'position') {
                return parseInt(a.dataset.start) - parseInt(b.dataset.start);
            } else if (sortBy === 'type') {
                const typeA = a.dataset.type;
                const typeB = b.dataset.type;
                return typeA.localeCompare(typeB);
            }
            return 0;
        });
        
        // Rimuovi gli elementi esistenti
        items.forEach(item => item.remove());
        
        // Aggiungi gli elementi ordinati
        items.forEach(item => container.appendChild(item));
        
        AnnotationLogger.debug(`Ordinamento completato, ${items.length} elementi riordinati`);
    },
    
    /**
     * Salta a una specifica annotazione nel testo
     * @param {string} annotationId - L'ID dell'annotazione da evidenziare
     */
    jumpToAnnotation: function(annotationId) {
        AnnotationLogger.debug(`Salto all'annotazione ${annotationId}`);
        
        const highlight = document.querySelector(`.entity-highlight[data-id="${annotationId}"]`);
        
        if (highlight) {
            // Rimuovi la classe focused da tutte le evidenziazioni
            document.querySelectorAll('.entity-highlight.focused').forEach(el => {
                el.classList.remove('focused');
            });
            
            // Aggiungi la classe focused a questa evidenziazione
            highlight.classList.add('focused');
            
            // Aggiorna lo stato
            this.state.highlightedAnnotationId = annotationId;
            
            // Scorri fino all'annotazione nel testo
            highlight.scrollIntoView({behavior: 'smooth', block: 'center'});
            
            // Aggiungi un effetto flash
            highlight.style.transition = 'background-color 0.3s';
            const originalColor = highlight.style.backgroundColor;
            
            highlight.style.backgroundColor = '#ffff00';
            
            setTimeout(() => {
                highlight.style.backgroundColor = originalColor;
                setTimeout(() => {
                    highlight.style.transition = '';
                }, 300);
            }, 800);
        } else {
            AnnotationLogger.warn(`Nessun elemento evidenziato trovato per l'ID: ${annotationId}`);
        }
    },
    
    /**
     * Salta a una specifica annotazione nella lista laterale
     * @param {string} annotationId - L'ID dell'annotazione da evidenziare
     */
    jumpToAnnotationInList: function(annotationId) {
        const annotationItem = document.querySelector(`.annotation-item[data-id="${annotationId}"]`);
        
        if (annotationItem) {
            // Rimuovi selected da tutte le altre annotazioni
            document.querySelectorAll('.annotation-item.selected').forEach(el => {
                if (el !== annotationItem) el.classList.remove('selected');
            });
            
            // Aggiungi selected a questa annotazione
            annotationItem.classList.add('selected');
            
            // Aggiorna lo stato
            this.state.selectedAnnotationId = annotationId;
            
            // Scorri alla annotazione nella lista
            annotationItem.scrollIntoView({behavior: 'smooth', block: 'center'});
            
            // Evidenzia brevemente
            annotationItem.classList.add('highlight');
            setTimeout(() => {
                annotationItem.classList.remove('highlight');
            }, 2000);
        } else {
            AnnotationLogger.warn(`Elemento per l'annotazione ${annotationId} non trovato nella lista`);
        }
    },
    
    /**
     * Attiva/disattiva la modalità a schermo intero
     */
    toggleCleanMode: function() {
        this.state.isCleanMode = !this.state.isCleanMode;
        document.body.classList.toggle('clean-mode', this.state.isCleanMode);
        
        AnnotationLogger.debug(`Modalità clean ${this.state.isCleanMode ? 'attivata' : 'disattivata'}`);
        
        // Gestione dell'icona
        const icon = this.elements.cleanModeToggle.querySelector('i');
        if (icon) {
            if (this.state.isCleanMode) {
                icon.className = 'fas fa-compress';
                this.elements.cleanModeToggle.title = "Esci dalla modalità a schermo intero";
            } else {
                icon.className = 'fas fa-expand';
                this.elements.cleanModeToggle.title = "Modalità a schermo intero";
            }
        }
        
        NERGiuridico.showNotification(
            this.state.isCleanMode ? 
                'Modalità a schermo intero attivata. Passa con il mouse sui bordi per vedere i pannelli.' : 
                'Modalità a schermo intero disattivata', 
            'info'
        );
        
        // Salva lo stato
        localStorage.setItem('ner-clean-mode', this.state.isCleanMode);
    },
    
    /**
     * Incrementa lo zoom del testo
     */
    zoomIn: function() {
        this.state.currentTextSize = Math.min(this.state.currentTextSize + 0.1, 2);
        this.elements.textContent.style.fontSize = `${this.state.currentTextSize}rem`;
        AnnotationLogger.debug(`Zoom aumentato a ${this.state.currentTextSize}rem`);
    },
    
    /**
     * Decrementa lo zoom del testo
     */
    zoomOut: function() {
        this.state.currentTextSize = Math.max(this.state.currentTextSize - 0.1, 0.8);
        this.elements.textContent.style.fontSize = `${this.state.currentTextSize}rem`;
        AnnotationLogger.debug(`Zoom diminuito a ${this.state.currentTextSize}rem`);
    },
    
    /**
     * Reimposta lo zoom del testo
     */
    resetZoom: function() {
        this.state.currentTextSize = this.state.originalTextSize;
        this.elements.textContent.style.fontSize = `${this.state.currentTextSize}rem`;
        AnnotationLogger.debug(`Zoom reimpostato a ${this.state.currentTextSize}rem`);
    },
    
    /**
     * Ottiene il colore dell'entità dal suo ID
     * @param {string} entityId - L'ID del tipo di entità
     * @returns {string} - Il colore dell'entità in formato esadecimale
     */
    getEntityColorById: function(entityId) {
        for (const entityType of this.elements.entityTypes) {
            if (entityType.dataset.type === entityId) {
                return entityType.style.backgroundColor;
            }
        }
        return "#CCCCCC";
    },
    
    /**
     * Ottiene il nome dell'entità dal suo ID
     * @param {string} entityId - L'ID del tipo di entità
     * @returns {string} - Il nome visualizzato dell'entità
     */
    getEntityNameById: function(entityId) {
        for (const entityType of this.elements.entityTypes) {
            if (entityType.dataset.type === entityId) {
                return entityType.querySelector('.entity-name').textContent;
            }
        }
        return entityId;
    },
    
    /**
     * Ordina le annotazioni per posizione di inizio e lunghezza
     * @param {Array} annotations - Array di annotazioni da ordinare
     * @returns {Array} - Array ordinato di annotazioni
     */
    sortAnnotationsByPosition: function(annotations) {
        return [...annotations].sort((a, b) => {
            // Ordinamento principale per posizione di inizio
            if (a.start !== b.start) {
                return a.start - b.start;
            }
            // In caso di pari inizio, ordina per lunghezza (più lunghe prima)
            return (b.end - b.start) - (a.end - a.start);
        });
    },
    
    /**
     * Incrementa il contatore delle operazioni in corso
     */
    startPendingOperation: function() {
        this.state.pendingOperations++;
        if (this.state.pendingOperations === 1) {
            // Potrebbe essere aggiunto un indicatore di caricamento globale
            document.body.classList.add('loading');
        }
    },
    
    /**
     * Decrementa il contatore delle operazioni in corso
     */
    endPendingOperation: function() {
        this.state.pendingOperations = Math.max(0, this.state.pendingOperations - 1);
        if (this.state.pendingOperations === 0) {
            document.body.classList.remove('loading');
        }
    },
    
    /**
     * Sincronizza lo stato visuale con i dati delle annotazioni
     * Assicura che tutte le evidenziazioni nel testo corrispondano alle annotazioni nell'elenco
     */
    syncAnnotationState: function() {
        AnnotationLogger.startOperation('syncAnnotationState');
        
        // Ottieni tutte le evidenziazioni attualmente nel testo
        const highlights = document.querySelectorAll('.entity-highlight');
        
        // Crea un set di ID validi
        const validAnnotationIds = new Set(this.state.annotations.map(ann => ann.id));
        
        // Verifica se ci sono evidenziazioni orfane (senza corrispondenza nella lista)
        let orphanedHighlights = 0;
        highlights.forEach(highlight => {
            const highlightId = highlight.dataset.id;
            if (!validAnnotationIds.has(highlightId)) {
                // Questa è un'evidenziazione orfana - rimuovila
                orphanedHighlights++;
                const textContent = highlight.textContent;
                const textNode = document.createTextNode(textContent);
                highlight.parentNode.replaceChild(textNode, highlight);
            }
        });
        
        if (orphanedHighlights > 0) {
            AnnotationLogger.debug(`Rimosse ${orphanedHighlights} evidenziazioni orfane`);
        }
        
        // Controlla le annotazioni mancanti
        const highlightIds = new Set(Array.from(highlights).map(hl => hl.dataset.id));
        const missingIds = this.state.annotations.filter(ann => !highlightIds.has(ann.id));
        
        if (missingIds.length > 0) {
            AnnotationLogger.debug(`Trovate ${missingIds.length} annotazioni senza evidenziazione`);
            // In questo caso, meglio rifare completamente l'evidenziazione
            this.highlightAnnotations();
        }
        
        AnnotationLogger.endOperation('syncAnnotationState');
    },
    
    /**
     * Aggiunge stili dinamici per l'applicazione
     */
    addDynamicStyles: function() {
        // Crea un elemento style se non esiste già
        let styleEl = document.getElementById('annotator-dynamic-styles');
        if (!styleEl) {
            styleEl = document.createElement('style');
            styleEl.id = 'annotator-dynamic-styles';
            document.head.appendChild(styleEl);
        }
        
        // Aggiungi stili CSS
        styleEl.textContent = `
            /* Animazione per rimozione di elementi */
            @keyframes fadeOut {
                from { opacity: 1; transform: translateY(0); }
                to { opacity: 0; transform: translateY(-10px); }
            }
            
            .fade-out {
                animation: fadeOut 0.3s forwards;
            }
            
            /* Miglior contrasto per le entità evidenziate */
            .entity-highlight {
                position: relative;
                border-radius: 2px;
                cursor: pointer;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
                transition: all 0.2s ease;
            }
            
            .entity-highlight:hover {
                z-index: 10;
                transform: translateY(-2px);
                box-shadow: 0 3px 6px rgba(0, 0, 0, 0.16);
            }
            
            /* Miglior stile per le annotazioni in overlap */
            .entity-highlight.overlap {
                outline: 2px dashed rgba(255, 255, 255, 0.7);
                z-index: 2;
                box-shadow: 0 0 0 1px #ff9800, 0 1px 2px rgba(0, 0, 0, 0.08);
            }
            
            /* Stile per highlight focused/selezionato */
            .entity-highlight.focused {
                outline: 2px solid #2563eb;
                outline-offset: 2px;
                z-index: 3;
            }
            
            /* Stile per elementi nell'annotationsContainer */
            .annotation-item {
                transition: all 0.3s ease;
                border-left: 3px solid transparent;
            }
            
            .annotation-item:hover {
                transform: translateX(4px);
            }
            
            .annotation-item.selected {
                background-color: #f0f9ff;
                border-left-color: #2563eb;
            }
            
            /* Stile globale di caricamento */
            body.loading {
                position: relative;
            }
            
            body.loading::after {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                height: 3px;
                background: linear-gradient(to right, transparent, #2563eb, transparent);
                animation: loadingBar 2s infinite;
                z-index: 9999;
            }
            
            @keyframes loadingBar {
                0% { transform: translateX(-100%); }
                100% { transform: translateX(100%); }
            }
        `;
    },
    
    /**
     * Inserisce caratteri di escape in una stringa HTML
     * @param {string} text - La stringa da formattare
     * @returns {string} - La stringa con caratteri di escape
     */
    escapeHtml: function(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// Inizializzazione dell'applicazione
document.addEventListener('DOMContentLoaded', function() {
    AnnotationManager.init();
    
    // Esponi le funzioni globalmente per compatibilità con il codice esistente
    window.updateAnnotationCount = () => AnnotationManager.updateAnnotationCount();
    window.addAnnotationToList = (annotation) => AnnotationManager.addAnnotationToDOM(annotation);
    window.highlightExistingAnnotations = () => AnnotationManager.highlightAnnotations();
    window.jumpToAnnotation = (annotationId) => AnnotationManager.jumpToAnnotation(annotationId);
    window.deleteAnnotation = (annotationId) => AnnotationManager.deleteAnnotation(annotationId);
    window.updateStatus = (message, isError) => AnnotationManager.updateStatus(message, isError);
    window.clearAnnotations = (docId, entityType) => {
        // Implementazione da mantenere per retrocompatibilità
        return new Promise((resolve, reject) => {
            NERGiuridico.showConfirmation(
                entityType ? `Elimina annotazioni di tipo ${entityType}` : 'Elimina tutte le annotazioni',
                entityType ? 
                    `Sei sicuro di voler eliminare tutte le annotazioni di tipo ${entityType}?` : 
                    'Sei sicuro di voler eliminare tutte le annotazioni?',
                () => {
                    AnnotationManager.startPendingOperation();
                    
                    const requestData = entityType 
                        ? { doc_id: docId, entity_type: entityType } 
                        : { doc_id: docId };
                    
                    fetch('/api/clear_annotations', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(requestData)
                    })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`Errore HTTP: ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        AnnotationManager.endPendingOperation();
                        if (data.status === 'success') {
                            NERGiuridico.showNotification(data.message || 'Annotazioni eliminate con successo', 'success');
                            setTimeout(() => {
                                window.location.reload();
                            }, 1500);
                            resolve(true);
                        } else {
                            NERGiuridico.showNotification('Errore: ' + data.message, 'danger');
                            reject(new Error(data.message));
                        }
                    })
                    .catch(error => {
                        AnnotationManager.endPendingOperation();
                        console.error('Errore nella richiesta di eliminazione annotazioni', error);
                        NERGiuridico.showNotification('Si è verificato un errore durante l\'eliminazione', 'danger');
                        reject(error);
                    });
                },
                'Elimina',
                'btn-danger'
            );
        });
    };
});