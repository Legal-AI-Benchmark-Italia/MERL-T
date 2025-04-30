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
let physicsEnabled = true; // Track physics state

// --- Helper Functions Exposed to Window ---

window.resetGraphZoom = () => {
    if (graphVisualization) {
        graphVisualization.fit();
    } else {
        console.warn("Graph visualization not initialized for zoom reset.");
    }
};

window.toggleGraphPhysics = () => {
    if (graphVisualization) {
        physicsEnabled = !physicsEnabled;
        graphVisualization.setOptions({ physics: { enabled: physicsEnabled } });
        showNotification(`Fisica ${physicsEnabled ? 'abilitata' : 'disabilitata'}`, 'info');
    } else {
        console.warn("Graph visualization not initialized for physics toggle.");
    }
};

window.refreshProposals = () => {
    if (currentChunkId) {
        loadChunkProposals(currentChunkId);
        showNotification('Lista proposte aggiornata.', 'info');
    } else {
        showNotification('Nessun chunk selezionato per aggiornare le proposte.', 'warning');
    }
};

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
    
    // Setup listeners for proposal initiation buttons
    setupProposalInitiationListeners();
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
        
        // Get current user ID
        const userId = api.getCurrentUserId(); 
        if (!userId) {
            showNotification('ID utente non trovato. Impossibile caricare i chunk assegnati.', 'danger');
            hideLoading();
            return;
        }

        // Call API with status and user ID
        // Assuming api.getGraphChunks now accepts (status, assignedTo)
        const response = await api.getGraphChunks(status, userId);
        
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
        if (chunk.status === 'validated' || chunk.status === 'applied') {
            statusBadgeClass = 'bg-success';
        } else if (chunk.status === 'rejected' || chunk.status === 'failed') {
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
        try {
            const response = await api.getGraphChunk(chunkId);
            
            if (response && response.status === 'success') {
                currentChunkId = chunkId;
                currentGraph = response.chunk.data;
                
                // Aggiorna la visualizzazione
                updateGraphVisualization(currentGraph);
                
                // Carica le proposte per questo chunk
                loadChunkProposals(chunkId);
            } else {
                throw new Error(response?.message || 'Errore nel caricamento del chunk');
            }
        } catch (error) {
            console.error('Error selecting graph chunk:', error);
            showNotification(`Errore nel caricamento del chunk: ${error.message}. Caricamento di un chunk alternativo...`, 'warning');
            
            // Carica un chunk alternativo
            try {
                // Ricarica la lista completa dei chunk
                await loadAssignedChunks();
                
                // Seleziona il primo chunk disponibile
                if (graphChunks.length > 0) {
                    selectChunk(graphChunks[0].id);
                    showNotification('Caricato un chunk alternativo.', 'info');
                } else {
                    // Se non ci sono chunk, mostra un messaggio e pulisci la visualizzazione
                    showEmptyState();
                }
                
            } catch (fallbackError) {
                console.error('Error loading fallback chunk:', fallbackError);
                showNotification('Impossibile caricare chunk alternativi.', 'danger');
                showEmptyState();
            }
        }
    } catch (error) {
        console.error('Error in chunk selection workflow:', error);
        showNotification(`Errore: ${error.message}`, 'danger');
        showEmptyState();
    } finally {
        hideLoading();
    }
}

// Funzione helper per mostrare lo stato vuoto
function showEmptyState() {
    const graphViewer = document.getElementById('graph-viewer');
    if (graphViewer) {
        graphViewer.innerHTML = `
            <div class="text-center p-5">
                <i class="fas fa-project-diagram fa-4x mb-3 text-muted"></i>
                <h4>Nessun chunk del grafo disponibile</h4>
                <p class="text-muted">Non sono disponibili chunk del grafo da visualizzare.</p>
            </div>
        `;
    }
    
    const proposalList = document.getElementById('proposal-list');
    if (proposalList) {
        proposalList.innerHTML = '';
    }
    
    currentChunkId = null;
    currentGraph = null;
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

// Funzione helper per evidenziare nodi/relazioni nel grafo
function highlightGraphEntities(proposal) {
    if (!graphVisualization) return;

    const nodeIdsToHighlight = [];
    const edgeIdsToHighlight = [];

    const extractIds = (data) => {
        if (!data) return;
        if (data.nodes) {
            data.nodes.forEach(node => node.id && nodeIdsToHighlight.push(node.id));
        }
        if (data.edges) {
            // Per le relazioni, potremmo evidenziare i nodi sorgente/destinazione se l'ID della relazione non è nel grafo
            data.edges.forEach(edge => {
                if (edge.id && graphVisualization.body.data.edges.get(edge.id)) {
                    edgeIdsToHighlight.push(edge.id);
                } else {
                    // Se la relazione non è visualizzata (es. in 'add'), evidenzia nodi connessi
                    if (edge.source) nodeIdsToHighlight.push(edge.source);
                    if (edge.target) nodeIdsToHighlight.push(edge.target);
                }
            });
        }
    };

    // Estrai IDs dai dati originali e proposti
    extractIds(proposal.original_data);
    extractIds(proposal.proposed_data);

    // Rimuovi duplicati
    const uniqueNodeIds = [...new Set(nodeIdsToHighlight)];
    const uniqueEdgeIds = [...new Set(edgeIdsToHighlight)];

    // Resetta selezioni precedenti
    graphVisualization.unselectAll();

    // Seleziona/Evidenzia le entità trovate
    if (uniqueNodeIds.length > 0 || uniqueEdgeIds.length > 0) {
        graphVisualization.selectNodes(uniqueNodeIds);
        graphVisualization.selectEdges(uniqueEdgeIds);
        // Opzionale: zoom sulle entità evidenziate
        // graphVisualization.fit({ nodes: uniqueNodeIds, animation: true });
    } else {
        // Nessuna entità specifica trovata, forse è una proposta generica?
        // console.warn(`Nessuna entità specifica da evidenziare per la proposta ${proposal.id}`);
    }
}

// Funzione helper per resettare l'evidenziazione
function resetGraphHighlighting() {
     if (graphVisualization) {
        graphVisualization.unselectAll();
    }
}

// Renderizza la lista delle proposte
function renderProposalList(proposals) {
    const proposalList = document.getElementById('proposal-list');
    if (!proposalList) return;
    
    // Get the current filter value
    const statusFilter = document.getElementById('proposal-status-filter')?.value || 'all';

    // Filter proposals based on status
    const filteredProposals = proposals.filter(p => {
        if (statusFilter === 'all') return true;
        return p.status === statusFilter;
    });
    
    if (filteredProposals.length === 0) {
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
    
    filteredProposals.forEach(proposal => {
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

        // Aggiungi event listeners per hover sulla card per evidenziare
        item.addEventListener('mouseenter', () => highlightGraphEntities(proposal));
        item.addEventListener('mouseleave', resetGraphHighlighting);
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
    const originalData = proposal.original_data || {};
    const proposedData = proposal.proposed_data || {};
    
    let contentHtml = '';

    if (type === 'add') {
        const nodesToAdd = proposedData.nodes || [];
        const edgesToAdd = proposedData.edges || [];
        contentHtml = `
            <div class="alert alert-success small">
                <i class="fas fa-plus-circle me-1"></i> 
                <strong>Aggiunta:</strong> ${nodesToAdd.length} nodi, ${edgesToAdd.length} relazioni.
            </div>
            ${renderEntitiesTable(nodesToAdd, 'Nodi da Aggiungere')}${renderEntitiesTable(edgesToAdd, 'Relazioni da Aggiungere')}
        `;
    } else if (type === 'modify') {
        const nodesToModify = proposedData.nodes || [];
        const edgesToModify = proposedData.edges || [];
        contentHtml = `
            <div class="alert alert-warning small">
                <i class="fas fa-edit me-1"></i> 
                <strong>Modifica:</strong> ${nodesToModify.length} nodi, ${edgesToModify.length} relazioni.
            </div>
            <div class="row gx-2">
                <div class="col-md-6">
                    <h6>Originale</h6>
                    ${renderEntitiesTable(originalData.nodes, 'Nodi Originali', true)}${renderEntitiesTable(originalData.edges, 'Relazioni Originali', true)}
                </div>
                <div class="col-md-6">
                    <h6>Proposta</h6>
                    ${renderEntitiesTable(nodesToModify, 'Nodi Modificati')}${renderEntitiesTable(edgesToModify, 'Relazioni Modificate')}
                </div>
            </div>
        `;
    } else if (type === 'delete') {
        const nodesToDelete = proposedData.nodes || [];
        const edgesToDelete = proposedData.edges || [];
        contentHtml = `
            <div class="alert alert-danger small">
                <i class="fas fa-trash-alt me-1"></i> 
                <strong>Eliminazione:</strong> ${nodesToDelete.length} nodi, ${edgesToDelete.length} relazioni.
            </div>
            ${renderEntitiesTable(nodesToDelete, 'Nodi da Eliminare')}${renderEntitiesTable(edgesToDelete, 'Relazioni da Eliminare')}
        `;
    } else {
        contentHtml = `<div class="alert alert-secondary small">Proposta di tipo sconosciuto: ${type}</div>`;
    }
    
    return contentHtml;
}

// Funzione helper per renderizzare tabelle di entità
function renderEntitiesTable(entities, title, isOriginal = false) {
    if (!entities || entities.length === 0) {
        // Non mostrare nulla se non ci sono entità di quel tipo
        // return `<div class="text-muted small p-2"><em>${title}: Nessuna</em></div>`;
        return ''; 
    }

    let tableHtml = `<h6 class="mt-2 small ${isOriginal ? 'text-muted' : ''}">${title} (${entities.length})</h6>`;
    tableHtml += `<div class="table-responsive" style="max-height: 150px; overflow-y: auto;">`;
    tableHtml += `<table class="table table-sm table-bordered small font-monospace">`;
    
    // Determina le colonne (semplificato)
    let headers = [];
    if (entities[0]?.source !== undefined) { // Sembra una relazione
        headers = ['ID', 'Source', 'Target', 'Type', 'Props'];
    } else { // Sembra un nodo
        headers = ['ID', 'Label', 'Type', 'Props'];
    }

    tableHtml += `<thead><tr>${headers.map(h => `<th>${h}</th>`).join('')}</tr></thead><tbody>`;

    entities.forEach(entity => {
        tableHtml += `<tr>`;
        headers.forEach(header => {
            const key = header.toLowerCase();
            let value = entity[key];
            if (key === 'props') {
                // Estrai proprietà extra
                const coreKeys = ['id', 'label', 'type', 'source', 'target'];
                const props = Object.entries(entity)
                                  .filter(([k, v]) => !coreKeys.includes(k))
                                  .reduce((obj, [k, v]) => ({ ...obj, [k]: v }), {});
                value = Object.keys(props).length > 0 ? JSON.stringify(props) : '-';
            } else {
                 value = value !== undefined ? value : '-';
            }
            // Rendi l'ID cliccabile per evidenziare? (Futuro miglioramento)
            // if (key === 'id') value = `<a href="#" class="entity-link" data-id="${value}">${value}</a>`;
            tableHtml += `<td>${escapeHtml(String(value))}</td>`;
        });
        tableHtml += `</tr>`;
    });

    tableHtml += `</tbody></table></div>`;
    return tableHtml;
}

// Funzione di escape HTML base
function escapeHtml(unsafe) {
    if (unsafe === null || unsafe === undefined) return '';
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
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
            
            // Update proposal list immediately to reflect vote changes
            loadChunkProposals(currentChunkId); 
            
            // Check if the proposal was applied (backend should indicate this)
            // Let's assume the backend now returns e.g., response.result.proposal_applied = true
            if (response.result?.proposal_applied) {
                showNotification('Proposta approvata e applicata al grafo! Aggiornamento in corso...', 'success');
                
                // Reload the chunk data and graph visualization
                // Use a small delay to allow backend processing if needed, or rely on eventual consistency
                // setTimeout(() => { selectChunk(currentChunkId); }, 500); 
                // Or better: Reload immediately, assuming backend update is fast enough
                await selectChunk(currentChunkId); 

                // Optionally refresh the chunk list as well if the chunk status changed
                const currentFilter = document.getElementById('chunk-filter')?.value || 'pending';
                await loadAssignedChunks(currentFilter);

            } else if (response.result?.proposal_approved && !response.result?.proposal_applied) {
                // Approved but maybe not applied yet or failed application?
                // Backend logic determines this. If apply failed, backend should update status.
                showNotification('Proposta approvata, in attesa di applicazione o errore.', 'info');
            } else if (response.result?.proposal_rejected) {
                showNotification('La proposta è stata respinta.', 'warning');
            }
        } else {
             // Use the error message from the backend response if available
            const errorMessage = response?.message || 'Errore nel registrare il voto';
            showNotification(errorMessage, 'danger');
        }
    } catch (error) {
        console.error('Error voting on proposal:', error);
        showNotification(`Errore: ${error.message}`, 'danger');
    } finally {
        hideLoading();
    }
}

// Mostra l'editor per creare una nuova proposta
function showProposalEditor(presetType = null, presetEntityType = null) {
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
        
        // Pre-select types if provided
        if (presetType) {
            document.getElementById('proposalType').value = presetType;
        }
        if (presetEntityType) {
             document.getElementById('entityType').value = presetEntityType;
        }
        
        // Update form based on presets
        updateProposalForm();

        // Add selected entities if modifying/deleting
        if ((presetType === 'modify' || presetType === 'delete') && presetEntityType) {
            addSelectedGraphEntitiesToForm(presetEntityType);
        }

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
            const selectedEntities = getSelectedEntitiesFromForm();
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

// Ottieni le entità selezionate DAL FORM della proposta (non più direttamente dal grafo)
function getSelectedEntitiesFromForm() {
    const selectedEntitiesList = document.getElementById('selectedEntitiesList');
    if (!selectedEntitiesList) return [];

    const entities = [];
    const items = selectedEntitiesList.querySelectorAll('.list-group-item');
    
    items.forEach(item => {
        const entityId = item.dataset.entityId;
        // We only need the ID for delete/modify proposals usually
        // If more data is needed, store it in data-* attributes or retrieve from graphVisualization
        if (entityId) {
             entities.push({ id: entityId }); // Simplification: just send ID
             // Retrieve full data if needed:
             // const nodeData = graphVisualization.body.data.nodes.get(entityId);
             // const edgeData = graphVisualization.body.data.edges.get(entityId);
             // if (nodeData) entities.push({ id: nodeData.id, label: nodeData.label, type: nodeData.group });
             // else if (edgeData) entities.push({ id: edgeData.id, source: edgeData.from, target: edgeData.to, type: edgeData.label });
        }
    });
    
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

// Setup event listeners for the new proposal buttons
function setupProposalInitiationListeners() {
    document.getElementById('init-add-proposal-btn')?.addEventListener('click', () => {
        showProposalEditor('add');
    });

    document.getElementById('init-modify-proposal-btn')?.addEventListener('click', () => {
        const selectedNodes = graphVisualization?.getSelectedNodes() || [];
        const selectedEdges = graphVisualization?.getSelectedEdges() || [];
        if (selectedNodes.length === 0 && selectedEdges.length === 0) {
            showNotification('Seleziona almeno un nodo o una relazione dal grafo per proporre una modifica.', 'warning');
            return;
        }
        const entityType = selectedNodes.length > 0 ? 'nodes' : 'edges'; // Prefer nodes if both selected
        showProposalEditor('modify', entityType);
    });

    document.getElementById('init-delete-proposal-btn')?.addEventListener('click', () => {
         const selectedNodes = graphVisualization?.getSelectedNodes() || [];
        const selectedEdges = graphVisualization?.getSelectedEdges() || [];
        if (selectedNodes.length === 0 && selectedEdges.length === 0) {
            showNotification('Seleziona almeno un nodo o una relazione dal grafo per proporre un\'eliminazione.', 'warning');
            return;
        }
         const entityType = selectedNodes.length > 0 ? 'nodes' : 'edges';
        showProposalEditor('delete', entityType);
    });

    // Listener for proposal status filter
    document.getElementById('proposal-status-filter')?.addEventListener('change', (e) => {
        renderProposalList(currentProposals); // Re-render with the new filter value
    });
}

// Helper function to add currently selected graph entities to the proposal form
function addSelectedGraphEntitiesToForm(entityType) {
    const selectedEntitiesList = document.getElementById('selectedEntitiesList');
    if (!selectedEntitiesList) return;

    selectedEntitiesList.innerHTML = ''; // Clear previous selections in form

    const selectedNodes = graphVisualization?.getSelectedNodes() || [];
    const selectedEdges = graphVisualization?.getSelectedEdges() || [];

    if (entityType === 'nodes') {
        selectedNodes.forEach(nodeId => {
            const nodeData = graphVisualization.body.data.nodes.get(nodeId);
            if (nodeData) addEntityElementToList(nodeData, 'node', selectedEntitiesList);
        });
    } else if (entityType === 'edges') {
        selectedEdges.forEach(edgeId => {
            const edgeData = graphVisualization.body.data.edges.get(edgeId);
            if (edgeData) addEntityElementToList(edgeData, 'edge', selectedEntitiesList);
        });
    }
}

// Helper to create and add list item for an entity to the form
function addEntityElementToList(entityData, entityType, listElement) {
     const entityItem = document.createElement('div');
    entityItem.className = 'list-group-item d-flex justify-content-between align-items-center py-1 px-2 small';
    entityItem.dataset.entityId = entityData.id;
    
    let labelHtml = '';
    if (entityType === 'node') {
        labelHtml = `
            <span>
                <i class="fas fa-cube me-1"></i> 
                <strong>${entityData.label || entityData.id}</strong>
                <span class="badge bg-secondary ms-1">${entityData.group}</span>
            </span>
        `;
    } else { // edge
        labelHtml = `
            <span>
                 <i class="fas fa-exchange-alt me-1"></i>
                <strong>${entityData.label || 'Relazione'}</strong>
                <small class="ms-1 text-muted">(${entityData.from} → ${entityData.to})</small>
            </span>
        `;
    }

    entityItem.innerHTML = `
        ${labelHtml}
        <button type="button" class="btn btn-sm btn-outline-danger remove-entity-btn border-0 p-0 ms-2">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    // Add event listener to remove the entity
    entityItem.querySelector('.remove-entity-btn')?.addEventListener('click', function() {
        entityItem.remove();
    });
    
    listElement.appendChild(entityItem);
}