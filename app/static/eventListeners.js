/**
 * KEYBOARD NAVIGATION SHORTCUTS (Visualization View Only):
 * - 'n': Navigate to next session (with wraparound)
 * - 'p': Navigate to previous session (with wraparound)
 * - 's': Toggle split mode
 * - 'r': Create new bout
 * - 'b': Score visible range with selected model
 * - Ctrl/Cmd + 's': Split session
 * - Ctrl/Cmd + 'd': Return to table view
 * 
 * Navigation automatically saves any pending bout changes before switching sessions.
 * Only non-discarded sessions (keep != 0) are included in navigation.
 */

import ProjectController from "./js/controllers/projectController.js";

// Variable to track keyboard shortcuts modal state
let keyboardShortcutsModal = null;

export function addEventListeners() {
    // Initialize keyboard shortcuts modal reference
    document.addEventListener('DOMContentLoaded', function() {
        keyboardShortcutsModal = new bootstrap.Modal(document.getElementById('keyboardShortcutsModal'));
    });

    // Handle question mark key for keyboard shortcuts helper
    document.addEventListener('keydown', function(event) {
        // Check for question mark key (? or Shift + /)
        if (event.key === '?' || (event.key === '/' && event.shiftKey)) {
            // Don't show modal if user is typing in form inputs
            const activeElement = document.activeElement;
            const isInInput = activeElement && (
                activeElement.tagName === 'INPUT' || 
                activeElement.tagName === 'TEXTAREA' || 
                activeElement.tagName === 'SELECT' ||
                activeElement.contentEditable === 'true' ||
                activeElement.closest('.modal') // ignore if another modal is already open
            );
            
            if (!isInInput && keyboardShortcutsModal) {
                event.preventDefault();
                keyboardShortcutsModal.show();
                return;
            }
        }
    });

    // Hide keyboard shortcuts modal on keyup (Google Calendar style)
    document.addEventListener('keyup', function(event) {
        if ((event.key === '?' || event.key === '/') && keyboardShortcutsModal) {
            // Small delay to prevent immediate close if user releases key quickly
            setTimeout(() => {
                keyboardShortcutsModal.hide();
            }, 50);
        }
    });

    document.addEventListener('keydown', function(event) {
        // ignore keydown events when user is typing in form inputs
        const activeElement = document.activeElement;
        const isInInput = activeElement && (
            activeElement.tagName === 'INPUT' || 
            activeElement.tagName === 'TEXTAREA' || 
            activeElement.tagName === 'SELECT' ||
            activeElement.contentEditable === 'true' ||
            activeElement.closest('.modal') // ignore all keydowns when modal is open
        );
        
        if (isInInput) {
            console.log('ignoring keyboard shortcut - user is typing in form');
            return;
        }
        
        // Check if visualization view is active
        const visualizationView = document.getElementById("visualization-view");
        const visualizationViewActive = visualizationView && visualizationView.style.display === "flex";
        
        // Only process keyboard shortcuts if in visualization view
        if (visualizationViewActive) {
        // For Mac: event.metaKey is Command, for Windows/Linux: event.ctrlKey is Control
        if ((event.metaKey || event.ctrlKey) && (event.key.toLowerCase() === 's')) {
            event.preventDefault(); // Prevent browser save dialog
            splitSession();
        } else if (event.key.toLowerCase() === 's') {
            event.preventDefault(); // Prevent browser save dialog
            toggleSplitMode();
        } else if (event.key.toLowerCase() === 'v') {
            event.preventDefault(); // Prevent browser save dialog
            toggleVerifiedStatus();
        } else if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'd') {
            event.preventDefault(); // Prevent browser save dialog
            showTableView();
        } else if (event.key.toLowerCase() === 'r' && !(event.metaKey || event.ctrlKey)) {
            // Check if the 'r' key is pressed without any modifier keys
            console.log('Creating new bout...');
            event.preventDefault(); // Prevent browser refresh
            createNewBout();
        } else if (event.key.toLowerCase() === 'n' && !(event.metaKey || event.ctrlKey)) {
            // Navigate to next session
            event.preventDefault();
            ProjectController.navigateToNextSession();
        } else if (event.key.toLowerCase() === 'p' && !(event.metaKey || event.ctrlKey)) {
            // Navigate to previous session
            event.preventDefault();
            ProjectController.navigateToPreviousSession();
        } else if (event.key.toLowerCase() === 'b' && !(event.metaKey || event.ctrlKey)) {
            console.log(window.currentModelId, window.currentModelName);
            // Navigate to first session
            event.preventDefault();
            selectModelForScoringInVisibleRange(window.currentModelId,window.currentModelName, confirm = false);
            
        }
    }
    });
    const backButton = document.getElementById('back-btn-overlay');
    if (backButton) {
        backButton.addEventListener('click', showTableView);
        backButton.addEventListener('mouseenter', () => {
            backButton.style.background = 'rgba(0, 0, 0, 0.1)';
        });
        backButton.addEventListener('mouseleave', () => {
            backButton.style.background = 'rgba(0, 0, 0, 0)';
        });
    }
    // Download button functionality
    const download_btn_overlay = document.getElementById('download-btn-overlay');
    download_btn_overlay.addEventListener('mouseenter', () => {
        download_btn_overlay.style.background = 'rgba(0, 0, 0, 0.1)';
        download_btn_overlay.style.cursor = 'pointer'; // Add pointer cursor
    });
    download_btn_overlay.addEventListener('mouseleave', () => {
        download_btn_overlay.style.background = 'rgba(224, 224, 224, 0)';
    });
    download_btn_overlay.addEventListener('click', function() {
        exportLabelsJSON();
    });

    const uploadButton = document.getElementById('upload-btn-overlay');
    if (uploadButton) {
        uploadButton.addEventListener('click', showCreateProjectForm);
        uploadButton.addEventListener('mouseenter', () => {
            uploadButton.style.background = 'rgba(0, 0, 0, 0.1)';
        });
        uploadButton.addEventListener('mouseleave', () => {
            uploadButton.style.background = 'rgba(0, 0, 0, 0)';
        });
    }

    const bulkUploadButton = document.getElementById('bulk-upload-btn');
    if (bulkUploadButton) {
        bulkUploadButton.addEventListener('click', showBulkUploadForm);
        bulkUploadButton.addEventListener('mouseenter', () => {
            bulkUploadButton.style.background = 'rgba(0, 0, 0, 0.1)';
        });
        bulkUploadButton.addEventListener('mouseleave', () => {
            bulkUploadButton.style.background = 'rgba(0, 0, 0, 0)';
        });
    }

    document.addEventListener('DOMContentLoaded', function() {
        const createProjectForm = document.getElementById('create-project-form');
        createProjectForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            const projectName = document.getElementById('project-name').value;
            const participantCode = document.getElementById('project-participant').value;
            const projectPath = document.getElementById('project-path').value;
            
            const formData = {
                name: projectName,
                participant: participantCode,
                projectPath: projectPath,
            };
            
            // Send data to your backend
            createNewProject(formData);
        });
    });
}