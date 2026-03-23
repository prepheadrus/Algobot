# 🤖 Bot Manager

**Son Güncelleme:** Mart 2026  
**Durum:** ✅ Production Ready  
**Kategori:** Bot Management

---

## 🎯 Genel Bakış

**Bot Manager**, bot orkestrasyonu ve lifecycle yönetimini sorumludur:
- Bot başlatma
- Bot durdurma
- Bot devam ettirme
- Bot silme
- Durum takibi

**Dosya:** `core/bot/bot_manager.py`

---

## 🏗️ Mimari

```
┌─────────────────────────────────────────────────────────┐
│                 BotManager                              │
├─────────────────────────────────────────────────────────┤
│ - bots: Dict[str, BotInfo]                              │
│ - bot_counter: int                                      │
│ - total_bots_started: int                               │
│ - total_bots_stopped: int                               │
├─────────────────────────────────────────────────────────┤
│ + start_bot(...)                                        │
│ + stop_bot(...)                                         │
│ + resume_bot(...)                                       │
│ + remove_bot(...)                                       │
│ + get_bot(...)                                          │
│ + get_active_bots()                                     │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 Kullanım

### **1. BotManager Oluştur**

```python
from core.bot.bot_manager import BotManager

bm = BotManager()
```

---

### **2. Bot Başlat**

```python
from core.bot.bot_manager import BotConfig, MarketType

config = BotConfig(
    symbol="BTC/USDT",
    strategy_id="trend_master",
    timeframe="1m",
    market_type=MarketType.SWAP,
    leverage=5.0,
    risk_per_trade=0.01
)

bot_id = bm.start_bot(config)
# Returns: "BTC/USDT_trend_master_1m_1"
```

**Bot ID Formatı:**
```
{symbol}_{strategy_id}_{timeframe}_{counter}
Örnek: BTC/USDT_trend_master_1m_1
```

---

### **3. Bot Durdur**

```python
success = bm.stop_bot(bot_id="BTC/USDT_trend_master_1m_1")
```

---

### **4. Bot Devam Ettir**

```python
success = bm.resume_bot(bot_id="BTC/USDT_trend_master_1m_1")
```

---

### **5. Bot Sil**

```python
success = bm.remove_bot(bot_id="BTC/USDT_trend_master_1m_1")
```

---

### **6. Bot Sorguları**

```python
# Bot bilgisi al
bot = bm.get_bot(bot_id)
print(f"Status: {bot.state.status}, PnL: ${bot.state.pnl:.2f}")

# Aktif botları al
active_bots = bm.get_active_bots()

# Sembol'e göre botlar
bots = bm.get_bots_by_symbol("BTC/USDT")

# Strateji'ye göre botlar
bots = bm.get_bots_by_strategy("trend_master")

# Durum'a göre botlar
running_bots = bm.get_bots_by_status(BotStatus.RUNNING)
```

---

## 📊 Özellikler

### **1. Type-Safe Dataclass'lar**

```python
from core.bot.bot_manager import BotConfig, BotState, BotInfo, BotStatus

# Bot config
config = BotConfig(
    symbol="BTC/USDT",
    strategy_id="trend_master",
    timeframe="1m"
)

# Bot state
state = BotState(
    status=BotStatus.RUNNING,
    pnl=100.0,
    trades=5,
    wins=3
)

# Bot info
bot = BotInfo(
    bot_id="bot_123",
    config=config,
    state=state,
    started_at=datetime.utcnow()
)
```

---

### **2. Bot Lifecycle**

```
STOPPED → RUNNING → PAUSED → RUNNING → STOPPED
              ↓
           REMOVED
```

---

### **3. Bot State Tracking**

```python
# PnL güncelle
bm.update_bot_pnl(bot_id, pnl=100.0)

# Marjin güncelle
bm.update_bot_margin(bot_id, margin=500.0)

# Trade kaydet
bm.record_bot_trade(bot_id, pnl=100.0)

# Sinyal kaydet
bm.record_bot_signal(bot_id)
```

---

### **4. Legacy Uyumluluk**

```python
from core.bot.bot_manager import LegacyBotManager

# Dict-based legacy API
legacy_bm = LegacyBotManager()

bot_id = legacy_bm.start_bot(
    bot_id="bot_123",
    symbol="BTC/USDT",
    strategy_id="trend_master",
    timeframe="1m"
)
```

---

## 🧪 Test Örnekleri

### **Bot Lifecycle Testi:**

```python
def test_bot_lifecycle():
    bm = BotManager()
    
    config = BotConfig(
        symbol="BTC/USDT",
        strategy_id="trend_master",
        timeframe="1m"
    )
    
    # Başlat
    bot_id = bm.start_bot(config)
    assert bm.is_bot_running(bot_id) == True
    
    # Durdur
    bm.stop_bot(bot_id)
    assert bm.is_bot_running(bot_id) == False
    
    # Devam et
    bm.resume_bot(bot_id)
    assert bm.is_bot_running(bot_id) == True
    
    # Sil
    bm.remove_bot(bot_id)
    assert bm.bot_exists(bot_id) == False
```

---

### **Bot State Testi:**

```python
def test_bot_state():
    bm = BotManager()
    
    config = BotConfig(symbol="BTC/USDT", strategy_id="trend_master")
    bot_id = bm.start_bot(config)
    
    # PnL güncelle
    bm.update_bot_pnl(bot_id, pnl=100.0)
    
    bot = bm.get_bot(bot_id)
    assert bot.state.pnl == 100.0
```

---

## 🚨 Sorun Giderme

### **Sorun 1: Bot Bulunamadı**

**Hata:**
```
Bot bulunamadı: bot_123
```

**Çözüm:**
```python
# Bot mevcut mu kontrol et
if bm.bot_exists(bot_id):
    bm.stop_bot(bot_id)
else:
    logger.warning(f"Bot bulunamadı: {bot_id}")
```

---

### **Sorun 2: Bot Devam Edemez**

**Sebep:** Bot running değil (paused veya stopped olmalı)

**Çözüm:**
```python
bot = bm.get_bot(bot_id)
if bot.state.status in [BotStatus.PAUSED, BotStatus.STOPPED]:
    bm.resume_bot(bot_id)
else:
    logger.warning(f"Bot devam edemez: {bot.state.status}")
```

---

## 📚 İlgili Dokümanlar

- **Position Manager:** `features/position_manager.md`
- **Risk Engine:** `features/risk_engine.md`
- **Event-Driven Architecture:** `architecture/event_driven_architecture.md`

---

*Bu doküman Bot Manager'ın Mart 2026 versiyonunu açıklar.*  
*Güncellemeler için `core/bot/bot_manager.py` dosyasını kontrol edin.*
