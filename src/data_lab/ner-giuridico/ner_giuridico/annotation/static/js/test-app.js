/**
 * test-app.js - Script per testare le funzionalità dell'applicazione
 * 
 * Questo script esegue una serie di test per verificare il corretto funzionamento
 * dell'applicazione dopo il refactoring.
 * 
 * @version 1.0.0
 */

import eventBus from './core/event-bus.js';
import store from './core/store.js';
import errorHandler from './core/error-handler.js';
import config from './config/config.js';
import annotationService from './services/annotation-service.js';
import documentService from './services/document-service.js';
import entityService from './services/entity-service.js';
import notificationService from './services/notification-service.js';
import highlightingComponent from './components/highlighting-component.js';

/**
 * Esegue tutti i test
 */
async function runAllTests() {
    console.group('Test dell\'applicazione NER-Giuridico');
    console.info('Inizio dei test...');
    
    let passedTests = 0;
    let failedTests = 0;
    
    try {
        // Test dei componenti core
        await testCoreComponents() ? passedTests++ : failedTests++;
        
        // Test dei servizi
        await testServices() ? passedTests++ : failedTests++;
        
        // Test dei componenti UI
        await testUIComponents() ? passedTests++ : failedTests++;
        
        // Test dell'integrazione
        await testIntegration() ? passedTests++ : failedTests++;
        
        console.info(`Test completati: ${passedTests} passati, ${failedTests} falliti`);
    } catch (error) {
        console.error('Errore durante l\'esecuzione dei test:', error);
    }
    
    console.groupEnd();
}

/**
 * Testa i componenti core
 * @returns {Promise<boolean>} - true se tutti i test passano
 */
async function testCoreComponents() {
    console.group('Test dei componenti core');
    let allPassed = true;
    
    try {
        // Test dell'EventBus
        console.info('Test dell\'EventBus...');
        let eventReceived = false;
        
        const subscription = eventBus.on('test-event', (data) => {
            eventReceived = true;
            console.assert(data.message === 'test', 'EventBus: dati evento non corretti');
        });
        
        eventBus.emit('test-event', { message: 'test' });
        
        console.assert(eventReceived, 'EventBus: evento non ricevuto');
        subscription.unsubscribe();
        
        // Test dello Store
        console.info('Test dello Store...');
        let stateChanged = false;
        
        const stateSubscription = store.watch('test.value', (value) => {
            stateChanged = true;
            console.assert(value === 'test-value', 'Store: valore non corretto');
        });
        
        store.commit('TEST_COMMIT', 'test.value', 'test-value');
        
        console.assert(stateChanged, 'Store: stato non aggiornato');
        console.assert(store.getState('test.value') === 'test-value', 'Store: getState non funziona correttamente');
        
        stateSubscription.unsubscribe();
        
        // Test dell'ErrorHandler
        console.info('Test dell\'ErrorHandler...');
        const errorId = errorHandler.handleError('Test error', 'test', { test: true }, false);
        
        console.assert(errorId && typeof errorId === 'string', 'ErrorHandler: ID errore non generato');
        
        const errorLog = errorHandler.getErrorLog();
        console.assert(errorLog.length > 0, 'ErrorHandler: log errori vuoto');
        console.assert(errorLog.some(e => e.id === errorId), 'ErrorHandler: errore non registrato nel log');
        
        console.info('Test dei componenti core completati con successo');
    } catch (error) {
        console.error('Errore durante il test dei componenti core:', error);
        allPassed = false;
    }
    
    console.groupEnd();
    return allPassed;
}

/**
 * Testa i servizi
 * @returns {Promise<boolean>} - true se tutti i test passano
 */
async function testServices() {
    console.group('Test dei servizi');
    let allPassed = true;
    
    try {
        // Mock delle risposte API
        mockApiResponses();
        
        // Test del DocumentService
        console.info('Test del DocumentService...');
        const documents = await documentService.loadDocuments();
        
        console.assert(Array.isArray(documents), 'DocumentService: loadDocuments non restituisce un array');
        console.assert(documents.length > 0, 'DocumentService: nessun documento caricato');
        
        const filteredDocs = documentService.filterDocuments('test');
        console.assert(Array.isArray(filteredDocs), 'DocumentService: filterDocuments non restituisce un array');
        
        // Test dell'EntityService
        console.info('Test dell\'EntityService...');
        const entityTypes = await entityService.loadEntityTypes();
        
        console.assert(Array.isArray(entityTypes), 'EntityService: loadEntityTypes non restituisce un array');
        console.assert(entityTypes.length > 0, 'EntityService: nessun tipo di entità caricato');
        
        const entityType = entityService.getEntityType(entityTypes[0].id);
        console.assert(entityType && entityType.id === entityTypes[0].id, 'EntityService: getEntityType non funziona correttamente');
        
        // Test dell'AnnotationService
        console.info('Test dell\'AnnotationService...');
        const docId = documents[0].id;
        store.commit('SET_DOCUMENT_ID', 'annotator.docId', docId);
        
        const annotations = await annotationService.loadAnnotations(docId);
        console.assert(Array.isArray(annotations), 'AnnotationService: loadAnnotations non restituisce un array');
        
        // Test del NotificationService
        console.info('Test del NotificationService...');
        notificationService.info('Test notification', { duration: 100 });
        
        console.info('Test dei servizi completati con successo');
    } catch (error) {
        console.error('Errore durante il test dei servizi:', error);
        allPassed = false;
    }
    
    console.groupEnd();
    return allPassed;
}

/**
 * Testa i componenti UI
 * @returns {Promise<boolean>} - true se tutti i test passano
 */
async function testUIComponents() {
    console.group('Test dei componenti UI');
    let allPassed = true;
    
    try {
        // Test del HighlightingComponent
        console.info('Test del HighlightingComponent...');
        
        // Crea un elemento di test
        const testContainer = document.createElement('div');
        testContainer.id = 'test-container';
        testContainer.textContent = 'Questo è un testo di test per l\'evidenziazione.';
        document.body.appendChild(testContainer);
        
        // Inizializza il componente
        const initialized = highlightingComponent.initialize(testContainer);
        console.assert(initialized, 'HighlightingComponent: inizializzazione fallita');
        
        // Crea un'annotazione di test
        const testAnnotation = {
            id: 'test_ann_1',
            start: 0,
            end: 6,
            text: 'Questo',
            type: 'TEST_TYPE'
        };
        
        // Aggiungi un tipo di entità fittizio allo store
        const entityTypes = [
            { id: 'TEST_TYPE', name: 'Test Type', color: '#FF0000' }
        ];
        store.commit('SET_ENTITY_TYPES', 'entities.types', entityTypes);
        
        // Evidenzia l'annotazione
        highlightingComponent.highlightAnnotation(testAnnotation);
        
        // Verifica che l'evidenziazione sia stata creata
        const highlight = testContainer.querySelector('.annotation-highlight');
        console.assert(highlight, 'HighlightingComponent: evidenziazione non creata');
        console.assert(highlight.dataset.id === 'test_ann_1', 'HighlightingComponent: ID annotazione non corretto');
        
        // Pulisci
        highlightingComponent.clearAllHighlights();
        document.body.removeChild(testContainer);
        
        console.info('Test dei componenti UI completati con successo');
    } catch (error) {
        console.error('Errore durante il test dei componenti UI:', error);
        allPassed = false;
    }
    
    console.groupEnd();
    return allPassed;
}

/**
 * Testa l'integrazione tra i componenti
 * @returns {Promise<boolean>} - true se tutti i test passano
 */
async function testIntegration() {
    console.group('Test di integrazione');
    let allPassed = true;
    
    try {
        // Test dell'integrazione tra EventBus e servizi
        console.info('Test dell\'integrazione tra EventBus e servizi...');
        
        let documentsLoaded = false;
        const subscription = eventBus.on('document:loaded', () => {
            documentsLoaded = true;
        });
        
        // Emetti un evento per caricare i documenti
        eventBus.emit('document:load-request');
        
        // Attendi che l'evento di caricamento venga emesso
        await new Promise(resolve => setTimeout(resolve, 100));
        
        console.assert(documentsLoaded, 'Integrazione: evento document:loaded non emesso');
        subscription.unsubscribe();
        
        // Test dell'integrazione tra Store e servizi
        console.info('Test dell\'integrazione tra Store e servizi...');
        
        // Verifica che lo store sia stato aggiornato
        const documents = store.getState('documents.list');
        console.assert(Array.isArray(documents) && documents.length > 0, 'Integrazione: documenti non aggiornati nello store');
        
        // Test dell'integrazione tra servizi
        console.info('Test dell\'integrazione tra servizi...');
        
        // Simula la creazione di un'annotazione
        const docId = documents[0].id;
        store.commit('SET_DOCUMENT_ID', 'annotator.docId', docId);
        
        let annotationCreated = false;
        const annotationSubscription = eventBus.on('annotation:created', () => {
            annotationCreated = true;
        });
        
        // Crea un'annotazione
        const annotation = annotationService.createAnnotation('Test', 0, 4, 'TEST_TYPE');
        
        console.assert(annotation && annotation.id, 'Integrazione: annotazione non creata');
        console.assert(annotationCreated, 'Integrazione: evento annotation:created non emesso');
        
        annotationSubscription.unsubscribe();
        
        console.info('Test di integrazione completati con successo');
    } catch (error) {
        console.error('Errore durante il test di integrazione:', error);
        allPassed = false;
    }
    
    console.groupEnd();
    return allPassed;
}

/**
 * Mock delle risposte API per i test
 */
function mockApiResponses() {
    // Sovrascrivi temporaneamente il metodo get dell'apiClient
    const originalGet = window.fetch;
    
    window.fetch = function(url, options) {
        // Simula le risposte API
        if (url.includes('/api/documents')) {
            return Promise.resolve({
                ok: true,
                status: 200,
                json: () => Promise.resolve({
                    documents: [
                        {
                            id: 'doc_1',
                            title: 'Documento di test 1',
                            text: 'Questo è un documento di test.',
                            word_count: 7,
                            date_created: new Date().toISOString()
                        },
                        {
                            id: 'doc_2',
                            title: 'Documento di test 2',
                            text: 'Questo è un altro documento di test.',
                            word_count: 8,
                            date_created: new Date().toISOString()
                        }
                    ]
                })
            });
        } else if (url.includes('/api/entity-types')) {
            return Promise.resolve({
                ok: true,
                status: 200,
                json: () => Promise.resolve({
                    entityTypes: [
                        {
                            id: 'TEST_TYPE',
                            name: 'Test Type',
                            color: '#FF0000',
                            category: 'test'
                        },
                        {
                            id: 'ANOTHER_TYPE',
                            name: 'Another Type',
                            color: '#00FF00',
                            category: 'test'
                        }
                    ]
                })
            });
        } else if (url.includes('/api/annotations/')) {
            return Promise.resolve({
                ok: true,
                status: 200,
                json: () => Promise.resolve({
                    annotations: [
                        {
                            id: 'ann_1',
                            text: 'test',
                            start: 0,
                            end: 4,
                            type: 'TEST_TYPE'
                        }
                    ]
                })
            });
        }
        
        // Per le altre richieste, usa il fetch originale
        return originalGet(url, options);
    };
    
    // Ripristina il fetch originale dopo i test
    setTimeout(() => {
        window.fetch = originalGet;
    }, 1000);
}

// Esporta la funzione di test
export default runAllTests;
