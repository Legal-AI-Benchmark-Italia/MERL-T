/**
 * document-manager.js - Gestore documenti ottimizzato
 * 
 * Gestisce l'interfaccia per il caricamento, visualizzazione e gestione dei documenti
 * con un approccio modulare e implementazione robusta della gestione errori
 * 
 * @version 2.0.0
 */

const DocumentManager = (function() {
    'use strict';
    
    // Stato dell'applicazione
    const state = {
        documents: [],        // Lista di documenti
        filterText: '',       // Testo di ricerca per filtri
        filterCategory: '',   // Filtro categoria
        isProcessing: false,  // Flag operazione in corso
        initialized: false    // Flag inizializzazione
    };
    
    // Elementi DOM
    let elements = {};
    
    /**
     * Inizializza il gestore documenti
     * @param {Object} options - Opzioni di configurazione
     * @returns {boolean} Stato dell'inizializzazione
     */
    function initialize(options = {}) {
        try {
            // Evita reinizializzazioni
            if (state.initialized) {
                return true;
            }
            
            console.info('Inizializzazione DocumentManager...');
            
            // Seleziona gli elementi DOM principali
            elements = {
                documentsContainer: document.querySelector('.row-cols-1'),
                uploadForm: document.getElementById('upload-form'),
                fileInput: document.getElementById('document-file'),
                exportJsonBtn: document.getElementById('export-json'),
                exportSpacyBtn: document.getElementById('export-spacy'),
                trainModelBtn: document.getElementById('train-model-btn'),
                searchInput: document.getElementById('search-documents'),
                categoryFilter: document.getElementById('category-filter'),
                documentCount: document.querySelector('.badge.bg-primary'),
                emptyState: document.querySelector('.text-center.py-5')
            };
            
            // Verifica elementi essenziali
            if (!elements.documentsContainer) {
                console.warn('Elemento container documenti non trovato');
            }
            
            // Carica i documenti dal DOM
            loadDocumentsFromDOM();
            
            // Configura i gestori di eventi
            setupEventHandlers();
            
            // Segna come inizializzato
            state.initialized = true;
            console.info('DocumentManager inizializzato con successo');
            
            return true;
        } catch (error) {
            console.error('Errore durante l\'inizializzazione di DocumentManager:', error);
            return false;
        }
    }
    
    /**
     * Carica i documenti dal DOM
     */
    function loadDocumentsFromDOM() {
        try {
            state.documents = [];
            
            // Trova tutti i card dei documenti
            const docCards = document.querySelectorAll('.doc-card');
            
            docCards.forEach(card => {
                const docId = card.dataset.id;
                const title = card.querySelector('.document-title')?.textContent || 'Documento senza titolo';
                const preview = card.querySelector('.document-preview')?.textContent || '';
                const annotations = parseInt(card.dataset.annotations || '0');
                const wordCount = parseInt(card.dataset.wordCount || '0');
                const dateElement = card.querySelector('.document-metadata span:nth-child(2)');
                const date = dateElement ? dateElement.textContent.replace(/[^\d-]/g, '') : '';
                
                state.documents.push({
                    id: docId,
                    title: title,
                    preview: preview,
                    annotations: annotations,
                    wordCount: wordCount,
                    date: date
                });
            });
            
            // Aggiorna il conteggio dei documenti
            updateDocumentCount();
            
            console.info(`Caricati ${state.documents.length} documenti dal DOM`);
        } catch (error) {
            console.error('Errore durante il caricamento dei documenti dal DOM:', error);
        }
    }
    
    /**
     * Configura i gestori di eventi
     */
    function setupEventHandlers() {
        try {
            // Form di upload
            if (elements.uploadForm) {
                elements.uploadForm.addEventListener('submit', handleDocumentUpload);
                
                // Mostra il nome del file quando un file viene selezionato
                if (elements.fileInput) {
                    elements.fileInput.addEventListener('change', function() {
                        const fileNameDisplay = document.querySelector('.file-name');
                        if (fileNameDisplay) {
                            fileNameDisplay.textContent = this.files[0] ? this.files[0].name : 'Nessun file selezionato';
                        }
                    });
                }
            }
            
            // Pulsanti di esportazione
            if (elements.exportJsonBtn) {
                elements.exportJsonBtn.addEventListener('click', () => exportAnnotations('json'));
            }
            
            if (elements.exportSpacyBtn) {
                elements.exportSpacyBtn.addEventListener('click', () => exportAnnotations('spacy'));
            }
            
            // Addestramento modello
            if (elements.trainModelBtn) {
                elements.trainModelBtn.addEventListener('click', trainModel);
            }
            
            // Ricerca e filtro
            if (elements.searchInput) {
                elements.searchInput.addEventListener('input', debounce(filterDocuments, 300));
            }
            
            if (elements.categoryFilter) {
                elements.categoryFilter.addEventListener('change', filterDocuments);
            }
            
            // Gestione delle azioni sui documenti (delegazione eventi)
            document.addEventListener('click', handleDocumentAction);
        } catch (error) {
            console.error('Errore nella configurazione degli event handlers:', error);
        }
    }
    
    /**
     * Gestisce le azioni sui documenti (elimina, rinomina)
     * @param {Event} e - Evento click
     */
    function handleDocumentAction(e) {
        try {
            // Gestione pulsante eliminazione
            if (e.target.closest('.delete-doc-btn')) {
                const btn = e.target.closest('.delete-doc-btn');
                const docId = btn.dataset.id;
                const docTitle = btn.dataset.title || docId;
                deleteDocument(docId, docTitle);
                return;
            }
            
            // Gestione pulsante rinomina
            if (e.target.closest('.edit-title-btn')) {
                const btn = e.target.closest('.edit-title-btn');
                const docId = btn.dataset.id;
                const currentTitle = btn.dataset.title;
                renameDocument(docId, currentTitle);
                return;
            }
            
            // Pulsante per cancellare i filtri di ricerca
            if (e.target.closest('.clear-filters-btn')) {
                if (elements.searchInput) {
                    elements.searchInput.value = '';
                }
                
                if (elements.categoryFilter) {
                    elements.categoryFilter.value = '';
                }
                
                filterDocuments();
                return;
            }
        } catch (error) {
            console.error('Errore nella gestione delle azioni sui documenti:', error);
        }
    }
    
    /**
     * Gestisce l'upload di un documento
     * @param {Event} e - Evento submit
     */
    function handleDocumentUpload(e) {
        try {
            e.preventDefault();
            
            if (state.isProcessing) {
                showNotification('Operazione già in corso, attendere...', 'warning');
                return;
            }
            
            // Verifica che sia stato selezionato un file
            const fileInput = elements.fileInput;
            if (!fileInput || !fileInput.files || !fileInput.files[0]) {
                showNotification('Seleziona un file da caricare', 'warning');
                return;
            }
            
            const file = fileInput.files[0];
            
            // Verifica dimensione massima (10MB)
            if (file.size > 10 * 1024 * 1024) {
                showNotification('Il file è troppo grande. Il limite è di 10MB.', 'danger');
                return;
            }
            
            // Mostra stato di caricamento
            state.isProcessing = true;
            const submitButton = elements.uploadForm.querySelector('button[type="submit"]');
            
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Caricamento...';
            }
            
            // Prepara i dati per l'upload
            const formData = new FormData();
            formData.append('file', file);
            
            // Usa APIClient se disponibile
            if (window.APIClient) {
                APIClient.documents.upload(formData)
                    .then(data => {
                        handleDocumentUploaded(data.document);
                    })
                    .catch(error => {
                        console.error('Errore durante l\'upload:', error);
                        showNotification('Errore durante il caricamento: ' + (error.message || 'Errore sconosciuto'), 'danger');
                    })
                    .finally(() => {
                        finishUploadProcessing(submitButton);
                    });
            } else {
                // Fallback con fetch
                fetch('/api/upload_document', {
                    method: 'POST',
                    body: formData
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Errore HTTP: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'success') {
                        handleDocumentUploaded(data.document);
                    } else {
                        throw new Error(data.message || 'Errore non specificato');
                    }
                })
                .catch(error => {
                    console.error('Errore durante l\'upload:', error);
                    showNotification('Errore durante il caricamento: ' + error.message, 'danger');
                })
                .finally(() => {
                    finishUploadProcessing(submitButton);
                });
            }
        } catch (error) {
            console.error('Errore durante il caricamento del documento:', error);
            showNotification('Errore durante il caricamento', 'danger');
            
            // Ripristina lo stato del form
            state.isProcessing = false;
            const submitButton = elements.uploadForm.querySelector('button[type="submit"]');
            
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = 'Carica';
            }
        }
    }
    
    /**
     * Gestisce il completamento dell'upload
     * @param {HTMLElement} submitButton - Pulsante di invio del form
     */
    function finishUploadProcessing(submitButton) {
        try {
            state.isProcessing = false;
            
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = 'Carica';
            }
            
            // Resetta il form
            if (elements.uploadForm) {
                elements.uploadForm.reset();
                
                // Aggiorna il nome del file visualizzato
                const fileNameDisplay = document.querySelector('.file-name');
                if (fileNameDisplay) {
                    fileNameDisplay.textContent = 'Nessun file selezionato';
                }
            }
        } catch (error) {
            console.error('Errore durante il completamento dell\'upload:', error);
        }
    }
    
    /**
     * Gestisce l'upload riuscito di un documento
     * @param {Object} document - Il documento caricato
     */
    function handleDocumentUploaded(document) {
        try {
            if (!document) {
                throw new Error('Dati documento mancanti nella risposta');
            }
            
            // Aggiungi il documento allo stato
            state.documents.push({
                id: document.id,
                title: document.title,
                preview: document.text?.substring(0, 150) + '...' || '',
                annotations: 0,
                wordCount: document.word_count || 0,
                date: new Date().toISOString().split('T')[0]
            });
            
            // Aggiorna la UI
            addDocumentToUI(document);
            
            // Aggiorna il conteggio
            updateDocumentCount();
            
            // Nascondi il messaggio "nessun documento" se presente
            if (elements.emptyState) {
                elements.emptyState.classList.add('d-none');
            }
            
            // Mostra conferma
            showNotification('Documento caricato con successo', 'success');
        } catch (error) {
            console.error('Errore nella gestione del documento caricato:', error);
        }
    }
    
    /**
     * Aggiunge un documento all'interfaccia
     * @param {Object} document - Il documento da aggiungere
     */
    function addDocumentToUI(document) {
        try {
            if (!elements.documentsContainer) {
                console.warn('Container documenti non trovato, impossibile aggiungere documento alla UI');
                return;
            }
            
            // Formatta la data
            const formattedDate = formatDate(document.date_created || new Date());
            
            // Crea l'elemento del documento
            const col = document.createElement('div');
            col.className = 'col';
            
            col.innerHTML = `
                <div class="card h-100 doc-card" data-id="${document.id}" data-word-count="${document.word_count || 0}" data-annotations="0">
                    <div class="card-header bg-light">
                        <h5 class="card-title document-title mb-0">${document.title}</h5>
                    </div>
                    <div class="card-body">
                        <p class="card-text document-preview text-truncate">${document.text?.substring(0, 150) || ''}...</p>
                        <div class="document-metadata text-muted small">
                            <span><i class="fas fa-file-word me-1"></i>${document.word_count || 0} parole</span>
                            <span><i class="fas fa-calendar-alt me-1"></i>${formattedDate}</span>
                        </div>
                    </div>
                    <div class="card-footer bg-white">
                        <div class="btn-group w-100" role="group">
                            <a href="/annotate/${document.id}" class="btn btn-success">
                                <i class="fas fa-tag me-1"></i>Annota
                            </a>
                            <button class="btn btn-primary edit-title-btn" data-id="${document.id}" data-title="${document.title}">
                                <i class="fas fa-edit me-1"></i>Rinomina
                            </button>
                            <button class="btn btn-danger delete-doc-btn" data-id="${document.id}" data-title="${document.title}">
                                <i class="fas fa-trash-alt me-1"></i>Elimina
                            </button>
                        </div>
                    </div>
                </div>
            `;
            
            // Aggiungi all'inizio del container
            elements.documentsContainer.insertBefore(col, elements.documentsContainer.firstChild);
            
            // Effetto di evidenziazione
            setTimeout(() => {
                col.querySelector('.card').style.backgroundColor = '#f0fff4';
                
                setTimeout(() => {
                    col.querySelector('.card').style.transition = 'background-color 0.5s';
                    col.querySelector('.card').style.backgroundColor = '';
                }, 300);
            }, 100);
        } catch (error) {
            console.error('Errore nell\'aggiunta del documento all\'interfaccia:', error);
        }
    }
    
    /**
     * Elimina un documento
     * @param {string} docId - ID del documento
     * @param {string} docTitle - Titolo del documento
     */
    function deleteDocument(docId, docTitle) {
        try {
            if (state.isProcessing) {
                showNotification('Operazione già in corso, attendere...', 'warning');
                return;
            }
            
            if (!confirm(`Sei sicuro di voler eliminare il documento "${docTitle || docId}" e tutte le sue annotazioni?`)) {
                return;
            }
            
            // Mostra stato di caricamento
            state.isProcessing = true;
            const deleteBtn = document.querySelector(`.delete-doc-btn[data-id="${docId}"]`);
            
            if (deleteBtn) {
                deleteBtn.disabled = true;
                deleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Eliminazione...';
            }
            
            // Usa APIClient se disponibile
            if (window.APIClient) {
                APIClient.documents.delete(docId)
                    .then(data => {
                        handleDocumentDeleted(docId);
                    })
                    .catch(error => {
                        console.error('Errore durante l\'eliminazione:', error);
                        showNotification('Errore durante l\'eliminazione: ' + (error.message || 'Errore sconosciuto'), 'danger');
                    })
                    .finally(() => {
                        state.isProcessing = false;
                    });
            } else {
                // Fallback con fetch
                fetch('/api/delete_document', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({doc_id: docId})
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Errore HTTP: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'success') {
                        handleDocumentDeleted(docId);
                    } else {
                        throw new Error(data.message || 'Errore non specificato');
                    }
                })
                .catch(error => {
                    console.error('Errore durante l\'eliminazione:', error);
                    showNotification('Errore durante l\'eliminazione: ' + error.message, 'danger');
                    
                    // Ripristina il pulsante
                    if (deleteBtn) {
                        deleteBtn.disabled = false;
                        deleteBtn.innerHTML = '<i class="fas fa-trash-alt me-1"></i>Elimina';
                    }
                })
                .finally(() => {
                    state.isProcessing = false;
                });
            }
        } catch (error) {
            console.error('Errore durante l\'eliminazione del documento:', error);
            showNotification('Errore durante l\'eliminazione', 'danger');
            state.isProcessing = false;
        }
    }
    
    /**
     * Gestisce l'eliminazione riuscita di un documento
     * @param {string} docId - ID del documento eliminato
     */
    function handleDocumentDeleted(docId) {
        try {
            // Rimuovi il documento dallo stato
            state.documents = state.documents.filter(doc => doc.id !== docId);
            
            // Rimuovi dalla UI con animazione
            const docCard = document.querySelector(`.doc-card[data-id="${docId}"]`);
            
            if (docCard) {
                const col = docCard.closest('.col');
                
                if (col) {
                    // Animazione di uscita
                    col.style.transition = 'all 0.5s ease';
                    col.style.opacity = '0';
                    col.style.transform = 'translateY(-20px)';
                    
                    // Rimuovi dopo l'animazione
                    setTimeout(() => {
                        col.remove();
                        
                        // Mostra messaggio se non ci sono più documenti
                        if (state.documents.length === 0 && elements.emptyState) {
                            elements.emptyState.classList.remove('d-none');
                        }
                        
                        // Aggiorna il conteggio
                        updateDocumentCount();
                    }, 500);
                }
            }
            
            // Mostra conferma
            showNotification('Documento eliminato con successo', 'success');
        } catch (error) {
            console.error('Errore nella gestione del documento eliminato:', error);
        }
    }
    
    /**
     * Rinomina un documento
     * @param {string} docId - ID del documento
     * @param {string} currentTitle - Titolo attuale
     */
    function renameDocument(docId, currentTitle) {
        try {
            if (state.isProcessing) {
                showNotification('Operazione già in corso, attendere...', 'warning');
                return;
            }
            
            // Usa prompt per ottenere il nuovo titolo
            const newTitle = prompt('Inserisci il nuovo titolo del documento', currentTitle);
            
            if (!newTitle || newTitle === currentTitle) {
                return;
            }
            
            // Mostra stato di caricamento
            state.isProcessing = true;
            const renameBtn = document.querySelector(`.edit-title-btn[data-id="${docId}"]`);
            
            if (renameBtn) {
                renameBtn.disabled = true;
                renameBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Salvataggio...';
            }
            
            // Usa APIClient se disponibile
            if (window.APIClient) {
                APIClient.documents.update(docId, { title: newTitle })
                    .then(data => {
                        handleDocumentRenamed(docId, newTitle);
                    })
                    .catch(error => {
                        console.error('Errore durante il rinomino:', error);
                        showNotification('Errore durante il rinomino: ' + (error.message || 'Errore sconosciuto'), 'danger');
                    })
                    .finally(() => {
                        finishRenameProcessing(renameBtn);
                    });
            } else {
                // Fallback con fetch
                fetch('/api/update_document', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        doc_id: docId,
                        title: newTitle
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
                        handleDocumentRenamed(docId, newTitle);
                    } else {
                        throw new Error(data.message || 'Errore non specificato');
                    }
                })
                .catch(error => {
                    console.error('Errore durante il rinomino:', error);
                    showNotification('Errore durante il rinomino: ' + error.message, 'danger');
                })
                .finally(() => {
                    finishRenameProcessing(renameBtn);
                });
            }
        } catch (error) {
            console.error('Errore durante il rinomino del documento:', error);
            showNotification('Errore durante il rinomino', 'danger');
            
            // Ripristina lo stato
            state.isProcessing = false;
            const renameBtn = document.querySelector(`.edit-title-btn[data-id="${docId}"]`);
            
            if (renameBtn) {
                renameBtn.disabled = false;
                renameBtn.innerHTML = '<i class="fas fa-edit me-1"></i>Rinomina';
            }
        }
    }
    
    /**
     * Finalizza il processo di rinomina
     * @param {HTMLElement} renameBtn - Pulsante di rinomina
     */
    function finishRenameProcessing(renameBtn) {
        try {
            state.isProcessing = false;
            
            if (renameBtn) {
                renameBtn.disabled = false;
                renameBtn.innerHTML = '<i class="fas fa-edit me-1"></i>Rinomina';
            }
        } catch (error) {
            console.error('Errore durante il completamento del rinomino:', error);
        }
    }
    
    /**
     * Gestisce il rinomino riuscito di un documento
     * @param {string} docId - ID del documento
     * @param {string} newTitle - Nuovo titolo
     */
    function handleDocumentRenamed(docId, newTitle) {
        try {
            // Aggiorna lo stato
            const docIndex = state.documents.findIndex(doc => doc.id === docId);
            if (docIndex !== -1) {
                state.documents[docIndex].title = newTitle;
            }
            
            // Aggiorna la UI
            const titleElement = document.querySelector(`.doc-card[data-id="${docId}"] .document-title`);
            const renameBtn = document.querySelector(`.edit-title-btn[data-id="${docId}"]`);
            const deleteBtn = document.querySelector(`.delete-doc-btn[data-id="${docId}"]`);
            
            if (titleElement) {
                titleElement.textContent = newTitle;
                
                // Effetto di evidenziazione
                titleElement.style.backgroundColor = '#ffff9e';
                
                setTimeout(() => {
                    titleElement.style.transition = 'background-color 1s';
                    titleElement.style.backgroundColor = '';
                }, 1000);
            }
            
            if (renameBtn) {
                renameBtn.dataset.title = newTitle;
            }
            
            if (deleteBtn) {
                deleteBtn.dataset.title = newTitle;
            }
            
            // Mostra conferma
            showNotification('Documento rinominato con successo', 'success');
        } catch (error) {
            console.error('Errore nella gestione del documento rinominato:', error);
        }
    }
    
    /**
     * Esporta le annotazioni
     * @param {string} format - Formato di esportazione (json, spacy)
     */
    function exportAnnotations(format) {
        try {
            if (state.isProcessing) {
                showNotification('Operazione già in corso, attendere...', 'warning');
                return;
            }
            
            // Mostra stato di caricamento
            state.isProcessing = true;
            const exportBtn = format === 'json' ? elements.exportJsonBtn : elements.exportSpacyBtn;
            
            if (exportBtn) {
                exportBtn.disabled = true;
                exportBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Esportazione...';
            }
            
            // Formatta il nome per la visualizzazione
            const formatName = format === 'spacy' ? 'formato spaCy' : 'JSON';
            
            // Avvia il download
            window.location.href = `/api/export_annotations?format=${format}&download=true`;
            
            // Mostra conferma
            setTimeout(() => {
                showNotification(`Esportazione in ${formatName} completata`, 'success');
                
                if (exportBtn) {
                    exportBtn.disabled = false;
                    exportBtn.innerHTML = format === 'json' ? 'Esporta JSON' : 'Esporta formato spaCy';
                }
                
                state.isProcessing = false;
            }, 1000);
        } catch (error) {
            console.error('Errore durante l\'esportazione delle annotazioni:', error);
            showNotification('Errore durante l\'esportazione', 'danger');
            
            // Ripristina lo stato
            state.isProcessing = false;
            const exportBtn = format === 'json' ? elements.exportJsonBtn : elements.exportSpacyBtn;
            
            if (exportBtn) {
                exportBtn.disabled = false;
                exportBtn.innerHTML = format === 'json' ? 'Esporta JSON' : 'Esporta formato spaCy';
            }
        }
    }
    
    /**
     * Addestra il modello NER
     */
    function trainModel() {
        try {
            if (state.isProcessing) {
                showNotification('Operazione già in corso, attendere...', 'warning');
                return;
            }
            
            if (!confirm('Vuoi esportare le annotazioni e preparare i dati per l\'addestramento del modello NER?')) {
                return;
            }
            
            // Mostra stato di caricamento
            state.isProcessing = true;
            
            if (elements.trainModelBtn) {
                elements.trainModelBtn.disabled = true;
                elements.trainModelBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Preparazione dati...';
            }
            
            // Usa APIClient se disponibile
            if (window.APIClient && window.APIClient.recognition) {
                APIClient.recognition.trainModel()
                    .then(data => {
                        handleModelTrained(data);
                    })
                    .catch(error => {
                        console.error('Errore durante la preparazione dei dati:', error);
                        showNotification('Errore durante la preparazione dei dati: ' + (error.message || 'Errore sconosciuto'), 'danger');
                    })
                    .finally(() => {
                        finishTrainingProcessing();
                    });
            } else {
                // Fallback con fetch
                fetch('/api/train_model', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'}
                })
                .then(response => {
                    if (!response.ok) {
                        throw new Error(`Errore HTTP: ${response.status}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.status === 'success') {
                        handleModelTrained(data);
                    } else {
                        throw new Error(data.message || 'Errore non specificato');
                    }
                })
                .catch(error => {
                    console.error('Errore durante la preparazione dei dati:', error);
                    showNotification('Errore durante la preparazione dei dati: ' + error.message, 'danger');
                })
                .finally(() => {
                    finishTrainingProcessing();
                });
            }
        } catch (error) {
            console.error('Errore durante l\'addestramento del modello:', error);
            showNotification('Errore durante l\'addestramento del modello', 'danger');
            finishTrainingProcessing();
        }
    }
    
    /**
     * Finalizza il processo di addestramento
     */
    function finishTrainingProcessing() {
        try {
            state.isProcessing = false;
            
            if (elements.trainModelBtn) {
                elements.trainModelBtn.disabled = false;
                elements.trainModelBtn.innerHTML = 'Prepara dati addestramento';
            }
        } catch (error) {
            console.error('Errore durante il completamento dell\'addestramento:', error);
        }
    }
    
    /**
     * Gestisce il completamento dell'addestramento
     * @param {Object} data - Dati del risultato
     */
    function handleModelTrained(data) {
        try {
            // Mostra le statistiche
            const statsContainer = document.getElementById('training-stats');
            
            if (statsContainer) {
                statsContainer.innerHTML = `
                    <div class="alert alert-success mt-3">
                        <h5><i class="fas fa-check-circle me-2"></i>Dati di addestramento preparati con successo</h5>
                        <p>
                            <strong>${data.count}</strong> documenti pronti per l'addestramento.<br>
                            File salvato in: <code>${data.file}</code>
                        </p>
                        <div class="mt-2">
                            <a href="/api/export_annotations?format=spacy&download=true" class="btn btn-outline-primary btn-sm">
                                <i class="fas fa-download me-2"></i>Scarica dati di addestramento
                            </a>
                        </div>
                    </div>
                `;
                
                statsContainer.classList.remove('d-none');
                statsContainer.scrollIntoView({ behavior: 'smooth' });
            }
            
            // Mostra conferma
            showNotification('Dati di addestramento esportati con successo', 'success');
        } catch (error) {
            console.error('Errore nella gestione del completamento dell\'addestramento:', error);
        }
    }
    
    /**
     * Filtra i documenti in base al testo di ricerca e alla categoria
     */
    function filterDocuments() {
        try {
            const searchTerm = elements.searchInput ? elements.searchInput.value.toLowerCase() : '';
            const categoryValue = elements.categoryFilter ? elements.categoryFilter.value : '';
            
            state.filterText = searchTerm;
            state.filterCategory = categoryValue;
            
            // Filtra i documenti nella UI
            const docCards = document.querySelectorAll('.doc-card');
            let visibleCount = 0;
            
            docCards.forEach(card => {
                const title = card.querySelector('.document-title').textContent.toLowerCase();
                const preview = card.querySelector('.document-preview')?.textContent.toLowerCase() || '';
                const metadata = card.querySelector('.document-metadata')?.textContent.toLowerCase() || '';
                
                // Determina se il documento corrisponde alla ricerca
                const matchesSearch = !searchTerm || 
                                     title.includes(searchTerm) || 
                                     preview.includes(searchTerm) ||
                                     metadata.includes(searchTerm);
                
                // TODO: implementare il filtro per categoria
                const matchesCategory = true;
                
                // Mostra/nascondi il documento
                const isVisible = matchesSearch && matchesCategory;
                const col = card.closest('.col');
                
                if (col) {
                    if (isVisible) {
                        col.style.display = '';
                        visibleCount++;
                    } else {
                        col.style.display = 'none';
                    }
                }
            });
            
            // Aggiorna il contatore nel badge
            updateFilteredCount(visibleCount, docCards.length);
            
            // Mostra/nascondi il messaggio "nessun documento"
            updateEmptyState(visibleCount, docCards.length);
        } catch (error) {
            console.error('Errore durante il filtraggio dei documenti:', error);
        }
    }
    
    /**
     * Aggiorna il conteggio dei documenti filtrati
     * @param {number} visibleCount - Numero di documenti visibili
     * @param {number} totalCount - Numero totale di documenti
     */
    function updateFilteredCount(visibleCount, totalCount) {
        try {
            if (!elements.documentCount) return;
            
            if (visibleCount === totalCount) {
                elements.documentCount.textContent = `${totalCount} Documenti`;
            } else {
                elements.documentCount.textContent = `${visibleCount}/${totalCount} Documenti`;
            }
        } catch (error) {
            console.error('Errore durante l\'aggiornamento del conteggio filtrato:', error);
        }
    }
    
    /**
     * Aggiorna lo stato vuoto
     * @param {number} visibleCount - Numero di documenti visibili
     * @param {number} totalCount - Numero totale di documenti
     */
    function updateEmptyState(visibleCount, totalCount) {
        try {
            // Mostra/nascondi lo stato vuoto appropriato
            const emptyState = elements.emptyState;
            const filterEmptyState = document.getElementById('filter-empty-state');
            
            if (!emptyState) return;
            
            if (totalCount === 0) {
                // Non ci sono documenti
                emptyState.classList.remove('d-none');
                if (filterEmptyState) filterEmptyState.classList.add('d-none');
            } else if (visibleCount === 0) {
                // Ci sono documenti, ma nessuno corrisponde al filtro
                emptyState.classList.add('d-none');
                
                if (!filterEmptyState) {
                    // Crea il messaggio di filtro vuoto se non esiste
                    const newFilterEmptyState = document.createElement('div');
                    newFilterEmptyState.id = 'filter-empty-state';
                    newFilterEmptyState.className = 'text-center py-5';
                    newFilterEmptyState.innerHTML = `
                        <i class="fas fa-filter text-muted" style="font-size: 4rem;"></i>
                        <h4 class="mt-3">Nessun risultato</h4>
                        <p class="text-muted">Nessun documento corrisponde ai criteri di ricerca "${state.filterText}"</p>
                        <button class="btn btn-outline-primary mt-3 clear-filters-btn">
                            <i class="fas fa-times me-2"></i>Cancella filtri
                        </button>
                    `;
                    
                    // Inserisci dopo lo stato vuoto
                    emptyState.parentNode.insertBefore(newFilterEmptyState, emptyState.nextSibling);
                } else {
                    // Aggiorna il messaggio
                    filterEmptyState.classList.remove('d-none');
                    const message = filterEmptyState.querySelector('p');
                    if (message) {
                        message.textContent = `Nessun documento corrisponde ai criteri di ricerca "${state.filterText}"`;
                    }
                }
            } else {
                // Ci sono documenti visibili
                emptyState.classList.add('d-none');
                if (filterEmptyState) filterEmptyState.classList.add('d-none');
            }
        } catch (error) {
            console.error('Errore durante l\'aggiornamento dello stato vuoto:', error);
        }
    }
    
    /**
     * Aggiorna il conteggio dei documenti
     */
    function updateDocumentCount() {
        try {
            if (!elements.documentCount) return;
            
            const docCount = state.documents.length;
            elements.documentCount.textContent = `${docCount} Documenti`;
        } catch (error) {
            console.error('Errore durante l\'aggiornamento del conteggio dei documenti:', error);
        }
    }
    
    /**
     * Formatta una data in formato italiano
     * @param {string|Date} date - Data da formattare
     * @returns {string} - Data formattata
     */
    function formatDate(date) {
        try {
            if (!date) return 'N/A';
            
            if (typeof date === 'string') {
                date = new Date(date);
            }
            
            if (isNaN(date.getTime())) {
                return 'Data non valida';
            }
            
            return date.toLocaleDateString('it-IT');
        } catch (error) {
            console.error('Errore durante la formattazione della data:', error);
            return 'N/A';
        }
    }
    
    /**
     * Funzione di debounce
     * @param {Function} func - Funzione da ritardare
     * @param {number} wait - Tempo di attesa in ms
     * @returns {Function} - Funzione con debounce
     */
    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }
    
    /**
     * Mostra una notifica
     * @param {string} message - Messaggio da mostrare
     * @param {string} type - Tipo di notifica (success, info, warning, danger)
     */
    function showNotification(message, type = 'info') {
        if (typeof window.showNotification === 'function') {
            window.showNotification(message, type);
        } else {
            console.log(`[${type}] ${message}`);
            
            // Mostra alert per errori
            if (type === 'danger' || type === 'warning') {
                alert(message);
            }
        }
    }
    
    // API pubblica
    return {
        initialize,
        loadDocumentsFromDOM,
        filterDocuments,
        exportAnnotations,
        trainModel,
        getState: () => Object.assign({}, state)
    };
})();

// Inizializzazione automatica
document.addEventListener('DOMContentLoaded', function() {
    DocumentManager.initialize();
    
    // Esponi globalmente per compatibilità con il codice esistente
    window.DocumentManager = DocumentManager;
    
    // Esponi funzioni globali esistenti
    window.deleteDocument = function(docId, docTitle) {
        return DocumentManager.deleteDocument(docId, docTitle);
    };
    
    window.renameDocument = function(docId, currentTitle) {
        return DocumentManager.renameDocument(docId, currentTitle);
    };
});