import * as eventListeners from './eventListeners.js';
import { ensureSessionBoutsIsArray } from './helpers.js'
import ProjectAPI from './js/api/projectAPI.js';
import SessionAPI from './js/api/sessionAPI.js';
import SessionService from './js/services/sessionService.js';
import { ActionButtonTemplates, ActionButtonHandlers } from './js/templates/actionButtonTemplates.js';
import { SessionListTemplates, SessionListHandlers } from './js/templates/sessionListTemplates.js';

// Check URL parameters on page load
function checkUrlParameters() {
    const urlParams = new URLSearchParams(window.location.search);
    const participantCode = urlParams.get('participant');
    const createProject = urlParams.get('create_project');
    
    if (participantCode && createProject === 'true') {
        // Pre-fill participant code and show create project modal
        setTimeout(() => {
            document.getElementById('project-participant').value = participantCode;
            showCreateProjectForm();
        }, 500); // Small delay to ensure page is loaded
    }
}

// Add to your script.js
async function initializeProjects() {
    try {
        const projects = await ProjectAPI.fetchProjects();

        // Populate the dropdown
        const dropdownMenu = document.getElementById('project-dropdown-menu');
        dropdownMenu.innerHTML = ''; // Clear existing items
        
        projects.forEach(project => {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.className = 'dropdown-item d-flex justify-content-between align-items-center';
            a.href = '#';
            a.dataset.projectId = project.project_id;
            
            // Create project name span
            const nameSpan = document.createElement('span');
            nameSpan.textContent = project.project_name;
            nameSpan.style.flexGrow = '1';
            nameSpan.onclick = function(e) {
                e.preventDefault();
                currentProjectId = project.project_id; // Store selected project ID
                fetchProjectSessions(project.project_id);
                
                // Update current project pill
                updateCurrentProjectPill(project.project_name);
                
                // Update active state
                document.querySelectorAll('#project-dropdown-menu .dropdown-item').forEach(item => {
                    item.classList.remove('active');
                    item.removeAttribute('aria-current');
                });
                a.classList.add('active');
                a.setAttribute('aria-current', 'page');
            };
            
            // Create delete button
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn btn-sm btn-outline-danger ms-2';
            deleteBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';
            deleteBtn.title = 'Delete Project';
            deleteBtn.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                deleteProject(project.project_id, project.project_name);
            };
            
            a.appendChild(nameSpan);
            a.appendChild(deleteBtn);
            li.appendChild(a);
            dropdownMenu.appendChild(li);
        });

        // Add divider and "All Projects" option
        if (projects.length > 0) {
            const divider = document.createElement('li');
            divider.innerHTML = '<hr class="dropdown-divider">';
            dropdownMenu.appendChild(divider);
            
            const allLi = document.createElement('li');
            const allA = document.createElement('a');
            allA.className = 'dropdown-item';
            allA.href = '#';
            allA.textContent = 'All Projects';
            // In your initializeProjects function, update the "All Projects" click handler:
            // Update the All Projects click handler
            allA.onclick = function(e) {
                e.preventDefault();
                currentProjectId = null; // Clear the project ID
                
                // Hide current project pill
                updateCurrentProjectPill(null);
                
                // Update active state
                document.querySelectorAll('#project-dropdown-menu .dropdown-item').forEach(item => {
                    item.classList.remove('active');
                    item.removeAttribute('aria-current');
                });
                this.classList.add('active');
                this.setAttribute('aria-current', 'page');
                
                // Fetch all sessions
                fetchSession();
            };
            allLi.appendChild(allA);
            dropdownMenu.appendChild(allLi);
        }
        
        // Select first project by default
        if (projects.length > 0) {
            const firstProject = dropdownMenu.querySelector('.dropdown-item');
            firstProject.classList.add('active');
            firstProject.setAttribute('aria-current', 'page');
            currentProjectId = projects[0].project_id; // ADD THIS LINE to set current project ID
            
            // Update current project pill
            updateCurrentProjectPill(projects[0].project_name);
            
            fetchProjectSessions(projects[0].project_id);
        }
    } catch (error) {
        console.error('Error initializing projects:', error);
    }
}

// Fetch sessions for a specific project
async function fetchProjectSessions(projectId) {
    try {
        sessions = await ProjectAPI.fetchProjectSessions(projectId);
        labelings = await ProjectAPI.fetchLabelings(projectId);

        // Set currentLabeling to the first available labeling or "No Labeling"
        if (labelings && labelings.length > 0) {
            currentLabelingJSON = labelings[0];
            currentLabelingName = currentLabelingJSON.name;
        } else {
            currentLabelingJSON = null;
            currentLabelingName = "No Labeling";
        }
        console.log(labelings)
        // Log session statistics
        const stats = SessionService.getSessionStats(sessions);
        console.log(`Session statistics: ${stats.available} available, ${stats.discarded} discarded, ${stats.verified} verified (${stats.total} total)`);
        
        // Update the session table/list
        updateSessionsList();
    } catch (error) {
        console.error('Error fetching project sessions:', error);
    }
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

// Update the sessions list in the UI
function updateSessionsList() {
    const sessionList = document.getElementById("session-list");
    const tbody = document.getElementById("sessions-table-body");
    
    // Check if required elements exist
    if (!sessionList && !tbody) {
        console.warn('Neither session-list nor sessions-table-body elements found on this page');
        return;
    }
    
    // Clear existing content
    if (sessionList) {
        sessionList.innerHTML = "";
    }
    if (tbody) {
        tbody.innerHTML = "";
    }
    
    if (sessions.length === 0) {
        // Display a message for empty sessions
        if (tbody) {
            tbody.innerHTML = SessionListTemplates.emptyState();
        }
        return;
    }
    
    // Populate sessions
    sessions.forEach(session => {
        if (session.keep == 0) return; // Skip discarded sessions
        
        // Sidebar entry (only if sessionList exists)
        if (sessionList) {
            const li = document.createElement("li");
            li.className = "nav-item";
            li.innerHTML = SessionListTemplates.sidebarItem(session, currentActiveSession);
            sessionList.appendChild(li);
        }

        // Table row (only if tbody exists)
        if (tbody) {
            const row = document.createElement("tr");
            const sessionId = session.session_id;
            
            // Use template for table row
            row.innerHTML = SessionListTemplates.tableRow(session);
            tbody.appendChild(row);

            // Setup event handlers using the template handlers
            SessionListHandlers.setupTableRowHandlers(
                sessionId, 
                decideSession, 
                toggleVerifiedStatus
            );

        }
    });
}
async function scoreSession(sessionId, projectName, sessionName) {
    try {
        console.log(`Scoring session: ${sessionId} (${sessionName} from project ${projectName})`);
        
        // Update button to show loading state
        const scoreBtn = document.getElementById(`score-btn-overlay`);
        if (scoreBtn) {
            scoreBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        }
        
        const response = await fetch('/score_session', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                session_id: sessionId,
                project_name: projectName,
                session_name: sessionName
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showNotification(`Scoring started for ${sessionName}`, 'success');
            
            // Start polling for completion
            pollScoringStatus(result.scoring_id, sessionId, sessionName);
        } else {
            showNotification(`Scoring failed: ${result.error}`, 'error');
            resetScoreButton(sessionId);
        }
    } catch (error) {
        console.error('Error scoring session:', error);
        showNotification('Failed to start scoring', 'error');
        resetScoreButton(sessionId);
    }
}

async function pollScoringStatus(scoringId, sessionId, sessionName) {
    const maxPolls = 120; // 2 minutes max
    let pollCount = 0;
    
    const poll = setInterval(async () => {
        try {
            const response = await fetch(`/api/scoring_status/${scoringId}`);
            const status = await response.json();
            
            pollCount++;
            
            if (status.status === 'completed') {
                clearInterval(poll);
                showNotification(`Scoring complete for ${sessionName}! Found ${status.bouts_count} bouts.`, 'success');
                resetScoreButton(sessionId);
                
                // Force refresh the session data from the server
                const sessionResponse = await fetch(`/api/session/${sessionId}`);
                if (sessionResponse.ok) {
                    const sessionData = await sessionResponse.json();
                    
                    // Update the session in our local sessions array
                    const sessionIndex = sessions.findIndex(s => s.session_id == sessionId);
                    if (sessionIndex !== -1) {
                        // Parse bouts if they're a string
                        let bouts = sessionData.bouts;
                        if (typeof bouts === 'string') {
                            try {
                                bouts = JSON.parse(bouts);
                            } catch (e) {
                                console.error('Error parsing bouts:', e);
                                bouts = [];
                            }
                        }
                        sessions[sessionIndex].bouts = bouts || [];
                        sessions[sessionIndex].data = sessionData.data;
                    }
                }
                
                // If this session is currently being visualized, refresh it
                if (currentSessionId == sessionId) {
                    console.log('Refreshing currently visualized session with new bouts');
                    visualizeSession(sessionId);
                }
                
            } else if (status.status === 'error') {
                clearInterval(poll);
                showNotification(`Scoring failed: ${status.error}`, 'error');
                resetScoreButton(sessionId);
                
            } else if (pollCount >= maxPolls) {
                clearInterval(poll);
                showNotification('Scoring is taking longer than expected', 'warning');
                resetScoreButton(sessionId);
            }
            
        } catch (error) {
            console.error('Error polling scoring status:', error);
            clearInterval(poll);
            resetScoreButton(sessionId);
        }
    }, 1000); // Poll every second
}

function resetScoreButton(sessionId) {
    const scoreBtn = document.getElementById(`score-btn-overlay`);
    if (scoreBtn) {
        scoreBtn.innerHTML = '<i class="fa-solid fa-rocket"></i>';
    }
}

function showNotification(message, type = 'info') {
    // Simple notification - you can replace with a proper notification library
    console.log(`${type.toUpperCase()}: ${message}`);
    
    // Or create a simple toast notification
    const toast = document.createElement('div');
    toast.className = `alert alert-${type === 'error' ? 'danger' : type} position-fixed`;
    toast.style.top = '20px';
    toast.style.right = '300px';
    toast.style.zIndex = '9999';
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        document.body.removeChild(toast);
    }, 5000);
}
// Fetch session for each project
async function fetchSession(projectId) {
    try {
        // Build URL with query parameter if projectId is provided
        const url = projectId ? `/api/sessions?project_id=${projectId}` : '/api/sessions';
        
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch sessions');
        sessions = await response.json();
        
        console.log('Fetched sessions:', sessions);
        
        // Add this line to update the UI
        updateSessionsList();
        
        // Update unified sidebar if function is available
        if (window.updateSessionsSidebarList) {
            window.updateSessionsSidebarList(sessions, projectId);
        }
        
    } catch (error) {
        console.error('Error fetching sessions:', error);
    }
}

// Function to handle API call
function createNewProject(formData) {
    // Create a FormData object to handle file uploads
    const uploadData = new FormData();
    uploadData.append('name', formData.name);
    uploadData.append('participant', formData.participant);
    uploadData.append('folderName', formData.folderName);
    
    // Add all files to the FormData
    formData.files.forEach((file, index) => {
        uploadData.append('files', file);
    });
    
    // Use fetch API to send data to your backend
    fetch('/api/project/upload', {
        method: 'POST',
        body: uploadData  // Don't set Content-Type header, let browser set it for FormData
    })
    .then(response => response.json())
    .then(data => {
        // Handle successful response
        console.log('Upload started:', data);
        console.log('Upload ID:', data.upload_id);
        console.log('Sessions found:', data.sessions_found);
        
        // Close the modal
        const modalElement = document.getElementById('createProjectModal');
        if (modalElement) {
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                modal.hide();
            }
        }
        
        // Reset the form
        const form = document.getElementById('create-project-form');
        if (form) {
            form.reset();
        }
        
        // Refresh the project list
        initializeProjects().then(() => {
            // Navigate to the new project
            currentProjectId = data.project_id;
            console.log('Navigating to project:', data.project_id);
            
            // Update current project pill with the created project name
            updateCurrentProjectPill(formData.name);
            
            // Update active state in dropdown
            document.querySelectorAll('#project-dropdown-menu .dropdown-item').forEach(item => {
                item.classList.remove('active');
                item.removeAttribute('aria-current');
                if (item.dataset.projectId == data.project_id) {
                    item.classList.add('active');
                    item.setAttribute('aria-current', 'page');
                }
            });
        });
    })
    .catch(error => {
        // Handle errors
        console.error('Error:', error);
        alert('Failed to create project. Please try again.');
    });
}

// Show create project form
function showCreateProjectForm() {
    const modalElement = document.getElementById('createProjectModal');
    if (modalElement) {
        const modal = new bootstrap.Modal(modalElement);
        modal.show();
    } else {
        console.error('Create Project Modal not found');
    }
}

// Show table view
function showTableView() {
    document.getElementById("table-view").style.display = "block";
    document.getElementById("visualization-view").style.display = "none";
}

// Show visualization view
async function visualizeSession(sessionId) {
    // If we're already viewing a session and switching to another, save changes first
    if (currentSessionId && currentSessionId !== sessionId) {
        const currentSession = sessions.find(s => s.session_id == currentSessionId);
        if (currentSession) {
            try {
                console.log(`Saving bout changes before switching from ${currentSessionId} to ${sessionId}`);
                await SessionAPI.updateSessionMetadata(currentSession);
            } catch (error) {
                console.error('Error saving bout changes before switching sessions:', error);
            }
        }
    }
    // Clean up previous event handlers
    activeHandlers.forEach(h => {
        document.removeEventListener(h.type, h.handler);
    });
    activeHandlers.length = 0;
    
    // Also clean up any stray elements
    document.querySelectorAll('.drag-overlay, .left-overlay, .right-overlay').forEach(el => el.remove());
    
    // Find the session by ID
    const session = sessions.find(s => s.session_id == sessionId);
    if (!session) {
        console.error('Session not found:', sessionId);
        return;
    }
    
    // Check if the session is actually available (not deleted)
    if (!SessionService.isSessionAvailable(session)) {
        console.error('Attempted to visualize deleted session:', sessionId);
        
        // Find an available session to visualize instead
        const availableSessions = SessionService.getFilteredSessions(sessions);
        if (availableSessions.length > 0) {
            console.log('Redirecting to first available session');
            visualizeSession(availableSessions[0].session_id);
        } else {
            console.log('No available sessions');
            showTableView();
        }
        return;
    }
    
    // Set the current session name/id
    currentSessionId = sessionId;
    currentActiveSession = session.session_name;
    
    dragContext.currentSession = session;

    if (!session.data || session.data.length === 0) {
        const { bouts, data } = await SessionAPI.loadSessionData(sessionId);
        session.bouts = bouts;
        session.data = data;
        if (!session.data || session.data.length === 0) {
            console.error('No valid data for session:', currentActiveSession);
            return;
        }
    }
    const validData = SessionService.validateSessionData(session);
    if (!validData) {
        console.error('Invalid data format:', session.data);
        return;
    }

    document.getElementById("table-view").style.display = "none";
    document.getElementById("visualization-view").style.display = "flex";

    // Update sidebar highlighting for the current session
    updateSidebarHighlighting();

    if (session.status === "Initial") {
        session.status = "Visualized";
        await SessionAPI.updateSessionMetadata(session);
        updateSessionsList();
    }

    // If currentLabelingName is "No Labeling", set it to the first available labeling
    if (currentLabelingName === "No Labeling") {
        const availableLabelings = Object.keys(session.labelings || {});
        console.log('Available labelings:', availableLabelings);
        if (availableLabelings.length > 0) {
            currentLabelingName = availableLabelings[0];
        }
    }
    console.log('Current selected labeling:', currentLabelingName);
    const actionButtons = document.getElementById("action-buttons");
    actionButtons.innerHTML = "";

    // Use template for action buttons
    actionButtons.innerHTML = ActionButtonTemplates.visualizationActionButtons({
        isSplitting: isSplitting,
        isVerified: session.verified,
        labelingName: currentLabelingName,
        labelingColor: currentLabelingJSON ? currentLabelingJSON.color : '#000000',
    });

    // Setup event listeners using the template handlers
    ActionButtonHandlers.setupVisualizationButtons({
        onDelete: () => decideSession(currentSessionId, false),
        onVerify: () => toggleVerifiedStatus(),
        onSplit: () => toggleSplitMode(),
        onScore: () => scoreSession(currentSessionId, session.project_name, session.session_name),
        isSplitting: isSplitting
    });

    const dataToPlot = session.data;
    if (!dataToPlot || dataToPlot.length === 0) {
        console.error('No data to plot for session:', sessionName);
        return;
    }

    const timestamps = dataToPlot.map(d => d.ns_since_reboot).filter(t => t);
    const xValues = dataToPlot.map(d => d.x).filter(x => typeof x === 'number');
    const yValues = dataToPlot.map(d => d.y).filter(y => typeof y === 'number');
    const zValues = dataToPlot.map(d => d.z).filter(z => typeof z === 'number');
    const labels = dataToPlot.map(d => d.label).filter(label => typeof label === 'number');
    if (timestamps.length === 0) {
        console.error('No valid timestamps for plotting');
        return;
    }

    // With this more efficient approach:
    minTimestamp = timestamps.reduce((min, val) => Math.min(min, val), Infinity);

    // And similarly for maxTimestamp:
    maxTimestamp = timestamps.reduce((max, val) => Math.max(max, val), -Infinity);

    const traces = [
        { x: timestamps, y: xValues, name: 'X Axis', type: 'scatter', mode: 'lines', line: { color: '#17BECF' } },
        { x: timestamps, y: yValues, name: 'Y Axis', type: 'scatter', mode: 'lines', line: { color: '#FF7F0E' } },
        { x: timestamps, y: zValues, name: 'Z Axis', type: 'scatter', mode: 'lines', line: { color: '#2CA02C' } },
        { x: timestamps, y: labels, name: 'Z Axis', type: 'scatter', mode: 'lines', line: { color: '#FF0000' } }
    ];
    const shapes = [];

    splitPoints.forEach(point => {
        shapes.push({
            type: 'line',
            x0: point,
            x1: point,
            y0: 0,
            y1: 1,
            yref: 'paper', // Span full y-axis height
            line: {
                color: '#FF0000', // Grey
                width: 2,
                dash: 'dash'
            }
        });
    });

    const layout = {
        xaxis: { title: 'Timestamp', rangeslider: { visible: false } },
        yaxis: { title: 'Acceleration (m/s²)'},
        showlegend: true,
        shapes: shapes,
    };

    const container = document.querySelector('.plot-container');
    container.querySelectorAll('.drag-overlay').forEach(el => el.remove());

    Plotly.newPlot('timeSeriesPlot', traces, layout).then(() => {
        const plotDiv = document.getElementById('timeSeriesPlot');

        ensureSessionBoutsIsArray(session);

        const overlays = session.bouts.map((bout, index) => createBoutOverlays(index, container));
        // Update all overlay positions
        function updateAllOverlayPositions() {
            console.log('Updating overlay positions');
            session.bouts.forEach((bout, index) => {
                // Only show overlays for bouts that match the currently selected labeling
                if (bout['label'] === currentLabelingName) {
                    updateOverlayPositions(plotDiv, bout, index);
                } else {
                    // Hide overlays that don't match the current labeling
                    hideOverlay(index);
                }
            });
        }
        updateAllOverlayPositions();

        // Handle plot click for splitting
        plotDiv.on('plotly_click', function(data) {
            if (isSplitting) {
                const splitPoint = data.points[0].x;
                if (!splitPoints.includes(splitPoint)) {
                    // Get current zoom level before adding split point
                    let viewState = null;
                    if (plotDiv && plotDiv._fullLayout && plotDiv._fullLayout.xaxis) {
                        viewState = {
                            xrange: plotDiv._fullLayout.xaxis.range.slice(),
                            yrange: plotDiv._fullLayout.yaxis.range.slice()
                        };
                    }
                    
                    splitPoints.push(splitPoint);
                    
                    // Refresh plot to show new split point marker and restore zoom level
                    visualizeSession(sessionId).then(() => {
                        if (viewState && plotDiv) {
                            Plotly.relayout(plotDiv, {
                                'xaxis.range': viewState.xrange,
                                'yaxis.range': viewState.yrange
                            });
                        }
                    });
                }
            }
        });
        // Update overlays on plot relayout (pan, zoom, etc.)
        plotDiv.on('plotly_relayout', () => {
            console.log('Plotly relayout event');
            updateAllOverlayPositions();
        });
        // Update overlays during pan/zoom interaction
        plotDiv.on('plotly_relayouting', () => {
            updateAllOverlayPositions();
        });
        // Update overlays on window resize
        window.addEventListener('resize', () => {
            Plotly.Plots.resize(plotDiv).then(() => {
                updateAllOverlayPositions();
            });
        });
    });


}
// Convert from pixel positions to data values
function pixelToData(pixelX, xAxis) {
    return xAxis.range[0] + (pixelX - xAxis._offset) * (xAxis.range[1] - xAxis.range[0]) / xAxis._length;
}
// When opening the modal
document.getElementById('labelingModal').addEventListener('show.bs.modal', function() {
    console.log('Labeling modal opened');
    fetchAndDisplayLabelings(currentProjectId);
});

async function createNewLabeling() {
    // Show a prompt to get the new labeling name
    const labelingName = prompt('Enter a name for the new labeling:');
    
    if (labelingName && labelingName.trim()) {
        try {
            // Make API call to create new labeling
            const response = await fetch(`/api/labelings/${currentProjectId}/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: labelingName.trim(),
                    labels: {}  // Initialize with empty labels structure
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('New labeling created:', result);
            
            // Refresh the labelings list to show the new labeling
            await fetchAndDisplayLabelings(currentProjectId);
            
            // Select the new labeling immediately
            selectLabeling(labelingName.trim());
            
        } catch (error) {
            console.error('Error creating new labeling:', error);
            alert('Failed to create new labeling. Please try again.');
        }
    }
}
// You can also initialize it in the DOMContentLoaded event listener
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the global variable
    labelingsList = document.getElementById('available-labelings-list');
    
    if (labelingsList) {
        // Handle clicks on the plus icon
        labelingsList.addEventListener('click', function(event) {
            if (event.target.classList.contains('fa-plus')) {
                event.preventDefault();
                createNewLabeling();
            }
        });
        
        // Handle hover effects on the plus icon
        labelingsList.addEventListener('mouseenter', function(event) {
            if (event.target.classList.contains('fa-plus')) {
                event.target.style.background = 'rgba(0,0,0,0.1)';
                event.target.style.borderRadius = '50%';
                event.target.style.padding = '4px';
                event.target.style.cursor = 'pointer';
            }
        }, true);
        
        labelingsList.addEventListener('mouseleave', function(event) {
            if (event.target.classList.contains('fa-plus')) {
                event.target.style.background = 'rgba(224,224,224,0)';
            }
        }, true);
    }

});
async function fetchAndDisplayLabelings(projectId) {
    try {
        labelings = await ProjectAPI.fetchLabelings(projectId);
        labelingsList = document.getElementById('available-labelings-list');
        
        // Reset current labeling header when refreshing the list
        updateCurrentLabelingHeader();
        
        // Clear existing content except the plus icon
        const plusIcon = labelingsList.querySelector('.fa-plus');
        labelingsList.innerHTML = '';
        if (plusIcon) {
            labelingsList.appendChild(plusIcon);
        }
        
        console.log('Parsed labelings:', labelings);
        console.log(typeof(labelings))
        // Display each labeling
        if (labelings && labelings.length > 0) {
            labelings.forEach((labeling, index) => {
                console.log(typeof(labeling))
                console.log('Labeling item:', labeling.name);
                const currentColor = labeling.color || generateDefaultColor(index);
                labeling = labeling.name;
                const labelingItem = document.createElement('div');
                labelingItem.className = 'labeling-item d-flex justify-content-between align-items-center py-1';

                labelingItem.innerHTML = `
                    <div class="d-flex align-items-center">
                        <div class="color-picker-container me-2" style="position: relative;">
                            <div class="color-circle" style="width: 20px; height: 20px; border-radius: 50%; background-color: ${currentColor}; border: 1px solid #ccc; cursor: pointer;" onclick="openColorPicker('${labeling}', this)"></div>
                            <input type="color" class="color-picker" value="${currentColor}" style="position: absolute; opacity: 0; width: 20px; height: 20px; cursor: pointer;" onchange="updateLabelingColor('${labeling}', this.value, this)">
                        </div>
                        <span>${labeling}</span>
                    </div>
                    <div class="labeling-actions d-flex">
                        <button class="btn btn-sm btn-outline-primary" onclick="selectLabeling('${labeling}')">
                            Select
                        </button>
                    </div>
                `;
                labelingsList.appendChild(labelingItem);
            });
        } else {
            const noLabelings = document.createElement('div');
            noLabelings.className = 'text-muted small';
            noLabelings.textContent = 'No labelings available';
            labelingsList.appendChild(noLabelings);
        }
        
    } catch (error) {
        console.error('Error fetching labelings:', error);
        const labelingsList = document.getElementById('available-labelings-list');
        labelingsList.innerHTML = '<div class="text-danger small">Error loading labelings</div>';
    }
}

function getLabelingFromLabelingName(labelingName) {
    if (!labelings || labelings.length === 0) {
        console.warn('No labelings available to search from');
        return null;
    }
    const labeling = labelings.find(l => l.name === labelingName);
    if (!labeling) {
        console.warn(`Labeling not found for name: ${labelingName}`);
        return null;
    }
    return labeling;
}

function selectLabeling(labelingName) {
    currentLabelingName = labelingName;
    currentLabelingJSON = getLabelingFromLabelingName(labelingName);

    // Update the current labeling name in visualization view with color and maintain interactivity
    const currentLabelingNameElement = document.getElementById('current-labeling-name');
    if (currentLabelingNameElement) {

        const currentLabeling = getLabelingFromLabelingName(labelingName);
        const labelingColor = currentLabeling.color
        
        currentLabelingNameElement.innerHTML = `
            <div class="color-circle me-1" style="width: 12px; height: 12px; border-radius: 50%; background-color: ${labelingColor}; border: 1px solid #ccc; display: inline-block;"></div>
            ${labelingName}
        `;
        
        // Maintain the cursor pointer and transition styles
        currentLabelingNameElement.style.cursor = 'pointer';
        currentLabelingNameElement.style.transition = 'background-color 0.2s ease, transform 0.1s ease';
    }
    
    // If we're in visualization view, update the overlays to show only bouts matching this labeling
    if (dragContext.currentSession && dragContext.currentSession.bouts) {
        const plotDiv = document.getElementById('timeSeriesPlot');
        if (plotDiv && plotDiv._fullLayout && plotDiv._fullLayout.xaxis) {
            dragContext.currentSession.bouts.forEach((bout, index) => {
                if (bout['label'] === currentLabelingName) {
                    updateOverlayPositions(plotDiv, bout, index);
                } else {
                    hideOverlay(index);
                }
            });
        }
    }
    
    // You can add more logic here for what happens when a labeling is selected
}

function updateCurrentLabelingHeader(labelingName = null) {
    const displayName = labelingName || currentLabelingName;

    // Update visualization view name display
    const currentLabelingNameElement = document.getElementById('current-labeling-name');
    if (currentLabelingNameElement) {
        if (displayName && displayName !== 'No Labeling') {
            const currentLabeling = getLabelingFromLabelingName(displayName);
            const labelingColor = currentLabeling ? currentLabeling.color : generateDefaultColor(0);

            currentLabelingNameElement.innerHTML = `
                <div class="color-circle me-1" style="width: 12px; height: 12px; border-radius: 50%; background-color: ${labelingColor}; border: 1px solid #ccc; display: inline-block;"></div>
                ${displayName}
            `;
        } else {
            currentLabelingNameElement.textContent = 'No Labeling';
        }
        
        // Always maintain the interactive styling
        currentLabelingNameElement.style.cursor = 'pointer';
        currentLabelingNameElement.style.transition = 'background-color 0.2s ease, transform 0.1s ease';
    }
}
function createBoutOverlays(index, container) {
    const dragOverlay = document.createElement('div');
    dragOverlay.id = `drag-overlay-${index}`;
    dragOverlay.className = 'drag-overlay';
    dragOverlay.dataset.boutIndex = index; // Store index for reference
    container.appendChild(dragOverlay);
    
    const leftOverlay = document.createElement('div');
    leftOverlay.id = `left-overlay-${index}`;
    leftOverlay.className = 'left-overlay';
    leftOverlay.dataset.boutIndex = index;
    container.appendChild(leftOverlay);

    const rightOverlay = document.createElement('div');
    rightOverlay.id = `right-overlay-${index}`;
    rightOverlay.className = 'right-overlay';
    rightOverlay.dataset.boutIndex = index;
    container.appendChild(rightOverlay);
    
    // Dragging state variables
    let isDragging = false;
    let isResizingLeft = false;
    let isResizingRight = false;
    let startX = 0;
    let originalLeft = 0;
    let originalWidth = 0;
    let hasMovedBout = false; // Track if bout was actually moved
    
    // Add double-click event to remove the bout
    dragOverlay.addEventListener('dblclick', function() {
        const boutIndex = parseInt(dragOverlay.dataset.boutIndex);
        if (dragContext.currentSession && dragContext.currentSession.bouts) {
            // Get current zoom level before removing bout
            const plotDiv = document.getElementById('timeSeriesPlot');
            let viewState = null;
            if (plotDiv && plotDiv._fullLayout && plotDiv._fullLayout.xaxis) {
                viewState = {
                    xrange: plotDiv._fullLayout.xaxis.range.slice(),
                    yrange: plotDiv._fullLayout.yaxis.range.slice()
                };
            }
            
            dragContext.currentSession.bouts.splice(boutIndex, 1);
            console.log(`Removed bout ${boutIndex}`);
            SessionAPI.updateSessionMetadata(dragContext.currentSession);
            
            // Refresh the plot and restore zoom level
            visualizeSession(currentSessionId).then(() => {
                if (viewState && plotDiv) {
                    Plotly.relayout(plotDiv, {
                        'xaxis.range': viewState.xrange,
                        'yaxis.range': viewState.yrange
                    });
                }
            });
        }
    });
    // Element-specific mouse events for dragging
    dragOverlay.addEventListener('mousedown', function(e) {
        isDragging = true;
        hasMovedBout = false; // Reset movement flag
        startX = e.clientX;
        originalLeft = parseInt(dragOverlay.style.left) || 0;
        originalWidth = parseInt(dragOverlay.style.width) || 0;
        e.preventDefault();
        
        // Add temporary handlers
        addTemporaryMouseHandlers();
    });
    
    // Mouse handlers for left and right resizing
    leftOverlay.addEventListener('mousedown', function(e) {
        isResizingLeft = true;
        hasMovedBout = false; // Reset movement flag
        startX = e.clientX;
        originalLeft = parseInt(dragOverlay.style.left) || 0;
        originalWidth = parseInt(dragOverlay.style.width) || 0;
        e.preventDefault();
        dragOverlay.style.cursor = 'w-resize';
        
        // Add temporary handlers
        addTemporaryMouseHandlers();
    });
    
    rightOverlay.addEventListener('mousedown', function(e) {
        isResizingRight = true;
        hasMovedBout = false; // Reset movement flag
        startX = e.clientX;
        originalLeft = parseInt(dragOverlay.style.left) || 0;
        originalWidth = parseInt(dragOverlay.style.width) || 0;
        e.preventDefault();
        dragOverlay.style.cursor = 'e-resize';
        
        // Add temporary handlers
        addTemporaryMouseHandlers();
    });
    // Add temporary mousemove and mouseup handlers that clean themselves up
    function addTemporaryMouseHandlers() {
        const mouseMoveHandler = function(e) {
            if (!isDragging && !isResizingLeft && !isResizingRight) return;
        
            const boutIndex = parseInt(dragOverlay.dataset.boutIndex);
            const plotDiv = document.getElementById('timeSeriesPlot');
            const xAxis = plotDiv._fullLayout.xaxis;
            
            // Regular dragging - move entire overlay
            if (isDragging) {
                const dx = e.clientX - startX;
                dragOverlay.style.left = `${originalLeft + dx}px`;
                
                // Mark that the bout has moved if there's significant movement
                if (Math.abs(dx) > 2) {
                    hasMovedBout = true;
                }
                
                // Convert pixel position back to data coordinates
                const newX0 = pixelToData(originalLeft + dx, xAxis);
                const newX1 = pixelToData(originalLeft + originalWidth + dx, xAxis);
                
                updateBoutData(boutIndex, newX0, newX1);
                
                // Update left and right handle positions
                leftOverlay.style.left = `${originalLeft + dx}px`;
                rightOverlay.style.left = `${originalLeft + originalWidth + dx - parseInt(rightOverlay.style.width || 10)}px`;
            }
            
            // Left resize - adjust left side of overlay
            else if (isResizingLeft) {
                const dx = e.clientX - startX;
                const newLeft = originalLeft + dx;
                const newWidth = originalWidth - dx;
                
                // Prevent width from becoming negative
                if (newWidth <= 10) return;
                
                // Mark that the bout has moved if there's significant movement
                if (Math.abs(dx) > 2) {
                    hasMovedBout = true;
                }
                
                dragOverlay.style.left = `${newLeft}px`;
                dragOverlay.style.width = `${newWidth}px`;
                leftOverlay.style.left = `${newLeft}px`;
                
                // Convert pixel position back to data coordinates
                const newX0 = pixelToData(newLeft, xAxis);
                const newX1 = pixelToData(newLeft + newWidth, xAxis);
                
                updateBoutData(boutIndex, newX0, newX1);
            }
            
            // Right resize - adjust right side of overlay
            else if (isResizingRight) {
                const dx = e.clientX - startX;
                const newWidth = originalWidth + dx;
                
                // Prevent width from becoming negative
                if (newWidth <= 10) return;
                
                // Mark that the bout has moved if there's significant movement
                if (Math.abs(dx) > 2) {
                    hasMovedBout = true;
                }
                
                dragOverlay.style.width = `${newWidth}px`;
                rightOverlay.style.left = `${originalLeft + newWidth - parseInt(rightOverlay.style.width || 10)}px`;
                
                // Convert pixel position back to data coordinates
                const newX0 = pixelToData(originalLeft, xAxis);
                const newX1 = pixelToData(originalLeft + newWidth, xAxis);
                
                updateBoutData(boutIndex, newX0, newX1);
            }
        };
        
        const mouseUpHandler = function() {
            isDragging = isResizingLeft = isResizingRight = false;
            if (dragOverlay) dragOverlay.style.cursor = 'move';

            // Only save bout changes if the bout was actually moved
            if (hasMovedBout) {
                saveBoutChanges().catch(err => console.error('Error in saveBoutChanges:', err));
            }
            
            // Remove the temporary handlers
            document.removeEventListener('mousemove', mouseMoveHandler);
            document.removeEventListener('mouseup', mouseUpHandler);
            
            // Also remove from our tracking array
            const moveIndex = activeHandlers.findIndex(h => h.handler === mouseMoveHandler);
            if (moveIndex !== -1) activeHandlers.splice(moveIndex, 1);
            
            const upIndex = activeHandlers.findIndex(h => h.handler === mouseUpHandler);
            if (upIndex !== -1) activeHandlers.splice(upIndex, 1);
        };
        
        // Store references to remove them later
        activeHandlers.push({ 
            type: 'mousemove', 
            handler: mouseMoveHandler 
        });
        activeHandlers.push({ 
            type: 'mouseup', 
            handler: mouseUpHandler 
        });
        
        document.addEventListener('mousemove', mouseMoveHandler);
        document.addEventListener('mouseup', mouseUpHandler);
    }
    
    // Helper function to update bout data
    function updateBoutData(boutIndex, x0, x1) {
        if (dragContext.currentSession && dragContext.currentSession.bouts) {
            if (dragContext.currentSession.bouts[boutIndex]) {
                dragContext.currentSession.bouts[boutIndex]['start'] = x0;
                dragContext.currentSession.bouts[boutIndex]['end'] = x1;
            } else {
                // If boutIndex is out of bounds, log an error
                console.error(`Bout index ${boutIndex} not found in session ${dragContext.currentSession.name}`);
            }
        } else {
            console.error("No current session in drag context");
        }
    }
    
    // Make saveBoutChanges async and ensure it completes
    async function saveBoutChanges() {
        if (sessions && sessions.length > 0) {
            const session = sessions.find(s => s.session_id == currentSessionId);
            if (session) {
                console.log(`Saving bout changes for session ${session.session_name} (ID: ${currentSessionId})`);
                try {
                    await SessionAPI.updateSessionMetadata(session);
                    console.log('Successfully saved bout changes to server');
                } catch (error) {
                    console.error('Failed to save bout changes:', error);
                    alert('Failed to save bout changes. Your changes may be lost when switching sessions.');
                }
            } else {
                console.error(`Session not found for saving: ID ${currentSessionId}`);
            }
        } else {
            console.error("No sessions available for saving");
        }
    }

    return { dragOverlay, leftOverlay, rightOverlay };
}


// Add this function to update the overlay positions
function updateOverlayPositions(plotDiv, bout, index) {
    // Ensure the plotDiv is available and initialized
    if (!plotDiv || !plotDiv._fullLayout || !plotDiv._fullLayout.xaxis) {
        console.error('Plot layout not available');
        return;
    }
    const bout_start = bout['start'];
    const bout_end = bout['end'];
    const bout_label = bout['label'];

    // Get the overlay elements
    const dragOverlay = document.getElementById(`drag-overlay-${index}`);
    const leftOverlay = document.getElementById(`left-overlay-${index}`);
    const rightOverlay = document.getElementById(`right-overlay-${index}`);
    
    if (!dragOverlay || !leftOverlay || !rightOverlay) return;

    // Only show and position overlays for the currently selected labeling
    if (bout_label !== currentLabelingName) {
        hideOverlay(index);
        return;
    }

    // Show overlays (in case they were hidden)
    dragOverlay.style.display = 'block';
    leftOverlay.style.display = 'block';
    rightOverlay.style.display = 'block';

    // Get axis object from Plotly layout
    const xAxis = plotDiv._fullLayout.xaxis;
    const yAxis = plotDiv._fullLayout.yaxis;
    
    // Convert data coordinates to pixel positions
    const pixelX0 = xAxis._length * (bout_start - xAxis.range[0]) / (xAxis.range[1] - xAxis.range[0]) + xAxis._offset;
    const pixelX1 = xAxis._length * (bout_end - xAxis.range[0]) / (xAxis.range[1] - xAxis.range[0]) + xAxis._offset;
    
    // Set handle size
    const handleWidth = 20;
    const handleHeight = yAxis._length;
    
    const currentLabeling = getLabelingFromLabelingName(currentLabelingName);
    const labelingColor = currentLabeling ? currentLabeling.color : generateDefaultColor(0);

    // Set main overlay position and size
    dragOverlay.style.position = 'absolute';
    dragOverlay.style.left = `${pixelX0}px`;
    dragOverlay.style.width = `${pixelX1 - pixelX0}px`;
    dragOverlay.style.top = `${yAxis._offset}px`;
    dragOverlay.style.height = `${handleHeight}px`;
    dragOverlay.style.backgroundColor = labelingColor + "77"
    dragOverlay.style.border = '2px solid black';
    
    // Set left handle position and size
    leftOverlay.style.position = 'absolute';
    leftOverlay.style.left = `${pixelX0}px`;
    leftOverlay.style.width = `${handleWidth}px`;
    leftOverlay.style.top = `${yAxis._offset}px`;
    leftOverlay.style.height = `${handleHeight}px`;
    leftOverlay.style.backgroundColor = 'rgba(0, 0, 255, 0)';
    leftOverlay.style.cursor = 'w-resize';
    leftOverlay.style.zIndex = '1000';
    
    // Set right handle position and size
    rightOverlay.style.position = 'absolute';
    rightOverlay.style.left = `${pixelX1 - handleWidth}px`;
    rightOverlay.style.width = `${handleWidth}px`;
    rightOverlay.style.top = `${yAxis._offset}px`;
    rightOverlay.style.height = `${handleHeight}px`;
    rightOverlay.style.backgroundColor = 'rgba(0, 0, 255, 0)';
    rightOverlay.style.cursor = 'e-resize';
    rightOverlay.style.zIndex = '1000';
}

// Helper function to hide overlay that doesn't match current labeling
function hideOverlay(index) {
    const dragOverlay = document.getElementById(`drag-overlay-${index}`);
    const leftOverlay = document.getElementById(`left-overlay-${index}`);
    const rightOverlay = document.getElementById(`right-overlay-${index}`);
    
    if (dragOverlay) dragOverlay.style.display = 'none';
    if (leftOverlay) leftOverlay.style.display = 'none';
    if (rightOverlay) rightOverlay.style.display = 'none';
}

// Toggle splitting mode
function toggleSplitMode() {
    isSplitting = !isSplitting;
    const split_btn_overlay = document.getElementById('split-btn-overlay');
    split_btn_overlay.style.background = isSplitting ? 'rgba(224, 224, 224)' : 'rgba(0, 0, 0, 0)';
}
async function toggleVerifiedStatus() {
    // Get current session
    const session = getCurrentSession();
    if (!session) {
        console.error('No current session to toggle verified status');
        return;
    }
    
    // Get the verified button (try visualization view first, then table view)
    let verified_btn_viz = document.getElementById('verified-btn-viz');
    if (!verified_btn_viz) {
        verified_btn_viz = document.getElementById(`verified-btn-${session.session_id}`);
    }
    
    if (!verified_btn_viz) {
        console.error('Verified button not found');
        return;
    }
    
    // Toggle verified status
    session.verified = session.verified ? 0 : 1;
    
    // Update the visual state immediately
    verified_btn_viz.style.color = session.verified ? '#28a745' : '#dee2e6';
    
    // Save to backend
    try {
        await SessionAPI.updateSessionMetadata(session);
        console.log(`Session ${session.session_id} verified status updated to: ${session.verified}`);
        
        // Also update the sessions list if we're in table view or sidebar
        updateSessionsList();

    } catch (error) {
        console.error('Error updating verified status:', error);
        // Revert the visual change on error
        session.verified = session.verified ? 0 : 1;
        verified_btn_viz.style.color = session.verified ? '#28a745' : '#dee2e6';
    }
}

function getCurrentSession() {
    return SessionService.findSessionById(sessions, currentSessionId);
}

async function decideSession(sessionId, keep) {
    const session = sessions.find(s => s.session_id == sessionId);
    if (!session) return;
    
    const wasCurrentlyVisualized = (currentSessionId == sessionId);
    
    // Find the next session before marking this one as deleted
    let nextSessionToShow = null;
    if (!keep && wasCurrentlyVisualized) {
        nextSessionToShow = SessionService.findNextSessionAfterDeletion(sessions, sessionId);
    }
    
    // Update the session status
    session.status = "Decision Made";
    // Explicitly set keep to 0 or 1, rather than false/true
    session.keep = keep ? 1 : 0;
    await SessionAPI.updateSessionMetadata(session);
    
    // Update the UI with the new session list
    updateSessionsList();
    
    // Handle navigation after deletion
    if (!keep && wasCurrentlyVisualized) {
        if (nextSessionToShow && nextSessionToShow.session_id != sessionId) {
            // Navigate to the next session in sequence
            console.log(`Deleted currently visualized session, navigating to: ${nextSessionToShow.session_name}`);
            visualizeSession(nextSessionToShow.session_id);
        } else {
            // If we couldn't find a proper next session or only this session exists
            const remainingSessions = SessionService.getFilteredSessions(sessions);
            if (remainingSessions.length > 0) {
                console.log(`Navigating to first available session: ${remainingSessions[0].session_name}`);
                visualizeSession(remainingSessions[0].session_id);
            } else {
                // No sessions left, return to table view
                console.log('No sessions available after deletion, returning to table view');
                showTableView();
            }
        }
    } else {
        // Return to table view for non-current sessions or when keeping sessions
        showTableView();
    }
}

// Now update the splitSession function to maintain context
async function splitSession() {
    console.log('Splitting session:', currentSessionId);
    if (splitPoints.length === 0) {
        alert('No split points selected');
        return;
    }
    
    // First, ensure any pending bout changes are saved
    const currentSession = sessions.find(s => s.session_id == currentSessionId);
    if (currentSession) {
        try {
            // Wait for metadata update to complete before proceeding
            await SessionAPI.updateSessionMetadata(currentSession);
            console.log('Ensured latest bout changes are saved before splitting');
        } catch (error) {
            console.error('Error saving bout changes before split:', error);
        }
    }
    
    try {
        const response = await fetch(`/api/session/${currentSessionId}/split`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ split_points: splitPoints })
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to split session');
        }
        const result = await response.json();
        // Clear split points
        splitPoints = [];
        isSplitting = false;

        // PROBLEM: This only resets colors, not the expanded state
        document.querySelectorAll('#project-dropdown-menu .dropdown-item').forEach(item => {
            if (!item.classList.contains('active')) {
                item.style.backgroundColor = '';
                item.style.color = '';
            }
        });

        // Reset Bootstrap dropdown state
        const dropdownToggle = document.querySelector('[data-bs-toggle="dropdown"]');
        if (dropdownToggle) {
            dropdownToggle.setAttribute('aria-expanded', 'false');
            const dropdownMenu = document.getElementById('project-dropdown-menu');
            if (dropdownMenu) dropdownMenu.classList.remove('show');
            dropdownToggle.classList.remove('show');
        }

        // Fetch sessions based on current context
        if (currentProjectId) {
            await fetchProjectSessions(currentProjectId);
        } else {
            await fetchSession();
        }
        
        showTableView();
    } catch (error) {
        console.error('Error splitting session:', error);
        alert('Failed to split session: ' + error.message);
    }
}

function createNewBout() {
    // Get the current plotly visualization
    const plotDiv = document.getElementById('timeSeriesPlot');
    
    // If there's no active plot, fall back to the full dataset range
    if (!plotDiv || !plotDiv._fullLayout || !plotDiv._fullLayout.xaxis) {
        // Fallback to using full dataset range with 25% width
        const middleTimestamp = (minTimestamp + maxTimestamp) / 2;
        const fullRange = maxTimestamp - minTimestamp;
        const boutHalfWidth = (fullRange * 0.25) / 2;
        const newBout = [middleTimestamp - boutHalfWidth, middleTimestamp + boutHalfWidth];
        addBoutToSession(newBout);
        return;
    }
    
    // Get the current visible x-axis range
    const xAxis = plotDiv._fullLayout.xaxis;
    const visibleMin = xAxis.range[0];
    const visibleMax = xAxis.range[1];
    
    // Save current zoom level
    const currentViewState = {
        xrange: [visibleMin, visibleMax],
        yrange: plotDiv._fullLayout.yaxis.range.slice()
    };
    
    // Calculate the midpoint of the visible range
    const middleTimestamp = (visibleMin + visibleMax) / 2;
    
    // Create a bout that is 25% of the visible range (12.5% on each side of the midpoint)
    const visibleRange = visibleMax - visibleMin;
    const boutHalfWidth = (visibleRange * 0.25) / 2;

    // Get current labeling name
    const currentLabelingElement = document.getElementById('current-labeling-name');
    let currentLabelingName = '';
    
    if (currentLabelingElement) {
        // Extract text content, removing any HTML elements
        const textContent = currentLabelingElement.textContent || currentLabelingElement.innerText;
        currentLabelingName = textContent.trim();
    }

    // Create a 480s wide bout (240s on each side of the midpoint)
    const newBout = {'start':middleTimestamp - boutHalfWidth,'end':middleTimestamp + boutHalfWidth,'label':currentLabelingName};
    
    // Add the bout to the session and maintain view state
    addBoutToSession(newBout, currentViewState);
}

// Helper function to add bout to session and update display
function addBoutToSession(newBout, viewState = null) {
    if (dragContext.currentSession && dragContext.currentSession.bouts) {
        // Add the new bout to the session
        dragContext.currentSession.bouts.push(newBout);
        
        // Update the session metadata in the background
        SessionAPI.updateSessionMetadata(dragContext.currentSession).then(() => {
            // Instead of full reloading, just add the new overlay
            const container = document.querySelector('.plot-container');
            
            // Create and add the new overlay elements
            const boutIndex = dragContext.currentSession.bouts.length - 1;
            createBoutOverlays(boutIndex, container);
            
            // Position the new overlay
            const plotDiv = document.getElementById('timeSeriesPlot');
            updateOverlayPositions(plotDiv, newBout, boutIndex);
            
            // Apply the previous view state if provided
            if (viewState) {
                Plotly.relayout(plotDiv, {
                    'xaxis.range': viewState.xrange,
                    'yaxis.range': viewState.yrange
                });
            }
        }).catch(error => {
            console.error('Error saving new bout:', error);
        });
    } else {
        console.error('No current session in drag context');
    }
}
// Delete project function
async function deleteProject(projectId, projectName) {
    // Show confirmation dialog
    const confirmDelete = confirm(
        `Are you sure you want to delete the project "${projectName}"?\n\n` +
        `This will permanently delete:\n` +
        `• All sessions in this project\n` +
        `• All data files and directories\n` +
        `• The participant record (if no other projects exist)\n\n` +
        `This action cannot be undone.`
    );
    
    if (!confirmDelete) {
        return;
    }
    
    try {
        const response = await fetch(`/api/project/${projectId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to delete project');
        }
        
        const result = await response.json();
        
        // Show success message
        alert(
            `Project deleted successfully!\n\n` +
            `Project: ${result.project_name}\n` +
            `Participant: ${result.participant_code}\n` +
            `Sessions deleted: ${result.sessions_deleted}\n` +
            `Directory deleted: ${result.directory_deleted ? 'Yes' : 'No'}\n` +
            `Participant deleted: ${result.participant_deleted ? 'Yes' : 'No'}`
        );
        
        // Refresh the projects list
        await initializeProjects();
        
        // If the deleted project was currently selected, clear the session view
        if (currentProjectId === projectId) {
            currentProjectId = null;
            document.getElementById('sessions-table-body').innerHTML = '';
            showTableView(); // Go back to table view if in visualization
        }
        
        updateCurrentProjectPill();
        
    } catch (error) {
        console.error('Error deleting project:', error);
        alert(`Failed to delete project: ${error.message}`);
    }
}

async function exportLabelsJSON() {
    try {
        const response = await fetch('/api/export/labels');
        if (!response.ok) {
            throw new Error('Failed to export data');
        }
        
        const data = await response.json();
        
        // Create downloadable JSON file
        const jsonString = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        // Create download link
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0] + '_' + 
                         new Date().toISOString().replace(/[:.]/g, '-').split('T')[1].split('-')[0];
        const filename = `smoking_labels_export_${timestamp}.json`;
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        // Success - file downloaded automatically, no need for alert/toast
        console.log(`Successfully exported ${data.total_sessions} sessions with ${data.total_labels} labels to ${filename}`);
        
    } catch (error) {
        console.error('Error exporting JSON:', error);
        // Show error notification only
        showNotification('Failed to export data: ' + error.message, 'error');
    }
}

function updateSidebarHighlighting() {
    // Remove active-session class from all links
    document.querySelectorAll('#session-list .nav-link').forEach(link => {
        link.classList.remove('active-session');
    });
    
    // Add active-session class to the current session
    if (currentActiveSession) {
        const activeLink = document.querySelector(`#session-list .nav-link[onclick*="'${currentSessionId}'"]`);
        if (activeLink) {
            activeLink.classList.add('active-session');
        }
    }
}

function navigateToNextSession() {
    const nextSession = SessionService.getNextSession(sessions, currentSessionId);
    
    if (!nextSession) {
        console.log('No next session available');
        if (SessionService.getFilteredSessions(sessions).length === 0) {
            showTableView();
        }
        return;
    }
    
    console.log(`Navigating to next session: ${nextSession.session_name}`);
    visualizeSession(nextSession.session_id);
}

function navigateToPreviousSession() {
    const prevSession = SessionService.getPreviousSession(sessions, currentSessionId);
    
    if (!prevSession) {
        console.log('No previous session available');
        if (SessionService.getFilteredSessions(sessions).length === 0) {
            showTableView();
        }
        return;
    }
    
    console.log(`Navigating to previous session: ${prevSession.session_name}`);
    visualizeSession(prevSession.session_id);
}

// Helper function to generate default colors for labelings
function generateDefaultColor(index) {
    const colors = [
        '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
        '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
        '#F8C471', '#82E0AA', '#F1948A', '#85C1E9', '#D2B4DE'
    ];
    return colors[index % colors.length];
}

// Function to open color picker when circle is clicked
function openColorPicker(labelingName, circleElement) {
    const colorPicker = circleElement.parentElement.querySelector('.color-picker');
    if (colorPicker) {
        colorPicker.click();
    }
}

// Function to update labeling color
async function updateLabelingColor(labelingName, newColor, colorPickerElement) {
    try {
        // Update the visual circle
        const colorCircle = colorPickerElement.parentElement.querySelector('.color-circle');
        if (colorCircle) {
            colorCircle.style.backgroundColor = newColor;
        }
        
        // Here you could save the color preference to backend/localStorage
        console.log(`Updated color for labeling "${labelingName}" to ${newColor}`);
        
        // Update color in database
        const response = await fetch(`/api/labelings/${currentProjectId}/color`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                color: newColor,
                name: labelingName
            })
        });
        console.log(`Response from server: ${response.status} ${response.statusText}`);
        labelings = await ProjectAPI.fetchLabelings(currentProjectId);
        // If we're in visualization view, update the overlays to show only bouts matching this labeling
        if (dragContext.currentSession && dragContext.currentSession.bouts) {
            const plotDiv = document.getElementById('timeSeriesPlot');
            if (plotDiv && plotDiv._fullLayout && plotDiv._fullLayout.xaxis) {
                dragContext.currentSession.bouts.forEach((bout, index) => {
                    if (bout['label'] === currentLabelingName) {
                        updateOverlayPositions(plotDiv, bout, index);
                    } else {
                        hideOverlay(index);
                    }
                });
            }
        }
        const currentLabelingNameElement = document.getElementById('current-labeling-name');
        if (labelingName == currentLabelingName) {
            currentLabelingNameElement.innerHTML = `
                <div class="color-circle me-1" style="width: 12px; height: 12px; border-radius: 50%; background-color: ${newColor}; border: 1px solid #ccc; display: inline-block;"></div>
                ${labelingName}
            `;
        }

    } catch (error) {
        console.error('Error updating labeling color:', error);
    }
}
// Global drag context
const dragContext = {
    currentSession: null  // Will store the session being modified
};
// Add at the top of your file
const activeHandlers = [];

// Create global reference to these handlers so we can remove them
let sessions = [];
// Add this variable to track the current project
let currentLabelingName = 'No Labeling';
let currentLabelingJSON = null;
let labelingsList = null; // Add this global variable

let labelings = null;
let currentProjectId = null;
let currentSessionId = null;
let currentActiveSession = null;
let isSplitting = false;
let activeUploadId = null; // Track active upload
let splitPoints = [];
let minTimestamp = null;
let maxTimestamp = null;

// Make functions available globally for inline event handlers
window.visualizeSession = visualizeSession;
window.openColorPicker = openColorPicker;
window.updateLabelingColor = updateLabelingColor;
window.selectLabeling = selectLabeling;
window.scoreSession = scoreSession;
window.showTableView = showTableView;
window.decideSession = decideSession;
window.toggleSplitMode = toggleSplitMode;
window.toggleVerifiedStatus = toggleVerifiedStatus;
window.splitSession = splitSession;
window.createNewBout = createNewBout;
window.showCreateProjectForm = showCreateProjectForm;
window.createNewProject = createNewProject;
window.navigateToNextSession = navigateToNextSession;
window.navigateToPreviousSession = navigateToPreviousSession;
window.updateSidebarHighlighting = updateSidebarHighlighting;
window.exportLabelsJSON = exportLabelsJSON;


initializeProjects();
eventListeners.addEventListeners();
checkUrlParameters();
checkUrlParameters();