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
// ++ Aggiunte per stato documento ++
let documentStatus = 'pending'; // Default status ('pending', 'completed', 'skipped')
let documentStatusModalInstance = null; // Placeholder se servirà un modal specifico

// --- DOM Elements ---
// Declare vars, will be assigned in cacheDOMElements
let entityTypeListEl, textContentEl, annotationsContainerEl, annotationCountEl, noAnnotationsMsgEl;
let autoAnnotateBtn, clearSelectionBtn, editBtn, saveBtn, cancelBtn, editControlsEl;
let zoomInBtn, zoomOutBtn, zoomResetBtn;
let sortPositionBtn, sortTypeBtn, searchInput;
let clearAllBtn, clearByTypeModalEl, clearByTypeSelect, confirmClearByTypeBtn;
// ++ Aggiunte per stato documento ++
let markCompletedBtn, markSkippedBtn, statusIndicator, nextDocumentBtn;
// Placeholder per modal, anche se ora usiamo confirm()
let documentStatusModalEl, confirmChangeStatusBtn;


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

    // ++ Aggiunte per stato documento ++
    markCompletedBtn = document.getElementById('mark-completed-btn');
    markSkippedBtn = document.getElementById('mark-skipped-btn');
    statusIndicator = document.getElementById('document-status-indicator');
    nextDocumentBtn = document.getElementById('next-document-btn');
    // Cache anche se non usati attivamente con confirm()
    documentStatusModalEl = document.getElementById('documentStatusModal');
    confirmChangeStatusBtn = document.getElementById('confirm-status-change-btn');

    // Crucial Check: Ensure required elements are found
    if (!textContentEl) {
        console.error("FATAL: textContentEl (#text-content) not found!");
        throw new Error("Required element #text-content is missing.");
    }
    if (!entityTypeListEl) {
        console.warn("Warning: entityTypeListEl (#entityTypeList) not found. Entity selection shortcuts won't work.");
    }
    if (!statusIndicator) {
         console.warn("Warning: statusIndicator (#document-status-indicator) not found. Status UI won't update.");
    }
    // ... (altri controlli esistenti)

    if (clearByTypeModalEl) {
         try {
            clearByTypeModalInstance = new bootstrap.Modal(clearByTypeModalEl);
         } catch(e) {
             console.error("Error initializing Bootstrap Modal (Clear By Type):", e);
             clearByTypeModalInstance = null; // Prevent errors later
         }
     } else {
        console.warn("Warning: clearByTypeModalEl (#clearByTypeModal) not found. Clear by type functionality disabled.");
     }
    // Aggiungere inizializzazione modal stato se necessario in futuro
    // if (documentStatusModalEl) { ... }

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

    // Caricamento Annotazioni Esistenti (dal tag script)
    const annotationsScript = document.getElementById('initial-annotations');
    try {
         if (annotationsScript) {
             const rawAnnotations = JSON.parse(annotationsScript.textContent || '[]') || [];
             // Basic validation of loaded annotations
             annotations = rawAnnotations.filter(ann =>
                 ann.id != null &&
                 ann.start != null &&
                 ann.end != null &&
                 ann.start < ann.end && // Basic check
                 ann.text != null &&
                 ann.type != null
             );
             if (annotations.length !== rawAnnotations.length) {
                 console.warn("Some initial annotations were filtered out due to missing/invalid data.");
             }
             console.log(`Loaded ${annotations.length} initial annotations.`);
         } else {
             console.warn("Initial annotations script tag (#initial-annotations) not found. Assuming no initial annotations.");
             annotations = [];
         }
     } catch (e) {
         console.error("Error parsing initial annotations data:", e);
         showNotification("Errore nel caricamento delle annotazioni esistenti.", "danger");
         annotations = [];
     }


    // Caricamento Tipi di Entità (dal tag script)
    const entityTypesScript = document.getElementById('entity-types-data');
    try {
        if (entityTypesScript) {
            const rawEntityTypes = JSON.parse(entityTypesScript.textContent || '[]') || [];
            entityTypes = rawEntityTypes.map(et => ({
                id: et.id,
                name: et.name || et.display_name, // Support both formats
                color: et.color || '#6c757d' // Default color if missing
            })).filter(et => et.id != null && et.name != null); // Ensure basic validity
            entityTypesMap = new Map(entityTypes.map(et => [et.id.toString(), et])); // Ensure map keys are strings if IDs are numbers

            if (entityTypes.length !== rawEntityTypes.length) {
                console.warn("Some entity types were filtered out due to missing ID or name.");
            }
            console.log(`Loaded ${entityTypes.length} entity types.`);
        } else {
            console.warn("Entity types script tag (#entity-types-data) not found.");
            entityTypes = [];
            entityTypesMap = new Map();
        }
    } catch (e) {
        console.error("Error parsing entity types data:", e);
        showNotification("Errore nel caricamento dei tipi di entità.", "danger");
        entityTypes = [];
        entityTypesMap = new Map();
    }
    console.log("Initial data loaded.");
}

// ++ Nuova funzione per caricare lo stato del documento ++
function loadDocumentStatus() {
    console.log("Loading document status...");
    // Get status from data attribute on the text content element
    const statusAttr = textContentEl?.dataset.docStatus;
    if (statusAttr && ['pending', 'completed', 'skipped'].includes(statusAttr)) {
        documentStatus = statusAttr;
        console.log("Document status loaded from attribute:", documentStatus);
    } else {
        console.warn(`No valid document status found in data-doc-status attribute (found: ${statusAttr}). Using default: ${documentStatus}`);
        // Potresti voler impostare un default o loggare un errore più specifico
        // documentStatus = 'pending'; // Assicurati sia il default desiderato
    }
    updateStatusUI(); // Aggiorna l'UI subito dopo il caricamento
}

// --- Rendering & UI Updates ---

// ++ Nuova funzione per aggiornare l'UI dello stato ++
function updateStatusUI() {
    if (!statusIndicator) {
        // console.warn("Cannot update status UI: statusIndicator element not found.");
        return; // Non fare nulla se l'elemento non c'è
    }

    // Rimuovi classi di stato precedenti per sicurezza
    statusIndicator.classList.remove('bg-secondary', 'bg-success', 'bg-warning', 'text-dark', 'text-white');

    let statusText = 'In Corso';
    let statusClass = 'bg-secondary';
    let textClass = 'text-white'; // Default text color

    // Aggiorna testo, stile e stato pulsanti
    if (documentStatus === 'completed') {
        statusText = 'Completato';
        statusClass = 'bg-success';
        textClass = 'text-white';
        if (markCompletedBtn) markCompletedBtn.disabled = true; // Disabilita se già completato
        if (markSkippedBtn) markSkippedBtn.disabled = false; // Riabilita "Salta" se era disabilitato
        // Potresti voler disabilitare *tutta* l'interfaccia di annotazione qui
        // disableAnnotationInterface(true);
    } else if (documentStatus === 'skipped') {
        statusText = 'Saltato';
        statusClass = 'bg-warning';
        textClass = 'text-dark'; // Warning di Bootstrap spesso sta meglio con testo scuro
        if (markSkippedBtn) markSkippedBtn.disabled = true; // Disabilita se già saltato
        if (markCompletedBtn) markCompletedBtn.disabled = false; // Riabilita "Completa"
        // disableAnnotationInterface(true); // Anche qui potresti disabilitare l'annotazione
    } else { // 'pending' or any other fallback state
        statusText = 'In Corso';
        statusClass = 'bg-secondary';
        textClass = 'text-white';
        if (markCompletedBtn) markCompletedBtn.disabled = false;
        if (markSkippedBtn) markSkippedBtn.disabled = false;
        // disableAnnotationInterface(false); // Assicurati che l'interfaccia sia abilitata
    }

    statusIndicator.textContent = statusText;
    statusIndicator.classList.add(statusClass, textClass);
    // console.log(`Status UI updated to: ${statusText} (${statusClass})`);
}


// -- Funzioni Esistenti (renderAnnotationList, updateEntityTypeCounters, etc.) --
// Assicurati che queste funzioni non vengano modificate involontariamente
function renderAnnotationList() {
    if (!annotationsContainerEl || !annotationCountEl) return;
    // console.log("Rendering annotation list..."); // Can be noisy, enable if needed
    annotationsContainerEl.innerHTML = ''; // Clear list

    // 1. Sort
    const sortedAnnotations = [...annotations].sort((a, b) => {
        if (currentSort === 'type') {
            // Usa toString() per sicurezza se gli ID non sono stringhe
            const typeA = entityTypesMap.get(a.type?.toString())?.name || a.type?.toString() || 'N/D';
            const typeB = entityTypesMap.get(b.type?.toString())?.name || b.type?.toString() || 'N/D';
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
            const entityName = entityTypesMap.get(ann.type?.toString())?.name.toLowerCase() || '';
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

                const entityType = entityTypesMap.get(ann.type?.toString()); // Usa toString() per sicurezza

                itemEl.dataset.annotationId = ann.id;
                itemEl.dataset.start = ann.start;
                itemEl.dataset.end = ann.end;
                itemEl.dataset.type = ann.type; // Keep type id for potential filtering

                typeBadge.textContent = entityType?.name || ann.type?.toString() || 'N/D'; // Fallback name
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
        const typeKey = ann.type?.toString(); // Usa toString() per consistenza
        if (typeKey) {
             acc[typeKey] = (acc[typeKey] || 0) + 1;
        }
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
            // Passa la mappa con chiavi stringa per coerenza
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
    // Converti typeId a stringa se non lo è già, per confronto con dataset
    const typeIdStr = typeId?.toString();
    selectedEntityTypeId = typeIdStr; // Salva come stringa o null/undefined

    entityTypeListEl?.querySelectorAll('.entity-type').forEach(el => {
        // Confronta stringhe
        el.classList.toggle('selected', el.dataset.entityType === typeIdStr);
    });
    console.log("Selected entity type ID:", selectedEntityTypeId); // Log the ID for clarity
     // Provide user feedback
     if (selectedEntityTypeId) {
         const typeName = entityTypesMap.get(selectedEntityTypeId)?.name || selectedEntityTypeId;
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
    // ++ Aggiunta: Non permettere nuove annotazioni se lo stato è 'completed' o 'skipped' ++
    if (documentStatus === 'completed' || documentStatus === 'skipped') {
        showNotification(`Il documento è ${documentStatus === 'completed' ? 'completato' : 'saltato'}. Non è possibile aggiungere annotazioni.`, 'warning');
        clearSelection(); // Pulisci la selezione visuale
        return;
    }
    // -- Fine Aggiunta --

    if (isEditingText) {
        return;
    }
    if (!selectedEntityTypeId) {
        return;
    }

    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) {
        return;
    }

    const range = selection.getRangeAt(0);
    const container = range.commonAncestorContainer;

    if (!textContentEl || !textContentEl.contains(container)) {
        console.warn("Selection occurred outside #text-content. Ignoring.");
        clearSelection();
        return;
    }

    let start, end, text;
    try {
        if (highlightingEngine && typeof highlightingEngine.getRangeOffsets === 'function') {
            ({ start, end } = highlightingEngine.getRangeOffsets(textContentEl, range));
        } else {
             console.warn("Using fallback offset calculation. May be inaccurate if highlighting modifies DOM structure significantly.");
             const preSelectionRange = document.createRange();
             preSelectionRange.selectNodeContents(textContentEl);
             preSelectionRange.setEnd(range.startContainer, range.startOffset);
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

    if (!text.trim()) {
        console.log("Ignoring whitespace-only selection.");
        selection.removeAllRanges();
        return;
    }

    const newAnnotation = {
        start: start,
        end: end,
        text: text,
        type: selectedEntityTypeId // Usa l'ID stringa salvato
    };

    console.log("Attempting to create annotation:", newAnnotation);
    selection.removeAllRanges();
    showLoading("Salvataggio annotazione...");

    try {
        const savedAnnotationResult = await api.saveAnnotation(currentDocId, newAnnotation);

        if (!savedAnnotationResult || !savedAnnotationResult.annotation) {
             throw new Error("API response did not contain the saved annotation.");
        }
        const savedAnnotation = savedAnnotationResult.annotation;

        // Assicura che l'ID tipo sia stringa per consistenza
        if(savedAnnotation.type && typeof savedAnnotation.type !== 'string') {
            savedAnnotation.type = savedAnnotation.type.toString();
        }

        if (!savedAnnotation.id || savedAnnotation.start == null || savedAnnotation.end == null || !savedAnnotation.text || !savedAnnotation.type) {
            console.error("Received invalid annotation data from API:", savedAnnotation);
            throw new Error("Dati annotazione ricevuti dal server non validi.");
        }

        annotations.push(savedAnnotation);
        renderAnnotationList();
        updateHighlighting();
        // Usa la mappa per ottenere il nome, usando l'ID stringa
        const typeName = entityTypesMap.get(savedAnnotation.type)?.name || savedAnnotation.type;
        showNotification(`Annotazione "${typeName}" creata.`, 'success');
    } catch (error) {
        console.error("Error saving annotation:", error);
        const message = error.response?.data?.message || error.message || "Errore sconosciuto";
        showNotification(`Errore creazione annotazione: ${message}`, 'danger');
    } finally {
        hideLoading();
        // setActiveEntityType(null); // Commentato: scelta UX se mantenere o no il tipo selezionato
    }
}

async function handleDeleteAnnotation(annotationId) {
     // ++ Aggiunta: Non permettere eliminazione se lo stato è 'completed' o 'skipped' ++
    if (documentStatus === 'completed' || documentStatus === 'skipped') {
        showNotification(`Il documento è ${documentStatus === 'completed' ? 'completato' : 'saltato'}. Non è possibile eliminare annotazioni.`, 'warning');
        return;
    }
    // -- Fine Aggiunta --

    const annotationIndex = annotations.findIndex(ann => ann.id === annotationId);
    if (annotationIndex === -1) {
        console.warn(`Annotation with ID ${annotationId} not found for deletion.`);
        return;
    }

    const annotationToDelete = annotations[annotationIndex];
    // Usa toString() per sicurezza con la mappa
    const typeName = entityTypesMap.get(annotationToDelete.type?.toString())?.name || annotationToDelete.type?.toString() || 'N/D';

    // Optional: Confirmation (already commented out)
    // if (!confirm(`...`)) { return; }

    annotations.splice(annotationIndex, 1);
    renderAnnotationList();
    updateHighlighting();
    showLoading("Eliminazione annotazione...");

    try {
        await api.deleteAnnotation(currentDocId, annotationId);
        showNotification(`Annotazione "${typeName}" eliminata.`, 'success');
    } catch (error) {
        console.error(`Error deleting annotation ${annotationId}:`, error);
        const message = error.response?.data?.message || error.message || "Errore sconosciuto";
        showNotification(`Errore eliminazione annotazione: ${message}`, 'danger');
        annotations.splice(annotationIndex, 0, annotationToDelete); // Revert
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
        el.classList.remove('selected');
        // Confronta gli ID come stringhe per sicurezza (dataset sono stringhe)
        if (el.dataset.annotationId === annotationId.toString()) {
            el.classList.add('selected');
            el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    });

     // 2. Scroll and potentially highlight in the main text content
    if (highlightingEngine && typeof highlightingEngine.highlightAnnotation === 'function') {
         try {
            // Passa l'ID come ricevuto (potrebbe essere numero o stringa, il motore deve gestirlo)
            highlightingEngine.highlightAnnotation(annotationId, textContentEl);
         } catch (e) {
             console.error("Error highlighting annotation in text:", e);
             textContentEl.scrollTo({ top: 0, behavior: 'smooth' }); // Fallback
         }
    } else {
        // Fallback scroll logic (codice esistente)
        console.warn("Highlighting engine missing highlightAnnotation method. Using fallback scroll.");
        const textToFind = annotation.text;
        if (window.find) {
            window.getSelection().removeAllRanges();
            const found = window.find(textToFind, false, false, true, false, true, false);
            if(found) {
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
                 textContentEl.scrollTo({ top: 0, behavior: 'smooth' });
            }
        } else {
            textContentEl.scrollTo({ top: 0, behavior: 'smooth' });
        }
    }
}

async function handleAutoAnnotate() {
    // Controlli di sicurezza e preparazione
    if (!documentText) {
        showToast('Errore', 'Testo del documento non disponibile', 'error');
        return;
    }

    try {
        // Riferimento al pulsante
        const autoAnnotateBtn = document.getElementById('auto-annotate-btn');
        
        // Mostra indicatore di caricamento
        autoAnnotateBtn.classList.add('loading');
        autoAnnotateBtn.disabled = true;
        autoAnnotateBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Elaborazione...';

        // Chiama l'API per il riconoscimento delle entità
        const response = await api.recognizeEntities(documentText);
        
        if (response.status === 'success' && response.entities && response.entities.length > 0) {
            // Salva le entità riconosciute per la validazione
            const recognizedEntities = response.entities;
            
            // Messaggi di avviso dal server
            if (response.warning) {
                showToast('Attenzione', response.warning, 'warning');
            }
            
            // Feedback all'utente
            showToast('Informazione', `Riconosciute ${recognizedEntities.length} entità. Procedi con la validazione.`, 'info');
            
            // Creazione modalità di validazione
            enterValidationMode(recognizedEntities);
        } else if (response.status === 'success' && (!response.entities || response.entities.length === 0)) {
            showToast('Informazione', 'Nessuna entità riconosciuta nel testo. Prova ad annotare manualmente.', 'info');
            
            // Messaggi di avviso dal server
            if (response.warning) {
                showToast('Attenzione', response.warning, 'warning');
            }
        } else {
            showToast('Errore', 'Risposta dal server non valida', 'error');
        }
    } catch (error) {
        console.error('Errore durante il riconoscimento automatico:', error);
        showToast('Errore', `Errore durante il riconoscimento automatico: ${error.message}`, 'error');
    } finally {
        // Ripristina il pulsante
        const autoAnnotateBtn = document.getElementById('auto-annotate-btn');
        autoAnnotateBtn.classList.remove('loading');
        autoAnnotateBtn.disabled = false;
        autoAnnotateBtn.innerHTML = '<i class="fas fa-magic me-1"></i> Riconoscimento Auto';
    }
}

/**
 * Attiva la modalità di validazione per le entità riconosciute automaticamente
 * @param {Array} entities - Lista delle entità riconosciute
 */
function enterValidationMode(entities) {
    // Salva le entità originali in una variabile globale per riferimento futuro nel feedback
    window.originalRecognizedEntities = [...entities];
    
    // Crea interfaccia di validazione
    const validationPanel = document.createElement('div');
    validationPanel.id = 'validationPanel';
    validationPanel.className = 'validation-panel card border-primary shadow';
    validationPanel.innerHTML = `
        <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
            <h5 class="mb-0"><i class="fas fa-check-circle me-2"></i>Validazione Entità Riconosciute</h5>
            <button type="button" class="btn-close btn-close-white" aria-label="Chiudi"></button>
        </div>
        <div class="card-body">
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>Sono state riconosciute <strong>${entities.length}</strong> entità.
                <p class="mb-0 small mt-1">Controlla, correggi ed accetta le entità corrette. Questo migliorerà il sistema di riconoscimento automatico nel tempo.</p>
            </div>
            <div class="mb-2 d-flex justify-content-between align-items-center">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="selectAllEntities" checked>
                    <label class="form-check-label" for="selectAllEntities">Seleziona tutte</label>
                </div>
                <div class="d-flex">
                    <div class="btn-group btn-group-sm me-2">
                        <button class="btn btn-outline-secondary" id="sortByPosition">
                            <i class="fas fa-sort-numeric-down"></i> Posizione
                        </button>
                        <button class="btn btn-outline-secondary" id="sortByConfidence">
                            <i class="fas fa-sort-amount-down"></i> Confidenza
                        </button>
                        <button class="btn btn-outline-secondary" id="sortByType">
                            <i class="fas fa-sort-alpha-down"></i> Tipo
                        </button>
                    </div>
                    <input type="search" class="form-control form-control-sm" id="filterValidationEntities" placeholder="Filtra...">
                </div>
            </div>
            <div class="entity-validation-list" style="max-height: 60vh; overflow-y: auto;">
                <table class="table table-sm table-hover">
                    <thead class="sticky-top bg-white">
                        <tr>
                            <th style="width: 40%">Testo</th>
                            <th style="width: 25%">Tipo</th>
                            <th style="width: 25%">Confidenza</th>
                            <th style="width: 10%">Azioni</th>
                        </tr>
                    </thead>
                    <tbody id="entityValidationTbody">
                    </tbody>
                </table>
            </div>
            <div class="d-flex justify-content-between mt-3">
                <button id="rejectAllBtn" class="btn btn-outline-danger">
                    <i class="fas fa-times me-1"></i> Annulla
                </button>
                <button id="acceptSelectedBtn" class="btn btn-success">
                    <i class="fas fa-check me-1"></i> Conferma Selezionate (<span id="selectedCount">${entities.length}</span>)
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(validationPanel);
    
    // Popola la tabella delle entità
    const tbody = document.getElementById('entityValidationTbody');
    
    entities.forEach((entity, index) => {
        // Cerca l'entityType corrispondente nella mappa
        const entityType = entityTypesMap.get(entity.type) || {
            name: entity.type, 
            color: '#aaa',
            display_name: entity.type.charAt(0).toUpperCase() + entity.type.slice(1).toLowerCase()
        };
        
        // Formatta la percentuale di confidenza
        const confidence = entity.confidence ? (entity.confidence * 100).toFixed(0) + '%' : 'N/A';
        const confidenceClass = entity.confidence > 0.8 ? 'bg-success' : 
                               entity.confidence > 0.5 ? 'bg-warning' : 'bg-danger';
        
        const row = document.createElement('tr');
        row.dataset.entityIndex = index;
        row.dataset.entityId = entity.id || `temp_${index}`;
        row.dataset.entityText = entity.text;
        row.dataset.entityType = entity.type;
        row.dataset.entityConfidence = entity.confidence || 0;
        
        row.innerHTML = `
            <td class="entity-text" title="${entity.text}">${entity.text.length > 50 ? entity.text.substring(0, 50) + '...' : entity.text}</td>
            <td>
                <span class="badge" style="background-color: ${entityType.color}">
                    ${entityType.display_name || entityType.name}
                </span>
            </td>
            <td>
                <div class="progress" style="height: 12px;">
                    <div class="progress-bar ${confidenceClass}" role="progressbar" 
                        style="width: ${entity.confidence ? entity.confidence * 100 : 50}%;" 
                        aria-valuenow="${entity.confidence ? entity.confidence * 100 : 50}" 
                        aria-valuemin="0" aria-valuemax="100">
                    </div>
                </div>
                <small>${confidence}</small>
            </td>
            <td>
                <div class="form-check">
                    <input class="form-check-input entity-validation-check" type="checkbox" checked>
                </div>
            </td>
        `;
        
        // Click sulla riga per evidenziare l'entità nel testo
        row.addEventListener('click', (e) => {
            if (!e.target.matches('input[type="checkbox"]')) {
                const entity = entities[index];
                jumpToTextPosition(entity.start, entity.end);
            }
        });
        
        tbody.appendChild(row);
    });
    
    // Event listener per il checkbox "seleziona tutti"
    document.getElementById('selectAllEntities').addEventListener('change', (e) => {
        const checked = e.target.checked;
        document.querySelectorAll('.entity-validation-check').forEach(checkbox => {
            checkbox.checked = checked;
        });
        updateSelectedCount();
    });
    
    // Event listener per chiudere il pannello di validazione
    validationPanel.querySelector('.btn-close').addEventListener('click', () => {
        exitValidationMode();
    });
    
    // Event listener per rifiutare tutte le annotazioni
    document.getElementById('rejectAllBtn').addEventListener('click', () => {
        if (confirm("Sei sicuro di voler annullare la validazione? Tutte le entità riconosciute saranno scartate.")) {
            exitValidationMode();
        }
    });
    
    // Event listener per accettare le annotazioni selezionate
    document.getElementById('acceptSelectedBtn').addEventListener('click', async () => {
        const checkedRows = document.querySelectorAll('#entityValidationTbody tr .entity-validation-check:checked');
        
        if (checkedRows.length === 0) {
            showToast('Avviso', 'Nessuna entità selezionata per il salvataggio', 'warning');
            return;
        }
        
        const selectedEntities = [];
        
        checkedRows.forEach(checkbox => {
            const row = checkbox.closest('tr');
            const index = parseInt(row.dataset.entityIndex);
            selectedEntities.push(entities[index]);
        });
        
        if (selectedEntities.length > 0) {
            // Salva le entità selezionate come annotazioni
            await saveRecognizedEntities(selectedEntities);
        }
        
        exitValidationMode();
    });
    
    // Funzione per aggiornare il conteggio delle entità selezionate
    function updateSelectedCount() {
        const checkedCount = document.querySelectorAll('.entity-validation-check:checked').length;
        document.getElementById('selectedCount').textContent = checkedCount;
    }
    
    // Aggiungi event listener per aggiornare il conteggio quando cambia una selezione
    document.querySelectorAll('.entity-validation-check').forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedCount);
    });
    
    // Event listener per ordinare per posizione
    document.getElementById('sortByPosition').addEventListener('click', () => {
        sortValidationTable('position');
    });
    
    // Event listener per ordinare per confidenza
    document.getElementById('sortByConfidence').addEventListener('click', () => {
        sortValidationTable('confidence');
    });
    
    // Event listener per ordinare per tipo
    document.getElementById('sortByType').addEventListener('click', () => {
        sortValidationTable('type');
    });
    
    // Event listener per filtrare le entità
    document.getElementById('filterValidationEntities').addEventListener('input', (e) => {
        const filterText = e.target.value.toLowerCase();
        document.querySelectorAll('#entityValidationTbody tr').forEach(row => {
            const entityText = row.dataset.entityText.toLowerCase();
            const entityType = row.dataset.entityType.toLowerCase();
            
            if (entityText.includes(filterText) || entityType.includes(filterText)) {
                row.style.display = '';
            } else {
                row.style.display = 'none';
            }
        });
    });
    
    // Funzione per ordinare la tabella di validazione
    function sortValidationTable(criterion) {
        const tbody = document.getElementById('entityValidationTbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.sort((a, b) => {
            if (criterion === 'position') {
                return parseInt(a.dataset.entityIndex) - parseInt(b.dataset.entityIndex);
            } else if (criterion === 'confidence') {
                return parseFloat(b.dataset.entityConfidence) - parseFloat(a.dataset.entityConfidence);
            } else if (criterion === 'type') {
                return a.dataset.entityType.localeCompare(b.dataset.entityType);
            }
            return 0;
        });
        
        // Rimuovi le righe esistenti
        rows.forEach(row => row.remove());
        
        // Aggiungi le righe ordinate
        rows.forEach(row => tbody.appendChild(row));
    }
    
    // Evidenzia le entità riconosciute nel testo del documento
    highlightRecognizedEntities(entities);
}

/**
 * Esce dalla modalità di validazione
 */
function exitValidationMode() {
    // Rimuovi il pannello di validazione
    const validationPanel = document.getElementById('validationPanel');
    if (validationPanel) {
        validationPanel.remove();
    }
    
    // Ripristina l'evidenziazione normale
    updateHighlighting();
}

/**
 * Salva le entità riconosciute come annotazioni e invia feedback per l'apprendimento
 * @param {Array} entities - Lista delle entità riconosciute da salvare
 */
async function saveRecognizedEntities(entities) {
    try {
        showToast('Informazione', 'Salvataggio annotazioni in corso...', 'info');
        
        let savedCount = 0;
        let feedbackData = {
            document_id: documentId,
            original_predictions: [],
            validated_entities: [],
            document_text: documentText,
            timestamp: new Date().toISOString()
        };
        
        // Prima elaboriamo tutte le entità per creare il feedback completo
        for (const entity of entities) {
            // Aggiungi l'entità ai dati di feedback come validata
            feedbackData.validated_entities.push({
                id: entity.id || generateUniqueId(),
                start: entity.start,
                end: entity.end,
                text: entity.text,
                type: entity.type,
                confidence: entity.confidence || 1.0
            });
        }
        
        // Aggiunge tutte le predizioni originali per confronto
        if (window.originalRecognizedEntities && window.originalRecognizedEntities.length > 0) {
            // Per ogni entità originale (incluse quelle rifiutate)
            const acceptedIds = new Set(entities.map(e => e.id));
            
            window.originalRecognizedEntities.forEach(entity => {
                feedbackData.original_predictions.push({
                    text: entity.text,
                    start: entity.start,
                    end: entity.end,
                    type: entity.type,
                    confidence: entity.confidence || 1.0,
                    was_accepted: acceptedIds.has(entity.id)
                });
            });
        } else {
            // Se non abbiamo predizioni originali salvate, usiamo le entità accettate
            feedbackData.original_predictions = entities.map(entity => ({
                text: entity.text,
                start: entity.start,
                end: entity.end,
                type: entity.type,
                confidence: entity.confidence || 1.0,
                was_accepted: true
            }));
        }
        
        // Invia il feedback per l'apprendimento (prima di salvare le annotazioni)
        try {
            const feedbackResponse = await api.sendAnnotationFeedback(feedbackData);
            console.log("Feedback inviato per il reinforcement learning", feedbackResponse);
        } catch (error) {
            console.error("Errore nell'invio del feedback:", error);
            // Non blocchiamo il flusso principale se c'è un errore nel feedback
        }
        
        // Ora salviamo le entità validate come annotazioni
        for (const entity of entities) {
            // Crea un oggetto annotazione
            const annotation = {
                id: entity.id || generateUniqueId(),
                start: entity.start,
                end: entity.end,
                text: entity.text,
                type: entity.type,
                created_at: new Date().toISOString()
            };
            
            // Aggiungi metadati di confidenza e origine
            annotation.metadata = {
                confidence: entity.confidence || 1.0,
                source: 'auto', // Indica che l'annotazione è stata generata automaticamente
                validated: true, // Indica che l'annotazione è stata validata dall'utente
                feedback_sent: true // Indica che è stato inviato feedback
            };
            
            try {
                // Salva l'annotazione
                const response = await api.saveAnnotation(documentId, annotation);
                if (response.status === 'success') {
                    annotations.push(annotation);
                    savedCount++;
                }
            } catch (error) {
                console.error(`Errore nel salvataggio dell'annotazione ${annotation.text}:`, error);
            }
        }
        
        if (savedCount > 0) {
            // Aggiorna l'interfaccia
            renderAnnotationList();
            updateEntityTypeCounters();
            updateHighlighting();
            
            showToast('Successo', `Salvate ${savedCount} annotazioni con feedback per il modello`, 'success');
            
            // Aggiorna lo stato del documento se non è già completato
            if (documentStatus !== 'completed') {
                await changeDocumentStatus('in_progress');
            }
            
            // Aggiungi una classe css per indicare che questo documento è stato usato per l'addestramento
            document.getElementById('text-content').classList.add('has-validated-entities');
        } else {
            showToast('Avviso', 'Nessuna annotazione salvata', 'warning');
        }
    } catch (error) {
        console.error('Errore durante il salvataggio delle annotazioni:', error);
        showToast('Errore', `Errore durante il salvataggio: ${error.message}`, 'error');
    }
}

/**
 * Evidenzia temporaneamente le entità riconosciute nel testo
 * @param {Array} entities - Lista delle entità da evidenziare
 */
function highlightRecognizedEntities(entities) {
    const textElement = document.getElementById('documentText');
    if (!textElement) return;
    
    // Pulisci le evidenziazioni esistenti
    highlightingEngine.removeHighlighting(textElement);
    
    // Crea una versione mappabile delle entità
    const tempAnnotations = entities.map(entity => ({
        id: 'temp_' + Math.random().toString(36).substring(2, 9),
        start: entity.start,
        end: entity.end,
        text: entity.text,
        type: entity.type
    }));
    
    // Applica l'evidenziazione con uno stile distintivo per le entità riconosciute
    highlightingEngine.applyHighlights(textElement, tempAnnotations, entityTypesMap);
    
    // Aggiungi una classe speciale agli span di evidenziazione per le entità riconosciute
    tempAnnotations.forEach(tempAnn => {
        const span = highlightingEngine.currentHighlights.get(tempAnn.id);
        if (span) {
            span.classList.add('recognized-entity');
            span.style.border = '1px dashed #333';
        }
    });
}

/**
 * Salta a una posizione specifica nel testo del documento
 * @param {number} start - Posizione di inizio
 * @param {number} end - Posizione di fine
 */
function jumpToTextPosition(start, end) {
    const textElement = document.getElementById('documentText');
    if (!textElement) return;
    
    // Evidenzia temporaneamente il testo
    const tempId = 'temp_' + Math.random().toString(36).substring(2, 9);
    const tempAnnotation = {
        id: tempId,
        start: start,
        end: end,
        text: documentText.substring(start, end),
        type: 'HIGHLIGHT' // Tipo fittizio
    };
    
    // Crea una mappa temporanea con un colore distintivo
    const tempMap = new Map([['HIGHLIGHT', {name: 'Highlight', color: '#ffff00'}]]);
    
    // Ripristina l'evidenziazione originale dopo lo scroll
    const originalHighlights = [...highlightingEngine.currentHighlights.entries()];
    
    // Applica l'evidenziazione temporanea
    highlightingEngine.applyHighlights(textElement, [tempAnnotation], tempMap);
    
    // Scorri fino alla posizione
    const span = highlightingEngine.currentHighlights.get(tempId);
    if (span) {
        span.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Aggiungi un effetto visivo
        span.style.backgroundColor = '#ffff00';
        span.style.transition = 'background-color 1s ease';
        
        // Ripristina l'evidenziazione originale dopo un breve ritardo
        setTimeout(() => {
            // Ripristina le evidenziazioni originali
            highlightingEngine.removeHighlighting(textElement);
            const originalAnnotations = originalHighlights.map(([id, _]) => 
                annotations.find(ann => ann.id === id) || tempAnnotation);
            highlightingEngine.applyHighlights(textElement, originalAnnotations, entityTypesMap);
        }, 1500);
    }
}

// Funzioni di supporto
function generateUniqueId() {
    return 'ann_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
}

// --- Text Editing ---
function toggleTextEditing(enable) {
     // ++ Aggiunta: Non permettere modifica testo se lo stato è 'completed' o 'skipped' ++
    if (enable && (documentStatus === 'completed' || documentStatus === 'skipped')) {
        showNotification(`Il documento è ${documentStatus === 'completed' ? 'completato' : 'saltato'}. Non è possibile modificare il testo.`, 'warning');
        return;
    }
    // -- Fine Aggiunta --

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
        originalTextContent = getTextContent(textContentEl);
        console.log("Text editing enabled. Original text stored.");
        if (highlightingEngine && typeof highlightingEngine.removeHighlighting === 'function') {
            console.log("Removing highlights for editing.");
            highlightingEngine.removeHighlighting(textContentEl);
        }
        textContentEl.focus();
        if (annotations.length > 0) {
            showNotification("Attenzione: Modificare il testo invaliderà le annotazioni esistenti al salvataggio.", "warning", null, 5000);
        }
    } else {
        console.log("Text editing disabled.");
        // Re-apply highlighting only if annotations still exist (might have been cleared by save)
        if(annotations.length > 0) {
            updateHighlighting();
        } else {
            // If annotations were cleared, ensure highlights are also cleared
             if (highlightingEngine && typeof highlightingEngine.removeHighlighting === 'function') {
                highlightingEngine.removeHighlighting(textContentEl);
            }
        }
    }
}

async function saveTextChanges() {
    // Blocco implicito da toggleTextEditing, ma doppia sicurezza
    if (documentStatus === 'completed' || documentStatus === 'skipped') return;

    if (!textContentEl || !saveBtn) return;
    const newText = getTextContent(textContentEl);

    if (newText === originalTextContent) {
        showNotification("Nessuna modifica al testo rilevata.", "info");
        toggleTextEditing(false);
        return;
    }

    if (annotations.length > 0) {
        if (!confirm("Salvare le modifiche al testo eliminerà TUTTE le annotazioni esistenti per questo documento. Questa azione è irreversibile. Continuare?")) {
            console.log("User cancelled text save due to annotation warning.");
            return;
        }
        console.log("User confirmed text save, proceeding with annotation deletion.");
    } else {
        console.log("Saving text changes (no existing annotations).");
    }

    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Salvataggio...';
    showLoading("Salvataggio modifiche testo...");

    try {
        const hadAnnotations = annotations.length > 0;
        if (hadAnnotations) {
            // Aggiorna UI localmente *prima* delle chiamate API
            annotations = [];
            renderAnnotationList(); // Svuota lista UI
            // Non serve updateHighlighting qui perchè siamo in edit mode senza highlights
            console.log("Local annotations cleared visually before saving text.");
        }

        console.log("Calling API to update document content...");
        await api.updateDocument(currentDocId, { content: newText });
        console.log("Document content updated via API.");

        if (hadAnnotations) {
            console.log("Calling API to clear server-side annotations...");
            // Chiamata API per pulire le annotazioni lato server
            // Questa chiamata potrebbe essere inclusa nell'updateDocument o separata
            // Qui assumiamo sia separata:
            await api.clearAnnotations(currentDocId); // Assicurati che esista e funzioni
            console.log("Server-side annotations cleared via API.");
            showNotification("Testo aggiornato. Le annotazioni precedenti sono state eliminate.", "success");
        } else {
            showNotification("Testo aggiornato.", "success");
        }

        originalTextContent = newText;
        toggleTextEditing(false); // Esce dalla modalità edit (questo gestirà re-highlighting se necessario)

    } catch (error) {
        console.error("Error saving text changes:", error);
        const message = error.response?.data?.message || error.message || "Errore sconosciuto";
        showNotification(`Errore durante il salvataggio del testo: ${message}`, 'danger');
        toggleTextEditing(false); // Esce comunque dalla modalità edit
        // Non si fa revert automatico del testo, si informa l'utente
        showNotification("Modifiche al testo non salvate a causa di un errore. Ricarica o riprova.", "danger", null, 7000);
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="fas fa-save"></i> Salva';
        hideLoading();
    }
}

function cancelTextEditing() {
    if (!textContentEl) return;
    console.log("Cancelling text editing, reverting text content.");
    setTextContent(textContentEl, originalTextContent);
    toggleTextEditing(false);
    showNotification("Modifiche al testo annullate.", "info");
}


// --- Other Actions --- (Zoom, Sort, Search) - Mantenute come sono
function handleZoom(direction) {
    const step = 0.1;
    const minZoom = 0.5;
    const maxZoom = 3.0;
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
        currentZoom = Math.round(currentZoom * 10) / 10;
        console.log("Zoom changed to:", currentZoom);
        updateZoom();
        if(zoomInBtn) zoomInBtn.disabled = currentZoom >= maxZoom;
        if(zoomOutBtn) zoomOutBtn.disabled = currentZoom <= minZoom;
    }
}

function handleSort(type) {
    if (type !== 'position' && type !== 'type') {
        console.warn("Invalid sort type requested:", type);
        return;
    }
    if (currentSort === type) {
        return;
    }

    console.log("Changing sort type to:", type);
    currentSort = type;

    sortPositionBtn?.classList.toggle('active', type === 'position');
    sortPositionBtn?.setAttribute('aria-pressed', (type === 'position').toString());
    sortTypeBtn?.classList.toggle('active', type === 'type');
    sortTypeBtn?.setAttribute('aria-pressed', (type === 'type').toString());

    renderAnnotationList();
}

function handleSearch(event) {
    const newSearchTerm = event.target.value || '';
    if (newSearchTerm !== currentSearchTerm) {
        console.log("Search term changed:", newSearchTerm);
        currentSearchTerm = newSearchTerm;
        renderAnnotationList();
    }
}

async function handleClearAllAnnotations() {
    // ++ Aggiunta: Non permettere clear se lo stato è 'completed' o 'skipped' ++
    if (documentStatus === 'completed' || documentStatus === 'skipped') {
        showNotification(`Il documento è ${documentStatus === 'completed' ? 'completato' : 'saltato'}. Non è possibile eliminare annotazioni.`, 'warning');
        return;
    }
    // -- Fine Aggiunta --

     if (annotations.length === 0) {
         showNotification("Nessuna annotazione da eliminare.", "info");
         return;
     }
     if (!confirm(`Sei sicuro di voler eliminare TUTTE le (${annotations.length}) annotazioni per questo documento? Questa azione è irreversibile.`)) {
         console.log("User cancelled clear all annotations.");
         return;
     }
     console.log("User confirmed clear all annotations.");

     showLoading("Eliminazione di tutte le annotazioni...");
     const oldAnnotations = [...annotations];
     annotations = [];
     renderAnnotationList();
     updateHighlighting(); // Aggiorna per rimuovere highlights

     try {
         await api.clearAnnotations(currentDocId);
         showNotification("Tutte le annotazioni sono state eliminate con successo.", "success");
     } catch (error) {
         console.error("Error clearing all annotations:", error);
         const message = error.response?.data?.message || error.message || "Errore sconosciuto";
         showNotification(`Errore durante l'eliminazione: ${message}`, 'danger');
         annotations = oldAnnotations; // Revert
         renderAnnotationList();
         updateHighlighting();
     } finally {
         hideLoading();
     }
}

function openClearByTypeModal() {
    // ++ Aggiunta: Non permettere clear se lo stato è 'completed' o 'skipped' ++
    if (documentStatus === 'completed' || documentStatus === 'skipped') {
        showNotification(`Il documento è ${documentStatus === 'completed' ? 'completato' : 'saltato'}. Non è possibile eliminare annotazioni.`, 'warning');
        return;
    }
    // -- Fine Aggiunta --

     if (!clearByTypeModalInstance) {
         showNotification("Funzionalità non disponibile: Modale non trovato.", "warning");
         return;
     }
     if (clearByTypeSelect) {
        // Popola dinamicamente le opzioni basate sui tipi presenti nelle annotazioni?
        // O semplicemente mostra tutti i tipi definiti? Mostriamo tutti i tipi definiti.
        clearByTypeSelect.innerHTML = '<option value="">Seleziona un tipo...</option>'; // Reset
        entityTypes.forEach(et => {
            const option = document.createElement('option');
            option.value = et.id.toString(); // Usa ID stringa
            option.textContent = et.name;
            clearByTypeSelect.appendChild(option);
        });
     }
     if (confirmClearByTypeBtn) confirmClearByTypeBtn.disabled = true;
     clearByTypeModalInstance.show();
}

async function handleClearAnnotationsByType() {
    // Blocco implicito dal modal, ma doppia sicurezza
     if (documentStatus === 'completed' || documentStatus === 'skipped') return;

    if (!clearByTypeSelect || !confirmClearByTypeBtn) return;

    const selectedTypeId = clearByTypeSelect.value; // Questo sarà una stringa
    if (!selectedTypeId) {
        showNotification("Seleziona un tipo di entità da eliminare.", "warning");
        return;
    }

    const typeName = entityTypesMap.get(selectedTypeId)?.name || selectedTypeId;
    const count = annotations.filter(ann => ann.type?.toString() === selectedTypeId).length;

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

    const originalAnnotations = [...annotations];
    annotations = annotations.filter(ann => ann.type?.toString() !== selectedTypeId);
    renderAnnotationList();
    updateHighlighting(); // Aggiorna highlights
    clearByTypeModalInstance?.hide();

    try {
        // Passa l'ID tipo (stringa) all'API
        await api.clearAnnotations(currentDocId, selectedTypeId);
        showNotification(`Annotazioni di tipo "${typeName}" eliminate con successo.`, "success");
    } catch (error) {
         console.error(`Error clearing annotations by type ${selectedTypeId}:`, error);
         const message = error.response?.data?.message || error.message || "Errore sconosciuto";
         showNotification(`Errore durante l'eliminazione per tipo: ${message}`, 'danger');
         annotations = originalAnnotations; // Revert
         renderAnnotationList();
         updateHighlighting();
    } finally {
        confirmClearByTypeBtn.disabled = false; // Riabilita anche se nascosto
        confirmClearByTypeBtn.innerHTML = '<i class="fas fa-trash-alt me-2"></i>Elimina annotazioni';
        hideLoading();
    }
}

// ++ Nuove funzioni per gestione stato documento ++

// Funzione per cambiare lo stato del documento via API
async function changeDocumentStatus(newStatus) {
    // Impedisce cambi se lo stato è già quello o se manca ID
    if (!currentDocId || newStatus === documentStatus || !['completed', 'skipped'].includes(newStatus)) {
        console.warn(`Change status aborted. Current: ${documentStatus}, Requested: ${newStatus}, DocID: ${currentDocId}`);
        return;
    }

    const statusText = newStatus === 'completed' ? 'Completato' : 'Saltato';
    // Usa confirm() come da richiesta originale
    if (!confirm(`Sei sicuro di voler contrassegnare questo documento come "${statusText}"?`)) {
        console.log(`User cancelled changing status to ${newStatus}.`);
        return;
    }
    console.log(`User confirmed changing status to ${newStatus}.`);

    showLoading(`Aggiornamento stato a "${statusText}"...`);
    // Disabilita temporaneamente i bottoni di stato per evitare doppi click
    if (markCompletedBtn) markCompletedBtn.disabled = true;
    if (markSkippedBtn) markSkippedBtn.disabled = true;

    try {
        // Assicurati che api.updateDocumentStatus esista e funzioni!
        const result = await api.updateDocumentStatus(currentDocId, newStatus);

        // Controlla la risposta API (adatta la struttura se necessario)
        if (result && (result.status === 'success' || result.success === true)) { // Flessibile sulla risposta
            const oldStatus = documentStatus;
            documentStatus = newStatus; // Aggiorna stato locale
            updateStatusUI(); // Aggiorna UI (disabiliterà il bottone corretto)
            showNotification(result.message || `Documento marcato come ${statusText}.`, 'success');

            // Aggiorna l'attributo data sul DOM se vuoi che rifletta lo stato senza ricaricare
            if (textContentEl) {
                textContentEl.dataset.docStatus = newStatus;
            }

            // Chiedi se passare al prossimo documento
            // Attendi un breve istante prima di chiedere, per far vedere la notifica
            setTimeout(() => {
                if (confirm('Stato aggiornato. Vuoi passare al prossimo documento disponibile?')) {
                    goToNextDocument();
                }
            }, 500); // Mezzo secondo di ritardo

        } else {
            // L'API ha risposto ma non con successo
            throw new Error(result?.message || 'Errore sconosciuto durante l\'aggiornamento dello stato.');
        }
    } catch (error) {
        console.error('Error updating document status:', error);
        const message = error.response?.data?.message || error.message || "Errore sconosciuto";
        showNotification(`Errore aggiornamento stato: ${message}`, 'danger');
        // Riabilita i bottoni se l'operazione fallisce
        updateStatusUI(); // Richiama questo per ripristinare lo stato corretto dei bottoni
    } finally {
        hideLoading();
        // Lo stato dei bottoni viene gestito da updateStatusUI, non serve riabilitarli qui esplicitamente
    }
}

// Funzione per caricare e navigare al documento successivo
async function goToNextDocument() {
    if (!currentDocId) {
        showNotification("ID documento corrente non disponibile.", "warning");
        return;
    }
    if (!nextDocumentBtn) {
         console.warn("Next document button not found.");
         // Potrebbe comunque procedere, ma informa
    } else {
        nextDocumentBtn.disabled = true; // Disabilita durante il caricamento
        nextDocumentBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Caricamento...';
    }

    showLoading('Ricerca documento successivo...');

    try {
        // Assicurati che api.getNextDocument esista e funzioni!
        // Passa lo stato desiderato ('pending' o quello che serve)
        const result = await api.getNextDocument(currentDocId, 'pending');

        // Controlla la risposta API (adatta la struttura se necessario)
        if (result && result.status === 'success' && result.document?.id) {
            const nextDocId = result.document.id;
            showNotification(`Trovato documento successivo (ID: ${nextDocId}). Reindirizzamento...`, 'info', null, 2000);
            // Reindirizza alla pagina di annotazione del nuovo documento
            window.location.href = `/annotate/${nextDocId}`; // Adatta l'URL se necessario
            // Il caricamento non verrà nascosto perchè la pagina cambia
        } else if (result && result.status === 'success' && !result.document) {
             // Successo, ma nessun altro documento trovato
             showNotification('Nessun altro documento "In Corso" disponibile da annotare.', 'info');
             hideLoading(); // Nascondi qui perchè non c'è redirect
             if(nextDocumentBtn) {
                 nextDocumentBtn.disabled = false; // Riabilita bottone
                 nextDocumentBtn.innerHTML = '<i class="fas fa-forward me-1"></i> Prossimo Doc.';
             }
        } else {
            // L'API ha risposto ma non con successo o formato inatteso
            throw new Error(result?.message || 'Errore nel recupero del documento successivo.');
        }
    } catch (error) {
        console.error('Error getting next document:', error);
        const message = error.response?.data?.message || error.message || "Errore sconosciuto";
        showNotification(`Errore recupero prossimo documento: ${message}`, 'danger');
        hideLoading(); // Nascondi in caso di errore
        if(nextDocumentBtn) {
            nextDocumentBtn.disabled = false; // Riabilita bottone
            nextDocumentBtn.innerHTML = '<i class="fas fa-forward me-1"></i> Prossimo Doc.';
        }
    }
    // Non c'è finally per hideLoading qui perchè il redirect lo impedirebbe
}

// --- Event Listeners Setup ---
function setupEventListeners() {
    console.log("Setting up event listeners...");

    // Entity Type Selection
    entityTypeListEl?.addEventListener('click', (event) => {
        const target = event.target.closest('.entity-type');
        if (target && target.dataset.entityType) {
            setActiveEntityType(target.dataset.entityType); // Passa l'ID (stringa)
        }
    });

    // Text Selection for Annotation
    textContentEl?.addEventListener('mouseup', handleTextSelection);

    // Button Clicks (Annotation Controls)
    autoAnnotateBtn?.addEventListener('click', handleAutoAnnotate);
    clearSelectionBtn?.addEventListener('click', clearSelection);

    // Button Clicks (Text Editing)
    editBtn?.addEventListener('click', () => toggleTextEditing(true));
    saveBtn?.addEventListener('click', saveTextChanges);
    cancelBtn?.addEventListener('click', cancelTextEditing);

    // Button Clicks (Zoom)
    zoomInBtn?.addEventListener('click', () => handleZoom('in'));
    zoomOutBtn?.addEventListener('click', () => handleZoom('out'));
    zoomResetBtn?.addEventListener('click', () => handleZoom('reset'));

    // Button Clicks (Sorting)
    sortPositionBtn?.addEventListener('click', () => handleSort('position'));
    sortTypeBtn?.addEventListener('click', () => handleSort('type'));

    // Search Input
    searchInput?.addEventListener('input', handleSearch);

    // Button Clicks (Clear Annotations)
    clearAllBtn?.addEventListener('click', handleClearAllAnnotations);
    // Il bottone che apre il modal "Clear by Type" usa data-bs-toggle, quindi non serve listener per aprirlo
    // document.getElementById('open-clear-by-type-modal-btn')?.addEventListener('click', openClearByTypeModal); // Solo se non usi data-bs-toggle

    // Clear by Type Modal Interactions
    confirmClearByTypeBtn?.addEventListener('click', handleClearAnnotationsByType);
    clearByTypeSelect?.addEventListener('change', (event) => {
       if(confirmClearByTypeBtn) confirmClearByTypeBtn.disabled = !event.target.value;
    });

    // ++ Aggiunti Event Listener per Stato Documento ++
    markCompletedBtn?.addEventListener('click', () => changeDocumentStatus('completed'));
    markSkippedBtn?.addEventListener('click', () => changeDocumentStatus('skipped'));
    nextDocumentBtn?.addEventListener('click', goToNextDocument);

    // Keyboard Shortcuts
    setupKeyboardShortcuts(); // Chiama la funzione che inizializza KeyboardManager

    console.log("Event listeners set up.");
}


// --- Keyboard Shortcuts (Mantenuto il KeyboardManager esistente) ---
const KeyboardManager = {
    entityShortcuts: [],
    keyCodeToNumber: {
        'Digit1': '1', 'Digit2': '2', 'Digit3': '3', 'Digit4': '4', 'Digit5': '5',
        'Digit6': '6', 'Digit7': '7', 'Digit8': '8', 'Digit9': '9',
        'Numpad1': '1', 'Numpad2': '2', 'Numpad3': '3', 'Numpad4': '4', 'Numpad5': '5',
        'Numpad6': '6', 'Numpad7': '7', 'Numpad8': '8', 'Numpad9': '9'
    },
    init() {
        this.registerEntityShortcuts();
        // Rimuove eventuali listener precedenti prima di aggiungerne nuovi
        document.removeEventListener('keydown', this.boundHandleKeyDown, true);
        this.boundHandleKeyDown = this.handleKeyDown.bind(this); // Lega la funzione una sola volta
        document.addEventListener('keydown', this.boundHandleKeyDown, true); // Usa cattura

        // Rimuovi/Aggiungi listener anche sull'elemento di testo se esiste
        if (textContentEl) {
             textContentEl.removeEventListener('keydown', this.boundHandleKeyDown, true);
             textContentEl.addEventListener('keydown', this.boundHandleKeyDown, true); // Usa cattura
        }

        console.log("KeyboardManager initialized", { entityShortcuts: this.entityShortcuts });
    },
    registerEntityShortcuts() {
        this.entityShortcuts = [];
        if (!entityTypeListEl) {
            console.warn("entityTypeListEl not available for registering shortcuts");
            return;
        }
        const entityElements = entityTypeListEl.querySelectorAll('.entity-type[data-entity-type]'); // Assicurati che abbiano l'attributo
        entityElements.forEach((el, index) => {
            if (index < 9) { // Limit to 1-9
                const shortcutKey = String(index + 1);
                const entityTypeId = el.dataset.entityType; // Deve essere presente
                this.entityShortcuts.push({
                    key: shortcutKey,
                    type: entityTypeId, // Salva l'ID tipo (stringa)
                    element: el,
                    displayName: el.querySelector('.entity-name')?.textContent.trim() || entityTypeId
                });
                this.addShortcutBadge(el, shortcutKey);
            }
        });
        console.log(`Registered ${this.entityShortcuts.length} entity type shortcuts`);
    },
    addShortcutBadge(element, key) {
        let badge = element.querySelector('.shortcut-badge');
        if (!badge) {
            badge = document.createElement('span');
            // Aggiungi classi Bootstrap per stile e margine
            badge.className = 'shortcut-badge badge rounded-pill bg-secondary ms-1 small';
            // Inseriscilo magari prima del contatore se esiste
            const counter = element.querySelector('.entity-counter');
            if(counter) {
                 element.insertBefore(badge, counter);
            } else {
                element.appendChild(badge);
            }
        }
        badge.textContent = `Alt+${key}`;
        badge.classList.remove('d-none'); // Assicura sia visibile
    },
    // boundHandleKeyDown: null, // Riferimento alla funzione bindata per rimuoverla

    handleKeyDown(event) {
        // Se stiamo scrivendo in un input, textarea, o nel contentEditable (ma *non* il nostro textContentEl),
        // O se un modal è aperto, ignora le scorciatoie.
        // Aggiunta verifica per stato documento: ignora scorciatoie se completato/saltato? (Opzionale)
        if (this.shouldIgnoreKeyEvent(event)) {
            // console.log("Ignoring key event:", event.key, event.target);
            return;
        }

        // Gestione scorciatoie (logica esistente)
        const alt = event.altKey;
        const ctrl = event.ctrlKey;
        const shift = event.shiftKey;
        const key = event.key.toLowerCase();
        const code = event.code;

        // Alt + Numero (1-9) per tipo entità
        if (alt && !ctrl && !shift && this.isNumberKey(event)) {
            this.handleEntityShortcut(event);
            return; // Importante: return per non processare altre shortcut
        }

        // Alt + A per Auto-Annotate
        if (alt && !ctrl && !shift && (key === 'a' || code === 'KeyA')) {
            this.handleAutoAnnotateShortcut(event);
            return;
        }

        // Escape o Ctrl+Z per Clear Selection
        // Ctrl+Z potrebbe interferire con undo nativo se contentEditable è attivo.
        // Escape è più sicuro.
        if (key === 'escape' /*|| (ctrl && !alt && !shift && key === 'z')*/) {
             this.handleClearSelectionShortcut(event);
             return;
        }

        // ++ Aggiunta scorciatoie stato documento (Esempio) ++
        // Alt + C per Completato
        if (alt && !ctrl && !shift && (key === 'c' || code === 'KeyC')) {
             event.preventDefault();
             event.stopPropagation();
             if (markCompletedBtn && !markCompletedBtn.disabled) {
                 this.addVisualFeedback(markCompletedBtn, 'btn-flash');
                 changeDocumentStatus('completed'); // Chiama direttamente la funzione
             }
             return;
        }
        // Alt + S per Saltato
        if (alt && !ctrl && !shift && (key === 's' || code === 'KeyS')) {
             event.preventDefault();
             event.stopPropagation();
             if (markSkippedBtn && !markSkippedBtn.disabled) {
                 this.addVisualFeedback(markSkippedBtn, 'btn-flash');
                 changeDocumentStatus('skipped'); // Chiama direttamente la funzione
             }
             return;
        }
         // Alt + N per Prossimo Documento
         if (alt && !ctrl && !shift && (key === 'n' || code === 'KeyN')) {
             event.preventDefault();
             event.stopPropagation();
             if (nextDocumentBtn && !nextDocumentBtn.disabled) {
                 this.addVisualFeedback(nextDocumentBtn, 'btn-flash');
                 goToNextDocument(); // Chiama direttamente la funzione
             }
             return;
         }
    },
    isNumberKey(event) {
        return this.keyCodeToNumber[event.code] || /^[1-9]$/.test(event.key);
    },
    getNumberFromKey(event) {
        return this.keyCodeToNumber[event.code] || (/^[1-9]$/.test(event.key) ? event.key : null);
    },
    shouldIgnoreKeyEvent(event) {
        const target = event.target;
        const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;
        const isOurContentArea = target === textContentEl;
        const modalOpen = document.querySelector('.modal.show');

        // Ignora se:
        // 1. Un modal è aperto
        // 2. L'evento proviene da un input/textarea/contentEditable generico
        // 3. Stiamo modificando il testo principale (isEditingText) E l'evento NON è Escape (per permettere cancel)
        // 4. Il documento è completato o saltato (blocca la maggior parte delle scorciatoie qui?)
        // 5. L'evento è Alt+S e il target è l'input di ricerca (evita conflitto con "Salva Pagina") - specifico browser/OS?

        if (modalOpen) return true;
        if (isInput && !isOurContentArea) return true; // Ignora se in input/textarea/altro contentEditable
        if (isEditingText && event.key !== 'Escape') return true; // Ignora quasi tutto in modalità modifica testo

        // Aggiunta opzionale: bloccare scorciatoie se documento non è 'pending'?
        // if (documentStatus !== 'pending' && !(event.altKey && (event.key === 'n' || event.code === 'KeyN'))) { // Permetti solo 'Next'
        //     console.log("Ignoring shortcut because document status is:", documentStatus);
        //     return true;
        // }


        return false;
    },
    handleEntityShortcut(event) {
        event.preventDefault(); // Impedisce azioni default (es. Alt+1 focus menu)
        event.stopPropagation(); // Ferma la propagazione
        const numericKey = this.getNumberFromKey(event);
        if (!numericKey) return;
        const shortcut = this.entityShortcuts.find(s => s.key === numericKey);
        if (!shortcut) return;

        setActiveEntityType(shortcut.type); // Usa l'ID tipo salvato
        shortcut.element?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        this.addVisualFeedback(shortcut.element, 'keyboard-activate');
    },
    handleAutoAnnotateShortcut(event) {
        event.preventDefault();
        event.stopPropagation();
        if (autoAnnotateBtn && !autoAnnotateBtn.disabled) { // Controlla se il bottone è abilitato
            this.addVisualFeedback(autoAnnotateBtn, 'btn-flash');
            handleAutoAnnotate(); // Chiama la funzione globale
        }
    },
    handleClearSelectionShortcut(event) {
        // Non serve prevent default per Escape solitamente, ma non fa male
        event.preventDefault();
        event.stopPropagation();
        if (clearSelectionBtn) { // Bottone opzionale
            this.addVisualFeedback(clearSelectionBtn, 'btn-flash');
        }
        clearSelection(); // Chiama la funzione globale
    },
    addVisualFeedback(element, className, duration = 300) {
        if (!element) return;
        element.classList.add(className);
        setTimeout(() => element.classList.remove(className), duration);
    }
};

// Chiamata per inizializzare il gestore scorciatoie
function setupKeyboardShortcuts() {
    console.log("Initializing keyboard manager...");
    KeyboardManager.init(); // Chiama l'init del manager
}

// Mostra le scorciatoie (aggiornata per includere le nuove)
function showKeyboardShortcutsInfo() {
    let messages = ["Esc (Annulla Sel.)"]; // Inizia con le scorciatoie base

    if (KeyboardManager.entityShortcuts.length > 0) {
        messages.push(KeyboardManager.entityShortcuts
            .map(s => `Alt+${s.key} (${s.displayName.substring(0, 15)}${s.displayName.length > 15 ? '...' : ''})`) // Tronca nomi lunghi
            .join(', '));
    }

    if (autoAnnotateBtn) messages.push("Alt+A (Auto)");
    if (markCompletedBtn) messages.push("Alt+C (Completa)");
    if (markSkippedBtn) messages.push("Alt+S (Salta)");
    if (nextDocumentBtn) messages.push("Alt+N (Prossimo)");

    // Unisci i messaggi, magari su più righe se troppi
    const fullMessage = messages.join(', ');
    showNotification(fullMessage, 'info', 'Scorciatoie Tastiera', 8000); // Durata maggiore
}

// Funzione ausiliaria (opzionale) per disabilitare/abilitare controlli annotazione
/*
function disableAnnotationInterface(disable = true) {
    console.log(`Setting annotation interface disabled state to: ${disable}`);
    const elementsToDisable = [
        entityTypeListEl, textContentEl, annotationsContainerEl,
        autoAnnotateBtn, clearSelectionBtn, editBtn, saveBtn, cancelBtn,
        clearAllBtn, document.getElementById('open-clear-by-type-modal-btn'), // Bottone che apre il modal
         searchInput
        // Aggiungi altri controlli se necessario
    ];
    elementsToDisable.forEach(el => {
        if (el) {
            if (el.tagName === 'BUTTON' || el.tagName === 'INPUT' || el.tagName === 'SELECT') {
                el.disabled = disable;
            } else {
                // Per div o altri contenitori, potresti aggiungere una classe CSS
                el.classList.toggle('disabled-ui', disable);
                // Per textContentEl specificamente
                if (el === textContentEl) {
                    el.contentEditable = disable ? 'false' : (isEditingText ? 'true' : 'false'); // Ripristina contentEditable corretto
                }
            }
        }
    });
     // Disabilita/Riabilita anche le scorciatoie? Potrebbe essere complesso.
     // KeyboardManager.enabled = !disable; // Aggiungere stato a KeyboardManager
}
*/

// --- Public Init Function ---
export function initAnnotator() {
    console.log('Initializing Annotator Page...');
    try {
        cacheDOMElements(); // Trova elementi DOM
        loadInitialData(); // Carica dati iniziali (annotazioni, tipi entità) da script/attributi
        loadDocumentStatus(); // ++ Carica stato documento ++

        // Initialize Highlighting Engine
        // Assicurati che HighlightingEngine sia importato correttamente
        if (typeof HighlightingEngine !== 'undefined') {
            highlightingEngine = new HighlightingEngine(/* pass options if needed */);
            console.log("Highlighting engine initialized.");
        } else {
             console.error("HighlightingEngine not found/imported. Highlighting will not work.");
             // Potresti voler mostrare un errore all'utente o usare un fallback
             highlightingEngine = null; // Assicura sia null
        }


        setupEventListeners(); // Imposta listener per bottoni, selezione, ecc. (include setupKeyboardShortcuts)

        // Initial Render Cycle
        renderEntityTypeList(); // Assicura che la lista tipi sia renderizzata prima di contatori/highlighting
        renderAnnotationList(); // Renderizza la lista annotazioni
        updateHighlighting();  // Applica highlighting iniziale
        updateZoom();          // Imposta zoom iniziale
        handleSort(currentSort); // Applica sort default e aggiorna UI bottoni sort

        console.log("Annotator initialization complete.");
        // Mostra le scorciatoie dopo che tutto è pronto
        setTimeout(showKeyboardShortcutsInfo, 500); // Piccolo ritardo per non sovrapporsi ad altre notifiche

    } catch (error) {
         console.error("FATAL ERROR during annotator initialization:", error);
         const body = document.body;
         const errorDiv = document.createElement('div');
         errorDiv.className = 'alert alert-danger m-3'; // Usa classi Bootstrap
         errorDiv.setAttribute('role', 'alert');
         errorDiv.innerHTML = `<strong>Errore Critico Inizializzazione Annotatore:</strong><br>${error.message}<br>L'applicazione potrebbe non funzionare correttamente. Si prega di ricaricare la pagina o contattare il supporto.`;

         // Prova a inserire l'errore in un contenitore principale o nel body
         const mainContainer = document.querySelector('.container, .container-fluid') || body; // Trova un contenitore comune
         mainContainer.prepend(errorDiv); // Aggiungi all'inizio

         // Nascondi colonne principali per evitare interazioni con UI rotta
         document.getElementById('controls-column')?.classList.add('d-none');
         document.getElementById('main-content-column')?.classList.add('d-none');
         document.getElementById('annotations-column')?.classList.add('d-none');
    }
}

// --- Helper function per renderizzare la lista dei tipi (se necessario separatamente) ---
function renderEntityTypeList() {
    if (!entityTypeListEl || entityTypes.length === 0) {
        // console.log("Skipping entity type list rendering.");
        return;
    }
    // Qui potresti avere logica per creare dinamicamente gli elementi della lista
    // Se sono già nell'HTML, questa funzione potrebbe solo aggiornare i contatori
    // o assicurare che i badge delle scorciatoie siano presenti.
    // L'esempio attuale assume che gli elementi .entity-type siano già nell'HTML.
    // Aggiorna i contatori iniziali (saranno 0 se le annotazioni non sono ancora caricate)
    updateEntityTypeCounters();
     // Assicura che i badge shortcut siano aggiunti (se non già fatto da KeyboardManager)
     KeyboardManager.registerEntityShortcuts(); // Chiamarlo qui assicura che i badge siano aggiunti
}


// --- Auto-run Initialization ---
// Logica esistente per avviare l'init solo se siamo nella pagina corretta
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initIfAnnotationPage);
} else {
    initIfAnnotationPage();
}

function initIfAnnotationPage() {
    const isAnnotationPage = Boolean(
        document.getElementById('text-content') &&
        (document.getElementById('entityTypeList') || document.getElementById('annotationsContainer')) // Rende la condizione un po' più flessibile
    );

    if (!isAnnotationPage) {
        console.log("Not on the annotation page, skipping annotator initialization.");
        return;
    }

    console.log("Annotation page detected, proceeding with initialization.");
    initAnnotator(); // Chiama la funzione di inizializzazione principale
}