/**
 * store.js - Store centralizzato per la gestione dello stato dell'applicazione
 * 
 * Implementa un pattern di gestione dello stato centralizzato per mantenere
 * i dati condivisi tra i vari moduli dell'applicazione.
 * 
 * @version 1.0.0
 */

import eventBus from './event-bus.js';

class Store {
    constructor() {
        // Stato iniziale dell'applicazione
        this._state = {
            // Stato dell'annotatore
            annotator: {
                initialized: false,
                selectedEntityType: null,
                annotations: [],
                isProcessing: false,
                docId: null,
                errorCount: 0
            },
            
            // Stato dei documenti
            documents: {
                list: [],
                current: null,
                filterText: '',
                filterCategory: '',
                isProcessing: false
            },
            
            // Stato delle entità
            entities: {
                types: [],
                selectedEntity: null,
                isLoading: false,
                filterText: '',
                filterCategory: ''
            },
            
            // Stato dell'interfaccia utente
            ui: {
                isFullscreen: false,
                zoomLevel: 1,
                darkMode: false,
                sidebarCollapsed: false,
                notifications: []
            }
        };
        
        // Registro delle mutazioni (per debugging)
        this._mutations = [];
    }
    
    /**
     * Ottiene una copia dello stato corrente o di una sua parte
     * @param {string} [path] - Percorso opzionale per ottenere solo una parte dello stato
     * @returns {Object} - Copia dello stato o della parte richiesta
     */
    getState(path = null) {
        if (!path) {
            // Restituisce una copia profonda dell'intero stato
            return JSON.parse(JSON.stringify(this._state));
        }
        
        // Naviga il percorso per ottenere la parte richiesta
        const parts = path.split('.');
        let current = this._state;
        
        for (const part of parts) {
            if (current[part] === undefined) {
                console.warn(`Percorso "${path}" non trovato nello store`);
                return null;
            }
            current = current[part];
        }
        
        // Restituisce una copia profonda della parte richiesta
        return JSON.parse(JSON.stringify(current));
    }
    
    /**
     * Aggiorna lo stato con una mutazione
     * @param {string} type - Tipo di mutazione (per logging)
     * @param {string} path - Percorso della parte di stato da aggiornare
     * @param {any} value - Nuovo valore
     * @param {boolean} [merge=false] - Se true, unisce il valore con quello esistente invece di sostituirlo
     */
    commit(type, path, value, merge = false) {
        // Registra la mutazione per debugging
        this._mutations.push({
            type,
            path,
            value: JSON.parse(JSON.stringify(value)),
            timestamp: new Date().toISOString()
        });
        
        // Naviga il percorso per trovare la parte di stato da aggiornare
        const parts = path.split('.');
        let current = this._state;
        
        // Naviga fino al penultimo livello
        for (let i = 0; i < parts.length - 1; i++) {
            const part = parts[i];
            if (current[part] === undefined) {
                current[part] = {};
            }
            current = current[part];
        }
        
        // Aggiorna l'ultimo livello
        const lastPart = parts[parts.length - 1];
        
        if (merge && typeof current[lastPart] === 'object' && !Array.isArray(current[lastPart]) && 
            typeof value === 'object' && !Array.isArray(value)) {
            // Unisce gli oggetti se merge è true
            current[lastPart] = { ...current[lastPart], ...value };
        } else {
            // Altrimenti sostituisce il valore
            current[lastPart] = value;
        }
        
        // Emette un evento per notificare i cambiamenti
        eventBus.emit('store:changed', path, value);
        eventBus.emit(`store:changed:${path}`, value);
    }
    
    /**
     * Registra un listener per i cambiamenti dello stato
     * @param {string} path - Percorso della parte di stato da monitorare
     * @param {Function} callback - Funzione da chiamare quando lo stato cambia
     * @returns {Object} - Oggetto con metodo unsubscribe
     */
    watch(path, callback) {
        return eventBus.on(`store:changed:${path}`, callback);
    }
    
    /**
     * Registra un listener per tutti i cambiamenti dello stato
     * @param {Function} callback - Funzione da chiamare quando lo stato cambia
     * @returns {Object} - Oggetto con metodo unsubscribe
     */
    watchAll(callback) {
        return eventBus.on('store:changed', callback);
    }
    
    /**
     * Ottiene lo storico delle mutazioni (per debugging)
     * @param {number} [limit] - Numero massimo di mutazioni da restituire
     * @returns {Array} - Array di mutazioni
     */
    getMutations(limit = null) {
        const mutations = [...this._mutations];
        if (limit) {
            return mutations.slice(-limit);
        }
        return mutations;
    }
    
    /**
     * Resetta lo stato a un valore iniziale
     * @param {Object} [initialState] - Stato iniziale (se omesso, usa uno stato vuoto)
     */
    resetState(initialState = null) {
        this._state = initialState || {
            annotator: { initialized: false, annotations: [] },
            documents: { list: [] },
            entities: { types: [] },
            ui: { notifications: [] }
        };
        
        this._mutations = [];
        eventBus.emit('store:reset');
    }
}

// Crea un'istanza singleton dello Store
const store = new Store();

// Esporta l'istanza singleton
export default store;
