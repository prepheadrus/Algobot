/**
 * Centralized State Management (Redux-like Pattern)
 * 
 * Single Source of Truth - Uygulamanın tüm durumu tek nesnede.
 * Pub/Sub Pattern - Değişiklikleri otomatik dinle.
 * 
 * Usage:
 *   import store from '../state/store.js';
 *   
 *   // Subscribe
 *   store.subscribe((state) => {
 *       console.log('State changed:', state);
 *   });
 *   
 *   // Update state
 *   store.setState('bots', { list: [...], count: 5 });
 *   
 *   // Get state
 *   const bots = store.getState('bots');
 */

class StateStore {
    constructor() {
        // Single Source of Truth
        this.state = {
            // Market data
            markets: {
                list: [],
                selected: null,
                loading: false
            },
            
            // Bot management
            bots: {
                list: [],
                active: [],
                selected: null,
                loading: false
            },
            
            // Portfolio
            portfolio: {
                balance: 10000.0,
                equity: 10000.0,
                pnl: 0.0,
                pnlPercent: 0.0,
                openPositions: [],
                closedTrades: []
            },
            
            // ML decisions
            ml: {
                models: [],
                predictions: {},
                loading: false
            },
            
            // Data downloads
            downloads: {
                active: [],
                completed: [],
                loading: false
            },
            
            // System status
            system: {
                status: 'unknown',
                metrics: {},
                lastUpdate: null
            },
            
            // UI state
            ui: {
                activeTab: 'dashboard',
                loading: false,
                notifications: []
            }
        };
        
        // Subscribers (Pub/Sub)
        this.subscribers = new Set();
        
        console.log('📦 [STORE] State management initialized');
    }
    
    /**
     * Subscribe to state changes
     * @param {Function} callback - Called when state changes
     * @returns {Function} Unsubscribe function
     */
    subscribe(callback) {
        this.subscribers.add(callback);
        console.debug('📬 [STORE] Subscriber added');
        
        // Return unsubscribe function
        return () => {
            this.subscribers.delete(callback);
            console.debug('📤 [STORE] Subscriber removed');
        };
    }
    
    /**
     * Update state (immutable pattern)
     * @param {string} key - State key to update
     * @param {any} value - New value
     */
    setState(key, value) {
        const oldState = this.state[key];
        
        // Update state
        this.state[key] = value;
        
        // Notify subscribers
        this.notify(this.state, key, oldState, value);
    }
    
    /**
     * Get state or specific key
     * @param {string} [key] - Optional key to get specific state
     * @returns {any} State or specific key value
     */
    getState(key) {
        if (key) {
            return this.state[key];
        }
        return this.state;
    }
    
    /**
     * Get specific state property
     * @param {string} key - State key
     * @param {string} property - Property name
     * @returns {any} Property value
     */
    get(key, property) {
        if (this.state[key] && property) {
            return this.state[key][property];
        }
        return this.state[key];
    }
    
    /**
     * Notify all subscribers
     * @param {Object} newState - New state
     * @param {string} changedKey - Key that changed
     * @param {any} oldValue - Old value
     * @param {any} newValue - New value
     */
    notify(newState, changedKey, oldValue, newValue) {
        // Clone state to prevent direct mutation
        const stateClone = JSON.parse(JSON.stringify(newState));
        
        this.subscribers.forEach(callback => {
            try {
                callback(stateClone, changedKey, oldValue, newValue);
            } catch (error) {
                console.error('❌ [STORE] Subscriber error:', error);
            }
        });
        
        console.debug(`🔄 [STORE] State updated: ${changedKey}`);
    }
    
    /**
     * Reset state to initial
     */
    reset() {
        this.state = {
            markets: { list: [], selected: null, loading: false },
            bots: { list: [], active: [], selected: null, loading: false },
            portfolio: { balance: 10000.0, equity: 10000.0, pnl: 0.0, pnlPercent: 0.0, openPositions: [], closedTrades: [] },
            ml: { models: [], predictions: {}, loading: false },
            downloads: { active: [], completed: [], loading: false },
            system: { status: 'unknown', metrics: {}, lastUpdate: null },
            ui: { activeTab: 'dashboard', loading: false, notifications: [] }
        };
        
        this.notify(this.state, 'reset', null, null);
        console.info('🔄 [STORE] State reset');
    }
}

// Singleton instance
const store = new StateStore();

// Export singleton
export default store;

// Also export for window access (debugging)
if (typeof window !== 'undefined') {
    window.store = store;
}
