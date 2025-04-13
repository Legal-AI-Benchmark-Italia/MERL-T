/**
 * entityManager.js
 * Gestione dinamica delle entità nell'interfaccia utente
 */

import { api } from './api.js';
import { showNotification, showLoading, hideLoading } from './ui.js';

// Stato
let entities = [];
let entityModalInstance = null;
let deleteModalInstance = null;
let entityToDelete = null;

// Elementi DOM
const entityListEl = document.getElementById('entity-list');
const entityFormEl = document.getElementById('entity-form');
const entityModalEl = document.getElementById('entityModal');
const deleteModalEl = document.getElementById('deleteEntityModal');
const entityNameInputEl = document.getElementById('entity-name');
const displayNameInputEl = document.getElementById('display-name');
const categorySelectEl = document.getElementById('category');
const colorInputEl = document.getElementById('color');
const descriptionInputEl = document.getElementById('description');
const metadataSchemaEl = document.getElementById('metadata-schema');
const patternsInputEl = document.getElementById('patterns');
const saveEntityBtnEl = document.getElementById('save-entity-btn');
const entityPreviewEl = document.getElementById('entity-preview');
const colorPreviewEl = document.getElementById('color-preview');
const confirmDeleteBtnEl = document.getElementById('confirm-delete-btn');
const entityNameToDeleteEl = document.getElementById('entity-name-to-delete');

/**
 * Inizializza il gestore delle entità
 */
export function initEntityManager() {
    console.log("Inizializzazione del gestore delle entità");
    
    // Inizializza le modali
    if (entityModalEl) {
        entityModalInstance = new bootstrap.Modal(entityModalEl);
    }
    if (deleteModalEl) {
        deleteModalInstance = new bootstrap.Modal(deleteModalEl);
    }
    
    // Carica le entità
    loadEntities();
    
    // Configura gli event listener
    setupEventListeners();
    
    // Configura il sistema di importazione/esportazione
    setupImportExport();
}

/**
 * Configura gli event listener
 */
function setupEventListeners() {
    // Form per l'aggiunta/modifica di entità
    entityFormEl?.addEventListener('submit', handleEntityFormSubmit);
    
    // Anteprima del colore
    colorInputEl?.addEventListener('input', updateColorPreview);
    
    // Pulsante per confermare l'eliminazione
    confirmDeleteBtnEl?.addEventListener('click', handleDeleteEntity);
    
    // Pulsante per aggiungere una nuova entità
    document.getElementById('add-entity-btn')?.addEventListener('click', () => {
        showEntityModal();
    });
    
    // Filtro per categoria
    document.getElementById('category-filter')?.addEventListener('change', (e) => {
        filterEntities(e.target.value);
    });
    
    // Ricerca
    document.getElementById('entity-search')?.addEventListener('input', (e) => {
        searchEntities(e.target.value);
    });
}

/**
 * Configura il sistema di importazione/esportazione
 */
function setupImportExport() {
    const exportBtn = document.getElementById('export-entities-btn');
    const importBtn = document.getElementById('import-entities-btn');
    
    if (exportBtn) {
        exportBtn.addEventListener('click', handleExportEntities);
    }
    
    if (importBtn) {
        importBtn.addEventListener('click', function() {
            // Mostra il modal di importazione
            const importModalEl = document.getElementById('importEntitiesModal');
            if (importModalEl) {
                const importModal = new bootstrap.Modal(importModalEl);
                importModal.show();
            } else {
                console.error("Modal di importazione non trovato nel DOM");
                showNotification("Componente di importazione non trovato", "danger");
            }
        });
    }
    
    // Setup del form di importazione
    const importForm = document.getElementById('import-entities-form');
    if (importForm) {
        importForm.addEventListener('submit', handleImportEntities);
    }
}

/**
 * Gestisce l'esportazione delle entità
 */
async function handleExportEntities() {
    try {
        // Inizia il download del file
        window.location.href = '/api/entity_types/export?download=true';
        showNotification("Download dei tipi di entità avviato", "success");
    } catch (error) {
        console.error("Errore nell'esportazione delle entità:", error);
        showNotification(`Errore: ${error.message}`, 'danger');
    }
}

/**
 * Gestisce l'importazione delle entità
 */
async function handleImportEntities(event) {
    event.preventDefault();
    
    const fileInput = document.getElementById('entity-import-file');
    const modeRadios = document.getElementsByName('import-mode');
    
    if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
        showNotification('Seleziona un file JSON da importare', 'warning');
        return;
    }
    
    // Trova il valore selezionato per la modalità
    let mode = 'merge'; // Default
    for (const radio of modeRadios) {
        if (radio.checked) {
            mode = radio.value;
            break;
        }
    }
    
    // Crea FormData per l'upload
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('mode', mode);
    
    // Disabilita il pulsante durante il caricamento
    const submitBtn = document.getElementById('submit-import-btn');
    const importModalEl = document.getElementById('importEntitiesModal');
    let importModal = null;
    
    if (importModalEl) {
        importModal = bootstrap.Modal.getInstance(importModalEl);
        if (!importModal) {
            importModal = new bootstrap.Modal(importModalEl);
        }
    }
    
    if (submitBtn) submitBtn.disabled = true;
    showLoading();
    
    try {
        const result = await api.importEntityTypes(formData);
        
        if (result.status === 'success' || result.status === 'warning') {
            showNotification(result.message, result.status);
            
            // Se ci sono errori, mostrali
            const importResultEl = document.getElementById('import-result');
            if (result.errors && result.errors.length > 0 && importResultEl) {
                const errorDetails = document.createElement('div');
                errorDetails.innerHTML = `
                    <div class="alert alert-warning mt-3">
                        <h6>Dettagli Errori:</h6>
                        <ul>
                            ${result.errors.map(err => `<li>${err}</li>`).join('')}
                        </ul>
                    </div>
                `;
                
                importResultEl.innerHTML = '';
                importResultEl.appendChild(errorDetails);
            }
            
            // Ricarica la lista delle entità
            if (result.imported > 0) {
                loadEntities();
            }
            
            if (importModal) {
                setTimeout(() => {
                    importModal.hide();
                }, 3000);
            }
        } else {
            throw new Error(result.message || "Errore durante l'importazione");
        }
    } catch (error) {
        console.error("Errore nell'importazione delle entità:", error);
        showNotification(`Errore: ${error.message}`, 'danger');
    } finally {
        if (submitBtn) submitBtn.disabled = false;
        hideLoading();
        
        // Reset form
        fileInput.value = '';
    }
}

/**
 * Carica le entità dal server
 */
async function loadEntities() {
    try {
        showLoading();
        
        const response = await api.getEntityTypes();
        
        if (response.status !== 'success') {
            throw new Error(response.message || 'Errore nel caricamento delle entità');
        }
        
        entities = response.entity_types;
        renderEntities(entities);
        
        hideLoading();
    } catch (error) {
        console.error("Errore nel caricamento delle entità:", error);
        showNotification(`Errore: ${error.message}`, 'danger');
        hideLoading();
    }
}

/**
 * Renderizza le entità nella lista
 */
function renderEntities(entitiesToRender) {
    if (!entityListEl) return;
    
    // Svuota la lista
    entityListEl.innerHTML = '';
    
    if (entitiesToRender.length === 0) {
        entityListEl.innerHTML = `
            <div class="text-center p-4 text-muted">
                <i class="fas fa-tag fa-3x mb-3"></i>
                <p>Nessun tipo di entità trovato.</p>
                <button id="add-first-entity" class="btn btn-primary">
                    <i class="fas fa-plus me-1"></i> Aggiungi il primo tipo
                </button>
            </div>
        `;
        
        // Aggiungi event listener per il pulsante
        document.getElementById('add-first-entity')?.addEventListener('click', () => {
            showEntityModal();
        });
        
        return;
    }
    
    // Crea un elemento per ogni entità
    entitiesToRender.forEach(entity => {
        const entityEl = document.createElement('div');
        entityEl.className = 'card mb-3 entity-card';
        entityEl.dataset.entityId = entity.id;
        
        // Crea il colore di sfondo sfumato
        entityEl.style.borderLeft = `4px solid ${entity.color}`;
        
        entityEl.innerHTML = `
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <div>
                        <h5 class="card-title mb-0 d-flex align-items-center">
                            <span class="color-preview me-2" style="background-color: ${entity.color};"></span>
                            ${entity.display_name}
                            ${entity.system ? '<span class="badge bg-secondary ms-2">Sistema</span>' : ''}
                        </h5>
                        <div class="small text-muted font-monospace">${entity.name}</div>
                    </div>
                    <div class="badge ${getCategoryBadgeClass(entity.category)} text-white">
                        ${getCategoryDisplayName(entity.category)}
                    </div>
                </div>
                
                ${entity.description ? `<p class="card-text small">${entity.description}</p>` : ''}
                
                <div class="entity-details small">
                    <div class="mb-2">
                        <strong>Schema metadati:</strong>
                        ${Object.keys(entity.metadata_schema || {}).length > 0 
                            ? `<code>${JSON.stringify(entity.metadata_schema)}</code>` 
                            : '<span class="text-muted">Nessuno</span>'}
                    </div>
                    <div>
                        <strong>Pattern:</strong>
                        ${entity.patterns && entity.patterns.length > 0 
                            ? `<div class="mt-1">${entity.patterns.map(p => `<code class="d-block mb-1">${p}</code>`).join('')}</div>` 
                            : '<span class="text-muted">Nessuno</span>'}
                    </div>
                </div>
                
                <div class="mt-3 entity-actions">
                    <button class="btn btn-sm btn-outline-primary edit-entity-btn">
                        <i class="fas fa-edit me-1"></i> Modifica
                    </button>
                    ${!entity.system ? `
                        <button class="btn btn-sm btn-outline-danger delete-entity-btn">
                            <i class="fas fa-trash-alt me-1"></i> Elimina
                        </button>
                    ` : ''}
                    <button class="btn btn-sm btn-outline-info test-patterns-btn">
                        <i class="fas fa-vial me-1"></i> Testa Pattern
                    </button>
                </div>
            </div>
        `;
        
        // Aggiungi event listeners per i pulsanti
        entityEl.querySelector('.edit-entity-btn')?.addEventListener('click', () => {
            showEntityModal(entity);
        });
        
        entityEl.querySelector('.delete-entity-btn')?.addEventListener('click', () => {
            showDeleteModal(entity);
        });
        
        entityEl.querySelector('.test-patterns-btn')?.addEventListener('click', () => {
            showPatternTestModal(entity);
        });
        
        entityListEl.appendChild(entityEl);
    });
    
    // Aggiungi il pulsante fluttuante per aggiungere entità
    if (!document.getElementById('add-entity-floating-btn')) {
        const floatingBtn = document.createElement('button');
        floatingBtn.id = 'add-entity-floating-btn';
        floatingBtn.className = 'btn btn-primary btn-lg rounded-circle position-fixed';
        floatingBtn.style.bottom = '2rem';
        floatingBtn.style.right = '2rem';
        floatingBtn.style.zIndex = '1000';
        floatingBtn.innerHTML = '<i class="fas fa-plus"></i>';
        floatingBtn.title = 'Aggiungi nuovo tipo di entità';
        
        floatingBtn.addEventListener('click', () => {
            showEntityModal();
        });
        
        document.body.appendChild(floatingBtn);
    }
}

/**
 * Mostra la modale per aggiungere/modificare un'entità
 */
function showEntityModal(entity = null) {
    if (!entityModalInstance) return;
    
    // Reset form
    entityFormEl.reset();
    
    // Configura la modale
    const modalTitle = document.getElementById('entityModalLabel');
    
    if (entity) {
        // Modifica
        modalTitle.textContent = `Modifica ${entity.display_name}`;
        entityFormEl.dataset.mode = 'edit';
        entityFormEl.dataset.entityId = entity.id;
        
        // Popola i campi
        entityNameInputEl.value = entity.name;
        entityNameInputEl.disabled = true; // Non permettere la modifica del nome
        displayNameInputEl.value = entity.display_name;
        categorySelectEl.value = entity.category;
        colorInputEl.value = entity.color;
        descriptionInputEl.value = entity.description || '';
        metadataSchemaEl.value = JSON.stringify(entity.metadata_schema || {}, null, 2);
        patternsInputEl.value = (entity.patterns || []).join('\n');
        
        // Disabilita la modifica per le entità di sistema
        if (entity.system) {
            const fieldsToDisable = [
                entityNameInputEl,
                categorySelectEl
            ];
            fieldsToDisable.forEach(field => {
                if (field) field.disabled = true;
            });
            
            // Mostra un avviso
            const systemWarning = document.createElement('div');
            systemWarning.className = 'alert alert-warning mt-2';
            systemWarning.textContent = 'Questa è un\'entità di sistema. Alcune proprietà non possono essere modificate.';
            entityFormEl.querySelector('.modal-body').prepend(systemWarning);
        }
    } else {
        // Aggiunta
        modalTitle.textContent = 'Nuovo Tipo di Entità';
        entityFormEl.dataset.mode = 'add';
        entityFormEl.dataset.entityId = '';
        
        // Reset campi
        entityNameInputEl.disabled = false;
        
        // Valori predefiniti
        colorInputEl.value = '#' + Math.floor(Math.random()*16777215).toString(16).padStart(6, '0');
        categorySelectEl.value = 'custom';
    }
    
    // Aggiorna l'anteprima del colore
    updateColorPreview();
    
    // Mostra la modale
    entityModalInstance.show();
}

/**
 * Mostra la modale per confermare l'eliminazione di un'entità
 */
function showDeleteModal(entity) {
    if (!deleteModalInstance) return;
    
    // Memorizza l'entità da eliminare
    entityToDelete = entity;
    
    // Aggiorna il nome dell'entità nel messaggio di conferma
    if (entityNameToDeleteEl) {
        entityNameToDeleteEl.textContent = entity.display_name;
    }
    
    // Mostra la modale
    deleteModalInstance.show();
}

/**
 * Mostra la modale per testare i pattern di un'entità
 */
function showPatternTestModal(entity) {
    // Implementazione esistente...
}

/**
 * Gestisce l'invio del form per l'aggiunta/modifica di un'entità
 */
async function handleEntityFormSubmit(e) {
    e.preventDefault();
    
    // Valida il form
    if (!validateEntityForm()) {
        return;
    }
    
    // Prepara i dati
    const formData = {
        name: entityNameInputEl.value.trim(),
        display_name: displayNameInputEl.value.trim(),
        category: categorySelectEl.value,
        color: colorInputEl.value,
        description: descriptionInputEl.value.trim()
    };
    
    // Aggiungi i metadati se specificati
    if (metadataSchemaEl.value.trim()) {
        try {
            formData.metadata_schema = JSON.parse(metadataSchemaEl.value.trim());
        } catch (error) {
            showNotification('Formato JSON non valido per lo schema dei metadati', 'danger');
            return;
        }
    } else {
        formData.metadata_schema = {};
    }
    
    // Aggiungi i pattern se specificati
    if (patternsInputEl.value.trim()) {
        formData.patterns = patternsInputEl.value.trim().split('\n').filter(p => p.trim() !== '');
    } else {
        formData.patterns = [];
    }
    
    try {
        showLoading();
        
        const mode = entityFormEl.dataset.mode;
        let response;
        
        if (mode === 'edit') {
            const entityId = entityFormEl.dataset.entityId;
            response = await api.updateEntityType(entityId, formData);
        } else {
            response = await api.createEntityType(formData);
        }
        
        if (response.status !== 'success') {
            throw new Error(response.message || 'Errore nel salvataggio dell\'entità');
        }
        
        // Aggiorna la lista delle entità
        await loadEntities();
        
        // Chiudi la modale
        entityModalInstance.hide();
        
        // Mostra un messaggio di successo
        showNotification(response.message, 'success');
    } catch (error) {
        console.error("Errore nel salvataggio dell'entità:", error);
        showNotification(`Errore: ${error.message}`, 'danger');
    } finally {
        hideLoading();
    }
}

/**
 * Gestisce l'eliminazione di un'entità
 */
async function handleDeleteEntity() {
    if (!entityToDelete) return;
    
    try {
        showLoading();
        
        const response = await api.deleteEntityType(entityToDelete.id);
        
        if (response.status !== 'success') {
            throw new Error(response.message || 'Errore nell\'eliminazione dell\'entità');
        }
        
        // Aggiorna la lista delle entità
        await loadEntities();
        
        // Chiudi la modale
        deleteModalInstance.hide();
        
        // Mostra un messaggio di successo
        showNotification(response.message, 'success');
    } catch (error) {
        console.error("Errore nell'eliminazione dell'entità:", error);
        showNotification(`Errore: ${error.message}`, 'danger');
    } finally {
        hideLoading();
        entityToDelete = null;
    }
}

/**
 * Aggiorna l'anteprima del colore
 */
function updateColorPreview() {
    if (!colorInputEl || !colorPreviewEl) return;
    
    const color = colorInputEl.value;
    colorPreviewEl.style.backgroundColor = color;
    colorPreviewEl.textContent = color;
    
    // Aggiorna anche l'entità di esempio
    if (entityPreviewEl) {
        entityPreviewEl.style.backgroundColor = color;
        entityPreviewEl.style.color = getContrastColor(color);
    }
}

/**
 * Valida il form dell'entità
 */
function validateEntityForm() {
    // Nome entità (solo se nuovo)
    if (entityFormEl.dataset.mode === 'add' && entityNameInputEl) {
        const name = entityNameInputEl.value.trim();
        
        if (!name) {
            showNotification('Il nome dell\'entità è obbligatorio', 'danger');
            entityNameInputEl.focus();
            return false;
        }
        
        if (!name.match(/^[A-Z0-9_]+$/)) {
            showNotification('Il nome dell\'entità deve contenere solo lettere maiuscole, numeri e underscore', 'danger');
            entityNameInputEl.focus();
            return false;
        }
    }
    
    // Nome visualizzato
    if (displayNameInputEl) {
        const displayName = displayNameInputEl.value.trim();
        
        if (!displayName) {
            showNotification('Il nome visualizzato è obbligatorio', 'danger');
            displayNameInputEl.focus();
            return false;
        }
    }
    
    // Schema metadati (se presente)
    if (metadataSchemaEl && metadataSchemaEl.value.trim()) {
        try {
            JSON.parse(metadataSchemaEl.value.trim());
        } catch (error) {
            showNotification('Formato JSON non valido per lo schema dei metadati', 'danger');
            metadataSchemaEl.focus();
            return false;
        }
    }
    
    return true;
}

/**
 * Filtra le entità per categoria
 */
function filterEntities(category) {
    if (category === 'all') {
        renderEntities(entities);
    } else {
        const filtered = entities.filter(e => e.category === category);
        renderEntities(filtered);
    }
}

/**
 * Cerca le entità per nome o descrizione
 */
function searchEntities(query) {
    if (!query.trim()) {
        renderEntities(entities);
        return;
    }
    
    const q = query.toLowerCase();
    const filtered = entities.filter(e => 
        e.name.toLowerCase().includes(q) || 
        e.display_name.toLowerCase().includes(q) || 
        (e.description && e.description.toLowerCase().includes(q))
    );
    
    renderEntities(filtered);
}

/**
 * Ottiene il nome della categoria per la visualizzazione
 */
function getCategoryDisplayName(category) {
    const categoryNames = {
        'normative': 'Normativa',
        'jurisprudence': 'Giurisprudenziale',
        'concepts': 'Concetto',
        'custom': 'Personalizzata'
    };
    
    return categoryNames[category] || category;
}

/**
 * Ottiene la classe del badge per la categoria
 */
function getCategoryBadgeClass(category) {
    const categoryClasses = {
        'normative': 'bg-primary',
        'jurisprudence': 'bg-success',
        'concepts': 'bg-info',
        'custom': 'bg-secondary'
    };
    
    return categoryClasses[category] || 'bg-secondary';
}

/**
 * Ottiene il colore di contrasto per un colore di sfondo
 */
function getContrastColor(hexColor) {
    // Converte il colore esadecimale in RGB
    const r = parseInt(hexColor.substr(1, 2), 16);
    const g = parseInt(hexColor.substr(3, 2), 16);
    const b = parseInt(hexColor.substr(5, 2), 16);
    
    // Calcola la luminosità
    const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
    
    // Restituisce bianco o nero in base alla luminosità
    return (yiq >= 128) ? '#000000' : '#ffffff';
}