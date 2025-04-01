/**
 * notification.js - Sistema di notifiche minimale
 * 
 * Fornisce un sistema centralizzato per mostrare feedback all'utente
 * con un'interfaccia semplice e coerente
 * 
 * @version 1.0.0
 */

const NotificationSystem = (function() {
    'use strict';
    
    // Configurazione
    const config = {
        defaultDuration: 5000,  // 5 secondi
        maxNotifications: 3,    // Numero massimo di notifiche contemporanee
        position: 'top-right',  // Posizione delle notifiche (top-right, top-left, bottom-right, bottom-left)
        errorDuration: 8000     // Durata maggiore per gli errori
    };
    
    // Stato delle notifiche
    const state = {
        notifications: [],      // Notifiche attive
        container: null,        // Elemento contenitore delle notifiche
        initialized: false      // Flag di inizializzazione
    };
    
    /**
     * Inizializza il sistema di notifiche
     * @param {Object} options - Opzioni di configurazione
     */
    function initialize(options = {}) {
        // Evita reinizializzazioni
        if (state.initialized) {
            return;
        }
        
        // Aggiorna la configurazione
        Object.assign(config, options);
        
        // Crea il contenitore delle notifiche
        createContainer();
        
        // Segna come inizializzato
        state.initialized = true;
        
        console.log(`Sistema di notifiche inizializzato (${config.position})`);
    }
    
    /**
     * Crea il contenitore delle notifiche nel DOM
     */
    function createContainer() {
        // Verifica se esiste già un contenitore
        let container = document.getElementById('notification-container');
        
        if (!container) {
            // Crea un nuovo contenitore
            container = document.createElement('div');
            container.id = 'notification-container';
            container.className = `notification-container ${config.position}`;
            
            // Aggiungi al body
            document.body.appendChild(container);
            
            // Aggiungi gli stili
            addStyles();
        }
        
        // Salva il riferimento
        state.container = container;
    }
    
    /**
     * Aggiunge gli stili CSS per le notifiche
     */
    function addStyles() {
        // Crea l'elemento style
        const style = document.createElement('style');
        style.id = 'notification-styles';
        
        // Definisci gli stili
        style.textContent = `
            .notification-container {
                position: fixed;
                z-index: 9999;
                max-width: 320px;
                box-sizing: border-box;
                display: flex;
                flex-direction: column;
                gap: 8px;
                pointer-events: none;
            }
            
            .notification-container.top-right {
                top: 16px;
                right: 16px;
            }
            
            .notification-container.top-left {
                top: 16px;
                left: 16px;
            }
            
            .notification-container.bottom-right {
                bottom: 16px;
                right: 16px;
            }
            
            .notification-container.bottom-left {
                bottom: 16px;
                left: 16px;
            }
            
            .notification {
                background-color: white;
                border-radius: 4px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
                padding: 12px 16px;
                margin: 0;
                opacity: 0;
                transform: translateY(-20px);
                transition: all 0.3s ease;
                pointer-events: auto;
                position: relative;
                overflow: hidden;
                max-width: 100%;
                display: flex;
                align-items: flex-start;
            }
            
            .notification.show {
                opacity: 1;
                transform: translateY(0);
            }
            
            .notification-progress {
                position: absolute;
                bottom: 0;
                left: 0;
                height: 3px;
                background-color: rgba(0, 0, 0, 0.1);
                width: 100%;
            }
            
            .notification-icon {
                margin-right: 12px;
                font-size: 16px;
                flex-shrink: 0;
            }
            
            .notification-content {
                flex: 1;
                min-width: 0;
            }
            
            .notification-title {
                font-weight: 500;
                margin-bottom: 4px;
                font-size: 14px;
                display: -webkit-box;
                -webkit-line-clamp: 1;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }
            
            .notification-message {
                font-size: 13px;
                margin: 0;
                color: rgba(0, 0, 0, 0.7);
                display: -webkit-box;
                -webkit-line-clamp: 3;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }
            
            .notification-close {
                position: absolute;
                top: 8px;
                right: 8px;
                cursor: pointer;
                font-size: 14px;
                color: rgba(0, 0, 0, 0.5);
                border: none;
                background: none;
                padding: 0;
                width: 16px;
                height: 16px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .notification-success {
                border-left: 4px solid #10b981;
            }
            
            .notification-success .notification-progress {
                background-color: #10b981;
            }
            
            .notification-info {
                border-left: 4px solid #3b82f6;
            }
            
            .notification-info .notification-progress {
                background-color: #3b82f6;
            }
            
            .notification-warning {
                border-left: 4px solid #f59e0b;
            }
            
            .notification-warning .notification-progress {
                background-color: #f59e0b;
            }
            
            .notification-error {
                border-left: 4px solid #ef4444;
            }
            
            .notification-error .notification-progress {
                background-color: #ef4444;
            }
        `;
        
        // Aggiungi al document
        document.head.appendChild(style);
    }
    
    /**
     * Mostra una notifica
     * @param {string} message - Testo della notifica
     * @param {string} type - Tipo di notifica (success, info, warning, error)
     * @param {Object} options - Opzioni aggiuntive
     * @returns {string} ID della notifica
     */
    function show(message, type = 'info', options = {}) {
        // Assicura che il sistema sia inizializzato
        if (!state.initialized) {
            initialize();
        }
        
        // Limita il numero di notifiche attive
        if (state.notifications.length >= config.maxNotifications) {
            // Rimuovi la notifica più vecchia
            if (state.notifications.length > 0) {
                remove(state.notifications[0].id);
            }
        }
        
        // Genera un ID univoco
        const id = 'notification-' + Date.now() + '-' + Math.floor(Math.random() * 1000);
        
        // Determina la durata
        let duration = options.duration || config.defaultDuration;
        if (type === 'error') {
            duration = options.duration || config.errorDuration;
        }
        
        // Crea l'elemento della notifica
        const notificationElement = createNotificationElement(id, message, type, options.title);
        
        // Aggiungi al contenitore
        state.container.appendChild(notificationElement);
        
        // Mostra la notifica con una transizione
        setTimeout(() => {
            notificationElement.classList.add('show');
        }, 10);
        
        // Crea la barra di progresso
        const progressElement = notificationElement.querySelector('.notification-progress');
        startProgressBar(progressElement, duration);
        
        // Aggiungi la notifica allo stato
        state.notifications.push({
            id,
            element: notificationElement,
            timer: setTimeout(() => {
                remove(id);
            }, duration)
        });
        
        return id;
    }
    
    /**
     * Crea l'elemento HTML della notifica
     * @param {string} id - ID della notifica
     * @param {string} message - Testo della notifica
     * @param {string} type - Tipo di notifica
     * @param {string} title - Titolo opzionale della notifica
     * @returns {HTMLElement} Elemento della notifica
     */
    function createNotificationElement(id, message, type, title) {
        const element = document.createElement('div');
        element.className = `notification notification-${type}`;
        element.id = id;
        
        // Scegli l'icona in base al tipo
        let icon = '';
        switch (type) {
            case 'success':
                icon = '✓';
                break;
            case 'error':
                icon = '✗';
                break;
            case 'warning':
                icon = '⚠';
                break;
            case 'info':
            default:
                icon = 'ℹ';
                break;
        }
        
        // Crea il contenuto HTML
        element.innerHTML = `
            <div class="notification-icon">${icon}</div>
            <div class="notification-content">
                ${title ? `<div class="notification-title">${title}</div>` : ''}
                <p class="notification-message">${message}</p>
            </div>
            <button class="notification-close" aria-label="Chiudi">&times;</button>
            <div class="notification-progress"></div>
        `;
        
        // Aggiungi l'evento di chiusura
        element.querySelector('.notification-close').addEventListener('click', () => {
            remove(id);
        });
        
        return element;
    }
    
    /**
     * Avvia l'animazione della barra di progresso
     * @param {HTMLElement} progressElement - Elemento della barra di progresso
     * @param {number} duration - Durata in millisecondi
     */
    function startProgressBar(progressElement, duration) {
        // Imposta larghezza iniziale
        progressElement.style.width = '100%';
        
        // Applica la transizione
        progressElement.style.transition = `width ${duration}ms linear`;
        
        // Avvia l'animazione
        setTimeout(() => {
            progressElement.style.width = '0%';
        }, 50);
    }
    
    /**
     * Rimuove una notifica
     * @param {string} id - ID della notifica da rimuovere
     */
    function remove(id) {
        // Trova la notifica
        const index = state.notifications.findIndex(n => n.id === id);
        
        if (index !== -1) {
            const notification = state.notifications[index];
            
            // Rimuovi il timer
            clearTimeout(notification.timer);
            
            // Nascondi con animazione
            notification.element.classList.remove('show');
            
            // Rimuovi dal DOM dopo l'animazione
            setTimeout(() => {
                if (notification.element.parentNode) {
                    notification.element.parentNode.removeChild(notification.element);
                }
            }, 300);
            
            // Rimuovi dallo stato
            state.notifications.splice(index, 1);
        }
    }
    
    /**
     * Rimuove tutte le notifiche
     */
    function clear() {
        // Copia l'array per evitare problemi durante la rimozione
        const notifications = [...state.notifications];
        
        // Rimuovi ogni notifica
        notifications.forEach(notification => {
            remove(notification.id);
        });
    }
    
    /**
     * Helper per mostrare notifiche di successo
     * @param {string} message - Messaggio da mostrare
     * @param {Object} options - Opzioni aggiuntive
     * @returns {string} ID della notifica
     */
    function success(message, options = {}) {
        return show(message, 'success', options);
    }
    
    /**
     * Helper per mostrare notifiche informative
     * @param {string} message - Messaggio da mostrare
     * @param {Object} options - Opzioni aggiuntive
     * @returns {string} ID della notifica
     */
    function info(message, options = {}) {
        return show(message, 'info', options);
    }
    
    /**
     * Helper per mostrare notifiche di avviso
     * @param {string} message - Messaggio da mostrare
     * @param {Object} options - Opzioni aggiuntive
     * @returns {string} ID della notifica
     */
    function warning(message, options = {}) {
        return show(message, 'warning', options);
    }
    
    /**
     * Helper per mostrare notifiche di errore
     * @param {string} message - Messaggio da mostrare
     * @param {Object} options - Opzioni aggiuntive
     * @returns {string} ID della notifica
     */
    function error(message, options = {}) {
        return show(message, 'error', options);
    }
    
    // API pubblica
    return {
        initialize,
        show,
        remove,
        clear,
        success,
        info,
        warning,
        error
    };
})();

// Inizializzazione automatica
document.addEventListener('DOMContentLoaded', function() {
    NotificationSystem.initialize();
    
    // Esponi globalmente per compatibilità
    window.showNotification = function(message, type = 'info') {
        // Mappa i tipi di Bootstrap a quelli del sistema di notifiche
        const typeMap = {
            'primary': 'info',
            'secondary': 'info',
            'success': 'success',
            'danger': 'error',
            'warning': 'warning',
            'info': 'info'
        };
        
        return NotificationSystem.show(message, typeMap[type] || 'info');
    };
    
    // Esponi il sistema completo
    window.NotificationSystem = NotificationSystem;
});