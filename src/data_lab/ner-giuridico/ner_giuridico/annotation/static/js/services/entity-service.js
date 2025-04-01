/**
 * entity-service.js - Servizio per la gestione delle entità
 * 
 * Gestisce la logica di business per le operazioni sui tipi di entità,
 * separando la logica dalla manipolazione del DOM.
 * 
 * @version 1.0.0
 */

import eventBus from '../core/event-bus.js';
import store from '../core/store.js';
import apiClient from '../core/api-client.js';
import errorHandler, { ErrorTypes } from '../core/error-handler.js';
import { generateId } from '../utils/utils.js';
import config from '../config/config.js';

class EntityService {
    constructor() {
        // Cache delle entità per ottimizzare le prestazioni
        this.entityCache = {
            byId: {},
            byCategory: {}
        };
        
        // Registra i listener per gli eventi
        this._registerEventListeners();
    }
    
    /**
     * Registra i listener per gli eventi
     * @private
     */
    _registerEventListeners() {
        // Ascolta gli eventi di richiesta di caricamento entità
        eventBus.on('entity:load-request', this.loadEntityTypes.bind(this));
        
        // Ascolta gli eventi di richiesta di creazione entità
        eventBus.on('entity:create-request', this.createEntityType.bind(this));
        
        // Ascolta gli eventi di richiesta di aggiornamento entità
        eventBus.on('entity:update-request', (data) => {
            this.updateEntityType(data.id, data.entityData);
        });
        
        // Ascolta gli eventi di richiesta di eliminazione entità
        eventBus.on('entity:delete-request', this.deleteEntityType.bind(this));
    }
    
    /**
     * Inizializza il servizio entità
     * @returns {Promise<boolean>} - Promise che si risolve con lo stato dell'inizializzazione
     */
    async initialize() {
        try {
            // Carica i tipi di entità
            await this.loadEntityTypes();
            
            return true;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante l\'inizializzazione del servizio entità',
                ErrorTypes.UNKNOWN,
                { error }
            );
            return false;
        }
    }
    
    /**
     * Carica tutti i tipi di entità
     * @returns {Promise<Array>} - Promise che si risolve con i tipi di entità caricati
     */
    async loadEntityTypes() {
        try {
            store.commit('SET_LOADING', 'entities.isLoading', true);
            
            // Carica i tipi di entità dal server
            const response = await apiClient.get('/entity-types');
            
            if (response && response.entityTypes) {
                // Aggiorna lo store con i tipi di entità caricati
                store.commit('SET_ENTITY_TYPES', 'entities.types', response.entityTypes);
                
                // Aggiorna la cache
                this._updateCache(response.entityTypes);
                
                // Emette un evento per i tipi di entità caricati
                eventBus.emit('entity:loaded', { 
                    entityTypes: response.entityTypes 
                });
                
                return response.entityTypes;
            }
            
            return [];
        } catch (error) {
            errorHandler.handleError(
                'Errore durante il caricamento dei tipi di entità',
                ErrorTypes.NETWORK,
                { error }
            );
            return [];
        } finally {
            store.commit('SET_LOADING', 'entities.isLoading', false);
        }
    }
    
    /**
     * Ottiene un tipo di entità per ID
     * @param {string} entityId - ID del tipo di entità
     * @returns {Object|null} - Tipo di entità o null se non trovato
     */
    getEntityType(entityId) {
        try {
            // Prova prima dalla cache
            if (this.entityCache.byId[entityId]) {
                return this.entityCache.byId[entityId];
            }
            
            // Altrimenti cerca nello store
            const entityTypes = store.getState('entities.types') || [];
            const entityType = entityTypes.find(e => e.id === entityId);
            
            // Aggiorna la cache se trovato
            if (entityType) {
                this.entityCache.byId[entityId] = entityType;
            }
            
            return entityType || null;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante il recupero del tipo di entità',
                ErrorTypes.UNKNOWN,
                { entityId, error }
            );
            return null;
        }
    }
    
    /**
     * Ottiene tutti i tipi di entità per categoria
     * @param {string} category - Categoria
     * @returns {Array} - Tipi di entità nella categoria
     */
    getEntityTypesByCategory(category) {
        try {
            // Prova prima dalla cache
            if (this.entityCache.byCategory[category]) {
                return [...this.entityCache.byCategory[category]];
            }
            
            // Altrimenti filtra dallo store
            const entityTypes = store.getState('entities.types') || [];
            const filteredTypes = entityTypes.filter(e => e.category === category);
            
            // Aggiorna la cache
            this.entityCache.byCategory[category] = filteredTypes;
            
            return [...filteredTypes];
        } catch (error) {
            errorHandler.handleError(
                'Errore durante il recupero dei tipi di entità per categoria',
                ErrorTypes.UNKNOWN,
                { category, error }
            );
            return [];
        }
    }
    
    /**
     * Crea un nuovo tipo di entità
     * @param {Object} entityData - Dati del tipo di entità
     * @returns {Promise<Object>} - Promise che si risolve con il tipo di entità creato
     */
    async createEntityType(entityData) {
        try {
            store.commit('SET_LOADING', 'entities.isLoading', true);
            
            // Prepara i dati del tipo di entità
            const entityType = {
                ...entityData,
                id: entityData.id || entityData.name.toUpperCase().replace(/\s+/g, '_'),
                color: entityData.color || config.entityManager.defaultColor
            };
            
            // Crea il tipo di entità sul server
            const response = await apiClient.post('/entity-types', entityType);
            
            if (response && response.entityType) {
                // Aggiorna la lista dei tipi di entità nello store
                const entityTypes = [...(store.getState('entities.types') || [])];
                entityTypes.push(response.entityType);
                store.commit('SET_ENTITY_TYPES', 'entities.types', entityTypes);
                
                // Aggiorna la cache
                this._updateCache([response.entityType]);
                
                // Emette un evento per il tipo di entità creato
                eventBus.emit('entity:created', { 
                    entityType: response.entityType 
                });
                
                return response.entityType;
            }
            
            return null;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante la creazione del tipo di entità',
                ErrorTypes.NETWORK,
                { entityData, error }
            );
            return null;
        } finally {
            store.commit('SET_LOADING', 'entities.isLoading', false);
        }
    }
    
    /**
     * Aggiorna un tipo di entità esistente
     * @param {string} entityId - ID del tipo di entità
     * @param {Object} entityData - Dati aggiornati del tipo di entità
     * @returns {Promise<Object>} - Promise che si risolve con il tipo di entità aggiornato
     */
    async updateEntityType(entityId, entityData) {
        try {
            store.commit('SET_LOADING', 'entities.isLoading', true);
            
            // Aggiorna il tipo di entità sul server
            const response = await apiClient.put(`/entity-types/${entityId}`, entityData);
            
            if (response && response.entityType) {
                // Aggiorna la lista dei tipi di entità nello store
                const entityTypes = [...(store.getState('entities.types') || [])];
                const index = entityTypes.findIndex(e => e.id === entityId);
                
                if (index !== -1) {
                    entityTypes[index] = response.entityType;
                    store.commit('SET_ENTITY_TYPES', 'entities.types', entityTypes);
                }
                
                // Aggiorna la cache
                this._updateCache([response.entityType]);
                
                // Emette un evento per il tipo di entità aggiornato
                eventBus.emit('entity:updated', { 
                    entityType: response.entityType 
                });
                
                return response.entityType;
            }
            
            return null;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante l\'aggiornamento del tipo di entità',
                ErrorTypes.NETWORK,
                { entityId, entityData, error }
            );
            return null;
        } finally {
            store.commit('SET_LOADING', 'entities.isLoading', false);
        }
    }
    
    /**
     * Elimina un tipo di entità
     * @param {string} entityId - ID del tipo di entità
     * @returns {Promise<boolean>} - Promise che si risolve con lo stato dell'eliminazione
     */
    async deleteEntityType(entityId) {
        try {
            store.commit('SET_LOADING', 'entities.isLoading', true);
            
            // Elimina il tipo di entità dal server
            await apiClient.delete(`/entity-types/${entityId}`);
            
            // Aggiorna la lista dei tipi di entità nello store
            const entityTypes = [...(store.getState('entities.types') || [])];
            const updatedTypes = entityTypes.filter(e => e.id !== entityId);
            store.commit('SET_ENTITY_TYPES', 'entities.types', updatedTypes);
            
            // Aggiorna la cache
            delete this.entityCache.byId[entityId];
            for (const category in this.entityCache.byCategory) {
                this.entityCache.byCategory[category] = this.entityCache.byCategory[category].filter(
                    e => e.id !== entityId
                );
            }
            
            // Emette un evento per il tipo di entità eliminato
            eventBus.emit('entity:deleted', { entityId });
            
            return true;
        } catch (error) {
            errorHandler.handleError(
                'Errore durante l\'eliminazione del tipo di entità',
                ErrorTypes.NETWORK,
                { entityId, error }
            );
            return false;
        } finally {
            store.commit('SET_LOADING', 'entities.isLoading', false);
        }
    }
    
    /**
     * Filtra i tipi di entità in base a una query di ricerca
     * @param {string} query - Query di ricerca
     * @param {string} [category] - Categoria opzionale per filtrare ulteriormente
     * @returns {Array} - Tipi di entità filtrati
     */
    filterEntityTypes(query, category = null) {
        try {
            const entityTypes = store.getState('entities.types') || [];
            
            // Filtra per categoria se specificata
            let filteredTypes = entityTypes;
            if (category) {
                filteredTypes = entityTypes.filter(e => e.category === category);
            }
            
            // Se la query è vuota, restituisci i tipi filtrati per categoria
            if (!query || !query.trim()) {
                return filteredTypes;
            }
            
            const normalizedQuery = query.toLowerCase().trim();
            
            // Filtra i tipi di entità
            return filteredTypes.filter(entity => {
                return (
                    (entity.id && entity.id.toLowerCase().includes(normalizedQuery)) ||
                    (entity.name && entity.name.toLowerCase().includes(normalizedQuery)) ||
                    (entity.description && entity.description.toLowerCase().includes(normalizedQuery))
                );
            });
        } catch (error) {
            errorHandler.handleError(
                'Errore durante il filtraggio dei tipi di entità',
                ErrorTypes.UNKNOWN,
                { query, category, error }
            );
            return [];
        }
    }
    
    /**
     * Verifica se un tipo di entità esiste
     * @param {string} entityId - ID del tipo di entità
     * @returns {boolean} - true se il tipo di entità esiste
     */
    entityTypeExists(entityId) {
        return this.getEntityType(entityId) !== null;
    }
    
    /**
     * Aggiorna la cache delle entità
     * @private
     * @param {Array} entityTypes - Tipi di entità da aggiungere alla cache
     */
    _updateCache(entityTypes) {
        if (!entityTypes || !entityTypes.length) return;
        
        // Aggiorna la cache per ID
        entityTypes.forEach(entity => {
            this.entityCache.byId[entity.id] = entity;
            
            // Aggiorna la cache per categoria
            const category = entity.category || 'uncategorized';
            if (!this.entityCache.byCategory[category]) {
                this.entityCache.byCategory[category] = [];
            }
            
            // Rimuovi eventuali duplicati
            this.entityCache.byCategory[category] = this.entityCache.byCategory[category].filter(
                e => e.id !== entity.id
            );
            
            // Aggiungi l'entità alla categoria
            this.entityCache.byCategory[category].push(entity);
        });
    }
    
    /**
     * Invalida la cache delle entità
     */
    invalidateCache() {
        this.entityCache = {
            byId: {},
            byCategory: {}
        };
    }
}

// Crea un'istanza singleton dell'EntityService
const entityService = new EntityService();

// Esporta l'istanza singleton
export default entityService;
