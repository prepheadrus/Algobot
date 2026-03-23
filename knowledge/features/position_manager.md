# 📊 Position Manager

**Son Güncelleme:** Mart 2026  
**Durum:** ✅ Production Ready  
**Kategori:** Trading Engine

---

## 🎯 Genel Bakış

**Position Manager**, pozisyon lifecycle yönetimini sorumludur:
- Pozisyon açma
- Pozisyon kapatma
- Trailing stop güncelleme
- PnL hesaplama
- Likidasyon kontrolü

**Dosya:** `core/trading/position_manager.py`

---

## 🏗️ Mimari

```
┌─────────────────────────────────────────────────────────┐
│              PositionManager                            │
├─────────────────────────────────────────────────────────┤
│ - positions: Dict[str, Position]                        │
│ - legacy_positions: List[Dict]                          │
│ - trade_history: TradeHistory                           │
├─────────────────────────────────────────────────────────┤
│ + open_position(...)                                    │
│ + close_position(...)                                   │
│ + update_trailing_stop(...)                             │
│ + get_unrealized_pnl(...)                               │
│ + check_liquidation(...)                                │
│ + check_exit_condition(...)                             │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 Kullanım

### **1. PositionManager Oluştur**

```python
from core.trading.position_manager import PositionManager

pm = PositionManager(
    fee_rate_spot=0.001,
    fee_rate_futures=0.0004
)
```

---

### **2. Pozisyon Aç**

```python
position = pm.open_position(
    bot_id="bot_123",
    symbol="BTC/USDT",
    direction="LONG",
    entry_price=50000.0,
    size=0.1,
    leverage=5.0,
    stop_loss=49000.0,
    take_profit=52000.0,
    atr=500.0,
    atr_multiplier=3.0,
    strategy_name="TrendMaster Pro",
    timeframe="1m"
)
```

**Parametreler:**
- `bot_id`: Benzersiz bot ID
- `symbol`: Sembol (örn: BTC/USDT)
- `direction`: Yön (LONG/SHORT)
- `entry_price`: Giriş fiyatı
- `size`: Pozisyon boyutu (coin miktarı)
- `leverage`: Kaldıraç
- `stop_loss`: Stop loss fiyatı
- `take_profit`: Take profit fiyatı
- `atr`: ATR değeri (trailing stop için)
- `atr_multiplier`: ATR çarpanı
- `strategy_name`: Strateji adı
- `timeframe`: Timeframe

---

### **3. Trailing Stop Güncelle**

```python
# Immutable update (yeni instance döner)
position = pm.update_trailing_stop(
    position=position,
    current_high=51000.0,
    current_low=50500.0
)
```

**LONG için:**
- Yeni zirve kontrolü
- Zirveden (ATR × Çarpan) çıkar
- Sadece yukarı taşı

**SHORT için:**
- Yeni dip kontrolü
- Dipten (ATR × Çarpan) ekle
- Sadece aşağı taşı

---

### **4. Pozisyon Kapat**

```python
trade = await pm.close_position(
    bot_id="bot_123",
    exit_price=51000.0,
    reason="take_profit"
)
```

**Returns:**
- `Trade` object (kayıt için)

---

### **5. PnL Hesapla**

```python
# Unrealized PnL
pnl = pm.get_unrealized_pnl(position, current_price=51000.0)

# Legacy dict için
pnl_percent, pnl_usd = pm.get_unrealized_pnl_legacy(pos, current_price)
```

---

### **6. Likidasyon Kontrolü**

```python
if pm.check_liquidation(position, current_price=48000.0):
    logger.critical("🚨 LIKIDASYON!")
    await pm.close_position(bot_id, exit_price=48000.0, reason="liquidation")
```

---

## 📊 Özellikler

### **1. Position Value Object Kullanımı**

```python
from core.trading.entities import Position, PositionDirection

# Immutable position
position = Position(
    bot_id="bot_123",
    symbol="BTC/USDT",
    direction=PositionDirection.LONG,
    entry_price=50000.0,
    size=0.1,
    leverage=5.0
)
```

**Avantajlar:**
- ✅ Thread-safe
- ✅ Predictable state
- ✅ Easy debugging

---

### **2. Legacy Uyumluluk**

```python
# Legacy dict listesi (core/paper.py uyumluluğu)
legacy_positions = pm.legacy_positions

# Her dict, eski core/paper.py formatında
for pos in legacy_positions:
    print(f"Symbol: {pos['symbol']}, PnL: {pos['unrealized_usd']}")
```

---

### **3. Double-Close Kilidi**

```python
# Position metadata
position.metadata['is_closing'] = True

# İkinci kapatma çağrısı engellenir
if position.metadata.get('is_closing', False):
    return None
```

---

### **4. Slipaj ve Komisyon Simülasyonu**

```python
# Slipaj (LONG için %0.01 yukarıdan al)
execution_price = entry_price * 1.0001

# Komisyon
fee = position_value * fee_rate
```

---

## 🧪 Test Örnekleri

### **Pozisyon Açma Testi:**

```python
def test_open_position():
    pm = PositionManager()
    
    position = pm.open_position(
        bot_id="bot_123",
        symbol="BTC/USDT",
        direction="LONG",
        entry_price=50000.0,
        size=0.1,
        leverage=5.0,
        stop_loss=49000.0
    )
    
    assert position is not None
    assert position.direction == PositionDirection.LONG
    assert position.entry_price == 50000.0
```

---

### **Trailing Stop Testi:**

```python
def test_trailing_stop():
    pm = PositionManager()
    
    position = pm.open_position(...)
    
    # Fiyat yükseldi
    position = pm.update_trailing_stop(
        position,
        current_high=51000.0,
        current_low=50500.0
    )
    
    # Stop loss yukarı taşındı mı?
    assert position.stop_loss > 49000.0
```

---

### **PnL Hesaplama Testi:**

```python
def test_pnl_calculation():
    pm = PositionManager()
    
    position = pm.open_position(
        bot_id="bot_123",
        symbol="BTC/USDT",
        direction="LONG",
        entry_price=50000.0,
        size=0.1
    )
    
    pnl = pm.get_unrealized_pnl(position, current_price=51000.0)
    assert pnl == 100.0  # (51000 - 50000) * 0.1
```

---

## 🚨 Sorun Giderme

### **Sorun 1: Pozisyon Açılamıyor**

**Sebep:** Validation hatası

**Çözüm:**
```python
# Validation kontrolü
if entry_price <= 0:
    raise ValueError("entry_price pozitif olmalı")

if size <= 0:
    raise ValueError("size pozitif olmalı")
```

---

### **Sorun 2: Trailing Stop Güncellenmiyor**

**Sebep:** Immutable pattern - yeni instance döner

**Çözüm:**
```python
# ❌ YANLIŞ
pm.update_trailing_stop(position, ...)  # Return value kullanılmıyor

# ✅ DOĞRU
position = pm.update_trailing_stop(position, ...)  # Yeni instance al
```

---

### **Sorun 3: Double-Close Hatası**

**Sebep:** Pozisyon zaten kapanıyor

**Çözüm:**
```python
# is_closing kontrolü
if position.metadata.get('is_closing', False):
    logger.warning("Pozisyon zaten kapanıyor")
    return None
```

---

## 📚 İlgili Dokümanlar

- **Value Objects:** `architecture/value_objects.md`
- **Risk Engine:** `features/risk_engine.md`
- **Event-Driven Architecture:** `architecture/event_driven_architecture.md`

---

*Bu doküman Position Manager'ın Mart 2026 versiyonunu açıklar.*  
*Güncellemeler için `core/trading/position_manager.py` dosyasını kontrol edin.*
