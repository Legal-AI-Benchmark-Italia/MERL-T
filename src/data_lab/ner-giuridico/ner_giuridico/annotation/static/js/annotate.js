/**
 * annotate.js - Script migliorato per la funzionalità di annotazione
 * Versione aggiornata con supporto per Bootstrap 5 e un'esperienza utente migliore
 */

document.addEventListener('DOMContentLoaded', function() {
    // === Elementi DOM principali ===
    const textContent = document.getElementById('text-content');
    const docId = textContent.dataset.docId;
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

    // === Carica le annotazioni esistenti ===
    function loadExistingAnnotations() {
        existingAnnotations = [];
        document.querySelectorAll('.annotation-item').forEach(item => {
            const id = item.dataset.id;
            const text = item.querySelector('.annotation-text').textContent;
            const type = item.dataset.type;
            const start = parseInt(item.dataset.start);
            const end = parseInt(item.dataset.end);
            
            // Trova il colore dall'elemento badge
            const typeElement = item.querySelector('.annotation-type');
            const color = typeElement ? typeElement.style.backgroundColor : "";
            
            existingAnnotations.push({ id, text, type, start, end, color });
        });
        
        // Aggiorna i contatori e statistiche
        updateAnnotationCount();
        updateEntityCounters();
        updateAnnotationProgress();
        updateVisibleCount();
        
        // Chiama le nuove utility di debug e gestione eventi
        debugEventHandlers();
        setupDelegatedEventHandlers();
    }
    
    function optimizeTextDisplay() {
        // Verifica e corregge eventuali problemi di visualizzazione dopo il rendering
        setTimeout(() => {
            const highlights = document.querySelectorAll('.entity-highlight');
            
            // Miglioramento per garantire che le annotazioni non causino problemi di layout
            highlights.forEach(highlight => {
                // Verifica se l'elemento ha un layout corretto
                const rect = highlight.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) {
                    console.warn('Rilevato elemento di annotazione con dimensione zero:', highlight);
                    // Tentativo di correzione forzando un reflow
                    highlight.style.display = 'inline-block';
                    setTimeout(() => highlight.style.display = 'inline', 0);
                }
            });
            
            // Verifica se ci sono sovrapposizioni problematiche
            checkForOverlappingHighlights();
        }, 500);
    }
    
    // === Funzione per individuare e correggere sovrapposizioni problematiche ===
    function checkForOverlappingHighlights() {
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
        
        // Controllo e gestisco le sovrapposizioni per ogni linea
        lineMap.forEach(line => {
            if (line.length < 2) return; // Nessuna sovrapposizione possibile
            
            // Ordino per posizione da sinistra
            line.sort((a, b) => a.left - b.left);
            
            // Controllo sovrapposizioni orizzontali
            for (let i = 0; i < line.length - 1; i++) {
                const current = line[i];
                const next = line[i + 1];
                
                if (current.right > next.left + 2) { // 2px di tolleranza
                    console.log('Sovrapposizione orizzontale rilevata:', current.element, next.element);
                    
                    // Aggiungi classe per evidenziare la sovrapposizione
                    current.element.classList.add('overlap');
                    next.element.classList.add('overlap');
                }
            }
        });
    }
        
    // === Sistema di notifiche migliorato ===
    function showNotification(message, type = 'primary') {
        // Usa i toast di Bootstrap
        const toastEl = document.getElementById('notification-toast');
        if (!toastEl) return;
        
        const toastBody = toastEl.querySelector('.toast-body');
        toastBody.textContent = message;
        
        // Imposta il tipo di toast
        toastEl.className = toastEl.className.replace(/bg-\w+/, '');
        toastEl.classList.add(`bg-${type}`);
        
        // Mostra il toast
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
    }
    
    // === Funzione per aggiornare lo stato dell'annotazione ===
    function updateStatus(message, isError = false) {
        if (!annotationStatus) return;
        
        if (!message) {
            annotationStatus.classList.add('d-none');
            return;
        }
        
        annotationStatus.textContent = message;
        annotationStatus.classList.remove('d-none', 'alert-info', 'alert-danger');
        annotationStatus.classList.add(isError ? 'alert-danger' : 'alert-info');
        
        // Rimuovi il messaggio dopo un po'
        setTimeout(() => {
            annotationStatus.classList.add('d-none');
        }, 5000);
    }
    
    // === Funzioni per aggiornare statistiche e contatori ===
    function updateAnnotationCount() {
        const count = document.querySelectorAll('.annotation-item').length;
        if (annotationCount) annotationCount.textContent = `(${count})`;
    }
    
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
    }
    
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
    }
    
    function updateVisibleCount() {
        if (!visibleCount) return;
        
        const total = document.querySelectorAll('.annotation-item').length;
        const visible = document.querySelectorAll('.annotation-item:not(.d-none)').length;
        
        visibleCount.textContent = visible === total ? total : `${visible}/${total}`;
    }
    
    // === Gestione dello zoom del testo ===
    if (zoomInBtn) {
        zoomInBtn.addEventListener('click', function() {
            currentTextSize = Math.min(currentTextSize + 0.1, 2);
            textContent.style.fontSize = `${currentTextSize}rem`;
        });
    }
    
    if (zoomOutBtn) {
        zoomOutBtn.addEventListener('click', function() {
            currentTextSize = Math.max(currentTextSize - 0.1, 0.8);
            textContent.style.fontSize = `${currentTextSize}rem`;
        });
    }
    
    if (resetZoomBtn) {
        resetZoomBtn.addEventListener('click', function() {
            currentTextSize = originalTextSize;
            textContent.style.fontSize = `${currentTextSize}rem`;
        });
    }
    
    // === Gestione della ricerca nelle annotazioni ===
    if (searchAnnotations) {
        searchAnnotations.addEventListener('input', function() {
            const query = this.value.toLowerCase();
            
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
    
    // === Gestione scorciatoie da tastiera ===
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
    });
    
    // === Gestione della selezione del tipo di entità ===
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
        });
    });
    
    // === Funzione per pulire la selezione ===
    function clearSelection() {
        entityTypes.forEach(et => et.classList.remove('selected'));
        selectedType = null;
        window.getSelection().removeAllRanges();
        updateStatus('Selezione annullata');
    }
    
    // === Gestione del pulsante per annullare la selezione ===
    if (clearSelectionBtn) {
        clearSelectionBtn.addEventListener('click', clearSelection);
    }
    
    // === Funzione per determinare l'offset reale nel testo ===
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
    
    // === Ordina le annotazioni per posizione di inizio ===
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
    
    // === Verifica se due annotazioni si sovrappongono ===
    function isOverlapping(a, b) {
        return (a.start <= b.end && a.end >= b.start);
    }
    
    // === Funzione per evidenziare le annotazioni esistenti nel testo ===
    function highlightExistingAnnotations() {
        const text = textContent.textContent;
        
        // Aggiorna l'array delle annotazioni con i dati correnti dal DOM
        loadExistingAnnotations();
        
        // Se non ci sono annotazioni, mostra solo il testo originale
        if (existingAnnotations.length === 0) {
            textContent.innerHTML = text;
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
        
        // Aggiungi eventi alle entità evidenziate
        document.querySelectorAll('.entity-highlight').forEach(highlight => {
            highlight.addEventListener('click', function(e) {
                e.preventDefault();
                const annotationId = this.dataset.id;
                const annotationItem = document.querySelector(`.annotation-item[data-id="${annotationId}"]`);
                
                if (annotationItem) {
                    // Scorri fino all'annotazione nella lista
                    annotationItem.scrollIntoView({behavior: 'smooth', block: 'center'});
                    
                    // Evidenzia brevemente l'annotazione nella lista
                    annotationItem.classList.add('highlight');
                    setTimeout(() => {
                        annotationItem.classList.remove('highlight');
                    }, 2000);
                }
            });
        });
    }
    
    // === Funzione per ottenere il nome dell'entità dal suo ID ===
    function getEntityNameById(entityId) {
        for (const entityType of entityTypes) {
            if (entityType.dataset.type === entityId) {
                return entityType.querySelector('.entity-name').textContent;
            }
        }
        return entityId;
    }
    
    // === Funzione per ottenere il colore dell'entità dal suo ID ===
    function getEntityColorById(entityId) {
        for (const entityType of entityTypes) {
            if (entityType.dataset.type === entityId) {
                return entityType.style.backgroundColor;
            }
        }
        return "#CCCCCC";
    }
    
    // === Gestione della selezione del testo ===
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
            
            // Verifica se l'annotazione si sovrappone con altre esistenti
            const existingItems = document.querySelectorAll('.annotation-item');
            let hasOverlap = false;
            
            existingItems.forEach(item => {
                const itemStart = parseInt(item.dataset.start);
                const itemEnd = parseInt(item.dataset.end);
                
                // Controlla sovrapposizione
                if ((startOffset <= itemEnd && endOffset >= itemStart)) {
                    hasOverlap = true;
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
            console.error("Errore nella selezione del testo:", e);
            updateStatus('Errore nella selezione del testo', true);
        }
    });
    
    // === Funzione per creare un'annotazione ===
    function createAnnotation(start, end, text, type) {
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
    
    // === Funzione per salvare un'annotazione ===
    function saveAnnotation(annotation) {
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
                showNotification(`Errore: ${data.message}`, 'danger');
                updateStatus(`Errore: ${data.message}`, true);
            }
        })
        .catch(error => {
            console.error('Errore:', error);
            showNotification('Errore durante il salvataggio', 'danger');
            updateStatus('Errore durante il salvataggio', true);
        });
    }
    
    // === Funzione per aggiungere un'annotazione alla lista ===
    function addAnnotationToList(annotation) {
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
        
        // Aggiungi eventi per le azioni
        const deleteBtn = annotationItem.querySelector('.delete-annotation');
        deleteBtn.addEventListener('click', function() {
            deleteAnnotation(annotation.id);
        });
        
        const jumpBtn = annotationItem.querySelector('.jump-to-annotation');
        jumpBtn.addEventListener('click', function() {
            jumpToAnnotation(annotation.id);
        });
        
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
    
    // === Funzione per saltare a una specifica annotazione nel testo ===
    function jumpToAnnotation(annotationId) {
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
        }
    }
    
    // === Funzione per eliminare un'annotazione ===
    function deleteAnnotation(annotationId) {
        // Usa un modale di conferma Bootstrap anziché il confirm standard
        const confirmModal = new bootstrap.Modal(document.getElementById('confirm-modal'));
        document.getElementById('confirm-title').textContent = 'Elimina annotazione';
        document.getElementById('confirm-message').textContent = 'Sei sicuro di voler eliminare questa annotazione?';
        
        const confirmBtn = document.getElementById('confirm-action-btn');
        confirmBtn.textContent = 'Elimina';
        confirmBtn.className = 'btn btn-danger';
        
        confirmBtn.onclick = function() {
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
                    // DEBUG: Registra lo stato prima dell'eliminazione
                    console.log('Eliminazione avviata per ID:', annotationId);
                    console.log('Elementi trovati:', document.querySelectorAll(`.entity-highlight[data-id="${annotationId}"]`).length);
                    console.log('Elemento annotazione:', document.querySelector(`.annotation-item[data-id="${annotationId}"]`));
                    
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
                        console.warn('Elemento annotazione non trovato nel DOM:', annotationId);
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
                    showNotification(`Errore: ${data.message}`, 'danger');
                    updateStatus(`Errore: ${data.message}`, true);
                }
            })
            .catch(error => {
                confirmModal.hide();
                console.error('Errore:', error);
                showNotification('Errore durante l\'eliminazione', 'danger');
                updateStatus('Errore durante l\'eliminazione', true);
            });
        };
        
        confirmModal.show();
    }
    
    
    // === Gestione degli eventi di eliminazione per le annotazioni esistenti ===
    document.querySelectorAll('.delete-annotation').forEach(btn => {
        btn.addEventListener('click', function() {
            const annotationId = this.dataset.id;
            deleteAnnotation(annotationId);
        });
    });
    
    // === Gestione degli eventi di salto all'annotazione ===
    document.querySelectorAll('.jump-to-annotation').forEach(btn => {
        btn.addEventListener('click', function() {
            const annotationId = this.dataset.id;
            jumpToAnnotation(annotationId);
        });
    });
    
    // === Gestione del pulsante per l'annotazione automatica ===
    if (autoAnnotateBtn) {
        autoAnnotateBtn.addEventListener('click', function() {
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
                        console.log(`Riconosciute ${entities.length} entità automaticamente`);
                        
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
                            console.log(`Salvate ${savedCount} annotazioni automatiche`);
                            autoAnnotateBtn.disabled = false;
                            autoAnnotateBtn.innerHTML = '<i class="fas fa-magic me-2"></i>Riconoscimento automatico';
                            
                            // Aggiorna l'evidenziazione delle annotazioni
                            highlightExistingAnnotations();
                            
                            // Mostra notifica
                            showNotification(`Salvate ${savedCount} annotazioni automatiche`, 'success');
                            updateStatus(`Completato: salvate ${savedCount} annotazioni automatiche`);
                        })
                        .catch(error => {
                            console.error('Errore durante il salvataggio:', error);
                            autoAnnotateBtn.disabled = false;
                            autoAnnotateBtn.innerHTML = '<i class="fas fa-magic me-2"></i>Riconoscimento automatico';
                            showNotification('Errore durante il salvataggio delle annotazioni', 'danger');
                            updateStatus('Errore durante il salvataggio delle annotazioni', true);
                        });
                    } else {
                        showNotification(`Errore: ${data.message}`, 'danger');
                        updateStatus(`Errore: ${data.message}`, true);
                        autoAnnotateBtn.disabled = false;
                        autoAnnotateBtn.innerHTML = '<i class="fas fa-magic me-2"></i>Riconoscimento automatico';
                    }
                })
                .catch(error => {
                    console.error('Errore:', error);
                    showNotification('Errore durante il riconoscimento automatico', 'danger');
                    updateStatus('Errore durante il riconoscimento automatico', true);
                    autoAnnotateBtn.disabled = false;
                    autoAnnotateBtn.innerHTML = '<i class="fas fa-magic me-2"></i>Riconoscimento automatico';
                });
            };
            
            confirmModal.show();
        });
    }
    
    // === Funzione per ordinare le annotazioni ===
    function sortAnnotations(sortBy) {
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
    }
    
    // === Collega gli eventi di ordinamento ===
    document.querySelectorAll('.sort-annotations').forEach(button => {
        button.addEventListener('click', function() {
            sortAnnotations(this.dataset.sort);
            
            // Aggiorna lo stato dei pulsanti
            document.querySelectorAll('.sort-annotations').forEach(btn => {
                btn.classList.remove('active');
            });
            this.classList.add('active');
        });
    });
    
    // === Funzione per eliminare tutte le annotazioni ===
    window.clearAnnotations = function(docId, entityType) {
        return new Promise((resolve, reject) => {
            fetch('/api/clear_annotations', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(entityType ? {
                    doc_id: docId,
                    entity_type: entityType
                } : {
                    doc_id: docId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showNotification(data.message || 'Annotazioni eliminate con successo', 'success');
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                    resolve(true);
                } else {
                    showNotification('Errore: ' + data.message, 'danger');
                    reject(new Error(data.message));
                }
            })
            .catch(error => {
                console.error('Errore:', error);
                showNotification('Si è verificato un errore durante l\'eliminazione', 'danger');
                reject(error);
            });
        });
    };
    
    // === Inizializzazione: evidenzia le annotazioni esistenti ===
    highlightExistingAnnotations();
    
    // === Esponi funzioni globali ===
    window.showNotification = showNotification;
    window.updateStatus = updateStatus;
    window.updateAnnotationCount = updateAnnotationCount;
    window.addAnnotationToList = addAnnotationToList;
    window.highlightExistingAnnotations = highlightExistingAnnotations;
    window.jumpToAnnotation = jumpToAnnotation;
    window.deleteAnnotation = deleteAnnotation;

    // === Gestione della modalità clean (a schermo intero) ===
    function toggleCleanMode() {
        isCleanMode = !isCleanMode;
        document.body.classList.toggle('clean-mode', isCleanMode);
        
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

    // Ripristina lo stato della modalità clean
    const savedCleanMode = localStorage.getItem('ner-clean-mode') === 'true';
    if (savedCleanMode && cleanModeToggle) {
        toggleCleanMode();
    }

    if (cleanModeToggle) {
        cleanModeToggle.addEventListener('click', toggleCleanMode);
    }

    // === Preparazione dei badge delle scorciatoie ===
    function setupShortcutBadges() {
        const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
        const modifierKey = isMac ? '⌘' : 'Ctrl';
        
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

    // Configura i badge delle scorciatoie
    setupShortcutBadges();

    // === Gestione migliorata delle scorciatoie da tastiera ===
    document.addEventListener('keydown', function(e) {
        // Cmd/Ctrl + numero per selezionare un tipo di entità
        if ((e.metaKey || e.ctrlKey) && e.key >= '1' && e.key <= '9') {
            e.preventDefault();
            
            const index = parseInt(e.key) - 1;
            const entityTypes = document.querySelectorAll('.entity-type');
            
            if (index < entityTypes.length) {
                entityTypes[index].click();
                entityTypes[index].classList.add('shortcut-highlight');
                setTimeout(() => {
                    entityTypes[index].classList.remove('shortcut-highlight');
                }, 500);
                
                const entityName = entityTypes[index].querySelector('.entity-name').textContent;
                updateStatus(`Tipo selezionato: ${entityName} tramite scorciatoia da tastiera`);
            }
        }
        
        // Cmd/Ctrl + F per modalità clean
        if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
            e.preventDefault();
            if (cleanModeToggle) toggleCleanMode();
        }
        
        // Escape gestisce anche l'uscita dalla modalità clean
        if (e.key === 'Escape') {
            if (isCleanMode) {
                toggleCleanMode();
                e.preventDefault();
                return;
            }
            // ...existing Escape handling...
        }
    });

    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.target.id === 'text-content') {
                optimizeTextDisplay();
            }
        });
    });
    
    // Osserva i cambiamenti nel contenuto del testo
    if (textContent) {
        observer.observe(textContent, { childList: true, subtree: true });
    }
    
    // Ottimizza il display all'avvio
    optimizeTextDisplay();
    
});

// === Nuove funzioni aggiunte ===
debugEventHandlers();
setupDelegatedEventHandlers();