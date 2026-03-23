# 🔄 Exchange Architecture (Asenkron Poller & WebSocket)

**Versiyon:** v4.0 (Production-Ready)
**Son Güncelleme:** Mart 2026
**Dosya:** `core/exchange.py`

---

## 📋 Genel Bakış

ExchangeManager, CCXT Pro kütüphanesini kullanarak:
1. **Asenkron Poller:** Her sembol için strateji sinyallerini işleyen merkezi dinleyici
2. **WebSocket Push:** Canlı fiyat güncellemeleri (0 polling)
3. **1-to-N Mimarisi:** Bir sembolde sınırsız bot çalıştırma

---

## 🏗️ Mimari

```
┌─────────────────────────────────────────────────────────┐
│  Binance Futures (CCXT Pro)                             │
└──────────────┬──────────────────────────────────────────┘
               │ WebSocket (Live Ticker)
               ▼
┌─────────────────────────────────────────────────────────┐
│  ExchangeManager (core/exchange.py)                     │
├─────────────────────────────────────────────────────────┤
│  - active_pollers: {symbol: asyncio.Task}               │
│  - local_active_bots: {bot_id: bot_info}                │
│  - local_active_strategies: {symbol: strategy}          │
└──────────────┬──────────────────────────────────────────┘
               │ Event Bus (Pub/Sub)
               ▼
┌─────────────────────────────────────────────────────────┐
│  PaperTrader (core/paper.py)                            │
│  - Position Manager                                     │
│  - Risk Engine                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 1. ASEKRON POLLER

### **Poller Başlatma**

```python
# core/exchange.py
async def run_strategy_poller(self, symbol: str):
    """
    Her sembol için 1 poller başlat (1-to-N mimarisi).
    
    Poller:
    - Her 1 saniyede bir strateji sinyali üretir
    - Event Bus'a publish eder (signal.generated)
    - Circular dependency YOK (Event Bus kullanır)
    """
    
    logger.info(f"🚀 [POLLER] {symbol} için strateji poller başlatılıyor...")
    
    while True:
        try:
            # 1. Son mumu al
            df = await self.get_latest_candles(symbol, timeframe='1m', limit=100)
            
            # 2. Strateji sinyali üret
            strategy = self.local_active_strategies.get(symbol)
            if strategy:
                signal = strategy.generate_signal(df.iloc[-1])
                
                # 3. Event yayınla
                event = SignalGeneratedEvent(
                    bot_id=f"{symbol}_bot",
                    symbol=symbol,
                    signal=signal,
                    price=df['close'].iloc[-1],
                    indicators={...}
                ).to_event()
                
                await event_bus.publish(event)
            
            # 4. 1 saniye bekle
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"❌ [POLLER] {symbol} hatası: {e}")
            await asyncio.sleep(5)  # Hata durumunda 5 saniye bekle
```

### **Poller Yönetimi**

```python
# Poller başlat
task = asyncio.create_task(exchange_manager.run_strategy_poller('BTC/USDT:USDT'))
exchange_manager.active_pollers['BTC/USDT:USDT'] = task

# Poller durdur
if symbol in exchange_manager.active_pollers:
    exchange_manager.active_pollers[symbol].cancel()
    del exchange_manager.active_pollers[symbol]
```

---

## 2. WEBSOCKET PUSH

### **WebSocket Döngüsü**

```python
# core/exchange.py
async def watch_ticker_loop(self, symbol: str):
    """
    WebSocket üzerinden canlı ticker dinle (PUSH - POLLING YOK!).
    
    Avantajlar:
    - 0 polling (API limit dostu)
    - <100ms gecikme (real-time)
    - %98 CPU tasarrufu (polling'e göre)
    """
    
    logger.info(f"📡 [WSS] {symbol} için WebSocket döngüsü başlatılıyor...")
    
    while True:
        try:
            # CCXT Pro WebSocket ticker
            ticker = await self.exchange.watch_ticker(symbol)
            
            # Event yayınla
            event = LivePriceUpdatedEvent(
                symbol=symbol,
                price=ticker['last'],
                timestamp=ticker['timestamp']
            ).to_event()
            
            await event_bus.publish(event)
            
        except Exception as e:
            logger.error(f"❌ [WSS] {symbol} hatası: {e}")
            await asyncio.sleep(1)
```

### **Polling vs WebSocket Karşılaştırma**

| Özellik | Polling | WebSocket |
|---------|---------|-----------|
| **API Çağrıları** | 60/dk (her saniye) | 1 (sürekli bağlantı) |
| **Gecikme** | 500-1000ms | <100ms |
| **CPU Kullanımı** | Yüksek (sürekli sorgu) | Düşük (event-driven) |
| **Rate Limit** | Hızla aşılır | Aşılmaz |

---

## 3. 1-to-N MULTI-BOT MİMARİSİ

### **Aynı Sembolde Sınırsız Bot**

```python
# core/exchange.py
async def start_bot(self, symbol, strategy_id, timeframe):
    """
    Aynı sembolde birden fazla bot çalıştır.
    
    Örnek:
    - BTC/USDT:USDT → trend_master (1h)
    - BTC/USDT:USDT → scalper_ninja (5m)
    - BTC/USDT:USDT → mean_reversion (15m)
    
    Hepsi AYNI sembolde, FARKLI stratejiler!
    """
    
    bot_id = f"{symbol}_{strategy_id}_{timeframe}_{len(self.local_active_bots)}"
    
    # Bot bilgilerini kaydet (State Replication)
    self.local_active_bots[bot_id] = {
        'symbol': symbol,
        'strategy_id': strategy_id,
        'timeframe': timeframe,
        'status': 'running'
    }
    
    # Strateji instance'ını kaydet
    strategy = StrategyManager.get_strategy(strategy_id)
    self.local_active_strategies[symbol] = strategy
    
    # Event yayınla
    event = BotStartedEvent(
        bot_id=bot_id,
        symbol=symbol,
        strategy_id=strategy_id,
        timeframe=timeframe
    ).to_event()
    
    await event_bus.publish(event)
    
    logger.info(f"✅ Bot başlatıldı: {bot_id}")
```

### **Rate Limit Koruması**

```python
# Aynı sembol için SADECE 1 poller
if symbol not in self.active_pollers:
    # İlk bot → Poller başlat
    task = asyncio.create_task(self.run_strategy_poller(symbol))
    self.active_pollers[symbol] = task
else:
    # Zaten poller var → Sadece bot ekle
    logger.debug(f"📊 [POLLER] {symbol} için poller zaten çalışıyor")
```

---

## 4. EVENT BUS ENTEGRASYONU

### **Subscription (Abonelik)**

```python
# core/exchange.py
def _setup_event_subscriptions(self):
    """Event Bus'a abone ol - State senkronizasyonu"""
    
    # Bot lifecycle eventleri
    event_bus.subscribe("bot.started", self._on_bot_started)
    event_bus.subscribe("bot.stopped", self._on_bot_stopped)
    
    logger.info("📬 [EDA] Event subscriptions kuruldu")
```

### **Handler Implementasyonları**

```python
async def _on_bot_started(self, event):
    """Bot başladı - local state güncelle"""
    bot_id = event.payload.get('bot_id')
    if bot_id:
        self.local_active_bots[bot_id] = event.payload
        logger.debug(f"🤖 [EDA] Bot başladı (local state güncellendi): {bot_id}")

async def _on_bot_stopped(self, event):
    """Bot durdu - local state'den sil"""
    bot_id = event.payload.get('bot_id')
    if bot_id and bot_id in self.local_active_bots:
        del self.local_active_bots[bot_id]
        logger.debug(f"🛑 [EDA] Bot durdu (local state silindi): {bot_id}")
```

---

## 5. LIQUIDITY SWEEP KORUMASI

### **Order Book Imbalance**

```python
# core/exchange.py
async def get_order_book_imbalance(self, symbol: str, depth: int = 20) -> float:
    """
    Order Book Imbalance hesapla.
    
    Formula:
        imbalance = ask_volume / (bid_volume + ask_volume)
    
    Returns:
        0.5: Dengeli
        >0.6: Ask baskın (satıcılar güçlü - LONG riskli)
        <0.4: Bid baskın (alıcılar güçlü - SHORT riskli)
    """
    
    order_book = await self.exchange.fetch_order_book(symbol, limit=depth)
    
    bid_volume = sum([float(level[1]) for level in order_book.get('bids', [])])
    ask_volume = sum([float(level[1]) for level in order_book.get('asks', [])])
    
    total_volume = bid_volume + ask_volume
    if total_volume == 0:
        return 0.5
    
    imbalance = ask_volume / total_volume
    return imbalance
```

### **Liquidity Sweep Filtresi**

```python
def check_liquidity_sweep(self, symbol: str, imbalance: float, direction: str) -> bool:
    """
    Liquidity Sweep koruması.
    
    WFO ve ML "LONG" dese dahi,
    eğer order book'da satıcılar baskın (%60+ ask) ise
    işlem AÇILMAZ.
    
    Returns:
        True: İşlem ONAYLI
        False: İşlem REDDEDİLDİ
    """
    
    if direction == 'LONG':
        if imbalance > 0.60:
            logger.warning(f"⚠️ [LIQUIDITY] {symbol} LONG reddedildi - Ask baskın")
            return False
    
    elif direction == 'SHORT':
        if imbalance < 0.40:
            logger.warning(f"⚠️ [LIQUIDITY] {symbol} SHORT reddedildi - Bid baskın")
            return False
    
    return True
```

---

## 6. STATE REPLICATION

### **Circular Dependency Kırıldı**

```python
# core/exchange.py
class ExchangeManager:
    def __init__(self):
        # Local state (PaperTrader'a circular dependency YOK)
        self.local_active_bots: Dict[str, Dict] = {}
        self.local_active_strategies: Dict[str, Any] = {}
        self.local_active_timeframes: Dict[str, str] = {}
        
        # Event Bus subscriptions
        event_bus.subscribe("bot.started", self._on_bot_started)
        event_bus.subscribe("bot.stopped", self._on_bot_stopped)
```

**Önceki Sorun (Monolitik):**
```python
# ❌ YANLIŞ: Circular dependency
from core.paper import paper_engine

class ExchangeManager:
    def start_bot(self, ...):
        paper_engine.start_bot(...)  # PaperTrader → Exchange → PaperTrader
```

**Şimdiki Çözüm (Event-Driven):**
```python
# ✅ DOĞRU: Event Bus ile loose coupling
from shared.events import event_bus

class ExchangeManager:
    def start_bot(self, ...):
        event = BotStartedEvent(...).to_event()
        await event_bus.publish(event)  # PaperTrader abone, dinliyor
```

---

## 🚨 Sorun Giderme

### **Sorun 1: Poller Çalışmıyor**

**Semptom:** Bot başladı ama sinyal yok

**Çözüm:**
```python
# Poller durumunu kontrol et
print(f"Active pollers: {exchange_manager.active_pollers.keys()}")

# Eğer boşsa, poller başlat
if symbol not in exchange_manager.active_pollers:
    task = asyncio.create_task(exchange_manager.run_strategy_poller(symbol))
    exchange_manager.active_pollers[symbol] = task
```

---

### **Sorun 2: WebSocket Bağlantısı Koptu**

**Semptom:** Fiyat güncellenmiyor

**Çözüm:**
```python
# WebSocket'i yeniden başlat
task = asyncio.create_task(exchange_manager.watch_ticker_loop(symbol))

# Veya tüm bağlantıları reset et
await exchange_manager.exchange.close()
await exchange_manager.exchange.__init__(...)
```

---

### **Sorun 3: Rate Limit Aşıldı**

**Semptom:** `APIError: Rate limit exceeded`

**Çözüm:**
```python
# WebSocket'e geç (polling'i bırak)
# WebSocket: 0 rate limit (sürekli bağlantı)

# API key ekle (.env dosyasına)
BINANCE_API_KEY=pk_live_...
BINANCE_API_SECRET=sk_live_...

# Yüksek rate limit aktif olur (1200 weight/min → 2400 weight/min)
```

---

## 📚 İlgili Dokümanlar

- **Event-Driven Architecture:** `architecture/event_driven_architecture.md`
- **1-to-N Multi-Bot:** `architecture/1-to-N-multi-bot-architecture.md`
- **Smart Hybrid Architecture:** `architecture/smart-hybrid-architecture.md`

---

*Bu doküman Exchange Architecture v4.0 (Mart 2026) için hazırlanmıştır.*
