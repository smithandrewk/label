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
        const grid = document.getElementById('projects-grid');
        grid.innerHTML = '<p class="text-danger">Failed to load projects. Please try again later.</p>';
    }
}

function renderProjects(projects) {
    console.log('Rendering projects:', projects);
    const grid = document.getElementById('projects-grid');
    
    // Clear existing content except the title
    const titleElement = grid.querySelector('.fs-5.fw-semibold');
    grid.innerHTML = '';
    if (titleElement) {
        grid.appendChild(titleElement.parentElement);
    } else {
        grid.innerHTML = '<div class="d-flex flex-column align-items-stretch flex-shrink-0 bg-body-tertiary" style="width: 100%;"><span class="fs-5 fw-semibold">Projects</span></div>';
    }
    
    projects.forEach(project => {
        console.log(project);
        grid.innerHTML += `
            <div class="list-group list-group-flush border-bottom scrollarea"> 
                <div class="list-group-item list-group-item-action py-3 lh-sm" aria-current="true">
                    <div class="d-flex w-100 align-items-center justify-content-between">
                        <div class="flex-grow-1" onclick="onClickProject('${project.project_name}'); return false;" style="cursor: pointer;">
                            <strong class="mb-1 project-name" data-project-id="${project.project_id}">${project.project_name}</strong>
                            <div class="col-10 mb-1 small">${project.participant_code}</div>
                        </div>
                        <div class="dropdown">
                            <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                                <i class="bi bi-three-dots-vertical"></i>
                            </button>
                            <ul class="dropdown-menu">
                                <li><a class="dropdown-item" href="#" onclick="showRenameModal(${project.project_id}, '${project.project_name}'); return false;">
                                    <i class="bi bi-pencil me-2"></i>Rename
                                </a></li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        `;
    })
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

// Make functions globally accessible
window.showRenameModal = showRenameModal;
window.renameProject = renameProject;
window.clearRenameError = clearRenameError;