/**
 * Model API Module
 * Handles all model-related API calls
 */

export class ModelAPI {
    /**
     * Fetch all available models
     * @returns {Promise<Array>} List of available models
     */
    static async fetchModels() {
        try {
            console.log('fetching models from api');
            const response = await fetch('/api/models');
            if (!response.ok) {
                throw new Error(`failed to fetch models: ${response.status} ${response.statusText}`);
            }
            
            const models = await response.json();
            console.log(`fetched ${models.length} models from api`);
            return models;
        } catch (error) {
            console.error('error fetching models:', error);
            throw error;
        }
    }

    /**
     * Add a new model to the system
     * @param {Object} modelData - Model configuration data
     * @param {string} modelData.name - Display name for the model
     * @param {string} modelData.description - Model description
     * @param {string} modelData.pyFilename - Python file name
     * @param {string} modelData.ptFilename - PyTorch weights file name
     * @param {string} modelData.className - Python class name
     * @returns {Promise<Object>} Created model data
     */
    static async addModel(modelData) {
        try {
            console.log('adding new model:', modelData);
            
            const response = await fetch('/api/models', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(modelData)
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'failed to add model');
            }
            
            const result = await response.json();
            console.log('model added successfully:', result);
            return result;
        } catch (error) {
            console.error('error adding model:', error);
            throw error;
        }
    }

    /**
     * Delete a model from the system
     * @param {string|number} modelId - ID of the model to delete
     * @returns {Promise<Object>} Deletion result
     */
    static async deleteModel(modelId) {
        try {
            console.log('deleting model:', modelId);
            
            const response = await fetch(`/api/models/${modelId}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'failed to delete model');
            }
            
            const result = await response.json();
            console.log('model deleted successfully:', result);
            return result;
        } catch (error) {
            console.error('error deleting model:', error);
            throw error;
        }
    }

    /**
     * Update an existing model
     * @param {string|number} modelId - ID of the model to update
     * @param {Object} modelData - Updated model data
     * @returns {Promise<Object>} Updated model data
     */
    static async updateModel(modelId, modelData) {
        try {
            console.log('updating model:', modelId, modelData);
            
            const response = await fetch(`/api/models/${modelId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(modelData)
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'failed to update model');
            }
            
            const result = await response.json();
            console.log('model updated successfully:', result);
            return result;
        } catch (error) {
            console.error('error updating model:', error);
            throw error;
        }
    }

    /**
     * Score a session using a specific model
     * @param {string|number} sessionId - ID of the session to score
     * @param {string|number} modelId - ID of the model to use
     * @param {string} projectName - Name of the project
     * @param {string} sessionName - Name of the session
     * @returns {Promise<Object>} Scoring result with scoring_id
     */
    static async scoreSession(sessionId, modelId, projectName, sessionName) {
        try {
            console.log('scoring session with model:', { sessionId, modelId, projectName, sessionName });
            
            const response = await fetch('/api/models/score', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    model_id: modelId,
                    project_name: projectName,
                    session_name: sessionName
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'failed to start scoring');
            }
            
            const result = await response.json();
            console.log('scoring started:', result);
            return result;
        } catch (error) {
            console.error('error scoring session:', error);
            throw error;
        }
    }

    /**
     * Get the status of a scoring operation
     * @param {string} scoringId - ID of the scoring operation
     * @returns {Promise<Object>} Scoring status
     */
    static async getScoringStatus(scoringId) {
        try {
            const response = await fetch(`/api/scoring_status/${scoringId}`);
            if (!response.ok) {
                throw new Error(`failed to get scoring status: ${response.status}`);
            }
            
            const status = await response.json();
            return status;
        } catch (error) {
            console.error('error getting scoring status:', error);
            throw error;
        }
    }



        /**
     * Score a session using a specific model on GPU
     * @param {string|number} sessionId - ID of the session to score
     * @param {string|number} modelId - ID of the model to use
     * @param {string} projectName - Name of the project
     * @param {string} sessionName - Name of the session
     * @returns {Promise<Object>} Scoring result with scoring_id
     */
    static async scoreSessionGpu(sessionId, modelId, projectName, sessionName) {
        try {
            console.log('scoring session with model on GPU:', { sessionId, modelId, projectName, sessionName });
            
            const response = await fetch('/api/models/score_gpu', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    model_id: modelId,
                    project_name: projectName,
                    session_name: sessionName
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'failed to start GPU scoring');
            }
            
            const result = await response.json();
            console.log('GPU scoring started:', result);
            return result;
        } catch (error) {
            console.error('error scoring session on GPU:', error);
            throw error;
        }
    }

    /**
     * Check GPU availability status
     * @returns {Promise<Object>} GPU status information
     */
    static async getGpuStatus() {
        try {
            const response = await fetch('/api/gpu_status');
            if (!response.ok) {
                throw new Error(`failed to get GPU status: ${response.status}`);
            }
            
            const status = await response.json();
            return status;
        } catch (error) {
            console.error('error getting GPU status:', error);
            throw error;
        }
    }
}

export default ModelAPI;