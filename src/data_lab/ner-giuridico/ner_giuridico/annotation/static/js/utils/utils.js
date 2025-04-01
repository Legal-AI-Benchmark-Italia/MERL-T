/**
 * utils.js - Funzioni di utilità condivise
 * 
 * Raccolta di funzioni di utilità riutilizzabili in tutta l'applicazione
 * per ridurre la duplicazione del codice e standardizzare operazioni comuni.
 * 
 * @version 1.0.0
 */

/**
 * Ritarda l'esecuzione di una funzione
 * @param {Function} func - Funzione da eseguire
 * @param {number} wait - Tempo di attesa in ms
 * @returns {Function} - Funzione con debounce
 */
export function debounce(func, wait) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

/**
 * Limita la frequenza di esecuzione di una funzione
 * @param {Function} func - Funzione da eseguire
 * @param {number} limit - Limite di tempo in ms
 * @returns {Function} - Funzione con throttle
 */
export function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Genera un ID univoco
 * @param {string} [prefix='id'] - Prefisso per l'ID
 * @returns {string} - ID univoco
 */
export function generateId(prefix = 'id') {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Formatta una data in formato leggibile
 * @param {string|Date} date - Data da formattare
 * @param {Object} [options] - Opzioni di formattazione
 * @returns {string} - Data formattata
 */
export function formatDate(date, options = {}) {
    const dateObj = date instanceof Date ? date : new Date(date);
    
    if (isNaN(dateObj.getTime())) {
        return 'Data non valida';
    }
    
    const defaultOptions = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    };
    
    const mergedOptions = { ...defaultOptions, ...options };
    
    try {
        return new Intl.DateTimeFormat('it-IT', mergedOptions).format(dateObj);
    } catch (error) {
        console.error('Errore nella formattazione della data:', error);
        return dateObj.toLocaleString('it-IT');
    }
}

/**
 * Tronca un testo alla lunghezza specificata
 * @param {string} text - Testo da troncare
 * @param {number} length - Lunghezza massima
 * @param {string} [suffix='...'] - Suffisso da aggiungere
 * @returns {string} - Testo troncato
 */
export function truncateText(text, length, suffix = '...') {
    if (!text) return '';
    if (text.length <= length) return text;
    return text.substring(0, length).trim() + suffix;
}

/**
 * Sanitizza un testo per l'HTML
 * @param {string} text - Testo da sanitizzare
 * @returns {string} - Testo sanitizzato
 */
export function sanitizeHtml(text) {
    if (!text) return '';
    const element = document.createElement('div');
    element.textContent = text;
    return element.innerHTML;
}

/**
 * Converte un oggetto in parametri query string
 * @param {Object} params - Parametri
 * @returns {string} - Query string
 */
export function objectToQueryString(params) {
    return Object.entries(params)
        .filter(([_, value]) => value !== undefined && value !== null)
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
        .join('&');
}

/**
 * Converte una query string in un oggetto
 * @param {string} queryString - Query string
 * @returns {Object} - Oggetto con i parametri
 */
export function queryStringToObject(queryString) {
    if (!queryString) return {};
    
    const params = {};
    const query = queryString.startsWith('?') 
        ? queryString.substring(1) 
        : queryString;
    
    query.split('&').forEach(param => {
        if (!param) return;
        const [key, value] = param.split('=');
        params[decodeURIComponent(key)] = decodeURIComponent(value || '');
    });
    
    return params;
}

/**
 * Filtra un array di oggetti in base a una query di ricerca
 * @param {Array} items - Array di oggetti
 * @param {string} query - Query di ricerca
 * @param {Array|string} fields - Campi su cui cercare
 * @returns {Array} - Array filtrato
 */
export function filterItems(items, query, fields) {
    if (!query || !query.trim()) return items;
    
    const searchFields = Array.isArray(fields) ? fields : [fields];
    const normalizedQuery = query.toLowerCase().trim();
    
    return items.filter(item => {
        return searchFields.some(field => {
            const value = item[field];
            if (value === undefined || value === null) return false;
            return String(value).toLowerCase().includes(normalizedQuery);
        });
    });
}

/**
 * Ordina un array di oggetti
 * @param {Array} items - Array di oggetti
 * @param {string} field - Campo su cui ordinare
 * @param {string} [direction='asc'] - Direzione (asc/desc)
 * @returns {Array} - Array ordinato
 */
export function sortItems(items, field, direction = 'asc') {
    const sortedItems = [...items];
    
    sortedItems.sort((a, b) => {
        let valueA = a[field];
        let valueB = b[field];
        
        // Gestione valori null/undefined
        if (valueA === undefined || valueA === null) valueA = '';
        if (valueB === undefined || valueB === null) valueB = '';
        
        // Confronto numerico se entrambi i valori sono numeri
        if (typeof valueA === 'number' && typeof valueB === 'number') {
            return direction === 'asc' ? valueA - valueB : valueB - valueA;
        }
        
        // Confronto date se entrambi i valori sono date
        if (valueA instanceof Date && valueB instanceof Date) {
            return direction === 'asc' 
                ? valueA.getTime() - valueB.getTime() 
                : valueB.getTime() - valueA.getTime();
        }
        
        // Confronto stringhe negli altri casi
        const strA = String(valueA).toLowerCase();
        const strB = String(valueB).toLowerCase();
        
        return direction === 'asc' 
            ? strA.localeCompare(strB) 
            : strB.localeCompare(strA);
    });
    
    return sortedItems;
}

/**
 * Raggruppa un array di oggetti per un campo
 * @param {Array} items - Array di oggetti
 * @param {string} field - Campo su cui raggruppare
 * @returns {Object} - Oggetto con i gruppi
 */
export function groupBy(items, field) {
    return items.reduce((groups, item) => {
        const key = item[field] || 'undefined';
        if (!groups[key]) {
            groups[key] = [];
        }
        groups[key].push(item);
        return groups;
    }, {});
}

/**
 * Calcola la differenza tra due array
 * @param {Array} arr1 - Primo array
 * @param {Array} arr2 - Secondo array
 * @returns {Array} - Elementi presenti in arr1 ma non in arr2
 */
export function arrayDifference(arr1, arr2) {
    return arr1.filter(item => !arr2.includes(item));
}

/**
 * Verifica se due oggetti sono uguali
 * @param {Object} obj1 - Primo oggetto
 * @param {Object} obj2 - Secondo oggetto
 * @returns {boolean} - true se gli oggetti sono uguali
 */
export function objectsEqual(obj1, obj2) {
    if (obj1 === obj2) return true;
    if (!obj1 || !obj2) return false;
    
    const keys1 = Object.keys(obj1);
    const keys2 = Object.keys(obj2);
    
    if (keys1.length !== keys2.length) return false;
    
    return keys1.every(key => {
        const val1 = obj1[key];
        const val2 = obj2[key];
        
        // Confronto ricorsivo per oggetti annidati
        if (typeof val1 === 'object' && typeof val2 === 'object') {
            return objectsEqual(val1, val2);
        }
        
        return val1 === val2;
    });
}

/**
 * Crea una copia profonda di un oggetto
 * @param {Object} obj - Oggetto da copiare
 * @returns {Object} - Copia dell'oggetto
 */
export function deepClone(obj) {
    if (obj === null || typeof obj !== 'object') {
        return obj;
    }
    
    // Usa JSON per oggetti semplici (più veloce)
    try {
        return JSON.parse(JSON.stringify(obj));
    } catch (e) {
        // Fallback per oggetti complessi
        if (Array.isArray(obj)) {
            return obj.map(item => deepClone(item));
        }
        
        const clone = {};
        for (const key in obj) {
            if (Object.prototype.hasOwnProperty.call(obj, key)) {
                clone[key] = deepClone(obj[key]);
            }
        }
        return clone;
    }
}

/**
 * Conta le parole in un testo
 * @param {string} text - Testo
 * @returns {number} - Numero di parole
 */
export function countWords(text) {
    if (!text) return 0;
    return text.trim().split(/\s+/).length;
}

/**
 * Calcola la percentuale
 * @param {number} value - Valore
 * @param {number} total - Totale
 * @param {number} [decimals=0] - Decimali
 * @returns {number} - Percentuale
 */
export function calculatePercentage(value, total, decimals = 0) {
    if (!total) return 0;
    const percentage = (value / total) * 100;
    return Number(percentage.toFixed(decimals));
}

// Esporta tutte le funzioni come oggetto
export default {
    debounce,
    throttle,
    generateId,
    formatDate,
    truncateText,
    sanitizeHtml,
    objectToQueryString,
    queryStringToObject,
    filterItems,
    sortItems,
    groupBy,
    arrayDifference,
    objectsEqual,
    deepClone,
    countWords,
    calculatePercentage
};
