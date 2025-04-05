/**
 * api.js
 * Centralized API interaction functions
 */

const API_BASE = '/api'; // Or use Flask's url_for if needed via data attributes

async function request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
    };
    const config = { ...defaultOptions, ...options };
    
    // Special handling for FormData (file uploads)
    if (config.body instanceof FormData) {
        // For FormData, let the browser set the Content-Type header with proper boundary
        delete config.headers['Content-Type'];
    } else if (config.body && typeof config.body !== 'string') {
        config.body = JSON.stringify(config.body);
    }

    try {
        const response = await fetch(url, config);
        if (!response.ok) {
            let errorData;
            try {
                errorData = await response.json();
            } catch (e) {
                errorData = { message: `HTTP error! status: ${response.status}` };
            }
            console.error(`API Error (${response.status}) on ${endpoint}:`, errorData);
            throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }
        // Handle cases where the response might be empty (e.g., 204 No Content)
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.indexOf("application/json") !== -1) {
            return await response.json();
        } else {
            // Handle non-JSON responses if necessary, or return null/undefined
            return null; // Or response.text() if text is expected
        }
    } catch (error) {
        console.error(`Fetch Error on ${endpoint}:`, error);
        throw error; // Re-throw to be caught by the caller
    }
}

export const api = {
    // Auth Endpoints
    login: (username, password, remember) => request('/login', { 
        method: 'POST', 
        body: { username, password, remember } 
    }),
    logout: () => request('/logout', { method: 'POST' }),
    register: (userData) => request('/register', { method: 'POST', body: userData }),

    // Profile Management
    updateProfile: (data) => request('/profile/edit', { method: 'POST', body: data }),
    changePassword: (currentPassword, newPassword) => request('/profile/change_password', { 
        method: 'POST', 
        body: { current_password: currentPassword, new_password: newPassword } 
    }),

    // User Management (Admin)
    getUsers: () => request('/admin/users'),
    createUser: (userData) => request('/admin/users', { method: 'POST', body: userData }),
    updateUser: (userId, userData) => request(`/admin/users/${userId}`, { method: 'PUT', body: userData }),
    deleteUser: (userId) => request(`/admin/users/${userId}`, { method: 'DELETE' }),
    
    // Document Endpoints
    getDocuments: () => request('/documents'),
    uploadDocument: (formData) => request('/upload_document', { method: 'POST', body: formData, headers: {} }), // Add /api/ prefix
    deleteDocument: (docId) => request('/delete_document', { method: 'POST', body: { doc_id: docId } }),
    updateDocument: (docId, data) => request('/update_document', { method: 'POST', body: { doc_id: docId, ...data } }),

    // Annotation Endpoints
    saveAnnotation: (docId, annotation) => request('/save_annotation', { method: 'POST', body: { doc_id: docId, annotation } }),
    deleteAnnotation: (docId, annotationId) => request('/delete_annotation', { method: 'POST', body: { doc_id: docId, annotation_id: annotationId } }),
    updateAnnotation: (docId, annotation) => request('/update_annotation', { method: 'POST', body: { doc_id: docId, annotation } }),
    clearAnnotations: (docId, entityType = null) => request('/clear_annotations', { method: 'POST', body: { doc_id: docId, entity_type: entityType } }),
    recognizeEntities: (text) => request('/recognize', { method: 'POST', body: { text } }),
    exportAnnotations: (format = 'json', download = false) => request(`/export_annotations?format=${format}&download=${download}`), // GET request

    // Entity Type Endpoints
    getEntityTypes: () => request('/entity_types'),
    createEntityType: (data) => request('/entity_types', { method: 'POST', body: data }),
    updateEntityType: (name, data) => request(`/entity_types/${name}`, { method: 'PUT', body: data }),
    deleteEntityType: (name) => request(`/entity_types/${name}`, { method: 'DELETE' }),
    testPattern: (pattern, text) => request('/test_pattern', { method: 'POST', body: { pattern, text } }),

    // Stats & Analytics
    getStats: (filters = {}) => request('/annotation_stats', { 
        method: 'GET', 
        params: new URLSearchParams(filters)
    }),
    getUserStats: (userId = null) => request(`/user_stats${userId ? `?user_id=${userId}` : ''}`),
    getProjectProgress: () => request('/project_progress'),
    getEntityDistribution: () => request('/entity_distribution'),

    // Assignment Management
    assignDocument: (docId, userId) => request('/assign_document', { 
        method: 'POST', 
        body: { doc_id: docId, user_id: userId } 
    }),
    getAssignments: (userId = null) => request(`/assignments${userId ? `?user_id=${userId}` : ''}`),
    removeAssignment: (docId, userId) => request('/remove_assignment', { 
        method: 'POST', 
        body: { doc_id: docId, user_id: userId } 
    }),

    // Helper Functions
    isAuthenticated: () => Boolean(document.body.dataset.userAuthenticated === 'true'),
    getUserRole: () => document.body.dataset.userRole || '',
    isAdmin: () => document.body.dataset.userRole === 'admin',
    getCurrentUserId: () => document.body.dataset.userId || '',
    refreshPage: () => window.location.reload(),

    // Error Handling Helper
    handleError: (error) => {
        console.error('API Error:', error);
        if (error.message.includes('Autenticazione richiesta')) {
            window.location.href = '/login';
            return;
        }
        // You can add custom error handling here
        throw error;
    }
};