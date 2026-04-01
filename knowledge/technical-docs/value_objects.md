# 📦 Value Objects (Domain-Driven Design)

**Son Güncelleme:** Mart 2026  
**Durum:** ✅ Production Ready  
**Kategori:** Mimari (Architecture)

---

## 🎯 Genel Bakış

**Value Objects (Değer Nesneleri)**, Domain-Driven Design (DDD) pattern'inde kullanılan immutable (değiştirilemez) entity'lerdir.

### **Temel Felsefe:**
> "Entity'ler ID ile tanımlanır, Value Objects ise özellikleri ile. Immutable oldukları için thread-safe ve side-effect free'dir."

---

## 🏛️ Value Object Hiyerarşisi

```
Trading Domain
├── Position (Pozisyon)
│   ├── bot_id
│   ├── symbol
│   ├── direction (LONG/SHORT)
│   ├── entry_price
│   ├── size
│   ├── leverage
│   ├── stop_loss
│   └── take_profit
│
├── Trade (İşlem)
│   ├── id
│   ├── bot_id
│   ├── symbol
│   ├── direction
│   ├── entry_price
│   ├── exit_price
│   ├── pnl
│   └── pnl_percent
│
└── Order (Emir)
    ├── id
    ├── bot_id
    ├── symbol
    ├── type (MARKET/LIMIT/STOP)
    ├── side (BUY/SELL)
    ├── status
    ├── size
    └── price
```

---

## 1️⃣ Position (Pozisyon)

**Dosya:** `core/trading/entities/position.py`

### **Özellikler:**
- ✅ Immutable (frozen dataclass)
- ✅ PnL hesaplama
- ✅ Trailing stop desteği
- ✅ Serialization (dict/JSON)

### **Kullanım:**

```python
from core.trading.entities import Position, PositionDirection

# Position oluştur
position = Position(
    bot_id="bot_123",
    symbol="BTC/USDT",
    direction=PositionDirection.LONG,
    entry_price=50000.0,
    size=0.1,
    leverage=5.0,
    stop_loss=49000.0,
    take_profit=52000.0
)

# Unrealized PnL hesapla
current_price = 51000.0
pnl = position.unrealized_pnl(current_price)
pnl_percent = position.unrealized_pnl_percent(current_price)

# Trailing stop güncelle (immutable - yeni instance döner)
position = position.update_stop_loss(49500.0)

# Pozisyon kapat
trade = position.close(exit_price=51000.0, reason="take_profit")
```

### **PnL Hesaplama:**

```python
# LONG için
pnl = (current_price - entry_price) * size

# SHORT için
pnl = (entry_price - current_price) * size
```

### **Trailing Stop (Immutable):**

```python
# LONG için trailing stop
def update_stop_loss(self, new_stop: float) -> 'Position':
    # LONG için stop loss sadece yukarı hareket eder
    if self.direction == PositionDirection.LONG:
        if self.stop_loss is not None and new_stop <= self.stop_loss:
            return self  # Değişiklik yok
    
    # Yeni instance oluştur (immutable)
    return dataclasses.replace(self, stop_loss=new_stop)
```

---

## 2️⃣ Trade (İşlem)

**Dosya:** `core/trading/entities/trade.py`

### **Özellikler:**
- ✅ Immutable (frozen dataclass)
- ✅ Trade result (WIN/LOSS/BREAKEVEN)
- ✅ Duration hesaplama
- ✅ Performance metrics

### **Kullanım:**

```python
from core.trading.entities import Trade, TradeResult

# Trade oluştur (Position.close() metodundan)
trade = Trade(
    id="trade_123",
    bot_id="bot_123",
    symbol="BTC/USDT",
    direction=PositionDirection.LONG,
    entry_price=50000.0,
    exit_price=51000.0,
    size=0.1,
    leverage=5.0,
    pnl=100.0,
    pnl_percent=0.10,
    opened_at=datetime.utcnow(),
    closed_at=datetime.utcnow(),
    reason="take_profit"
)

# Trade result
result = trade.result  # TradeResult.WIN

# Duration
duration = trade.duration_minutes

# Performance metrics
roi = trade.return_on_margin_percent
```

### **Trade Result:**

```python
@property
def result(self) -> TradeResult:
    if abs(self.pnl) < 0.01:  # Başa baş
        return TradeResult.BREAKEVEN
    elif self.pnl > 0:
        return TradeResult.WIN
    else:
        return TradeResult.LOSS
```

---

## 3️⃣ Order (Emir)

**Dosya:** `core/trading/entities/order.py`

### **Özellikler:**
- ✅ Immutable (frozen dataclass)
- ✅ Order lifecycle (pending -> open -> filled/cancelled)
- ✅ Order type support (market, limit, stop, vb.)
- ✅ Factory methods

### **Kullanım:**

```python
from core.trading.entities import Order, OrderType, OrderSide, OrderStatus

from core.trading.entities.order_params import MarketOrderParams, LimitOrderParams, StopLossOrderParams

# Market order oluştur
order = Order.create_market_order(MarketOrderParams(
    bot_id="bot_123",
    symbol="BTC/USDT",
    side=OrderSide.BUY,
    size=0.1,
    leverage=5.0
))

# Limit order oluştur
order = Order.create_limit_order(LimitOrderParams(
    bot_id="bot_123",
    symbol="BTC/USDT",
    side=OrderSide.BUY,
    size=0.1,
    price=49000.0,
    leverage=5.0
))

# Stop loss order oluştur
order = Order.create_stop_loss_order(StopLossOrderParams(
    bot_id="bot_123",
    symbol="BTC/USDT",
    side=OrderSide.SELL,
    size=0.1,
    stop_price=49000.0,
    leverage=5.0
))

# Order status güncelle (immutable)
order = order.with_status(OrderStatus.FILLED, filled_price=49500.0)
```

### **Order Lifecycle:**

```
PENDING → OPEN → FILLED
              ↓
         CANCELLED
              ↓
         REJECTED
```

---

## 📊 Value Object Pattern'leri

### **1. Immutable (Değiştirilemez)**

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Position:
    bot_id: str
    symbol: str
    direction: PositionDirection
    entry_price: float
    # ...
```

**Avantajlar:**
- ✅ Thread-safe
- ✅ Side-effect free
- ✅ Predictable state
- ✅ Easy debugging

---

### **2. Factory Methods**

```python
@classmethod
def create_market_order(cls, params: MarketOrderParams):
    """Market order oluştur"""
    return cls(
        id=f"order_{uuid4().hex[:12]}",
        bot_id=params.bot_id,
        symbol=params.symbol,
        type=OrderType.MARKET,
        side=params.side,
        size=params.size,
        leverage=params.leverage,
        status=OrderStatus.PENDING
    )
```

---

### **3. Validation (Doğrulama)**

```python
def __post_init__(self):
    """Validation (dataclass initialization sonrası)"""
    if self.entry_price <= 0:
        raise ValueError("entry_price pozitif olmalı")
    
    if self.size <= 0:
        raise ValueError("size pozitif olmalı")
    
    if self.leverage < 1:
        raise ValueError("leverage en az 1x olmalı")
```

---

### **4. Serialization**

```python
def to_dict(self) -> Dict[str, Any]:
    """Dict'e çevir"""
    return {
        'bot_id': self.bot_id,
        'symbol': self.symbol,
        'direction': self.direction.value,
        'entry_price': self.entry_price,
        'size': self.size,
        'leverage': self.leverage
    }

@classmethod
def from_dict(cls, data: Dict[str, Any]) -> 'Position':
    """Dict'ten oluştur"""
    return cls(
        bot_id=data['bot_id'],
        symbol=data['symbol'],
        direction=PositionDirection(data['direction']),
        entry_price=data['entry_price'],
        size=data['size'],
        leverage=data['leverage']
    )
```

---

## 🔄 Integration (Entegrasyon)

### **PositionManager ile:**

```python
from core.trading.position_manager import PositionManager

pm = PositionManager()

# Position aç
position = pm.open_position(
    bot_id="bot_123",
    symbol="BTC/USDT",
    direction="LONG",
    entry_price=50000.0,
    size=0.1,
    leverage=5.0
)

# Position'ı PositionManager yönetir
```

---

### **Event Bus ile:**

```python
from shared.events.events import PositionOpenedEvent

# Event oluştur
event = PositionOpenedEvent(
    bot_id="bot_123",
    symbol="BTC/USDT",
    direction="LONG",
    entry_price=50000.0,
    size=0.1
).to_event()

# Event Bus'a yayınla
await event_bus.publish(event)
```

---

## 🧪 Test Örnekleri

### **Position Test:**

```python
def test_position_pnl():
    position = Position(
        bot_id="bot_123",
        symbol="BTC/USDT",
        direction=PositionDirection.LONG,
        entry_price=50000.0,
        size=0.1,
        leverage=5.0
    )
    
    # PnL hesapla
    pnl = position.unrealized_pnl(current_price=51000.0)
    assert pnl == 100.0  # (51000 - 50000) * 0.1
    
    # PnL %
    pnl_percent = position.unrealized_pnl_percent(51000.0)
    assert pnl_percent > 0.0
```

---

### **Trade Test:**

```python
def test_trade_result():
    trade = Trade(
        id="trade_123",
        bot_id="bot_123",
        symbol="BTC/USDT",
        direction=PositionDirection.LONG,
        entry_price=50000.0,
        exit_price=51000.0,
        size=0.1,
        pnl=100.0
    )
    
    # Result
    assert trade.result == TradeResult.WIN
```

---

## 📚 İlgili Dokümanlar

- **Event-Driven Architecture:** `architecture/event_driven_architecture.md`
- **Position Manager:** `features/position_manager.md`
- **Risk Engine:** `features/risk_engine.md`
- **Bot Manager:** `features/bot_manager.md`

---

*Bu doküman Value Objects'in Mart 2026 versiyonunu açıklar.*  
*Güncellemeler için `core/trading/entities/` klasörünü kontrol edin.*
