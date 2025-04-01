/**
 * utils.js - Utilities condivise per l'applicazione NER-Giuridico
 * 
 * Questo file contiene funzioni utility utilizzate in tutto il frontend dell'applicazione.
 * Centralizzando queste funzioni, evitiamo ridondanze e manteniamo una implementazione coerente.
 */

/** 
 * Namespace globale per l'applicazione NER-Giuridico 
 * Racchiude tutte le funzioni e utilità condivise per evitare inquinamento globale
 */
const NERGiuridico = {
    /**
     * Mostra una notifica toast all'utente
     * @param {string} message - Il messaggio da visualizzare
     * @param {string} type - Il tipo di notifica (primary, success, danger, warning, info)
     */
    showNotification: function(message, type = 'primary') {
        // Verifica che l'elemento toast esista
        const toastEl = document.getElementById('notification-toast');
        if (!toastEl) {
            console.warn('Elemento toast non trovato, impossibile mostrare la notifica');
            return;
        }
        
        // Imposta il messaggio
        const toastBody = document.getElementById('notification-message');
        if (toastBody) toastBody.textContent = message;
        
        // Imposta il tipo/colore
        toastEl.className = toastEl.className.replace(/bg-\w+/, '');
        toastEl.classList.add(`bg-${type}`);
        
        // Mostra il toast
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
        
        // Per debugging - log alla console
        if (NERGiuridico.debugMode) {
            console.info(`Notifica (${type}): ${message}`);
        }
    },
    
    /**
     * Mostra una finestra di conferma modale
     * @param {string} title - Il titolo della finestra di conferma
     * @param {string} message - Il messaggio da visualizzare
     * @param {Function} onConfirm - Funzione da eseguire alla conferma
     * @param {string} confirmText - Testo del pulsante di conferma
     * @param {string} confirmClass - Classe del pulsante di conferma
     * @returns {bootstrap.Modal} L'istanza della finestra modale
     */
    showConfirmation: function(title, message, onConfirm, confirmText = 'Conferma', confirmClass = 'btn-primary') {
        const confirmModal = document.getElementById('confirm-modal');
        if (!confirmModal) {
            console.warn('Elemento modale non trovato, impossibile mostrare la conferma');
            return null;
        }
        
        // Imposta il titolo e il messaggio
        document.getElementById('confirm-title').textContent = title;
        document.getElementById('confirm-message').textContent = message;
        
        // Configura il pulsante di conferma
        const confirmBtn = document.getElementById('confirm-action-btn');
        confirmBtn.textContent = confirmText;
        confirmBtn.className = `btn ${confirmClass}`;
        
        // Imposta la funzione di callback
        const originalOnClick = confirmBtn.onclick;
        confirmBtn.onclick = function() {
            if (typeof onConfirm === 'function') {
                onConfirm();
            }
            // Ripristina l'onclick originale
            confirmBtn.onclick = originalOnClick;
        };
        
        // Mostra la finestra modale
        const modal = new bootstrap.Modal(confirmModal);
        modal.show();
        
        return modal;
    },
    
    /**
     * Mostra un indicatore di caricamento su un elemento
     * @param {HTMLElement} element - L'elemento su cui mostrare il caricamento
     * @param {string} originalText - Il testo originale dell'elemento
     */
    showLoading: function(element, originalText) {
        if (!element) return;
        
        element.disabled = true;
        element._originalText = element.innerHTML;
        element.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span>${originalText || 'Caricamento...'}`;
    },
    
    /**
     * Rimuove l'indicatore di caricamento da un elemento
     * @param {HTMLElement} element - L'elemento da cui rimuovere il caricamento
     */
    hideLoading: function(element) {
        if (!element) return;
        
        element.disabled = false;
        if (element._originalText) {
            element.innerHTML = element._originalText;
            delete element._originalText;
        }
    },
    
    /**
     * Esegue una richiesta fetch con gestione standardizzata degli errori
     * @param {string} url - L'URL da richiedere
     * @param {Object} options - Opzioni per la richiesta fetch
     * @param {Function} successCallback - Funzione da chiamare in caso di successo
     * @param {Function} errorCallback - Funzione da chiamare in caso di errore
     */
    fetchWithErrorHandling: function(url, options, successCallback, errorCallback) {
        fetch(url, options)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw new Error(err.message || `Errore HTTP: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    if (typeof successCallback === 'function') {
                        successCallback(data);
                    }
                } else {
                    throw new Error(data.message || 'Si è verificato un errore non specificato');
                }
            })
            .catch(error => {
                console.error('Errore nella richiesta:', error);
                NERGiuridico.showNotification(`Errore: ${error.message}`, 'danger');
                if (typeof errorCallback === 'function') {
                    errorCallback(error);
                }
            });
    },
    
    /**
     * Applica una funzione di debounce
     * @param {Function} func - La funzione da eseguire
     * @param {number} wait - Il tempo di attesa in millisecondi
     * @returns {Function} La funzione con debounce
     */
    debounce: function(func, wait) {
        let timeout;
        return function() {
            const context = this;
            const args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                func.apply(context, args);
            }, wait);
        };
    },
    
    /**
     * Controlla se due intervalli si sovrappongono
     * @param {number} start1 - Inizio del primo intervallo
     * @param {number} end1 - Fine del primo intervallo
     * @param {number} start2 - Inizio del secondo intervallo
     * @param {number} end2 - Fine del secondo intervallo
     * @returns {boolean} True se gli intervalli si sovrappongono
     */
    isOverlapping: function(start1, end1, start2, end2) {
        return start1 <= end2 && end1 >= start2;
    },
    
    /**
     * Calcola la luminosità di un colore
     * @param {string} hexColor - Colore in formato esadecimale (#RRGGBB)
     * @returns {number} Valore di luminosità (0-1)
     */
    calculateLuminance: function(hexColor) {
        // Rimuovi il # se presente
        hexColor = hexColor.replace(/^#/, '');
        
        // Converti il colore HEX in RGB
        const r = parseInt(hexColor.substr(0, 2), 16) / 255;
        const g = parseInt(hexColor.substr(2, 2), 16) / 255;
        const b = parseInt(hexColor.substr(4, 2), 16) / 255;
        
        // Calcola la luminanza
        const a = [r, g, b].map(function(v) {
            return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
        });
        return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
    },
    
    /**
     * Determina se un testo su uno sfondo colorato dovrebbe essere chiaro o scuro
     * @param {string} backgroundColor - Colore di sfondo in formato esadecimale (#RRGGBB)
     * @returns {string} Colore del testo ('white' o 'black')
     */
    getTextColorForBackground: function(backgroundColor) {
        const luminance = this.calculateLuminance(backgroundColor);
        return luminance > 0.5 ? 'black' : 'white';
    },
    
    /**
     * Formatta una data in formato standard italiano
     * @param {string} isoDate - Data in formato ISO (es. '2023-10-15T14:30:00')
     * @returns {string} Data formattata (es. '15/10/2023')
     */
    formatDate: function(isoDate) {
        if (!isoDate) return 'N/A';
        
        try {
            const date = new Date(isoDate);
            return date.toLocaleDateString('it-IT');
        } catch (e) {
            console.warn('Errore nella formattazione della data:', e);
            return isoDate.split('T')[0] || 'N/A';
        }
    },
    
    /**
     * Inserisce caratteri di escape in una stringa per uso in regex
     * @param {string} string - La stringa da formattare
     * @returns {string} La stringa con caratteri di escape
     */
    escapeRegExp: function(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    },
    
    /**
     * Determina se l'app sta eseguendo su un dispositivo mobile
     * @returns {boolean} True se è un dispositivo mobile
     */
    isMobileDevice: function() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth < 768;
    },
    
    /**
     * Determina se l'app sta eseguendo su un dispositivo Mac
     * @returns {boolean} True se è un dispositivo Mac
     */
    isMacOS: function() {
        return navigator.platform.toUpperCase().indexOf('MAC') >= 0;
    },
    
    /**
     * Imposta lo stato di debug dell'applicazione
     */
    debugMode: window.location.search.includes('debug=true'),
    
    /**
     * Versione dell'applicazione
     */
    version: '2.1.0'
};

// Esponi le funzioni globalmente per retrocompatibilità
// Questo permette alle implementazioni esistenti di continuare a funzionare
window.showNotification = function(message, type) {
    return NERGiuridico.showNotification(message, type);
};

// Inizializzazione all'avvio
document.addEventListener('DOMContentLoaded', function() {
    console.info(`NER-Giuridico Utils v${NERGiuridico.version} inizializzato`);
    
    // Adatta le scorciatoie da tastiera in base al sistema operativo
    if (!NERGiuridico.isMacOS()) {
        document.querySelectorAll('.shortcut-badge').forEach(badge => {
            if (badge.textContent.includes('⌘')) {
                badge.textContent = badge.textContent.replace('⌘', 'Ctrl+');
            }
        });
        
        document.querySelectorAll('.keyboard-shortcuts').forEach(shortcuts => {
            shortcuts.innerHTML = shortcuts.innerHTML.replace(/⌘/g, 'Ctrl');
        });
    }
});