/**
 * Session API Module
 * Handles all session-related API calls
 */

export class SessionAPI {
    /**
     * Load session data for a specific session
     * @param {string} sessionId - The ID of the session to load
     * @returns {Promise<{bouts: Array, data: Array}>} Session data
     */
    static async loadSessionData(sessionId) {
        try {
            console.log(`Loading session data for session ID: ${sessionId}`);
            
            const response = await fetch(`/api/session/${sessionId}`);
            if (!response.ok) {
                throw new Error(`Failed to fetch session data: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Received session data:', data);
                    
            // Ensure bouts is an array
            let bouts = data.bouts;
            if (typeof bouts === 'string') {
                try {
                    bouts = JSON.parse(bouts);
                } catch (e) {
                    console.error('Error parsing bouts in loadSessionData:', e);
                    bouts = [];
                }
            } else if (!Array.isArray(bouts)) {
                bouts = [];
            }
            
            console.log(`Successfully loaded session data: ${bouts.length} bouts, ${data.data?.length || 0} data points`);
            
            return { bouts: bouts, data: data.data };
        } catch (error) {
            console.error('Error loading session data:', error);
            throw error;
        }
    }
    /**
     * Fetch all sessions or sessions for a specific project
     * @param {number|null} projectId - The project ID (optional)
     * @returns {Promise<Array>} List of sessions
     */
    static async fetchSessions(projectId = null) {
        try {
            // Build URL with query parameter if projectId is provided
            const url = projectId ? `/api/sessions?project_id=${projectId}` : '/api/sessions';
            
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`Failed to fetch sessions: ${response.status} ${response.statusText}`);
            }
            
            const sessions = await response.json();
            console.log(`Fetched ${sessions.length} sessions${projectId ? ` for project ${projectId}` : ''}`);
            
            return sessions;
        } catch (error) {
            console.error('Error fetching sessions:', error);
            throw error;
        }
    }

    static async updateSessionMetadata(session) {
        try {
            const response = await fetch(`/api/session/${session.session_id}/metadata`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    status: session.status,
                    keep: session.keep,
                    verified: session.verified || 0,
                    puffs_verified: session.puffs_verified || 0,
                    smoking_verified: session.smoking_verified || 0,
                    bouts: JSON.stringify(session.bouts || [])
                })
            });
            if (!response.ok) throw new Error('Failed to update metadata');
            const result = await response.json();
            console.log('Metadata update result:', result);
        } catch (error) {
            console.error('Error updating metadata:', error);
        }
    }

    static async scoreSession(session_id, project_name, session_name) {
        try {
            const response = await fetch('/score_session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    session_id: session_id,
                    project_name: project_name,
                    session_name: session_name
                })
            });
            if (!response.ok) throw new Error('Failed to score session');
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('Error scoring session', error)
        }
    }
}

export default SessionAPI;