/**
 * ui.js
 * UI helper functions
 */

let toastInstance = null;

function getToastInstance() {
    if (!toastInstance) {
        const toastEl = document.getElementById('notificationToast');
        if (toastEl) {
            toastInstance = new bootstrap.Toast(toastEl, { delay: 5000 });
        }
    }
    return toastInstance;
}

export function showNotification(message, type = 'info', title = 'Notifica') {
    const toast = getToastInstance();
    if (!toast) return;

    const toastEl = document.getElementById('notificationToast');
    const titleEl = document.getElementById('notificationTitle');
    const messageEl = document.getElementById('notificationMessage');

    // Remove previous background classes
    toastEl.classList.remove('bg-primary', 'bg-success', 'bg-danger', 'bg-warning', 'bg-info', 'text-white');

    let bgClass = `bg-${type}`;
    let textClass = 'text-white';
    if (type === 'light' || type === 'white') {
        textClass = 'text-dark'; // Ensure contrast for light backgrounds
    } else if (type === 'warning') {
         textClass = 'text-dark'; // Better contrast for default warning
    }


    toastEl.classList.add(bgClass, textClass);
    titleEl.textContent = title;
    messageEl.textContent = message;

    toast.show();
}

export function showLoading(show = true) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.classList.toggle('d-none', !show);
    } else {
        console.warn('Loading overlay element not found');
    }
}

export function hideLoading() {
    showLoading(false);
}

// Add other UI helpers as needed (e.g., creating elements, toggling classes)
export function getCategoryDisplayName(category) {
    switch (category) {
        case 'normative': return 'Normativa';
        case 'jurisprudence': return 'Giurisprudenziale';
        case 'concepts': return 'Concetto';
        case 'custom': return 'Personalizzata';
        default: return category;
    }
}

export function getCategoryBadgeClass(category) {
     switch (category) {
        case 'normative': return 'bg-primary';
        case 'jurisprudence': return 'bg-success';
        case 'concepts': return 'bg-info text-dark';
        case 'custom': return 'bg-secondary';
        default: return 'bg-dark';
    }
}

// Helper to safely get text content (useful for contenteditable)
export function getTextContent(element) {
    // Normalize line breaks and trim whitespace
    return element.innerText.replace(/\r\n|\r/g, '\n').trim();
}

// Helper to set text content reliably in contenteditable
export function setTextContent(element, text) {
    // Clear existing content first
    while (element.firstChild) {
        element.removeChild(element.firstChild);
    }
    // Create a text node to preserve whitespace correctly
    const textNode = document.createTextNode(text);
    element.appendChild(textNode);
}

// Helper for hex to rgb conversion (for text contrast calculation)
export function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
}

// Helper to calculate luminance (for text contrast)
export function calculateLuminance(r, g, b) {
    const a = [r, g, b].map(function (v) {
        v /= 255;
        return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
}