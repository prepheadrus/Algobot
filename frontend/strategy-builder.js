/**
 * Strategy Builder - Frontend JavaScript Motoru
 * 
 * No-Code Strateji Oluşturucu için API entegrasyonu.
 * Backend: api/routers/strategy_builder.py
 */

// ============================================================================
// GLOBAL DEĞİŞKENLER
// ============================================================================

let selectedIndicators = [];
let longConditions = [];
let shortConditions = [];
let longLogic = 'AND';
let shortLogic = 'AND';

// ============================================================================
// SAYFA YÜKLENDİĞİNDE
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('[Strategy Builder] Sayfa yüklendi');
    
    // İndikatör butonlarını dinle
    setupIndicatorButtons();
    
    // Kaydedilmiş stratejileri yükle
    loadStrategies();
    
    // Varsayılan koşulları ekle
    addCondition('long');
    addCondition('short');
});

// ============================================================================
// İNDİKATÖR SEÇİMİ
// ============================================================================

function setupIndicatorButtons() {
    const buttons = document.querySelectorAll('.indicator-btn');
    
    buttons.forEach(btn => {
        btn.addEventListener('click', function() {
            const type = this.dataset.type;
            const params = JSON.parse(this.dataset.params);
            
            // Toggle selection
            this.classList.toggle('selected');
            
            if (this.classList.contains('selected')) {
                // İndikatörü listeye ekle
                selectedIndicators.push({
                    name: type,
                    ...params
                });
                console.log(`[OK] İndikatör eklendi: ${type}`, params);
            } else {
                // İndikatörü listeden çıkar
                selectedIndicators = selectedIndicators.filter(ind => ind.name !== type);
                console.log(`[OK] İndikatör çıkarıldı: ${type}`);
            }
        });
    });
}

// ============================================================================
// KOŞUL OLUŞTURUCU
// ============================================================================

function addCondition(type, conditionData = null) {
    const container = document.getElementById(`${type}-conditions-container`);
    const conditionId = `${type}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    // Koşul objesi oluştur
    const condition = {
        id: conditionId,
        indicator: conditionData?.indicator || '',
        operator: conditionData?.operator || '<',
        value: conditionData?.value || ''
    };

    // Array'e ekle
    if (type === 'long') {
        longConditions.push(condition);
    } else {
        shortConditions.push(condition);
    }

    // HTML oluştur
    const conditionHTML = createConditionHTML(condition, type);
    container.insertAdjacentHTML('beforeend', conditionHTML);

    // Satırı bul ve değerleri doldur (eğer conditionData varsa)
    if (conditionData) {
        setTimeout(() => {
            const row = document.getElementById(conditionId);
            if (row) {
                const indicatorSelect = row.querySelector('.condition-indicator');
                const operatorSelect = row.querySelector('.condition-operator');
                const valueInput = row.querySelector('.condition-value');

                if (indicatorSelect) indicatorSelect.value = conditionData.indicator || '';
                if (operatorSelect) operatorSelect.value = conditionData.operator || '<';
                if (valueInput) valueInput.value = conditionData.value || '';
            }
        }, 0);
    }

    // Event listener'ları ekle
    setupConditionListeners(conditionId, type);

    console.log(`[OK] ${type.toUpperCase()} koşulu eklendi:`, conditionId, conditionData || '');
}

function createConditionHTML(condition, type) {
    return `
        <div class="condition-row" id="${condition.id}">
            <select class="form-select condition-indicator">
                <option value="">İndikatör Seç...</option>
                <option value="RSI_14">RSI (14)</option>
                <option value="MACD_12_26_9">MACD (12, 26, 9)</option>
                <option value="MACD_Signal_12_26_9">MACD Signal</option>
                <option value="EMA_20">EMA (20)</option>
                <option value="SMA_20">SMA (20)</option>
                <option value="ATR_14">ATR (14)</option>
                <option value="STOCH_K_14_3">Stochastic %K</option>
                <option value="STOCH_D_14_3">Stochastic %D</option>
                <option value="BBU_20_2.0">Bollinger Upper</option>
                <option value="BBL_20_2.0">Bollinger Lower</option>
            </select>
            
            <select class="form-select condition-operator">
                <option value="&lt;">&lt;</option>
                <option value="&gt;">&gt;</option>
                <option value="&lt;=">&lt;=</option>
                <option value="&gt;=">&gt;=</option>
                <option value="==">=</option>
                <option value="!=">!=</option>
            </select>
            
            <input type="text" class="form-input condition-value" placeholder="Değer (örn: 30)">
            
            <button class="btn-remove" onclick="removeCondition('${condition.id}', '${type}')">✕</button>
        </div>
    `;
}

function setupConditionListeners(conditionId, type) {
    const row = document.getElementById(conditionId);
    if (!row) return;
    
    const indicatorSelect = row.querySelector('.condition-indicator');
    const operatorSelect = row.querySelector('.condition-operator');
    const valueInput = row.querySelector('.condition-value');
    
    // Değişiklikleri dinle ve array'i güncelle
    indicatorSelect.addEventListener('change', function() {
        const conditions = type === 'long' ? longConditions : shortConditions;
        const condition = conditions.find(c => c.id === conditionId);
        if (condition) {
            condition.indicator = this.value;
        }
    });
    
    operatorSelect.addEventListener('change', function() {
        const conditions = type === 'long' ? longConditions : shortConditions;
        const condition = conditions.find(c => c.id === conditionId);
        if (condition) {
            condition.operator = this.value;
        }
    });
    
    valueInput.addEventListener('input', function() {
        const conditions = type === 'long' ? longConditions : shortConditions;
        const condition = conditions.find(c => c.id === conditionId);
        if (condition) {
            condition.value = this.value;
        }
    });
}

function removeCondition(conditionId, type) {
    const row = document.getElementById(conditionId);
    if (row) {
        row.remove();
    }
    
    const conditions = type === 'long' ? longConditions : shortConditions;
    const index = conditions.findIndex(c => c.id === conditionId);
    if (index !== -1) {
        conditions.splice(index, 1);
    }
    
    console.log(`[OK] ${type.toUpperCase()} koşulu çıkarıldı:`, conditionId);
}

// ============================================================================
// LOGIC SEÇİMİ (AND/OR)
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // LONG logic selector
    const longLogicButtons = document.querySelectorAll('#long-logic-selector .logic-btn');
    longLogicButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            longLogicButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            longLogic = this.dataset.logic;
            console.log('[OK] LONG logic:', longLogic);
        });
    });
    
    // SHORT logic selector
    const shortLogicButtons = document.querySelectorAll('#short-logic-selector .logic-btn');
    shortLogicButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            shortLogicButtons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            shortLogic = this.dataset.logic;
            console.log('[OK] SHORT logic:', shortLogic);
        });
    });
});

// ============================================================================
// JSON OLUŞTURMA
// ============================================================================

function buildStrategyJSON() {
    // Strateji bilgilerini topla
    const name = document.getElementById('strategy-name').value.trim();
    const description = document.getElementById('strategy-description').value.trim();
    
    // Risk parametreleri
    const stopLossATR = parseFloat(document.getElementById('stop-loss-atr').value) || 2.0;
    const takeProfitATR = parseFloat(document.getElementById('take-profit-atr').value) || 4.0;
    const maxRiskPercent = parseFloat(document.getElementById('max-risk-percent').value) || 2.0;
    
    // LONG koşullarını oluştur
    const longConditionsData = longConditions.map(c => ({
        indicator: c.indicator,
        operator: c.operator,
        value: isNaN(parseFloat(c.value)) ? c.value : parseFloat(c.value)
    })).filter(c => c.indicator && c.value);
    
    // SHORT koşullarını oluştur
    const shortConditionsData = shortConditions.map(c => ({
        indicator: c.indicator,
        operator: c.operator,
        value: isNaN(parseFloat(c.value)) ? c.value : parseFloat(c.value)
    })).filter(c => c.indicator && c.value);
    
    // JSON objesi oluştur
    const strategyJSON = {
        name: name || 'Yeni Strateji',
        description: description || '',
        indicators: selectedIndicators,
        conditions: {
            LONG: {
                logic: longLogic,
                conditions: longConditionsData
            },
            SHORT: {
                logic: shortLogic,
                conditions: shortConditionsData
            }
        },
        risk: {
            stop_loss_atr_multiplier: stopLossATR,
            take_profit_atr_multiplier: takeProfitATR,
            max_risk_percent: maxRiskPercent
        }
    };
    
    console.log('[OK] Strategy JSON oluşturuldu:', strategyJSON);
    return strategyJSON;
}

// ============================================================================
// API ÇAĞRILARI
// ============================================================================

/**
 * Stratejiyi kaydet
 */
async function saveStrategy() {
    try {
        console.log('[INFO] Strateji kaydediliyor...');
        
        // JSON oluştur
        const strategyData = buildStrategyJSON();
        
        // Validasyon
        if (strategyData.conditions.LONG.conditions.length === 0 && 
            strategyData.conditions.SHORT.conditions.length === 0) {
            alert('⚠️ En az bir LONG veya SHORT koşulu eklemelisiniz!');
            return;
        }
        
        // API çağrısı
        const response = await fetch('/api/v1/strategy/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(strategyData)
        });
        
        const result = await response.json();
        
        if (response.ok && result.status === 'success') {
            console.log('[OK] Strateji kaydedildi:', result.filename);
            alert(`✅ ${result.message}`);
            
            // Formu temizle
            clearForm();
            
            // Strateji listesini yenile
            loadStrategies();
        } else {
            console.error('[HATA] Strateji kaydedilemedi:', result);
            alert(`❌ Hata: ${result.detail || 'Bilinmeyen hata'}`);
        }
        
    } catch (error) {
        console.error('[HATA] Strateji kaydetme hatası:', error);
        alert(`❌ Bağlantı hatası: ${error.message}`);
    }
}

/**
 * Kaydedilmiş stratejileri yükle
 */
async function loadStrategies() {
    try {
        console.log('[INFO] Stratejiler yükleniyor...');

        const response = await fetch('/api/v1/strategy/list');
        const result = await response.json();

        if (response.ok && result.status === 'success') {
            const container = document.getElementById('saved-strategies-list');

            if (!result.strategies || result.strategies.length === 0) {
                container.innerHTML = `
                    <div style="text-align: center; padding: 20px; color: var(--text-muted);">
                        📭 Henüz kaydedilmiş strateji yok
                    </div>
                `;
                return;
            }
            
            // Strateji listesini oluştur
            let html = '';
            result.strategies.forEach(strategy => {
                html += `
                    <div class="strategy-item" onclick="loadStrategy('${strategy.filename}')">
                        <div class="strategy-item-header">
                            <span class="strategy-item-name">${strategy.name}</span>
                            <span class="strategy-item-meta">${strategy.indicators_count} indikatör</span>
                        </div>
                        <div class="strategy-item-meta">${strategy.created_at}</div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
            console.log(`[OK] ${result.count} strateji yüklendi`);
        } else {
            console.error('[HATA] Stratejiler yüklenemedi:', result);
        }
        
    } catch (error) {
        console.error('[HATA] Strateji yükleme hatası:', error);
    }
}

/**
 * Strateji yükle
 */
async function loadStrategy(filename) {
    try {
        console.log('[INFO] Strateji yükleniyor:', filename);

        const response = await fetch(`/api/v1/strategy/info/${filename}`);
        const result = await response.json();

        if (response.ok && result.status === 'success') {
            const data = result.data;

            // 1. Önce formu tamamen temizle
            clearForm();

            // 2. Strateji bilgilerini doldur
            document.getElementById('strategy-name').value = data.name || '';
            document.getElementById('strategy-description').value = data.description || '';

            // 3. Risk parametrelerini doldur
            if (data.risk) {
                document.getElementById('stop-loss-atr').value = data.risk.stop_loss_atr_multiplier || 2.0;
                document.getElementById('take-profit-atr').value = data.risk.take_profit_atr_multiplier || 4.0;
                document.getElementById('max-risk-percent').value = data.risk.max_risk_percent || 2.0;
            }

            // 4. İndikatörleri işaretle ve seçili olarak ekle
            if (data.indicators && data.indicators.length > 0) {
                data.indicators.forEach(ind => {
                    // İndikatör butonunu bul ve işaretle
                    const buttons = document.querySelectorAll('.indicator-btn');
                    buttons.forEach(btn => {
                        if (btn.dataset.type === ind.name) {
                            btn.classList.add('selected');
                        }
                    });
                    // Seçili indikatörler listesine ekle
                    selectedIndicators.push({
                        name: ind.name,
                        ...ind
                    });
                });
            }

            // 5. LONG koşullarını yükle
            if (data.conditions && data.conditions.LONG) {
                // Logic operatörünü ayarla
                if (data.conditions.LONG.logic === 'OR') {
                    longLogic = 'OR';
                    document.querySelectorAll('#long-logic-selector .logic-btn').forEach(btn => {
                        btn.classList.remove('active');
                        if (btn.dataset.logic === 'OR') btn.classList.add('active');
                    });
                }

                // Her LONG koşulunu ekle (conditionData ile) - BOŞ ARRAY KONTROLÜ
                if (data.conditions.LONG.conditions &&
                    Array.isArray(data.conditions.LONG.conditions) &&
                    data.conditions.LONG.conditions.length > 0) {

                    // Container'ı temizle
                    const longContainer = document.getElementById('long-conditions-container');
                    if (longContainer) longContainer.innerHTML = '';
                    longConditions = [];

                    // Tüm koşulları ekle
                    data.conditions.LONG.conditions.forEach((cond) => {
                        addCondition('long', {
                            indicator: cond.indicator || '',
                            operator: cond.operator || '<',
                            value: cond.value !== undefined ? cond.value : ''
                        });
                    });
                }
            }

            // 6. SHORT koşullarını yükle
            if (data.conditions && data.conditions.SHORT) {
                // Logic operatörünü ayarla
                if (data.conditions.SHORT.logic === 'OR') {
                    shortLogic = 'OR';
                    document.querySelectorAll('#short-logic-selector .logic-btn').forEach(btn => {
                        btn.classList.remove('active');
                        if (btn.dataset.logic === 'OR') btn.classList.add('active');
                    });
                }

                // Her SHORT koşulunu ekle (conditionData ile) - BOŞ ARRAY KONTROLÜ
                if (data.conditions.SHORT.conditions &&
                    Array.isArray(data.conditions.SHORT.conditions) &&
                    data.conditions.SHORT.conditions.length > 0) {

                    // Container'ı temizle
                    const shortContainer = document.getElementById('short-conditions-container');
                    if (shortContainer) shortContainer.innerHTML = '';
                    shortConditions = [];

                    // Tüm koşulları ekle
                    data.conditions.SHORT.conditions.forEach((cond) => {
                        addCondition('short', {
                            indicator: cond.indicator || '',
                            operator: cond.operator || '<',
                            value: cond.value !== undefined ? cond.value : ''
                        });
                    });
                }
            }

            console.log('[OK] Strateji yüklendi:', filename);
            alert(`✅ Strateji '${data.name}' yüklendi`);
        } else {
            console.error('[HATA] Strateji yüklenemedi:', result);
            alert(`❌ Hata: ${result.detail || 'Bilinmeyen hata'}`);
        }

    } catch (error) {
        console.error('[HATA] Strateji yükleme hatası:', error);
        alert(`❌ Bağlantı hatası: ${error.message}`);
    }
}

/**
 * Stratejiyi test et (Backtest)
 */
async function testStrategy() {
    try {
        console.log('[INFO] Backtest çalıştırılıyor...');

        // GUARD CLAUSE: En az 1 koşul var mı kontrol et
        const totalConditions = longConditions.filter(c => c.indicator && c.value).length +
                               shortConditions.filter(c => c.indicator && c.value).length;

        if (totalConditions === 0) {
            alert('⚠️ Lütfen test etmeden önce en az bir LONG veya SHORT koşulu ekleyin veya strateji yükleyin!');
            return;
        }

        // UI güncelle (loading state)
        const testBtn = document.querySelector('button[onclick="testStrategy()"]');
        const originalText = testBtn.innerHTML;
        testBtn.innerHTML = '⏳ Test ediliyor...';
        testBtn.disabled = true;

        // Form verilerini al
        const symbol = document.getElementById('backtest-symbol').value || 'BTC/USDT';
        const timeframe = document.getElementById('backtest-timeframe').value || '1h';
        const days = parseInt(document.getElementById('backtest-days').value) || 30;
        const initialBalance = parseFloat(document.getElementById('backtest-balance').value) || 10000;

        // Strateji JSON oluştur
        const strategyData = buildStrategyJSON();

        // API çağrısı
        const response = await fetch('/api/v1/backtest/run', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                strategy: strategyData,
                symbol: symbol,
                timeframe: timeframe,
                days: days,
                initial_balance: initialBalance,
                risk_per_trade: 0.01
            })
        });

        const result = await response.json();

        if (response.ok && result.status === 'success') {
            console.log('[OK] Backtest tamamlandı:', result.metrics);

            // Test sonuçlarını göster
            displayBacktestResults(result);

            testBtn.innerHTML = '✅ Test Tamamlandı';
            testBtn.style.background = 'var(--neon-green)';
        } else {
            console.error('[HATA] Backtest başarısız:', result);
            alert(`❌ Hata: ${result.detail || 'Bilinmeyen hata'}`);
            testBtn.innerHTML = originalText;
            testBtn.disabled = false;
        }

    } catch (error) {
        console.error('[HATA] Backtest hatası:', error);
        alert(`❌ Bağlantı hatası: ${error.message}`);

        const testBtn = document.querySelector('button[onclick="testStrategy()"]');
        testBtn.innerHTML = '🧪 Test Et';
        testBtn.disabled = false;
    }
}

/**
 * Backtest sonuçlarını göster
 */
function displayBacktestResults(result) {
    const metrics = result.metrics;
    const equityCurve = result.equity_curve;
    const recentTrades = result.recent_trades;

    // Test sonuçları div'ini göster
    const resultsDiv = document.getElementById('test-results');
    resultsDiv.style.display = 'block';

    // 1. Metrik kartlarını güncelle
    document.getElementById('metric-winrate').textContent = `${metrics.win_rate.toFixed(1)}%`;
    document.getElementById('metric-pnl').textContent = `$${metrics.net_pnl.toFixed(2)}`;
    document.getElementById('metric-profit-factor').textContent = metrics.profit_factor.toFixed(2);
    document.getElementById('metric-drawdown').textContent = `${metrics.max_drawdown.toFixed(2)}%`;

    // PnL rengini ayarla
    const pnlEl = document.getElementById('metric-pnl');
    if (metrics.net_pnl > 0) {
        pnlEl.style.color = 'var(--neon-green)';
    } else if (metrics.net_pnl < 0) {
        pnlEl.style.color = 'var(--neon-red)';
    } else {
        pnlEl.style.color = 'var(--neon-blue)';
    }

    // 2. Equity curve grafiğini çiz
    drawEquityCurve(equityCurve);

    // 3. İşlem geçmişini tabloya ekle
    displayTradesTable(recentTrades);
}

/**
 * Equity curve grafiğini çiz (Simple Line Chart)
 */
function drawEquityCurve(equityCurve) {
    const container = document.getElementById('equity-curve-chart');

    if (!equityCurve || equityCurve.length === 0) {
        container.innerHTML = `
            <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); color: var(--text-muted); font-size: 0.85rem;">
                Veri yok
            </div>
        `;
        return;
    }

    // Basit SVG line chart oluştur
    const width = container.offsetWidth;
    const height = container.offsetHeight;
    const padding = 20;

    // Veri analizi
    const equities = equityCurve.map(p => p.equity);
    const minEquity = Math.min(...equities);
    const maxEquity = Math.max(...equities);
    const equityRange = maxEquity - minEquity || 1;

    // SVG path oluştur
    let pathD = '';
    equityCurve.forEach((point, i) => {
        const x = padding + (i / (equityCurve.length - 1)) * (width - 2 * padding);
        const y = height - padding - ((point.equity - minEquity) / equityRange) * (height - 2 * padding);

        if (i === 0) {
            pathD += `M ${x} ${y}`;
        } else {
            pathD += ` L ${x} ${y}`;
        }
    });

    // Gradient color (yeşil -> kırmızı)
    const startColor = equities[0] >= equities[equities.length - 1] ? '#f85149' : '#2ea043';
    const endColor = equities[0] >= equities[equities.length - 1] ? '#2ea043' : '#f85149';

    // SVG HTML
    container.innerHTML = `
        <svg width="${width}" height="${height}" style="overflow: visible;">
            <!-- Grid lines -->
            <line x1="${padding}" y1="${height/2}" x2="${width-padding}" y2="${height/2}"
                  stroke="rgba(255,255,255,0.1)" stroke-dasharray="4"/>

            <!-- Equity line -->
            <path d="${pathD}" fill="none" stroke="url(#gradient)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>

            <!-- Gradient definition -->
            <defs>
                <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" style="stop-color:${startColor};stop-opacity:1" />
                    <stop offset="100%" style="stop-color:${endColor};stop-opacity:1" />
                </linearGradient>
            </defs>

            <!-- Start point -->
            <circle cx="${padding}" cy="${height - padding - ((equities[0] - minEquity) / equityRange) * (height - 2 * padding)}"
                    r="4" fill="${startColor}"/>

            <!-- End point -->
            <circle cx="${width-padding}" cy="${height - padding - ((equities[equities.length-1] - minEquity) / equityRange) * (height - 2 * padding)}"
                    r="4" fill="${endColor}"/>
        </svg>

        <!-- Labels -->
        <div style="position: absolute; top: ${padding/2}px; left: ${padding}px; font-size: 0.7rem; color: var(--text-muted);">
            $${maxEquity.toFixed(0)}
        </div>
        <div style="position: absolute; bottom: ${padding/2}px; left: ${padding}px; font-size: 0.7rem; color: var(--text-muted);">
            $${minEquity.toFixed(0)}
        </div>
    `;
}

/**
 * İşlem geçmişini tabloya ekle
 */
function displayTradesTable(trades) {
    const tbody = document.getElementById('trades-table-body');

    if (!trades || trades.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="padding: 20px; text-align: center; color: var(--text-muted);">
                    Henüz işlem yok
                </td>
            </tr>
        `;
        return;
    }

    let html = '';
    trades.forEach(trade => {
        // Entry/Exit zamanlarını formatla
        const entryTime = new Date(trade.entry_time).toLocaleString('tr-TR', {
            month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
        });
        const exitTime = new Date(trade.exit_time).toLocaleString('tr-TR', {
            month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
        });

        // PnL rengi
        const pnlColor = trade.pnl >= 0 ? 'var(--neon-green)' : 'var(--neon-red)';

        // Direction badge
        const directionBadge = trade.direction === 'LONG'
            ? '<span style="background: rgba(46,160,67,0.2); color: var(--neon-green); padding: 2px 6px; border-radius: 4px; font-size: 0.7rem;">LONG</span>'
            : '<span style="background: rgba(248,81,73,0.2); color: var(--neon-red); padding: 2px 6px; border-radius: 4px; font-size: 0.7rem;">SHORT</span>';

        // Exit reason badge
        let reasonBadge = '';
        if (trade.exit_reason === 'TARGET') {
            reasonBadge = '<span style="background: rgba(46,160,67,0.2); color: var(--neon-green); padding: 2px 6px; border-radius: 4px; font-size: 0.7rem;">🎯 TARGET</span>';
        } else if (trade.exit_reason === 'STOP') {
            reasonBadge = '<span style="background: rgba(248,81,73,0.2); color: var(--neon-red); padding: 2px 6px; border-radius: 4px; font-size: 0.7rem;">🛑 STOP</span>';
        } else {
            reasonBadge = '<span style="background: rgba(255,255,255,0.1); color: var(--text-muted); padding: 2px 6px; border-radius: 4px; font-size: 0.7rem;">SIGNAL</span>';
        }

        html += `
            <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                <td style="padding: 8px;">
                    <div style="margin-bottom: 4px;">${directionBadge}</div>
                    <div style="font-size: 0.7rem; color: var(--text-muted);">${entryTime}</div>
                    <div style="font-size: 0.7rem;">$${trade.entry_price.toFixed(2)}</div>
                </td>
                <td style="padding: 8px;">
                    <div style="font-size: 0.7rem; color: var(--text-muted);">${exitTime}</div>
                    <div style="font-size: 0.7rem;">$${trade.exit_price.toFixed(2)}</div>
                </td>
                <td style="padding: 8px; text-align: right;">
                    <div style="font-size: 0.85rem; font-weight: 700; color: ${pnlColor};">
                        ${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)}
                    </div>
                    <div style="font-size: 0.7rem; color: ${pnlColor};">
                        ${trade.pnl_percent >= 0 ? '+' : ''}${trade.pnl_percent.toFixed(2)}%
                    </div>
                </td>
                <td style="padding: 8px; text-align: center;">
                    ${reasonBadge}
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

/**
 * Formu temizle
 */
function clearForm() {
    console.log('[INFO] Form temizleniyor...');

    // 1. Strateji bilgilerini sıfırla
    document.getElementById('strategy-name').value = 'Yeni Strateji';
    document.getElementById('strategy-description').value = '';

    // 2. Risk parametrelerini varsayılana döndür
    document.getElementById('stop-loss-atr').value = 2.0;
    document.getElementById('take-profit-atr').value = 4.0;
    document.getElementById('max-risk-percent').value = 2.0;

    // 3. İndikatörleri temizle (seçili butonları kaldır)
    selectedIndicators = [];
    document.querySelectorAll('.indicator-btn').forEach(btn => {
        btn.classList.remove('selected');
    });

    // 4. LONG koşullarını tamamen temizle
    longConditions = [];
    const longContainer = document.getElementById('long-conditions-container');
    if (longContainer) {
        longContainer.innerHTML = '';
    }

    // 5. SHORT koşullarını tamamen temizle
    shortConditions = [];
    const shortContainer = document.getElementById('short-conditions-container');
    if (shortContainer) {
        shortContainer.innerHTML = '';
    }

    // 6. Varsayılan koşulları ekle (1'er tane)
    addCondition('long');
    addCondition('short');

    // 7. Logic selector'ları sıfırla
    longLogic = 'AND';
    shortLogic = 'AND';
    document.querySelectorAll('#long-logic-selector .logic-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.logic === 'AND') btn.classList.add('active');
    });
    document.querySelectorAll('#short-logic-selector .logic-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.logic === 'AND') btn.classList.add('active');
    });

    // 8. Test sonuçlarını gizle
    document.getElementById('test-results').style.display = 'none';

    console.log('[OK] Form temizlendi');
}

// ============================================================================
// YARDIMCI FONKSİYONLAR
// ============================================================================

// İndikatör arama
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('indicator-search');
    
    searchInput.addEventListener('input', function() {
        const searchTerm = this.value.toLowerCase();
        const buttons = document.querySelectorAll('.indicator-btn');
        
        buttons.forEach(btn => {
            const text = btn.textContent.toLowerCase();
            if (text.includes(searchTerm)) {
                btn.style.display = 'block';
            } else {
                btn.style.display = 'none';
            }
        });
    });
});
