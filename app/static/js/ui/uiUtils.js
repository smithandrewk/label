/**
 * UI Utility Functions
 * Pure DOM manipulation functions with no business logic
 */

/**
 * Update current project pill in sidebar
 * @param {string|null} projectName - Name of the project to display
 */
export function updateCurrentProjectPill(projectName) {
    const pill = document.getElementById('current-project-pill');
    const pillName = document.getElementById('current-project-pill-name');

    if (projectName && pill && pillName) {
        pillName.textContent = projectName;
        pill.style.display = 'block';
    } else if (pill) {
        pill.style.display = 'none';
    }
}

/**
 * Reset scoring button to show rocket icon
 * @param {string} sessionId - Session ID (for future use)
 */
export function resetScoreButton(sessionId) {
    const scoreBtn = document.getElementById(`score-btn-overlay`);
    if (scoreBtn) {
        scoreBtn.innerHTML = '<i class="fa-solid fa-rocket"></i>';
    }
}


export function displayBulkPreview(projectGroups) {
    const previewElement = document.getElementById('bulk-preview');
    const projectListElement = document.getElementById('bulk-project-list');

    if (Object.keys(projectGroups).length === 0) {
        previewElement.style.display = 'none';
        return;
    }

    let html = '';
    Object.keys(projectGroups).forEach(projectName => {
        const fileCount = projectGroups[projectName].length;
        html += `
            <div class="d-flex justify-content-between align-items-center mb-2 p-2 border rounded">
                <span><i class="fa-solid fa-folder me-2"></i>${projectName}</span>
                <span class="badge bg-secondary">${fileCount} files</span>
            </div>
        `;
    });

    projectListElement.innerHTML = html;
    previewElement.style.display = 'block';
}

/**
 * Show table view and hide visualization view
 */
export function showTableView() {
    document.getElementById("table-view").style.display = "block";
    document.getElementById("visualization-view").style.display = "none";

    // Remove dark mode if it is on
    document.body.classList.remove('dark-mode');
    localStorage.setItem('dark-mode', false);
}

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type of notification ('info', 'success', 'error', 'warning')
 */
export function showNotification(message, type = 'info') {
    // Simple notification - you can replace with a proper notification library
    console.log(`${type.toUpperCase()}: ${message}`);

    // Create a simple toast notification
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'error' ? 'danger' : type} position-fixed`;
    toast.style.top = '20px';
    toast.style.right = '300px';
    toast.style.zIndex = '9999';
    toast.textContent = message;

    document.body.appendChild(toast);

    setTimeout(() => {
        document.body.removeChild(toast);
    }, 5000);
}

/**
 * Hide a Bootstrap modal by ID
 * @param {string} modalId - The ID of the modal to hide
 */
export function hideModal(modalId) {
    const modalElement = document.getElementById(modalId);
    if (modalElement) {
        const modal = bootstrap.Modal.getInstance(modalElement);
        if (modal) {
            modal.hide();
        }
    }
}

/**
 * Reset a form by ID
 * @param {string} formId - The ID of the form to reset
 */
export function resetForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.reset();
    }
}
