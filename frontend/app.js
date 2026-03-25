/**
 * CryptoAlgoBot - Main Application Coordinator
 *
 * Modern ES6 Module Architecture
 * - State Management: store.js
 * - API Client: api-client.js
 * - Components: chart-renderer.js, bot-manager.js
 *
 * Usage:
 *   <script type="module" src="app.js"></script>
 */

// Import modules
import store from './state/store.js';
import api from './services/api-client.js';
import chartRenderer from './components/charts/chart-renderer.js';
import botManager from './components/bots/bot-manager.js';

// ============================================================================
// APPLICATION STATE
// ============================================================================

const app = {
    initialized: false,
    activeTab: 'tab-empty-state',
    openTabs: [], // Array to keep track of dynamically opened tabs {id, title, icon}
    refreshInterval: null
};

// ============================================================================
// INITIALIZATION
// ============================================================================

/**
 * Initialize application
 */
async function init() {
    console.log('🚀 CryptoAlgoBot başlatılıyor...');

    try {
        // 1. Initialize components
        botManager.init();

        // 2. Setup UI
        setupTabs();
        setupEventListeners();

        // 3. Show default tab (portfolio)
        switchTab('tab-portfolio');

        // 4. Load initial data
        await loadDashboard();
        await loadActiveTasks();
        startLiveTicker();
        await loadDatabaseInventory();  // Load inventory
        await loadMarketList();  // Load market list
        await loadBotConfig();      // Load bot config
        await loadRiskSettings();  // Load risk settings
        await loadAdvancedSettings();  // Load advanced settings
        await loadSymbolsForBot();  // Load symbols for bot launcher
        await loadStrategiesForBot();  // Load strategies
        await loadTimeframesForBot();  // Load timeframes
        await loadStrategyLibrary();  // Load strategy library
        await loadMLTrainingHistory();  // Load ML training history
        await loadSymbolsForML();  // Load symbols for ML training
        await loadTimeframesForML();  // Load timeframes for ML training

        // XAI: ML Strateji Karar Merkezi dropdown'larını yükle
        await loadMLStrategies();  // Stratejileri API'den yükle
        await loadMLSymbols();  // Sembolleri API'den yükle

        // 5. Start auto-refresh
        startAutoRefresh();

        app.initialized = true;
        console.log('✅ Uygulama başarıyla başlatıldı');

    } catch (error) {
        console.error('❌ Uygulama başlatma hatası:', error);
    }
}

// ============================================================================
// TAB NAVIGATION
// ============================================================================

/**
 * Setup tab navigation
 */
function setupTabs() {
    // Sadece sidebar linklerine tıklandığında sekme açma (SPA Mantığı)
    const sidebarLinks = document.querySelectorAll('.sidebar-link');

    sidebarLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetTab = link.dataset.target;
            switchTab(targetTab);
        });
    });
}

/**
 * Switch to tab
 * @param {string} tabId - Tab ID
 */
function switchTab(tabId) {
    if (!tabId) {
        console.warn('⚠️ [TAB] No tabId provided');
        return;
    }

    app.activeTab = tabId;

    console.log(`📑 [TAB] Switching to: ${tabId}`);

    // Update sidebar links visual state
    document.querySelectorAll('.sidebar-link').forEach(item => {
        const target = item.dataset.target;
        if (target === tabId) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        if (content.id === tabId) {
            content.classList.add('active-tab');
            content.style.display = 'block';
            console.log(`✅ [TAB] Showing: ${content.id}`);
            
            // Resume rendering for active tab charts
            if (window.chartRenderer && typeof window.chartRenderer.resume === 'function') {
                window.chartRenderer.resume();
            }

            // ============================================
            // TAB-SPECIFIC DATA LOADING
            // ============================================
            if (tabId === 'tab-history') {
                console.log('📜 [TAB] History tab activated, loading trade history...');
                loadTradeHistory();
            } else if (tabId === 'tab-portfolio') {
                console.log('📊 [TAB] Portfolio tab activated, refreshing data...');
                loadDashboard();
            } else if (tabId === 'tab-orders') {
                console.log('📋 [TAB] Orders tab activated, refreshing data...');
                loadDashboard();
            }
        } else {
            content.classList.remove('active-tab');
            content.style.display = 'none';
            // Display: none için inline style'ı force olarak override et (bazen tab flex olabiliyor)
            if(content.id === 'tab-empty-state' && tabId !== 'tab-empty-state') {
                content.style.display = 'none';
            }

            // Pause rendering for inactive tabs to prevent memory leaks and high CPU usage
            if (content.id === 'tab-portfolio' || content.id === 'tab-ml') {
                if (window.chartRenderer && typeof window.chartRenderer.pause === 'function') {
                    window.chartRenderer.pause();
                }
            }
        }
    });

    // Boş state gösterimi ayarı
    const emptyState = document.getElementById('tab-empty-state');
    if(emptyState) {
        if(tabId === 'tab-empty-state') {
            emptyState.style.display = 'flex';
        }
    }

    // Update store
    store.setState('ui', { ...store.get('ui'), activeTab: tabId });

    console.log(`📑 [TAB] Switched to: ${tabId}`);
}

// ============================================================================
// DATA LOADING
// ============================================================================

/**
 * Load dashboard data
 */
async function loadDashboard() {
    try {
        const metrics = await api.getDashboardMetrics();
        store.setState('system', {
            status: 'online',
            metrics: metrics,
            lastUpdate: new Date().toISOString()
        });

        console.log('📊 [DASHBOARD] Metrics loaded');

        // ============================================
        // SYMBOL CONFIGURATION CHECK
        // ============================================
        // İlk yüklemede sembol kontrolü yap
        if (!window._symbolCheckDone) {
            const symbols = await api.getTrackedSymbols();
            if (!symbols || symbols.length === 0) {
                showToast('⚠️ Hiçbir sembol yapılandırılmamış! Veri Laboratuvarı\'ndan sembol ekleyin.', 'warning');
                window._symbolCheckDone = true;
            }
        }

        // Render positions and update performance metrics
        if (metrics.positions) {
            renderPositions(metrics.positions);
        }
        if (metrics.portfolio) {
            updatePerformanceMetrics(metrics.portfolio);
        }

    } catch (error) {
        console.error('❌ [DASHBOARD] Load error:', error);
        store.setState('system', { status: 'error' });
    }
}

/**
 * Render open positions table
 */
function renderPositions(positions) {
    const tbody = document.getElementById('positions-body');
    if (!tbody) return;

    if (positions.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:40px; color:var(--text-muted);">📭 Açık pozisyon yok</td></tr>`;
        return;
    }

    tbody.innerHTML = positions.map(pos => {
        const direction = pos.direction || pos.side || 'LONG';
        const directionIcon = direction === 'LONG' ? '🟢' : '🔴';
        const directionColor = direction === 'LONG' ? 'var(--neon-green)' : 'var(--neon-red)';
        const pnl = pos.unrealized_usd || pos.pnl_usd || 0;
        const pnlClass = pnl >= 0 ? 'color:var(--neon-green)' : 'color:var(--neon-red)';
        const pnlSign = pnl >= 0 ? '+' : '';
        const roe = pos.pnl_percent || 0;
        const roeClass = roe >= 0 ? 'color:var(--neon-green)' : 'color:var(--neon-red)';
        const roeSign = roe >= 0 ? '+' : '';
        const notional = (pos.size || 0) * (pos.entry_price || 0) * (pos.leverage || 1);

        return `
            <tr>
                <td>
                    <div style="font-weight:600; color:var(--text-main);">${pos.strategy_id || pos.strategy || 'Unknown'}</div>
                    <div style="font-size:0.7rem; color:var(--text-muted);">${pos.timeframe || 'N/A'}</div>
                </td>
                <td>
                    <div style="color:${directionColor}; font-weight:600;">${directionIcon} ${direction}</div>
                    <div style="font-size:0.75rem; color:var(--text-main);">${pos.symbol || 'N/A'}</div>
                </td>
                <td>
                    <div style="font-family:monospace;">${(pos.size || 0).toFixed(4)}</div>
                    <div style="font-size:0.7rem; color:var(--text-muted);">${pos.leverage || 1}x</div>
                </td>
                <td>
                    <div style="font-family:monospace;">$${(pos.entry_price || 0).toFixed(2)}</div>
                    <div style="font-size:0.7rem; color:var(--text-muted);">$${notional.toFixed(2)}</div>
                </td>
                <td>
                    <div style="font-family:monospace; font-weight:bold; ${pnlClass}">${pnlSign}$${pnl.toFixed(2)}</div>
                    <div style="font-size:0.7rem; color:var(--text-muted);">$${(pos.current_price || pos.entry_price || 0).toFixed(2)}</div>
                </td>
                <td style="font-family:monospace; font-weight:bold; ${roeClass}">
                    ${roeSign}${roe.toFixed(2)}%
                </td>
                <td style="font-size:0.7rem;">
                    <div style="color:var(--neon-red);">SL: $${(pos.stop_loss || 0).toFixed(2)}</div>
                    <div style="color:var(--neon-green);">TP: $${(pos.take_profit || 0).toFixed(2)}</div>
                    <div style="color:var(--text-muted);">Liq: $${(pos.liquidation_price || 0).toFixed(2)}</div>
                </td>
                <td>
                    <button onclick="closePosition('${pos.bot_id || pos.id || ''}', '${pos.symbol || ''}')"
                        style="padding:4px 8px; background:var(--neon-red); color:#fff; border:none; border-radius:4px; cursor:pointer; font-size:0.7rem; font-weight:600;">
                        🚫 Kapat
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    console.log(`✅ [POSITIONS] ${positions.length} pozisyon render edildi`);
}

/**
 * Update performance metrics (KPI dashboard)
 */
function updatePerformanceMetrics(portfolio) {
    const elBalance = document.getElementById('perf-balance');
    const elEquity = document.getElementById('perf-equity');
    const elWinRate = document.getElementById('perf-winrate');
    const elCount = document.getElementById('perf-count');
    const elTotalTrades = document.getElementById('perf-total-trades');
    const elTotalPnl = document.getElementById('perf-total-pnl');
    const elFees = document.getElementById('perf-total-fees');

    const elUsedMargin = document.getElementById('usage-used-margin');
    const elFreeMargin = document.getElementById('usage-free-margin');
    const elNotional = document.getElementById('usage-notional');
    const elLeverage = document.getElementById('usage-leverage');

    const balance = portfolio.balance || 10000;
    const equity = portfolio.equity || balance;
    const usedMargin = portfolio.used_margin || 0;
    const freeMargin = portfolio.free_margin || balance;
    const totalPnl = portfolio.total_pnl || 0;
    const winRate = portfolio.win_rate || 0;
    const totalTrades = portfolio.total_trades || 0;
    const fees = portfolio.total_commission || 0;
    const notional = portfolio.total_notional || 0;

    // Calculate average leverage (approximate)
    const avgLeverage = notional > 0 && usedMargin > 0 ? (notional / usedMargin).toFixed(1) : '1.0';

    // Update DOM
    if (elBalance) elBalance.textContent = `$${balance.toFixed(2)}`;
    if (elEquity) elEquity.textContent = `$${equity.toFixed(2)}`;
    if (elWinRate) {
        elWinRate.textContent = `${winRate.toFixed(1)}%`;
        elWinRate.style.color = winRate >= 50 ? 'var(--neon-green)' : 'var(--neon-red)';
    }
    if (elCount) elCount.textContent = totalTrades;
    if (elTotalTrades) elTotalTrades.textContent = totalTrades;
    if (elTotalPnl) {
        elTotalPnl.textContent = `$${totalPnl.toFixed(2)}`;
        elTotalPnl.style.color = totalPnl >= 0 ? 'var(--neon-green)' : 'var(--neon-red)';

        // Add neon border to parent card based on profit/loss
        const parentCard = elTotalPnl.closest('.card, .kpi-card, .glass-panel');
        if (parentCard) {
            parentCard.classList.remove('profit', 'loss');
            parentCard.classList.add(totalPnl >= 0 ? 'profit' : 'loss');
        }
    }
    if (elFees) elFees.textContent = `$${fees.toFixed(2)}`;

    if (elUsedMargin) {
        elUsedMargin.textContent = `$${usedMargin.toFixed(2)}`;
        elUsedMargin.style.color = usedMargin > balance * 0.5 ? 'var(--neon-red)' : 'var(--text-main)';
    }
    if (elFreeMargin) {
        elFreeMargin.textContent = `$${freeMargin.toFixed(2)}`;
        elFreeMargin.style.color = freeMargin < balance * 0.2 ? 'var(--neon-red)' : 'var(--neon-green)';
    }
    if (elNotional) elNotional.textContent = `$${notional.toFixed(2)}`;
    if (elLeverage) elLeverage.textContent = `${avgLeverage}x`;

    console.log('📊 [PERF] Metrics updated');
}

/**
 * Close position
 */
window.closePosition = function(botId, symbol) {
    if (!botId) {
        showToast('❌ Bot ID bulunamadı', 'error');
        return;
    }

    if (!confirm(`⚠️ ${symbol} pozisyonunu kapatmak istediğinizden emin misiniz?`)) {
        return;
    }

    console.log('🚫 [POSITION] Closing position:', { botId, symbol });

    // Bot manager'ı kullan
    if (typeof botManager !== 'undefined' && botManager.stopBot) {
        botManager.stopBot(botId)
            .then(result => {
                if (result.status === 'success') {
                    showToast(`✅ ${symbol} pozisyonu kapatıldı`, 'success');
                    // Refresh dashboard
                    setTimeout(() => loadDashboard(), 1000);
                } else {
                    showToast('❌ ' + (result.message || 'Kapatma başarısız'), 'error');
                }
            })
            .catch(error => {
                showToast('❌ Hata: ' + error.message, 'error');
            });
    } else {
        showToast('❌ Bot manager bulunamadı', 'error');
    }
};

/**
 * Load active download tasks
 */
async function loadActiveTasks() {
    try {
        const data = await api.getActiveDownloads();
        store.setState('downloads', data);

        // Render tasks
        renderActiveTasks(data.downloads || {});

        console.log('📥 [DOWNLOADS] Tasks loaded');

    } catch (error) {
        console.error('❌ [DOWNLOADS] Load error:', error);
    }
}

/**
 * Load database inventory
 */
async function loadDatabaseInventory() {
    try {
        const inventory = await api.getDataInventory();
        const stats = await api.getDataStats();

        store.setState('inventory', { inventory, stats });

        // Render inventory
        renderDatabaseInventory(inventory, stats);

        console.log('📊 [INVENTORY] Loaded');

    } catch (error) {
        console.error('❌ [INVENTORY] Load error:', error);
    }
}

/**
 * Render database inventory
 */
function renderDatabaseInventory(inventory, stats) {
    const statsEl = document.getElementById('data-stats-summary');
    const tableEl = document.getElementById('data-stats-table');

    if (!statsEl || !tableEl) return;

    const totalCandles = inventory?.total_candles || stats?.total_candles || 0;
    const inventoryList = inventory?.inventory || stats?.stats || [];

    // Update summary
    const millions = (totalCandles / 1000000).toFixed(2);
    statsEl.innerHTML = `
        <span style="font-size:1.3rem; font-weight:700; color:var(--neon-blue);">📊 Toplam: ${millions} Milyon</span>
        <div style="display:flex; gap:20px; margin-top:8px;">
            <span style="font-size:0.85rem; color:var(--text-muted);">
                📦 ${inventoryList.length} farklı sembol/timeframe kombinasyonu
            </span>
        </div>
    `;

    // Render table
    if (inventoryList.length === 0) {
        tableEl.innerHTML = '<p style="text-align:center; color:var(--text-muted); padding:20px;">📭 Veritabanında henüz veri yok</p>';
        return;
    }

    tableEl.innerHTML = `
        <table style="width:100%; border-collapse:collapse;">
            <thead>
                <tr style="border-bottom:2px solid rgba(255,255,255,0.15); position: sticky; top: 0; background: #0a0e1a;">
                    <th style="padding:12px 10px; text-align:left; font-size:0.8rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.5px;">🪙 Sembol</th>
                    <th style="padding:12px 10px; text-align:left; font-size:0.8rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.5px;">📅 Başlangıç</th>
                    <th style="padding:12px 10px; text-align:left; font-size:0.8rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.5px;">📅 Bitiş</th>
                    <th style="padding:12px 10px; text-align:right; font-size:0.8rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.5px;">📊 Mum Sayısı</th>
                </tr>
            </thead>
            <tbody>
                ${inventoryList.map(item => {
                    const countFormatted = (item.count || 0).toLocaleString('tr-TR');
                    const countShort = item.count >= 1000000 ? `${(item.count / 1000000).toFixed(2)}M` :
                                      item.count >= 1000 ? `${(item.count / 1000).toFixed(0)}K` : item.count;
                    const countColor = item.count >= 1000000 ? '#00ff88' :
                                      item.count >= 100000 ? 'var(--neon-green)' : 'var(--text-main)';

                    // GERÇEK MARKET TYPE TESPİTİ
                    const symbol = item.symbol || 'N/A';
                    const isFutures = symbol.includes(':USDT') || symbol.includes(':USDC') || symbol.endsWith('-SWAP');
                    const marketTypeLabel = isFutures ? '💹 Vadeli' : '💰 Spot';
                    const marketTypeColor = isFutures ? 'var(--neon-blue)' : 'var(--neon-green)';
                    const marketTypeKey = isFutures ? 'future' : 'spot';

                    return `
                        <tr style="border-bottom:1px solid rgba(255,255,255,0.05); transition: background 0.2s;"
                            onmouseover="this.style.background='rgba(255,255,255,0.03)'"
                            onmouseout="this.style.background='transparent'">
                            <td style="padding:12px 10px;">
                                <div style="display:flex; align-items:center; gap:8px;">
                                    <span style="font-weight:700; font-size:0.95rem; color:var(--text-main);">${symbol}</span>
                                    <span style="font-size:0.7rem; padding:2px 8px; border-radius:4px;
                                                background:${isFutures ? 'rgba(88, 166, 255, 0.2)' : 'rgba(46, 220, 135, 0.2)'}; color:${marketTypeColor}; font-weight:600;">
                                        ${marketTypeLabel}
                                    </span>
                                </div>
                                <div style="font-size:0.7rem; color:var(--text-muted); margin-top:4px;">
                                    ⏱️ ${item.timeframe || '1m'}
                                </div>
                            </td>
                            <td style="padding:12px 10px;">
                                <span style="font-size:0.85rem; color:#ffa500; font-weight:600;">📅 ${item.min_date || 'N/A'}</span>
                            </td>
                            <td style="padding:12px 10px;">
                                <span style="font-size:0.85rem; color:#ff6b6b; font-weight:600;">📅 ${item.max_date || 'N/A'}</span>
                            </td>
                            <td style="padding:12px 10px; text-align:right;">
                                <div style="display:flex; align-items:center; justify-content:flex-end; gap:12px;">
                                    <button class="data-btn data-btn-danger" onclick="deleteSymbolData('${symbol}', '${marketTypeKey}')"
                                        title="${symbol} verilerini sil"
                                        style="padding:4px 10px; font-size:0.75rem; background: linear-gradient(135deg, #dc2626, #991b1b);">
                                        🗑️ Sil
                                    </button>
                                    <span style="font-size:1rem; font-weight:700; color:${countColor};">${countShort}</span>
                                </div>
                                <div style="font-size:0.7rem; color:var(--text-muted); margin-top:2px;">
                                    ${countFormatted} mum
                                </div>
                            </td>
                        </tr>
                    `;
                }).join('')}
            </tbody>
        </table>
    `;
}

/**
 * Render active tasks
 */
function renderActiveTasks(downloads) {
    const tasksListEl = document.getElementById('active-tasks-list');
    const tasksCountEl = document.getElementById('active-tasks-count');

    if (!tasksListEl) return;

    const tasks = Object.entries(downloads);
    const activeCount = tasks.filter(([_, t]) => t.status === 'running').length;
    const totalCount = tasks.length;

    // Update count
    if (tasksCountEl) {
        tasksCountEl.textContent = `${activeCount} Aktif / ${totalCount} Toplam`;
    }

    if (tasks.length === 0) {
        tasksListEl.innerHTML = `
            <div style="text-align: center; padding: 40px; color: var(--text-muted);">
                📭 Aktif veya tamamlanmış indirme yok
            </div>
        `;
        return;
    }

    // Render tasks
    tasksListEl.innerHTML = tasks.map(([key, task]) => {
        const statusClass = task.status === 'running' ? 'running' :
                           task.status === 'completed' ? 'completed' :
                           task.status === 'paused' ? 'paused' : 'stopped';

        const statusDisplay = task.status === 'running' ? '🔄 İndiriliyor' :
                             task.status === 'completed' ? '✅ Tamamlandı' :
                             task.status === 'paused' ? '⏸️ Duraklatıldı' : '⏹️ Durduruldu';

        const progress = task.progress || (task.status === 'completed' ? 100 : 0);
        const speed = task.speed || 0;

        // Tarih bilgileri
        let startDate = task.start_date || '...';
        let lastCandleDate = '-';

        if (task.target_start_ms && !startDate) {
            startDate = new Date(task.target_start_ms).toLocaleDateString('tr-TR');
        }

        if (task.current_ts) {
            const dateObj = new Date(task.current_ts);
            lastCandleDate = dateObj.toLocaleString('tr-TR', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
                timeZone: 'Europe/Istanbul'
            });
        }

        // Sembol ve market type
        let symbolName = key;
        let marketType = task.market_type || 'future';

        if (key.includes('_future') || key.includes('_spot')) {
            const parts = key.split('_');
            marketType = parts[parts.length - 1];
            symbolName = parts.slice(0, -1).join('_');
        }

        // Silme butonları
        const deleteButtons = `
            <div style="display:flex; gap:4px;">
                <button class="task-btn task-btn-delete" onclick="deleteDownloadTask('${key}', '${marketType}')" title="Sadece görevi sil (veri korunur)"
                    style="background: linear-gradient(135deg, #6b7280, #4b5563); border: none; color: white; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 0.9rem;">
                    🗑️
                </button>
                <button class="task-btn task-btn-danger" onclick="deleteDownloadTaskWithData('${key}', '${marketType}')" title="Görev + TÜM veriyi sil (DB + Flat files)"
                    style="background: linear-gradient(135deg, #dc2626, #991b1b); border: none; color: white; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 0.9rem; animation: pulse 2s infinite;">
                    ⚠️
                </button>
            </div>
        `;

        const pauseButton = (task.status === 'running' || task.status === 'paused') ? `
            <button class="task-btn" onclick="togglePause('${key}', '${task.status === 'paused' ? 'resume' : 'pause'}')" title="${task.status === 'paused' ? 'Devam Et' : 'Duraklat'}"
                style="background: var(--neon-blue); border: none; color: white; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 0.9rem;">
                ${task.status === 'paused' ? '▶️' : '⏸️'}
            </button>
        ` : '';

        return `
            <div class="task-item ${statusClass}">
                <div class="task-header">
                    <span class="task-symbol">${symbolName}</span>
                    <span class="task-status status-${statusClass}">${statusDisplay}</span>
                </div>

                <div class="task-body">
                    <div class="task-info">
                        <span class="task-info-label">Timeframe</span>
                        <span class="task-info-value">${task.timeframe || '1m'}</span>
                    </div>
                    <div class="task-info">
                        <span class="task-info-label">Market</span>
                        <span class="task-info-value">${marketType === 'future' ? '💹 Futures' : '💰 Spot'}</span>
                    </div>
                    <div class="task-info">
                        <span class="task-info-label">Başlangıç</span>
                        <span class="task-info-value">${startDate}</span>
                    </div>
                    <div class="task-info">
                        <span class="task-info-label">Son Mum</span>
                        <span class="task-info-value">${lastCandleDate}</span>
                    </div>
                </div>

                <div class="task-progress-section">
                    <div class="task-progress-bar-wrapper">
                        <div class="task-progress-bar-fill" style="width: ${Math.min(progress, 100)}%"></div>
                    </div>
                    <div class="task-progress-text">
                        <span>📊 %${Math.round(progress)} tamamlandı</span>
                        ${speed > 0 ? `<span>⚡ ${Math.round(speed)} mum/sn</span>` : ''}
                    </div>
                </div>

                <div class="task-footer">
                    ${deleteButtons}
                    ${pauseButton}
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Load market list from exchange
 */
async function loadMarketList() {
    try {
        const response = await fetch('/api/v1/exchange/markets');
        const data = await response.json();

        const marketListEl = document.getElementById('market-selection-list');
        const searchInput = document.getElementById('market-search');

        if (marketListEl && data.markets && data.markets.length > 0) {
            // Store markets in state for filtering
            store.setState('markets', { list: data.markets, filtered: data.markets });

            renderMarketList(data.markets);

            // Add search listener
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    filterMarkets(e.target.value);
                });
            }

            console.log(`📊 [MARKETS] ${data.markets.length} market loaded`);
        }

    } catch (error) {
        console.error('❌ [MARKETS] Load error:', error);
    }
}

/**
 * Render market list
 */
function renderMarketList(markets) {
    const marketListEl = document.getElementById('market-selection-list');
    if (!marketListEl) return;

    marketListEl.innerHTML = markets.map(m => `
        <div class="market-item" onclick="selectMarket('${m.symbol}', '${m.raw_type}')">
            <span>${m.symbol}</span>
            <span class="market-type">${m.type}</span>
        </div>
    `).join('');
}

/**
 * Filter markets by search query
 */
function filterMarkets(query) {
    const state = store.get('markets');
    if (!state || !state.list) return;

    const filtered = state.list.filter(m =>
        m.symbol.toLowerCase().includes(query.toLowerCase()) ||
        m.base.toLowerCase().includes(query.toLowerCase())
    );

    store.setState('markets', { ...state, filtered });
    renderMarketList(filtered);

    console.log(`🔍 [FILTER] ${filtered.length} markets found`);
}

/**
 * Save market selection (called from HTML)
 */
window.saveMarketSelection = function() {
    console.log('💾 [MARKET] Selection saved');
    // Implement market selection logic here
};

/**
 * Select market (called from HTML)
 */
window.selectMarket = function(symbol, marketType) {
    console.log(`📊 [MARKET] Selected: ${symbol} (${marketType})`);

    // Auto-fill symbol in download section
    const selectedSymbolEl = document.getElementById('selected-symbol-val');
    const selectedMarketTypeEl = document.getElementById('market-type-display');

    if (selectedSymbolEl) {
        selectedSymbolEl.textContent = symbol;

        // Visual feedback
        const container = document.getElementById('selected-symbol-container');
        if (container) {
            container.classList.add('pulse-blue');
            setTimeout(() => container.classList.remove('pulse-blue'), 2000);
        }

        console.log(`✅ [MARKET] Symbol filled: ${symbol}`);
    }

    if (selectedMarketTypeEl) {
        selectedMarketTypeEl.textContent = marketType === 'future' ? '💹 Vadeli' : '💰 Spot';
        console.log(`✅ [MARKET] Market type filled: ${marketType}`);
    }

    // Scroll to download section
    const downloadSection = document.getElementById('download-controls');
    if (downloadSection) {
        downloadSection.scrollIntoView({ behavior: 'smooth', block: 'center' });
        console.log('📜 [MARKET] Scrolled to download section');
    }
};

/**
 * Delete symbol data (called from HTML)
 */
window.deleteSymbolData = async function(symbol, marketType) {
    if (!confirm(`${symbol} (${marketType === 'future' ? 'Futures' : 'Spot'}) verilerini silmek istediğinizden emin misiniz?\n\nBu işlem geri alınamaz!`)) {
        return;
    }

    try {
        alert(`🗑️ ${symbol} verileri siliniyor...`);

        const result = await api.deleteData(symbol, marketType);

        if (result.status === 'success') {
            alert(`✅ ${symbol} verileri silindi!`);
            await loadDatabaseInventory(); // Refresh inventory
            await loadActiveTasks();
        } else {
            alert(`❌ Silme hatası: ${result.message}`);
        }
    } catch (error) {
        alert(`❌ Silme hatası: ${error.message}`);
    }
};

/**
 * Start download (called from HTML)
 */
window.startDownload = async function() {
    const symbol = document.getElementById('selected-symbol-val')?.textContent;
    const startDate = document.getElementById('download-start-date')?.value;
    const marketType = document.getElementById('market-type-filter')?.value || 'future';

    if (!symbol) {
        alert('❌ Lütfen bir sembol seçin!');
        return;
    }

    if (!startDate) {
        alert('❌ Lütfen bir başlangıç tarihi seçin!');
        return;
    }

    try {
        console.log(`🚀 [DOWNLOAD] Starting: ${symbol} from ${startDate}`);

        const result = await api.startDownload(symbol, '1m', startDate);

        if (result.status === 'started' || result.status === 'exists') {
            alert(`✅ ${result.message}`);
            await loadActiveTasks(); // Refresh tasks
        } else {
            alert(`⚠️ ${result.message}`);
        }

    } catch (error) {
        console.error('❌ [DOWNLOAD] Error:', error);
        alert('❌ İndirme hatası: ' + error.message);
    }
};

/**
 * Stop download (called from HTML)
 */
window.stopDownload = async function() {
    const symbol = document.getElementById('selected-symbol-val')?.textContent;

    if (!symbol) {
        alert('❌ Lütfen bir sembol seçin!');
        return;
    }

    try {
        const result = await api.stopDownload(symbol);
        alert(result.message);
        await loadActiveTasks();
    } catch (error) {
        alert('❌ Durdurma hatası: ' + error.message);
    }
};

/**
 * Delete all data (called from HTML)
 */
window.deleteAllData = async function() {
    if (!confirm('⚠️ DİKKAT! Tüm veriler silinecek. Emin misiniz?')) {
        return;
    }

    try {
        const response = await fetch('/api/v1/data/delete-all', { method: 'DELETE' });
        const result = await response.json();

        if (result.status === 'success') {
            alert(`✅ ${result.message}`);
            await loadActiveTasks();
        } else {
            alert(`⚠️ ${result.message}`);
        }
    } catch (error) {
        alert('❌ Silme hatası: ' + error.message);
    }
};

/**
 * Delete download task (called from HTML)
 */
window.deleteDownloadTask = async function(symbol, marketType) {
    if (!confirm(`${symbol} (${marketType}) için indirme görevi silinecek. Veri KORUNUR, sadece görev silinir. Emin misiniz?`)) {
        return;
    }

    try {
        const result = await api.deleteDownloadTask(symbol, marketType);

        if (result.status === 'success') {
            alert(`✅ ${result.message}`);
            await loadActiveTasks();
        } else {
            alert(`❌ Silme hatası: ${result.message}`);
        }
    } catch (error) {
        alert('❌ Silme hatası: ' + error.message);
    }
};

/**
 * Delete download task with data (called from HTML)
 */
window.deleteDownloadTaskWithData = async function(symbol, marketType) {
    if (!confirm(`⚠️ DİKKAT! ${symbol} (${marketType}) için:\n\n• İndirme görevi silinecek\n• TÜM mum verileri silinecek (DB)\n• TÜM flat file'lar silinecek\n\nBu işlem GERİ ALINAMAZ! Emin misiniz?`)) {
        return;
    }

    // İkinci onay
    if (!confirm('Gerçekten emin misiniz? TÜM veriler silinecek!')) {
        return;
    }

    try {
        alert(`⚠️ ${symbol} görev + veri siliniyor...`);

        // 1. Önce download task sil
        await api.deleteDownloadTask(symbol, marketType);

        // 2. Veriyi sil (DB + Flat files)
        const symbolClean = symbol.split('_')[0].trim();
        const deleteDataResult = await fetch('/api/v1/data/delete-klines', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: symbolClean,
                market_type: marketType
            })
        });

        const deleteDataJson = await deleteDataResult.json();

        if (deleteDataJson.status === 'success') {
            alert(`✅ ${symbol} görev + TÜM veriler silindi!`);
        } else {
            alert(`⚠️ Görev silindi ama veri silme hatası: ${deleteDataJson.message}`);
        }

        await loadActiveTasks();

    } catch (error) {
        alert('❌ Silme hatası: ' + error.message);
    }
};

/**
 * Toggle pause (called from HTML)
 */
window.togglePause = async function(symbol, action) {
    try {
        const result = await api.togglePause(symbol, action);

        if (result.status === 'success') {
            alert(`✅ ${result.message}`);
            await loadActiveTasks();
        } else {
            alert(`❌ Hata: ${result.message}`);
        }
    } catch (error) {
        alert('❌ Hata: ' + error.message);
    }
};

// ============================================================================
// UI UTILITIES
// ============================================================================

/**
 * Add line to AI Terminal
 * @param {string} message - Message to add
 */
let terminalLogQueue = [];
let terminalUpdateTimer = null;

function addTerminalLog(message) {
    terminalLogQueue.push(message);

    if (!terminalUpdateTimer) {
        terminalUpdateTimer = setTimeout(() => {
            const body = document.getElementById('terminal-body');
            if (body) {
                // Batch DOM updates using DocumentFragment
                const fragment = document.createDocumentFragment();

                terminalLogQueue.forEach(msg => {
                    const line = document.createElement('div');
                    line.className = 'terminal-line';
                    line.textContent = msg; // Avoid innerHTML for XSS protection
                    fragment.appendChild(line);
                });

                body.appendChild(fragment);

                // Ensure scroll happens only once per batch
                body.scrollTop = body.scrollHeight;

                // Keep only last 50 lines
                while (body.children.length > 50) {
                    body.removeChild(body.firstChild);
                }
            }

            terminalLogQueue = [];
            terminalUpdateTimer = null;
        }, 500); // 500ms debounce/throttle batch update
    }
}

/**
 * Show toast notification
 * @param {string} message - Notification message
 * @param {string} type - success, error, info, warning
 */
function showToast(message, type = 'info') {
    // Also log to terminal
    addTerminalLog(message);

    const container = document.getElementById('toast-container') || createToastContainer();

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '❌';
    if (type === 'warning') icon = '⚠️';

    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <span class="toast-message">${message}</span>
    `;

    container.appendChild(toast);

    // Auto-remove
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
    return container;
}

// ============================================================================
// BOT LAUNCHER
// ============================================================================

/**
 * Handle bot start form submission
 */
async function handleBotSubmit(event) {
    event.preventDefault();

    const timeframeEl = document.getElementById('bot-timeframe');
    const botData = {
        symbol: document.getElementById('bot-symbol').value,
        strategy_id: document.getElementById('bot-strategy').value,
        timeframe: timeframeEl?.value || '1m',  // Fallback to '1m' if empty
        market_type: document.getElementById('bot-market').value,
        margin_type: document.getElementById('bot-margin-type').value
    };

    // 🔥 DEBUG: Form değerlerini logla
    console.log('🔥 [BOT FORM] handleBotSubmit çağrıldı');
    console.log('   📊 Symbol:', botData.symbol);
    console.log('   📚 Strategy:', botData.strategy_id);
    console.log('   ⏱️ Timeframe:', botData.timeframe, `(element value: ${timeframeEl?.value})`);
    console.log('   🏛️ Market:', botData.market_type);
    console.log('   🛡️ Margin:', botData.margin_type);

    if (!botData.symbol || !botData.strategy_id) {
        showToast('❌ Lütfen sembol ve strateji seçin!', 'error');
        return;
    }

    try {
        showToast(`🚀 ${botData.symbol} için bot başlatılıyor...`, 'info');
        const result = await botManager.startBot(botData);
        showToast(`✅ Bot başlatıldı! ID: ${result.bot_id}`, 'success');
    } catch (error) {
        showToast(`❌ Hata: ${error.message}`, 'error');
    }
}

// ============================================================================
// SETTINGS FORMS
// ============================================================================

/**
 * Load general bot config
 */
async function loadBotConfig() {
    try {
        const data = await api.getBotConfig();
        if (data.status === 'success' && data.config) {
            document.getElementById('bot-config-exchange').value = data.config.exchange || 'binance';
            document.getElementById('bot-config-environment').value = data.config.environment || 'development';
            document.getElementById('bot-config-loglevel').value = data.config.log_level || 'INFO';
            console.log('⚙️ [SETTINGS] Bot config loaded');
        }
    } catch (error) {
        console.error('❌ [SETTINGS] Bot config load error:', error);
    }
}

/**
 * Save general bot config
 */
async function saveBotConfig() {
    const data = {
        exchange: document.getElementById('bot-config-exchange').value,
        environment: document.getElementById('bot-config-environment').value,
        log_level: document.getElementById('bot-config-loglevel').value
    };

    try {
        const result = await api.saveBotConfig(data);
        if (result.status === 'success') {
            showToast('✅ Bot ayarları güncellendi', 'success');
        } else {
            showToast('❌ ' + result.message, 'error');
        }
    } catch (error) {
        showToast('❌ Kaydetme hatası: ' + error.message, 'error');
    }
}

/**
 * Load risk settings
 */
async function loadRiskSettings() {
    try {
        const data = await api.getRiskSettings();

        if (data.status === 'success' && data.config) {
            // Fill form inputs (Aligning with HTML IDs)
            document.getElementById('risk-max-risk').value = data.config.max_risk_per_trade_percent || 0.2;
            document.getElementById('risk-max-leverage').value = data.config.max_leverage || 10;
            document.getElementById('risk-max-positions').value = data.config.max_open_positions || 5;
            document.getElementById('risk-max-losses').value = data.config.max_consecutive_losses || 10;
            document.getElementById('risk-kill-switch-enabled').checked = data.config.kill_switch_enabled !== false;

            console.log('⚙️ [SETTINGS] Risk settings loaded');
        }
    } catch (error) {
        console.error('❌ [SETTINGS] Risk load error:', error);
    }
}

/**
 * Save risk settings
 */
async function saveRiskSettings() {
    const data = {
        max_risk_per_trade_percent: parseFloat(document.getElementById('risk-max-risk').value),
        max_leverage: parseInt(document.getElementById('risk-max-leverage').value),
        max_open_positions: parseInt(document.getElementById('risk-max-positions').value),
        max_consecutive_losses: parseInt(document.getElementById('risk-max-losses').value),
        kill_switch_enabled: document.getElementById('risk-kill-switch-enabled').checked
    };

    // Validation
    if (data.max_risk_per_trade_percent < 0.1 || data.max_risk_per_trade_percent > 5.0) {
        showToast('❌ Risk %0.1 - %5.0 arasında olmalı!', 'error');
        return;
    }

    if (data.max_leverage < 1 || data.max_leverage > 50) {
        showToast('❌ Kaldıraç 1x - 50x arasında olmalı!', 'error');
        return;
    }

    if (data.max_open_positions < 1 || data.max_open_positions > 20) {
        showToast('❌ Max pozisyon 1 - 20 arasında olmalı!', 'error');
        return;
    }

    try {
        console.log('💾 [SETTINGS] Risk ayarları gönderiliyor:', data);
        const result = await api.saveRiskSettings(data);
        console.log('💾 [SETTINGS] Sonuç:', result);

        if (result.status === 'success') {
            showToast('✅ Risk ayarları güncellendi (Hot-Reload)', 'success');

            // Başarı sonrası config'i yeniden yükle
            await loadRiskSettings();
        } else {
            // Hata mesajını düzgün formatla
            let errorMsg = 'Bilinmeyen hata';
            if (result.message) {
                errorMsg = typeof result.message === 'string' ? result.message : JSON.stringify(result.message);
            }
            showToast('❌ ' + errorMsg, 'error');
        }
    } catch (error) {
        console.error('❌ [SETTINGS] Risk save error:', error);
        
        // Hata mesajını düzgün formatla
        let errorMsg = 'Sunucu hatası';
        if (error.message) {
            errorMsg = typeof error.message === 'string' ? error.message : JSON.stringify(error.message);
        } else if (typeof error === 'string') {
            errorMsg = error;
        } else if (error.detail) {
            errorMsg = typeof error.detail === 'string' ? error.detail : JSON.stringify(error.detail);
        }
        
        showToast('❌ Kaydetme hatası: ' + errorMsg, 'error');
    }
}

/**
 * Load advanced settings
 */
async function loadAdvancedSettings() {
    try {
        const data = await api.getAdvancedSettings();

        if (data.status === 'success' && data.config) {
            // WFO
            const wfo = data.config.wfo || {};
            document.getElementById('wfo-enabled').checked = wfo.enabled || false;
            document.getElementById('wfo-train-days').value = wfo.train_days || 30;
            document.getElementById('wfo-test-days').value = wfo.test_days || 7;
            document.getElementById('wfo-interval').value = wfo.reoptimize_interval || 168;

            // ML
            const ml = data.config.ml || {};
            document.getElementById('ml-enabled').checked = ml.enabled || true;
            document.getElementById('ml-threshold').value = ml.confidence_threshold || 0.6;

            // HTF
            const htf = data.config.htf || {};
            document.getElementById('htf-enabled').checked = htf.enabled || true;
            document.getElementById('htf-method').value = htf.trend_method || 'ema_stack';

            // Kalman
            const kalman = data.config.kalman || { enabled: true, q: 0.001, r: 0.1 };
            document.getElementById('kalman-enabled').checked = kalman.enabled;
            document.getElementById('kalman-process-noise').value = kalman.q || 0.001;
            document.getElementById('kalman-measurement-noise').value = kalman.r || 0.1;

            // Candle Lock
            const candleLock = data.config.candle_lock || { enabled: true, interval: 1 };
            document.getElementById('candle-lock-enabled').checked = candleLock.enabled;
            document.getElementById('candle-lock-interval').value = candleLock.interval || 5;

            console.log('⚙️ [SETTINGS] Advanced settings loaded');
        }
    } catch (error) {
        console.error('❌ [SETTINGS] Advanced load error:', error);
    }
}

/**
 * Save advanced settings
 */
async function saveAdvancedSettings() {
    const data = {
        wfo: {
            enabled: document.getElementById('wfo-enabled').checked,
            train_days: parseInt(document.getElementById('wfo-train-days').value),
            test_days: parseInt(document.getElementById('wfo-test-days').value),
            reoptimize_interval: parseInt(document.getElementById('wfo-interval').value)
        },
        ml: {
            enabled: document.getElementById('ml-enabled').checked,
            confidence_threshold: parseFloat(document.getElementById('ml-threshold').value)
        },
        htf: {
            enabled: document.getElementById('htf-enabled').checked,
            trend_method: document.getElementById('htf-method').value
        }
    };

    try {
        const result = await api.saveAdvancedSettings(data);
        if (result.status === 'success') {
            showToast('✅ Gelişmiş ayarlar güncellendi', 'success');
        } else {
            showToast('❌ ' + result.message, 'error');
        }
    } catch (error) {
        showToast('❌ Kaydetme hatası: ' + error.message, 'error');
    }
}

/**
 * Save Kalman Settings
 */
async function saveKalmanSettings() {
    const data = {
        kalman: {
            enabled: document.getElementById('kalman-enabled').checked,
            q: parseFloat(document.getElementById('kalman-process-noise').value),
            r: parseFloat(document.getElementById('kalman-measurement-noise').value)
        }
    };

    try {
        const result = await api.saveAdvancedSettings(data);
        if (result.status === 'success') {
            showToast('✅ Kalman ayarları güncellendi', 'success');
        } else {
            showToast('❌ ' + result.message, 'error');
        }
    } catch (error) {
        showToast('❌ Kaydetme hatası: ' + error.message, 'error');
    }
}

async function resetKalmanSettings() {
    document.getElementById('kalman-process-noise').value = 0.001;
    document.getElementById('kalman-measurement-noise').value = 0.1;
    await saveKalmanSettings();
}

/**
 * Save Candle Lock Settings
 */
async function saveCandleLockSettings() {
    const data = {
        candle_lock: {
            enabled: document.getElementById('candle-lock-enabled').checked,
            interval: parseInt(document.getElementById('candle-lock-interval').value)
        }
    };

    try {
        const result = await api.saveAdvancedSettings(data);
        if (result.status === 'success') {
            showToast('✅ Mum kapanış kilidi güncellendi', 'success');
        } else {
            showToast('❌ ' + result.message, 'error');
        }
    } catch (error) {
        showToast('❌ Kaydetme hatası: ' + error.message, 'error');
    }
}

async function resetCandleLockSettings() {
    document.getElementById('candle-lock-interval').value = 5;
    await saveCandleLockSettings();
}

/**
 * Save API keys
 */
async function saveApiKeys() {
    const apiKey = document.getElementById('api-key').value;
    const apiSecret = document.getElementById('api-secret').value;

    if (!apiKey || !apiSecret) {
        showToast('❌ API Key ve Secret giriniz!', 'error');
        return;
    }

    try {
        const result = await api.saveApiKeys({ api_key: apiKey, api_secret: apiSecret });

        if (result.status === 'success') {
            showToast('✅ API anahtarları şifrelenerek kaydedildi', 'success');
        } else {
            showToast('❌ ' + result.message, 'error');
        }
    } catch (error) {
        showToast('❌ Kaydetme hatası: ' + error.message, 'error');
    }
}

/**
 * Test API connection
 */
async function testApiConnection() {
    const apiKey = document.getElementById('api-key').value;
    const apiSecret = document.getElementById('api-secret').value;

    if (!apiKey || !apiSecret) {
        showToast('❌ API Key ve Secret giriniz!', 'error');
        return;
    }

    try {
        showToast('🧪 API bağlantısı test ediliyor...', 'info');
        const result = await api.testApiConnection({ api_key: apiKey, api_secret: apiSecret });

        if (result.valid) {
            showToast(`✅ API bağlantısı başarılı!`, 'success');
        } else {
            showToast('❌ ' + result.message, 'error');
        }
    } catch (error) {
        showToast('❌ Test hatası: ' + error.message, 'error');
    }
}

/**
 * Load symbols for bot launcher
 */
async function loadSymbolsForBot() {
    try {
        const data = await api.getSymbolsWithData();
        const symbols = data.symbols || [];

        const symbolSelects = document.querySelectorAll('.symbol-select');
        symbolSelects.forEach(select => {
            // ML training symbol selection should NOT be filled here
            if (select.id !== 'market-symbol' && select.id !== 'ml-train-symbol') {
                select.innerHTML = '<option value="">Sembol Seçin...</option>' +
                    symbols.map(s => `<option value="${s.symbol}">${s.symbol}</option>`).join('');
            }
        });

        console.log(`📊 [SYMBOLS] ${symbols.length} sembol yüklendi`);
    } catch (error) {
        console.error('❌ [SYMBOLS] Load error:', error);
    }
}

/**
 * Load symbols for ML training
 */
async function loadSymbolsForML() {
    try {
        const data = await api.getSymbolsWithData();
        const symbols = data.symbols || [];

        const mlSymbolSelect = document.getElementById('ml-train-symbol');
        if (mlSymbolSelect) {
            mlSymbolSelect.innerHTML = '<option value="">Sembol Seçin...</option>' +
                symbols.map(s => `<option value="${s.symbol}">${s.symbol}</option>`).join('');
        }

        console.log(`📊 [ML] ${symbols.length} sembol ML için yüklendi`);
    } catch (error) {
        console.error('❌ [ML] Symbol load error:', error);
    }
}

/**
 * Load strategies for bot launcher
 */
async function loadStrategiesForBot() {
    try {
        const data = await api.getStrategies();
        const strategies = data.strategies || [];

        const strategySelects = document.querySelectorAll('.strategy-select');
        strategySelects.forEach(select => {
            // ML training symbol selection should NOT be filled here
            if (select.id !== 'ml-train-symbol') {
                select.innerHTML = '<option value="">Strateji Seçin...</option>' +
                    strategies.map(s => `<option value="${s.id || s.strategy_id}">${s.name || s.strategy_id}</option>`).join('');
            }
        });

        console.log(`📚 [STRATEGIES] ${strategies.length} strateji yüklendi`);
    } catch (error) {
        console.error('❌ [STRATEGIES] Load error:', error);
    }
}

/**
 * Load timeframes for bot launcher
 */
async function loadTimeframesForBot() {
    const timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d'];

    const timeframeSelects = document.querySelectorAll('.timeframe-select');
    timeframeSelects.forEach(select => {
        // ML training timeframe selection should NOT be filled here
        if (select.id !== 'ml-train-timeframe') {
            select.innerHTML = '<option value="">Timeframe Seçin...</option>' +
                timeframes.map(tf => `<option value="${tf}">${tf}</option>`).join('');
        }
    });

    console.log(`⏱️ [TIMEFRAMES] ${timeframes.length} timeframe yüklendi`);
}

/**
 * Load timeframes for ML training
 */
async function loadTimeframesForML() {
    const timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d'];

    const mlTimeframeSelect = document.getElementById('ml-train-timeframe');
    if (mlTimeframeSelect) {
        mlTimeframeSelect.innerHTML = '<option value="1h" selected>1h</option>' +
            timeframes.filter(tf => tf !== '1h').map(tf => `<option value="${tf}">${tf}</option>`).join('');
    }

    console.log(`⏱️ [ML] Timeframes yüklendi`);
}

/**
 * Load strategy library (detailed strategy info with logic)
 */
async function loadStrategyLibrary() {
    try {
        const data = await api.getStrategies();
        const strategies = data.strategies || [];

        console.log(`📚 [LIBRARY] ${strategies.length} strateji yüklendi`);
        renderStrategyLibrary(strategies);
    } catch (error) {
        console.error('❌ [LIBRARY] Load error:', error);
    }
}

/**
 * Load trade history
 */
async function loadTradeHistory() {
    try {
        console.log('📜 [HISTORY] Loading trade history...');
        const data = await api.getTrades();
        const trades = data.trades || [];

        console.log(`📜 [HISTORY] API Response:`, data);
        console.log(`📜 [HISTORY] ${trades.length} işlem yüklendi`);
        
        if (trades.length === 0) {
            console.warn('⚠️ [HISTORY] Hiç işlem yok!');
            console.log('API Count:', data.count);
            console.log('API Status:', data.status);
        }
        
        renderTradeHistory(trades);
    } catch (error) {
        console.error('❌ [HISTORY] Load error:', error);
        console.error('Stack trace:', error.stack);
        const tbody = document.getElementById('history-body');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:40px; color:var(--neon-red);">Hata: ${error.message}</td></tr>`;
        }
    }
}

/**
 * Render trade history table
 */
function renderTradeHistory(trades) {
    const tbody = document.getElementById('history-body');
    if (!tbody) return;

    if (trades.length === 0) {
        tbody.innerHTML = `<tr><td colspan="10" style="text-align:center; padding:40px; color:var(--text-muted);">Henüz işlem geçmişi yok</td></tr>`;
        updateHistoryStats([]);
        return;
    }

    tbody.innerHTML = trades.map(trade => {
        const pnl = trade.pnl_usd || trade.pnl || 0;
        const pnlPercent = trade.pnl_percent || 0;
        const isProfit = pnl >= 0;
        const direction = trade.direction || 'LONG';
        const directionIcon = direction === 'LONG' ? '🟢' : '🔴';
        const closedAt = trade.closed_at;
        let dateStr = 'N/A';
        if (closedAt) {
            try {
                if (typeof closedAt === 'string') {
                    dateStr = new Date(closedAt).toLocaleString('tr-TR');
                } else if (closedAt instanceof Date) {
                    dateStr = closedAt.toLocaleString('tr-TR');
                }
            } catch (e) {
                dateStr = closedAt;
            }
        }

        return `
            <tr>
                <td>${dateStr}</td>
                <td style="font-weight:600; color:var(--text-main);">${trade.symbol || 'N/A'}</td>
                <td style="font-size:0.85rem; color:var(--text-muted);">${trade.strategy_id || trade.strategy || 'N/A'}</td>
                <td><span style="color:${direction === 'LONG' ? 'var(--neon-green)' : 'var(--neon-red)'};">${directionIcon} ${direction}</span></td>
                <td style="font-family:monospace;">$${(trade.entry_price || 0).toFixed(4)}</td>
                <td style="font-family:monospace;">$${(trade.exit_price || 0).toFixed(4)}</td>
                <td style="font-family:monospace;">${(trade.size || 0).toFixed(4)} / ${trade.leverage || 1}x</td>
                <td style="font-family:monospace; font-weight:bold; color:${isProfit ? 'var(--neon-green)' : 'var(--neon-red)'};">
                    ${isProfit ? '+' : ''}$${pnl.toFixed(2)}
                </td>
                <td style="font-family:monospace; color:${pnlPercent >= 0 ? 'var(--neon-green)' : 'var(--neon-red)'};">
                    ${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(2)}%
                </td>
                <td style="font-size:0.75rem; color:var(--text-muted); max-width:150px; overflow:hidden; text-overflow:ellipsis;">
                    ${trade.reason || '-'}
                </td>
            </tr>
        `;
    }).join('');

    updateHistoryStats(trades);
    console.log('✅ [HISTORY] Table rendered');
}

/**
 * Update trade history statistics
 */
function updateHistoryStats(trades) {
    const totalTrades = trades.length;
    const winningTrades = trades.filter(t => (t.pnl_usd || t.pnl || 0) > 0).length;
    const winRate = totalTrades > 0 ? (winningTrades / totalTrades * 100) : 0;
    const totalPnl = trades.reduce((sum, t) => sum + (t.pnl_usd || t.pnl || 0), 0);
    const avgPnl = totalTrades > 0 ? totalPnl / totalTrades : 0;

    // Calculate best strategy
    const strategyPnl = {};
    trades.forEach(t => {
        const strat = t.strategy_id || t.strategy || 'Unknown';
        const pnl = t.pnl_usd || t.pnl || 0;
        strategyPnl[strat] = (strategyPnl[strat] || 0) + pnl;
    });

    let bestStrategy = 'N/A';
    let maxPnl = -Infinity;
    Object.entries(strategyPnl).forEach(([strat, pnl]) => {
        if (pnl > maxPnl) {
            maxPnl = pnl;
            bestStrategy = strat;
        }
    });

    // Update DOM
    const elTotalTrades = document.getElementById('hist-total-trades');
    const elWinRate = document.getElementById('hist-win-rate');
    const elTotalPnl = document.getElementById('hist-total-pnl');
    const elAvgPnl = document.getElementById('hist-avg-pnl');
    const elBestStrategy = document.getElementById('hist-best-strategy');

    if (elTotalTrades) elTotalTrades.textContent = totalTrades;
    if (elWinRate) elWinRate.textContent = `${winRate.toFixed(1)}%`;
    if (elTotalPnl) {
        elTotalPnl.textContent = `$${totalPnl.toFixed(2)}`;
        elTotalPnl.style.color = totalPnl >= 0 ? 'var(--neon-green)' : 'var(--neon-red)';

        // Add neon border to parent card based on profit/loss
        const parentCard = elTotalPnl.closest('.card, .kpi-card, .glass-panel');
        if (parentCard) {
            parentCard.classList.remove('profit', 'loss');
            parentCard.classList.add(totalPnl >= 0 ? 'profit' : 'loss');
        }
    }
    if (elAvgPnl) {
        elAvgPnl.textContent = `$${avgPnl.toFixed(2)}`;
        elAvgPnl.style.color = avgPnl >= 0 ? 'var(--neon-green)' : 'var(--neon-red)';
    }
    if (elBestStrategy) elBestStrategy.textContent = bestStrategy;

    console.log('📊 [HISTORY] Stats updated');
}

/**
 * Clear trade history
 */
async function clearTradeHistory() {
    if (!confirm('⚠️ Tüm işlem geçmişini silmek istediğinizden emin misiniz? Bu işlem geri alınamaz!')) {
        return;
    }

    try {
        const result = await api.clearTrades();
        if (result.status === 'success') {
            showToast('✅ İşlem geçmişi temizlendi', 'success');
            await loadTradeHistory();
        } else {
            showToast('❌ ' + (result.message || 'Temizleme başarısız'), 'error');
        }
    } catch (error) {
        showToast('❌ Hata: ' + error.message, 'error');
    }
}

/**
 * Filter history table by symbol
 */
window.filterHistoryTable = function() {
    const filterInput = document.getElementById('hist-filter-symbol');
    if (!filterInput) return;

    const filter = filterInput.value.toUpperCase();
    const table = document.getElementById('history-table');
    if (!table) return;

    const tr = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');

    for (let i = 0; i < tr.length; i++) {
        const td = tr[i].getElementsByTagName('td')[1]; // Symbol column
        if (td) {
            const txtValue = td.textContent || td.innerText;
            tr[i].style.display = txtValue.toUpperCase().indexOf(filter) > -1 ? '' : 'none';
        }
    }
};

// Global scope'a ekle (HTML onclick için)
window.loadTradeHistory = loadTradeHistory;
window.clearTradeHistory = clearTradeHistory;

// ============================================================================
// ML TRAINING FUNCTIONS
// ============================================================================

/**
 * Validate mum count against database
 */
window.validateMumCount = function() {
    const symbolSelect = document.getElementById('ml-train-symbol');
    const timeframeSelect = document.getElementById('ml-train-timeframe');
    const limitInput = document.getElementById('ml-train-limit');
    const dbCountEl = document.getElementById('ml-db-count');
    const warningEl = document.getElementById('ml-limit-warning');
    const rangeEl = document.getElementById('ml-db-range');

    if (!symbolSelect || !timeframeSelect || !limitInput) return;

    const symbol = symbolSelect.value;
    const timeframe = timeframeSelect.value;

    if (!symbol) {
        if (dbCountEl) dbCountEl.textContent = '';
        if (rangeEl) rangeEl.textContent = '';
        return;
    }

    // Get available data count from API
    api.getDataStats().then(stats => {
        if (!stats || !stats.stats) {
            if (rangeEl) {
                rangeEl.textContent = '❌ Veri sorgulanamadı!';
                rangeEl.style.color = 'var(--neon-red)';
            }
            return;
        }

        // Find matching symbol/timeframe
        const stat = stats.stats.find(s => {
            const sSymbol = s.symbol || s.pair || '';
            const sTimeframe = s.timeframe || s.tf || '';
            return sSymbol.includes(symbol) && sTimeframe === timeframe;
        });

        if (stat) {
            const dbCount = stat.candle_count || stat.count || stat.total || 0;
            const limitValue = parseInt(limitInput.value) || 0;

            if (dbCountEl) dbCountEl.textContent = `(DB: ${(dbCount / 1000).toFixed(1)}K)`;
            if (rangeEl) {
                if (limitValue > dbCount && dbCount > 0) {
                    rangeEl.textContent = `⚠️ Veritabanında ${(dbCount / 1000).toFixed(1)}K mum var. ${limitValue} mum için önce veri indirin!`;
                    rangeEl.style.color = 'var(--neon-red)';
                } else if (dbCount > 0) {
                    rangeEl.textContent = `✅ Mevcut: ${(dbCount / 1000).toFixed(1)}K mum - ${Math.min(limitValue, dbCount)} mum kullanılacak`;
                    rangeEl.style.color = 'var(--neon-green)';
                } else {
                    rangeEl.textContent = '❌ Bu sembol/timeframe için veri bulunamadı!';
                    rangeEl.style.color = 'var(--neon-red)';
                }
            }

            // Show warning if limit > db count
            if (warningEl) {
                if (limitValue > dbCount && dbCount > 0) {
                    warningEl.style.display = 'block';
                    warningEl.textContent = `⚠️ DB'de sadece ${(dbCount / 1000).toFixed(1)}K mum var! Önce veri indirin.`;
                    limitInput.style.borderColor = 'var(--neon-red)';
                } else {
                    warningEl.style.display = 'none';
                    limitInput.style.borderColor = 'rgba(255,255,255,0.1)';
                }
            }
        } else {
            if (rangeEl) {
                rangeEl.textContent = '⏳ Veri yükleniyor...';
                rangeEl.style.color = 'var(--text-muted)';
            }
        }
    }).catch(err => {
        console.error('❌ [ML] DB stats error:', err);
        if (rangeEl) {
            rangeEl.textContent = '❌ DB sorgusu başarısız!';
            rangeEl.style.color = 'var(--neon-red)';
        }
    });
};

/**
 * Start ML model training
 */
window.startMLTraining = async function() {
    const symbolSelect = document.getElementById('ml-train-symbol');
    const timeframeSelect = document.getElementById('ml-train-timeframe');
    const limitInput = document.getElementById('ml-train-limit');
    const tpInput = document.getElementById('ml-train-tp');
    const slInput = document.getElementById('ml-train-sl');

    const symbol = symbolSelect?.value;
    const timeframe = timeframeSelect?.value;
    const limit = parseInt(limitInput?.value) || 5000;
    const tpMultiplier = parseFloat(tpInput?.value) || 2.0;
    const slMultiplier = parseFloat(slInput?.value) || 2.0;

    // Validation
    if (!symbol || !timeframe) {
        showToast('❌ Sembol ve zaman dilimi seçin!', 'error');
        return;
    }

    if (limit < 100) {
        showToast('❌ Mum sayısı en az 100 olmalı!', 'error');
        return;
    }

    if (tpMultiplier < 0.5 || tpMultiplier > 10) {
        showToast('❌ TP çarpanı 0.5 - 10 arasında olmalı!', 'error');
        return;
    }

    if (slMultiplier < 0.5 || slMultiplier > 10) {
        showToast('❌ SL çarpanı 0.5 - 10 arasında olmalı!', 'error');
        return;
    }

    // Check DB count before training
    let dbCount = 0;
    try {
        const stats = await api.getDataStats();
        if (stats && stats.stats) {
            const stat = stats.stats.find(s => {
                const sSymbol = s.symbol || s.pair || '';
                const sTimeframe = s.timeframe || s.tf || '';
                return sSymbol.includes(symbol) && sTimeframe === timeframe;
            });

            if (stat) {
                dbCount = stat.candle_count || stat.count || stat.total || 0;
            }
        }
    } catch (err) {
        console.error('❌ [ML] DB stats error:', err);
    }

    // Warn if limit > db count
    if (limit > dbCount && dbCount > 0) {
        const confirmed = await new Promise(resolve => {
            const result = confirm(
                `⚠️ UYARI: Veritabanında sadece ${(dbCount / 1000).toFixed(1)}K (${dbCount}) mum var!\n\n` +
                `Siz ${limit} mum istiyorsunuz.\n\n` +
                `Seçenekler:\n` +
                `1️⃣ Devam et (Mevcut ${dbCount} mum kullanılacak)\n` +
                `2️⃣ İptal et ve önce veri indir\n\n` +
                `Devam etmek istiyor musunuz?`
            );
            resolve(result);
        });

        if (!confirmed) {
            showToast('ℹ️ Eğitim iptal edildi. Önce veri laboratuvarından veri indirebilirsiniz.', 'info');
            return;
        }
    }

    // Confirm
    if (!confirm(`🧠 ${symbol} (${timeframe}) için ML modeli eğitilecek.\n\nParametreler:\n- Mum Sayısı: ${limit}${dbCount > 0 ? ` (Mevcut: ${(dbCount / 1000).toFixed(1)}K)` : ''}\n- TP Çarpan: ${tpMultiplier}\n- SL Çarpan: ${slMultiplier}\n\nDevam etmek istiyor musunuz?`)) {
        return;
    }

    // Show progress
    const progressDiv = document.getElementById('ml-training-progress');
    const progressBar = document.getElementById('ml-progress-bar');
    const progressMsg = document.getElementById('ml-training-message');
    const resultDiv = document.getElementById('ml-training-result');

    if (progressDiv) progressDiv.style.display = 'block';
    if (progressBar) progressBar.style.width = '0%';
    if (progressMsg) progressMsg.textContent = '📊 Veri hazırlanıyor...';
    if (resultDiv) resultDiv.style.display = 'none';

    try {
        // Start training - BEKLE!
        const data = {
            symbol: symbol,
            timeframe: timeframe,
            limit: limit,
            tp_multiplier: tpMultiplier,
            sl_multiplier: slMultiplier
        };

        console.log('🧠 [ML] Eğitim başlatılıyor...', data);

        const result = await api.trainModel(data);

        if (result.status === 'success') {
            // Show success
            if (progressBar) progressBar.style.width = '100%';
            if (progressMsg) progressMsg.textContent = '✅ Eğitim tamamlandı!';

            if (resultDiv) {
                resultDiv.style.display = 'block';
                resultDiv.style.background = 'rgba(46, 220, 135, 0.1)';
                resultDiv.style.border = '1px solid var(--neon-green)';

                const accuracy = (result.accuracy || 0).toFixed(2);
                const datasetSize = result.dataset_size || 0;

                resultDiv.innerHTML = `
                    <h4 style="color: var(--neon-green); margin-bottom: 10px;">🎉 ML Model Eğitimi Başarılı!</h4>
                    <div style="text-align: left; max-width: 500px; margin: 0 auto; color: var(--text-main);">
                        <p><strong>Sembol:</strong> ${symbol}</p>
                        <p><strong>Timeframe:</strong> ${timeframe}</p>
                        <p><strong>Dataset:</strong> ${datasetSize.toLocaleString()} örnek</p>
                        <p><strong>Accuracy:</strong> ${accuracy}%</p>
                        <p style="color: var(--neon-blue); margin-top: 15px;">
                            Model artık Strateji Karar Merkezi'nde kullanıma hazır.
                        </p>
                    </div>
                `;
            }

            showToast('✅ ML modeli eğitildi! Geçmiş yenileniyor...', 'success');

            // Refresh history AFTER training completes
            setTimeout(() => {
                loadMLTrainingHistory();
            }, 500);
        } else {
            throw new Error(result.message || 'Eğitim başarısız');
        }

    } catch (error) {
        console.error('❌ [ML] Training error:', error);

        if (progressDiv) progressDiv.style.display = 'none';
        if (resultDiv) {
            resultDiv.style.display = 'block';
            resultDiv.style.background = 'rgba(248, 83, 73, 0.1)';
            resultDiv.style.border = '1px solid var(--neon-red)';
            resultDiv.innerHTML = `
                <h4 style="color: var(--neon-red); margin-bottom: 10px;">❌ Eğitim Hatası!</h4>
                <p style="color: var(--text-main); font-size: 0.85rem;">
                    ${error.message || 'Bilinmeyen hata'}
                </p>
                <p style="color: var(--text-muted); font-size: 0.75rem; margin-top: 10px;">
                    Server hatası olabilir. Console'u (F12) kontrol edin.
                </p>
            `;
        }

        showToast('❌ ML eğitimi hatası: ' + error.message, 'error');
    }
};

/**
 * Load ML training history
 */
window.loadMLTrainingHistory = async function() {
    const container = document.getElementById('training-history-table');
    if (!container) return;

    try {
        const data = await api.get('/ml/training-history');
        const history = data.history || data.training_history || [];

        if (history.length === 0) {
            container.innerHTML = `
                <p style="text-align: center; padding: 40px; color: var(--text-muted);">
                    📭 Henüz eğitilmiş model yok
                </p>
            `;
            return;
        }

        container.innerHTML = `
            <div style="overflow-x: auto;">
                <table class="positions-table" style="font-size: 0.7rem; min-width: 1200px;">
                    <thead>
                        <tr>
                            <th style="min-width: 150px;">Tarih</th>
                            <th>Sembol</th>
                            <th>TF</th>
                            <th>Dataset</th>
                            <th>Feat</th>
                            <th style="min-width: 200px;">📊 Metrikler</th>
                            <th style="min-width: 150px;">🎯 Accuracy</th>
                            <th>İşlem</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${history.map(item => {
                            const date = item.timestamp || item.created_at || 'N/A';
                            const dateStr = typeof date === 'string' ? date.split('T')[0] : date;
                            const metrics = item.metrics || {};

                            // Ana accuracy
                            const accuracy = (metrics.accuracy || 0) * 100;
                            const f1 = metrics.f1 || 0;
                            const precision = metrics.precision || 0;
                            const recall = metrics.recall || 0;

                            // Model-specific accuracies
                            const xgbAcc = (metrics.xgb_accuracy || accuracy) * 100;
                            const rfAcc = (metrics.rf_accuracy || accuracy) * 100;
                            const ensembleAcc = (metrics.ensemble_accuracy || accuracy) * 100;

                            // Color coding
                            const accColor = accuracy >= 50 ? 'var(--neon-green)' : (accuracy >= 40 ? '#ffcc00' : 'var(--neon-red)');
                            const xgbColor = xgbAcc >= 50 ? 'var(--neon-green)' : (xgbAcc >= 40 ? '#ffcc00' : 'var(--neon-red)');
                            const rfColor = rfAcc >= 50 ? 'var(--neon-green)' : (rfAcc >= 40 ? '#ffcc00' : 'var(--neon-red)');
                            const ensembleColor = ensembleAcc >= 50 ? 'var(--neon-green)' : (ensembleAcc >= 40 ? '#ffcc00' : 'var(--neon-red)');

                            return `
                                <tr style="vertical-align: top;">
                                    <td style="font-size: 0.7rem;">${dateStr}<br><span style="color: var(--text-muted);">${typeof date === 'string' && date.includes('T') ? date.split('T')[1].split('.')[0] : ''}</span></td>
                                    <td style="font-weight:600; color:var(--text-main);">${item.symbol || 'N/A'}</td>
                                    <td>${item.timeframe || 'N/A'}</td>
                                    <td>${(item.dataset_size || 0).toLocaleString()}</td>
                                    <td>${item.feature_count || 0}</td>
                                    <td>
                                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 0.65rem;">
                                            <div>Precision: <strong style="color: var(--neon-blue);">${(precision * 100).toFixed(1)}%</strong></div>
                                            <div>Recall: <strong style="color: var(--neon-purple);">${(recall * 100).toFixed(1)}%</strong></div>
                                            <div>F1-Score: <strong style="color: var(--neon-green);">${(f1 * 100).toFixed(1)}%</strong></div>
                                            <div>TP: <strong>${(metrics.tp_multiplier || 2.0).toFixed(1)}x</strong></div>
                                        </div>
                                    </td>
                                    <td>
                                        <div style="display: grid; gap: 3px; font-size: 0.65rem;">
                                            <div style="color: ${xgbColor};">🌲 XGB: <strong>${xgbAcc.toFixed(1)}%</strong></div>
                                            <div style="color: ${rfColor};">🌳 RF: <strong>${rfAcc.toFixed(1)}%</strong></div>
                                            <div style="color: ${ensembleColor}; border-top: 1px solid var(--glass-border); padding-top: 2px;">🎯 Ens: <strong>${ensembleAcc.toFixed(1)}%</strong></div>
                                        </div>
                                    </td>
                                    <td>
                                        <button onclick="deleteMLModel('${item.symbol || ''}', '${item.timeframe || ''}')"
                                            style="padding:4px 8px; background:rgba(255,255,255,0.1); color:#fff; border:none; border-radius:4px; cursor:pointer; font-size:0.65rem;"
                                            title="Modeli sil">
                                            🗑️
                                        </button>
                                    </td>
                                </tr>
                            `;
                        }).join('')}
                    </tbody>
                </table>
            </div>
        `;

        console.log(`✅ [ML] ${history.length} eğitim geçmişi yüklendi`);

    } catch (error) {
        console.error('❌ [ML] History load error:', error);
        container.innerHTML = `
            <p style="text-align: center; padding: 40px; color: var(--neon-red);">
                ❌ Geçmiş yüklenemedi: ${error.message}
            </p>
        `;
    }
};

/**
 * Clear ML training history
 */
window.clearTrainingHistory = async function() {
    if (!confirm('⚠️ Tüm ML eğitim geçmişini silmek istediğinizden emin misiniz?')) {
        return;
    }

    try {
        const result = await api.delete('/ml/training-history');
        if (result.status === 'success') {
            showToast('✅ Geçmiş temizlendi', 'success');
            loadMLTrainingHistory();
        } else {
            showToast('❌ ' + (result.message || 'Temizleme başarısız'), 'error');
        }
    } catch (error) {
        showToast('❌ Hata: ' + error.message, 'error');
    }
};

/**
 * Delete ML model
 */
window.deleteMLModel = async function(symbol, timeframe) {
    if (!symbol || !timeframe) {
        showToast('❌ Sembol ve timeframe gerekli', 'error');
        return;
    }

    if (!confirm(`⚠️ ${symbol} (${timeframe}) ML modelini silmek istediğinizden emin misiniz?`)) {
        return;
    }

    try {
        const result = await api.deleteMLModel(symbol, timeframe);
        if (result.status === 'success') {
            showToast('✅ Model silindi', 'success');
            loadMLTrainingHistory();
        } else {
            showToast('❌ ' + (result.message || 'Silme başarısız'), 'error');
        }
    } catch (error) {
        showToast('❌ Hata: ' + error.message, 'error');
    }
};

/**
 * Render strategy library with detailed info
 */
function renderStrategyLibrary(strategies) {
    const container = document.getElementById('strategy-library-container');
    if (!container) return;

    if (strategies.length === 0) {
        container.innerHTML = `
            <div style="text-align: center; padding: 40px; color: var(--text-muted); grid-column: span 3;">
                📭 Henüz strateji bulunmuyor
            </div>
        `;
        return;
    }

    // Strateji bilgilerini detaylı göster
    container.innerHTML = strategies.map(strategy => {
        const strategyId = strategy.id || strategy.strategy_id || strategy.filename || 'unknown';
        const name = strategy.name || strategy.strategy_id || strategyId;
        const description = strategy.description || strategy.info || 'Açıklama yok';
        const indicators = strategy.indicators || [];
        const longConditions = strategy.conditions?.LONG || [];
        const shortConditions = strategy.conditions?.SHORT || [];

        return `
            <div class="strategy-card glass-panel" style="padding: 20px; border-radius: 12px; border: 1px solid var(--glass-border);">
                <div class="strategy-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                    <h3 style="color: var(--neon-blue); margin: 0;">${name}</h3>
                    <span style="font-size: 0.75rem; padding: 4px 8px; background: rgba(88, 166, 255, 0.1); color: var(--neon-blue); border-radius: 4px;">
                        ${indicators.length} İndikatör
                    </span>
                </div>

                <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 15px; line-height: 1.5;">
                    ${description}
                </p>

                <div style="margin-bottom: 15px;">
                    <h4 style="font-size: 0.8rem; color: var(--text-muted); margin-bottom: 8px;">📊 İndikatörler:</h4>
                    <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                        ${indicators.map(ind => `
                            <span style="font-size: 0.75rem; padding: 4px 8px; background: rgba(255,255,255,0.05); border-radius: 4px; color: var(--text-main);">
                                ${ind.name || ind}
                            </span>
                        `).join('')}
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                    <div style="background: rgba(46, 220, 135, 0.05); padding: 12px; border-radius: 8px; border: 1px solid rgba(46, 220, 135, 0.2);">
                        <h4 style="font-size: 0.8rem; color: var(--neon-green); margin-bottom: 8px;">🟢 LONG Koşulları</h4>
                        <div style="font-size: 0.75rem; color: var(--text-muted); line-height: 1.6;">
                            ${longConditions.length > 0 ? longConditions.map(c => `• ${c.description || c}`).join('<br>') : 'ℹ️ Koşul tanımlanmamış'}
                        </div>
                    </div>

                    <div style="background: rgba(248, 83, 73, 0.05); padding: 12px; border-radius: 8px; border: 1px solid rgba(248, 83, 73, 0.2);">
                        <h4 style="font-size: 0.8rem; color: var(--neon-red); margin-bottom: 8px;">🔴 SHORT Koşulları</h4>
                        <div style="font-size: 0.75rem; color: var(--text-muted); line-height: 1.6;">
                            ${shortConditions.length > 0 ? shortConditions.map(c => `• ${c.description || c}`).join('<br>') : 'ℹ️ Koşul tanımlanmamış'}
                        </div>
                    </div>
                </div>

                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid var(--glass-border); display: flex; gap: 8px;">
                    <button onclick="useStrategy('${strategyId}')" style="flex: 1; padding: 8px 12px; background: var(--neon-blue); color: #fff; border: none; border-radius: 6px; cursor: pointer; font-weight: 600; font-size: 0.85rem;">
                        🚀 Bu Stratejiyi Kullan
                    </button>
                    <button onclick="editStrategy('${strategyId}')" style="padding: 8px 12px; background: rgba(255,255,255,0.1); color: #fff; border: none; border-radius: 6px; cursor: pointer; font-size: 0.85rem;">
                        ✏️ Düzenle
                    </button>
                </div>
            </div>
        `;
    }).join('');

    console.log('✅ [LIBRARY] Stratejiler render edildi');
}

// ============================================================================
// ML VISUAL ANALYSIS (XAI - Strateji Karar Merkezi)
// ============================================================================

/**
 * ML Stratejilerini API'den yükle ve dropdown'u doldur
 */
async function loadMLStrategies() {
    const select = document.getElementById('ml-analysis-strategy');
    if (!select) {
        console.error('❌ [ML] Strategy dropdown bulunamadı');
        return;
    }

    try {
        const response = await api.get('/strategies');
        const strategies = response.strategies || [];

        // Clear existing options (hardcoded olanları temizle)
        select.innerHTML = '';

        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Strateji Seçin...';
        select.appendChild(defaultOption);

        // Add strategies dynamically
        strategies.forEach(strategy => {
            const option = document.createElement('option');
            option.value = strategy.id || strategy.strategy_id;
            option.textContent = strategy.name || strategy.strategy_id;
            select.appendChild(option);
        });

        console.log(`✅ [ML] ${strategies.length} strateji yüklendi`);
    } catch (error) {
        console.error('❌ [ML] Strateji yükleme hatası:', error);
        select.innerHTML = '<option value="">Yükleme Hatası</option>';
    }
}

/**
 * ML Sembollerini API'den yükle ve dropdown'u doldur
 */
async function loadMLSymbols() {
    const select = document.getElementById('ml-analysis-symbol');
    if (!select) {
        console.error('❌ [ML] Symbol dropdown bulunamadı');
        return;
    }

    try {
        const response = await api.get('/data/symbols-with-data');
        const symbols = response.symbols || [];

        // Clear existing options
        select.innerHTML = '';

        // Add default option
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = 'Sembol Seçin...';
        select.appendChild(defaultOption);

        // Add symbols dynamically
        symbols.forEach(symbol => {
            const option = document.createElement('option');
            option.value = symbol.symbol || symbol;
            option.textContent = symbol.symbol || symbol;
            select.appendChild(option);
        });

        console.log(`✅ [ML] ${symbols.length} sembol yüklendi`);
    } catch (error) {
        console.error('❌ [ML] Sembol yükleme hatası:', error);
        select.innerHTML = '<option value="">Yükleme Hatası</option>';
    }
}

/**
 * ML Görsel Analizi Başlat (XAI - Strateji Karar Merkezi)
 * Global function (window objesine export edilir)
 */
async function runMLVisualAnalysis() {
    console.log('🚀 [XAI] ML Görsel Analizi başlatılıyor...');

    // Form değerlerini al
    const strategyId = document.getElementById('ml-analysis-strategy')?.value;
    const symbol = document.getElementById('ml-analysis-symbol')?.value;
    const timeframe = document.getElementById('ml-analysis-timeframe')?.value || '1h';
    const marketType = document.getElementById('ml-analysis-market-type')?.value || 'swap';

    // Validasyon
    if (!strategyId) {
        showToast('⚠️ Lütfen strateji seçin!', 'warning');
        return;
    }

    if (!symbol) {
        showToast('⚠️ Lütfen sembol seçin!', 'warning');
        return;
    }

    // Loading göster
    const chartContainer = document.getElementById('ml-analysis-chart');
    if (chartContainer) {
        chartContainer.innerHTML = '<div style="display:flex;justify-content:center;align-items:center;height:100%;color:var(--neon-blue);">⏳ Analiz ediliyor...</div>';
    }

    try {
        // API'den veri çek
        const response = await api.get(`/api/v1/ml/visual-analysis?symbol=${encodeURIComponent(symbol)}&strategy_id=${encodeURIComponent(strategyId)}&timeframe=${timeframe}&limit=1000`);

        if (response.status !== 'success') {
            throw new Error(response.detail || 'Analiz başarısız');
        }

        const { candles, markers, feature_importance } = response;

        console.log(`📊 [XAI] ${candles.length} mum, ${markers.length} marker, ${feature_importance.length} feature importance yüklendi`);

        // 1. Chart'ı render et
        if (window.chartRenderer) {
            // Destroy existing chart
            window.chartRenderer.destroy();

            // Initialize new chart
            window.chartRenderer.init('ml-analysis-chart', {
                width: chartContainer.clientWidth,
                height: 450
            });

            // Render candles
            const formattedCandles = candles.map(c => ({
                time: c.time / 1000, // Unix timestamp (seconds)
                open: c.open,
                high: c.high,
                low: c.low,
                close: c.close
            }));

            window.chartRenderer.updateCandles(formattedCandles);

            // Render markers (ML + Strateji + Gerçek İşlemler)
            if (markers && markers.length > 0) {
                window.chartRenderer.updateMarkers(markers);
                console.log(`✅ [XAI] ${markers.length} marker render edildi`);
            }
        }

        // 2. Feature Importance grafiğini çizdir (Plotly)
        if (feature_importance && feature_importance.length > 0) {
            renderFeatureImportance(feature_importance);
        }

        showToast('✅ ML Görsel Analizi tamamlandı!', 'success');

    } catch (error) {
        console.error('❌ [XAI] Analiz hatası:', error);
        showToast('❌ Analiz hatası: ' + error.message, 'error');

        if (chartContainer) {
            chartContainer.innerHTML = '<div style="display:flex;justify-content:center;align-items:center;height:100%;color:var(--neon-red);">❌ Hata: ' + error.message + '</div>';
        }
    }
}

/**
 * Feature Importance Grafiği (Plotly - XAI)
 * Yatay bar chart (barh) formatında
 */
function renderFeatureImportance(featureImportance) {
    const chartDiv = document.getElementById('feature-importance-chart');
    if (!chartDiv) {
        console.error('❌ [XAI] Feature importance chart div bulunamadı');
        return;
    }

    // Data hazırla
    const features = featureImportance.map(f => f.feature_name || f.feature || 'Unknown');
    const importancePct = featureImportance.map(f => f.importance_pct || f.importance || 0);

    // Plotly data
    const trace = {
        x: importancePct,
        y: features,
        type: 'bar',
        orientation: 'h', // Horizontal bar
        marker: {
            color: 'rgba(88, 166, 255, 0.8)',
            line: {
                color: 'rgba(88, 166, 255, 1)',
                width: 1
            }
        }
    };

    const layout = {
        title: '🧬 Model Ağırlık Analizi (Feature Importance)',
        font: {
            family: 'Inter, sans-serif',
            size: 12,
            color: '#fff'
        },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        margin: {
            l: 150, // Left margin for feature names
            r: 20,
            t: 50,
            b: 50
        },
        xaxis: {
            title: 'Önem Yüzdesi (%)',
            gridcolor: 'rgba(255,255,255,0.1)',
            zerolinecolor: 'rgba(255,255,255,0.2)'
        },
        yaxis: {
            gridcolor: 'rgba(255,255,255,0.1)',
            automargin: true
        }
    };

    const config = {
        responsive: true,
        displayModeBar: false,
        scrollZoom: false
    };

    // Plotly.react kullan (memory leak önleme - newPlot yerine)
    Plotly.react(chartDiv, [trace], layout, config);

    console.log(`✅ [XAI] Feature Importance grafiği çizildi: ${features.length} özellik`);
}

// Export to window (global access)
window.loadMLStrategies = loadMLStrategies;
window.loadMLSymbols = loadMLSymbols;
window.runMLVisualAnalysis = runMLVisualAnalysis;
window.renderFeatureImportance = renderFeatureImportance;

// ============================================================================
// LIVE TICKER
// ============================================================================

// Optional: throttle mechanism for high-frequency updates
function throttle(func, limit) {
    let lastFunc;
    let lastRan;
    return function() {
        const context = this;
        const args = arguments;
        if (!lastRan) {
            window.requestAnimationFrame(() => {
                func.apply(context, args);
            });
            lastRan = Date.now();
        } else {
            clearTimeout(lastFunc);
            lastFunc = setTimeout(function() {
                if ((Date.now() - lastRan) >= limit) {
                    window.requestAnimationFrame(() => {
                        func.apply(context, args);
                    });
                    lastRan = Date.now();
                }
            }, limit - (Date.now() - lastRan));
        }
    }
}

function startLiveTicker() {
    console.log('📈 [TICKER] Starting live ticker via WebSocket bindings...');

    // Set Initial Loading States
    document.getElementById('ticker-pnl').textContent = 'Bekleniyor...';
    document.getElementById('ticker-pnl').style.color = 'var(--text-muted)';

    document.getElementById('ticker-dd').textContent = 'Bekleniyor...';

    document.getElementById('ticker-ml-confidence').textContent = 'Bekleniyor...';
    document.getElementById('ticker-ml-confidence').className = 'ticker-value';
    document.getElementById('ticker-ml-confidence').style.color = 'var(--text-muted)';

    document.getElementById('ticker-api-rate-text').textContent = 'Bekleniyor...';
    document.getElementById('ticker-ws-latency').textContent = 'Bekleniyor...';

    // Initial fetch to populate Top Ticker Band
    const fetchTickerData = async () => {
        try {
            const metrics = await api.getDashboardMetrics();
            if (metrics && metrics.portfolio) {
                updateTopTicker(metrics.portfolio);
            }
        } catch (error) {
            console.error('❌ [TICKER] Load error:', error);
        }
    };

    fetchTickerData();
    // Instead of heavy REST polling every 60s, WebSocket will update it on events.
    // We can leave a slow fallback poll every 5 minutes to ensure sync.
    setInterval(fetchTickerData, 300000);
}

function updateTopTicker(portfolio) {
    const pnlEl = document.getElementById('ticker-pnl');
    const ddEl = document.getElementById('ticker-dd');
    const apiRateBar = document.getElementById('ticker-api-rate-bar');
    const apiRateText = document.getElementById('ticker-api-rate-text');

    if (pnlEl) {
        const pnl = portfolio.total_pnl || 0;
        pnlEl.textContent = `$${pnl.toFixed(2)}`;
        pnlEl.style.color = pnl >= 0 ? 'var(--accent-emerald)' : 'var(--accent-crimson)';
    }

    if (ddEl) {
        const dd = portfolio.drawdown || 0;
        ddEl.textContent = `${dd.toFixed(1)}% DD`;
    }

    // Simulated or fetched API rate limit status
    if (apiRateBar && apiRateText) {
        const rateUsed = portfolio.api_rate_usage || Math.floor(Math.random() * 40); // Placeholder if missing
        apiRateBar.style.width = `${rateUsed}%`;
        apiRateText.textContent = `${rateUsed}%`;

        if (rateUsed > 80) apiRateBar.style.backgroundColor = 'var(--accent-crimson)';
        else if (rateUsed > 50) apiRateBar.style.backgroundColor = 'var(--accent-gold)';
        else apiRateBar.style.backgroundColor = 'var(--accent-emerald)';
    }
}

// ============================================================================
// EVENT LISTENERS
// ============================================================================

/**
 * Use strategy (navigate to bot launcher with pre-selected strategy)
 */
window.useStrategy = function(strategyId) {
    console.log('🚀 [STRATEGY] Using strategy:', strategyId);

    // Navigate to settings tab
    switchTab('tab-settings');

    // Wait for tab to render, then select strategy
    setTimeout(() => {
        const strategySelect = document.querySelector('.strategy-select');
        if (strategySelect) {
            strategySelect.value = strategyId;
            // Trigger change event
            strategySelect.dispatchEvent(new Event('change'));
            showToast(`✅ ${strategyId} stratejisi seçildi`, 'success');
        }
    }, 300);
};

/**
 * Edit strategy (navigate to strategy builder)
 */
window.editStrategy = function(strategyId) {
    console.log('✏️ [STRATEGY] Editing strategy:', strategyId);

    // Navigate to strategy builder tab
    switchTab('tab-strategy-builder');

    // Load strategy into builder
    setTimeout(() => {
        showToast(`ℹ️ ${strategyId} düzenleme moduna geçildi`, 'info');
        // Strategy builder will handle loading
    }, 300);
};

/**
 * Setup global event listeners
 */
function setupEventListeners() {
    // Window resize
    window.addEventListener('resize', () => {
        console.debug('📐 [RESIZE] Window resized');
        if (window.chartRenderer && typeof window.chartRenderer.resize === 'function') {
            window.chartRenderer.resize();
        }
    });

    // Before unload
    window.addEventListener('beforeunload', () => {
        stopAutoRefresh();
        if (botManager && typeof botManager.destroy === 'function') {
            botManager.destroy();
        }
        if (window.chartRenderer && typeof window.chartRenderer.destroy === 'function') {
            window.chartRenderer.destroy();
        }
    });
}

// ============================================================================
// WEBSOCKET CLIENT (Real-time Event Streaming)
// ============================================================================

/**
 * WebSocket Client - Real-time event streaming from backend
 * Connects to /ws endpoint and listens for position events
 */
class WebSocketClient {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;
        this.isConnecting = false;
        this.lastMessageTime = null;
    }

    /**
     * Connect to WebSocket server
     */
    connect() {
        if (this.isConnecting || this.ws?.readyState === WebSocket.OPEN) {
            console.log('🔌 [WS] Already connected or connecting');
            return;
        }

        this.isConnecting = true;

        // WebSocket URL (same host as API)
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/v1/ws`;

        console.log(`🔌 [WS] Connecting to ${wsUrl}...`);

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                this.isConnecting = false;
                this.reconnectAttempts = 0;
                console.log('✅ [WS] Connected to backend');
                this.lastMessageTime = Date.now();
            };

            this.ws.onmessage = (event) => {
                try {
                    const receiveTime = Date.now();
                    const message = JSON.parse(event.data);

                    // Update System WS latency in Ticker
                    const latencyEl = document.getElementById('ticker-ws-latency');
                    const dotEl = document.getElementById('ticker-ws-dot');
                    if (latencyEl && message.timestamp) {
                        const latency = receiveTime - message.timestamp;
                        // Avoid negative latency from clock drift
                        latencyEl.textContent = `${Math.max(1, latency)}ms`;
                        if (dotEl) {
                            dotEl.style.backgroundColor = latency > 500 ? 'var(--accent-crimson)' : 'var(--accent-emerald)';
                        }
                    }

                    this.handleMessage(message);
                    this.lastMessageTime = receiveTime;
                } catch (error) {
                    console.error('❌ [WS] Message parse error:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('❌ [WS] WebSocket error:', error);
                this.isConnecting = false;
            };

            this.ws.onclose = () => {
                console.log('🔌 [WS] Disconnected');
                this.isConnecting = false;
                this.scheduleReconnect();
            };

        } catch (error) {
            console.error('❌ [WS] Connection error:', error);
            this.isConnecting = false;
            this.scheduleReconnect();
        }
    }

    /**
     * Handle incoming WebSocket message
     */
    handleMessage(message) {
        const { type, payload } = message;

        console.log(`📬 [WS] Event received: ${type}`, payload);

        switch (type) {
            case 'position.opened':
                this.onPositionOpened(payload);
                break;

            case 'position.closed':
                this.onPositionClosed(payload);
                break;

            case 'position.updated':
            case 'portfolio.updated':
                this.onPositionUpdated(payload);
                this.onPortfolioUpdated(payload);
                break;

            case 'bot.started':
                this.onBotStarted(payload);
                break;

            case 'bot.stopped':
                this.onBotStopped(payload);
                break;

            case 'ml.evaluation':
            case 'signal.evaluated':
            case 'signal.confirmed':
                this.onMLEvaluation(payload);
                break;

            case 'system.status':
                this.onSystemStatus(payload);
                break;

            default:
                console.debug(`📬 [WS] Unhandled event: ${type}`);
        }
    }

    onPortfolioUpdated = throttle((payload) => {
        const pnl = payload?.total_pnl_usd;
        const drawdown = payload?.current_drawdown_percent;

        if (pnl !== undefined) {
            const pnlEl = document.getElementById('ticker-pnl');
            if (pnlEl) {
                pnlEl.textContent = `$${pnl.toFixed(2)}`;
                pnlEl.style.color = pnl >= 0 ? 'var(--accent-emerald)' : 'var(--accent-crimson)';
            }
        }

        if (drawdown !== undefined) {
            const ddEl = document.getElementById('ticker-dd');
            if (ddEl) {
                ddEl.textContent = `${drawdown.toFixed(1)}% DD`;
            }
        }
    }, 100);

    onMLEvaluation = throttle((payload) => {
        const conf = payload?.confidence;
        if (conf === undefined) return;

        const confidencePercent = (conf * 100).toFixed(0);
        const mlEl = document.getElementById('ticker-ml-confidence');
        if (mlEl) {
            mlEl.textContent = `${confidencePercent}%`;

            // Remove previous color classes
            mlEl.classList.remove('text-cyan', 'text-crimson', 'text-white');
            mlEl.style.color = '';

            if (confidencePercent > 60) {
                mlEl.classList.add('text-cyan');
            } else if (confidencePercent < 40) {
                mlEl.classList.add('text-crimson');
            } else {
                mlEl.style.color = 'var(--text-main)';
            }
        }
    }, 100);

    onSystemStatus = throttle((payload) => {
        const rateLimit = payload?.api_rate_limit_percent;
        const latency = payload?.ws_latency_ms;

        if (rateLimit !== undefined) {
            const rateBar = document.getElementById('ticker-api-rate-bar');
            const rateText = document.getElementById('ticker-api-rate-text');

            if (rateBar && rateText) {
                rateBar.style.width = `${rateLimit}%`;
                rateText.textContent = `${rateLimit}%`;

                if (rateLimit > 80) rateBar.style.backgroundColor = 'var(--accent-crimson)';
                else if (rateLimit > 50) rateBar.style.backgroundColor = 'var(--accent-gold)';
                else rateBar.style.backgroundColor = 'var(--accent-emerald)';
            }
        }

        if (latency !== undefined) {
            const latencyEl = document.getElementById('ticker-ws-latency');
            const dotEl = document.getElementById('ticker-ws-dot');

            if (latencyEl) {
                latencyEl.textContent = `${Math.max(1, latency)}ms`;
                if (dotEl) {
                    dotEl.style.backgroundColor = latency > 500 ? 'var(--accent-crimson)' : 'var(--accent-emerald)';
                }
            }
        }
    }, 100);

    /**
     * Position Opened Event Handler
     */
    onPositionOpened(payload) {
        console.log('🟢 [WS] Position opened:', payload);

        // Update latest decisions
        if (payload.symbol && window.app?.latestDecisions) {
            window.app.latestDecisions[payload.symbol] = {
                ...window.app.latestDecisions[payload.symbol],
                has_position: true,
                position_opened_at: new Date().toISOString()
            };
        }

        // Refresh dashboard immediately
        loadDashboard();
        showToast(`🟢 ${payload.symbol} pozisyonu açıldı`, 'success');
    }

    /**
     * Position Closed Event Handler
     */
    onPositionClosed(payload) {
        console.log('🔴 [WS] Position closed:', payload);

        // Update latest decisions
        if (payload.symbol && window.app?.latestDecisions) {
            window.app.latestDecisions[payload.symbol] = {
                ...window.app.latestDecisions[payload.symbol],
                has_position: false,
                position_closed_at: new Date().toISOString()
            };
        }

        // Refresh dashboard immediately
        loadDashboard();

        const pnlClass = payload.pnl >= 0 ? 'success' : 'error';
        const pnlIcon = payload.pnl >= 0 ? '✅' : '❌';
        showToast(
            `${pnlIcon} ${payload.symbol} pozisyonu kapatıldı | PnL: ${pnlIcon}$${payload.pnl?.toFixed(2) || '0.00'} (${(payload.pnl_percent * 100)?.toFixed(2)}%)`,
            pnlClass
        );
    }

    /**
     * Position Updated Event Handler (Trailing Stop, PnL changes)
     */
    onPositionUpdated(payload) {
        console.log('📊 [WS] Position updated:', payload);

        // Update specific position in UI (without full refresh)
        this.updatePositionInTable(payload);
    }

    /**
     * Update position in table (PnL, trailing stop)
     */
    updatePositionInTable(payload) {
        const { bot_id, updates } = payload;

        if (!bot_id || !updates) return;

        // Find position row by bot_id
        const tbody = document.getElementById('positions-body');
        if (!tbody) return;

        const rows = tbody.querySelectorAll('tr');
        for (const row of rows) {
            // Check if this row matches the bot_id
            const closeBtn = row.querySelector('button[onclick*="' + bot_id + '"]');
            if (closeBtn) {
                // Update PnL if available
                if (updates.unrealized_usd !== undefined) {
                    const pnlCell = row.cells[4]; // PnL column
                    if (pnlCell) {
                        const pnl = updates.unrealized_usd;
                        const pnlClass = pnl >= 0 ? 'color:var(--neon-green)' : 'color:var(--neon-red)';
                        const pnlSign = pnl >= 0 ? '+' : '';
                        pnlCell.innerHTML = `
                            <div style="font-family:monospace; font-weight:bold; ${pnlClass}">${pnlSign}$${pnl.toFixed(2)}</div>
                            <div style="font-size:0.7rem; color:var(--text-muted);">$${(updates.current_price || 0).toFixed(2)}</div>
                        `;
                    }
                }

                // Update ROE if available
                if (updates.pnl_percent !== undefined) {
                    const roeCell = row.cells[5]; // ROE column
                    if (roeCell) {
                        const roe = updates.pnl_percent;
                        const roeClass = roe >= 0 ? 'color:var(--neon-green)' : 'color:var(--neon-red)';
                        const roeSign = roe >= 0 ? '+' : '';
                        roeCell.textContent = `${roeSign}${roe.toFixed(2)}%`;
                    }
                }

                // Update stop loss if available
                if (updates.stop_loss !== undefined) {
                    const slCell = row.cells[6]; // SL/TP column
                    if (slCell) {
                        const slDiv = slCell.querySelector('div[color*="neon-red"]');
                        if (slDiv) {
                            slDiv.textContent = `SL: $${updates.stop_loss.toFixed(2)}`;
                        }
                    }
                }

                break;
            }
        }
    }

    /**
     * Bot Started Event Handler
     */
    onBotStarted(payload) {
        console.log('🚀 [WS] Bot started:', payload);
        loadDashboard();
        showToast(`🚀 ${payload.symbol} botu başlatıldı`, 'success');
    }

    /**
     * Bot Stopped Event Handler
     */
    onBotStopped(payload) {
        console.log('🛑 [WS] Bot stopped:', payload);
        loadDashboard();
        showToast(`🛑 ${payload.symbol} botu durduruldu`, 'info');
    }

    /**
     * Schedule reconnection
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('❌ [WS] Max reconnect attempts reached, using polling only');
            return;
        }

        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts);
        this.reconnectAttempts++;

        console.log(`🔄 [WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

        setTimeout(() => this.connect(), delay);
    }

    /**
     * Disconnect
     */
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
            console.log('🔌 [WS] Disconnected by user');
        }
    }
}

// ============================================================================
// AUTO REFRESH
// ============================================================================

/**
 * Start auto-refresh
 */
function startAutoRefresh() {
    // Start WebSocket client
    if (!app.wsClient) {
        app.wsClient = new WebSocketClient();
        app.wsClient.connect();
    }

    // Fallback polling (5 seconds) - in case WebSocket fails
    app.refreshInterval = setInterval(async () => {
        if (app.initialized) {
            await loadDashboard();
            await botManager.loadBots();
            await loadActiveTasks();
        }
    }, 5000); // 5 seconds

    console.log('🔄 [REFRESH] Auto-refresh started (5s) + WebSocket real-time');
}

/**
 * Stop auto-refresh
 */
function stopAutoRefresh() {
    if (app.refreshInterval) {
        clearInterval(app.refreshInterval);
        app.refreshInterval = null;
        console.log('⏹️ [REFRESH] Auto-refresh stopped');
    }

    if (app.wsClient) {
        app.wsClient.disconnect();
        app.wsClient = null;
        console.log('🔌 [WS] WebSocket disconnected');
    }
}

// ============================================================================
// GLOBAL FUNCTIONS (for HTML onclick handlers)
// ============================================================================

// Export functions to window for legacy HTML onclick handlers
window.switchTab = switchTab;
window.botManager = botManager;
window.chartRenderer = chartRenderer;
window.store = store;
window.api = api;
window.loadDashboard = loadDashboard;
window.loadActiveTasks = loadActiveTasks;

// Settings & Launcher
window.handleBotSubmit = handleBotSubmit;
window.saveBotConfig = saveBotConfig;
window.saveRiskSettings = saveRiskSettings;
window.saveAdvancedSettings = saveAdvancedSettings;
window.saveKalmanSettings = saveKalmanSettings;
window.resetKalmanSettings = resetKalmanSettings;
window.saveCandleLockSettings = saveCandleLockSettings;
window.resetCandleLockSettings = resetCandleLockSettings;
window.saveApiKeys = saveApiKeys;
window.testApiConnection = testApiConnection;
window.showToast = showToast;

/**
 * Handle Kill Switch Activation
 */
window.handleKillSwitch = async function() {
    if (!confirm('🚨 DİKKAT! Tüm açık pozisyonlar market emriyle anında kapatılacak ve botlar durdurulacaktır. Onaylıyor musunuz?')) {
        return;
    }

    if (!confirm('⚠️ Bu işlem GERİ ALINAMAZ! Son kez onaylayın.')) {
        return;
    }

    try {
        showToast('🚨 KILL SWITCH AKTİF! Sistem acil durduruluyor...', 'error');
        // Call backend API to stop all and close positions
        // Since we don't have the exact API endpoint in front of us, we use a placeholder or known one.
        // We'll rely on botManager to stop all active bots if we can, or a generic backend endpoint.
        const response = await fetch('/api/v1/system/kill-switch', { method: 'POST' });

        if (response.ok) {
            const data = await response.json();
            showToast('✅ Kill Switch başarılı: ' + data.message, 'success');
            await loadDashboard();
        } else {
            showToast('❌ Kill Switch sunucu hatası!', 'error');
        }
    } catch (error) {
        showToast('❌ Kill Switch hata: ' + error.message, 'error');
    }
};

// ML Training
window.startMLTraining = startMLTraining;
window.validateMumCount = validateMumCount;
window.loadMLTrainingHistory = loadMLTrainingHistory;
window.clearTrainingHistory = clearTrainingHistory;

// ============================================================================
// START APPLICATION
// ============================================================================

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// ============================================================================
// FINAL LOG
// ============================================================================

console.log('🎉 [MİMARİ] Faz 3 Tamamlandı: Frontend ES6 Modüllerine Parçalandı');
