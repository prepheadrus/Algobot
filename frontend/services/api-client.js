/**
 * API Client - Centralized Communication Layer
 * 
 * Tüm API çağrıları bu sınıfta toplanır.
 * Error handling, retry logic ve request/response interceptors.
 * 
 * Usage:
 *   import api from '../services/api-client.js';
 *   
 *   // GET request
 *   const bots = await api.getBots();
 *   
 *   // POST request
 *   const result = await api.startBot({ symbol: 'BTC/USDT', strategy: 'trend_master' });
 */

class APIClient {
    constructor() {
        this.baseURL = '/api/v1';
        this.timeout = 30000; // 30 seconds
        this.retryAttempts = 3;
        
        console.log('🌐 [API] Client initialized');
    }
    
    /**
     * Generic request method
     * @param {string} endpoint - API endpoint
     * @param {Object} options - Fetch options
     * @returns {Promise<any>} Response data
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        
        const config = {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        };
        
        try {
            const response = await fetch(url, config);
            
            // Handle errors
            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            return await response.json();
            
        } catch (error) {
            console.error(`❌ [API] Request failed: ${endpoint}`, error);
            throw error;
        }
    }
    
    /**
     * GET request
     * @param {string} endpoint - Endpoint
     * @param {Object} params - Query parameters
     * @returns {Promise<any>}
     */
    async get(endpoint, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        
        return this.request(url, { method: 'GET' });
    }
    
    /**
     * POST request
     * @param {string} endpoint - Endpoint
     * @param {Object} data - Request body
     * @returns {Promise<any>}
     */
    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
    
    /**
     * DELETE request
     * @param {string} endpoint - Endpoint
     * @param {Object} data - Request body
     * @returns {Promise<any>}
     */
    async delete(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'DELETE',
            body: JSON.stringify(data)
        });
    }
    
    // ========================================================================
    // STATUS & SYSTEM
    // ========================================================================
    
    getStatus() {
        return this.get('/status');
    }
    
    getDashboardMetrics(params = {}) {
        return this.get('/dashboard-metrics', params);
    }
    
    // ========================================================================
    // BOT MANAGEMENT
    // ========================================================================

    getBots() {
        return this.get('/bot/bots/list');
    }

    getBotStatus(botId) {
        return this.get('/bot/status', { bot_id: botId });
    }

    startBot(botData) {
        console.log('🔥 [API] startBot çağrıldı:', botData);
        return this.post('/bot/start', botData);
    }

    stopBot(botId) {
        return this.post('/bot/stop', { bot_id: botId, action: 'stop' });
    }

    resumeBot(botId) {
        return this.post('/bot/resume', { bot_id: botId, action: 'resume' });
    }

    removeBot(botId) {
        return this.post('/bot/remove', { bot_id: botId });
    }
    
    // ========================================================================
    // STRATEGY
    // ========================================================================
    
    getStrategies() {
        return this.get('/strategies');
    }

    getStrategyReport() {
        return this.get('/strategy-report');
    }
    
    // ========================================================================
    // ML
    // ========================================================================
    
    getMLModels() {
        return this.get('/ml/models');
    }
    
    trainModel(data) {
        return this.post('/ml/train', data);
    }
    
    deleteMLModel(symbol, timeframe) {
        return this.delete(`/ml/model?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}`);
    }
    
    // ========================================================================
    // DATA
    // ========================================================================

    getDataInventory() {
        return this.get('/data/inventory');
    }

    getDataStats() {
        return this.get('/data/stats');
    }

    getActiveDownloads() {
        return this.get('/data/all-download-tasks');
    }

    getTrackedSymbols() {
        return this.get('/data/symbols-with-data');
    }

    startDownload(symbol, timeframe, startDate) {
        return this.post('/data/download-history', {
            symbol,
            timeframe,
            start_date: startDate
        });
    }

    stopDownload(symbol) {
        return this.post('/data/stop-download', { symbol });
    }

    deleteData(symbol, marketType) {
        return this.delete('/data/delete-klines', { symbol, market_type: marketType });
    }

    deleteDownloadTask(symbol, marketType) {
        return this.post('/data/delete-download-task', { symbol, market_type: marketType });
    }

    togglePause(symbol, action) {
        return this.post('/data/toggle-pause', { symbol, action });
    }

    // ========================================================================
    // TRADES
    // ========================================================================

    getTrades() {
        return this.get('/trades/history');
    }

    clearTrades() {
        return this.delete('/trades/clear');
    }

    // ========================================================================
    // CONFIG & SETTINGS
    // ========================================================================

    getBotConfig() {
        return this.get('/config/bot');
    }

    saveBotConfig(data) {
        return this.post('/config/bot', data);
    }

    getRiskSettings() {
        return this.get('/config/risk');
    }

    saveRiskSettings(data) {
        return this.post('/config/risk', data);
    }

    getAdvancedSettings() {
        return this.get('/config/advanced');
    }

    saveAdvancedSettings(data) {
        return this.post('/config/advanced', data);
    }

    saveApiKeys(data) {
        return this.post('/config/api-keys', data);
    }

    testApiConnection(data) {
        return this.post('/config/test-api-keys', data);
    }

    // ========================================================================
    // BOT LAUNCHER
    // ========================================================================

    getSymbolsWithData() {
        return this.get('/data/symbols-with-data');
    }

    getStrategies() {
        return this.get('/strategies');
    }

    getActiveDownloads() {
        return this.get('/data/all-download-tasks');
    }
}

// Singleton instance
const api = new APIClient();

// Export singleton
export default api;

// Also export for window access (debugging)
if (typeof window !== 'undefined') {
    window.api = api;
}
