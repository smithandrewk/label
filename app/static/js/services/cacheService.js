/**
 * Frontend Cache Service
 * Provides smart caching for API responses using localStorage
 * Includes cache invalidation, compression, and performance tracking
 */

export class CacheService {
    constructor() {
        this.prefix = 'label_app_cache_';
        this.maxAge = 5 * 60 * 1000; // 5 minutes default
        this.maxCacheSize = 50 * 1024 * 1024; // 50MB max cache size
        this.compressionThreshold = 1024; // Compress items larger than 1KB
        
        // Performance tracking
        this.stats = {
            hits: 0,
            misses: 0,
            stores: 0,
            evictions: 0
        };
        
        this.initCache();
    }
    
    initCache() {
        // Clean up expired entries on initialization
        this.cleanupExpired();
        
        // Track cache performance
        console.log('🗄️ CacheService initialized');
        this.logStats();
    }
    
    /**
     * Generate cache key with version info
     */
    generateKey(baseKey, version = '1.0') {
        return `${this.prefix}${baseKey}_v${version}`;
    }
    
    /**
     * Store data in cache with optional compression
     */
    set(key, data, maxAge = this.maxAge) {
        try {
            const fullKey = this.generateKey(key);
            const timestamp = Date.now();
            
            const cacheEntry = {
                data: data,
                timestamp: timestamp,
                expires: timestamp + maxAge,
                compressed: false,
                originalSize: 0,
                compressedSize: 0
            };
            
            // Serialize the data
            let serialized = JSON.stringify(cacheEntry);
            cacheEntry.originalSize = serialized.length;
            
            // Simple compression for large items (JSON.stringify is already compact)
            if (serialized.length > this.compressionThreshold) {
                // For now, we'll just track that we could compress
                cacheEntry.compressed = true;
                cacheEntry.compressedSize = serialized.length; // Would be smaller with real compression
            }
            
            // Check cache size limits
            if (this.getCurrentCacheSize() + serialized.length > this.maxCacheSize) {
                this.evictOldest();
            }
            
            localStorage.setItem(fullKey, serialized);
            this.stats.stores++;
            
            console.log(`📦 Cached ${key}: ${(serialized.length / 1024).toFixed(1)}KB, expires in ${maxAge/1000}s`);
            
            return true;
        } catch (error) {
            console.error('Cache storage error:', error);
            // Likely localStorage is full, try to make space
            this.evictOldest();
            return false;
        }
    }
    
    /**
     * Retrieve data from cache
     */
    get(key) {
        try {
            const fullKey = this.generateKey(key);
            const cached = localStorage.getItem(fullKey);
            
            if (!cached) {
                this.stats.misses++;
                return null;
            }
            
            const cacheEntry = JSON.parse(cached);
            
            // Check expiration
            if (Date.now() > cacheEntry.expires) {
                localStorage.removeItem(fullKey);
                this.stats.misses++;
                console.log(`⏰ Cache expired for ${key}`);
                return null;
            }
            
            this.stats.hits++;
            const age = (Date.now() - cacheEntry.timestamp) / 1000;
            console.log(`🎯 Cache hit for ${key} (age: ${age.toFixed(1)}s)`);
            
            return cacheEntry.data;
        } catch (error) {
            console.error('Cache retrieval error:', error);
            this.stats.misses++;
            return null;
        }
    }
    
    /**
     * Check if key exists and is valid
     */
    has(key) {
        return this.get(key) !== null;
    }
    
    /**
     * Remove specific cache entry
     */
    remove(key) {
        const fullKey = this.generateKey(key);
        localStorage.removeItem(fullKey);
        console.log(`🗑️ Removed cache entry: ${key}`);
    }
    
    /**
     * Clear all cache entries
     */
    clear() {
        const keys = Object.keys(localStorage).filter(key => key.startsWith(this.prefix));
        keys.forEach(key => localStorage.removeItem(key));
        console.log(`🧹 Cleared ${keys.length} cache entries`);
        
        // Reset stats
        this.stats = { hits: 0, misses: 0, stores: 0, evictions: 0 };
    }
    
    /**
     * Clean up expired entries
     */
    cleanupExpired() {
        let cleaned = 0;
        const keys = Object.keys(localStorage).filter(key => key.startsWith(this.prefix));
        
        keys.forEach(key => {
            try {
                const cached = localStorage.getItem(key);
                if (cached) {
                    const cacheEntry = JSON.parse(cached);
                    if (Date.now() > cacheEntry.expires) {
                        localStorage.removeItem(key);
                        cleaned++;
                    }
                }
            } catch (error) {
                // Remove corrupted entries
                localStorage.removeItem(key);
                cleaned++;
            }
        });
        
        if (cleaned > 0) {
            console.log(`🧹 Cleaned up ${cleaned} expired cache entries`);
        }
    }
    
    /**
     * Evict oldest entries to make space
     */
    evictOldest() {
        const entries = [];
        const keys = Object.keys(localStorage).filter(key => key.startsWith(this.prefix));
        
        keys.forEach(key => {
            try {
                const cached = localStorage.getItem(key);
                if (cached) {
                    const cacheEntry = JSON.parse(cached);
                    entries.push({ key, timestamp: cacheEntry.timestamp, size: cached.length });
                }
            } catch (error) {
                // Remove corrupted entries
                localStorage.removeItem(key);
            }
        });
        
        // Sort by timestamp (oldest first) and remove 25%
        entries.sort((a, b) => a.timestamp - b.timestamp);
        const toRemove = Math.ceil(entries.length * 0.25);
        
        for (let i = 0; i < toRemove; i++) {
            localStorage.removeItem(entries[i].key);
            this.stats.evictions++;
        }
        
        console.log(`🗑️ Evicted ${toRemove} oldest cache entries`);
    }
    
    /**
     * Get current cache size
     */
    getCurrentCacheSize() {
        let totalSize = 0;
        const keys = Object.keys(localStorage).filter(key => key.startsWith(this.prefix));
        
        keys.forEach(key => {
            const value = localStorage.getItem(key);
            if (value) {
                totalSize += value.length * 2; // Rough estimate (UTF-16)
            }
        });
        
        return totalSize;
    }
    
    /**
     * Get cache statistics
     */
    getStats() {
        const hitRate = this.stats.hits + this.stats.misses > 0 
            ? (this.stats.hits / (this.stats.hits + this.stats.misses) * 100).toFixed(1)
            : 0;
            
        return {
            ...this.stats,
            hitRate: `${hitRate}%`,
            totalSize: `${(this.getCurrentCacheSize() / 1024 / 1024).toFixed(2)}MB`,
            entryCount: Object.keys(localStorage).filter(key => key.startsWith(this.prefix)).length
        };
    }
    
    /**
     * Log cache performance stats
     */
    logStats() {
        const stats = this.getStats();
        console.log('📊 Cache Stats:', stats);
    }
    
    /**
     * Smart cache strategy for session data
     */
    cacheSessionData(sessionId, data, isPaginated = false) {
        const key = isPaginated 
            ? `session_${sessionId}_paginated`
            : `session_${sessionId}_full`;
            
        // Longer cache time for session data since it doesn't change often
        const maxAge = 10 * 60 * 1000; // 10 minutes
        
        return this.set(key, data, maxAge);
    }
    
    /**
     * Get cached session data
     */
    getCachedSessionData(sessionId, isPaginated = false) {
        const key = isPaginated 
            ? `session_${sessionId}_paginated`
            : `session_${sessionId}_full`;
            
        return this.get(key);
    }
    
    /**
     * Cache project/session lists (shorter cache time since they change more)
     */
    cacheList(type, data) {
        const maxAge = 2 * 60 * 1000; // 2 minutes for lists
        return this.set(`${type}_list`, data, maxAge);
    }
    
    /**
     * Get cached list data
     */
    getCachedList(type) {
        return this.get(`${type}_list`);
    }
}

// Export singleton instance
export const cacheService = new CacheService();
export default cacheService;