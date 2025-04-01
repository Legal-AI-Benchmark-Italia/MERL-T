/**
 * app.js
 * Main application entry point. Initializes page-specific logic.
 */

import { initIndexPage } from './indexPage.js';
import { initAnnotator } from './annotator.js';
import { initEntityManager } from './entityManager.js';

document.addEventListener('DOMContentLoaded', () => {
    const pageId = document.body.dataset.pageId;

    console.log(`Initializing page: ${pageId}`);

    switch (pageId) {
        case 'index':
            initIndexPage();
            break;
        case 'annotate':
            initAnnotator();
            break;
        case 'entity_types':
            initEntityManager();
            break;
        default:
            console.log('No specific JS initialization for this page.');
    }

    // Global initializations (like tooltips) can go here
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
      return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});