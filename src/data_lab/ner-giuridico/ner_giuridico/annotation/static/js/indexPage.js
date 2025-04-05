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

// Manteniamo le funzioni esistenti che verranno riutilizzate
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

let renameModalInstance = null;
let confirmDeleteModalInstance = null;
let docToDeleteId = null;
let docToDeleteTitle = '';

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
    // Mantieni la funzionalità esistente per l'upload
}

function handleExport() {
    // Mantieni la funzionalità esistente per l'export
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