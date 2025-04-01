/**
 * entityManager.js
 * Logic for the Entity Types management page.
 */
import { api } from './api.js';
import { showNotification, showLoading, hideLoading, getCategoryDisplayName, getCategoryBadgeClass, hexToRgb, calculateLuminance } from './ui.js';

let allEntities = [];
let entityTypeModalInstance = null;
let confirmDeleteModalInstance = null;
let entityToDeleteName = null;

// --- DOM Elements ---
let tableBody, loadingRow, emptyRow, searchInput, categoryFilter;
let modalEl, formEl, editModeInput, originalNameInput, nameInput, displayNameInput, categoryInput, colorInput, colorPreview, colorSample, metadataInput, patternsInput, saveBtn, modalTitle;
let testTextarea, testBtn, testResultsEl, testOutputEl, matchCountEl;
let confirmDeleteModalEl, entityNameToDeleteEl, confirmDeleteBtn, deleteWarningEl;

// --- Initialization ---
function cacheDOMElements() {
    tableBody = document.querySelector('#entity-types-table tbody');
    loadingRow = document.getElementById('loading-row');
    emptyRow = document.getElementById('empty-row');
    searchInput = document.getElementById('entity-search-input');
    categoryFilter = document.getElementById('category-filter-select');

    modalEl = document.getElementById('entityTypeModal');
    formEl = document.getElementById('entity-type-form');
    editModeInput = document.getElementById('edit-mode');
    originalNameInput = document.getElementById('original-name');
    nameInput = document.getElementById('entity-name');
    displayNameInput = document.getElementById('display-name');
    categoryInput = document.getElementById('category');
    colorInput = document.getElementById('color');
    colorPreview = document.getElementById('color-preview');
    colorSample = document.getElementById('color-sample');
    metadataInput = document.getElementById('metadata-schema');
    patternsInput = document.getElementById('patterns');
    saveBtn = document.getElementById('save-entity-type-btn');
    modalTitle = document.getElementById('entityTypeModalLabel');

    testTextarea = document.getElementById('test-text');
    testBtn = document.getElementById('test-patterns-btn');
    testResultsEl = document.getElementById('test-results');
    testOutputEl = document.getElementById('test-output');
    matchCountEl = document.getElementById('match-count');

    confirmDeleteModalEl = document.getElementById('confirmDeleteEntityTypeModal');
    entityNameToDeleteEl = document.getElementById('entity-type-to-delete-name');
    confirmDeleteBtn = document.getElementById('confirm-delete-entity-type-btn');
    deleteWarningEl = document.getElementById('delete-warning-in-use');

    if (modalEl) entityTypeModalInstance = new bootstrap.Modal(modalEl);
    if (confirmDeleteModalEl) confirmDeleteModalInstance = new bootstrap.Modal(confirmDeleteModalEl);
}

// --- Rendering ---
function renderEntityTypes(entities) {
    if (!tableBody) return;
    tableBody.innerHTML = ''; // Clear existing rows

    if (entities.length === 0) {
        emptyRow?.classList.remove('d-none');
        loadingRow?.classList.add('d-none');
        return;
    }

    emptyRow?.classList.add('d-none');
    loadingRow?.classList.add('d-none');

    const template = document.getElementById('entity-type-row-template');
    if (!template) return;

    entities.forEach(entity => {
        const clone = template.content.cloneNode(true);
        const tr = clone.querySelector('tr');
        const cells = clone.querySelectorAll('td');

        tr.dataset.entityName = entity.name;
        cells[0].textContent = entity.name;
        cells[1].textContent = entity.display_name;

        const categoryBadge = cells[2].querySelector('.badge');
        categoryBadge.textContent = getCategoryDisplayName(entity.category);
        categoryBadge.className = `badge rounded-pill ${getCategoryBadgeClass(entity.category)}`;

        cells[3].querySelector('.color-preview').style.backgroundColor = entity.color;
        cells[3].querySelector('code').textContent = entity.color;

        const editBtn = cells[4].querySelector('.edit-entity-btn');
        const deleteBtn = cells[4].querySelector('.delete-entity-btn');

        editBtn.addEventListener('click', () => showEditForm(entity));

        if (entity.category === 'custom') {
            deleteBtn.addEventListener('click', () => showDeleteConfirmation(entity));
        } else {
            deleteBtn.disabled = true;
            deleteBtn.title = 'Le entità predefinite non possono essere eliminate';
            deleteBtn.classList.replace('btn-outline-danger', 'btn-outline-secondary');
            deleteBtn.innerHTML = '<i class="fas fa-lock"></i>';
        }

        tableBody.appendChild(clone);
    });
}

// --- Data Fetching and Filtering ---
async function loadEntityTypes() {
    loadingRow?.classList.remove('d-none');
    emptyRow?.classList.add('d-none');
    tableBody.innerHTML = ''; // Clear while loading
    tableBody.appendChild(loadingRow); // Add loading row back

    try {
        const data = await api.getEntityTypes();
        allEntities = data.entity_types || [];
        filterAndRender();
    } catch (error) {
        showNotification(`Errore nel caricamento dei tipi di entità: ${error.message}`, 'danger');
        allEntities = [];
        filterAndRender(); // Render empty state
    } finally {
         loadingRow?.classList.add('d-none');
    }
}

function filterAndRender() {
    const searchTerm = searchInput?.value.toLowerCase() || '';
    const selectedCategory = categoryFilter?.value || '';

    const filtered = allEntities.filter(entity => {
        const nameMatch = entity.name.toLowerCase().includes(searchTerm) || entity.display_name.toLowerCase().includes(searchTerm);
        const categoryMatch = !selectedCategory || entity.category === selectedCategory;
        return nameMatch && categoryMatch;
    });

    renderEntityTypes(filtered);
}

// --- Form Handling ---
function updateColorPreview() {
    const colorValue = colorInput.value;
    if (colorPreview) colorPreview.textContent = colorValue;
    if (colorSample) {
        colorSample.style.backgroundColor = colorValue;
        // Basic contrast check
        const rgb = hexToRgb(colorValue);
        if (rgb) {
            const luminance = calculateLuminance(rgb.r, rgb.g, rgb.b);
            colorSample.style.color = luminance > 0.5 ? '#000' : '#fff';
        }
    }
}

function resetForm() {
    formEl?.reset();
    editModeInput.value = 'create';
    originalNameInput.value = '';
    modalTitle.textContent = 'Nuovo Tipo di Entità';
    saveBtn.textContent = 'Crea';
    nameInput.disabled = false;
    colorInput.value = '#CCCCCC'; // Reset color picker
    updateColorPreview();
    testResultsEl?.classList.add('d-none');
    testOutputEl.textContent = '';
    matchCountEl.textContent = '0';
    // Remove validation classes
    formEl?.classList.remove('was-validated');
    formEl?.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    formEl?.querySelectorAll('.is-valid').forEach(el => el.classList.remove('is-valid'));

}

function showCreateForm() {
    resetForm();
    entityTypeModalInstance?.show();
}

function showEditForm(entity) {
    resetForm();
    editModeInput.value = 'edit';
    originalNameInput.value = entity.name;
    modalTitle.textContent = `Modifica Tipo Entità: ${entity.name}`;
    saveBtn.textContent = 'Salva Modifiche';

    nameInput.value = entity.name;
    nameInput.disabled = true; // Cannot edit name
    displayNameInput.value = entity.display_name;
    categoryInput.value = entity.category;
    colorInput.value = entity.color;
    metadataInput.value = entity.metadata_schema ? JSON.stringify(entity.metadata_schema, null, 2) : '';
    patternsInput.value = entity.patterns ? entity.patterns.join('\n') : '';

    updateColorPreview();
    entityTypeModalInstance?.show();
}

function validateForm() {
    let isValid = true;

    // Name validation (only for create)
    if (editModeInput.value === 'create') {
        const name = nameInput.value;
        const nameRegex = /^[A-Z0-9_]+$/;
        const nameExists = allEntities.some(e => e.name === name);
        if (!name || !nameRegex.test(name) || nameExists) {
            nameInput.classList.add('is-invalid');
            nameInput.nextElementSibling.nextElementSibling.textContent = // Adjust selector if needed
                !name ? 'Nome richiesto.' :
                !nameRegex.test(name) ? 'Formato non valido (solo A-Z, 0-9, _).' :
                'Nome già esistente.';
            isValid = false;
        } else {
            nameInput.classList.remove('is-invalid');
        }
    }

    // Display Name
    if (!displayNameInput.value.trim()) {
        displayNameInput.classList.add('is-invalid');
        isValid = false;
    } else {
        displayNameInput.classList.remove('is-invalid');
    }

    // Category
    if (!categoryInput.value) {
         categoryInput.classList.add('is-invalid');
         isValid = false;
    } else {
         categoryInput.classList.remove('is-invalid');
    }

    // Color
     if (!colorInput.value || !/^#[0-9A-Fa-f]{6}$/.test(colorInput.value)) {
         // Bootstrap color input usually handles this, but add class if needed
         isValid = false; // Or rely on browser validation
     }

    // Metadata Schema (optional, but must be valid JSON if provided)
    const metadataVal = metadataInput.value.trim();
    const metadataFeedback = document.getElementById('metadata-validation');
    metadataInput.classList.remove('is-invalid');
    if (metadataVal) {
        try {
            JSON.parse(metadataVal);
        } catch (e) {
            metadataInput.classList.add('is-invalid');
            metadataFeedback.textContent = `Schema JSON non valido: ${e.message}`;
            isValid = false;
        }
    }

    // Patterns (optional, but must be valid regex if provided)
    const patternsVal = patternsInput.value.trim();
    const patternsFeedback = document.getElementById('patterns-validation');
    patternsInput.classList.remove('is-invalid');
    if (patternsVal) {
        const lines = patternsVal.split('\n').filter(line => line.trim() !== '');
        let invalidPatternFound = false;
        for (const line of lines) {
            try {
                new RegExp(line);
            } catch (e) {
                patternsInput.classList.add('is-invalid');
                patternsFeedback.textContent = `Pattern non valido: "${line}" (${e.message})`;
                isValid = false;
                invalidPatternFound = true;
                break;
            }
        }
    }

    return isValid;
}

async function handleFormSubmit(event) {
    event.preventDefault();
    formEl.classList.add('was-validated'); // Trigger Bootstrap validation styles

    if (!validateForm()) {
        showNotification('Correggi gli errori nel form.', 'warning');
        return;
    }

    const isEdit = editModeInput.value === 'edit';
    const name = isEdit ? originalNameInput.value : nameInput.value;

    let metadataSchema = {};
    if (metadataInput.value.trim()) {
        try {
            metadataSchema = JSON.parse(metadataInput.value.trim());
        } catch { /* Already validated, ignore */ }
    }

    const patterns = patternsInput.value.trim()
        ? patternsInput.value.trim().split('\n').filter(line => line.trim() !== '')
        : [];

    const data = {
        display_name: displayNameInput.value.trim(),
        category: categoryInput.value,
        color: colorInput.value,
        metadata_schema: metadataSchema,
        patterns: patterns
    };

    // Only include name for creation
    if (!isEdit) {
        data.name = name;
    }

    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Salvataggio...';
    showLoading();

    try {
        if (isEdit) {
            await api.updateEntityType(name, data);
            showNotification(`Tipo entità "${name}" aggiornato.`, 'success');
        } else {
            await api.createEntityType(data);
            showNotification(`Tipo entità "${name}" creato.`, 'success');
        }
        entityTypeModalInstance?.hide();
        await loadEntityTypes(); // Reload the list
    } catch (error) {
        showNotification(`Errore durante il salvataggio: ${error.message}`, 'danger');
    } finally {
        saveBtn.disabled = false;
        saveBtn.textContent = isEdit ? 'Salva Modifiche' : 'Crea';
        hideLoading();
        formEl.classList.remove('was-validated');
    }
}

// --- Deletion ---
function showDeleteConfirmation(entity) {
    entityToDeleteName = entity.name;
    entityNameToDeleteEl.textContent = entity.name;
    // Basic check if it's custom (backend enforces this anyway)
    deleteWarningEl?.classList.add('d-none'); // Reset warning
    confirmDeleteBtn.disabled = false;

    // Optional: Add a check here if the entity is in use (would require another API endpoint or passing usage data)
    // For now, rely on backend 409 response.
    // deleteWarningEl?.classList.remove('d-none'); // If in use

    confirmDeleteModalInstance?.show();
}

async function handleDeleteConfirmation() {
    if (!entityToDeleteName) return;

    confirmDeleteBtn.disabled = true;
    confirmDeleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Eliminazione...';
    showLoading();

    try {
        await api.deleteEntityType(entityToDeleteName);
        showNotification(`Tipo entità "${entityToDeleteName}" eliminato.`, 'success');
        confirmDeleteModalInstance?.hide();
        await loadEntityTypes(); // Reload list
    } catch (error) {
         if (error.message && error.message.includes('in use')) { // Check for specific error messages if backend provides them
             showNotification(`Impossibile eliminare "${entityToDeleteName}": è in uso nelle annotazioni.`, 'danger');
         } else if (error.message && error.message.includes('predefinito')) {
              showNotification(`Impossibile eliminare "${entityToDeleteName}": è un tipo predefinito.`, 'warning');
         }
         else {
            showNotification(`Errore durante l'eliminazione: ${error.message}`, 'danger');
         }
        confirmDeleteModalInstance?.hide(); // Still hide modal on error
    } finally {
        confirmDeleteBtn.disabled = false;
        confirmDeleteBtn.innerHTML = 'Elimina';
        entityToDeleteName = null;
        hideLoading();
    }
}

// --- Pattern Testing ---
async function handleTestPatterns() {
    const patternsVal = patternsInput.value.trim();
    const textVal = testTextarea.value;

    if (!patternsVal || !textVal) {
        showNotification('Inserisci almeno un pattern e del testo di esempio.', 'warning');
        return;
    }

    const lines = patternsVal.split('\n').filter(line => line.trim() !== '');
    if (lines.length === 0) {
         showNotification('Nessun pattern valido inserito.', 'warning');
         return;
    }

    // Test only the first pattern for simplicity, or loop through all
    const patternToTest = lines[0];
    testBtn.disabled = true;
    testBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Test...';

    try {
        // Validate regex locally first
        new RegExp(patternToTest);

        const result = await api.testPattern(patternToTest, textVal);
        matchCountEl.textContent = result.matches_count || 0;
        testOutputEl.textContent = JSON.stringify(result.matches || [], null, 2);
        testResultsEl.classList.remove('d-none');
    } catch (error) {
        showNotification(`Errore nel test del pattern: ${error.message}`, 'danger');
        testOutputEl.textContent = `Errore: ${error.message}`;
        matchCountEl.textContent = '0';
        testResultsEl.classList.remove('d-none');
    } finally {
         testBtn.disabled = false;
         testBtn.innerHTML = '<i class="fas fa-vial me-2"></i>Testa';
    }
}


// --- Event Listeners ---
function setupEventListeners() {
    searchInput?.addEventListener('input', filterAndRender);
    categoryFilter?.addEventListener('change', filterAndRender);

    document.getElementById('add-entity-type-btn')?.addEventListener('click', showCreateForm);
    document.getElementById('add-first-entity')?.addEventListener('click', showCreateForm); // Button in empty state

    formEl?.addEventListener('submit', handleFormSubmit);
    colorInput?.addEventListener('input', updateColorPreview);

    testBtn?.addEventListener('click', handleTestPatterns);

    confirmDeleteBtn?.addEventListener('click', handleDeleteConfirmation);
}

// --- Public Init ---
export function initEntityManager() {
    console.log('Initializing Entity Manager Page...');
    cacheDOMElements();
    setupEventListeners();
    loadEntityTypes(); // Initial load
}