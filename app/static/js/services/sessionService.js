/**
 * Session Service Module
 * Handles session-related business logic and data manipulation
 */

export class SessionService {
    /**
     * Filter sessions to exclude discarded sessions
     * @param {Array} sessions - Array of session objects
     * @returns {Array} Filtered sessions (excludes sessions with keep === 0)
     */
    static getFilteredSessions(sessions) {
        if (!Array.isArray(sessions)) {
            console.warn('getFilteredSessions: sessions is not an array', sessions);
            return [];
        }
        
        // Only filter out sessions explicitly marked as discarded (keep === 0)
        return sessions.filter(session => {
            // Session is available unless explicitly marked as keep=0
            return session.keep !== 0;
        });
    }

    /**
     * Find session by ID
     * @param {Array} sessions - Array of session objects
     * @param {string|number} sessionId - The session ID to find
     * @returns {Object|null} The session object or null if not found
     */
    static findSessionById(sessions, sessionId) {
        if (!Array.isArray(sessions)) {
            return null;
        }
        return sessions.find(session => session.session_id == sessionId) || null;
    }

    /**
     * Get the next session in the filtered list
     * @param {Array} sessions - Array of session objects
     * @param {string|number} currentSessionId - Current session ID
     * @returns {Object|null} Next session or null if none found
     */
    static getNextSession(sessions, currentSessionId) {
        const filteredSessions = this.getFilteredSessions(sessions);
        
        if (filteredSessions.length <= 1) {
            return null;
        }
        
        const currentIndex = filteredSessions.findIndex(s => s.session_id == currentSessionId);
        if (currentIndex === -1) {
            return filteredSessions[0]; // Return first if current not found
        }
        
        const nextIndex = (currentIndex + 1) % filteredSessions.length;
        return filteredSessions[nextIndex];
    }

    /**
     * Get the previous session in the filtered list
     * @param {Array} sessions - Array of session objects
     * @param {string|number} currentSessionId - Current session ID
     * @returns {Object|null} Previous session or null if none found
     */
    static getPreviousSession(sessions, currentSessionId) {
        const filteredSessions = this.getFilteredSessions(sessions);
        
        if (filteredSessions.length <= 1) {
            return null;
        }
        
        const currentIndex = filteredSessions.findIndex(s => s.session_id == currentSessionId);
        if (currentIndex === -1) {
            return filteredSessions[0]; // Return first if current not found
        }
        
        const prevIndex = currentIndex === 0 ? filteredSessions.length - 1 : currentIndex - 1;
        return filteredSessions[prevIndex];
    }

    /**
     * Check if a session is available (not discarded)
     * @param {Object} session - Session object
     * @returns {boolean} True if session is available
     */
    static isSessionAvailable(session) {
        return session && session.keep !== 0;
    }

    /**
     * Validate session data format
     * @param {Object} session - Session object with data property
     * @returns {boolean} True if data format is valid
     */
    static validateSessionData(session) {
        if (!session || !session.data || !Array.isArray(session.data)) {
            return false;
        }

        return session.data.every(d => 
            d.ns_since_reboot && 
            typeof d.accel_x === 'number' && 
            typeof d.accel_y === 'number' && 
            typeof d.accel_z === 'number'
        );
    }

    /**
     * Get session statistics
     * @param {Array} sessions - Array of session objects
     * @returns {Object} Statistics about the sessions
     */
    static getSessionStats(sessions) {
        if (!Array.isArray(sessions)) {
            return { total: 0, available: 0, discarded: 0, verified: 0 };
        }

        const stats = {
            total: sessions.length,
            available: 0,
            discarded: 0,
            verified: 0
        };

        sessions.forEach(session => {
            if (session.keep === 0) {
                stats.discarded++;
            } else {
                stats.available++;
            }
            
            if (session.verified) {
                stats.verified++;
            }
        });

        return stats;
    }

    /**
     * Find the best session to navigate to after deleting the current one
     * @param {Array} sessions - Array of session objects
     * @param {string|number} currentSessionId - ID of session being deleted
     * @returns {Object|null} Best session to navigate to, or null if none
     */
    static findNextSessionAfterDeletion(sessions, currentSessionId) {
        const filteredSessions = this.getFilteredSessions(sessions);
        
        if (filteredSessions.length <= 1) {
            return null;
        }
        
        const currentIndex = filteredSessions.findIndex(s => s.session_id == currentSessionId);
        
        if (currentIndex === -1) {
            return filteredSessions[0]; // Return first if current not found
        }
        
        // If we're at the end, go to the previous one
        if (currentIndex === filteredSessions.length - 1 && currentIndex > 0) {
            return filteredSessions[currentIndex - 1];
        } else {
            // Otherwise go to the next one (with wraparound)
            const nextIndex = (currentIndex + 1) % filteredSessions.length;
            return filteredSessions[nextIndex];
        }
    }
}

export default SessionService;
