/**
 * error-handler.js - Sistema centralizzato di gestione degli errori
 * 
 * Fornisce funzionalità per la gestione centralizzata degli errori,
 * il logging e la visualizzazione di messaggi di errore all'utente.
 * 
 * @version 1.0.0
 */

import eventBus from './event-bus.js';
import store from './store.js';
import config from '../config/config.js';

// Definizione dei tipi di errore
export const ErrorTypes = {
    VALIDATION: 'validation',
    NETWORK: 'network',
    SERVER: 'server',
    AUTHORIZATION: 'authorization',
    NOT_FOUND: 'not_found',
    TIMEOUT: 'timeout',
    UNKNOWN: 'unknown'
};

// Definizione dei livelli di gravità
export const ErrorSeverity = {
    INFO: 'info',
    WARNING: 'warning',
    ERROR: 'error',
    CRITICAL: 'critical'
};

class ErrorHandler {
    constructor() {
        // Registro degli errori
        this.errorLog = [];
        
        // Limite del registro errori
        this.logLimit = 100;
        
        // Flag per modalità debug
        this.debugMode = config.app.debugMode;
    }
    
    /**
     * Gestisce un errore
     * @param {Error|string} error - Errore o messaggio di errore
     * @param {string} [type=ErrorTypes.UNKNOWN] - Tipo di errore
     * @param {string} [severity=ErrorSeverity.ERROR] - Livello di gravità
     * @param {Object} [metadata={}] - Metadati aggiuntivi sull'errore
     * @param {boolean} [notify=true] - Se notificare l'utente
     * @returns {string} - ID dell'errore
     */
    handleError(error, type = ErrorTypes.UNKNOWN, severity = ErrorSeverity.ERROR, metadata = {}, notify = true) {
        // Crea un oggetto errore strutturato
        const errorObj = {
            id: this._generateErrorId(),
            message: error instanceof Error ? error.message : error,
            type: type,
            severity: severity,
            timestamp: new Date().toISOString(),
            stack: error instanceof Error ? error.stack : null,
            metadata: metadata
        };
        
        // Aggiunge l'errore al registro
        this._addToLog(errorObj);
        
        // Emette un evento per l'errore
        eventBus.emit('error:occurred', errorObj);
        
        // Aggiorna lo stato dell'applicazione
        store.commit('ERROR_OCCURRED', 'ui.lastError', errorObj);
        
        // Notifica l'utente se richiesto
        if (notify) {
            this._notifyUser(errorObj);
        }
        
        // Log dell'errore nella console in modalità debug
        if (this.debugMode) {
            console.error(`[${errorObj.severity.toUpperCase()}] ${errorObj.type}: ${errorObj.message}`, errorObj);
        }
        
        return errorObj.id;
    }
    
    /**
     * Gestisce un errore di validazione
     * @param {string} message - Messaggio di errore
     * @param {Object} [validationErrors={}] - Dettagli degli errori di validazione
     * @param {boolean} [notify=true] - Se notificare l'utente
     * @returns {string} - ID dell'errore
     */
    handleValidationError(message, validationErrors = {}, notify = true) {
        return this.handleError(
            message,
            ErrorTypes.VALIDATION,
            ErrorSeverity.WARNING,
            { validationErrors },
            notify
        );
    }
    
    /**
     * Gestisce un errore di rete
     * @param {Error|string} error - Errore o messaggio di errore
     * @param {Object} [requestInfo={}] - Informazioni sulla richiesta
     * @param {boolean} [notify=true] - Se notificare l'utente
     * @returns {string} - ID dell'errore
     */
    handleNetworkError(error, requestInfo = {}, notify = true) {
        return this.handleError(
            error,
            ErrorTypes.NETWORK,
            ErrorSeverity.ERROR,
            { request: requestInfo },
            notify
        );
    }
    
    /**
     * Gestisce un errore del server
     * @param {Error|string} error - Errore o messaggio di errore
     * @param {Object} [responseInfo={}] - Informazioni sulla risposta
     * @param {boolean} [notify=true] - Se notificare l'utente
     * @returns {string} - ID dell'errore
     */
    handleServerError(error, responseInfo = {}, notify = true) {
        return this.handleError(
            error,
            ErrorTypes.SERVER,
            ErrorSeverity.ERROR,
            { response: responseInfo },
            notify
        );
    }
    
    /**
     * Ottiene il registro degli errori
     * @param {number} [limit] - Numero massimo di errori da restituire
     * @returns {Array} - Registro degli errori
     */
    getErrorLog(limit = null) {
        if (limit) {
            return [...this.errorLog].slice(-limit);
        }
        return [...this.errorLog];
    }
    
    /**
     * Cancella il registro degli errori
     */
    clearErrorLog() {
        this.errorLog = [];
        eventBus.emit('error:log-cleared');
    }
    
    /**
     * Imposta la modalità debug
     * @param {boolean} enabled - Se abilitare la modalità debug
     */
    setDebugMode(enabled) {
        this.debugMode = enabled;
    }
    
    /**
     * Genera un ID univoco per l'errore
     * @private
     * @returns {string} - ID errore
     */
    _generateErrorId() {
        return 'err_' + Date.now().toString(36) + '_' + Math.random().toString(36).substr(2, 5);
    }
    
    /**
     * Aggiunge un errore al registro
     * @private
     * @param {Object} errorObj - Oggetto errore
     */
    _addToLog(errorObj) {
        this.errorLog.push(errorObj);
        
        // Limita la dimensione del registro
        if (this.errorLog.length > this.logLimit) {
            this.errorLog.shift();
        }
    }
    
    /**
     * Notifica l'utente dell'errore
     * @private
     * @param {Object} errorObj - Oggetto errore
     */
    _notifyUser(errorObj) {
        // Determina il tipo di notifica in base alla gravità
        let notificationType;
        switch (errorObj.severity) {
            case ErrorSeverity.INFO:
                notificationType = 'info';
                break;
            case ErrorSeverity.WARNING:
                notificationType = 'warning';
                break;
            case ErrorSeverity.CRITICAL:
                notificationType = 'danger';
                break;
            case ErrorSeverity.ERROR:
            default:
                notificationType = 'error';
                break;
        }
        
        // Emette un evento per mostrare una notifica
        eventBus.emit('notification:show', {
            type: notificationType,
            message: errorObj.message,
            duration: errorObj.severity === ErrorSeverity.CRITICAL ? 0 : config.ui.toastDuration,
            errorId: errorObj.id
        });
    }
}

// Crea un'istanza singleton dell'ErrorHandler
const errorHandler = new ErrorHandler();

// Esporta l'istanza singleton
export default errorHandler;
