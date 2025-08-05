/**
 * Pagination Service
 * Handles frontend pagination for large datasets with virtual scrolling support
 */

import SessionAPI from '../api/sessionAPI.js';
import { cacheService } from './cacheService.js';

export class PaginationService {
    constructor() {
        this.activePaginators = new Map(); // Track active pagination instances
        this.defaultPageSize = 1000;
        this.bufferSize = 500; // Extra items to load for smooth scrolling
        
        this.stats = {
            pagesLoaded: 0,
            totalItemsLoaded: 0,
            averageLoadTime: 0
        };
        
        console.log('📄 PaginationService initialized');
    }
    
    /**
     * Create a new paginator for a dataset
     */
    createPaginator(config) {
        const {
            id,
            sessionId,
            pageSize = this.defaultPageSize,
            onDataLoaded,
            onLoadStart,
            onLoadEnd,
            onError
        } = config;
        
        const paginator = new DataPaginator({
            id,
            sessionId,
            pageSize,
            bufferSize: this.bufferSize,
            onDataLoaded,
            onLoadStart,
            onLoadEnd,
            onError,
            paginationService: this
        });
        
        this.activePaginators.set(id, paginator);
        console.log(`📄 Created paginator ${id} for session ${sessionId}`);
        
        return paginator;
    }
    
    /**
     * Get existing paginator
     */
    getPaginator(id) {
        return this.activePaginators.get(id);
    }
    
    /**
     * Remove paginator
     */
    removePaginator(id) {
        const paginator = this.activePaginators.get(id);
        if (paginator) {
            paginator.destroy();
            this.activePaginators.delete(id);
            console.log(`📄 Removed paginator ${id}`);
        }
    }
    
    /**
     * Update statistics
     */
    updateStats(loadTime, itemsLoaded) {
        this.stats.pagesLoaded++;
        this.stats.totalItemsLoaded += itemsLoaded;
        
        // Update average load time
        const currentAvg = this.stats.averageLoadTime;
        const count = this.stats.pagesLoaded;
        this.stats.averageLoadTime = ((currentAvg * (count - 1)) + loadTime) / count;
    }
    
    /**
     * Get pagination statistics
     */
    getStats() {
        return {
            ...this.stats,
            averageLoadTime: `${this.stats.averageLoadTime.toFixed(0)}ms`,
            activePaginators: this.activePaginators.size,
            avgItemsPerPage: this.stats.pagesLoaded > 0 ? 
                Math.round(this.stats.totalItemsLoaded / this.stats.pagesLoaded) : 0
        };
    }
    
    /**
     * Clear all paginators
     */
    clear() {
        this.activePaginators.forEach((paginator, id) => {
            this.removePaginator(id);
        });
    }
}

/**
 * Individual Data Paginator Class
 */
class DataPaginator {
    constructor(config) {
        this.id = config.id;
        this.sessionId = config.sessionId;
        this.pageSize = config.pageSize;
        this.bufferSize = config.bufferSize;
        this.paginationService = config.paginationService;
        
        // Callbacks
        this.onDataLoaded = config.onDataLoaded || (() => {});
        this.onLoadStart = config.onLoadStart || (() => {});
        this.onLoadEnd = config.onLoadEnd || (() => {});
        this.onError = config.onError || (() => {});
        
        // State
        this.currentPage = 0;
        this.totalPages = 0;
        this.totalItems = 0;
        this.loadedPages = new Set();
        this.data = []; // All loaded data
        this.isLoading = false;
        this.hasMore = true;
        
        // Cache
        this.pageCache = new Map();
        
        console.log(`📄 DataPaginator ${this.id} created (pageSize: ${this.pageSize})`);
    }
    
    /**
     * Load a specific page
     */
    async loadPage(pageNumber, force = false) {
        if (this.isLoading && !force) {
            console.log(`📄 Page ${pageNumber} already loading`);
            return;
        }
        
        if (this.loadedPages.has(pageNumber) && !force) {
            console.log(`📄 Page ${pageNumber} already loaded`);
            return this.getPageData(pageNumber);
        }
        
        this.isLoading = true;
        this.onLoadStart(pageNumber);
        
        const offset = pageNumber * this.pageSize;
        const cacheKey = `${this.sessionId}_page_${pageNumber}`;
        
        try {
            console.log(`📄 Loading page ${pageNumber} (offset: ${offset}, limit: ${this.pageSize})`);
            
            const startTime = performance.now();
            
            // Check cache first
            let pageData = this.pageCache.get(pageNumber);
            if (!pageData) {
                const response = await SessionAPI.loadSessionData(this.sessionId, {
                    useCache: true,
                    offset: offset,
                    limit: this.pageSize
                });
                
                pageData = {
                    data: response.data || [],
                    pagination: response.pagination || {},
                    bouts: response.bouts || [],
                    session_info: response.session_info || {}
                };
                
                // Cache the page
                this.pageCache.set(pageNumber, pageData);
            }
            
            const loadTime = performance.now() - startTime;
            
            // Update state
            this.loadedPages.add(pageNumber);
            this.hasMore = pageData.pagination.has_more || false;
            this.totalItems = pageData.pagination.estimated_total || 0;
            this.totalPages = Math.ceil(this.totalItems / this.pageSize);
            
            // Insert data into the correct position
            const startIndex = offset;
            const endIndex = startIndex + pageData.data.length;
            
            // Ensure data array is large enough
            while (this.data.length < endIndex) {
                this.data.push(null);
            }
            
            // Insert page data
            for (let i = 0; i < pageData.data.length; i++) {
                this.data[startIndex + i] = pageData.data[i];
            }
            
            // Update statistics
            this.paginationService.updateStats(loadTime, pageData.data.length);
            
            // Notify callback
            this.onDataLoaded({
                pageNumber,
                pageData: pageData.data,
                totalItems: this.totalItems,
                hasMore: this.hasMore,
                loadTime
            });
            
            console.log(`✅ Loaded page ${pageNumber}: ${pageData.data.length} items in ${loadTime.toFixed(0)}ms`);
            
            return pageData;
            
        } catch (error) {
            console.error(`❌ Error loading page ${pageNumber}:`, error);
            this.onError(error, pageNumber);
            throw error;
            
        } finally {
            this.isLoading = false;
            this.onLoadEnd(pageNumber);
        }
    }
    
    /**
     * Load next page
     */
    async loadNextPage() {
        if (!this.hasMore) {
            console.log('📄 No more pages to load');
            return null;
        }
        
        const nextPage = this.currentPage + 1;
        const result = await this.loadPage(nextPage);
        this.currentPage = nextPage;
        return result;
    }
    
    /**
     * Load previous page
     */
    async loadPreviousPage() {
        if (this.currentPage <= 0) {
            console.log('📄 Already at first page');
            return null;
        }
        
        const prevPage = this.currentPage - 1;
        const result = await this.loadPage(prevPage);
        this.currentPage = prevPage;
        return result;
    }
    
    /**
     * Load multiple pages (for virtual scrolling)
     */
    async loadPageRange(startPage, endPage) {
        const promises = [];
        
        for (let page = startPage; page <= endPage; page++) {
            if (!this.loadedPages.has(page)) {
                promises.push(this.loadPage(page));
            }
        }
        
        if (promises.length > 0) {
            console.log(`📄 Loading page range ${startPage}-${endPage} (${promises.length} pages)`);
            await Promise.all(promises);
        }
    }
    
    /**
     * Get data for a specific page
     */
    getPageData(pageNumber) {
        return this.pageCache.get(pageNumber);
    }
    
    /**
     * Get data for a specific range
     */
    getDataRange(startIndex, endIndex) {
        return this.data.slice(startIndex, endIndex);
    }
    
    /**
     * Get item at specific index
     */
    getItem(index) {
        return this.data[index];
    }
    
    /**
     * Check if data is loaded for index
     */
    isIndexLoaded(index) {
        return this.data[index] !== null && this.data[index] !== undefined;
    }
    
    /**
     * Preload pages around current position for smooth scrolling
     */
    async preloadAround(centerPage, radius = 1) {
        const startPage = Math.max(0, centerPage - radius);
        const endPage = Math.min(this.totalPages - 1, centerPage + radius);
        
        console.log(`📄 Preloading pages around ${centerPage} (${startPage}-${endPage})`);
        await this.loadPageRange(startPage, endPage);
    }
    
    /**
     * Reset paginator
     */
    reset() {
        this.currentPage = 0;
        this.totalPages = 0;
        this.totalItems = 0;
        this.loadedPages.clear();
        this.data = [];
        this.pageCache.clear();
        this.hasMore = true;
        
        console.log(`📄 Reset paginator ${this.id}`);
    }
    
    /**
     * Get current state
     */
    getState() {
        return {
            id: this.id,
            sessionId: this.sessionId,
            currentPage: this.currentPage,
            totalPages: this.totalPages,
            totalItems: this.totalItems,
            loadedPages: Array.from(this.loadedPages),
            hasMore: this.hasMore,
            isLoading: this.isLoading,
            cachedPages: this.pageCache.size,
            dataLength: this.data.length
        };
    }
    
    /**
     * Destroy paginator
     */
    destroy() {
        this.reset();
        console.log(`📄 Destroyed paginator ${this.id}`);
    }
}

// Export singleton instance
export const paginationService = new PaginationService();
export default paginationService;