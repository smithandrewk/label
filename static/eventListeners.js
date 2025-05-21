export function addEventListeners() {
    document.addEventListener('keydown', function(event) {
        // For Mac: event.metaKey is Command, for Windows/Linux: event.ctrlKey is Control
        if ((event.metaKey || event.ctrlKey) && (event.key.toLowerCase() === 's') && event.shiftKey) {
            event.preventDefault(); // Prevent browser save dialog
            splitSession();
        } else if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
            event.preventDefault(); // Prevent browser save dialog
            toggleSplitMode();
        } else if (event.key.toLowerCase() === 'r' && !(event.metaKey || event.ctrlKey)) {
            // Check if the 'r' key is pressed without any modifier keys
            console.log('Creating new bout...');
            event.preventDefault(); // Prevent browser refresh
            createNewBout();
        }
    });
    const backButton = document.getElementById('back-btn-overlay');
    if (backButton) {
        backButton.addEventListener('click', function() {
            const currentUrl = window.location.href;
            const newUrl = currentUrl.replace(/\/[^\/]*$/, '/');
            window.history.pushState({ path: newUrl }, '', newUrl);
            window.location.reload();
        });
        backButton.addEventListener('mouseenter', () => {
            backButton.style.background = 'rgba(0, 0, 0, 0.1)';
        });
        backButton.addEventListener('mouseleave', () => {
            backButton.style.background = 'rgba(0, 0, 0, 0)';
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
            const projectPath = document.getElementById('project-path').value;
            
            // Create form data object
            const formData = {
                name: projectName,
                participant: participantCode,
                path: projectPath
            };
            
            // Send data to your backend
            createNewProject(formData);
        });
    });
}