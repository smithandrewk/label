// Global variables
let participants = [];

// Initialize the page when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    loadParticipants();
    setupEventListeners();
});

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
    const grid = document.getElementById('participants-grid');
    
    if (participants.length === 0) {
        grid.innerHTML = `
            <div class="col-12">
                <div class="text-center py-5">
                    <i class="fa-solid fa-users fa-3x text-muted mb-3"></i>
                    <h4 class="text-muted">No Participants Found</h4>
                    <p class="text-muted">Add your first participant to get started.</p>
                    <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#createParticipantModal">
                        <i class="fa-solid fa-user-plus me-2"></i>Add First Participant
                    </button>
                </div>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = participants.map(participant => `
        <div class="col-xl-4 col-lg-6 col-md-6 mb-4">
            <div class="card h-100 shadow-sm" data-participant-id="${participant.participant_id}">
                <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
                    <h5 class="card-title mb-0">
                        <i class="fa-solid fa-user me-2"></i>
                        ${participant.participant_code}
                    </h5>
                    <div class="dropdown">
                        <button class="btn btn-sm btn-outline-light" type="button" data-bs-toggle="dropdown">
                            <i class="fa-solid fa-ellipsis-vertical"></i>
                        </button>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="#" onclick="editParticipant(${participant.participant_id})">
                                <i class="fa-solid fa-edit me-2"></i>Edit
                            </a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item text-danger" href="#" onclick="deleteParticipant(${participant.participant_id}, '${participant.participant_code}')">
                                <i class="fa-solid fa-trash me-2"></i>Delete
                            </a></li>
                        </ul>
                    </div>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        ${participant.first_name || participant.last_name ? `
                            <p class="mb-1">
                                <strong>Name:</strong> 
                                ${[participant.first_name, participant.last_name].filter(Boolean).join(' ') || 'Not specified'}
                            </p>
                        ` : ''}
                        
                        ${participant.email ? `
                            <p class="mb-1">
                                <strong>Email:</strong> 
                                <a href="mailto:${participant.email}">${participant.email}</a>
                            </p>
                        ` : ''}
                        
                        <p class="mb-1">
                            <strong>Created:</strong> 
                            ${new Date(participant.created_at).toLocaleDateString()}
                        </p>
                        
                        ${participant.notes ? `
                            <p class="mb-1">
                                <strong>Notes:</strong> 
                                ${participant.notes}
                            </p>
                        ` : ''}
                    </div>
                    
                    <div class="row text-center mb-3">
                        <div class="col-6">
                            <div class="bg-light p-2 rounded">
                                <h5 class="mb-0 text-primary">${participant.project_count || 0}</h5>
                                <small class="text-muted">Projects</small>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="bg-light p-2 rounded">
                                <h5 class="mb-0 text-success">${participant.total_sessions || 0}</h5>
                                <small class="text-muted">Sessions</small>
                            </div>
                        </div>
                    </div>
                    
                    ${participant.project_count > 0 ? `
                        <div class="mb-3">
                            <h6 class="mb-2">Projects:</h6>
                            <div class="d-flex flex-wrap gap-1">
                                ${participant.project_names.split(', ').map((name, index) => `
                                    <span class="badge bg-secondary" style="cursor: pointer;" 
                                          onclick="viewProject(${participant.project_ids[index]}, '${name.replace(/'/g, "\\'")}')">
                                        ${name}
                                    </span>
                                `).join('')}
                            </div>
                        </div>
                    ` : `
                        <div class="text-center text-muted">
                            <i class="fa-solid fa-folder-open fa-2x mb-2"></i>
                            <p class="mb-0">No projects yet</p>
                        </div>
                    `}
                </div>
                <div class="card-footer bg-transparent">
                    <div class="d-flex justify-content-between">
                        <a href="/?participant=${participant.participant_code}" class="btn btn-outline-primary btn-sm">
                            <i class="fa-solid fa-chart-gantt me-1"></i>
                            View Sessions
                        </a>
                        <button type="button" class="btn btn-primary btn-sm" onclick="createProjectForParticipant('${participant.participant_code}')">
                            <i class="fa-solid fa-plus me-1"></i>
                            Add Project
                        </button>
                    </div>
                </div>
            </div>
        </div>
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

// View project details
async function viewProject(projectId, projectName) {
    try {
        // For now, we'll show basic project info and link to sessions
        // In the future, this could fetch detailed project information
        const project = participants.flatMap(p => 
            p.project_ids.map((id, index) => ({
                id: id,
                name: p.project_names.split(', ')[index],
                participant_code: p.participant_code
            }))
        ).find(p => p.id === projectId);
        
        if (!project) throw new Error('Project not found');
        
        const content = document.getElementById('project-details-content');
        content.innerHTML = `
            <div class="mb-3">
                <h6>Project Information</h6>
                <table class="table table-sm">
                    <tr>
                        <th width="30%">Project Name:</th>
                        <td>${project.name}</td>
                    </tr>
                    <tr>
                        <th>Participant:</th>
                        <td>${project.participant_code}</td>
                    </tr>
                    <tr>
                        <th>Project ID:</th>
                        <td>${project.id}</td>
                    </tr>
                </table>
            </div>
            <div class="alert alert-info">
                <i class="fa-solid fa-info-circle me-2"></i>
                Click "View Sessions" below to see all sessions for this project.
            </div>
        `;
        
        // Update the view sessions button to filter by this project
        document.getElementById('view-sessions-btn').href = `/?project_id=${projectId}`;
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('projectDetailsModal'));
        modal.show();
        
    } catch (error) {
        console.error('Error viewing project:', error);
        showError(error.message);
    }
}

// Create project for participant (redirect to main page with participant pre-filled)
function createProjectForParticipant(participantCode) {
    // Redirect to main page with participant code as URL parameter
    window.location.href = `/?participant=${participantCode}&create_project=true`;
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
