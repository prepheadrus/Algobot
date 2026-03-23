/**
 * Bot Manager Component
 * 
 * Bot lifecycle management (start, stop, resume, remove).
 * Tüm bot DOM manipülasyonları bu modülde izole edilmiştir.
 * 
 * Usage:
 *   import botManager from '../components/bots/bot-manager.js';
 *   
 *   // Initialize
 *   botManager.init();
 *   
 *   // Start bot
 *   await botManager.startBot({ symbol: 'BTC/USDT', strategy: 'trend_master' });
 */

import api from '../../services/api-client.js';
import store from '../../state/store.js';

class BotManager {
    constructor() {
        this.bots = [];
        this.selectedBot = null;
        
        console.log('🤖 [BOT] Manager initialized');
    }
    
    /**
     * Initialize bot manager
     */
    init() {
        this.loadBots();
        this.setupEventListeners();

        // Subscribe to store changes
        store.subscribe((state) => {
            if (state.bots) {
                const newList = state.bots.list || [];
                // Only update and render if list changed
                if (JSON.stringify(newList) !== JSON.stringify(this.bots)) {
                    this.bots = newList;
                    console.log(`🤖 [BOT] Store updated: ${this.bots.length} bots`);
                    this.render();
                }
            }
        });
    }

    /**
     * Load bots from API
     */
    async loadBots() {
        try {
            console.log('🤖 [BOT] Loading bots from API...');
            const data = await api.getBots();
            console.log(`🤖 [BOT] API returned: ${data.bots?.length || 0} bots`);
            store.setState('bots', {
                list: data.bots || [],
                loading: false
            });
            // Force render after load
            this.bots = data.bots || [];
            setTimeout(() => this.render(), 100);
        } catch (error) {
            console.error('❌ [BOT] Load error:', error);
            store.setState('bots', { list: [], loading: false });
        }
    }
    
    /**
     * Start bot
     * @param {Object} botData - Bot configuration
     */
    async startBot(botData) {
        try {
            const result = await api.startBot(botData);
            
            if (result.status === 'success') {
                console.log(`✅ [BOT] Started: ${result.bot_id}`);
                await this.loadBots(); // Refresh list
                return result;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            console.error('❌ [BOT] Start error:', error);
            throw error;
        }
    }
    
    /**
     * Stop bot
     * @param {string} botId - Bot ID
     */
    async stopBot(botId) {
        try {
            const result = await api.stopBot(botId);

            if (result.status === 'success') {
                console.log(`🛑 [BOT] Stopped: ${botId}`);
                await this.loadBots();
                return result;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            console.error('❌ [BOT] Stop error:', error);
            throw error;
        }
    }
    
    /**
     * Resume bot
     * @param {string} botId - Bot ID
     */
    async resumeBot(botId) {
        try {
            const result = await api.resumeBot(botId);
            
            if (result.status === 'success') {
                console.log(`▶️ [BOT] Resumed: ${botId}`);
                await this.loadBots();
                return result;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            console.error('❌ [BOT] Resume error:', error);
            throw error;
        }
    }
    
    /**
     * Remove bot
     * @param {string} botId - Bot ID
     */
    async removeBot(botId) {
        try {
            const result = await api.removeBot(botId);
            
            if (result.status === 'success') {
                console.log(`🗑️ [BOT] Removed: ${botId}`);
                await this.loadBots();
                return result;
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            console.error('❌ [BOT] Remove error:', error);
            throw error;
        }
    }
    
    /**
     * Select bot
     * @param {string} botId - Bot ID
     */
    selectBot(botId) {
        this.selectedBot = botId;
        store.setState('bots', { selected: botId });
        this.render();
    }
    
    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Auto-refresh bots every 5 seconds
        setInterval(() => {
            this.loadBots();
        }, 5000);
    }
    
    /**
     * Render bot list
     */
    render() {
        console.log('🎨 [BOT] Render called, bots count:', this.bots.length);
        const container = document.getElementById('active-bots-container');
        const summaryContainer = document.getElementById('system-status-summary');

        console.log('🔍 [BOT] Containers:', {
            'active-bots-container': container ? 'FOUND' : 'NOT FOUND',
            'system-status-summary': summaryContainer ? 'FOUND' : 'NOT FOUND'
        });

        // Render active bots container (Settings tab)
        if (container) {
            console.log('📝 [BOT] Rendering active-bots-container with', this.bots.length, 'bots');
            if (this.bots.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: var(--text-muted);">
                        📭 Aktif bot yok
                    </div>
                `;
            } else {
                container.innerHTML = this.bots.map(bot => `
                    <div class="bot-card" data-bot-id="${bot.bot_id}" style="padding: 12px; margin-bottom: 12px; border-radius: 8px; border: 1px solid ${bot.status === 'running' ? 'var(--neon-green)' : 'var(--text-muted)'}; background: rgba(255,255,255,0.02);">
                        <div class="bot-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span class="bot-symbol" style="font-weight: 700; color: var(--text-main); font-size: 1rem;">${bot.symbol}</span>
                            <span class="bot-status" style="font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; background: ${bot.status === 'running' ? 'var(--neon-green)' : 'var(--text-muted)'}; color: #000;">
                                ${bot.status === 'running' ? '● Çalışıyor' : '● Duraklatıldı'}
                            </span>
                        </div>
                        <div class="bot-info" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; font-size: 0.85rem; margin-bottom: 12px;">
                            <div><span style="color: var(--text-muted);">Strateji:</span> <span style="color: var(--text-main);">${bot.strategy_id}</span></div>
                            <div><span style="color: var(--text-muted);">Timeframe:</span> <span style="color: var(--text-main);">${bot.timeframe}</span></div>
                            <div><span style="color: var(--text-muted);">PnL:</span> <span style="color: ${bot.pnl >= 0 ? 'var(--neon-green)' : 'var(--neon-red)'};">$${bot.pnl.toFixed(2)} (${bot.pnl_percent.toFixed(2)}%)</span></div>
                            <div><span style="color: var(--text-muted);">İşlem:</span> <span style="color: var(--text-main);">${bot.trades} (${bot.wins} Kazanç)</span></div>
                        </div>
                        <div class="bot-actions" style="display: flex; gap: 8px;">
                            ${bot.status === 'running' ? `
                                <button onclick="botManager.stopBot('${bot.bot_id}')" class="btn btn-danger" style="flex: 1; padding: 8px 12px; background: var(--neon-red); color: #fff; border: none; border-radius: 4px; cursor: pointer; font-weight: 600;">
                                    ⏹️ Durdur
                                </button>
                            ` : `
                                <button onclick="botManager.resumeBot('${bot.bot_id}')" class="btn btn-primary" style="flex: 1; padding: 8px 12px; background: var(--neon-blue); color: #fff; border: none; border-radius: 4px; cursor: pointer; font-weight: 600;">
                                    ▶️ Devam
                                </button>
                            `}
                            <button onclick="botManager.removeBot('${bot.bot_id}')" class="btn btn-delete" style="padding: 8px 12px; background: rgba(255,255,255,0.1); color: #fff; border: none; border-radius: 4px; cursor: pointer;">
                                🗑️ Sil
                            </button>
                        </div>
                    </div>
                `).join('');
                console.log('✅ [BOT] active-bots-container rendered successfully');
            }
        }

        // Render system status summary (compact view - Orders tab)
        if (summaryContainer) {
            console.log('📊 [BOT] Rendering system-status-summary with', this.bots.length, 'bots');
            if (this.bots.length === 0) {
                summaryContainer.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: var(--text-muted); grid-column: span 100%;">
                        📭 Aktif strateji yok
                    </div>
                `;
            } else {
                summaryContainer.innerHTML = this.bots.map(bot => `
                    <div class="system-status-card glass-panel" data-bot-id="${bot.bot_id}" style="padding: 12px; border-radius: 8px; border: 1px solid ${bot.status === 'running' ? 'var(--neon-green)' : 'var(--text-muted)'};">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-weight: 700; color: var(--text-main);">${bot.symbol}</span>
                            <span style="font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; background: ${bot.status === 'running' ? 'var(--neon-green)' : 'var(--text-muted)'}; color: #000;">
                                ${bot.status === 'running' ? '● Çalışıyor' : '● Duraklatıldı'}
                            </span>
                        </div>
                        <div style="display: flex; flex-direction: column; gap: 4px; font-size: 0.75rem;">
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color: var(--text-muted);">Strateji:</span>
                                <span style="color: var(--text-main);">${bot.strategy_id}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color: var(--text-muted);">Timeframe:</span>
                                <span style="color: var(--text-main);">${bot.timeframe}</span>
                            </div>
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color: var(--text-muted);">PnL:</span>
                                <span style="color: ${bot.pnl >= 0 ? 'var(--neon-green)' : 'var(--neon-red)'};">
                                    $${bot.pnl.toFixed(2)} (${bot.pnl_percent.toFixed(2)}%)
                                </span>
                            </div>
                            <div style="display: flex; justify-content: space-between;">
                                <span style="color: var(--text-muted);">İşlem:</span>
                                <span style="color: var(--text-main);">${bot.trades} (${bot.wins} Kazanç)</span>
                            </div>
                        </div>
                        <div style="display: flex; gap: 4px; margin-top: 8px;">
                            ${bot.status === 'running' ? `
                                <button onclick="botManager.stopBot('${bot.bot_id}')" style="flex: 1; padding: 4px 8px; font-size: 0.7rem; background: var(--neon-red); color: #fff; border: none; border-radius: 4px; cursor: pointer;">
                                    ⏹️ Durdur
                                </button>
                            ` : `
                                <button onclick="botManager.resumeBot('${bot.bot_id}')" style="flex: 1; padding: 4px 8px; font-size: 0.7rem; background: var(--neon-blue); color: #fff; border: none; border-radius: 4px; cursor: pointer;">
                                    ▶️ Devam
                                </button>
                            `}
                            <button onclick="botManager.removeBot('${bot.bot_id}')" style="padding: 4px 8px; font-size: 0.7rem; background: rgba(255,255,255,0.1); color: #fff; border: none; border-radius: 4px; cursor: pointer;">
                                🗑️
                            </button>
                        </div>
                    </div>
                `).join('');
                console.log('✅ [BOT] system-status-summary rendered successfully');
            }
        }
    }
    
    /**
     * Destroy bot manager
     */
    destroy() {
        this.bots = [];
        this.selectedBot = null;
        console.log('🗑️ [BOT] Manager destroyed');
    }
}

// Singleton instance
const botManager = new BotManager();

// Export singleton
export default botManager;

// Also export for window access (debugging)
if (typeof window !== 'undefined') {
    window.botManager = botManager;
}
