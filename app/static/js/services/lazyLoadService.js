/**
 * Lazy Loading Service
 * Implements progressive loading, viewport-based optimization, and background prefetching
 * for improved performance on remote connections
 */

import SessionAPI from '../api/sessionAPI.js';
import { cacheService } from './cacheService.js';

export class LazyLoadService {
    constructor() {
        this.loadingQueue = new Map(); // Track what's currently loading
        this.prefetchQueue = new Set(); // Track what to prefetch next
        this.viewportObserver = null;
        this.prefetchDelay = 2000; // 2 second delay before prefetching
        this.chunkSize = 1000; // Default chunk size for pagination
        
        this.stats = {
            lazyLoads: 0,
            prefetches: 0,
            cacheHits: 0,
            bandwidthSaved: 0
        };
        
        this.initViewportObserver();
        console.log('🔄 LazyLoadService initialized');
    }
    
    /**
     * Initialize Intersection Observer for viewport-based loading
     */
    initViewportObserver() {
        if ('IntersectionObserver' in window) {
            this.viewportObserver = new IntersectionObserver(
                this.handleViewportIntersection.bind(this),
                {
                    root: null,
                    rootMargin: '200px', // Start loading 200px before element comes into view
                    threshold: 0.1
                }
            );
        }
    }
    
    /**
     * Handle viewport intersection events
     */
    handleViewportIntersection(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const element = entry.target;
                const sessionId = element.dataset.sessionId;
                
                if (sessionId && !this.loadingQueue.has(sessionId)) {
                    console.log(`👁️ Session ${sessionId} entering viewport - lazy loading`);
                    this.lazyLoadSessionData(sessionId, element);
                }
            }
        });
    }
    
    /**
     * Observe an element for viewport-based lazy loading
     */
    observeElement(element, sessionId) {
        if (this.viewportObserver && element) {
            element.dataset.sessionId = sessionId;
            this.viewportObserver.observe(element);
        }
    }
    
    /**
     * Stop observing an element
     */
    unobserveElement(element) {
        if (this.viewportObserver && element) {
            this.viewportObserver.unobserve(element);
        }
    }
    
    /**
     * Lazy load session data with progressive loading
     */
    async lazyLoadSessionData(sessionId, element = null) {
        // Check if already loading
        if (this.loadingQueue.has(sessionId)) {
            return this.loadingQueue.get(sessionId);
        }
        
        // Check cache first
        const cached = cacheService.getCachedSessionData(sessionId, false);
        if (cached) {
            this.stats.cacheHits++;
            console.log(`🎯 Lazy load cache hit for session ${sessionId}`);
            this.updateElementWithData(element, cached);
            return cached;
        }
        
        // Show loading state
        if (element) {
            this.showLoadingState(element);
        }
        
        // Start progressive loading
        const loadPromise = this.progressiveLoadSession(sessionId, element);
        this.loadingQueue.set(sessionId, loadPromise);
        
        try {
            const result = await loadPromise;
            this.stats.lazyLoads++;
            
            // Schedule prefetch of related sessions
            this.schedulePrefetch(sessionId);
            
            return result;
        } finally {
            this.loadingQueue.delete(sessionId);
        }
    }
    
    /**
     * Progressive loading: Load data in chunks starting with most important
     */
    async progressiveLoadSession(sessionId, element) {
        try {
            // Phase 1: Load initial chunk (first 1000 points)
            console.log(`📊 Phase 1: Loading initial chunk for session ${sessionId}`);
            const initialData = await SessionAPI.loadSessionData(sessionId, {
                useCache: true,
                offset: 0,
                limit: this.chunkSize
            });
            
            // Update UI with initial data immediately
            if (element) {
                this.updateElementWithData(element, initialData, false);
            }
            
            // Phase 2: Check if more data is needed
            const pagination = initialData.pagination;
            if (pagination && pagination.has_more) {
                console.log(`📊 Phase 2: More data available for session ${sessionId}`);
                
                // Load remaining data in background if session is in viewport
                if (this.isElementInViewport(element)) {
                    this.loadRemainingDataInBackground(sessionId, element, initialData);
                }
            }
            
            return initialData;
            
        } catch (error) {
            console.error(`Error in progressive loading for session ${sessionId}:`, error);
            if (element) {
                this.showErrorState(element, error);
            }
            throw error;
        }
    }
    
    /**
     * Load remaining data in background
     */
    async loadRemainingDataInBackground(sessionId, element, initialData) {
        try {
            const pagination = initialData.pagination;
            const totalEstimate = pagination.estimated_total || 0;
            const loaded = pagination.returned_count || 0;
            
            if (loaded >= totalEstimate) return;
            
            console.log(`🔄 Background loading remaining data for session ${sessionId}`);
            
            // Load full dataset
            const fullData = await SessionAPI.loadSessionData(sessionId, {
                useCache: true,
                offset: 0,
                limit: 0 // 0 means load all
            });
            
            // Update UI with complete data
            if (element && this.isElementInViewport(element)) {
                this.updateElementWithData(element, fullData, true);
            }
            
        } catch (error) {
            console.error(`Error loading remaining data for session ${sessionId}:`, error);
        }
    }
    
    /**
     * Schedule prefetching of related sessions
     */
    schedulePrefetch(sessionId) {
        // Simple strategy: prefetch next/previous sessions by ID
        const nextSessionId = parseInt(sessionId) + 1;
        const prevSessionId = parseInt(sessionId) - 1;
        
        if (prevSessionId > 0) {
            this.prefetchQueue.add(prevSessionId.toString());
        }
        this.prefetchQueue.add(nextSessionId.toString());
        
        // Start prefetching after delay
        setTimeout(() => {
            this.processPrefetchQueue();
        }, this.prefetchDelay);
    }
    
    /**
     * Process prefetch queue in background
     */
    async processPrefetchQueue() {
        if (this.prefetchQueue.size === 0) return;
        
        // Only prefetch if not too many active loads
        if (this.loadingQueue.size > 2) {
            console.log('🔄 Delaying prefetch - too many active loads');
            return;
        }
        
        const sessionId = Array.from(this.prefetchQueue)[0];
        this.prefetchQueue.delete(sessionId);
        
        // Check if already cached
        if (cacheService.getCachedSessionData(sessionId, false)) {
            console.log(`🎯 Skipping prefetch for session ${sessionId} - already cached`);
            return;
        }
        
        try {
            console.log(`⚡ Prefetching session ${sessionId} in background`);
            await SessionAPI.loadSessionData(sessionId, {
                useCache: true,
                offset: 0,
                limit: this.chunkSize // Just prefetch initial chunk
            });
            
            this.stats.prefetches++;
            this.stats.bandwidthSaved += this.chunkSize * 50; // Estimate bytes saved on future access
            
        } catch (error) {
            console.log(`⚠️ Prefetch failed for session ${sessionId}:`, error.message);
        }
        
        // Continue processing queue
        if (this.prefetchQueue.size > 0) {
            setTimeout(() => {
                this.processPrefetchQueue();
            }, 1000); // 1 second between prefetches
        }
    }
    
    /**
     * Check if element is in viewport
     */
    isElementInViewport(element) {
        if (!element) return false;
        
        const rect = element.getBoundingClientRect();
        return (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
    }
    
    /**
     * Update element with loaded data
     */
    updateElementWithData(element, data, isComplete = true) {
        if (!element) return;
        
        // Remove loading state
        element.classList.remove('lazy-loading', 'lazy-error');
        
        // Add data attributes
        element.dataset.loaded = 'true';
        element.dataset.complete = isComplete.toString();
        element.dataset.dataPoints = data.data?.length || 0;
        
        // Dispatch custom event for other components to handle
        const event = new CustomEvent('sessionDataLoaded', {
            detail: {
                sessionId: element.dataset.sessionId,
                data: data,
                isComplete: isComplete
            }
        });
        element.dispatchEvent(event);
        
        console.log(`✅ Updated element with ${data.data?.length || 0} data points (complete: ${isComplete})`);
    }
    
    /**
     * Show loading state on element
     */
    showLoadingState(element) {
        if (!element) return;
        
        element.classList.add('lazy-loading');
        element.classList.remove('lazy-error');
        
        // Add loading indicator if it doesn't exist
        if (!element.querySelector('.lazy-loading-indicator')) {
            const indicator = document.createElement('div');
            indicator.className = 'lazy-loading-indicator';
            indicator.innerHTML = '🔄 Loading...';
            indicator.style.cssText = `
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: rgba(0, 0, 0, 0.8);
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-size: 12px;
                z-index: 1000;
            `;
            element.style.position = 'relative';
            element.appendChild(indicator);
        }
    }
    
    /**
     * Show error state on element
     */
    showErrorState(element, error) {
        if (!element) return;
        
        element.classList.add('lazy-error');
        element.classList.remove('lazy-loading');
        
        // Remove loading indicator
        const indicator = element.querySelector('.lazy-loading-indicator');
        if (indicator) {
            indicator.remove();
        }
        
        // Add error indicator
        const errorIndicator = document.createElement('div');
        errorIndicator.className = 'lazy-error-indicator';
        errorIndicator.innerHTML = `❌ Failed to load`;
        errorIndicator.style.cssText = `
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: rgba(244, 67, 54, 0.9);
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 1000;
            cursor: pointer;
        `;
        
        // Allow retry on click
        errorIndicator.onclick = () => {
            errorIndicator.remove();
            this.lazyLoadSessionData(element.dataset.sessionId, element);
        };
        
        element.appendChild(errorIndicator);
        
        console.error(`❌ Lazy load error for session ${element.dataset.sessionId}:`, error);
    }
    
    /**
     * Get lazy loading statistics
     */
    getStats() {
        const totalRequests = this.stats.lazyLoads + this.stats.cacheHits;
        const cacheHitRate = totalRequests > 0 ? (this.stats.cacheHits / totalRequests * 100).toFixed(1) : 0;
        
        return {
            ...this.stats,
            cacheHitRate: `${cacheHitRate}%`,
            activeLoads: this.loadingQueue.size,
            prefetchQueue: this.prefetchQueue.size,
            bandwidthSavedKB: `${(this.stats.bandwidthSaved / 1024).toFixed(1)}KB`
        };
    }
    
    /**
     * Clear all loading states and queues
     */
    clear() {
        this.loadingQueue.clear();
        this.prefetchQueue.clear();
        
        // Remove all loading indicators
        document.querySelectorAll('.lazy-loading-indicator, .lazy-error-indicator').forEach(el => {
            el.remove();
        });
        
        console.log('🧹 LazyLoadService cleared');
    }
    
    /**
     * Destroy the service
     */
    destroy() {
        this.clear();
        if (this.viewportObserver) {
            this.viewportObserver.disconnect();
        }
    }
}

// Export singleton instance
export const lazyLoadService = new LazyLoadService();
export default lazyLoadService;