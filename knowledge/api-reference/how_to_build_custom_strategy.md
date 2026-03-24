# 🎨 No-Code Strateji Geliştirme Rehberi (How to Build Custom Strategy)

**Versiyon:** v4.0 (Production-Ready)
**Son Güncelleme:** Mart 2026
**Süre:** ~30 dakika
**Zorluk:** Orta

---

## 📋 Genel Bakış

Bu rehber, kullanıcının arayüzü kullanarak kantitatif bir trading modeli tasarlamasını, backtest etmesini ve optimize etmesini adım adım anlatır.

**4 Ana Aşama:**
1. ✅ İndikatör Seçimi
2. ✅ Mantıksal Kapılar (Logic Gates)
3. ✅ Risk Parametrelerinin Tanımlanması
4. ✅ Simülasyon ve Optimizasyon

---

## ⚠️ Ön Koşullar (Prerequisites)

### **1. Temel Bilgiler**

| Konu | Gereksinim | Kaynak |
|------|------------|--------|
| **Trading Temelleri** | LONG/SHORT, Stop Loss, Take Profit | [Investopedia](https://investopedia.com) |
| **Teknik Analiz** | İndikatörler (RSI, MACD, EMA) | `data/indicators/` dokümantasyonu |
| **Mantıksal Operatörler** | AND, OR, NOT | Boolean cebiri temelleri |

### **2. Sistem Hazırlığı**

```bash
# 1. Veri hazır olmalı (minimum 7 gün)
python check_db.py --symbol BTC/USDT --timeframe 1m

# Beklenen çıktı:
# ✅ BTC/USDT (1m): 10,080 mum bulundu (7 gün)

# 2. API çalışıyor olmalı
curl http://localhost:8000/api/v1/strategies

# Beklenen çıktı:
# {"strategies": ["trend_master", "scalper_ninja", ...]}
```

### **3. Strateji Tuvali**

```
Dashboard → Sol Menü → 🎨 Strateji Oluşturucu
```

---

## 📊 ADIM 1: İndikatör Seçimi

**Süre:** 5-10 dakika
**Amaç:** Strateji için gerekli teknik göstergeleri tuvale eklemek

---

### **1.1: Strateji Oluşturucu'yu Aç**

```
Dashboard → Sol Menü → 🎨 Strateji Oluşturucu
```

**Arayüz Düzeni:**
```
┌─────────────────────────────────────────────────────────┐
│  SOL PANEL           │  ORTA PANEL       │  SAĞ PANEL   │
│  📚 Gösterge         │  ⚙️ Koşul         │  🎯 Backtest │
│  Kütüphanesi         │  Oluşturucu       │  & Analiz    │
└─────────────────────────────────────────────────────────┘
```

---

### **1.2: Trend İndikatörleri**

#### **EMA (Exponential Moving Average)**

**Kategori:** `📈 TREND`

**Ekleme:**
```
1. SOL PANEL → 📈 TREND → EMA (20) tıkla
2. Parametre Modalı açılır
3. Period: 20 (varsayılan)
4. "Ekle" tıkla
```

**Parametreler:**
```json
{
    "type": "EMA",
    "params": {
        "period": 20
    },
    "output": "ema_20"
}
```

**Kullanım:**
- **Trend Yönü:** Fiyat > EMA 20 → BULL
- **Kesişim:** EMA 20 crosses_over EMA 50 → LONG sinyal

**Formül:**
```python
# data/indicators/trend.py
def ema(close: pd.Series, period: int = 20) -> pd.Series:
    """
    Exponential Moving Average.
    
    EMA = (Close × α) + (EMA_prev × (1 - α))
    α = 2 / (period + 1)
    """
    alpha = 2 / (period + 1)
    return close.ewm(alpha=alpha, adjust=False).mean()
```

---

#### **SMA (Simple Moving Average)**

**Kategori:** `📈 TREND`

**Ekleme:**
```
1. SOL PANEL → 📈 TREND → SMA (20) tıkla
2. Period: 50 (trend filtresi için)
3. "Ekle" tıkla
```

**Parametreler:**
```json
{
    "type": "SMA",
    "params": {
        "period": 50
    },
    "output": "sma_50"
}
```

---

### **1.3: Momentum İndikatörleri**

#### **RSI (Relative Strength Index)**

**Kategori:** `🚀 MOMENTUM`

**Ekleme:**
```
1. SOL PANEL → 🚀 MOMENTUM → RSI (14) tıkla
2. Period: 14 (varsayılan)
3. Overbought: 70
4. Oversold: 30
5. "Ekle" tıkla
```

**Parametreler:**
```json
{
    "type": "RSI",
    "params": {
        "period": 14,
        "overbought": 70,
        "oversold": 30
    },
    "output": "rsi_14"
}
```

**Yorumlama:**
- **RSI > 70:** Overbought (SAT baskısı)
- **RSI < 30:** Oversold (AL baskısı)
- **RSI = 50:** Nötr

**Formül:**
```python
# data/indicators/momentum.py
def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index.
    
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss (period boyunca)
    """
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    return 100 - (100 / (1 + rs))
```

---

#### **MACD (Moving Average Convergence Divergence)**

**Kategori:** `🚀 MOMENTUM`

**Ekleme:**
```
1. SOL PANEL → 🚀 MOMENTUM → MACD tıkla
2. Fast: 12
3. Slow: 26
4. Signal: 9
5. "Ekle" tıkla
```

**Parametreler:**
```json
{
    "type": "MACD",
    "params": {
        "fast": 12,
        "slow": 26,
        "signal": 9
    },
    "output": ["macd_line", "signal_line", "histogram"]
}
```

**Yorumlama:**
- **MACD > Signal:** BULL (LONG sinyal)
- **MACD < Signal:** BEAR (SHORT sinyal)
- **Histogram > 0:** Momentum yukarı

**Formül:**
```python
# data/indicators/momentum.py
def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    MACD = EMA(fast) - EMA(slow)
    Signal = EMA(MACD, signal)
    Histogram = MACD - Signal
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram
```

---

### **1.4: Hacim İndikatörleri**

#### **Koncorde (Hacim Tabanlı)**

**Kategori:** `📊 HACİM`

**Ekleme:**
```
1. SOL PANEL → 📊 HACİM → Koncorde tıkla
2. Period: 14
3. "Ekle" tıkla
```

**Parametreler:**
```json
{
    "type": "Koncorde",
    "params": {
        "period": 14
    },
    "output": "koncorde"
}
```

**Yorumlama:**
- **Koncorde > 0:** Hacim artışı (trend güçlü)
- **Koncorde < 0:** Hacim düşüşü (trend zayıf)

---

### **1.5: İndikatör Özeti**

**Eklenen İndikatörler:**
```
┌─────────────────────────────────────┐
│ 📚 Eklenen İndikatörler             │
├─────────────────────────────────────┤
│ 📈 TREND                            │
│   ├─ EMA (20) → ema_20              │
│   └─ SMA (50) → sma_50              │
│                                     │
│ 🚀 MOMENTUM                         │
│   ├─ RSI (14) → rsi_14              │
│   └─ MACD (12,26,9) → macd_line     │
│                                     │
│ 📊 HACİM                            │
│   └─ Koncorde (14) → koncorde       │
└─────────────────────────────────────┘
```

---

## 🔀 ADIM 2: Mantıksal Kapılar (Logic Gates)

**Süre:** 10-15 dakika
**Amaç:** AL (LONG) ve SAT (SHORT) koşullarını AND/OR operatörleriyle tanımlamak

---

### **2.1: LONG Koşulları**

**Panel:** `ORTA PANEL → 🟢 LONG Koşulları`

**Mantık Seçici:** `VE (AND)` seçili

---

#### **Koşul 1: Trend Filtresi**

**Ekleme:**
```
1. "➕ LONG Koşulu Ekle" tıkla
2. İndikatör: EMA
3. Operatör: > (Büyüktür)
4. Karşılaştırma: SMA
5. Değer: 50
```

**Koşul:**
```
ema_20 > sma_50
```

**Anlamı:**
- Kısa vadeli trend (EMA 20), uzun vadeli trendin (SMA 50) üzerinde
- BULL trend onayı

---

#### **Koşul 2: Momentum Onayı**

**Ekleme:**
```
1. "➕ LONG Koşulu Ekle" tıkla
2. İndikatör: RSI
3. Operatör: > (Büyüktür)
4. Değer: 50
```

**Koşul:**
```
rsi_14 > 50
```

**Anlamı:**
- RSI 50'nin üzerinde → Pozitif momentum
- Alıcılar satıcılardan güçlü

---

#### **Koşul 3: MACD Kesişimi**

**Ekleme:**
```
1. "➕ LONG Koşulu Ekle" tıkla
2. İndikatör: MACD
3. Operatör: crosses_over (Üstten Keser)
4. Karşılaştırma: Signal
```

**Koşul:**
```
macd_line crosses_over signal_line
```

**Anlamı:**
- MACD, signal çizgisini yukarı kesiyor
- Momentum değişimi (bear → bull)

---

#### **Koşul 4: Hacim Onayı (Confluence)**

**Ekleme:**
```
1. "➕ LONG Koşulu Ekle" tıkla
2. İndikatör: Koncorde
3. Operatör: > (Büyüktür)
4. Değer: 0
```

**Koşul:**
```
koncorde > 0
```

**Anlamı:**
- Hacim artışı → Trend güçlü
- False sinyal filtresi

---

#### **LONG Mantığı (AND)**

**Tüm Koşullar:**
```python
# Strateji JSON
"long_conditions": [
    {"indicator": "EMA", "params": {"period": 20}, "operator": ">", "target": "SMA", "target_params": {"period": 50}},
    {"indicator": "RSI", "params": {"period": 14}, "operator": ">", "value": 50},
    {"indicator": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "crosses_over", "target": "Signal"},
    {"indicator": "Koncorde", "params": {"period": 14}, "operator": ">", "value": 0}
],
"long_logic": "AND"
```

**Mantık:**
```
LONG = (ema_20 > sma_50) 
    AND (rsi_14 > 50) 
    AND (macd crosses_over signal) 
    AND (koncorde > 0)
```

**Anlamı:**
- **AND:** TÜM koşullar aynı anda sağlanmalı
- Yüksek doğruluk (daha az sinyal, daha kaliteli)

---

### **2.2: SHORT Koşulları**

**Panel:** `ORTA PANEL → 🔴 SHORT Koşulları`

**Mantık Seçici:** `VE (AND)` seçili

---

#### **Koşul 1: Trend Filtresi**

**Koşul:**
```
ema_20 < sma_50
```

**Anlamı:**
- Kısa vadeli trend, uzun vadeli trendin altında
- BEAR trend onayı

---

#### **Koşul 2: Momentum Onayı**

**Koşul:**
```
rsi_14 < 50
```

**Anlamı:**
- RSI 50'nin altında → Negatif momentum
- Satıcılar alıcılardan güçlü

---

#### **Koşul 3: MACD Kesişimi**

**Koşul:**
```
macd_line crosses_under signal_line
```

**Anlamı:**
- MACD, signal çizgisini aşağı kesiyor
- Momentum değişimi (bull → bear)

---

#### **Koşul 4: Hacim Onayı**

**Koşul:**
```
koncorde < 0
```

**Anlamı:**
- Hacim artışı (düşüş yönünde)
- False sinyal filtresi

---

#### **SHORT Mantığı (AND)**

**Tüm Koşullar:**
```python
# Strateji JSON
"short_conditions": [
    {"indicator": "EMA", "params": {"period": 20}, "operator": "<", "target": "SMA", "target_params": {"period": 50}},
    {"indicator": "RSI", "params": {"period": 14}, "operator": "<", "value": 50},
    {"indicator": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}, "operator": "crosses_under", "target": "Signal"},
    {"indicator": "Koncorde", "params": {"period": 14}, "operator": "<", "value": 0}
],
"short_logic": "AND"
```

**Mantık:**
```
SHORT = (ema_20 < sma_50) 
     AND (rsi_14 < 50) 
     AND (macd crosses_under signal) 
     AND (koncorde < 0)
```

---

### **2.3: Mantıksal Operatörler**

#### **VE (AND)**

**Doğruluk Tablosu:**
| Koşul 1 | Koşul 2 | Sonuç |
|---------|---------|-------|
| TRUE | TRUE | TRUE ✅ |
| TRUE | FALSE | FALSE ❌ |
| FALSE | TRUE | FALSE ❌ |
| FALSE | FALSE | FALSE ❌ |

**Kullanım:**
- Yüksek doğruluk
- Daha az sinyal
- Daha güçlü confluence

---

#### **VEYA (OR)**

**Doğruluk Tablosu:**
| Koşul 1 | Koşul 2 | Sonuç |
|---------|---------|-------|
| TRUE | TRUE | TRUE ✅ |
| TRUE | FALSE | TRUE ✅ |
| FALSE | TRUE | TRUE ✅ |
| FALSE | FALSE | FALSE ❌ |

**Kullanım:**
- Daha fazla sinyal
- Daha düşük doğruluk
- Esnek koşullar

---

### **2.4: Strateji Meta Bilgileri**

**Strateji Adı:**
```
ORTA PANEL → Strateji Adı: "EMA_RSI_MACD_Confluence"
```

**Açıklama:**
```
ORTA PANEL → Açıklama: 
"Trend (EMA), Momentum (RSI, MACD) ve Hacim (Koncorde) 
confluence stratejisi. Tüm koşullar aynı anda sağlanınca 
işlem açılır."
```

---

## 🛡️ ADIM 3: Risk Parametrelerinin Tanımlanması

**Süre:** 5-10 dakika
**Amaç:** Dinamik ATR Trailing Stop ve Take Profit hedeflerini belirlemek

---

### **3.1: Backtest Parametreleri**

**Panel:** `SAĞ PANEL → 🎯 Backtest & Risk`

**Ayarlar:**
```
┌─────────────────────────────────────┐
│ 🎯 Backtest Parametreleri           │
├─────────────────────────────────────┤
│ Sembol: BTC/USDT                    │
│ Timeframe: 1h                       │
│ Gün: 30                             │
│ Bakiye: $10,000                     │
└─────────────────────────────────────┘
```

---

### **3.2: ATR Trailing Stop**

#### **SL (Stop Loss) Çarpanı**

**Input:**
- **ID:** `#stop-loss-atr`
- **Varsayılan:** `2.0`
- **Min/Max:** `0.1 - 10.0`

**Hesaplama:**
```python
# core/trading/position_manager.py
def calculate_stop_loss(entry_price, direction, atr, multiplier):
    if direction == "LONG":
        stop_loss = entry_price - (atr * multiplier)
    else:  # SHORT
        stop_loss = entry_price + (atr * multiplier)
    return stop_loss
```

**Örnek:**
```
Giriş: $50,000 (LONG)
ATR: $500
Multiplier: 2.0

Stop Loss = 50,000 - (500 × 2.0) = $49,000
```

**Trailing Stop Mantığı:**
```python
# core/trading/position_manager.py
def update_trailing_stop(position, current_price, atr, multiplier):
    if position.direction == "LONG":
        new_stop = current_price - (atr * multiplier)
        
        # RATCHET: Sadece yukarı hareket
        if new_stop > position.stop_loss:
            position.stop_loss = new_stop
            # Aşağı hareket yok (ratchet prensibi)
    
    else:  # SHORT
        new_stop = current_price + (atr * multiplier)
        
        # RATCHET: Sadece aşağı hareket
        if new_stop < position.stop_loss:
            position.stop_loss = new_stop
```

**Örnek (LONG):**
```
Giriş: $50,000
İlk Stop: $49,000 (ATR: 500 × 2.0)

Fiyat ↑ $51,000
Yeni Stop: $50,000 (51,000 - 1,000)
→ Stop YUKARI taşındı ✅

Fiyat ↓ $50,500
Yeni Stop: $49,500 (50,500 - 1,000)
→ Stop AŞAĞI taşınamaz (ratchet) ❌
→ Mevcut Stop: $50,000 (korunur)
```

---

#### **TP (Take Profit) Çarpanı**

**Input:**
- **ID:** `#take-profit-atr`
- **Varsayılan:** `4.0`
- **Min/Max:** `0.1 - 20.0`

**Hesaplama:**
```python
def calculate_take_profit(entry_price, direction, atr, multiplier):
    if direction == "LONG":
        take_profit = entry_price + (atr * multiplier)
    else:  # SHORT
        take_profit = entry_price - (atr * multiplier)
    return take_profit
```

**Örnek:**
```
Giriş: $50,000 (LONG)
ATR: $500
Multiplier: 4.0

Take Profit = 50,000 + (500 × 4.0) = $52,000
```

---

### **3.3: Risk/Reward Oranı**

**Formül:**
```
Risk/Reward = TP Çarpanı / SL Çarpanı
```

**Örnek:**
```
SL Çarpanı: 2.0
TP Çarpanı: 4.0

Risk/Reward = 4.0 / 2.0 = 2.0
```

**Yorumlama:**
- **≥ 2.0:** İyi (1 birim risk, 2 birim reward)
- **≥ 3.0:** Çok iyi
- **< 1.5:** Kötü (risk > reward)

---

### **3.4: Maksimum Risk (%)**

**Input:**
- **ID:** `#max-risk-percent`
- **Varsayılan:** `2.0`
- **Min/Max:** `0.1 - 10.0`

**Pozisyon Boyutu Formülü:**
```python
# core/risk/risk_engine.py
def calculate_position_size(balance, entry, stop, risk_percentage):
    risk_amount = balance * (risk_percentage / 100)
    price_distance = abs(entry - stop)
    size = risk_amount / price_distance
    return size
```

**Örnek:**
```
Bakiye: $10,000
Risk: %2 → $200
Giriş: $50,000
Stop: $49,000 (mesafe: $1,000)

Pozisyon Boyutu = $200 / $1,000 = 0.2 BTC
```

---

### **3.5: Risk Parametre Özeti**

```
┌─────────────────────────────────────┐
│ 🛡️ Risk Parametreleri               │
├─────────────────────────────────────┤
│ SL (ATR): 2.0                       │
│ TP (ATR): 4.0                       │
│ Risk/Reward: 2.0                    │
│ Max Risk: %2                        │
│ Max Risk Amount: $200               │
└─────────────────────────────────────┘
```

---

## 📈 ADIM 4: Simülasyon ve Optimizasyon

**Süre:** 10-15 dakika
**Amaç:** Walk-Forward backtest çalıştırıp metrikleri yorumlamak

---

### **4.1: Backtest Başlat**

**Buton:** `SAĞ PANEL → 🧪 Backtest Başlat`

**API Request:**
```http
POST /api/v1/backtest/test
Content-Type: application/json

{
    "strategy": {
        "name": "EMA_RSI_MACD_Confluence",
        "long_conditions": [...],
        "short_conditions": [...],
        "long_logic": "AND",
        "short_logic": "AND"
    },
    "params": {
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "days": 30,
        "initial_balance": 10000,
        "stop_loss_atr": 2.0,
        "take_profit_atr": 4.0,
        "max_risk_percent": 2.0
    }
}
```

---

### **4.2: Backtest Sonuçları**

**Panel:** `SAĞ PANEL → 📊 SONUÇLAR`

#### **Metrik Kutuları**

| Metrik | ID | Değer | Yorum |
|--------|----|-------|-------|
| **Win Rate** | `#metric-winrate` | `65%` | 100 işlemden 65'i kar |
| **Net PnL** | `#metric-pnl` | `+$2,345` | Toplam kar |
| **Profit Factor** | `#metric-profit-factor` | `2.1` | Brüt Kar / Brüt Zarar |
| **Max DD** | `#metric-drawdown` | `-8.5%` | Tepe'den çukura |

---

#### **Win Rate**

**Formül:**
```
Win Rate = (Kazanan İşlemler / Toplam İşlem) × 100
```

**Yorumlama:**
- **≥ 60%:** Çok iyi
- **50-60%:** İyi
- **40-50%:** Orta
- **< 40%:** Kötü (strateji gözden geçir)

**Örnek:**
```
Kazanan: 65 işlem
Kaybeden: 35 işlem
Toplam: 100 işlem

Win Rate = (65 / 100) × 100 = 65% ✅
```

---

#### **Net PnL**

**Formül:**
```
Net PnL = Σ(Kar) + Σ(Zarar)
```

**Örnek:**
```
Brüt Kar: +$5,000
Brüt Zarar: -$2,655

Net PnL = 5,000 - 2,655 = +$2,345 ✅
```

---

#### **Profit Factor**

**Formül:**
```
Profit Factor = Brüt Kar / |Brüt Zarar|
```

**Yorumlama:**
- **≥ 2.0:** Çok iyi
- **1.5-2.0:** İyi
- **1.0-1.5:** Orta
- **< 1.0:** Kötü (zarardasın)

**Örnek:**
```
Brüt Kar: $5,000
Brüt Zarar: -$2,655

Profit Factor = 5,000 / 2,655 = 1.88 ✅ (İyi)
```

---

#### **Max Drawdown**

**Formül:**
```
Max DD = (Tepe Bakiye - Çukur Bakiye) / Tepe Bakiye
```

**Yorumlama:**
- **≤ 10%:** Düşük risk
- **10-20%:** Orta risk
- **≥ 20%:** Yüksek risk (risk azalt)

**Örnek:**
```
Tepe Bakiye: $12,500
Çukur Bakiye: $11,437

Max DD = (12,500 - 11,437) / 12,500 = 0.085 = 8.5% ✅
```

---

### **4.3: Equity Curve Grafiği**

**ID:** `#equity-curve-chart`

**Yorumlama:**
```
📈 Yukarı trend: Strateji karlı
📉 Aşağı trend: Strateji zararda
〰️ Yatay: Strateji nötr (komisyonlar karlılığı yiyor)
```

**İdeal Eğri:**
```
Bakiye
  │
  │    ╱─╲
  │   ╱   ╲──╲
  │  ╱       ╲──╲
  │ ╱           ╲──╲
  │╱               ╲──╲
  └───────────────────── Zaman
```

**Sorunlu Eğriler:**
```
Aşırı Volatil:          Düşüş Trendi:
  │                        │
  │  ╱╲╱╲╱╲                │╲
  │ ╱    ╲                 │ ╲
  │╱      ╲                │  ╲
  └─────────                │   ╲
                           └─────
```

---

### **4.4: Walk-Forward Optimizasyon (WFO)**

**Amaç:** Strateji parametrelerini otomatik optimize etmek

**WFO Döngüsü:**
```
┌─────────────────────────────────────────────────────────┐
│ Walk-Forward Optimization                               │
├─────────────────────────────────────────────────────────┤
│ In-Sample (Eğitim) → Optimize → Out-of-Sample (Test)   │
├─────────────────────────────────────────────────────────┤
│ [Oca 1 - Oca 30] → [Parametreler] → [Oca 31 - Şub 6]   │
│ [Oca 8 - Şub 6] → [Parametreler] → [Şub 7 - Şub 13]    │
│ [Oca 15 - Şub 13] → [Parametreler] → [Şub 14 - Şub 20] │
└─────────────────────────────────────────────────────────┘
```

**Optimize Edilen Parametreler:**
```json
{
    "ema_period": {"min": 10, "max": 50, "step": 5},
    "rsi_period": {"min": 7, "max": 21, "step": 2},
    "rsi_overbought": {"min": 60, "max": 80, "step": 5},
    "rsi_oversold": {"min": 20, "max": 40, "step": 5},
    "sl_atr_multiplier": {"min": 1.0, "max": 3.0, "step": 0.5},
    "tp_atr_multiplier": {"min": 2.0, "max": 6.0, "step": 0.5}
}
```

**WFO Sonuçları:**
```
┌─────────────────────────────────────┐
│ 🔄 WFO Optimizasyon Sonuçları       │
├─────────────────────────────────────┤
│ En İyi Parametreler:                │
│   EMA Period: 25                    │
│   RSI Period: 12                    │
│   RSI Overbought: 75                │
│   RSI Oversold: 25                  │
│   SL ATR: 2.5                       │
│   TP ATR: 5.0                       │
│                                     │
│ OOS Performansı:                    │
│   Win Rate: 62%                     │
│   Profit Factor: 1.95               │
│   Max DD: 9.2%                      │
└─────────────────────────────────────┘
```

---

### **4.5: Sharpe Ratio**

**Formül:**
```
Sharpe Ratio = (Rp - Rf) / σp

Rp = Portföy getirisi
Rf = Risksiz getiri (örn: %5 yıllık)
σp = Portföy volatilitesi (standart sapma)
```

**Yorumlama:**
- **≥ 2.0:** Çok iyi
- **1.0-2.0:** İyi
- **0.5-1.0:** Orta
- **< 0.5:** Kötü

**Örnek:**
```
Portföy Getirisi (Rp): %30 (yıllık)
Risksiz Getiri (Rf): %5 (yıllık)
Volatilite (σp): %15

Sharpe Ratio = (30 - 5) / 15 = 1.67 ✅ (İyi)
```

---

### **4.6: Strateji Kaydetme**

**Buton:** `SAĞ PANEL → 💾 Stratejiyi Kaydet`

**API Request:**
```http
POST /api/v1/strategy/save
Content-Type: application/json

{
    "name": "EMA_RSI_MACD_Confluence",
    "description": "Trend, Momentum ve Hacim confluence stratejisi",
    "version": "1.0",
    "timeframe": "1h",
    "long_conditions": [...],
    "short_conditions": [...],
    "long_logic": "AND",
    "short_logic": "AND",
    "stop_loss_atr": 2.0,
    "take_profit_atr": 4.0,
    "max_risk_percent": 2.0
}
```

**Response:**
```json
{
    "status": "success",
    "strategy_id": "ema_rsi_macd_confluence",
    "file_path": "strategy/custom/ema_rsi_macd_confluence.py",
    "message": "Strateji kaydedildi: EMA_RSI_MACD_Confluence"
}
```

---

## 🚨 Troubleshooting 101

### **Senaryo 1: Backtest Çalışmıyor**

**Semptom:** "❌ Backtest hatası: Yetersiz veri"

**Çözüm:**
```bash
# 1. Veri miktarını kontrol et
python check_db.py --symbol BTC/USDT --timeframe 1h

# 2. Yetersizse (≤ 1000 mum) daha fazla veri indir
# Veri Laboratuvarı → Gün sayısı: 7 → 30

# 3. Timeframe'i düşür (1h → 15m)
# Daha fazla veri noktası olur
```

---

### **Senaryo 2: Win Rate Düşük (<40%)**

**Semptom:** Backtest sonuçları kötü

**Çözüm:**
```
1. Koşulları sıkılaştır:
   - AND yerine daha fazla koşul ekle
   - OR kullanıyorsan AND'ye çevir

2. Filtre ekle:
   - HTF (Multi-Timeframe) onayı
   - ML Confidence ≥ 65%
   - Hacim (Koncorde) onayı

3. Risk parametrelerini optimize et:
   - SL çarpanı: 2.0 → 2.5 (daha geniş stop)
   - TP çarpanı: 4.0 → 5.0 (daha yüksek hedef)
```

---

### **Senaryo 3: Max Drawdown Yüksek (>20%)**

**Semptom:** Büyük bakiye düşüşleri

**Çözüm:**
```
1. Risk azalt:
   - Max Risk: %2 → %1
   - Max Pozisyon: 5 → 3

2. Trailing Stop ekle:
   - ATR çarpanı: 2.0 → 1.5 (daha sıkı)
   - Trailing stop aktif et

3. Koşulları iyileştir:
   - False sinyalleri filtrele
   - Confluence artır (daha fazla koşul)
```

---

### **Senaryo 4: Profit Factor < 1.0**

**Semptom:** Strateji zararda

**Çözüm:**
```
1. Risk/Reward oranını artır:
   - SL çarpanı: 2.0 → 1.5 (daha dar stop)
   - TP çarpanı: 4.0 → 6.0 (daha yüksek hedef)
   - Hedef: R/R ≥ 2.0

2. Win rate'i artır:
   - Koşulları sıkılaştır
   - Filtre ekle (HTF, ML, Hacim)

3. Komisyonları gözden geçir:
   - Yüksek frekanslı trading azalt
   - Timeframe'i yükselt (15m → 1h)
```

---

## ✅ Kontrol Listesi (Checklist)

### **İndikatör Seçimi**
- [ ] EMA (20) eklendi
- [ ] SMA (50) eklendi
- [ ] RSI (14) eklendi
- [ ] MACD (12,26,9) eklendi
- [ ] Koncorde (14) eklendi

### **Mantıksal Kapılar**
- [ ] LONG koşulları tanımlandı (4 koşul)
- [ ] SHORT koşulları tanımlandı (4 koşul)
- [ ] LONG Logic: AND
- [ ] SHORT Logic: AND
- [ ] Strateji adı girildi

### **Risk Parametreleri**
- [ ] SL (ATR): 2.0
- [ ] TP (ATR): 4.0
- [ ] Risk/Reward: 2.0
- [ ] Max Risk: %2

### **Backtest Sonuçları**
- [ ] Win Rate: ≥ 60%
- [ ] Net PnL: Pozitif
- [ ] Profit Factor: ≥ 1.5
- [ ] Max DD: ≤ 15%
- [ ] Sharpe Ratio: ≥ 1.0

### **Kaydetme**
- [ ] Strateji kaydedildi
- [ ] Dosya yolu: `strategy/custom/`
- [ ] Backtest sonuçları export edildi

---

## 📚 İlgili Dokümanlar

- **Strateji Oluşturucu:** `ui_reference/strategy_builder.md`
- **No-Code Strategy Builder:** `features/no_code_strategy_builder.md`
- **ATR Trailing Stop:** `features/ATR_TRAILING_STOP_SYSTEM.md`
- **Walk-Forward Optimization:** `features/walk_forward_optimization.md`
- **Confluence:** `strategies/confluence.md`

---

*Bu rehber CryptoAlgoBot v4.0 (Mart 2026) için hazırlanmıştır.*
*Güncellemeler için `knowledge/workflows/` dizinini kontrol edin.*
