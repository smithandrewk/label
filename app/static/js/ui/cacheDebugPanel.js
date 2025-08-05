/**
 * Cache Debug Panel
 * Shows cache performance and allows manual cache management
 */

import { cacheService } from '../services/cacheService.js';

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
        
        const stats = cacheService.getStats();
        
        this.panel.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h3 style="margin: 0; color: #4CAF50;">🗄️ Cache Stats</h3>
                <button id="cache-clear-btn" style="background: #f44336; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer;">Clear</button>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
                <div>
                    <div style="color: #81C784;">Hits: ${stats.hits}</div>
                    <div style="color: #FFAB91;">Misses: ${stats.misses}</div>
                    <div style="color: #90CAF9;">Hit Rate: ${stats.hitRate}</div>
                </div>
                <div>
                    <div style="color: #CE93D8;">Stores: ${stats.stores}</div>
                    <div style="color: #FFCC02;">Evictions: ${stats.evictions}</div>
                    <div style="color: #A5D6A7;">Entries: ${stats.entryCount}</div>
                </div>
            </div>
            
            <div style="margin-bottom: 10px;">
                <div style="color: #B39DDB;">Total Size: ${stats.totalSize}</div>
                <div style="background: #333; height: 8px; border-radius: 4px; overflow: hidden; margin-top: 4px;">
                    <div style="background: linear-gradient(90deg, #4CAF50, #FFC107, #F44336); height: 100%; width: ${Math.min(100, parseFloat(stats.totalSize) / 50 * 100)}%;"></div>
                </div>
                <div style="font-size: 10px; color: #999; margin-top: 2px;">Max: 50MB</div>
            </div>
            
            <div style="display: flex; gap: 5px; flex-wrap: wrap;">
                <button id="cache-stats-btn" style="background: #2196F3; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 10px;">Log Stats</button>
                <button id="cache-cleanup-btn" style="background: #FF9800; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 10px;">Cleanup</button>
                <button id="cache-disable-btn" style="background: #9E9E9E; color: white; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 10px;">Disable</button>
            </div>
            
            <div style="margin-top: 10px; font-size: 10px; color: #999;">
                Ctrl+Shift+C to toggle panel
            </div>
        `;
        
        // Bind button events
        this.bindButtonEvents();
    }
    
    bindButtonEvents() {
        const clearBtn = document.getElementById('cache-clear-btn');
        const statsBtn = document.getElementById('cache-stats-btn');
        const cleanupBtn = document.getElementById('cache-cleanup-btn');
        const disableBtn = document.getElementById('cache-disable-btn');
        
        if (clearBtn) {
            clearBtn.onclick = () => {
                cacheService.clear();
                this.updatePanel();
                console.log('🧹 Cache cleared via debug panel');
            };
        }
        
        if (statsBtn) {
            statsBtn.onclick = () => {
                cacheService.logStats();
            };
        }
        
        if (cleanupBtn) {
            cleanupBtn.onclick = () => {
                cacheService.cleanupExpired();
                this.updatePanel();
                console.log('🧹 Cache cleanup completed via debug panel');
            };
        }
        
        if (disableBtn) {
            disableBtn.onclick = () => {
                this.hide();
                console.log('🐛 Cache debug panel disabled');
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