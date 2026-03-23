# 📚 Strateji Kütüphanesi (Strategy Library)

**Versiyon:** v4.0 (Production-Ready)
**Son Güncelleme:** Mart 2026
**Dosya:** `frontend/index.html` (tab-strategies)

---

## 📋 Genel Bakış

**Strateji Kütüphanesi**, sistemde gömülü (built-in) bulunan 6 ana stratejiyi ve kullanıcı tarafından oluşturulan no-code (JSON) stratejileri yöneten merkezi kütüphanedir.

---

## 📁 Konum

```
Sol Menü → 📚 Strateji Kütüphanesi
```

**Tab ID:** `tab-strategies`

---

## 🏗️ Strateji Mimarisi

```
┌─────────────────────────────────────────────────────────┐
│  StrategyManager (strategy/manager.py)                  │
├─────────────────────────────────────────────────────────┤
│  BUILT-IN STRATEJİLER (Python)                          │
│  ├─ TrendMaster Pro                                     │
│  ├─ Scalper Ninja                                       │
│  ├─ Adaptive Koncorde X                                 │
│  ├─ Golden Combo                                        │
│  ├─ Divergence Hunter                                   │
│  └─ KNN Quant ATR Shield                                │
├─────────────────────────────────────────────────────────┤
│  NO-CODE STRATEJİLER (JSON - Runtime Load)              │
│  ├─ user_strategy_1.json                                │
│  ├─ user_strategy_2.json                                │
│  └─ ... (strategy/custom/ klasöründe)                   │
└─────────────────────────────────────────────────────────┘
```

---

## 1. BUILT-IN STRATEJİLER (Python)

### **1.1 TrendMaster Pro**

**Dosya:** `strategy/trend_master.py`

**Sınıf:**
```python
class TrendMasterPro(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.params = {
            'ema_period': 20,
            'atr_multiplier': 2.0,
            'rsi_period': 14
        }
```

**Hedef Timeframe:**
- ✅ **1h** (Önerilen)
- ✅ **4h**
- ✅ **1d**

**Strateji Mantığı:**
```
LONG Koşulları:
  1. EMA 20 > EMA 50 (Trend BULL)
  2. RSI > 50 (Momentum pozitif)
  3. MACD > Signal (Kesişim yukarı)

SHORT Koşulları:
  1. EMA 20 < EMA 50 (Trend BEAR)
  2. RSI < 50 (Momentum negatif)
  3. MACD < Signal (Kesişim aşağı)
```

**Çıkış Stratejisi:**
```
Stop Loss: Entry - (ATR × 2.0)
Take Profit: Entry + (ATR × 4.0)
Trailing Stop: ATR × 1.5 (dinamik)
```

---

### **1.2 Scalper Ninja**

**Dosya:** `strategy/scalper_ninja.py`

**Sınıf:**
```python
class ScalperNinja(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.params = {
            'fast_ema': 9,
            'slow_ema': 21,
            'scalp_target': 0.005  # %0.5
        }
```

**Hedef Timeframe:**
- ✅ **1m** (Önerilen)
- ✅ **3m**
- ✅ **5m**

**Strateji Mantığı:**
```
LONG:
  - Fast EMA (9) crosses_over Slow EMA (21)
  - RSI < 30 (Oversold bounce)
  - Hızlı çıkış (%0.5 kar)

SHORT:
  - Fast EMA (9) crosses_under Slow EMA (21)
  - RSI > 70 (Overbought drop)
  - Hızlı çıkış (%0.5 kar)
```

**Çıkış Stratejisi:**
```
Stop Loss: %1 zarar
Take Profit: %0.5 kar (hızlı scalp)
Max Hold Time: 15 dakika
```

---

### **1.3 Adaptive Koncorde X**

**Dosya:** `strategy/adaptive_koncorde.py`

**Sınıf:**
```python
class AdaptiveKoncordeX(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.params = {
            'kalman_enabled': True,
            'koncorde_period': 14,
            'vix_threshold': 0.02
        }
```

**Hedef Timeframe:**
- ✅ **15m** (Önerilen)
- ✅ **30m**
- ✅ **1h**

**Strateji Mantığı:**
```
Özellikler:
  - Kalman Filtresi (Noise reduction)
  - Koncorde Patterns (Akıllı Para takibi)
  - BTC VIX (Volatilite endeksi filtresi)

LONG:
  - Kalman smoothed_close > EMA 50
  - Koncorde AL sinyali
  - BTC VIX < 0.02 (Düşük volatilite)

SHORT:
  - Kalman smoothed_close < EMA 50
  - Koncorde SAT sinyali
  - BTC VIX < 0.02
```

---

### **1.4 Golden Combo**

**Dosya:** `strategy/golden_combo.py`

**Sınıf:**
```python
class GoldenCombo(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.params = {
            'golden_cross_period': 200,
            'htf_enabled': True
        }
```

**Hedef Timeframe:**
- ✅ **1h** (Önerilen)
- ✅ **4h**
- ✅ **1d**

**Strateji Mantığı:**
```
Golden Cross (LONG):
  - EMA 50 crosses_over EMA 200
  - HTF Major BULL onayı
  - Volume > SMA 20 (Hacim artışı)

Death Cross (SHORT):
  - EMA 50 crosses_under EMA 200
  - HTF Major BEAR onayı
  - Volume > SMA 20
```

---

### **1.5 Divergence Hunter**

**Dosya:** `strategy/divergence_hunter.py`

**Sınıf:**
```python
class DivergenceHunter(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.params = {
            'divergence_lookback': 5,
            'min_divergence_angle': 15
        }
```

**Hedef Timeframe:**
- ✅ **15m** (Önerilen)
- ✅ **1h**
- ✅ **4h**

**Strateji Mantığı:**
```
Bullish Divergence (LONG):
  - Fiyat: Lower Low
  - RSI: Higher Low
  - Açı: ≥ 15 derece

Bearish Divergence (SHORT):
  - Fiyat: Higher High
  - RSI: Lower High
  - Açı: ≥ 15 derece
```

---

### **1.6 KNN Quant ATR Shield**

**Dosya:** `strategy/knn_quant.py`

**Sınıf:**
```python
class KNNQuantATRShield(BaseStrategy):
    def __init__(self):
        super().__init__()
        self.params = {
            'k_neighbors': 5,
            'atr_shield_multiplier': 2.5
        }
```

**Hedef Timeframe:**
- ✅ **1h** (Önerilen)
- ✅ **4h**

**Strateji Mantığı:**
```
KNN Classification:
  - 5 en yakın komşuyu bul
  - Majority vote ile yön tahmini
  - Confidence ≥ 60% → İşlem

ATR Shield:
  - Stop Loss: ATR × 2.5 (Geniş stop)
  - Take Profit: ATR × 5.0 (Yüksek hedef)
  - Risk/Reward: 1:2
```

---

## 2. NO-CODE STRATEJİLER (JSON)

### **2.1 Runtime Hot Reload**

**Sistem Durmadan Dinamik Yükleme:**

```python
# strategy/manager.py
class StrategyManager:
    @staticmethod
    def load_custom_strategies():
        """
        strategy/custom/ klasöründeki JSON stratejileri
        runtime'da (sistem durmadan) yükle.
        """
        custom_dir = Path('strategy/custom')
        
        for json_file in custom_dir.glob('*.json'):
            try:
                with open(json_file, 'r') as f:
                    strategy_data = json.load(f)
                
                # StrategyBuilder ile çalıştırılabilir hale getir
                executor = StrategyExecutor(strategy_data)
                
                # StrategyManager'a kaydet
                StrategyManager.custom_strategies[json_file.stem] = executor
                
                logger.info(f"✅ No-code strateji yüklendi: {json_file.stem}")
                
            except Exception as e:
                logger.error(f"❌ Strateji yükleme hatası ({json_file}): {e}")
```

**Hot Reload Akışı:**
```
1. Kullanıcı Strateji Oluşturucu'dan strateji kaydeder
2. JSON dosyası strategy/custom/ klasörüne yazılır
3. StrategyManager dosyayı algılar (file watcher)
4. JSON parse edilir, StrategyExecutor oluşturulur
5. StrategyManager.custom_strategies dict'e eklenir
6. Bot başlatıldığında yeni strateji kullanılabilir

SÜREÇ: < 1 saniye (sistem durmadan)
```

---

### **2.2 JSON Strateji Formatı**

**Örnek:**
```json
{
    "name": "My Custom Strategy",
    "description": "RSI + EMA confluence",
    "version": "1.0",
    "timeframe": "1h",
    "indicators": [
        {
            "type": "EMA",
            "params": {"period": 20},
            "output": "ema_20"
        },
        {
            "type": "RSI",
            "params": {"period": 14},
            "output": "rsi_14"
        }
    ],
    "long_conditions": [
        {
            "indicator": "ema_20",
            "operator": ">",
            "target": "ema_50"
        },
        {
            "indicator": "rsi_14",
            "operator": ">",
            "value": 50
        }
    ],
    "short_conditions": [
        {
            "indicator": "ema_20",
            "operator": "<",
            "target": "ema_50"
        },
        {
            "indicator": "rsi_14",
            "operator": "<",
            "value": 50
        }
    ],
    "long_logic": "AND",
    "short_logic": "AND",
    "stop_loss_atr": 2.0,
    "take_profit_atr": 4.0,
    "max_risk_percent": 1.0
}
```

---

### **2.3 Strateji Yönetimi**

**Kaydetme:**
```javascript
// frontend/app.js
async function saveStrategy() {
    const strategy = {
        name: document.getElementById('strategy-name').value,
        description: document.getElementById('strategy-description').value,
        long_conditions: collectConditions('long'),
        short_conditions: collectConditions('short'),
        long_logic: getLogic('long'),
        short_logic: getLogic('short')
    };
    
    const response = await api.post('/api/v1/strategy-builder/save', strategy);
    
    if (response.status === 'success') {
        showToast('✅ Strateji kaydedildi: ' + strategy.name, 'success');
        loadStrategyLibrary(); // Kütüphaneyi yenile
    }
}
```

**Silme:**
```javascript
async function deleteStrategy(filename) {
    if (confirm(`${filename} silinecek. Emin misiniz?`)) {
        const response = await api.delete(`/api/v1/strategy-builder/delete/${filename}`);
        
        if (response.status === 'success') {
            showToast('✅ Strateji silindi', 'success');
            loadStrategyLibrary();
        }
    }
}
```

**Yükleme:**
```javascript
async function loadStrategyLibrary() {
    const response = await api.get('/api/v1/strategy-builder/list');
    
    const container = document.getElementById('strategy-library-container');
    container.innerHTML = response.strategies.map(s => `
        <div class="strategy-card">
            <div class="strategy-name">${s.name}</div>
            <div class="strategy-type">${s.type}</div>
            <div class="strategy-actions">
                <button onclick="selectStrategy('${s.filename}')">Seç</button>
                <button onclick="deleteStrategy('${s.filename}')">Sil</button>
            </div>
        </div>
    `).join('');
}
```

---

## 📊 Strateji Karşılaştırma Tablosu

| Strateji | Timeframe | Win Rate | Risk/Reward | Özellikler |
|----------|-----------|----------|-------------|------------|
| **TrendMaster Pro** | 1h-4h | %60-65 | 1:2 | EMA trend, RSI momentum |
| **Scalper Ninja** | 1m-5m | %55-60 | 1:0.5 | Hızlı scalp, EMA cross |
| **Adaptive Koncorde X** | 15m-1h | %65-70 | 1:2.5 | Kalman, Koncorde, VIX |
| **Golden Combo** | 1h-1d | %50-55 | 1:3 | Golden/Death cross, HTF |
| **Divergence Hunter** | 15m-4h | %60-65 | 1:2 | RSI divergence |
| **KNN Quant** | 1h-4h | %65-70 | 1:2 | KNN classification, ATR shield |

---

## 🚨 Sorun Giderme

### **Sorun 1: No-Code Strateji Yüklenmiyor**

**Semptom:** "Strateji bulunamadı" hatası

**Çözüm:**
1. JSON dosyası `strategy/custom/` klasöründe mi:
   ```bash
   ls strategy/custom/*.json
   ```
2. JSON syntax doğru mu:
   ```bash
   python -m json.tool strategy/custom/my_strategy.json
   ```
3. StrategyManager yeniden yüklendi mi:
   ```python
   StrategyManager.load_custom_strategies()
   ```

---

### **Sorun 2: Built-in Strateji Çalışmıyor**

**Semptom:** "TrendMaster Pro bulunamadı"

**Çözüm:**
1. Strateji dosyası var mı:
   ```bash
   ls strategy/trend_master.py
   ```
2. Import hatası var mı:
   ```python
   from strategy.trend_master import TrendMasterPro
   ```
3. StrategyManager loglarını kontrol et:
   ```python
   logger.info(f"Loaded strategies: {StrategyManager.strategies.keys()}")
   ```

---

## 📚 İlgili Dokümanlar

- **Strategy Builder:** `ui_reference/strategy_builder.md`
- **Strategy Confluence:** `strategies/confluence.md`
- **Walk-Forward Optimization:** `features/walk_forward_optimization.md`

---

*Bu doküman Strateji Kütüphanesi v4.0 (Mart 2026) için hazırlanmıştır.*
*Güncellemeler için `strategy/manager.py` ve `strategy/` klasörünü kontrol edin.*
