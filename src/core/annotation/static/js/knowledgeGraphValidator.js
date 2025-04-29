/**
 * knowledgeGraphValidator.js
 * Gestione della visualizzazione e validazione del Knowledge Graph
 */

import { api } from './api.js';
import { showNotification, showLoading, hideLoading } from './ui.js';

// Stato dell'applicazione
let graphChunks = [];
let currentChunkId = null;
let currentGraph = null;
let currentProposals = [];
let graphVisualization = null;

// Inizializzazione della pagina
export function initGraphValidator() {
    console.log('Initializing Knowledge Graph Validator...');
    
    // Cache dei riferimenti DOM
    const chunkList = document.getElementById('graph-chunk-list');
    const graphViewer = document.getElementById('graph-viewer');
    const proposalList = document.getElementById('proposal-list');
    const createProposalBtn = document.getElementById('create-proposal-btn');
    const chunkFilter = document.getElementById('chunk-filter');
    
    // Inizializza libreria di visualizzazione grafo (es. vis.js o cytoscape.js)
    initGraphVisualization(graphViewer);
    
    // Carica i chunk assegnati all'utente
    loadAssignedChunks();
    
    // Event listeners
    if (chunkList) {
        chunkList.addEventListener('click', function(e) {
            const chunkItem = e.target.closest('.chunk-item');
            if (chunkItem) {
                const chunkId = chunkItem.dataset.chunkId;
                selectChunk(chunkId);
            }
        });
    }
    
    if (createProposalBtn) {
        createProposalBtn.addEventListener('click', function() {
            showProposalEditor();
        });
    }
    
    if (chunkFilter) {
        chunkFilter.addEventListener('change', function() {
            const status = this.value;
            loadAssignedChunks(status);
        });
    }
}

// Inizializza la visualizzazione del grafo
function initGraphVisualization(container) {
    if (!container) return;
    
    // Utilizziamo vis-network per la visualizzazione del grafo
    // Questa è una libreria ampiamente utilizzata per la visualizzazione di grafi
    try {
        // Configurazione base per vis.js
        const options = {
            nodes: {
                shape: 'box',
                font: {
                    size: 16,
                    face: 'Roboto'
                },
                borderWidth: 2,
                shadow: true
            },
            edges: {
                width: 2,
                shadow: true,
                arrows: {
                    to: { enabled: true, scaleFactor: 1 }
                },
                font: {
                    size: 12,
                    align: 'middle'
                }
            },
            physics: {
                enabled: true,
                barnesHut: {
                    gravitationalConstant: -2000,
                    centralGravity: 0.3,
                    springLength: 150,
                    springConstant: 0.04
                }
            },
            interaction: {
                navigationButtons: true,
                keyboard: true,
                multiselect: true
            }
        };
        
        // Crea un'istanza vuota di vis Network
        graphVisualization = new vis.Network(container, { nodes: [], edges: [] }, options);
        
        // Event listeners per interagire con il grafo
        graphVisualization.on('click', function(params) {
            if (params.nodes.length > 0) {
                // Selezione di un nodo
                const nodeId = params.nodes[0];
                selectGraphNode(nodeId);
            } else if (params.edges.length > 0) {
                // Selezione di una relazione
                const edgeId = params.edges[0];
                selectGraphEdge(edgeId);
            }
        });
        
        console.log('Graph visualization initialized successfully');
    } catch (error) {
        console.error('Error initializing graph visualization:', error);
        showNotification('Errore nell\'inizializzazione della visualizzazione del grafo', 'danger');
    }
}

// Carica i chunk del grafo assegnati all'utente
async function loadAssignedChunks(status = 'pending') {
    try {
        showLoading();
        
        const response = await api.getGraphChunks(status);
        
        if (response && response.status === 'success') {
            graphChunks = response.chunks || [];
            renderChunkList(graphChunks);
            
            // Se c'è almeno un chunk, seleziona il primo
            if (graphChunks.length > 0) {
                selectChunk(graphChunks[0].id);
            } else {
                // Nessun chunk disponibile
                const graphViewer = document.getElementById('graph-viewer');
                if (graphViewer) {
                    graphViewer.innerHTML = `
                        <div class="text-center p-5">
                            <i class="fas fa-project-diagram fa-4x mb-3 text-muted"></i>
                            <h4>Nessun chunk del grafo disponibile</h4>
                            <p class="text-muted">Non hai chunk del grafo assegnati con lo stato selezionato.</p>
                        </div>
                    `;
                }
                
                const proposalList = document.getElementById('proposal-list');
                if (proposalList) {
                    proposalList.innerHTML = '';
                }
            }
        } else {
            showNotification('Errore nel caricamento dei chunk del grafo', 'danger');
        }
    } catch (error) {
        console.error('Error loading graph chunks:', error);
        showNotification(`Errore: ${error.message}`, 'danger');
    } finally {
        hideLoading();
    }
}

// Renderizza la lista dei chunk
function renderChunkList(chunks) {
    const chunkList = document.getElementById('graph-chunk-list');
    if (!chunkList) return;
    
    if (chunks.length === 0) {
        chunkList.innerHTML = `
            <div class="text-center p-3">
                <p class="text-muted">Nessun chunk disponibile</p>
            </div>
        `;
        return;
    }
    
    chunkList.innerHTML = '';
    
    chunks.forEach(chunk => {
        const item = document.createElement('div');
        item.className = 'list-group-item list-group-item-action chunk-item d-flex justify-content-between align-items-center';
        item.dataset.chunkId = chunk.id;
        
        // Determina la classe di stato
        let statusBadgeClass = 'bg-secondary';
        if (chunk.status === 'validated') {
            statusBadgeClass = 'bg-success';
        } else if (chunk.status === 'rejected') {
            statusBadgeClass = 'bg-danger';
        }
        
        item.innerHTML = `
            <div>
                <h6 class="mb-1">${chunk.title}</h6>
                <small class="text-muted">${chunk.description || 'Nessuna descrizione'}</small>
            </div>
            <div>
                <span class="badge ${statusBadgeClass}">${chunk.status}</span>
            </div>
        `;
        
        chunkList.appendChild(item);
    });
}

// Seleziona un chunk e carica i suoi dati
async function selectChunk(chunkId) {
    if (currentChunkId === chunkId) return;
    
    try {
        showLoading();
        
        // Evidenzia il chunk selezionato
        document.querySelectorAll('.chunk-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.chunkId === chunkId) {
                item.classList.add('active');
            }
        });
        
        // Carica i dati del chunk
        const response = await api.getGraphChunk(chunkId);
        
        if (response && response.status === 'success') {
            currentChunkId = chunkId;
            currentGraph = response.chunk.data;
            
            // Aggiorna la visualizzazione
            updateGraphVisualization(currentGraph);
            
            // Carica le proposte per questo chunk
            loadChunkProposals(chunkId);
        } else {
            showNotification('Errore nel caricamento del chunk', 'danger');
        }
    } catch (error) {
        console.error('Error selecting graph chunk:', error);
        showNotification(`Errore: ${error.message}`, 'danger');
    } finally {
        hideLoading();
    }
}

// Aggiorna la visualizzazione del grafo
function updateGraphVisualization(graphData) {
    if (!graphVisualization || !graphData) return;
    
    try {
        // Converti i dati nel formato richiesto da vis.js
        const nodes = [];
        const edges = [];
        
        // Aggiungi i nodi
        if (graphData.nodes && Array.isArray(graphData.nodes)) {
            graphData.nodes.forEach(node => {
                nodes.push({
                    id: node.id,
                    label: node.label || node.id,
                    title: getNodeTooltip(node),
                    color: getNodeColor(node.type),
                    group: node.type
                });
            });
        }
        
        // Aggiungi le relazioni
        if (graphData.edges && Array.isArray(graphData.edges)) {
            graphData.edges.forEach(edge => {
                edges.push({
                    id: edge.id,
                    from: edge.source,
                    to: edge.target,
                    label: edge.type,
                    title: getEdgeTooltip(edge)
                });
            });
        }
        
        // Aggiorna la visualizzazione
        graphVisualization.setData({
            nodes: new vis.DataSet(nodes),
            edges: new vis.DataSet(edges)
        });
        
        // Adatta la vista per mostrare tutto il grafo
        graphVisualization.fit();
        
    } catch (error) {
        console.error('Error updating graph visualization:', error);
        showNotification('Errore nell\'aggiornamento della visualizzazione del grafo', 'danger');
    }
}

// Carica le proposte di modifica per un chunk
async function loadChunkProposals(chunkId) {
    try {
        const response = await api.getGraphProposals(chunkId);
        
        if (response && response.status === 'success') {
            currentProposals = response.proposals || [];
            renderProposalList(currentProposals);
        } else {
            showNotification('Errore nel caricamento delle proposte', 'danger');
        }
    } catch (error) {
        console.error('Error loading graph proposals:', error);
        showNotification(`Errore: ${error.message}`, 'danger');
    }
}

// Renderizza la lista delle proposte
function renderProposalList(proposals) {
    const proposalList = document.getElementById('proposal-list');
    if (!proposalList) return;
    
    if (proposals.length === 0) {
        proposalList.innerHTML = `
            <div class="text-center p-3">
                <p class="text-muted">Nessuna proposta disponibile</p>
                <button id="create-first-proposal" class="btn btn-primary btn-sm">
                    <i class="fas fa-plus me-1"></i> Crea la prima proposta
                </button>
            </div>
        `;
        
        document.getElementById('create-first-proposal')?.addEventListener('click', showProposalEditor);
        return;
    }
    
    proposalList.innerHTML = '';
    
    proposals.forEach(proposal => {
        const item = document.createElement('div');
        item.className = 'card mb-3 proposal-card';
        item.dataset.proposalId = proposal.id;
        
        // Determina la classe di stato
        let statusBadgeClass = 'bg-secondary';
        if (proposal.status === 'approved') {
            statusBadgeClass = 'bg-success';
        } else if (proposal.status === 'rejected') {
            statusBadgeClass = 'bg-danger';
        }
        
        // Calcola la percentuale di voti a favore
        const totalVotes = proposal.approve_count + proposal.reject_count;
        const approvePercentage = totalVotes > 0 ? Math.round((proposal.approve_count / totalVotes) * 100) : 0;
        
        item.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center">
                <span>Proposta di ${getProposalTypeText(proposal.proposal_type)}</span>
                <span class="badge ${statusBadgeClass}">${proposal.status}</span>
            </div>
            <div class="card-body">
                <h6 class="card-title">
                    Creata da ${proposal.created_by_username || 'Utente sconosciuto'} 
                    <small class="text-muted">${formatDate(proposal.date_created)}</small>
                </h6>
                
                <div class="proposal-details mt-3">
                    <div class="proposal-content">
                        ${renderProposalContent(proposal)}
                    </div>
                </div>
                
                <div class="vote-progress mt-3">
                    <div class="d-flex justify-content-between mb-1">
                        <span>${proposal.approve_count} approvazioni</span>
                        <span>${proposal.reject_count} rifiuti</span>
                    </div>
                    <div class="progress" style="height: 10px;">
                        <div class="progress-bar bg-success" role="progressbar" 
                             style="width: ${approvePercentage}%" 
                             aria-valuenow="${approvePercentage}" 
                             aria-valuemin="0" aria-valuemax="100"></div>
                    </div>
                    <small class="text-muted mt-1 d-block">
                        Richiesti: ${proposal.votes_required} voti per approvazione (${proposal.approve_count}/${proposal.votes_required})
                    </small>
                </div>
                
                <div class="vote-buttons mt-3 d-flex justify-content-between">
                    <button class="btn btn-outline-danger reject-proposal-btn" data-proposal-id="${proposal.id}">
                        <i class="fas fa-times me-1"></i> Rifiuta
                    </button>
                    <button class="btn btn-success approve-proposal-btn" data-proposal-id="${proposal.id}">
                        <i class="fas fa-check me-1"></i> Approva
                    </button>
                </div>
                
                <div class="vote-list mt-3">
                    <h6 class="mb-2">Voti (${proposal.votes?.length || 0})</h6>
                    ${renderVotesList(proposal.votes || [])}
                </div>
            </div>
        `;
        
        proposalList.appendChild(item);
    });
    
    // Aggiungi event listeners per i pulsanti di voto
    document.querySelectorAll('.approve-proposal-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const proposalId = this.dataset.proposalId;
            voteProposal(proposalId, 'approve');
        });
    });
    
    document.querySelectorAll('.reject-proposal-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const proposalId = this.dataset.proposalId;
            voteProposal(proposalId, 'reject');
        });
    });
}

// Visualizza i dettagli della proposta in base al tipo
function renderProposalContent(proposal) {
    const type = proposal.proposal_type;
    
    if (type === 'add') {
        // Proposta di aggiunta
        const entities = proposal.proposed_data.nodes || proposal.proposed_data.edges || [];
        return `
            <div class="alert alert-info">
                Aggiunta di ${entities.length} ${proposal.proposed_data.nodes ? 'nodi' : 'relazioni'} al grafo
            </div>
            <pre class="bg-light p-2 mt-2">${JSON.stringify(entities, null, 2)}</pre>
        `;
    } else if (type === 'modify') {
        // Proposta di modifica
        const originalData = proposal.original_data;
        const proposedData = proposal.proposed_data;
        
        return `
            <div class="alert alert-warning">
                Modifica di ${proposedData.nodes ? 'nodi' : 'relazioni'} nel grafo
            </div>
            <div class="row">
                <div class="col-md-6">
                    <h6>Originale</h6>
                    <pre class="bg-light p-2">${JSON.stringify(originalData, null, 2)}</pre>
                </div>
                <div class="col-md-6">
                    <h6>Proposta</h6>
                    <pre class="bg-light p-2">${JSON.stringify(proposedData, null, 2)}</pre>
                </div>
            </div>
        `;
    } else if (type === 'delete') {
        // Proposta di eliminazione
        const entities = proposal.proposed_data.nodes || proposal.proposed_data.edges || [];
        
        return `
            <div class="alert alert-danger">
                Eliminazione di ${entities.length} ${proposal.proposed_data.nodes ? 'nodi' : 'relazioni'} dal grafo
            </div>
            <pre class="bg-light p-2 mt-2">${JSON.stringify(entities, null, 2)}</pre>
        `;
    }
    
    return `<div class="alert alert-secondary">Proposta di tipo sconosciuto</div>`;
}

// Renderizza la lista dei voti per una proposta
function renderVotesList(votes) {
    if (!votes || votes.length === 0) {
        return `<p class="text-muted small">Nessun voto</p>`;
    }
    
    let html = '<ul class="list-group list-group-flush">';
    
    votes.forEach(vote => {
        const isApprove = vote.vote === 'approve';
        const badgeClass = isApprove ? 'bg-success' : 'bg-danger';
        const iconClass = isApprove ? 'fa-check' : 'fa-times';
        
        html += `
            <li class="list-group-item py-2">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <span class="badge ${badgeClass} me-2">
                            <i class="fas ${iconClass}"></i>
                        </span>
                        <strong>${vote.username || vote.user_id}</strong>
                    </div>
                    <small class="text-muted">${formatDate(vote.date_created)}</small>
                </div>
                ${vote.comment ? `<p class="mb-0 mt-1 small">${vote.comment}</p>` : ''}
            </li>
        `;
    });
    
    html += '</ul>';
    return html;
}

// Vota una proposta
async function voteProposal(proposalId, voteType) {
    try {
        showLoading();
        
        // Opzionale: chiedi un commento per il voto
        let comment = '';
        if (voteType === 'reject') {
            comment = prompt('Inserisci un commento per motivare il tuo rifiuto (opzionale):');
        }
        
        const response = await api.voteGraphProposal({
            proposal_id: proposalId,
            vote: voteType,
            comment: comment
        });
        
        if (response && response.status === 'success') {
            showNotification(`Voto registrato con successo`, 'success');
            
            // Aggiorna le proposte
            loadChunkProposals(currentChunkId);
            
            // Se la proposta è stata approvata, aggiorna anche la visualizzazione
            if (response.result.proposal_approved) {
                showNotification('La proposta è stata approvata e applicata al grafo!', 'success');
                
                // Ricarica il chunk per visualizzare le modifiche
                selectChunk(currentChunkId);
            } else if (response.result.proposal_rejected) {
                showNotification('La proposta è stata respinta.', 'warning');
            }
        } else {
            showNotification('Errore nel registrare il voto', 'danger');
        }
    } catch (error) {
        console.error('Error voting on proposal:', error);
        showNotification(`Errore: ${error.message}`, 'danger');
    } finally {
        hideLoading();
    }
}

// Mostra l'editor per creare una nuova proposta
function showProposalEditor() {
    const modalId = 'proposalEditorModal';
    
    // Verifica se il modal esiste già
    let modal = document.getElementById(modalId);
    if (!modal) {
        // Crea il modal
        modal = document.createElement('div');
        modal.id = modalId;
        modal.className = 'modal fade';
        modal.tabIndex = -1;
        modal.setAttribute('aria-labelledby', 'proposalEditorModalLabel');
        modal.setAttribute('aria-hidden', 'true');
        
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="proposalEditorModalLabel">Nuova Proposta di Modifica</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <form id="proposalForm">
                            <div class="mb-3">
                                <label for="proposalType" class="form-label">Tipo di Proposta</label>
                                <select class="form-select" id="proposalType" required>
                                    <option value="">Seleziona un tipo...</option>
                                    <option value="add">Aggiunta</option>
                                    <option value="modify">Modifica</option>
                                    <option value="delete">Eliminazione</option>
                                </select>
                            </div>
                            
                            <div class="mb-3">
                                <label for="entityType" class="form-label">Tipo di Entità</label>
                                <select class="form-select" id="entityType" required>
                                    <option value="">Seleziona un tipo...</option>
                                    <option value="nodes">Nodi</option>
                                    <option value="edges">Relazioni</option>
                                </select>
                            </div>
                            
                            <div id="addModifyContainer" class="d-none">
                                <div class="mb-3">
                                    <label for="jsonEditor" class="form-label">Dati JSON</label>
                                    <div class="alert alert-info small">
                                        Inserisci i dati in formato JSON. Per i nodi, includi campi come "id", "label", "type". 
                                        Per le relazioni, includi "id", "source", "target", "type".
                                    </div>
                                    <textarea class="form-control font-monospace" id="jsonEditor" rows="10"></textarea>
                                </div>
                            </div>
                            
                            <div id="entitySelectionContainer" class="d-none">
                                <div class="mb-3">
                                    <label class="form-label">Seleziona Entità dal Grafo</label>
                                    <div class="alert alert-info small">
                                        Seleziona nodi o relazioni direttamente dal grafo cliccando su di essi nella visualizzazione.
                                    </div>
                                    <div id="selectedEntitiesList" class="mt-2 list-group"></div>
                                </div>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Annulla</button>
                        <button type="button" class="btn btn-primary" id="saveProposalBtn">Salva Proposta</button>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Inizializza il modal con Bootstrap
        const modalInstance = new bootstrap.Modal(modal);
        
        // Aggiungi event listeners
        document.getElementById('proposalType').addEventListener('change', updateProposalForm);
        document.getElementById('entityType').addEventListener('change', updateProposalForm);
        document.getElementById('saveProposalBtn').addEventListener('click', saveProposal);
        
        // Mostra il modal
        modalInstance.show();
    } else {
        // Il modal esiste già, mostralo
        const modalInstance = bootstrap.Modal.getInstance(modal) || new bootstrap.Modal(modal);
        modalInstance.show();
    }
}

// Aggiorna il form della proposta in base alle selezioni
function updateProposalForm() {
    const proposalType = document.getElementById('proposalType').value;
    const entityType = document.getElementById('entityType').value;
    
    const addModifyContainer = document.getElementById('addModifyContainer');
    const entitySelectionContainer = document.getElementById('entitySelectionContainer');
    
    // Reset
    addModifyContainer.classList.add('d-none');
    entitySelectionContainer.classList.add('d-none');
    
    if (!proposalType || !entityType) return;
    
    if (proposalType === 'add' || proposalType === 'modify') {
        // Per aggiunta o modifica, mostra l'editor JSON
        addModifyContainer.classList.remove('d-none');
        
        // Se è modifica, mostra anche il selettore di entità
        if (proposalType === 'modify') {
            entitySelectionContainer.classList.remove('d-none');
        }
        
        // Prepopola con un template
        const jsonEditor = document.getElementById('jsonEditor');
        if (jsonEditor.value === '') {
            if (entityType === 'nodes') {
                jsonEditor.value = JSON.stringify([
                    {
                        "id": "node1",
                        "label": "Esempio Nodo",
                        "type": "concept"
                    }
                ], null, 2);
            } else {
                jsonEditor.value = JSON.stringify([
                    {
                        "id": "edge1",
                        "source": "node1",
                        "target": "node2",
                        "type": "relates_to"
                    }
                ], null, 2);
            }
        }
    } else if (proposalType === 'delete') {
        // Per eliminazione, mostra solo il selettore di entità
        entitySelectionContainer.classList.remove('d-none');
    }
}

// Salva una proposta
async function saveProposal() {
    try {
        const proposalType = document.getElementById('proposalType').value;
        const entityType = document.getElementById('entityType').value;
        const jsonEditor = document.getElementById('jsonEditor');
        
        if (!proposalType || !entityType) {
            showNotification('Seleziona il tipo di proposta e il tipo di entità', 'warning');
            return;
        }
        
        let proposedData = {};
        
        if (proposalType === 'add') {
            // Proposta di aggiunta
            try {
                const entities = JSON.parse(jsonEditor.value);
                proposedData[entityType] = entities;
            } catch (error) {
                showNotification('JSON non valido. Verifica il formato.', 'danger');
                return;
            }
        } else if (proposalType === 'modify') {
            // Proposta di modifica
            try {
                const entities = JSON.parse(jsonEditor.value);
                proposedData[entityType] = entities;
            } catch (error) {
                showNotification('JSON non valido. Verifica il formato.', 'danger');
                return;
            }
        } else if (proposalType === 'delete') {
            // Proposta di eliminazione
            const selectedEntities = getSelectedEntities();
            if (selectedEntities.length === 0) {
                showNotification('Seleziona almeno un\'entità dal grafo', 'warning');
                return;
            }
            proposedData[entityType] = selectedEntities;
        }
        
        // Prepara i dati della proposta
        const proposalData = {
            chunk_id: currentChunkId,
            proposal_type: proposalType,
            proposed_data: proposedData
        };
        
        // Se è una modifica, includi anche i dati originali
        if (proposalType === 'modify') {
            proposalData.original_data = getOriginalData(entityType, proposedData[entityType]);
        }
        
        showLoading();
        
        // Invia la proposta
        const response = await api.createGraphProposal(proposalData);
        
        if (response && response.status === 'success') {
            showNotification('Proposta creata con successo', 'success');
            
            // Chiudi il modal
            const modal = document.getElementById('proposalEditorModal');
            const modalInstance = bootstrap.Modal.getInstance(modal);
            modalInstance.hide();
            
            // Aggiorna le proposte
            loadChunkProposals(currentChunkId);
        } else {
            showNotification('Errore nella creazione della proposta', 'danger');
        }
    } catch (error) {
        console.error('Error saving proposal:', error);
        showNotification(`Errore: ${error.message}`, 'danger');
    } finally {
        hideLoading();
    }
}

// Ottieni le entità selezionate dal grafo
function getSelectedEntities() {
    // Recupera le entità selezionate dalla visualizzazione del grafo
    const selectedNodes = graphVisualization.getSelectedNodes();
    const selectedEdges = graphVisualization.getSelectedEdges();
    
    const entities = [];
    
    if (document.getElementById('entityType').value === 'nodes') {
        // Estrai i nodi selezionati
        selectedNodes.forEach(nodeId => {
            const node = graphVisualization.body.data.nodes.get(nodeId);
            entities.push({
                id: node.id,
                label: node.label,
                type: node.group
            });
        });
    } else {
        // Estrai le relazioni selezionate
        selectedEdges.forEach(edgeId => {
            const edge = graphVisualization.body.data.edges.get(edgeId);
            entities.push({
                id: edge.id,
                source: edge.from,
                target: edge.to,
                type: edge.label
            });
        });
    }
    
    return entities;
}

// Ottieni i dati originali per una proposta di modifica
function getOriginalData(entityType, proposedEntities) {
    if (!currentGraph || !proposedEntities) return {};
    
    const originalData = {};
    const originalEntities = [];
    
    // Cerca gli ID delle entità proposte nel grafo corrente
    proposedEntities.forEach(proposedEntity => {
        const originalEntity = currentGraph[entityType]?.find(e => e.id === proposedEntity.id);
        if (originalEntity) {
            originalEntities.push(originalEntity);
        }
    });
    
    originalData[entityType] = originalEntities;
    return originalData;
}

// Funzioni di utilità
function getNodeTooltip(node) {
    return `<div>
        <strong>${node.label || node.id}</strong><br/>
        Tipo: ${node.type}<br/>
        ${Object.entries(node.properties || {})
            .map(([key, value]) => `${key}: ${value}`)
            .join('<br/>')}
    </div>`;
}

function getEdgeTooltip(edge) {
    return `<div>
        <strong>${edge.type}</strong><br/>
        Da: ${edge.source}<br/>
        A: ${edge.target}<br/>
        ${Object.entries(edge.properties || {})
            .map(([key, value]) => `${key}: ${value}`)
            .join('<br/>')}
    </div>`;
}

function getNodeColor(nodeType) {
    // Mappa dei colori per tipo di nodo
    const colorMap = {
        'norma': '#FF5733',
        'concept': '#33FF57',
        'judgment': '#3357FF',
        'subject': '#FF33A8',
        'procedure': '#33A8FF',
        'doctrine': '#A833FF'
    };
    
    return colorMap[nodeType] || '#7F7F7F';
}

function getProposalTypeText(type) {
    switch (type) {
        case 'add': return 'aggiunta';
        case 'modify': return 'modifica';
        case 'delete': return 'eliminazione';
        default: return type;
    }
}

function formatDate(dateString) {
    if (!dateString) return '';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleString('it-IT');
    } catch {
        return dateString;
    }
}

// Seleziona un nodo del grafo
function selectGraphNode(nodeId) {
    if (!graphVisualization) return;
    
    // Evidenzia il nodo
    graphVisualization.selectNodes([nodeId]);
    
    // Mostra info nel pannello laterale
    const nodeData = graphVisualization.body.data.nodes.get(nodeId);
    if (nodeData) {
        const infoPanel = document.getElementById('entity-info-panel') || createInfoPanel();
        
        infoPanel.innerHTML = `
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">Dettagli Nodo</h5>
                </div>
                <div class="card-body">
                    <h6>ID: ${nodeData.id}</h6>
                    <p><strong>Etichetta:</strong> ${nodeData.label}</p>
                    <p><strong>Tipo:</strong> ${nodeData.group}</p>
                    
                    <div class="mt-3">
                        <button class="btn btn-sm btn-outline-primary select-for-proposal-btn" data-entity-id="${nodeData.id}" data-entity-type="node">
                            <i class="fas fa-plus me-1"></i> Seleziona per proposta
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Aggiungi event listener per il pulsante di selezione
        infoPanel.querySelector('.select-for-proposal-btn')?.addEventListener('click', function() {
            addEntityToProposal(nodeData, 'node');
        });
    }
}

// Seleziona una relazione del grafo
function selectGraphEdge(edgeId) {
    if (!graphVisualization) return;
    
    // Evidenzia la relazione
    graphVisualization.selectEdges([edgeId]);
    
    // Mostra info nel pannello laterale
    const edgeData = graphVisualization.body.data.edges.get(edgeId);
    if (edgeData) {
        const infoPanel = document.getElementById('entity-info-panel') || createInfoPanel();
        
        infoPanel.innerHTML = `
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h5 class="mb-0">Dettagli Relazione</h5>
                </div>
                <div class="card-body">
                    <h6>ID: ${edgeData.id}</h6>
                    <p><strong>Tipo:</strong> ${edgeData.label}</p>
                    <p><strong>Da:</strong> ${edgeData.from}</p>
                    <p><strong>A:</strong> ${edgeData.to}</p>
                    
                    <div class="mt-3">
                        <button class="btn btn-sm btn-outline-primary select-for-proposal-btn" data-entity-id="${edgeData.id}" data-entity-type="edge">
                            <i class="fas fa-plus me-1"></i> Seleziona per proposta
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Aggiungi event listener per il pulsante di selezione
        infoPanel.querySelector('.select-for-proposal-btn')?.addEventListener('click', function() {
            addEntityToProposal(edgeData, 'edge');
        });
    }
}

// Crea il pannello info se non esiste
function createInfoPanel() {
    let infoPanel = document.getElementById('entity-info-panel');
    
    if (!infoPanel) {
        infoPanel = document.createElement('div');
        infoPanel.id = 'entity-info-panel';
        infoPanel.className = 'position-fixed top-0 end-0 m-3 shadow';
        infoPanel.style.width = '300px';
        infoPanel.style.zIndex = '1000';
        
        document.body.appendChild(infoPanel);
    }
    
    return infoPanel;
}

// Aggiunge un'entità alla proposta corrente
function addEntityToProposal(entityData, entityType) {
    const modal = document.getElementById('proposalEditorModal');
    if (!modal) {
        showProposalEditor();
        setTimeout(() => addEntityToProposal(entityData, entityType), 500);
        return;
    }
    
    // Seleziona il tipo corretto nel form
    document.getElementById('entityType').value = entityType === 'node' ? 'nodes' : 'edges';
    
    // Aggiunge l'entità al contenitore delle entità selezionate
    const selectedEntitiesList = document.getElementById('selectedEntitiesList');
    if (selectedEntitiesList) {
        const entityItem = document.createElement('div');
        entityItem.className = 'list-group-item d-flex justify-content-between align-items-center';
        entityItem.dataset.entityId = entityData.id;
        
        if (entityType === 'node') {
            entityItem.innerHTML = `
                <span>
                    <strong>${entityData.label || entityData.id}</strong>
                    <span class="badge bg-secondary ms-1">${entityData.group}</span>
                </span>
                <button class="btn btn-sm btn-outline-danger remove-entity-btn">
                    <i class="fas fa-times"></i>
                </button>
            `;
        } else {
            entityItem.innerHTML = `
                <span>
                    <strong>${entityData.label || 'Relazione'}</strong>
                    <small class="ms-1">(${entityData.from} → ${entityData.to})</small>
                </span>
                <button class="btn btn-sm btn-outline-danger remove-entity-btn">
                    <i class="fas fa-times"></i>
                </button>
            `;
        }
        
        // Aggiungi event listener per rimuovere l'entità
        entityItem.querySelector('.remove-entity-btn')?.addEventListener('click', function() {
            entityItem.remove();
        });
        
        selectedEntitiesList.appendChild(entityItem);
    }
    
    // Aggiorna il form
    updateProposalForm();
    
    // Mostra il modal se non è già visibile
    const modalInstance = bootstrap.Modal.getInstance(modal) || new bootstrap.Modal(modal);
    modalInstance.show();
}