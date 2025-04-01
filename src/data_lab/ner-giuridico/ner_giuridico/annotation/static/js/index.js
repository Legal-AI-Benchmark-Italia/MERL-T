/**
 * index.js - Script migliorato per la gestione della home page dell'applicazione NER-Giuridico
 * 
 * Questo script gestisce le interazioni principali nella home page, inclusi caricamento documenti,
 * eliminazione, rinomina e esportazione dei dati.
 *
 * @version 2.0.0
 * @author NER-Giuridico Team
 */

// Home Page Manager
const HomeManager = {
    // Riferimenti a elementi DOM
    elements: {},
    
    // Stato dell'applicazione
    state: {
        documents: [],
        uploadInProgress: false,
        filterText: '',
        filterCategory: '',
        pendingOperations: 0
    },
    
    /**
     * Inizializza il gestore della home page
     */
    init: function() {
        console.info('🏠 Inizializzazione Home Manager...');
        
        // Seleziona gli elementi DOM principali
        this.elements = {
            uploadForm: document.getElementById('upload-form'),
            fileInput: document.getElementById('document-file'),
            documentsContainer: document.querySelector('.row-cols-1'),
            exportJsonBtn: document.getElementById('export-json'),
            exportSpacyBtn: document.getElementById('export-spacy'),
            searchInput: document.getElementById('search-documents'),
            categoryFilter: document.getElementById('category-filter'),
            trainModelBtn: document.getElementById('train-model-btn')
        };
        
        // Carica i documenti esistenti dal DOM
        this.loadDocumentsFromDOM();
        
        // Configura gli event handlers
        this.setupEventHandlers();
        
        console.info(`📋 Home Manager inizializzato: ${this.state.documents.length} documenti caricati`);
    },
    
    /**
     * Carica i documenti dal DOM e li memorizza nello stato
     */
    loadDocumentsFromDOM: function() {
        this.state.documents = [];
        
        // Trova tutti i card dei documenti
        const docCards = document.querySelectorAll('.doc-card');
        
        docCards.forEach(card => {
            const docId = card.dataset.id;
            const title = card.querySelector('.document-title').textContent;
            const preview = card.querySelector('.document-preview')?.textContent || '';
            const wordCount = card.querySelector('.document-metadata span:first-child')?.textContent.match(/\d+/) || 0;
            
            this.state.documents.push({
                id: docId,
                title: title,
                preview: preview,
                wordCount: parseInt(wordCount)
            });
        });
    },
    
    /**
     * Configura tutti gli event handlers
     */
    setupEventHandlers: function() {
        // Gestione del form di upload
        if (this.elements.uploadForm) {
            this.elements.uploadForm.addEventListener('submit', e => this.handleDocumentUpload(e));
        }
        
        // Gestione dei pulsanti di esportazione
        if (this.elements.exportJsonBtn) {
            this.elements.exportJsonBtn.addEventListener('click', () => this.exportAnnotations('json'));
        }
        
        if (this.elements.exportSpacyBtn) {
            this.elements.exportSpacyBtn.addEventListener('click', () => this.exportAnnotations('spacy'));
        }
        
        // Gestione del training del modello
        if (this.elements.trainModelBtn) {
            this.elements.trainModelBtn.addEventListener('click', () => this.trainModel());
        }
        
        // Gestione della ricerca e del filtro (con debounce)
        if (this.elements.searchInput) {
            const debouncedSearch = NERGiuridico.debounce(() => this.filterDocuments(), 300);
            this.elements.searchInput.addEventListener('input', debouncedSearch);
        }
        
        if (this.elements.categoryFilter) {
            this.elements.categoryFilter.addEventListener('change', () => this.filterDocuments());
        }
        
        // Gestione delegata dei click sui documenti
        document.addEventListener('click', e => {
            // Gestione dei pulsanti di eliminazione dei documenti
            if (e.target.closest('.delete-doc-btn')) {
                const btn = e.target.closest('.delete-doc-btn');
                const docId = btn.dataset.id;
                const docTitle = btn.dataset.title || docId;
                this.deleteDocument(docId, docTitle);
                return;
            }
            
            // Gestione dei pulsanti di rinomina dei documenti
            if (e.target.closest('.edit-title-btn')) {
                const btn = e.target.closest('.edit-title-btn');
                const docId = btn.dataset.id;
                const currentTitle = btn.dataset.title;
                this.renameDocument(docId, currentTitle);
                return;
            }
        });
    },
    
    /**
     * Gestisce l'upload di un documento
     * @param {Event} e - L'evento submit
     */
    handleDocumentUpload: function(e) {
        e.preventDefault();
        
        // Verifica che sia stato selezionato un file
        const file = this.elements.fileInput.files[0];
        if (!file) {
            NERGiuridico.showNotification('Seleziona un file da caricare', 'warning');
            return;
        }
        
        // Verifica che il file non superi i 10MB
        if (file.size > 10 * 1024 * 1024) {
            NERGiuridico.showNotification('Il file è troppo grande. Il limite è di 10MB.', 'danger');
            return;
        }
        
        // Imposta lo stato di caricamento
        this.state.uploadInProgress = true;
        this.startPendingOperation();
        
        // Aggiungi un indicatore di caricamento
        const submitButton = this.elements.uploadForm.querySelector('button[type="submit"]');
        NERGiuridico.showLoading(submitButton, 'Caricamento in corso...');
        
        // Prepara i dati per l'upload
        const formData = new FormData();
        formData.append('file', file);
        
        // Invia la richiesta
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
                // Aggiungi il documento all'array di documenti
                this.state.documents.push({
                    id: data.document.id,
                    title: data.document.title,
                    preview: data.document.text.substring(0, 150) + '...',
                    wordCount: data.document.word_count
                });
                
                // Mostra una notifica di successo
                NERGiuridico.showNotification('Documento caricato con successo', 'success');
                
                // Aggiungi il nuovo documento alla UI con animazione
                if (this.elements.documentsContainer) {
                    this.addDocumentCard(data.document);
                } else {
                    // Se non è possibile aggiungere il documento dinamicamente, ricarica la pagina
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                }
                
                // Resetta il form
                this.elements.uploadForm.reset();
            } else {
                NERGiuridico.showNotification('Errore: ' + data.message, 'danger');
            }
        })
        .catch(error => {
            console.error('Errore:', error);
            NERGiuridico.showNotification('Si è verificato un errore durante il caricamento', 'danger');
        })
        .finally(() => {
            this.state.uploadInProgress = false;
            this.endPendingOperation();
            NERGiuridico.hideLoading(submitButton);
        });
    },
    
    /**
     * Aggiunge un nuovo documento card alla UI
     * @param {Object} document - Il documento da aggiungere
     */
    addDocumentCard: function(document) {
        // Crea un nuovo elemento col
        const col = document.createElement('div');
        col.className = 'col fade-in';
        
        // Data formattata
        const formattedDate = document.date_created ? NERGiuridico.formatDate(document.date_created) : 'N/A';
        
        // Crea il contenuto HTML
        col.innerHTML = `
            <div class="card h-100 doc-card" data-id="${document.id}">
                <div class="card-header bg-light">
                    <h5 class="card-title document-title mb-0">${document.title}</h5>
                </div>
                <div class="card-body">
                    <p class="card-text document-preview text-truncate">${document.text.substring(0, 150)}...</p>
                    <div class="document-metadata text-muted small">
                        <span><i class="fas fa-file-word me-1"></i>${document.word_count} parole</span>
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
        
        // Aggiungi l'elemento al container
        if (this.elements.documentsContainer) {
            this.elements.documentsContainer.prepend(col);
            
            // Nascondi il messaggio "nessun documento" se esiste
            const emptyState = document.querySelector('.text-center.py-5');
            if (emptyState) {
                emptyState.classList.add('d-none');
            }
            
            // Aggiungi una breve animazione
            setTimeout(() => {
                col.querySelector('.card').classList.add('highlight');
            }, 100);
            
            setTimeout(() => {
                col.querySelector('.card').classList.remove('highlight');
            }, 2000);
        }
    },
    
    /**
     * Elimina un documento
     * @param {string} docId - L'ID del documento da eliminare
     * @param {string} docTitle - Il titolo del documento
     */
    deleteDocument: function(docId, docTitle) {
        // Usa la funzione di conferma centralizzata
        NERGiuridico.showConfirmation(
            'Elimina documento',
            `Sei sicuro di voler eliminare il documento "${docTitle || docId}" e tutte le sue annotazioni?`,
            () => {
                this.startPendingOperation();
                
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
                        NERGiuridico.showNotification(data.message || 'Documento eliminato con successo', 'success');
                        
                        // Rimuovi il documento dall'array
                        this.state.documents = this.state.documents.filter(doc => doc.id !== docId);
                        
                        // Rimuovi il documento dalla UI con animazione
                        const docCard = document.querySelector(`.doc-card[data-id="${docId}"]`);
                        if (docCard) {
                            const col = docCard.closest('.col');
                            
                            // Aggiungi classe per animazione di uscita
                            col.classList.add('fade-out');
                            
                            // Rimuovi l'elemento dopo l'animazione
                            setTimeout(() => {
                                col.remove();
                                
                                // Se non ci sono più documenti, mostra il messaggio "nessun documento"
                                if (this.state.documents.length === 0) {
                                    const emptyState = document.querySelector('.text-center.py-5');
                                    if (emptyState) {
                                        emptyState.classList.remove('d-none');
                                    } else {
                                        // Se non è possibile aggiornare la UI, ricarica la pagina
                                        window.location.reload();
                                    }
                                }
                            }, 500);
                        } else {
                            // Se non è possibile rimuovere il documento dalla UI, ricarica la pagina
                            setTimeout(() => {
                                window.location.reload();
                            }, 1500);
                        }
                    } else {
                        NERGiuridico.showNotification('Errore: ' + data.message, 'danger');
                    }
                })
                .catch(error => {
                    console.error('Errore:', error);
                    NERGiuridico.showNotification('Si è verificato un errore durante l\'eliminazione', 'danger');
                })
                .finally(() => {
                    this.endPendingOperation();
                });
            },
            'Elimina',
            'btn-danger'
        );
    },
    
    /**
     * Rinomina un documento
     * @param {string} docId - L'ID del documento da rinominare
     * @param {string} currentTitle - Il titolo corrente del documento
     */
    renameDocument: function(docId, currentTitle) {
        // Usa un prompt o un modale per ottenere il nuovo titolo
        const newTitle = prompt('Inserisci il nuovo titolo del documento', currentTitle);
        
        if (!newTitle || newTitle === currentTitle) {
            return;
        }
        
        this.startPendingOperation();
        
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
                // Aggiorna il documento nell'array
                const docIndex = this.state.documents.findIndex(doc => doc.id === docId);
                if (docIndex !== -1) {
                    this.state.documents[docIndex].title = newTitle;
                }
                
                // Aggiorna la UI
                const titleElement = document.querySelector(`.doc-card[data-id="${docId}"] .document-title`);
                const renameBtn = document.querySelector(`.edit-title-btn[data-id="${docId}"]`);
                
                if (titleElement) {
                    titleElement.textContent = newTitle;
                    
                    // Aggiungi un'animazione di conferma
                    titleElement.classList.add('save-animation');
                    setTimeout(() => {
                        titleElement.classList.remove('save-animation');
                    }, 1000);
                }
                
                if (renameBtn) {
                    renameBtn.dataset.title = newTitle;
                }
                
                NERGiuridico.showNotification('Titolo aggiornato con successo', 'success');
            } else {
                NERGiuridico.showNotification('Errore: ' + data.message, 'danger');
            }
        })
        .catch(error => {
            console.error('Errore:', error);
            NERGiuridico.showNotification('Si è verificato un errore durante l\'aggiornamento', 'danger');
        })
        .finally(() => {
            this.endPendingOperation();
        });
    },
    
    /**
     * Esporta le annotazioni
     * @param {string} format - Il formato di esportazione ('json' o 'spacy')
     */
    exportAnnotations: function(format) {
        const formatName = format === 'spacy' ? 'formato spaCy' : 'JSON';
        this.startPendingOperation();
        
        // Aggiorna i pulsanti
        const exportBtn = format === 'spacy' ? this.elements.exportSpacyBtn : this.elements.exportJsonBtn;
        if (exportBtn) {
            NERGiuridico.showLoading(exportBtn, `Esportazione in ${formatName}...`);
        }
        
        // Reindirizza alla URL di download
        window.location.href = `/api/export_annotations?format=${format}&download=true`;
        
        // Mostra notifica
        setTimeout(() => {
            NERGiuridico.showNotification(`Esportazione in ${formatName} completata`, 'success');
            this.endPendingOperation();
            
            if (exportBtn) {
                NERGiuridico.hideLoading(exportBtn);
            }
        }, 1000);
    },
    
    /**
     * Addestra il modello NER con le annotazioni
     */
    trainModel: function() {
        // Usa la funzione di conferma centralizzata
        NERGiuridico.showConfirmation(
            'Addestra modello NER',
            'Vuoi esportare le annotazioni e preparare i dati per l\'addestramento del modello NER? Questo processo preparerà un file di dati formatato per l\'addestramento.',
            () => {
                this.startPendingOperation();
                
                // Mostra stato di caricamento sul pulsante
                if (this.elements.trainModelBtn) {
                    NERGiuridico.showLoading(this.elements.trainModelBtn, 'Preparazione dati...');
                }
                
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
                        // Mostra statistiche
                        const statsHtml = `
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
                        
                        // Aggiungi le statistiche alla pagina
                        const statsContainer = document.getElementById('training-stats');
                        if (statsContainer) {
                            statsContainer.innerHTML = statsHtml;
                            statsContainer.classList.remove('d-none');
                            
                            // Scorri fino alle statistiche
                            statsContainer.scrollIntoView({behavior: 'smooth', block: 'center'});
                        }
                        
                        NERGiuridico.showNotification(data.message || 'Dati di addestramento esportati con successo', 'success');
                    } else {
                        NERGiuridico.showNotification('Errore: ' + data.message, 'danger');
                    }
                })
                .catch(error => {
                    console.error('Errore:', error);
                    NERGiuridico.showNotification('Si è verificato un errore durante la preparazione dei dati', 'danger');
                })
                .finally(() => {
                    this.endPendingOperation();
                    
                    if (this.elements.trainModelBtn) {
                        NERGiuridico.hideLoading(this.elements.trainModelBtn);
                    }
                });
            },
            'Procedi',
            'btn-primary'
        );
    },
    
    /**
     * Filtra i documenti in base al testo di ricerca e alla categoria
     */
    filterDocuments: function() {
        if (!this.elements.searchInput && !this.elements.categoryFilter) return;
        
        const searchTerm = this.elements.searchInput ? this.elements.searchInput.value.toLowerCase() : '';
        const category = this.elements.categoryFilter ? this.elements.categoryFilter.value : '';
        
        this.state.filterText = searchTerm;
        this.state.filterCategory = category;
        
        const docCards = document.querySelectorAll('.doc-card');
        let visibleCount = 0;
        
        docCards.forEach(card => {
            const title = card.querySelector('.document-title').textContent.toLowerCase();
            const preview = card.querySelector('.document-preview').textContent.toLowerCase();
            const metadata = card.querySelector('.document-metadata').textContent.toLowerCase();
            
            // Determina se il documento corrisponde alla ricerca
            const matchesSearch = searchTerm === '' || 
                                 title.includes(searchTerm) || 
                                 preview.includes(searchTerm) ||
                                 metadata.includes(searchTerm);
            
            // Determina se il documento corrisponde alla categoria
            // Per ora, non implementiamo il filtro per categoria
            const matchesCategory = category === '' || true;
            
            const isVisible = matchesSearch && matchesCategory;
            
            // Mostra/nascondi il documento
            const col = card.closest('.col');
            if (col) {
                if (isVisible) {
                    col.classList.remove('d-none');
                    visibleCount++;
                } else {
                    col.classList.add('d-none');
                }
            }
        });
        
        // Aggiorna il contatore
        const totalCount = docCards.length;
        const counter = document.querySelector('.badge.bg-primary.rounded-pill');
        
        if (counter) {
            counter.textContent = visibleCount === totalCount ? 
                                 `${totalCount} Documenti` : 
                                 `${visibleCount}/${totalCount} Documenti`;
        }
        
        // Mostra/nascondi il messaggio "nessun documento"
        const emptyState = document.querySelector('.text-center.py-5');
        const filterEmptyState = document.getElementById('filter-empty-state');
        
        if (emptyState && filterEmptyState) {
            if (totalCount === 0) {
                // Non ci sono documenti
                emptyState.classList.remove('d-none');
                filterEmptyState.classList.add('d-none');
            } else if (visibleCount === 0) {
                // Ci sono documenti, ma nessuno corrisponde al filtro
                emptyState.classList.add('d-none');
                filterEmptyState.classList.remove('d-none');
                
                // Aggiorna il messaggio
                const message = filterEmptyState.querySelector('p');
                if (message) {
                    message.textContent = `Nessun documento corrisponde ai criteri di ricerca "${searchTerm}"`;
                }
            } else {
                // Ci sono documenti visibili
                emptyState.classList.add('d-none');
                filterEmptyState.classList.add('d-none');
            }
        }
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
    }
};

// Inizializzazione all'avvio
document.addEventListener('DOMContentLoaded', function() {
    // Inizializza il gestore della home page
    HomeManager.init();
    
    // Esponi funzioni per compatibilità con il codice esistente
    window.deleteDocument = (docId, docTitle) => HomeManager.deleteDocument(docId, docTitle);
    window.renameDocument = (docId, currentTitle) => HomeManager.renameDocument(docId, currentTitle);
    
    // Aggiungi un elemento per il messaggio di filtro vuoto se non esiste
    if (!document.getElementById('filter-empty-state') && HomeManager.elements.documentsContainer) {
        const filterEmptyState = document.createElement('div');
        filterEmptyState.id = 'filter-empty-state';
        filterEmptyState.className = 'text-center py-5 d-none';
        filterEmptyState.innerHTML = `
            <i class="fas fa-filter text-muted" style="font-size: 4rem;"></i>
            <h4 class="mt-3">Nessun risultato</h4>
            <p class="text-muted">Nessun documento corrisponde ai criteri di ricerca</p>
            <button class="btn btn-outline-primary mt-3" onclick="document.getElementById('search-documents').value = ''; HomeManager.filterDocuments();">
                <i class="fas fa-times me-2"></i>Cancella filtri
            </button>
        `;
        
        // Inserisci dopo il container dei documenti
        HomeManager.elements.documentsContainer.parentNode.insertBefore(
            filterEmptyState, 
            HomeManager.elements.documentsContainer.nextSibling
        );
    }
    
    // Aggiungi una container per le statistiche di training se non esiste
    if (!document.getElementById('training-stats') && document.querySelector('.card:last-child')) {
        const trainingStats = document.createElement('div');
        trainingStats.id = 'training-stats';
        trainingStats.className = 'mt-4 d-none';
        
        // Inserisci dopo l'ultima card
        const lastCard = document.querySelector('.card:last-child');
        lastCard.parentNode.insertBefore(trainingStats, lastCard.nextSibling);
    }
});