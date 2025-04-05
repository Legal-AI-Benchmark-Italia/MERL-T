/**
 * indexPage.js
 * Logic for the Home/Index page (document list, upload, export).
 */
import { api } from './api.js';
import { showNotification, showLoading, hideLoading } from './ui.js';

let renameModalInstance = null;
let confirmDeleteModalInstance = null;
let docToDeleteId = null;
let docToDeleteTitle = '';

function initRenameModal() {
    const renameModalEl = document.getElementById('renameModal');
    if (!renameModalEl) return;
    renameModalInstance = new bootstrap.Modal(renameModalEl);

    const form = document.getElementById('rename-form');
    const docIdInput = document.getElementById('rename-doc-id');
    const titleInput = document.getElementById('new-doc-title');
    const saveBtn = document.getElementById('save-rename-btn');

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const docId = docIdInput.value;
        const newTitle = titleInput.value.trim();
        if (!docId || !newTitle) return;

        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Salvataggio...';
        showLoading();

        try {
            await api.updateDocument(docId, { title: newTitle });
            // Update UI
            const cardTitle = document.querySelector(`.doc-card-col[data-doc-id="${docId}"] .document-title`);
            const renameBtn = document.querySelector(`.doc-card-col[data-doc-id="${docId}"] .rename-doc-btn`);
            if (cardTitle) cardTitle.textContent = newTitle;
            if (renameBtn) renameBtn.dataset.docTitle = newTitle;

            showNotification('Documento rinominato con successo.', 'success');
            renameModalInstance.hide();
        } catch (error) {
            showNotification(`Errore durante la rinomina: ${error.message}`, 'danger');
        } finally {
            saveBtn.disabled = false;
            saveBtn.innerHTML = 'Salva';
            hideLoading();
        }
    });
}

function initConfirmDeleteModal() {
    const confirmModalEl = document.getElementById('confirmDeleteModal');
    if (!confirmModalEl) return;
    confirmDeleteModalInstance = new bootstrap.Modal(confirmModalEl);

    const confirmBtn = document.getElementById('confirm-delete-btn');
    confirmBtn.addEventListener('click', async () => {
        if (!docToDeleteId) return;

        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Eliminazione...';
        showLoading();

        try {
            await api.deleteDocument(docToDeleteId);
            // Remove card from UI
            const cardToRemove = document.querySelector(`.doc-card-col[data-doc-id="${docToDeleteId}"]`);
            if (cardToRemove) {
                cardToRemove.remove();
            }
            showNotification(`Documento "${docToDeleteTitle}" eliminato con successo.`, 'success');
            confirmDeleteModalInstance.hide();

            // Check if list is now empty
            if (document.querySelectorAll('.doc-card-col').length === 0) {
                // Optionally display an empty state message or reload
                 window.location.reload(); // Simple reload for now
            }

        } catch (error) {
            showNotification(`Errore durante l'eliminazione: ${error.message}`, 'danger');
        } finally {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = 'Elimina';
            docToDeleteId = null;
            docToDeleteTitle = '';
            hideLoading();
        }
    });
}

function handleDocumentActions() {
    const docList = document.getElementById('document-list');
    if (!docList) return;

    docList.addEventListener('click', (event) => {
        const target = event.target;
        const deleteBtn = target.closest('.delete-doc-btn');
        const renameBtn = target.closest('.rename-doc-btn');

        if (deleteBtn && confirmDeleteModalInstance) {
            docToDeleteId = deleteBtn.dataset.docId;
            docToDeleteTitle = deleteBtn.dataset.docTitle || `ID: ${docToDeleteId}`;
            document.getElementById('doc-to-delete-title').textContent = docToDeleteTitle;
            confirmDeleteModalInstance.show();
        } else if (renameBtn && renameModalInstance) {
            const docId = renameBtn.dataset.docId;
            const currentTitle = renameBtn.dataset.docTitle;
            document.getElementById('rename-doc-id').value = docId;
            document.getElementById('new-doc-title').value = currentTitle;
            renameModalInstance.show();
        }
    });
}

// La funzione handleUpload gestisce l'upload di file multipl
function handleUpload() {
    const form = document.getElementById('upload-form');
    const fileInput = document.getElementById('document-files');
    const dropArea = document.getElementById('drop-area');
    const progressContainer = document.getElementById('upload-progress-container');
    const totalProgressBar = document.getElementById('total-progress-bar');
    const fileListEl = document.getElementById('file-list');
    const submitBtn = form.querySelector('button[type="submit"]');
    const processFolder = document.getElementById('process-folder-structure');
    
    // Aggiungi bordo tratteggiato al drop area
    if (dropArea) {
        dropArea.style.borderStyle = 'dashed';
        dropArea.style.borderWidth = '2px';
        dropArea.style.borderColor = '#ccc';
    }
    
    // Funzione per aggiornare l'interfaccia durante il caricamento
    function updateProgress(processed, total, currentFile = null) {
        const percentage = Math.round((processed / total) * 100);
        totalProgressBar.style.width = `${percentage}%`;
        totalProgressBar.textContent = `${percentage}%`;
        totalProgressBar.setAttribute('aria-valuenow', percentage);
        
        // Se è fornito il file corrente, aggiorna lo stato nella lista
        if (currentFile) {
            const fileId = `file-${currentFile.name.replace(/\W/g, '')}`;
            const fileEl = document.getElementById(fileId);
            if (fileEl) {
                fileEl.querySelector('.file-status').innerHTML = `<span class="text-success">Caricato</span>`;
            }
        }
    }
    
    // Configurazione del drag & drop (se supportato dal browser)
    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });
        
        // Stili per il drag hover
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => {
                dropArea.classList.add('bg-primary', 'bg-opacity-10');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => {
                dropArea.classList.remove('bg-primary', 'bg-opacity-10');
            }, false);
        });
        
        // Gestione del drop
        dropArea.addEventListener('drop', (e) => {
            const droppedItems = e.dataTransfer.items;
            const filesArray = [];
            
            // Se sono presenti elementi rilasciati
            if (droppedItems && droppedItems.length > 0) {
                // Verifica se webkitGetAsEntry è supportato (per cartelle)
                if (droppedItems[0].webkitGetAsEntry) {
                    for (let i = 0; i < droppedItems.length; i++) {
                        const entry = droppedItems[i].webkitGetAsEntry();
                        if (entry) {
                            traverseFileTree(entry, '', filesArray, processFolder && processFolder.checked);
                        }
                    }
                } else {
                    // Fallback per browser che non supportano webkitGetAsEntry
                    const droppedFiles = e.dataTransfer.files;
                    for (let i = 0; i < droppedFiles.length; i++) {
                        filesArray.push(droppedFiles[i]);
                    }
                    // Aggiorna l'input file con i file droppati (se possibile)
                    try {
                        if (window.DataTransfer && window.DataTransfer.prototype.items) {
                            const dt = new DataTransfer();
                            filesArray.forEach(file => dt.items.add(file));
                            fileInput.files = dt.files;
                        }
                        showSelectedFiles(filesArray);
                    } catch (e) {
                        console.error("Impossibile impostare i file nel campo input:", e);
                        showNotification("Il browser non supporta completamente drag & drop. Usa il selettore file.", "warning");
                    }
                }
            }
        }, false);
    }
    
    // Funzione ricorsiva per attraversare la struttura delle cartelle
    function traverseFileTree(item, path, filesArray, preservePath) {
        path = path || '';
        if (item.isFile) {
            item.file(file => {
                // Verifica se è un formato supportato
                const ext = file.name.split('.').pop().toLowerCase();
                const allowedExts = ['txt', 'md', 'html', 'xml', 'json', 'csv'];
                
                if (allowedExts.includes(ext)) {
                    // Se preservePath è true, mantieni il percorso nella cartella
                    if (preservePath && path) {
                        // Creare un nuovo file con il percorso nel nome o salvare il percorso come metadata
                        file.relativePath = path + file.name;
                    }
                    filesArray.push(file);
                    showSelectedFiles(filesArray);
                }
            });
        } else if (item.isDirectory) {
            // Leggi il contenuto della directory
            const dirReader = item.createReader();
            dirReader.readEntries(entries => {
                for (let i = 0; i < entries.length; i++) {
                    // Costruisci il percorso ricorsivamente
                    traverseFileTree(
                        entries[i], 
                        preservePath ? path + item.name + '/' : '', 
                        filesArray,
                        preservePath
                    );
                }
            });
        }
    }
    
    // Mostra i file selezionati
    function showSelectedFiles(files) {
        if (files.length > 0 && fileListEl) {
            progressContainer.classList.remove('d-none');
            fileListEl.innerHTML = '';
            
            files.forEach(file => {
                const fileId = `file-${file.name.replace(/\W/g, '')}`;
                const relativePath = file.relativePath ? file.relativePath : file.name;
                
                const fileItem = document.createElement('div');
                fileItem.id = fileId;
                fileItem.className = 'mb-1 d-flex justify-content-between';
                fileItem.innerHTML = `
                    <div class="text-truncate" title="${relativePath}">${relativePath}</div>
                    <div class="file-status"><span class="text-muted">In attesa...</span></div>
                `;
                fileListEl.appendChild(fileItem);
            });
        } else if (progressContainer) {
            progressContainer.classList.add('d-none');
        }
    }
    
    // Gestione della selezione dei file tramite input
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            const files = fileInput.files ? Array.from(fileInput.files) : [];
            showSelectedFiles(files);
        });
    }
    
    // Gestione dell'invio del form
    if (form) {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            
            if (!fileInput || !fileInput.files) {
                showNotification('Componente di input file non trovato o non supportato dal browser.', 'danger');
                return;
            }
            
            const files = Array.from(fileInput.files);
            
            if (files.length === 0) {
                showNotification('Seleziona almeno un file da caricare.', 'warning');
                return;
            }
            
            // Verifica la dimensione totale
            const totalSize = files.reduce((sum, file) => sum + file.size, 0);
            const maxTotalSize = 50 * 1024 * 1024; // 50MB come esempio
            
            if (totalSize > maxTotalSize) {
                showNotification(`La dimensione totale (${Math.round(totalSize/1024/1024)}MB) supera il limite di ${Math.round(maxTotalSize/1024/1024)}MB.`, 'warning');
                return;
            }
            
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Caricamento...';
            }
            
            showLoading();
            
            try {
                // Mostra il contenitore di progresso
                if (progressContainer) {
                    progressContainer.classList.remove('d-none');
                }
                
                // Processa i file uno alla volta
                let processed = 0;
                let successCount = 0;
                let errorCount = 0;
                
                for (const file of files) {
                    try {
                        const formData = new FormData();
                        formData.append('file', file);
                        
                        // Aggiungi informazioni sul percorso se necessario
                        if (file.relativePath) {
                            formData.append('relative_path', file.relativePath);
                        }
                        
                        // Opzione per mantenere la struttura della cartella
                        if (processFolder && processFolder.checked) {
                            formData.append('preserve_path', 'true');
                        }
                        
                        const result = await api.uploadDocument(formData);
                        
                        if (result && result.status === 'success') {
                            successCount++;
                        }
                    } catch (fileError) {
                        errorCount++;
                        console.error(`Errore nel caricamento del file ${file.name}:`, fileError);
                        
                        // Aggiorna lo stato del file nell'UI
                        const fileEl = document.getElementById(`file-${file.name.replace(/\W/g, '')}`);
                        if (fileEl) {
                            fileEl.querySelector('.file-status').innerHTML = `<span class="text-danger">Errore</span>`;
                        }
                    }
                    
                    // Aggiorna il progresso
                    processed++;
                    if (totalProgressBar) {
                        updateProgress(processed, files.length, file);
                    }
                }
                
                // Riepilogo finale
                if (successCount > 0) {
                    if (successCount === 1) {
                        showNotification('Documento caricato con successo!', 'success');
                    } else {
                        showNotification(`${successCount} documenti caricati con successo!`, 'success');
                    }
                    // Ricarica la pagina o aggiorna l'elenco dei documenti
                    setTimeout(() => window.location.reload(), 2000);
                }
                
                if (errorCount > 0) {
                    showNotification(`Si sono verificati errori durante il caricamento di ${errorCount} file.`, 'warning');
                }
            } catch (error) {
                console.error("Errore generale durante l'upload:", error);
                showNotification(`Errore durante il caricamento: ${error.message}`, 'danger');
            } finally {
                hideLoading();
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-cloud-upload-alt me-2"></i>Carica';
                }
                if (form) {
                    form.reset(); // Pulisce il form
                }
                if (progressContainer) {
                    setTimeout(() => {
                        progressContainer.classList.add('d-none');
                    }, 3000); // Nascondi la barra di progresso dopo qualche secondo
                }
            }
        });
    }
}

function handleExport() {
    const exportJsonBtn = document.getElementById('export-json-btn');
    const exportSpacyBtn = document.getElementById('export-spacy-btn');

    if (exportJsonBtn) {
        exportJsonBtn.addEventListener('click', () => {
            // Redirect to trigger download
            window.location.href = '/api/export_annotations?format=json&download=true';
        });
    }
     if (exportSpacyBtn) {
        exportSpacyBtn.addEventListener('click', () => {
             // Redirect to trigger download
            window.location.href = '/api/export_annotations?format=spacy&download=true';
        });
    }
}

export function initIndexPage() {
    console.log('Initializing Index Page...');
    initRenameModal();
    initConfirmDeleteModal();
    handleUpload();
    handleDocumentActions();
    handleExport();
}