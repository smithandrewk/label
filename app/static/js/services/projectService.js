import ProjectAPI from '../api/projectAPI.js';
import SessionAPI from '../api/sessionAPI.js';
import SessionService from './sessionService.js';

export class ProjectService {
    /**
     * Fetch project sessions and labelings, and set current labeling
     * @param {number} projectId - The project ID
     * @returns {Promise<{sessions: Array, labelings: Array, currentLabeling: Object}>}
     */
    static async fetchProjectSessionsAndLabelings(projectId) {
        try {
            // Fetch sessions and labelings concurrently
            let [sessions, labelings] = await Promise.all([
                SessionAPI.fetchSessions(projectId),
                ProjectAPI.fetchLabelings(projectId)
            ]);

            // Check if we need to discover sessions for dataset-based projects
            if (!sessions || sessions.length === 0) {
                console.log('No sessions found, checking if this is a dataset-based project...');
                try {
                    // Try to discover sessions from linked datasets
                    const response = await fetch(`/api/projects/${projectId}/discover-sessions`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' }
                    });
                    
                    if (response.ok) {
                        const discoveryResult = await response.json();
                        if (discoveryResult.success && discoveryResult.sessions_created > 0) {
                            console.log(`Discovered ${discoveryResult.sessions_created} sessions for dataset-based project`);
                            
                            // Re-fetch sessions after discovery
                            sessions = await SessionAPI.fetchSessions(projectId);
                            
                            // Show user feedback
                            if (window.showNotification) {
                                window.showNotification(
                                    `Discovered ${discoveryResult.sessions_created} sessions from linked datasets`,
                                    'success'
                                );
                            } else {
                                console.log('Session discovery result:', discoveryResult.message);
                            }
                        } else if (discoveryResult.sessions_created === 0) {
                            console.log('Session discovery result:', discoveryResult.message);
                        }
                    }
                } catch (discoveryError) {
                    console.log('Session discovery not available or failed:', discoveryError.message);
                    // Continue with empty sessions - this is expected for legacy projects
                }
            }

            // Determine current labeling
            let currentLabelingJSON = null;
            let currentLabelingName = "No Labeling";

            if (labelings && labelings.length > 0) {
                currentLabelingJSON = labelings[0];
                currentLabelingName = currentLabelingJSON.name;
            }

            // Log session statistics using SessionService
            const stats = SessionService.getSessionStats(sessions);
            console.log('Session stats:', stats);

            return {
                sessions,
                labelings,
                currentLabelingJSON,
                currentLabelingName,
                stats
            };
        } catch (error) {
            console.error('Error fetching project sessions and labelings:', error);
            throw error;
        }
    }

    /**
     * Fetch all sessions or sessions for a specific project
     * @param {number|null} projectId - The project ID (optional)
     * @returns {Promise<Array>} Sessions array
     */
    static async fetchSessions(projectId = null) {
        try {
            const sessions = await SessionAPI.fetchSessions(projectId);
            return sessions;
        } catch (error) {
            console.error('Error fetching sessions:', error);
            throw error;
        }
    }

    /**
     * Delete a labeling and handle state management
     * @param {number} projectId - The project ID
     * @param {string} labelingName - The name of the labeling to delete
     * @param {string} currentLabelingName - The currently selected labeling name
     * @returns {Promise<{result: Object, shouldUpdateCurrentLabeling: boolean, newCurrentLabelingName: string}>}
     */
    static async deleteLabeling(projectId, labelingName, currentLabelingName) {
        try {
            // Call the API to delete the labeling
            const result = await ProjectAPI.deleteLabeling(projectId, labelingName);
            
            // Determine if we need to update the current labeling selection
            const shouldUpdateCurrentLabeling = (currentLabelingName === labelingName);
            const newCurrentLabelingName = shouldUpdateCurrentLabeling ? 'No Labeling' : currentLabelingName;
            
            // Fetch updated labelings list
            const updatedLabelings = await ProjectAPI.fetchLabelings(projectId);
            
            return {
                result,
                shouldUpdateCurrentLabeling,
                newCurrentLabelingName,
                updatedLabelings
            };
        } catch (error) {
            console.error('Error in ProjectService.deleteLabeling:', error);
            throw error;
        }
    }

    /**
     * Create a new labeling and handle state management
     * @param {number} projectId - The project ID
     * @param {string} labelingName - The name of the new labeling
     * @param {Object} labels - The labels object (optional)
     * @returns {Promise<{result: Object, updatedLabelings: Array}>}
     */
    static async createLabeling(projectId, labelingName, labels = {}) {
        try {
            // Call the API to create the labeling
            const result = await ProjectAPI.createLabeling(projectId, labelingName, labels);
            
            // Fetch updated labelings list
            const updatedLabelings = await ProjectAPI.fetchLabelings(projectId);
            
            return {
                result,
                updatedLabelings
            };
        } catch (error) {
            console.error('Error in ProjectService.createLabeling:', error);
            throw error;
        }
    }

    /**
     * Rename a labeling and handle state management
     * @param {number} projectId - The project ID
     * @param {string} oldName - The current labeling name
     * @param {string} newName - The new labeling name
     * @param {string} currentLabelingName - The currently selected labeling name
     * @returns {Promise<{result: Object, shouldUpdateCurrentLabeling: boolean, newCurrentLabelingName: string, updatedLabelings: Array}>}
     */
    static async renameLabeling(projectId, oldName, newName, currentLabelingName) {
        try {
            // Call the API to rename the labeling
            const result = await ProjectAPI.renameLabeling(projectId, oldName, newName);
            
            // Determine if we need to update the current labeling selection
            const shouldUpdateCurrentLabeling = (currentLabelingName === oldName);
            const newCurrentLabelingName = shouldUpdateCurrentLabeling ? newName : currentLabelingName;
            
            // Fetch updated labelings list
            const updatedLabelings = await ProjectAPI.fetchLabelings(projectId);
            
            return {
                result,
                shouldUpdateCurrentLabeling,
                newCurrentLabelingName,
                updatedLabelings
            };
        } catch (error) {
            console.error('Error in ProjectService.renameLabeling:', error);
            throw error;
        }
    }

    /**
     * Duplicate a labeling and handle state management
     * @param {number} projectId - The project ID
     * @param {string} originalName - The name of the labeling to duplicate
     * @param {string} newName - The name of the new duplicate labeling
     * @returns {Promise<{result: Object, updatedLabelings: Array}>}
     */
    static async duplicateLabeling(projectId, originalName, newName) {
        try {
            // Call the API to duplicate the labeling
            const result = await ProjectAPI.duplicateLabeling(projectId, originalName, newName);
            
            // Fetch updated labelings list
            const updatedLabelings = await ProjectAPI.fetchLabelings(projectId);
            
            return {
                result,
                updatedLabelings
            };
        } catch (error) {
            console.error('Error in ProjectService.duplicateLabeling:', error);
            throw error;
        }
    }

    /**
     * Duplicate a labeling and refresh session data if needed
     * @param {number} projectId - The project ID
     * @param {string} originalName - The name of the labeling to duplicate
     * @param {string} newName - The name of the new duplicate labeling
     * @param {number|null} currentSessionId - Current session ID to refresh (optional)
     * @returns {Promise<{result: Object, updatedLabelings: Array, refreshedSessionData: Object|null}>}
     */
    static async duplicateLabelingWithSessionRefresh(projectId, originalName, newName, currentSessionId = null) {
        try {
            // Call the API to duplicate the labeling
            const result = await ProjectAPI.duplicateLabeling(projectId, originalName, newName);
            
            // Fetch updated labelings list
            const updatedLabelings = await ProjectAPI.fetchLabelings(projectId);
            
            // Refresh session data if a current session is provided
            let refreshedSessionData = null;
            if (currentSessionId) {
                try {
                    refreshedSessionData = await SessionAPI.loadSessionData(currentSessionId);
                } catch (error) {
                    console.error('Error refreshing session data after duplication:', error);
                    // Don't throw here - the duplication itself was successful
                }
            }
            
            return {
                result,
                updatedLabelings,
                refreshedSessionData
            };
        } catch (error) {
            console.error('Error in ProjectService.duplicateLabelingWithSessionRefresh:', error);
            throw error;
        }
    }

    /**
     * Update labeling color and handle state management
     * @param {number} projectId - The project ID
     * @param {string} labelingName - The name of the labeling
     * @param {string} color - The new color
     * @returns {Promise<{result: Object, updatedLabelings: Array}>}
     */
    static async updateLabelingColor(projectId, labelingName, color) {
        try {
            // Call the API to update the color
            const result = await ProjectAPI.updateLabelingColor(projectId, labelingName, color);
            
            // Fetch updated labelings list
            const updatedLabelings = await ProjectAPI.fetchLabelings(projectId);
            
            return {
                result,
                updatedLabelings
            };
        } catch (error) {
            console.error('Error in ProjectService.updateLabelingColor:', error);
            throw error;
        }
    }

    /**
     * Create or update a labeling for model-generated results
     * @param {number} projectId - The project ID
     * @param {string} labelingName - The name of the labeling
     * @param {Array} existingLabelings - The current labelings array
     * @returns {Promise<{created: boolean, labeling: Object, updatedLabelings: Array}>}
     */
    static async createOrUpdateModelLabeling(projectId, labelingName, existingLabelings) {
        try {
            // Check if labeling already exists
            const existingLabeling = existingLabelings.find(l => l.name === labelingName);
            
            if (!existingLabeling) {
                // Create new labeling for model results
                const result = await ProjectAPI.createLabeling(projectId, labelingName);
                const updatedLabelings = await ProjectAPI.fetchLabelings(projectId);
                
                return {
                    created: true,
                    labeling: result,
                    updatedLabelings
                };
            } else {
                return {
                    created: false,
                    labeling: existingLabeling,
                    updatedLabelings: existingLabelings
                };
            }
        } catch (error) {
            console.error('Error in ProjectService.createOrUpdateModelLabeling:', error);
            throw error;
        }
    }

    /**
     * Create a new project with file upload
     * @param {Object} formData - The form data containing name, participant, folderName, and files
     * @returns {Promise<Object>} The upload result
     */
    static async createProject(formData) {
        try {
            // Create a FormData object to handle file uploads
            const uploadData = new FormData();
            uploadData.append('name', formData.name);
            uploadData.append('participant', formData.participant);
            uploadData.append('projectPath', formData.projectPath);
            
            // Call the API to upload the project
            const result = await ProjectAPI.createProject(uploadData);
            
            // Log business-relevant information
            console.log('Upload started:', result);
            console.log('Upload ID:', result.upload_id);
            console.log('Sessions found:', result.sessions_found);
            
            return result;
        } catch (error) {
            console.error('Error in ProjectService.createProject:', error);
            throw error;
        }
    }
}

export default ProjectService;
