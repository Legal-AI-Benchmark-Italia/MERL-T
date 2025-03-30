document.addEventListener('DOMContentLoaded', function() {
    // Elementi DOM
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
    const notification = document.getElementById('notification');
    const confirmationDialog = document.getElementById('confirmation-dialog');
    const confirmationMessage = document.getElementById('confirmation-message');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    const confirmCancelBtn = document.getElementById('confirm-cancel-btn');
    const loadingIndicator = document.getElementById('loading-indicator');
    const emptyState = document.getElementById('empty-state');
    const entitySearch = document.getElementById('entity-search');
    const categoryFilter = document.getElementById('category-filter');
    const nameValidation = document.getElementById('name-validation');
    const metadataValidation = document.getElementById('metadata-validation');
    const patternsValidation = document.getElementById('patterns-validation');
    const testPatternsBtn = document.getElementById('test-patterns-btn');
    const testText = document.getElementById('test-text');
    const testResults = document.getElementById('test-results');
    const testOutput = document.getElementById('test-output');
    
    // Stato dell'applicazione - CORREZIONE: inizializza allEntities come array vuoto
    let entityToDelete = null;
    let allEntities = [];
    let isLoading = true;
    
    function setLoading(loading) {
        isLoading = loading;
        
        // Debug logging
        console.log('Setting loading state:', loading);
        console.log('Entity types count:', Array.isArray(allEntities) ? allEntities.length : 'not an array');
        
        // Make sure DOM elements exist
        if (!loadingIndicator || !entityTypesTable || !emptyState) {
            console.error('DOM elements not found:', {
                loadingIndicator: !!loadingIndicator,
                entityTypesTable: !!entityTypesTable,
                emptyState: !!emptyState
            });
            return;
        }
        
        if (loading) {
            loadingIndicator.style.display = 'flex';
            entityTypesTable.style.display = 'none';
            emptyState.style.display = 'none';
        } else {
            loadingIndicator.style.display = 'none';
            
            if (!Array.isArray(allEntities) || allEntities.length === 0) {
                emptyState.style.display = 'block';
                entityTypesTable.style.display = 'none';
            } else {
                emptyState.style.display = 'none';
                entityTypesTable.style.display = 'table';
            }
        }
    }
    
    // Carica i tipi di entità all'avvio
    loadEntityTypes();
    
    // Event listeners
    addEntityTypeBtn.addEventListener('click', showCreateForm);
    if (addFirstEntityBtn) {
        addFirstEntityBtn.addEventListener('click', showCreateForm);
    }
    cancelBtn.addEventListener('click', hideForm);
    closeFormBtn.addEventListener('click', hideForm);
    entityTypeForm.addEventListener('submit', handleFormSubmit);
    colorInput.addEventListener('input', updateColorPreview);
    confirmDeleteBtn.addEventListener('click', confirmDelete);
    confirmCancelBtn.addEventListener('click', hideConfirmationDialog);
    entitySearch.addEventListener('input', filterEntities);
    categoryFilter.addEventListener('change', filterEntities);
    testPatternsBtn.addEventListener('click', testPatterns);
    
    // Validazione in tempo reale
    nameInput.addEventListener('input', validateEntityName);
    metadataSchemaInput.addEventListener('input', validateMetadataSchema);
    patternsInput.addEventListener('input', validatePatterns);
    
    // Funzione per mostrare una notifica
    function showNotification(message, type = 'info') {
        notification.textContent = message;
        notification.className = `notification ${type} show`;
        
        setTimeout(() => {
            notification.className = 'notification';
        }, 5000);
    }
    
    // Funzione per caricare i tipi di entità - CORREZIONE: gestione degli errori migliorata
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
                // CORREZIONE: verifica che i dati siano nel formato atteso
                if (data && data.status === 'success' && Array.isArray(data.entity_types)) {
                    allEntities = data.entity_types;
                } else {
                    console.error('Formato risposta non valido:', data);
                    allEntities = [];
                    showNotification('Errore nel formato dei dati ricevuti', 'error');
                }
                
                renderEntityTypes(allEntities);
            })
            .catch(error => {
                console.error('Errore:', error);
                allEntities = [];
                showNotification(`Errore durante il caricamento dei tipi di entità: ${error.message}`, 'error');
            })
            .finally(() => {
                setLoading(false);
            });
    }
    
    // Funzione per filtrare le entità
    function filterEntities() {
        const searchTerm = entitySearch.value.toLowerCase();
        const categoryValue = categoryFilter.value;
        
        // CORREZIONE: assicuriamoci che allEntities sia un array
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
            td.className = 'empty-results';
            tr.appendChild(td);
            tbody.appendChild(tr);
        }
    }
    
    // Funzione per visualizzare i tipi di entità nella tabella - CORREZIONE: gestione di casi limite
    function renderEntityTypes(entityTypes) {
        // Svuota la tabella
        const tbody = entityTypesTable.querySelector('tbody');
        tbody.innerHTML = '';
        
        // CORREZIONE: verifica che entityTypes sia un array
        if (!Array.isArray(entityTypes)) {
            console.error('entityTypes non è un array:', entityTypes);
            entityTypes = [];
        }
        
        // CORREZIONE: aggiunta una gestione esplicita di zero entità
        if (entityTypes.length === 0) {
            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = 5;
            td.textContent = 'Nessun tipo di entità trovato';
            td.className = 'empty-results';
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
            tr.appendChild(nameTd);
            
            // Nome visualizzato
            const displayNameTd = document.createElement('td');
            displayNameTd.textContent = entityType.display_name;
            tr.appendChild(displayNameTd);
            
            // Categoria
            const categoryTd = document.createElement('td');
            categoryTd.textContent = getCategoryDisplayName(entityType.category);
            tr.appendChild(categoryTd);
            
            // Colore
            const colorTd = document.createElement('td');
            const colorCell = document.createElement('div');
            colorCell.className = 'color-cell';
            
            const colorPreview = document.createElement('span');
            colorPreview.className = 'color-preview';
            colorPreview.style.backgroundColor = entityType.color;
            
            const colorText = document.createElement('span');
            colorText.textContent = entityType.color;
            
            colorCell.appendChild(colorPreview);
            colorCell.appendChild(colorText);
            colorTd.appendChild(colorCell);
            tr.appendChild(colorTd);
            
            // Azioni
            const actionsTd = document.createElement('td');
            const actionButtons = document.createElement('div');
            actionButtons.className = 'action-buttons';
            
            const editBtn = document.createElement('button');
            editBtn.className = 'edit-btn';
            editBtn.innerHTML = '<span class="icon">✏️</span> Modifica';
            editBtn.title = 'Modifica il tipo di entità';
            editBtn.addEventListener('click', () => showEditForm(entityType));
            
            actionButtons.appendChild(editBtn);
            
            // Aggiungi il pulsante di eliminazione solo per i tipi di entità personalizzati
            if (entityType.category === 'custom') {
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'delete-btn';
                deleteBtn.innerHTML = '<span class="icon">🗑️</span> Elimina';
                deleteBtn.title = 'Elimina il tipo di entità';
                deleteBtn.addEventListener('click', () => showDeleteConfirmation(entityType));
                
                actionButtons.appendChild(deleteBtn);
            }
            
            actionsTd.appendChild(actionButtons);
            tr.appendChild(actionsTd);
            
            tbody.appendChild(tr);
        });
    }
    
    // Funzione per ottenere il nome visualizzato della categoria
    function getCategoryDisplayName(category) {
        const categories = {
            'normative': 'Normativa',
            'jurisprudence': 'Giurisprudenziale',
            'concepts': 'Concetto',
            'custom': 'Personalizzata'
        };
        
        return categories[category] || category;
    }
    
    // Funzione per mostrare il form di creazione
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
        
        // Pulisci i messaggi di validazione
        clearValidationMessages();
        
        // Nascondi i risultati del test
        testResults.classList.add('hidden');
        
        // Mostra il form
        entityTypeFormContainer.classList.remove('hidden');
        
        // Scorri fino al form
        entityTypeFormContainer.scrollIntoView({behavior: 'smooth'});
        
        // Focus sul campo del nome
        nameInput.focus();
    }
    
    // Funzione per mostrare il form di modifica
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
        
        // Pulisci i messaggi di validazione
        clearValidationMessages();
        
        // Nascondi i risultati del test
        testResults.classList.add('hidden');
        
        // Mostra il form
        entityTypeFormContainer.classList.remove('hidden');
        
        // Scorri fino al form
        entityTypeFormContainer.scrollIntoView({behavior: 'smooth'});
        
        // Focus sul campo del nome visualizzato
        displayNameInput.focus();
    }
    
    // Funzione per nascondere il form
    function hideForm() {
        entityTypeFormContainer.classList.add('hidden');
        // Pulisci i messaggi di validazione
        clearValidationMessages();
    }
    
    // Funzione per aggiornare l'anteprima del colore
    function updateColorPreview() {
        const colorValue = colorInput.value;
        colorPreview.textContent = colorValue;
        colorSample.style.backgroundColor = colorValue;
        
        // Calcola il colore del testo in base al colore di sfondo
        const rgb = hexToRgb(colorValue);
        const luminance = calculateLuminance(rgb.r, rgb.g, rgb.b);
        colorSample.style.color = luminance > 0.5 ? '#000000' : '#FFFFFF';
    }
    
    // Funzione per convertire un colore HEX in RGB
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
    
    // Funzione per calcolare la luminanza di un colore
    function calculateLuminance(r, g, b) {
        const a = [r, g, b].map(function(v) {
            v /= 255;
            return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
        });
        return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
    }
    
    // Funzione per validare il nome dell'entità
    function validateEntityName() {
        const name = nameInput.value;
        
        // Resetta il messaggio di validazione
        nameValidation.textContent = '';
        nameValidation.className = 'validation-message';
        
        // Controlla se il nome è vuoto
        if (!name) {
            nameValidation.textContent = 'Il nome è obbligatorio';
            nameValidation.classList.add('error');
            return false;
        }
        
        // Controlla se il nome è in maiuscolo
        if (name !== name.toUpperCase()) {
            nameValidation.textContent = 'Il nome deve essere in maiuscolo';
            nameValidation.classList.add('error');
            return false;
        }
        
        // Controlla se il nome contiene spazi
        if (name.includes(' ')) {
            nameValidation.textContent = 'Il nome non deve contenere spazi';
            nameValidation.classList.add('error');
            return false;
        }
        
        // Controlla se il nome è già utilizzato (solo in modalità creazione)
        if (editMode.value === 'create') {
            const existingEntity = allEntities.find(entity => entity.name === name);
            if (existingEntity) {
                nameValidation.textContent = 'Questo nome è già in uso';
                nameValidation.classList.add('error');
                return false;
            }
        }
        
        nameValidation.textContent = 'Nome valido';
        nameValidation.classList.add('success');
        return true;
    }
    
    // Funzione per validare lo schema dei metadati
    function validateMetadataSchema() {
        const schema = metadataSchemaInput.value.trim();
        
        // Resetta il messaggio di validazione
        metadataValidation.textContent = '';
        metadataValidation.className = 'validation-message';
        
        // Se lo schema è vuoto, è valido
        if (!schema) {
            return true;
        }
        
        // Prova a parsare lo schema JSON
        try {
            JSON.parse(schema);
            metadataValidation.textContent = 'Schema JSON valido';
            metadataValidation.classList.add('success');
            return true;
        } catch (error) {
            metadataValidation.textContent = `Schema JSON non valido: ${error.message}`;
            metadataValidation.classList.add('error');
            return false;
        }
    }
    
    // Funzione per validare i pattern
    function validatePatterns() {
        const patterns = patternsInput.value.trim();
        
        // Resetta il messaggio di validazione
        patternsValidation.textContent = '';
        patternsValidation.className = 'validation-message';
        
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
            patternsValidation.textContent = 'Pattern validi';
            patternsValidation.classList.add('success');
            return true;
        } else {
            patternsValidation.textContent = `Pattern non valido: "${invalidPattern}" - ${errorMessage}`;
            patternsValidation.classList.add('error');
            return false;
        }
    }
    
    // Funzione per testare i pattern
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
        testResults.classList.remove('hidden');
    }
    
    // Funzione per pulire i messaggi di validazione
    function clearValidationMessages() {
        nameValidation.textContent = '';
        nameValidation.className = 'validation-message';
        
        metadataValidation.textContent = '';
        metadataValidation.className = 'validation-message';
        
        patternsValidation.textContent = '';
        patternsValidation.className = 'validation-message';
    }
    
    // Funzione per gestire l'invio del form
    function handleFormSubmit(e) {
        e.preventDefault();
        
        // Valida il form
        const isNameValid = validateEntityName();
        const isMetadataValid = validateMetadataSchema();
        const arePatternsValid = validatePatterns();
        
        if (!isNameValid || !isMetadataValid || !arePatternsValid) {
            showNotification('Correggi gli errori di validazione prima di salvare', 'error');
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
                    showNotification('Schema dei metadati non valido. Deve essere in formato JSON.', 'error');
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
                        showNotification(`Pattern non valido: "${pattern}" - ${error.message}`, 'error');
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
            saveBtn.innerHTML = '<span class="spinner-sm"></span> Salvataggio...';
            
            // Determina se stiamo creando o aggiornando
            const isCreating = editMode.value === 'create';
            
            if (isCreating) {
                createEntityType(data);
            } else {
                updateEntityType(originalName.value, data);
            }
        } catch (error) {
            console.error('Errore:', error);
            showNotification(`Errore durante il salvataggio: ${error.message}`, 'error');
            
            // Ripristina il pulsante di salvataggio
            saveBtn.disabled = false;
            saveBtn.textContent = editMode.value === 'create' ? 'Crea' : 'Aggiorna';
        }
    }
    
    // Funzione per creare un nuovo tipo di entità
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
                showNotification(`Errore: ${data.message}`, 'error');
            }
            
            // Ripristina il pulsante di salvataggio
            saveBtn.disabled = false;
            saveBtn.textContent = 'Crea';
        })
        .catch(error => {
            console.error('Errore:', error);
            showNotification(`Errore durante la creazione: ${error.message}`, 'error');
            
            // Ripristina il pulsante di salvataggio
            saveBtn.disabled = false;
            saveBtn.textContent = 'Crea';
        });
    }
    
    // Funzione per aggiornare un tipo di entità esistente
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
        .then(data => {
            if (data.status === 'success') {
                showNotification(`Tipo di entità "${data.entity_type.name}" aggiornato con successo`, 'success');
                hideForm();
                loadEntityTypes();
            } else {
                showNotification(`Errore: ${data.message}`, 'error');
            }
            
            // Ripristina il pulsante di salvataggio
            saveBtn.disabled = false;
            saveBtn.textContent = 'Aggiorna';
        })
        .catch(error => {
            console.error('Errore:', error);
            showNotification(`Errore durante l'aggiornamento: ${error.message}`, 'error');
            
            // Ripristina il pulsante di salvataggio
            saveBtn.disabled = false;
            saveBtn.textContent = 'Aggiorna';
        });
    }
    
    // Funzione per mostrare la conferma di eliminazione
    function showDeleteConfirmation(entityType) {
        entityToDelete = entityType;
        confirmationMessage.textContent = `Sei sicuro di voler eliminare il tipo di entità "${entityType.name}"?`;
        confirmationDialog.classList.remove('hidden');
        
        // Focus sul pulsante di cancellazione
        setTimeout(() => {
            confirmCancelBtn.focus();
        }, 100);
    }
    
    // Funzione per nascondere la finestra di conferma
    function hideConfirmationDialog() {
        confirmationDialog.classList.add('hidden');
        entityToDelete = null;
    }
    
    // Funzione per confermare l'eliminazione
    function confirmDelete() {
        if (!entityToDelete) {
            hideConfirmationDialog();
            return;
        }
        
        const name = entityToDelete.name;
        
        // Disabilita i pulsanti di conferma
        confirmDeleteBtn.disabled = true;
        confirmCancelBtn.disabled = true;
        confirmDeleteBtn.innerHTML = '<span class="spinner-sm"></span> Eliminazione...';
        
        fetch(`/api/entity_types/${name}`, {
            method: 'DELETE'
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
                showNotification(`Errore: ${data.message}`, 'error');
            }
        })
        .catch(error => {
            console.error('Errore:', error);
            showNotification(`Errore durante l'eliminazione: ${error.message}`, 'error');
        })
        .finally(() => {
            hideConfirmationDialog();
            
            // Ripristina i pulsanti di conferma
            confirmDeleteBtn.disabled = false;
            confirmCancelBtn.disabled = false;
            confirmDeleteBtn.textContent = 'Elimina';
        });
    }
    
    // Gestione dei tasti di scelta rapida
    document.addEventListener('keydown', function(e) {
        // Escape per chiudere il form o la finestra di conferma
        if (e.key === 'Escape') {
            if (!confirmationDialog.classList.contains('hidden')) {
                hideConfirmationDialog();
            } else if (!entityTypeFormContainer.classList.contains('hidden')) {
                hideForm();
            }
        }
    });
});