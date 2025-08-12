/**
 * Raw Datasets Management JavaScript
 * Handles upload, preview, and management of raw sensor datasets
 */

class RawDatasetManager {
    constructor() {
        this.currentDataset = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadDatasets();
    }

    bindEvents() {
        // Scan datasets button
        document.getElementById('scan-datasets-btn').addEventListener('click', () => this.scanAndRegisterDatasets());

        // Upload form events
        document.getElementById('preview-dataset-btn').addEventListener('click', () => this.previewDataset());
        document.getElementById('upload-dataset-btn').addEventListener('click', () => this.uploadDataset());
        document.getElementById('delete-dataset-btn').addEventListener('click', () => this.deleteCurrentDataset());

        // Project creation events
        document.getElementById('create-project-btn').addEventListener('click', () => this.createProjectFromDatasets());

        // Form validation
        document.getElementById('dataset-path').addEventListener('blur', () => this.validatePath());
        
        // Modal events
        document.getElementById('uploadDatasetModal').addEventListener('hidden.bs.modal', () => this.resetUploadForm());
        document.getElementById('createProjectModal').addEventListener('shown.bs.modal', () => this.loadDatasetsForProjectCreation());
        document.getElementById('createProjectModal').addEventListener('hidden.bs.modal', () => this.resetProjectForm());
    }

    async loadDatasets() {
        try {
            const response = await fetch('/api/datasets');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const datasets = await response.json();
            this.renderDatasets(datasets);
            
        } catch (error) {
            console.error('Error loading datasets:', error);
            this.showError('Failed to load datasets: ' + error.message);
        }
    }

    renderDatasets(datasets) {
        const container = document.getElementById('datasets-container');
        const emptyState = document.getElementById('empty-state');

        if (datasets.length === 0) {
            container.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }

        emptyState.style.display = 'none';
        
        const grid = document.createElement('div');
        grid.className = 'row g-4';

        datasets.forEach(dataset => {
            const card = this.createDatasetCard(dataset);
            grid.appendChild(card);
        });

        container.innerHTML = '';
        container.appendChild(grid);
    }

    createDatasetCard(dataset) {
        const col = document.createElement('div');
        col.className = 'col-md-6 col-lg-4';

        const uploadDate = new Date(dataset.upload_timestamp).toLocaleDateString();
        const fileSize = this.formatFileSize(dataset.file_size_bytes);
        const shortHash = dataset.dataset_hash.substring(0, 8);

        col.innerHTML = `
            <div class="card dataset-card h-100" data-dataset-id="${dataset.dataset_id}">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <h5 class="card-title mb-0">${this.escapeHtml(dataset.dataset_name)}</h5>
                        <span class="badge bg-primary">${dataset.session_count} sessions</span>
                    </div>
                    
                    ${dataset.description ? `<p class="card-text text-muted small">${this.escapeHtml(dataset.description)}</p>` : ''}
                    
                    <div class="mt-auto">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <small class="file-size">${fileSize}</small>
                            <small class="text-muted">${uploadDate}</small>
                        </div>
                        
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="dataset-hash">${shortHash}...</span>
                            <div class="badge bg-success">${dataset.project_count} projects</div>
                        </div>
                    </div>
                </div>
                <div class="card-footer bg-transparent">
                    <button class="btn btn-outline-primary btn-sm w-100" onclick="rawDatasetManager.viewDataset(${dataset.dataset_id})">
                        <i class="fa-solid fa-eye me-2"></i>View Details
                    </button>
                </div>
            </div>
        `;

        return col;
    }

    async validatePath() {
        const pathInput = document.getElementById('dataset-path');
        const path = pathInput.value.trim();
        
        if (!path) return;

        try {
            const response = await fetch('/api/datasets/validate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sourcePath: path })
            });

            const result = await response.json();
            
            if (result.valid) {
                pathInput.classList.remove('is-invalid');
                pathInput.classList.add('is-valid');
            } else {
                pathInput.classList.remove('is-valid');
                pathInput.classList.add('is-invalid');
                this.showError(result.error);
            }
            
        } catch (error) {
            console.error('Error validating path:', error);
            pathInput.classList.remove('is-valid');
            pathInput.classList.add('is-invalid');
        }
    }

    async previewDataset() {
        const form = document.getElementById('upload-dataset-form');
        const formData = new FormData(form);
        const sourcePath = formData.get('sourcePath');

        if (!sourcePath) {
            this.showError('Please enter a source path');
            return;
        }

        const previewBtn = document.getElementById('preview-dataset-btn');
        const originalText = previewBtn.innerHTML;
        previewBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Loading...';
        previewBtn.disabled = true;

        try {
            const response = await fetch('/api/datasets/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sourcePath })
            });

            const result = await response.json();
            
            if (response.ok && result.valid) {
                this.renderPreview(result);
            } else {
                this.showError(result.error || 'Failed to preview dataset');
            }
            
        } catch (error) {
            console.error('Error previewing dataset:', error);
            this.showError('Failed to preview dataset: ' + error.message);
        } finally {
            previewBtn.innerHTML = originalText;
            previewBtn.disabled = false;
        }
    }

    renderPreview(previewData) {
        const previewSection = document.getElementById('dataset-preview');
        const previewContent = document.getElementById('preview-content');

        const fileSize = this.formatFileSize(previewData.file_size_bytes);
        
        previewContent.innerHTML = `
            <div class="row">
                <div class="col-md-4">
                    <div class="card bg-light">
                        <div class="card-body text-center">
                            <h6 class="card-title">Sessions Found</h6>
                            <h3 class="text-primary">${previewData.session_count}</h3>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card bg-light">
                        <div class="card-body text-center">
                            <h6 class="card-title">Total Size</h6>
                            <h5 class="text-info">${fileSize}</h5>
                        </div>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card bg-light">
                        <div class="card-body text-center">
                            <h6 class="card-title">Status</h6>
                            <span class="badge bg-success">Valid</span>
                        </div>
                    </div>
                </div>
            </div>
            
            ${previewData.sessions && previewData.sessions.length > 0 ? `
                <div class="mt-3">
                    <h6>Sessions Preview:</h6>
                    <div class="list-group list-group-flush" style="max-height: 200px; overflow-y: auto;">
                        ${previewData.sessions.slice(0, 10).map(session => `
                            <div class="list-group-item d-flex justify-content-between align-items-center">
                                <span>${this.escapeHtml(session.name)}</span>
                                <small class="text-muted">${session.original_labels ? session.original_labels.length : 0} labels</small>
                            </div>
                        `).join('')}
                        ${previewData.sessions.length > 10 ? `
                            <div class="list-group-item text-center text-muted">
                                ... and ${previewData.sessions.length - 10} more sessions
                            </div>
                        ` : ''}
                    </div>
                </div>
            ` : ''}
        `;

        previewSection.style.display = 'block';
    }

    async uploadDataset() {
        const form = document.getElementById('upload-dataset-form');
        const formData = new FormData(form);

        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        const uploadBtn = document.getElementById('upload-dataset-btn');
        const originalText = uploadBtn.innerHTML;
        uploadBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Uploading...';
        uploadBtn.disabled = true;

        try {
            const response = await fetch('/api/datasets/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();
            
            if (response.ok) {
                if (result.duplicate) {
                    this.showSuccess(`Dataset already exists: ${result.dataset_name}. Using existing dataset.`);
                } else {
                    this.showSuccess(`Dataset "${result.dataset_name}" uploaded successfully!`);
                }
                
                // Close modal and refresh list
                bootstrap.Modal.getInstance(document.getElementById('uploadDatasetModal')).hide();
                this.loadDatasets();
            } else {
                this.showError(result.error || 'Upload failed');
            }
            
        } catch (error) {
            console.error('Error uploading dataset:', error);
            this.showError('Upload failed: ' + error.message);
        } finally {
            uploadBtn.innerHTML = originalText;
            uploadBtn.disabled = false;
        }
    }

    async viewDataset(datasetId) {
        try {
            const response = await fetch(`/api/datasets/${datasetId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const dataset = await response.json();
            this.currentDataset = dataset;
            this.renderDatasetDetail(dataset);
            
            const modal = new bootstrap.Modal(document.getElementById('datasetDetailModal'));
            modal.show();
            
        } catch (error) {
            console.error('Error loading dataset details:', error);
            this.showError('Failed to load dataset details: ' + error.message);
        }
    }

    renderDatasetDetail(dataset) {
        const content = document.getElementById('dataset-detail-content');
        const uploadDate = new Date(dataset.upload_timestamp).toLocaleDateString();
        const fileSize = this.formatFileSize(dataset.file_size_bytes);

        content.innerHTML = `
            <div class="row">
                <div class="col-md-8">
                    <h4>${this.escapeHtml(dataset.dataset_name)}</h4>
                    ${dataset.description ? `<p class="text-muted">${this.escapeHtml(dataset.description)}</p>` : ''}
                    
                    <div class="row mt-4">
                        <div class="col-sm-6">
                            <strong>Upload Date:</strong><br>
                            <span class="text-muted">${uploadDate}</span>
                        </div>
                        <div class="col-sm-6">
                            <strong>File Size:</strong><br>
                            <span class="text-muted">${fileSize}</span>
                        </div>
                    </div>
                    
                    <div class="row mt-3">
                        <div class="col-sm-6">
                            <strong>Sessions:</strong><br>
                            <span class="session-count">${dataset.session_count}</span>
                        </div>
                        <div class="col-sm-6">
                            <strong>Used by Projects:</strong><br>
                            <span class="badge bg-success">${dataset.project_count || 0}</span>
                        </div>
                    </div>
                    
                    <div class="mt-3">
                        <strong>Dataset Hash:</strong><br>
                        <code class="dataset-hash">${dataset.dataset_hash}</code>
                    </div>
                    
                    <div class="mt-3">
                        <strong>File Path:</strong><br>
                        <code class="text-break">${dataset.file_path}</code>
                    </div>
                </div>
                
                <div class="col-md-4">
                    <div class="card">
                        <div class="card-header">
                            <h6 class="card-title mb-0">Sessions in Dataset</h6>
                        </div>
                        <div class="card-body p-0">
                            <div class="list-group list-group-flush" style="max-height: 300px; overflow-y: auto;">
                                ${dataset.sessions && dataset.sessions.length > 0 ? 
                                    dataset.sessions.map(session => `
                                        <div class="list-group-item d-flex justify-content-between align-items-center">
                                            <span>${this.escapeHtml(session.session_name)}</span>
                                            <small class="text-muted">${session.file_count} files</small>
                                        </div>
                                    `).join('') : 
                                    '<div class="list-group-item text-muted">No sessions found</div>'
                                }
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    async deleteCurrentDataset() {
        if (!this.currentDataset) return;

        const confirmDelete = confirm(
            `Are you sure you want to delete the dataset "${this.currentDataset.dataset_name}"?\n\n` +
            `This will permanently delete all raw data files.\n` +
            `This action cannot be undone.`
        );

        if (!confirmDelete) return;

        const deleteBtn = document.getElementById('delete-dataset-btn');
        const originalText = deleteBtn.innerHTML;
        deleteBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Deleting...';
        deleteBtn.disabled = true;

        try {
            const response = await fetch(`/api/datasets/${this.currentDataset.dataset_id}`, {
                method: 'DELETE'
            });

            const result = await response.json();
            
            if (response.ok) {
                this.showSuccess(`Dataset "${result.dataset_name}" deleted successfully!`);
                bootstrap.Modal.getInstance(document.getElementById('datasetDetailModal')).hide();
                this.loadDatasets();
            } else if (response.status === 409) {
                this.showError('Cannot delete dataset: it is referenced by one or more projects');
            } else {
                this.showError(result.error || 'Failed to delete dataset');
            }
            
        } catch (error) {
            console.error('Error deleting dataset:', error);
            this.showError('Failed to delete dataset: ' + error.message);
        } finally {
            deleteBtn.innerHTML = originalText;
            deleteBtn.disabled = false;
        }
    }

    resetUploadForm() {
        const form = document.getElementById('upload-dataset-form');
        form.reset();
        form.classList.remove('was-validated');
        
        // Reset validation states
        const inputs = form.querySelectorAll('.form-control');
        inputs.forEach(input => {
            input.classList.remove('is-valid', 'is-invalid');
        });

        // Hide preview
        document.getElementById('dataset-preview').style.display = 'none';
    }

    async loadDatasetsForProjectCreation() {
        try {
            const response = await fetch('/api/datasets');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const datasets = await response.json();
            this.renderDatasetSelection(datasets);
            
        } catch (error) {
            console.error('Error loading datasets for project creation:', error);
            this.showError('Failed to load datasets: ' + error.message);
        }
    }

    renderDatasetSelection(datasets) {
        const container = document.getElementById('dataset-selection');
        
        if (datasets.length === 0) {
            container.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="fa-solid fa-database" style="font-size: 2rem; opacity: 0.3;"></i>
                    <p class="mb-0 mt-2">No datasets available</p>
                    <small>Upload some datasets first</small>
                </div>
            `;
            return;
        }

        container.innerHTML = datasets.map(dataset => {
            const uploadDate = new Date(dataset.upload_timestamp).toLocaleDateString();
            const fileSize = this.formatFileSize(dataset.file_size_bytes);
            
            return `
                <div class="form-check border rounded p-3 mb-2">
                    <input class="form-check-input" type="checkbox" value="${dataset.dataset_id}" 
                           id="dataset-${dataset.dataset_id}" name="dataset_ids">
                    <label class="form-check-label w-100" for="dataset-${dataset.dataset_id}">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h6 class="mb-1">${this.escapeHtml(dataset.dataset_name)}</h6>
                                ${dataset.description ? `<p class="text-muted small mb-1">${this.escapeHtml(dataset.description)}</p>` : ''}
                                <div class="d-flex gap-3 small text-muted">
                                    <span><i class="fa-solid fa-calendar me-1"></i>${uploadDate}</span>
                                    <span><i class="fa-solid fa-weight-scale me-1"></i>${fileSize}</span>
                                </div>
                            </div>
                            <div class="text-end">
                                <div class="badge bg-primary">${dataset.session_count} sessions</div>
                                ${dataset.project_count > 0 ? `<div class="badge bg-success mt-1">${dataset.project_count} projects</div>` : ''}
                            </div>
                        </div>
                    </label>
                </div>
            `;
        }).join('');
    }

    async createProjectFromDatasets() {
        const form = document.getElementById('create-project-form');
        const formData = new FormData(form);
        
        if (!form.checkValidity()) {
            form.reportValidity();
            return;
        }

        // Get selected datasets
        const selectedDatasets = Array.from(
            form.querySelectorAll('input[name="dataset_ids"]:checked')
        ).map(input => parseInt(input.value));

        if (selectedDatasets.length === 0) {
            this.showError('Please select at least one dataset');
            return;
        }

        const createBtn = document.getElementById('create-project-btn');
        const originalText = createBtn.innerHTML;
        createBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Creating...';
        createBtn.disabled = true;

        try {
            const projectData = {
                name: formData.get('name'),
                participant: formData.get('participant'),
                description: formData.get('description'),
                dataset_ids: selectedDatasets,
                split_configs: {} // Future enhancement
            };

            const response = await fetch('/api/projects/create-from-datasets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(projectData)
            });

            const result = await response.json();
            
            if (response.ok) {
                this.showSuccess(
                    `Project "${result.project_name}" created successfully with ${result.dataset_count} dataset(s)!`
                );
                
                // Close modal
                bootstrap.Modal.getInstance(document.getElementById('createProjectModal')).hide();
                
                // Refresh datasets list to show updated project counts
                this.loadDatasets();
            } else {
                this.showError(result.error || 'Failed to create project');
            }
            
        } catch (error) {
            console.error('Error creating project:', error);
            this.showError('Failed to create project: ' + error.message);
        } finally {
            createBtn.innerHTML = originalText;
            createBtn.disabled = false;
        }
    }

    resetProjectForm() {
        const form = document.getElementById('create-project-form');
        form.reset();
        form.classList.remove('was-validated');
        
        // Reset validation states
        const inputs = form.querySelectorAll('.form-control');
        inputs.forEach(input => {
            input.classList.remove('is-valid', 'is-invalid');
        });

        // Clear dataset selection
        document.getElementById('dataset-selection').innerHTML = '';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }

    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    showSuccess(message) {
        // Simple alert for now - could be enhanced with toast notifications
        alert(`Success: ${message}`);
    }

    showError(message) {
        // Simple alert for now - could be enhanced with toast notifications
        alert(`Error: ${message}`);
        console.error('RawDatasetManager Error:', message);
    }

    async scanAndRegisterDatasets() {
        const scanBtn = document.getElementById('scan-datasets-btn');
        const originalText = scanBtn.innerHTML;
        scanBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-2"></i>Scanning...';
        scanBtn.disabled = true;

        try {
            const response = await fetch('/api/datasets/scan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });

            const result = await response.json();
            
            if (response.ok) {
                let message = `Scan complete!\n\n`;
                message += `Datasets found: ${result.datasets_found}\n`;
                message += `Datasets registered: ${result.datasets_registered}\n`;
                message += `Datasets skipped: ${result.datasets_skipped}\n`;
                
                if (result.errors && result.errors.length > 0) {
                    message += `\nErrors:\n${result.errors.join('\n')}`;
                }
                
                if (result.datasets_registered > 0) {
                    this.showSuccess(message);
                    this.loadDatasets(); // Refresh the list to show new datasets
                } else {
                    alert(message);
                }
            } else {
                this.showError(result.error || 'Scan and register failed');
            }
            
        } catch (error) {
            console.error('Error scanning and registering datasets:', error);
            this.showError('Scan and register failed: ' + error.message);
        } finally {
            scanBtn.innerHTML = originalText;
            scanBtn.disabled = false;
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.rawDatasetManager = new RawDatasetManager();
});