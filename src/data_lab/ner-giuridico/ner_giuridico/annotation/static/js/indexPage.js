/**
 * indexPage.js
 * Complete enhanced version with folder structure support
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
            
            // Refresh the document list to show the updated title
            refreshDocumentList();
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

            // Refresh the document list
            refreshDocumentList();

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

// Enhanced function to handle multiple files and folder structure
function handleUpload() {
    const form = document.getElementById('upload-form');
    const fileInput = document.getElementById('document-files');
    const dropArea = document.getElementById('drop-area');
    const progressContainer = document.getElementById('upload-progress-container');
    const totalProgressBar = document.getElementById('total-progress-bar');
    const fileListEl = document.getElementById('file-list');
    const submitBtn = form?.querySelector('button[type="submit"]');
    const processFolder = document.getElementById('process-folder-structure');
    
    // Add dashed border to drop area
    if (dropArea) {
        dropArea.style.borderStyle = 'dashed';
        dropArea.style.borderWidth = '2px';
        dropArea.style.borderColor = '#ccc';
    }
    
    // Function to update UI during upload
    function updateProgress(processed, total, currentFile = null) {
        const percentage = Math.round((processed / total) * 100);
        if (totalProgressBar) {
            totalProgressBar.style.width = `${percentage}%`;
            totalProgressBar.textContent = `${percentage}%`;
            totalProgressBar.setAttribute('aria-valuenow', percentage);
        }
        
        // If current file is provided, update its status in the list
        if (currentFile && fileListEl) {
            const fileId = `file-${currentFile.name.replace(/\W/g, '')}`;
            const fileEl = document.getElementById(fileId);
            if (fileEl) {
                fileEl.querySelector('.file-status').innerHTML = `<span class="text-success">Caricato</span>`;
            }
        }
    }
    
    // Setup drag & drop (if supported by browser)
    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });
        
        // Styles for drag hover
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
        
        // Handle drop
        dropArea.addEventListener('drop', (e) => {
            const droppedItems = e.dataTransfer.items;
            const filesArray = [];
            
            // If dropped items are present
            if (droppedItems && droppedItems.length > 0) {
                // Check if webkitGetAsEntry is supported (for folders)
                if (droppedItems[0].webkitGetAsEntry) {
                    for (let i = 0; i < droppedItems.length; i++) {
                        const entry = droppedItems[i].webkitGetAsEntry();
                        if (entry) {
                            traverseFileTree(entry, '', filesArray, processFolder && processFolder.checked);
                        }
                    }
                } else {
                    // Fallback for browsers that don't support webkitGetAsEntry
                    const droppedFiles = e.dataTransfer.files;
                    for (let i = 0; i < droppedFiles.length; i++) {
                        filesArray.push(droppedFiles[i]);
                    }
                    // Update file input with dropped files (if possible)
                    try {
                        if (window.DataTransfer && window.DataTransfer.prototype.items) {
                            const dt = new DataTransfer();
                            filesArray.forEach(file => dt.items.add(file));
                            fileInput.files = dt.files;
                        }
                        showSelectedFiles(filesArray);
                    } catch (e) {
                        console.error("Cannot set files in input field:", e);
                        showNotification("Browser doesn't fully support drag & drop. Use the file selector.", "warning");
                    }
                }
            }
        }, false);
    }
    
    // Recursive function to traverse folder structure
    function traverseFileTree(item, path, filesArray, preservePath) {
        path = path || '';
        if (item.isFile) {
            item.file(file => {
                // Check if it's a supported format
                const ext = file.name.split('.').pop().toLowerCase();
                const allowedExts = ['txt', 'md', 'html', 'xml', 'json', 'csv'];
                
                if (allowedExts.includes(ext)) {
                    // If preservePath is true, keep the path in the folder
                    if (preservePath && path) {
                        // Create a new file with path in name or save path as metadata
                        file.relativePath = path + file.name;
                    }
                    filesArray.push(file);
                    showSelectedFiles(filesArray);
                }
            });
        } else if (item.isDirectory) {
            // Read directory contents
            const dirReader = item.createReader();
            dirReader.readEntries(entries => {
                for (let i = 0; i < entries.length; i++) {
                    // Build path recursively
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
    
    // Show selected files
    function showSelectedFiles(files) {
        if (files.length > 0 && fileListEl) {
            progressContainer?.classList.remove('d-none');
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
    
    // Handle file selection via input
    if (fileInput) {
        fileInput.addEventListener('change', () => {
            const files = fileInput.files ? Array.from(fileInput.files) : [];
            showSelectedFiles(files);
        });
    }
    
    // Handle form submission
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
            
            // Check total size
            const totalSize = files.reduce((sum, file) => sum + file.size, 0);
            const maxTotalSize = 50 * 1024 * 1024; // 50MB as example
            
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
                // Show progress container
                if (progressContainer) {
                    progressContainer.classList.remove('d-none');
                }
                
                // Process files one by one
                let processed = 0;
                let successCount = 0;
                let errorCount = 0;
                
                for (const file of files) {
                    try {
                        const formData = new FormData();
                        formData.append('file', file);
                        
                        // Add path information if needed
                        if (file.relativePath) {
                            formData.append('relative_path', file.relativePath);
                        }
                        
                        // Option to keep folder structure
                        if (processFolder && processFolder.checked) {
                            formData.append('preserve_path', 'true');
                        }
                        
                        const result = await api.uploadDocument(formData);
                        
                        if (result && result.status === 'success') {
                            successCount++;
                        }
                    } catch (fileError) {
                        errorCount++;
                        console.error(`Error uploading file ${file.name}:`, fileError);
                        
                        // Update file status in UI
                        const fileEl = document.getElementById(`file-${file.name.replace(/\W/g, '')}`);
                        if (fileEl) {
                            fileEl.querySelector('.file-status').innerHTML = `<span class="text-danger">Errore</span>`;
                        }
                    }
                    
                    // Update progress
                    processed++;
                    if (totalProgressBar) {
                        updateProgress(processed, files.length, file);
                    }
                }
                
                // Final summary
                if (successCount > 0) {
                    if (successCount === 1) {
                        showNotification('Documento caricato con successo!', 'success');
                    } else {
                        showNotification(`${successCount} documenti caricati con successo!`, 'success');
                    }
                    
                    // Refresh the document list instead of reloading the page
                    refreshDocumentList();
                }
                
                if (errorCount > 0) {
                    showNotification(`Si sono verificati errori durante il caricamento di ${errorCount} file.`, 'warning');
                }
            } catch (error) {
                console.error("General error during upload:", error);
                showNotification(`Errore durante il caricamento: ${error.message}`, 'danger');
            } finally {
                hideLoading();
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-cloud-upload-alt me-2"></i>Carica';
                }
                if (form) {
                    form.reset(); // Clear form
                }
                if (progressContainer) {
                    setTimeout(() => {
                        progressContainer.classList.add('d-none');
                    }, 3000); // Hide progress bar after a few seconds
                }
            }
        });
    }
}

// Enhanced function to render document list with folder structure support
function renderDocumentList(documents) {
    const documentList = document.getElementById('document-list');
    if (!documentList) return;

    if (!documents || documents.length === 0) {
        documentList.innerHTML = `
            <div class="col-12 text-center py-5 text-muted">
                <i class="fas fa-file-circle-xmark fa-3x mb-3"></i>
                <h5 class="mb-1">Nessun documento disponibile</h5>
                <p>Carica un documento per iniziare.</p>
            </div>
        `;
        return;
    }

    let html = '';
    
    // Group documents by folder if they have metadata
    const folderGroups = {};
    const ungroupedDocs = [];
    
    documents.forEach(doc => {
        if (doc.metadata && doc.metadata.relative_path && doc.metadata.relative_path.includes('/')) {
            // Extract folder name from relative path
            const folderPath = doc.metadata.relative_path.split('/').slice(0, -1).join('/');
            if (!folderGroups[folderPath]) {
                folderGroups[folderPath] = [];
            }
            folderGroups[folderPath].push(doc);
        } else {
            ungroupedDocs.push(doc);
        }
    });
    
    // Render folder groups
    Object.keys(folderGroups).sort().forEach(folder => {
        const docs = folderGroups[folder];
        html += `
            <div class="col-12 mb-3">
                <div class="card">
                    <div class="card-header bg-light d-flex justify-content-between align-items-center">
                        <h6 class="mb-0"><i class="fas fa-folder me-2"></i>${folder}</h6>
                        <span class="badge bg-secondary rounded-pill">${docs.length} file</span>
                    </div>
                    <div class="card-body p-3">
                        <div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-3">
        `;
        
        docs.forEach(doc => {
            html += createDocumentCard(doc);
        });
        
        html += `
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    // Render ungrouped documents
    if (ungroupedDocs.length > 0) {
        html += `<div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-4">`;
        ungroupedDocs.forEach(doc => {
            html += createDocumentCard(doc);
        });
        html += `</div>`;
    }
    
    documentList.innerHTML = html;
}

function createDocumentCard(doc) {
    // Extract file name without folder path
    let displayTitle = doc.title;
    if (doc.metadata && doc.metadata.relative_path) {
        const pathParts = doc.metadata.relative_path.split('/');
        displayTitle = pathParts[pathParts.length - 1]; // Get just the file name
    }
    
    return `
        <div class="col doc-card-col" data-doc-id="${doc.id}">
            <div class="card h-100 doc-card">
                <div class="card-body pb-0">
                    <h6 class="card-title document-title mb-1" title="${doc.title}">${displayTitle}</h6>
                    ${doc.metadata && doc.metadata.relative_path ? 
                      `<small class="text-muted d-block mb-2"><i class="fas fa-folder-open me-1"></i>${doc.metadata.relative_path}</small>` : ''}
                    <p class="card-text document-preview mb-2">${doc.text ? doc.text.substring(0, 120) + '...' : ''}</p>
                    <div class="document-metadata text-muted small mb-2">
                        <span><i class="fas fa-file-word me-1"></i>${doc.word_count} parole</span>
                        ${doc.date_created ? 
                          `<span><i class="fas fa-calendar-alt me-1"></i>${doc.date_created.split('T')[0]}</span>` : ''}
                    </div>
                </div>
                <div class="card-footer">
                    <div class="btn-group w-100" role="group">
                        <a href="/annotate/${doc.id}" class="btn btn-sm btn-success">
                            <i class="fas fa-tag"></i> Annota
                        </a>
                        <button class="btn btn-sm btn-outline-secondary rename-doc-btn" 
                                data-doc-id="${doc.id}" 
                                data-doc-title="${displayTitle}">
                            <i class="fas fa-edit"></i> Rinomina
                        </button>
                        <button class="btn btn-sm btn-outline-danger delete-doc-btn" 
                                data-doc-id="${doc.id}" 
                                data-doc-title="${displayTitle}">
                            <i class="fas fa-trash-alt"></i> Elimina
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}
/**
 * Enhanced refreshDocumentList function with better error handling and fallback
 */
async function refreshDocumentList() {
    try {
        showLoading();
        
        // Try to use the API if available
        if (api && typeof api.getDocuments === 'function') {
            try {
                const response = await api.getDocuments();
                if (response && response.status === 'success') {
                    renderDocumentList(response.documents);
                } else {
                    showNotification('Errore nel caricamento dei documenti', 'danger');
                    fallbackToDOM();
                }
            } catch (apiError) {
                console.error('API Error:', apiError);
                showNotification(`Errore API: ${apiError.message}`, 'danger');
                
                // Fallback to existing DOM content
                fallbackToDOM();
            }
        } else {
            // Fallback: use existing documents or reload
            fallbackToDOM();
        }
    } catch (error) {
        console.error('Error loading documents:', error);
        showNotification(`Errore: ${error.message}`, 'danger');
    } finally {
        hideLoading();
    }
}

function fallbackToDOM() {
    console.log('Using documents from DOM as fallback or reloading');
    
    // Check if we have documents in the DOM
    const docCards = document.querySelectorAll('.doc-card-col');
    if (docCards.length > 0) {
        // Extract documents from existing DOM
        const documents = [];
        docCards.forEach(el => {
            const docId = el.dataset.docId;
            const titleEl = el.querySelector('.document-title');
            const previewEl = el.querySelector('.document-preview');
            
            if (docId && titleEl) {
                const doc = {
                    id: docId,
                    title: titleEl.textContent,
                    text: previewEl ? previewEl.textContent : '',
                    metadata: {} // Default empty metadata
                };
                documents.push(doc);
            }
        });
        
        if (documents.length > 0) {
            console.log(`Extracted ${documents.length} documents from DOM`);
            renderDocumentList(documents);
            return;
        }
    }
    
    // If no documents in DOM or extraction failed, simply reload
    window.location.reload();
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