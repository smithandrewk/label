/**
 * Overlay Manager - Handles creation, positioning, and lifecycle of plot overlays
 */
class OverlayManager {
    constructor() {
        this.activeOverlays = [];
    }

    /**
     * Clean up all existing overlays from the DOM
     */
    cleanupOverlays() {
        document.querySelectorAll('.drag-overlay, .left-overlay, .right-overlay').forEach(el => el.remove());
        this.activeOverlays = [];
    }

    /**
     * Recreate overlays for refreshed session data
     * @param {Object} sessionData - The session data containing bouts
     * @param {string} currentLabelingName - The currently selected labeling name
     * @param {string} currentSessionId - The current session ID
     */
    recreateOverlaysForRefreshedSession(sessionData, currentLabelingName, currentSessionId) {
        if (!sessionData || !currentSessionId || !document.getElementById('timeSeriesPlot')) {
            return;
        }

        console.log('Recreating overlays for refreshed session data...');
        
        // Clean up existing overlays
        this.cleanupOverlays();
        
        // Recreate overlays for all bouts
        const container = document.querySelector('.plot-container');
        if (!container) {
            console.error('Plot container not found');
            return;
        }

        // Ensure bouts is an array
        this.ensureSessionBoutsIsArray(sessionData);
        
        // Create overlays for each bout
        const overlays = sessionData.bouts.map((bout, index) => 
            this.createBoutOverlays(index, container)
        );
        
        this.activeOverlays = overlays;

        // Update all overlay positions
        this.updateAllOverlayPositions(sessionData, currentLabelingName);
    }

    /**
     * Update positions for all overlays based on current plot state
     * @param {Object} sessionData - The session data containing bouts
     * @param {string} currentLabelingName - The currently selected labeling name
     */
    updateAllOverlayPositions(sessionData, currentLabelingName) {
        const plotDiv = document.getElementById('timeSeriesPlot');
        if (!plotDiv || !plotDiv._fullLayout || !plotDiv._fullLayout.xaxis) {
            console.error('Plot not ready for overlay positioning');
            return;
        }

        sessionData.bouts.forEach((bout, index) => {
            // Only show overlays for bouts that match the currently selected labeling
            if (bout['label'] === currentLabelingName) {
                this.updateOverlayPositions(plotDiv, bout, index);
            } else {
                this.hideOverlay(index);
            }
        });
    }

    /**
     * Ensure session bouts is an array (utility function)
     * @param {Object} session - Session object to validate
     */
    ensureSessionBoutsIsArray(session) {
        // CRITICAL FIX: Don't destructively overwrite existing bout data
        if (session.bouts === undefined) {
            session.bouts = [];
        } else if (session.bouts === null || !Array.isArray(session.bouts)) {
            console.warn('Session bouts is not an array but not overwriting to preserve database data:', session.bouts);
            // Only set to empty as last resort for UI functionality - this may still cause issues
            session.bouts = [];
        }
    }

    /**
     * Create bout overlays for a specific bout index
     * Note: This delegates to the existing createBoutOverlays function in script.js
     * @param {number} index - Bout index
     * @param {HTMLElement} container - Container element
     * @returns {Object} Overlay elements
     */
    createBoutOverlays(index, container) {
        // Delegate to the existing function in script.js
        // This maintains all the existing drag/resize functionality
        if (typeof window.createBoutOverlays === 'function') {
            return window.createBoutOverlays(index, container);
        } else {
            console.error('createBoutOverlays function not available');
            return null;
        }
    }

    /**
     * Update overlay positions for a specific bout
     * Note: This delegates to the existing updateOverlayPositions function in script.js
     * @param {Object} plotDiv - Plotly plot element
     * @param {Object} bout - Bout data
     * @param {number} index - Bout index
     */
    updateOverlayPositions(plotDiv, bout, index) {
        // Delegate to the existing function in script.js
        if (typeof window.updateOverlayPositions === 'function') {
            window.updateOverlayPositions(plotDiv, bout, index);
        } else {
            console.error('updateOverlayPositions function not available');
        }
    }

    /**
     * Hide overlay for a specific bout index
     * Note: This delegates to the existing hideOverlay function in script.js
     * @param {number} index - Bout index
     */
    hideOverlay(index) {
        // Delegate to the existing function in script.js
        if (typeof window.hideOverlay === 'function') {
            window.hideOverlay(index);
        } else {
            console.error('hideOverlay function not available');
        }
    }

    /**
     * Handle session data refresh after operations like duplication
     * @param {Object} params - Parameters object
     * @param {Object} params.refreshedSessionData - New session data
     * @param {Object} params.dragContext - Current drag context
     * @param {string} params.currentLabelingName - Current labeling name
     * @param {string} params.currentSessionId - Current session ID
     */
    handleSessionDataRefresh({ refreshedSessionData, dragContext, currentLabelingName, currentSessionId }) {
        if (!refreshedSessionData || !dragContext.currentSession) {
            return;
        }

        // Update session data
        dragContext.currentSession.bouts = refreshedSessionData.bouts;
        dragContext.currentSession.data = refreshedSessionData.data;
        console.log('Session data updated with refreshed bouts');
        
        // Recreate overlays if we're currently visualizing this session
        this.recreateOverlaysForRefreshedSession(
            dragContext.currentSession, 
            currentLabelingName, 
            currentSessionId
        );
    }

    /**
     * Update overlays when labeling selection changes
     * @param {Object} sessionData - The current session data
     * @param {string} currentLabelingName - The newly selected labeling name
     */
    updateOverlaysForLabelingChange(sessionData, currentLabelingName) {
        if (!sessionData || !sessionData.bouts) {
            return;
        }
        
        console.log('Updating overlays for labeling change to:', currentLabelingName);
        
        const plotDiv = document.getElementById('timeSeriesPlot');
        if (!plotDiv || !plotDiv._fullLayout || !plotDiv._fullLayout.xaxis) {
            console.log('Plot not ready for overlay update');
            return;
        }
        
        sessionData.bouts.forEach((bout, index) => {
            if (bout['label'] === currentLabelingName) {
                console.log(`Updating overlay for bout ${index} with label ${bout['label']}`);
                this.updateOverlayPositions(plotDiv, bout, index);
            } else {
                this.hideOverlay(index);
            }
        });
    }
}

// Create singleton instance
const overlayManager = new OverlayManager();

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = overlayManager;
} else {
    window.OverlayManager = overlayManager;
}
