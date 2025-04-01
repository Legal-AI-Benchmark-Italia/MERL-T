/**
 * document-service.js - Servizio per la gestione dei documenti
 * 
 * Gestisce la logica di business per le operazioni sui documenti,
 * separando la logica dalla manipolazione del DOM.
 * 
 * @version 1.0.0
 */

import eventBus from '../core/event-bus.js';
import store from '../core/store.js';
import apiClient from '../core/api-client.js';
import errorHandler, { ErrorTypes } from '../core/error-handler.js';
import { generateId, countWords } from '../utils/utils.js';
import config from '../config/config.js';

class DocumentService {
    constructor() {
        // Registra i listener per gli eventi
        this._registerEventListeners();
    }
    
    /**
     * Registra i listener per gli eventi
     * @private
     */
    _registerEventListeners() {
        // Ascolta gli eventi di richiesta di caricamento documenti
        eventBus.on('document:load-request', this.loadDocuments.bind(this));
        
        // Ascolta gli eventi di richiesta di caricamento di un documento specifico
        eventBus.on('document:load-single-request', this.loadDocument.bind(this));
        
        // Ascolta gli eventi di richiesta di eliminazione documento
        eventBus.on('document:delete-request', this.deleteDocument.bind(this));
    }
    
    /**
     * Inizializza il servizio documenti
     * @returns {Promise<boolean>} - Promise che si risolve con lo stato dell'inizializzazione
     */
    async initialize() {
        try {
            // Carica i documenti
            await this.loadDocuments();
            
            return true;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante l\'inizializzazione del servizio documenti',
                ErrorTypes.UNKNOWN,
                { error }
            );
            return false;
        }
    }
    
    /**
     * Carica tutti i documenti
     * @returns {Promise<Array>} - Promise che si risolve con i documenti caricati
     */
    async loadDocuments() {
        try {
            store.commit('SET_PROCESSING', 'documents.isProcessing', true);
            
            // Carica i documenti dal server
            const response = await apiClient.get('/documents');
            
            if (response && response.documents) {
                // Aggiorna lo store con i documenti caricati
                store.commit('SET_DOCUMENTS', 'documents.list', response.documents);
                
                // Emette un evento per i documenti caricati
                eventBus.emit('document:loaded', { 
                    documents: response.documents 
                });
                
                return response.documents;
            }
            
            return [];
        } catch (error) {
            errorHandler.handleError(
                'Errore durante il caricamento dei documenti',
                ErrorTypes.NETWORK,
                { error }
            );
            return [];
        } finally {
            store.commit('SET_PROCESSING', 'documents.isProcessing', false);
        }
    }
    
    /**
     * Carica un documento specifico
     * @param {string} docId - ID del documento
     * @returns {Promise<Object>} - Promise che si risolve con il documento caricato
     */
    async loadDocument(docId) {
        try {
            store.commit('SET_PROCESSING', 'documents.isProcessing', true);
            
            // Carica il documento dal server
            const response = await apiClient.get(`/documents/${docId}`);
            
            if (response && response.document) {
                // Aggiorna lo store con il documento corrente
                store.commit('SET_CURRENT_DOCUMENT', 'documents.current', response.document);
                
                // Emette un evento per il documento caricato
                eventBus.emit('document:single-loaded', { 
                    document: response.document 
                });
                
                return response.document;
            }
            
            return null;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante il caricamento del documento',
                ErrorTypes.NETWORK,
                { docId, error }
            );
            return null;
        } finally {
            store.commit('SET_PROCESSING', 'documents.isProcessing', false);
        }
    }
    
    /**
     * Crea un nuovo documento
     * @param {Object} documentData - Dati del documento
     * @returns {Promise<Object>} - Promise che si risolve con il documento creato
     */
    async createDocument(documentData) {
        try {
            store.commit('SET_PROCESSING', 'documents.isProcessing', true);
            
            // Prepara i dati del documento
            const document = {
                ...documentData,
                id: documentData.id || generateId('doc'),
                date_created: documentData.date_created || new Date().toISOString(),
                word_count: documentData.word_count || countWords(documentData.text)
            };
            
            // Crea il documento sul server
            const response = await apiClient.post('/documents', document);
            
            if (response && response.document) {
                // Aggiorna la lista dei documenti nello store
                const documents = [...(store.getState('documents.list') || [])];
                documents.push(response.document);
                store.commit('SET_DOCUMENTS', 'documents.list', documents);
                
                // Emette un evento per il documento creato
                eventBus.emit('document:created', { 
                    document: response.document 
                });
                
                return response.document;
            }
            
            return null;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante la creazione del documento',
                ErrorTypes.NETWORK,
                { documentData, error }
            );
            return null;
        } finally {
            store.commit('SET_PROCESSING', 'documents.isProcessing', false);
        }
    }
    
    /**
     * Aggiorna un documento esistente
     * @param {string} docId - ID del documento
     * @param {Object} documentData - Dati aggiornati del documento
     * @returns {Promise<Object>} - Promise che si risolve con il documento aggiornato
     */
    async updateDocument(docId, documentData) {
        try {
            store.commit('SET_PROCESSING', 'documents.isProcessing', true);
            
            // Prepara i dati del documento
            const document = {
                ...documentData,
                id: docId,
                word_count: documentData.word_count || countWords(documentData.text)
            };
            
            // Aggiorna il documento sul server
            const response = await apiClient.put(`/documents/${docId}`, document);
            
            if (response && response.document) {
                // Aggiorna la lista dei documenti nello store
                const documents = [...(store.getState('documents.list') || [])];
                const index = documents.findIndex(d => d.id === docId);
                
                if (index !== -1) {
                    documents[index] = response.document;
                    store.commit('SET_DOCUMENTS', 'documents.list', documents);
                }
                
                // Aggiorna il documento corrente se è quello modificato
                const currentDoc = store.getState('documents.current');
                if (currentDoc && currentDoc.id === docId) {
                    store.commit('SET_CURRENT_DOCUMENT', 'documents.current', response.document);
                }
                
                // Emette un evento per il documento aggiornato
                eventBus.emit('document:updated', { 
                    document: response.document 
                });
                
                return response.document;
            }
            
            return null;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante l\'aggiornamento del documento',
                ErrorTypes.NETWORK,
                { docId, documentData, error }
            );
            return null;
        } finally {
            store.commit('SET_PROCESSING', 'documents.isProcessing', false);
        }
    }
    
    /**
     * Elimina un documento
     * @param {string} docId - ID del documento
     * @returns {Promise<boolean>} - Promise che si risolve con lo stato dell'eliminazione
     */
    async deleteDocument(docId) {
        try {
            store.commit('SET_PROCESSING', 'documents.isProcessing', true);
            
            // Elimina il documento dal server
            await apiClient.delete(`/documents/${docId}`);
            
            // Aggiorna la lista dei documenti nello store
            const documents = [...(store.getState('documents.list') || [])];
            const updatedDocuments = documents.filter(d => d.id !== docId);
            store.commit('SET_DOCUMENTS', 'documents.list', updatedDocuments);
            
            // Se il documento corrente è quello eliminato, resetta il documento corrente
            const currentDoc = store.getState('documents.current');
            if (currentDoc && currentDoc.id === docId) {
                store.commit('SET_CURRENT_DOCUMENT', 'documents.current', null);
            }
            
            // Emette un evento per il documento eliminato
            eventBus.emit('document:deleted', { docId });
            
            return true;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante l\'eliminazione del documento',
                ErrorTypes.NETWORK,
                { docId, error }
            );
            return false;
        } finally {
            store.commit('SET_PROCESSING', 'documents.isProcessing', false);
        }
    }
    
    /**
     * Carica un documento da file
     * @param {File} file - File del documento
     * @returns {Promise<Object>} - Promise che si risolve con il documento caricato
     */
    async uploadDocument(file) {
        try {
            store.commit('SET_PROCESSING', 'documents.isProcessing', true);
            
            // Verifica che il file sia valido
            if (!file) {
                throw new Error('Nessun file selezionato');
            }
            
            // Verifica la dimensione del file
            if (file.size > config.documentManager.maxFileSize) {
                throw new Error(`Il file è troppo grande (max ${config.documentManager.maxFileSize / 1024 / 1024}MB)`);
            }
            
            // Verifica il formato del file
            const fileExt = file.name.split('.').pop().toLowerCase();
            if (!config.documentManager.supportedFormats.includes(fileExt)) {
                throw new Error(`Formato file non supportato. Formati supportati: ${config.documentManager.supportedFormats.join(', ')}`);
            }
            
            // Crea un FormData per l'upload
            const formData = new FormData();
            formData.append('document', file);
            
            // Carica il file sul server
            const response = await apiClient.uploadFile('/documents/upload', formData);
            
            if (response && response.document) {
                // Aggiorna la lista dei documenti nello store
                const documents = [...(store.getState('documents.list') || [])];
                documents.push(response.document);
                store.commit('SET_DOCUMENTS', 'documents.list', documents);
                
                // Emette un evento per il documento caricato
                eventBus.emit('document:uploaded', { 
                    document: response.document 
                });
                
                return response.document;
            }
            
            return null;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante il caricamento del documento',
                ErrorTypes.NETWORK,
                { fileName: file?.name, error }
            );
            return null;
        } finally {
            store.commit('SET_PROCESSING', 'documents.isProcessing', false);
        }
    }
    
    /**
     * Filtra i documenti in base a una query di ricerca
     * @param {string} query - Query di ricerca
     * @returns {Array} - Documenti filtrati
     */
    filterDocuments(query) {
        try {
            const documents = store.getState('documents.list') || [];
            
            // Se la query è vuota, restituisci tutti i documenti
            if (!query || !query.trim()) {
                return documents;
            }
            
            const normalizedQuery = query.toLowerCase().trim();
            
            // Filtra i documenti
            return documents.filter(doc => {
                return (
                    (doc.title && doc.title.toLowerCase().includes(normalizedQuery)) ||
                    (doc.text && doc.text.toLowerCase().includes(normalizedQuery))
                );
            });
        } catch (error) {
            errorHandler.handleError(
                'Errore durante il filtraggio dei documenti',
                ErrorTypes.UNKNOWN,
                { query, error }
            );
            return [];
        }
    }
    
    /**
     * Esporta le annotazioni di un documento in formato JSON
     * @param {string} docId - ID del documento
     * @returns {Promise<Object>} - Promise che si risolve con le annotazioni esportate
     */
    async exportAnnotationsJson(docId) {
        try {
            store.commit('SET_PROCESSING', 'documents.isProcessing', true);
            
            // Richiedi l'esportazione in formato JSON al server
            const response = await apiClient.get(`/export-json/${docId}`);
            
            // Emette un evento per l'esportazione completata
            eventBus.emit('document:export-complete', { 
                docId, 
                format: 'json' 
            });
            
            return response;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante l\'esportazione delle annotazioni in JSON',
                ErrorTypes.NETWORK,
                { docId, error }
            );
            return null;
        } finally {
            store.commit('SET_PROCESSING', 'documents.isProcessing', false);
        }
    }
    
    /**
     * Esporta le annotazioni di un documento in formato spaCy
     * @param {string} docId - ID del documento
     * @returns {Promise<Object>} - Promise che si risolve con le annotazioni esportate
     */
    async exportAnnotationsSpacy(docId) {
        try {
            store.commit('SET_PROCESSING', 'documents.isProcessing', true);
            
            // Richiedi l'esportazione in formato spaCy al server
            const response = await apiClient.get(`/export-spacy/${docId}`);
            
            // Emette un evento per l'esportazione completata
            eventBus.emit('document:export-complete', { 
                docId, 
                format: 'spacy' 
            });
            
            return response;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante l\'esportazione delle annotazioni in formato spaCy',
                ErrorTypes.NETWORK,
                { docId, error }
            );
            return null;
        } finally {
            store.commit('SET_PROCESSING', 'documents.isProcessing', false);
        }
    }
}

// Crea un'istanza singleton del DocumentService
const documentService = new DocumentService();

// Esporta l'istanza singleton
export default documentService;
