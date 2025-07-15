import SessionAPI from '../api/sessionAPI.js';
import { showNotification, resetScoreButton } from '../ui/uiUtils.js';

export class SessionController {
    /**
     * Score a session using the default scoring model
     * @param {string|number} sessionId - The session ID to score
     * @param {string} projectName - Name of the project
     * @param {string} sessionName - Name of the session
     */
    static async scoreSession(sessionId, projectName, sessionName) {
        try {
            console.log(`Scoring session: ${sessionId} (${sessionName} from project ${projectName})`);
            
            const scoreBtn = document.getElementById(`score-btn-overlay`);
            if (scoreBtn) {
                scoreBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
            }
            
            const result = await SessionAPI.scoreSession(sessionId, projectName, sessionName);
            
            if (result.success) {
                showNotification(`Scoring started for ${sessionName}`, 'success');
                // Use global pollScoringStatus function for now since it has complex dependencies
                if (typeof window.pollScoringStatus === 'function') {
                    window.pollScoringStatus(result.scoring_id, sessionId, sessionName, 'cpu');
                } else {
                    console.error('pollScoringStatus function not available globally');
                    resetScoreButton(sessionId);
                }
            } else {
                showNotification(`Scoring failed: ${result.error}`, 'error');
                resetScoreButton(sessionId);
            }
        } catch (error) {
            console.error('Error scoring session:', error);
            showNotification('Failed to start scoring', 'error');
            resetScoreButton(sessionId);
        }
    }
}

export default SessionController;