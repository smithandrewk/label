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
    projects.forEach(project => {
        console.log(project);
        grid.innerHTML += `
            <div class="list-group list-group-flush border-bottom scrollarea"> 
                <a href="#" class="list-group-item list-group-item-action py-3 lh-sm" aria-current="true" onclick="onClickProject('${project.project_name}'); return false;">
                    <div class="d-flex w-100 align-items-center justify-content-between">
                        <strong class="mb-1">${project.project_name}</strong>
                        <small>Wed</small>
                    </div>
                    <div class="col-10 mb-1 small">${project.participant_code}</div>
                </a>
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