/**
 * annotate.js - Script migliorato per la funzionalità di annotazione
 * 
 * Questo file gestisce tutte le interazioni utente relative all'annotazione di documenti
 * incluse la selezione del testo, la creazione/eliminazione di annotazioni e la
 * visualizzazione delle annotazioni esistenti.
 * 
 * @version 2.1.0
 * @author NER-Giuridico Team
 */

/**
 * Sistema di logging per l'applicazione di annotazione
 * Fornisce funzioni strutturate per il logging con diversi livelli di verbosità
 */
const AnnotationLogger = {
    // Impostare a true per abilitare il logging dettagliato
    debugMode: false,
    
    /**
     * Registra un messaggio informativo
     * @param {string} message - Il messaggio da registrare
     * @param {Object} [data] - Dati aggiuntivi da registrare
     */
    info: function(message, data) {
        console.info(`ℹ️ [Annotator] ${message}`, data || '');
    },
    
    /**
     * Registra un messaggio di debug (solo in modalità debug)
     * @param {string} message - Il messaggio da registrare
     * @param {Object} [data] - Dati aggiuntivi da registrare
     */
    debug: function(message, data) {
        if (this.debugMode) {
            console.debug(`🔍 [Annotator] ${message}`, data || '');
        }
    },
    
    /**
     * Registra un messaggio di avvertimento
     * @param {string} message - Il messaggio da registrare
     * @param {Object} [data] - Dati aggiuntivi da registrare
     */
    warn: function(message, data) {
        console.warn(`⚠️ [Annotator] ${message}`, data || '');
    },
    
    /**
     * Registra un messaggio di errore
     * @param {string} message - Il messaggio da registrare
     * @param {Error} [error] - L'oggetto errore associato
     */
    error: function(message, error) {
        console.error(`❌ [Annotator] ${message}`, error || '');
        if (error && error.stack) {
            console.error(error.stack);
        }
    },
    
    /**
     * Registra un'operazione iniziata
     * @param {string} operation - Il nome dell'operazione
     */
    startOperation: function(operation) {
        this.debug(`Iniziata operazione: ${operation}`);
        console.time(`⏱️ [Annotator] ${operation}`);
    },
    
    /**
     * Registra un'operazione completata
     * @param {string} operation - Il nome dell'operazione
     */
    endOperation: function(operation) {
        console.timeEnd(`⏱️ [Annotator] ${operation}`);
        this.debug(`Completata operazione: ${operation}`);
    }
};

// Inizializzazione dell'applicazione
document.addEventListener('DOMContentLoaded', function() {
    // === Impostazione del logging ===
    AnnotationLogger.debugMode = window.location.search.includes('debug=true');
    AnnotationLogger.info('Inizializzazione applicazione di annotazione');
    AnnotationLogger.startOperation('inizializzazione');
    
    // === Elementi DOM principali ===
    const textContent = document.getElementById('text-content');
    const docId = textContent ? textContent.dataset.docId : null;
    const entityTypes = document.querySelectorAll('.entity-type');
    const clearSelectionBtn = document.getElementById('clear-selection');
    const autoAnnotateBtn = document.getElementById('auto-annotate');
    const annotationsContainer = document.getElementById('annotations-container');
    const searchAnnotations = document.getElementById('search-annotations');
    const annotationStatus = document.getElementById('annotation-status');
    const annotationCount = document.getElementById('annotation-count');
    const visibleCount = document.getElementById('visible-count');
    const annotationProgress = document.getElementById('annotation-progress');
    const noAnnotationsMsg = document.getElementById('no-annotations');
    const cleanModeToggle = document.getElementById('clean-mode-toggle');
    
    // === Controlli per lo zoom del testo ===
    const zoomInBtn = document.getElementById('zoom-in');
    const zoomOutBtn = document.getElementById('zoom-out');
    const resetZoomBtn = document.getElementById('reset-zoom');
    
    // === Stato dell'applicazione ===
    let selectedType = null;
    let originalTextSize = 1.05; // rem
    let currentTextSize = originalTextSize;
    let existingAnnotations = [];
    let isCleanMode = false;
    let pendingOperations = 0;
    
    // === Verifica degli elementi DOM richiesti ===
    if (!textContent) {
        AnnotationLogger.error('Elemento #text-content non trovato. L\'applicazione potrebbe non funzionare correttamente.');
    }
    
    if (!docId) {
        AnnotationLogger.error('ID documento mancante. L\'applicazione potrebbe non funzionare correttamente.');
    }
    
    /**
     * Incrementa il contatore delle operazioni in corso
     */
    function startPendingOperation() {
        pendingOperations++;
        if (pendingOperations === 1) {
            // Potrebbe essere aggiunto un indicatore di caricamento globale
            document.body.classList.add('loading');
        }
    }
    
    /**
     * Decrementa il contatore delle operazioni in corso
     */
    function endPendingOperation() {
        pendingOperations = Math.max(0, pendingOperations - 1);
        if (pendingOperations === 0) {
            document.body.classList.remove('loading');
        }
    }
    
    // === GESTIONE DATI ANNOTAZIONI ===
    
    /**
     * Carica le annotazioni esistenti dal DOM e le memorizza nell'array existingAnnotations
     */
    function loadExistingAnnotations() {
        AnnotationLogger.startOperation('loadExistingAnnotations');
        
        existingAnnotations = [];
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
                
                existingAnnotations.push({ id, text, type, start, end, color });
                
                AnnotationLogger.debug(`Caricata annotazione #${index+1}`, { id, type, start, end });
            } catch (error) {
                AnnotationLogger.error(`Errore nel caricamento dell'annotazione #${index+1}`, error);
            }
        });
        
        // Aggiorna i contatori e statistiche
        updateAnnotationCount();
        updateEntityCounters();
        updateAnnotationProgress();
        updateVisibleCount();
        
        AnnotationLogger.debug(`Caricate ${existingAnnotations.length} annotazioni in totale`);
        AnnotationLogger.endOperation('loadExistingAnnotations');
    }
    
    /**
     * Ordina le annotazioni per posizione di inizio e lunghezza
     * @param {Array} annotations - Array di annotazioni da ordinare
     * @returns {Array} - Array ordinato di annotazioni
     */
    function sortAnnotationsByPosition(annotations) {
        return [...annotations].sort((a, b) => {
            // Ordinamento principale per posizione di inizio
            if (a.start !== b.start) {
                return a.start - b.start;
            }
            // In caso di pari inizio, ordina per lunghezza (più lunghe prima)
            return (b.end - b.start) - (a.end - a.start);
        });
    }
    
    /**
     * Verifica se due annotazioni si sovrappongono
     * @param {Object} a - Prima annotazione
     * @param {Object} b - Seconda annotazione
     * @returns {boolean} - True se le annotazioni si sovrappongono
     */
    function isOverlapping(a, b) {
        return (a.start <= b.end && a.end >= b.start);
    }
    
    // === STATISTICHE E CONTATORI ===
    
    /**
     * Aggiorna il contatore del numero totale di annotazioni
     */
    function updateAnnotationCount() {
        const count = document.querySelectorAll('.annotation-item').length;
        if (annotationCount) annotationCount.textContent = `(${count})`;
        AnnotationLogger.debug(`Conteggio annotazioni aggiornato: ${count}`);
    }
    
    /**
     * Aggiorna i contatori per tipo di entità
     */
    function updateEntityCounters() {
        // Resetta tutti i contatori
        document.querySelectorAll('.entity-counter').forEach(counter => {
            counter.textContent = '0';
        });
        
        // Conta le annotazioni per tipo
        const annotations = document.querySelectorAll('.annotation-item');
        const counts = {};
        
        annotations.forEach(item => {
            const type = item.dataset.type;
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
    }
    
    /**
     * Aggiorna la barra di avanzamento dell'annotazione
     */
    function updateAnnotationProgress() {
        if (!annotationProgress) return;
        
        const totalWords = parseInt(textContent.dataset.wordCount) || 100;
        const annotationCount = document.querySelectorAll('.annotation-item').length;
        
        // Calcola una stima della copertura (puramente visiva)
        const coverage = Math.min(annotationCount / (totalWords / 20) * 100, 100);
        
        annotationProgress.style.width = `${coverage}%`;
        
        // Aggiorna il colore in base alla copertura
        annotationProgress.className = 'progress-bar';
        if (coverage < 30) {
            annotationProgress.classList.add('bg-danger');
        } else if (coverage < 70) {
            annotationProgress.classList.add('bg-warning');
        } else {
            annotationProgress.classList.add('bg-success');
        }
        
        AnnotationLogger.debug(`Progresso annotazione aggiornato: ${coverage.toFixed(1)}%`);
    }
    
    /**
     * Aggiorna il contatore di annotazioni visibili
     */
    function updateVisibleCount() {
        if (!visibleCount) return;
        
        const total = document.querySelectorAll('.annotation-item').length;
        const visible = document.querySelectorAll('.annotation-item:not(.d-none)').length;
        
        visibleCount.textContent = visible === total ? total : `${visible}/${total}`;
        
        // Mostra/nascondi il messaggio "Nessuna annotazione"
        if (noAnnotationsMsg) {
            if (total === 0) {
                noAnnotationsMsg.classList.remove('d-none');
            } else {
                noAnnotationsMsg.classList.add('d-none');
            }
        }
        
        AnnotationLogger.debug(`Conteggio visibili aggiornato: ${visible}/${total}`);
    }
    
    // === VISUALIZZAZIONE E UI ===
    
    /**
     * Ottimizza la visualizzazione del testo dopo il rendering
     */
    function optimizeTextDisplay() {
        AnnotationLogger.startOperation('optimizeTextDisplay');
        
        // Verifica e corregge eventuali problemi di visualizzazione dopo il rendering
        setTimeout(() => {
            const highlights = document.querySelectorAll('.entity-highlight');
            AnnotationLogger.debug(`Ottimizzazione di ${highlights.length} elementi di evidenziazione`);
            
            // Miglioramento per garantire che le annotazioni non causino problemi di layout
            highlights.forEach((highlight, index) => {
                // Verifica se l'elemento ha un layout corretto
                const rect = highlight.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) {
                    AnnotationLogger.warn(`Rilevato elemento di annotazione #${index} con dimensione zero:`, highlight);
                    // Tentativo di correzione forzando un reflow
                    highlight.style.display = 'inline-block';
                    setTimeout(() => highlight.style.display = 'inline', 0);
                }
            });
            
            // Verifica se ci sono sovrapposizioni problematiche
            checkForOverlappingHighlights();
            
            AnnotationLogger.debug('Ottimizzazione display completata');
            AnnotationLogger.endOperation('optimizeTextDisplay');
        }, 500);
    }
    
    /**
     * Verifica e marca le sovrapposizioni problematiche tra annotazioni evidenziate
     */
    function checkForOverlappingHighlights() {
        AnnotationLogger.startOperation('checkForOverlappingHighlights');
        
        const highlights = Array.from(document.querySelectorAll('.entity-highlight'));
        let overlapsFound = 0;
        
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
        AnnotationLogger.endOperation('checkForOverlappingHighlights');
    }
    
    /**
     * Mostra una notifica all'utente
     * @param {string} message - Il messaggio da mostrare
     * @param {string} type - Il tipo di notifica (primary, success, danger, warning, info)
     */
    function showNotification(message, type = 'primary') {
        AnnotationLogger.debug(`Notifica (${type}): ${message}`);
        
        // Usa i toast di Bootstrap
        const toastEl = document.getElementById('notification-toast');
        if (!toastEl) {
            AnnotationLogger.warn('Elemento toast non trovato, impossibile mostrare la notifica');
            return;
        }
        
        const toastBody = toastEl.querySelector('.toast-body');
        if (toastBody) toastBody.textContent = message;
        
        // Imposta il tipo di toast
        toastEl.className = toastEl.className.replace(/bg-\w+/, '');
        toastEl.classList.add(`bg-${type}`);
        
        // Mostra il toast
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
    }
    
    /**
     * Aggiorna lo stato dell'annotazione
     * @param {string} message - Il messaggio da mostrare
     * @param {boolean} isError - Indica se il messaggio è un errore
     */
    function updateStatus(message, isError = false) {
        if (!annotationStatus) return;
        
        if (!message) {
            annotationStatus.classList.add('d-none');
            return;
        }
        
        AnnotationLogger.debug(`Stato aggiornato${isError ? ' (errore)' : ''}: ${message}`);
        
        annotationStatus.textContent = message;
        annotationStatus.classList.remove('d-none', 'alert-info', 'alert-danger');
        annotationStatus.classList.add(isError ? 'alert-danger' : 'alert-info');
        
        // Rimuovi il messaggio dopo un po'
        setTimeout(() => {
            annotationStatus.classList.add('d-none');
        }, 5000);
    }
    
    /**
     * Evidenzia le annotazioni esistenti nel testo
     */
    function highlightExistingAnnotations() {
        AnnotationLogger.startOperation('highlightExistingAnnotations');
        
        const text = textContent.textContent;
        
        // Aggiorna l'array delle annotazioni con i dati correnti dal DOM
        loadExistingAnnotations();
        
        // Se non ci sono annotazioni, mostra solo il testo originale
        if (existingAnnotations.length === 0) {
            textContent.innerHTML = text;
            AnnotationLogger.debug('Nessuna annotazione da evidenziare');
            AnnotationLogger.endOperation('highlightExistingAnnotations');
            return;
        }
        
        // Ordina le annotazioni per posizione di inizio e poi per lunghezza (più lunghe prima)
        const annotations = sortAnnotationsByPosition(existingAnnotations);
        
        // Crea un array di oggetti che rappresentano ogni carattere del testo
        const charObjects = Array.from(text).map((char, index) => ({
            char: char,
            annotations: []
        }));
        
        // Aggiungi informazioni su quali annotazioni coprono ogni carattere
        annotations.forEach(ann => {
            for (let i = ann.start; i < ann.end; i++) {
                if (i >= 0 && i < charObjects.length) {
                    charObjects[i].annotations.push(ann);
                }
            }
        });
        
        // Costruisci l'HTML per evidenziare le annotazioni
        let htmlContent = '';
        let currentAnnotations = [];
        
        for (let i = 0; i < charObjects.length; i++) {
            const charObj = charObjects[i];
            const char = charObj.char;
            
            // Controlla se dobbiamo chiudere tag di entità
            const toClose = currentAnnotations.filter(ann => ann.end === i);
            
            // Chiudi i tag in ordine inverso (l'ultimo aperto è il primo chiuso)
            toClose.sort((a, b) => b.start - a.start).forEach(ann => {
                htmlContent += '</span>';
                currentAnnotations = currentAnnotations.filter(a => a.id !== ann.id);
            });
            
            // Controlla se dobbiamo aprire nuovi tag di entità
            const toOpen = charObj.annotations.filter(ann => ann.start === i);
            
            // Apri nuovi tag
            toOpen.forEach(ann => {
                const isOverlap = currentAnnotations.length > 0;
                const entityName = getEntityNameById(ann.type);
                
                // Modificato il markup HTML per migliorare la visualizzazione
                htmlContent += `<span class="entity-highlight ${isOverlap ? 'overlap' : ''}" 
                      style="background-color: ${ann.color};" 
                      data-id="${ann.id}" 
                      data-type="${ann.type}"><span class="tooltip">${entityName}: ${ann.text}</span><span>`;
                          
                currentAnnotations.push(ann);
            });
            
            // Aggiungi il carattere
            htmlContent += char;
        }
        
        // Chiudi tutti i tag rimanenti alla fine
        currentAnnotations.sort((a, b) => b.start - a.start).forEach(ann => {
            htmlContent += '</span></span>';
        });
        
        // Sostituisci il contenuto
        textContent.innerHTML = htmlContent;
        
        AnnotationLogger.debug(`Evidenziate ${annotations.length} annotazioni nel testo`);
        AnnotationLogger.endOperation('highlightExistingAnnotations');
        
        // Aggiungi eventi alle entità evidenziate
        setupHighlightEvents();
    }
    
    /**
     * Aggiunge eventi interattivi alle entità evidenziate
     */
    function setupHighlightEvents() {
        AnnotationLogger.startOperation('setupHighlightEvents');
        
        const highlights = document.querySelectorAll('.entity-highlight');
        AnnotationLogger.debug(`Configurazione eventi per ${highlights.length} elementi evidenziati`);
        
        highlights.forEach(highlight => {
            highlight.addEventListener('click', function(e) {
                e.preventDefault();
                const annotationId = this.dataset.id;
                const annotationItem = document.querySelector(`.annotation-item[data-id="${annotationId}"]`);
                
                if (annotationItem) {
                    AnnotationLogger.debug(`Clic su evidenziazione, scroll all'annotazione ${annotationId}`);
                    
                    // Scorri fino all'annotazione nella lista
                    annotationItem.scrollIntoView({behavior: 'smooth', block: 'center'});
                    
                    // Evidenzia brevemente l'annotazione nella lista
                    annotationItem.classList.add('highlight');
                    setTimeout(() => {
                        annotationItem.classList.remove('highlight');
                    }, 2000);
                } else {
                    AnnotationLogger.warn(`Elemento per l'annotazione ${annotationId} non trovato nel DOM`);
                }
            });
        });
        
        AnnotationLogger.endOperation('setupHighlightEvents');
    }
    
    /**
     * Salta a una specifica annotazione nel testo
     * @param {string} annotationId - L'ID dell'annotazione da evidenziare
     */
    function jumpToAnnotation(annotationId) {
        AnnotationLogger.debug(`Salto all'annotazione ${annotationId}`);
        
        const highlight = document.querySelector(`.entity-highlight[data-id="${annotationId}"]`);
        
        if (highlight) {
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
    }
    
    // === GESTIONE SELEZIONE E ANNOTAZIONE ===
    
    /**
     * Pulisce la selezione corrente
     */
    function clearSelection() {
        entityTypes.forEach(et => et.classList.remove('selected'));
        selectedType = null;
        window.getSelection().removeAllRanges();
        updateStatus('Selezione annullata');
        AnnotationLogger.debug('Selezione annullata');
    }
    
    /**
     * Ottiene il nome dell'entità dal suo ID
     * @param {string} entityId - L'ID del tipo di entità
     * @returns {string} - Il nome visualizzato dell'entità
     */
    function getEntityNameById(entityId) {
        for (const entityType of entityTypes) {
            if (entityType.dataset.type === entityId) {
                return entityType.querySelector('.entity-name').textContent;
            }
        }
        return entityId;
    }
    
    /**
     * Ottiene il colore dell'entità dal suo ID
     * @param {string} entityId - L'ID del tipo di entità
     * @returns {string} - Il colore dell'entità in formato esadecimale
     */
    function getEntityColorById(entityId) {
        for (const entityType of entityTypes) {
            if (entityType.dataset.type === entityId) {
                return entityType.style.backgroundColor;
            }
        }
        return "#CCCCCC";
    }
    
    /**
     * Ottiene l'offset reale nel testo
     * @param {Node} container - Il contenitore principale
     * @param {Node} targetNode - Il nodo target
     * @param {number} offset - L'offset nel nodo target
     * @returns {number} - L'offset assoluto nel testo completo
     */
    function getTextNodeOffset(container, targetNode, offset) {
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
    }
    
    /**
     * Crea una nuova annotazione
     * @param {number} start - Posizione di inizio dell'annotazione nel testo
     * @param {number} end - Posizione di fine dell'annotazione nel testo
     * @param {string} text - Il testo selezionato
     * @param {string} type - Il tipo di entità
     */
    function createAnnotation(start, end, text, type) {
        AnnotationLogger.debug(`Creazione annotazione: ${type}, "${text}" (${start}-${end})`);
        
        const annotation = {
            start: start,
            end: end,
            text: text,
            type: type
        };
        
        updateStatus('Creazione annotazione in corso...');
        
        // Salva l'annotazione
        saveAnnotation(annotation);
    }
    
    /**
     * Salva un'annotazione tramite API
     * @param {Object} annotation - L'annotazione da salvare
     */
    function saveAnnotation(annotation) {
        AnnotationLogger.startOperation('saveAnnotation');
        startPendingOperation();
        
        AnnotationLogger.debug('Invio richiesta di salvataggio annotazione', annotation);
        
        fetch('/api/save_annotation', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                doc_id: docId,
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
                
                // Aggiungi l'annotazione alla lista
                addAnnotationToList(data.annotation);
                
                // Pulisci la selezione
                window.getSelection().removeAllRanges();
                
                // Riesegui l'highlighting
                highlightExistingAnnotations();
                
                // Mostra notifica
                showNotification('Annotazione salvata con successo', 'success');
                updateStatus('Annotazione salvata con successo');
            } else {
                AnnotationLogger.error(`Errore nel salvataggio: ${data.message}`, data);
                showNotification(`Errore: ${data.message}`, 'danger');
                updateStatus(`Errore: ${data.message}`, true);
            }
        })
        .catch(error => {
            AnnotationLogger.error('Errore durante il salvataggio dell\'annotazione', error);
            showNotification('Errore durante il salvataggio', 'danger');
            updateStatus('Errore durante il salvataggio', true);
        })
        .finally(() => {
            endPendingOperation();
            AnnotationLogger.endOperation('saveAnnotation');
        });
    }
    
    /**
     * Aggiunge un'annotazione alla lista
     * @param {Object} annotation - L'annotazione da aggiungere
     */
    function addAnnotationToList(annotation) {
        AnnotationLogger.debug(`Aggiunta annotazione alla lista: ${annotation.id}`, annotation);
        
        // Ottieni il colore e il nome del tipo di entità
        const entityColor = getEntityColorById(annotation.type);
        const entityName = getEntityNameById(annotation.type);
        
        // Nascondi il messaggio "nessuna annotazione"
        if (noAnnotationsMsg) noAnnotationsMsg.classList.add('d-none');
        
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
        annotationsContainer.insertBefore(annotationItem, annotationsContainer.firstChild);
        
        // Evidenzia brevemente
        annotationItem.classList.add('highlight');
        setTimeout(() => {
            annotationItem.classList.remove('highlight');
        }, 2000);
        
        // Aggiorna contatori e statistiche
        updateAnnotationCount();
        updateEntityCounters();
        updateAnnotationProgress();
        updateVisibleCount();
    }
    
    /**
     * Elimina un'annotazione
     * @param {string} annotationId - L'ID dell'annotazione da eliminare
     */
    function deleteAnnotation(annotationId) {
        AnnotationLogger.debug(`Richiesta eliminazione annotazione: ${annotationId}`);
        
        // Usa un modale di conferma Bootstrap anziché il confirm standard
        const confirmModal = new bootstrap.Modal(document.getElementById('confirm-modal'));
        document.getElementById('confirm-title').textContent = 'Elimina annotazione';
        document.getElementById('confirm-message').textContent = 'Sei sicuro di voler eliminare questa annotazione?';
        
        const confirmBtn = document.getElementById('confirm-action-btn');
        confirmBtn.textContent = 'Elimina';
        confirmBtn.className = 'btn btn-danger';
        
        confirmBtn.onclick = function() {
            AnnotationLogger.startOperation('deleteAnnotation');
            startPendingOperation();
            
            // Disabilita il pulsante e mostra il caricamento
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Eliminazione...';
            
            updateStatus('Eliminazione in corso...');
            
            fetch('/api/delete_annotation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    doc_id: docId,
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
                confirmModal.hide();
                
                if (data.status === 'success') {
                    AnnotationLogger.debug(`Eliminazione completata per ID: ${annotationId}`);
                    
                    // Rimuovi l'annotazione dalla lista con animazione
                    const annotationItem = document.querySelector(`.annotation-item[data-id="${annotationId}"]`);
                    if (annotationItem) {
                        annotationItem.style.transition = 'all 0.3s ease';
                        annotationItem.style.opacity = '0';
                        annotationItem.style.height = '0';
                        annotationItem.style.overflow = 'hidden';
                        
                        setTimeout(() => {
                            annotationItem.remove();
                            
                            // Aggiorna la lista delle annotazioni esistenti
                            loadExistingAnnotations();
                            
                            // Riesegui l'highlighting con la nuova lista
                            highlightExistingAnnotations();
                            
                            // Mostra il messaggio "nessuna annotazione" se non ci sono più annotazioni
                            if (document.querySelectorAll('.annotation-item').length === 0) {
                                if (noAnnotationsMsg) noAnnotationsMsg.classList.remove('d-none');
                            }
                            
                            // Aggiorna contatori e statistiche
                            updateAnnotationCount();
                            updateEntityCounters();
                            updateAnnotationProgress();
                            updateVisibleCount();
                        }, 300);
                    } else {
                        AnnotationLogger.warn(`Elemento annotazione non trovato nel DOM: ${annotationId}`);
                        // Se l'elemento non è stato trovato, ricarica comunque le annotazioni
                        loadExistingAnnotations();
                        highlightExistingAnnotations();
                        
                        // Aggiorna contatori e statistiche
                        updateAnnotationCount();
                        updateEntityCounters();
                        updateAnnotationProgress();
                        updateVisibleCount();
                    }
                    
                    // Mostra notifica
                    showNotification('Annotazione eliminata', 'success');
                    updateStatus('Annotazione eliminata con successo');
                } else {
                    AnnotationLogger.error(`Errore nell'eliminazione: ${data.message}`, data);
                    showNotification(`Errore: ${data.message}`, 'danger');
                    updateStatus(`Errore: ${data.message}`, true);
                }
            })
            .catch(error => {
                confirmModal.hide();
                AnnotationLogger.error('Errore durante l\'eliminazione', error);
                showNotification('Errore durante l\'eliminazione', 'danger');
                updateStatus('Errore durante l\'eliminazione', true);
            })
            .finally(() => {
                endPendingOperation();
                AnnotationLogger.endOperation('deleteAnnotation');
            });
        };
        
        confirmModal.show();
    }
    
    /**
     * Ordina le annotazioni nella lista
     * @param {string} sortBy - Criterio di ordinamento ('position' o 'type')
     */
    function sortAnnotations(sortBy) {
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
    }
    
    // === RICONOSCIMENTO AUTOMATICO ===
    
    /**
     * Esegue il riconoscimento automatico delle entità
     */
    function performAutoAnnotation() {
        if (!autoAnnotateBtn) return;
        if (autoAnnotateBtn.disabled) return;
        
        const text = textContent.textContent;
        
        // Usa un modale di conferma Bootstrap anziché il confirm standard
        const confirmModal = new bootstrap.Modal(document.getElementById('confirm-modal'));
        document.getElementById('confirm-title').textContent = 'Riconoscimento automatico';
        document.getElementById('confirm-message').textContent = 
            'Vuoi eseguire il riconoscimento automatico delle entità nel testo? Questo processo potrebbe richiedere alcuni secondi.';
        
        const confirmBtn = document.getElementById('confirm-action-btn');
        confirmBtn.textContent = 'Procedi';
        confirmBtn.className = 'btn btn-primary';
        
        confirmBtn.onclick = function() {
            confirmModal.hide();
            
            AnnotationLogger.startOperation('autoAnnotation');
            startPendingOperation();
            
            // Mostra un indicatore di caricamento
            autoAnnotateBtn.disabled = true;
            autoAnnotateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Elaborazione...';
            updateStatus('Riconoscimento automatico in corso...');
            
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
                        showNotification('Nessuna entità riconosciuta', 'info');
                        updateStatus('Nessuna entità riconosciuta');
                        autoAnnotateBtn.disabled = false;
                        autoAnnotateBtn.innerHTML = '<i class="fas fa-magic me-2"></i>Riconoscimento automatico';
                        return;
                    }
                    
                    // Per ogni entità riconosciuta, crea un'annotazione
                    let savedCount = 0;
                    const totalToSave = entities.length;
                    
                    updateStatus(`Riconosciute ${entities.length} entità. Salvataggio in corso...`);
                    
                    // Funzione per salvare un'annotazione e gestire il conteggio
                    const saveAnnotationWithTracking = (annotation) => {
                        return fetch('/api/save_annotation', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                doc_id: docId,
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
                                autoAnnotateBtn.innerHTML = 
                                    `<span class="spinner-border spinner-border-sm me-2"></span>Salvate ${savedCount}/${totalToSave}...`;
                                updateStatus(`Salvate ${savedCount}/${totalToSave} annotazioni...`);
                                
                                // Aggiungi l'annotazione alla lista
                                addAnnotationToList(data.annotation);
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
                        autoAnnotateBtn.disabled = false;
                        autoAnnotateBtn.innerHTML = '<i class="fas fa-magic me-2"></i>Riconoscimento automatico';
                        
                        // Aggiorna l'evidenziazione delle annotazioni
                        highlightExistingAnnotations();
                        
                        // Mostra notifica
                        showNotification(`Salvate ${savedCount} annotazioni automatiche`, 'success');
                        updateStatus(`Completato: salvate ${savedCount} annotazioni automatiche`);
                    })
                    .catch(error => {
                        AnnotationLogger.error('Errore durante il salvataggio delle annotazioni automatiche', error);
                        autoAnnotateBtn.disabled = false;
                        autoAnnotateBtn.innerHTML = '<i class="fas fa-magic me-2"></i>Riconoscimento automatico';
                        showNotification('Errore durante il salvataggio delle annotazioni', 'danger');
                        updateStatus('Errore durante il salvataggio delle annotazioni', true);
                    });
                } else {
                    AnnotationLogger.error(`Errore nel riconoscimento automatico: ${data.message}`, data);
                    showNotification(`Errore: ${data.message}`, 'danger');
                    updateStatus(`Errore: ${data.message}`, true);
                    autoAnnotateBtn.disabled = false;
                    autoAnnotateBtn.innerHTML = '<i class="fas fa-magic me-2"></i>Riconoscimento automatico';
                }
            })
            .catch(error => {
                AnnotationLogger.error('Errore durante il riconoscimento automatico', error);
                showNotification('Errore durante il riconoscimento automatico', 'danger');
                updateStatus('Errore durante il riconoscimento automatico', true);
                autoAnnotateBtn.disabled = false;
                autoAnnotateBtn.innerHTML = '<i class="fas fa-magic me-2"></i>Riconoscimento automatico';
            })
            .finally(() => {
                endPendingOperation();
                AnnotationLogger.endOperation('autoAnnotation');
            });
        };
        
        confirmModal.show();
    }
    
    // === MODALITÀ CLEAN (SCHERMO INTERO) ===
    
    /**
     * Attiva/disattiva la modalità a schermo intero
     */
    function toggleCleanMode() {
        isCleanMode = !isCleanMode;
        document.body.classList.toggle('clean-mode', isCleanMode);
        
        AnnotationLogger.debug(`Modalità clean ${isCleanMode ? 'attivata' : 'disattivata'}`);
        
        const icon = cleanModeToggle.querySelector('i');
        if (icon) {
            if (isCleanMode) {
                icon.className = 'fas fa-compress';
                cleanModeToggle.title = "Esci dalla modalità a schermo intero";
                showNotification('Modalità a schermo intero attivata. Passa con il mouse sui bordi per vedere i pannelli.', 'info');
            } else {
                icon.className = 'fas fa-expand';
                cleanModeToggle.title = "Modalità a schermo intero";
                showNotification('Modalità a schermo intero disattivata', 'info');
            }
        }
        
        if (isCleanMode) {
            setTimeout(() => {
                if (textContent) textContent.focus();
            }, 300);
        }

        // Salva lo stato
        localStorage.setItem('ner-clean-mode', isCleanMode);
    }
    
    // === EVENTI DI SISTEMA ===
    
    /**
     * Configura i badge delle scorciatoie in base al sistema operativo
     */
    function setupShortcutBadges() {
        const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
        const modifierKey = isMac ? '⌘' : 'Ctrl';
        
        AnnotationLogger.debug(`Configurazione badge scorciatoie per piattaforma: ${navigator.platform}`);
        
        document.querySelectorAll('.shortcut-badge').forEach((badge, index) => {
            badge.textContent = `${modifierKey}${index + 1}`;
        });
        
        const keyboardShortcuts = document.querySelector('.keyboard-shortcuts');
        if (keyboardShortcuts && !isMac) {
            const items = keyboardShortcuts.querySelectorAll('li');
            items.forEach(item => {
                item.innerHTML = item.innerHTML.replace(/⌘/g, 'Ctrl');
            });
        }
    }
    
    /**
     * Registra gli eventi di debug per il monitoraggio dell'applicazione
     */
    function debugEventHandlers() {
        if (!AnnotationLogger.debugMode) return;
        
        AnnotationLogger.debug('Configurazione handler di debug');
        
        // Monitora le modifiche al DOM per debug
        const debugObserver = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList') {
                    AnnotationLogger.debug(`DOM modificato: ${mutation.target.id || mutation.target.className}`, {
                        added: mutation.addedNodes.length,
                        removed: mutation.removedNodes.length
                    });
                }
            });
        });
        
        // Osserva modifiche in aree critiche
        if (textContent) {
            debugObserver.observe(textContent, { childList: true, subtree: true });
        }
        
        if (annotationsContainer) {
            debugObserver.observe(annotationsContainer, { childList: true, subtree: false });
        }
        
        // Estendi le funzioni originali per il logging
        const originalShowNotification = showNotification;
        showNotification = function(message, type) {
            AnnotationLogger.debug(`Notifica: ${message} (${type})`);
            return originalShowNotification(message, type);
        };
        
        // Monitora gli errori JavaScript
        window.addEventListener('error', function(event) {
            AnnotationLogger.error('Errore JavaScript non gestito', {
                message: event.message,
                source: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                error: event.error
            });
        });
        
        // Monitora il tempo di inattività
        let lastActivityTime = Date.now();
        const trackActivity = () => { lastActivityTime = Date.now(); };
        
        document.addEventListener('mousemove', trackActivity);
        document.addEventListener('keydown', trackActivity);
        document.addEventListener('click', trackActivity);
        document.addEventListener('scroll', trackActivity);
        
        setInterval(() => {
            const idleTime = Math.floor((Date.now() - lastActivityTime) / 1000);
            if (idleTime > 300) { // 5 minuti
                AnnotationLogger.debug(`Utente inattivo da ${idleTime} secondi`);
            }
        }, 60000); // Controlla ogni minuto
    }
    
    /**
     * Configura handler di eventi delegati per elementi dinamici
     */
    function setupDelegatedEventHandlers() {
        AnnotationLogger.debug('Configurazione handler di eventi delegati');
        
        // Usa la delega degli eventi per gestire elementi creati dinamicamente
        if (annotationsContainer) {
            // Gestione unificata dei clic all'interno del container delle annotazioni
            annotationsContainer.addEventListener('click', function(e) {
                // Bottone di eliminazione
                if (e.target.closest('.delete-annotation')) {
                    const btn = e.target.closest('.delete-annotation');
                    const annotationId = btn.dataset.id;
                    deleteAnnotation(annotationId);
                    return;
                }
                
                // Bottone di salto all'annotazione
                if (e.target.closest('.jump-to-annotation')) {
                    const btn = e.target.closest('.jump-to-annotation');
                    const annotationId = btn.dataset.id;
                    jumpToAnnotation(annotationId);
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
                }
            });
        }
        
        // Delega per i pulsanti di ordinamento
        document.addEventListener('click', function(e) {
            if (e.target.closest('.sort-annotations')) {
                const sortBtn = e.target.closest('.sort-annotations');
                const sortBy = sortBtn.dataset.sort;
                sortAnnotations(sortBy);
                
                // Aggiorna lo stato dei pulsanti
                document.querySelectorAll('.sort-annotations').forEach(btn => {
                    btn.classList.remove('active');
                });
                sortBtn.classList.add('active');
            }
        });
    }
    
    // === INIZIALIZZAZIONE ===
    
    /**
     * Elimina tutte le annotazioni del documento o di un tipo specifico
     * @param {string} docId - L'ID del documento
     * @param {string} [entityType] - Opzionale: il tipo di entità da eliminare
     * @returns {Promise} - Promise che si risolve quando l'eliminazione è completata
     */
    function clearAnnotations(docId, entityType) {
        AnnotationLogger.startOperation('clearAnnotations');
        startPendingOperation();
        
        return new Promise((resolve, reject) => {
            const requestData = entityType 
                ? { doc_id: docId, entity_type: entityType } 
                : { doc_id: docId };
                
            AnnotationLogger.debug(`Richiesta eliminazione annotazioni`, requestData);
            
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
                if (data.status === 'success') {
                    AnnotationLogger.debug('Annotazioni eliminate con successo', data);
                    showNotification(data.message || 'Annotazioni eliminate con successo', 'success');
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                    resolve(true);
                } else {
                    AnnotationLogger.error(`Errore nell'eliminazione delle annotazioni: ${data.message}`, data);
                    showNotification('Errore: ' + data.message, 'danger');
                    reject(new Error(data.message));
                }
            })
            .catch(error => {
                AnnotationLogger.error('Errore nella richiesta di eliminazione annotazioni', error);
                showNotification('Si è verificato un errore durante l\'eliminazione', 'danger');
                reject(error);
            })
            .finally(() => {
                endPendingOperation();
                AnnotationLogger.endOperation('clearAnnotations');
            });
        });
    }
    
    // === GESTIONE EVENTI ===
    
    // Collega gli eventi per la gestione dello zoom
    if (zoomInBtn) {
        zoomInBtn.addEventListener('click', function() {
            currentTextSize = Math.min(currentTextSize + 0.1, 2);
            textContent.style.fontSize = `${currentTextSize}rem`;
            AnnotationLogger.debug(`Zoom aumentato a ${currentTextSize}rem`);
        });
    }
    
    if (zoomOutBtn) {
        zoomOutBtn.addEventListener('click', function() {
            currentTextSize = Math.max(currentTextSize - 0.1, 0.8);
            textContent.style.fontSize = `${currentTextSize}rem`;
            AnnotationLogger.debug(`Zoom diminuito a ${currentTextSize}rem`);
        });
    }
    
    if (resetZoomBtn) {
        resetZoomBtn.addEventListener('click', function() {
            currentTextSize = originalTextSize;
            textContent.style.fontSize = `${currentTextSize}rem`;
            AnnotationLogger.debug(`Zoom reimpostato a ${currentTextSize}rem`);
        });
    }
    
    // Gestione della ricerca nelle annotazioni
    if (searchAnnotations) {
        searchAnnotations.addEventListener('input', function() {
            const query = this.value.toLowerCase();
            AnnotationLogger.debug(`Ricerca annotazioni: "${query}"`);
            
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
            updateVisibleCount();
        });
    }
    
    // Scorciatoie da tastiera globali
    document.addEventListener('keydown', function(e) {
        // Escape per annullare la selezione
        if (e.key === 'Escape') {
            clearSelection();
        }
        
        // Alt+A per annotazione automatica
        if (e.key === 'a' && e.altKey) {
            e.preventDefault();
            if (autoAnnotateBtn && !autoAnnotateBtn.disabled) {
                autoAnnotateBtn.click();
            }
        }
        
        // Cmd/Ctrl + numero per selezionare un tipo di entità
        if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '9') {
            e.preventDefault();
            
            const index = parseInt(e.key) - 1;
            const entityTypeElements = document.querySelectorAll('.entity-type');
            
            if (index < entityTypeElements.length) {
                entityTypeElements[index].click();
                entityTypeElements[index].classList.add('shortcut-highlight');
                setTimeout(() => {
                    entityTypeElements[index].classList.remove('shortcut-highlight');
                }, 500);
                
                const entityName = entityTypeElements[index].querySelector('.entity-name').textContent;
                updateStatus(`Tipo selezionato: ${entityName} tramite scorciatoia da tastiera`);
            }
        }
        
        // Cmd/Ctrl + F per modalità clean
        if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
            e.preventDefault();
            if (cleanModeToggle) toggleCleanMode();
        }
    });
    
    // Selezione del tipo di entità
    entityTypes.forEach(entityType => {
        entityType.addEventListener('click', function() {
            // Rimuovi la selezione precedente
            entityTypes.forEach(et => et.classList.remove('selected'));
            
            // Seleziona il nuovo tipo
            this.classList.add('selected');
            selectedType = this.dataset.type;
            
            // Mostra il messaggio di stato
            const entityName = this.querySelector('.entity-name').textContent;
            updateStatus(`Tipo selezionato: ${entityName}. Seleziona il testo da annotare.`);
            
            AnnotationLogger.debug(`Tipo di entità selezionato: ${selectedType} (${entityName})`);
        });
    });
    
    // Gestione del pulsante per annullare la selezione
    if (clearSelectionBtn) {
        clearSelectionBtn.addEventListener('click', clearSelection);
    }
    
    // Gestione della selezione del testo
    if (textContent) {
        textContent.addEventListener('mouseup', function(e) {
            // Se il contenuto è in modalità di modifica, non fare nulla
            if (textContent.contentEditable === 'true') return;
            
            const selection = window.getSelection();
            
            // Verifica se c'è del testo selezionato
            if (selection.toString().trim() === '') {
                return;
            }
            
            if (!selectedType) {
                showNotification('Seleziona prima un tipo di entità', 'danger');
                updateStatus('Seleziona un tipo di entità prima di annotare', true);
                return;
            }
            
            try {
                const range = selection.getRangeAt(0);
                
                // Calcola l'offset nel testo completo
                const fullText = textContent.textContent;
                
                // Ottieni i nodi di inizio e fine della selezione
                const startNode = range.startContainer;
                const endNode = range.endContainer;
                
                // Calcola gli offset nei nodi
                const startOffset = getTextNodeOffset(textContent, startNode, range.startOffset);
                const endOffset = getTextNodeOffset(textContent, endNode, range.endOffset);
                
                if (startOffset < 0 || endOffset < 0) {
                    AnnotationLogger.error('Impossibile determinare la posizione nel testo', {
                        startNode, endNode, rangeStart: range.startOffset, rangeEnd: range.endOffset
                    });
                    updateStatus('Impossibile determinare la posizione nel testo', true);
                    return;
                }
                
                // Verifica che la selezione sia valida
                if (startOffset >= endOffset) {
                    updateStatus('Selezione non valida', true);
                    return;
                }
                
                // Ottieni il testo selezionato
                const selectedText = fullText.substring(startOffset, endOffset);
                
                AnnotationLogger.debug(`Nuova selezione: "${selectedText}" (${startOffset}-${endOffset})`);
                
                // Verifica se l'annotazione si sovrappone con altre esistenti
                const existingItems = document.querySelectorAll('.annotation-item');
                let hasOverlap = false;
                
                existingItems.forEach(item => {
                    const itemStart = parseInt(item.dataset.start);
                    const itemEnd = parseInt(item.dataset.end);
                    
                    // Controlla sovrapposizione
                    if ((startOffset <= itemEnd && endOffset >= itemStart)) {
                        hasOverlap = true;
                        AnnotationLogger.debug(`Sovrapposizione rilevata con annotazione esistente:`, {
                            newSelection: { start: startOffset, end: endOffset, text: selectedText },
                            existing: { id: item.dataset.id, start: itemStart, end: itemEnd }
                        });
                    }
                });
                
                if (hasOverlap) {
                    // Usa un modale di conferma Bootstrap anziché il confirm standard
                    const confirmModal = new bootstrap.Modal(document.getElementById('confirm-modal'));
                    document.getElementById('confirm-title').textContent = 'Sovrapposizione rilevata';
                    document.getElementById('confirm-message').textContent = 
                        'La selezione si sovrappone a un\'annotazione esistente. Continuare comunque?';
                    
                    const confirmBtn = document.getElementById('confirm-action-btn');
                    confirmBtn.textContent = 'Continua';
                    confirmBtn.className = 'btn btn-warning';
                    
                    confirmBtn.onclick = function() {
                        confirmModal.hide();
                        createAnnotation(startOffset, endOffset, selectedText, selectedType);
                    };
                    
                    confirmModal.show();
                    return;
                }
                
                // Crea l'annotazione
                createAnnotation(startOffset, endOffset, selectedText, selectedType);
                
            } catch (e) {
                AnnotationLogger.error("Errore nella selezione del testo:", e);
                updateStatus('Errore nella selezione del testo', true);
            }
        });
    }
    
    // Gestione del pulsante per l'annotazione automatica
    if (autoAnnotateBtn) {
        autoAnnotateBtn.addEventListener('click', performAutoAnnotation);
    }
    
    // Gestione della modalità clean (a schermo intero)
    if (cleanModeToggle) {
        cleanModeToggle.addEventListener('click', toggleCleanMode);
        
        // Ripristina lo stato della modalità clean
        const savedCleanMode = localStorage.getItem('ner-clean-mode') === 'true';
        if (savedCleanMode) {
            toggleCleanMode();
        }
    }
    
    // === FUNZIONI ESPOSTE GLOBALMENTE ===
    window.showNotification = showNotification;
    window.updateStatus = updateStatus;
    window.updateAnnotationCount = updateAnnotationCount;
    window.addAnnotationToList = addAnnotationToList;
    window.highlightExistingAnnotations = highlightExistingAnnotations;
    window.jumpToAnnotation = jumpToAnnotation;
    window.deleteAnnotation = deleteAnnotation;
    window.clearAnnotations = clearAnnotations;
    
    // === INIZIALIZZAZIONE DELL'APPLICAZIONE ===
    function initializeApplication() {
        AnnotationLogger.debug('Inizializzazione dell\'applicazione di annotazione');
        
        // Carica le annotazioni esistenti
        loadExistingAnnotations();
        
        // Evidenzia le annotazioni nel testo
        highlightExistingAnnotations();
        
        // Configura i badge delle scorciatoie
        setupShortcutBadges();
        
        // Configura gli handler di debug
        debugEventHandlers();
        
        // Configura gli handler di eventi delegati
        setupDelegatedEventHandlers();
        
        // Aggiungi un osservatore per monitorare le modifiche al contenuto del testo
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.type === 'childList' && mutation.target.id === 'text-content') {
                    optimizeTextDisplay();
                }
            });
        });
        
        if (textContent) {
            observer.observe(textContent, { childList: true, subtree: true });
        }
        
        // Ottimizza la visualizzazione all'avvio
        optimizeTextDisplay();
        
        AnnotationLogger.endOperation('inizializzazione');
        AnnotationLogger.info('Applicazione di annotazione inizializzata con successo');
    }
    
    // Avvia l'inizializzazione
    initializeApplication();
});