document.addEventListener('DOMContentLoaded', function() {
    // Elementi DOM
    const entityTypesTable = document.getElementById('entity-types-table');
    const entityTypeForm = document.getElementById('entity-type-form');
    const entityTypeFormContainer = document.getElementById('entity-type-form-container');
    const formTitle = document.getElementById('form-title');
    const addEntityTypeBtn = document.getElementById('add-entity-type-btn');
    const cancelBtn = document.getElementById('cancel-btn');
    const saveBtn = document.getElementById('save-btn');
    const editMode = document.getElementById('edit-mode');
    const originalName = document.getElementById('original-name');
    const nameInput = document.getElementById('entity-name');
    const displayNameInput = document.getElementById('display-name');
    const categorySelect = document.getElementById('category');
    const colorInput = document.getElementById('color');
    const colorPreview = document.getElementById('color-preview');
    const metadataSchemaInput = document.getElementById('metadata-schema');
    const patternsInput = document.getElementById('patterns');
    const notification = document.getElementById('notification');
    const confirmationDialog = document.getElementById('confirmation-dialog');
    const confirmationMessage = document.getElementById('confirmation-message');
    const confirmDeleteBtn = document.getElementById('confirm-delete-btn');
    const confirmCancelBtn = document.getElementById('confirm-cancel-btn');
    
    // Stato dell'applicazione
    let entityToDelete = null;
    
    // Carica i tipi di entità all'avvio
    loadEntityTypes();
    
    // Event listeners
    addEntityTypeBtn.addEventListener('click', showCreateForm);
    cancelBtn.addEventListener('click', hideForm);
    entityTypeForm.addEventListener('submit', handleFormSubmit);
    colorInput.addEventListener('input', updateColorPreview);
    confirmDeleteBtn.addEventListener('click', confirmDelete);
    confirmCancelBtn.addEventListener('click', hideConfirmationDialog);
    
    // Funzione per mostrare una notifica
    function showNotification(message, type = 'info') {
        notification.textContent = message;
        notification.className = `notification ${type} show`;
        
        setTimeout(() => {
            notification.className = 'notification';
        }, 3000);
    }
    
    // Funzione per caricare i tipi di entità
    function loadEntityTypes() {
        fetch('/api/entity_types')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Errore HTTP: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.status === 'success') {
                    renderEntityTypes(data.entity_types);
                } else {
                    showNotification(`Errore nel caricamento dei tipi di entità: ${data.message}`, 'error');
                }
            })
            .catch(error => {
                console.error('Errore:', error);
                showNotification(`Errore durante il caricamento dei tipi di entità: ${error.message}`, 'error');
            });
    }
    
    // Funzione per visualizzare i tipi di entità nella tabella
    function renderEntityTypes(entityTypes) {
        // Ordina i tipi di entità per categoria e nome
        entityTypes.sort((a, b) => {
            if (a.category !== b.category) {
                return a.category.localeCompare(b.category);
            }
            return a.name.localeCompare(b.name);
        });
        
        // Svuota la tabella
        const tbody = entityTypesTable.querySelector('tbody');
        tbody.innerHTML = '';
        
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
            editBtn.textContent = 'Modifica';
            editBtn.addEventListener('click', () => showEditForm(entityType));
            
            actionButtons.appendChild(editBtn);
            
            // Aggiungi il pulsante di eliminazione solo per i tipi di entità personalizzati
            if (entityType.category === 'custom') {
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'delete-btn';
                deleteBtn.textContent = 'Elimina';
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
        
        // Mostra il form
        entityTypeFormContainer.classList.remove('hidden');
        
        // Scorri fino al form
        entityTypeFormContainer.scrollIntoView({behavior: 'smooth'});
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
        
        // Mostra il form
        entityTypeFormContainer.classList.remove('hidden');
        
        // Scorri fino al form
        entityTypeFormContainer.scrollIntoView({behavior: 'smooth'});
    }
    
    // Funzione per nascondere il form
    function hideForm() {
        entityTypeFormContainer.classList.add('hidden');
    }
    
    // Funzione per aggiornare l'anteprima del colore
    function updateColorPreview() {
        colorPreview.textContent = colorInput.value;
    }
    
    // Funzione per gestire l'invio del form
    function handleFormSubmit(e) {
        e.preventDefault();
        
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
        })
        .catch(error => {
            console.error('Errore:', error);
            showNotification(`Errore durante la creazione: ${error.message}`, 'error');
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
        })
        .catch(error => {
            console.error('Errore:', error);
            showNotification(`Errore durante l'aggiornamento: ${error.message}`, 'error');
        });
    }
    
    // Funzione per mostrare la conferma di eliminazione
    function showDeleteConfirmation(entityType) {
        entityToDelete = entityType;
        confirmationMessage.textContent = `Sei sicuro di voler eliminare il tipo di entità "${entityType.name}"?`;
        confirmationDialog.classList.remove('hidden');
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
        });
    }
});