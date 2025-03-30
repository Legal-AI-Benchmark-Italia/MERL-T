// EntityManager.js
// Componente React per la gestione delle entità
import React, { useState, useEffect } from 'react';

// Componente principale per la gestione delle entità
function EntityManager() {
  const [entities, setEntities] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [editingEntity, setEditingEntity] = useState(null);
  const [newEntity, setNewEntity] = useState({
    name: '',
    display_name: '',
    category: 'custom',
    color: '#CCCCCC',
    metadata_fields: []
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Categorie disponibili
  const categories = [
    { id: 'all', name: 'Tutte le categorie' },
    { id: 'normative', name: 'Riferimenti normativi' },
    { id: 'jurisprudence', name: 'Riferimenti giurisprudenziali' },
    { id: 'concepts', name: 'Concetti giuridici' },
    { id: 'custom', name: 'Entità personalizzate' }
  ];

  // Tipi di campi disponibili per i metadati
  const fieldTypes = [
    { id: 'string', name: 'Testo' },
    { id: 'number', name: 'Numero' },
    { id: 'boolean', name: 'Booleano' },
    { id: 'date', name: 'Data' }
  ];

  // Carica le entità all'avvio e quando cambia la categoria selezionata
  useEffect(() => {
    fetchEntities();
  }, [selectedCategory]);

  // Funzione per caricare le entità
  const fetchEntities = async () => {
    try {
      const url = selectedCategory === 'all' 
        ? '/api/v1/entities/' 
        : `/api/v1/entities/?category=${selectedCategory}`;
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Errore nel caricamento delle entità: ${response.statusText}`);
      }
      
      const data = await response.json();
      setEntities(data);
    } catch (error) {
      setError(error.message);
      console.error('Errore nel caricamento delle entità:', error);
    }
  };

  // Funzione per creare una nuova entità
  const createEntity = async () => {
    try {
      // Validazione
      if (!newEntity.name) {
        setError('Il nome dell\'entità è obbligatorio');
        return;
      }
      
      if (!newEntity.name.match(/^[A-Z][A-Z0-9_]*$/)) {
        setError('Il nome dell\'entità deve essere in maiuscolo e può contenere solo lettere, numeri e underscore');
        return;
      }
      
      if (!newEntity.display_name) {
        setError('Il nome visualizzato è obbligatorio');
        return;
      }
      
      // Invia la richiesta
      const response = await fetch('/api/v1/entities/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(newEntity)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Errore nella creazione dell'entità: ${response.statusText}`);
      }
      
      // Aggiorna la lista delle entità
      await fetchEntities();
      
      // Resetta il form
      setNewEntity({
        name: '',
        display_name: '',
        category: 'custom',
        color: '#CCCCCC',
        metadata_fields: []
      });
      
      setSuccess(`Entità ${newEntity.name} creata con successo`);
      setTimeout(() => setSuccess(''), 3000);
    } catch (error) {
      setError(error.message);
      console.error('Errore nella creazione dell\'entità:', error);
    }
  };

  // Funzione per aggiornare un'entità esistente
  const updateEntity = async () => {
    try {
      if (!editingEntity) return;
      
      // Validazione
      if (!editingEntity.display_name) {
        setError('Il nome visualizzato è obbligatorio');
        return;
      }
      
      // Prepara i dati per l'aggiornamento
      const updateData = {
        display_name: editingEntity.display_name,
        color: editingEntity.color,
        metadata_fields: editingEntity.metadata_fields
      };
      
      // Invia la richiesta
      const response = await fetch(`/api/v1/entities/${editingEntity.name}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updateData)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Errore nell'aggiornamento dell'entità: ${response.statusText}`);
      }
      
      // Aggiorna la lista delle entità
      await fetchEntities();
      
      // Chiudi il form di modifica
      setEditingEntity(null);
      
      setSuccess(`Entità ${editingEntity.name} aggiornata con successo`);
      setTimeout(() => setSuccess(''), 3000);
    } catch (error) {
      setError(error.message);
      console.error('Errore nell\'aggiornamento dell\'entità:', error);
    }
  };

  // Funzione per eliminare un'entità
  const deleteEntity = async (entityName) => {
    if (!confirm(`Sei sicuro di voler eliminare l'entità ${entityName}?`)) {
      return;
    }
    
    try {
      const response = await fetch(`/api/v1/entities/${entityName}`, {
        method: 'DELETE'
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Errore nell'eliminazione dell'entità: ${response.statusText}`);
      }
      
      // Aggiorna la lista delle entità
      await fetchEntities();
      
      setSuccess(`Entità ${entityName} eliminata con successo`);
      setTimeout(() => setSuccess(''), 3000);
    } catch (error) {
      setError(error.message);
      console.error('Errore nell\'eliminazione dell\'entità:', error);
    }
  };

  // Funzione per aggiungere un campo metadati all'entità in creazione
  const addMetadataField = () => {
    setNewEntity({
      ...newEntity,
      metadata_fields: [
        ...newEntity.metadata_fields,
        { name: '', field_type: 'string', description: '', required: false }
      ]
    });
  };

  // Funzione per aggiungere un campo metadati all'entità in modifica
  const addMetadataFieldToEditing = () => {
    if (!editingEntity) return;
    
    setEditingEntity({
      ...editingEntity,
      metadata_fields: [
        ...editingEntity.metadata_fields,
        { name: '', field_type: 'string', description: '', required: false }
      ]
    });
  };

  // Funzione per aggiornare un campo metadati dell'entità in creazione
  const updateMetadataField = (index, field, value) => {
    const updatedFields = [...newEntity.metadata_fields];
    updatedFields[index] = { ...updatedFields[index], [field]: value };
    
    setNewEntity({
      ...newEntity,
      metadata_fields: updatedFields
    });
  };

  // Funzione per aggiornare un campo metadati dell'entità in modifica
  const updateEditingMetadataField = (index, field, value) => {
    if (!editingEntity) return;
    
    const updatedFields = [...editingEntity.metadata_fields];
    updatedFields[index] = { ...updatedFields[index], [field]: value };
    
    setEditingEntity({
      ...editingEntity,
      metadata_fields: updatedFields
    });
  };

  // Funzione per rimuovere un campo metadati dall'entità in creazione
  const removeMetadataField = (index) => {
    const updatedFields = [...newEntity.metadata_fields];
    updatedFields.splice(index, 1);
    
    setNewEntity({
      ...newEntity,
      metadata_fields: updatedFields
    });
  };

  // Funzione per rimuovere un campo metadati dall'entità in modifica
  const removeEditingMetadataField = (index) => {
    if (!editingEntity) return;
    
    const updatedFields = [...editingEntity.metadata_fields];
    updatedFields.splice(index, 1);
    
    setEditingEntity({
      ...editingEntity,
      metadata_fields: updatedFields
    });
  };

  return (
    <div className="entity-manager-container">
      <h1>Gestione Entità</h1>
      
      {/* Messaggi di errore e successo */}
      {error && <div className="error-message">{error}</div>}
      {success && <div className="success-message">{success}</div>}
      
      {/* Selezione categoria */}
      <div className="category-filter">
        <label htmlFor="category-select">Filtra per categoria:</label>
        <select 
          id="category-select" 
          value={selectedCategory} 
          onChange={(e) => setSelectedCategory(e.target.value)}
        >
          {categories.map(category => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </select>
      </div>
      
      {/* Lista delle entità */}
      <div className="entities-list">
        <h2>Entità Disponibili</h2>
        <table>
          <thead>
            <tr>
              <th>Nome</th>
              <th>Nome Visualizzato</th>
              <th>Categoria</th>
              <th>Colore</th>
              <th>Campi Metadati</th>
              <th>Azioni</th>
            </tr>
          </thead>
          <tbody>
            {entities.map(entity => (
              <tr key={entity.name}>
                <td>{entity.name}</td>
                <td>{entity.display_name}</td>
                <td>{entity.category}</td>
                <td>
                  <div 
                    className="color-preview" 
                    style={{ backgroundColor: entity.color }}
                    title={entity.color}
                  />
                </td>
                <td>{entity.metadata_fields.length} campi</td>
                <td>
                  <button 
                    onClick={() => setEditingEntity(entity)}
                    className="edit-button"
                  >
                    Modifica
                  </button>
                  {entity.category === 'custom' && (
                    <button 
                      onClick={() => deleteEntity(entity.name)}
                      className="delete-button"
                    >
                      Elimina
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      
      {/* Form per la creazione di una nuova entità */}
      <div className="entity-form">
        <h2>Crea Nuova Entità</h2>
        <div className="form-group">
          <label htmlFor="new-entity-name">Nome (maiuscolo, senza spazi):</label>
          <input 
            id="new-entity-name"
            type="text" 
            value={newEntity.name} 
            onChange={(e) => setNewEntity({...newEntity, name: e.target.value})}
            placeholder="ES: NUOVO_TIPO_ENTITA"
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="new-entity-display-name">Nome Visualizzato:</label>
          <input 
            id="new-entity-display-name"
            type="text" 
            value={newEntity.display_name} 
            onChange={(e) => setNewEntity({...newEntity, display_name: e.target.value})}
            placeholder="Es: Nuovo Tipo Entità"
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="new-entity-category">Categoria:</label>
          <select 
            id="new-entity-category"
            value={newEntity.category} 
            onChange={(e) => setNewEntity({...newEntity, category: e.target.value})}
          >
            <option value="normative">Riferimenti normativi</option>
            <option value="jurisprudence">Riferimenti giurisprudenziali</option>
            <option value="concepts">Concetti giuridici</option>
            <option value="custom">Entità personalizzate</option>
          </select>
        </div>
        
        <div className="form-group">
          <label htmlFor="new-entity-color">Colore:</label>
          <input 
            id="new-entity-color"
            type="color" 
            value={newEntity.color} 
            onChange={(e) => setNewEntity({...newEntity, color: e.target.value})}
          />
        </div>
        
        <div className="metadata-fields">
          <h3>Campi Metadati</h3>
          {newEntity.metadata_fields.map((field, index) => (
            <div key={index} className="metadata-field">
              <input 
                type="text"
                placeholder="Nome campo"
                value={field.name}
                onChange={(e) => updateMetadataField(index, 'name', e.target.value)}
              />
              
              <select 
                value={field.field_type}
                onChange={(e) => updateMetadataField(index, 'field_type', e.target.value)}
              >
                {fieldTypes.map(type => (
                  <option key={type.id} value={type.id}>{type.name}</option>
                ))}
              </select>
              
              <input 
                type="text"
                placeholder="Descrizione"
                value={field.description}
                onChange={(e) => updateMetadataField(index, 'description', e.target.value)}
              />
              
              <label>
                <input 
                  type="checkbox"
                  checked={field.required}
                  onChange={(e) => updateMetadataField(index, 'required', e.target.checked)}
                />
                Obbligatorio
              </label>
              
              <button 
                onClick={() => removeMetadataField(index)}
                className="remove-field"
              >
                Rimuovi
              </button>
            </div>
          ))}
          
          <button 
            onClick={addMetadataField}
            className="add-field-button"
          >
            Aggiungi Campo
          </button>
        </div>
        
        <button 
          onClick={createEntity}
          className="create-button"
        >
          Crea Entità
        </button>
      </div>
      
      {/* Modal per la modifica di un'entità esistente */}
      {editingEntity && (
        <div className="edit-modal">
          <div className="modal-content">
            <h2>Modifica Entità: {editingEntity.name}</h2>
            
            <div className="form-group">
              <label htmlFor="edit-entity-display-name">Nome Visualizzato:</label>
              <input 
                id="edit-entity-display-name"
                type="text" 
                value={editingEntity.display_name} 
                onChange={(e) => setEditingEntity({...editingEntity, display_name: e.target.value})}
              />
            </div>
            
            <div className="form-group">
              <label htmlFor="edit-entity-color">Colore:</label>
              <input 
                id="edit-entity-color"
                type="color" 
                value={editingEntity.color} 
                onChange={(e) => setEditingEntity({...editingEntity, color: e.target.value})}
              />
            </div>
            
            <div className="metadata-fields">
              <h3>Campi Metadati</h3>
              {editingEntity.metadata_fields.map((field, index) => (
                <div key={index} className="metadata-field">
                  <input 
                    type="text"
                    placeholder="Nome campo"
                    value={field.name}
                    onChange={(e) => updateEditingMetadataField(index, 'name', e.target.value)}
                  />
                  
                  <select 
                    value={field.field_type}
                    onChange={(e) => updateEditingMetadataField(index, 'field_type', e.target.value)}
                  >
                    {fieldTypes.map(type => (
                      <option key={type.id} value={type.id}>{type.name}</option>
                    ))}
                  </select>
                  
                  <input 
                    type="text"
                    placeholder="Descrizione"
                    value={field.description}
                    onChange={(e) => updateEditingMetadataField(index, 'description', e.target.value)}
                  />
                  
                  <label>
                    <input 
                      type="checkbox"
                      checked={field.required}
                      onChange={(e) => updateEditingMetadataField(index, 'required', e.target.checked)}
                    />
                    Obbligatorio
                  </label>
                  
                  <button 
                    onClick={() => removeEditingMetadataField(index)}
                    className="remove-field"
                  >
                    Rimuovi
                  </button>
                </div>
              ))}
              
              <button 
                onClick={addMetadataFieldToEditing}
                className="add-field-button"
              >
                Aggiungi Campo
              </button>
            </div>
            
            <div className="modal-buttons">
              <button 
                onClick={updateEntity}
                className="update-button"
              >
                Aggiorna
              </button>
              
              <button 
                onClick={() => setEditingEntity(null)}
                className="cancel-button"
              >
                Annulla
              </button>
            </div>
          </div>
        </div>
      )}
      
      <style jsx>{`
        .entity-manager-container {
          padding: 20px;
          max-width: 1200px;
          margin: 0 auto;
        }
        
        h1, h2, h3 {
          color: #333;
        }
        
        .error-message {
          background-color: #ffebee;
          color: #c62828;
          padding: 10px;
          border-radius: 4px;
          margin-bottom: 15px;
        }
        
        .success-message {
          background-color: #e8f5e9;
          color: #2e7d32;
          padding: 10px;
          border-radius: 4px;
          margin-bottom: 15px;
        }
        
        .category-filter {
          margin-bottom: 20px;
        }
        
        .category-filter select {
          padding: 8px;
          border-radius: 4px;
          border: 1px solid #ccc;
          margin-left: 10px;
        }
        
        .entities-list {
          margin-bottom: 30px;
        }
        
        table {
          width: 100%;
          border-collapse: collapse;
        }
        
        th, td {
          padding: 10px;
          text-align: left;
          border-bottom: 1px solid #ddd;
        }
        
        th {
          background-color: #f5f5f5;
        }
        
        .color-preview {
          width: 20px;
          height: 20px;
          border-radius: 4px;
          display: inline-block;
        }
        
        .edit-button, .delete-button {
          padding: 5px 10px;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          margin-right: 5px;
        }
        
        .edit-button {
          background-color: #2196f3;
          color: white;
        }
        
        .delete-button {
          background-color: #f44336;
          color: white;
        }
        
        .entity-form {
          background-color: #f9f9f9;
          padding: 20px;
          border-radius: 4px;
        }
        
        .form-group {
          margin-bottom: 15px;
        }
        
        .form-group label {
          display: block;
          margin-bottom: 5px;
        }
        
        .form-group input, .form-group select {
          width: 100%;
          padding: 8px;
          border-radius: 4px;
          border: 1px solid #ccc;
        }
        
        .metadata-fields {
          margin-top: 20px;
        }
        
        .metadata-field {
          display: flex;
          gap: 10px;
          margin-bottom: 10px;
          align-items: center;
        }
        
        .metadata-field input, .metadata-field select {
          padding: 8px;
          border-radius: 4px;
          border: 1px solid #ccc;
        }
        
        .remove-field {
          background-color: #f44336;
          color: white;
          border: none;
          border-radius: 4px;
          padding: 5px 10px;
          cursor: pointer;
        }
        
        .add-field-button {
          background-color: #4caf50;
          color: white;
          border: none;
          border-radius: 4px;
          padding: 8px 15px;
          cursor: pointer;
          margin-bottom: 20px;
        }
        
        .create-button, .update-button {
          background-color: #2196f3;
          color: white;
          border: none;
          border-radius: 4px;
          padding: 10px 20px;
          cursor: pointer;
          font-size: 16px;
        }
        
        .edit-modal {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background-color: rgba(0, 0, 0, 0.5);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 1000;
        }
        
        .modal-content {
          background-color: white;
          padding: 20px;
          border-radius: 4px;
          max-width: 800px;
          width: 100%;
          max-height: 90vh;
          overflow-y: auto;
        }
        
        .modal-buttons {
          display: flex;
          justify-content: flex-end;
          gap: 10px;
          margin-top: 20px;
        }
        
        .cancel-button {
          background-color: #9e9e9e;
          color: white;
          border: none;
          border-radius: 4px;
          padding: 10px 20px;
          cursor: pointer;
        }
      `}</style>
    </div>
  );
}

export default EntityManager;