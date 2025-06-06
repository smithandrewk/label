// Settings page functionality
document.addEventListener('DOMContentLoaded', function() {
    // Database settings form
    const dbForm = document.getElementById('database-settings-form');
    if (dbForm) {
        dbForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const settings = Object.fromEntries(formData);
            
            // TODO: Send to backend API
            console.log('Database settings:', settings);
            
            // Show success message
            showToast('Database settings saved successfully!', 'success');
        });
    }
    
    // Processing settings form
    const processingForm = document.getElementById('processing-settings-form');
    if (processingForm) {
        processingForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            const settings = Object.fromEntries(formData);
            
            // TODO: Send to backend API
            console.log('Processing settings:', settings);
            
            // Show success message
            showToast('Processing settings saved successfully!', 'success');
        });
    }
    
    // System tools
    document.getElementById('clear-cache-btn')?.addEventListener('click', function() {
        if (confirm('Are you sure you want to clear the cache?')) {
            // TODO: Implement cache clearing
            showToast('Cache cleared successfully!', 'success');
        }
    });
    
    document.getElementById('export-settings-btn')?.addEventListener('click', function() {
        // TODO: Implement settings export
        const settings = {
            database: {
                host: document.getElementById('db-host').value,
                port: document.getElementById('db-port').value,
                name: document.getElementById('db-name').value
            },
            processing: {
                samplingRate: document.getElementById('sampling-rate').value,
                windowSize: document.getElementById('window-size').value,
                autoLabeling: document.getElementById('auto-labeling').checked
            }
        };
        
        const blob = new Blob([JSON.stringify(settings, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'settings.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        showToast('Settings exported successfully!', 'success');
    });
    
    document.getElementById('import-settings-btn')?.addEventListener('click', function() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.json';
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    try {
                        const settings = JSON.parse(e.target.result);
                        
                        // Apply settings to form
                        if (settings.database) {
                            document.getElementById('db-host').value = settings.database.host || '';
                            document.getElementById('db-port').value = settings.database.port || '';
                            document.getElementById('db-name').value = settings.database.name || '';
                        }
                        
                        if (settings.processing) {
                            document.getElementById('sampling-rate').value = settings.processing.samplingRate || '';
                            document.getElementById('window-size').value = settings.processing.windowSize || '';
                            document.getElementById('auto-labeling').checked = settings.processing.autoLabeling || false;
                        }
                        
                        showToast('Settings imported successfully!', 'success');
                    } catch (error) {
                        showToast('Error importing settings: Invalid JSON file', 'error');
                    }
                };
                reader.readAsText(file);
            }
        });
        input.click();
    });
    
    document.getElementById('reset-settings-btn')?.addEventListener('click', function() {
        if (confirm('Are you sure you want to reset all settings to defaults?')) {
            // Reset to default values
            document.getElementById('db-host').value = 'localhost';
            document.getElementById('db-port').value = '3306';
            document.getElementById('db-name').value = 'smoking_data';
            document.getElementById('sampling-rate').value = '50';
            document.getElementById('window-size').value = '5';
            document.getElementById('auto-labeling').checked = true;
            
            showToast('Settings reset to defaults!', 'success');
        }
    });
});

// Utility function to show toast notifications
function showToast(message, type = 'info') {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
    toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(toast);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 3000);
}
