/**
 * annotator.js - Modulo principale per le funzionalità di annotazione
 * 
 * Versione ottimizzata con gestione errori migliorata e performance ottimizzata
 * @version 3.0.0
 */

const Annotator = (function() {
    'use strict';
    
    // Stato dell'applicazione
    const state = {
        initialized: false,
        selectedEntityType: null,
        annotations: [],
        isProcessing: false,
        docId: null,
        errorCount: 0,
        lastError: null
    };
    
    // Elementi DOM principali
    let elements = {
        textContent: null,
        entityTypes: null,
        annotationsContainer: null,
        searchInput: null,
        clearButton: null,
        autoAnnotateButton: null
    };
    
    // Configurazione
    const config = {
        debugMode: false,
        retryLimit: 3,
        textHighlightDelay: 10,
        saveRetryDelay: 1000,
        maxWordCount: 10000
    };
    
    /**
     * Inizializza il modulo di annotazione
     * @param {Object} options - Opzioni di configurazione
     * @returns {boolean} - Stato dell'inizializzazione
     */
    function initialize(options = {}) {
        try {
            // Estendi la configurazione con le opzioni fornite
            Object.assign(config, options);
            
            // Ottieni gli elementi DOM principali
            elements.textContent = document.getElementById('text-content');
            elements.entityTypes = document.querySelectorAll('.entity-type');
            elements.annotationsContainer = document.getElementById('annotations-container');
            elements.searchInput = document.getElementById('search-annotations');
            elements.clearButton = document.getElementById('clear-selection');
            elements.autoAnnotateButton = document.getElementById('auto-annotate');
            
            // Verifica che gli elementi essenziali esistano
            if (!elements.textContent) {
                logError('Elemento #text-content non trovato');
                return false;
            }
            
            // Ottieni l'ID del documento
            state.docId = elements.textContent.dataset.docId;
            if (!state.docId) {
                logError('ID documento mancante');
                return false;
            }
            
            // Carica le annotazioni esistenti
            loadExistingAnnotations();
            
            // Configura gli event handlers
            setupEventHandlers();
            
            // Segnala inizializzazione completata
            state.initialized = true;
            log('Modulo di annotazione inizializzato con successo');
            
            return true;
        } catch (error) {
            logError('Errore durante l\'inizializzazione', error);
            return false;
        }
    }
    
    /**
     * Configura i gestori di eventi per l'interfaccia utente
     */
    function setupEventHandlers() {
        try {
            // Gestione selezione tipo di entità
            elements.entityTypes.forEach(entityType => {
                entityType.addEventListener('click', function() {
                    selectEntityType(this.dataset.type);
                });
            });
            
            // Gestione selezione del testo
            if (elements.textContent) {
                elements.textContent.addEventListener('mouseup', handleTextSelection);
            }
            
            // Gestione ricerca annotazioni
            if (elements.searchInput) {
                elements.searchInput.addEventListener('input', function() {
                    const query = this.value.toLowerCase();
                    filterAnnotations(query);
                });
            }
            
            // Gestione reset selezione
            if (elements.clearButton) {
                elements.clearButton.addEventListener('click', clearSelection);
            }
            
            // Gestione annotazione automatica
            if (elements.autoAnnotateButton) {
                elements.autoAnnotateButton.addEventListener('click', performAutoAnnotation);
            }
            
            // Gestione delle azioni sulle annotazioni esistenti
            if (elements.annotationsContainer) {
                elements.annotationsContainer.addEventListener('click', handleAnnotationAction);
            }
            
            // Scorciatoie da tastiera
            document.addEventListener('keydown', handleKeyboardShortcuts);
            
            log('Event handlers configurati');
        } catch (error) {
            logError('Errore nella configurazione degli event handlers', error);
        }
    }
    
    /**
     * Gestisce le azioni sulle annotazioni (elimina, vai a)
     * @param {Event} e - Evento click
     */
    function handleAnnotationAction(e) {
        try {
            // Gestione pulsante eliminazione
            if (e.target.closest('.delete-annotation')) {
                const btn = e.target.closest('.delete-annotation');
                const annotationId = btn.dataset.id;
                deleteAnnotation(annotationId);
                return;
            }
            
            // Gestione pulsante di navigazione
            if (e.target.closest('.jump-to-annotation')) {
                const btn = e.target.closest('.jump-to-annotation');
                const annotationId = btn.dataset.id;
                jumpToAnnotation(annotationId);
                return;
            }
            
            // Selezione di un'annotazione
            const annotationItem = e.target.closest('.annotation-item');
            if (annotationItem && !e.target.closest('button')) {
                // Gestione selezione annotazione
                document.querySelectorAll('.annotation-item.selected').forEach(item => {
                    item.classList.remove('selected');
                });
                annotationItem.classList.add('selected');
            }
        } catch (error) {
            logError('Errore nella gestione delle azioni sulle annotazioni', error);
        }
    }
    
    /**
     * Gestisce le scorciatoie da tastiera
     * @param {KeyboardEvent} e - Evento tastiera
     */
    function handleKeyboardShortcuts(e) {
        try {
            // Escape per annullare la selezione
            if (e.key === 'Escape') {
                clearSelection();
            }
            
            // Alt+A per annotazione automatica
            if (e.key === 'a' && e.altKey && elements.autoAnnotateButton && !elements.autoAnnotateButton.disabled) {
                e.preventDefault();
                performAutoAnnotation();
            }
            
            // Ctrl/Cmd + numero per selezionare tipo di entità
            if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '9') {
                e.preventDefault();
                const index = parseInt(e.key) - 1;
                if (index < elements.entityTypes.length) {
                    elements.entityTypes[index].click();
                }
            }
        } catch (error) {
            logError('Errore nella gestione delle scorciatoie da tastiera', error);
        }
    }
    
    /**
     * Carica le annotazioni esistenti dal DOM
     */
    function loadExistingAnnotations() {
        try {
            state.annotations = [];
            const items = document.querySelectorAll('.annotation-item');
            
            items.forEach(item => {
                try {
                    const id = item.dataset.id;
                    const text = item.querySelector('.annotation-text').textContent;
                    const type = item.dataset.type;
                    const start = parseInt(item.dataset.start);
                    const end = parseInt(item.dataset.end);
                    
                    // Trova il colore dall'elemento badge
                    const typeElement = item.querySelector('.annotation-type');
                    const color = typeElement ? typeElement.style.backgroundColor : "";
                    
                    state.annotations.push({ id, text, type, start, end, color });
                } catch (error) {
                    logError(`Errore nel caricamento dell'annotazione`, error);
                }
            });
            
            log(`Caricate ${state.annotations.length} annotazioni dal DOM`);
            
            // Evidenzia le annotazioni nel testo
            highlightAnnotations();
        } catch (error) {
            logError('Errore nel caricamento delle annotazioni', error);
        }
    }
    
    /**
     * Seleziona un tipo di entità
     * @param {string} entityType - ID del tipo di entità
     */
    function selectEntityType(entityType) {
        try {
            // Rimuovi selezione dai tipi precedenti
            elements.entityTypes.forEach(el => {
                el.classList.remove('selected');
            });
            
            // Seleziona il nuovo tipo
            const entityElement = document.querySelector(`.entity-type[data-type="${entityType}"]`);
            if (entityElement) {
                entityElement.classList.add('selected');
                state.selectedEntityType = entityType;
                
                // Aggiorna stato UI
                const entityName = entityElement.querySelector('.entity-name').textContent;
                updateStatus(`Tipo selezionato: ${entityName}`);
            }
        } catch (error) {
            logError('Errore nella selezione del tipo di entità', error);
        }
    }
    
    /**
     * Gestisce la selezione del testo
     * @param {Event} e - Evento mouseup
     */
    function handleTextSelection(e) {
        try {
            const selection = window.getSelection();
            
            // Controlla se c'è del testo selezionato
            if (selection.toString().trim() === '') {
                return;
            }
            
            // Controlla se è stato selezionato un tipo di entità
            if (!state.selectedEntityType) {
                showNotification('Seleziona prima un tipo di entità', 'warning');
                return;
            }
            
            const range = selection.getRangeAt(0);
            
            // Calcola l'offset nel testo
            const fullText = elements.textContent.textContent;
            const startNode = range.startContainer;
            const endNode = range.endContainer;
            
            const startOffset = getTextNodeOffset(startNode, range.startOffset);
            const endOffset = getTextNodeOffset(endNode, range.endOffset);
            
            if (startOffset < 0 || endOffset < 0) {
                logError('Impossibile determinare la posizione nel testo');
                return;
            }
            
            // Verifica che la selezione sia valida
            if (startOffset >= endOffset) {
                updateStatus('Selezione non valida', true);
                return;
            }
            
            // Ottieni il testo selezionato
            const selectedText = fullText.substring(startOffset, endOffset);
            
            // Verifica sovrapposizioni
            const hasOverlap = checkForOverlaps(startOffset, endOffset);
            
            if (hasOverlap) {
                // Chiedi conferma
                if (confirm('La selezione si sovrappone a un\'annotazione esistente. Continuare?')) {
                    createAnnotation(startOffset, endOffset, selectedText, state.selectedEntityType);
                }
            } else {
                // Crea l'annotazione
                createAnnotation(startOffset, endOffset, selectedText, state.selectedEntityType);
            }
        } catch (error) {
            logError('Errore nella selezione del testo', error);
        }
    }
    
    /**
     * Ottiene l'offset assoluto di un nodo di testo
     * @param {Node} node - Il nodo di testo
     * @param {number} offset - L'offset nel nodo
     * @returns {number} - L'offset assoluto nel testo completo
     */
    function getTextNodeOffset(node, offset) {
        try {
            if (!elements.textContent.contains(node)) {
                return -1;
            }
            
            let currentOffset = 0;
            const textNodes = [];
            
            // Funzione ricorsiva per raccogliere i nodi di testo
            function collectTextNodes(element) {
                if (element.nodeType === Node.TEXT_NODE) {
                    textNodes.push(element);
                } else {
                    for (let i = 0; i < element.childNodes.length; i++) {
                        collectTextNodes(element.childNodes[i]);
                    }
                }
            }
            
            collectTextNodes(elements.textContent);
            
            // Calcola l'offset
            for (const textNode of textNodes) {
                if (textNode === node) {
                    return currentOffset + offset;
                }
                currentOffset += textNode.textContent.length;
            }
            
            return -1;
        } catch (error) {
            logError('Errore nel calcolo dell\'offset di testo', error);
            return -1;
        }
    }
    
    /**
     * Verifica sovrapposizioni con annotazioni esistenti
     * @param {number} start - Inizio nuova selezione
     * @param {number} end - Fine nuova selezione
     * @returns {boolean} - True se ci sono sovrapposizioni
     */
    function checkForOverlaps(start, end) {
        return state.annotations.some(annotation => 
            (start <= annotation.end && end >= annotation.start)
        );
    }
    
    /**
     * Crea una nuova annotazione
     * @param {number} start - Inizio selezione
     * @param {number} end - Fine selezione
     * @param {string} text - Testo selezionato
     * @param {string} type - Tipo di entità
     */
    function createAnnotation(start, end, text, type) {
        try {
            if (state.isProcessing) {
                updateStatus('Operazione in corso, attendere...', true);
                return;
            }
            
            state.isProcessing = true;
            updateStatus('Creazione annotazione in corso...');
            
            const annotation = { start, end, text, type };
            
            // Salva l'annotazione tramite API
            fetch('/api/save_annotation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    doc_id: state.docId,
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
                    // Aggiungi l'annotazione allo stato
                    state.annotations.push(data.annotation);
                    
                    // Aggiungi alla UI
                    addAnnotationToList(data.annotation);
                    
                    // Aggiorna l'evidenziazione
                    highlightAnnotations();
                    
                    // Pulisci la selezione
                    window.getSelection().removeAllRanges();
                    
                    // Mostra conferma
                    showNotification('Annotazione creata con successo', 'success');
                    updateStatus('Annotazione salvata');
                } else {
                    throw new Error(data.message || 'Errore sconosciuto');
                }
            })
            .catch(error => {
                logError('Errore durante il salvataggio dell\'annotazione', error);
                showNotification(`Errore: ${error.message}`, 'danger');
            })
            .finally(() => {
                state.isProcessing = false;
            });
        } catch (error) {
            state.isProcessing = false;
            logError('Errore nella creazione dell\'annotazione', error);
            showNotification('Si è verificato un errore', 'danger');
        }
    }
    
    /**
     * Aggiunge un'annotazione alla lista UI
     * @param {Object} annotation - L'annotazione da aggiungere
     */
    function addAnnotationToList(annotation) {
        try {
            if (!elements.annotationsContainer) return;
            
            // Ottieni il colore e il nome del tipo di entità
            const entityColor = getEntityColorById(annotation.type);
            const entityName = getEntityNameById(annotation.type);
            
            // Nascondi messaggio "nessuna annotazione" se presente
            const noAnnotationsMsg = document.getElementById('no-annotations');
            if (noAnnotationsMsg) noAnnotationsMsg.classList.add('d-none');
            
            // Crea l'elemento annotazione
            const item = document.createElement('div');
            item.className = 'annotation-item';
            item.dataset.id = annotation.id;
            item.dataset.type = annotation.type;
            item.dataset.start = annotation.start;
            item.dataset.end = annotation.end;
            
            // Limita il testo a 50 caratteri
            const displayText = annotation.text.length > 50 
                ? annotation.text.substring(0, 47) + '...' 
                : annotation.text;
            
            item.innerHTML = `
                <div class="annotation-header">
                    <span class="annotation-type" style="background-color: ${entityColor}">${entityName}</span>
                    <span class="annotation-text">${displayText}</span>
                </div>
                <div class="annotation-actions">
                    <button class="btn btn-sm btn-outline-primary jump-to-annotation" data-id="${annotation.id}" title="Vai al testo">
                        <i class="fas fa-search"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger delete-annotation" data-id="${annotation.id}" title="Elimina">
                        <i class="fas fa-trash-alt"></i>
                    </button>
                </div>
            `;
            
            // Aggiungi alla lista
            elements.annotationsContainer.appendChild(item);
            
            // Aggiorna contatori
            updateAnnotationCount();
            
            return item;
        } catch (error) {
            logError('Errore nell\'aggiunta dell\'annotazione alla lista', error);
            return null;
        }
    }
    
    /**
     * Aggiorna il conteggio delle annotazioni
     */
    function updateAnnotationCount() {
        try {
            const count = document.querySelectorAll('.annotation-item').length;
            const countElement = document.getElementById('annotation-count');
            if (countElement) {
                countElement.textContent = `(${count})`;
            }
            
            // Aggiorna la barra di progresso se esiste
            const progressBar = document.getElementById('annotation-progress');
            if (progressBar) {
                const totalWords = parseInt(elements.textContent.dataset.wordCount) || 100;
                const coverage = Math.min(count / (totalWords / 20) * 100, 100);
                progressBar.style.width = `${coverage}%`;
            }
            
            log(`Conteggio annotazioni aggiornato: ${count}`);
        } catch (error) {
            logError('Errore nell\'aggiornamento del conteggio annotazioni', error);
        }
    }
    
    /**
     * Evidenzia le annotazioni nel testo
     */
    function highlightAnnotations() {
        try {
            if (!elements.textContent || state.annotations.length === 0) return;
            
            // Salva il contenuto originale
            const originalContent = elements.textContent.textContent;
            
            // Creiamo un array di caratteri con le loro annotazioni
            const textLength = originalContent.length;
            const charAnnotations = new Array(textLength).fill().map(() => []);
            
            // Associa ogni carattere alle sue annotazioni
            state.annotations.forEach(annotation => {
                for (let i = annotation.start; i < annotation.end; i++) {
                    if (i >= 0 && i < textLength) {
                        charAnnotations[i].push(annotation);
                    }
                }
            });
            
            // Costruisci l'HTML
            let html = '';
            let currentAnnotations = [];
            
            for (let i = 0; i < textLength; i++) {
                const char = originalContent[i];
                const charAnnos = charAnnotations[i];
                
                // Se le annotazioni sono cambiate in questo carattere
                if (!arraysEqual(currentAnnotations, charAnnos)) {
                    // Chiudi i tag aperti
                    for (let j = 0; j < currentAnnotations.length; j++) {
                        html += '</span>';
                    }
                    
                    // Apri nuovi tag
                    charAnnos.forEach(annotation => {
                        const style = `background-color: ${annotation.color || getEntityColorById(annotation.type)}`;
                        html += `<span class="entity-highlight" data-id="${annotation.id}" style="${style}">`;
                    });
                    
                    currentAnnotations = [...charAnnos];
                }
                
                // Aggiungi il carattere, con escape per HTML
                html += escapeHTML(char);
            }
            
            // Chiudi i tag rimanenti
            for (let j = 0; j < currentAnnotations.length; j++) {
                html += '</span>';
            }
            
            // Aggiorna il contenuto
            elements.textContent.innerHTML = html;
            
            // Aggiungi eventi alle entità evidenziate
            setupHighlightEvents();
            
            log('Annotazioni evidenziate nel testo');
        } catch (error) {
            logError('Errore nell\'evidenziazione delle annotazioni', error);
            
            // Ripristina il contenuto originale in caso di errore
            if (elements.textContent) {
                elements.textContent.textContent = originalContent || '';
            }
        }
    }
    
    /**
     * Aggiunge eventi agli elementi evidenziati
     */
    function setupHighlightEvents() {
        try {
            const highlights = document.querySelectorAll('.entity-highlight');
            
            highlights.forEach(highlight => {
                highlight.addEventListener('click', function(e) {
                    e.preventDefault();
                    const annotationId = this.dataset.id;
                    jumpToAnnotation(annotationId);
                });
            });
            
            log(`Eventi configurati per ${highlights.length} elementi evidenziati`);
        } catch (error) {
            logError('Errore nella configurazione degli eventi per gli elementi evidenziati', error);
        }
    }
    
    /**
     * Salta a un'annotazione nel testo
     * @param {string} annotationId - ID dell'annotazione
     */
    function jumpToAnnotation(annotationId) {
        try {
            // Trova l'elemento evidenziato nel testo
            const highlight = document.querySelector(`.entity-highlight[data-id="${annotationId}"]`);
            if (highlight) {
                // Scorri fino all'elemento
                highlight.scrollIntoView({ behavior: 'smooth', block: 'center' });
                
                // Aggiungi classe per evidenziare temporaneamente
                highlight.classList.add('active');
                setTimeout(() => {
                    highlight.classList.remove('active');
                }, 2000);
            }
            
            // Evidenzia anche l'elemento nella lista
            const listItem = document.querySelector(`.annotation-item[data-id="${annotationId}"]`);
            if (listItem) {
                // Rimuovi highlight da altri elementi
                document.querySelectorAll('.annotation-item.selected').forEach(item => {
                    item.classList.remove('selected');
                });
                
                // Aggiungi highlight a questo elemento
                listItem.classList.add('selected');
                
                // Scorri alla annotazione nella lista
                listItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        } catch (error) {
            logError('Errore nel salto all\'annotazione', error);
        }
    }
    
    /**
     * Elimina un'annotazione
     * @param {string} annotationId - ID dell'annotazione
     */
    function deleteAnnotation(annotationId) {
        try {
            if (state.isProcessing) {
                updateStatus('Operazione in corso, attendere...', true);
                return;
            }
            
            // Chiedi conferma
            if (!confirm('Sei sicuro di voler eliminare questa annotazione?')) {
                return;
            }
            
            state.isProcessing = true;
            updateStatus('Eliminazione annotazione in corso...');
            
            fetch('/api/delete_annotation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    doc_id: state.docId,
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
                    // Rimuovi l'annotazione dallo stato
                    state.annotations = state.annotations.filter(a => a.id !== annotationId);
                    
                    // Rimuovi dalla UI
                    const annotationItem = document.querySelector(`.annotation-item[data-id="${annotationId}"]`);
                    if (annotationItem) {
                        annotationItem.remove();
                    }
                    
                    // Aggiorna l'evidenziazione
                    highlightAnnotations();
                    
                    // Aggiorna contatori
                    updateAnnotationCount();
                    
                    // Mostra conferma
                    showNotification('Annotazione eliminata con successo', 'success');
                    updateStatus('Annotazione eliminata');
                } else {
                    throw new Error(data.message || 'Errore sconosciuto');
                }
            })
            .catch(error => {
                logError('Errore durante l\'eliminazione dell\'annotazione', error);
                showNotification(`Errore: ${error.message}`, 'danger');
            })
            .finally(() => {
                state.isProcessing = false;
            });
        } catch (error) {
            state.isProcessing = false;
            logError('Errore nell\'eliminazione dell\'annotazione', error);
            showNotification('Si è verificato un errore', 'danger');
        }
    }
    
    /**
     * Pulisce la selezione corrente
     */
    function clearSelection() {
        try {
            // Deseleziona il tipo di entità
            elements.entityTypes.forEach(el => {
                el.classList.remove('selected');
            });
            
            // Ripristina lo stato
            state.selectedEntityType = null;
            
            // Rimuovi la selezione di testo
            window.getSelection().removeAllRanges();
            
            updateStatus('Selezione annullata');
        } catch (error) {
            logError('Errore nell\'annullamento della selezione', error);
        }
    }
    
    /**
     * Filtra le annotazioni in base al testo di ricerca
     * @param {string} query - Testo di ricerca
     */
    function filterAnnotations(query) {
        try {
            if (!elements.annotationsContainer) return;
            
            const items = elements.annotationsContainer.querySelectorAll('.annotation-item');
            let visibleCount = 0;
            
            items.forEach(item => {
                const text = item.querySelector('.annotation-text').textContent.toLowerCase();
                const type = item.querySelector('.annotation-type').textContent.toLowerCase();
                
                if (text.includes(query) || type.includes(query)) {
                    item.style.display = '';
                    visibleCount++;
                } else {
                    item.style.display = 'none';
                }
            });
            
            // Aggiorna il contatore di visibili
            const visibleCounter = document.getElementById('visible-count');
            if (visibleCounter) {
                const totalCount = items.length;
                visibleCounter.textContent = visibleCount === totalCount ? 
                                            totalCount : `${visibleCount}/${totalCount}`;
            }
            
            log(`Annotazioni filtrate. Visibili: ${visibleCount}/${items.length}`);
        } catch (error) {
            logError('Errore nel filtraggio delle annotazioni', error);
        }
    }
    
    /**
     * Esegue l'annotazione automatica
     */
    function performAutoAnnotation() {
        try {
            if (state.isProcessing) {
                updateStatus('Operazione in corso, attendere...', true);
                return;
            }
            
            // Ottieni il testo completo
            const text = elements.textContent.textContent;
            if (!text) {
                showNotification('Nessun testo da analizzare', 'warning');
                return;
            }
            
            // Chiedi conferma
            if (!confirm('Eseguire il riconoscimento automatico delle entità nel testo? Questo processo potrebbe richiedere tempo.')) {
                return;
            }
            
            state.isProcessing = true;
            updateStatus('Analisi in corso...');
            
            // Disabilita il pulsante e mostra caricamento
            if (elements.autoAnnotateButton) {
                elements.autoAnnotateButton.disabled = true;
                elements.autoAnnotateButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Elaborazione...';
            }
            
            fetch('/api/recognize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
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
                    const entities = data.entities || [];
                    
                    if (entities.length === 0) {
                        showNotification('Nessuna entità riconosciuta', 'info');
                        return;
                    }
                    
                    updateStatus(`Riconosciute ${entities.length} entità. Salvataggio in corso...`);
                    
                    // Salva le entità una alla volta
                    return saveEntitiesSequentially(entities);
                } else {
                    throw new Error(data.message || 'Errore sconosciuto');
                }
            })
            .then(result => {
                if (result && result.savedCount > 0) {
                    showNotification(`Salvate ${result.savedCount} annotazioni`, 'success');
                    highlightAnnotations();
                }
            })
            .catch(error => {
                logError('Errore durante il riconoscimento automatico', error);
                showNotification(`Errore: ${error.message}`, 'danger');
            })
            .finally(() => {
                state.isProcessing = false;
                
                // Ripristina il pulsante
                if (elements.autoAnnotateButton) {
                    elements.autoAnnotateButton.disabled = false;
                    elements.autoAnnotateButton.innerHTML = '<i class="fas fa-magic me-2"></i>Riconoscimento automatico';
                }
                
                updateStatus('Operazione completata');
            });
        } catch (error) {
            state.isProcessing = false;
            logError('Errore nell\'annotazione automatica', error);
            showNotification('Si è verificato un errore', 'danger');
            
            // Ripristina il pulsante
            if (elements.autoAnnotateButton) {
                elements.autoAnnotateButton.disabled = false;
                elements.autoAnnotateButton.innerHTML = '<i class="fas fa-magic me-2"></i>Riconoscimento automatico';
            }
        }
    }
    
    /**
     * Salva le entità in sequenza
     * @param {Array} entities - Entità da salvare
     * @returns {Promise} Promise che si risolve con il conteggio dei salvataggi
     */
    function saveEntitiesSequentially(entities) {
        return new Promise((resolve, reject) => {
            let savedCount = 0;
            let index = 0;
            
            function saveNext() {
                if (index >= entities.length) {
                    resolve({ savedCount });
                    return;
                }
                
                const entity = entities[index];
                index++;
                
                // Prepara l'annotazione
                const annotation = {
                    start: entity.start,
                    end: entity.end,
                    text: entity.text,
                    type: entity.type
                };
                
                // Salva l'annotazione
                fetch('/api/save_annotation', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        doc_id: state.docId,
                        annotation: annotation
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        savedCount++;
                        
                        // Aggiorna stato e UI
                        state.annotations.push(data.annotation);
                        addAnnotationToList(data.annotation);
                        
                        // Aggiorna il testo del pulsante
                        if (elements.autoAnnotateButton) {
                            elements.autoAnnotateButton.innerHTML = 
                                `<span class="spinner-border spinner-border-sm me-2"></span>Salvate ${savedCount}/${entities.length}...`;
                        }
                        
                        updateStatus(`Salvate ${savedCount}/${entities.length} annotazioni...`);
                    }
                    
                    // Passa alla prossima entità
                    setTimeout(saveNext, 10);
                })
                .catch(error => {
                    logError('Errore nel salvataggio di un\'entità', error);
                    // Continua con la prossima anche in caso di errore
                    setTimeout(saveNext, 10);
                });
            }
            
            // Inizia il processo
            saveNext();
        });
    }
    
    /**
     * Ottiene il colore di un tipo di entità dal suo ID
     * @param {string} entityId - ID del tipo di entità
     * @returns {string} - Colore in formato CSS
     */
    function getEntityColorById(entityId) {
        const entityType = document.querySelector(`.entity-type[data-type="${entityId}"]`);
        return entityType ? entityType.style.backgroundColor : "#CCCCCC";
    }
    
    /**
     * Ottiene il nome di un tipo di entità dal suo ID
     * @param {string} entityId - ID del tipo di entità
     * @returns {string} - Nome visualizzato
     */
    function getEntityNameById(entityId) {
        const entityType = document.querySelector(`.entity-type[data-type="${entityId}"]`);
        const nameElement = entityType ? entityType.querySelector('.entity-name') : null;
        return nameElement ? nameElement.textContent : entityId;
    }
    
    /**
     * Mostra una notifica all'utente
     * @param {string} message - Messaggio da mostrare
     * @param {string} type - Tipo di notifica (success, danger, warning, info)
     */
    function showNotification(message, type = 'info') {
        // Se esiste una funzione globale, usala
        if (typeof window.showNotification === 'function') {
            window.showNotification(message, type);
        } else {
            // Altrimenti, usa un alert per i messaggi di errore
            if (type === 'danger' || type === 'warning') {
                alert(message);
            }
            
            // Log sempre nella console
            console.info(`[${type}] ${message}`);
        }
    }
    
    /**
     * Aggiorna lo stato dell'annotazione
     * @param {string} message - Messaggio da mostrare
     * @param {boolean} isError - Se è un messaggio di errore
     */
    function updateStatus(message, isError = false) {
        // Se esiste una funzione globale, usala
        if (typeof window.updateStatus === 'function') {
            window.updateStatus(message, isError);
        } else {
            // Altrimenti, usa la console
            if (isError) {
                console.error(message);
            } else {
                console.info(message);
            }
        }
    }
    
    /**
     * Confronta due array per vedere se sono uguali
     * @param {Array} a - Primo array
     * @param {Array} b - Secondo array
     * @returns {boolean} - True se gli array sono uguali
     */
    function arraysEqual(a, b) {
        if (a === b) return true;
        if (a == null || b == null) return false;
        if (a.length !== b.length) return false;
        
        // Confronto basato sull'ID
        const aIds = a.map(item => item.id).sort();
        const bIds = b.map(item => item.id).sort();
        
        for (let i = 0; i < aIds.length; i++) {
            if (aIds[i] !== bIds[i]) return false;
        }
        
        return true;
    }
    
    /**
     * Applica escape ai caratteri HTML
     * @param {string} str - Stringa da formattare
     * @returns {string} - Stringa con escape HTML
     */
    function escapeHTML(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
    
    /**
     * Registra un messaggio di log
     * @param {string} message - Messaggio da registrare
     */
    function log(message) {
        if (config.debugMode) {
            console.log(`[Annotator] ${message}`);
        }
    }
    
    /**
     * Registra un errore
     * @param {string} message - Messaggio di errore
     * @param {Error} [error] - Oggetto errore
     */
    function logError(message, error) {
        console.error(`[Annotator] ${message}`, error);
        
        state.errorCount++;
        state.lastError = {
            message,
            error: error ? (error.message || error) : null,
            timestamp: new Date()
        };
    }
    
    // API pubblica
    return {
        initialize,
        getState: () => Object.assign({}, state),
        getConfig: () => Object.assign({}, config),
        highlightAnnotations,
        clearSelection,
        getLastError: () => state.lastError,
        getErrorCount: () => state.errorCount
    };
})();

// Esponi globalmente
window.Annotator = Annotator;

// Inizializza quando il DOM è pronto
document.addEventListener('DOMContentLoaded', function() {
    Annotator.initialize({
        debugMode: window.location.search.includes('debug=true')
    });
});