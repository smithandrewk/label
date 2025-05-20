import * as eventListeners from './eventListeners.js';

// Fetch sessions from backend
async function fetchSessions() {
    try {
        const response = await fetch('/api/sessions');
        if (!response.ok) throw new Error('Failed to fetch sessions');
        sessions = await response.json();
        for (let session of sessions) {
            const metadata = await fetchSessionMetadata(session.name);
            session.status = metadata.status;
            session.keep = metadata.keep;
            session.data = [];
            session.bouts = [];
        }
        populateSessions();
    } catch (error) {
        console.error('Error fetching sessions:', error);
    }
}

// Fetch session metadata
async function fetchSessionMetadata(sessionName) {
    try {
        const response = await fetch(`/api/session/${sessionName}/metadata`);
        if (!response.ok) throw new Error('Failed to fetch metadata');
        return await response.json();
    } catch (error) {
        console.error('Error fetching metadata:', error);
        return { status: 'Initial', keep: null, bouts: [] };
    }
}

// Update session metadata
async function updateSessionMetadata(session) {
    try {
        const response = await fetch(`/api/session/${session.name}/metadata`, {
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

// Modify loadSessionData to return an object
async function loadSessionData(sessionName) {
    try {
        const response = await fetch(`/api/session/${sessionName}`);
        if (!response.ok) throw new Error('Failed to fetch session data');
        const data = await response.json();
        return { bouts: data.bouts, data: data.data }; // Return as an object
    } catch (error) {
        console.error('Error loading session data:', error);
        return { bouts: [], data: [] }; // Return default values
    }
}

// Populate sidebar and table
function populateSessions() {
    const sessionList = document.getElementById("session-list");
    const tbody = document.getElementById("sessions-table-body");
    sessionList.innerHTML = "";
    tbody.innerHTML = "";
    sessions.forEach(session => {
        if (session.keep !== 0) {
            //Sidebar
            const li = document.createElement("li");
            li.className = "nav-item";
            const linkClass = session.name === currentActiveSession ? "nav-link active-session" : "nav-link";
            li.innerHTML = `<a class="${linkClass}" href="#" onclick="visualizeSession('${session.name}')">${session.name}</a>`;
            sessionList.appendChild(li);

            // Table
            const row = document.createElement("tr");
            let actionButton = "";
            if (session.status === "Initial") {
                actionButton = `<button class="btn btn-primary btn-sm" onclick="visualizeSession('${session.name}')">Visualize</button>`;
            } else if (session.status === "Visualized") {
                actionButton = `<button class="btn btn-primary btn-sm" onclick="visualizeSession('${session.name}')">Visualize</button>` +
                            `<button class="btn btn-success btn-sm me-1" onclick="decideSession('${session.name}', true)">Keep</button>` +
                            `<button class="btn btn-danger btn-sm" onclick="decideSession('${session.name}', false)">Discard</button>`;
            }
            row.innerHTML = `
                <td>${session.name}</td>
                <td>${session.file}</td>
                <td>${session.status}${session.label ? ': ' + session.label : ''}${session.keep === false ? ' (Discarded)' : ''}</td>
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
async function visualizeSession(sessionName) {
    // Clean up previous event handlers
    activeHandlers.forEach(h => {
        document.removeEventListener(h.type, h.handler);
    });
    activeHandlers.length = 0; // Clear the array
    // Also clean up any stray elements
    document.querySelectorAll('.drag-overlay, .left-overlay, .right-overlay').forEach(el => el.remove());
    
    // Set the current session name at the beginning
    currentSessionName = sessionName;
    currentActiveSession = sessionName;
    
    const session = sessions.find(s => s.name === sessionName);
    if (!session) {
        console.error('Session not found:', sessionName);
        return;
    }
    dragContext.currentSession = session;

    if (!session.data || session.data.length === 0) {
        const { bouts, data } = await loadSessionData(sessionName);
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

    const detailsDiv = document.getElementById("session-details");
    detailsDiv.innerHTML = `
        <p><strong>Session:</strong> ${session.name}</p>
        <p><strong>File:</strong> ${session.file}</p>
        <p><strong>Status:</strong> ${session.status}</p>
        ${session.keep === false ? '<p><strong>Decision:</strong> Discarded</p>' : ''}
    `;

    const actionButtons = document.getElementById("action-buttons");
    actionButtons.innerHTML = "";
    if (session.status === "Visualized") {
        actionButtons.innerHTML = `
            <button class="btn btn-success btn-sm me-1" onclick="decideSession('${session.name}', true)">Keep</button>
            <button class="btn btn-danger btn-sm" onclick="decideSession('${session.name}', false)">Discard</button>
        `;
    }

    if (!isSplitting) {
        actionButtons.innerHTML += `<button class="btn btn-warning btn-sm" onclick="toggleSplitMode('${session.name}')">Split</button>`;
    } else {
        actionButtons.innerHTML += `<button class="btn btn-info btn-sm" onclick="toggleSplitMode('${session.name}')">Click Plot to Split</button>`;
    }

    actionButtons.innerHTML += `<button class="btn btn-info btn-sm" onclick="splitSession('${session.name}')">SEND SPLIT</button>`;


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

    const minTimestamp = Math.min(...timestamps);
    const maxTimestamp = Math.max(...timestamps);

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
    
    // Helper function to save changes
    function saveBoutChanges() {
        if (sessions && sessions.length > 0) {
            const session = sessions.find(s => s.name === currentSessionName);
            if (session) {
                console.log(`Saving bout changes for session ${currentSessionName}`);
                updateSessionMetadata(session);
            } else {
                console.error(`Session not found for saving: ${currentSessionName}`);
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
function toggleSplitMode(sessionName) {
    isSplitting = !isSplitting;
    const splitButton = document.querySelector(`#action-buttons button[onclick="toggleSplitMode('${sessionName}')"]`);
    splitButton.textContent = isSplitting ? 'Click Plot to Split' : 'Split';
    splitButton.classList.toggle('btn-warning', !isSplitting);
    splitButton.classList.toggle('btn-info', isSplitting);
}

// Decide to keep or discard
async function decideSession(sessionName, keep) {
    const session = sessions.find(s => s.name === sessionName);
    if (!session) return;
    session.status = "Decision Made";
    session.keep = keep;
    await updateSessionMetadata(session);
    populateSessions();
    showTableView(); // Return to table view after split
    // visualizeSession(sessionName);
}

async function splitSession(sessionName) {
    if (splitPoints.length === 0) {
        alert('No split points selected');
        return;
    }
    try {
        const response = await fetch(`/api/session/${sessionName}/split`, {
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

// Global drag context
const dragContext = {
    currentSession: null  // Will store the session being modified
};
// Add at the top of your file
const activeHandlers = [];

// Create global reference to these handlers so we can remove them
let documentMouseMoveHandler;
let documentMouseUpHandler;
let sessions = [];
let currentSessionName = null;
let currentActiveSession = null;
let isSplitting = false;
let splitPoints = [];

// Make functions available globally for inline event handlers
window.visualizeSession = visualizeSession;
window.showTableView = showTableView;
window.decideSession = decideSession;
window.toggleSplitMode = toggleSplitMode;
window.splitSession = splitSession;

fetchSessions();
eventListeners.addEventListeners();