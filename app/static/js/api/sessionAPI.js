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
     * Fetch all sessions for a specific project
     * @param {string} projectId - The ID of the project
     * @returns {Promise<Array>} List of sessions
     */

    static async updateSessionMetadata(session) {
        try {
            const response = await fetch(`/api/session/${session.session_id}/metadata`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    status: session.status,
                    keep: session.keep,
                    verified: session.verified || 0,
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
}

export default SessionAPI;