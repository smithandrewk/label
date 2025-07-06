// Make function globally accessible
window.onClickProject = function(project_name) {
    console.log('Project clicked:', project_name);
    updateCurrentProjectPill(project_name)
}
document.addEventListener('DOMContentLoaded', function () {
    loadProjects();
});

async function loadProjects() {
    try {
        const response = await fetch('/api/projects');
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const projects = await response.json();
        renderProjects(projects);
    } catch (error) {
        console.error('Error fetching projects:', error);
        const tableBody = document.getElementById('projects-table-body');
        if (tableBody) {
            tableBody.innerHTML = '<tr><td colspan="3" class="text-danger text-center">Failed to load projects. Please try again later.</td></tr>';
        }
    }
}

function renderProjects(projects) {
    console.log('Rendering projects:', projects);
    const tableBody = document.getElementById('projects-table-body');
    
    if (!tableBody) {
        console.error('Table body not found');
        return;
    }
    
    // Clear existing content
    tableBody.innerHTML = '';
    
    if (projects.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="3" class="text-center text-muted">No projects found</td></tr>';
        return;
    }

    projects.forEach(project => {
        console.log(project);
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <strong class="project-name" data-project-id="${project.project_id}" 
                        onclick="onClickProject('${project.project_name.replace(/'/g, '&apos;').replace(/"/g, '&quot;')}'); return false;" 
                        style="cursor: pointer;">
                    ${project.project_name}
                </strong>
            </td>
            <td>${project.participant_code}</td>
            <td>
                <div class="dropdown">
                    <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                        <i class="bi bi-three-dots-vertical"></i>
                    </button>
                    <ul class="dropdown-menu">
                        <li><a class="dropdown-item" href="#" onclick="showRenameModal(${project.project_id}, '${project.project_name.replace(/'/g, '&apos;').replace(/"/g, '&quot;')}'); return false;">
                            <i class="bi bi-pencil me-2"></i>Rename
                        </a></li>
                        <li><a class="dropdown-item" href="#" onclick="showChangeParticipantModal(${project.project_id}, '${project.project_name.replace(/'/g, '&apos;').replace(/"/g, '&quot;')}', '${project.participant_code.replace(/'/g, '&apos;').replace(/"/g, '&quot;')}'); return false;">
                            <i class="bi bi-person me-2"></i>Change Participant
                        </a></li>
                        <li><a class="dropdown-item" href="#" onclick="deleteProject(${project.project_id}, '${project.project_name.replace(/'/g, '&apos;').replace(/"/g, '&quot;')}'); return false;">
                            <i class="bi bi-trash me-2"></i>Delete
                        </a></li>
                    </ul>
                </div>
            </td>
        `;
        tableBody.appendChild(row);
    });
}

// Update current project pill in sidebar
function updateCurrentProjectPill(projectName) {
    const pill = document.getElementById('current-project-pill');
    const pillName = document.getElementById('current-project-pill-name');
    
    if (projectName && pill && pillName) {
        pillName.textContent = projectName;
        pill.style.display = 'block';
    } else if (pill) {
        pill.style.display = 'none';
    }
}

// Show rename modal
function showRenameModal(projectId, currentName) {
    const modal = document.getElementById('renameProjectModal');
    const input = document.getElementById('newProjectNameInput');
    const projectIdField = document.getElementById('renameProjectId');
    
    if (modal && input && projectIdField) {
        input.value = currentName;
        projectIdField.value = projectId;
        
        // Show the modal
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
        
        // Focus on the input and select the text
        setTimeout(() => {
            input.focus();
            input.select();
        }, 500);
    }
}

// Rename project
async function renameProject() {
    const projectId = document.getElementById('renameProjectId').value;
    const newName = document.getElementById('newProjectNameInput').value.trim();
    const errorDiv = document.getElementById('renameError');
    
    if (!newName) {
        showRenameError('Project name cannot be empty');
        return;
    }
    
    try {
        const response = await fetch(`/api/project/${projectId}/rename`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name: newName })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to rename project');
        }
        
        const result = await response.json();
        
        // Hide the modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('renameProjectModal'));
        modal.hide();
        
        // Reload the projects list
        loadProjects();
        
        // Show success message (optional)
        console.log('Project renamed successfully:', result);
        
    } catch (error) {
        console.error('Error renaming project:', error);
        showRenameError(error.message);
    }
}

// Show error in rename modal
function showRenameError(message) {
    const errorDiv = document.getElementById('renameError');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }
}

// Clear error in rename modal
function clearRenameError() {
    const errorDiv = document.getElementById('renameError');
    if (errorDiv) {
        errorDiv.style.display = 'none';
        errorDiv.textContent = '';
    }
}

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
        
        // Reload the projects list
        loadProjects();
        
        // Show success message
        console.log('Project participant changed successfully:', result);
        
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

// Make functions globally accessible
window.showRenameModal = showRenameModal;
window.renameProject = renameProject;
window.clearRenameError = clearRenameError;
window.showChangeParticipantModal = showChangeParticipantModal;
window.changeProjectParticipant = changeProjectParticipant;
window.onParticipantSelectChange = onParticipantSelectChange;
window.clearChangeParticipantError = clearChangeParticipantError;
window.showChangeParticipantModal = showChangeParticipantModal;
window.changeProjectParticipant = changeProjectParticipant;
window.clearChangeParticipantError = clearChangeParticipantError;