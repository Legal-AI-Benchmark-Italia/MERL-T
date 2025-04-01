/**
 * annotation-interactions.js - Modulo dedicato alla gestione delle interazioni tra annotazioni
 * 
 * Questo modulo gestisce tutte le interazioni tra le annotazioni nel testo 
 * e gli elementi corrispondenti nella lista delle annotazioni, garantendo
 * sincronizzazione e coerenza nell'esperienza utente.
 */

const AnnotationInteractions = {
    // Stato delle interazioni
    state: {
        activeAnnotation: null,
        focusedHighlight: null,
        focusedItem: null,
        isSynchronizing: false,
        highlightClassTimeout: null
    },

    /**
     * Inizializza il sistema di interazioni tra annotazioni
     */
    init: function() {
        console.info('🔄 Inizializzazione sistema di interazioni tra annotazioni');
        
        // Configura delegati per gli eventi principali
        this.setupEventDelegates();
        
        // Aggiungi i listener per navigazione da tastiera
        this.setupKeyboardNavigation();
        
        console.info('✅ Sistema di interazioni tra annotazioni inizializzato');
    },

    /**
     * Configura i delegati degli eventi per tutti gli elementi di annotazione
     */
    setupEventDelegates: function() {
        // Gestione click su evidenziazioni nel testo
        document.addEventListener('click', (e) => {
            // Non fare nulla se stiamo già sincronizzando
            if (this.state.isSynchronizing) return;
            
            const highlightElement = e.target.closest('.entity-highlight');
            if (highlightElement) {
                this.handleHighlightClick(highlightElement);
            }
        });

        // Gestione click su elementi nella lista di annotazioni
        document.addEventListener('click', (e) => {
            // Non fare nulla se stiamo già sincronizzando
            if (this.state.isSynchronizing) return;
            
            // Ignora se è stato cliccato un bottone all'interno dell'item
            if (e.target.closest('button')) return;
            
            const annotationItem = e.target.closest('.annotation-item');
            if (annotationItem) {
                this.handleAnnotationItemClick(annotationItem);
            }
        });

        // Prevenire problemi di bubble per pulsanti all'interno degli item
        document.addEventListener('click', (e) => {
            const actionButton = e.target.closest('.annotation-item button');
            if (actionButton) {
                // Evita che il click sul pulsante si propaghi all'item
                e.stopPropagation();
            }
        }, true);
    },

    /**
     * Configura la navigazione da tastiera tra le annotazioni
     */
    setupKeyboardNavigation: function() {
        document.addEventListener('keydown', (e) => {
            // Ignora se siamo in un campo di input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
            
            // Shift + Freccia su: vai all'annotazione precedente
            if (e.shiftKey && e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigateToPreviousAnnotation();
            }
            
            // Shift + Freccia giù: vai all'annotazione successiva
            if (e.shiftKey && e.key === 'ArrowDown') {
                e.preventDefault();
                this.navigateToNextAnnotation();
            }
            
            // Escape: deseleziona l'annotazione corrente
            if (e.key === 'Escape') {
                this.clearAnnotationFocus();
            }
        });
    },

    /**
     * Gestisce il click su un'evidenziazione nel testo
     * @param {HTMLElement} highlightElement - L'elemento dell'evidenziazione
     */
    handleHighlightClick: function(highlightElement) {
        this.state.isSynchronizing = true;
        
        const annotationId = highlightElement.dataset.id;
        
        // Se è già attivo, deseleziona
        if (this.state.focusedHighlight === highlightElement) {
            this.clearAnnotationFocus();
            this.state.isSynchronizing = false;
            return;
        }
        
        // Rimuovi le classi focus da tutti gli highlight
        document.querySelectorAll('.entity-highlight.focused').forEach(el => {
            if (el !== highlightElement) el.classList.remove('focused');
        });
        
        // Aggiungi la classe focused all'highlight attuale
        highlightElement.classList.add('focused');
        this.state.focusedHighlight = highlightElement;
        
        // Trova e attiva l'elemento corrispondente nella lista
        const annotationItem = document.querySelector(`.annotation-item[data-id="${annotationId}"]`);
        if (annotationItem) {
            // Rimuovi active da tutti gli item
            document.querySelectorAll('.annotation-item.active').forEach(el => {
                el.classList.remove('active');
            });
            
            // Aggiungi active all'item corrispondente
            annotationItem.classList.add('active');
            this.state.focusedItem = annotationItem;
            
            // Scorri la lista fino all'item
            annotationItem.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center',
                inline: 'nearest'
            });
            
            // Imposta l'annotazione attiva
            this.state.activeAnnotation = annotationId;
            
            // Pubblica l'evento di selezione
            if (window.EventBus && window.AppEvents) {
                EventBus.publish(AppEvents.ANNOTATION.SELECTED, { 
                    annotationId,
                    source: 'text' 
                });
            }
        }
        
        this.state.isSynchronizing = false;
    },

    /**
     * Gestisce il click su un elemento nella lista di annotazioni
     * @param {HTMLElement} annotationItem - L'elemento della lista
     */
    handleAnnotationItemClick: function(annotationItem) {
        this.state.isSynchronizing = true;
        
        const annotationId = annotationItem.dataset.id;
        
        // Se è già attivo, deseleziona
        if (this.state.focusedItem === annotationItem) {
            this.clearAnnotationFocus();
            this.state.isSynchronizing = false;
            return;
        }
        
        // Rimuovi active da tutti gli altri item
        document.querySelectorAll('.annotation-item.active').forEach(el => {
            if (el !== annotationItem) el.classList.remove('active');
        });
        
        // Aggiungi active all'item corrente
        annotationItem.classList.add('active');
        this.state.focusedItem = annotationItem;
        
        // Trova e attiva l'highlight corrispondente nel testo
        const highlightElement = document.querySelector(`.entity-highlight[data-id="${annotationId}"]`);
        if (highlightElement) {
            // Rimuovi focused da tutti gli highlight
            document.querySelectorAll('.entity-highlight.focused').forEach(el => {
                if (el !== highlightElement) el.classList.remove('focused');
            });
            
            // Aggiungi focused all'highlight corrente
            highlightElement.classList.add('focused');
            this.state.focusedHighlight = highlightElement;
            
            // Scorri fino all'highlight nel testo
            highlightElement.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center',
                inline: 'nearest' 
            });
            
            // Aggiungi effetto flash temporaneo
            if (this.state.highlightClassTimeout) {
                clearTimeout(this.state.highlightClassTimeout);
            }
            
            highlightElement.classList.add('flash-highlight');
            this.state.highlightClassTimeout = setTimeout(() => {
                highlightElement.classList.remove('flash-highlight');
            }, 1500);
            
            // Imposta l'annotazione attiva
            this.state.activeAnnotation = annotationId;
            
            // Pubblica l'evento di selezione
            if (window.EventBus && window.AppEvents) {
                EventBus.publish(AppEvents.ANNOTATION.SELECTED, { 
                    annotationId,
                    source: 'list' 
                });
            }
        }
        
        this.state.isSynchronizing = false;
    },

    /**
     * Naviga alla prossima annotazione nella lista
     */
    navigateToNextAnnotation: function() {
        const annotations = Array.from(document.querySelectorAll('.annotation-item:not(.d-none)'));
        if (annotations.length === 0) return;
        
        let nextIndex = -1;
        if (this.state.focusedItem) {
            const currentIndex = annotations.indexOf(this.state.focusedItem);
            nextIndex = (currentIndex + 1) % annotations.length;
        } else {
            nextIndex = 0;
        }
        
        if (nextIndex !== -1) {
            this.handleAnnotationItemClick(annotations[nextIndex]);
        }
    },

    /**
     * Naviga all'annotazione precedente nella lista
     */
    navigateToPreviousAnnotation: function() {
        const annotations = Array.from(document.querySelectorAll('.annotation-item:not(.d-none)'));
        if (annotations.length === 0) return;
        
        let prevIndex = -1;
        if (this.state.focusedItem) {
            const currentIndex = annotations.indexOf(this.state.focusedItem);
            prevIndex = (currentIndex - 1 + annotations.length) % annotations.length;
        } else {
            prevIndex = annotations.length - 1;
        }
        
        if (prevIndex !== -1) {
            this.handleAnnotationItemClick(annotations[prevIndex]);
        }
    },

    /**
     * Rimuove il focus da tutte le annotazioni
     */
    clearAnnotationFocus: function() {
        document.querySelectorAll('.entity-highlight.focused').forEach(el => {
            el.classList.remove('focused');
        });
        
        document.querySelectorAll('.annotation-item.active').forEach(el => {
            el.classList.remove('active');
        });
        
        this.state.focusedHighlight = null;
        this.state.focusedItem = null;
        this.state.activeAnnotation = null;
        
        // Pubblica l'evento di deseleziona
        if (window.EventBus && window.AppEvents) {
            EventBus.publish(AppEvents.ANNOTATION.DESELECTED, {});
        }
    },

    /**
     * Evidenzia un'annotazione specifica
     * @param {string} annotationId - L'ID dell'annotazione
     */
    highlightAnnotation: function(annotationId) {
        const annotationItem = document.querySelector(`.annotation-item[data-id="${annotationId}"]`);
        if (annotationItem) {
            this.handleAnnotationItemClick(annotationItem);
        }
    },
    
    /**
     * Aggiunge stili CSS necessari al modulo
     */
    addStyles: function() {
        // Verifica se gli stili sono già stati aggiunti
        if (document.getElementById('annotation-interactions-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'annotation-interactions-styles';
        
        style.textContent = `
            /* Stili per le annotazioni attive e con focus */
            .entity-highlight.focused {
                outline: 2px solid #2563eb !important;
                outline-offset: 2px !important;
                z-index: 5 !important;
            }
            
            .annotation-item.active {
                background-color: #f0f9ff !important;
                border-left: 3px solid #2563eb !important;
            }
            
            /* Effetto flash per l'evidenziazione */
            @keyframes flash-highlight {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
            
            .flash-highlight {
                animation: flash-highlight 0.5s ease-in-out;
            }
            
            /* Miglioramenti visivi per le interazioni */
            .entity-highlight {
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .entity-highlight:hover {
                z-index: 4;
                transform: translateY(-1px);
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            
            .annotation-item {
                transition: all 0.2s ease;
                cursor: pointer;
            }
            
            .annotation-item:hover {
                transform: translateX(2px);
            }
            
            /* Stile per pulsanti nelle annotazioni */
            .annotation-item button {
                position: relative;
                z-index: 2;
            }
        `;
        
        document.head.appendChild(style);
    }
};

// Funzione per integrazione con altri moduli
function setupAnnotationInteractions() {
    // Aggiungi gli stili necessari
    AnnotationInteractions.addStyles();
    
    // Inizializza il modulo
    AnnotationInteractions.init();
    
    // Esponi funzioni pubbliche per l'integrazione
    window.highlightAnnotation = (annotationId) => AnnotationInteractions.highlightAnnotation(annotationId);
    window.clearAnnotationFocus = () => AnnotationInteractions.clearAnnotationFocus();
    
    // Se esiste il gestore di eventi, registra handlers per eventi rilevanti
    if (window.EventBus && window.AppEvents) {
        // Quando viene eliminata un'annotazione, pulisci il focus
        EventBus.subscribe(AppEvents.ANNOTATION.DELETED, () => {
            AnnotationInteractions.clearAnnotationFocus();
        });
        
        // Quando cambia la vista (modalità pulita), ripristina il focus dopo
        EventBus.subscribe(AppEvents.UI.CLEAN_MODE_TOGGLED, () => {
            setTimeout(() => {
                if (AnnotationInteractions.state.activeAnnotation) {
                    AnnotationInteractions.highlightAnnotation(AnnotationInteractions.state.activeAnnotation);
                }
            }, 300); // Attendi il completamento della transizione
        });
    }
    
    return AnnotationInteractions;
}

// Inizializza automaticamente se non all'interno di un altro modulo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupAnnotationInteractions);
} else {
    setupAnnotationInteractions();
}

// Esporta il modulo
window.AnnotationInteractions = AnnotationInteractions;