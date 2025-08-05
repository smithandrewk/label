/**
 * Cache Debug Panel
 * Shows cache performance and allows manual cache management
 */

import { cacheService } from '../services/cacheService.js';
import { lazyLoadService } from '../services/lazyLoadService.js';
import { paginationService } from '../services/paginationService.js';

export class CacheDebugPanel {
    constructor() {
        this.isVisible = false;
        this.panel = null;
        this.updateInterval = null;
        
        // Only show in development or when debug param is present
        this.shouldShow = window.location.hostname === 'localhost' || 
                         window.location.search.includes('debug=true');
                         
        if (this.shouldShow) {
            this.init();
        }
    }
    
    init() {
        this.createPanel();
        this.bindEvents();
        
        // Auto-update stats every 5 seconds when visible
        this.startAutoUpdate();
        
        console.log('🐛 Cache Debug Panel initialized (Ctrl+Shift+C to toggle)');
    }
    
    createPanel() {
        // Create floating debug panel
        this.panel = document.createElement('div');
        this.panel.id = 'cache-debug-panel';
        this.panel.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            width: 300px;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            z-index: 10000;
            display: none;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
        `;
        
        document.body.appendChild(this.panel);
        this.updatePanel();
    }
    
    updatePanel() {
        if (!this.panel) return;
        
        const cacheStats = cacheService.getStats();
        const lazyStats = lazyLoadService.getStats();
        const paginationStats = paginationService.getStats();
        
        this.panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h3 style="margin: 0; color: #4CAF50;">⚡ Performance Monitor</h3>
                <button id="cache-clear-btn" style="background: #f44336; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer;">Clear All</button>
            </div>
            
            <!-- Cache Stats -->
            <div style="margin-bottom: 12px;">
                <h4 style="margin: 0 0 6px 0; color: #81C784; font-size: 12px;">🗄️ CACHE</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 11px;">
                    <div>
                        <div style="color: #81C784;">Hits: ${cacheStats.hits}</div>
                        <div style="color: #FFAB91;">Misses: ${cacheStats.misses}</div>
                        <div style="color: #90CAF9;">Rate: ${cacheStats.hitRate}</div>
                    </div>
                    <div>
                        <div style="color: #CE93D8;">Stores: ${cacheStats.stores}</div>
                        <div style="color: #A5D6A7;">Entries: ${cacheStats.entryCount}</div>
                        <div style="color: #B39DDB;">Size: ${cacheStats.totalSize}</div>
                    </div>
                </div>
            </div>
            
            <!-- Lazy Loading Stats -->
            <div style="margin-bottom: 12px;">
                <h4 style="margin: 0 0 6px 0; color: #FFC107; font-size: 12px;">🔄 LAZY LOADING</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 11px;">
                    <div>
                        <div style="color: #FFC107;">Lazy: ${lazyStats.lazyLoads}</div>
                        <div style="color: #FF9800;">Prefetch: ${lazyStats.prefetches}</div>
                        <div style="color: #4CAF50;">Cache Rate: ${lazyStats.cacheHitRate}</div>
                    </div>
                    <div>
                        <div style="color: #2196F3;">Active: ${lazyStats.activeLoads}</div>
                        <div style="color: #9C27B0;">Queue: ${lazyStats.prefetchQueue}</div>
                        <div style="color: #00BCD4;">Saved: ${lazyStats.bandwidthSavedKB}</div>
                    </div>
                </div>
            </div>
            
            <!-- Pagination Stats -->
            <div style="margin-bottom: 12px;">
                <h4 style="margin: 0 0 6px 0; color: #E91E63; font-size: 12px;">📄 PAGINATION</h4>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 11px;">
                    <div>
                        <div style="color: #E91E63;">Pages: ${paginationStats.pagesLoaded}</div>
                        <div style="color: #FF5722;">Items: ${paginationStats.totalItemsLoaded}</div>
                        <div style="color: #795548;">Avg Time: ${paginationStats.averageLoadTime}</div>
                    </div>
                    <div>
                        <div style="color: #607D8B;">Active: ${paginationStats.activePaginators}</div>
                        <div style="color: #9E9E9E;">Per Page: ${paginationStats.avgItemsPerPage}</div>
                        <div></div>
                    </div>
                </div>
            </div>
            
            <!-- Cache Size Bar -->
            <div style="margin-bottom: 12px;">
                <div style="background: #333; height: 6px; border-radius: 3px; overflow: hidden;">
                    <div style="background: linear-gradient(90deg, #4CAF50, #FFC107, #F44336); height: 100%; width: ${Math.min(100, parseFloat(cacheStats.totalSize) / 50 * 100)}%;"></div>
                </div>
                <div style="font-size: 9px; color: #999; margin-top: 2px;">Cache Usage (Max: 50MB)</div>
            </div>
            
            <!-- Controls -->
            <div style="display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 8px;">
                <button id="cache-stats-btn" style="background: #2196F3; color: white; border: none; padding: 3px 6px; border-radius: 3px; cursor: pointer; font-size: 9px;">Log Stats</button>
                <button id="cache-cleanup-btn" style="background: #FF9800; color: white; border: none; padding: 3px 6px; border-radius: 3px; cursor: pointer; font-size: 9px;">Cleanup</button>
                <button id="lazy-clear-btn" style="background: #9C27B0; color: white; border: none; padding: 3px 6px; border-radius: 3px; cursor: pointer; font-size: 9px;">Clear Lazy</button>
            </div>
            
            <div style="font-size: 9px; color: #666; text-align: center;">
                Ctrl+Shift+C to toggle
            </div>
        `;
        
        // Bind button events
        this.bindButtonEvents();
    }
    
    bindButtonEvents() {
        const clearBtn = document.getElementById('cache-clear-btn');
        const statsBtn = document.getElementById('cache-stats-btn');
        const cleanupBtn = document.getElementById('cache-cleanup-btn');
        const lazyClearBtn = document.getElementById('lazy-clear-btn');
        
        if (clearBtn) {
            clearBtn.onclick = () => {
                cacheService.clear();
                lazyLoadService.clear();
                paginationService.clear();
                this.updatePanel();
                console.log('🧹 All caches and services cleared via debug panel');
            };
        }
        
        if (statsBtn) {
            statsBtn.onclick = () => {
                console.log('📊 Cache Stats:', cacheService.getStats());
                console.log('📊 Lazy Loading Stats:', lazyLoadService.getStats());
                console.log('📊 Pagination Stats:', paginationService.getStats());
            };
        }
        
        if (cleanupBtn) {
            cleanupBtn.onclick = () => {
                cacheService.cleanupExpired();
                this.updatePanel();
                console.log('🧹 Cache cleanup completed via debug panel');
            };
        }
        
        if (lazyClearBtn) {
            lazyClearBtn.onclick = () => {
                lazyLoadService.clear();
                this.updatePanel();
                console.log('🧹 Lazy loading service cleared via debug panel');
            };
        }
    }
    
    bindEvents() {
        // Toggle panel with Ctrl+Shift+C
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && e.code === 'KeyC') {
                e.preventDefault();
                this.toggle();
            }
        });
    }
    
    toggle() {
        if (this.isVisible) {
            this.hide();
        } else {
            this.show();
        }
    }
    
    show() {
        if (this.panel) {
            this.panel.style.display = 'block';
            this.isVisible = true;
            this.startAutoUpdate();
            console.log('🐛 Cache debug panel shown');
        }
    }
    
    hide() {
        if (this.panel) {
            this.panel.style.display = 'none';
            this.isVisible = false;
            this.stopAutoUpdate();
            console.log('🐛 Cache debug panel hidden');
        }
    }
    
    startAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
        
        this.updateInterval = setInterval(() => {
            if (this.isVisible) {
                this.updatePanel();
            }
        }, 5000); // Update every 5 seconds
    }
    
    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }
    
    destroy() {
        this.stopAutoUpdate();
        if (this.panel) {
            this.panel.remove();
        }
    }
}

// Initialize debug panel automatically
export const cacheDebugPanel = new CacheDebugPanel();
export default cacheDebugPanel;