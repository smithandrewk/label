/**
 * KEYBOARD NAVIGATION SHORTCUTS (Visualization View Only):
 * - 'n': Navigate to next session (with wraparound)
 * - 'p': Navigate to previous session (with wraparound)
 * - 's': Toggle split mode
 * - 'r': Create new bout
 * - Ctrl/Cmd + 's': Split session
 * - Ctrl/Cmd + 'd': Return to table view
 * 
 * Navigation automatically saves any pending bout changes before switching sessions.
 * Only non-discarded sessions (keep != 0) are included in navigation.
 */

export function addEventListeners() {
    document.addEventListener('keydown', function(event) {
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
            navigateToNextSession();
        } else if (event.key.toLowerCase() === 'p' && !(event.metaKey || event.ctrlKey)) {
            // Navigate to previous session
            event.preventDefault();
            navigateToPreviousSession();
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
    // Add this to your script.js file
    document.addEventListener('DOMContentLoaded', function() {
        // Get the form element
        const createProjectForm = document.getElementById('create-project-form');
        
        // Add submit event listener
        createProjectForm.addEventListener('submit', function(event) {
            // Prevent the default form submission
            event.preventDefault();
            
            // Get form values
            const projectName = document.getElementById('project-name').value;
            const participantCode = document.getElementById('project-participant').value;
            const projectPathInput = document.getElementById('project-path');
            
            // Extract the folder path from the file input
            if (projectPathInput.files.length === 0) {
                alert('Please select a project folder');
                return;
            }
            
            // Get the parent directory path from the first file
            const firstFile = projectPathInput.files[0];
            const relativePath = firstFile.webkitRelativePath;
            const folderName = relativePath.split('/')[0];
            
            // Since we can't get the absolute path in a web browser for security reasons,
            // we'll need to use the File API to read the directory structure
            const formData = {
                name: projectName,
                participant: participantCode,
                folderName: folderName,
                files: Array.from(projectPathInput.files)
            };
            
            // Send data to your backend
            createNewProject(formData);
        });
    });
}