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
}
export default ProjectController;