/**
 * highlighting-engine.js - Motore di evidenziazione avanzato per le annotazioni
 * 
 * Questo modulo gestisce tutte le operazioni di evidenziazione delle annotazioni nel testo,
 * con particolare attenzione alla stabilità, alle prestazioni e alla gestione delle sovrapposizioni.
 */

const HighlightingEngine = {
    // Stato del sistema di highlighting
    state: {
        processedText: null,
        annotations: [],
        isProcessing: false,
        textNode: null,
        lastHighlightTime: 0,
        debounceTime: 100, // ms di debounce per operazioni di highlighting
        preprocessed: false
    },

    /**
     * Inizializza il motore di evidenziazione
     * @param {HTMLElement} textNode - Elemento del testo in cui fare l'highlighting
     */
    init: function(textNode) {
        console.info('🔄 Inizializzazione motore di evidenziazione');
        this.state.textNode = textNode || document.getElementById('text-content');
        
        if (!this.state.textNode) {
            console.warn('⚠️ Elemento di testo non trovato, l\'evidenziazione non funzionerà');
            return;
        }
        
        // Esegui il preprocessing iniziale del testo
        this.preprocessText();
        
        // Configura l'observer per rilevare cambiamenti
        this.setupMutationObserver();
        
        console.info('✅ Motore di evidenziazione inizializzato');
    },

    /**
     * Esegue il preprocessing ottimizzato del testo
     */
    preprocessText: function() {
        if (!this.state.textNode || this.state.isProcessing) return;
        
        // Salva la posizione di scorrimento
        const scrollPos = this.state.textNode.scrollTop;
        
        this.state.isProcessing = true;
        this.state.preprocessed = true;
        
        // Salva il testo originale se non è già stato fatto
        if (!this.state.processedText) {
            this.state.processedText = this.state.textNode.textContent;
        }
        
        // Formattazione migliorata per testi giuridici
        if (this.state.processedText) {
            // Applicare formattazione
            let formattedText = this.state.processedText
                // Formatta riferimenti giuridici
                .replace(/(\b(?:art|artt|comma|commi|par|paragr)\.\s*\d+(?:[,\s]\d+)*)/gi, 
                         '<span class="legal-reference">$1</span>')
                // Formatta sequenze numeriche
                .replace(/(\d+(?:[,.]\d+){1,})/g, 
                         '<span class="legal-number">$1</span>')
                // Migliora la spaziatura
                .replace(/\.(\w)/g, '. $1')
                // Formatta i paragrafi
                .replace(/\n\s*\n/g, '</p><p class="legal-paragraph">');
            
            // Avvolgi in paragrafi se necessario
            if (!formattedText.includes('<p')) {
                formattedText = '<p class="legal-paragraph">' + formattedText + '</p>';
            }
            
            // Aggiorna il testo solo se necessario per evitare flickering
            if (this.state.textNode.innerHTML !== formattedText) {
                this.state.textNode.innerHTML = formattedText;
            }
        }
        
        // Ripristina la posizione di scorrimento
        this.state.textNode.scrollTop = scrollPos;
        this.state.isProcessing = false;
    },

    /**
     * Configura l'observer per monitorare modifiche nel DOM
     */
    setupMutationObserver: function() {
        // Verifica esplicitamente che textNode sia un elemento DOM valido
        if (!this.state.textNode || !(this.state.textNode instanceof Element)) {
            console.warn('⚠️ MutationObserver: textNode non è un elemento DOM valido');
            return;
        }
        
        try {
            // Crea un observer per monitorare cambiamenti nel content-text
            const observer = new MutationObserver((mutations) => {
                // Ignora durante l'elaborazione per evitare cicli infiniti
                if (this.state.isProcessing) return;
                
                let shouldReprocess = false;
                
                // Verifica se ci sono stati cambiamenti rilevanti
                for (const mutation of mutations) {
                    if (mutation.type === 'childList' || mutation.type === 'characterData') {
                        shouldReprocess = true;
                        break;
                    }
                }
                
                // Se necessario, reprocessa e riapplica l'highlighting
                if (shouldReprocess) {
                    // Limita la frequenza delle operazioni di highlighting con debounce
                    const now = Date.now();
                    if (now - this.state.lastHighlightTime > this.state.debounceTime) {
                        this.state.lastHighlightTime = now;
                        
                        // Dopo una modifica, esegui il preprocessing e poi l'highlighting
                        if (!this.state.preprocessed) {
                            this.preprocessText();
                        }
                        
                        // Se ci sono annotazioni, riapplica l'highlighting
                        if (this.state.annotations.length > 0) {
                            this.highlightAnnotations(this.state.annotations);
                        }
                    }
                }
            });
            
            // Verifica che l'elemento sia ancora valido prima di iniziare l'osservazione
            if (this.state.textNode && this.state.textNode.nodeType === Node.ELEMENT_NODE) {
                observer.observe(this.state.textNode, {
                    childList: true,
                    characterData: true,
                    subtree: true
                });
                console.debug('MutationObserver inizializzato con successo su', this.state.textNode);
            } else {
                console.warn('⚠️ Impossibile inizializzare MutationObserver: elemento non valido');
            }
        } catch (error) {
            console.error('Errore nell\'inizializzazione del MutationObserver:', error);
        }
    },

    /**
     * Carica le annotazioni e le evidenzia nel testo
     * @param {Array} annotations - Array di annotazioni da evidenziare
     */
    highlightAnnotations: function(annotations) {
        if (!this.state.textNode || this.state.isProcessing) return;
        
        this.state.isProcessing = true;
        
        // Salva la posizione di scorrimento e la selezione
        const scrollPos = this.state.textNode.scrollTop;
        const selection = window.getSelection();
        const savedSelection = {
            rangeCount: selection.rangeCount,
            ranges: []
        };
        
        for (let i = 0; i < selection.rangeCount; i++) {
            savedSelection.ranges.push(selection.getRangeAt(i));
        }
        
        try {
            // Salva le annotazioni nello stato
            this.state.annotations = Array.isArray(annotations) ? [...annotations] : [];
            
            // Se non ci sono annotazioni, reimposta il testo e esci
            if (!this.state.annotations.length) {
                // Se non è mai stato preprocessato, fallo ora
                if (!this.state.preprocessed) {
                    this.preprocessText();
                }
                this.state.isProcessing = false;
                return;
            }
            
            // Ottieni il testo completo
            const fullText = this.state.processedText || this.state.textNode.textContent;
            
            // Ordina le annotazioni per posizione e lunghezza (le più lunghe prima)
            const sortedAnnotations = this.sortAnnotationsByPosition([...this.state.annotations]);
            
            // Crea un array di oggetti per ogni carattere nel testo
            const charObjects = this.prepareCharacterObjects(fullText, sortedAnnotations);
            
            // Genera l'HTML con le evidenziazioni
            const html = this.generateHighlightedHTML(charObjects);
            
            // Aggiorna il contenuto solo se è cambiato
            if (this.state.textNode.innerHTML !== html) {
                this.state.textNode.innerHTML = html;
            }
            
            // Controlla sovrapposizioni problematiche
            setTimeout(() => {
                this.checkForOverlappingHighlights();
            }, 0);
            
        } catch (error) {
            console.error('Errore durante l\'evidenziazione:', error);
        } finally {
            // Ripristina lo scroll
            this.state.textNode.scrollTop = scrollPos;
            
            // Ripristina la selezione se c'era
            if (savedSelection.rangeCount > 0) {
                selection.removeAllRanges();
                for (const range of savedSelection.ranges) {
                    selection.addRange(range);
                }
            }
            
            this.state.isProcessing = false;
        }
    },

    /**
     * Ordina le annotazioni per posizione e lunghezza
     * @param {Array} annotations - Le annotazioni da ordinare
     * @returns {Array} - Annotazioni ordinate
     */
    sortAnnotationsByPosition: function(annotations) {
        return annotations.sort((a, b) => {
            // Prima per posizione di inizio
            if (a.start !== b.start) {
                return a.start - b.start;
            }
            // A parità di inizio, ordina per lunghezza (le più lunghe prima)
            return (b.end - b.start) - (a.end - a.start);
        });
    },

    /**
     * Prepara un array di oggetti carattere con le annotazioni associate
     * @param {string} text - Il testo completo
     * @param {Array} annotations - Le annotazioni ordinate
     * @returns {Array} - Array di oggetti carattere
     */
    prepareCharacterObjects: function(text, annotations) {
        // Crea un array di oggetti che rappresentano ciascun carattere del testo
        const charObjects = Array.from(text).map((char, index) => ({
            char: char,
            annotations: []
        }));
        
        // Associa le annotazioni a ciascun carattere
        annotations.forEach(ann => {
            // Assicurati che start e end siano numeri
            const start = parseInt(ann.start, 10);
            const end = parseInt(ann.end, 10);
            
            // Verifica che gli indici siano validi
            if (isNaN(start) || isNaN(end) || start < 0 || end > charObjects.length) {
                console.warn(`Annotazione con indici non validi: ${ann.id}, start=${start}, end=${end}, lunghezza testo=${charObjects.length}`);
                return;
            }
            
            // Associa l'annotazione a ciascun carattere nell'intervallo
            for (let i = start; i < end; i++) {
                if (i >= 0 && i < charObjects.length) {
                    charObjects[i].annotations.push(ann);
                }
            }
        });
        
        return charObjects;
    },

    /**
     * Genera l'HTML con le evidenziazioni
     * @param {Array} charObjects - Array di oggetti carattere
     * @returns {string} - HTML con evidenziazioni
     */
    generateHighlightedHTML: function(charObjects) {
        let html = '';
        let currentAnnotations = [];
        
        for (let i = 0; i < charObjects.length; i++) {
            const charObj = charObjects[i];
            
            // Verifica se le annotazioni sono cambiate
            if (!this.arraysEqual(currentAnnotations, charObj.annotations)) {
                // Chiudi tutti i tag span precedenti
                for (let j = 0; j < currentAnnotations.length; j++) {
                    html += '</span>';
                }
                
                // Apri nuovi tag span per le nuove annotazioni
                charObj.annotations.forEach(ann => {
                    const entityColor = ann.color || this.getEntityColor(ann.type);
                    const tooltipText = this.getEntityName(ann.type);
                    
                    html += `<span class="entity-highlight" 
                                  data-id="${ann.id}" 
                                  data-type="${ann.type}" 
                                  data-tooltip="${tooltipText}"
                                  style="background-color: ${entityColor}">`;
                });
                
                currentAnnotations = [...charObj.annotations];
            }
            
            // Aggiungi il carattere corrente
            html += this.escapeHTML(charObj.char);
        }
        
        // Chiudi tutti i tag span alla fine
        for (let j = 0; j < currentAnnotations.length; j++) {
            html += '</span>';
        }
        
        return html;
    },

    /**
     * Verifica se ci sono sovrapposizioni visive tra le evidenziazioni
     */
    checkForOverlappingHighlights: function() {
        const highlights = Array.from(document.querySelectorAll('.entity-highlight'));
        let overlapsFound = 0;
        
        // Crea una mappa di elementi per riga
        const lineMap = new Map();
        
        highlights.forEach(highlight => {
            const rect = highlight.getBoundingClientRect();
            const lineKey = Math.round(rect.top); // Arrotonda per gestire imprecisioni
            
            if (!lineMap.has(lineKey)) {
                lineMap.set(lineKey, []);
            }
            
            lineMap.get(lineKey).push({
                element: highlight,
                left: rect.left,
                right: rect.right
            });
        });
        
        // Controlla le sovrapposizioni per ogni riga
        lineMap.forEach((line, lineKey) => {
            if (line.length < 2) return; // Nessuna sovrapposizione possibile
            
            // Ordina per posizione da sinistra
            line.sort((a, b) => a.left - b.left);
            
            // Controlla sovrapposizioni orizzontali
            for (let i = 0; i < line.length - 1; i++) {
                const current = line[i];
                const next = line[i + 1];
                
                if (current.right > next.left + 2) { // 2px di tolleranza
                    current.element.classList.add('overlap');
                    next.element.classList.add('overlap');
                    overlapsFound++;
                }
            }
        });
        
        if (overlapsFound > 0) {
            console.debug(`Trovate ${overlapsFound} sovrapposizioni tra annotazioni`);
        }
    },

    /**
     * Ottiene il colore associato a un tipo di entità
     * @param {string} entityType - Il tipo di entità
     * @returns {string} - Il colore in formato CSS
     */
    getEntityColor: function(entityType) {
        // Cerca il tipo di entità nel DOM
        const entityElement = document.querySelector(`.entity-type[data-type="${entityType}"]`);
        
        if (entityElement) {
            return entityElement.style.backgroundColor || "#CCCCCC";
        }
        
        // Cerca con il metodo del toolkit globale (retrocompatibilità)
        if (window.getEntityColorById) {
            return window.getEntityColorById(entityType);
        }
        
        // Colore di fallback se non trovato
        return "#CCCCCC";
    },

    /**
     * Ottiene il nome visualizzato di un tipo di entità
     * @param {string} entityType - Il tipo di entità
     * @returns {string} - Il nome visualizzato dell'entità
     */
    getEntityName: function(entityType) {
        // Cerca il tipo di entità nel DOM
        const entityElement = document.querySelector(`.entity-type[data-type="${entityType}"]`);
        
        if (entityElement) {
            const nameElement = entityElement.querySelector('.entity-name');
            return nameElement ? nameElement.textContent : entityType;
        }
        
        // Cerca con il metodo del toolkit globale (retrocompatibilità)
        if (window.getEntityNameById) {
            return window.getEntityNameById(entityType);
        }
        
        // Ritorna l'ID se non trovato
        return entityType;
    },

    /**
     * Verifica l'uguaglianza tra due array di annotazioni
     * @param {Array} a - Primo array di annotazioni
     * @param {Array} b - Secondo array di annotazioni
     * @returns {boolean} - True se gli array sono uguali
     */
    arraysEqual: function(a, b) {
        if (a.length !== b.length) return false;
        
        // Confronta gli id delle annotazioni
        for (let i = 0; i < a.length; i++) {
            if (a[i].id !== b[i].id) return false;
        }
        
        return true;
    },

    /**
     * Escapa i caratteri HTML
     * @param {string} text - Testo da escapare
     * @returns {string} - Testo escapato
     */
    escapeHTML: function(text) {
        const entityMap = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;',
            '/': '&#x2F;',
            '`': '&#x60;',
            '=': '&#x3D;'
        };
        
        return String(text).replace(/[&<>"'`=\/]/g, function (s) {
            return entityMap[s];
        });
    },

    /**
     * Pulisce tutte le evidenziazioni
     */
    clearHighlights: function() {
        if (!this.state.textNode || this.state.isProcessing) return;
        
        this.state.annotations = [];
        this.state.isProcessing = true;
        
        // Ripristina il testo originale processato
        if (this.state.processedText) {
            this.preprocessText();
        }
        
        this.state.isProcessing = false;
    },

    /**
     * Aggiorna una singola annotazione
     * @param {Object} annotation - L'annotazione aggiornata
     */
    updateAnnotation: function(annotation) {
        if (!annotation || !annotation.id) return;
        
        // Trova e aggiorna l'annotazione
        const index = this.state.annotations.findIndex(a => a.id === annotation.id);
        if (index !== -1) {
            this.state.annotations[index] = annotation;
            
            // Ri-esegui l'highlighting
            this.highlightAnnotations(this.state.annotations);
        }
    },

    /**
     * Rimuove un'annotazione dall'highlighting
     * @param {string} annotationId - L'ID dell'annotazione
     */
    removeAnnotation: function(annotationId) {
        if (!annotationId) return;
        
        // Filtra le annotazioni per rimuovere quella con l'ID specificato
        this.state.annotations = this.state.annotations.filter(a => a.id !== annotationId);
        
        // Ri-esegui l'highlighting
        this.highlightAnnotations(this.state.annotations);
    },

    /**
     * Aggiunge stili CSS necessari per il funzionamento del motore
     */
    addStyles: function() {
        // Verifica se gli stili sono già stati aggiunti
        if (document.getElementById('highlighting-engine-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'highlighting-engine-styles';
        
        style.textContent = `
            /* Stili per le evidenziazioni */
            .entity-highlight {
                display: inline !important;
                padding: 0.1em 0.1em !important;
                border-radius: 3px !important;
                position: relative !important;
                white-space: pre-wrap !important;
                line-height: inherit !important;
                width: auto !important;
                box-decoration-break: clone !important;
                -webkit-box-decoration-break: clone !important;
                cursor: pointer !important;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08) !important;
                transition: all 0.2s ease !important;
                color: white !important;
                text-shadow: 0px 0px 1px rgba(0, 0, 0, 0.4) !important;
                opacity: 1 !important;
            }
            
            .entity-highlight:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 3px 6px rgba(0, 0, 0, 0.16) !important;
                z-index: 10 !important;
            }
            
            /* Stile per sovrapposizioni */
            .entity-highlight.overlap {
                outline: 2px dashed rgba(255, 255, 255, 0.7) !important;
                z-index: 2 !important;
                box-shadow: 0 0 0 1px #ff9800, 0 1px 2px rgba(0, 0, 0, 0.08) !important;
            }
            
            /* Stili per riferimenti legali e numeri */
            .legal-reference {
                font-weight: 500;
                color: #0056b3;
            }
            
            .legal-number {
                font-family: monospace;
                color: #555;
            }
            
            .legal-paragraph {
                margin-bottom: 1.2rem;
                text-indent: 1.5rem;
            }
        `;
        
        document.head.appendChild(style);
    }
};

/**
 * Funzione di setup per l'integrazione con altri moduli
 * @param {HTMLElement} textNode - Elemento del testo (opzionale)
 * @returns {Object} - Istanza del motore di evidenziazione
 */
function setupHighlightingEngine(textNode) {
    // Aggiungi gli stili necessari
    HighlightingEngine.addStyles();
    
    // Inizializza il motore
    HighlightingEngine.init(textNode);
    
    // Reimposta le funzioni globali con versioni migliorate per retrocompatibilità
    if (typeof window.highlightExistingAnnotations === 'function') {
        // Salva la funzione originale
        const originalHighlight = window.highlightExistingAnnotations;
        
        // Sostituisci con una versione migliorata
        window.highlightExistingAnnotations = function() {
            // Carica le annotazioni usando la logica esistente
            if (typeof loadExistingAnnotations === 'function') {
                loadExistingAnnotations();
            }
            
            // Se le annotazioni sono state caricate in una variabile globale
            if (Array.isArray(window.existingAnnotations)) {
                HighlightingEngine.highlightAnnotations(window.existingAnnotations);
            } else {
                // Altrimenti usa la funzione originale
                originalHighlight.apply(this, arguments);
            }
            
            // Configura gli eventi degli highlight se esistenti
            if (typeof setupHighlightEvents === 'function') {
                setupHighlightEvents();
            }
        };
    }
    
    // Integrazione con EventBus
    if (window.EventBus && window.AppEvents) {
        // Quando le annotazioni vengono caricate
        EventBus.subscribe(AppEvents.ANNOTATION.LOADED, (data) => {
            if (Array.isArray(data.annotations)) {
                HighlightingEngine.highlightAnnotations(data.annotations);
            }
        });
        
        // Quando un'annotazione viene eliminata
        EventBus.subscribe(AppEvents.ANNOTATION.DELETED, (data) => {
            if (data.annotationId) {
                HighlightingEngine.removeAnnotation(data.annotationId);
            }
        });
        
        // Quando un'annotazione viene aggiornata
        EventBus.subscribe(AppEvents.ANNOTATION.UPDATED, (data) => {
            if (data.annotation) {
                HighlightingEngine.updateAnnotation(data.annotation);
            }
        });
    }
    
    return HighlightingEngine;
}

// Inizializza automaticamente se non all'interno di un altro modulo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupHighlightingEngine);
} else {
    setupHighlightingEngine();
}

// Esporta il modulo
window.HighlightingEngine = HighlightingEngine;