/**
 * Action Button Templates
 * Contains reusable HTML templates for action buttons in the visualization view
 */

export const ActionButtonTemplates = {
    /**
     * Current labeling display template
     */
currentLabeling: (labelingName, labelingColor) => `
    <span id="current-labeling-name" style="display: inline-flex; align-items: center; margin-right: 8px; padding: 4px 8px; background: rgba(0, 123, 255, 0.1); border-radius: 12px; font-size: 12px; color: #007bff; font-weight: 500; cursor: pointer; transition: background-color 0.2s ease, transform 0.1s ease;">
        ${labelingName !== "No Labeling" ? `<div class="color-circle me-1" style="width: 12px; height: 12px; border-radius: 50%; background-color: ${labelingColor}; border: 1px solid #ccc; display: inline-block;"></div>` : ''}
        ${labelingName}
    </span>
`,

    /**
     * Score button template
     */
    scoreButton: () => `
        <span id="score-btn-overlay" style="display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; background:rgba(224, 224, 224, 0); cursor: pointer;" title="Select Model & Score">
            <i class="fa-solid fa-rocket"></i>
        </span>
    `,

    /**
     * Split button template
     * @param {boolean} isSplitting - Whether splitting mode is active
     */
    splitButton: (isSplitting = false) => `
        <span id="split-btn-overlay" style="display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; background:rgba(224, 224, 224, ${isSplitting ? '1' : '0'});">
            <i class="fa-solid fa-arrows-split-up-and-left"></i>
        </span>
    `,

    /** 
     * Delete Bouts button with confirmation template
    */
    deleteBoutButton: () =>`
    <div style="position: relative; display: inline-block; width: 32px; height: 32px;">
            <span id="cancel-delete-btn-overlay" style="position: absolute; right: 100%; display: none; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; margin-right: 4px; cursor: pointer;">
                <i id="cancel-delete-btn" class="fa-solid fa-xmark" style="font-size:20px;"></i>
            </span>
            <span id="delete-btn-overlay" style="display:inline-flex; align-items:center; justify-content:center; width:32px; height:32px; border-radius:50%; background:rgba(224,224,224,0); cursor:pointer;">
                <i id="delete-btn" class="fa-solid fa-bomb"></i>
            </span>
        </div>
    `,
    /**
     * Trash/Delete button with confirmation template
     */
    deleteButton: () => `
        <div style="position: relative; display: inline-block; width: 32px; height: 32px;">
            <span id="cancel-btn-overlay" style="position: absolute; right: 100%; display: none; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; margin-right: 4px; cursor: pointer;">
                <i id="cancel-btn" class="fa-solid fa-xmark" style="font-size:20px;"></i>
            </span>
            <span id="trash-btn-overlay" style="display:inline-flex; align-items:center; justify-content:center; width:32px; height:32px; border-radius:50%; background:rgba(224,224,224,0); cursor:pointer;">
                <i id="trash-btn" class="fa-solid fa-trash"></i>
            </span>
        </div>
    `,

    /**
     * Verified status button template
     * @param {boolean} isVerified - Whether the session is verified
     */
    verifiedButton: (isVerified = false) => `
        <span id="verified-btn-overlay-viz" style="display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; background: rgba(224,224,224,0); cursor: pointer; margin-left: 8px;">
            <i id="verified-btn-viz" class="fa-solid fa-check" style="color: ${isVerified ? '#28a745' : '#dee2e6'}; font-size: 18px;"></i>
        </span>
    `,

    /**
     * Complete action buttons container for visualization view
     * @param {Object} options - Configuration options
     * @param {boolean} options.isSplitting - Whether splitting mode is active
     * @param {boolean} options.isVerified - Whether the session is verified
     */
    visualizationActionButtons: ({ isSplitting = false, isVerified = false, labelingName = "No Labeling", labelingColor = "#000000" } = {}) => {
        return [
            ActionButtonTemplates.currentLabeling(labelingName, labelingColor),
            ActionButtonTemplates.scoreButton(),
            ActionButtonTemplates.splitButton(isSplitting),
            ActionButtonTemplates.deleteBoutButton(),
            ActionButtonTemplates.deleteButton(),
            ActionButtonTemplates.verifiedButton(isVerified)
        ].join('');
    }
};

/**
 * Event Handler Utilities for Action Buttons
 */
export const ActionButtonHandlers = {
    /**
     * Setup event listeners for visualization action buttons
     * @param {Object} options - Configuration options
     * @param {Function} options.onDeleteBouts - Delete Bouts callback function
     * @param {Function} options.onDelete - Delete callback function
     * @param {Function} options.onVerify - Verify callback function
     * @param {Function} options.onSplit - Split toggle callback function
     * @param {Function} options.onScore - Score callback function
     * @param {boolean} options.isSplitting - Current splitting state
     */
    setupVisualizationButtons: ({ onDeleteBouts, onDelete, onVerify, onSplit, onScore, onLabeling, isSplitting = false } = {}) => {
        // Setup delete bout button with confirmation
        ActionButtonHandlers.setupDeleteBoutButton(onDeleteBouts);

        // Setup delete button with confirmation
        ActionButtonHandlers.setupDeleteButton(onDelete);

        // Setup verified button
        ActionButtonHandlers.setupVerifiedButton(onVerify);
        
        // Setup split button
        ActionButtonHandlers.setupSplitButton(onSplit, isSplitting);
        
        // Setup score button (now opens model selection)
        ActionButtonHandlers.setupScoreButton(onScore);

        // Setup current labeling button
        ActionButtonHandlers.setupCurrentLabelingButton(onLabeling);
    },

    /**
     * Setup delete bouts button with confirmation behavior
     * @param {Function} onDeleteBouts - Delete bouts callback function
     */
    setupDeleteBoutButton: (onDeleteBouts) => {

        const delete_btn_overlay = document.getElementById('delete-btn-overlay');
        const delete_btn = document.getElementById('delete-btn');
        const cancel_delete_btn_overlay = document.getElementById('cancel-delete-btn-overlay');

        if (!delete_btn_overlay || !delete_btn || !cancel_delete_btn_overlay) return;

        delete_btn_overlay.dataset.armed = "false";

        delete_btn_overlay.addEventListener('mouseenter', () => {
            delete_btn_overlay.style.background = 'rgba(0, 0, 0, 0.1)';
        });
        delete_btn_overlay.addEventListener('mouseleave', () => {
            delete_btn_overlay.style.background ='rgba(224, 224, 224, 0)';
        });

        // Click handling with confirmation
        delete_btn_overlay.addEventListener('click', () => {
            const isArmed = delete_btn_overlay.dataset.armed === "true";
            if (!isArmed) {
                // Arm the delete button
                delete_btn_overlay.dataset.armed = "true";
                delete_btn.style.color = '#dc3545'; // Bootstrap red
                cancel_delete_btn_overlay.style.display = 'inline-flex';
            } else {
                
                // Execute delete
                if (onDeleteBouts) onDeleteBouts();
                // Reset state
                ActionButtonHandlers.resetDeleteBoutButton();
            }
        });

        // Cancel button for delete btn handling with stopPropagation
        cancel_delete_btn_overlay.addEventListener('click', (e) => {
            // Cancel delete and prevent event from bubbling to parent
            e.stopPropagation();
            ActionButtonHandlers.resetDeleteBoutButton();
        });
        cancel_delete_btn_overlay.addEventListener('mouseenter', () => {
            cancel_delete_btn_overlay.style.background = 'rgba(0,0,0,0.1)';
        });
        cancel_delete_btn_overlay.addEventListener('mouseleave', () => {
            cancel_delete_btn_overlay.style.background = 'rgba(224,224,224,0)';
        });
    },

    /**
     * Reset delete button to unarmed state
     */
    resetDeleteBoutButton: () => {
        const delete_btn_overlay = document.getElementById('delete-btn-overlay');
        const delete_btn = document.getElementById('delete-btn');
        const cancel_delete_btn_overlay = document.getElementById('cancel-delete-btn-overlay');

        if (delete_btn_overlay) delete_btn_overlay.dataset.armed = "false";
        if (delete_btn) delete_btn.style.color = '';
        if (cancel_delete_btn_overlay) cancel_delete_btn_overlay.style.display = 'none';
    },
        
    /**
     * Setup delete button with confirmation behavior
     * @param {Function} onDelete - Delete callback function
     */
    setupDeleteButton: (onDelete) => {
        const trash_btn_overlay = document.getElementById('trash-btn-overlay');
        const trash_btn = document.getElementById('trash-btn');
        const cancel_btn_overlay = document.getElementById('cancel-btn-overlay');

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
                if (onDelete) onDelete();
                ActionButtonHandlers.resetDeleteButton();
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
            ActionButtonHandlers.resetDeleteButton();
        });
    },

    /**
     * Reset delete button to unarmed state
     */
    resetDeleteButton: () => {
        const trash_btn_overlay = document.getElementById('trash-btn-overlay');
        const trash_btn = document.getElementById('trash-btn');
        const cancel_btn_overlay = document.getElementById('cancel-btn-overlay');

        if (trash_btn_overlay) trash_btn_overlay.dataset.armed = "false";
        if (trash_btn) trash_btn.style.color = '';
        if (cancel_btn_overlay) cancel_btn_overlay.style.display = 'none';
    },

    /**
     * Setup verified button
     * @param {Function} onVerify - Verify callback function
     */
    setupVerifiedButton: (onVerify) => {
        const verified_btn_overlay = document.getElementById('verified-btn-overlay-viz');

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
     * Setup split button
     * @param {Function} onSplit - Split toggle callback function
     * @param {boolean} isSplitting - Current splitting state
     */
    setupSplitButton: (onSplit, isSplitting = false) => {
        const split_btn_overlay = document.getElementById('split-btn-overlay');

        if (!split_btn_overlay) return;

        // Hover effects
        split_btn_overlay.addEventListener('mouseenter', () => {
            split_btn_overlay.style.background = isSplitting ? 'rgba(224, 224, 224)' : 'rgba(0, 0, 0, 0.1)';
        });
        
        split_btn_overlay.addEventListener('mouseleave', () => {
            split_btn_overlay.style.background = isSplitting ? 'rgba(224, 224, 224)' : 'rgba(224, 224, 224, 0)';
        });
        
        // Click handling
        split_btn_overlay.addEventListener('click', () => {
            if (onSplit) onSplit();
        });
    },

    /**
     * Setup score button - now opens model selection modal
     * @param {Function} onScore - Score callback function (optional, for backward compatibility)
     */
    setupScoreButton: (onScore) => {
        const score_btn_overlay = document.getElementById('score-btn-overlay');

        if (!score_btn_overlay) return;

        // Hover effects
        score_btn_overlay.addEventListener('mouseenter', () => {
            score_btn_overlay.style.background = 'rgba(0,0,0,0.1)';
        });
        
        score_btn_overlay.addEventListener('mouseleave', () => {
            score_btn_overlay.style.background = 'rgba(224,224,224,0)';
        });
        
        // Click handling - now opens model selection modal
        score_btn_overlay.addEventListener('click', () => {
            console.log('opening model selection modal');
            ActionButtonHandlers.openModelSelection();
        });
    },

    /**
     * Open model selection modal
     */
    openModelSelection: () => {
        const modalElement = document.getElementById('modelSelection');
        if (modalElement && window.bootstrap) {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
            
            // load models when modal is opened
            ActionButtonHandlers.loadAvailableModels();
            
            console.log('model selection modal opened');
        } else {
            console.error('model selection modal not found or bootstrap not available');
        }
    },

    /**
     * Load available models and populate the list
     */
    loadAvailableModels: () => {
        const modelsList = document.getElementById('available-models-list');
        if (!modelsList) return;
        
        // for now just show placeholder content and log to console
        console.log('loading available models from database/api');
        
        // simulate loading
        setTimeout(() => {
            modelsList.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="fa-solid fa-robot fa-2x mb-2 d-block"></i>
                    <p class="mb-0">no models configured yet</p>
                    <small>use the add model button to create your first model</small>
                </div>
            `;
        }, 500);
    },

    /**
     * Setup current labeling button to open modal
     * @param {Function} onLabeling - Callback to open labeling modal
     */
    setupCurrentLabelingButton: (onLabeling) => {
        const labelingBtn = document.getElementById('current-labeling-name');
        if (!labelingBtn) return;

        labelingBtn.addEventListener('mouseenter', () => {
            labelingBtn.style.backgroundColor = 'rgba(0, 123, 255, 0.15)';
            labelingBtn.style.transform = 'scale(1.03)';
        });
        labelingBtn.addEventListener('mouseleave', () => {
            labelingBtn.style.backgroundColor = 'rgba(0, 123, 255, 0.1)';
            labelingBtn.style.transform = 'scale(1)';
        });
        labelingBtn.addEventListener('click', () => {
            if (onLabeling) {
                onLabeling();
            } else {
                // Default: open modal with id 'labelingModal' if present
                const labelingModal = document.getElementById('labelingModal');
                if (labelingModal && window.bootstrap) {
                    const modal = new bootstrap.Modal(labelingModal);
                    modal.show();
                    
                    // Add keyboard listener for 'R' key to close modal
                    const handleKeyPress = (event) => {
                        if (event.key.toLowerCase() === 'r') {
                            modal.hide();
                            document.removeEventListener('keydown', handleKeyPress);
                        }
                    };
                    
                    document.addEventListener('keydown', handleKeyPress);
                    
                    // Clean up listener when modal is hidden
                    labelingModal.addEventListener('hidden.bs.modal', () => {
                        document.removeEventListener('keydown', handleKeyPress);
                    }, { once: true });
                }
            }
        });
    }
};

// Global functions for model management (to be called from modal)
window.showAddModelForm = function() {
    console.log('showing add model form');
    const form = document.getElementById('add-model-form');
    if (form) {
        form.style.display = 'block';
    }
};

window.hideAddModelForm = function() {
    console.log('hiding add model form');
    const form = document.getElementById('add-model-form');
    if (form) {
        form.style.display = 'none';
        // reset form
        document.getElementById('new-model-form').reset();
    }
};

window.handleAddModel = function(event) {
    event.preventDefault();
    
    const formData = {
        name: document.getElementById('model-name').value,
        description: document.getElementById('model-description').value,
        pyFilename: document.getElementById('py-filename').value,
        ptFilename: document.getElementById('pt-filename').value,
        className: document.getElementById('model-class-name').value
    };
    
    console.log('adding new model:', formData);
    
    // for now just log and hide form
    // later this will call api to save model
    alert('model would be saved (placeholder functionality)');
    window.hideAddModelForm();
};

export default ActionButtonTemplates;