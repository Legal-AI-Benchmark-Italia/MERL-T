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
// Declare vars, will be assigned in cacheDOMElements
let entityTypeListEl, textContentEl, annotationsContainerEl, annotationCountEl, noAnnotationsMsgEl;
let autoAnnotateBtn, clearSelectionBtn, editBtn, saveBtn, cancelBtn, editControlsEl;
let zoomInBtn, zoomOutBtn, zoomResetBtn;
let sortPositionBtn, sortTypeBtn, searchInput;
let clearAllBtn, clearByTypeModalEl, clearByTypeSelect, confirmClearByTypeBtn;

// --- Initialization ---
function cacheDOMElements() {
    console.log("Caching DOM elements...");
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

    // Crucial Check: Ensure required elements are found
    if (!textContentEl) {
        console.error("FATAL: textContentEl (#text-content) not found!");
        throw new Error("Required element #text-content is missing.");
    }
     if (!entityTypeListEl) {
        console.warn("Warning: entityTypeListEl (#entityTypeList) not found. Entity selection shortcuts won't work.");
    }
     if (clearByTypeModalEl) {
         try {
            clearByTypeModalInstance = new bootstrap.Modal(clearByTypeModalEl);
         } catch(e) {
             console.error("Error initializing Bootstrap Modal:", e);
             clearByTypeModalInstance = null; // Prevent errors later
         }
     } else {
        console.warn("Warning: clearByTypeModalEl (#clearByTypeModal) not found. Clear by type functionality disabled.");
     }
    console.log("DOM elements cached.");
}

function loadInitialData() {
    console.log("Loading initial data...");
    // Get docId ONLY AFTER caching elements
    currentDocId = textContentEl?.dataset.docId;
    if (!currentDocId) {
         console.error("FATAL: data-doc-id attribute missing on #text-content element!");
         throw new Error("Document ID is missing.");
    }
    console.log("Document ID:", currentDocId);

    const annotationsScript = document.getElementById('initial-annotations');
    const entityTypesScript = document.getElementById('entity-types-data');

    try {
        if (annotationsScript) {
            annotations = JSON.parse(annotationsScript.textContent || '[]') || [];
            annotations.forEach((ann, index) => {
                if (!ann.id) ann.id = `temp_${Date.now()}_${index}`; // Ensure IDs exist
            });
            console.log(`Loaded ${annotations.length} annotations.`);
        } else {
            console.warn("Initial annotations script tag (#initial-annotations) not found.");
        }
        if (entityTypesScript) {
            entityTypes = JSON.parse(entityTypesScript.textContent || '[]') || [];
            entityTypesMap = new Map(entityTypes.map(et => [et.id, et]));
            console.log(`Loaded ${entityTypes.length} entity types.`);
             // Populate clear by type select
             if (clearByTypeSelect) {
                 clearByTypeSelect.innerHTML = '<option value="">Seleziona tipo...</option>'; // Reset
                 entityTypes.forEach(et => {
                     const option = document.createElement('option');
                     option.value = et.id;
                     option.textContent = et.name;
                     clearByTypeSelect.appendChild(option);
                 });
             }
        } else {
            console.warn("Entity types script tag (#entity-types-data) not found.");
        }
    } catch (e) {
        console.error("Error parsing initial data:", e);
        showNotification("Errore nel caricamento dei dati iniziali.", "danger");
        annotations = [];
        entityTypes = [];
        entityTypesMap = new Map();
    }
    console.log("Initial data loaded.");
}

// --- Rendering & UI Updates ---
function renderAnnotationList() {
    if (!annotationsContainerEl || !annotationCountEl) return;
    // console.log("Rendering annotation list..."); // Can be noisy, enable if needed
    annotationsContainerEl.innerHTML = ''; // Clear list

    // 1. Sort
    const sortedAnnotations = [...annotations].sort((a, b) => {
        if (currentSort === 'type') {
            const typeA = entityTypesMap.get(a.type)?.name || a.type;
            const typeB = entityTypesMap.get(b.type)?.name || b.type;
            if (typeA.toLowerCase() < typeB.toLowerCase()) return -1;
            if (typeA.toLowerCase() > typeB.toLowerCase()) return 1;
        }
        // Default or fallback to position sort
        return a.start - b.start;
    });

    // 2. Filter
    const searchTerm = currentSearchTerm.toLowerCase().trim();
    const filteredAnnotations = searchTerm
        ? sortedAnnotations.filter(ann => {
            const entityName = entityTypesMap.get(ann.type)?.name.toLowerCase() || '';
            const annotationText = ann.text.toLowerCase();
            return annotationText.includes(searchTerm) || entityName.includes(searchTerm);
          })
        : sortedAnnotations;

    // 3. Render
    if (filteredAnnotations.length === 0) {
        noAnnotationsMsgEl?.classList.remove('d-none');
    } else {
        noAnnotationsMsgEl?.classList.add('d-none');
        const template = document.getElementById('annotation-item-template');
        if (!template) {
            console.error("Annotation item template (#annotation-item-template) not found.");
            return;
        }

        filteredAnnotations.forEach(ann => {
            try { // Add try-catch for robustness during rendering loop
                const clone = template.content.cloneNode(true);
                const itemEl = clone.querySelector('.annotation-item');
                const typeBadge = clone.querySelector('.annotation-type');
                const textEl = clone.querySelector('.annotation-text');
                const jumpBtn = clone.querySelector('.jump-to-btn');
                const deleteBtn = clone.querySelector('.delete-annotation-btn');

                if (!itemEl || !typeBadge || !textEl || !jumpBtn || !deleteBtn) {
                   console.warn("Skipping annotation render: Template structure incorrect for", ann);
                   return; // Skip this item if template parts are missing
                }

                const entityType = entityTypesMap.get(ann.type);

                itemEl.dataset.annotationId = ann.id;
                itemEl.dataset.start = ann.start;
                itemEl.dataset.end = ann.end;
                itemEl.dataset.type = ann.type; // Keep type id for potential filtering

                typeBadge.textContent = entityType?.name || ann.type || 'N/D'; // Fallback name
                const color = entityType?.color || '#6c757d'; // Default grey color
                typeBadge.style.backgroundColor = color;
                itemEl.style.borderLeftColor = color;

                textEl.textContent = ann.text;

                jumpBtn.addEventListener('click', () => handleJumpToAnnotation(ann.id));
                deleteBtn.addEventListener('click', () => handleDeleteAnnotation(ann.id));

                annotationsContainerEl.appendChild(clone);
            } catch(renderError) {
                console.error("Error rendering annotation item:", ann, renderError);
            }
        });
    }

    // Update total count
    annotationCountEl.textContent = annotations.length;
    updateEntityTypeCounters();
    // console.log("Annotation list rendered."); // Enable if needed
}

function updateEntityTypeCounters() {
    const counters = entityTypeListEl?.querySelectorAll('.entity-counter');
    if (!counters || counters.length === 0) return; // Check if counters exist

    const counts = annotations.reduce((acc, ann) => {
        acc[ann.type] = (acc[ann.type] || 0) + 1;
        return acc;
    }, {});

    counters.forEach(counter => {
        const typeId = counter.dataset.countType; // Assuming dataset.countType holds the entity type ID
        if (typeId) { // Ensure the dataset attribute exists
            counter.textContent = counts[typeId] || 0;
        } else {
            console.warn("Entity counter element missing data-count-type attribute", counter);
        }
    });
}

function updateHighlighting() {
    if (highlightingEngine && textContentEl && !isEditingText) { // Only highlight if not editing
        // console.log("Applying highlights..."); // Enable if needed
        try {
            highlightingEngine.applyHighlights(textContentEl, annotations, entityTypesMap);
            // console.log("Highlights applied."); // Enable if needed
        } catch (e) {
            console.error("Error applying highlights:", e);
            showNotification("Errore nell'applicare le evidenziazioni.", "danger");
        }
    } else if (isEditingText) {
        // console.log("Skipping highlighting while editing."); // Enable if needed
    }
}

function setActiveEntityType(typeId) {
    selectedEntityTypeId = typeId;
    entityTypeListEl?.querySelectorAll('.entity-type').forEach(el => {
        // Use strict equality check for the dataset attribute
        el.classList.toggle('selected', el.dataset.entityType === typeId);
    });
    console.log("Selected entity type ID:", typeId); // Log the ID for clarity
     // Provide user feedback
     if (typeId) {
         const typeName = entityTypesMap.get(typeId)?.name || typeId;
         showNotification(`Tipo selezionato: ${typeName}. Seleziona testo per annotare.`, 'info', null, 2000); // Short duration
     }
}

function clearSelection() {
    console.log("Clearing text selection and active entity type.");
    window.getSelection()?.removeAllRanges();
    // Also deselect the type in the UI and state
    if (selectedEntityTypeId) {
        setActiveEntityType(null); // This will set selectedEntityTypeId to null and update UI
    }
}

function updateZoom() {
    if (!textContentEl) return;
    const zoomPercentage = `${currentZoom * 100}%`;
    // console.log(`Updating zoom to: ${zoomPercentage}`); // Enable if needed
    textContentEl.style.fontSize = zoomPercentage;
}

// --- Annotation Actions ---
async function handleTextSelection(event) {
    // Prevent triggering on clicks within existing highlights if they are interactive
    // This depends on how HighlightingEngine adds elements. Example:
    // if (event.target.closest('.highlight-span')) { // Adjust selector if needed
    //     console.log("Clicked on existing highlight, ignoring selection.");
    //     return;
    // }

    if (isEditingText) {
        // console.log("Ignoring text selection while editing."); // Enable if needed
        return;
    }
    if (!selectedEntityTypeId) {
        // console.log("Ignoring text selection, no entity type selected."); // Enable if needed
        return;
    }

    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
        // console.log("Ignoring empty/collapsed selection."); // Enable if needed
        return;
    }

    const range = selection.getRangeAt(0);
    const container = range.commonAncestorContainer;

    // Ensure selection is truly within the editable text content element
    if (!textContentEl || !textContentEl.contains(container)) {
        console.warn("Selection occurred outside #text-content. Ignoring.");
        clearSelection(); // Clear potentially invalid selection state
        return;
    }

    // --- Accurate Offset Calculation ---
    // This remains tricky and depends HEAVILY on HighlightingEngine's output.
    // If HighlightingEngine wraps text in spans, simple textContent length won't work reliably.
    // A more robust approach might involve traversing the DOM nodes within the range.
    // For simplicity, we'll stick to the textContent approach but add warnings.
    // CONSIDER using a library specifically for range/offset calculations if issues persist.

    let start, end, text;
    try {
        // Use the HighlightingEngine's method if it provides one, otherwise fallback
        if (highlightingEngine && typeof highlightingEngine.getRangeOffsets === 'function') {
            ({ start, end } = highlightingEngine.getRangeOffsets(textContentEl, range));
        } else {
            // Fallback (potentially less accurate with complex highlighting)
             console.warn("Using fallback offset calculation. May be inaccurate if highlighting modifies DOM structure significantly.");
             const preSelectionRange = document.createRange();
             preSelectionRange.selectNodeContents(textContentEl);
             preSelectionRange.setEnd(range.startContainer, range.startOffset);
             // Use textContent for offset calculation - assumes highlighting doesn't add non-visible chars affecting length
             start = preSelectionRange.toString().length;
             end = start + range.toString().length;
        }
        text = range.toString();

    } catch (offsetError) {
        console.error("Error calculating selection offsets:", offsetError);
        showNotification("Errore nel calcolare la posizione della selezione.", "danger");
        selection.removeAllRanges();
        return;
    }

    // --- End Offset Calculation ---


    if (!text.trim()) { // Ignore whitespace-only selections
        console.log("Ignoring whitespace-only selection.");
        selection.removeAllRanges(); // Clear the visual selection
        return;
    }

    const newAnnotation = {
        // No ID needed here, backend should assign it
        start: start,
        end: end,
        text: text,
        type: selectedEntityTypeId // Use the currently selected type ID
    };

    console.log("Attempting to create annotation:", newAnnotation);
    selection.removeAllRanges(); // Clear selection immediately after getting data
    showLoading("Salvataggio annotazione...");

    try {
        // Save the annotation via API
        const savedAnnotationResult = await api.saveAnnotation(currentDocId, newAnnotation);

        if (!savedAnnotationResult || !savedAnnotationResult.annotation) {
             throw new Error("API response did not contain the saved annotation.");
        }
        const savedAnnotation = savedAnnotationResult.annotation;

        // Ensure the saved annotation has necessary fields (id, start, end, text, type)
        if (!savedAnnotation.id || savedAnnotation.start == null || savedAnnotation.end == null || !savedAnnotation.text || !savedAnnotation.type) {
            console.error("Received invalid annotation data from API:", savedAnnotation);
            throw new Error("Dati annotazione ricevuti dal server non validi.");
        }


        // Add the VERIFIED annotation from the server response
        annotations.push(savedAnnotation);
        renderAnnotationList(); // Re-render the list
        updateHighlighting(); // Update highlights in the text
        showNotification(`Annotazione "${entityTypesMap.get(savedAnnotation.type)?.name || savedAnnotation.type}" creata.`, 'success');
    } catch (error) {
        console.error("Error saving annotation:", error);
        // More specific error message if available from api.js
        const message = error.response?.data?.message || error.message || "Errore sconosciuto";
        showNotification(`Errore creazione annotazione: ${message}`, 'danger');
        // No need to remove temporary annotation as we didn't add one optimistically
    } finally {
        hideLoading();
        // UX Choice: Keep the entity type selected or clear it? Clearing it might be safer.
        // setActiveEntityType(null); // Uncomment this line to clear type after successful annotation
    }
}

async function handleDeleteAnnotation(annotationId) {
    const annotationIndex = annotations.findIndex(ann => ann.id === annotationId);
    if (annotationIndex === -1) {
        console.warn(`Annotation with ID ${annotationId} not found for deletion.`);
        return;
    }

    const annotationToDelete = annotations[annotationIndex];
    const typeName = entityTypesMap.get(annotationToDelete.type)?.name || annotationToDelete.type;

    // Optional: Ask for confirmation
    // if (!confirm(`Sei sicuro di voler eliminare l'annotazione "${typeName}": "${annotationToDelete.text}"?`)) {
    //     return;
    // }

    // Optimistic UI update
    annotations.splice(annotationIndex, 1);
    renderAnnotationList();
    updateHighlighting();
    showLoading("Eliminazione annotazione..."); // Show loading AFTER optimistic update

    try {
        await api.deleteAnnotation(currentDocId, annotationId);
        showNotification(`Annotazione "${typeName}" eliminata.`, 'success');
    } catch (error) {
        console.error(`Error deleting annotation ${annotationId}:`, error);
        showNotification(`Errore eliminazione annotazione: ${error.message}`, 'danger');
        // Revert UI update if deletion failed
        annotations.splice(annotationIndex, 0, annotationToDelete); // Add it back at the original position
        renderAnnotationList();
        updateHighlighting();
    } finally {
        hideLoading();
    }
}

function handleJumpToAnnotation(annotationId) {
    const annotation = annotations.find(ann => ann.id === annotationId);
    if (!annotation || !textContentEl) return;
    console.log("Jumping to annotation:", annotationId, annotation);

    // 1. Highlight in the list
    annotationsContainerEl?.querySelectorAll('.annotation-item').forEach(el => {
        el.classList.remove('selected'); // Ensure only one is selected
        if (el.dataset.annotationId === annotationId) {
            el.classList.add('selected');
            // Scroll list item into view if needed
            el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    });

    // 2. Scroll and potentially highlight in the main text content
    if (highlightingEngine && typeof highlightingEngine.highlightAnnotation === 'function') {
         try {
            highlightingEngine.highlightAnnotation(annotationId, textContentEl); // Pass textContentEl
         } catch (e) {
             console.error("Error highlighting annotation in text:", e);
             // Fallback to simple scroll if highlighting fails
             textContentEl.scrollTo({ top: 0, behavior: 'smooth' }); // Go to top as fallback
         }
    } else {
        // Fallback: Scroll to approximate position (less reliable)
        console.warn("Highlighting engine missing highlightAnnotation method. Using fallback scroll.");
        // Simple scroll to top might be less confusing than inaccurate scrolling
        textContentEl.scrollTo({ top: 0, behavior: 'smooth' });
        // Simple text search and scroll (better than approximate offset)
        const textToFind = annotation.text;
        if (window.find) { // Browser's built-in find
            // Reset selection to search from the beginning
            window.getSelection().removeAllRanges();
            const found = window.find(textToFind, false, false, true, false, true, false);
            if(found) {
                 // Center the found text if possible (rough calculation)
                 const selection = window.getSelection();
                 if (selection && selection.rangeCount > 0) {
                     const range = selection.getRangeAt(0);
                     const rect = range.getBoundingClientRect();
                     const elementScrollTop = textContentEl.scrollTop;
                     const elementTop = textContentEl.getBoundingClientRect().top;
                     const scrollTarget = elementScrollTop + rect.top - elementTop - (textContentEl.clientHeight / 2) + (rect.height / 2);
                     textContentEl.scrollTo({ top: scrollTarget, behavior: 'smooth' });
                 }
            } else {
                 textContentEl.scrollTo({ top: 0, behavior: 'smooth' }); // Scroll top if not found
            }
        } else {
            textContentEl.scrollTo({ top: 0, behavior: 'smooth' }); // Scroll top if window.find not supported
        }
    }
}

async function handleAutoAnnotate() {
    if (!textContentEl) return;
    const text = getTextContent(textContentEl); // Use helper for consistency
    if (!text || !text.trim()) {
        showNotification("Nessun testo da analizzare.", "info");
        return;
    }
    if (!autoAnnotateBtn) return;

    autoAnnotateBtn.disabled = true;
    autoAnnotateBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Riconoscimento...';
    showLoading("Riconoscimento entità in corso...");

    try {
        const result = await api.recognizeEntities(text);
        const recognizedEntities = result.entities || [];
        console.log("Recognized entities raw:", recognizedEntities);

        if (recognizedEntities.length === 0) {
            showNotification("Nessuna nuova entità riconosciuta automaticamente.", "info");
            return;
        }

        let addedCount = 0;
        const annotationsToSave = []; // Batch potential saves

        // Filter out invalid types and overlaps
        const validNewEntities = recognizedEntities.filter(recEntity => {
            // Check 1: Is the type known/valid in this project?
            if (!entityTypesMap.has(recEntity.type)) {
                console.warn(`Auto-annotate: Skipping entity with unknown type "${recEntity.type}"`, recEntity);
                return false;
            }
            // Check 2: Does it overlap with existing annotations?
            const overlaps = annotations.some(existingAnn =>
                (recEntity.start < existingAnn.end && recEntity.end > existingAnn.start)
            );
            if (overlaps) {
                 console.log(`Auto-annotate: Skipping overlapping entity`, recEntity);
                 return false;
            }
            // Basic validation
            if (recEntity.start == null || recEntity.end == null || recEntity.start >= recEntity.end || !recEntity.text) {
                 console.warn(`Auto-annotate: Skipping invalid entity data`, recEntity);
                 return false;
            }

            return true;
        });

        console.log("Valid new entities to add:", validNewEntities);

        if (validNewEntities.length > 0) {
             // Backend ideally supports batch creation. If not, save one by one.
             // Assuming batch IS NOT supported by api.saveAnnotation:
             showLoading(`Salvataggio di ${validNewEntities.length} nuove annotazioni...`);
             for (const newAnnData of validNewEntities) {
                 try {
                    // Create the annotation structure expected by the API
                    const annotationPayload = {
                        start: newAnnData.start,
                        end: newAnnData.end,
                        text: newAnnData.text,
                        type: newAnnData.type
                    };
                    const saved = await api.saveAnnotation(currentDocId, annotationPayload);
                    if (saved && saved.annotation) {
                        annotations.push(saved.annotation); // Add the saved one from response
                        addedCount++;
                    } else {
                         console.warn("Auto-annotate save response missing annotation data for:", newAnnData);
                    }
                 } catch (saveError) {
                     console.error("Error saving auto-annotation:", newAnnData, saveError);
                     // Decide how to handle partial failures - maybe show a summary error at the end
                     showNotification(`Errore salvataggio annotazione auto: ${newAnnData.text.substring(0,20)}...`, "warning");
                 }
             }

            renderAnnotationList();
            updateHighlighting();
            if (addedCount > 0) {
                showNotification(`${addedCount} nuove annotazioni aggiunte automaticamente.`, 'success');
            } else {
                 showNotification("Nessuna nuova annotazione valida è stata salvata (potrebbero esserci stati errori).", "warning");
            }

        } else {
            showNotification("Nessuna nuova annotazione non sovrapposta o di tipo valido trovata.", "info");
        }

    } catch (error) {
        console.error("Error during auto-annotation process:", error);
        showNotification(`Errore nel riconoscimento automatico: ${error.message}`, 'danger');
    } finally {
        autoAnnotateBtn.disabled = false;
        autoAnnotateBtn.innerHTML = '<i class="fas fa-magic me-1"></i> Riconoscimento Auto';
        hideLoading();
    }
}

// --- Text Editing ---
function toggleTextEditing(enable) {
    if (!textContentEl || !editControlsEl || !editBtn) {
         console.error("Cannot toggle text editing: required buttons/elements missing.");
         return;
    }

    isEditingText = enable;
    textContentEl.contentEditable = isEditingText ? 'true' : 'false';
    textContentEl.classList.toggle('editing', isEditingText);
    editControlsEl.classList.toggle('d-none', !isEditingText);
    editBtn.classList.toggle('d-none', isEditingText);

    if (isEditingText) {
        originalTextContent = getTextContent(textContentEl); // Store original text using helper
        console.log("Text editing enabled. Original text stored.");
        // Remove highlighting during editing for clarity and to prevent issues
        if (highlightingEngine && typeof highlightingEngine.removeHighlighting === 'function') {
            console.log("Removing highlights for editing.");
            highlightingEngine.removeHighlighting(textContentEl);
        }
        textContentEl.focus();
        // Warn user about annotation loss ONLY if annotations exist
        if (annotations.length > 0) {
            showNotification("Attenzione: Modificare il testo invaliderà le annotazioni esistenti al salvataggio.", "warning", null, 5000); // Longer duration
        }
    } else {
        console.log("Text editing disabled.");
        // Re-apply highlighting if editing is cancelled or finished without saving changes that clear annotations
        // Ensure highlighting reflects current state (annotations might have been cleared)
        updateHighlighting();
    }
}

async function saveTextChanges() {
    if (!textContentEl || !saveBtn) return;
    const newText = getTextContent(textContentEl); // Use helper

    if (newText === originalTextContent) {
        showNotification("Nessuna modifica al testo rilevata.", "info");
        toggleTextEditing(false); // Just exit edit mode
        return;
    }

    // Explicit confirmation REQUIRED if annotations exist
    if (annotations.length > 0) {
        if (!confirm("Salvare le modifiche al testo eliminerà TUTTE le annotazioni esistenti per questo documento. Questa azione è irreversibile. Continuare?")) {
            console.log("User cancelled text save due to annotation warning.");
            return; // User cancelled
        }
        console.log("User confirmed text save, proceeding with annotation deletion.");
    } else {
        // If no annotations, maybe a simpler confirmation or none at all?
        // if (!confirm("Salvare le modifiche al testo?")) {
        //     return;
        // }
        console.log("Saving text changes (no existing annotations).");
    }


    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Salvataggio...';
    showLoading("Salvataggio modifiche testo...");

    try {
        // 1. Clear existing annotations LOCALLY FIRST (if any) - prevents flicker if API calls are slow
        const hadAnnotations = annotations.length > 0;
        if (hadAnnotations) {
            annotations = [];
            renderAnnotationList(); // Update list (will be empty)
            updateHighlighting(); // Update highlighting (will be empty) - does nothing if editing
            console.log("Local annotations cleared before saving text.");
        }

        // 2. Update document content via API
        console.log("Calling API to update document content...");
        await api.updateDocument(currentDocId, { content: newText });
        console.log("Document content updated via API.");

        // 3. Clear existing annotations on the server (only if they existed)
        if (hadAnnotations) {
            console.log("Calling API to clear server-side annotations...");
            await api.clearAnnotations(currentDocId);
            console.log("Server-side annotations cleared via API.");
            showNotification("Testo aggiornato. Le annotazioni precedenti sono state eliminate.", "success");
        } else {
            showNotification("Testo aggiornato.", "success");
        }


        originalTextContent = newText; // Update original text baseline AFTER successful save
        toggleTextEditing(false); // Exit editing mode

        // Render list and highlights again AFTER exiting edit mode to ensure UI is correct
        renderAnnotationList();
        updateHighlighting();


    } catch (error) {
        console.error("Error saving text changes:", error);
        showNotification(`Errore durante il salvataggio del testo: ${error.message}`, 'danger');
        // Revert UI potentially? This is complex.
        // Option 1: Revert text in editor
        // setTextContent(textContentEl, originalTextContent);
        // Option 2: Leave modified text, user has to cancel or try again
        // Keep editing mode active? Maybe best to disable it to avoid confusion.
        toggleTextEditing(false); // Exit editing mode even on error to avoid inconsistent state
        // Re-fetch original text/annotations? Maybe too complex. Show error and let user decide.
        showNotification("Modifiche al testo non salvate. Si prega di ricaricare o riprovare.", "danger", null, 7000);
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="fas fa-save"></i> Salva';
        hideLoading();
    }
}

function cancelTextEditing() {
    if (!textContentEl) return;
    console.log("Cancelling text editing, reverting text content.");
    // Revert text content using helper
    setTextContent(textContentEl, originalTextContent);
    toggleTextEditing(false); // Exit edit mode (this will re-apply highlights)
    showNotification("Modifiche al testo annullate.", "info");
}

// --- Other Actions ---
function handleZoom(direction) {
    const step = 0.1;
    const minZoom = 0.5;
    const maxZoom = 3.0; // Set a max zoom too
    let changed = false;

    if (direction === 'in') {
        if (currentZoom < maxZoom) {
             currentZoom = Math.min(maxZoom, currentZoom + step);
             changed = true;
        }
    } else if (direction === 'out') {
         if (currentZoom > minZoom) {
             currentZoom = Math.max(minZoom, currentZoom - step);
             changed = true;
         }
    } else { // reset
        if (currentZoom !== 1) {
            currentZoom = 1;
            changed = true;
        }
    }

    if(changed) {
        // Round zoom to avoid floating point issues in display/style
        currentZoom = Math.round(currentZoom * 10) / 10;
        console.log("Zoom changed to:", currentZoom);
        updateZoom();
        // Update button states (optional)
        zoomInBtn.disabled = currentZoom >= maxZoom;
        zoomOutBtn.disabled = currentZoom <= minZoom;
    }
}

function handleSort(type) {
    if (type !== 'position' && type !== 'type') {
        console.warn("Invalid sort type requested:", type);
        return;
    }
    if (currentSort === type) {
        // console.log("Sort type already set to:", type); // Enable if needed
        return; // No change needed
    }

    console.log("Changing sort type to:", type);
    currentSort = type;

    // Update button active states visually
    sortPositionBtn?.classList.toggle('active', type === 'position');
    sortPositionBtn?.setAttribute('aria-pressed', type === 'position');
    sortTypeBtn?.classList.toggle('active', type === 'type');
    sortTypeBtn?.setAttribute('aria-pressed', type === 'type');

    renderAnnotationList(); // Re-render the list with the new sort order
}

function handleSearch(event) {
    // Use requestAnimationFrame or a debounce function for high-frequency input events
    // to avoid excessive re-rendering on fast typing. Simple version for now:
    const newSearchTerm = event.target.value || ''; // Ensure it's a string
    if (newSearchTerm !== currentSearchTerm) {
        console.log("Search term changed:", newSearchTerm);
        currentSearchTerm = newSearchTerm;
        renderAnnotationList(); // Re-render based on the new search term
    }
}

async function handleClearAllAnnotations() {
     if (annotations.length === 0) {
         showNotification("Nessuna annotazione da eliminare.", "info");
         return;
     }
     if (!confirm("Sei sicuro di voler eliminare TUTTE le ("+ annotations.length +") annotazioni per questo documento? Questa azione è irreversibile.")) {
         console.log("User cancelled clear all annotations.");
         return;
     }
     console.log("User confirmed clear all annotations.");

     showLoading("Eliminazione di tutte le annotazioni...");
     // Optimistic UI update
     const oldAnnotations = [...annotations]; // Keep backup for revert
     annotations = [];
     renderAnnotationList();
     updateHighlighting();

     try {
         await api.clearAnnotations(currentDocId); // API call without type clears all
         showNotification("Tutte le annotazioni sono state eliminate con successo.", "success");
     } catch (error) {
         console.error("Error clearing all annotations:", error);
         showNotification(`Errore durante l'eliminazione: ${error.message}`, 'danger');
         // Revert UI
         annotations = oldAnnotations;
         renderAnnotationList();
         updateHighlighting();
     } finally {
         hideLoading();
     }
}

function openClearByTypeModal() {
     if (!clearByTypeModalInstance) {
         showNotification("Funzionalità non disponibile: Modale non trovato.", "warning");
         return;
     }
     // Reset select and disable button before showing
     if (clearByTypeSelect) clearByTypeSelect.value = "";
     if (confirmClearByTypeBtn) confirmClearByTypeBtn.disabled = true;
     clearByTypeModalInstance.show();
}

async function handleClearAnnotationsByType() {
    if (!clearByTypeSelect || !confirmClearByTypeBtn) return;

    const selectedTypeId = clearByTypeSelect.value;
    if (!selectedTypeId) {
        showNotification("Seleziona un tipo di entità da eliminare.", "warning");
        return;
    }

    const typeName = entityTypesMap.get(selectedTypeId)?.name || selectedTypeId;
    const count = annotations.filter(ann => ann.type === selectedTypeId).length;

    if (count === 0) {
        showNotification(`Nessuna annotazione di tipo "${typeName}" da eliminare.`, "info");
        clearByTypeModalInstance?.hide();
        return;
    }

    if (!confirm(`Sei sicuro di voler eliminare tutte le ${count} annotazioni di tipo "${typeName}"? Questa azione è irreversibile.`)) {
        console.log("User cancelled clear by type.");
        return;
    }
    console.log(`User confirmed clear annotations of type: ${typeName} (ID: ${selectedTypeId})`);


    confirmClearByTypeBtn.disabled = true;
    confirmClearByTypeBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Eliminazione...';
    showLoading(`Eliminazione annotazioni tipo "${typeName}"...`);

    // Optimistic UI Update
    const originalAnnotations = [...annotations];
    annotations = annotations.filter(ann => ann.type !== selectedTypeId);
    renderAnnotationList();
    updateHighlighting();
    clearByTypeModalInstance?.hide(); // Hide modal after optimistic update

    try {
        await api.clearAnnotations(currentDocId, selectedTypeId); // Pass type ID to API
        showNotification(`Annotazioni di tipo "${typeName}" eliminate con successo.`, "success");
    } catch (error) {
         console.error(`Error clearing annotations by type ${selectedTypeId}:`, error);
         showNotification(`Errore durante l'eliminazione per tipo: ${error.message}`, 'danger');
         // Revert UI
         annotations = originalAnnotations;
         renderAnnotationList();
         updateHighlighting();
         // Maybe re-show the modal or keep it open? Hiding is simpler.
    } finally {
        // Reset button state even if it's hidden, for the next time modal opens
        confirmClearByTypeBtn.disabled = false;
        confirmClearByTypeBtn.innerHTML = '<i class="fas fa-trash-alt me-2"></i>Elimina annotazioni';
        hideLoading();
    }
}


// --- Event Listeners Setup ---
function setupEventListeners() {
    console.log("Setting up event listeners...");

    // Entity Type Selection (using event delegation on the list)
    entityTypeListEl?.addEventListener('click', (event) => {
        const target = event.target.closest('.entity-type'); // Find the clickable parent
        if (target && target.dataset.entityType) { // Check if it's a valid target with ID
            const typeId = target.dataset.entityType;
            setActiveEntityType(typeId);
        }
    });

    // Text Selection for Annotation (on text container)
    // Use 'selectend' if available and suitable, otherwise mouseup is common
    textContentEl?.addEventListener('mouseup', handleTextSelection);
    // Consider 'selectstart' to potentially clear selection early if needed

    // Button Clicks
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

    // Search Input (using 'input' for real-time feedback)
    searchInput?.addEventListener('input', handleSearch);

    // --- Clear by Type Modal ---
    // Button within the modal to trigger deletion
    confirmClearByTypeBtn?.addEventListener('click', handleClearAnnotationsByType);
    // Enable/disable confirm button based on selection in the modal's dropdown
    clearByTypeSelect?.addEventListener('change', (event) => {
       if(confirmClearByTypeBtn) confirmClearByTypeBtn.disabled = !event.target.value;
    });
    // Optional: Find the button that OPENS the modal (if it's not using data-bs-toggle)
    // document.getElementById('open-clear-by-type-modal-btn')?.addEventListener('click', openClearByTypeModal);
    // If using data-bs-toggle="modal" data-bs-target="#clearByTypeModal", you might not need a separate listener to open it.

    // --- Keyboard Shortcuts ---
    // Setup specifically
    setupKeyboardShortcuts();

    console.log("Event listeners set up.");
}

// --- Keyboard Shortcuts ---
const KeyboardManager = {
    // Mappatura scorciatoie per i tipi di entità
    entityShortcuts: [],
    
    // Mappa la posizione fisica dei tasti numerici sulla tastiera
    keyCodeToNumber: {
        // Numeri nella riga principale (non tastierino numerico)
        'Digit1': '1', 'Digit2': '2', 'Digit3': '3', 'Digit4': '4', 'Digit5': '5', 
        'Digit6': '6', 'Digit7': '7', 'Digit8': '8', 'Digit9': '9',
        // Tastierino numerico
        'Numpad1': '1', 'Numpad2': '2', 'Numpad3': '3', 'Numpad4': '4', 'Numpad5': '5',
        'Numpad6': '6', 'Numpad7': '7', 'Numpad8': '8', 'Numpad9': '9'
    },
    
    init() {
        this.registerEntityShortcuts();
        this.setupEventListeners();
        console.log("KeyboardManager inizializzato", {
            entityShortcuts: this.entityShortcuts,
        });
    },
    
    registerEntityShortcuts() {
        this.entityShortcuts = [];
        
        if (!entityTypeListEl) {
            console.warn("entityTypeListEl non disponibile per la registrazione delle scorciatoie");
            return;
        }
        
        // Seleziona tutti i tipi di entità e associa la scorciatoia Alt+numero
        const entityElements = entityTypeListEl.querySelectorAll('.entity-type');
        entityElements.forEach((el, index) => {
            if (index < 9) { // Limita a 9 shortcut (1-9)
                const shortcutKey = String(index + 1);
                this.entityShortcuts.push({
                    key: shortcutKey,
                    type: el.dataset.entityType,
                    element: el,
                    displayName: el.querySelector('.entity-name')?.textContent || el.dataset.entityType
                });
                
                // Aggiorna il badge visibile con la scorciatoia
                this.addShortcutBadge(el, shortcutKey);
            }
        });
        
        console.log(`Registrate ${this.entityShortcuts.length} scorciatoie per tipi di entità`);
    },

    addShortcutBadge(element, key) {
        let badge = element.querySelector('.shortcut-badge');
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'shortcut-badge badge bg-secondary ms-1';
            element.appendChild(badge);
        }
        badge.textContent = `Alt+${key}`;
        badge.classList.remove('d-none');
    },
    
    setupEventListeners() {
        document.removeEventListener('keydown', this.handleKeyDown.bind(this));
        document.addEventListener('keydown', this.handleKeyDown.bind(this), true);
        
        if (textContentEl) {
            textContentEl.removeEventListener('keydown', this.handleKeyDown.bind(this));
            textContentEl.addEventListener('keydown', this.handleKeyDown.bind(this), true);
        }
    },
    
    handleKeyDown(event) {
        if (this.shouldIgnoreKeyEvent(event)) {
            return;
        }
        
        // Alt + tasto numerico
        if (event.altKey && !event.ctrlKey && !event.shiftKey && this.isNumberKey(event)) {
            this.handleEntityShortcut(event);
            return;
        }
        
        // Alt + A per annotazione automatica
        if (event.altKey && !event.ctrlKey && !event.shiftKey && 
            (event.key.toLowerCase() === 'a' || event.code === 'KeyA')) {
            this.handleAutoAnnotateShortcut(event);
            return;
        }
        
        // Escape o Ctrl+Z per annullare selezione
        if (event.key === 'Escape' || (event.ctrlKey && event.key.toLowerCase() === 'z')) {
            this.handleClearSelectionShortcut(event);
            return;
        }
    },
    
    isNumberKey(event) {
        return this.keyCodeToNumber[event.code] || /^[1-9]$/.test(event.key);
    },
    
    getNumberFromKey(event) {
        return this.keyCodeToNumber[event.code] || 
               (/^[1-9]$/.test(event.key) ? event.key : null);
    },
    
    shouldIgnoreKeyEvent(event) {
        return isEditingText || 
               document.querySelector('.modal.show') || 
               event.target.tagName === 'INPUT' || 
               event.target.tagName === 'TEXTAREA' ||
               (event.target.hasAttribute('contenteditable') && 
                event.target.getAttribute('contenteditable') === 'true' &&
                event.target !== textContentEl);
    },
    
    handleEntityShortcut(event) {
        event.preventDefault();
        event.stopPropagation();
        
        const numericKey = this.getNumberFromKey(event);
        if (!numericKey) return;
        
        const shortcut = this.entityShortcuts.find(s => s.key === numericKey);
        if (!shortcut) return;
        
        setActiveEntityType(shortcut.type);
        shortcut.element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        this.addVisualFeedback(shortcut.element, 'keyboard-activate');
    },
    
    handleAutoAnnotateShortcut(event) {
        event.preventDefault();
        event.stopPropagation();
        
        if (autoAnnotateBtn) {
            this.addVisualFeedback(autoAnnotateBtn, 'btn-flash');
            handleAutoAnnotate();
        }
    },
    
    handleClearSelectionShortcut(event) {
        event.preventDefault();
        event.stopPropagation();
        
        if (clearSelectionBtn) {
            this.addVisualFeedback(clearSelectionBtn, 'btn-flash');
        }
        clearSelection();
    },
    
    addVisualFeedback(element, className, duration = 300) {
        if (!element) return;
        element.classList.add(className);
        setTimeout(() => element.classList.remove(className), duration);
    }
};

// --- Update setupKeyboardShortcuts function ---
function setupKeyboardShortcuts() {
    console.log("Initializing keyboard manager...");
    KeyboardManager.init();
}

// --- Update showKeyboardShortcutsInfo function ---
function showKeyboardShortcutsInfo() {
    // Build message based on registered shortcuts
    let message = "Scorciatoie: Esc/Ctrl+Z (Annulla Sel.)";
    
    if (KeyboardManager.entityShortcuts.length > 0) {
        message += ", " + KeyboardManager.entityShortcuts
            .map(s => `Alt+${s.key} (${s.displayName})`)
            .join(', ');
    }
    
    if (autoAnnotateBtn) {
        message += ", Alt+A (Auto-Annotate)";
    }

    showNotification(message, 'info', 'Scorciatoie da Tastiera', 7000);
}

// --- Update entity type list template in HTML ---
// Find where entity types are rendered and add shortcut badge span
function renderEntityTypeList() {
    // ...existing code...
    entityTypeListEl.querySelectorAll('.entity-type').forEach((el, index) => {
        if (index < 9) {
            // Add shortcut badge if not exists
            if (!el.querySelector('.shortcut-badge')) {
                const badge = document.createElement('span');
                badge.className = 'shortcut-badge badge bg-secondary ms-1 d-none';
                badge.textContent = `Alt+${index + 1}`;
                el.appendChild(badge);
            }
        }
    });
    // ...existing code...
}

// --- Public Init Function ---
export function initAnnotator() {
    console.log('Initializing Annotator Page...');
    try {
        cacheDOMElements(); // Find elements first
        loadInitialData(); // Load data (needs docId from cached element)

        // Initialize Highlighting Engine AFTER DOM is ready and data potentially loaded
        highlightingEngine = new HighlightingEngine(/* pass options if needed */);
        console.log("Highlighting engine initialized.");

        setupEventListeners(); // Setup interactions and keyboard shortcuts

        // Initial Render Cycle
        renderAnnotationList();
        updateHighlighting();
        updateZoom();
        handleSort(currentSort); // Apply default sort and update buttons

        console.log("Annotator initialization complete.");
        showKeyboardShortcutsInfo(); // Show shortcuts info after successful init

    } catch (error) {
         console.error("FATAL ERROR during annotator initialization:", error);
         // Display a user-friendly error message on the page itself if possible
         const body = document.body;
         const errorDiv = document.createElement('div');
         errorDiv.style.color = 'red';
         errorDiv.style.padding = '20px';
         errorDiv.style.border = '2px solid red';
         errorDiv.style.backgroundColor = '#ffebeb';
         errorDiv.innerHTML = `<strong>Errore Critico Inizializzazione Annotatore:</strong><br>${error.message}<br>L'applicazione potrebbe non funzionare correttamente. Si prega di ricaricare la pagina o contattare il supporto.`;
         if(textContentEl) {
             textContentEl.innerHTML = ''; // Clear potentially broken content
             textContentEl.appendChild(errorDiv);
         } else if (body) {
             body.prepend(errorDiv); // Add to top of body if text content not found
         }
         // Optionally hide other controls to prevent further errors
         document.getElementById('controls-column')?.classList.add('d-none'); // Example
         document.getElementById('main-content-column')?.classList.add('w-100'); // Example
    }
}

// --- Auto-run Initialization ---
// Ensure the DOM is fully loaded before running the initialization logic
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAnnotator);
} else {
    // DOMContentLoaded has already fired
    initAnnotator();
}