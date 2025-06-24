/**
 * Session List Templates
 * Contains reusable HTML templates for session list items and table rows
 */

export const SessionListTemplates = {
    /**
     * Trash button template for table rows
     * @param {string} sessionId - The session ID
     */
    tableTrashButton: (sessionId) => `
        <div style="position: relative; display: inline-block; width: 32px; height: 32px;">
            <span id="cancel-btn-overlay-${sessionId}" style="position: absolute; right: 100%; display: none; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; margin-right: 4px; cursor: pointer;">
                <i id="cancel-btn-${sessionId}" class="fa-solid fa-xmark" style="font-size: 20px;"></i>
            </span>
            <span id="trash-btn-overlay-${sessionId}" style="display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; background: rgba(224,224,224,0); cursor: pointer;">
                <i id="trash-btn-${sessionId}" class="fa-solid fa-trash"></i>
            </span>
        </div>
    `,

    /**
     * Verified checkbox template for table rows
     * @param {string} sessionId - The session ID
     * @param {boolean} isVerified - Whether the session is verified
     */
    tableVerifiedButton: (sessionId, isVerified = false) => `
        <span id="verified-btn-overlay-${sessionId}" style="display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; background: rgba(224,224,224,0); cursor: pointer;">
            <i id="verified-btn-${sessionId}" class="fa-solid fa-check" style="color: ${isVerified ? '#28a745' : '#dee2e6'}; font-size: 18px;"></i>
        </span>
    `,

    /**
     * Table row template for sessions
     * @param {Object} session - Session object
     */
    tableRow: (session) => {
        const { session_id: sessionId, session_name, project_name, status, label, keep, verified } = session;
        const statusText = `${status}${label ? ': ' + label : ''}${keep === 0 ? ' (Discarded)' : ''}`;
        
        return `
            <td>${session_name}</td>
            <td>${project_name || ''}</td>
            <td>${statusText}</td>
            <td>${SessionListTemplates.tableVerifiedButton(sessionId, verified)}</td>
            <td>
                <div class="btn-group" role="group">
                    <button class="btn btn-sm btn-primary" onclick="visualizeSession('${sessionId}')">
                        <i class="fa-solid fa-eye"></i>
                    </button>
                </div>
            </td>
            <td>${SessionListTemplates.tableTrashButton(sessionId)}</td>
        `;
    },

    /**
     * Sidebar navigation item template
     * @param {Object} session - Session object
     * @param {string} currentActiveSession - Currently active session name
     */
    sidebarItem: (session, currentActiveSession = null) => {
        const linkClass = session.session_name === currentActiveSession ? "nav-link active-session" : "nav-link";
        return `<a class="${linkClass}" href="#" onclick="visualizeSession('${session.session_id}')">${session.session_name}</a>`;
    },

    /**
     * Empty state template for when no sessions are available
     */
    emptyState: () => `
        <tr>
            <td colspan="4" class="text-center">No sessions available for this project</td>
        </tr>
    `
};

/**
 * Event Handler Utilities for Session List Items
 */
export const SessionListHandlers = {
    /**
     * Setup event listeners for table row trash button
     * @param {string} sessionId - The session ID
     * @param {Function} onDelete - Delete callback function
     */
    setupTableTrashButton: (sessionId, onDelete) => {
        const trash_btn_overlay = document.getElementById(`trash-btn-overlay-${sessionId}`);
        const trash_btn = document.getElementById(`trash-btn-${sessionId}`);
        const cancel_btn_overlay = document.getElementById(`cancel-btn-overlay-${sessionId}`);

        if (!trash_btn_overlay || !trash_btn || !cancel_btn_overlay) return;

        // Initialize armed state
        trash_btn_overlay.dataset.armed = "false";
        
        // Hover effects
        trash_btn_overlay.addEventListener('mouseenter', () => {
            trash_btn_overlay.style.background = 'rgba(0,0,0,0.1)';
        });
        
        trash_btn_overlay.addEventListener('mouseleave', () => {
            trash_btn_overlay.style.background = 'rgba(224,224,224,0)';
        });
        
        // Click handling with confirmation
        trash_btn_overlay.addEventListener('click', () => {
            const isArmed = trash_btn_overlay.dataset.armed === "true";
            if (!isArmed) {
                // Arm the button
                trash_btn_overlay.dataset.armed = "true";
                trash_btn.style.color = '#dc3545';
                cancel_btn_overlay.style.display = 'inline-flex';
            } else {
                // Execute delete
                if (onDelete) onDelete(sessionId, false);
                SessionListHandlers.resetTableTrashButton(sessionId);
            }
        });
        
        // Cancel button handling
        cancel_btn_overlay.addEventListener('mouseenter', () => {
            cancel_btn_overlay.style.background = 'rgba(0,0,0,0.1)';
        });
        
        cancel_btn_overlay.addEventListener('mouseleave', () => {
            cancel_btn_overlay.style.background = 'rgba(224,224,224,0)';
        });
        
        cancel_btn_overlay.addEventListener('click', (e) => {
            e.stopPropagation();
            SessionListHandlers.resetTableTrashButton(sessionId);
        });
    },

    /**
     * Reset table trash button to unarmed state
     * @param {string} sessionId - The session ID
     */
    resetTableTrashButton: (sessionId) => {
        const trash_btn_overlay = document.getElementById(`trash-btn-overlay-${sessionId}`);
        const trash_btn = document.getElementById(`trash-btn-${sessionId}`);
        const cancel_btn_overlay = document.getElementById(`cancel-btn-overlay-${sessionId}`);

        if (trash_btn_overlay) trash_btn_overlay.dataset.armed = "false";
        if (trash_btn) trash_btn.style.color = '';
        if (cancel_btn_overlay) cancel_btn_overlay.style.display = 'none';
    },

    /**
     * Setup event listeners for table row verified button
     * @param {string} sessionId - The session ID
     * @param {Function} onVerify - Verify callback function
     */
    setupTableVerifiedButton: (sessionId, onVerify) => {
        const verified_btn_overlay = document.getElementById(`verified-btn-overlay-${sessionId}`);

        if (!verified_btn_overlay) return;

        // Hover effects
        verified_btn_overlay.addEventListener('mouseenter', () => {
            verified_btn_overlay.style.background = 'rgba(0,0,0,0.1)';
        });
        
        verified_btn_overlay.addEventListener('mouseleave', () => {
            verified_btn_overlay.style.background = 'rgba(224,224,224,0)';
        });
        
        // Click handling
        verified_btn_overlay.addEventListener('click', () => {
            if (onVerify) onVerify();
        });
    },

    /**
     * Setup all event listeners for a session table row
     * @param {string} sessionId - The session ID
     * @param {Function} onDelete - Delete callback function
     * @param {Function} onVerify - Verify callback function
     */
    setupTableRowHandlers: (sessionId, onDelete, onVerify) => {
        SessionListHandlers.setupTableTrashButton(sessionId, onDelete);
        SessionListHandlers.setupTableVerifiedButton(sessionId, onVerify);
    }
};

export default SessionListTemplates;
