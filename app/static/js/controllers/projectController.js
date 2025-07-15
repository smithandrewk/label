import ProjectService from '../services/projectService.js';

export class ProjectController {
    /**
     * Fetch project sessions and labelings, then update global state and UI
     * @param {number} projectId - The project ID
     */
    static async fetchProjectSessions(projectId) {
        try {
            const projectData = await ProjectService.fetchProjectSessionsAndLabelings(projectId);
            
            // Update global variables
            window.sessions = projectData.sessions;
            window.labelings = projectData.labelings;
            window.currentLabelingJSON = projectData.currentLabelingJSON;
            window.currentLabelingName = projectData.currentLabelingName;
            
            // Update the session table/list
            if (window.updateSessionsList) {
                window.updateSessionsList();
            }
        } catch (error) {
            console.error('Error fetching project sessions:', error);
        }
    }

    /**
     * Fetch sessions (without labelings), then update global state and UI
     * @param {number} projectId - The project ID (optional)
     */
    static async fetchSessions(projectId = null) {
        try {
            window.sessions = await ProjectService.fetchSessions(projectId);
            
            // Update the session table/list
            if (window.updateSessionsList) {
                window.updateSessionsList();
            }
            
            // Update unified sidebar if function is available
            if (window.updateSessionsSidebarList) {
                window.updateSessionsSidebarList(window.sessions, projectId);
            }
            
        } catch (error) {
            console.error('Error fetching sessions:', error);
        }
    }

    /**
     * Delete a labeling with user confirmation and state management
     * @param {string} labelingName - The name of the labeling to delete
     */
    static async deleteLabeling(labelingName) {
        // Show confirmation dialog
        const confirmed = confirm(`Are you sure you want to delete the labeling "${labelingName}"? This action will mark it as deleted but can be recovered by an administrator.`);
        if (!confirmed) {
            return;
        }
        
        try {
            const { result, shouldUpdateCurrentLabeling, newCurrentLabelingName, updatedLabelings } = 
                await ProjectService.deleteLabeling(window.currentProjectId, labelingName, window.currentLabelingName);
            
            // Update global labelings array
            window.labelings = updatedLabelings;
            
            // Update current labeling selection if needed
            if (shouldUpdateCurrentLabeling) {
                window.currentLabelingName = newCurrentLabelingName;
                window.currentLabelingJSON = null;
                if (window.updateCurrentLabelingHeader) {
                    window.updateCurrentLabelingHeader(newCurrentLabelingName);
                }
            }
            
            // Refresh the labelings display
            if (window.fetchAndDisplayLabelings) {
                console.log('Labeling deleted successfully:', result);
                await window.fetchAndDisplayLabelings(window.currentProjectId);
            }
        } catch (error) {
            console.error('Error deleting labeling:', error);
            alert('Failed to delete labeling: ' + error.message);
        }
    }
}
export default ProjectController;