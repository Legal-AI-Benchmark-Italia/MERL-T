/**
 * notification-service.js - Servizio per la gestione delle notifiche
 * 
 * Gestisce la visualizzazione di notifiche e toast all'utente
 * in modo centralizzato e consistente.
 * 
 * @version 1.0.0
 */

import eventBus from '../core/event-bus.js';
import config from '../config/config.js';

class NotificationService {
    constructor() {
        this.toastElement = null;
        this.toastMessageElement = null;
        this.activeToasts = [];
        this.toastQueue = [];
        this.isProcessingQueue = false;
        
        // Inizializza il servizio
        this.initialize();
    }
    
    /**
     * Inizializza il servizio di notifica
     */
    initialize() {
        // Registra i listener per gli eventi
        eventBus.on('notification:show', this.showNotification.bind(this));
        
        // Trova gli elementi toast esistenti o creali se non esistono
        this._setupToastElements();
        
        console.info('Servizio di notifica inizializzato');
    }
    
    /**
     * Mostra una notifica all'utente
     * @param {Object} options - Opzioni della notifica
     * @param {string} options.message - Messaggio da mostrare
     * @param {string} [options.type='info'] - Tipo di notifica (info, success, warning, error, danger)
     * @param {number} [options.duration] - Durata in ms (0 per persistente)
     * @param {boolean} [options.dismissible=true] - Se la notifica può essere chiusa
     * @param {string} [options.position='bottom-right'] - Posizione della notifica
     * @param {Function} [options.onClose] - Callback alla chiusura
     */
    showNotification(options) {
        const defaults = {
            message: '',
            type: 'info',
            duration: config.ui.toastDuration,
            dismissible: true,
            position: 'bottom-right',
            onClose: null
        };
        
        const settings = { ...defaults, ...options };
        
        // Aggiungi alla coda
        this.toastQueue.push(settings);
        
        // Processa la coda se non è già in corso
        if (!this.isProcessingQueue) {
            this._processToastQueue();
        }
    }
    
    /**
     * Mostra una notifica di successo
     * @param {string} message - Messaggio da mostrare
     * @param {Object} [options] - Opzioni aggiuntive
     */
    success(message, options = {}) {
        this.showNotification({
            message,
            type: 'success',
            ...options
        });
    }
    
    /**
     * Mostra una notifica di errore
     * @param {string} message - Messaggio da mostrare
     * @param {Object} [options] - Opzioni aggiuntive
     */
    error(message, options = {}) {
        this.showNotification({
            message,
            type: 'error',
            duration: options.duration || 0, // Gli errori sono persistenti di default
            ...options
        });
    }
    
    /**
     * Mostra una notifica di avviso
     * @param {string} message - Messaggio da mostrare
     * @param {Object} [options] - Opzioni aggiuntive
     */
    warning(message, options = {}) {
        this.showNotification({
            message,
            type: 'warning',
            ...options
        });
    }
    
    /**
     * Mostra una notifica informativa
     * @param {string} message - Messaggio da mostrare
     * @param {Object} [options] - Opzioni aggiuntive
     */
    info(message, options = {}) {
        this.showNotification({
            message,
            type: 'info',
            ...options
        });
    }
    
    /**
     * Chiude tutte le notifiche attive
     */
    closeAll() {
        this.activeToasts.forEach(toast => {
            if (toast.element && typeof toast.close === 'function') {
                toast.close();
            }
        });
        
        this.activeToasts = [];
        this.toastQueue = [];
        this.isProcessingQueue = false;
    }
    
    /**
     * Configura gli elementi toast
     * @private
     */
    _setupToastElements() {
        // Cerca il container dei toast
        let toastContainer = document.querySelector('.toast-container');
        
        // Se non esiste, crealo
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            toastContainer.style.zIndex = '1080';
            document.body.appendChild(toastContainer);
        }
        
        // Cerca il toast template
        this.toastElement = document.getElementById('notification-toast');
        
        // Se non esiste, crealo
        if (!this.toastElement) {
            this.toastElement = document.createElement('div');
            this.toastElement.id = 'notification-toast-template';
            this.toastElement.className = 'toast align-items-center text-white bg-primary border-0';
            this.toastElement.setAttribute('role', 'alert');
            this.toastElement.setAttribute('aria-live', 'assertive');
            this.toastElement.setAttribute('aria-atomic', 'true');
            this.toastElement.style.display = 'none';
            
            this.toastElement.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body" id="notification-message">
                        Notifica
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            `;
            
            toastContainer.appendChild(this.toastElement);
        }
        
        // Trova l'elemento del messaggio
        this.toastMessageElement = document.getElementById('notification-message');
        if (!this.toastMessageElement) {
            this.toastMessageElement = this.toastElement.querySelector('.toast-body');
        }
    }
    
    /**
     * Processa la coda dei toast
     * @private
     */
    _processToastQueue() {
        if (this.toastQueue.length === 0) {
            this.isProcessingQueue = false;
            return;
        }
        
        this.isProcessingQueue = true;
        const settings = this.toastQueue.shift();
        
        // Crea un nuovo elemento toast
        const toastElement = this._createToastElement(settings);
        
        // Aggiungi alla lista dei toast attivi
        const toastId = `toast_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
        const toastInstance = {
            id: toastId,
            element: toastElement,
            settings: settings,
            close: () => this._closeToast(toastId)
        };
        
        this.activeToasts.push(toastInstance);
        
        // Mostra il toast
        const toastContainer = document.querySelector('.toast-container');
        toastContainer.appendChild(toastElement);
        
        // Inizializza il toast di Bootstrap
        const bsToast = new bootstrap.Toast(toastElement, {
            autohide: settings.duration > 0,
            delay: settings.duration
        });
        
        // Gestisci l'evento di chiusura
        toastElement.addEventListener('hidden.bs.toast', () => {
            this._onToastHidden(toastId);
            
            // Processa il prossimo toast nella coda
            setTimeout(() => this._processToastQueue(), 100);
        });
        
        // Mostra il toast
        bsToast.show();
    }
    
    /**
     * Crea un elemento toast
     * @private
     * @param {Object} settings - Impostazioni del toast
     * @returns {HTMLElement} - Elemento toast
     */
    _createToastElement(settings) {
        const toastElement = this.toastElement.cloneNode(true);
        toastElement.id = `toast_${Date.now()}`;
        toastElement.style.display = '';
        
        // Imposta il messaggio
        const messageElement = toastElement.querySelector('.toast-body');
        messageElement.innerHTML = settings.message;
        
        // Imposta il tipo/colore
        toastElement.className = toastElement.className.replace(/bg-\w+/, '');
        let bgClass = 'bg-primary';
        
        switch (settings.type) {
            case 'success':
                bgClass = 'bg-success';
                break;
            case 'warning':
                bgClass = 'bg-warning text-dark';
                break;
            case 'error':
            case 'danger':
                bgClass = 'bg-danger';
                break;
            case 'info':
            default:
                bgClass = 'bg-primary';
        }
        
        toastElement.classList.add(bgClass);
        
        // Gestisci dismissible
        if (!settings.dismissible) {
            const closeButton = toastElement.querySelector('.btn-close');
            if (closeButton) {
                closeButton.style.display = 'none';
            }
        }
        
        return toastElement;
    }
    
    /**
     * Gestisce la chiusura di un toast
     * @private
     * @param {string} toastId - ID del toast
     */
    _closeToast(toastId) {
        const index = this.activeToasts.findIndex(t => t.id === toastId);
        if (index !== -1) {
            const toast = this.activeToasts[index];
            
            // Rimuovi dalla lista dei toast attivi
            this.activeToasts.splice(index, 1);
            
            // Chiama il callback onClose se presente
            if (toast.settings.onClose && typeof toast.settings.onClose === 'function') {
                toast.settings.onClose();
            }
            
            // Rimuovi l'elemento dal DOM
            if (toast.element && toast.element.parentNode) {
                toast.element.parentNode.removeChild(toast.element);
            }
        }
    }
    
    /**
     * Gestisce l'evento di chiusura di un toast
     * @private
     * @param {string} toastId - ID del toast
     */
    _onToastHidden(toastId) {
        this._closeToast(toastId);
    }
}

// Crea un'istanza singleton del NotificationService
const notificationService = new NotificationService();

// Esporta l'istanza singleton
export default notificationService;
