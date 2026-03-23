# ⚠️ Risk Engine

**Version:** v4.0 (Production-Ready)
**Last Update:** March 2026
**Status:** ✅ Production Ready (Risk Engine E2E Tests Passed)
**Category:** Risk Management / Trading Engine

---

## 🎯 Overview

**Risk Engine** is the core risk management and calculation module responsible for:
- Position sizing (risk-based)
- Dynamic leverage calculation
- Stop loss / take profit computation
- Risk limit validation
- Kill switch management

**File:** `core/risk/risk_engine.py`

**Key Features:**
- ✅ **Position Sizing Formula:** `(Balance × Risk%) / |Entry - Stop|`
- ✅ **Dynamic Leverage:** ML confidence-based (1x-10x)
- ✅ **Timeframe-Aware Leverage:** Noise-adjusted limits for low timeframes
- ✅ **ATR-Based Stops:** Volatility-adjusted stop loss / take profit
- ✅ **Kill Switch:** Consecutive loss + daily loss protection
- ✅ **Margin Limits:** Per-position and free margin constraints

---

## 🎯 Genel Bakış

**Risk Engine**, risk yönetimi ve hesaplama motorudur:
- Pozisyon boyutu hesaplama
- Dinamik kaldıraç hesaplama
- Stop loss / take profit hesaplama
- Risk limiti kontrolü
- Kill switch yönetimi

**Dosya:** `core/risk/risk_engine.py`

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                 RiskEngine                              │
├─────────────────────────────────────────────────────────┤
│ - config: RiskConfig                                    │
│ - consecutive_losses: int                               │
│ - daily_pnl: float                                      │
│ - kill_switch_active: bool                              │
├─────────────────────────────────────────────────────────┤
│ + calculate_position_size(...)                          │
│   → (Balance × Risk%) / |Entry - Stop|                 │
│   → Min of: risk-based, margin-limit, free-margin      │
│                                                         │
│ + calculate_dynamic_leverage(...)                       │
│   → ML confidence-based (1x-10x)                       │
│   → Timeframe-aware (noise adjustment)                 │
│                                                         │
│ + calculate_dynamic_stops(...)                          │
│   → ATR-based (volatility-adjusted)                    │
│   → Risk/Reward ratio optimized                        │
│                                                         │
│ + check_kill_switch()                                   │
│   → Consecutive losses >= max_consecutive_losses       │
│   → Daily loss >= max_daily_loss                       │
│                                                         │
│ + can_open_position()                                   │
│   → Kill switch check                                   │
│   → Max positions check                                 │
│   → Margin suitability check                            │
└─────────────────────────────────────────────────────────┘
```

---

## 📐 Position Sizing (Mathematical Formula)

### **Core Formula:**

```
Position Size = min(
    (Balance × Risk%) / |Entry - Stop|,     # Risk-based size
    (Balance / MaxPositions × Leverage × 0.98) / Entry,  # Margin limit
    (FreeMargin × Leverage × 0.98) / Entry   # Free margin limit
)
```

**Variables:**
- `Balance`: Account balance (USDT)
- `Risk%`: Risk per trade (e.g., 1% = 0.01)
- `Entry`: Entry price
- `Stop`: Stop loss price
- `MaxPositions`: Maximum concurrent positions
- `Leverage`: Selected leverage
- `FreeMargin`: Available margin for new positions

### **Implementation:**

```python
# core/risk/risk_engine.py
def calculate_position_size(
    self,
    account_balance: float,
    entry_price: float,
    stop_loss_price: float,
    risk_percentage: Optional[float] = None,
    leverage: float = 1.0,
    free_margin: Optional[float] = None
) -> float:
    """
    Calculate position size (risk-based).

    Formula: min((Balance × Risk%) / |Entry - Stop|, (Balance × Leverage) / Entry)

    Args:
        account_balance: Account balance
        entry_price: Entry price
        stop_loss_price: Stop loss price
        risk_percentage: Risk % (None → config.max_risk_per_trade)
        leverage: Leverage (for size limitation)
        free_margin: Available margin (optional)

    Returns:
        Position size (coin amount)
    """
    # Determine risk percentage
    if risk_percentage is None:
        risk_percentage = self.config.max_risk_per_trade * 100

    # Validate risk percentage
    if risk_percentage <= 0.0 or risk_percentage > 5.0:
        risk_percentage = 1.0  # Safe fallback

    # Risk amount ($)
    risk_amount = account_balance * (risk_percentage / 100.0)

    # Price distance
    price_distance = abs(entry_price - stop_loss_price)

    if price_distance <= 0:
        return 0.0

    # 1. Risk-based size
    size_by_risk = risk_amount / price_distance

    # 2. Max capital per position (account limit)
    max_positions = getattr(self.config, 'max_open_positions', 10)
    max_positions = max(1, max_positions)
    max_margin_per_trade = account_balance / max_positions

    # Max notional by margin limit
    max_notional_by_margin = max_margin_per_trade * leverage * 0.98  # 2% buffer
    size_by_margin_limit = max_notional_by_margin / entry_price

    # 3. Free margin limit
    size_by_free_margin = float('inf')
    if free_margin is not None:
        max_notional_by_free_margin = free_margin * leverage * 0.98
        size_by_free_margin = max_notional_by_free_margin / entry_price

    # Take minimum of all three
    position_size = min(size_by_risk, size_by_margin_limit, size_by_free_margin)

    logger.debug(
        f"📏 Size Calculation | Risk: {size_by_risk:.4f}, "
        f"MarginLimit: {size_by_margin_limit:.4f}, "
        f"FreeMarginLimit: {size_by_free_margin:.4f} -> Final: {position_size:.4f}"
    )

    return position_size
```

### **Example Calculation:**

```python
# Given:
balance = 10000  # $10,000
risk = 1.0  # 1%
entry = 50000  # BTC @ $50,000
stop = 49000  # Stop @ $49,000
leverage = 5  # 5x leverage
max_positions = 5
free_margin = 8000  # $8,000 available

# Calculations:
risk_amount = 10000 * 0.01 = $100
price_distance = |50000 - 49000| = $1000

# 1. Risk-based size
size_by_risk = 100 / 1000 = 0.1 BTC

# 2. Margin limit
max_margin_per_trade = 10000 / 5 = $2000
max_notional = 2000 * 5 * 0.98 = $9800
size_by_margin = 9800 / 50000 = 0.196 BTC

# 3. Free margin limit
max_notional_free = 8000 * 5 * 0.98 = $39200
size_by_free = 39200 / 50000 = 0.784 BTC

# Final size (minimum)
position_size = min(0.1, 0.196, 0.784) = 0.1 BTC
```

---

## 📊 Dynamic Leverage

### **ML Confidence-Based Leverage:**

| ML Confidence | Recommendation | Leverage | Rationale |
|---------------|----------------|----------|-----------|
| **< 50%** | HOLD/WEAK | 1x (base) | Low confidence → minimal risk |
| **50-65%** | WEAK_LONG/WEAK_SHORT | 2-3x | Moderate confidence |
| **65-80%** | LONG/SHORT | 3-5x | High confidence |
| **> 80%** | STRONG_LONG/STRONG_SHORT | 5-10x | Very high confidence |

### **Timeframe-Aware Leverage (Noise Adjustment):**

**CRITICAL:** Low timeframes (1m, 3m) have high market noise and commission impact. Leverage is automatically limited.

```python
def calculate_dynamic_leverage(
    self,
    confidence_score: float,
    base_leverage: Optional[float] = None,
    max_leverage: Optional[float] = None,
    timeframe: str = "1h"  # NEW: Timeframe awareness
) -> float:
    """
    Calculate dynamic leverage based on confidence and timeframe.

    Args:
        confidence_score: ML confidence (0.0 - 1.0)
        base_leverage: Base leverage (default: config.default_leverage)
        max_leverage: Max leverage (default: config.max_leverage)
        timeframe: Trading timeframe (e.g., "1m", "15m", "1h")

    Returns:
        Dynamic leverage (1x - 10x)
    """
    base = base_leverage or self.config.default_leverage
    maximum = max_leverage or self.config.max_leverage

    # ============================================
    # TIMEFRAME-AWARE LEVERAGE LIMITS
    # ============================================
    timeframe_lower = timeframe.lower()

    # 1m, 3m: Very high noise - Max 5x-10x
    if timeframe_lower in ["1m", "3m"]:
        maximum = min(maximum, 10)  # Absolute max 10x
        logger.info(
            f"⚠️ [TIMEFRAME-AWARE] {timeframe} leverage limited: "
            f"Max {maximum}x (Noise + commission protection)"
        )

    # 5m, 10m, 15m: Medium noise - Max 15x-20x
    elif timeframe_lower in ["5m", "10m", "15m", "20m", "30m"]:
        maximum = min(maximum, 20)  # Absolute max 20x
        logger.debug(
            f"📊 [TIMEFRAME-AWARE] {timeframe} leverage limited: "
            f"Max {maximum}x (Medium noise)"
        )

    # 1h+: Normal high leverage allowed
    else:
        logger.debug(f"✅ [TIMEFRAME-AWARE] {timeframe} normal leverage: Max {maximum}x")

    # Low confidence → base leverage
    if confidence_score < 0.50:
        return base

    # Power curve: Leverage increases faster with confidence
    raw_ratio = (confidence_score - 0.50) / 0.50

    # Add floor ratio for initial boost (avoids starting at exactly 1x)
    if raw_ratio == 0:
        boosted_ratio = 0.05  # 5% starting boost
    else:
        boosted_ratio = 0.05 + (0.95 * (raw_ratio ** 0.7))

    calculated = base + (boosted_ratio * (maximum - base))

    # Round and clamp
    final_leverage = int(round(min(maximum, max(base, calculated))))

    logger.debug(
        f"🚀 Dynamic leverage: Confidence={confidence_score:.2%}, "
        f"Leverage={final_leverage}x (Base={base}x, Max={maximum}x, TF={timeframe})"
    )

    return float(final_leverage)
```

### **Leverage from ML Recommendation:**

```python
def calculate_leverage_from_ml_recommendation(
    self,
    ml_recommendation: str,
    max_leverage: Optional[float] = None
) -> float:
    """
    Calculate leverage from ML recommendation (core/paper.py compatible).

    Args:
        ml_recommendation: ML recommendation (STRONG_LONG, LONG, etc.)
        max_leverage: Max leverage

    Returns:
        Leverage
    """
    maximum = max_leverage or self.config.max_leverage

    if ml_recommendation in ["STRONG_LONG", "STRONG_SHORT"]:
        # High confidence (>80%): Max leverage
        leverage = min(maximum, 10)
    elif ml_recommendation in ["LONG", "SHORT"]:
        # Medium confidence (65-79%): Medium leverage
        leverage = min(maximum, 3)
    else:
        # Low confidence (<65%): Min leverage
        leverage = 1.0

    logger.debug(f"ML leverage: {ml_recommendation} -> {leverage}x")
    return leverage
```

---

### **5. Kill Switch**

```python
# Kill switch kontrolü
if engine.check_kill_switch():
    logger.critical("🚨 KILL SWITCH AKTİF!")
    return  # Trading durduruldu

# Ardışık kayıp >= 5 ise
# Veya günlük kayıp >= %5 ise
```

---

### **6. Trade Result Kaydet**

```python
# Trade sonucunu kaydet
engine.record_trade_result(pnl=-100.0)  # $100 kayıp

# Ardışık kayıp sayacı artar
# Günlük PnL güncellenir
# Kill switch kontrolü yapılır
```

---

## 📊 Özellikler

### **1. Risk Bazlı Pozisyon Boyutu**

```python
# Formül
position_size = (account_balance * risk_percentage) / |entry_price - stop_loss|

# Örnek
balance = 10000
risk = 1.0  # %1
entry = 50000
stop = 49000

size = (10000 * 0.01) / |50000 - 49000| = 100 / 1000 = 0.1 BTC
```

---

### **2. Dinamik Kaldıraç Tablosu**

| ML Confidence | Recommendation | Kaldıraç |
|---------------|----------------|----------|
| < 50% | HOLD/WEAK | 1x (base) |
| 50-65% | WEAK_LONG/WEAK_SHORT | 2-3x |
| 65-80% | LONG/SHORT | 3-5x |
| > 80% | STRONG_LONG/STRONG_SHORT | 5-10x (max) |

---

### **3. ATR Bazlı Stops**

```python
# LONG için
stop_loss = price - (ATR × multiplier)
take_profit = price + (ATR × multiplier × risk_reward_ratio)

# SHORT için
stop_loss = price + (ATR × multiplier)
take_profit = price - (ATR × multiplier × risk_reward_ratio)
```

---

## 🧪 Test Örnekleri

### **Pozisyon Boyutu Testi:**

```python
def test_position_size():
    engine = RiskEngine()
    
    size = engine.calculate_position_size(
        account_balance=10000,
        entry_price=50000,
        stop_loss_price=49000,
        risk_percentage=1.0
    )
    
    assert size == 0.1  # 100 / 1000
```

---

### **Kill Switch Testi:**

```python
def test_kill_switch():
    engine = RiskEngine()
    
    # 5 ardışık kayıp
    for i in range(5):
        engine.record_trade_result(pnl=-100.0)
    
    # Kill switch aktif olmalı
    assert engine.kill_switch_active == True
    assert engine.check_kill_switch() == True
```

---

## 🚨 Sorun Giderme

### **Sorun 1: Geçersiz Risk Limiti**

**Hata:**
```
ValueError: Geçersiz risk limiti: 10.0%. Kabul edilebilir aralık: 0-5%
```

**Çözüm:**
```python
# Risk %0-5 arası olmalı
risk_percentage = 1.0  # %1 (doğru)
risk_percentage = 10.0  # %10 (yanlış!)
```

---

### **Sorun 2: Kill Switch Aktif**

**Sebep:** Ardışık kayıp limiti aşıldı

**Çözüm:**
```python
# Manuel sıfırlama (kullanıcı onayı ile)
engine.reset_kill_switch()

# Veya günlük sıfırlama
engine.reset_daily()
```

---

## 📚 İlgili Dokümanlar

- **Position Manager:** `features/position_manager.md`
- **Bot Manager:** `features/bot_manager.md`
- **Event-Driven Architecture:** `architecture/event_driven_architecture.md`

---

*Bu doküman Risk Engine'in Mart 2026 versiyonunu açıklar.*  
*Güncellemeler için `core/risk/risk_engine.py` dosyasını kontrol edin.*
