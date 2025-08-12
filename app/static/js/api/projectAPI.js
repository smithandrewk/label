export class ProjectAPI {
    static async fetchProjects() {
        try {
            const response = await fetch('/api/projects');
            if (!response.ok) throw new Error('Network response was not ok');
            return await response.json();
        } catch (error) {
            console.error('Error fetching projects:', error);
            throw error;
        }
    }

    static async fetchLabelingMetadata(projectId) {
        try {
            const response = await fetch(`/api/labeling_metadata?project_id=${projectId}`);
            if (!response.ok) throw new Error('Failed to fetch labeling metadata');
            return await response.json();
        } catch (error) {
            console.error('Error fetching labeling metadata:', error);
            throw error;
        }
    }
    /**
     * Fetch labelings for a given project
     * @param {string|number} projectId
     * @returns {Promise<Object[]>}
     */
    static async fetchLabelings(projectId) {
        const response = await fetch(`/api/labelings/${projectId}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        // Parse the labelings JSON string
        let labelings = [];
        if (data.length > 0 && data[0].labelings) {
            try {
                labelings = JSON.parse(data[0].labelings);
            } catch (e) {
                console.error('Error parsing labelings JSON:', e);
                labelings = [];
            }
        }
        return labelings;
    }

    /**
     * Create or update a labeling for a project
     * @param {string|number} projectId
     * @param {string} name - The labeling name
     * @param {Object} labels - The labels object (optional, defaults to empty)
     * @returns {Promise<Object>}
     */
    static async createLabeling(projectId, name, labels = {}) {
        try {
            const response = await fetch(`/api/labelings/${projectId}/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    name: name,
                    labels: labels
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error creating labeling:', error);
            throw error;
        }
    }

    /**
     * Update the color of a labeling
     * @param {string|number} projectId
     * @param {string} labelingName
     * @param {string} color - The new color
     * @returns {Promise<Object>}
     */
    static async updateLabelingColor(projectId, labelingName, color) {
        try {
            const response = await fetch(`/api/labelings/${projectId}/color`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    color: color,
                    name: labelingName
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('Error updating labeling color:', error);
            throw error;
        }
    }

    /**
     * Rename a labeling
     * @param {string|number} projectId
     * @param {string} oldName
     * @param {string} newName
     * @returns {Promise<Object>}
     */
    static async renameLabeling(projectId, oldName, newName) {
        try {
            const response = await fetch(`/api/labelings/${projectId}/rename`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    old_name: oldName,
                    new_name: newName
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to rename labeling');
            }

            return await response.json();
        } catch (error) {
            console.error('Error renaming labeling:', error);
            throw error;
        }
    }

    /**
     * Duplicate a labeling
     * @param {string|number} projectId
     * @param {string} originalName
     * @param {string} newName
     * @returns {Promise<Object>}
     */
    static async duplicateLabeling(projectId, originalName, newName) {
        try {
            const response = await fetch(`/api/labelings/${projectId}/duplicate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    original_name: originalName,
                    new_name: newName
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to duplicate labeling');
            }

            return await response.json();
        } catch (error) {
            console.error('Error duplicating labeling:', error);
            throw error;
        }
    }

    /**
     * Delete a labeling
     * @param {string|number} projectId
     * @param {string} labelingName
     * @returns {Promise<Object>}
     */
    static async deleteLabeling(projectId, labelingName) {
        try {
            const response = await fetch(`/api/labelings/${projectId}/delete`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    name: labelingName
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to delete labeling');
            }

            return await response.json();
        } catch (error) {
            console.error('Error deleting labeling:', error);
            throw error;
        }
    }

    /**
     * Export a specific labeling as JSON
     * @param {string|number} projectId
     * @param {string} labelingName
     * @returns {Promise<Object>}
     */
    static async exportLabeling(projectId, labelingName) {
        try {
            const response = await fetch(`/api/export/labeling/${projectId}/${encodeURIComponent(labelingName)}`);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to export labeling');
            }

            return await response.json();
        } catch (error) {
            console.error('Error exporting labeling:', error);
            throw error;
        }
    }

    /**
     * Import a labeling from JSON data
     * @param {string|number} projectId
     * @param {Object} importData - The JSON data to import
     * @returns {Promise<Object>}
     */
    static async importLabeling(projectId, importData) {
        try {
            const response = await fetch(`/api/import/labeling/${projectId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(importData)
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to import labeling');
            }

            return await response.json();
        } catch (error) {
            console.error('Error importing labeling:', error);
            throw error;
        }
    }

    /**
     * Create a new project with file upload
     * @param {FormData} uploadData - The FormData object ready for upload
     * @returns {Promise<Object>} The upload result
     */
    static async createProject(uploadData) {
        try {
            // Use fetch API to send data to the backend
            const response = await fetch('/api/project/upload', {
                method: 'POST',
                body: uploadData  // Don't set Content-Type header, let browser set it for FormData
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to create project');
            }
            
            return data;
        } catch (error) {
            console.error('Error in ProjectAPI.createProject:', error);
            throw error;
        }
    }

    /**
     * Export project configuration as downloadable JSON
     * @param {string|number} projectId - The project ID to export
     * @returns {Promise<void>} - Triggers download of JSON file
     */
    static async exportProjectConfiguration(projectId) {
        try {
            const response = await fetch(`/api/projects/${projectId}/export-config`);
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to export project configuration');
            }
            
            const configData = await response.json();
            
            // Create a blob and download link
            const blob = new Blob([JSON.stringify(configData, null, 2)], {
                type: 'application/json'
            });
            
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `${configData.project.project_name}_config_${new Date().toISOString().slice(0, 10)}.json`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            
            return configData;
        } catch (error) {
            console.error('Error exporting project configuration:', error);
            throw error;
        }
    }

    /**
     * Import project configuration from JSON data
     * @param {Object} configData - The project configuration data to import
     * @returns {Promise<Object>} The import result
     */
    static async importProjectConfiguration(configData) {
        try {
            const response = await fetch('/api/projects/import-config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(configData)
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Failed to import project configuration');
            }
            
            return data;
        } catch (error) {
            console.error('Error importing project configuration:', error);
            throw error;
        }
    }

}

export default ProjectAPI;