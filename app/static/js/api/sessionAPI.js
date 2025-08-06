/**
 * Session API Module
 * Handles all session-related API calls with intelligent caching
 */

import { cacheService } from '../services/cacheService.js';

export class SessionAPI {
    /**
     * Load session data for a specific session with intelligent caching
     * @param {string} sessionId - The ID of the session to load
     * @param {Object} options - Loading options (useCache, offset, limit)
     * @returns {Promise<{bouts: Array, data: Array}>} Session data
     */
    static async loadSessionData(sessionId, options = {}) {
        // Load full dataset by default - pagination is opt-in for special cases
        const { useCache = true, offset = null, limit = null, progressiveLoad = false } = options;
        const isPaginated = offset !== null || limit !== null;
        
        // Progressive loading: load preview first, then full dataset
        if (progressiveLoad && !isPaginated) {
            console.log(`🔄 Progressive loading for session ${sessionId}: loading preview first`);
            
            // Load preview (first 5000 points) for immediate display
            const preview = await this.loadSessionData(sessionId, {
                useCache,
                offset: 0,
                limit: 5000
            });
            
            // Trigger full load in background
            setTimeout(async () => {
                console.log(`📊 Loading full dataset for session ${sessionId} in background`);
                await this.loadSessionData(sessionId, { useCache, offset: null, limit: null });
            }, 100);
            
            return preview;
        }
        
        // Check cache first if enabled
        if (useCache) {
            const cached = cacheService.getCachedSessionData(sessionId, isPaginated);
            if (cached) {
                console.log(`🎯 Using cached session data for session ${sessionId}`);
                return this.processSessionData(cached);
            }
        }
        
        try {
            console.log(`🌐 Loading session data from API for session ID: ${sessionId}`);
            
            // Build URL with pagination parameters
            let url = `/api/session/${sessionId}`;
            const params = new URLSearchParams();
            if (offset !== null) params.append('offset', offset);
            if (limit !== null) params.append('limit', limit);
            if (params.toString()) url += `?${params.toString()}`;
            
            const startTime = performance.now();
            const response = await fetch(url);
            const loadTime = performance.now() - startTime;
            
            if (!response.ok) {
                throw new Error(`Failed to fetch session data: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            const dataSize = JSON.stringify(data).length / 1024; // KB
            
            console.log(`📊 API Response: ${loadTime.toFixed(0)}ms, ${dataSize.toFixed(1)}KB, ${data.data?.length || 0} points`);
            
            // Cache the response if caching is enabled
            if (useCache) {
                cacheService.cacheSessionData(sessionId, data, isPaginated);
            }
            
            return this.processSessionData(data);
        } catch (error) {
            console.error('Error loading session data:', error);
            throw error;
        }
    }
    
    /**
     * Process and normalize session data
     */
    static processSessionData(data) {
        // Ensure bouts is an array
        let bouts = data.bouts;
        if (typeof bouts === 'string') {
            try {
                bouts = JSON.parse(bouts);
            } catch (e) {
                console.error('Error parsing bouts in processSessionData:', e);
                bouts = [];
            }
        } else if (!Array.isArray(bouts)) {
            bouts = [];
        }
        
        const result = { 
            bouts: bouts, 
            data: data.data,
            pagination: data.pagination,
            session_info: data.session_info
        };
        
        console.log(`✅ Processed session data: ${bouts.length} bouts, ${data.data?.length || 0} data points`);
        
        return result;
    }
    /**
     * Fetch all sessions or sessions for a specific project with caching
     * @param {number|null} projectId - The project ID (optional)
     * @param {boolean} useCache - Whether to use cache (default: true)
     * @returns {Promise<Array>} List of sessions
     */
    static async fetchSessions(projectId = null, useCache = true) {
        const cacheKey = projectId ? `sessions_project_${projectId}` : 'sessions_all';
        
        // Check cache first
        if (useCache) {
            const cached = cacheService.getCachedList(cacheKey);
            if (cached) {
                console.log(`🎯 Using cached sessions list${projectId ? ` for project ${projectId}` : ''}`);
                return cached;
            }
        }
        
        try {
            // Build URL with query parameter if projectId is provided
            const url = projectId ? `/api/sessions?project_id=${projectId}` : '/api/sessions';
            
            const startTime = performance.now();
            const response = await fetch(url);
            const loadTime = performance.now() - startTime;
            
            if (!response.ok) {
                throw new Error(`Failed to fetch sessions: ${response.status} ${response.statusText}`);
            }
            
            const sessions = await response.json();
            console.log(`📊 Fetched ${sessions.length} sessions${projectId ? ` for project ${projectId}` : ''} in ${loadTime.toFixed(0)}ms`);
            
            // Cache the results
            if (useCache) {
                cacheService.cacheList(cacheKey, sessions);
            }
            
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
                    bouts: JSON.stringify(session.bouts || [])
                })
            });
            if (!response.ok) throw new Error('Failed to update metadata');
            const result = await response.json();
            console.log('Metadata update result:', result);
            
            // Invalidate related caches since session data changed
            this.invalidateSessionCaches(session.session_id);
            
        } catch (error) {
            console.error('Error updating metadata:', error);
        }
    }
    
    /**
     * Invalidate caches related to a session
     */
    static invalidateSessionCaches(sessionId) {
        // Remove session-specific caches
        cacheService.remove(`session_${sessionId}_full`);
        cacheService.remove(`session_${sessionId}_paginated`);
        
        // Remove sessions list caches (they might show updated metadata)
        cacheService.remove('sessions_all');
        // Also remove project-specific session lists (we don't know which project this session belongs to)
        const allKeys = Object.keys(localStorage).filter(key => key.includes('sessions_project_'));
        allKeys.forEach(key => localStorage.removeItem(key));
        
        console.log(`🧹 Invalidated caches for session ${sessionId}`);
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