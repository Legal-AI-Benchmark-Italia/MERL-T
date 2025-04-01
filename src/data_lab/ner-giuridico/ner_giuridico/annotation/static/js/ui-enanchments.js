/**
 * ui-enhancements.js - Miglioramenti dell'interfaccia utente per l'applicazione di annotazione
 * Questo script aggiunge miglioramenti significativi all'esperienza utente dell'interfaccia di annotazione
 */

document.addEventListener('DOMContentLoaded', function() {
    const UIEnhancer = {
        /**
         * Inizializza tutti i miglioramenti dell'interfaccia utente
         */
        init: function() {
            console.info("✨ Inizializzazione miglioramenti UI");
            this.addProgressIndicator();
            this.enhancePanelVisibility();
            this.addAccessibilityFeatures();
            this.setupUserOnboarding();
            this.addKeyboardShortcutsPanel();
            this.improveTabNavigation();
            this.addResponsiveDesignSupport();
            this.enhanceAnnotationVisibility();
        },

        /**
         * Aggiunge un indicatore di progresso persistente
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

                // Aggiungi gli stili necessari
                this.addStyles(`
                    .annotation-progress-container {
                        margin-bottom: 1rem;
                        padding: 0.75rem;
                        background: white;
                        border-radius: 0.5rem;
                        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                        display: flex;
                        align-items: center;
                        flex-wrap: wrap;
                        gap: 0.75rem;
                    }
                    
                    .annotation-progress-bar {
                        flex: 1;
                        height: 0.75rem;
                        background: #f0f0f0;
                        border-radius: 1rem;
                        overflow: hidden;
                        position: relative;
                    }
                    
                    .annotation-progress-fill {
                        height: 100%;
                        background: linear-gradient(90deg, #2563eb, #4f46e5);
                        width: 0%;
                        transition: width 0.5s ease;
                        border-radius: 1rem;
                    }
                    
                    .annotation-progress-stats {
                        display: flex;
                        gap: 1rem;
                        font-weight: 500;
                        color: #4b5563;
                    }
                    
                    #annotation-progress-percentage {
                        color: #2563eb;
                        font-weight: 700;
                    }
                `);

                // Implementa la funzione di aggiornamento del progresso
                window.updateGlobalProgressIndicator = function() {
                    const totalWords = parseInt(document.getElementById('text-content').dataset.wordCount) || 100;
                    const annotationCount = document.querySelectorAll('.annotation-item').length;
                    
                    // Calcola una stima della copertura
                    const coverage = Math.min(annotationCount / (totalWords / 15) * 100, 100);
                    
                    // Aggiorna la barra di progresso e le statistiche
                    document.getElementById('global-annotation-progress').style.width = `${coverage}%`;
                    document.getElementById('annotation-progress-percentage').textContent = `${Math.round(coverage)}%`;
                    document.getElementById('annotation-progress-count').textContent = 
                        `${annotationCount} ${annotationCount === 1 ? 'annotazione' : 'annotazioni'}`;
                    
                    // Aggiorna anche la classe nel body per lo stato di completamento
                    if (coverage >= 70) {
                        document.body.classList.add('high-completion');
                    } else if (coverage >= 30) {
                        document.body.classList.add('medium-completion');
                        document.body.classList.remove('high-completion');
                    } else {
                        document.body.classList.remove('medium-completion', 'high-completion');
                    }
                };

                // Hook per aggiornare l'indicatore quando vengono aggiornate le annotazioni
                const originalUpdateAnnotationCount = window.updateAnnotationCount;
                if (originalUpdateAnnotationCount) {
                    window.updateAnnotationCount = function() {
                        originalUpdateAnnotationCount.apply(this, arguments);
                        window.updateGlobalProgressIndicator();
                    };
                }

                // Esegui subito l'aggiornamento iniziale
                setTimeout(window.updateGlobalProgressIndicator, 500);
            }
        },

        /**
         * Migliora la visibilità e l'accessibilità dei pannelli
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
                
                // Aggiungi indicatori visivi per pannelli
                this.addStyles(`
                    .entity-sidebar, .annotations-sidebar {
                        position: relative;
                        transition: all 0.3s ease;
                        min-width: 280px;
                    }
                    
                    .entity-sidebar::before, .annotations-sidebar::before {
                        content: '';
                        position: absolute;
                        top: 0;
                        height: 100%;
                        width: 3px;
                        background: linear-gradient(to bottom, #2563eb, #4f46e5);
                        opacity: 0.7;
                    }
                    
                    .entity-sidebar::before {
                        left: 0;
                        border-radius: 3px 0 0 3px;
                    }
                    
                    .annotations-sidebar::before {
                        right: 0;
                        border-radius: 0 3px 3px 0;
                    }
                    
                    .panel-header {
                        display: flex;
                        align-items: center;
                        padding: 0.75rem 0;
                        margin-bottom: 1rem;
                        border-bottom: 2px solid #e5e7eb;
                    }
                    
                    .panel-header i {
                        font-size: 1.25rem;
                        margin-right: 0.5rem;
                        color: #2563eb;
                    }
                    
                    .panel-header h5 {
                        margin: 0;
                        font-weight: 600;
                        color: #1f2937;
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
                    
                    .panel-toggle i {
                        font-size: 0.8rem;
                        color: #4b5563;
                    }
                    
                    /* Quando il pannello è aperto, cambia l'icona */
                    .panel-collapsed .panel-toggle i.fa-chevron-left:before {
                        content: "\\f054"; /* fa-chevron-right */
                    }
                    
                    .panel-collapsed .panel-toggle i.fa-chevron-right:before {
                        content: "\\f053"; /* fa-chevron-left */
                    }
                `);
            }
            
            // Salva e ripristina lo stato dei pannelli
            this.setupPanelStateRestoration();
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
                
                toggleBtn.addEventListener('click', function() {
                    entitySidebar.classList.toggle('panel-collapsed');
                    // Aggiorna la classe di text-container per dare più spazio
                    if (textContainer) {
                        textContainer.classList.toggle('entity-panel-collapsed');
                    }
                    // Salva lo stato
                    localStorage.setItem('entity-panel-collapsed', 
                                        entitySidebar.classList.contains('panel-collapsed'));
                });
            }
            
            if (annotationsSidebar) {
                const toggleBtn = document.createElement('div');
                toggleBtn.className = 'panel-toggle annotations-panel-toggle';
                toggleBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
                toggleBtn.title = 'Espandi/Contrai pannello';
                annotationsSidebar.appendChild(toggleBtn);
                
                toggleBtn.addEventListener('click', function() {
                    annotationsSidebar.classList.toggle('panel-collapsed');
                    // Aggiorna la classe di text-container per dare più spazio
                    if (textContainer) {
                        textContainer.classList.toggle('annotations-panel-collapsed');
                    }
                    // Salva lo stato
                    localStorage.setItem('annotations-panel-collapsed', 
                                        annotationsSidebar.classList.contains('panel-collapsed'));
                });
            }
            
            // Aggiungi stili per l'espansione del contenuto
            this.addStyles(`
                .text-container {
                    transition: all 0.3s ease;
                }
                
                .text-container.entity-panel-collapsed {
                    margin-left: 50px !important;
                }
                
                .text-container.annotations-panel-collapsed {
                    margin-right: 50px !important;
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
            
            // Ripristina lo stato dei pannelli
            if (entitySidebar && localStorage.getItem('entity-panel-collapsed') === 'true') {
                entitySidebar.classList.add('panel-collapsed');
                if (textContainer) textContainer.classList.add('entity-panel-collapsed');
            }
            
            if (annotationsSidebar && localStorage.getItem('annotations-panel-collapsed') === 'true') {
                annotationsSidebar.classList.add('panel-collapsed');
                if (textContainer) textContainer.classList.add('annotations-panel-collapsed');
            }
        },

        /**
         * Aggiunge caratteristiche di accessibilità
         */
        addAccessibilityFeatures: function() {
            // Migliora il contrasto delle etichette
            this.addStyles(`
                .entity-highlight {
                    text-shadow: 0 0 3px rgba(0,0,0,0.5) !important;
                    font-weight: 500 !important;
                }
                
                .entity-type, .annotation-type {
                    text-shadow: 0 0 2px rgba(0,0,0,0.3);
                }
                
                /* Migliora la leggibilità delle annotazioni selezionate */
                .entity-highlight:focus, 
                .entity-highlight.focused {
                    outline: 2px solid #2563eb !important;
                    outline-offset: 2px !important;
                }
                
                /* Migliora il focus sulla lista delle annotazioni */
                .annotation-item:focus-within,
                .annotation-item.focused {
                    box-shadow: 0 0 0 2px #2563eb !important;
                }
                
                /* Aumenta la dimensione di clic per i piccoli bottoni */
                .btn-sm {
                    min-height: 38px;
                    min-width: 38px;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                }
            `);
            
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
                if (window.showNotification) {
                    window.showNotification('Tour completato! Ora puoi iniziare ad annotare.', 'success');
                }
                
                // Rimuovi eventuali stili di evidenziazione
                document.querySelectorAll('.tour-highlight').forEach(el => {
                    el.classList.remove('tour-highlight');
                });
            };
            
            // Aggiungi stili per il tour
            this.addStyles(`
                .tour-highlight {
                    position: relative;
                    z-index: 9998;
                    box-shadow: 0 0 0 2000px rgba(0,0,0,0.4) !important;
                    animation: pulse-highlight 2s infinite;
                }
                
                @keyframes pulse-highlight {
                    0% { box-shadow: 0 0 0 2000px rgba(0,0,0,0.4), 0 0 0 0 rgba(37, 99, 235, 0.4); }
                    70% { box-shadow: 0 0 0 2000px rgba(0,0,0,0.4), 0 0 0 10px rgba(37, 99, 235, 0); }
                    100% { box-shadow: 0 0 0 2000px rgba(0,0,0,0.4), 0 0 0 0 rgba(37, 99, 235, 0); }
                }
            `);
            
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
                        <li><kbd>Ctrl</kbd> + <kbd>D</kbd> Duplica l'annotazione selezionata</li>
                        <li><kbd>Ctrl</kbd> + <kbd>F</kbd> Cerca nel testo</li>
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
         */
        addResponsiveDesignSupport: function() {
            // Aggiungi media queries per migliorare l'esperienza su dispositivi diversi
            this.addStyles(`
                /* Tablet e dispositivi più piccoli */
                @media (max-width: 1024px) {
                    .annotation-area {
                        flex-wrap: wrap;
                    }
                    
                    .entity-sidebar, .annotations-sidebar {
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
                    
                    .panel-toggle {
                        display: none !important;
                    }
                    
                    /* Layout a tabs per mobile */
                    .mobile-tabs {
                        display: flex !important;
                        background: white;
                        border-radius: 0.5rem;
                        margin-bottom: 1rem;
                        overflow: hidden;
                    }
                    
                    .mobile-tab {
                        flex: 1;
                        text-align: center;
                        padding: 0.75rem;
                        cursor: pointer;
                        border-bottom: 3px solid transparent;
                        font-weight: 500;
                    }
                    
                    /* Nascondi il pannello non attivo */
                    .entity-sidebar.tab-hidden,
                    .annotations-sidebar.tab-hidden {
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
                    }
                    
                    .entity-type {
                        padding: 0.5rem !important;
                    }
                    
                    /* Semplifico l'interfaccia su mobile */
                    .keyboard-shortcuts,
                    .annotation-stats {
                        display: none !important;
                    }
                }
            `);
            
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
            }
        },

        /**
         * Migliora la visibilità delle annotazioni
         */
        enhanceAnnotationVisibility: function() {
            // Aggiungi styles per migliorare la leggibilità delle annotazioni
            this.addStyles(`
                /* Effetto hover migliorato per le annotazioni */
                .entity-highlight {
                    position: relative;
                    border-radius: 2px;
                    transition: all 0.2s ease;
                }
                
                .entity-highlight:hover {
                    z-index: 10;
                    transform: translateY(-2px) !important;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.2) !important;
                }
                
                /* Miglioramento popup tooltips */
                .entity-highlight .tooltip {
                    min-width: 150px;
                    max-width: 300px;
                    border-radius: 4px;
                    font-size: 0.8rem !important;
                    box-shadow: 0 3px 10px rgba(0,0,0,0.2);
                    z-index: 100;
                    padding: 4px 8px !important;
                    pointer-events: none;
                }
                
                /* Miglioramento della lista di annotazioni */
                .annotation-item {
                    transition: all 0.3s ease;
                    border-left: 3px solid transparent;
                }
                
                .annotation-item:hover {
                    transform: translateX(4px);
                }
                
                /* Evidenziazione dell'annotazione attiva */
                .annotation-item.active {
                    background-color: #f3f4f6;
                    border-left-color: #2563eb;
                }
                
                /* Effetto focus quando si clicca su un'annotazione nella lista */
                .entity-highlight.focused {
                    outline: 2px solid #2563eb !important;
                    outline-offset: 2px !important;
                }
            `);
            
            // Aggiungi interazione tra la lista e le annotazioni
            this.setupAnnotationInteractions();
        },
        
        /**
         * Configura interazioni avanzate tra le annotazioni
         */
        setupAnnotationInteractions: function() {
            // Aggiungi un listener delegato per gestire clic su annotazioni
            document.addEventListener('click', function(e) {
                // Quando si clicca su un'annotazione evidenziata nel testo
                if (e.target.closest('.entity-highlight')) {
                    const highlight = e.target.closest('.entity-highlight');
                    const annotationId = highlight.dataset.id;
                    
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
                            el.classList.remove('active');
                        });
                        
                        // Aggiungi active a questa annotazione
                        annotationItem.classList.add('active');
                        
                        // Scorri alla annotazione nella lista
                        annotationItem.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                }
                
                // Quando si clicca su un'annotazione nella lista
                if (e.target.closest('.annotation-item')) {
                    const annotationItem = e.target.closest('.annotation-item');
                    const annotationId = annotationItem.dataset.id;
                    
                    // Se non è stato cliccato su un pulsante interno
                    if (!e.target.closest('button')) {
                        // Rimuovi active da tutte le altre annotazioni
                        document.querySelectorAll('.annotation-item.active').forEach(el => {
                            if (el !== annotationItem) el.classList.remove('active');
                        });
                        
                        // Aggiungi active a questa annotazione
                        annotationItem.classList.add('active');
                        
                        // Trova l'elemento corrispondente nel testo e focalizzalo
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

    // Inizializza i miglioramenti UI
    UIEnhancer.init();
});