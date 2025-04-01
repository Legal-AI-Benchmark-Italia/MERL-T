/**
 * ui-enhancements.js - Miglioramenti dell'interfaccia utente per l'applicazione di annotazione
 * Versione ristrutturata per compatibilità con le correzioni alle funzionalità di annotazione
 */

document.addEventListener('DOMContentLoaded', function() {
    const UIEnhancer = {
        /**
         * Stato dell'enhancer
         */
        state: {
            initialized: false,
            panelStates: {
                entityCollapsed: false,
                annotationsCollapsed: false
            }
        },
        
        /**
         * Inizializza tutti i miglioramenti dell'interfaccia utente
         */
        init: function() {
            console.info("✨ Inizializzazione miglioramenti UI");
            
            // Verifica prerequisiti
            if (!this.checkPrerequisites()) {
                console.warn("Prerequisiti mancanti per UI Enhancer, alcune funzionalità potrebbero non funzionare correttamente");
            }
            
            // Inizializza funzionalità in ordine di priorità
            this.addProgressIndicator();
            this.enhancePanelVisibility();
            this.addAccessibilityFeatures();
            this.setupUserOnboarding();
            this.addKeyboardShortcutsPanel();
            this.improveTabNavigation();
            this.addResponsiveDesignSupport();
            this.enhanceAnnotationVisibility();
            
            // Segnala inizializzazione completata
            this.state.initialized = true;
            console.info("✨ Miglioramenti UI inizializzati con successo");
        },

        /**
         * Verifica che i prerequisiti siano presenti
         */
        checkPrerequisites: function() {
            let allPresent = true;
            
            // Verifica che AnnotationManager sia definito
            if (typeof AnnotationManager === 'undefined') {
                console.warn("AnnotationManager non trovato");
                allPresent = false;
            }
            
            // Verifica che NERGiuridico sia definito
            if (typeof NERGiuridico === 'undefined') {
                console.warn("NERGiuridico utilities non trovate");
                allPresent = false;
            }
            
            return allPresent;
        },

        /**
         * Aggiunge un indicatore di progresso persistente
         * Compatibile con la barra di progresso migliorata
         */
        addProgressIndicator: function() {
            // Crea un elemento per il progresso complessivo nella parte superiore della pagina
            const progressContainer = document.createElement('div');
            progressContainer.className = 'annotation-progress-container';
            progressContainer.innerHTML = `
                <div class="annotation-progress-bar">
                    <div class="annotation-progress-fill" id="global-annotation-progress"></div>
                </div>
                <div class="annotation-progress-stats">
                    <span id="annotation-progress-percentage">0%</span>
                    <span id="annotation-progress-count">0 annotazioni</span>
                </div>
            `;

            // Inserisci dopo la document-info, prima dell'area di annotazione
            const documentInfo = document.querySelector('.document-info');
            if (documentInfo) {
                documentInfo.parentNode.insertBefore(progressContainer, documentInfo.nextSibling);

                // Non è più necessario aggiungere stili custom poiché sono inclusi nel CSS migliorato

                // Implementa la funzione di aggiornamento del progresso
                window.updateGlobalProgressIndicator = function() {
                    // Ottieni elementi DOM
                    const progressFill = document.getElementById('global-annotation-progress');
                    const percentageEl = document.getElementById('annotation-progress-percentage');
                    const countEl = document.getElementById('annotation-progress-count');
                    
                    if (!progressFill || !percentageEl || !countEl) return;
                    
                    // Ottieni conteggi
                    const totalWords = parseInt(document.getElementById('text-content').dataset.wordCount) || 100;
                    const annotationCount = document.querySelectorAll('.annotation-item').length;
                    
                    // Calcola una stima della copertura
                    const coverage = Math.min(annotationCount / (totalWords / 15) * 100, 100);
                    
                    // Aggiorna la barra di progresso e le statistiche
                    progressFill.style.width = `${coverage}%`;
                    percentageEl.textContent = `${Math.round(coverage)}%`;
                    countEl.textContent = 
                        `${annotationCount} ${annotationCount === 1 ? 'annotazione' : 'annotazioni'}`;
                    
                    // Aggiorna anche la classe nel body per lo stato di completamento
                    if (coverage >= 70) {
                        document.body.classList.add('high-completion');
                        document.body.classList.remove('medium-completion');
                    } else if (coverage >= 30) {
                        document.body.classList.add('medium-completion');
                        document.body.classList.remove('high-completion');
                    } else {
                        document.body.classList.remove('medium-completion', 'high-completion');
                    }
                };

                // Hook per aggiornare l'indicatore quando vengono aggiornate le annotazioni
                // Usa l'implementazione originale se esiste, altrimenti crea una nuova
                const originalUpdateAnnotationCount = window.updateAnnotationCount;
                if (originalUpdateAnnotationCount) {
                    window.updateAnnotationCount = function() {
                        // Chiama la funzione originale
                        originalUpdateAnnotationCount.apply(this, arguments);
                        
                        // Aggiorna l'indicatore globale
                        if (typeof window.updateGlobalProgressIndicator === 'function') {
                            window.updateGlobalProgressIndicator();
                        }
                    };
                }

                // Esegui subito l'aggiornamento iniziale
                setTimeout(function() {
                    if (typeof window.updateGlobalProgressIndicator === 'function') {
                        window.updateGlobalProgressIndicator();
                    }
                }, 500);
            }
        },

        /**
         * Migliora la visibilità e l'accessibilità dei pannelli
         * Compatibile con la nuova gestione della modalità clean
         */
        enhancePanelVisibility: function() {
            // Aggiungi indicatori di pannello per rendere chiaro che ci sono pannelli laterali
            const entitySidebar = document.querySelector('.entity-sidebar');
            const annotationsSidebar = document.querySelector('.annotations-sidebar');
            
            if (entitySidebar && annotationsSidebar) {
                // Assicura che i pannelli abbiano un'intestazione visibile
                this.enhancePanelHeader(entitySidebar, 'Tipi di Entità', 'fas fa-tags');
                this.enhancePanelHeader(annotationsSidebar, 'Annotazioni', 'fas fa-list-ul');
                
                // Aggiungi pulsanti per espandere/contrarre i pannelli
                this.addPanelToggleButtons();
                
                // Salva e ripristina lo stato dei pannelli
                this.setupPanelStateRestoration();
            }
        },
        
        /**
         * Migliora l'intestazione del pannello
         * @param {HTMLElement} panel - Il pannello da migliorare
         * @param {string} title - Il titolo da mostrare
         * @param {string} iconClass - La classe Font Awesome per l'icona
         */
        enhancePanelHeader: function(panel, title, iconClass) {
            // Trova l'intestazione esistente o creane una nuova
            let header = panel.querySelector('h5');
            if (!header) {
                header = document.createElement('div');
                header.className = 'panel-header';
                panel.insertBefore(header, panel.firstChild);
            } else {
                // Avvolgi l'intestazione esistente in un div
                const parent = header.parentNode;
                const wrapper = document.createElement('div');
                wrapper.className = 'panel-header';
                parent.insertBefore(wrapper, header);
                wrapper.appendChild(header);
                header = wrapper;
            }
            
            // Estrai il testo esistente o usa il titolo fornito
            const headerText = header.textContent.trim() || title;
            
            // Sostituisci il contenuto con il nuovo formato
            header.innerHTML = `
                <i class="${iconClass}"></i>
                <h5>${headerText}</h5>
            `;
        },
        
        /**
         * Aggiunge pulsanti per espandere/contrarre i pannelli
         * Compatibile con la nuova modalità clean
         */
        addPanelToggleButtons: function() {
            const entitySidebar = document.querySelector('.entity-sidebar');
            const annotationsSidebar = document.querySelector('.annotations-sidebar');
            const textContainer = document.querySelector('.text-container');
            
            if (entitySidebar) {
                const toggleBtn = document.createElement('div');
                toggleBtn.className = 'panel-toggle entity-panel-toggle';
                toggleBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
                toggleBtn.title = 'Espandi/Contrai pannello';
                entitySidebar.appendChild(toggleBtn);
                
                toggleBtn.addEventListener('click', () => {
                    // Non permettere il toggle in modalità clean
                    if (document.body.classList.contains('clean-mode')) return;
                    
                    entitySidebar.classList.toggle('panel-collapsed');
                    this.state.panelStates.entityCollapsed = entitySidebar.classList.contains('panel-collapsed');
                    
                    // Aggiorna la classe di text-container per dare più spazio
                    if (textContainer) {
                        textContainer.classList.toggle('entity-panel-collapsed');
                    }
                    
                    // Salva lo stato
                    localStorage.setItem('entity-panel-collapsed', this.state.panelStates.entityCollapsed);
                });
            }
            
            if (annotationsSidebar) {
                const toggleBtn = document.createElement('div');
                toggleBtn.className = 'panel-toggle annotations-panel-toggle';
                toggleBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
                toggleBtn.title = 'Espandi/Contrai pannello';
                annotationsSidebar.appendChild(toggleBtn);
                
                toggleBtn.addEventListener('click', () => {
                    // Non permettere il toggle in modalità clean
                    if (document.body.classList.contains('clean-mode')) return;
                    
                    annotationsSidebar.classList.toggle('panel-collapsed');
                    this.state.panelStates.annotationsCollapsed = annotationsSidebar.classList.contains('panel-collapsed');
                    
                    // Aggiorna la classe di text-container per dare più spazio
                    if (textContainer) {
                        textContainer.classList.toggle('annotations-panel-collapsed');
                    }
                    
                    // Salva lo stato
                    localStorage.setItem('annotations-panel-collapsed', this.state.panelStates.annotationsCollapsed);
                });
            }
            
            // Aggiungi stili per i pulsanti e l'espansione del contenuto
            this.addStyles(`
                .panel-toggle {
                    position: absolute;
                    top: 1rem;
                    background: white;
                    border: 1px solid #e5e7eb;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    border-radius: 50%;
                    width: 28px;
                    height: 28px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    z-index: 10;
                    transition: all 0.2s ease;
                }
                
                .panel-toggle:hover {
                    background: #f3f4f6;
                    transform: scale(1.1);
                }
                
                .entity-sidebar .panel-toggle {
                    right: -14px;
                }
                
                .annotations-sidebar .panel-toggle {
                    left: -14px;
                }
                
                .panel-collapsed {
                    width: 50px !important;
                    overflow: hidden;
                }
                
                .panel-collapsed * {
                    opacity: 0;
                }
                
                .panel-collapsed .panel-toggle {
                    opacity: 1;
                }
                
                .text-container.entity-panel-collapsed {
                    margin-left: 50px !important;
                }
                
                .text-container.annotations-panel-collapsed {
                    margin-right: 50px !important;
                }
                
                /* Quando il pannello è aperto, cambia l'icona */
                .panel-collapsed .panel-toggle i.fa-chevron-left:before {
                    content: "\\f054"; /* fa-chevron-right */
                }
                
                .panel-collapsed .panel-toggle i.fa-chevron-right:before {
                    content: "\\f053"; /* fa-chevron-left */
                }
                
                /* Disabilita il toggle quando in modalità clean */
                body.clean-mode .panel-toggle {
                    display: none !important;
                }
            `);
        },
        
        /**
         * Salva e ripristina lo stato dei pannelli
         */
        setupPanelStateRestoration: function() {
            const entitySidebar = document.querySelector('.entity-sidebar');
            const annotationsSidebar = document.querySelector('.annotations-sidebar');
            const textContainer = document.querySelector('.text-container');
            
            // Ripristina lo stato dei pannelli solo se non siamo in modalità clean
            if (!document.body.classList.contains('clean-mode')) {
                // Stato del pannello entità
                this.state.panelStates.entityCollapsed = localStorage.getItem('entity-panel-collapsed') === 'true';
                if (entitySidebar && this.state.panelStates.entityCollapsed) {
                    entitySidebar.classList.add('panel-collapsed');
                    if (textContainer) textContainer.classList.add('entity-panel-collapsed');
                }
                
                // Stato del pannello annotazioni
                this.state.panelStates.annotationsCollapsed = localStorage.getItem('annotations-panel-collapsed') === 'true';
                if (annotationsSidebar && this.state.panelStates.annotationsCollapsed) {
                    annotationsSidebar.classList.add('panel-collapsed');
                    if (textContainer) textContainer.classList.add('annotations-panel-collapsed');
                }
            }
        },

        /**
         * Aggiunge caratteristiche di accessibilità
         */
        addAccessibilityFeatures: function() {
            // Aggiungi attributi ARIA per migliorare l'accessibilità
            this.enhanceAriaAttributes();
        },
        
        /**
         * Aggiunge attributi ARIA per migliorare l'accessibilità
         */
        enhanceAriaAttributes: function() {
            // Aggiungi ruoli e attributi ARIA ai pannelli
            const entitySidebar = document.querySelector('.entity-sidebar');
            const annotationsSidebar = document.querySelector('.annotations-sidebar');
            const textContainer = document.querySelector('.text-container');
            
            if (entitySidebar) {
                entitySidebar.setAttribute('role', 'region');
                entitySidebar.setAttribute('aria-label', 'Tipi di entità');
            }
            
            if (annotationsSidebar) {
                annotationsSidebar.setAttribute('role', 'region');
                annotationsSidebar.setAttribute('aria-label', 'Lista annotazioni');
            }
            
            if (textContainer) {
                textContainer.setAttribute('role', 'main');
                textContainer.setAttribute('aria-label', 'Testo del documento');
            }
            
            // Aggiungi attributi ai pulsanti dell'interfaccia
            document.querySelectorAll('.btn').forEach(btn => {
                // Se non ha già un aria-label, usa il testo del pulsante
                if (!btn.hasAttribute('aria-label')) {
                    const text = btn.textContent.trim();
                    if (text) {
                        btn.setAttribute('aria-label', text);
                    }
                }
            });
        },

        /**
         * Configura il sistema di onboarding per nuovi utenti
         */
        setupUserOnboarding: function() {
            // Verifica se l'utente è nuovo (prima visita)
            const isNewUser = !localStorage.getItem('annotation-app-visited');
            
            if (isNewUser) {
                this.showOnboardingTour();
                localStorage.setItem('annotation-app-visited', 'true');
            }
            
            // Aggiungi pulsante di aiuto nella navbar
            this.addHelpButton();
        },
        
        /**
         * Mostra un tour di onboarding per nuovi utenti
         */
        showOnboardingTour: function() {
            // Crea il contenitore del tour
            const tourOverlay = document.createElement('div');
            tourOverlay.className = 'onboarding-overlay';
            
            // Crea il pannello del tour
            const tourPanel = document.createElement('div');
            tourPanel.className = 'onboarding-panel';
            tourPanel.innerHTML = `
                <div class="onboarding-header">
                    <h3>Benvenuto nell'Interfaccia di Annotazione</h3>
                    <button class="onboarding-close"><i class="fas fa-times"></i></button>
                </div>
                <div class="onboarding-content">
                    <p>Ti guideremo attraverso i passi fondamentali per iniziare ad annotare:</p>
                    
                    <div class="onboarding-step">
                        <span class="step-number">1</span>
                        <div class="step-content">
                            <h4>Seleziona un tipo di entità</h4>
                            <p>Nel pannello a sinistra, clicca su un tipo di entità per selezionarlo</p>
                        </div>
                    </div>
                    
                    <div class="onboarding-step">
                        <span class="step-number">2</span>
                        <div class="step-content">
                            <h4>Seleziona il testo</h4>
                            <p>Nel documento centrale, seleziona il testo che vuoi annotare</p>
                        </div>
                    </div>
                    
                    <div class="onboarding-step">
                        <span class="step-number">3</span>
                        <div class="step-content">
                            <h4>Gestisci le annotazioni</h4>
                            <p>Nel pannello a destra, puoi vedere e gestire tutte le tue annotazioni</p>
                        </div>
                    </div>
                </div>
                <div class="onboarding-footer">
                    <button class="btn btn-primary start-tour">Inizia il tour</button>
                    <button class="btn btn-outline-secondary skip-tour">Salta</button>
                </div>
            `;
            
            tourOverlay.appendChild(tourPanel);
            document.body.appendChild(tourOverlay);
            
            // Aggiungi gli stili necessari
            this.addStyles(`
                .onboarding-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0,0,0,0.5);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 9999;
                    backdrop-filter: blur(3px);
                }
                
                .onboarding-panel {
                    background: white;
                    border-radius: 0.5rem;
                    width: 90%;
                    max-width: 600px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                    overflow: hidden;
                }
                
                .onboarding-header {
                    padding: 1.25rem;
                    border-bottom: 1px solid #e5e7eb;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                }
                
                .onboarding-header h3 {
                    margin: 0;
                    font-size: 1.25rem;
                    color: #1f2937;
                }
                
                .onboarding-close {
                    background: none;
                    border: none;
                    font-size: 1.25rem;
                    color: #6b7280;
                    cursor: pointer;
                }
                
                .onboarding-content {
                    padding: 1.5rem;
                }
                
                .onboarding-step {
                    display: flex;
                    margin-bottom: 1.5rem;
                    align-items: flex-start;
                }
                
                .step-number {
                    width: 30px;
                    height: 30px;
                    background: #2563eb;
                    color: white;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    margin-right: 1rem;
                    flex-shrink: 0;
                }
                
                .step-content h4 {
                    margin: 0 0 0.5rem 0;
                    font-size: 1.1rem;
                    color: #1f2937;
                }
                
                .step-content p {
                    margin: 0;
                    color: #4b5563;
                }
                
                .onboarding-footer {
                    padding: 1.25rem;
                    border-top: 1px solid #e5e7eb;
                    display: flex;
                    justify-content: flex-end;
                    gap: 0.75rem;
                }
                
                .tooltip-step {
                    position: absolute;
                    background: white;
                    padding: 1rem;
                    border-radius: 0.5rem;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.15);
                    max-width: 300px;
                    z-index: 9999;
                }
                
                .tooltip-step::after {
                    content: '';
                    position: absolute;
                    width: 12px;
                    height: 12px;
                    background: white;
                    transform: rotate(45deg);
                }
                
                .tooltip-step.top::after {
                    bottom: -6px;
                    left: 50%;
                    margin-left: -6px;
                }
                
                .tooltip-step.bottom::after {
                    top: -6px;
                    left: 50%;
                    margin-left: -6px;
                }
                
                .tooltip-step.left::after {
                    right: -6px;
                    top: 50%;
                    margin-top: -6px;
                }
                
                .tooltip-step.right::after {
                    left: -6px;
                    top: 50%;
                    margin-top: -6px;
                }
                
                .tooltip-step-header {
                    font-weight: bold;
                    margin-bottom: 0.5rem;
                    color: #2563eb;
                }
                
                .tooltip-step-content {
                    margin-bottom: 1rem;
                }
                
                .tooltip-nav {
                    display: flex;
                    justify-content: space-between;
                }
                
                /* Stile per elementi evidenziati nel tour */
                .tour-highlight {
                    position: relative;
                    z-index: 9998;
                    box-shadow: 0 0 0 2000px rgba(0,0,0,0.4);
                    animation: pulse-highlight 2s infinite;
                }
                
                @keyframes pulse-highlight {
                    0% { box-shadow: 0 0 0 2000px rgba(0,0,0,0.4), 0 0 0 0 rgba(37, 99, 235, 0.4); }
                    70% { box-shadow: 0 0 0 2000px rgba(0,0,0,0.4), 0 0 0 10px rgba(37, 99, 235, 0); }
                    100% { box-shadow: 0 0 0 2000px rgba(0,0,0,0.4), 0 0 0 0 rgba(37, 99, 235, 0); }
                }
            `);
            
            // Aggiungi logica per il tour
            const closeOverlay = () => {
                document.body.removeChild(tourOverlay);
            };
            
            tourPanel.querySelector('.onboarding-close').addEventListener('click', closeOverlay);
            tourPanel.querySelector('.skip-tour').addEventListener('click', closeOverlay);
            
            // Aggiunge il tour interattivo
            tourPanel.querySelector('.start-tour').addEventListener('click', () => {
                closeOverlay();
                this.startInteractiveTour();
            });
        },
        
        /**
         * Avvia un tour interattivo dell'interfaccia
         */
        startInteractiveTour: function() {
            // Definisci i passi del tour
            const steps = [
                {
                    element: '.entity-sidebar',
                    title: 'Pannello Tipi di Entità',
                    content: 'Qui puoi selezionare il tipo di entità che vuoi annotare',
                    position: 'right'
                },
                {
                    element: '.entity-type:first-child',
                    title: 'Tipo di Entità',
                    content: 'Clicca su un tipo di entità per selezionarlo',
                    position: 'right'
                },
                {
                    element: '.text-container',
                    title: 'Testo del Documento',
                    content: 'Dopo aver selezionato un tipo, seleziona il testo qui per crearne un\'annotazione',
                    position: 'bottom'
                },
                {
                    element: '.annotations-sidebar',
                    title: 'Lista Annotazioni',
                    content: 'Qui puoi visualizzare e gestire tutte le tue annotazioni',
                    position: 'left'
                },
                {
                    element: '#auto-annotate',
                    title: 'Riconoscimento Automatico',
                    content: 'Questo pulsante utilizza l\'IA per riconoscere automaticamente le entità nel testo',
                    position: 'right'
                },
                {
                    element: '#clean-mode-toggle',
                    title: 'Modalità a Schermo Intero',
                    content: 'Questo pulsante attiva la modalità a schermo intero per un\'esperienza di annotazione più immersiva',
                    position: 'left'
                }
            ];
            
            let currentStep = 0;
            
            const showStep = (index) => {
                const step = steps[index];
                const element = document.querySelector(step.element);
                
                if (!element) {
                    console.warn(`Elemento ${step.element} non trovato, passo al passaggio successivo`);
                    if (index < steps.length - 1) {
                        showStep(index + 1);
                    } else {
                        endTour();
                    }
                    return;
                }
                
                // Mostra il tooltip
                const tooltip = document.createElement('div');
                tooltip.className = `tooltip-step ${step.position}`;
                tooltip.innerHTML = `
                    <div class="tooltip-step-header">${step.title}</div>
                    <div class="tooltip-step-content">${step.content}</div>
                    <div class="tooltip-nav">
                        ${index > 0 ? '<button class="btn btn-sm btn-outline-secondary prev-step">Indietro</button>' : '<div></div>'}
                        ${index < steps.length - 1 ? 
                          '<button class="btn btn-sm btn-primary next-step">Avanti</button>' : 
                          '<button class="btn btn-sm btn-success end-tour">Fine</button>'}
                    </div>
                `;
                
                document.body.appendChild(tooltip);
                
                // Posiziona il tooltip
                const rect = element.getBoundingClientRect();
                
                switch (step.position) {
                    case 'top':
                        tooltip.style.bottom = `${window.innerHeight - rect.top + 10}px`;
                        tooltip.style.left = `${rect.left + rect.width / 2 - tooltip.offsetWidth / 2}px`;
                        break;
                    case 'bottom':
                        tooltip.style.top = `${rect.bottom + 10}px`;
                        tooltip.style.left = `${rect.left + rect.width / 2 - tooltip.offsetWidth / 2}px`;
                        break;
                    case 'left':
                        tooltip.style.right = `${window.innerWidth - rect.left + 10}px`;
                        tooltip.style.top = `${rect.top + rect.height / 2 - tooltip.offsetHeight / 2}px`;
                        break;
                    case 'right':
                        tooltip.style.left = `${rect.right + 10}px`;
                        tooltip.style.top = `${rect.top + rect.height / 2 - tooltip.offsetHeight / 2}px`;
                        break;
                }
                
                // Evidenzia l'elemento
                element.classList.add('tour-highlight');
                
                // Aggiungi eventi
                if (tooltip.querySelector('.prev-step')) {
                    tooltip.querySelector('.prev-step').addEventListener('click', () => {
                        element.classList.remove('tour-highlight');
                        document.body.removeChild(tooltip);
                        showStep(index - 1);
                    });
                }
                
                if (tooltip.querySelector('.next-step')) {
                    tooltip.querySelector('.next-step').addEventListener('click', () => {
                        element.classList.remove('tour-highlight');
                        document.body.removeChild(tooltip);
                        showStep(index + 1);
                    });
                }
                
                if (tooltip.querySelector('.end-tour')) {
                    tooltip.querySelector('.end-tour').addEventListener('click', () => {
                        element.classList.remove('tour-highlight');
                        document.body.removeChild(tooltip);
                        endTour();
                    });
                }
            };
            
            const endTour = () => {
                // Mostra una notifica
                if (typeof NERGiuridico !== 'undefined' && typeof NERGiuridico.showNotification === 'function') {
                    NERGiuridico.showNotification('Tour completato! Ora puoi iniziare ad annotare.', 'success');
                }
                
                // Rimuovi eventuali stili di evidenziazione
                document.querySelectorAll('.tour-highlight').forEach(el => {
                    el.classList.remove('tour-highlight');
                });
            };
            
            // Avvia il tour
            showStep(currentStep);
        },

        /**
         * Aggiunge un pulsante di aiuto nella navbar
         */
        addHelpButton: function() {
            const navbar = document.querySelector('.navbar-nav');
            if (!navbar) return;
            
            const helpItem = document.createElement('li');
            helpItem.className = 'nav-item';
            helpItem.innerHTML = `
                <a class="nav-link" href="#" id="help-button">
                    <i class="fas fa-question-circle me-1"></i> Aiuto
                </a>
            `;
            
            navbar.appendChild(helpItem);
            
            // Aggiungi evento per mostrare il tour
            helpItem.querySelector('#help-button').addEventListener('click', (e) => {
                e.preventDefault();
                this.showOnboardingTour();
            });
        },

        /**
         * Aggiunge un pannello di scorciatoie da tastiera
         */
        addKeyboardShortcutsPanel: function() {
            // Trova il pannello esistente delle scorciatoie
            const existingShortcuts = document.querySelector('.keyboard-shortcuts');
            
            if (existingShortcuts) {
                // Migliora il pannello esistente
                existingShortcuts.classList.add('improved-shortcuts');
                
                // Aggiungi un pulsante di toggle
                const toggleBtn = document.createElement('button');
                toggleBtn.className = 'shortcuts-toggle btn btn-sm btn-outline-secondary';
                toggleBtn.innerHTML = '<i class="fas fa-keyboard me-1"></i> Mostra tutte le scorciatoie';
                
                // Aggiungi il pulsante al pannello esistente
                existingShortcuts.appendChild(toggleBtn);
                
                // Aggiungi le nuove scorciatoie
                const extraShortcuts = document.createElement('div');
                extraShortcuts.className = 'extra-shortcuts d-none';
                extraShortcuts.innerHTML = `
                    <hr>
                    <h6 class="mb-2">Scorciatoie avanzate</h6>
                    <ul class="list-unstyled small mb-0">
                        <li><kbd>Shift</kbd> + <kbd>↑</kbd>/<kbd>↓</kbd> Naviga tra le annotazioni</li>
                        <li><kbd>Ctrl</kbd> + <kbd>G</kbd> Vai alla riga</li>
                        <li><kbd>Ctrl</kbd> + <kbd>Z</kbd> Annulla ultima annotazione</li>
                        <li><kbd>/</kbd> Cerca nelle annotazioni</li>
                    </ul>
                `;
                
                existingShortcuts.appendChild(extraShortcuts);
                
                // Aggiungi l'evento per mostrare/nascondere le scorciatoie extra
                toggleBtn.addEventListener('click', function() {
                    extraShortcuts.classList.toggle('d-none');
                    this.innerHTML = extraShortcuts.classList.contains('d-none') ? 
                        '<i class="fas fa-keyboard me-1"></i> Mostra tutte le scorciatoie' : 
                        '<i class="fas fa-keyboard me-1"></i> Nascondi scorciatoie';
                });
                
                // Aggiungi stili migliorati per le scorciatoie
                this.addStyles(`
                    .improved-shortcuts {
                        background: white;
                        border-radius: 0.5rem;
                        padding: 1rem !important;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                        transition: all 0.3s ease;
                    }
                    
                    .improved-shortcuts:hover {
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }
                    
                    .improved-shortcuts kbd {
                        background: #f3f4f6;
                        border: 1px solid #d1d5db;
                        border-radius: 3px;
                        box-shadow: 0 1px 0 rgba(0,0,0,0.1);
                        padding: 2px 4px;
                        font-size: 0.85em;
                        font-family: monospace;
                        margin: 0 2px;
                    }
                    
                    .improved-shortcuts li {
                        margin-bottom: 0.5rem;
                    }
                    
                    .shortcuts-toggle {
                        margin-top: 0.75rem;
                        width: 100%;
                    }
                `);
                
                // Sistema operativo specifico testi per scorciatoie
                const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
                if (!isMac) {
                    extraShortcuts.innerHTML = extraShortcuts.innerHTML.replace(/Ctrl/g, 'Ctrl');
                }
            }
        },

        /**
         * Migliora la navigazione tra le schede
         */
        improveTabNavigation: function() {
            // Aggiungi navigazione via tastiera tra le schede
            document.addEventListener('keydown', function(e) {
                // Shift+Tab per navigare tra i pannelli (Left, Center, Right)
                if (e.shiftKey && e.key === 'Tab') {
                    e.preventDefault();
                    
                    const entitySidebar = document.querySelector('.entity-sidebar');
                    const textContainer = document.querySelector('.text-container');
                    const annotationsSidebar = document.querySelector('.annotations-sidebar');
                    
                    if (document.activeElement.closest('.entity-sidebar')) {
                        // Vai alla sidebar delle annotazioni
                        if (annotationsSidebar) {
                            const firstFocusable = annotationsSidebar.querySelector('button, [tabindex="0"]');
                            if (firstFocusable) firstFocusable.focus();
                        }
                    } else if (document.activeElement.closest('.annotations-sidebar')) {
                        // Vai al container di testo
                        if (textContainer) textContainer.focus();
                    } else {
                        // Vai alla sidebar delle entità
                        if (entitySidebar) {
                            const firstFocusable = entitySidebar.querySelector('button, [tabindex="0"]');
                            if (firstFocusable) firstFocusable.focus();
                        }
                    }
                }
            });
            
            // Aggiungi struttura di navigazione per migliorare l'usabilità
            this.addStyles(`
                /* Migliora lo stile degli elementi attivi */
                .entity-sidebar:focus-within,
                .annotations-sidebar:focus-within,
                .text-container:focus-within {
                    outline: none;
                    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.4);
                }
                
                /* Stile per evidenziare la tab attiva */
                .active-tab {
                    border-bottom: 3px solid #2563eb !important;
                }
            `);
        },

        /**
         * Aggiunge supporto per design responsive
         * Compatibile con i miglioramenti CSS
         */
        addResponsiveDesignSupport: function() {
            // Aggiungi navegazione a tabs per mobile
            const annotationArea = document.querySelector('.annotation-area');
            if (annotationArea) {
                const entitySidebar = document.querySelector('.entity-sidebar');
                const annotationsSidebar = document.querySelector('.annotations-sidebar');
                
                // Crea il container delle tabs
                const tabsContainer = document.createElement('div');
                tabsContainer.className = 'mobile-tabs d-none d-md-none'; // Nascosto di default, verrà mostrato su mobile
                
                // Crea le tabs
                tabsContainer.innerHTML = `
                    <div class="mobile-tab active-tab" data-target="entity-sidebar">
                        <i class="fas fa-tags me-1"></i>Tipi
                    </div>
                    <div class="mobile-tab" data-target="annotations-sidebar">
                        <i class="fas fa-list-ul me-1"></i>Annotazioni
                    </div>
                `;
                
                // Inserisci prima dell'area di annotazione
                annotationArea.parentNode.insertBefore(tabsContainer, annotationArea);
                
                // Gestisci la navigazione a tabs
                tabsContainer.querySelectorAll('.mobile-tab').forEach(tab => {
                    tab.addEventListener('click', function() {
                        // Aggiorna lo stato delle tabs
                        tabsContainer.querySelectorAll('.mobile-tab').forEach(t => {
                            t.classList.remove('active-tab');
                        });
                        this.classList.add('active-tab');
                        
                        // Mostra/nascondi i pannelli
                        const targetPanel = this.dataset.target;
                        if (targetPanel === 'entity-sidebar') {
                            entitySidebar.classList.remove('tab-hidden');
                            annotationsSidebar.classList.add('tab-hidden');
                        } else {
                            entitySidebar.classList.add('tab-hidden');
                            annotationsSidebar.classList.remove('tab-hidden');
                        }
                    });
                });
                
                // Aggiungi media query listener per mostrare/nascondere le tabs
                const checkScreenSize = () => {
                    if (window.innerWidth <= 1024) {
                        tabsContainer.classList.remove('d-none', 'd-md-none');
                        
                        // All'inizio su mobile, mostra solo il pannello attivo
                        const activeTab = tabsContainer.querySelector('.active-tab');
                        if (activeTab) {
                            const targetPanel = activeTab.dataset.target;
                            if (targetPanel === 'entity-sidebar') {
                                entitySidebar.classList.remove('tab-hidden');
                                annotationsSidebar.classList.add('tab-hidden');
                            } else {
                                entitySidebar.classList.add('tab-hidden');
                                annotationsSidebar.classList.remove('tab-hidden');
                            }
                        }
                    } else {
                        tabsContainer.classList.add('d-none', 'd-md-none');
                        entitySidebar.classList.remove('tab-hidden');
                        annotationsSidebar.classList.remove('tab-hidden');
                    }
                };
                
                // Controlla subito e aggiungi listener per resize
                checkScreenSize();
                window.addEventListener('resize', checkScreenSize);
                
                // Aggiungi stili responsivi
                this.addStyles(`
                    /* Layout a tabs per mobile */
                    .mobile-tabs {
                        display: flex !important;
                        background: white;
                        border-radius: 0.5rem;
                        margin-bottom: 1rem;
                        overflow: hidden;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    }
                    
                    .mobile-tab {
                        flex: 1;
                        text-align: center;
                        padding: 0.75rem;
                        cursor: pointer;
                        border-bottom: 3px solid transparent;
                        font-weight: 500;
                        transition: all 0.2s ease;
                    }
                    
                    .mobile-tab.active-tab {
                        background-color: #f9fafb;
                        border-bottom-color: #2563eb;
                    }
                    
                    .mobile-tab:hover {
                        background-color: #f3f4f6;
                    }
                    
                    /* Nascondi il pannello non attivo */
                    .entity-sidebar.tab-hidden,
                    .annotations-sidebar.tab-hidden {
                        display: none !important;
                    }
                    
                    /* Tablet e dispositivi più piccoli */
                    @media (max-width: 1024px) {
                        .annotation-area {
                            flex-wrap: wrap;
                        }
                        
                        .entity-sidebar, 
                        .annotations-sidebar {
                            width: 100% !important;
                            order: 2;
                            max-height: 300px !important;
                            overflow-y: auto !important;
                        }
                        
                        .text-container {
                            width: 100% !important;
                            order: 1;
                            margin: 0 0 1rem 0 !important;
                        }
                        
                        body:not(.clean-mode) .panel-toggle {
                            display: none !important;
                        }
                    }
                    
                    /* Mobile */
                    @media (max-width: 640px) {
                        .document-info h2 {
                            font-size: 1.25rem !important;
                        }
                        
                        .text-container {
                            font-size: 0.9rem !important;
                            padding: 1rem !important;
                        }
                        
                        .entity-type {
                            padding: 0.5rem !important;
                        }
                        
                        /* Semplifico l'interfaccia su mobile */
                        .keyboard-shortcuts,
                        .annotation-stats {
                            display: none !important;
                        }
                        
                        /* Minore padding su mobile */
                        .annotation-progress-container {
                            padding: 0.5rem !important;
                        }
                    }
                `);
            }
        },

        /**
         * Migliora la visibilità delle annotazioni
         * Compatibile con i miglioramenti CSS per le entità
         */
        enhanceAnnotationVisibility: function() {
            // Non aggiungiamo stili duplicati per gli highlight,
            // poiché sono già definiti nelle correzioni proposte
            
            // Aggiungi interazione tra la lista e le annotazioni
            this.setupAnnotationInteractions();
        },
        
        /**
         * Configura interazioni avanzate tra le annotazioni
         * Compatibile con le nuove funzioni del gestore annotazioni
         */
        setupAnnotationInteractions: function() {
            // Aggiungi un listener delegato per gestire clic su annotazioni
            document.addEventListener('click', function(e) {
                // Quando si clicca su un'annotazione evidenziata nel testo
                const highlight = e.target.closest('.entity-highlight');
                if (highlight) {
                    const annotationId = highlight.dataset.id;
                    if (!annotationId) return;
                    
                    // Rimuovi la classe focused da tutte le altre annotazioni
                    document.querySelectorAll('.entity-highlight.focused').forEach(el => {
                        if (el !== highlight) el.classList.remove('focused');
                    });
                    
                    // Aggiungi la classe focused a questa annotazione
                    highlight.classList.add('focused');
                    
                    // Trova l'elemento corrispondente nella lista e attivalo
                    const annotationItem = document.querySelector(`.annotation-item[data-id="${annotationId}"]`);
                    if (annotationItem) {
                        // Rimuovi active da tutte le altre annotazioni
                        document.querySelectorAll('.annotation-item.active').forEach(el => {
                            el.classList.remove('active', 'selected');
                        });
                        
                        // Aggiungi active a questa annotazione
                        annotationItem.classList.add('active', 'selected');
                        
                        // Scorri alla annotazione nella lista
                        annotationItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                    
                    // Se esiste AnnotationManager, aggiorna lo stato
                    if (typeof AnnotationManager !== 'undefined') {
                        AnnotationManager.state.highlightedAnnotationId = annotationId;
                        AnnotationManager.state.selectedAnnotationId = annotationId;
                    }
                }
                
                // Quando si clicca su un'annotazione nella lista
                const annotationItem = e.target.closest('.annotation-item');
                if (annotationItem && !e.target.closest('button')) {
                    const annotationId = annotationItem.dataset.id;
                    if (!annotationId) return;
                    
                    // Rimuovi active da tutte le altre annotazioni
                    document.querySelectorAll('.annotation-item.active, .annotation-item.selected').forEach(el => {
                        if (el !== annotationItem) el.classList.remove('active', 'selected');
                    });
                    
                    // Aggiungi active a questa annotazione
                    annotationItem.classList.add('active', 'selected');
                    
                    // Se abbiamo la funzione jumpToAnnotation, la utilizziamo
                    if (typeof window.jumpToAnnotation === 'function') {
                        window.jumpToAnnotation(annotationId);
                    } else {
                        // Altrimenti, facciamo il nostro best effort
                        const highlight = document.querySelector(`.entity-highlight[data-id="${annotationId}"]`);
                        if (highlight) {
                            // Rimuovi focused da tutte le altre annotazioni
                            document.querySelectorAll('.entity-highlight.focused').forEach(el => {
                                if (el !== highlight) el.classList.remove('focused');
                            });
                            
                            // Aggiungi focused a questa annotazione
                            highlight.classList.add('focused');
                            
                            // Scorri all'annotazione nel testo
                            highlight.scrollIntoView({ behavior: 'smooth', block: 'center' });
                        }
                    }
                    
                    // Se esiste AnnotationManager, aggiorna lo stato
                    if (typeof AnnotationManager !== 'undefined') {
                        AnnotationManager.state.selectedAnnotationId = annotationId;
                        AnnotationManager.state.highlightedAnnotationId = annotationId;
                    }
                }
            });
            
            // Supporto per le scorciatoie da tastiera di navigazione
            document.addEventListener('keydown', function(e) {
                // Shift + frecce per navigare tra le annotazioni
                if (e.shiftKey && (e.key === 'ArrowUp' || e.key === 'ArrowDown')) {
                    e.preventDefault();
                    
                    const annotationItems = Array.from(document.querySelectorAll('.annotation-item:not(.d-none)'));
                    if (annotationItems.length === 0) return;
                    
                    // Trova l'indice corrente
                    let currentIndex = -1;
                    const selectedItem = document.querySelector('.annotation-item.selected');
                    
                    if (selectedItem) {
                        currentIndex = annotationItems.indexOf(selectedItem);
                    }
                    
                    // Calcola il nuovo indice
                    let newIndex;
                    if (e.key === 'ArrowUp') {
                        newIndex = currentIndex <= 0 ? annotationItems.length - 1 : currentIndex - 1;
                    } else {
                        newIndex = currentIndex === annotationItems.length - 1 || currentIndex === -1 ? 0 : currentIndex + 1;
                    }
                    
                    // Attiva la nuova annotazione
                    const newItem = annotationItems[newIndex];
                    if (newItem) {
                        // Simula un click sulla nuova annotazione
                        newItem.click();
                    }
                }
            });
        },

        /**
         * Aggiunge stili CSS all'head del documento
         * @param {string} css - CSS da aggiungere
         */
        addStyles: function(css) {
            if (!this.styleSheet) {
                this.styleSheet = document.createElement('style');
                this.styleSheet.id = 'ui-enhancements-styles';
                document.head.appendChild(this.styleSheet);
            }
            
            this.styleSheet.textContent += css;
        }
    };

    // Inizializza i miglioramenti UI dopo un breve ritardo per assicurare
    // che AnnotationManager e altre dipendenze siano completamente caricate
    setTimeout(function() {
        UIEnhancer.init();
    }, 50);
});