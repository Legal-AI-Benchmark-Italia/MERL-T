document.addEventListener('DOMContentLoaded', function() {
    // Elementi DOM principali
    const textContent = document.getElementById('text-content');
    const docId = textContent.dataset.docId;
    const entityTypes = document.querySelectorAll('.entity-type');
    const clearSelectionBtn = document.getElementById('clear-selection');
    const autoAnnotateBtn = document.getElementById('auto-annotate');
    const annotationsContainer = document.getElementById('annotations-container');
    const searchAnnotations = document.getElementById('search-annotations');
    const annotationStatus = document.getElementById('annotation-status');
    const annotationCount = document.getElementById('annotation-count');
    const notification = document.getElementById('notification');
    
    // Controlli per lo zoom del testo
    const zoomInBtn = document.getElementById('zoom-in');
    const zoomOutBtn = document.getElementById('zoom-out');
    const resetZoomBtn = document.getElementById('reset-zoom');
    
    // Stato dell'applicazione
    let selectedType = null;
    let originalTextSize = 1.05; // rem
    let currentTextSize = originalTextSize;
    
    // Debug
    console.log(`Tipi di entità disponibili: ${entityTypes.length}`);
    entityTypes.forEach(et => {
        console.log(`Entità: ${et.textContent.trim()}, tipo: ${et.dataset.type}, colore: ${et.style.backgroundColor}`);
    });
    
    // Carica le annotazioni esistenti
    const existingAnnotations = [];
    document.querySelectorAll('.annotation-item').forEach(item => {
        const id = item.dataset.id;
        const text = item.querySelector('.annotation-text').textContent;
        const typeElement = item.querySelector('.annotation-type');
        const type = item.dataset.type;
        const start = parseInt(item.dataset.start);
        const end = parseInt(item.dataset.end);
        const color = typeElement ? typeElement.style.backgroundColor : "";
        
        existingAnnotations.push({ id, text, type, start, end, color });
    });
    
    // Aggiorna il conteggio delle annotazioni
    updateAnnotationCount();
    
    // Funzione per mostrare notifiche
    function showNotification(message, type = 'info') {
        notification.textContent = message;
        notification.className = `notification ${type} show`;
        
        setTimeout(() => {
            notification.className = 'notification';
        }, 3000);
    }
    
    // Funzione per aggiornare lo stato dell'annotazione
    function updateStatus(message, isError = false) {
        annotationStatus.textContent = message;
        annotationStatus.style.backgroundColor = isError ? '#ffcccc' : '#e6f7ff';
        annotationStatus.style.color = isError ? '#dc3545' : '#0066cc';
        
        // Rimuovi il messaggio dopo un po'
        if (message) {
            setTimeout(() => {
                annotationStatus.textContent = '';
                annotationStatus.style.backgroundColor = '';
                annotationStatus.style.color = '';
            }, 5000);
        }
    }
    
    // Funzione per aggiornare il conteggio delle annotazioni
    function updateAnnotationCount() {
        const count = document.querySelectorAll('.annotation-item').length;
        annotationCount.textContent = `(${count})`;
    }
    
    // Gestione dello zoom del testo
    zoomInBtn.addEventListener('click', function() {
        currentTextSize = Math.min(currentTextSize + 0.1, 2);
        textContent.style.fontSize = `${currentTextSize}rem`;
    });
    
    zoomOutBtn.addEventListener('click', function() {
        currentTextSize = Math.max(currentTextSize - 0.1, 0.8);
        textContent.style.fontSize = `${currentTextSize}rem`;
    });
    
    resetZoomBtn.addEventListener('click', function() {
        currentTextSize = originalTextSize;
        textContent.style.fontSize = `${currentTextSize}rem`;
    });
    
    // Gestione della ricerca nelle annotazioni
    searchAnnotations.addEventListener('input', function() {
        const query = this.value.toLowerCase();
        
        document.querySelectorAll('.annotation-item').forEach(item => {
            const text = item.querySelector('.annotation-text').textContent.toLowerCase();
            const type = item.querySelector('.annotation-type').textContent.toLowerCase();
            
            if (text.includes(query) || type.includes(query)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    });
    
    // Gestione scorciatoie da tastiera
    document.addEventListener('keydown', function(e) {
        // Escape per annullare la selezione
        if (e.key === 'Escape') {
            clearSelection();
        }
        
        // Alt+A per annotazione automatica
        if (e.key === 'a' && e.altKey) {
            e.preventDefault();
            if (!autoAnnotateBtn.disabled) {
                autoAnnotateBtn.click();
            }
        }
    });
    
    // Gestione della selezione del tipo di entità
    entityTypes.forEach(entityType => {
        entityType.addEventListener('click', function() {
            // Rimuovi la selezione precedente
            entityTypes.forEach(et => et.classList.remove('selected'));
            
            // Seleziona il nuovo tipo
            this.classList.add('selected');
            selectedType = this.dataset.type;
            updateStatus(`Tipo selezionato: ${this.textContent.trim()}`);
        });
    });
    
    // Funzione per pulire la selezione
    function clearSelection() {
        entityTypes.forEach(et => et.classList.remove('selected'));
        selectedType = null;
        window.getSelection().removeAllRanges();
        updateStatus('Selezione annullata');
    }
    
    // Gestione del pulsante per annullare la selezione
    clearSelectionBtn.addEventListener('click', clearSelection);
    
    // Funzione per determinare l'offset reale nel testo
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
    
    // Ordina le annotazioni per posizione di inizio
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
    
    // Verifica se due annotazioni si sovrappongono
    function isOverlapping(a, b) {
        return (a.start <= b.end && a.end >= b.start);
    }
    
    // Funzione per evidenziare le annotazioni esistenti nel testo
    function highlightExistingAnnotations() {
        const text = textContent.textContent;
        let annotations = existingAnnotations.slice();
        
        // Aggiorna l'array delle annotazioni con i dati correnti dal DOM
        annotations = [];
        document.querySelectorAll('.annotation-item').forEach(item => {
            const id = item.dataset.id;
            const start = parseInt(item.dataset.start);
            const end = parseInt(item.dataset.end);
            const type = item.dataset.type;
            const typeElement = item.querySelector('.annotation-type');
            const color = typeElement ? typeElement.style.backgroundColor : "";
            const text = item.querySelector('.annotation-text').textContent;
            
            if (!isNaN(start) && !isNaN(end)) {
                annotations.push({ id, start, end, type, color, text });
            }
        });
        
        // Se non ci sono annotazioni, mostra solo il testo originale
        if (annotations.length === 0) {
            textContent.innerHTML = text;
            return;
        }
        
        // Ordina le annotazioni per posizione di inizio e poi per lunghezza (più lunghe prima)
        annotations = sortAnnotationsByPosition(annotations);
        
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
                
                htmlContent += `<span class="entity-highlight ${isOverlap ? 'overlap' : ''}" 
                          style="background-color: ${ann.color};" 
                          data-id="${ann.id}" 
                          data-type="${ann.type}">
                          <span class="tooltip">${entityName}: ${ann.text}</span>`;
                          
                currentAnnotations.push(ann);
            });
            
            // Aggiungi il carattere
            htmlContent += char;
        }
        
        // Chiudi tutti i tag rimanenti alla fine
        currentAnnotations.sort((a, b) => b.start - a.start).forEach(() => {
            htmlContent += '</span>';
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
    
    // Funzione per ottenere il nome dell'entità dal suo ID
    function getEntityNameById(entityId) {
        for (const entityType of entityTypes) {
            if (entityType.dataset.type === entityId) {
                return entityType.textContent.trim();
            }
        }
        return entityId;
    }
    
    // Funzione per ottenere il colore dell'entità dal suo ID
    function getEntityColorById(entityId) {
        for (const entityType of entityTypes) {
            if (entityType.dataset.type === entityId) {
                return entityType.style.backgroundColor;
            }
        }
        return "#CCCCCC";
    }
    
    // Gestione della selezione del testo
    textContent.addEventListener('mouseup', function(e) {
        const selection = window.getSelection();
        
        // Verifica se c'è del testo selezionato
        if (selection.toString().trim() === '') {
            return;
        }
        
        if (!selectedType) {
            showNotification('Seleziona prima un tipo di entità', 'error');
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
                const proceed = confirm('La selezione si sovrappone a un\'annotazione esistente. Continuare?');
                if (!proceed) {
                    updateStatus('Annotazione annullata', true);
                    return;
                }
            }
            
            // Crea l'annotazione
            const annotation = {
                start: startOffset,
                end: endOffset,
                text: selectedText,
                type: selectedType
            };
            
            console.log(`Creata annotazione: ${JSON.stringify(annotation)}`);
            updateStatus('Creazione annotazione in corso...');
            
            // Salva l'annotazione
            saveAnnotation(annotation);
        } catch (e) {
            console.error("Errore nella selezione del testo:", e);
            updateStatus('Errore nella selezione del testo', true);
        }
    });
    
    // Funzione per salvare un'annotazione
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
                
                // Aggiorna il conteggio
                updateAnnotationCount();
                
                // Mostra notifica
                showNotification('Annotazione salvata con successo', 'success');
                updateStatus('Annotazione salvata con successo');
            } else {
                showNotification(`Errore: ${data.message}`, 'error');
                updateStatus(`Errore: ${data.message}`, true);
            }
        })
        .catch(error => {
            console.error('Errore:', error);
            showNotification('Errore durante il salvataggio', 'error');
            updateStatus('Errore durante il salvataggio', true);
        });
    }
    
    // Funzione per aggiungere un'annotazione alla lista
    function addAnnotationToList(annotation) {
        // Ottieni il colore e il nome del tipo di entità
        const entityColor = getEntityColorById(annotation.type);
        const entityName = getEntityNameById(annotation.type);
        
        // Crea l'elemento HTML per l'annotazione
        const annotationItem = document.createElement('div');
        annotationItem.className = 'annotation-item';
        annotationItem.dataset.id = annotation.id;
        annotationItem.dataset.start = annotation.start;
        annotationItem.dataset.end = annotation.end;
        annotationItem.dataset.type = annotation.type;
        
        annotationItem.innerHTML = `
            <span class="annotation-text">${annotation.text}</span>
            <span class="annotation-type" style="background-color: ${entityColor}">
                ${entityName || annotation.type}
            </span>
            <div class="annotation-actions">
                <button class="jump-to-annotation" data-id="${annotation.id}" title="Vai al testo">🔍</button>
                <button class="delete-annotation" data-id="${annotation.id}" title="Elimina">🗑️</button>
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
    }
    
    // Funzione per saltare a una specifica annotazione nel testo
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
    
    // Funzione per eliminare un'annotazione
    function deleteAnnotation(annotationId) {
        if (!confirm('Sei sicuro di voler eliminare questa annotazione?')) {
            return;
        }
        
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
            if (data.status === 'success') {
                // Rimuovi l'annotazione dalla lista
                const annotationItem = document.querySelector(`.annotation-item[data-id="${annotationId}"]`);
                if (annotationItem) {
                    annotationItem.remove();
                }
                
                // Riesegui l'highlighting
                highlightExistingAnnotations();
                
                // Aggiorna il conteggio
                updateAnnotationCount();
                
                // Mostra notifica
                showNotification('Annotazione eliminata', 'success');
                updateStatus('Annotazione eliminata con successo');
            } else {
                showNotification(`Errore: ${data.message}`, 'error');
                updateStatus(`Errore: ${data.message}`, true);
            }
        })
        .catch(error => {
            console.error('Errore:', error);
            showNotification('Errore durante l\'eliminazione', 'error');
            updateStatus('Errore durante l\'eliminazione', true);
        });
    }
    
    // Gestione degli eventi di eliminazione per le annotazioni esistenti
    document.querySelectorAll('.delete-annotation').forEach(btn => {
        btn.addEventListener('click', function() {
            const annotationId = this.dataset.id;
            deleteAnnotation(annotationId);
        });
    });
    
    // Gestione degli eventi di salto all'annotazione
    document.querySelectorAll('.jump-to-annotation').forEach(btn => {
        btn.addEventListener('click', function() {
            const annotationId = this.dataset.id;
            jumpToAnnotation(annotationId);
        });
    });
    
    // Gestione del pulsante per l'annotazione automatica
    if (autoAnnotateBtn) {
        autoAnnotateBtn.addEventListener('click', function() {
            const text = textContent.textContent;
            
            if (!confirm('Vuoi eseguire il riconoscimento automatico delle entità nel testo? Questo processo potrebbe richiedere alcuni secondi.')) {
                return;
            }
            
            // Mostra un indicatore di caricamento
            autoAnnotateBtn.disabled = true;
            autoAnnotateBtn.textContent = "Elaborazione...";
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
                        autoAnnotateBtn.textContent = "Riconoscimento automatico";
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
                                autoAnnotateBtn.textContent = `Salvate ${savedCount}/${totalToSave}...`;
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
                        autoAnnotateBtn.textContent = "Riconoscimento automatico";
                        
                        // Aggiorna l'evidenziazione delle annotazioni
                        highlightExistingAnnotations();
                        
                        // Aggiorna il conteggio
                        updateAnnotationCount();
                        
                        // Mostra notifica
                        showNotification(`Salvate ${savedCount} annotazioni automatiche`, 'success');
                        updateStatus(`Completato: salvate ${savedCount} annotazioni automatiche`);
                    })
                    .catch(error => {
                        console.error('Errore durante il salvataggio:', error);
                        autoAnnotateBtn.disabled = false;
                        autoAnnotateBtn.textContent = "Riconoscimento automatico";
                        showNotification('Errore durante il salvataggio delle annotazioni', 'error');
                        updateStatus('Errore durante il salvataggio delle annotazioni', true);
                    });
                } else {
                    showNotification(`Errore: ${data.message}`, 'error');
                    updateStatus(`Errore: ${data.message}`, true);
                    autoAnnotateBtn.disabled = false;
                    autoAnnotateBtn.textContent = "Riconoscimento automatico";
                }
            })
            .catch(error => {
                console.error('Errore:', error);
                showNotification('Errore durante il riconoscimento automatico', 'error');
                updateStatus('Errore durante il riconoscimento automatico', true);
                autoAnnotateBtn.disabled = false;
                autoAnnotateBtn.textContent = "Riconoscimento automatico";
            });
        });
    }
    
    // Inizializzazione: evidenzia le annotazioni esistenti
    highlightExistingAnnotations();
});

// Add document management functions
function deleteDocument(docId) {
    if (!confirm('Sei sicuro di voler eliminare questo documento e tutte le sue annotazioni?')) {
        return;
    }
    
    fetch('/api/delete_document', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({doc_id: docId})
    })
    .then(handleResponse)
    .then(() => window.location.href = '/')
    .catch(handleError);
}

function updateDocument(docId, newContent) {
    return fetch('/api/update_document', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({doc_id: docId, content: newContent})
    });
}