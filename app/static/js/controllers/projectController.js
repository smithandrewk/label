import ProjectService from '../services/projectService.js';
import { generateDefaultColor } from '../helpers.js';
import ProjectAPI from '../api/projectAPI.js';

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
            console.log('Labeling deleted successfully:', result);
            await ProjectController.fetchAndDisplayLabelings(window.currentProjectId);
        } catch (error) {
            console.error('Error deleting labeling:', error);
            alert('Failed to delete labeling: ' + error.message);
        }
    }

    /**
     * Fetch and display labelings for a project
     * @param {number} projectId - The project ID
     */
    static async fetchAndDisplayLabelings(projectId) {
        try {
            window.labelings = await ProjectAPI.fetchLabelings(projectId);
            const labelingsList = document.getElementById('available-labelings-list');
            
            // Reset current labeling header when refreshing the list
            if (window.updateCurrentLabelingHeader) {
                window.updateCurrentLabelingHeader();
            }
            
            // Clear existing content except the plus icon
            const plusIcon = labelingsList.querySelector('.fa-plus');
            labelingsList.innerHTML = '';
            if (plusIcon) {
                labelingsList.appendChild(plusIcon);
            }
            
            console.log('Parsed labelings:', window.labelings);
            console.log(typeof(window.labelings))
            
            // Display each labeling
            if (window.labelings && window.labelings.length > 0) {
                window.labelings.forEach((labeling, index) => {
                    console.log(typeof(labeling))
                    console.log('Labeling item:', labeling.name);
                    const currentColor = labeling.color || generateDefaultColor(index);
                    const labelingName = labeling.name;
                    const labelingItem = document.createElement('div');
                    labelingItem.className = 'labeling-item d-flex justify-content-between align-items-center py-1';

                    labelingItem.innerHTML = `
                        <div class="d-flex align-items-center">
                            <div class="color-picker-container me-2" style="position: relative;">
                                <div class="color-circle" style="width: 20px; height: 20px; border-radius: 50%; background-color: ${currentColor}; border: 1px solid #ccc; cursor: pointer;" onclick="openColorPicker('${labelingName.replace(/'/g, "\\'")}', this)"></div>
                                <input type="color" class="color-picker" value="${currentColor}" style="position: absolute; opacity: 0; width: 20px; height: 20px; cursor: pointer;" onchange="updateLabelingColor('${labelingName.replace(/'/g, "\\'")}', this.value, this)">
                            </div>
                            <span>${labelingName}</span>
                        </div>
                        <div class="labeling-actions d-flex gap-1">
                            <button class="btn btn-sm btn-outline-secondary" onclick="editLabeling('${labelingName.replace(/'/g, "\\'")}'); return false;" title="Edit Labeling">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-info" onclick="duplicateLabeling('${labelingName.replace(/'/g, "\\'")}'); return false;" title="Duplicate Labeling">
                                <i class="bi bi-files"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="ProjectController.deleteLabeling('${labelingName.replace(/'/g, "\\'")}'); return false;" title="Delete Labeling">
                                <i class="bi bi-trash"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-primary" onclick="selectLabeling('${labelingName.replace(/'/g, "\\'")}'); return false;">
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

    /**
     * Create a new labeling with user input and update UI
     */
    static async createNewLabeling() {
        // Show a prompt to get the new labeling name
        const labelingName = prompt('Enter a name for the new labeling:');
        
        if (labelingName && labelingName.trim()) {
            try {
                const { result, updatedLabelings } = await ProjectService.createLabeling(window.currentProjectId, labelingName.trim());
                console.log('New labeling created:', result);
                
                // Update global labelings array
                window.labelings = updatedLabelings;
                
                // Refresh the labelings list to show the new labeling
                await ProjectController.fetchAndDisplayLabelings(window.currentProjectId);
                
                // Select the new labeling immediately
                if (window.selectLabeling) {
                    window.selectLabeling(labelingName.trim());
                }
                
            } catch (error) {
                console.error('Error creating new labeling:', error);
                alert('Failed to create new labeling. Please try again.');
            }
        }
    }
}
export default ProjectController;