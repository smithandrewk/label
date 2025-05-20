export function addEventListeners() {
    document.addEventListener('keydown', function(event) {
        // For Mac: event.metaKey is Command, for Windows/Linux: event.ctrlKey is Control
        if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
            console.log('Save shortcut triggered');
            event.preventDefault(); // Prevent browser save dialog
            // Find the currently visible split button and trigger it
            const splitButton = document.querySelector('#action-buttons button.btn-warning, #action-buttons button.btn-info');
            if (splitButton) {
                splitButton.click();
            }
        }
    });
}