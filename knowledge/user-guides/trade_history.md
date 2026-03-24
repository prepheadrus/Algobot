# 📜 İşlem Geçmişi (Trade History)

**Versiyon:** v4.0 (Production-Ready)
**Son Güncelleme:** Mart 2026
**Dosya:** `frontend/index.html` (tab-history)

---

## 📋 Genel Bakış

**İşlem Geçmişi** sekmesi, veritabanına kaydedilen tüm geçmiş işlemleri, detaylı performans analizini ve işlem istatistiklerini gösterir.

---

## 📁 Konum

```
Sol Menü → 📜 İşlem Geçmişi
```

**Tab ID:** `tab-history`

---

## 🧩 Bileşenler

### **1. İşlem Geçmişi Tablosu**

**ID:** `#trade-history-table`

**Tablo Yapısı:**
```html
<table class="trade-history-table">
    <thead>
        <tr>
            <th>ID</th>
            <th>Tarih</th>
            <th>Sembol</th>
            <th>Strateji</th>
            <th>Yön</th>
            <th>Giriş</th>
            <th>Çıkış</th>
            <th>Miktar</th>
            <th>Kaldıraç</th>
            <th>PnL ($)</th>
            <th>PnL (%)</th>
            <th>Neden</th>
        </tr>
    </thead>
    <tbody id="trade-history-body"></tbody>
</table>
```

**Her Satır (İşlem):**
```html
<tr>
    <td>trade_1710847205</td>
    <td>2026-03-17 12:30:00</td>
    <td>BTC/USDT:USDT</td>
    <td>trend_master</td>
    <td style="color:var(--neon-green);">🟢 LONG</td>
    <td>$50,000.00</td>
    <td>$51,000.00</td>
    <td>0.1 BTC</td>
    <td>5x</td>
    <td style="color:var(--neon-green);">+$100.00</td>
    <td style="color:var(--neon-green);">+2.00%</td>
    <td>TAKE_PROFIT</td>
</tr>
```

**Yükleme:**
```javascript
// frontend/app.js
async function loadTradeHistory() {
    const tbody = document.getElementById('trade-history-body');
    
    try {
        const history = await api.get('/api/v1/trades/history');
        
        tbody.innerHTML = history.trades.map(trade => `
            <tr>
                <td>${trade.id}</td>
                <td>${trade.timestamp}</td>
                <td>${trade.symbol}</td>
                <td>${trade.strategy_id || 'N/A'}</td>
                <td style="color:${trade.direction === 'LONG' ? 'var(--neon-green)' : 'var(--neon-red)'}">
                    ${trade.direction === 'LONG' ? '🟢' : '🔴'} ${trade.direction}
                </td>
                <td>$${trade.entry_price.toFixed(2)}</td>
                <td>$${trade.exit_price?.toFixed(2) || 'N/A'}</td>
                <td>${trade.size} ${trade.symbol.split('/')[0]}</td>
                <td>${trade.leverage}x</td>
                <td style="color:${trade.pnl_usd >= 0 ? 'var(--neon-green)' : 'var(--neon-red)'}">
                    ${trade.pnl_usd >= 0 ? '+' : ''}$${trade.pnl_usd.toFixed(2)}
                </td>
                <td style="color:${trade.pnl_percent >= 0 ? 'var(--neon-green)' : 'var(--neon-red)'}">
                    ${trade.pnl_percent >= 0 ? '+' : ''}${(trade.pnl_percent * 100).toFixed(2)}%
                </td>
                <td>${trade.reason || 'N/A'}</td>
            </tr>
        `).join('');
    } catch (error) {
        showToast('❌ Geçmiş yükleme hatası: ' + error.message, 'error');
    }
}
```

---

### **2. İşlem İstatistikleri**

**Container:** `#trade-stats-container`

| İstatistik | ID | Format | Açıklama |
|------------|----|--------|----------|
| **Toplam İşlem** | `#stat-total-trades` | `45` | Tüm işlem sayısı |
| **Kazanan İşlem** | `#stat-winning-trades` | `28` | Karlı işlem sayısı |
| **Kaybeden İşlem** | `#stat-losing-trades` | `17` | Zararlı işlem sayısı |
| **Win Rate** | `#stat-win-rate` | `62.2%` | Kazanma oranı |
| **Toplam PnL** | `#stat-total-pnl` | `+$2,500.00` | Net kar/zarar |
| **Ortalama PnL** | `#stat-avg-pnl` | `$55.56` | İşlem başına ortalama |
| **Profit Factor** | `#stat-profit-factor` | `2.1` | Brüt Kar / Brüt Zarar |
| **Max Drawdown** | `#stat-max-drawdown` | `-$450.00` | Maksimum düşüş |

**Güncelleme:**
```javascript
// frontend/app.js
async function updateTradeStats() {
    const stats = await api.get('/api/v1/trades/stats');
    
    document.getElementById('stat-total-trades').textContent = stats.total_trades;
    document.getElementById('stat-winning-trades').textContent = stats.winning_trades;
    document.getElementById('stat-losing-trades').textContent = stats.losing_trades;
    document.getElementById('stat-win-rate').textContent = `${(stats.win_rate * 100).toFixed(1)}%`;
    document.getElementById('stat-total-pnl').textContent = `${stats.total_pnl >= 0 ? '+' : ''}$${stats.total_pnl.toFixed(2)}`;
    document.getElementById('stat-avg-pnl').textContent = `$${stats.average_pnl.toFixed(2)}`;
    document.getElementById('stat-profit-factor').textContent = stats.profit_factor.toFixed(2);
    document.getElementById('stat-max-drawdown').textContent = `-$${Math.abs(stats.max_drawdown).toFixed(2)}`;
}
```

---

### **3. Filtreler**

**Container:** `.trade-filters`

| Filtre | ID | Tip | Seçenekler |
|--------|----|-----|------------|
| **Sembol** | `#filter-symbol` | Select | BTC/USDT, ETH/USDT, vb. |
| **Strateji** | `#filter-strategy` | Select | trend_master, scalper_ninja, vb. |
| **Yön** | `#filter-direction` | Select | LONG, SHORT, ALL |
| **Tarih Aralığı** | `#filter-date-range` | Date Range | Start - End |
| **Durum** | `#filter-status` | Select | Closed, Open, ALL |

**Uygulama:**
```javascript
// frontend/app.js
async function filterTradeHistory() {
    const filters = {
        symbol: document.getElementById('filter-symbol').value,
        strategy: document.getElementById('filter-strategy').value,
        direction: document.getElementById('filter-direction').value,
        start_date: document.getElementById('filter-start-date').value,
        end_date: document.getElementById('filter-end-date').value,
        status: document.getElementById('filter-status').value
    };
    
    const history = await api.get('/api/v1/trades/history', filters);
    renderTradeHistory(history.trades);
}
```

---

### **4. Butonlar**

| Buton | onclick | Aksiyon |
|-------|---------|---------|
| **🔄 Yenile** | `onclick="loadTradeHistory()"` | İşlem geçmişini yeniden yükle |
| **🗑️ Geçmişi Temizle** | `onclick="clearTradeHistory()"` | Tüm işlem geçmişini sil |

**Geçmişi Temizle:**
```javascript
// frontend/app.js
async function clearTradeHistory() {
    if (confirm('⚠️ TÜM işlem geçmişi silinecek! Emin misiniz?')) {
        try {
            await api.delete('/api/v1/trades/clear');
            showToast('✅ İşlem geçmişi temizlendi', 'success');
            loadTradeHistory(); // Tabloyu yenile
        } catch (error) {
            showToast('❌ Temizleme hatası: ' + error.message, 'error');
        }
    }
}
```

---

## 🔄 Otomatik Güncelleme

| Bileşen | Interval | Kaynak |
|---------|----------|--------|
| **İşlem Tablosu** | Manuel | REST API |
| **İstatistikler** | 10 saniye | REST API |
| **Filtreler** | Manuel | User input |

---

## 📊 İşlem Geçmişi API

### **GET /api/v1/trades/history**

**Açıklama:** İşlem geçmişini döner.

**Request:**
```http
GET /api/v1/trades/history?symbol=BTC/USDT&strategy=trend_master&direction=LONG
```

**Response:**
```json
{
    "trades": [
        {
            "id": "trade_1710847205",
            "timestamp": "2026-03-17T12:30:00Z",
            "closed_at": "2026-03-17T14:45:00Z",
            "symbol": "BTC/USDT:USDT",
            "strategy_id": "trend_master",
            "direction": "LONG",
            "entry_price": 50000.0,
            "exit_price": 51000.0,
            "size": 0.1,
            "leverage": 5.0,
            "pnl_usd": 100.0,
            "pnl_percent": 0.02,
            "reason": "TAKE_PROFIT",
            "bot_id": "BTC_1h_1"
        }
    ]
}
```

---

### **GET /api/v1/trades/stats**

**Açıklama:** İşlem istatistiklerini döner.

**Response:**
```json
{
    "total_trades": 45,
    "winning_trades": 28,
    "losing_trades": 17,
    "win_rate": 0.622,
    "total_pnl": 2500.0,
    "average_pnl": 55.56,
    "profit_factor": 2.1,
    "max_drawdown": -450.0
}
```

---

### **DELETE /api/v1/trades/clear**

**Açıklama:** Tüm işlem geçmişini siler.

**Response:**
```json
{
    "status": "success",
    "message": "İşlem geçmişi temizlendi"
}
```

---

## 🚨 Sorun Giderme

### **Sorun 1: İşlem Geçmişi Yüklenmiyor**

**Semptom:** Tablo boş, "İşlem yok" mesajı

**Çözüm:**
1. Bot çalıştı mı kontrol et:
   ```javascript
   const bots = await api.get('/api/v1/bot/list');
   console.log('Active bots:', bots);
   ```
2. Veritabanı bağlantısını kontrol et:
   ```bash
   python check_db.py
   ```
3. Manuel refresh yap:
   ```javascript
   loadTradeHistory();
   ```

---

### **Sorun 2: İstatistikler Yanlış**

**Semptom:** Win Rate %100 gösteriyor ama 10 işlem var

**Çözüm:**
1. Veritabanı sorgusunu kontrol et:
   ```sql
   SELECT COUNT(*) FROM trades WHERE pnl_usd > 0;
   ```
2. API response'u logla:
   ```javascript
   const stats = await api.get('/api/v1/trades/stats');
   console.log('Stats:', stats);
   ```

---

### **Sorun 3: Filtreler Çalışmıyor**

**Semptom:** Filtre seçince tablo güncellenmiyor

**Çözüm:**
1. Event listener bağlı mı:
   ```javascript
   document.getElementById('filter-symbol').addEventListener('change', filterTradeHistory);
   ```
2. API parametreleri doğru mu:
   ```javascript
   console.log('Filters:', filters);
   ```

---

## 📚 İlgili Dokümanlar

- **Aktif Emirler:** `ui_reference/active_orders_positions.md`
- **Paper Trader:** `trading_engine/paper_trader.md`
- **Database Schema:** `developer_reference/database_schema_reference.md`

---

*Bu doküman İşlem Geçmişi v4.0 (Mart 2026) için hazırlanmıştır.*
*Güncellemeler için `frontend/index.html` (tab-history) ve `frontend/app.js` dosyalarını kontrol edin.*
