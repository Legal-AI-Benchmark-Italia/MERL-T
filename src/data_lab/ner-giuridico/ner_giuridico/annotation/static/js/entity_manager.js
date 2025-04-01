/**
 * entity_manager.js - Script migliorato per la gestione dei tipi di entità
 * 
 * Questo script gestisce l'interfaccia utente per la creazione, modifica ed eliminazione
 * dei tipi di entità utilizzati nel sistema NER-Giuridico.
 *
 * @version 2.0.0
 * @author NER-Giuridico Team
 */

// Entity Type Manager
const EntityManager = {
    // Stato dell'applicazione
    state: {
        entityTypes: [],
        selectedEntityType: null,
        isLoading: true,
        pendingOperations: 0,
        filterText: '',
        filterCategory: '',
        isEditMode: false,
        entityToDelete: null
    },
    
    // Elementi DOM
    elements: {},
    
    /**
     * Inizializza il gestore dei tipi di entità
     */
    init: function() {
        console.info('🔖 Inizializzazione Entity Manager...');
        
        // Seleziona gli elementi DOM principali
        this.elements = {
            entityTypesTable: document.getElementById('entity-types-table'),
            entityTypeForm: document.getElementById('entity-type-form'),
            entityTypeFormContainer: document.getElementById('entity-type-form-container'),
            formTitle: document.getElementById('form-title'),
            addEntityTypeBtn: document.getElementById('add-entity-type-btn'),
            addFirstEntityBtn: document.getElementById('add-first-entity'),
            cancelBtn: document.getElementById('cancel-btn'),
            closeFormBtn: document.getElementById('close-form-btn'),
            saveBtn: document.getElementById('save-btn'),
            editMode: document.getElementById('edit-mode'),
            originalName: document.getElementById('original-name'),
            nameInput: document.getElementById('entity-name'),
            displayNameInput: document.getElementById('display-name'),
            categorySelect: document.getElementById('category'),
            colorInput: document.getElementById('color'),
            colorPreview: document.getElementById('color-preview'),
            colorSample: document.getElementById('color-sample'),
            metadataSchemaInput: document.getElementById('metadata-schema'),
            patternsInput: document.getElementById('patterns'),
            testPatternsBtn: document.getElementById('test-patterns-btn'),
            testText: document.getElementById('test-text'),
            testResults: document.getElementById('test-results'),
            testOutput: document.getElementById('test-output'),
            confirmDeleteBtn: document.getElementById('confirm-delete-btn'),
            confirmCancelBtn: document.getElementById('confirm-cancel-btn'),
            loadingIndicator: document.getElementById('loading-indicator'),
            emptyState: document.getElementById('empty-state'),
            entitySearch: document.getElementById('entity-search'),
            categoryFilter: document.getElementById('category-filter')
        };
        
        // Configura gli event handlers
        this.setupEventHandlers();
        
        // Carica i tipi di entità
        this.loadEntityTypes();
        
        console.info('🔖 Entity Manager inizializzato');
    },
    
    /**
     * Configura tutti gli event handlers
     */
    setupEventHandlers: function() {
        // Pulsanti per mostrare il form di creazione
        if (this.elements.addEntityTypeBtn) {
            this.elements.addEntityTypeBtn.addEventListener('click', () => this.showCreateForm());
        }
        
        if (this.elements.addFirstEntityBtn) {
            this.elements.addFirstEntityBtn.addEventListener('click', () => this.showCreateForm());
        }
        
        // Pulsanti per nascondere il form
        if (this.elements.cancelBtn) {
            this.elements.cancelBtn.addEventListener('click', () => this.hideForm());
        }
        
        if (this.elements.closeFormBtn) {
            this.elements.closeFormBtn.addEventListener('click', () => this.hideForm());
        }
        
        // Gestione del form
        if (this.elements.entityTypeForm) {
            this.elements.entityTypeForm.addEventListener('submit', e => this.handleFormSubmit(e));
        }
        
        // Preview del colore
        if (this.elements.colorInput) {
            this.elements.colorInput.addEventListener('input', () => this.updateColorPreview());
        }
        
        // Conferma eliminazione
        if (this.elements.confirmDeleteBtn) {
            this.elements.confirmDeleteBtn.addEventListener('click', () => this.confirmDelete());
        }
        
        if (this.elements.confirmCancelBtn) {
            this.elements.confirmCancelBtn.addEventListener('click', () => this.hideConfirmationDialog());
        }
        
        // Ricerca e filtro
        if (this.elements.entitySearch) {
            const debouncedSearch = NERGiuridico.debounce(() => this.filterEntityTypes(), 300);
            this.elements.entitySearch.addEventListener('input', debouncedSearch);
        }
        
        if (this.elements.categoryFilter) {
            this.elements.categoryFilter.addEventListener('change', () => this.filterEntityTypes());
        }
        
        // Test dei pattern
        if (this.elements.testPatternsBtn) {
            this.elements.testPatternsBtn.addEventListener('click', () => this.testPatterns());
        }
        
        // Validazione in tempo reale
        if (this.elements.nameInput) {
            this.elements.nameInput.addEventListener('input', () => this.validateEntityName());
        }
        
        if (this.elements.metadataSchemaInput) {
            this.elements.metadataSchemaInput.addEventListener('input', () => this.validateMetadataSchema());
        }
        
        if (this.elements.patternsInput) {
            this.elements.patternsInput.addEventListener('input', () => this.validatePatterns());
        }
        
        // Gestione dei tasti di scelta rapida
        document.addEventListener('keydown', e => {
            // Escape per chiudere il form o la finestra di conferma
            if (e.key === 'Escape') {
                const confirmationModal = bootstrap.Modal.getInstance(document.getElementById('confirmation-dialog'));
                if (confirmationModal) {
                    confirmationModal.hide();
                } else if (!this.elements.entityTypeFormContainer.classList.contains('d-none')) {
                    this.hideForm();
                }
            }
        });
        
        // Gestione del cambiamento della categoria
        if (this.elements.categorySelect) {
            this.elements.categorySelect.addEventListener('change', function() {
                // Salva la categoria originale quando si carica l'entità
                if (!this.dataset.originalCategory && EntityManager.state.isEditMode) {
                    this.dataset.originalCategory = this.value;
                }
                
                // Evidenzia visivamente il cambio di categoria
                if (EntityManager.state.isEditMode && this.value !== this.dataset.originalCategory) {
                    this.classList.add('border-warning', 'bg-warning', 'bg-opacity-10');
                } else {
                    this.classList.remove('border-warning', 'bg-warning', 'bg-opacity-10');
                }
            });
        }
    },
    
    /**
     * Carica i tipi di entità dal server
     */
    loadEntityTypes: function() {
        this.setLoading(true);
        
        fetch('/api/entity_types')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Errore HTTP: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Verifica che i dati siano nel formato atteso
                if (data && data.status === 'success' && Array.isArray(data.entity_types)) {
                    this.state.entityTypes = data.entity_types;
                    window.allEntities = data.entity_types; // Per compatibilità
                } else {
                    console.error('Formato risposta non valido:', data);
                    this.state.entityTypes = [];
                    window.allEntities = [];
                    NERGiuridico.showNotification('Errore nel formato dei dati ricevuti', 'danger');
                }
                
                this.renderEntityTypes(this.state.entityTypes);
            })
            .catch(error => {
                console.error('Errore:', error);
                this.state.entityTypes = [];
                window.allEntities = [];
                NERGiuridico.showNotification(`Errore durante il caricamento dei tipi di entità: ${error.message}`, 'danger');
            })
            .finally(() => {
                this.setLoading(false);
            });
    },
    
    /**
     * Imposta lo stato di caricamento
     * @param {boolean} loading - True se sta caricando, false altrimenti
     */
    setLoading: function(loading) {
        this.state.isLoading = loading;
        
        if (!this.elements.loadingIndicator || !this.elements.entityTypesTable || !this.elements.emptyState) {
            console.error('DOM elements not found');
            return;
        }
        
        if (loading) {
            this.elements.loadingIndicator.classList.remove('d-none');
            this.elements.entityTypesTable.classList.add('d-none');
            this.elements.emptyState.classList.add('d-none');
        } else {
            this.elements.loadingIndicator.classList.add('d-none');
            
            if (this.state.entityTypes.length === 0) {
                this.elements.emptyState.classList.remove('d-none');
                this.elements.entityTypesTable.classList.add('d-none');
            } else {
                this.elements.emptyState.classList.add('d-none');
                this.elements.entityTypesTable.classList.remove('d-none');
            }
        }
    },
    
    /**
     * Filtra i tipi di entità in base al testo di ricerca e alla categoria
     */
    filterEntityTypes: function() {
        const searchTerm = this.elements.entitySearch.value.toLowerCase();
        const categoryValue = this.elements.categoryFilter.value;
        
        this.state.filterText = searchTerm;
        this.state.filterCategory = categoryValue;
        
        // Assicuriamoci che entityTypes sia un array
        if (!Array.isArray(this.state.entityTypes)) {
            this.state.entityTypes = [];
            this.setLoading(false);
            return;
        }

        const filteredEntities = this.state.entityTypes.filter(entity => {
            const matchesSearch = 
                entity.name.toLowerCase().includes(searchTerm) || 
                entity.display_name.toLowerCase().includes(searchTerm);
            
            const matchesCategory = 
                categoryValue === '' || entity.category === categoryValue;
            
            return matchesSearch && matchesCategory;
        });
        
        this.renderEntityTypes(filteredEntities);
    },
    
    /**
     * Visualizza i tipi di entità nella tabella
     * @param {Array} entityTypes - Array di tipi di entità da visualizzare
     */
    renderEntityTypes: function(entityTypes) {
        // Svuota la tabella
        const tbody = this.elements.entityTypesTable.querySelector('tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        // Gestione esplicita di zero entità
        if (entityTypes.length === 0) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 5;
            td.textContent = 'Nessun tipo di entità trovato';
            td.className = 'text-center py-4 text-muted';
            tr.appendChild(td);
            tbody.appendChild(tr);
            return;
        }
        
        // Aggiungi i tipi di entità alla tabella
        entityTypes.forEach(entityType => {
            const tr = document.createElement('tr');
            
            // Nome
            const nameTd = document.createElement('td');
            nameTd.textContent = entityType.name;
            nameTd.className = 'align-middle';
            tr.appendChild(nameTd);
            
            // Nome visualizzato
            const displayNameTd = document.createElement('td');
            displayNameTd.textContent = entityType.display_name;
            displayNameTd.className = 'align-middle';
            tr.appendChild(displayNameTd);
            
            // Categoria
            const categoryTd = document.createElement('td');
            const categoryBadge = document.createElement('span');
            categoryBadge.className = 'badge rounded-pill';
            
            // Colore della badge in base alla categoria
            switch (entityType.category) {
                case 'normative':
                    categoryBadge.classList.add('bg-primary');
                    break;
                case 'jurisprudence':
                    categoryBadge.classList.add('bg-success');
                    break;
                case 'concepts':
                    categoryBadge.classList.add('bg-info');
                    break;
                case 'custom':
                    categoryBadge.classList.add('bg-secondary');
                    break;
                default:
                    categoryBadge.classList.add('bg-dark');
            }
            
            categoryBadge.textContent = this.getCategoryDisplayName(entityType.category);
            categoryTd.className = 'align-middle';
            categoryTd.appendChild(categoryBadge);
            tr.appendChild(categoryTd);
            
            // Colore
            const colorTd = document.createElement('td');
            colorTd.className = 'align-middle';
            
            const colorCell = document.createElement('div');
            colorCell.className = 'd-flex align-items-center';
            
            const colorPreview = document.createElement('div');
            colorPreview.className = 'me-2 rounded';
            colorPreview.style.backgroundColor = entityType.color;
            colorPreview.style.width = '24px';
            colorPreview.style.height = '24px';
            colorPreview.style.border = '1px solid rgba(0,0,0,0.1)';
            
            const colorText = document.createElement('code');
            colorText.textContent = entityType.color;
            
            colorCell.appendChild(colorPreview);
            colorCell.appendChild(colorText);
            colorTd.appendChild(colorCell);
            tr.appendChild(colorTd);
            
            // Azioni
            const actionsTd = document.createElement('td');
            actionsTd.className = 'align-middle';
            
            const actionButtons = document.createElement('div');
            actionButtons.className = 'btn-group';
            
            const editBtn = document.createElement('button');
            editBtn.className = 'btn btn-sm btn-outline-primary';
            editBtn.innerHTML = '<i class="fas fa-edit me-1"></i> Modifica';
            editBtn.title = 'Modifica il tipo di entità';
            editBtn.addEventListener('click', () => this.showEditForm(entityType));
            
            actionButtons.appendChild(editBtn);
            
            // Aggiungi sempre il pulsante di eliminazione, ma con styling diverso per tipi predefiniti
            const deleteBtn = document.createElement('button');
            
            if (entityType.category === 'custom') {
                deleteBtn.className = 'btn btn-sm btn-outline-danger';
                deleteBtn.innerHTML = '<i class="fas fa-trash-alt me-1"></i> Elimina';
                deleteBtn.title = 'Elimina il tipo di entità';
            } else {
                deleteBtn.className = 'btn btn-sm btn-outline-secondary disabled';
                deleteBtn.innerHTML = '<i class="fas fa-lock me-1"></i> Protetto';
                deleteBtn.title = 'Le entità predefinite non possono essere eliminate';
                deleteBtn.disabled = true;
            }
            
            deleteBtn.addEventListener('click', () => {
                if (entityType.category === 'custom') {
                    this.showDeleteConfirmation(entityType);
                } else {
                    NERGiuridico.showNotification('Le entità predefinite non possono essere eliminate', 'warning');
                }
            });
            
            actionButtons.appendChild(deleteBtn);
            
            actionsTd.appendChild(actionButtons);
            tr.appendChild(actionsTd);
            
            tbody.appendChild(tr);
        });
    },
    
    /**
     * Ottiene il nome visualizzato della categoria
     * @param {string} category - Codice della categoria
     * @returns {string} - Nome visualizzato della categoria
     */
    getCategoryDisplayName: function(category) {
        const categories = {
            'normative': 'Normativa',
            'jurisprudence': 'Giurisprudenziale',
            'concepts': 'Concetto',
            'custom': 'Personalizzata'
        };
        
        return categories[category] || category;
    },
    
    /**
     * Mostra il form di creazione di un nuovo tipo di entità
     */
    showCreateForm: function() {
        // Resetta il form
        this.elements.entityTypeForm.reset();
        this.elements.editMode.value = 'create';
        this.elements.originalName.value = '';
        this.elements.formTitle.textContent = 'Nuovo Tipo di Entità';
        this.elements.saveBtn.textContent = 'Crea';
        
        // Abilita il campo del nome
        this.elements.nameInput.disabled = false;
        
        // Inizializza il colore
        this.elements.colorInput.value = '#CCCCCC';
        this.updateColorPreview();
        
        // Rimuovi classi di validazione
        document.querySelectorAll('.is-valid, .is-invalid').forEach(el => {
            el.classList.remove('is-valid', 'is-invalid');
        });
        
        // Nascondi i risultati del test
        this.elements.testResults.classList.add('d-none');
        
        // Mostra il form
        this.elements.entityTypeFormContainer.classList.remove('d-none');
        
        // Aggiorna lo stato
        this.state.isEditMode = false;
        
        // Scorri fino al form
        this.elements.entityTypeFormContainer.scrollIntoView({behavior: 'smooth'});
        
        // Focus sul campo del nome
        this.elements.nameInput.focus();
    },
    
    /**
     * Mostra il form di modifica di un tipo di entità esistente
     * @param {Object} entityType - Il tipo di entità da modificare
     */
    showEditForm: function(entityType) {
        // Popola il form con i dati dell'entità
        this.elements.nameInput.value = entityType.name;
        this.elements.displayNameInput.value = entityType.display_name;
        this.elements.categorySelect.value = entityType.category;
        this.elements.colorInput.value = entityType.color;
        this.updateColorPreview();
        
        // Popola i metadati e i pattern
        this.elements.metadataSchemaInput.value = JSON.stringify(entityType.metadata_schema || {}, null, 2);
        this.elements.patternsInput.value = (entityType.patterns || []).join('\n');
        
        // Imposta la modalità di modifica
        this.elements.editMode.value = 'edit';
        this.elements.originalName.value = entityType.name;
        this.elements.formTitle.textContent = `Modifica Tipo di Entità: ${entityType.name}`;
        this.elements.saveBtn.textContent = 'Aggiorna';
        
        // Disabilita il campo del nome (non dovrebbe essere modificato)
        this.elements.nameInput.disabled = true;
        
        // Rimuovi classi di validazione
        document.querySelectorAll('.is-valid, .is-invalid').forEach(el => {
            el.classList.remove('is-valid', 'is-invalid');
        });
        
        // Gestisci lo stato del campo categoria in base al tipo di entità
        if (entityType.category !== 'custom' && ['normative', 'jurisprudence', 'concepts'].includes(entityType.category)) {
            // Disabilita il campo categoria se è un'entità predefinita
            this.elements.categorySelect.disabled = true;
            
            // Aggiungi un avviso sul campo della categoria
            const categoryGroup = this.elements.categorySelect.closest('.form-group') || this.elements.categorySelect.closest('.mb-3');
            
            // Rimuovi avvisi precedenti
            const existingWarning = categoryGroup.querySelector('.alert-warning');
            if (existingWarning) existingWarning.remove();
            
            // Aggiungi nuovo avviso
            const categoryWarning = document.createElement('div');
            categoryWarning.className = 'alert alert-warning mt-2 p-2 small';
            categoryWarning.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i> Non è possibile modificare la categoria di un\'entità predefinita';
            categoryGroup.appendChild(categoryWarning);
        } else {
            // Abilita il campo categoria per le entità personalizzate
            this.elements.categorySelect.disabled = false;
            
            // Rimuovi eventuali avvisi precedenti
            const categoryGroup = this.elements.categorySelect.closest('.form-group') || this.elements.categorySelect.closest('.mb-3');
            const existingWarning = categoryGroup.querySelector('.alert-warning');
            if (existingWarning) existingWarning.remove();
        }
        
        // Nascondi i risultati del test
        this.elements.testResults.classList.add('d-none');
        
        // Aggiorna lo stato
        this.state.isEditMode = true;
        this.state.selectedEntityType = entityType;
        
        // Mostra il form
        this.elements.entityTypeFormContainer.classList.remove('d-none');
        
        // Scorri fino al form
        this.elements.entityTypeFormContainer.scrollIntoView({behavior: 'smooth'});
        
        // Focus sul campo del nome visualizzato
        this.elements.displayNameInput.focus();
    },
    
    /**
     * Nasconde il form di creazione/modifica
     */
    hideForm: function() {
        this.elements.entityTypeFormContainer.classList.add('d-none');
        
        // Rimuovi classi di validazione
        document.querySelectorAll('.is-valid, .is-invalid').forEach(el => {
            el.classList.remove('is-valid', 'is-invalid');
        });
        
        // Reimposta lo stato
        this.state.isEditMode = false;
        this.state.selectedEntityType = null;
    },
    
    /**
     * Gestisce l'invio del form
     * @param {Event} e - L'evento submit
     */
    handleFormSubmit: function(e) {
        e.preventDefault();
        
        // Valida il form
        const isNameValid = this.validateEntityName();
        const isMetadataValid = this.validateMetadataSchema();
        const arePatternsValid = this.validatePatterns();
        
        if (!isNameValid || !isMetadataValid || !arePatternsValid) {
            NERGiuridico.showNotification('Correggi gli errori di validazione prima di salvare', 'danger');
            return;
        }
        
        try {
            // Ottieni i dati dal form
            const name = this.elements.nameInput.value;
            const displayName = this.elements.displayNameInput.value;
            const category = this.elements.categorySelect.value;
            const color = this.elements.colorInput.value;
            
            // Valida i metadati
            let metadataSchema = {};
            if (this.elements.metadataSchemaInput.value.trim()) {
                try {
                    metadataSchema = JSON.parse(this.elements.metadataSchemaInput.value);
                } catch (error) {
                    NERGiuridico.showNotification('Schema dei metadati non valido. Deve essere in formato JSON.', 'danger');
                    return;
                }
            }
            
            // Valida i pattern
            let patterns = [];
            if (this.elements.patternsInput.value.trim()) {
                patterns = this.elements.patternsInput.value.split('\n').filter(pattern => pattern.trim() !== '');
                
                // Verifica che tutti i pattern siano validi
                for (const pattern of patterns) {
                    try {
                        new RegExp(pattern);
                    } catch (error) {
                        NERGiuridico.showNotification(`Pattern non valido: "${pattern}" - ${error.message}`, 'danger');
                        return;
                    }
                }
            }
            
            // Prepara i dati da inviare
            const data = {
                name: name,
                display_name: displayName,
                category: category,
                color: color,
                metadata_schema: metadataSchema,
                patterns: patterns
            };
            
            // Mostra un indicatore di caricamento
            this.startPendingOperation();
            NERGiuridico.showLoading(this.elements.saveBtn, 'Salvataggio...');
            
            // Determina se stiamo creando o aggiornando
            const isCreating = this.elements.editMode.value === 'create';
            
            if (isCreating) {
                this.createEntityType(data);
            } else {
                this.updateEntityType(this.elements.originalName.value, data);
            }
        } catch (error) {
            console.error('Errore:', error);
            NERGiuridico.showNotification(`Errore durante il salvataggio: ${error.message}`, 'danger');
            
            // Ripristina il pulsante di salvataggio
            this.endPendingOperation();
            NERGiuridico.hideLoading(this.elements.saveBtn);
        }
    },
    
    /**
     * Crea un nuovo tipo di entità
     * @param {Object} data - I dati del tipo di entità
     */
    createEntityType: function(data) {
        fetch('/api/entity_types', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
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
                NERGiuridico.showNotification(`Tipo di entità "${data.entity_type.name}" creato con successo`, 'success');
                
                // Aggiungi la nuova entità all'array
                this.state.entityTypes.push(data.entity_type);
                
                // Aggiorna la tabella
                this.renderEntityTypes(this.state.entityTypes);
                
                // Nascondi il form
                this.hideForm();
            } else {
                NERGiuridico.showNotification(`Errore: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Errore:', error);
            NERGiuridico.showNotification(`Errore durante la creazione: ${error.message}`, 'danger');
        })
        .finally(() => {
            this.endPendingOperation();
            NERGiuridico.hideLoading(this.elements.saveBtn);
        });
    },
    
    /**
     * Aggiorna un tipo di entità esistente
     * @param {string} name - Il nome del tipo di entità
     * @param {Object} data - I nuovi dati del tipo di entità
     */
    updateEntityType: function(name, data) {
        fetch(`/api/entity_types/${name}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.message || `Errore HTTP: ${response.status}`);
                });
            }
            return response.json();
        })
        .then(responseData => {
            if (responseData && responseData.status === 'success') {
                // Usa entity_type o entity, a seconda di quale esiste nella risposta
                const updatedEntity = responseData.entity_type || responseData.entity;
                
                NERGiuridico.showNotification(`Tipo di entità "${name}" aggiornato con successo`, 'success');
                
                // Se la categoria è stata aggiornata, mostra un messaggio specifico
                const originalCategory = this.elements.categorySelect.dataset.originalCategory;
                if (updatedEntity && updatedEntity.category && originalCategory && 
                    updatedEntity.category !== originalCategory) {
                    NERGiuridico.showNotification(`Categoria aggiornata da "${this.getCategoryDisplayName(originalCategory)}" a "${this.getCategoryDisplayName(updatedEntity.category)}"`, 'info');
                }
                
                // Aggiorna l'entità nell'array
                const index = this.state.entityTypes.findIndex(e => e.name === name);
                if (index !== -1) {
                    this.state.entityTypes[index] = updatedEntity;
                }
                
                // Aggiorna la tabella
                this.renderEntityTypes(this.state.entityTypes);
                
                // Nascondi il form
                this.hideForm();
            } else {
                throw new Error(responseData.message || 'Errore durante l\'aggiornamento');
            }
        })
        .catch(error => {
            console.error('Errore:', error);
            NERGiuridico.showNotification(`Errore durante l'aggiornamento: ${error.message}`, 'danger');
        })
        .finally(() => {
            this.endPendingOperation();
            NERGiuridico.hideLoading(this.elements.saveBtn);
        });
    },
    
    /**
     * Mostra la finestra di conferma per l'eliminazione
     * @param {Object} entityType - Il tipo di entità da eliminare
     */
    showDeleteConfirmation: function(entityType) {
        this.state.entityToDelete = entityType;
        
        // Usa il modale di Bootstrap
        const confirmationModal = new bootstrap.Modal(document.getElementById('confirmation-dialog'));
        
        const confirmationMessage = document.getElementById('confirmation-message');
        confirmationMessage.innerHTML = `Sei sicuro di voler eliminare il tipo di entità <strong>"${entityType.name}"</strong> (${entityType.display_name})?`;
        
        // Aggiungiamo un testo aggiuntivo per la categoria
        if (entityType.category !== 'custom') {
            const warningText = document.createElement('div');
            warningText.className = 'alert alert-warning mt-3';
            warningText.innerHTML = '<i class="fas fa-exclamation-triangle me-2"></i>Attenzione: Questa è un\'entità predefinita. L\'eliminazione potrebbe non essere possibile.';
            confirmationMessage.appendChild(warningText);
        }
        
        confirmationModal.show();
        
        // Focus sul pulsante di cancellazione
        setTimeout(() => {
            if (this.elements.confirmCancelBtn) this.elements.confirmCancelBtn.focus();
        }, 300);
    },
    
    /**
     * Nasconde la finestra di conferma
     */
    hideConfirmationDialog: function() {
        const confirmationModal = bootstrap.Modal.getInstance(document.getElementById('confirmation-dialog'));
        if (confirmationModal) confirmationModal.hide();
        this.state.entityToDelete = null;
    },
    
    /**
     * Conferma l'eliminazione del tipo di entità
     */
    confirmDelete: function() {
        if (!this.state.entityToDelete) {
            this.hideConfirmationDialog();
            return;
        }
        
        const name = this.state.entityToDelete.name;
        
        // Disabilita i pulsanti di conferma
        this.startPendingOperation();
        NERGiuridico.showLoading(this.elements.confirmDeleteBtn, 'Eliminazione...');
        this.elements.confirmCancelBtn.disabled = true;
        
        fetch(`/api/entity_types/${name}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        })
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
                NERGiuridico.showNotification(`Tipo di entità "${name}" eliminato con successo`, 'success');
                
                // Rimuovi l'entità dall'array
                this.state.entityTypes = this.state.entityTypes.filter(e => e.name !== name);
                
                // Aggiorna la tabella
                this.renderEntityTypes(this.state.entityTypes);
                
                // Se non ci sono più entità, mostra il messaggio vuoto
                if (this.state.entityTypes.length === 0) {
                    this.elements.emptyState.classList.remove('d-none');
                    this.elements.entityTypesTable.classList.add('d-none');
                }
            } else {
                NERGiuridico.showNotification(`Errore: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Errore durante l\'eliminazione:', error);
            NERGiuridico.showNotification(`Errore durante l'eliminazione: ${error.message}`, 'danger');
        })
        .finally(() => {
            this.hideConfirmationDialog();
            this.endPendingOperation();
            
            // Ripristina i pulsanti di conferma
            this.elements.confirmDeleteBtn.disabled = false;
            this.elements.confirmCancelBtn.disabled = false;
            NERGiuridico.hideLoading(this.elements.confirmDeleteBtn);
        });
    },
    
    /**
     * Testa i pattern
     */
    testPatterns: function() {
        const patterns = this.elements.patternsInput.value.trim();
        const testString = this.elements.testText.value;
        
        // Se non ci sono pattern o testo di test, non fare nulla
        if (!patterns || !testString) {
            NERGiuridico.showNotification('Inserisci almeno un pattern e un testo di esempio', 'warning');
            return;
        }
        
        // Dividi i pattern in righe
        const patternLines = patterns.split('\n').filter(line => line.trim() !== '');
        
        // Test manuale dei pattern
        this.testPatternsLocally(patternLines, testString);
        
        // In alternativa, testa i pattern usando l'API
        //this.testPatternsViaAPI(patternLines, testString);
    },
    
    /**
     * Testa i pattern localmente (client-side)
     * @param {Array} patternLines - I pattern da testare
     * @param {string} testString - Il testo su cui testare i pattern
     */
    testPatternsLocally: function(patternLines, testString) {
        // Compila ogni pattern regex e cerca le corrispondenze
        const results = [];
        
        for (const pattern of patternLines) {
            try {
                const regex = new RegExp(pattern, 'g');
                const matches = [...testString.matchAll(regex)];
                
                results.push({
                    pattern,
                    matches: matches.map(match => ({
                        text: match[0],
                        index: match.index,
                        groups: match.slice(1)
                    }))
                });
            } catch (error) {
                results.push({
                    pattern,
                    error: error.message
                });
            }
        }
        
        // Mostra i risultati
        let output = '';
        
        results.forEach((result, index) => {
            output += `Pattern ${index + 1}: ${result.pattern}\n`;
            
            if (result.error) {
                output += `  Errore: ${result.error}\n`;
            } else if (result.matches.length === 0) {
                output += '  Nessuna corrispondenza trovata\n';
            } else {
                output += `  ${result.matches.length} corrispondenze trovate:\n`;
                
                result.matches.forEach((match, matchIndex) => {
                    output += `    ${matchIndex + 1}. "${match.text}" (indice: ${match.index})\n`;
                    
                    if (match.groups.length > 0) {
                        output += '       Gruppi catturati:\n';
                        match.groups.forEach((group, groupIndex) => {
                            if (group) {
                                output += `         ${groupIndex + 1}: "${group}"\n`;
                            }
                        });
                    }
                });
            }
            
            output += '\n';
        });
        
        // Mostra i risultati
        this.elements.testOutput.textContent = output;
        this.elements.testResults.classList.remove('d-none');
        
        // Scorri ai risultati
        this.elements.testResults.scrollIntoView({behavior: 'smooth'});
    },
    
    /**
     * Testa i pattern tramite API
     * @param {Array} patternLines - I pattern da testare
     * @param {string} testString - Il testo su cui testare i pattern
     */
    testPatternsViaAPI: function(patternLines, testString) {
        this.startPendingOperation();
        NERGiuridico.showLoading(this.elements.testPatternsBtn, 'Test in corso...');
        
        fetch('/api/test_pattern', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                pattern: patternLines[0], // Testa solo il primo pattern
                text: testString
            })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Errore HTTP: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                let output = '';
                
                output += `Pattern: ${data.pattern}\n`;
                
                if (data.matches_count === 0) {
                    output += '  Nessuna corrispondenza trovata\n';
                } else {
                    output += `  ${data.matches_count} corrispondenze trovate:\n`;
                    
                    data.matches.forEach((match, index) => {
                        output += `    ${index + 1}. "${match.text}" (indice: ${match.start})\n`;
                        
                        if (match.groups.length > 0) {
                            output += '       Gruppi catturati:\n';
                            match.groups.forEach((group, groupIndex) => {
                                if (group) {
                                    output += `         ${groupIndex + 1}: "${group}"\n`;
                                }
                            });
                        }
                    });
                }
                
                // Mostra i risultati
                this.elements.testOutput.textContent = output;
                this.elements.testResults.classList.remove('d-none');
                
                // Scorri ai risultati
                this.elements.testResults.scrollIntoView({behavior: 'smooth'});
            } else {
                NERGiuridico.showNotification(`Errore: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Errore durante il test:', error);
            NERGiuridico.showNotification(`Errore durante il test: ${error.message}`, 'danger');
        })
        .finally(() => {
            this.endPendingOperation();
            NERGiuridico.hideLoading(this.elements.testPatternsBtn);
        });
    },
    
    /**
     * Valida il nome dell'entità
     * @returns {boolean} True se il nome è valido, false altrimenti
     */
    validateEntityName: function() {
        const name = this.elements.nameInput.value;
        
        // Resetta il campo
        this.elements.nameInput.classList.remove('is-valid', 'is-invalid');
        
        // Se il campo è disabilitato (in modalità modifica), ritorna true
        if (this.elements.nameInput.disabled) return true;
        
        // Controlla se il nome è vuoto
        if (!name) {
            this.elements.nameInput.classList.add('is-invalid');
            const feedback = this.elements.nameInput.nextElementSibling?.nextElementSibling;
            if (feedback) feedback.textContent = 'Il nome è obbligatorio';
            return false;
        }
        
        // Controlla se il nome è in maiuscolo
        if (name !== name.toUpperCase()) {
            this.elements.nameInput.classList.add('is-invalid');
            const feedback = this.elements.nameInput.nextElementSibling?.nextElementSibling;
            if (feedback) feedback.textContent = 'Il nome deve essere in maiuscolo';
            return false;
        }
        
        // Controlla se il nome contiene spazi
        if (name.includes(' ')) {
            this.elements.nameInput.classList.add('is-invalid');
            const feedback = this.elements.nameInput.nextElementSibling?.nextElementSibling;
            if (feedback) feedback.textContent = 'Il nome non deve contenere spazi';
            return false;
        }
        
        // Controlla se il nome è già utilizzato (solo in modalità creazione)
        if (this.elements.editMode.value === 'create') {
            const existingEntity = this.state.entityTypes.find(entity => entity.name === name);
            if (existingEntity) {
                this.elements.nameInput.classList.add('is-invalid');
                const feedback = this.elements.nameInput.nextElementSibling?.nextElementSibling;
                if (feedback) feedback.textContent = 'Questo nome è già in uso';
                return false;
            }
        }
        
        this.elements.nameInput.classList.add('is-valid');
        return true;
    },
    
    /**
     * Valida lo schema dei metadati
     * @returns {boolean} True se lo schema è valido, false altrimenti
     */
    validateMetadataSchema: function() {
        const schema = this.elements.metadataSchemaInput.value.trim();
        
        // Resetta il campo
        this.elements.metadataSchemaInput.classList.remove('is-valid', 'is-invalid');
        
        // Se lo schema è vuoto, è valido
        if (!schema) {
            return true;
        }
        
        // Prova a parsare lo schema JSON
        try {
            JSON.parse(schema);
            this.elements.metadataSchemaInput.classList.add('is-valid');
            return true;
        } catch (error) {
            this.elements.metadataSchemaInput.classList.add('is-invalid');
            const feedback = this.elements.metadataSchemaInput.nextElementSibling?.nextElementSibling;
            if (feedback) feedback.textContent = `Schema JSON non valido: ${error.message}`;
            return false;
        }
    },
    
    /**
     * Valida i pattern regex
     * @returns {boolean} True se i pattern sono validi, false altrimenti
     */
    validatePatterns: function() {
        const patterns = this.elements.patternsInput.value.trim();
        
        // Resetta il campo
        this.elements.patternsInput.classList.remove('is-valid', 'is-invalid');
        
        // Se non ci sono pattern, è valido
        if (!patterns) {
            return true;
        }
        
        // Dividi i pattern in righe
        const patternLines = patterns.split('\n').filter(line => line.trim() !== '');
        
        // Prova a compilare ogni pattern regex
        let allValid = true;
        let invalidPattern = null;
        let errorMessage = null;
        
        for (const pattern of patternLines) {
            try {
                new RegExp(pattern);
            } catch (error) {
                allValid = false;
                invalidPattern = pattern;
                errorMessage = error.message;
                break;
            }
        }
        
        if (allValid) {
            this.elements.patternsInput.classList.add('is-valid');
            return true;
        } else {
            this.elements.patternsInput.classList.add('is-invalid');
            const feedback = this.elements.patternsInput.nextElementSibling?.nextElementSibling;
            if (feedback) feedback.textContent = `Pattern non valido: "${invalidPattern}" - ${errorMessage}`;
            return false;
        }
    },
    
    /**
     * Aggiorna l'anteprima del colore
     */
    updateColorPreview: function() {
        const colorValue = this.elements.colorInput.value;
        this.elements.colorPreview.textContent = colorValue;
        this.elements.colorSample.style.backgroundColor = colorValue;
        
        // Calcola il colore del testo in base al colore di sfondo
        const textColor = NERGiuridico.getTextColorForBackground(colorValue);
        this.elements.colorSample.style.color = textColor;
    },
    
    /**
     * Incrementa il contatore delle operazioni in corso
     */
    startPendingOperation: function() {
        this.state.pendingOperations++;
        if (this.state.pendingOperations === 1) {
            // Potrebbe essere aggiunto un indicatore di caricamento globale
            document.body.classList.add('loading');
        }
    },
    
    /**
     * Decrementa il contatore delle operazioni in corso
     */
    endPendingOperation: function() {
        this.state.pendingOperations = Math.max(0, this.state.pendingOperations - 1);
        if (this.state.pendingOperations === 0) {
            document.body.classList.remove('loading');
        }
    }
};

// Inizializzazione all'avvio
document.addEventListener('DOMContentLoaded', function() {
    // Inizializza il gestore dei tipi di entità
    EntityManager.init();
    
    // Esponi funzioni per compatibilità con il codice esistente
    window.setLoading = loading => EntityManager.setLoading(loading);
    window.renderEntityTypes = entityTypes => EntityManager.renderEntityTypes(entityTypes);
    window.showCreateForm = () => EntityManager.showCreateForm();
    window.hideForm = () => EntityManager.hideForm();
    window.updateColorPreview = () => EntityManager.updateColorPreview();
    window.validateEntityName = () => EntityManager.validateEntityName();
    window.validateMetadataSchema = () => EntityManager.validateMetadataSchema();
    window.validatePatterns = () => EntityManager.validatePatterns();
    window.showDeleteConfirmation = entityType => EntityManager.showDeleteConfirmation(entityType);
});