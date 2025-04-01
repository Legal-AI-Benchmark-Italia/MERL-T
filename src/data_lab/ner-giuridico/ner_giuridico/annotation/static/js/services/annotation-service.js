/**
 * annotation-service.js - Servizio per la gestione delle annotazioni
 * 
 * Gestisce la logica di business per le operazioni di annotazione,
 * separando la logica dalla manipolazione del DOM.
 * 
 * @version 1.0.0
 */

import eventBus from '../core/event-bus.js';
import store from '../core/store.js';
import apiClient from '../core/api-client.js';
import errorHandler, { ErrorTypes } from '../core/error-handler.js';
import { generateId, deepClone } from '../utils/utils.js';
import config from '../config/config.js';

class AnnotationService {
    constructor() {
        // Registra i listener per gli eventi
        this._registerEventListeners();
    }
    
    /**
     * Registra i listener per gli eventi
     * @private
     */
    _registerEventListeners() {
        // Ascolta gli eventi di selezione del testo
        eventBus.on('text:selection', this.handleTextSelection.bind(this));
        
        // Ascolta gli eventi di selezione del tipo di entità
        eventBus.on('entity:type-selected', this.setSelectedEntityType.bind(this));
        
        // Ascolta gli eventi di richiesta di annotazione automatica
        eventBus.on('annotation:auto-annotate', this.performAutoAnnotation.bind(this));
    }
    
    /**
     * Inizializza il servizio di annotazione per un documento
     * @param {string} docId - ID del documento
     * @returns {Promise<boolean>} - Promise che si risolve con lo stato dell'inizializzazione
     */
    async initialize(docId) {
        try {
            // Imposta l'ID del documento nello store
            store.commit('SET_DOCUMENT_ID', 'annotator.docId', docId);
            
            // Carica le annotazioni esistenti
            await this.loadAnnotations(docId);
            
            // Segna come inizializzato
            store.commit('SET_INITIALIZED', 'annotator.initialized', true);
            
            // Emette un evento di inizializzazione completata
            eventBus.emit('annotation:initialized', { docId });
            
            return true;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante l\'inizializzazione del servizio di annotazione',
                ErrorTypes.UNKNOWN,
                { docId, error }
            );
            return false;
        }
    }
    
    /**
     * Carica le annotazioni esistenti per un documento
     * @param {string} docId - ID del documento
     * @returns {Promise<Array>} - Promise che si risolve con le annotazioni caricate
     */
    async loadAnnotations(docId) {
        try {
            store.commit('SET_PROCESSING', 'annotator.isProcessing', true);
            
            // Carica le annotazioni dal server
            const response = await apiClient.get(`/annotations/${docId}`);
            
            if (response && response.annotations) {
                // Aggiorna lo store con le annotazioni caricate
                store.commit('SET_ANNOTATIONS', 'annotator.annotations', response.annotations);
                
                // Emette un evento per le annotazioni caricate
                eventBus.emit('annotation:loaded', { 
                    docId, 
                    annotations: response.annotations 
                });
                
                return response.annotations;
            }
            
            return [];
        } catch (error) {
            errorHandler.handleError(
                'Errore durante il caricamento delle annotazioni',
                ErrorTypes.NETWORK,
                { docId, error }
            );
            return [];
        } finally {
            store.commit('SET_PROCESSING', 'annotator.isProcessing', false);
        }
    }
    
    /**
     * Imposta il tipo di entità selezionato
     * @param {string} entityType - Tipo di entità
     */
    setSelectedEntityType(entityType) {
        store.commit('SET_SELECTED_ENTITY_TYPE', 'annotator.selectedEntityType', entityType);
        eventBus.emit('annotation:entity-type-changed', { entityType });
    }
    
    /**
     * Gestisce la selezione del testo
     * @param {Object} selection - Oggetto con i dettagli della selezione
     */
    handleTextSelection(selection) {
        const selectedEntityType = store.getState('annotator.selectedEntityType');
        
        // Verifica che ci sia un tipo di entità selezionato
        if (!selectedEntityType) {
            eventBus.emit('annotation:error', { 
                message: 'Seleziona prima un tipo di entità' 
            });
            return;
        }
        
        // Verifica che la selezione sia valida
        if (!selection || !selection.text || selection.start === selection.end) {
            return;
        }
        
        // Crea una nuova annotazione
        this.createAnnotation(
            selection.text,
            selection.start,
            selection.end,
            selectedEntityType
        );
    }
    
    /**
     * Crea una nuova annotazione
     * @param {string} text - Testo selezionato
     * @param {number} start - Posizione di inizio
     * @param {number} end - Posizione di fine
     * @param {string} type - Tipo di entità
     * @returns {Object} - Nuova annotazione
     */
    createAnnotation(text, start, end, type) {
        try {
            const docId = store.getState('annotator.docId');
            
            // Verifica che ci sia un documento attivo
            if (!docId) {
                throw new Error('Nessun documento attivo');
            }
            
            // Crea l'oggetto annotazione
            const annotation = {
                id: generateId('ann'),
                text: text,
                start: start,
                end: end,
                type: type,
                created: new Date().toISOString()
            };
            
            // Ottieni le annotazioni correnti
            const annotations = deepClone(store.getState('annotator.annotations') || []);
            
            // Aggiungi la nuova annotazione
            annotations.push(annotation);
            
            // Aggiorna lo store
            store.commit('SET_ANNOTATIONS', 'annotator.annotations', annotations);
            
            // Salva l'annotazione
            this.saveAnnotations(docId, annotations);
            
            // Emetti un evento per la nuova annotazione
            eventBus.emit('annotation:created', { annotation });
            
            return annotation;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante la creazione dell\'annotazione',
                ErrorTypes.UNKNOWN,
                { text, start, end, type, error }
            );
            return null;
        }
    }
    
    /**
     * Elimina un'annotazione
     * @param {string} annotationId - ID dell'annotazione
     * @returns {boolean} - true se l'annotazione è stata eliminata
     */
    deleteAnnotation(annotationId) {
        try {
            const docId = store.getState('annotator.docId');
            
            // Verifica che ci sia un documento attivo
            if (!docId) {
                throw new Error('Nessun documento attivo');
            }
            
            // Ottieni le annotazioni correnti
            const annotations = deepClone(store.getState('annotator.annotations') || []);
            
            // Trova l'indice dell'annotazione
            const index = annotations.findIndex(a => a.id === annotationId);
            
            // Verifica che l'annotazione esista
            if (index === -1) {
                throw new Error(`Annotazione con ID ${annotationId} non trovata`);
            }
            
            // Rimuovi l'annotazione
            const deletedAnnotation = annotations.splice(index, 1)[0];
            
            // Aggiorna lo store
            store.commit('SET_ANNOTATIONS', 'annotator.annotations', annotations);
            
            // Salva le annotazioni
            this.saveAnnotations(docId, annotations);
            
            // Emetti un evento per l'annotazione eliminata
            eventBus.emit('annotation:deleted', { 
                annotationId, 
                annotation: deletedAnnotation 
            });
            
            return true;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante l\'eliminazione dell\'annotazione',
                ErrorTypes.UNKNOWN,
                { annotationId, error }
            );
            return false;
        }
    }
    
    /**
     * Elimina tutte le annotazioni di un tipo specifico
     * @param {string} entityType - Tipo di entità
     * @returns {number} - Numero di annotazioni eliminate
     */
    deleteAnnotationsByType(entityType) {
        try {
            const docId = store.getState('annotator.docId');
            
            // Verifica che ci sia un documento attivo
            if (!docId) {
                throw new Error('Nessun documento attivo');
            }
            
            // Ottieni le annotazioni correnti
            const allAnnotations = deepClone(store.getState('annotator.annotations') || []);
            
            // Filtra le annotazioni da mantenere
            const remainingAnnotations = allAnnotations.filter(a => a.type !== entityType);
            
            // Calcola il numero di annotazioni eliminate
            const deletedCount = allAnnotations.length - remainingAnnotations.length;
            
            // Se non ci sono annotazioni da eliminare, esci
            if (deletedCount === 0) {
                return 0;
            }
            
            // Aggiorna lo store
            store.commit('SET_ANNOTATIONS', 'annotator.annotations', remainingAnnotations);
            
            // Salva le annotazioni
            this.saveAnnotations(docId, remainingAnnotations);
            
            // Emetti un evento per le annotazioni eliminate
            eventBus.emit('annotation:deleted-by-type', { 
                entityType, 
                count: deletedCount 
            });
            
            return deletedCount;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante l\'eliminazione delle annotazioni per tipo',
                ErrorTypes.UNKNOWN,
                { entityType, error }
            );
            return 0;
        }
    }
    
    /**
     * Elimina tutte le annotazioni
     * @returns {number} - Numero di annotazioni eliminate
     */
    deleteAllAnnotations() {
        try {
            const docId = store.getState('annotator.docId');
            
            // Verifica che ci sia un documento attivo
            if (!docId) {
                throw new Error('Nessun documento attivo');
            }
            
            // Ottieni le annotazioni correnti
            const annotations = store.getState('annotator.annotations') || [];
            
            // Calcola il numero di annotazioni eliminate
            const deletedCount = annotations.length;
            
            // Se non ci sono annotazioni da eliminare, esci
            if (deletedCount === 0) {
                return 0;
            }
            
            // Aggiorna lo store
            store.commit('SET_ANNOTATIONS', 'annotator.annotations', []);
            
            // Salva le annotazioni
            this.saveAnnotations(docId, []);
            
            // Emetti un evento per le annotazioni eliminate
            eventBus.emit('annotation:deleted-all', { count: deletedCount });
            
            return deletedCount;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante l\'eliminazione di tutte le annotazioni',
                ErrorTypes.UNKNOWN,
                { error }
            );
            return 0;
        }
    }
    
    /**
     * Salva le annotazioni sul server
     * @param {string} docId - ID del documento
     * @param {Array} annotations - Annotazioni da salvare
     * @returns {Promise<boolean>} - Promise che si risolve con lo stato del salvataggio
     */
    async saveAnnotations(docId, annotations) {
        try {
            store.commit('SET_PROCESSING', 'annotator.isProcessing', true);
            
            // Salva le annotazioni sul server
            await apiClient.put(`/annotations/${docId}`, { annotations });
            
            // Emetti un evento per le annotazioni salvate
            eventBus.emit('annotation:saved', { 
                docId, 
                count: annotations.length 
            });
            
            return true;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante il salvataggio delle annotazioni',
                ErrorTypes.NETWORK,
                { docId, error }
            );
            
            // Incrementa il contatore degli errori
            const errorCount = (store.getState('annotator.errorCount') || 0) + 1;
            store.commit('SET_ERROR_COUNT', 'annotator.errorCount', errorCount);
            
            return false;
        } finally {
            store.commit('SET_PROCESSING', 'annotator.isProcessing', false);
        }
    }
    
    /**
     * Esegue l'annotazione automatica
     * @returns {Promise<number>} - Promise che si risolve con il numero di annotazioni create
     */
    async performAutoAnnotation() {
        try {
            const docId = store.getState('annotator.docId');
            
            // Verifica che ci sia un documento attivo
            if (!docId) {
                throw new Error('Nessun documento attivo');
            }
            
            store.commit('SET_PROCESSING', 'annotator.isProcessing', true);
            
            // Emetti un evento per l'inizio dell'annotazione automatica
            eventBus.emit('annotation:auto-annotate-start');
            
            // Richiedi l'annotazione automatica al server
            const response = await apiClient.post(`/auto-annotate/${docId}`);
            
            if (response && response.annotations) {
                // Ottieni le annotazioni correnti
                const currentAnnotations = deepClone(store.getState('annotator.annotations') || []);
                
                // Unisci le annotazioni esistenti con quelle nuove
                const mergedAnnotations = this._mergeAnnotations(currentAnnotations, response.annotations);
                
                // Aggiorna lo store
                store.commit('SET_ANNOTATIONS', 'annotator.annotations', mergedAnnotations);
                
                // Salva le annotazioni
                await this.saveAnnotations(docId, mergedAnnotations);
                
                // Calcola il numero di nuove annotazioni
                const newCount = mergedAnnotations.length - currentAnnotations.length;
                
                // Emetti un evento per il completamento dell'annotazione automatica
                eventBus.emit('annotation:auto-annotate-complete', { 
                    count: newCount 
                });
                
                return newCount;
            }
            
            return 0;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante l\'annotazione automatica',
                ErrorTypes.NETWORK,
                { error }
            );
            
            // Emetti un evento per l'errore
            eventBus.emit('annotation:auto-annotate-error', { 
                error: error.message 
            });
            
            return 0;
        } finally {
            store.commit('SET_PROCESSING', 'annotator.isProcessing', false);
        }
    }
    
    /**
     * Unisce le annotazioni esistenti con quelle nuove
     * @private
     * @param {Array} existing - Annotazioni esistenti
     * @param {Array} newAnnotations - Nuove annotazioni
     * @returns {Array} - Annotazioni unite
     */
    _mergeAnnotations(existing, newAnnotations) {
        // Crea una mappa delle annotazioni esistenti per posizione
        const existingMap = new Map();
        
        existing.forEach(ann => {
            const key = `${ann.start}-${ann.end}-${ann.type}`;
            existingMap.set(key, ann);
        });
        
        // Filtra le nuove annotazioni per rimuovere quelle già esistenti
        const uniqueNew = newAnnotations.filter(ann => {
            const key = `${ann.start}-${ann.end}-${ann.type}`;
            return !existingMap.has(key);
        });
        
        // Aggiungi un ID alle nuove annotazioni
        uniqueNew.forEach(ann => {
            ann.id = generateId('ann');
            ann.created = new Date().toISOString();
        });
        
        // Unisci le annotazioni
        return [...existing, ...uniqueNew];
    }
    
    /**
     * Esporta le annotazioni in formato JSON
     * @returns {Object} - Oggetto con le annotazioni esportate
     */
    exportAnnotationsJson() {
        try {
            const docId = store.getState('annotator.docId');
            const annotations = store.getState('annotator.annotations') || [];
            
            return {
                docId,
                annotations,
                exportDate: new Date().toISOString(),
                format: 'json'
            };
        } catch (error) {
            errorHandler.handleError(
                'Errore durante l\'esportazione delle annotazioni in JSON',
                ErrorTypes.UNKNOWN,
                { error }
            );
            return null;
        }
    }
    
    /**
     * Esporta le annotazioni in formato spaCy
     * @returns {Promise<Object>} - Promise che si risolve con le annotazioni in formato spaCy
     */
    async exportAnnotationsSpacy() {
        try {
            const docId = store.getState('annotator.docId');
            
            // Verifica che ci sia un documento attivo
            if (!docId) {
                throw new Error('Nessun documento attivo');
            }
            
            // Richiedi l'esportazione in formato spaCy al server
            const response = await apiClient.get(`/export-spacy/${docId}`);
            
            return response;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante l\'esportazione delle annotazioni in formato spaCy',
                ErrorTypes.NETWORK,
                { error }
            );
            return null;
        }
    }
}

// Crea un'istanza singleton dell'AnnotationService
const annotationService = new AnnotationService();

// Esporta l'istanza singleton
export default annotationService;
