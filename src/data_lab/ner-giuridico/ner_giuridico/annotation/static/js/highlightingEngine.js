/**
 * highlightingEngine.js
 * Implementazione completa per l'applicazione e la gestione delle evidenziazioni del testo.
 * Utilizza l'API Range di JavaScript per una manipolazione DOM sicura e precisa.
 */

export class HighlightingEngine {
    constructor() {
        console.log("Highlighting Engine Initialized");
        this.currentHighlights = new Map(); // Memorizza gli span di evidenziazione per ID annotazione
    }

    /**
     * Applica evidenziazioni al contenuto di testo in base alle annotazioni.
     * @param {HTMLElement} textElement - L'elemento contenente il testo.
     * @param {Array} annotations - Array di oggetti annotazione {id, start, end, text, type}.
     * @param {Map} entityTypesMap - Mappa dei tipi di entità {id: {name, color}}.
     */
    applyHighlights(textElement, annotations, entityTypesMap) {
        if (!textElement) return;

        // 1. Rimuovi le evidenziazioni precedenti
        this.removeHighlighting(textElement);
        
        // 2. Memorizza la mappa corrente delle evidenziazioni
        this.currentHighlights = new Map();

        // 3. Ottieni tutti i nodi di testo nell'elemento
        const textNodes = this._getTextNodes(textElement);
        if (textNodes.length === 0) return;

        // 4. Ordina le annotazioni per posizione di inizio (importante per gestire sovrapposizioni)
        const sortedAnnotations = [...annotations].sort((a, b) => a.start - b.start);

        // 5. Applica le evidenziazioni in ordine inverso per evitare problemi con gli offset
        for (let i = sortedAnnotations.length - 1; i >= 0; i--) {
            const ann = sortedAnnotations[i];
            const entityType = entityTypesMap.get(ann.type);
            const color = entityType?.color || '#6c757d'; // Colore predefinito

            // Crea l'evidenziazione utilizzando l'API Range
            const highlightSpan = this._createHighlightSpan(textElement, textNodes, ann, color);
            
            // Memorizza il riferimento allo span per un accesso rapido
            if (highlightSpan) {
                this.currentHighlights.set(ann.id, highlightSpan);
            }
        }
    }

    /**
     * Crea un elemento span di evidenziazione per un'annotazione specifica.
     * @private
     * @param {HTMLElement} textElement - L'elemento contenente il testo.
     * @param {Array} textNodes - Array di nodi di testo all'interno dell'elemento.
     * @param {Object} annotation - L'oggetto annotazione.
     * @param {string} color - Il colore dell'evidenziazione.
     * @returns {HTMLElement|null} - L'elemento span creato o null in caso di errore.
     */
    _createHighlightSpan(textElement, textNodes, annotation, color) {
        try {
            // Crea un range per l'intera area di testo
            const range = document.createRange();
            range.selectNodeContents(textElement);
            
            // Trova i nodi di testo e gli offset corrispondenti alle posizioni di inizio e fine
            const { startNode, startOffset, endNode, endOffset } = 
                this._findNodesAndOffsets(textNodes, annotation.start, annotation.end);
            
            if (!startNode || !endNode) {
                console.warn(`Impossibile trovare i nodi per l'annotazione: ${annotation.text}`);
                return null;
            }
            
            // Imposta l'inizio e la fine del range
            range.setStart(startNode, startOffset);
            range.setEnd(endNode, endOffset);
            
            // Crea l'elemento span di evidenziazione
            const highlightSpan = document.createElement('span');
            highlightSpan.className = 'entity-highlight';
            highlightSpan.dataset.annotationId = annotation.id;
            highlightSpan.dataset.entityType = annotation.type;
            highlightSpan.style.backgroundColor = color;
            highlightSpan.style.padding = '2px 0';
            highlightSpan.style.borderRadius = '2px';
            highlightSpan.style.transition = 'all 0.2s ease-in-out';
            
            // Sostituisci il contenuto del range con lo span
            range.surroundContents(highlightSpan);
            
            return highlightSpan;
        } catch (error) {
            console.error(`Errore durante l'evidenziazione di "${annotation.text}": ${error.message}`);
            return null;
        }
    }

    /**
     * Trova i nodi di testo e gli offset corrispondenti alle posizioni di caratteri.
     * @private
     * @param {Array} textNodes - Array di nodi di testo.
     * @param {number} startPos - Posizione di inizio.
     * @param {number} endPos - Posizione di fine.
     * @returns {Object} - Oggetto contenente nodi e offset di inizio e fine.
     */
    _findNodesAndOffsets(textNodes, startPos, endPos) {
        let currentPos = 0;
        let startNode = null, startOffset = 0;
        let endNode = null, endOffset = 0;
        
        // Itera attraverso tutti i nodi di testo per trovare le posizioni
        for (const node of textNodes) {
            const nodeLength = node.nodeValue.length;
            
            // Controlla se la posizione di inizio è in questo nodo
            if (startNode === null && startPos >= currentPos && startPos <= currentPos + nodeLength) {
                startNode = node;
                startOffset = startPos - currentPos;
            }
            
            // Controlla se la posizione di fine è in questo nodo
            if (endNode === null && endPos >= currentPos && endPos <= currentPos + nodeLength) {
                endNode = node;
                endOffset = endPos - currentPos;
                break; // Possiamo uscire dal ciclo una volta trovati entrambi i nodi
            }
            
            currentPos += nodeLength;
        }
        
        return { startNode, startOffset, endNode, endOffset };
    }

    /**
     * Evidenzia e scorre fino a un'annotazione specifica.
     * @param {string} annotationId - L'ID dell'annotazione da evidenziare.
     * @param {HTMLElement} textElement - L'elemento contenente il testo.
     */
    highlightAnnotation(annotationId, textElement) {
        if (!textElement) return;
        
        // Cerca lo span di evidenziazione per l'ID annotazione
        const highlightSpan = this.currentHighlights.get(annotationId) || 
                             textElement.querySelector(`.entity-highlight[data-annotation-id="${annotationId}"]`);
        
        if (highlightSpan) {
            // Scorre fino alla vista
            highlightSpan.scrollIntoView({ behavior: 'smooth', block: 'center' });

            // Aggiunge una classe temporanea di focus/evidenziazione
            highlightSpan.classList.add('focused');
            highlightSpan.style.boxShadow = '0 0 0 2px rgba(38, 132, 255, 0.8)';
            
            // Rimuove l'evidenziazione dopo 2 secondi
            setTimeout(() => {
                highlightSpan.classList.remove('focused');
                highlightSpan.style.boxShadow = '';
            }, 2000);
        } else {
            console.warn(`Span di evidenziazione non trovato per l'ID annotazione: ${annotationId}`);
            // Fallback se lo span non viene trovato (meno preciso)
            const annotations = Array.from(textElement.querySelectorAll('.entity-highlight'))
                .map(span => ({
                    id: span.dataset.annotationId,
                    start: parseInt(span.dataset.start || '0'),
                    end: parseInt(span.dataset.end || '0')
                }));
            
            const annotation = annotations.find(ann => ann.id === annotationId);
            if (annotation) {
                const approxCharHeight = 20;
                const approxScroll = (annotation.start / textElement.textContent.length) * 
                                    textElement.scrollHeight - (textElement.clientHeight / 2);
                textElement.scrollTo({ top: approxScroll, behavior: 'smooth' });
            }
        }
    }

    /**
     * Rimuove tutti gli span di evidenziazione.
     * @param {HTMLElement} textElement - L'elemento contenente il testo.
     */
    removeHighlighting(textElement) {
        if (!textElement) return;
        
        // Trova tutti gli span di evidenziazione
        const highlights = textElement.querySelectorAll('span.entity-highlight');
        
        // Rimuovi ogni span preservando il suo contenuto
        highlights.forEach(span => {
            const parent = span.parentNode;
            
            // Sposta tutti i figli dello span prima dello span stesso
            while (span.firstChild) {
                parent.insertBefore(span.firstChild, span);
            }
            
            // Rimuovi lo span vuoto
            parent.removeChild(span);
            parent.normalize(); // Unisce i nodi di testo adiacenti
        });
        
        // Pulisci la mappa delle evidenziazioni correnti
        this.currentHighlights.clear();
    }

    /**
     * Ottiene tutti i nodi di testo all'interno di un elemento (necessario per il mapping degli offset).
     * @private
     * @param {Node} node - Il nodo da cui iniziare la ricerca.
     * @returns {Array} - Array di nodi di testo.
     */
    _getTextNodes(node) {
        const textNodes = [];
        
        // Funzione ricorsiva per attraversare l'albero DOM
        const getTextNodesRecursive = (currentNode) => {
            if (currentNode.nodeType === Node.TEXT_NODE) {
                // Includi solo nodi di testo non vuoti
                if (currentNode.nodeValue.trim() !== '') {
                    textNodes.push(currentNode);
                }
            } else {
                // Attraversa ricorsivamente i figli
                for (const child of currentNode.childNodes) {
                    getTextNodesRecursive(child);
                }
            }
        };
        
        getTextNodesRecursive(node);
        return textNodes;
    }
}