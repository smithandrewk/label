import ProjectService from '../services/projectService.js';
import { generateDefaultColor } from '../helpers.js';
import ProjectAPI from '../api/projectAPI.js';
import { 
    updateCurrentProjectPill
} from '../ui/uiUtils.js';
import SessionService from '../services/sessionService.js';

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
            
            // Clear existing content except the control buttons
            const controlButtons = labelingsList.querySelector('.d-flex');
            labelingsList.innerHTML = '';
            if (controlButtons) {
                labelingsList.appendChild(controlButtons);
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
                            <button class="btn btn-sm btn-outline-success" onclick="exportLabelingJSON('${labelingName.replace(/'/g, "\\'")}'); return false;" title="Export Labeling">
                                <i class="bi bi-download"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-secondary" onclick="editLabeling('${labelingName.replace(/'/g, "\\'")}'); return false;" title="Edit Labeling">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-info" onclick="duplicateLabeling('${labelingName.replace(/'/g, "\\'")}'); return false;" title="Duplicate Labeling">
                                <i class="bi bi-files"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteLabeling('${labelingName.replace(/'/g, "\\'")}'); return false;" title="Delete Labeling">
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

    /**
     * Create a new project with form data and handle UI updates
     * @param {FormData|Object} formData - The form data for project creation
     */
    static createNewProject(formData) {
        // Hide modal and reset form
        if (window.hideModal) {
            window.hideModal('createProjectModal');
        }

        // Start project creation in background
        ProjectService.createProject(formData)
            .then(result => {
                console.log("Project created:", result);
            })
            .catch(error => {
                console.error('Error creating project:', error);
            });
            
        console.log('Project creation started in background:', formData);
        
        // Refresh projects list if we're on the projects page
        setTimeout(() => {
            console.log('Refreshing projects list after creation');
            if (ProjectController.initializeProjects) {
                ProjectController.initializeProjects();
            }
            location.reload(); // Refresh the page to show updated projects
        }, 1000);
        
        if (window.resetForm) {
            window.resetForm('create-project-form');
        }
    }

    /**
     * Create a bulk upload request to the server
     * @param {string} bulkUploadFolderPath - The folder path for the bulk upload
     */
    static createBulkUpload(bulkUploadFolderPath) {
        // Show progress UI
        const formElement = document.getElementById('bulk-upload-form');
        const progressElement = document.getElementById('bulk-upload-progress');
        formElement.style.display = 'none';
        progressElement.style.display = 'block';
        
        
        // Use fetch API to send data to your backend
        const formData = new FormData();
        formData.append('bulkUploadFolderPath', bulkUploadFolderPath);
        
        fetch('/api/projects/bulk-upload', {
            method: 'POST',
            body: formData
        });
        // Close the modal after starting the upload
        const bulkUploadModal = document.getElementById('bulkUploadModal');
        if (bulkUploadModal) {
            const modal = bootstrap.Modal.getInstance(bulkUploadModal);
            if (modal) {
                modal.hide();
            }
        }
        // Reload the projects list to reflect the new uploads and refresh page
        ProjectController.initializeProjects().then(() => {
            location.reload(); // Refresh the page to show updated projects
        }).catch(error => {
            console.error('Error during bulk upload:', error);
            alert('Failed to start bulk upload: ' + error.message);
        });
    }

    /**
     * Initialize projects dropdown and handle project selection state
     */
    static async initializeProjects() {
        console.log('Initializing projects...');
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
                    window.currentProjectId = project.project_id; // Store selected project ID
                    
                    // Navigate to sessions page with the selected project
                    window.location.href = `/sessions?project_id=${project.project_id}`;
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

            // Check sessionStorage for preserved project selection if currentProjectId is not set
            if (!window.currentProjectId) {
                const storedProjectId = sessionStorage.getItem('currentProjectId');
                if (storedProjectId) {
                    window.currentProjectId = parseInt(storedProjectId);
                }
            }
            
            // Select first project by default ONLY if no project is currently selected
            if (projects.length > 0 && !window.currentProjectId) {
                const firstProject = dropdownMenu.querySelector('.dropdown-item');
                firstProject.classList.add('active');
                firstProject.setAttribute('aria-current', 'page');
                window.currentProjectId = projects[0].project_id;
                
                // Update current project pill
                if (window.updateCurrentProjectPill) {
                    window.updateCurrentProjectPill(projects[0].project_name);
                }
                
                ProjectController.fetchProjectSessions(projects[0].project_id);
            } else if (window.currentProjectId) {
                // If we have a current project, make sure it's marked as active in the dropdown
                const currentProjectItem = dropdownMenu.querySelector(`[data-project-id="${window.currentProjectId}"]`);
                if (currentProjectItem) {
                    currentProjectItem.classList.add('active');
                    currentProjectItem.setAttribute('aria-current', 'page');
                    
                    // Find the project data to update the pill
                    const currentProject = projects.find(p => p.project_id === window.currentProjectId);
                    if (currentProject) {
                        if (window.updateCurrentProjectPill) {
                            window.updateCurrentProjectPill(currentProject.project_name);
                        }
                        
                        // Fetch sessions for the restored project
                        ProjectController.fetchProjectSessions(window.currentProjectId);
                    }
                }
            }
        } catch (error) {
            console.error('Error initializing projects:', error);
        }
    }

    /**
     * Duplicate a labeling with all its bouts
     * @param {string} labelingName - The name of the labeling to duplicate
     */
    static async duplicateLabeling(labelingName) {
        // Show confirmation dialog and get new name
        const confirmed = confirm(`Are you sure you want to duplicate the labeling "${labelingName}"?`);
        if (!confirmed) {
            return;
        }
        
        const newName = prompt(`Enter a name for the duplicate labeling:`, `${labelingName} Copy`);
        
        if (newName && newName.trim() && newName.trim() !== labelingName) {
            try {
                // Use the service method that handles session refresh
                const { result, updatedLabelings, refreshedSessionData } = await ProjectService.duplicateLabelingWithSessionRefresh(
                    window.currentProjectId, 
                    labelingName, 
                    newName.trim(), 
                    window.currentSessionId
                );
                
                console.log('Labeling duplicated successfully:', result);
                
                // Update global labelings array
                window.labelings = updatedLabelings;
                
                // Use overlay manager to handle session data refresh
                if (refreshedSessionData && window.OverlayManager) {
                    window.OverlayManager.handleSessionDataRefresh({
                        refreshedSessionData,
                        dragContext: window.dragContext,
                        currentLabelingName: window.currentLabelingName,
                        currentSessionId: window.currentSessionId
                    });
                }
                
                // Refresh the labelings list to show the new duplicate
                await ProjectController.fetchAndDisplayLabelings(window.currentProjectId);
                
                // Select the new labeling immediately (this will now show the duplicated bouts)
                if (window.selectLabeling) {
                    window.selectLabeling(newName.trim());
                }
                
                alert(`Labeling "${labelingName}" duplicated as "${newName.trim()}" successfully! All bouts have been copied.`);
                
            } catch (error) {
                console.error('Error duplicating labeling:', error);
                alert('Failed to duplicate labeling: ' + error.message);
            }
        } else if (newName && newName.trim() === labelingName) {
            alert('New name must be different from the original name.');
        }
    }

    // Delete project function
    static async deleteProject(projectId, projectName) {
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
            await ProjectController.initializeProjects();
            
            // If the deleted project was currently selected, clear the session view
            if (currentProjectId === projectId) {
                currentProjectId = null;
                document.getElementById('sessions-table-body').innerHTML = '';
                window.showTableView(); // Go back to table view if in visualization
            }
            
            updateCurrentProjectPill();
            
        } catch (error) {
            console.error('Error deleting project:', error);
            alert(`Failed to delete project: ${error.message}`);
        }
    }
    /**
     * Edit (rename) a labeling
     * @param {string} labelingName - The current name of the labeling to rename
     */
    static async editLabeling(labelingName) {
        const newName = prompt(`Enter a new name for labeling "${labelingName}":`, labelingName);
        
        if (newName && newName.trim() && newName.trim() !== labelingName) {
            try {
                const { result, shouldUpdateCurrentLabeling, newCurrentLabelingName, updatedLabelings } = 
                    await ProjectService.renameLabeling(window.currentProjectId, labelingName, newName.trim(), window.currentLabelingName);
                
                console.log('Labeling renamed successfully:', result);
                
                // Update global labelings array
                window.labelings = updatedLabelings;
                
                // Update current labeling selection if needed
                if (shouldUpdateCurrentLabeling) {
                    window.currentLabelingName = newCurrentLabelingName;
                    if (window.updateCurrentLabelingHeader) {
                        window.updateCurrentLabelingHeader(newCurrentLabelingName);
                    }
                }
                
                // Refresh the labelings list to show the updated name
                await ProjectController.fetchAndDisplayLabelings(window.currentProjectId);
                
                alert(`Labeling renamed from "${labelingName}" to "${newName.trim()}" successfully!`);
                
            } catch (error) {
                console.error('Error renaming labeling:', error);
                alert('Failed to rename labeling: ' + error.message);
            }
        } else if (newName && newName.trim() === labelingName) {
            alert('New name must be different from the current name.');
        }
    }

    /**
     * Create or update labeling for model-generated bouts
     * @param {string} labelingName - The name of the labeling to create or update
     */
    static async createOrUpdateModelLabeling(labelingName) {
        try {
            console.log(`Creating/updating labeling: ${labelingName} for project ${window.currentProjectId}`);
            
            const { created, labeling, updatedLabelings } = await ProjectService.createOrUpdateModelLabeling(
                window.currentProjectId, 
                labelingName, 
                window.labelings
            );
            
            if (created) {
                console.log('New model labeling created:', labeling);
                
                // Update global labelings array
                window.labelings = updatedLabelings;
                
                // Update the labelings display if modal is open
                const labelingModal = document.getElementById('labelingModal');
                if (labelingModal && labelingModal.classList.contains('show')) {
                    await ProjectController.fetchAndDisplayLabelings(window.currentProjectId);
                }
            } else {
                console.log(`Labeling ${labelingName} already exists, no need to create`);
            }
            
        } catch (error) {
            console.error('Error creating/updating model labeling:', error);
        }
    }

    /**
     * Update labeling color with immediate UI feedback and error handling
     * @param {string} labelingName - The name of the labeling to update
     * @param {string} newColor - The new color value
     * @param {HTMLElement} colorPickerElement - The color picker element for UI updates
     */
    static async updateLabelingColor(labelingName, newColor, colorPickerElement) {
        try {
            // Update the visual circle immediately for better UX
            const colorCircle = colorPickerElement.parentElement.querySelector('.color-circle');
            if (colorCircle) {
                colorCircle.style.backgroundColor = newColor;
            }
            
            // Update color via service layer
            const { result, updatedLabelings } = await ProjectService.updateLabelingColor(window.currentProjectId, labelingName, newColor);
            console.log(`Color updated for labeling "${labelingName}" to ${newColor}`);
            
            // Update global labelings array
            window.labelings = updatedLabelings;
            
            // If we're in visualization view, update the overlays to show only bouts matching this labeling
            if (window.dragContext.currentSession && window.dragContext.currentSession.bouts) {
                window.OverlayManager.updateOverlaysForLabelingChange(window.dragContext.currentSession, window.currentLabelingName);
            }
            
            // Update current labeling header color if this is the selected labeling
            const currentLabelingNameElement = document.getElementById('current-labeling-name');
            if (labelingName == window.currentLabelingName && currentLabelingNameElement) {
                currentLabelingNameElement.innerHTML = `
                    <div class="color-circle me-1" style="width: 12px; height: 12px; border-radius: 50%; background-color: ${newColor}; border: 1px solid #ccc; display: inline-block;"></div>
                    ${labelingName}
                `;
            }

        } catch (error) {
            console.error('Error updating labeling color:', error);
            // Revert the visual change on error
            const colorCircle = colorPickerElement.parentElement.querySelector('.color-circle');
            if (colorCircle) {
                // Try to find the original color from the labelings array
                const originalLabeling = window.labelings.find(l => l.name === labelingName);
                if (originalLabeling) {
                    colorCircle.style.backgroundColor = originalLabeling.color;
                }
            }
        }
    }

    static navigateToNextSession() {
        const nextSession = SessionService.getNextSession(sessions, currentSessionId);
        
        if (!nextSession) {
            console.log('No next session available');
            if (SessionService.getFilteredSessions(sessions).length === 0) {
                window.showTableView();
            }
            return;
        }
        
        console.log(`Navigating to next session: ${nextSession.session_name}`);
        window.visualizeSession(nextSession.session_id);
    }

    static navigateToPreviousSession() {
        const prevSession = SessionService.getPreviousSession(sessions, currentSessionId);
        
        if (!prevSession) {
            console.log('No previous session available');
            if (SessionService.getFilteredSessions(sessions).length === 0) {
                window.showTableView();
            }
            return;
        }
        
        console.log(`Navigating to previous session: ${prevSession.session_name}`);
        window.visualizeSession(prevSession.session_id);
    }
}

export default ProjectController;