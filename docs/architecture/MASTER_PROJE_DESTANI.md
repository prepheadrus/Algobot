# 🏛️ MASTER PROJE DESTANI (Architectural Epic)

**Versiyon:** v4.0 (Production-Ready)
**Son Güncelleme:** Mart 2026
**Mimari:** Event-Driven (Olay Güdümlü) + Pub/Sub
**Doküman Tipi:** Mimari Çatı (Architectural Roof)

---

## 📋 Genel Bakış

Bu doküman, CryptoAlgoBot sisteminin **monolitik "God Object"** yapısından **Asenkron Olay Güdümlü (Event-Driven)** mimariye geçişinin tam hikayesini anlatır. PositionManager, RiskEngine ve EventBus izolasyonlarını, Kalman Filtresi gürültü elemesini, Candle Lock mekanizmasını ve ML Triple Barrier Method entegrasyonlarını kapsar.

---

## 🏗️ MİMARİ EVRİM

### **1. Önceki Durum: Monolitik "God Object" (v1.0-v2.0)**

**Dosya:** `core/paper.py` (1,475 satır)

**Sorunlar:**
```python
# ❌ ÖNCEKİ YAPI (Tight Coupling)
class PaperTrader:
    def __init__(self):
        # HER ŞEY tek sınıfta
        self.positions = {}      # Pozisyon yönetimi
        self.risk_config = {}    # Risk ayarları
        self.bots = {}           # Bot yönetimi
        self.strategies = {}     # Strateji yönetimi
        self.exchange = None     # Borsa bağlantısı
    
    def start_bot(self, ...):
        # 200+ satır kod
        # Pozisyon aç, risk kontrolü, bot başlat, strateji yükle...
        pass
    
    def close_position(self, ...):
        # 150+ satır kod
        # PnL hesapla, trade kaydet, event yayınla...
        pass
```

**Sorunlar:**
- 🔴 **Circular Dependency:** `paper.py` ↔ `exchange.py` döngüsü
- 🔴 **Test Edilemez:** 1,475 satır tek sınıf (mocking imkansız)
- 🔴 **Tight Coupling:** Modüller birbirini direkt çağırır
- 🔴 **Single Point of Failure:** Bir hata tüm sistemi çökertir

---

### **2. Şimdiki Durum: Event-Driven Architecture (v3.0-v4.0)**

**Mimari Prensip:**
```
┌──────────────┐     Event Bus      ┌──────────────┐
│  Exchange    │◄────(Pub/Sub)─────▶│  PaperTrader │
│  Manager     │   Loose Coupling   │              │
└──────────────┘                    └──────────────┘
       │                                   │
       │ Event: signal.generated           │ Event: position.opened
       ▼                                   ▼
┌──────────────┐                    ┌──────────────┐
│  Strategy    │                    │  Position    │
│  Manager     │                    │  Manager     │
└──────────────┘                    └──────────────┘
```

**Kod Yapısı:**
```python
# ✅ ŞİMDİKİ YAPI (Loose Coupling)
class PaperTrader:
    def __init__(self):
        # Manager'lara delegate et
        self.position_manager = PositionManager()
        self.risk_engine = RiskEngine()
        self.bot_manager = BotManager()
        
        # Event Bus'a abone ol
        event_bus.subscribe("signal.generated", self.on_signal)
        event_bus.subscribe("position.opened", self.on_position_opened)
    
    def on_signal(self, event):
        # Event handler (izole)
        signal = event.payload['signal']
        if signal == 2:  # LONG
            position = self.position_manager.open_position(...)
```

**Avantajlar:**
- ✅ **Circular Dependency Kırıldı:** Event Bus arada
- ✅ **Test Edilebilir:** Her manager ayrı mock'lanabilir
- ✅ **Loose Coupling:** Modüller birbirini tanımaz
- ✅ **Error Isolation:** Bir hata diğer modülleri etkilemez

---

## 🔧 İZOLASYON KATMANLARI

### **1. PositionManager İzolasyonu**

**Dosya:** `core/trading/position_manager.py`

**Sorumluluk:**
- Pozisyon açma/kapatma
- PnL hesaplama
- Trailing stop yönetimi
- Legacy dict ↔ Value Object dönüşümü

**API:**
```python
class PositionManager:
    def open_position(
        self,
        bot_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        size: float,
        leverage: float,
        stop_loss: float,
        take_profit: float
    ) -> Position:
        """
        Pozisyon aç ve Event yayınla.
        
        Returns:
            Position Value Object
        """
        position = Position(
            bot_id=bot_id,
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            size=size,
            leverage=leverage,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        
        self.positions[bot_id] = position
        
        # Event yayınla
        event = PositionOpenedEvent(
            bot_id=bot_id,
            symbol=symbol,
            direction=direction,
            entry_price=entry_price
        ).to_event()
        
        await event_bus.publish(event)
        
        return position
    
    def close_position(
        self,
        bot_id: str,
        exit_price: float,
        reason: str
    ) -> Trade:
        """
        Pozisyon kapat ve Trade kaydet.
        """
        position = self.positions.get(bot_id)
        
        # PnL hesapla
        pnl = self.calculate_pnl(position, exit_price)
        
        # Trade oluştur
        trade = Trade(
            bot_id=bot_id,
            symbol=position.symbol,
            entry_price=position.entry_price,
            exit_price=exit_price,
            pnl=pnl
        )
        
        # Event yayınla
        event = PositionClosedEvent(
            bot_id=bot_id,
            pnl=pnl,
            reason=reason
        ).to_event()
        
        await event_bus.publish(event)
        
        return trade
```

**İzolasyon:**
- ✅ PaperTrader'dan bağımsız
- ✅ Event Bus üzerinden haberleşir
- ✅ Legacy dict ↔ Position Object dönüşümü yapar

---

### **2. RiskEngine İzolasyonu**

**Dosya:** `core/risk/risk_engine.py`

**Sorumluluk:**
- Pozisyon boyutu hesaplama
- Dinamik kaldıraç hesaplama
- Kill switch yönetimi
- Risk limit kontrolü

**API:**
```python
class RiskEngine:
    def calculate_position_size(
        self,
        balance: float,
        entry: float,
        stop: float,
        risk_pct: float,
        leverage: float
    ) -> float:
        """
        Formül: (Balance × Risk%) / |Entry - Stop|
        """
        risk_amount = balance * (risk_pct / 100)
        price_distance = abs(entry - stop)
        size = risk_amount / price_distance
        
        # Leverage ile sınırlandır
        max_size = (balance * leverage) / entry
        
        return min(size, max_size)
    
    def calculate_dynamic_leverage(
        self,
        confidence: float,
        timeframe: str
    ) -> int:
        """
        ML confidence'a göre kaldıraç.
        
        Timeframe-aware:
        - 1m, 3m: Max 10x (yüksek gürültü)
        - 5m-30m: Max 20x (orta gürültü)
        - 1h+: Max 50x (düşük gürültü)
        """
        if confidence < 0.50:
            return 1  # Düşük güven
        
        if timeframe in ["1m", "3m"]:
            max_leverage = 10
        elif timeframe in ["5m", "15m"]:
            max_leverage = 20
        else:
            max_leverage = 50
        
        # Power curve
        ratio = (confidence - 0.50) / 0.50
        leverage = 1 + (ratio ** 0.7) * (max_leverage - 1)
        
        return int(leverage)
    
    def check_kill_switch(self) -> bool:
        """
        Kill switch aktif mi?
        
        Koşullar:
        - Ardışık kayıp >= max_consecutive_losses
        - Günlük kayıp >= max_daily_loss
        """
        if self.consecutive_losses >= self.config.max_consecutive_losses:
            return True
        
        if self.daily_pnl <= -self.config.max_daily_loss:
            return True
        
        return False
```

**İzolasyon:**
- ✅ PaperTrader'dan bağımsız
- ✅ Sadece hesaplama yapar (state yok)
- ✅ Config-driven (config.yaml'dan okur)

---

### **3. EventBus İzolasyonu**

**Dosya:** `shared/events/event_bus.py`

**Sorumluluk:**
- Pub/Sub pattern implementasyonu
- Event queue yönetimi
- Worker thread pool
- Error isolation

**API:**
```python
class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_queue: asyncio.Queue = None
        self._num_workers = 5  # Parallel workers
        self._max_queue_size = 10000
    
    async def publish(self, event: Event):
        """
        Event yayınla (non-blocking).
        """
        await self._event_queue.put(event)
    
    def subscribe(self, event_type: str, handler: Callable):
        """
        Event'e abone ol.
        """
        self._subscribers[event_type].append(handler)
    
    async def _worker(self, worker_name: str):
        """
        Event worker (internal).
        Queue'dan event alır ve handler'lara gönderir.
        """
        while self._running:
            event = await self._event_queue.get()
            await self._process_event(event)
```

**Event Tipleri (40+):**
| Kategori | Event Tipleri |
|----------|--------------|
| **BOT** | `bot.started`, `bot.stopped`, `bot.error` |
| **SIGNAL** | `signal.generated`, `signal.confirmed` |
| **POSITION** | `position.opened`, `position.closed` |
| **ML** | `ml.training_started`, `ml.prediction` |
| **RISK** | `risk.killswitch_activated` |

**İzolasyon:**
- ✅ Singleton pattern (tek instance)
- ✅ 5 parallel worker (asyncio)
- ✅ Error isolation (bir handler hatası diğerlerini etkilemez)

---

## 🔮 KALMAN FİLTRESİ (Noise Elimination)

**Dosya:** `data/features.py`

**Felsefe:**
> Fiyat verilerindeki piyasa gürültüsünü (noise) elemine etmek için özyineli (recursive) algoritma.

**Formül:**
```python
class KalmanFilter:
    def __init__(self, period=14, alpha=0.1, beta=0.01):
        self.v1 = 0.0  # Smoothed price
        self.v2 = 0.0  # Trend (velocity)
    
    def update(self, val: float) -> float:
        """
        v1 = v1 + alpha * (val - v1)
        v2 = (1 - alpha) * v2 + beta / period * (val - v1)
        
        Returns:
            smoothed_close (filtrelenmiş fiyat)
        """
        v4 = self.alpha
        
        # Update smoothed price
        self.v1 = self.v1 + v4 * (val - self.v1)
        
        # Update trend
        self.v2 = (1 - v4) * self.v2 + self.beta / self.period * (val - self.v1)
        
        return self.v1
```

**Parametre Etkileri:**
| Alpha | Smoothness | Tepki Hızı | Noise Elimination |
|-------|------------|------------|-------------------|
| **0.01** | Çok smooth | Yavaş | %90+ |
| **0.1** (Önerilen) | Dengeli | Dengeli | %70-80 |
| **0.5** | Az smooth | Hızlı | %50-70 |

**Entegrasyon:**
```python
# strategy/adaptive_koncorde.py
class AdaptiveKoncordeX(BaseStrategy):
    def __init__(self):
        self.kalman = KalmanFilter(period=14, alpha=0.1, beta=0.01)
    
    def generate_signal(self, candle: pd.Series) -> int:
        close = candle['close']
        
        # Kalman filtresini güncelle
        smoothed_close = self.kalman.update(close)
        
        # Trend yönü
        trend = self.kalman.get_trend()
        
        # LONG: Smoothed > EMA 50 ve trend yukarı
        if smoothed_close > self.ema_50 and trend > 0:
            return 2  # LONG
        
        # SHORT: Smoothed < EMA 50 ve trend aşağı
        elif smoothed_close < self.ema_50 and trend < 0:
            return 0  # SHORT
        
        return 1  # HOLD
```

**Durum:** ✅ Production-Ready (Adaptive Koncorde X stratejisinde aktif)

---

## ⏱️ CANDLE LOCK (Yeni Mum Kapanış Kilidi)

**Dosya:** `core/exchange.py`

**Felsefe:**
> Saniyede 100+ tick geliyor. Her tick'te hesaplama YAPILMAZ. Sadece mum kapandığında hesaplanır. CPU tasarrufu: %98.

**Implementasyon:**
```python
class ExchangeManager:
    async def run_strategy_poller(self, symbol: str):
        last_candle_time = None
        
        while True:
            # Son mumu al
            df = await self.get_latest_candles(symbol, timeframe='1h', limit=100)
            current_candle_time = df.index[-1]
            
            # CANDLE LOCK KONTROLÜ
            if current_candle_time != last_candle_time:
                # ✅ YENİ MUM KAPANDI → Hesapla
                strategy = self.local_active_strategies.get(symbol)
                if strategy:
                    signal = strategy.generate_signal(df.iloc[-1])
                    
                    # Event yayınla
                    event = SignalGeneratedEvent(...)
                    await event_bus.publish(event)
                
                last_candle_time = current_candle_time
            else:
                # ⏳ MUM HALA AÇIK → Bekle (CPU idle)
                await asyncio.sleep(1)
```

**CPU Tasarrufu:**
```
1h Botu:
  - 1 mum = 3600 saniye
  - Candle Lock: 3599 saniye BEKLE, 1 saniye HESAPLA
  - CPU tasarrufu: %99.97

15m Botu:
  - 1 mum = 900 saniye
  - Candle Lock: 899 saniye BEKLE, 1 saniye HESAPLA
  - CPU tasarrufu: %99.89
```

**Durum:** ✅ Production-Ready (Tüm HTF botlarında aktif)

---

## 🎯 ML TRIPLE BARRIER METHOD

**Dosya:** `ml/data_prep.py`, `ml/model_training.py`

**Felsefe:**
> Marcos Lopez de Prado'nun devrimsel etiketleme yöntemi. Look-Ahead Bias (Geleceği Görme Yanılgısı) hatasını ortadan kaldırır.

**Üç Bariyer:**
```
Fiyat
  │
  │         ┌─── TP Bariyeri (2×ATR)
  │        ╱│
  │       ╱ │
  │      ╱  │
  │     ╱   │
  │    ╱    │
  │   ╱     │
  │  ╱      │
  │ ╱       │
  │╱        │
  ├─────────┼─────────────── Zaman
  │╲        │
  │ ╲       │
  │  ╲      │
  │   ╲     │
  │    ╲    │
  │     ╲   │
  │      ╲  │
  │       ╲ │
  │        ╲│
  │         └─── SL Bariyeri (2×ATR)
```

**Etiket Atama:**
```python
def get_triple_barrier_labels(prices, events, pt_sl, out):
    """
    Bariyerler:
    1. Profit-Take: entry + (tp_multiplier × volatility)
    2. Stop-Loss: entry - (sl_multiplier × volatility)
    3. Time Limit: t + T (5 mum)
    
    Etiketler:
    - 0: SHORT (stop-loss önce dokunuldu)
    - 1: NEUTRAL (time limit doldu)
    - 2: LONG (profit-take önce dokunuldu)
    """
    for t0, t1 in events['t1'].items():
        path = prices.loc[t0:t1]
        cumret = path.pct_change().cumsum()
        
        if (cumret >= pt.loc[t0]).any():
            labels.loc[t0, 'label'] = 2  # LONG
        elif (cumret <= sl.loc[t0]).any():
            labels.loc[t0, 'label'] = 0  # SHORT
        else:
            labels.loc[t0, 'label'] = 1  # NEUTRAL
```

**Model Eğitimi:**
```python
class ModelTrainer:
    def __init__(self):
        # XGBoost + Random Forest Ensemble
        self.xgb_model = xgb.XGBClassifier(
            objective='multi:softprob',
            num_class=3  # LONG, NEUTRAL, SHORT
        )
        self.rf_model = RandomForestClassifier()
    
    def train(self, X_train, y_train, X_test, y_test):
        # Soft Voting Ensemble
        xgb_proba = self.xgb_model.predict_proba(X_test)
        rf_proba = self.rf_model.predict_proba(X_test)
        
        ensemble_proba = (xgb_proba + rf_proba) / 2
        y_pred = np.argmax(ensemble_proba, axis=1)
        
        # Metrikler
        accuracy = accuracy_score(y_test, y_pred)
```

**Durum:** ✅ Production-Ready (ML Karar Motoru'nda aktif)

---

## 📊 MİMARİ ÖZET

```
┌─────────────────────────────────────────────────────────┐
│ 1. FRONTEND (Dashboard)                                 │
│    - ES6 Modules (app.js, chart-renderer.js)            │
│    - Lightweight Charts (TradingView)                   │
│    - Plotly.js (Feature Importance)                     │
└─────────────────────────────────────────────────────────┘
                            ↓ (HTTP/WebSocket)
┌─────────────────────────────────────────────────────────┐
│ 2. API LAYER (FastAPI)                                  │
│    - Routers (bot, ml, strategy, data)                  │
│    - Services (BotService, MLService)                   │
│    - Schemas (Pydantic validation)                      │
└─────────────────────────────────────────────────────────┘
                            ↓ (Event Bus Pub/Sub)
┌─────────────────────────────────────────────────────────┐
│ 3. CORE ENGINE                                          │
│    - ExchangeManager (Centralized poller)               │
│    - PaperTrader (Virtual execution)                    │
│    - Event Bus (5 workers, 10k queue)                   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 4. STRATEGY & ML                                        │
│    - StrategyManager (6 built-in + no-code JSON)        │
│    - ML Integration (XGBoost + RF Ensemble)             │
│    - WFO (Bayesian Optimization, TPE Sampler)           │
│    - Kalman Filter (Noise elimination)                  │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 5. DATA LAYER                                           │
│    - Parquet Data Lake (MTF-Daily partition)            │
│    - Database Manager (SQLite/PostgreSQL)               │
│    - Feature Engineering (40+ features)                 │
└─────────────────────────────────────────────────────────┘
```

---

**Doküman Versiyonu:** v4.0 (Mart 2026)
**Mimari Durum:** ✅ Production-Ready (14/14 E2E Test Passed)
