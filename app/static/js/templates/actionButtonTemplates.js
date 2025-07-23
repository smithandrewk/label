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
     * darkmode button
     */
    darkModeButton: () => `
        <span id="darkMode-btn-overlay" style="display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border-radius: 50%; background:rgba(224, 224, 224, 0);">
            <i id="darkModeIcon" class="fa-solid fa-moon"></i>
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

    modelStatusIndicator: () => `
        <div id="model-status-indicator" style="display: none; align-items: center; margin-right: 12px; padding: 4px 8px; background: rgba(40, 167, 69, 0.1); border: 1px solid rgba(40, 167, 69, 0.2); border-radius: 12px; font-size: 11px; color: #28a745; font-weight: 500;">
            <i class="fa-solid fa-robot me-1"></i>
            <span id="current-model-name"></span>
            <kbd style="margin-left: 6px; font-size: 10px; padding: 2px 4px; background: rgba(40, 167, 69, 0.2); border-radius: 3px; color: #155724;">B</kbd>
        </div>
    `,

    /**
     * Complete action buttons container for visualization view
     * @param {Object} options - Configuration options
     * @param {boolean} options.isSplitting - Whether splitting mode is active
     * @param {boolean} options.isVerified - Whether the session is verified
     */
    visualizationActionButtons: ({ isSplitting = false, isVerified = false, labelingName = "No Labeling", labelingColor = "#000000" } = {}) => {
        return [
            ActionButtonTemplates.modelStatusIndicator(),
            ActionButtonTemplates.currentLabeling(labelingName, labelingColor),
            ActionButtonTemplates.darkModeButton(),
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
     * @param {Function} options.onDarkMode - darkmode callback function
     * @param {boolean} options.isSplitting - Current splitting state
     */
    setupVisualizationButtons: ({ onDeleteBouts, onDelete, onVerify, onSplit, onScore, onDarkMode, onLabeling, isSplitting = false } = {}) => {
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

        // Setup darkmode button
        ActionButtonHandlers.setupDarkModeButton(onDarkMode); 

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
     * Load available models and GPU status, then populate the list
     */
    loadAvailableModels: async () => {
        const modelsList = document.getElementById('available-models-list');
        if (!modelsList) return;
        
        // show loading state
        modelsList.innerHTML = `
            <div class="text-center text-muted">
                <i class="fa-solid fa-spinner fa-spin me-2"></i>
                loading models and checking GPU...
            </div>
        `;
        
        try {
            // import ModelAPI dynamically to avoid circular dependencies
            const { default: ModelAPI } = await import('../api/modelAPI.js');
            
            // Load models and GPU status concurrently
            const [models, gpuStatus] = await Promise.all([
                ModelAPI.fetchModels(),
                ModelAPI.getGpuStatus()
            ]);
            
            // Update GPU button state and status display
            ActionButtonHandlers.updateGpuButtonState(gpuStatus);
            
            if (models && models.length > 0) {
                // render models list
                let modelsHtml = '';
                models.forEach(model => {
                    modelsHtml += `
                        <div class="model-item d-flex justify-content-between align-items-start p-3 border rounded mb-2" data-model-id="${model.id}">
                            <div class="flex-grow-1">
                                <h6 class="mb-1">${model.name}</h6>
                                <p class="text-muted small mb-1">${model.description || 'no description'}</p>
                                <div class="d-flex gap-3 text-muted" style="font-size: 11px;">
                                    <span><i class="fa-solid fa-file-code me-1"></i>${model.py_filename}</span>
                                    <span><i class="fa-solid fa-brain me-1"></i>${model.pt_filename}</span>
                                    <span><i class="fa-solid fa-cube me-1"></i>${model.class_name}</span>
                                </div>
                            </div>
                            <div class="d-flex gap-1">
                                <button class="btn btn-sm btn-outline-primary score-range-btn" 
                                        onclick="selectModelForScoringInVisibleRange('${model.id}', '${model.name}')" 
                                        data-bs-toggle="tooltip" 
                                        data-bs-placement="top" 
                                        title="Score visible range">
                                    <i class="fa-solid fa-crop-simple"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-primary" onclick="selectModelForScoring('${model.id}', '${model.name}')" title="use this model">
                                    <i class="fa-solid fa-rocket"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-secondary" onclick="editModel('${model.id}')" title="edit model">
                                    <i class="bi bi-pencil"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-danger" onclick="deleteModel('${model.id}', '${model.name}')" title="delete model">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </div>
                        </div>
                    `;
                });
                modelsList.innerHTML = modelsHtml;
                
                // Update tooltips with current visible range
                ActionButtonHandlers.updateScoreRangeTooltips();
            } else {
                // no models available
                modelsList.innerHTML = `
                    <div class="text-center text-muted py-3">
                        <i class="fa-solid fa-robot fa-2x mb-2 d-block"></i>
                        <p class="mb-0">no models configured yet</p>
                        <small>use the add model button to create your first model</small>
                    </div>
                `;
            }
        } catch (error) {
            console.error('error loading models or GPU status:', error);
            modelsList.innerHTML = `
                <div class="text-center text-danger py-3">
                    <i class="fa-solid fa-exclamation-triangle fa-2x mb-2 d-block"></i>
                    <p class="mb-0">failed to load models</p>
                    <small>${error.message}</small>
                </div>
            `;
            
            // If GPU status failed, disable GPU button
            ActionButtonHandlers.updateGpuButtonState({ gpu_available: false, error: error.message });
        }
    },

    updateScoreRangeTooltips: function() {
        const visibleRange = window.getVisibleRangeInNs();
        const scoreRangeButtons = document.querySelectorAll('.score-range-btn');
        
        if (visibleRange) {
            const rangeText = window.formatTimeRange(visibleRange.start, visibleRange.end);
            scoreRangeButtons.forEach(button => {
                button.setAttribute('title', `Score visible range: ${rangeText}`);
                // Reinitialize tooltip if Bootstrap is available
                if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
                    const tooltip = bootstrap.Tooltip.getInstance(button);
                    if (tooltip) {
                        tooltip.dispose();
                    }
                    new bootstrap.Tooltip(button);
                }
            });
        } else {
            scoreRangeButtons.forEach(button => {
                button.setAttribute('title', 'Score visible range (no plot data available)');
            });
        }
    },

    updateModelStatusIndicator: function(isScoring = false) {
        const indicator = document.getElementById('model-status-indicator');
        const modelNameSpan = document.getElementById('current-model-name');
        
        if (indicator && modelNameSpan) {
            if (window.currentModelId && window.currentModelName) {
                if (isScoring) {
                    modelNameSpan.innerHTML = `<i class="fa-solid fa-spinner fa-spin me-1"></i>${window.currentModelName}`;
                    indicator.style.background = 'rgba(255, 193, 7, 0.1)';
                    indicator.style.borderColor = 'rgba(255, 193, 7, 0.2)';
                    indicator.style.color = '#856404';
                } else {
                    modelNameSpan.textContent = window.currentModelName;
                    indicator.style.background = 'rgba(40, 167, 69, 0.1)';
                    indicator.style.borderColor = 'rgba(40, 167, 69, 0.2)';
                    indicator.style.color = '#28a745';
                }
                indicator.style.display = 'inline-flex';
            } else {
                indicator.style.display = 'none';
            }
        }
    },

    /**
     * Update GPU button state based on GPU availability
     * @param {Object} gpuStatus - GPU status from the backend
     */
    updateGpuButtonState: (gpuStatus) => {
        const gpuBtn = document.querySelector('.device-btn[data-device="gpu"]');
        const statusElement = document.getElementById('device-status');
        
        if (!gpuBtn || !statusElement) return;
        
        if (gpuStatus.gpu_available) {
            // GPU is available
            gpuBtn.disabled = false;
            gpuBtn.classList.remove('btn-outline-secondary');
            gpuBtn.classList.add('btn-outline-danger');
            gpuBtn.title = `GPU Available: ${gpuStatus.gpu_name || 'Unknown GPU'}`;
            
            console.log('GPU available:', gpuStatus);
        } else {
            // GPU is not available
            gpuBtn.disabled = true;
            gpuBtn.classList.remove('btn-outline-danger');
            gpuBtn.classList.add('btn-outline-secondary');
            gpuBtn.title = `GPU Not Available: ${gpuStatus.error || 'No GPU detected'}`;
            
            // Reset to CPU if GPU was selected
            const modal = document.getElementById('modelSelection');
            if (modal && modal.dataset.deviceType === 'gpu') {
                window.selectDevice('cpu');
            }
            
            console.log('GPU not available:', gpuStatus.error || 'No GPU detected');
        }
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
    },
    setupDarkModeButton: (onDarkMode) => {
        const darkMode_btn_overlay = document.getElementById('darkMode-btn-overlay');

        if (!darkMode_btn_overlay) return;

        // Hover effects
        darkMode_btn_overlay.addEventListener('mouseenter', () => {
            darkMode_btn_overlay.style.background = 'rgba(0,0,0,0.1)';
        });
        
        darkMode_btn_overlay.addEventListener('mouseleave', () => {
            darkMode_btn_overlay.style.background = 'rgba(224,224,224,0)';
        });
        
        // Click handling
        darkMode_btn_overlay.addEventListener('click', () => {
            if (onDarkMode) onDarkMode();
        });
    }
};

// Global functions for model management (to be called from modal)
window.showAddModelForm = function() {
    console.log('showing add model form');
    const form = document.getElementById('add-model-form');
    const errorMsg = document.getElementById('model-error-message');
    if (form) {
        form.style.display = 'block';
    }
    if (errorMsg) {
        errorMsg.style.display = 'none';
    }
};

window.hideAddModelForm = function() {
    console.log('hiding add model form');
    const form = document.getElementById('add-model-form');
    const errorMsg = document.getElementById('model-error-message');
    if (form) {
        form.style.display = 'none';
        // reset form
        document.getElementById('new-model-form').reset();
    }
    if (errorMsg) {
        errorMsg.style.display = 'none';
    }
};

window.handleAddModel = async function(event) {
    event.preventDefault();
    
    const errorMsg = document.getElementById('model-error-message');
    
    try {
        const formData = {
            name: document.getElementById('model-name').value.trim(),
            description: document.getElementById('model-description').value.trim(),
            py_filename: document.getElementById('py-filename').value.trim(),
            pt_filename: document.getElementById('pt-filename').value.trim(),
            class_name: document.getElementById('model-class-name').value.trim()
        };
        
        console.log('adding new model:', formData);
        
        // validate required fields
        if (!formData.name || !formData.py_filename || !formData.pt_filename || !formData.class_name) {
            throw new Error('please fill in all required fields');
        }
        
        // import ModelAPI and add model
        const { default: ModelAPI } = await import('../api/modelAPI.js');
        const result = await ModelAPI.addModel(formData);
        
        console.log('model added successfully:', result);
        
        // hide form and refresh models list
        window.hideAddModelForm();
        ActionButtonHandlers.loadAvailableModels();
        
        const successMessage = `Model "${formData.name}" added successfully!\n\n` +
            `⚠️  IMPORTANT REMINDER:\n` +
            `Please ensure these files are present in your MODEL_DIR:\n\n` +
            `📁 Python file: ${formData.py_filename}\n` +
            `📁 Weights file: ${formData.pt_filename}\n\n` +
            `The model will not work until both files are in the correct directory.\n` +
            `Check your .env file for the MODEL_DIR setting.`;
        
        alert(successMessage);
        
    } catch (error) {
        console.error('error adding model:', error);
        if (errorMsg) {
            errorMsg.textContent = error.message;
            errorMsg.style.display = 'block';
        }
    }
};

window.currentModelId = null;
window.currentModelName = null;

window.selectModelForScoring = function(modelId, modelName) {
    console.log('selected model for scoring:', { modelId, modelName });
    
    if (!window.currentSessionId) {
        alert('no session selected');
        return;
    }
    
    window.currentModelId = modelId;
    window.currentModelName = modelName;
    
    // Update the model status indicator
    ActionButtonHandlers.updateModelStatusIndicator();

    // get device type from modal
    const modal = document.getElementById('modelSelection');
    const deviceType = modal ? modal.dataset.deviceType || 'cpu' : 'cpu';
    console.log('🔍 Device type detected:', deviceType);
    
    const deviceLabel = deviceType.toUpperCase();
    const confirmed = confirm(`score current session using model: ${modelName} on ${deviceLabel}?`);
    if (!confirmed) return;
    
    // close modal
    const bsModal = bootstrap.Modal.getInstance(modal);
    if (bsModal) bsModal.hide();
    
    // start scoring with selected model and device
    if (deviceType === 'gpu') {
        window.scoreSessionWithModelGpu(window.currentSessionId, modelId, modelName);
    } else {
        window.scoreSessionWithModel(window.currentSessionId, modelId, modelName);
    }
};

window.selectModelForScoringInVisibleRange = function(modelId, modelName, send_confirm = true) {
    console.log('selected model for scoring:', { modelId, modelName });
    
    if (!window.currentSessionId) {
        alert('no session selected');
        return;
    }

    window.currentModelId = modelId;
    window.currentModelName = modelName;
    
    // Update the model status indicator
    ActionButtonHandlers.updateModelStatusIndicator();

    // get device type from modal
    const modal = document.getElementById('modelSelection');
    const deviceType = modal ? modal.dataset.deviceType || 'cpu' : 'cpu';
    console.log('🔍 Device type detected:', deviceType);
    
    const deviceLabel = deviceType.toUpperCase();
    if (send_confirm) {
        const visibleRange = window.getVisibleRangeInNs();
        let confirmMessage = `Score visible range using model: ${modelName} on ${deviceLabel}?`;
        
        if (visibleRange) {
            const rangeText = window.formatTimeRange(visibleRange.start, visibleRange.end);
            confirmMessage += `\n\nRange: ${rangeText}`;
        } else {
            confirmMessage += `\n\nWarning: No visible range detected`;
        }
        
        const confirmed = confirm(confirmMessage);
        if (!confirmed) return;
    }
    // close modal
    const bsModal = bootstrap.Modal.getInstance(modal);
    if (bsModal) bsModal.hide();
    
    // start scoring with selected model and device
    if (deviceType === 'gpu') {
        window.scoreSessionWithModelInVisibleRangeGpu(window.currentSessionId, modelId, modelName);
    } else {
        window.scoreSessionWithModelInVisibleRange(window.currentSessionId, modelId, modelName);
    }
};

window.getVisibleRangeInNs = function() {
    const plotDiv = document.getElementById('timeSeriesPlot');
    console.log(plotDiv);
    let viewState = null;
    if (plotDiv && plotDiv._fullLayout && plotDiv._fullLayout.xaxis) {
        viewState = {
            xrange: plotDiv._fullLayout.xaxis.range.slice(),
            yrange: plotDiv._fullLayout.yaxis.range.slice()
        };
    }
    return viewState.xrange ? {
        start: viewState.xrange[0],
        end: viewState.xrange[1]
    } : null;
}

window.formatTimeRange = function(startNs, endNs) {
    const startSeconds = (startNs / 1e9).toFixed(1);
    const endSeconds = (endNs / 1e9).toFixed(1);
    const durationSeconds = ((endNs - startNs) / 1e9).toFixed(1);
    return `${startSeconds}s - ${endSeconds}s (${durationSeconds}s duration)`;
}

window.scoreSessionWithModelInVisibleRange = async function(sessionId, modelId, modelName) {
    try {
        console.log('scoring session with CPU model:', { sessionId, modelId, modelName });
        
        // get session details
        const session = window.sessions?.find(s => s.session_id == sessionId);
        if (!session) {
            throw new Error('session not found');
        }
        
        // update score button to show loading
        const scoreBtn = document.getElementById('score-btn-overlay');
        if (scoreBtn) {
            scoreBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        }
        
        // Get start and end times of visible range in ns_since_reboot
        const visibleRange = window.getVisibleRangeInNs();
        console.log('Visible range for scoring:', visibleRange);

        // import ModelAPI and start scoring
        const { default: ModelAPI } = await import('../api/modelAPI.js');
        const result = await ModelAPI.scoreSessionInVisibleRange(sessionId, modelId, session.project_name, session.session_name, visibleRange.start, visibleRange.end);
        
        if (result.success) {
            console.log('scoring started successfully:', result);
            
            // Use the global function directly
            if (typeof window.pollScoringStatus === 'function') {
                window.pollScoringStatus(result.scoring_id, sessionId, session.session_name, 'cpu');
            } else {
                throw new Error('pollScoringStatus function not available globally');
            }
        } else {
            throw new Error(result.error || 'scoring failed to start');
        }
        
    } catch (error) {
        console.error('error scoring session with model:', error);
        alert('failed to start scoring: ' + error.message);
        
        // reset score button
        const scoreBtn = document.getElementById('score-btn-overlay');
        if (scoreBtn) {
            scoreBtn.innerHTML = '<i class="fa-solid fa-rocket"></i>';
        }
    }
};
window.scoreSessionWithModelInVisibleRangeGpu = async function(sessionId, modelId, modelName) {
    try {
        console.log('scoring session with CPU model:', { sessionId, modelId, modelName });
        
        // get session details
        const session = window.sessions?.find(s => s.session_id == sessionId);
        if (!session) {
            throw new Error('session not found');
        }
        
        // update score button to show loading
        const scoreBtn = document.getElementById('score-btn-overlay');
        if (scoreBtn) {
            scoreBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        }
        
        // Get start and end times of visible range in ns_since_reboot
        const visibleRange = window.getVisibleRangeInNs();
        console.log('Visible range for scoring:', visibleRange);

        // import ModelAPI and start scoring
        const { default: ModelAPI } = await import('../api/modelAPI.js');
        const result = await ModelAPI.scoreSessionInVisibleRangeGpu(sessionId, modelId, session.project_name, session.session_name, visibleRange.start, visibleRange.end);
        
        if (result.success) {
            console.log('scoring started successfully:', result);
            
            // Use the global function directly
            if (typeof window.pollScoringStatus === 'function') {
                window.pollScoringStatus(result.scoring_id, sessionId, session.session_name, 'cpu');
            } else {
                throw new Error('pollScoringStatus function not available globally');
            }
        } else {
            throw new Error(result.error || 'scoring failed to start');
        }
        
    } catch (error) {
        console.error('error scoring session with model:', error);
        alert('failed to start scoring: ' + error.message);
        
        // reset score button
        const scoreBtn = document.getElementById('score-btn-overlay');
        if (scoreBtn) {
            scoreBtn.innerHTML = '<i class="fa-solid fa-rocket"></i>';
        }
    }
};
window.scoreSessionWithModel = async function(sessionId, modelId, modelName) {
    try {
        console.log('scoring session with CPU model:', { sessionId, modelId, modelName });
        
        // get session details
        const session = window.sessions?.find(s => s.session_id == sessionId);
        if (!session) {
            throw new Error('session not found');
        }
        
        // update score button to show loading
        const scoreBtn = document.getElementById('score-btn-overlay');
        if (scoreBtn) {
            scoreBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        }
        
        // import ModelAPI and start scoring
        const { default: ModelAPI } = await import('../api/modelAPI.js');
        const result = await ModelAPI.scoreSession(sessionId, modelId, session.project_name, session.session_name);
        
        if (result.success) {
            console.log('scoring started successfully:', result);
            
            // Use the global function directly
            if (typeof window.pollScoringStatus === 'function') {
                window.pollScoringStatus(result.scoring_id, sessionId, session.session_name, 'cpu');
            } else {
                throw new Error('pollScoringStatus function not available globally');
            }
        } else {
            throw new Error(result.error || 'scoring failed to start');
        }
        
    } catch (error) {
        console.error('error scoring session with model:', error);
        alert('failed to start scoring: ' + error.message);
        
        // reset score button
        const scoreBtn = document.getElementById('score-btn-overlay');
        if (scoreBtn) {
            scoreBtn.innerHTML = '<i class="fa-solid fa-rocket"></i>';
        }
    }
};


window.scoreSessionWithModelGpu = async function(sessionId, modelId, modelName) {
    try {
        console.log('scoring session with GPU model:', { sessionId, modelId, modelName });
        
        // get session details
        const session = window.sessions?.find(s => s.session_id == sessionId);
        if (!session) {
            throw new Error('session not found');
        }
        
        // update score button to show loading
        const scoreBtn = document.getElementById('score-btn-overlay');
        if (scoreBtn) {
            scoreBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        }
        
        // import ModelAPI and start GPU scoring
        const { default: ModelAPI } = await import('../api/modelAPI.js');
        const result = await ModelAPI.scoreSessionGpu(sessionId, modelId, session.project_name, session.session_name);
        
        if (result.success) {
            console.log('GPU scoring started successfully:', result);
            
            // Use the global polling function with GPU indicator
            if (typeof window.pollScoringStatus === 'function') {
                window.pollScoringStatus(result.scoring_id, sessionId, session.session_name, 'gpu');
            } else {
                throw new Error('pollScoringStatus function not available globally');
            }
        } else {
            throw new Error(result.error || 'GPU scoring failed to start');
        }
        
    } catch (error) {
        console.error('error scoring session with GPU model:', error);
        alert('failed to start GPU scoring: ' + error.message);
        
        // reset score button
        const scoreBtn = document.getElementById('score-btn-overlay');
        if (scoreBtn) {
            scoreBtn.innerHTML = '<i class="fa-solid fa-rocket"></i>';
        }
    }
};

window.editModel = function(modelId) {
    console.log('editing model:', modelId);
    alert('edit model functionality coming soon');
};

window.deleteModel = async function(modelId, modelName) {
    const confirmed = confirm(`are you sure you want to delete model: ${modelName}?`);
    if (!confirmed) return;
    
    try {
        console.log('deleting model:', modelId);
        
        const { default: ModelAPI } = await import('../api/modelAPI.js');
        await ModelAPI.deleteModel(modelId);
        
        console.log('model deleted successfully');
        
        // refresh models list
        ActionButtonHandlers.loadAvailableModels();
        
        alert('model deleted successfully');
        
    } catch (error) {
        console.error('error deleting model:', error);
        alert('failed to delete model: ' + error.message);
    }
};

window.selectDevice = function(deviceType) {
    console.log('device selected:', deviceType);
    
    // update button states
    document.querySelectorAll('.device-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.device === deviceType) {
            btn.classList.add('active');
        }
    });
    
    // update status message
    const statusElement = document.getElementById('device-status');
    if (statusElement) {
        if (deviceType === 'gpu') {
            statusElement.textContent = 'GPU selected';
            statusElement.className = 'text d-block mt-1';
        } else {
            statusElement.textContent = 'CPU selected';
            statusElement.className = 'text d-block mt-1';
        }
    }
    
    // store device type for later use
    const modal = document.getElementById('modelSelection');
    if (modal) {
        modal.dataset.deviceType = deviceType;
    }
};


export default ActionButtonTemplates;