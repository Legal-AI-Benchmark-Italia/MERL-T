document.addEventListener('DOMContentLoaded', function() {
    // Gestione del form di upload (esistente)
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('document-file');
    
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const file = fileInput.files[0];
            if (!file) {
                alert('Seleziona un file da caricare');
                return;
            }
            
            const formData = new FormData();
            formData.append('file', file);
            
            // Aggiungi un indicatore di caricamento
            const submitButton = uploadForm.querySelector('button[type="submit"]');
            const originalText = submitButton.textContent;
            submitButton.disabled = true;
            submitButton.textContent = 'Caricamento in corso...';
            
            fetch('/api/upload_document', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showNotification('Documento caricato con successo', 'success');
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    showNotification('Errore: ' + data.message, 'error');
                    submitButton.disabled = false;
                    submitButton.textContent = originalText;
                }
            })
            .catch(error => {
                console.error('Errore:', error);
                showNotification('Si è verificato un errore durante il caricamento', 'error');
                submitButton.disabled = false;
                submitButton.textContent = originalText;
            });
        });
    }
    
    // Gestione dei pulsanti di esportazione (esistente)
    const exportJsonBtn = document.getElementById('export-json');
    const exportSpacyBtn = document.getElementById('export-spacy');
    
    if (exportJsonBtn) {
        exportJsonBtn.addEventListener('click', function() {
            window.location.href = '/api/export_annotations?format=json&download=true';
        });
    }
    
    if (exportSpacyBtn) {
        exportSpacyBtn.addEventListener('click', function() {
            window.location.href = '/api/export_annotations?format=spacy&download=true';
        });
    }
    
    // NUOVA FUNZIONALITÀ: Gestione dell'eliminazione di documenti
    // Collega gli eventi ai pulsanti di eliminazione esistenti nella pagina
    const deleteButtons = document.querySelectorAll('.delete-doc-btn');
    
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const docId = this.dataset.id;
            const docTitle = this.dataset.title || docId;
            
            // Usa la funzione globale deleteDocument definita in annotate.js
            if (typeof window.deleteDocument === 'function') {
                window.deleteDocument(docId, docTitle);
            } else {
                // Implementazione di fallback se la funzione globale non è disponibile
                if (confirm(`Sei sicuro di voler eliminare il documento "${docTitle}" e tutte le sue annotazioni?`)) {
                    fetch('/api/delete_document', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({doc_id: docId})
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            showNotification('Documento eliminato con successo', 'success');
                            setTimeout(() => {
                                window.location.reload();
                            }, 1500);
                        } else {
                            showNotification('Errore: ' + data.message, 'error');
                        }
                    })
                    .catch(error => {
                        console.error('Errore:', error);
                        showNotification('Si è verificato un errore durante l\'eliminazione', 'error');
                    });
                }
            }
        });
    });
    
    // Funzione di utilità per mostrare notifiche
    function showNotification(message, type) {
        // Verifica se esiste già un elemento di notifica
        let notification = document.getElementById('notification');
        
        // Se non esiste, crealo
        if (!notification) {
            notification = document.createElement('div');
            notification.id = 'notification';
            notification.className = 'notification';
            document.body.appendChild(notification);
        }
        
        // Imposta il messaggio e il tipo
        notification.textContent = message;
        notification.className = `notification ${type} show`;
        
        // Nascondi la notifica dopo 3 secondi
        setTimeout(() => {
            notification.className = 'notification';
        }, 3000);
    }
    
    // NUOVA FUNZIONALITÀ: Aggiungi la possibilità di modificare il titolo di un documento
    const editTitleButtons = document.querySelectorAll('.edit-title-btn');
    
    if (editTitleButtons) {
        editTitleButtons.forEach(function(button) {
            button.addEventListener('click', function() {
                const docId = this.dataset.id;
                const currentTitle = this.dataset.title;
                
                const newTitle = prompt('Inserisci il nuovo titolo del documento', currentTitle);
                
                if (newTitle && newTitle !== currentTitle) {
                    // Usa la funzione globale updateDocument definita in annotate.js
                    if (typeof window.updateDocument === 'function') {
                        window.updateDocument(docId, undefined, newTitle)
                            .then(() => {
                                // Aggiorna l'interfaccia utente senza ricaricare
                                const titleElement = document.querySelector(`.document-item[data-id="${docId}"] .document-title`);
                                if (titleElement) {
                                    titleElement.textContent = newTitle;
                                }
                                // Aggiorna l'attributo data-title per la prossima modifica
                                this.dataset.title = newTitle;
                            });
                    } else {
                        // Implementazione di fallback
                        fetch('/api/update_document', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                doc_id: docId,
                                title: newTitle
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.status === 'success') {
                                showNotification('Titolo aggiornato con successo', 'success');
                                // Aggiorna l'interfaccia utente senza ricaricare
                                const titleElement = document.querySelector(`.document-item[data-id="${docId}"] .document-title`);
                                if (titleElement) {
                                    titleElement.textContent = newTitle;
                                }
                                // Aggiorna l'attributo data-title per la prossima modifica
                                this.dataset.title = newTitle;
                            } else {
                                showNotification('Errore: ' + data.message, 'error');
                            }
                        })
                        .catch(error => {
                            console.error('Errore:', error);
                            showNotification('Si è verificato un errore durante l\'aggiornamento', 'error');
                        });
                    }
                }
            });
        });
    }
    
    // Esponi le funzioni utili come metodi globali
    window.showNotification = showNotification;
});