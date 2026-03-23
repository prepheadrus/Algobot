# 📈 Performans Raporları (Performance Reports)

**Versiyon:** v4.0 (Production-Ready)
**Son Güncelleme:** Mart 2026
**Dosya:** `frontend/index.html` (tab-reports)

---

## 📋 Genel Bakış

**Performans Raporları**, her stratejinin ve botun detaylı başarı metriklerini, AI önerilerini ve karşılaştırmalı analizleri sunan gelişmiş raporlama modülüdür.

---

## 📁 Konum

```
Sol Menü → 📈 Performans Raporları
```

**Tab ID:** `tab-reports`

---

## 🧩 Bileşenler

### **1. Strateji Rapor Kartları**

**Container:** `#strategy-report-container`

**Her Kart:**
```html
<div class="strategy-report-card">
    <div class="card-header">
        <h3>TrendMaster Pro</h3>
        <span class="badge badge-success">BTC/USDT:USDT</span>
    </div>
    <div class="card-metrics">
        <div class="metric">
            <span class="label">Toplam İşlem</span>
            <span class="value">45</span>
        </div>
        <div class="metric">
            <span class="label">Win Rate</span>
            <span class="value success">62.2%</span>
        </div>
        <div class="metric">
            <span class="label">Total P&L</span>
            <span class="value success">+$2,500.00</span>
        </div>
        <div class="metric">
            <span class="label">Profit Factor</span>
            <span class="value">2.1</span>
        </div>
        <div class="metric">
            <span class="label">Max Drawdown</span>
            <span class="value danger">-$450.00</span>
        </div>
    </div>
    <div class="card-ai-feedback">
        <div class="ai-recommendation ✅">
            Mükemmel uyum! Bu strateji BTC/USDT paritesinde yüksek başarı gösteriyor.
        </div>
    </div>
</div>
```

---

## 2. METRİK MATEMATİĞİ

### **2.1 Win Rate**

**Formül:**
```
Win Rate = (wins / total_trades) × 100
```

**Python Implementasyonu:**
```python
# core/trading/services/reporter.py
def calculate_win_rate(trades: List[Trade]) -> float:
    """
    Win Rate hesapla.
    
    Args:
        trades: İşlem listesi
    
    Returns:
        Win Rate (%)
    """
    if not trades:
        return 0.0
    
    wins = sum(1 for trade in trades if trade.pnl_usd > 0)
    total_trades = len(trades)
    
    win_rate = (wins / total_trades) × 100
    
    return win_rate
```

**Örnek:**
```
Toplam İşlem: 45
Kazanan İşlem: 28
Kaybeden İşlem: 17

Win Rate = (28 / 45) × 100 = 62.2%
```

---

### **2.2 Total P&L**

**Formül:**
```
Total P&L = Σ(pnl_usd)
```

**Python Implementasyonu:**
```python
def calculate_total_pnl(trades: List[Trade]) -> float:
    """
    Toplam P&L hesapla.
    
    Args:
        trades: İşlem listesi
    
    Returns:
        Total P&L ($)
    """
    return sum(trade.pnl_usd for trade in trades)
```

**Örnek:**
```
İşlem 1: +$100.00
İşlem 2: -$50.00
İşlem 3: +$200.00
İşlem 4: -$75.00

Total P&L = 100 - 50 + 200 - 75 = +$175.00
```

---

### **2.3 Profit Factor**

**Formül:**
```
Profit Factor = |Brüt Kar| / |Brüt Zarar|
```

**Python Implementasyonu:**
```python
def calculate_profit_factor(trades: List[Trade]) -> float:
    """
    Profit Factor hesapla.
    
    Args:
        trades: İşlem listesi
    
    Returns:
        Profit Factor
    """
    gross_profit = sum(trade.pnl_usd for trade in trades if trade.pnl_usd > 0)
    gross_loss = abs(sum(trade.pnl_usd for trade in trades if trade.pnl_usd < 0))
    
    if gross_loss == 0:
        return float('inf')  # Zarar yok
    
    return gross_profit / gross_loss
```

**Örnek:**
```
Brüt Kar: +$5,000.00
Brüt Zarar: -$2,380.00

Profit Factor = 5,000 / 2,380 = 2.1
```

---

### **2.4 Max Drawdown**

**Formül:**
```
Max Drawdown = max(peak_balance - current_balance) / peak_balance
```

**Python Implementasyonu:**
```python
def calculate_max_drawdown(equity_curve: List[float]) -> float:
    """
    Max Drawdown hesapla.
    
    Args:
        equity_curve: Bakiye geçmişi
    
    Returns:
        Max Drawdown ($)
    """
    if not equity_curve:
        return 0.0
    
    peak = equity_curve[0]
    max_drawdown = 0.0
    
    for balance in equity_curve:
        if balance > peak:
            peak = balance
        
        drawdown = peak - balance
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    
    return max_drawdown
```

**Örnek:**
```
Bakiye Geçmişi:
  $10,000 → $10,500 → $10,200 → $10,800 → $10,350

Peak: $10,800
Çukur: $10,350

Max Drawdown = $10,800 - $10,350 = $450.00
```

---

## 3. AI ÖNERİ ALGORİTMASI

### **3.1 Otonom Geri Bildirim Sistemi**

**AI Feedback Rules:**

```python
# core/trading/services/reporter.py
def generate_ai_recommendation(strategy_name: str, symbol: str, stats: Dict) -> str:
    """
    İşlem geçmişine dayalı otonom geri bildirim üret.
    
    Args:
        strategy_name: Strateji adı
        symbol: Sembol
        stats: İstatistikler (win_rate, total_pnl, total_trades, etc.)
    
    Returns:
        AI öneri metni
    """
    win_rate = stats.get('win_rate', 0)
    total_pnl = stats.get('total_pnl', 0)
    total_trades = stats.get('total_trades', 0)
    profit_factor = stats.get('profit_factor', 0)
    max_drawdown = stats.get('max_drawdown', 0)
    
    # ❌ KÖTÜ PERFORMANS
    if win_rate < 40 and total_trades >= 3:
        return (
            f"❌ Düşük başarı oranı ({win_rate:.1f}%). "
            f"Stop-Loss hatalı olabilir. ATR çarpanını gözden geçirin. "
            f"Win rate %{40 - win_rate:.1f} puan artırılmalı."
        )
    
    if profit_factor < 1.0 and total_trades >= 5:
        return (
            f"❌ Zarardasınız (Profit Factor: {profit_factor:.2f}). "
            f"Strateji {symbol} paritesine uygun değil. "
            f"Take Profit hedeflerini artırın veya strateji değiştirin."
        )
    
    if max_drawdown > 1000 and total_trades >= 10:
        return (
            f"❌ Yüksek drawdown (${max_drawdown:.2f}). "
            f"Risk ayarlarını gözden geçirin. "
            f"Max Risk %1'den düşük olmalı."
        )
    
    # ⚠️ ORTA PERFORMANS
    if 40 <= win_rate < 55 and total_trades >= 5:
        return (
            f"⚠️ Orta performans ({win_rate:.1f}%). "
            f"Strateji çalışıyor ancak optimize edilebilir. "
            f"HTF filtrelerini aktif etmeyi düşünün."
        )
    
    if 1.0 <= profit_factor < 1.5 and total_trades >= 5:
        return (
            f"⚠️ Kararsız denge (Profit Factor: {profit_factor:.2f}). "
            f"Risk/Reward oranını 1:2'ye yükseltin."
        )
    
    # ✅ İYİ PERFORMANS
    if win_rate >= 60 and total_pnl > 0 and total_trades >= 10:
        return (
            f"✅ Mükemmel uyum! Bu strateji {symbol} paritesinde yüksek başarı gösteriyor. "
            f"Win Rate: %{win_rate:.1f}, Profit Factor: {profit_factor:.2f}. "
            f"Mevcut ayarlarla devam edilebilir."
        )
    
    if profit_factor >= 2.0 and total_trades >= 10:
        return (
            f"✅ Karlı strateji (Profit Factor: {profit_factor:.2f}). "
            f"Son 10 işlemde ${total_pnl:.2f} kar. "
            f"Kaldıraç artırımı değerlendirilebilir."
        )
    
    # 🏆 ÇOK İYİ PERFORMANS
    if win_rate >= 65 and profit_factor >= 2.5 and total_trades >= 20:
        return (
            f"🏆 ÜSTÜN PERFORMANS! "
            f"Win Rate: %{win_rate:.1f}, Profit Factor: {profit_factor:.2f}, "
            f"Total P&L: ${total_pnl:.2f}. "
            f"Bu strateji ile daha büyük pozisyonlar açılabilir."
        )
    
    # Varsayılan
    return f"ℹ️ Yeterli veri yok (İşlem sayısı: {total_trades}). En az 10 işlem bekleyin."
```

---

### **3.2 AI Öneri Örnekleri**

**Senaryo 1: Düşük Win Rate (<40%)**
```
Strateji: Scalper Ninja
Sembol: BTC/USDT:USDT
Win Rate: %35.5 (10 işlem)
Total P&L: -$250.00

AI Öneri:
❌ Düşük başarı oranı (%35.5%). Stop-Loss hatalı olabilir. 
ATR çarpanını gözden geçirin. Win rate %4.5 puan artırılmalı.
```

**Aksiyon:**
```yaml
# config.yaml
strategy:
  scalp_ninja:
    stop_loss_atr: 1.5 → 2.0  # Daha geniş stop
    take_profit_atr: 1.0 → 1.5  # Daha yüksek target
```

---

**Senaryo 2: Profit Factor < 1.0 (Zarar)**
```
Strateji: TrendMaster Pro
Sembol: ETH/USDT:USDT
Win Rate: %45.0 (15 işlem)
Profit Factor: 0.85
Total P&L: -$450.00

AI Öneri:
❌ Zarardasınız (Profit Factor: 0.85). Strateji ETH/USDT:USDT paritesine uygun değil. 
Take Profit hedeflerini artırın veya strateji değiştirin.
```

**Aksiyon:**
```
1. Strateji değiştir: TrendMaster Pro → Adaptive Koncorde X
2. Veya TP çarpanını artır: 2.0 → 3.0
```

---

**Senaryo 3: Mükemmel Performans (Win Rate ≥60%)**
```
Strateji: Adaptive Koncorde X
Sembol: BTC/USDT:USDT
Win Rate: %68.2 (25 işlem)
Profit Factor: 2.8
Total P&L: +$3,500.00

AI Öneri:
✅ Mükemmel uyum! Bu strateji BTC/USDT:USDT paritesinde yüksek başarı gösteriyor. 
Win Rate: %68.2, Profit Factor: 2.8. Mevcut ayarlarla devam edilebilir.
```

**Aksiyon:**
```
Mevcut ayarları koru. Kaldıraç 5x → 7x artırılabilir.
```

---

**Senaryo 4: Üstün Performans (Win Rate ≥65%, PF ≥2.5)**
```
Strateji: KNN Quant ATR Shield
Sembol: BTC/USDT:USDT
Win Rate: %72.5 (40 işlem)
Profit Factor: 3.2
Total P&L: +$8,500.00
Max Drawdown: -$350.00

AI Öneri:
🏆 ÜSTÜN PERFORMANS! Win Rate: %72.5, Profit Factor: 3.2, Total P&L: $8,500.00. 
Bu strateji ile daha büyük pozisyonlar açılabilir.
```

**Aksiyon:**
```yaml
# config.yaml
risk_management:
  max_risk_per_trade_percent: 1.0 → 2.0  # Risk artır
  max_leverage: 10 → 15  # Kaldıraç artır
```

---

## 4. RAPOR OLUŞTURMA

### **4.1 API Endpoint**

**GET /api/v1/strategy-report**

**Response:**
```json
{
    "reports": [
        {
            "strategy_name": "TrendMaster Pro",
            "symbol": "BTC/USDT:USDT",
            "timeframe": "1h",
            "total_trades": 45,
            "winning_trades": 28,
            "losing_trades": 17,
            "win_rate": 62.2,
            "total_pnl": 2500.0,
            "average_pnl": 55.56,
            "profit_factor": 2.1,
            "max_drawdown": 450.0,
            "sharpe_ratio": 1.8,
            "ai_recommendation": "✅ Mükemmel uyum! Bu strateji BTC/USDT paritesinde yüksek başarı gösteriyor."
        }
    ]
}
```

---

### **4.2 Rapor Yükleme**

**Buton:** `🔄 Raporu Güncelle`

**JavaScript:**
```javascript
// frontend/app.js
async function loadStrategyReport() {
    const container = document.getElementById('strategy-report-container');
    container.innerHTML = '<p style="text-align:center;padding:40px;">⏳ Rapor hazırlanıyor...</p>';
    
    try {
        const response = await api.get('/api/v1/strategy-report');
        
        container.innerHTML = response.reports.map(report => `
            <div class="strategy-report-card">
                <div class="card-header">
                    <h3>${report.strategy_name}</h3>
                    <span class="badge badge-success">${report.symbol}</span>
                    <span class="badge badge-info">${report.timeframe}</span>
                </div>
                <div class="card-metrics">
                    <div class="metric">
                        <span class="label">Toplam İşlem</span>
                        <span class="value">${report.total_trades}</span>
                    </div>
                    <div class="metric">
                        <span class="label">Win Rate</span>
                        <span class="value ${report.win_rate >= 60 ? 'success' : 'warning'}">
                            ${report.win_rate.toFixed(1)}%
                        </span>
                    </div>
                    <div class="metric">
                        <span class="label">Total P&L</span>
                        <span class="value ${report.total_pnl >= 0 ? 'success' : 'danger'}">
                            ${report.total_pnl >= 0 ? '+' : ''}$${report.total_pnl.toFixed(2)}
                        </span>
                    </div>
                    <div class="metric">
                        <span class="label">Profit Factor</span>
                        <span class="value">${report.profit_factor.toFixed(2)}</span>
                    </div>
                    <div class="metric">
                        <span class="label">Max DD</span>
                        <span class="value danger">-$${report.max_drawdown.toFixed(2)}</span>
                    </div>
                </div>
                <div class="card-ai-feedback">
                    <div class="ai-recommendation ${getAiIcon(report)}">
                        ${report.ai_recommendation}
                    </div>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        showToast('❌ Rapor yükleme hatası: ' + error.message, 'error');
    }
}

function getAiIcon(report) {
    if (report.win_rate >= 65 && report.profit_factor >= 2.5) {
        return '✅';  // Üstün
    } else if (report.win_rate >= 60 && report.total_pnl > 0) {
        return '✅';  // İyi
    } else if (report.win_rate < 40 || report.profit_factor < 1.0) {
        return '❌';  // Kötü
    } else {
        return '⚠️';  // Orta
    }
}
```

---

## 🚨 Sorun Giderme

### **Sorun 1: Rapor Boş Görünüyor**

**Semptom:** "Rapor yok" mesajı

**Çözüm:**
1. Yeterli işlem var mı:
   ```javascript
   const stats = await api.get('/api/v1/trades/stats');
   console.log('Total trades:', stats.total_trades);
   ```
2. En az 3 işlem gerekli (AI önerisi için)
3. Bot çalışıyor mu kontrol et

---

### **Sorun 2: AI Önerisi Yanlış**

**Semptom:** Win Rate %70 ama "Düşük başarı" diyor

**Çözüm:**
1. API response'u logla:
   ```javascript
   const report = await api.get('/api/v1/strategy-report');
   console.log('Report:', report);
   ```
2. AI algoritması güncel mi:
   ```python
   # core/trading/services/reporter.py
   print(f"Win rate: {win_rate}, Trades: {total_trades}")
   ```

---

## 📚 İlgili Dokümanlar

- **Trade History:** `ui_reference/trade_history.md`
- **Risk Engine:** `features/risk_engine.md`
- **WFO:** `features/walk_forward_optimization.md`

---

*Bu doküman Performans Raporları v4.0 (Mart 2026) için hazırlanmıştır.*
*Güncellemeler için `frontend/index.html` (tab-reports) dosyasını kontrol edin.*
