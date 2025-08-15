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
        <button class="btn btn-sm btn-outline-secondary ms-2" id="trash-btn-${sessionId}" title="Delete Session">
            <i class="fa-solid fa-trash"></i>
        </button>
    `,

    /**
     * Dual verified buttons template for table rows
     * @param {string} sessionId - The session ID
     * @param {boolean} isPuffsVerified - Whether puffs are verified
     * @param {boolean} isSmokingVerified - Whether smoking are verified
     */
    tableDualVerifiedButtons: (sessionId, isPuffsVerified = false, isSmokingVerified = false) => `
        <div class="btn-group btn-group-sm" role="group">
            <button class="btn ${isPuffsVerified ? 'btn-success' : 'btn-outline-secondary'}" 
                    id="puffs-verified-btn-${sessionId}" 
                    title="${isPuffsVerified ? 'Puffs Verified' : 'Mark Puffs as Verified'}"
                    style="border-radius: 4px 0 0 4px;">
                <i class="fa-solid fa-wind"></i>
            </button>
            <button class="btn ${isSmokingVerified ? 'btn-success' : 'btn-outline-secondary'}" 
                    id="smoking-verified-btn-${sessionId}" 
                    title="${isSmokingVerified ? 'Smoking Verified' : 'Mark Smoking as Verified'}"
                    style="border-radius: 0 4px 4px 0;">
                <i class="fa-solid fa-smoking"></i>
            </button>
        </div>
    `,

    /**
     * Table row template for sessions
     * @param {Object} session - Session object
     */
    tableRow: (session) => {
        const { session_id: sessionId, session_name, project_name, status, label, keep, puffs_verified, smoking_verified } = session;
        
        // Create status badge based on status
        let statusBadge = '';
        if (status === 'completed') {
            statusBadge = `<span class="badge bg-success">${status}</span>`;
        } else if (status === 'in_progress') {
            statusBadge = `<span class="badge bg-warning">In Progress</span>`;
        } else if (status === 'error') {
            statusBadge = `<span class="badge bg-danger">Error</span>`;
        } else {
            statusBadge = `<span class="badge bg-secondary">${status || 'Unknown'}</span>`;
        }
        
        if (label) {
            statusBadge += ` <small class="text-muted">: ${label}</small>`;
        }
        
        if (keep === 0) {
            statusBadge += ` <span class="badge bg-secondary">Discarded</span>`;
        }
        
        return `
            <td><strong>${session_name}</strong></td>
            <td class="text-muted">${project_name || '-'}</td>
            <td>${statusBadge}</td>
            <td>${SessionListTemplates.tableDualVerifiedButtons(sessionId, puffs_verified, smoking_verified)}</td>
            <td>
                <div class="btn-group" role="group">
                    <button class="btn btn-sm btn-primary" onclick="visualizeSession('${sessionId}')" title="View Session">
                        <i class="fa-solid fa-eye me-1"></i>View
                    </button>
                    ${SessionListTemplates.tableTrashButton(sessionId)}
                </div>
            </td>
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
            <td colspan="5" class="text-center text-muted py-4">
                <i class="fa-solid fa-inbox fa-2x mb-2 d-block"></i>
                No sessions available for this project
            </td>
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
        const trash_btn = document.getElementById(`trash-btn-${sessionId}`);

        if (!trash_btn) return;
        
        // Click handling with confirmation
        trash_btn.addEventListener('click', (e) => {
            e.preventDefault();
            if (confirm('Are you sure you want to delete this session?')) {
                if (onDelete) onDelete(sessionId, false);
            }
        });
    },

    /**
     * Reset table trash button to unarmed state (no longer needed with simplified approach)
     * @param {string} sessionId - The session ID
     */
    resetTableTrashButton: (sessionId) => {
        // No longer needed with simplified button approach
    },

    /**
     * Setup event listeners for table row dual verified buttons
     * @param {string} sessionId - The session ID
     * @param {Function} onVerifyPuffs - Verify puffs callback function
     * @param {Function} onVerifySmoking - Verify smoking callback function
     */
    setupTableDualVerifiedButtons: (sessionId, onVerifyPuffs, onVerifySmoking) => {
        const puffs_btn = document.getElementById(`puffs-verified-btn-${sessionId}`);
        const smoking_btn = document.getElementById(`smoking-verified-btn-${sessionId}`);

        if (puffs_btn) {
            puffs_btn.addEventListener('click', (e) => {
                e.preventDefault();
                if (onVerifyPuffs) onVerifyPuffs(sessionId);
            });
        }

        if (smoking_btn) {
            smoking_btn.addEventListener('click', (e) => {
                e.preventDefault();
                if (onVerifySmoking) onVerifySmoking(sessionId);
            });
        }
    },

    /**
     * Setup all event listeners for a session table row
     * @param {string} sessionId - The session ID
     * @param {Function} onDelete - Delete callback function
     * @param {Function} onVerifyPuffs - Verify puffs callback function
     * @param {Function} onVerifySmoking - Verify smoking callback function
     */
    setupTableRowHandlers: (sessionId, onDelete, onVerifyPuffs, onVerifySmoking) => {
        SessionListHandlers.setupTableTrashButton(sessionId, onDelete);
        SessionListHandlers.setupTableDualVerifiedButtons(sessionId, onVerifyPuffs, onVerifySmoking);
    }
};

export default SessionListTemplates;
