/**
 * integration-script.js - Script di integrazione per i moduli di annotazione migliorati
 * 
 * Questo script coordina l'integrazione dei nuovi moduli di evidenziazione e interazione
 * con il sistema di annotazione esistente, garantendo compatibilità e miglioramenti.
 */

document.addEventListener('DOMContentLoaded', function() {
    console.info('🔌 Inizializzazione integrazione dei moduli di annotazione migliorati');
    
    // Verifica che siamo nella pagina di annotazione
    const textContent = document.getElementById('text-content');
    if (!textContent) {
        console.info('Non siamo nella pagina di annotazione, interrompo l\'inizializzazione');
        return;
    }
    
    // ===== INIZIALIZZAZIONE DEI MODULI =====
    
    // Inizializza il motore di evidenziazione
    const highlightingEngine = window.HighlightingEngine || (window.setupHighlightingEngine && window.setupHighlightingEngine(textContent));
    
    // Inizializza il sistema di interazioni
    const annotationInteractions = window.AnnotationInteractions || (window.setupAnnotationInteractions && window.setupAnnotationInteractions());
    
    // Verifica che i moduli siano stati caricati correttamente
    if (!highlightingEngine) {
        console.warn('⚠️ Motore di evidenziazione non trovato, la funzionalità potrebbe essere limitata');
    }
    
    if (!annotationInteractions) {
        console.warn('⚠️ Sistema di interazione con le annotazioni non trovato, la funzionalità potrebbe essere limitata');
    }
    
    // ===== INTEGRAZIONE CON LE FUNZIONI ESISTENTI =====
    
    // Salva riferimenti alle funzioni originali
    const originalFunctions = {
        highlightExistingAnnotations: window.highlightExistingAnnotations,
        jumpToAnnotation: window.jumpToAnnotation,
        addAnnotationToList: window.addAnnotationToList,
        deleteAnnotation: window.deleteAnnotation,
        loadExistingAnnotations: window.loadExistingAnnotations
    };
    
    // Verifica ed estendi la funzione jumpToAnnotation
    if (originalFunctions.jumpToAnnotation) {
        window.jumpToAnnotation = function(annotationId) {
            // Usa il sistema di interazione se disponibile
            if (annotationInteractions) {
                annotationInteractions.highlightAnnotation(annotationId);
            } else {
                // Altrimenti usa la funzione originale
                originalFunctions.jumpToAnnotation(annotationId);
            }
        };
    }
    
    // Estendi la funzione addAnnotationToList
    if (originalFunctions.addAnnotationToList) {
        window.addAnnotationToList = function(annotation) {
            // Chiama la funzione originale
            const result = originalFunctions.addAnnotationToList(annotation);
            
            // Aggiorna l'highlighting se disponibile
            if (highlightingEngine && Array.isArray(window.existingAnnotations)) {
                highlightingEngine.highlightAnnotations(window.existingAnnotations);
            }
            
            return result;
        };
    }
    
    // Estendi la funzione deleteAnnotation
    if (originalFunctions.deleteAnnotation) {
        const originalDeleteAnnotation = window.deleteAnnotation;
        window.deleteAnnotation = function(annotationId) {
            // Se ci sono interazioni attive, rimuovi il focus
            if (annotationInteractions) {
                annotationInteractions.clearAnnotationFocus();
            }
            
            // Rimuovi l'highlighting se il motore è disponibile
            if (highlightingEngine) {
                highlightingEngine.removeAnnotation(annotationId);
            }
            
            // Chiama la funzione originale
            return originalDeleteAnnotation(annotationId);
        };
    }
    
    // ===== CONFIGURAZIONE DEGLI EVENTI AGGIUNTIVI =====
    
    // Gestione dell'evidenziazione durante il caricamento della pagina
    if (Array.isArray(window.existingAnnotations) && highlightingEngine) {
        // Esegui l'highlighting iniziale
        highlightingEngine.highlightAnnotations(window.existingAnnotations);
    } else {
        // Se non abbiamo ancora le annotazioni, usa la funzione originale
        if (originalFunctions.highlightExistingAnnotations) {
            originalFunctions.highlightExistingAnnotations();
        }
    }
    
    // Gestione dell'effetto di focus
    document.addEventListener('click', function(e) {
        // Gestione del click fuori dalle annotazioni - rimuovi il focus
        if (!e.target.closest('.entity-highlight') && 
            !e.target.closest('.annotation-item') &&
            annotationInteractions) {
            annotationInteractions.clearAnnotationFocus();
        }
    });
    
    // ===== MIGLIORAMENTI VISIVI AGGIUNTIVI =====
    
    // Aggiungi tooltip avanzati per le entità evidenziate
    addAdvancedTooltips();
    
    // Aggiorna il contatore di visibilità dopo il filtraggio
    const searchInput = document.getElementById('search-annotations');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            setTimeout(updateVisibilityCounters, 100);
        });
    }
    
    // ===== FUNZIONI DI SUPPORTO =====
    
    /**
     * Aggiunge tooltip migliorati agli elementi di highlighting
     */
    function addAdvancedTooltips() {
        // Aggiungi CSS per i tooltip avanzati
        const style = document.createElement('style');
        style.textContent = `
            /* Tooltip migliorato */
            .entity-highlight {
                position: relative;
            }
            
            .entity-highlight::after {
                content: attr(data-tooltip);
                position: absolute;
                bottom: 100%;
                left: 50%;
                transform: translateX(-50%) translateY(5px);
                background-color: rgba(0, 0, 0, 0.8);
                color: white;
                text-align: center;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.8rem;
                white-space: nowrap;
                z-index: 1000;
                pointer-events: none;
                opacity: 0;
                transition: opacity 0.3s, transform 0.3s;
                font-family: var(--font-sans);
                font-weight: normal;
                text-shadow: none;
            }
            
            .entity-highlight:hover::after {
                opacity: 1;
                transform: translateX(-50%) translateY(0);
            }
            
            /* Stile migliorato per gli elementi di tipo entità */
            .entity-type {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.5rem 0.75rem;
                margin-bottom: 0.5rem;
                border-radius: 0.375rem;
                cursor: pointer;
                transition: all 0.2s ease;
                color: white;
                font-weight: 500;
            }
            
            .entity-type:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            
            .entity-type.selected {
                box-shadow: 0 0 0 2px white, 0 4px 6px rgba(0, 0, 0, 0.1);
                transform: translateY(-2px);
            }
        `;
        document.head.appendChild(style);
    }
    
    /**
     * Aggiorna il contatore di annotazioni visibili
     */
    function updateVisibilityCounters() {
        const visibleCount = document.getElementById('visible-count');
        if (!visibleCount) return;
        
        const total = document.querySelectorAll('.annotation-item').length;
        const visible = document.querySelectorAll('.annotation-item:not(.d-none)').length;
        
        visibleCount.textContent = visible === total ? 
            `${total}` : 
            `${visible}/${total}`;
            
        // Mostra/nascondi il messaggio "nessuna annotazione"
        const noAnnotationsMsg = document.getElementById('no-annotations');
        if (noAnnotationsMsg) {
            if (visible === 0) {
                noAnnotationsMsg.classList.remove('d-none');
            } else {
                noAnnotationsMsg.classList.add('d-none');
            }
        }
    }
    
    console.info('✅ Integrazione dei moduli di annotazione completata');
});