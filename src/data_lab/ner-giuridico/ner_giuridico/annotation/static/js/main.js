/**
 * main.js - Punto di ingresso principale dell'applicazione
 * 
 * Questo file è responsabile dell'avvio dell'applicazione e del caricamento
 * dei componenti necessari in base alla pagina corrente.
 * 
 * @version 1.0.0
 */

import appInitializer from './core/app-initializer.js';
import eventBus from './core/event-bus.js';
import store from './core/store.js';
import errorHandler from './core/error-handler.js';
import config from './config/config.js';
import notificationService from './services/notification-service.js';
import highlightingComponent from './components/highlighting-component.js';

// Componenti specifici per pagina
import annotationService from './services/annotation-service.js';
import documentService from './services/document-service.js';
import entityService from './services/entity-service.js';

/**
 * Inizializza l'applicazione in base alla pagina corrente
 */
document.addEventListener('DOMContentLoaded', async () => {
    try {
        console.info('Avvio dell\'applicazione NER-Giuridico...');
        
        // Determina la pagina corrente
        const pageId = document.body.dataset.page || 'generic';
        console.info(`Pagina corrente: ${pageId}`);
        
        // Opzioni di inizializzazione comuni
        const commonOptions = {
            pageId: pageId
        };
        
        // Inizializza in base alla pagina
        switch (pageId) {
            case 'index':
                await initializeIndexPage(commonOptions);
                break;
                
            case 'annotate':
                await initializeAnnotatePage(commonOptions);
                break;
                
            case 'entity_types':
                await initializeEntityTypesPage(commonOptions);
                break;
                
            default:
                await initializeGenericPage(commonOptions);
        }
        
        console.info('Applicazione avviata con successo');
        
        // Notifica l'utente
        notificationService.info('Applicazione caricata con successo');
    } catch (error) {
        console.error('Errore durante l\'avvio dell\'applicazione:', error);
        
        // Gestisci l'errore
        errorHandler.handleError(
            'Errore durante l\'avvio dell\'applicazione',
            'initialization',
            error
        );
        
        // Notifica l'utente
        notificationService.error('Si è verificato un errore durante il caricamento dell\'applicazione');
    }
});

/**
 * Inizializza la pagina principale (index)
 * @param {Object} options - Opzioni di inizializzazione
 */
async function initializeIndexPage(options) {
    // Opzioni specifiche per la pagina index
    const indexOptions = {
        ...options,
        initAnnotationService: false,
        pageComponents: []
    };
    
    // Inizializza l'applicazione
    await appInitializer.initialize(indexOptions);
    
    // Carica i documenti
    eventBus.emit('document:load-request');
    
    // Configura gli event handler specifici della pagina
    setupIndexPageEventHandlers();
}

/**
 * Inizializza la pagina di annotazione
 * @param {Object} options - Opzioni di inizializzazione
 */
async function initializeAnnotatePage(options) {
    // Ottieni l'ID del documento dalla pagina
    const textContent = document.getElementById('text-content');
    const documentId = textContent ? textContent.dataset.docId : null;
    
    if (!documentId) {
        throw new Error('ID documento non trovato');
    }
    
    // Opzioni specifiche per la pagina di annotazione
    const annotateOptions = {
        ...options,
        documentId: documentId,
        pageComponents: [highlightingComponent]
    };
    
    // Inizializza l'applicazione
    await appInitializer.initialize(annotateOptions);
    
    // Inizializza il componente di evidenziazione
    highlightingComponent.initialize(textContent);
    
    // Configura gli event handler specifici della pagina
    setupAnnotatePageEventHandlers();
}

/**
 * Inizializza la pagina dei tipi di entità
 * @param {Object} options - Opzioni di inizializzazione
 */
async function initializeEntityTypesPage(options) {
    // Opzioni specifiche per la pagina dei tipi di entità
    const entityTypesOptions = {
        ...options,
        initAnnotationService: false,
        pageComponents: []
    };
    
    // Inizializza l'applicazione
    await appInitializer.initialize(entityTypesOptions);
    
    // Configura gli event handler specifici della pagina
    setupEntityTypesPageEventHandlers();
}

/**
 * Inizializza una pagina generica
 * @param {Object} options - Opzioni di inizializzazione
 */
async function initializeGenericPage(options) {
    // Opzioni per pagine generiche
    const genericOptions = {
        ...options,
        initAnnotationService: false,
        initDocumentService: false,
        pageComponents: []
    };
    
    // Inizializza l'applicazione
    await appInitializer.initialize(genericOptions);
}

/**
 * Configura gli event handler per la pagina principale
 */
function setupIndexPageEventHandlers() {
    // Gestione del form di upload
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        uploadForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            
            const fileInput = document.getElementById('document-file');
            if (!fileInput || !fileInput.files || !fileInput.files[0]) {
                notificationService.warning('Seleziona un file da caricare');
                return;
            }
            
            const file = fileInput.files[0];
            
            try {
                // Mostra un indicatore di caricamento
                notificationService.info('Caricamento del documento in corso...');
                
                // Carica il documento
                const document = await documentService.uploadDocument(file);
                
                if (document) {
                    notificationService.success('Documento caricato con successo');
                    
                    // Ricarica la lista dei documenti
                    eventBus.emit('document:load-request');
                    
                    // Resetta il form
                    uploadForm.reset();
                } else {
                    notificationService.error('Errore durante il caricamento del documento');
                }
            } catch (error) {
                notificationService.error('Errore durante il caricamento del documento');
                console.error('Errore durante il caricamento del documento:', error);
            }
        });
    }
    
    // Gestione dei pulsanti di esportazione
    const exportJsonBtn = document.getElementById('export-json');
    if (exportJsonBtn) {
        exportJsonBtn.addEventListener('click', async () => {
            try {
                notificationService.info('Esportazione delle annotazioni in formato JSON...');
                
                // Esporta le annotazioni
                const result = await documentService.exportAnnotationsJson();
                
                if (result) {
                    notificationService.success('Annotazioni esportate con successo');
                    
                    // Scarica il file
                    window.location.href = `/api/download-export?format=json&timestamp=${Date.now()}`;
                } else {
                    notificationService.error('Errore durante l\'esportazione delle annotazioni');
                }
            } catch (error) {
                notificationService.error('Errore durante l\'esportazione delle annotazioni');
                console.error('Errore durante l\'esportazione delle annotazioni:', error);
            }
        });
    }
    
    const exportSpacyBtn = document.getElementById('export-spacy');
    if (exportSpacyBtn) {
        exportSpacyBtn.addEventListener('click', async () => {
            try {
                notificationService.info('Esportazione delle annotazioni in formato spaCy...');
                
                // Esporta le annotazioni
                const result = await documentService.exportAnnotationsSpacy();
                
                if (result) {
                    notificationService.success('Annotazioni esportate con successo');
                    
                    // Scarica il file
                    window.location.href = `/api/download-export?format=spacy&timestamp=${Date.now()}`;
                } else {
                    notificationService.error('Errore durante l\'esportazione delle annotazioni');
                }
            } catch (error) {
                notificationService.error('Errore durante l\'esportazione delle annotazioni');
                console.error('Errore durante l\'esportazione delle annotazioni:', error);
            }
        });
    }
    
    // Gestione della ricerca documenti
    const searchInput = document.getElementById('search-documents');
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            const query = searchInput.value;
            
            // Filtra i documenti
            const filteredDocuments = documentService.filterDocuments(query);
            
            // Aggiorna lo store
            store.commit('SET_FILTER_TEXT', 'documents.filterText', query);
            
            // Emetti un evento per i documenti filtrati
            eventBus.emit('document:filtered', { 
                documents: filteredDocuments,
                query: query
            });
            
            // Aggiorna la UI
            updateDocumentList(filteredDocuments);
        });
    }
}

/**
 * Configura gli event handler per la pagina di annotazione
 */
function setupAnnotatePageEventHandlers() {
    // Gestione della selezione del tipo di entità
    const entityTypes = document.querySelectorAll('.entity-type');
    entityTypes.forEach(entityType => {
        entityType.addEventListener('click', () => {
            // Rimuovi la selezione da tutti i tipi
            entityTypes.forEach(el => el.classList.remove('selected'));
            
            // Aggiungi la selezione al tipo cliccato
            entityType.classList.add('selected');
            
            // Emetti un evento per la selezione del tipo
            eventBus.emit('entity:type-selected', entityType.dataset.type);
        });
    });
    
    // Gestione dell'annotazione automatica
    const autoAnnotateBtn = document.getElementById('auto-annotate');
    if (autoAnnotateBtn) {
        autoAnnotateBtn.addEventListener('click', async () => {
            try {
                notificationService.info('Annotazione automatica in corso...');
                
                // Esegui l'annotazione automatica
                const count = await annotationService.performAutoAnnotation();
                
                if (count > 0) {
                    notificationService.success(`Aggiunte ${count} nuove annotazioni`);
                } else {
                    notificationService.info('Nessuna nuova annotazione trovata');
                }
            } catch (error) {
                notificationService.error('Errore durante l\'annotazione automatica');
                console.error('Errore durante l\'annotazione automatica:', error);
            }
        });
    }
    
    // Gestione della cancellazione della selezione
    const clearSelectionBtn = document.getElementById('clear-selection');
    if (clearSelectionBtn) {
        clearSelectionBtn.addEventListener('click', () => {
            // Rimuovi la selezione da tutti i tipi
            entityTypes.forEach(el => el.classList.remove('selected'));
            
            // Emetti un evento per la deselezione
            eventBus.emit('entity:type-selected', null);
        });
    }
    
    // Gestione della ricerca nelle annotazioni
    const searchAnnotationsInput = document.getElementById('search-annotations');
    if (searchAnnotationsInput) {
        searchAnnotationsInput.addEventListener('input', () => {
            const query = searchAnnotationsInput.value.toLowerCase();
            
            // Filtra le annotazioni
            const annotationItems = document.querySelectorAll('.annotation-item');
            
            annotationItems.forEach(item => {
                const text = item.querySelector('.annotation-text').textContent.toLowerCase();
                const type = item.querySelector('.annotation-type').textContent.toLowerCase();
                
                if (text.includes(query) || type.includes(query)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
            
            // Aggiorna il contatore
            updateVisibleAnnotationsCount();
        });
    }
    
    // Gestione delle azioni sulle annotazioni
    const annotationsContainer = document.getElementById('annotations-container');
    if (annotationsContainer) {
        annotationsContainer.addEventListener('click', (event) => {
            // Gestione pulsante eliminazione
            if (event.target.closest('.delete-annotation')) {
                const btn = event.target.closest('.delete-annotation');
                const annotationId = btn.dataset.id;
                
                // Chiedi conferma
                if (confirm('Sei sicuro di voler eliminare questa annotazione?')) {
                    // Elimina l'annotazione
                    annotationService.deleteAnnotation(annotationId);
                }
                return;
            }
            
            // Gestione pulsante di navigazione
            if (event.target.closest('.jump-to-annotation')) {
                const btn = event.target.closest('.jump-to-annotation');
                const annotationId = btn.dataset.id;
                
                // Emetti un evento per selezionare l'annotazione
                eventBus.emit('annotation:selected', { annotationId });
                return;
            }
        });
    }
}

/**
 * Configura gli event handler per la pagina dei tipi di entità
 */
function setupEntityTypesPageEventHandlers() {
    // Gestione del form di creazione/modifica
    const entityForm = document.getElementById('entity-type-form');
    if (entityForm) {
        entityForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            
            // Raccogli i dati dal form
            const formData = new FormData(entityForm);
            const entityData = {
                name: formData.get('name'),
                displayName: formData.get('display-name'),
                category: formData.get('category'),
                color: formData.get('color'),
                description: formData.get('description')
            };
            
            // Verifica se è in modalità modifica
            const editMode = document.getElementById('edit-mode');
            const originalName = document.getElementById('original-name');
            
            try {
                if (editMode && editMode.value === 'true' && originalName) {
                    // Aggiorna il tipo di entità
                    const entityId = originalName.value;
                    
                    notificationService.info('Aggiornamento del tipo di entità in corso...');
                    
                    const result = await entityService.updateEntityType(entityId, entityData);
                    
                    if (result) {
                        notificationService.success('Tipo di entità aggiornato con successo');
                        
                        // Ricarica i tipi di entità
                        eventBus.emit('entity:load-request');
                        
                        // Resetta il form
                        entityForm.reset();
                        
                        // Nascondi il form
                        const formContainer = document.getElementById('entity-type-form-container');
                        if (formContainer) {
                            formContainer.style.display = 'none';
                        }
                    } else {
                        notificationService.error('Errore durante l\'aggiornamento del tipo di entità');
                    }
                } else {
                    // Crea un nuovo tipo di entità
                    notificationService.info('Creazione del tipo di entità in corso...');
                    
                    const result = await entityService.createEntityType(entityData);
                    
                    if (result) {
                        notificationService.success('Tipo di entità creato con successo');
                        
                        // Ricarica i tipi di entità
                        eventBus.emit('entity:load-request');
                        
                        // Resetta il form
                        entityForm.reset();
                        
                        // Nascondi il form
                        const formContainer = document.getElementById('entity-type-form-container');
                        if (formContainer) {
                            formContainer.style.display = 'none';
                        }
                    } else {
                        notificationService.error('Errore durante la creazione del tipo di entità');
                    }
                }
            } catch (error) {
                notificationService.error('Errore durante l\'operazione sul tipo di entità');
                console.error('Errore durante l\'operazione sul tipo di entità:', error);
            }
        });
    }
    
    // Gestione del pulsante di aggiunta
    const addEntityBtn = document.getElementById('add-entity-type-btn');
    if (addEntityBtn) {
        addEntityBtn.addEventListener('click', () => {
            // Resetta il form
            const entityForm = document.getElementById('entity-type-form');
            if (entityForm) {
                entityForm.reset();
            }
            
            // Imposta la modalità di creazione
            const editMode = document.getElementById('edit-mode');
            if (editMode) {
                editMode.value = 'false';
            }
            
            // Aggiorna il titolo del form
            const formTitle = document.getElementById('form-title');
            if (formTitle) {
                formTitle.textContent = 'Crea nuovo tipo di entità';
            }
            
            // Mostra il form
            const formContainer = document.getElementById('entity-type-form-container');
            if (formContainer) {
                formContainer.style.display = 'block';
            }
        });
    }
    
    // Gestione del pulsante di annullamento
    const cancelBtn = document.getElementById('cancel-btn');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', (event) => {
            event.preventDefault();
            
            // Nascondi il form
            const formContainer = document.getElementById('entity-type-form-container');
            if (formContainer) {
                formContainer.style.display = 'none';
            }
        });
    }
    
    // Gestione della ricerca nei tipi di entità
    const searchEntityInput = document.getElementById('entity-search');
    if (searchEntityInput) {
        searchEntityInput.addEventListener('input', () => {
            const query = searchEntityInput.value;
            const categoryFilter = document.getElementById('category-filter');
            const category = categoryFilter ? categoryFilter.value : null;
            
            // Filtra i tipi di entità
            const filteredEntities = entityService.filterEntityTypes(query, category);
            
            // Aggiorna lo store
            store.commit('SET_FILTER_TEXT', 'entities.filterText', query);
            
            // Emetti un evento per i tipi di entità filtrati
            eventBus.emit('entity:filtered', { 
                entities: filteredEntities,
                query: query,
                category: category
            });
            
            // Aggiorna la UI
            updateEntityTypesList(filteredEntities);
        });
    }
}

/**
 * Aggiorna la lista dei documenti nella UI
 * @param {Array} documents - Documenti da visualizzare
 */
function updateDocumentList(documents) {
    const container = document.querySelector('.row-cols-1');
    if (!container) return;
    
    // Aggiorna il conteggio
    const countElement = document.querySelector('.badge.bg-primary');
    if (countElement) {
        countElement.textContent = documents.length;
    }
    
    // Mostra/nascondi il messaggio "nessun documento"
    const emptyState = document.querySelector('.text-center.py-5');
    if (emptyState) {
        emptyState.style.display = documents.length === 0 ? 'block' : 'none';
    }
    
    // Aggiorna la visibilità delle card
    const docCards = document.querySelectorAll('.doc-card');
    docCards.forEach(card => {
        const docId = card.dataset.id;
        const isVisible = documents.some(doc => doc.id === docId);
        card.style.display = isVisible ? '' : 'none';
    });
}

/**
 * Aggiorna la lista dei tipi di entità nella UI
 * @param {Array} entityTypes - Tipi di entità da visualizzare
 */
function updateEntityTypesList(entityTypes) {
    const tableBody = document.querySelector('#entity-types-table tbody');
    if (!tableBody) return;
    
    // Mostra/nascondi il messaggio "nessun tipo di entità"
    const emptyState = document.getElementById('empty-state');
    if (emptyState) {
        emptyState.style.display = entityTypes.length === 0 ? 'block' : 'none';
    }
    
    // Aggiorna la visibilità delle righe
    const rows = tableBody.querySelectorAll('tr');
    rows.forEach(row => {
        const entityId = row.dataset.id;
        const isVisible = entityTypes.some(entity => entity.id === entityId);
        row.style.display = isVisible ? '' : 'none';
    });
}

/**
 * Aggiorna il conteggio delle annotazioni visibili
 */
function updateVisibleAnnotationsCount() {
    const container = document.getElementById('annotations-container');
    const countElement = document.getElementById('visible-count');
    
    if (!container || !countElement) return;
    
    const visibleItems = container.querySelectorAll('.annotation-item:not([style*="display: none"])');
    countElement.textContent = visibleItems.length;
}

// Esporta le funzioni per i test
export {
    initializeIndexPage,
    initializeAnnotatePage,
    initializeEntityTypesPage,
    initializeGenericPage
};
