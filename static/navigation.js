/**
 * Unified Navigation System
 * Handles navigation between sessions and participants views within a unified sidebar
 */

// Navigation state
let currentView = 'sessions'; // 'sessions' or 'participants'

// Initialize navigation
function initializeNavigation() {
    setupNavigationEventListeners();
    
    // Determine current view based on URL
    if (window.location.pathname === '/participants') {
        currentView = 'participants';
        updateNavigationState();
    } else {
        currentView = 'sessions';
        updateNavigationState();
    }
}

// Setup navigation event listeners
function setupNavigationEventListeners() {
    const sessionsNavBtn = document.getElementById('sessions-nav-btn');
    const participantsNavBtn = document.getElementById('participants-nav-btn');
    
    if (sessionsNavBtn) {
        sessionsNavBtn.addEventListener('click', () => switchToSessionsView());
        
        // Hover effects
        sessionsNavBtn.addEventListener('mouseenter', () => {
            if (!sessionsNavBtn.classList.contains('active')) {
                sessionsNavBtn.style.background = 'rgba(13, 110, 253, 0.1)';
            }
        });
        
        sessionsNavBtn.addEventListener('mouseleave', () => {
            if (!sessionsNavBtn.classList.contains('active')) {
                sessionsNavBtn.style.background = 'rgba(224, 224, 224, 0.3)';
            }
        });
    }
    
    if (participantsNavBtn) {
        participantsNavBtn.addEventListener('click', () => switchToParticipantsView());
        
        // Hover effects
        participantsNavBtn.addEventListener('mouseenter', () => {
            if (!participantsNavBtn.classList.contains('active')) {
                participantsNavBtn.style.background = 'rgba(13, 110, 253, 0.1)';
            }
        });
        
        participantsNavBtn.addEventListener('mouseleave', () => {
            if (!participantsNavBtn.classList.contains('active')) {
                participantsNavBtn.style.background = 'rgba(224, 224, 224, 0.3)';
            }
        });
    }
}

// Switch to sessions view
function switchToSessionsView() {
    if (currentView === 'sessions') return;
    
    currentView = 'sessions';
    
    // Navigate to sessions page
    window.location.href = '/';
}

// Switch to participants view
function switchToParticipantsView() {
    if (currentView === 'participants') return;
    
    currentView = 'participants';
    
    // Navigate to participants page
    window.location.href = '/participants';
}

// Update navigation state (visual indicators)
function updateNavigationState() {
    const sessionsNavBtn = document.getElementById('sessions-nav-btn');
    const participantsNavBtn = document.getElementById('participants-nav-btn');
    
    if (!sessionsNavBtn || !participantsNavBtn) return;
    
    // Reset both buttons
    sessionsNavBtn.classList.remove('active');
    participantsNavBtn.classList.remove('active');
    
    sessionsNavBtn.style.background = 'rgba(224, 224, 224, 0.3)';
    sessionsNavBtn.style.color = '#666';
    
    participantsNavBtn.style.background = 'rgba(224, 224, 224, 0.3)';
    participantsNavBtn.style.color = '#666';
    
    // Activate current view
    if (currentView === 'sessions') {
        sessionsNavBtn.classList.add('active');
        sessionsNavBtn.style.background = '#0d6efd';
        sessionsNavBtn.style.color = 'white';
        
        // Show sessions sidebar content
        showSessionsSidebar();
    } else if (currentView === 'participants') {
        participantsNavBtn.classList.add('active');
        participantsNavBtn.style.background = '#0d6efd';
        participantsNavBtn.style.color = 'white';
        
        // Show participants sidebar content
        showParticipantsSidebar();
    }
}

// Show sessions sidebar content
function showSessionsSidebar() {
    const sessionsContent = document.getElementById('sessions-sidebar-content');
    const participantsContent = document.getElementById('participants-sidebar-content');
    
    if (sessionsContent) {
        sessionsContent.style.display = 'block';
    }
    
    if (participantsContent) {
        participantsContent.style.display = 'none';
    }
}

// Show participants sidebar content
function showParticipantsSidebar() {
    const sessionsContent = document.getElementById('sessions-sidebar-content');
    const participantsContent = document.getElementById('participants-sidebar-content');
    
    if (sessionsContent) {
        sessionsContent.style.display = 'none';
    }
    
    if (participantsContent) {
        participantsContent.style.display = 'block';
    }
}

// Update participants sidebar list
function updateParticipantsSidebarList(participants) {
    const sidebarList = document.getElementById('participants-sidebar-list');
    if (!sidebarList) return;
    
    sidebarList.innerHTML = '';
    
    if (participants.length === 0) {
        const li = document.createElement('li');
        li.className = 'nav-item';
        li.innerHTML = '<span class="nav-link text-muted">No participants</span>';
        sidebarList.appendChild(li);
        return;
    }
    
    participants.forEach(participant => {
        const li = document.createElement('li');
        li.className = 'nav-item';
        
        const link = document.createElement('a');
        link.className = 'nav-link';
        link.href = '#';
        link.style.cursor = 'pointer';
        link.textContent = participant.participant_code;
        link.title = `${participant.first_name || ''} ${participant.last_name || ''}`.trim();
        
        // Add click handler to scroll to participant card
        link.addEventListener('click', (e) => {
            e.preventDefault();
            scrollToParticipant(participant.participant_id);
        });
        
        li.appendChild(link);
        sidebarList.appendChild(li);
    });
}

// Scroll to specific participant card
function scrollToParticipant(participantId) {
    const participantCard = document.querySelector(`[data-participant-id="${participantId}"]`);
    if (participantCard) {
        participantCard.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center' 
        });
        
        // Highlight briefly
        participantCard.style.boxShadow = '0 0 20px rgba(13, 110, 253, 0.5)';
        setTimeout(() => {
            participantCard.style.boxShadow = '';
        }, 2000);
    }
}

// Update sessions sidebar list with project filtering support
function updateSessionsSidebarList(sessions, currentProjectId = null) {
    const sidebarList = document.getElementById('session-list');
    if (!sidebarList) return;
    
    sidebarList.innerHTML = '';
    
    if (sessions.length === 0) {
        const li = document.createElement('li');
        li.className = 'nav-item';
        li.innerHTML = '<span class="nav-link text-muted">No sessions</span>';
        sidebarList.appendChild(li);
        return;
    }
    
    // Filter sessions if project is selected
    const filteredSessions = currentProjectId 
        ? sessions.filter(session => session.project_id == currentProjectId)
        : sessions;
    
    // Group sessions by project if showing all projects
    if (!currentProjectId) {
        const projectGroups = {};
        filteredSessions.forEach(session => {
            const projectName = session.project_name || 'Unknown Project';
            if (!projectGroups[projectName]) {
                projectGroups[projectName] = [];
            }
            projectGroups[projectName].push(session);
        });
        
        Object.keys(projectGroups).forEach(projectName => {
            // Add project header
            const headerLi = document.createElement('li');
            headerLi.className = 'nav-item';
            headerLi.innerHTML = `<div class="text-muted small mb-1 px-2 fw-bold">${projectName}</div>`;
            sidebarList.appendChild(headerLi);
            
            // Add sessions for this project
            projectGroups[projectName].forEach(session => {
                if (session.keep == 0) return; // Skip discarded sessions
                
                const li = document.createElement('li');
                li.className = 'nav-item';
                const linkClass = session.session_name === window.currentActiveSession ? "nav-link active-session" : "nav-link";
                li.innerHTML = `<a class="${linkClass}" href="#" onclick="visualizeSession('${session.session_id}')" style="padding-left: 1rem;">${session.session_name}</a>`;
                sidebarList.appendChild(li);
            });
        });
    } else {
        // Show sessions for selected project only
        filteredSessions.forEach(session => {
            if (session.keep == 0) return; // Skip discarded sessions
            
            const li = document.createElement('li');
            li.className = 'nav-item';
            const linkClass = session.session_name === window.currentActiveSession ? "nav-link active-session" : "nav-link";
            li.innerHTML = `<a class="${linkClass}" href="#" onclick="visualizeSession('${session.session_id}')">${session.session_name}</a>`;
            sidebarList.appendChild(li);
        });
    }
}

// Export functions for use in other files
window.initializeNavigation = initializeNavigation;
window.updateParticipantsSidebarList = updateParticipantsSidebarList;
window.updateSessionsSidebarList = updateSessionsSidebarList;
window.updateNavigationState = updateNavigationState;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeNavigation);
