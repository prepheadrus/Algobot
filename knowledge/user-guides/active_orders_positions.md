# ⚡ Aktif Emirler ve Pozisyonlar Sekmesi (Active Orders & Positions)

**Versiyon:** v4.0 (Production-Ready)
**Son Güncelleme:** Mart 2026
**Dosya:** `frontend/index.html` (tab-orders)

---

## 📋 Genel Bakış

**Aktif Emirler** sekmesi (doğru adıyla **Aktif Stratejiler ve Açık Pozisyonlar**), sistemin canlı performansını, açık pozisyonları ve strateji durumlarını gerçek zamanlı gösteren ana kontrol panelidir.

---

## 📁 Konum

```
Sol Menü → ⚡ Aktif Emirler
```

**Tab ID:** `tab-orders`

---

## 🏗️ Arayüz Düzeni

```
┌─────────────────────────────────────────────────────────┐
│  1. AKTİF STRATEJİLER (Sistem Durum Özeti)             │
│     - Her bot için durum kartları                       │
│     - Strateji adı, sembol, PnL                         │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  2. PAPER TRADING - CANLI PERFORMANS (KPI Dashboard)   │
│     - Bakiye, Equity, Win Rate                          │
│     - İşlem Sayısı, Toplam P&L, Komisyon                │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  3. AÇIK POZİSYONLAR TABLOSU                            │
│     - Strateji / TF                                     │
│     - Yön / Parite                                      │
│     - Miktar / Kaldıraç                                 │
│     - Giriş / Pozisyon Değeri                           │
│     - Mevcut / P&L ($)                                  │
│     - ROE (%)                                           │
│     - SL / TP / Liq                                     │
│     - İşlem (Kapat butonu)                              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  4. SERMAYE KULLANIMI                                   │
│     - Kullanılan Marjin                                 │
│     - Kullanılabilir Bakiye                             │
│     - Toplam Pozisyon Değeri                            │
│     - Ortalama Kaldıraç                                 │
└─────────────────────────────────────────────────────────┘
```

---

## 🧩 Bileşenler

### **1. Aktif Stratejiler (Sistem Durum Özeti)**

**ID:** `#system-status-summary`

**Tip:** Grid Layout (Responsive)

**Her Kart:**
```html
<div class="strategy-card">
    <div class="strategy-name">trend_master</div>
    <div class="strategy-symbol">BTC/USDT:USDT</div>
    <div class="strategy-pnl">+$125.50 (+1.25%)</div>
    <div class="strategy-status">🟢 Çalışıyor</div>
</div>
```

**Dinamik Yükleme:**
```javascript
// frontend/app.js
async function loadSystemStatus() {
    const container = document.getElementById('system-status-summary');
    
    const bots = await api.get('/api/v1/bot/list');
    
    container.innerHTML = bots.bots.map(bot => `
        <div class="strategy-card">
            <div class="strategy-name">${bot.strategy_id}</div>
            <div class="strategy-symbol">${bot.symbol}</div>
            <div class="strategy-pnl ${bot.pnl >= 0 ? 'success' : 'danger'}">
                ${bot.pnl >= 0 ? '+' : ''}$${bot.pnl.toFixed(2)} 
                (${bot.pnl_percent.toFixed(2)}%)
            </div>
            <div class="strategy-status">
                ${bot.status === 'running' ? '🟢 Çalışıyor' : '⏸️ Durmuş'}
            </div>
        </div>
    `).join('');
}
```

---

### **2. Paper Trading - Canlı Performans (KPI Dashboard)**

**Container:** `.kpi-dashboard`

#### **KPI Kartları:**

| KPI | ID | Format | Açıklama |
|-----|----|--------|----------|
| **💰 Bakiye** | `#perf-balance` | `$10,000.00` | Toplam hesap bakiyesi |
| **📈 Equity** | `#perf-equity` | `$10,120.00` | Bakiye + Unrealized PnL |
| **🎯 Win Rate** | `#perf-winrate` | `62.5%` | Kazanan işlem oranı |
| **📊 İşlem** | `#perf-count` | `12 / 45` | Açık / Toplam işlem |
| **💵 P&L** | `#perf-total-pnl` | `+$250.00` | Toplam kar/zarar |
| **💸 Komisyon** | `#perf-total-fees` | `$12.50` | Toplam komisyon |

**Güncelleme:**
```javascript
// frontend/app.js
async function updatePerformanceMetrics() {
    const metrics = await api.get('/api/v1/dashboard-metrics');
    
    document.getElementById('perf-balance').textContent = 
        `$${metrics.portfolio.balance.toFixed(2)}`;
    
    document.getElementById('perf-equity').textContent = 
        `$${metrics.portfolio.equity.toFixed(2)}`;
    
    document.getElementById('perf-winrate').textContent = 
        `${(metrics.portfolio.win_rate * 100).toFixed(1)}%`;
    
    document.getElementById('perf-count').textContent = 
        `${metrics.positions.length} / ${metrics.portfolio.total_trades}`;
    
    document.getElementById('perf-total-pnl').textContent = 
        `${metrics.portfolio.total_pnl >= 0 ? '+' : ''}$${metrics.portfolio.total_pnl.toFixed(2)}`;
    
    document.getElementById('perf-total-fees').textContent = 
        `$${metrics.portfolio.total_commission.toFixed(2)}`;
}
```

---

### **3. Açık Pozisyonlar Tablosu**

**ID:** `#positions-body`

**Tablo Yapısı:**
```html
<table class="positions-table">
    <thead>
        <tr>
            <th>📚 Strateji / TF</th>
            <th>Yön / Parite</th>
            <th>Miktar / Kaldıraç</th>
            <th>Giriş / Pozisyon Değeri</th>
            <th>Mevcut / P&L ($)</th>
            <th>ROE (%)</th>
            <th>SL / TP / Liq</th>
            <th>İşlem</th>
        </tr>
    </thead>
    <tbody id="positions-body"></tbody>
</table>
```

**Her Satır (Pozisyon):**
```html
<tr>
    <td>
        <div style="font-weight:600;">trend_master</div>
        <div style="font-size:0.7rem; color:var(--text-muted);">1h</div>
    </td>
    <td>
        <div style="color:var(--neon-green);">🟢 LONG</div>
        <div>BTC/USDT:USDT</div>
    </td>
    <td>
        <div>0.1 BTC</div>
        <div>5x</div>
    </td>
    <td>
        <div>$50,000.00</div>
        <div style="font-size:0.7rem;">$25,000.00</div>
    </td>
    <td>
        <div>$50,250.00</div>
        <div style="color:var(--neon-green);">+$25.00</div>
    </td>
    <td style="color:var(--neon-green);">+0.50%</td>
    <td>
        <div style="font-size:0.7rem;">
            SL: $49,000<br>
            TP: $52,000<br>
            Liq: $38,500
        </div>
    </td>
    <td>
        <button class="btn btn-danger btn-sm" onclick="closePosition('bot_123')">
            ❌ Kapat
        </button>
    </td>
</tr>
```

**Pozisyon Kapatma:**
```javascript
// frontend/app.js
async function closePosition(bot_id) {
    if (confirm(`${bot_id} pozisyonu kapatılsın mı?`)) {
        try {
            await api.post('/api/v1/bot/stop', { bot_id });
            showToast('✅ Pozisyon kapatıldı', 'success');
            loadPositions(); // Tabloyu yenile
        } catch (error) {
            showToast('❌ Kapatma hatası: ' + error.message, 'error');
        }
    }
}
```

---

### **4. Sermaye Kullanımı**

**Container:** `.usage-grid`

| Metrik | ID | Format | Açıklama |
|--------|----|--------|----------|
| **💵 Kullanılan Marjin** | `#usage-used-margin` | `$5,000.00` | Açık pozisyonlarda kilitli |
| **💰 Kullanılabilir Bakiye** | `#usage-free-margin` | `$5,000.00` | Yeni işlem için mevcut |
| **📊 Toplam Pozisyon Değeri** | `#usage-notional` | `$25,000.00` | Kaldıraçlı toplam değer |
| **⚡ Ortalama Kaldıraç** | `#usage-leverage` | `5x` | Pozisyonlar ortalaması |

**Hesaplama:**
```javascript
// frontend/app.js
function updateCapitalUsage(positions) {
    let usedMargin = 0;
    let totalNotional = 0;
    let totalLeverage = 0;
    
    positions.forEach(pos => {
        const notional = pos.size * pos.entry_price * pos.leverage;
        const margin = notional / pos.leverage;
        
        usedMargin += margin;
        totalNotional += notional;
        totalLeverage += pos.leverage;
    });
    
    const avgLeverage = positions.length > 0 ? 
        (totalLeverage / positions.length).toFixed(1) : '0';
    
    document.getElementById('usage-used-margin').textContent = 
        `$${usedMargin.toFixed(2)}`;
    
    document.getElementById('usage-free-margin').textContent = 
        `$${(store.get('system').metrics?.balance - usedMargin).toFixed(2)}`;
    
    document.getElementById('usage-notional').textContent = 
        `$${totalNotional.toFixed(2)}`;
    
    document.getElementById('usage-leverage').textContent = 
        `${avgLeverage}x`;
}
```

---

## 🔄 Otomatik Güncelleme

| Bileşen | Interval | Kaynak |
|---------|----------|--------|
| **Aktif Stratejiler** | 5 saniye | REST API Polling |
| **KPI Dashboard** | 3 saniye | REST API Polling |
| **Pozisyon Tablosu** | 1 saniye | WebSocket Push |
| **Sermaye Kullanımı** | 3 saniye | REST API Polling |

**WebSocket Entegrasyonu:**
```javascript
// frontend/app.js
function setupWebSocket() {
    const ws = new WebSocket('ws://localhost:8000/ws/positions');
    
    ws.onmessage = (event) => {
        const positions = JSON.parse(event.data);
        renderPositionsTable(positions);
        updateCapitalUsage(positions);
    };
}
```

---

## 🚨 Sorun Giderme

### **Sorun 1: Pozisyonlar Gösterilmiyor**

**Semptom:** Tablo boş, "Açık pozisyon yok" mesajı

**Çözüm:**
1. Bot çalışıyor mu kontrol et:
   ```javascript
   const bots = await api.get('/api/v1/bot/list');
   console.log('Active bots:', bots);
   ```
2. Event Bus çalışıyor mu:
   ```javascript
   console.log('Event Bus running:', event_bus.running);
   ```
3. Manuel refresh yap:
   ```javascript
   loadPositions();
   ```

---

### **Sorun 2: P&L Güncellenmiyor**

**Semptom:** P&L sabit, canlı güncellenmiyor

**Çözüm:**
1. WebSocket bağlantısını kontrol et:
   ```javascript
   console.log('WebSocket state:', ws.readyState);
   ```
2. API endpoint çalışıyor mu:
   ```bash
   curl http://localhost:8000/api/v1/dashboard-metrics
   ```
3. Auto-refresh interval'i kontrol et:
   ```javascript
   console.log('Refresh interval:', refreshInterval);
   ```

---

### **Sorun 3: Pozisyon Kapatılmıyor**

**Semptom:** "Kapat" butonu çalışmıyor

**Çözüm:**
1. Bot ID doğru mu:
   ```javascript
   console.log('Bot ID:', bot_id);
   ```
2. API endpoint çalışıyor mu:
   ```bash
   curl -X POST http://localhost:8000/api/v1/bot/stop \
     -H "Content-Type: application/json" \
     -d '{"bot_id": "bot_123"}'
   ```
3. Console'da hata var mı kontrol et

---

## 📚 İlgili Dokümanlar

- **Dashboard:** `ui_reference/dashboard.md`
- **Paper Trader:** `trading_engine/paper_trader.md`
- **Position Manager:** `features/position_manager.md`
- **Risk Engine:** `features/risk_engine.md`

---

*Bu doküman Aktif Emirler Sekmesi v4.0 (Mart 2026) için hazırlanmıştır.*
*Güncellemeler için `frontend/index.html` (tab-orders) ve `frontend/app.js` dosyalarını kontrol edin.*
