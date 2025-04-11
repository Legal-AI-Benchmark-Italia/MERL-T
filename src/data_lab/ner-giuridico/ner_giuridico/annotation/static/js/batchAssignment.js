/**
 * batchAssignment.js
 * Gestisce l'assegnazione in batch dei documenti agli utenti
 */
import { api } from './api.js';
import { showNotification, showLoading, hideLoading } from './ui.js';

// Stato
let selectedDocIds = new Set();
let availableUsers = [];
let batchAssignModalInstance = null;

// Funzione di inizializzazione
export function initBatchAssignment() {
    console.log('Initializing batch assignment module');
    
    // Cache elementi DOM
    const batchAssignBtn = document.getElementById('batch-assign-btn');
    const batchAssignModal = document.getElementById('batchAssignModal');
    const userSelect = document.getElementById('batch-user-select');
    const confirmBatchAssignBtn = document.getElementById('confirm-batch-assign-btn');
    const docsSelectedCount = document.getElementById('docs-selected-count');
    
    // Inizializza modale
    if (batchAssignModal) {
        batchAssignModalInstance = new bootstrap.Modal(batchAssignModal);
    }
    
    // Event Listeners
    batchAssignBtn?.addEventListener('click', showBatchAssignModal);
    confirmBatchAssignBtn?.addEventListener('click', handleBatchAssign);
    
    // Setup listener per checkbox documenti (delega eventi)
    const documentList = document.getElementById('document-list');
    documentList?.addEventListener('change', function(e) {
        if (e.target.classList.contains('doc-checkbox')) {
            handleDocumentSelection(e.target);
        }
    });
    
    // Setup filter buttons
    setupFilterButtons();
    
    // Listener per deseleziona tutti
    document.getElementById('clear-selection-btn')?.addEventListener('click', clearSelection);
    
    // Carica utenti se siamo Admin
    if (document.body.dataset.userRole === 'admin') {
        loadAvailableUsers();
    }
}

// Carica gli utenti disponibili per l'assegnazione
async function loadAvailableUsers() {
    try {
        showLoading();
        // Assumiamo che esista un endpoint API per ottenere utenti
        const response = await api.getUsers();
        
        if (response && response.status === 'success') {
            availableUsers = response.users || [];
            updateUserSelect();
        } else {
            console.error('Failed to load users');
        }
        
        hideLoading();
    } catch (error) {
        console.error('Error loading users:', error);
        showNotification('Errore nel caricamento degli utenti', 'danger');
        hideLoading();
    }
}

// Aggiorna la select degli utenti
function updateUserSelect() {
    const userSelect = document.getElementById('batch-user-select');
    if (!userSelect) return;
    
    userSelect.innerHTML = '<option value="" selected disabled>-- Seleziona utente --</option>';
    
    availableUsers.forEach(user => {
        // Filtriamo solo gli annotatori
        if (user.role === 'annotator') {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = user.full_name || user.username;
            userSelect.appendChild(option);
        }
    });
}

// Gestisce la selezione/deselezione dei documenti
function handleDocumentSelection(checkbox) {
    const docId = checkbox.value;
    
    if (checkbox.checked) {
        selectedDocIds.add(docId);
    } else {
        selectedDocIds.delete(docId);
    }
    
    updateSelectionUI();
}

// Aggiorna l'interfaccia in base alle selezioni
function updateSelectionUI() {
    // Aggiorna il contatore documenti selezionati
    const counterElements = document.querySelectorAll('.selected-docs-counter');
    counterElements.forEach(el => {
        el.textContent = selectedDocIds.size;
    });
    
    // Mostra/nascondi pulsante di assegnazione batch
    const batchAssignBtn = document.getElementById('batch-assign-btn');
    if (batchAssignBtn) {
        batchAssignBtn.disabled = selectedDocIds.size === 0;
    }
    
    // Mostra/nascondi pulsante cancella selezione
    const clearSelectionBtn = document.getElementById('clear-selection-btn');
    if (clearSelectionBtn) {
        clearSelectionBtn.disabled = selectedDocIds.size === 0;
    }
    
    // Aggiorna l'UI per ogni documento
    document.querySelectorAll('.doc-card').forEach(card => {
        const docId = card.dataset.docId;
        if (selectedDocIds.has(docId)) {
            card.classList.add('border-primary');
        } else {
            card.classList.remove('border-primary');
        }
    });
}

// Mostra la modale di assegnazione batch
function showBatchAssignModal() {
    if (!batchAssignModalInstance) return;
    
    // Aggiorna il contatore nella modale
    const docsSelectedCount = document.getElementById('docs-selected-count');
    if (docsSelectedCount) {
        docsSelectedCount.textContent = selectedDocIds.size;
    }
    
    // Disabilita il pulsante di conferma se nessun utente è selezionato
    const userSelect = document.getElementById('batch-user-select');
    const confirmBtn = document.getElementById('confirm-batch-assign-btn');
    
    if (confirmBtn) {
        confirmBtn.disabled = !userSelect || !userSelect.value;
    }
    
    // Abilita il listener per la select degli utenti
    userSelect?.addEventListener('change', function() {
        if (confirmBtn) {
            confirmBtn.disabled = !this.value;
        }
    });
    
    batchAssignModalInstance.show();
}

// Gestisce l'assegnazione batch
async function handleBatchAssign() {
    const userSelect = document.getElementById('batch-user-select');
    const confirmBtn = document.getElementById('confirm-batch-assign-btn');
    
    if (!userSelect || !userSelect.value || selectedDocIds.size === 0) {
        return;
    }
    
    const userId = userSelect.value;
    const docIdsArray = Array.from(selectedDocIds);
    
    try {
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Assegnazione...';
        showLoading('Assegnazione documenti in corso...');
        
        const result = await api.batchAssignDocuments(docIdsArray, userId);
        
        if (result.status === 'success') {
            showNotification(result.message, 'success');
            
            // Aggiorna UI per indicare i documenti assegnati
            result.results.success.forEach(docId => {
                const docCard = document.querySelector(`.doc-card[data-doc-id="${docId}"]`);
                if (docCard) {
                    docCard.querySelector('.assigned-badge')?.classList.remove('d-none');
                }
            });
            
            // Chiudi la modale
            batchAssignModalInstance.hide();
            
            // Reset selezioni
            clearSelection();
            
            // Opzionale: ricarica la pagina per riflettere le modifiche
            if (result.results.success.length > 0) {
                if (confirm('Ricaricare la pagina per visualizzare le modifiche?')) {
                    window.location.reload();
                }
            }
        } else {
            throw new Error(result.message || 'Errore durante l\'assegnazione batch');
        }
    } catch (error) {
        console.error('Error during batch assignment:', error);
        showNotification(`Errore: ${error.message}`, 'danger');
    } finally {
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = 'Assegna';
        }
        hideLoading();
    }
}

// Cancella tutte le selezioni
function clearSelection() {
    selectedDocIds.clear();
    
    // Deseleziona tutte le checkbox
    document.querySelectorAll('.doc-checkbox').forEach(checkbox => {
        checkbox.checked = false;
    });
    
    updateSelectionUI();
}

// Configura i pulsanti di filtro per stato (pending, completed, skipped)
function setupFilterButtons() {
    const filterButtons = document.querySelectorAll('.status-filter-btn');
    
    filterButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const status = this.dataset.status;
            
            // Update active state
            filterButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // Reload with filter
            window.location.href = `?status=${status || ''}`;
        });
    });
}

// Esegui l'inizializzazione automaticamente se siamo nella pagina appropriata
document.addEventListener('DOMContentLoaded', function() {
    if (document.body.dataset.pageId === 'index' || document.body.dataset.pageId === 'admin_users') {
        initBatchAssignment();
    }
});