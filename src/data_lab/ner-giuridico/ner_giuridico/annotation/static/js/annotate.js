// Modifica completa di annotate.js con correzioni per l'highlighting

document.addEventListener('DOMContentLoaded', function() {
    const textContent = document.getElementById('text-content');
    const docId = textContent.dataset.docId;
    const entityTypes = document.querySelectorAll('.entity-type');
    const clearSelectionBtn = document.getElementById('clear-selection');
    const autoAnnotateBtn = document.getElementById('auto-annotate');
    const annotationsContainer = document.getElementById('annotations-container');
    
    let selectedType = null;
    
    // Debug
    console.log(`Tipi di entità disponibili: ${entityTypes.length}`);
    entityTypes.forEach(et => {
        console.log(`Entità: ${et.textContent.trim()}, tipo: ${et.dataset.type}, colore: ${et.style.backgroundColor}`);
    });
    
    // Carica le annotazioni esistenti e prepara i dati per l'highlighting
    const existingAnnotations = [];
    document.querySelectorAll('.annotation-item').forEach(item => {
        const id = item.dataset.id;
        const text = item.querySelector('.annotation-text').textContent;
        const type = item.querySelector('.annotation-type').textContent.trim();
        const start = parseInt(item.dataset.start);
        const end = parseInt(item.dataset.end);
        const color = item.querySelector('.annotation-type').style.backgroundColor;
        
        // Aggiungi attributi data-start e data-end all'elemento HTML se non esistono
        if (!item.hasAttribute('data-start')) {
            item.dataset.start = start;
        }
        if (!item.hasAttribute('data-end')) {
            item.dataset.end = end;
        }
        
        existingAnnotations.push({ id, text, type, start, end, color });
    });
    
    // Gestione della selezione del tipo di entità
    entityTypes.forEach(entityType => {
        entityType.addEventListener('click', function() {
            // Rimuovi la selezione precedente
            entityTypes.forEach(et => et.classList.remove('selected'));
            
            // Seleziona il nuovo tipo
            this.classList.add('selected');
            selectedType = this.dataset.type;
            console.log(`Selezionato tipo: ${selectedType}`);
        });
    });
    
    // Funzione per evidenziare le annotazioni esistenti nel testo
    function highlightExistingAnnotations() {
        // Ottieni il contenitore del testo e tutte le annotazioni
        const annotationItems = document.querySelectorAll('.annotation-item');
        const text = textContent.textContent;
        
        // Crea una mappa delle posizioni delle annotazioni
        // Struttura: {posizione: [{id: 'id_annotazione', type: 'tipo_entità', end: fine_annotazione, color: 'colore'}]}
        let annotationMap = {};
        
        annotationItems.forEach(item => {
            const id = item.dataset.id;
            const start = parseInt(item.dataset.start);
            const end = parseInt(item.dataset.end);
            const typeElement = item.querySelector('.annotation-type');
            const type = typeElement ? typeElement.textContent.trim() : "";
            const color = typeElement ? typeElement.style.backgroundColor : "#CCCCCC";
            
            console.log(`Annotazione: id=${id}, start=${start}, end=${end}, type=${type}, color=${color}`);
            
            // Verifica che start e end siano numeri validi
            if (!isNaN(start) && !isNaN(end)) {
                if (!annotationMap[start]) {
                    annotationMap[start] = [];
                }
                annotationMap[start].push({id, type, end, color});
            } else {
                console.warn(`Annotazione con valori non validi: id=${id}, start=${start}, end=${end}`);
            }
        });
        
        // Se non ci sono annotazioni, esci
        if (Object.keys(annotationMap).length === 0) {
            console.log("Nessuna annotazione da evidenziare");
            return;
        }
        
        // Sostituisci il contenuto del testo con una versione evidenziata
        let positions = Object.keys(annotationMap).map(Number).sort((a, b) => a - b);
        let htmlContent = '';
        let lastPosition = 0;
        
        positions.forEach(position => {
            // Aggiungi il testo prima dell'annotazione
            htmlContent += text.substring(lastPosition, position);
            
            // Gestisci le annotazioni che iniziano in questa posizione
            annotationMap[position].forEach(ann => {
                // Aggiungi il testo dell'annotazione con lo stile appropriato
                const entityText = text.substring(position, ann.end);
                htmlContent += `<span class="entity-highlight" style="background-color: ${ann.color};" data-id="${ann.id}" title="${ann.type}">${entityText}</span>`;
                
                // Aggiorna la posizione finale
                lastPosition = Math.max(lastPosition, ann.end);
            });
        });
        
        // Aggiungi il testo rimanente
        htmlContent += text.substring(lastPosition);
        
        // Sostituisci il contenuto
        textContent.innerHTML = htmlContent;
        
        // Aggiungi eventi alle entità evidenziate
        document.querySelectorAll('.entity-highlight').forEach(highlight => {
            highlight.addEventListener('click', function() {
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
    
    // Gestione della selezione del testo
    textContent.addEventListener('mouseup', function() {
        if (!selectedType) {
            alert('Seleziona prima un tipo di entità');
            return;
        }
        
        const selObj = window.getSelection();
        if (selObj.toString().trim() === '') {
            return;
        }
        
        try {
            // Ottieni l'intervallo di selezione
            const range = selObj.getRangeAt(0);
            
            // Calcola l'offset rispetto al testo completo
            // Questo è più affidabile che usare range.startOffset e range.endOffset
            // che sono relativi al nodo del DOM
            const fullText = textContent.textContent;
            const selectedText = selObj.toString();
            
            // Trova l'indice di inizio della selezione nel testo completo
            let startOffset = -1;
            
            // Ottieni le posizioni di tutte le occorrenze del testo selezionato
            let temp = fullText;
            let index = temp.indexOf(selectedText);
            let offsets = [];
            
            while (index !== -1) {
                offsets.push(index);
                temp = temp.substring(index + 1);
                index = temp.indexOf(selectedText);
                if (index !== -1) {
                    index += fullText.length - temp.length;
                }
            }
            
            // Cerca di determinare quale occorrenza è stata selezionata
            // basandoti sulla posizione del mouse
            // Per semplicità, usiamo la prima occorrenza
            if (offsets.length > 0) {
                startOffset = offsets[0];
            }
            
            if (startOffset === -1) {
                console.error("Non è possibile determinare la posizione della selezione nel testo");
                return;
            }
            
            const endOffset = startOffset + selectedText.length;
            
            // Crea l'annotazione
            const annotation = {
                start: startOffset,
                end: endOffset,
                text: selectedText,
                type: selectedType
            };
            
            console.log(`Creata annotazione: ${JSON.stringify(annotation)}`);
            
            // Salva l'annotazione
            saveAnnotation(annotation);
        } catch (e) {
            console.error("Errore nella selezione del testo:", e);
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
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Aggiungi l'annotazione alla lista
                addAnnotationToList(data.annotation);
                
                // Pulisci la selezione
                window.getSelection().removeAllRanges();
                
                // Riesegui l'highlighting
                highlightExistingAnnotations();
            } else {
                alert('Errore: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Errore:', error);
            alert('Si è verificato un errore durante il salvataggio dell\'annotazione');
        });
    }
    
    // Funzione per aggiungere un'annotazione alla lista
    function addAnnotationToList(annotation) {
        // Trova il colore e il nome del tipo di entità
        let entityColor = '';
        let entityName = '';
        
        entityTypes.forEach(entityType => {
            if (entityType.dataset.type === annotation.type) {
                entityColor = entityType.style.backgroundColor;
                entityName = entityType.textContent.trim();
            }
        });
        
        // Crea l'elemento HTML per l'annotazione
        const annotationItem = document.createElement('div');
        annotationItem.className = 'annotation-item';
        annotationItem.dataset.id = annotation.id;
        annotationItem.dataset.start = annotation.start;
        annotationItem.dataset.end = annotation.end;
        
        annotationItem.innerHTML = `
            <span class="annotation-text">${annotation.text}</span>
            <span class="annotation-type" style="background-color: ${entityColor}">
                ${entityName || annotation.type}
            </span>
            <button class="delete-annotation" data-id="${annotation.id}">Elimina</button>
        `;
        
        // Aggiungi l'elemento alla lista
        annotationsContainer.appendChild(annotationItem);
        
        // Aggiungi l'evento per eliminare l'annotazione
        const deleteBtn = annotationItem.querySelector('.delete-annotation');
        deleteBtn.addEventListener('click', function() {
            deleteAnnotation(annotation.id);
        });
    }
    
    // Funzione per eliminare un'annotazione
    function deleteAnnotation(annotationId) {
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
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Rimuovi l'annotazione dalla lista
                const annotationItem = document.querySelector(`.annotation-item[data-id="${annotationId}"]`);
                if (annotationItem) {
                    annotationItem.remove();
                }
                
                // Riesegui l'highlighting
                highlightExistingAnnotations();
            } else {
                alert('Errore: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Errore:', error);
            alert('Si è verificato un errore durante l\'eliminazione dell\'annotazione');
        });
    }
    
    // Gestione del pulsante per annullare la selezione
    clearSelectionBtn.addEventListener('click', function() {
        entityTypes.forEach(et => et.classList.remove('selected'));
        selectedType = null;
        window.getSelection().removeAllRanges();
    });
    
    // Gestione degli eventi di eliminazione per le annotazioni esistenti
    document.querySelectorAll('.delete-annotation').forEach(btn => {
        btn.addEventListener('click', function() {
            const annotationId = this.dataset.id;
            deleteAnnotation(annotationId);
        });
    });
    
    // Gestione del pulsante per l'annotazione automatica
    if (autoAnnotateBtn) {
        autoAnnotateBtn.addEventListener('click', function() {
            const text = textContent.textContent;
            
            // Mostra un indicatore di caricamento
            autoAnnotateBtn.disabled = true;
            autoAnnotateBtn.textContent = "Elaborazione...";
            
            // Richiedi il riconoscimento automatico delle entità
            fetch('/api/recognize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ text: text })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const entities = data.entities;
                    console.log(`Riconosciute ${entities.length} entità automaticamente`);
                    
                    // Per ogni entità riconosciuta, crea un'annotazione
                    let savedCount = 0;
                    const totalToSave = entities.length;
                    
                    // Se non ci sono entità riconosciute
                    if (entities.length === 0) {
                        alert('Nessuna entità riconosciuta automaticamente');
                        autoAnnotateBtn.disabled = false;
                        autoAnnotateBtn.textContent = "Riconoscimento automatico";
                        return;
                    }
                    
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
                        .then(response => response.json())
                        .then(data => {
                            if (data.status === 'success') {
                                savedCount++;
                                // Aggiorna il testo del pulsante per mostrare il progresso
                                autoAnnotateBtn.textContent = `Salvate ${savedCount}/${totalToSave}...`;
                                
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
                    });
                } else {
                    alert('Errore: ' + data.message);
                    autoAnnotateBtn.disabled = false;
                    autoAnnotateBtn.textContent = "Riconoscimento automatico";
                }
            })
            .catch(error => {
                console.error('Errore:', error);
                alert('Si è verificato un errore durante il riconoscimento automatico');
                autoAnnotateBtn.disabled = false;
                autoAnnotateBtn.textContent = "Riconoscimento automatico";
            });
        });
    }
    
    // Inizializzazione: evidenzia le annotazioni esistenti
    // Chiamiamo questa funzione all'avvio
    highlightExistingAnnotations();
});