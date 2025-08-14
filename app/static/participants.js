// Global variables
let participants = [];

// Initialize the page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    loadParticipants();
    setupEventListeners();
    checkAndPreserveProjectSelection();
});

// Check URL parameters and preserve project selection
function checkAndPreserveProjectSelection() {
    const urlParams = new URLSearchParams(window.location.search);
    const projectId = urlParams.get('project_id');
    
    if (projectId) {
        // If there's a project_id in URL, use it
        window.currentProjectId = parseInt(projectId);
        console.log(`Setting current project from URL: ${window.currentProjectId}`);
    } else if (window.currentProjectId) {
        // If we have a current project from a previous page, keep it
        console.log(`Preserving current project selection: ${window.currentProjectId}`);
    } else {
        // Check if there's a stored project selection (e.g., in sessionStorage)
        const storedProjectId = sessionStorage.getItem('currentProjectId');
        if (storedProjectId) {
            window.currentProjectId = parseInt(storedProjectId);
            console.log(`Restored project from storage: ${window.currentProjectId}`);
        }
    }
    
    // Store the current project for future page loads
    if (window.currentProjectId) {
        sessionStorage.setItem('currentProjectId', window.currentProjectId.toString());
    }
}

// Setup event listeners
function setupEventListeners() {
    // Create participant form
    document.getElementById('create-participant-form').addEventListener('submit', handleCreateParticipant);
    
    // Edit participant form
    document.getElementById('edit-participant-form').addEventListener('submit', handleEditParticipant);
}

// Load participants from API
async function loadParticipants() {
    try {
        const response = await fetch('/api/participants');
        if (!response.ok) throw new Error('Failed to fetch participants');
        
        participants = await response.json();
        renderParticipants();
        
        // Update sidebar list for navigation
        if (window.updateParticipantsSidebarList) {
            window.updateParticipantsSidebarList(participants);
        }
    } catch (error) {
        console.error('Error loading participants:', error);
        showError('Failed to load participants. Please try again.');
    }
}

// Render participants grid
function renderParticipants() {
    const tableBody = document.getElementById('participants-table-body');
    
    if (participants.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-5">
                    <i class="fa-solid fa-users fa-3x text-muted mb-3"></i>
                    <h4 class="text-muted">No Participants Found</h4>
                    <p class="text-muted">Add your first participant to get started.</p>
                    <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#createParticipantModal">
                        <i class="fa-solid fa-user-plus me-2"></i>Add First Participant
                    </button>
                </td>
            </tr>
        `;
        return;
    }
    
    tableBody.innerHTML = participants.map(participant => `
        <tr data-participant-id="${participant.participant_id}">
            <td>
                <strong>${participant.participant_code}</strong>
                ${participant.notes ? `<br><small class="text-muted">${participant.notes}</small>` : ''}
            </td>
            <td>
                ${[participant.first_name, participant.last_name].filter(Boolean).join(' ') || '<span class="text-muted">Not specified</span>'}
            </td>
            <td>
                <div class="dropdown"> 
                    <a href="#" class="d-block link-body-emphasis text-decoration-none dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false"> 
                        <span class="badge bg-primary">${participant.project_count || 0}</span>
                    </a>
                    <ul class="dropdown-menu text-small">
                        ${participant.project_count > 0 ? 
                            participant.project_names.split(', ').map((projectName, index) => {
                                const projectId = participant.project_ids ? participant.project_ids[index] : null;
                                const escapedProjectName = projectName.replace(/'/g, '&apos;').replace(/"/g, '&quot;');
                                const escapedParticipantCode = participant.participant_code.replace(/'/g, '&apos;').replace(/"/g, '&quot;');
                                return `
                                    <li class="d-flex align-items-center px-2 py-1 dropdown-item">
                                        <span class="flex-grow-1" onclick="viewProject(${projectId}, '${escapedProjectName}'); return false;" style="cursor: pointer;">${projectName}</span>
                                        <div class="btn-group ms-2" role="group">
                                            <button class="btn btn-sm btn-outline-primary" onclick="exportProjectConfiguration(${projectId}, '${escapedProjectName}'); return false;" title="Export project configuration">
                                                <i class="fa-solid fa-download"></i>
                                            </button>
                                            <button class="btn btn-sm btn-outline-secondary" onclick="showChangeParticipantModal(${projectId}, '${escapedProjectName}', '${escapedParticipantCode}'); return false;" title="Change participant">
                                                <i class="fa-solid fa-user"></i>
                                            </button>
                                            <button class="btn btn-sm btn-outline-danger" onclick="window.deleteProject(${projectId}, '${escapedProjectName}'); return false;" title="Delete project">
                                                <i class="fa-solid fa-trash"></i>
                                            </button>
                                        </div>
                                    </li>
                                `;
                            }).join('') : 
                            '<li><span class="dropdown-item-text text-muted">No projects</span></li>'
                        }
                        <li><hr class="dropdown-divider"></li>
                        <li><a class="dropdown-item" href="#" onclick="createProjectForParticipant('${participant.participant_code.replace(/'/g, '&apos;').replace(/"/g, '&quot;')}'); return false;">
                            <i class="fa-solid fa-plus me-2"></i>New project...
                        </a></li>
                        <li><a class="dropdown-item" href="#" onclick="showImportProjectModal('${participant.participant_code.replace(/'/g, '&apos;').replace(/"/g, '&quot;')}'); return false;">
                            <i class="fa-solid fa-upload me-2"></i>Import project...
                        </a></li>
                    </ul> 
                </div>
            </td>
            <td>
                <span class="badge bg-success">${participant.total_sessions || 0}</span>
            </td>
            <td>
                <small>${new Date(participant.created_at).toLocaleDateString()}</small>
            </td>
            <td>
                <div class="d-flex gap-1">
                    <button class="btn btn-sm btn-outline-primary" onclick="editParticipant(${participant.participant_id}); return false;" title="Edit Participant">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-success" onclick="createProjectForParticipant('${participant.participant_code.replace(/'/g, '&apos;').replace(/"/g, '&quot;')}'); return false;" title="Add Project">
                        <i class="bi bi-plus"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteParticipant(${participant.participant_id}, '${participant.participant_code.replace(/'/g, '&apos;').replace(/"/g, '&quot;')}'); return false;" title="Delete Participant">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// Handle create participant form submission
async function handleCreateParticipant(event) {
    event.preventDefault();
    
    const formData = {
        participant_code: document.getElementById('participant-code').value,
        first_name: document.getElementById('participant-first-name').value,
        last_name: document.getElementById('participant-last-name').value,
        email: document.getElementById('participant-email').value,
        notes: document.getElementById('participant-notes').value
    };
    
    try {
        const response = await fetch('/api/participants', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to create participant');
        }
        
        // Close modal and refresh
        const modal = bootstrap.Modal.getInstance(document.getElementById('createParticipantModal'));
        modal.hide();
        
        // Reset form
        document.getElementById('create-participant-form').reset();
        
        // Reload participants
        await loadParticipants();
        
        showSuccess('Participant created successfully!');
        
    } catch (error) {
        console.error('Error creating participant:', error);
        showError(error.message);
    }
}

// Handle edit participant form submission
async function handleEditParticipant(event) {
    event.preventDefault();
    
    const participantId = document.getElementById('edit-participant-id').value;
    const formData = {
        participant_code: document.getElementById('edit-participant-code').value,
        first_name: document.getElementById('edit-participant-first-name').value,
        last_name: document.getElementById('edit-participant-last-name').value,
        email: document.getElementById('edit-participant-email').value,
        notes: document.getElementById('edit-participant-notes').value
    };
    
    try {
        const response = await fetch(`/api/participants/${participantId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to update participant');
        }
        
        // Close modal and refresh
        const modal = bootstrap.Modal.getInstance(document.getElementById('editParticipantModal'));
        modal.hide();
        
        // Reload participants
        await loadParticipants();
        
        showSuccess('Participant updated successfully!');
        
    } catch (error) {
        console.error('Error updating participant:', error);
        showError(error.message);
    }
}

// Edit participant function
function editParticipant(participantId) {
    const participant = participants.find(p => p.participant_id === participantId);
    if (!participant) return;
    
    // Populate form
    document.getElementById('edit-participant-id').value = participant.participant_id;
    document.getElementById('edit-participant-code').value = participant.participant_code;
    document.getElementById('edit-participant-first-name').value = participant.first_name || '';
    document.getElementById('edit-participant-last-name').value = participant.last_name || '';
    document.getElementById('edit-participant-email').value = participant.email || '';
    document.getElementById('edit-participant-notes').value = participant.notes || '';
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('editParticipantModal'));
    modal.show();
}

// Delete participant function
async function deleteParticipant(participantId, participantCode) {
    const participant = participants.find(p => p.participant_id === participantId);
    
    const confirmMessage = `Are you sure you want to delete participant "${participantCode}"?\n\n` +
        `This will permanently delete:\n` +
        `• The participant record\n` +
        `• ${participant.project_count || 0} project(s)\n` +
        `• ${participant.total_sessions || 0} session(s)\n` +
        `• All associated data files\n\n` +
        `This action cannot be undone.`;
    
    if (!confirm(confirmMessage)) return;
    
    try {
        const response = await fetch(`/api/participants/${participantId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to delete participant');
        }
        
        const result = await response.json();
        
        // Show success message
        const successMessage = `Participant deleted successfully!\n\n` +
            `Participant: ${result.participant_code}\n` +
            `Projects deleted: ${result.projects_deleted}\n` +
            `Sessions deleted: ${result.sessions_deleted}`;
        
        alert(successMessage);
        
        // Reload participants
        await loadParticipants();
        
    } catch (error) {
        console.error('Error deleting participant:', error);
        showError(error.message);
    }
}

// View project details - navigate to sessions page
async function viewProject(projectId, projectName) {
    console.log(`Viewing project: ${projectName} (ID: ${projectId})`);
    try {
        // Navigate to sessions page with project selected
        window.location.href = `/sessions?project_id=${projectId}`;
        
    } catch (error) {
        console.error('Error viewing project:', error);
        showError(error.message);
    }
}

// Create project for participant (redirect to main page with participant pre-filled)
function createProjectForParticipant(participantCode) {
    // Build URL with participant code and preserve current project if it exists
    let url = `/?participant=${participantCode}&create_project=true`;
    if (window.currentProjectId) {
        url += `&project_id=${window.currentProjectId}`;
    }
    window.location.href = url;
}

// Utility functions for showing messages
function showError(message) {
    // Create a simple alert for now - could be enhanced with toasts
    alert('Error: ' + message);
}

function showSuccess(message) {
    // Create a simple alert for now - could be enhanced with toasts
    alert(message);
}

// Make functions available globally for onclick handlers
window.editParticipant = editParticipant;
window.deleteParticipant = deleteParticipant;
window.viewProject = viewProject;
window.createProjectForParticipant = createProjectForParticipant;

// Show change participant modal
async function showChangeParticipantModal(projectId, projectName, currentParticipantCode) {
    const modal = document.getElementById('changeParticipantModal');
    const projectIdField = document.getElementById('changeParticipantProjectId');
    const projectNameSpan = document.getElementById('changeParticipantProjectName');
    const currentParticipantSpan = document.getElementById('currentParticipantCode');
    
    if (modal && projectIdField && projectNameSpan && currentParticipantSpan) {
        projectIdField.value = projectId;
        projectNameSpan.textContent = projectName;
        currentParticipantSpan.textContent = currentParticipantCode;
        
        // Load participants into dropdown
        await loadParticipantsForDropdown();
        
        // Show the modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    }
}

// Load participants for the dropdown
async function loadParticipantsForDropdown() {
    try {
        const response = await fetch('/api/participants');
        if (!response.ok) {
            throw new Error('Failed to fetch participants');
        }
        
        const participants = await response.json();
        const select = document.getElementById('participantSelect');
        
        if (select) {
            // Clear existing options
            select.innerHTML = '<option value="">Select a participant...</option>';
            
            // Add participants to dropdown
            participants.forEach(participant => {
                const option = document.createElement('option');
                option.value = participant.participant_id;
                option.textContent = `${participant.participant_code} - ${[participant.first_name, participant.last_name].filter(Boolean).join(' ') || 'No name'}`;
                select.appendChild(option);
            });
            
            // Add option to create new participant
            const createOption = document.createElement('option');
            createOption.value = 'create_new';
            createOption.textContent = '+ Create New Participant';
            select.appendChild(createOption);
        }
    } catch (error) {
        console.error('Error loading participants:', error);
        showChangeParticipantError('Failed to load participants');
    }
}

// Handle participant selection change
function onParticipantSelectChange() {
    const select = document.getElementById('participantSelect');
    const createParticipantDiv = document.getElementById('createParticipantDiv');
    
    if (select.value === 'create_new') {
        createParticipantDiv.style.display = 'block';
    } else {
        createParticipantDiv.style.display = 'none';
        clearNewParticipantFields();
    }
    
    clearChangeParticipantError();
}

// Clear new participant fields
function clearNewParticipantFields() {
    document.getElementById('newParticipantCode').value = '';
    document.getElementById('newParticipantFirstName').value = '';
    document.getElementById('newParticipantLastName').value = '';
}

// Change project participant
async function changeProjectParticipant() {
    const projectId = document.getElementById('changeParticipantProjectId').value;
    const select = document.getElementById('participantSelect');
    let participantId = select.value;
    
    if (!participantId) {
        showChangeParticipantError('Please select a participant');
        return;
    }
    
    try {
        // If creating new participant, create it first
        if (participantId === 'create_new') {
            const newParticipantCode = document.getElementById('newParticipantCode').value.trim();
            const newParticipantFirstName = document.getElementById('newParticipantFirstName').value.trim();
            const newParticipantLastName = document.getElementById('newParticipantLastName').value.trim();
            
            if (!newParticipantCode) {
                showChangeParticipantError('Participant code is required');
                return;
            }
            
            // Create new participant
            const createResponse = await fetch('/api/participants', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    participant_code: newParticipantCode,
                    first_name: newParticipantFirstName,
                    last_name: newParticipantLastName,
                    email: '',
                    notes: ''
                })
            });
            
            if (!createResponse.ok) {
                const errorData = await createResponse.json();
                throw new Error(errorData.error || 'Failed to create participant');
            }
            
            const createResult = await createResponse.json();
            participantId = createResult.participant_id;
        }
        
        // Update project participant
        const response = await fetch(`/api/project/${projectId}/participant`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ participant_id: participantId })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to change project participant');
        }
        
        const result = await response.json();
        
        // Hide the modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('changeParticipantModal'));
        modal.hide();
        
        // Reload the participants list
        await loadParticipants();
        
        // Show success message
        showSuccess(`Project "${result.project_name}" has been moved to participant "${result.new_participant_code}"`);
        
    } catch (error) {
        console.error('Error changing project participant:', error);
        showChangeParticipantError(error.message);
    }
}

// Show error in change participant modal
function showChangeParticipantError(message) {
    const errorDiv = document.getElementById('changeParticipantError');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }
}

// Clear error in change participant modal
function clearChangeParticipantError() {
    const errorDiv = document.getElementById('changeParticipantError');
    if (errorDiv) {
        errorDiv.style.display = 'none';
        errorDiv.textContent = '';
    }
}

// Export project configuration
async function exportProjectConfiguration(projectId, projectName) {
    try {
        console.log(`Exporting project configuration for: ${projectName} (ID: ${projectId})`);
        
        // Import ProjectAPI dynamically
        const ProjectAPI = (await import('./js/api/projectAPI.js')).default;
        
        // Export will automatically trigger download
        await ProjectAPI.exportProjectConfiguration(projectId);
        
        showSuccess(`Project configuration exported successfully!`);
        
    } catch (error) {
        console.error('Error exporting project configuration:', error);
        showError(`Failed to export project: ${error.message}`);
    }
}

// Show import project modal
function showImportProjectModal(participantCode) {
    // Set the participant code
    document.getElementById('importParticipantCode').value = participantCode;
    
    // Clear any previous file selection and error messages
    document.getElementById('importFileInput').value = '';
    document.getElementById('importProjectError').style.display = 'none';
    document.getElementById('importProjectError').textContent = '';
    
    // Show the modal
    const modal = new bootstrap.Modal(document.getElementById('importProjectModal'));
    modal.show();
}

// Handle import project form
async function handleImportProject() {
    const fileInput = document.getElementById('importFileInput');
    const participantCode = document.getElementById('importParticipantCode').value;
    
    if (!fileInput.files || fileInput.files.length === 0) {
        showImportProjectError('Please select a project configuration file');
        return;
    }
    
    const file = fileInput.files[0];
    
    // Validate file type
    if (!file.name.endsWith('.json')) {
        showImportProjectError('Please select a valid JSON configuration file');
        return;
    }
    
    try {
        // Read the file
        const fileContent = await readFileAsText(file);
        let configData;
        
        try {
            configData = JSON.parse(fileContent);
        } catch (parseError) {
            throw new Error('Invalid JSON file format');
        }
        
        // Validate that it's a project configuration
        if (!configData.export_type || configData.export_type !== 'project_configuration') {
            throw new Error('Invalid project configuration file');
        }
        
        // Override participant code if specified
        if (participantCode) {
            configData.participant_code = participantCode;
        }
        
        // Add selected dataset if provided
        const selectedDatasetId = document.getElementById('rawDatasetSelector').value;
        if (selectedDatasetId) {
            configData.selected_dataset_id = parseInt(selectedDatasetId);
        }
        
        console.log('Importing project configuration:', configData.project_name);
        
        // Import ProjectAPI dynamically
        const ProjectAPI = (await import('./js/api/projectAPI.js')).default;
        
        // Import the project
        const result = await ProjectAPI.importProjectConfiguration(configData);
        
        // Hide the modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('importProjectModal'));
        modal.hide();
        
        // Reload participants to show the new project
        await loadParticipants();
        
        showSuccess(`Project "${result.project_name}" imported successfully!`);
        
    } catch (error) {
        console.error('Error importing project:', error);
        showImportProjectError(error.message);
    }
}

// Read file as text
function readFileAsText(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = (e) => reject(new Error('Failed to read file'));
        reader.readAsText(file);
    });
}

// Show error in import project modal
function showImportProjectError(message) {
    const errorDiv = document.getElementById('importProjectError');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }
}

// Clear import project error
function clearImportProjectError() {
    const errorDiv = document.getElementById('importProjectError');
    if (errorDiv) {
        errorDiv.style.display = 'none';
        errorDiv.textContent = '';
    }
}

// Handle config file selection - check if datasets are missing
async function handleConfigFileSelected() {
    clearImportProjectError();
    
    const fileInput = document.getElementById('importFileInput');
    const datasetSection = document.getElementById('datasetSelectorSection');
    
    if (!fileInput.files || fileInput.files.length === 0) {
        datasetSection.style.display = 'none';
        return;
    }
    
    try {
        const file = fileInput.files[0];
        const fileContent = await readFileAsText(file);
        const configData = JSON.parse(fileContent);
        
        // Check if this is a dataset-based project (export_version 2.0)
        if (configData.export_version === '2.0' && configData.datasets && configData.datasets.length > 0) {
            // Show dataset selector and populate with available datasets
            await loadRawDatasets();
            datasetSection.style.display = 'block';
        } else {
            datasetSection.style.display = 'none';
        }
    } catch (error) {
        console.warn('Could not parse config file for dataset check:', error);
        datasetSection.style.display = 'none';
    }
}

// Load available raw datasets for selection
async function loadRawDatasets() {
    try {
        const response = await fetch('/api/datasets');
        if (!response.ok) {
            throw new Error('Failed to load datasets');
        }
        
        const datasets = await response.json();
        const selector = document.getElementById('rawDatasetSelector');
        
        // Clear existing options except the first one
        selector.innerHTML = '<option value="">Select a raw dataset...</option>';
        
        // Add dataset options
        datasets.forEach(dataset => {
            const option = document.createElement('option');
            option.value = dataset.dataset_id;
            option.textContent = `${dataset.dataset_name} (${dataset.session_count} sessions)`;
            selector.appendChild(option);
        });
        
    } catch (error) {
        console.error('Error loading raw datasets:', error);
        showImportProjectError('Failed to load available datasets');
    }
}

// Make additional functions available globally
window.showChangeParticipantModal = showChangeParticipantModal;
window.changeProjectParticipant = changeProjectParticipant;
window.onParticipantSelectChange = onParticipantSelectChange;
window.clearChangeParticipantError = clearChangeParticipantError;
window.exportProjectConfiguration = exportProjectConfiguration;
window.handleConfigFileSelected = handleConfigFileSelected;
window.showImportProjectModal = showImportProjectModal;
window.handleImportProject = handleImportProject;
window.clearImportProjectError = clearImportProjectError;
