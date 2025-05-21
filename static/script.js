import * as eventListeners from './eventListeners.js';

// Fetch projects from backend
async function fetchProjects() {
    try {
        const response = await fetch('/api/projects');
        if (!response.ok) throw new Error('Failed to fetch projects');
        const projects = await response.json();
        console.log('Fetched projects:', projects);
        // populateSessions(projects);
        // populateProjects(projects);
    } catch (error) {
        console.error('Error fetching projects:', error);
    }
}
// Add to your script.js
async function initializeProjects() {
    try {
        const response = await fetch('/api/projects');
        if (!response.ok) throw new Error('Failed to fetch projects');
        const projects = await response.json();
        
        // Populate the dropdown
        const dropdownMenu = document.getElementById('project-dropdown-menu');
        dropdownMenu.innerHTML = ''; // Clear existing items
        
        projects.forEach(project => {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.className = 'dropdown-item';
            a.href = '#';
            a.textContent = project.project_name;
            a.dataset.projectId = project.project_id;
            a.onclick = function(e) {
                e.preventDefault();
                fetchProjectSessions(project.project_id);
                
                // Update active state
                document.querySelectorAll('#project-dropdown-menu .dropdown-item').forEach(item => {
                    item.classList.remove('active');
                    item.removeAttribute('aria-current');
                });
                this.classList.add('active');
                this.setAttribute('aria-current', 'page');
            };
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
            allA.onclick = function(e) {
                e.preventDefault();
                
                // Update active state
                document.querySelectorAll('#project-dropdown-menu .dropdown-item').forEach(item => {
                    item.classList.remove('active');
                    item.removeAttribute('aria-current');
                });
                this.classList.add('active');
                this.setAttribute('aria-current', 'page');
                
                // Fetch all sessions
                // Call fetchSession instead, which is your updated function
                fetchSession(); // Without projectId parameter to get all sessions
            };
            allLi.appendChild(allA);
            dropdownMenu.appendChild(allLi);
        }
        
        // Select first project by default
        if (projects.length > 0) {
            const firstProject = dropdownMenu.querySelector('.dropdown-item');
            firstProject.classList.add('active');
            firstProject.setAttribute('aria-current', 'page');
            fetchProjectSessions(projects[0].project_id);
        }
    } catch (error) {
        console.error('Error initializing projects:', error);
    }
}
// Fetch sessions for a specific project
async function fetchProjectSessions(projectId) {
    try {
        // Build URL with query parameter
        const url = `/api/sessions?project_id=${projectId}`;
        
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch sessions');
        sessions = await response.json();
        
        console.log('Fetched sessions for project:', projectId, sessions);
        
        // Update the session table/list
        updateSessionsList(sessions);
    } catch (error) {
        console.error('Error fetching project sessions:', error);
    }
}

// Update the sessions list in the UI
function updateSessionsList(sessions) {
    const sessionList = document.getElementById("session-list");
    const tbody = document.getElementById("sessions-table-body");
    
    // Clear existing content
    sessionList.innerHTML = "";
    tbody.innerHTML = "";
    
    if (sessions.length === 0) {
        // Display a message for empty sessions
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="text-center">No sessions available for this project</td>
            </tr>
        `;
        return;
    }
    
    // Populate sessions
    sessions.forEach(session => {
        // Sidebar entry
        const li = document.createElement("li");
        li.className = "nav-item";
        const linkClass = session.session_name === currentActiveSession ? "nav-link active-session" : "nav-link";
        li.innerHTML = `<a class="${linkClass}" href="#" onclick="visualizeSession('${session.session_id}')">${session.session_name}</a>`;
        sessionList.appendChild(li);

        // Table row
        const row = document.createElement("tr");
        let actionButton = `<button class="btn btn-sm btn-primary" onclick="visualizeSession('${session.session_id}')">View</button>`;
        
        row.innerHTML = `
            <td>${session.session_name}</td>
            <td>${session.project_name}</td>
            <td>${session.status}${session.label ? ': ' + session.label : ''}${session.keep === 0 ? ' (Discarded)' : ''}</td>
            <td>${actionButton}</td>
        `;
        tbody.appendChild(row);
    });
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
        // for (let session of sessions) {
        //     // If your backend now returns complete session data, you might not need this
        //     // Otherwise, keep it to fetch additional metadata
        //     const metadata = await fetchSessionMetadata(session.session_id);
        //     session.status = metadata.status || session.status;
        //     session.keep = metadata.keep || session.keep;
        //     session.data = [];
        //     session.bouts = [];
        // }
        // populateSessions();
    } catch (error) {
        console.error('Error fetching sessions:', error);
    }
}
// Fetch sessions from backend
async function fetchSessions() {
    try {
        const response = await fetch('/api/sessions');
        if (!response.ok) throw new Error('Failed to fetch sessions');
        sessions = await response.json();
        
        // No need to fetch additional metadata - the sessions API already provides all data
        // Remove this loop that's causing errors:
        /*
        for (let session of sessions) {
            const metadata = await fetchSessionMetadata(session.name);
            session.status = metadata.status;
            session.keep = metadata.keep;
            session.data = [];
            session.bouts = [];
        }
        */
        
        // Instead just initialize empty arrays for data and bouts
        sessions.forEach(session => {
            session.data = [];
            session.bouts = [];
        });
        
        // Update the UI with the sessions data
        updateSessionsList(sessions);
    } catch (error) {
        console.error('Error fetching sessions:', error);
    }
}
// Function to handle API call
function createNewProject(formData) {
    // Use fetch API to send data to your backend
    fetch('/api/project/upload', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(data => {
        // Handle successful response
        console.log('Success:', data);
        
        // Close the modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('createProjectModal'));
        modal.hide();
        
        // Refresh the project list or navigate to the new project
        // This depends on your application flow
        // For example: refreshProjectList();
    })
    .catch(error => {
        // Handle errors
        console.error('Error:', error);
        alert('Failed to create project. Please try again.');
    });
}

// Show create project form
function showCreateProjectForm() {
    const modal = new bootstrap.Modal(document.getElementById('createProjectModal'));
    modal.show();
}

// Update session metadata
async function updateSessionMetadata(session) {
    try {
        const response = await fetch(`/api/session/${session.session_id}/metadata`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                status: session.status,
                keep: session.keep,
                bouts: session.bouts
            })
        });
        if (!response.ok) throw new Error('Failed to update metadata');
    } catch (error) {
        console.error('Error updating metadata:', error);
    }
}

// Update loadSessionData to use sessionId
async function loadSessionData(sessionId) {
    try {
        const response = await fetch(`/api/session/${sessionId}`);
        if (!response.ok) throw new Error('Failed to fetch session data');
        const data = await response.json();
        return { bouts: data.bouts, data: data.data };
    } catch (error) {
        console.error('Error loading session data:', error);
        return { bouts: [], data: [] };
    }
}
function populateSessions() {
    const sessionList = document.getElementById("session-list");
    const tbody = document.getElementById("sessions-table-body");
    sessionList.innerHTML = "";
    tbody.innerHTML = "";
    
    sessions.forEach(session => {
        if (session.keep !== 0) {
            // Sidebar - Use session_name instead of name
            const li = document.createElement("li");
            li.className = "nav-item";
            // Use session_name for display and session_id for the function parameter
            const linkClass = session.session_name === currentActiveSession ? "nav-link active-session" : "nav-link";
            li.innerHTML = `<a class="${linkClass}" href="#" onclick="visualizeSession('${session.session_id}')">${session.session_name}</a>`;
            sessionList.appendChild(li);

            // Table - Update to use session_name and project_name
            const row = document.createElement("tr");
            let actionButton = `<button class="btn btn-sm btn-primary" onclick="visualizeSession('${session.session_id}')">View</button>`;
            
            row.innerHTML = `
                <td>${session.session_name}</td>
                <td>${session.project_name || ''}</td>
                <td>${session.status}${session.label ? ': ' + session.label : ''}${session.keep === 0 ? ' (Discarded)' : ''}</td>
                <td>${actionButton}</td>
            `;
            tbody.appendChild(row);
        }
    });
}

// Show table view
function showTableView() {
    document.getElementById("table-view").style.display = "flex";
    document.getElementById("visualization-view").style.display = "none";
}

// Show visualization view
async function visualizeSession(sessionId) {
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
    
    // Set the current session name/id
    currentSessionId = sessionId;
    currentSessionName = session.session_name;
    currentActiveSession = session.session_name;
    
    dragContext.currentSession = session;

    if (!session.data || session.data.length === 0) {
        const { bouts, data } = await loadSessionData(sessionId);
        session.bouts = bouts;
        session.data = data;
        if (!session.data || session.data.length === 0) {
            console.error('No valid data for session:', sessionName);
            return;
        }
    }
    const validData = session.data.every(d => 
        d.ns_since_reboot && 
        typeof d.x === 'number' && 
        typeof d.y === 'number' && 
        typeof d.z === 'number'
    );
    if (!validData) {
        console.error('Invalid data format:', session.data);
        return;
    }

    document.getElementById("table-view").style.display = "none";
    document.getElementById("visualization-view").style.display = "flex";

    if (session.status === "Initial") {
        session.status = "Visualized";
        await updateSessionMetadata(session);
        populateSessions();
    }

    const actionButtons = document.getElementById("action-buttons");
    actionButtons.innerHTML = "";

    if (isSplitting) {
        actionButtons.innerHTML += `
            <span id="split-btn-overlay" style="display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; background:rgba(224, 224, 224);">
                <i class="fa-solid fa-arrows-split-up-and-left" ></i>
            </span>
        `;
    } else {
        actionButtons.innerHTML += `
            <span id="split-btn-overlay" style="display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; background:rgba(224, 224, 224, 0);">
                <i class="fa-solid fa-arrows-split-up-and-left" ></i>
            </span>
        `;
    }

    actionButtons.innerHTML += `
        <span id="cancel-btn-overlay" style="display:none; align-items:center; justify-content:center; width:32px; height:32px; border-radius:50%; margin-right:4px; cursor:pointer;">
            <i id="cancel-btn" class="fa-solid fa-xmark" style="font-size:20px;"></i>
        </span>
        <span id="trash-btn-overlay" style="display:inline-flex; align-items:center; justify-content:center; width:32px; height:32px; border-radius:50%; background:rgba(224,224,224,0); cursor:pointer;">
            <i id="trash-btn" class="fa-solid fa-trash"></i>
        </span>
    `;

    let trashArmed = false;

    const trash_btn_overlay = document.getElementById('trash-btn-overlay');
    const trash_btn = document.getElementById('trash-btn');
    const cancel_btn_overlay = document.getElementById('cancel-btn-overlay');

    trash_btn_overlay.addEventListener('mouseenter', () => {
        trash_btn_overlay.style.background = 'rgba(0,0,0,0.1)';
    });
    trash_btn_overlay.addEventListener('mouseleave', () => {
        trash_btn_overlay.style.background = 'rgba(224,224,224,0)';
    });

    trash_btn_overlay.addEventListener('click', () => {
        if (!trashArmed) {
            // Arm the trashcan
            trashArmed = true;
            trash_btn.style.color = '#dc3545'; // Bootstrap red
            cancel_btn_overlay.style.display = 'inline-flex';
        } else {
            // Perform delete (placeholder)
            decideSession(currentSessionId, false);
            // Reset state
            trashArmed = false;
            trash_btn.style.color = '';
            cancel_btn_overlay.style.display = 'none';
        }
    });

    cancel_btn_overlay.addEventListener('click', () => {
        // Cancel delete
        trashArmed = false;
        trash_btn.style.color = '';
        cancel_btn_overlay.style.display = 'none';
    });

    cancel_btn_overlay.addEventListener('mouseenter', () => {
        cancel_btn_overlay.style.background = 'rgba(0,0,0,0.1)';
    });
    cancel_btn_overlay.addEventListener('mouseleave', () => {
        cancel_btn_overlay.style.background = 'rgba(224,224,224,0)';
    });

    const split_btn_overlay = document.getElementById('split-btn-overlay');
    split_btn_overlay.addEventListener('mouseenter', () => {
        split_btn_overlay.style.background = isSplitting ? 'rgba(224, 224, 224)' : 'rgba(0, 0, 0, 0.1)';
    });
    split_btn_overlay.addEventListener('mouseleave', () => {
        split_btn_overlay.style.background = isSplitting ? 'rgba(224, 224, 224)' : 'rgba(224, 224, 224, 0)';
    });
    split_btn_overlay.addEventListener('click', function() {
        toggleSplitMode();
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
        const overlays = session.bouts.map((bout, index) => createBoutOverlays(index, container));
        // Update all overlay positions
        function updateAllOverlayPositions() {
            console.log('Updating overlay positions');
            session.bouts.forEach((bout, index) => updateOverlayPositions(plotDiv, bout, index));
        }
        updateAllOverlayPositions();

        // Handle plot click for splitting
        plotDiv.on('plotly_click', function(data) {
            if (isSplitting) {
                const splitPoint = data.points[0].x;
                if (!splitPoints.includes(splitPoint)) {
                    splitPoints.push(splitPoint);
                    visualizeSession(sessionName); // Refresh plot to show new split point marker
                }
            }
        });
        // Update overlays on plot relayout (pan, zoom, etc.)
        plotDiv.on('plotly_relayout', () => {
            console.log('Plotly relayout event');
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
    
    // Add double-click event to remove the bout
    dragOverlay.addEventListener('dblclick', function() {
        const boutIndex = parseInt(dragOverlay.dataset.boutIndex);
        if (dragContext.currentSession && dragContext.currentSession.bouts) {
            dragContext.currentSession.bouts.splice(boutIndex, 1);
            console.log(`Removed bout ${boutIndex}`);
            updateSessionMetadata(dragContext.currentSession);
            visualizeSession(currentSessionId); // Refresh the plot
        }
    });
    // Element-specific mouse events for dragging
    dragOverlay.addEventListener('mousedown', function(e) {
        isDragging = true;
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
            saveBoutChanges();
            
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
                dragContext.currentSession.bouts[boutIndex][0] = x0;
                dragContext.currentSession.bouts[boutIndex][1] = x1;
                console.log(`Updated bout ${boutIndex} to [${x0}, ${x1}]`);
            } else {
                console.error(`Bout index ${boutIndex} not found in session ${dragContext.currentSession.name}`);
            }
        } else {
            console.error("No current session in drag context");
        }
    }
    
    function saveBoutChanges() {
        if (sessions && sessions.length > 0) {
            console.log(sessions);
            console.log(currentSessionId);
            const session = sessions.find(s => s.session_id == currentSessionId);
            if (session) {
                console.log(`Saving bout changes for session ${session.session_name} (ID: ${currentSessionId})`);
                updateSessionMetadata(session);
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

    // Get axis object from Plotly layout
    const xAxis = plotDiv._fullLayout.xaxis;
    const yAxis = plotDiv._fullLayout.yaxis;
    
    // Convert data coordinates to pixel positions
    const pixelX0 = xAxis._length * (bout[0] - xAxis.range[0]) / (xAxis.range[1] - xAxis.range[0]) + xAxis._offset;
    const pixelX1 = xAxis._length * (bout[1] - xAxis.range[0]) / (xAxis.range[1] - xAxis.range[0]) + xAxis._offset;
    
    // Get the overlay elements
    const dragOverlay = document.getElementById(`drag-overlay-${index}`);
    const leftOverlay = document.getElementById(`left-overlay-${index}`);
    const rightOverlay = document.getElementById(`right-overlay-${index}`);
    
    if (!dragOverlay || !leftOverlay || !rightOverlay) return;
    
    // Set handle size
    const handleWidth = 10;
    const handleHeight = yAxis._length;
    
    // Set main overlay position and size
    dragOverlay.style.position = 'absolute';
    dragOverlay.style.left = `${pixelX0}px`;
    dragOverlay.style.width = `${pixelX1 - pixelX0}px`;
    dragOverlay.style.top = `${yAxis._offset}px`;
    dragOverlay.style.height = `${handleHeight}px`;
    dragOverlay.style.backgroundColor = 'rgba(127, 249, 61, 0.2)';
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
// Toggle splitting mode
function toggleSplitMode() {
    isSplitting = !isSplitting;
    const split_btn_overlay = document.getElementById('split-btn-overlay');
    split_btn_overlay.style.background = isSplitting ? 'rgba(224, 224, 224)' : 'rgba(0, 0, 0, 0)';
}

async function decideSession(sessionId, keep) {
    const session = sessions.find(s => s.session_id === sessionId);
    if (!session) return;
    session.status = "Decision Made";
    session.keep = keep;
    await updateSessionMetadata(session);
    populateSessions();
    showTableView(); // Return to table view after split
}

async function splitSession() {
    console.log('Splitting session:', currentSessionId);
    if (splitPoints.length === 0) {
        alert('No split points selected');
        return;
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
        // Clear split points and refresh sessions
        splitPoints = [];
        isSplitting = false;
        await fetchSessions();
        showTableView();
    } catch (error) {
        console.error('Error splitting session:', error);
        alert('Failed to split session: ' + error.message);
    }
}

function createNewBout() {
    // Create new bout with values within min and max timestamps
    console.log(minTimestamp, maxTimestamp);
    const middleTimestamp = (minTimestamp + maxTimestamp) / 2;
    const newBout = [middleTimestamp - (240*1e9), middleTimestamp + (240*1e9)];
    // Add new bout to the session
    if (dragContext.currentSession && dragContext.currentSession.bouts) {
        dragContext.currentSession.bouts.push(newBout);
        console.log(`Created new bout: [${newBout[0]}, ${newBout[1]}]`);
        // Update the session metadata
        updateSessionMetadata(dragContext.currentSession);
        // Refresh the visualization
        visualizeSession(currentSessionId);
    } else {
        console.error('No current session in drag context');
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
let currentSessionName = null;
let currentSessionId = null;
let currentActiveSession = null;
let isSplitting = false;
let splitPoints = [];
let minTimestamp = null;
let maxTimestamp = null;

// Make functions available globally for inline event handlers
window.visualizeSession = visualizeSession;
window.showTableView = showTableView;
window.decideSession = decideSession;
window.toggleSplitMode = toggleSplitMode;
window.splitSession = splitSession;
window.createNewBout = createNewBout;
window.showCreateProjectForm = showCreateProjectForm;
window.createNewProject = createNewProject;

// fetchSessions();
fetchProjects();
initializeProjects();
eventListeners.addEventListeners();