/**
 * annotator.js
 * Logic for the annotation page.
 */
import { api } from './api.js';
import { showNotification, showLoading, hideLoading, getTextContent, setTextContent } from './ui.js';
// Assuming highlightingEngine.js exports necessary functions/class
import { HighlightingEngine } from './highlightingEngine.js'; // Adjust import as needed

// --- State ---
let currentDocId = null;
let annotations = [];
let entityTypes = []; // Store full entity type data
let entityTypesMap = new Map(); // For quick lookup by ID
let selectedEntityTypeId = null;
let isEditingText = false;
let originalTextContent = '';
let currentZoom = 1;
let currentSort = 'position'; // 'position' or 'type'
let currentSearchTerm = '';
let highlightingEngine = null;
let clearByTypeModalInstance = null;

// --- DOM Elements ---
let entityTypeListEl, textContentEl, annotationsContainerEl, annotationCountEl, noAnnotationsMsgEl;
let autoAnnotateBtn, clearSelectionBtn, editBtn, saveBtn, cancelBtn, editControlsEl;
let zoomInBtn, zoomOutBtn, zoomResetBtn;
let sortPositionBtn, sortTypeBtn, searchInput;
let clearAllBtn, clearByTypeModalEl, clearByTypeSelect, confirmClearByTypeBtn;

// --- Initialization ---
function cacheDOMElements() {
    entityTypeListEl = document.getElementById('entityTypeList');
    textContentEl = document.getElementById('text-content');
    annotationsContainerEl = document.getElementById('annotationsContainer');
    annotationCountEl = document.getElementById('annotation-count');
    noAnnotationsMsgEl = document.getElementById('no-annotations-message');

    autoAnnotateBtn = document.getElementById('auto-annotate-btn');
    clearSelectionBtn = document.getElementById('clear-selection-btn');
    editBtn = document.getElementById('edit-text-btn');
    saveBtn = document.getElementById('save-text-btn');
    cancelBtn = document.getElementById('cancel-edit-btn');
    editControlsEl = document.getElementById('edit-controls');

    zoomInBtn = document.getElementById('zoom-in-btn');
    zoomOutBtn = document.getElementById('zoom-out-btn');
    zoomResetBtn = document.getElementById('zoom-reset-btn');

    const sortBtns = document.querySelectorAll('.sort-annotations-btn');
    sortPositionBtn = Array.from(sortBtns).find(btn => btn.dataset.sort === 'position');
    sortTypeBtn = Array.from(sortBtns).find(btn => btn.dataset.sort === 'type');
    searchInput = document.getElementById('search-annotations-input');

    clearAllBtn = document.getElementById('clear-all-annotations-btn');
    clearByTypeModalEl = document.getElementById('clearByTypeModal');
    clearByTypeSelect = document.getElementById('clear-entity-type-select');
    confirmClearByTypeBtn = document.getElementById('confirm-clear-type-btn');

    if (clearByTypeModalEl) clearByTypeModalInstance = new bootstrap.Modal(clearByTypeModalEl);
}

function loadInitialData() {
    currentDocId = textContentEl?.dataset.docId;
    const annotationsScript = document.getElementById('initial-annotations');
    const entityTypesScript = document.getElementById('entity-types-data');

    try {
        if (annotationsScript) {
            annotations = JSON.parse(annotationsScript.textContent || '[]') || [];
            // Ensure annotations have unique IDs if missing from backend/storage
            annotations.forEach((ann, index) => {
                if (!ann.id) ann.id = `temp_${Date.now()}_${index}`;
            });
        }
        if (entityTypesScript) {
            entityTypes = JSON.parse(entityTypesScript.textContent || '[]') || [];
            entityTypesMap = new Map(entityTypes.map(et => [et.id, et]));
        }
    } catch (e) {
        console.error("Error parsing initial data:", e);
        showNotification("Errore nel caricamento dei dati iniziali.", "danger");
        annotations = [];
        entityTypes = [];
        entityTypesMap = new Map();
    }
}

// --- Rendering & UI Updates ---
function renderAnnotationList() {
    if (!annotationsContainerEl || !annotationCountEl) return;
    annotationsContainerEl.innerHTML = ''; // Clear list

    // 1. Sort
    const sortedAnnotations = [...annotations].sort((a, b) => {
        if (currentSort === 'type') {
            const typeA = entityTypesMap.get(a.type)?.name || a.type;
            const typeB = entityTypesMap.get(b.type)?.name || b.type;
            if (typeA < typeB) return -1;
            if (typeA > typeB) return 1;
        }
        // Default or fallback to position sort
        return a.start - b.start;
    });

    // 2. Filter
    const searchTerm = currentSearchTerm.toLowerCase();
    const filteredAnnotations = searchTerm
        ? sortedAnnotations.filter(ann => ann.text.toLowerCase().includes(searchTerm))
        : sortedAnnotations;

    // 3. Render
    if (filteredAnnotations.length === 0) {
        noAnnotationsMsgEl?.classList.remove('d-none');
    } else {
        noAnnotationsMsgEl?.classList.add('d-none');
        const template = document.getElementById('annotation-item-template');
        if (!template) return;

        filteredAnnotations.forEach(ann => {
            const clone = template.content.cloneNode(true);
            const itemEl = clone.querySelector('.annotation-item');
            const typeBadge = clone.querySelector('.annotation-type');
            const textEl = clone.querySelector('.annotation-text');
            const jumpBtn = clone.querySelector('.jump-to-btn');
            const deleteBtn = clone.querySelector('.delete-annotation-btn');

            const entityType = entityTypesMap.get(ann.type);

            itemEl.dataset.annotationId = ann.id;
            itemEl.dataset.start = ann.start;
            itemEl.dataset.end = ann.end;
            itemEl.dataset.type = ann.type;

            typeBadge.textContent = entityType?.name || ann.type;
            typeBadge.style.backgroundColor = entityType?.color || '#6c757d';
            itemEl.style.borderLeftColor = entityType?.color || '#6c757d';

            textEl.textContent = ann.text;

            jumpBtn.addEventListener('click', () => handleJumpToAnnotation(ann.id));
            deleteBtn.addEventListener('click', () => handleDeleteAnnotation(ann.id));

            annotationsContainerEl.appendChild(clone);
        });
    }

    // Update total count
    annotationCountEl.textContent = annotations.length;
    updateEntityTypeCounters();
}

function updateEntityTypeCounters() {
    const counters = entityTypeListEl.querySelectorAll('.entity-counter');
    const counts = annotations.reduce((acc, ann) => {
        acc[ann.type] = (acc[ann.type] || 0) + 1;
        return acc;
    }, {});

    counters.forEach(counter => {
        const type = counter.dataset.countType;
        counter.textContent = counts[type] || 0;
    });
}

function updateHighlighting() {
    if (highlightingEngine && textContentEl) {
        highlightingEngine.applyHighlights(textContentEl, annotations, entityTypesMap);
    }
}

function setActiveEntityType(typeId) {
    selectedEntityTypeId = typeId;
    entityTypeListEl.querySelectorAll('.entity-type').forEach(el => {
        el.classList.toggle('selected', el.dataset.entityType === typeId);
    });
    console.log("Selected entity type:", typeId);
}

function clearSelection() {
    window.getSelection()?.removeAllRanges();
    setActiveEntityType(null); // Also deselect the type
}

function updateZoom() {
    textContentEl.style.fontSize = `${currentZoom * 100}%`; // Use percentage for scaling
}

// --- Annotation Actions ---
async function handleTextSelection() {
    if (isEditingText || !selectedEntityTypeId) return;

    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return;

    const range = selection.getRangeAt(0);
    const container = range.commonAncestorContainer;

    // Ensure selection is within the text content element
    if (!textContentEl.contains(container)) {
        console.warn("Selection outside text content area.");
        clearSelection();
        return;
    }

    // Calculate start and end offsets relative to textContentEl
    // This is the tricky part and depends heavily on how highlightingEngine works.
    // A common approach is to create a temporary range spanning the whole content
    // and compare positions.
    const preSelectionRange = document.createRange();
    preSelectionRange.selectNodeContents(textContentEl);
    preSelectionRange.setEnd(range.startContainer, range.startOffset);
    const start = preSelectionRange.toString().length;
    const end = start + range.toString().length;
    const text = range.toString();

    if (!text.trim()) { // Ignore whitespace-only selections
        clearSelection();
        return;
    }

    const newAnnotation = {
        id: `temp_${Date.now()}`, // Temporary ID until saved
        start: start,
        end: end,
        text: text,
        type: selectedEntityTypeId
    };

    console.log("Creating annotation:", newAnnotation);
    selection.removeAllRanges(); // Clear selection immediately
    showLoading();

    try {
        // Save the annotation via API
        const savedAnnotation = await api.saveAnnotation(currentDocId, newAnnotation);
        // Replace temporary annotation with saved one (which should have a real ID)
        annotations.push(savedAnnotation.annotation);
        renderAnnotationList();
        updateHighlighting();
        showNotification(`Annotazione "${savedAnnotation.annotation.type}" creata.`, 'success');
    } catch (error) {
        showNotification(`Errore creazione annotazione: ${error.message}`, 'danger');
        // Optionally remove the temporary annotation if it was added optimistically
    } finally {
        hideLoading();
        // Deselect type after successful annotation? Optional UX choice.
        // setActiveEntityType(null);
    }
}

async function handleDeleteAnnotation(annotationId) {
    const annotationIndex = annotations.findIndex(ann => ann.id === annotationId);
    if (annotationIndex === -1) return;

    const annotation = annotations[annotationIndex];

    // Optimistic UI update
    annotations.splice(annotationIndex, 1);
    renderAnnotationList();
    updateHighlighting();
    showLoading(); // Show loading after optimistic update for perceived speed

    try {
        await api.deleteAnnotation(currentDocId, annotationId);
        showNotification(`Annotazione "${annotation.type}" eliminata.`, 'success');
    } catch (error) {
        showNotification(`Errore eliminazione annotazione: ${error.message}`, 'danger');
        // Revert UI update if deletion failed
        annotations.splice(annotationIndex, 0, annotation); // Add it back
        renderAnnotationList();
        updateHighlighting();
    } finally {
        hideLoading();
    }
}

function handleJumpToAnnotation(annotationId) {
    const annotation = annotations.find(ann => ann.id === annotationId);
    if (!annotation || !textContentEl) return;

    // Highlight in list
    annotationsContainerEl.querySelectorAll('.annotation-item').forEach(el => {
        el.classList.toggle('selected', el.dataset.annotationId === annotationId);
    });

    // Scroll and highlight in text (requires highlightingEngine support)
    if (highlightingEngine) {
        highlightingEngine.highlightAnnotation(annotationId, textContentEl); // Pass textContentEl
    } else {
        // Fallback: Scroll to approximate position
        // This is less accurate due to potential HTML structure changes by highlighting
        const approxCharHeight = 20; // Estimate
        const approxScroll = (annotation.start / textContentEl.textContent.length) * textContentEl.scrollHeight - (textContentEl.clientHeight / 2);
        textContentEl.scrollTo({ top: approxScroll, behavior: 'smooth' });
    }
}

async function handleAutoAnnotate() {
    const text = getTextContent(textContentEl); // Use helper
    if (!text) return;

    autoAnnotateBtn.disabled = true;
    autoAnnotateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Riconoscimento...';
    showLoading();

    try {
        const result = await api.recognizeEntities(text);
        const recognizedEntities = result.entities || [];
        if (recognizedEntities.length === 0) {
            showNotification("Nessuna nuova entità riconosciuta automaticamente.", "info");
            return;
        }

        let addedCount = 0;
        const newAnnotations = [];

        // Simple strategy: Add only non-overlapping new entities
        recognizedEntities.forEach(recEntity => {
            const overlaps = annotations.some(existingAnn =>
                (recEntity.start < existingAnn.end && recEntity.end > existingAnn.start)
            );
            if (!overlaps && entityTypesMap.has(recEntity.type)) { // Check if type is valid
                 newAnnotations.push({
                    // id: `temp_auto_${Date.now()}_${addedCount}`, // Assign temp ID
                    start: recEntity.start,
                    end: recEntity.end,
                    text: recEntity.text,
                    type: recEntity.type
                 });
                 addedCount++;
            }
        });

        if (newAnnotations.length > 0) {
             // Save new annotations (could be one API call if backend supports batch)
             // For simplicity, save one by one here, but batch is better
             for (const newAnn of newAnnotations) {
                 try {
                    const saved = await api.saveAnnotation(currentDocId, newAnn);
                    annotations.push(saved.annotation);
                 } catch (saveError) {
                     console.error("Error saving auto-annotation:", saveError);
                     // Decide how to handle partial failures
                 }
             }
            renderAnnotationList();
            updateHighlighting();
            showNotification(`${addedCount} nuove annotazioni aggiunte automaticamente.`, 'success');
        } else {
            showNotification("Nessuna nuova annotazione non sovrapposta trovata.", "info");
        }

    } catch (error) {
        showNotification(`Errore nel riconoscimento automatico: ${error.message}`, 'danger');
    } finally {
        autoAnnotateBtn.disabled = false;
        autoAnnotateBtn.innerHTML = '<i class="fas fa-magic me-1"></i> Riconoscimento Auto';
        hideLoading();
    }
}

// --- Text Editing ---
function toggleTextEditing(enable) {
    isEditingText = enable;
    textContentEl.contentEditable = isEditingText ? 'true' : 'false';
    textContentEl.classList.toggle('editing', isEditingText);
    editControlsEl?.classList.toggle('d-none', !isEditingText);
    editBtn?.classList.toggle('d-none', isEditingText); // Hide edit button when editing

    if (isEditingText) {
        originalTextContent = getTextContent(textContentEl); // Store original text
        // Remove highlighting during editing for clarity
        if (highlightingEngine) highlightingEngine.removeHighlighting(textContentEl);
        textContentEl.focus();
        // Warn user about annotation loss/invalidation
        if (annotations.length > 0) {
            showNotification("Attenzione: Modificare il testo invaliderà le annotazioni esistenti.", "warning");
        }
    } else {
        // Re-apply highlighting if editing is cancelled or finished without saving changes that clear annotations
        updateHighlighting();
    }
}

async function saveTextChanges() {
    const newText = getTextContent(textContentEl); // Use helper
    if (newText === originalTextContent) {
        toggleTextEditing(false); // No changes, just exit edit mode
        return;
    }

    // Confirm potentially invalidating annotations
    if (annotations.length > 0) {
        if (!confirm("Salvare le modifiche al testo eliminerà TUTTE le annotazioni esistenti per questo documento. Continuare?")) {
            return; // User cancelled
        }
    }

    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Salvataggio...';
    showLoading();

    try {
        // 1. Update document content
        await api.updateDocument(currentDocId, { content: newText });

        // 2. Clear existing annotations (as agreed in the confirm dialog)
        if (annotations.length > 0) {
            await api.clearAnnotations(currentDocId);
            annotations = []; // Clear local state
        }

        showNotification("Testo aggiornato. Annotazioni precedenti eliminate.", "success");
        originalTextContent = newText; // Update original text baseline
        toggleTextEditing(false);
        renderAnnotationList(); // Update list (will be empty)
        updateHighlighting(); // Update highlighting (will be empty)

    } catch (error) {
        showNotification(`Errore durante il salvataggio del testo: ${error.message}`, 'danger');
        // Optionally revert text content?
        // setTextContent(textContentEl, originalTextContent);
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="fas fa-save"></i> Salva';
        hideLoading();
    }
}

function cancelTextEditing() {
    setTextContent(textContentEl, originalTextContent); // Revert text
    toggleTextEditing(false);
}

// --- Other Actions ---
function handleZoom(direction) {
    const step = 0.1;
    if (direction === 'in') {
        currentZoom += step;
    } else if (direction === 'out') {
        currentZoom = Math.max(0.5, currentZoom - step); // Set a minimum zoom
    } else { // reset
        currentZoom = 1;
    }
    updateZoom();
}

function handleSort(type) {
    currentSort = type;
    // Update button active states
    sortPositionBtn?.classList.toggle('active', type === 'position');
    sortTypeBtn?.classList.toggle('active', type === 'type');
    renderAnnotationList();
}

function handleSearch(event) {
    currentSearchTerm = event.target.value;
    renderAnnotationList();
}

async function handleClearAllAnnotations() {
     if (annotations.length === 0) {
         showNotification("Nessuna annotazione da eliminare.", "info");
         return;
     }
     if (!confirm("Sei sicuro di voler eliminare TUTTE le annotazioni per questo documento?")) {
         return;
     }

     showLoading();
     try {
         await api.clearAnnotations(currentDocId);
         annotations = [];
         renderAnnotationList();
         updateHighlighting();
         showNotification("Tutte le annotazioni sono state eliminate.", "success");
     } catch (error) {
         showNotification(`Errore durante l'eliminazione: ${error.message}`, 'danger');
     } finally {
         hideLoading();
     }
}

async function handleClearAnnotationsByType() {
    const selectedType = clearByTypeSelect.value;
    if (!selectedType) {
        showNotification("Seleziona un tipo di entità da eliminare.", "warning");
        return;
    }

    confirmClearByTypeBtn.disabled = true;
    confirmClearByTypeBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Eliminazione...';
    showLoading();

    try {
        await api.clearAnnotations(currentDocId, selectedType);
        // Update local state
        annotations = annotations.filter(ann => ann.type !== selectedType);
        renderAnnotationList();
        updateHighlighting();
        showNotification(`Annotazioni di tipo "${entityTypesMap.get(selectedType)?.name || selectedType}" eliminate.`, "success");
        clearByTypeModalInstance?.hide();
    } catch (error) {
         showNotification(`Errore durante l'eliminazione per tipo: ${error.message}`, 'danger');
    } finally {
        confirmClearByTypeBtn.disabled = false;
        confirmClearByTypeBtn.innerHTML = '<i class="fas fa-trash-alt me-2"></i>Elimina annotazioni';
        hideLoading();
    }
}


// --- Event Listeners Setup ---
function setupEventListeners() {
    // Entity Type Selection
    entityTypeListEl?.addEventListener('click', (event) => {
        const target = event.target.closest('.entity-type');
        if (target) {
            const typeId = target.dataset.entityType;
            setActiveEntityType(typeId);
        }
    });

    // Text Selection for Annotation
    textContentEl?.addEventListener('mouseup', handleTextSelection);

    // Buttons
    autoAnnotateBtn?.addEventListener('click', handleAutoAnnotate);
    clearSelectionBtn?.addEventListener('click', clearSelection);
    editBtn?.addEventListener('click', () => toggleTextEditing(true));
    saveBtn?.addEventListener('click', saveTextChanges);
    cancelBtn?.addEventListener('click', cancelTextEditing);
    zoomInBtn?.addEventListener('click', () => handleZoom('in'));
    zoomOutBtn?.addEventListener('click', () => handleZoom('out'));
    zoomResetBtn?.addEventListener('click', () => handleZoom('reset'));
    sortPositionBtn?.addEventListener('click', () => handleSort('position'));
    sortTypeBtn?.addEventListener('click', () => handleSort('type'));
    clearAllBtn?.addEventListener('click', handleClearAllAnnotations);
    confirmClearByTypeBtn?.addEventListener('click', handleClearAnnotationsByType);

    // Search Input
    searchInput?.addEventListener('input', handleSearch);

    // Clear by Type Modal Logic
    clearByTypeSelect?.addEventListener('change', (event) => {
        confirmClearByTypeBtn.disabled = !event.target.value;
    });

    // Registro dei tasti di scelta rapida con debug
    setupKeyboardShortcuts();
}

function setupKeyboardShortcuts() {
    console.log("Registrazione dei tasti di scelta rapida...");
    
    // Rimuovi eventuali gestori di eventi esistenti per evitare duplicazioni
    document.removeEventListener('keydown', handleKeyDown);
    
    // Aggiungi il nuovo gestore di eventi
    document.addEventListener('keydown', handleKeyDown);
    
    console.log("Tasti di scelta rapida registrati con successo");
}

function handleKeyDown(event) {
    // Non processare i keydown se stiamo modificando del testo o ci sono modali aperti
    if (isEditingText || 
        document.querySelector('.modal.show') || 
        event.target.tagName === 'INPUT' || 
        event.target.tagName === 'TEXTAREA') {
        return;
    }

    console.log(`Tasto premuto: ${event.key}, Alt: ${event.altKey}, Ctrl: ${event.ctrlKey}, Shift: ${event.shiftKey}`);

    // Deselect type/selection on Escape
    if (event.key === 'Escape') {
        console.log("Escape premuto: eseguo clearSelection()");
        clearSelection();
        event.preventDefault();
    }
    
    // Select entity type with Alt + Number
    if (event.altKey && !isNaN(parseInt(event.key))) {
        const index = parseInt(event.key) - 1;
        console.log(`Alt+${event.key} premuto, cerco il tipo di entità all'indice ${index}`);
        
        const entityTypeElements = entityTypeListEl?.querySelectorAll('.entity-type');
        
        if (entityTypeElements && index >= 0 && index < entityTypeElements.length) {
            const typeElement = entityTypeElements[index];
            const entityTypeId = typeElement.dataset.entityType;
            console.log(`Trovato tipo di entità: ${entityTypeId}`);
            
            event.preventDefault();
            setActiveEntityType(entityTypeId);
        } else {
            console.log(`Nessun tipo di entità trovato all'indice ${index}`);
        }
    }
    
    // Alt+A for auto-annotate
    if (event.altKey && event.key.toLowerCase() === 'a') {
        console.log("Alt+A premuto: eseguo handleAutoAnnotate()");
        event.preventDefault();
        handleAutoAnnotate();
    }
    
    // Ctrl+Z per annullare la selezione (alternativa a Escape)
    if (event.ctrlKey && event.key.toLowerCase() === 'z') {
        console.log("Ctrl+Z premuto: eseguo clearSelection()");
        event.preventDefault();
        clearSelection();
    }
}


// --- Public Init ---
export function initAnnotator() {
    console.log('Initializing Annotator Page...');
    cacheDOMElements();
    
    // First check for DOM elements
    if (!textContentEl) {
        console.error("Missing text content element - ensure element with id 'text-content' exists in DOM");
        return;
    }
    
    // Then load initial data (which sets currentDocId)
    loadInitialData();

    // Now check for document ID
    if (!currentDocId) {
        console.error("Missing document ID - ensure text-content element has data-doc-id attribute");
        return;
    }

    // Verifica degli elementi dell'interfaccia per i key binding
    if (entityTypeListEl) {
        const entityTypes = entityTypeListEl.querySelectorAll('.entity-type');
        console.log(`Trovati ${entityTypes.length} tipi di entità per i tasti di scelta rapida`);
    } else {
        console.warn("Entity type list element not found - keyboard shortcuts for entity selection won't work");
    }

    // Initialize Highlighting Engine
    highlightingEngine = new HighlightingEngine();

    setupEventListeners();
    renderAnnotationList();
    updateHighlighting();
    updateZoom();
    handleSort(currentSort);
    
    // Aggiungiamo un messaggio info all'utente sui tasti di scelta rapida disponibili
    showKeyboardShortcutsInfo();
}

function showKeyboardShortcutsInfo() {
    try {
        const message = "Tasti di scelta rapida disponibili: Alt+[1-9] per selezionare un tipo di entità, Alt+A per l'annotazione automatica, Esc per annullare la selezione";
        // Usiamo showNotification se disponibile, altrimenti console.log
        if (typeof showNotification === 'function') {
            showNotification(message, 'info', 'Scorciatoie da tastiera');
        } else {
            console.info(message);
        }
    } catch (error) {
        console.warn("Impossibile mostrare l'informazione sui tasti di scelta rapida:", error);
    }
}
