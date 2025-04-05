/**
 * indexPage.js - Versione migliorata con gestione multipla dei documenti
 */
import { api } from './api.js';
import { showNotification, showLoading, hideLoading } from './ui.js';

// Stato dell'applicazione
let selectedDocIds = new Set();
let currentViewMode = 'grid';
let currentSort = 'date-desc';
let documentsData = [];
let bulkDeleteModalInstance = null;
let renameModalInstance = null;
let confirmDeleteModalInstance = null;
let docToDeleteId = null;
let docToDeleteTitle = '';

// Inizializzazione della pagina
export function initIndexPage() {
    console.log('Initializing Index Page with enhanced document management...');
    
    // Cache dei riferimenti DOM
    const documentList = document.getElementById('document-list');
    const bulkActionsToolbar = document.querySelector('.bulk-actions-toolbar');
    const selectedCountEl = document.getElementById('selected-count');
    const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
    const bulkDownloadBtn = document.getElementById('bulk-download-btn');
    const selectAllBtn = document.getElementById('select-all-btn');
    const deselectAllBtn = document.getElementById('deselect-all-btn');
    const searchInput = document.getElementById('document-search');
    const viewModeBtns = document.querySelectorAll('.view-mode-btn');
    const sortOptions = document.querySelectorAll('.sort-option');
    
    // Inizializza modali
    initRenameModal();
    initConfirmDeleteModal();
    initBulkDeleteModal();
    
    // Inizializza altre funzionalità
    handleUpload();
    handleDocumentActions();
    handleExport();
    
    // Carica i dati dei documenti iniziali
    loadInitialDocumentsData();
    
    // Event listeners per la gestione dei documenti multipli
    if (documentList) {
        // Delegazione eventi per i checkbox
        documentList.addEventListener('change', function(e) {
            if (e.target.classList.contains('doc-checkbox')) {
                handleCheckboxChange(e.target);
            }
        });
        
        // Delegazione eventi per click sulla card (selezione intera card)
        documentList.addEventListener('click', function(e) {
            // Verifica che il click non sia su un pulsante o un link
            if (!e.target.closest('a') && !e.target.closest('button') && !e.target.closest('input[type="checkbox"]')) {
                const card = e.target.closest('.doc-card-col');
                if (card) {
                    const checkbox = card.querySelector('.doc-checkbox');
                    if (checkbox) {
                        checkbox.checked = !checkbox.checked;
                        handleCheckboxChange(checkbox);
                    }
                }
            }
        });
    }
    
    // Bulk actions
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', function() {
            const checkboxes = document.querySelectorAll('.doc-checkbox');
            checkboxes.forEach(checkbox => {
                checkbox.checked = true;
                selectedDocIds.add(checkbox.value);
            });
            updateBulkActionsState();
        });
    }
    
    if (deselectAllBtn) {
        deselectAllBtn.addEventListener('click', function() {
            const checkboxes = document.querySelectorAll('.doc-checkbox');
            checkboxes.forEach(checkbox => {
                checkbox.checked = false;
            });
            selectedDocIds.clear();
            updateBulkActionsState();
        });
    }
    
    if (bulkDeleteBtn) {
        bulkDeleteBtn.addEventListener('click', function() {
            showBulkDeleteConfirmation();
        });
    }
    
    if (bulkDownloadBtn) {
        bulkDownloadBtn.addEventListener('click', function() {
            // La funzionalità di download sarebbe implementata qui
            showNotification('Funzionalità di download in fase di sviluppo', 'info');
        });
    }
    
    // Ricerca documenti
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            filterDocuments();
        });
    }
    
    // Switcher vista (griglia/lista)
    viewModeBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const viewMode = this.dataset.view;
            if (viewMode !== currentViewMode) {
                setViewMode(viewMode);
                
                // Aggiorna lo stato active dei bottoni
                viewModeBtns.forEach(b => b.classList.remove('active'));
                this.classList.add('active');
            }
        });
    });
    
    // Ordinamento
    sortOptions.forEach(option => {
        option.addEventListener('click', function() {
            const sortBy = this.dataset.sort;
            if (sortBy !== currentSort) {
                currentSort = sortBy;
                renderSortedDocuments();
            }
        });
    });
}

// Funzione per caricare i dati iniziali dei documenti
function loadInitialDocumentsData() {
    const docCards = document.querySelectorAll('.doc-card-col');
    documentsData = Array.from(docCards).map(card => {
        return {
            id: card.dataset.docId,
            title: card.dataset.docTitle,
            date: card.dataset.docDate,
            size: parseInt(card.dataset.docSize || 0),
            element: card
        };
    });
    
    // Ordina i documenti in base all'ordinamento corrente
    renderSortedDocuments();
}

// Funzione per gestire il cambio di stato dei checkbox
function handleCheckboxChange(checkbox) {
    const docId = checkbox.value;
    
    if (checkbox.checked) {
        selectedDocIds.add(docId);
    } else {
        selectedDocIds.delete(docId);
    }
    
    updateBulkActionsState();
}

// Aggiorna lo stato delle azioni bulk in base alle selezioni
function updateBulkActionsState() {
    const bulkActionsToolbar = document.querySelector('.bulk-actions-toolbar');
    const selectedCountEl = document.getElementById('selected-count');
    const bulkDeleteBtn = document.getElementById('bulk-delete-btn');
    const bulkDownloadBtn = document.getElementById('bulk-download-btn');
    
    if (selectedDocIds.size > 0) {
        bulkActionsToolbar?.classList.remove('d-none');
        bulkDeleteBtn.disabled = false;
        bulkDownloadBtn.disabled = false;
        
        if (selectedCountEl) {
            selectedCountEl.textContent = selectedDocIds.size;
        }
        
        // Evidenzia le card selezionate
        document.querySelectorAll('.doc-card-col').forEach(card => {
            const docId = card.dataset.docId;
            if (selectedDocIds.has(docId)) {
                card.querySelector('.card').classList.add('border-primary');
            } else {
                card.querySelector('.card').classList.remove('border-primary');
            }
        });
    } else {
        bulkActionsToolbar?.classList.add('d-none');
        bulkDeleteBtn.disabled = true;
        bulkDownloadBtn.disabled = true;
    }
}

// Inizializzazione del modal per l'eliminazione in blocco
function initBulkDeleteModal() {
    const bulkDeleteModalEl = document.getElementById('bulkDeleteModal');
    if (!bulkDeleteModalEl) return;
    
    bulkDeleteModalInstance = new bootstrap.Modal(bulkDeleteModalEl);
    
    const confirmBulkDeleteBtn = document.getElementById('confirm-bulk-delete-btn');
    confirmBulkDeleteBtn.addEventListener('click', async function() {
        await handleBulkDelete();
    });
}

// Visualizza il modal di conferma per l'eliminazione in blocco
function showBulkDeleteConfirmation() {
    if (!bulkDeleteModalInstance) return;
    
    const bulkDeleteCount = document.getElementById('bulk-delete-count');
    if (bulkDeleteCount) {
        bulkDeleteCount.textContent = selectedDocIds.size;
    }
    
    bulkDeleteModalInstance.show();
}

// Gestisce l'eliminazione multipla dei documenti
async function handleBulkDelete() {
    if (selectedDocIds.size === 0) return;
    
    const confirmBtn = document.getElementById('confirm-bulk-delete-btn');
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Eliminazione in corso...';
    
    showLoading();
    
    try {
        // Chiamata all'API per eliminazione in blocco
        const result = await api.bulkDeleteDocuments(Array.from(selectedDocIds));
        
        if (result.status === 'success') {
            // Rimuovi gli elementi dal DOM
            for (const docId of selectedDocIds) {
                const cardToRemove = document.querySelector(`.doc-card-col[data-doc-id="${docId}"]`);
                if (cardToRemove) {
                    cardToRemove.remove();
                }
            }
            
            // Aggiorna il contatore visualizzato
            const documentCountEl = document.getElementById('document-count');
            if (documentCountEl) {
                const currentCount = parseInt(documentCountEl.textContent);
                const newCount = Math.max(0, currentCount - selectedDocIds.size);
                documentCountEl.textContent = `${newCount} Documenti`;
            }
            
            showNotification(`${selectedDocIds.size} documenti eliminati con successo.`, 'success');
            
            // Aggiorna la lista documenti in memoria
            documentsData = documentsData.filter(doc => !selectedDocIds.has(doc.id));
            
            // Reset selezioni
            selectedDocIds.clear();
            updateBulkActionsState();
            
            // Chiudi il modal
            bulkDeleteModalInstance.hide();
        } else {
            throw new Error(result.message || "Errore durante l'eliminazione in blocco");
        }
    } catch (error) {
        console.error("Errore durante l'eliminazione in blocco:", error);
        showNotification(`Errore: ${error.message}`, 'danger');
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = '<i class="fas fa-trash-alt me-1"></i>Elimina Documenti';
        hideLoading();
    }
}

// Cambia la modalità di visualizzazione tra griglia e lista
function setViewMode(mode) {
    const documentList = document.getElementById('document-list');
    if (!documentList) return;
    
    currentViewMode = mode;
    
    if (mode === 'grid') {
        documentList.classList.remove('list-view');
        documentList.classList.add('row', 'row-cols-1', 'row-cols-md-2', 'row-cols-lg-3', 'g-4');
        
        // Ripristina le card alla visualizzazione normale
        document.querySelectorAll('.doc-card-col').forEach(card => {
            card.classList.remove('col-12');
            card.classList.add('col');
            
            // Ripristina altezza automatica
            const cardBody = card.querySelector('.card-body');
            if (cardBody) {
                cardBody.style.maxHeight = '';
            }
        });
    } else if (mode === 'list') {
        documentList.classList.add('list-view');
        documentList.classList.remove('row-cols-md-2', 'row-cols-lg-3', 'g-4');
        
        // Trasforma le card in elementi lista
        document.querySelectorAll('.doc-card-col').forEach(card => {
            card.classList.remove('col');
            card.classList.add('col-12', 'mb-2');
            
            // Limita l'altezza per la visualizzazione lista
            const cardBody = card.querySelector('.card-body');
            if (cardBody) {
                cardBody.style.maxHeight = '100px';
                cardBody.style.overflow = 'hidden';
            }
        });
    }
}

// Filtra i documenti in base al testo di ricerca
function filterDocuments() {
    const searchInput = document.getElementById('document-search');
    if (!searchInput) return;
    
    const searchText = searchInput.value.toLowerCase();
    
    document.querySelectorAll('.doc-card-col').forEach(card => {
        const title = card.dataset.docTitle?.toLowerCase() || '';
        const docId = card.dataset.docId;
        
        // Cerca nel titolo (eventualmente estendere a contenuto o metadati)
        if (title.includes(searchText) || !searchText) {
            card.classList.remove('d-none');
        } else {
            card.classList.add('d-none');
            
            // Se era selezionato, deselezionalo
            if (selectedDocIds.has(docId)) {
                selectedDocIds.delete(docId);
                const checkbox = card.querySelector('.doc-checkbox');
                if (checkbox) {
                    checkbox.checked = false;
                }
            }
        }
    });
    
    // Aggiorna lo stato delle azioni bulk
    updateBulkActionsState();
}

// Ordina e visualizza i documenti in base al criterio selezionato
function renderSortedDocuments() {
    // Ordina i dati in memoria
    const sortedData = [...documentsData].sort((a, b) => {
        switch(currentSort) {
            case 'title-asc':
                return a.title.localeCompare(b.title);
            case 'title-desc':
                return b.title.localeCompare(a.title);
            case 'date-asc':
                return new Date(a.date) - new Date(b.date);
            case 'date-desc':
                return new Date(b.date) - new Date(a.date);
            case 'size-asc':
                return a.size - b.size;
            case 'size-desc':
                return b.size - a.size;
            default:
                return 0;
        }
    });
    
    // Aggiorna l'ordine nel DOM
    const documentList = document.getElementById('document-list');
    if (!documentList) return;
    
    sortedData.forEach(doc => {
        documentList.appendChild(doc.element);
    });
}

// Aggiorna la lista dei documenti recuperandoli dall'API
async function refreshDocumentList() {
    try {
        showLoading();
        
        // Prova a usare l'API per ottenere i documenti aggiornati
        const response = await api.getDocuments();
        
        if (response && response.status === 'success') {
            // Aggiorna il contatore
            const documentCountEl = document.getElementById('document-count');
            if (documentCountEl) {
                documentCountEl.textContent = `${response.documents.length} Documenti`;
            }
            
            const documentList = document.getElementById('document-list');
            if (!documentList) {
                hideLoading();
                return;
            }
            
            // Se non ci sono documenti, mostra il messaggio vuoto
            if (!response.documents || response.documents.length === 0) {
                documentList.innerHTML = `
                    <div class="col-12 text-center py-5 text-muted">
                        <i class="fas fa-file-circle-xmark fa-3x mb-3"></i>
                        <h5 class="mb-1">Nessun documento disponibile</h5>
                        <p>Carica un documento per iniziare.</p>
                    </div>
                `;
                hideLoading();
                return;
            }
            
            // Prepara il contenuto HTML per i documenti
            let html = '';
            
            response.documents.forEach(doc => {
                // Estrai il nome del file senza percorso della cartella
                let displayTitle = doc.title;
                if (doc.metadata && doc.metadata.relative_path) {
                    const pathParts = doc.metadata.relative_path.split('/');
                    displayTitle = pathParts[pathParts.length - 1];
                }
                
                html += `
                <div class="col doc-card-col" data-doc-id="${doc.id}" data-doc-title="${doc.title}" 
                     data-doc-date="${doc.date_created}" data-doc-size="${doc.word_count || 0}">
                    <div class="card h-100 doc-card">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <div class="form-check">
                                <input class="form-check-input doc-checkbox" type="checkbox" value="${doc.id}" id="checkbox-${doc.id}">
                                <label class="form-check-label" for="checkbox-${doc.id}">
                                    <h6 class="card-title document-title mb-0 ms-2">${displayTitle}</h6>
                                </label>
                            </div>
                        </div>
                        <div class="card-body pb-0">
                            <p class="card-text document-preview mb-2">${doc.text ? doc.text.substring(0, 120) + '...' : ''}</p>
                            <div class="document-metadata text-muted small mb-2">
                                <span><i class="fas fa-file-word me-1"></i>${doc.word_count || 0} parole</span>
                                ${doc.date_created ? 
                                  `<span><i class="fas fa-calendar-alt me-1"></i>${doc.date_created.split('T')[0]}</span>` : ''}
                                ${doc.metadata && doc.metadata.relative_path ? 
                                  `<div class="mt-1 text-truncate">
                                      <i class="fas fa-folder me-1"></i>${doc.metadata.relative_path}
                                   </div>` : ''}
                            </div>
                        </div>
                        <div class="card-footer">
                            <div class="btn-group w-100" role="group">
                                <a href="/annotate/${doc.id}" class="btn btn-sm btn-success">
                                    <i class="fas fa-tag"></i> Annota
                                </a>
                                <button class="btn btn-sm btn-outline-secondary rename-doc-btn" data-doc-id="${doc.id}" data-doc-title="${displayTitle}">
                                    <i class="fas fa-edit"></i> Rinomina
                                </button>
                                <button class="btn btn-sm btn-outline-danger delete-doc-btn" data-doc-id="${doc.id}" data-doc-title="${displayTitle}">
                                    <i class="fas fa-trash-alt"></i> Elimina
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                `;
            });
            
            // Aggiorna il DOM
            documentList.innerHTML = html;
            
            // Ricarica i dati dei documenti in memoria
            loadInitialDocumentsData();
            
            // Applica la modalità di visualizzazione corrente
            setViewMode(currentViewMode);
            
        } else {
            // Gestione errori API
            showNotification('Errore nel caricamento dei documenti dal server', 'danger');
        }
    } catch (error) {
        console.error('Error refreshing document list:', error);
        showNotification(`Errore: ${error.message}`, 'danger');
    } finally {
        hideLoading();
    }
}

function initRenameModal() {
    const renameModalEl = document.getElementById('renameModal');
    if (!renameModalEl) return;
    renameModalInstance = new bootstrap.Modal(renameModalEl);

    const form = document.getElementById('rename-form');
    const docIdInput = document.getElementById('rename-doc-id');
    const titleInput = document.getElementById('new-doc-title');
    const saveBtn = document.getElementById('save-rename-btn');

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const docId = docIdInput.value;
        const newTitle = titleInput.value.trim();
        if (!docId || !newTitle) return;

        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Salvataggio...';
        showLoading();

        try {
            await api.updateDocument(docId, { title: newTitle });
            // Update UI and documentsData
            const cardTitle = document.querySelector(`.doc-card-col[data-doc-id="${docId}"] .document-title`);
            const renameBtn = document.querySelector(`.doc-card-col[data-doc-id="${docId}"] .rename-doc-btn`);
            const cardElement = document.querySelector(`.doc-card-col[data-doc-id="${docId}"]`);
            
            if (cardTitle) cardTitle.textContent = newTitle;
            if (renameBtn) renameBtn.dataset.docTitle = newTitle;
            if (cardElement) cardElement.dataset.docTitle = newTitle;
            
            // Aggiorna anche i dati in memoria
            const docIndex = documentsData.findIndex(doc => doc.id === docId);
            if (docIndex !== -1) {
                documentsData[docIndex].title = newTitle;
            }

            showNotification('Documento rinominato con successo.', 'success');
            renameModalInstance.hide();
        } catch (error) {
            showNotification(`Errore durante la rinomina: ${error.message}`, 'danger');
        } finally {
            saveBtn.disabled = false;
            saveBtn.innerHTML = 'Salva';
            hideLoading();
        }
    });
}

function initConfirmDeleteModal() {
    const confirmModalEl = document.getElementById('confirmDeleteModal');
    if (!confirmModalEl) return;
    confirmDeleteModalInstance = new bootstrap.Modal(confirmModalEl);

    const confirmBtn = document.getElementById('confirm-delete-btn');
    confirmBtn.addEventListener('click', async () => {
        if (!docToDeleteId) return;

        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Eliminazione...';
        showLoading();

        try {
            await api.deleteDocument(docToDeleteId);
            // Rimuovi card dal DOM e dai dati in memoria
            const cardToRemove = document.querySelector(`.doc-card-col[data-doc-id="${docToDeleteId}"]`);
            if (cardToRemove) {
                cardToRemove.remove();
            }
            
            // Rimuovi dai dati in memoria
            documentsData = documentsData.filter(doc => doc.id !== docToDeleteId);
            
            // Aggiorna il contatore
            const documentCountEl = document.getElementById('document-count');
            if (documentCountEl) {
                const currentCount = parseInt(documentCountEl.textContent);
                documentCountEl.textContent = `${Math.max(0, currentCount - 1)} Documenti`;
            }
            
            showNotification(`Documento "${docToDeleteTitle}" eliminato con successo.`, 'success');
            confirmDeleteModalInstance.hide();

        } catch (error) {
            showNotification(`Errore durante l'eliminazione: ${error.message}`, 'danger');
        } finally {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = 'Elimina';
            docToDeleteId = null;
            docToDeleteTitle = '';
            hideLoading();
        }
    });
}

function handleDocumentActions() {
    const docList = document.getElementById('document-list');
    if (!docList) return;

    docList.addEventListener('click', (event) => {
        const target = event.target;
        const deleteBtn = target.closest('.delete-doc-btn');
        const renameBtn = target.closest('.rename-doc-btn');

        if (deleteBtn && confirmDeleteModalInstance) {
            docToDeleteId = deleteBtn.dataset.docId;
            docToDeleteTitle = deleteBtn.dataset.docTitle || `ID: ${docToDeleteId}`;
            document.getElementById('doc-to-delete-title').textContent = docToDeleteTitle;
            confirmDeleteModalInstance.show();
        } else if (renameBtn && renameModalInstance) {
            const docId = renameBtn.dataset.docId;
            const currentTitle = renameBtn.dataset.docTitle;
            document.getElementById('rename-doc-id').value = docId;
            document.getElementById('new-doc-title').value = currentTitle;
            renameModalInstance.show();
        }
    });
}

function handleUpload() {
    const form = document.getElementById('upload-form');
    const fileInput = document.getElementById('document-files');
    const dropArea = document.getElementById('drop-area');
    const progressContainer = document.getElementById('upload-progress-container');
    const totalProgressBar = document.getElementById('total-progress-bar');
    const fileListEl = document.getElementById('file-list');
    const submitBtn = form?.querySelector('button[type="submit"]');
    const processFolder = document.getElementById('process-folder-structure');
    
    // Add dashed border to drop area
    if (dropArea) {
        dropArea.style.borderStyle = 'dashed';
        dropArea.style.borderWidth = '2px';
        dropArea.style.borderColor = '#ccc';
    }
    
    // Function to update UI during upload
    function updateProgress(processed, total, currentFile = null) {
        const percentage = Math.round((processed / total) * 100);
        if (totalProgressBar) {
            totalProgressBar.style.width = `${percentage}%`;
            totalProgressBar.textContent = `${percentage}%`;
            totalProgressBar.setAttribute('aria-valuenow', percentage);
        }
        
        // If current file is provided, update its status in the list
        if (currentFile && fileListEl) {
            const fileId = `file-${currentFile.name.replace(/\W/g, '')}`;
            const fileEl = document.getElementById(fileId);
            if (fileEl) {
                fileEl.querySelector('.file-status').innerHTML = `<span class="text-success">Caricato</span>`;
            }
        }
    }
    
    // Show selected files
    function showSelectedFiles(files) {
        if (files.length > 0 && fileListEl) {
            progressContainer?.classList.remove('d-none');
            fileListEl.innerHTML = '';
            
            files.forEach(file => {
                const fileId = `file-${file.name.replace(/\W/g, '')}`;
                const relativePath = file.relativePath ? file.relativePath : file.name;
                
                const fileItem = document.createElement('div');
                fileItem.id = fileId;
                fileItem.className = 'mb-1 d-flex justify-content-between';
                fileItem.innerHTML = `
                    <div class="text-truncate" title="${relativePath}">${relativePath}</div>
                    <div class="file-status"><span class="text-muted">In attesa...</span></div>
                `;
                fileListEl.appendChild(fileItem);
            });
        } else if (progressContainer) {
            progressContainer.classList.add('d-none');
        }
    }
    
    // Recursive function to traverse folder structure
    function traverseFileTree(item, path, filesArray, preservePath) {
        path = path || '';
        if (item.isFile) {
            item.file(file => {
                // Check if it's a supported format
                const ext = file.name.split('.').pop().toLowerCase();
                const allowedExts = ['txt', 'md', 'html', 'xml', 'json', 'csv'];
                
                if (allowedExts.includes(ext)) {
                    // If preservePath is true, keep the path in the folder
                    if (preservePath && path) {
                        // Create a new file with path in name or save path as metadata
                        file.relativePath = path + file.name;
                    }
                    filesArray.push(file);
                    showSelectedFiles(filesArray);
                }
            });
        } else if (item.isDirectory) {
            // Read directory contents
            const dirReader = item.createReader();
            dirReader.readEntries(entries => {
                for (let i = 0; i < entries.length; i++) {
                    // Build path recursively
                    traverseFileTree(
                        entries[i], 
                        preservePath ? path + item.name + '/' : '', 
                        filesArray,
                        preservePath
                    );
                }
            });
        }
    }
    
    // Setup drag & drop (if supported by browser)
    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });
        
        // Styles for drag hover
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => {
                dropArea.classList.add('bg-primary', 'bg-opacity-10');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => {
                dropArea.classList.remove('bg-primary', 'bg-opacity-10');
            }, false);
        });
        
        // Handle drop
        dropArea.addEventListener('drop', (e) => {
            const droppedItems = e.dataTransfer.items;
            const filesArray = [];
            
            // If dropped items are present
            if (droppedItems && droppedItems.length > 0) {
                // Check if webkitGetAsEntry is supported (for folders)
                if (droppedItems[0].webkitGetAsEntry) {
                    for (let i = 0; i < droppedItems.length; i++) {
                        const entry = droppedItems[i].webkitGetAsEntry();
                        if (entry) {
                            traverseFileTree(entry, '', filesArray, processFolder && processFolder.checked);
                        }
                    }
                } else {
                    // Fallback for browsers that don't support webkitGetAsEntry
                    const droppedFiles = e.dataTransfer.files;
                    for (let i = 0; i < droppedFiles.length; i++) {
                        filesArray.push(droppedFiles[i]);
                    }
                    // Update file input with dropped files (if possible)
                    try {
                        if (window.DataTransfer && window.DataTransfer.prototype.items) {
                            const dt = new DataTransfer();
                            filesArray.forEach(file => dt.items.add(file));
                            fileInput.files = dt.files;
                        }
                        showSelectedFiles(filesArray);
                    } catch (e) {
                        console.error("Cannot set files in input field:", e);
                        showNotification("Browser doesn't fully support drag & drop. Use the file selector.", "warning");
                    }
                }
            }
        }, false);
    }
    
    // Handle file selection via input
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            const files = fileInput.files ? Array.from(fileInput.files) : [];
            showSelectedFiles(files);
        });
    }
    
    // Handle form submission
    if (form) {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            
            if (!fileInput || !fileInput.files) {
                showNotification('Componente di input file non trovato o non supportato dal browser.', 'danger');
                return;
            }
            
            const files = Array.from(fileInput.files);
            
            if (files.length === 0) {
                showNotification('Seleziona almeno un file da caricare.', 'warning');
                return;
            }
            
            // Check total size
            const totalSize = files.reduce((sum, file) => sum + file.size, 0);
            const maxTotalSize = 50 * 1024 * 1024; // 50MB as example
            
            if (totalSize > maxTotalSize) {
                showNotification(`La dimensione totale (${Math.round(totalSize/1024/1024)}MB) supera il limite di ${Math.round(maxTotalSize/1024/1024)}MB.`, 'warning');
                return;
            }
            
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Caricamento...';
            }
            
            showLoading();
            
            try {
                // Show progress container
                if (progressContainer) {
                    progressContainer.classList.remove('d-none');
                }
                
                // Process files one by one
                let processed = 0;
                let successCount = 0;
                let errorCount = 0;
                
                for (const file of files) {
                    try {
                        const formData = new FormData();
                        formData.append('file', file);
                        
                        // Add path information if needed
                        if (file.relativePath) {
                            formData.append('relative_path', file.relativePath);
                        }
                        
                        // Option to keep folder structure
                        if (processFolder && processFolder.checked) {
                            formData.append('preserve_path', 'true');
                        }
                        
                        const result = await api.uploadDocument(formData);
                        
                        if (result && result.status === 'success') {
                            successCount++;
                        }
                    } catch (fileError) {
                        errorCount++;
                        console.error(`Error uploading file ${file.name}:`, fileError);
                        
                        // Update file status in UI
                        const fileEl = document.getElementById(`file-${file.name.replace(/\W/g, '')}`);
                        if (fileEl) {
                            fileEl.querySelector('.file-status').innerHTML = `<span class="text-danger">Errore</span>`;
                        }
                    }
                    
                    // Update progress
                    processed++;
                    updateProgress(processed, files.length, file);
                }
                
                // Final summary
                if (successCount > 0) {
                    if (successCount === 1) {
                        showNotification('Documento caricato con successo!', 'success');
                    } else {
                        showNotification(`${successCount} documenti caricati con successo!`, 'success');
                    }
                    
                    // Refresh the document list instead of reloading the page
                    refreshDocumentList();
                }
                
                if (errorCount > 0) {
                    showNotification(`Si sono verificati errori durante il caricamento di ${errorCount} file.`, 'warning');
                }
            } catch (error) {
                console.error("General error during upload:", error);
                showNotification(`Errore durante il caricamento: ${error.message}`, 'danger');
            } finally {
                hideLoading();
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-cloud-upload-alt me-2"></i>Carica';
                }
                if (form) {
                    form.reset(); // Clear form
                }
                if (progressContainer) {
                    setTimeout(() => {
                        progressContainer.classList.add('d-none');
                    }, 3000); // Hide progress bar after a few seconds
                }
            }
        });
    }
}

function handleExport() {
    const exportJsonBtn = document.getElementById('export-json-btn');
    const exportSpacyBtn = document.getElementById('export-spacy-btn');

    if (exportJsonBtn) {
        exportJsonBtn.addEventListener('click', () => {
            // Redirect to trigger download
            window.location.href = '/api/export_annotations?format=json&download=true';
        });
    }
     if (exportSpacyBtn) {
        exportSpacyBtn.addEventListener('click', () => {
             // Redirect to trigger download
            window.location.href = '/api/export_annotations?format=spacy&download=true';
        });
    }
}

// Inizializzazione automatica (se lo script è caricato direttamente)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        if (document.body.dataset.pageId === 'index') {
            initIndexPage();
        }
    });
} else {
    if (document.body.dataset.pageId === 'index') {
        initIndexPage();
    }
}