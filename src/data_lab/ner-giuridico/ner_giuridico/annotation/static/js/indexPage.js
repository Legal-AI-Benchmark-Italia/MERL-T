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

function handleUpload() {
    const form = document.getElementById('upload-form');
    const fileInput = document.getElementById('document-file');
    const submitBtn = form.querySelector('button[type="submit"]');

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const file = fileInput.files[0];
        if (!file) {
            showNotification('Seleziona un file da caricare.', 'warning');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Caricamento...';
        showLoading();

        try {
            const result = await api.uploadDocument(formData);
            showNotification('Documento caricato con successo!', 'success');
            // Optionally add the new document card dynamically instead of reloading
            window.location.reload();
        } catch (error) {
            showNotification(`Errore durante il caricamento: ${error.message}`, 'danger');
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-cloud-upload-alt me-2"></i>Carica';
        } finally {
            hideLoading();
            // Reset button state even on success if not reloading
            // submitBtn.disabled = false;
            // submitBtn.innerHTML = '<i class="fas fa-cloud-upload-alt me-2"></i>Carica';
            form.reset(); // Clear the file input
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