document.addEventListener('DOMContentLoaded', function() {
    // Gestione del form di upload
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('document-file');
    
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const file = fileInput.files[0];
        if (!file) {
            alert('Seleziona un file da caricare');
            return;
        }
        
        const formData = new FormData();
        formData.append('file', file);
        
        fetch('/api/upload_document', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                alert('Documento caricato con successo');
                window.location.reload();
            } else {
                alert('Errore: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Errore:', error);
            alert('Si è verificato un errore durante il caricamento');
        });
    });
    
    // Gestione dei pulsanti di esportazione
    const exportJsonBtn = document.getElementById('export-json');
    const exportSpacyBtn = document.getElementById('export-spacy');
    
    exportJsonBtn.addEventListener('click', function() {
        window.location.href = '/api/export_annotations?format=json';
    });
    
    exportSpacyBtn.addEventListener('click', function() {
        window.location.href = '/api/export_annotations?format=spacy';
    });
});
