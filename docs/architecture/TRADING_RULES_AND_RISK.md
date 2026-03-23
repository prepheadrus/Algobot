# 🛡️ TRADING RULES AND RISK PARAMETERS

**Versiyon:** v4.0 (Production-Ready)
**Son Güncelleme:** Mart 2026
**Kategori:** Kantitatif Kurallar ve Risk Yönetimi

---

## 📋 Genel Bakış

Bu doküman, CryptoAlgoBot sistemindeki **finansal koruma kalkanlarını**, **WFO overfitting denetim toleranslarını**, **dinamik ATR izleyen stop formüllerini**, **R/K (Risk/Kar) oran hedeflerini** ve **komisyon/slippage hesaplama mantığını** matematiksel denklemler halinde belge ler.

---

## 1. WFO OVERFITTING DENETİMİ

### **1.1 Dinamik Tolerans Oranları**

**Dosya:** `core/wfo_engine.py`

**Formül:**
```
overfitting_ratio = |IS_score| / |OOS_score|

Eğer overfitting_ratio > MAX_OVERFITTING_RATIO ise:
    → OVERFITTING TESPİT EDİLDİ ⚠️
```

**Tolerans Eşikleri:**

| Optimizasyon Metriği | MAX_OVERFITTING_RATIO | Maksimum Sapma | Durum |
|---------------------|----------------------|----------------|-------|
| **Sharpe Ratio** | 1.3 | %30 | ✅ AKTİF |
| **Net PnL** | 1.5 | %50 | ✅ AKTİF |

**Kod Implementasyonu:**
```python
# core/wfo_engine.py (Satır 420-432)
def _check_overfitting(
    self,
    is_score: float,
    oos_score: float,
    optimization_metric: str = 'sharpe'
) -> bool:
    # Sapma oranı hesapla
    overfitting_ratio = abs(is_score) / abs(oos_score)
    
    # Dinamik eşik
    if optimization_metric == 'sharpe':
        MAX_OVERFITTING_RATIO = 1.3  # ✅ Sharpe için %30 sapma
    else:
        MAX_OVERFITTING_RATIO = 1.5  # ✅ Net PnL için %50 sapma
    
    return overfitting_ratio > MAX_OVERFITTING_RATIO
```

**Örnek Senaryo:**
```
In-Sample Sharpe: 2.5
Out-of-Sample Sharpe: 2.0

overfitting_ratio = 2.5 / 2.0 = 1.25
MAX_OVERFITTING_RATIO (Sharpe) = 1.3

1.25 < 1.3 → ✅ OVERFITTING YOK (kabul edilebilir)
```

**Kritik Senaryo:**
```
In-Sample Sharpe: 3.5
Out-of-Sample Sharpe: 2.0

overfitting_ratio = 3.5 / 2.0 = 1.75
MAX_OVERFITTING_RATIO (Sharpe) = 1.3

1.75 > 1.3 → ❌ OVERFITTING TESPİT EDİLDİ (parametreler reddedilir)
```

---

## 2. DİNAMİK ATR İZLEYEN STOP (TRAILING STOP)

### **2.1 Ratchet Mekanizması**

**Dosya:** `core/trading/position_manager.py`

**Felsefe:**
> Trailing stop SADECE tek yönde ilerler (kar yönünde). Asla geri hareket etmez (zarar yönünde).

**Formül (LONG Pozisyon):**
```
Yeni Trailing Stop = current_price - (ATR × multiplier)

Eğer Yeni Stop > Mevcut Stop ise:
    → Stop'u YUKARI taşı ✅
Else:
    → Stop'u KORU (aşağı taşıma YOK) ❌
```

**Formül (SHORT Pozisyon):**
```
Yeni Trailing Stop = current_price + (ATR × multiplier)

Eğer Yeni Stop < Mevcut Stop ise:
    → Stop'u AŞAĞI taşı ✅
Else:
    → Stop'u KORU (yukarı taşıma YOK) ❌
```

**Kod Implementasyonu:**
```python
# core/trading/position_manager.py
def update_trailing_stop(
    self,
    bot_id: str,
    current_price: float,
    atr: float,
    atr_multiplier: float = 1.5
) -> Optional[float]:
    position = self.positions.get(bot_id)
    
    if position.direction == "LONG":
        # LONG: Trail below price
        new_trailing_stop = current_price - (atr * atr_multiplier)
        
        # RATCHET: Sadece YUKARI hareket
        if position.stop_loss and new_trailing_stop <= position.stop_loss:
            return None  # Stop aşağı taşınamaz
        
        position.stop_loss = new_trailing_stop
        
    else:  # SHORT
        # SHORT: Trail above price
        new_trailing_stop = current_price + (atr * atr_multiplier)
        
        # RATCHET: Sadece AŞAĞI hareket
        if position.stop_loss and new_trailing_stop >= position.stop_loss:
            return None  # Stop yukarı taşınamaz
        
        position.stop_loss = new_trailing_stop
    
    return position.stop_loss
```

**Örnek Senaryo (LONG):**
```
Giriş: $50,000
İlk Stop: $49,000 (ATR: $500 × 2.0)

Fiyat ↑ $51,000
Yeni Stop: $51,000 - ($500 × 2.0) = $50,000
→ Stop YUKARI taşındı ✅ ($49,000 → $50,000)

Fiyat ↓ $50,500
Yeni Stop: $50,500 - ($500 × 2.0) = $49,500
→ Stop AŞAĞI taşınamaz ❌ (Mevcut Stop: $50,000 korunur)

Fiyat ↑ $52,000
Yeni Stop: $52,000 - ($500 × 2.0) = $51,000
→ Stop YUKARI taşındı ✅ ($50,000 → $51,000)
```

---

## 3. R/K (RİSK/KAR) ORAN HEDEFLERİ

### **3.1 ATR Bazlı Hedefler**

**Dosya:** `core/risk/risk_engine.py`

**Formüller:**
```
Stop Loss (LONG) = entry_price - (ATR × sl_multiplier)
Take Profit (LONG) = entry_price + (ATR × tp_multiplier)

Risk/Reward Oranı = TP_mesafesi / SL_mesafesi
                  = (ATR × tp_multiplier) / (ATR × sl_multiplier)
                  = tp_multiplier / sl_multiplier
```

**Varsayılan Değerler:**

| Parametre | Varsayılan | Min | Max | Önerilen |
|-----------|------------|-----|-----|----------|
| **sl_multiplier** | 2.0 | 1.0 | 5.0 | 2.0-3.0 |
| **tp_multiplier** | 4.0 | 2.0 | 10.0 | 4.0-6.0 |
| **R/K Oranı** | 2.0 | 1.0 | 5.0 | 2.0-3.0 |

**Kod Implementasyonu:**
```python
# core/risk/risk_engine.py
def calculate_dynamic_stops(
    self,
    price: float,
    direction: str,
    atr: float,
    multiplier: float = 1.5,
    risk_reward_ratio: float = 2.0
) -> Tuple[float, float]:
    # Stop mesafesi
    stop_distance = atr * multiplier
    
    if direction.upper() == "LONG":
        stop_loss = price - stop_distance
        take_profit = price + (stop_distance * risk_reward_ratio)
    else:  # SHORT
        stop_loss = price + stop_distance
        take_profit = price - (stop_distance * risk_reward_ratio)
    
    return stop_loss, take_profit
```

**Örnek Senaryo:**
```
Giriş: $50,000 (LONG)
ATR: $500
sl_multiplier: 2.0
tp_multiplier: 4.0

Stop Loss = 50,000 - (500 × 2.0) = $49,000
Take Profit = 50,000 + (500 × 4.0) = $52,000

R/K Oranı = ($52,000 - $50,000) / ($50,000 - $49,000)
          = $2,000 / $1,000
          = 2.0 ✅
```

**Hedef R/K Oranları:**

| Strateji Tipi | Min R/K | Hedef R/K | Max R/K |
|---------------|---------|-----------|---------|
| **Scalping** | 1.0 | 1.5 | 2.0 |
| **Day Trading** | 1.5 | 2.0 | 3.0 |
| **Swing Trading** | 2.0 | 3.0 | 5.0 |
| **Position Trading** | 3.0 | 5.0 | 10.0 |

---

## 4. KOMİSYON VE SLIPPAGE HESAPLAMA

### **4.1 Komisyon Oranları**

**Dosya:** `core/paper.py`, `core/trading/position_manager.py`

**Komisyon Yapısı:**

| Piyasa | Maker Fee | Taker Fee | Uygulanan |
|--------|-----------|-----------|-----------|
| **Futures** | 0.02% (0.0002) | 0.04% (0.0004) | 0.04% (Taker) ✅ |
| **Spot** | 0.1% (0.001) | 0.1% (0.001) | 0.1% (Taker) ✅ |

**Kod Implementasyonu:**
```python
# core/paper.py (Satır 68-70)
def __init__(self, initial_balance=10000.0, 
             fee_rate_spot=0.001, 
             fee_rate_futures=0.0004):
    self.fee_rate_spot = fee_rate_spot      # ✅ 0.1% Spot
    self.fee_rate_futures = fee_rate_futures # ✅ 0.04% Futures
```

---

### **4.2 Slippage (Kayma) Simülasyonu**

**Slippage Oranı:**
```
SLIPPAGE = 0.0001  # %0.01 (minimum kayma)
```

**Giriş (Entry) Simülasyonu:**
```python
# LONG için
actual_entry = entry_price × (1 + SLIPPAGE)

# SHORT için
actual_entry = entry_price × (1 - SLIPPAGE)
```

**Çıkış (Exit) Simülasyonu:**
```python
# LONG için
actual_exit = exit_price × (1 - SLIPPAGE)

# SHORT için
actual_exit = exit_price × (1 + SLIPPAGE)
```

**Kod Implementasyonu:**
```python
# core/trading/position_manager.py
SLIPPAGE = 0.0001  # %0.01

def open_position(self, bot_id, symbol, direction, entry_price, ...):
    # Apply slippage (market order simulation)
    if direction == "LONG":
        # LONG: Buy higher (slippage against you)
        actual_entry_price = entry_price * (1 + self.SLIPPAGE)
    else:
        # SHORT: Sell lower (slippage against you)
        actual_entry_price = entry_price * (1 - self.SLIPPAGE)
    
    # Calculate entry fee
    entry_fee = actual_entry_price * size * self.fee_rate
```

**Örnek Senaryo (LONG):**
```
Sinyal Fiyatı: $50,000
Slippage: %0.01

Gerçek Giriş = 50,000 × (1 + 0.0001) = $50,005
→ $5 fazla ödedin (slippage maliyeti)

Giriş Komisyonu (Futures) = $50,005 × 0.0004 = $20.00
```

**Örnek Senaryo (Exit LONG):**
```
Çıkış Fiyatı: $52,000
Slippage: %0.01

Gerçek Çıkış = 52,000 × (1 - 0.0001) = $51,994.80
→ $5.20 daha az aldınız (slippage maliyeti)

Çıkış Komisyonu (Futures) = $51,994.80 × 0.0004 = $20.80
```

**Toplam İşlem Maliyeti:**
```
Giriş Slippage: $5.00
Giriş Komisyonu: $20.00
Çıkış Slippage: $5.20
Çıkış Komisyonu: $20.80
─────────────────────────
TOPLAM MALİYET: $51.00

Brüt Kar: $2,000.00
Net Kar: $2,000.00 - $51.00 = $1,949.00
```

---

## 5. POZİSYON BOYUTU HESAPLAMA

### **5.1 Risk Bazlı Formül**

**Dosya:** `core/risk/risk_engine.py`

**Ana Formül:**
```
Position Size = min(
    (Balance × Risk%) / |Entry - Stop|,           # Risk-based
    (Balance / MaxPositions × Leverage × 0.98) / Entry,  # Margin limit
    (FreeMargin × Leverage × 0.98) / Entry        # Free margin limit
)
```

**Değişkenler:**
- `Balance`: Hesap bakiyesi (USDT)
- `Risk%`: Risk yüzdesi (örn: 0.01 = %1)
- `Entry`: Giriş fiyatı
- `Stop`: Stop loss fiyatı
- `MaxPositions`: Maksimum açık pozisyon
- `Leverage`: Kaldıraç
- `FreeMargin`: Serbest marjin

**Kod Implementasyonu:**
```python
# core/risk/risk_engine.py (Satır 74-130)
def calculate_position_size(
    self,
    account_balance: float,
    entry_price: float,
    stop_loss_price: float,
    risk_percentage: float = None,
    leverage: float = 1.0,
    free_margin: float = None
) -> float:
    # Risk yüzdesini belirle
    if risk_percentage is None:
        risk_percentage = self.config.max_risk_per_trade * 100
    
    # Risk miktarı ($)
    risk_amount = account_balance * (risk_percentage / 100.0)
    
    # Fiyat mesafesi
    price_distance = abs(entry_price - stop_loss_price)
    
    if price_distance <= 0:
        return 0.0
    
    # 1. Risk bazlı boyut
    size_by_risk = risk_amount / price_distance
    
    # 2. Marjin limiti
    max_positions = getattr(self.config, 'max_open_positions', 10)
    max_margin_per_trade = account_balance / max_positions
    max_notional_by_margin = max_margin_per_trade * leverage * 0.98
    size_by_margin_limit = max_notional_by_margin / entry_price
    
    # 3. Serbest bakiye limiti
    size_by_free_margin = float('inf')
    if free_margin is not None:
        max_notional_by_free_margin = free_margin * leverage * 0.98
        size_by_free_margin = max_notional_by_free_margin / entry_price
    
    # En küçüğünü al
    position_size = min(size_by_risk, size_by_margin_limit, size_by_free_margin)
    
    return position_size
```

**Örnek Senaryo:**
```
Balance: $10,000
Risk: %1 → $100
Entry: $50,000
Stop: $49,000 (mesafe: $1,000)
Leverage: 5x
MaxPositions: 5
FreeMargin: $8,000

# 1. Risk bazlı
size_by_risk = $100 / $1,000 = 0.1 BTC

# 2. Marjin limiti
max_margin_per_trade = $10,000 / 5 = $2,000
max_notional = $2,000 × 5 × 0.98 = $9,800
size_by_margin = $9,800 / $50,000 = 0.196 BTC

# 3. Serbest bakiye limiti
max_notional_free = $8,000 × 5 × 0.98 = $39,200
size_by_free = $39,200 / $50,000 = 0.784 BTC

# Final (en katı limit)
position_size = min(0.1, 0.196, 0.784) = 0.1 BTC ✅
```

---

## 6. DİNAMİK KALDIRAÇ (ML CONFIDENCE BAZLI)

### **6.1 Confidence → Leverage Mapping**

**Dosya:** `core/risk/risk_engine.py`

**Tablo:**

| ML Confidence | Recommendation | Leverage (1h+) | Leverage (1m-3m) |
|---------------|----------------|----------------|------------------|
| **< 50%** | HOLD/WEAK | 1x (base) | 1x |
| **50-65%** | WEAK_LONG/WEAK_SHORT | 2-3x | 2-3x |
| **65-80%** | LONG/SHORT | 3-5x | 3-5x |
| **> 80%** | STRONG_LONG/STRONG_SHORT | 5-10x | 5-8x |

**Formül:**
```python
raw_ratio = (confidence - 0.50) / 0.50
boosted_ratio = 0.05 + (0.95 * (raw_ratio ** 0.7))
calculated = base + (boosted_ratio * (max_leverage - base))
final_leverage = int(round(min(max_leverage, calculated)))
```

**Kod Implementasyonu:**
```python
# core/risk/risk_engine.py (Satır 157-220)
def calculate_dynamic_leverage(
    self,
    confidence_score: float,
    base_leverage: float = None,
    max_leverage: float = None,
    timeframe: str = "1h"
) -> float:
    base = base_leverage or self.config.default_leverage
    maximum = max_leverage or self.config.max_leverage
    
    # Timeframe-aware limits
    if timeframe.lower() in ["1m", "3m"]:
        maximum = min(maximum, 10)  # Yüksek gürültü
    elif timeframe.lower() in ["5m", "15m"]:
        maximum = min(maximum, 20)  # Orta gürültü
    
    # Düşük güven → base leverage
    if confidence_score < 0.50:
        return base
    
    # Power curve
    raw_ratio = (confidence_score - 0.50) / 0.50
    boosted_ratio = 0.05 + (0.95 * (raw_ratio ** 0.7))
    calculated = base + (boosted_ratio * (maximum - base))
    
    final_leverage = int(round(min(maximum, calculated)))
    
    return float(final_leverage)
```

---

## 7. RİSK LİMİTLERİ (CONFIG)

### **7.1 Varsayılan Değerler**

**Dosya:** `config.yaml`, `core/risk/risk_engine.py`

| Parametre | Varsayılan | Min | Max | Açıklama |
|-----------|------------|-----|-----|----------|
| **max_risk_per_trade_percent** | 2.0 | 0.1 | 5.0 | İşlem başına maksimum risk (%) |
| **max_leverage** | 50 | 1 | 50 | Maksimum kaldıraç |
| **max_open_positions** | 10 | 1 | 20 | Maksimum açık pozisyon |
| **max_consecutive_losses** | 5 | 0 | 50 | Kill switch için ardışık kayıp (0=sınırsız) |
| **max_daily_loss** | 0.05 | 0.01 | 0.20 | Maksimum günlük kayıp (%5) |
| **kill_switch_enabled** | true | - | - | Kill switch aktif/pasif |

**config.yaml:**
```yaml
risk_management:
  max_risk_per_trade_percent: 2.0
  max_leverage: 50
  max_open_positions: 10
  max_consecutive_losses: 5
  kill_switch:
    enabled: true
    max_consecutive_losses: 5
```

---

## 8. ÖZET TABLOSU

| Kantitatif Kural | Formül / Değer | Durum |
|-----------------|----------------|-------|
| **WFO Overfitting (Sharpe)** | Max 1.3x (%30 sapma) | ✅ AKTİF |
| **WFO Overfitting (PnL)** | Max 1.5x (%50 sapma) | ✅ AKTİF |
| **Trailing Stop (Ratchet)** | Tek yönlü (kar yönünde) | ✅ AKTİF |
| **R/K Oranı (Varsayılan)** | 2.0 (TP: 4.0, SL: 2.0) | ✅ AKTİF |
| **Komisyon (Futures)** | 0.04% (Taker) | ✅ AKTİF |
| **Slippage** | 0.01% (Market order) | ✅ AKTİF |
| **Pozisyon Boyutu** | (Balance × Risk%) / \|Entry - Stop\| | ✅ AKTİF |
| **Dinamik Kaldıraç** | ML Confidence bazlı (1x-10x) | ✅ AKTİF |

---

**Doküman Versiyonu:** v4.0 (Mart 2026)
**Risk Yönetimi Durumu:** ✅ Production-Ready (Hedge Fund Standartları)
