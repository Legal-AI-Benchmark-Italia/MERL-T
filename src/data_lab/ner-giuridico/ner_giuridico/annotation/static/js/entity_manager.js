/**
 * entity_manager.js - Script migliorato per la gestione dei tipi di entità
 * Versione aggiornata con supporto per Bootstrap 5 e miglioramenti UX
 */

document.addEventListener('DOMContentLoaded', function() {
    // === Elementi DOM ===
    const entityTypesTable = document.getElementById('entity-types-table');
    const entityTypeForm = document.getElementById('entity-type-form');
    const entityTypeFormContainer = document.getElementById('entity-type-form-container');
    const formTitle = document.getElementById('form-title');
    const addEntityTypeBtn = document.getElementById('add-entity-type-btn');
    const addFirstEntityBtn = document.getElementById('add-first-entity');
    const cancelBtn = document.getElementById('cancel-btn');
    const closeFormBtn = document.getElementById('close-form-btn');
    const saveBtn = document.getElementById('save-btn');
    const editMode = document.getElementById('edit-mode');
    const originalName = document.getElementById('original-name');
    const nameInput = document.getElementById('entity-name');
    const displayNameInput = document.getElementById('display-name');
    const categorySelect = document.getElementById('category');
    const colorInput = document.getElementById('color');
    const colorPreview = document.getElementById('color-preview');
    const colorSample = document.getElementById('color-sample');
    const metadataSchemaInput = document.getElementById('metadata-schema');
    const patternsInput = document.getElementById('patterns');
    const testPatternsBtn = document.getElementById('test-patterns-btn');
    const testText = document.getElementById('test-text');
    const testResults = document.getElementById('test-results');
    const testOutput = document.getElementById('test-output');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    const confirmCancelBtn = document.getElementById('confirm-cancel-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    const emptyState = document.getElementById('empty-state');
    const entitySearch = document.getElementById('entity-search');
    const categoryFilter = document.getElementById('category-filter');
    
    // === Stato dell'applicazione ===
    let entityToDelete = null;
    let allEntities = [];
    let isLoading = true;
    
    // === Imposta lo stato di caricamento ===
    function setLoading(loading) {
        isLoading = loading;
        
        if (!loadingIndicator || !entityTypesTable || !emptyState) {
            console.error('DOM elements not found');
            return;
        }
        
        if (loading) {
            loadingIndicator.classList.remove('d-none');
            entityTypesTable.classList.add('d-none');
            emptyState.classList.add('d-none');
        } else {
            loadingIndicator.classList.add('d-none');
            
            if (!Array.isArray(allEntities) || allEntities.length === 0) {
                emptyState.classList.remove('d-none');
                entityTypesTable.classList.add('d-none');
            } else {
                emptyState.classList.add('d-none');
                entityTypesTable.classList.remove('d-none');
            }
        }
    }
    
    // === Carica i tipi di entità all'avvio ===
    loadEntityTypes();
    
    // === Event listeners ===
    if (addEntityTypeBtn) {
        addEntityTypeBtn.addEventListener('click', showCreateForm);
    }
    
    if (addFirstEntityBtn) {
        addFirstEntityBtn.addEventListener('click', showCreateForm);
    }
    
    if (cancelBtn) {
        cancelBtn.addEventListener('click', hideForm);
    }
    
    if (closeFormBtn) {
        closeFormBtn.addEventListener('click', hideForm);
    }
    
    if (entityTypeForm) {
        entityTypeForm.addEventListener('submit', handleFormSubmit);
    }
    
    if (colorInput) {
        colorInput.addEventListener('input', updateColorPreview);
    }
    
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', confirmDelete);
    }
    
    if (confirmCancelBtn) {
        confirmCancelBtn.addEventListener('click', hideConfirmationDialog);
    }
    
    if (entitySearch) {
        entitySearch.addEventListener('input', filterEntities);
    }
    
    if (categoryFilter) {
        categoryFilter.addEventListener('change', filterEntities);
    }
    
    if (testPatternsBtn) {
        testPatternsBtn.addEventListener('click', testPatterns);
    }
    
    // === Validazione in tempo reale ===
    if (nameInput) {
        nameInput.addEventListener('input', validateEntityName);
    }
    
    if (metadataSchemaInput) {
        metadataSchemaInput.addEventListener('input', validateMetadataSchema);
    }
    
    if (patternsInput) {
        patternsInput.addEventListener('input', validatePatterns);
    }
    
    // === Funzione per mostrare una notifica ===
    function showNotification(message, type = 'primary') {
        // Utilizziamo i toast di Bootstrap
        const toastEl = document.getElementById('notification-toast');
        if (!toastEl) return;
        
        const toastBody = toastEl.querySelector('.toast-body');
        if (toastBody) toastBody.textContent = message;
        
        // Imposta il tipo di toast
        toastEl.className = toastEl.className.replace(/bg-\w+/, '');
        toastEl.classList.add(`bg-${type}`);
        
        // Mostra il toast
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
    }
    
    // === Funzione per caricare i tipi di entità ===
    function loadEntityTypes() {
        setLoading(true);
        
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
                    window.allEntities = data.entity_types;
                    allEntities = data.entity_types;
                } else {
                    console.error('Formato risposta non valido:', data);
                    window.allEntities = [];
                    allEntities = [];
                    showNotification('Errore nel formato dei dati ricevuti', 'danger');
                }
                
                renderEntityTypes(allEntities);
            })
            .catch(error => {
                console.error('Errore:', error);
                window.allEntities = [];
                allEntities = [];
                showNotification(`Errore durante il caricamento dei tipi di entità: ${error.message}`, 'danger');
            })
            .finally(() => {
                setLoading(false);
            });
    }
    
    // === Funzione per filtrare le entità ===
    function filterEntities() {
        const searchTerm = entitySearch.value.toLowerCase();
        const categoryValue = categoryFilter.value;
        
        // Assicuriamoci che allEntities sia un array
        if (!Array.isArray(allEntities)) {
            allEntities = [];
            setLoading(false);
            return;
        }

        const filteredEntities = allEntities.filter(entity => {
            const matchesSearch = 
                entity.name.toLowerCase().includes(searchTerm) || 
                entity.display_name.toLowerCase().includes(searchTerm);
            
            const matchesCategory = 
                categoryValue === '' || entity.category === categoryValue;
            
            return matchesSearch && matchesCategory;
        });
        
        renderEntityTypes(filteredEntities);
        
        // Mostra messaggio se non ci sono risultati
        if (filteredEntities.length === 0 && allEntities.length > 0) {
            const tbody = entityTypesTable.querySelector('tbody');
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 5;
            td.textContent = 'Nessun risultato trovato';
            td.className = 'text-center py-4 text-muted';
            tr.appendChild(td);
            tbody.appendChild(tr);
        }
    }
    
    // === Funzione per visualizzare i tipi di entità nella tabella ===
    function renderEntityTypes(entityTypes) {
        // Svuota la tabella
        const tbody = entityTypesTable.querySelector('tbody');
        if (!tbody) return;
        
        tbody.innerHTML = '';
        
        // Verifica che entityTypes sia un array
        if (!Array.isArray(entityTypes)) {
            console.error('entityTypes non è un array:', entityTypes);
            entityTypes = [];
        }
        
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
            
            categoryBadge.textContent = getCategoryDisplayName(entityType.category);
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
            editBtn.addEventListener('click', () => showEditForm(entityType));
            
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
                    showDeleteConfirmation(entityType);
                } else {
                    showNotification('Le entità predefinite non possono essere eliminate', 'warning');
                }
            });
            
            actionButtons.appendChild(deleteBtn);
            
            actionsTd.appendChild(actionButtons);
            tr.appendChild(actionsTd);
            
            tbody.appendChild(tr);
        });
    }
    
    // === Funzione per ottenere il nome visualizzato della categoria ===
    function getCategoryDisplayName(category) {
        const categories = {
            'normative': 'Normativa',
            'jurisprudence': 'Giurisprudenziale',
            'concepts': 'Concetto',
            'custom': 'Personalizzata'
        };
        
        return categories[category] || category;
    }
    
    // === Funzione per mostrare il form di creazione ===
    function showCreateForm() {
        // Resetta il form
        entityTypeForm.reset();
        editMode.value = 'create';
        originalName.value = '';
        formTitle.textContent = 'Nuovo Tipo di Entità';
        saveBtn.textContent = 'Crea';
        
        // Abilita il campo del nome
        nameInput.disabled = false;
        
        // Inizializza il colore
        colorInput.value = '#CCCCCC';
        updateColorPreview();
        
        // Rimuovi classi di validazione
        document.querySelectorAll('.is-valid, .is-invalid').forEach(el => {
            el.classList.remove('is-valid', 'is-invalid');
        });
        
        // Nascondi i risultati del test
        testResults.classList.add('d-none');
        
        // Mostra il form
        entityTypeFormContainer.classList.remove('d-none');
        
        // Scorri fino al form
        entityTypeFormContainer.scrollIntoView({behavior: 'smooth'});
        
        // Focus sul campo del nome
        nameInput.focus();
    }
        
    // === Funzione per mostrare il form di modifica ===
    function showEditForm(entityType) {
        // Popola il form con i dati dell'entità
        nameInput.value = entityType.name;
        displayNameInput.value = entityType.display_name;
        categorySelect.value = entityType.category;
        colorInput.value = entityType.color;
        updateColorPreview();
        
        // Popola i metadati e i pattern
        metadataSchemaInput.value = JSON.stringify(entityType.metadata_schema || {}, null, 2);
        patternsInput.value = (entityType.patterns || []).join('\n');
        
        // Imposta la modalità di modifica
        editMode.value = 'edit';
        originalName.value = entityType.name;
        formTitle.textContent = `Modifica Tipo di Entità: ${entityType.name}`;
        saveBtn.textContent = 'Aggiorna';
        
        // Disabilita il campo del nome (non dovrebbe essere modificato)
        nameInput.disabled = true;
        
        // Rimuovi classi di validazione
        document.querySelectorAll('.is-valid, .is-invalid').forEach(el => {
            el.classList.remove('is-valid', 'is-invalid');
        });
        
        // Gestisci lo stato del campo categoria in base al tipo di entità
        if (entityType.category !== 'custom' && ['normative', 'jurisprudence', 'concepts'].includes(entityType.category)) {
            // Disabilita il campo categoria se è un'entità predefinita
            categorySelect.disabled = true;
            
            // Aggiungi un avviso sul campo della categoria
            const categoryGroup = categorySelect.closest('.form-group') || categorySelect.closest('.mb-3');
            
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
            categorySelect.disabled = false;
            
            // Rimuovi eventuali avvisi precedenti
            const categoryGroup = categorySelect.closest('.form-group') || categorySelect.closest('.mb-3');
            const existingWarning = categoryGroup.querySelector('.alert-warning');
            if (existingWarning) existingWarning.remove();
        }
        
        // Nascondi i risultati del test
        testResults.classList.add('d-none');
        
        // Mostra il form
        entityTypeFormContainer.classList.remove('d-none');
        
        // Scorri fino al form
        entityTypeFormContainer.scrollIntoView({behavior: 'smooth'});
        
        // Focus sul campo del nome visualizzato
        displayNameInput.focus();
    }
    
    // === Funzione per nascondere il form ===
    function hideForm() {
        entityTypeFormContainer.classList.add('d-none');
        
        // Rimuovi classi di validazione
        document.querySelectorAll('.is-valid, .is-invalid').forEach(el => {
            el.classList.remove('is-valid', 'is-invalid');
        });
    }
    
    // === Funzione per aggiornare l'anteprima del colore ===
    function updateColorPreview() {
        const colorValue = colorInput.value;
        colorPreview.textContent = colorValue;
        colorSample.style.backgroundColor = colorValue;
        
        // Calcola il colore del testo in base al colore di sfondo
        const rgb = hexToRgb(colorValue);
        const luminance = calculateLuminance(rgb.r, rgb.g, rgb.b);
        colorSample.style.color = luminance > 0.5 ? '#000000' : '#FFFFFF';
    }
    
    // === Funzione per convertire un colore HEX in RGB ===
    function hexToRgb(hex) {
        // Rimuovi il # se presente
        hex = hex.replace(/^#/, '');
        
        // Converti il colore HEX in RGB
        const bigint = parseInt(hex, 16);
        const r = (bigint >> 16) & 255;
        const g = (bigint >> 8) & 255;
        const b = bigint & 255;
        
        return { r, g, b };
    }
    
    // === Funzione per calcolare la luminanza di un colore ===
    function calculateLuminance(r, g, b) {
        const a = [r, g, b].map(function(v) {
            v /= 255;
            return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
        });
        return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
    }
    
    // === Funzione per validare il nome dell'entità ===
    function validateEntityName() {
        const name = nameInput.value;
        
        // Resetta il campo
        nameInput.classList.remove('is-valid', 'is-invalid');
        
        // Se il campo è disabilitato (in modalità modifica), ritorna true
        if (nameInput.disabled) return true;
        
        // Controlla se il nome è vuoto
        if (!name) {
            nameInput.classList.add('is-invalid');
            const feedback = nameInput.nextElementSibling.nextElementSibling;
            if (feedback) feedback.textContent = 'Il nome è obbligatorio';
            return false;
        }
        
        // Controlla se il nome è in maiuscolo
        if (name !== name.toUpperCase()) {
            nameInput.classList.add('is-invalid');
            const feedback = nameInput.nextElementSibling.nextElementSibling;
            if (feedback) feedback.textContent = 'Il nome deve essere in maiuscolo';
            return false;
        }
        
        // Controlla se il nome contiene spazi
        if (name.includes(' ')) {
            nameInput.classList.add('is-invalid');
            const feedback = nameInput.nextElementSibling.nextElementSibling;
            if (feedback) feedback.textContent = 'Il nome non deve contenere spazi';
            return false;
        }
        
        // Controlla se il nome è già utilizzato (solo in modalità creazione)
        if (editMode.value === 'create') {
            const existingEntity = allEntities.find(entity => entity.name === name);
            if (existingEntity) {
                nameInput.classList.add('is-invalid');
                const feedback = nameInput.nextElementSibling.nextElementSibling;
                if (feedback) feedback.textContent = 'Questo nome è già in uso';
                return false;
            }
        }
        
        nameInput.classList.add('is-valid');
        return true;
    }
    
    // === Funzione per validare lo schema dei metadati ===
    function validateMetadataSchema() {
        const schema = metadataSchemaInput.value.trim();
        
        // Resetta il campo
        metadataSchemaInput.classList.remove('is-valid', 'is-invalid');
        
        // Se lo schema è vuoto, è valido
        if (!schema) {
            return true;
        }
        
        // Prova a parsare lo schema JSON
        try {
            JSON.parse(schema);
            metadataSchemaInput.classList.add('is-valid');
            return true;
        } catch (error) {
            metadataSchemaInput.classList.add('is-invalid');
            const feedback = metadataSchemaInput.nextElementSibling.nextElementSibling;
            if (feedback) feedback.textContent = `Schema JSON non valido: ${error.message}`;
            return false;
        }
    }
    
    // === Funzione per validare i pattern ===
    function validatePatterns() {
        const patterns = patternsInput.value.trim();
        
        // Resetta il campo
        patternsInput.classList.remove('is-valid', 'is-invalid');
        
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
            patternsInput.classList.add('is-valid');
            return true;
        } else {
            patternsInput.classList.add('is-invalid');
            const feedback = patternsInput.nextElementSibling.nextElementSibling;
            if (feedback) feedback.textContent = `Pattern non valido: "${invalidPattern}" - ${errorMessage}`;
            return false;
        }
    }
    
    // === Funzione per testare i pattern ===
    function testPatterns() {
        const patterns = patternsInput.value.trim();
        const testString = testText.value;
        
        // Se non ci sono pattern o testo di test, non fare nulla
        if (!patterns || !testString) {
            showNotification('Inserisci almeno un pattern e un testo di esempio', 'warning');
            return;
        }
        
        // Dividi i pattern in righe
        const patternLines = patterns.split('\n').filter(line => line.trim() !== '');
        
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
        testOutput.textContent = output;
        testResults.classList.remove('d-none');
    }
    
    // === Funzione per gestire l'invio del form ===
    function handleFormSubmit(e) {
        e.preventDefault();
        
        // Valida il form
        const isNameValid = validateEntityName();
        const isMetadataValid = validateMetadataSchema();
        const arePatternsValid = validatePatterns();
        
        if (!isNameValid || !isMetadataValid || !arePatternsValid) {
            showNotification('Correggi gli errori di validazione prima di salvare', 'danger');
            return;
        }
        
        try {
            // Ottieni i dati dal form
            const name = nameInput.value;
            const displayName = displayNameInput.value;
            const category = categorySelect.value;
            const color = colorInput.value;
            
            // Valida i metadati
            let metadataSchema = {};
            if (metadataSchemaInput.value.trim()) {
                try {
                    metadataSchema = JSON.parse(metadataSchemaInput.value);
                } catch (error) {
                    showNotification('Schema dei metadati non valido. Deve essere in formato JSON.', 'danger');
                    return;
                }
            }
            
            // Valida i pattern
            let patterns = [];
            if (patternsInput.value.trim()) {
                patterns = patternsInput.value.split('\n').filter(pattern => pattern.trim() !== '');
                
                // Verifica che tutti i pattern siano validi
                for (const pattern of patterns) {
                    try {
                        new RegExp(pattern);
                    } catch (error) {
                        showNotification(`Pattern non valido: "${pattern}" - ${error.message}`, 'danger');
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
            saveBtn.disabled = true;
            saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Salvataggio...';
            
            // Determina se stiamo creando o aggiornando
            const isCreating = editMode.value === 'create';
            
            if (isCreating) {
                createEntityType(data);
            } else {
                updateEntityType(originalName.value, data);
            }
        } catch (error) {
            console.error('Errore:', error);
            showNotification(`Errore durante il salvataggio: ${error.message}`, 'danger');
            
            // Ripristina il pulsante di salvataggio
            saveBtn.disabled = false;
            saveBtn.textContent = editMode.value === 'create' ? 'Crea' : 'Aggiorna';
        }
    }
    
    // === Funzione per creare un nuovo tipo di entità ===
    function createEntityType(data) {
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
                showNotification(`Tipo di entità "${data.entity_type.name}" creato con successo`, 'success');
                hideForm();
                loadEntityTypes();
            } else {
                showNotification(`Errore: ${data.message}`, 'danger');
            }
            
            // Ripristina il pulsante di salvataggio
            saveBtn.disabled = false;
            saveBtn.textContent = 'Crea';
        })
        .catch(error => {
            console.error('Errore:', error);
            showNotification(`Errore durante la creazione: ${error.message}`, 'danger');
            
            // Ripristina il pulsante di salvataggio
            saveBtn.disabled = false;
            saveBtn.textContent = 'Crea';
        });
    }
    
    // === Funzione per aggiornare un tipo di entità ===
    function updateEntityType(name, data) {
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
                
                showNotification(`Tipo di entità "${name}" aggiornato con successo`, 'success');
                
                // Se la categoria è stata aggiornata, mostra un messaggio specifico
                const originalCategory = categorySelect.dataset.originalCategory;
                if (updatedEntity && updatedEntity.category && originalCategory && 
                    updatedEntity.category !== originalCategory) {
                    showNotification(`Categoria aggiornata da "${getCategoryDisplayName(originalCategory)}" a "${getCategoryDisplayName(updatedEntity.category)}"`, 'info');
                }
                
                hideForm();
                loadEntityTypes();
            } else {
                throw new Error(responseData.message || 'Errore durante l\'aggiornamento');
            }
            
            // Ripristina il pulsante di salvataggio
            saveBtn.disabled = false;
            saveBtn.textContent = 'Aggiorna';
        })
        .catch(error => {
            console.error('Errore:', error);
            showNotification(`Errore durante l'aggiornamento: ${error.message}`, 'danger');
            
            // Ripristina il pulsante di salvataggio
            saveBtn.disabled = false;
            saveBtn.textContent = 'Aggiorna';
        });
    }
    
    // === Funzione per mostrare la conferma di eliminazione ===
    function showDeleteConfirmation(entityType) {
        entityToDelete = entityType;
        
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
            if (confirmCancelBtn) confirmCancelBtn.focus();
        }, 300);
    }
    
    // === Funzione per nascondere la finestra di conferma ===
    function hideConfirmationDialog() {
        const confirmationModal = bootstrap.Modal.getInstance(document.getElementById('confirmation-dialog'));
        if (confirmationModal) confirmationModal.hide();
        entityToDelete = null;
    }
    
    // === Funzione per confermare l'eliminazione ===
    function confirmDelete() {
        if (!entityToDelete) {
            hideConfirmationDialog();
            return;
        }
        
        const name = entityToDelete.name;
        
        // Disabilita i pulsanti di conferma
        confirmDeleteBtn.disabled = true;
        confirmCancelBtn.disabled = true;
        confirmDeleteBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Eliminazione...';
        
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
                showNotification(`Tipo di entità "${name}" eliminato con successo`, 'success');
                loadEntityTypes();
            } else {
                showNotification(`Errore: ${data.message}`, 'danger');
            }
        })
        .catch(error => {
            console.error('Errore durante l\'eliminazione:', error);
            showNotification(`Errore durante l'eliminazione: ${error.message}`, 'danger');
        })
        .finally(() => {
            hideConfirmationDialog();
            
            // Ripristina i pulsanti di conferma
            confirmDeleteBtn.disabled = false;
            confirmCancelBtn.disabled = false;
            confirmDeleteBtn.textContent = 'Elimina';
        });
    }
    
    // === Gestione dei tasti di scelta rapida ===
    document.addEventListener('keydown', function(e) {
        // Escape per chiudere il form o la finestra di conferma
        if (e.key === 'Escape') {
            const confirmationModal = bootstrap.Modal.getInstance(document.getElementById('confirmation-dialog'));
            if (confirmationModal) {
                confirmationModal.hide();
            } else if (!entityTypeFormContainer.classList.contains('d-none')) {
                hideForm();
            }
        }
    });

    // === Aggiungi gestione del cambiamento della categoria ===
    if (categorySelect) {
        categorySelect.addEventListener('change', function() {
            // Salva la categoria originale quando si carica l'entità
            if (!this.dataset.originalCategory && editMode.value === 'edit') {
                this.dataset.originalCategory = this.value;
            }
            
            // Evidenzia visivamente il cambio di categoria
            if (editMode.value === 'edit' && this.value !== this.dataset.originalCategory) {
                this.classList.add('border-warning', 'bg-warning', 'bg-opacity-10');
            } else {
                this.classList.remove('border-warning', 'bg-warning', 'bg-opacity-10');
            }
        });
    }
    
    // === Esponi funzioni globali ===
    window.showNotification = showNotification;
    window.setLoading = setLoading;
    window.renderEntityTypes = renderEntityTypes;
    window.showCreateForm = showCreateForm;
    window.hideForm = hideForm;
    window.updateColorPreview = updateColorPreview;
    window.validateEntityName = validateEntityName;
    window.validateMetadataSchema = validateMetadataSchema;
    window.validatePatterns = validatePatterns;
    window.showDeleteConfirmation = showDeleteConfirmation;
});