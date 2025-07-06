import ProjectAPI from './api/projectAPI.js';
import './ui/overlayManager.js'; // Import overlay manager to make it available globally

// Global state and functions used across pages
window.projects = [];
window.sessions = [];

window.currentProjectId = null;
window.currentSessionId = null;
window.currentActiveSession = null;
window.currentLabelingName = 'No Labeling';
window.currentLabelingJSON = null;

window.labelingsList = null;
window.labelings = null;

window.isSplitting = false;
window.splitPoints = [];

window.minTimestamp = null;
window.maxTimestamp = null;

window.dragContext = { currentSession: null };
window.activeHandlers = [];

export async function initializeApp() {
    console.log("Initializing application...");
    try {
        await loadCoreData();
    } catch (error) {
        console.error("Error initializing application:", error);
    }
}

async function loadCoreData() {
    console.log("📊 Loading core application data...");
    try {
        // Load projects first (most important for navigation)
        window.projects = await ProjectAPI.fetchProjects();
        console.log(`Loaded ${window.projects.length} projects`);
    } catch (error) {
        console.error("Error loading core data:", error);
    }
}
document.addEventListener('DOMContentLoaded', initializeApp);