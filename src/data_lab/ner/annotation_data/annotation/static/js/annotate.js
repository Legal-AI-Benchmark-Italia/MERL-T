document.addEventListener('DOMContentLoaded', function() {
    const textContent = document.getElementById('text-content');
    const docId = textContent.dataset.docId;
    const entityTypes = document.querySelectorAll('.entity-type');
    const clearSelectionBtn = document.getElementById('clear-selection');
    const annotationsContainer = document.getElementById('annotations-container');
    
    let selectedType = null;
    let selection = null;
    
    // Carica le annotazioni esistenti
    const existingAnnotations = [];
    document.querySelectorAll('.annotation-item').forEach(item => {
        const id = item.dataset.id;
        const text = item.querySelector('.annotation-text').textContent;
        const type = item.querySelector('.annotation-type').textContent;
        existingAnnotations.push({ id, text, type });
    });
    
    // Evidenzia le annotazioni esistenti nel testo
    function highlightExistingAnnotations() {
        // Implementazione dell'evidenziazione delle annotazioni esistenti
    }
    
    // Gestione della selezione del tipo di entità
    entityTypes.forEach(entityType => {
        entityType.addEventListener('click', function() {
            // Rimuovi la selezione precedente
            entityTypes.forEach(et => et.classList.remove('selected'));
            
            // Seleziona il nuovo tipo
            this.classList.add('selected');
            selectedType = this.dataset.type;
        });
    });
    
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
        
        // Ottieni l'intervallo di selezione
        const range = selObj.getRangeAt(0);
        const startOffset = range.startOffset;
        const endOffset = range.endOffset;
        
        // Crea l'annotazione
        const annotation = {
            start: startOffset,
            end: endOffset,
            text: selObj.toString(),
            type: selectedType
        };
        
        // Salva l'annotazione
        saveAnnotation(annotation);
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
        
        annotationItem.innerHTML = `
            <span class="annotation-text">${annotation.text}</span>
            <span class="annotation-type" style="background-color: ${entityColor}">
                ${entityName}
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
});
