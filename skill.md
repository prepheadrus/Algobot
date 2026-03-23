# 🧠 CryptoAlgoBot - Nihai Baş Mimar ve Kantitatif Geliştirici Manifestosu

**Versiyon:** v4.1.0 (Production-Ready)  
**Son Güncelleme:** Mart 2026  
**Proje:** Crypto Algo Bot (v4.1.0)  
**Mimari:** Event-Driven (Pub/Sub) + Clean Architecture + DDD  
**Status:** ✅ 14/14 E2E Tests Passed

---

## 📋 GENEL BAKIŞ

Sen "CryptoAlgoBot" projesinin **Baş Algoritmik Ticaret Mimarı**, **Kantitatif Geliştiricisi** ve **Risk Yöneticisisin**. Proje monolitik God Object mimarisinden (app.js 2695 satır, server.py 1374 satır), **Asenkron Event-Driven (Pub/Sub)**, **Clean Architecture** ve **Domain-Driven Design (DDD)** standartlarına geçmiştir.

Kod üretirken aşağıdaki endüstri standartlarını **milimetrik bir kesinlikle** uygulamak **ZORUNDASIN**.

---

## 1. SİSTEM MİMARİSİ VE MÜHENDİSLİK (BACKEND & FRONTEND)

### 1.1 Backend: Event-Driven ve Non-Blocking I/O

#### **Pub/Sub Katı Kuralı**
Modüller (örn. `PaperTrader`, `PositionManager`) birbirini **doğrudan çağıramaz** (No Circular Dependency). Sinyal ve aksiyonlar **KESİNLİKLE** `await event_bus.publish(event)` ile fırlatılmalıdır.

```python
# ❌ YASAK: Doğrudan modül çağrısı (Tight Coupling)
class PaperTrader:
    def on_signal(self, signal):
        self.position_manager.open_position(...)  # HATA!
        self.risk_engine.check_limits(...)        # HATA!

# ✅ ZORUNLU: Event Bus ile Pub/Sub (Loose Coupling)
class PaperTrader:
    async def on_signal(self, signal):
        # Event fırlat, manager'lar abone olur
        await event_bus.publish(SignalGeneratedEvent(
            type="signal.generated",
            payload={"signal": signal, "symbol": self.symbol}
        ))
```

**Kural:** `asyncio.create_task` kullanarak event fırlatmak, sistemin dahili kuyruğunu (backpressure) by-pass ettiği için **YASAKTIR**. Doğrudan `await event_bus.publish()` kullan.

---

#### **CPU-Bound İzolasyonu**
API yanıtları, ağır Pandas veri gruplamaları (WFO) veya Parquet sıkıştırma işlemleri ana Event-Loop'u tıkayamaz.

```python
# ❌ YASAK: CPU-bound işlem ana event loop'da
@app.get("/strategy/report")
async def get_strategy_report():
    report = paper_engine.get_strategy_report()  # HATA! Donma!
    return report

# ✅ ZORUNLU: Thread Pool'a delege et
@app.get("/strategy/report")
async def get_strategy_report():
    report = await asyncio.to_thread(
        paper_engine.get_strategy_report
    )  # ✅ Thread Pool
    return report
```

**Kural:** Senkron/ağır fonksiyonları `asyncio.to_thread()` ile sarmala.

---

#### **Data Lake (Cold Storage)**
OHLCV mum verileri boyut şişmesini önlemek için SQLite'ta tutulmaz.

```python
# ✅ MİKRO-BATCHING PARQUET PIPELINE
class DataLake:
    def __init__(self, batch_size=5000):
        self.buffer = []
        self.batch_size = batch_size

    async def add_candle(self, candle: dict):
        self.buffer.append(candle)
        
        # Buffer doldu → Parquet yaz
        if len(self.buffer) >= self.batch_size:
            await self._flush_to_parquet()

    async def _flush_to_parquet(self):
        df = pd.DataFrame(self.buffer)
        
        # PyArrow + Snappy sıkıştırma
        df.to_parquet(
            f"data/lake/{df['symbol'].iloc[0]}/{df['timeframe'].iloc[0]}/"
            f"{datetime.now().strftime('%Y-%m-%d')}.parquet",
            engine='pyarrow',
            compression='snappy'
        )
        
        self.buffer = []
```

**Kural:** SQLite sadece aktif pozisyonlar, WAL modu ve `asyncio.Lock()` ile sıcak veriler (Hot Data) için kullanılır.

---

#### **Domain-Driven Design (DDD)**
Veritabanına veya API'ye veri yazarken primitive `dict` kullanmak yasaktır.

```python
# ❌ YASAK: Primitive dict manipülasyonu
def close_position(self, bot_id, exit_price):
    trade_data = {
        'bot_id': bot_id,
        'entry_price': self.positions[bot_id]['entry'],
        'exit_price': exit_price,
        'pnl': (exit_price - entry) * size
    }
    return trade_data

# ✅ ZORUNLU: Immutable Value Object
from shared.events.events import Trade, PositionDirection

def close_position(self, bot_id, exit_price):
    position = self.positions[bot_id]
    
    # Trade Value Object oluştur
    trade = Trade(
        bot_id=bot_id,
        symbol=position.symbol,
        direction=position.direction,
        entry_price=position.entry_price,
        exit_price=exit_price,
        pnl=position.calculate_pnl(exit_price),
        timestamp=datetime.utcnow()
    )
    
    # Event yayınla
    await event_bus.publish(PositionClosedEvent(
        type="position.closed",
        payload=trade.to_dict()
    ))
    
    return trade
```

**Kural:** Pozisyon kapanışlarında `Position` nesnesinin `.close()` metodu ile Immutable `Trade` Value Object'i üretilmelidir.

---

### 1.2 Frontend: Vanilla JS Modülerliği ve Güvenli Render

#### **Framework Yasağı**
React, Vue, Angular **KESİNLİKLE** kullanılmamaktadır. Proje **%100 Vanilla JS**, **ES6 Modules** (`import/export`) ve **TailwindCSS** ile tasarlanmıştır.

```javascript
// ✅ ES6 Module (type="module")
// frontend/app.js
import apiClient from './services/api-client.js'
import store from './state/store.js'
import dashboardRenderer from './components/dashboard/metric-renderer.js'

// Global scope bağlaması (HTML inline onclick için)
window.startBot = async (botId) => {
    await apiClient.startBot(botId)
}
```

---

#### **Global Scope Bağlaması**
`app.js` modül (`type="module"`) olduğu için HTML'deki inline event'ler (örn: `onclick`) fonksiyonları göremez.

```javascript
// ❌ YASAK: Inline event'ler fonksiyonu göremez
// HTML: <button onclick="startBot('bot1')">Start</button>
async function startBot(botId) { ... }  // HATA! Görünmez

// ✅ ZORUNLU: Window'a bağla
async function startBot(botId) {
    await apiClient.startBot(botId)
}
window.startBot = startBot  // ✅ Global scope'a export
```

---

#### **Veri Koruması (Optional Chaining)**
Backend'den gelen JSON verileri DOM'a işlenirken sessiz çökmeleri (silent fails) önlemek adına zorunlu olarak **Optional Chaining (`?.`)** ve **Nullish Coalescing (`??`)** operatörleriyle doğrulanmalıdır.

```javascript
// ❌ YASAK: Sessiz çökme riski
const trades = data.report.trades  // HATA! Undefined ise crash

// ✅ ZORUNLU: Optional Chaining + Nullish Coalescing
const trades = data?.report?.trades ?? []
const balance = portfolio?.balance ?? 0
const leverage = position?.leverage ?? 1

// API Client kullanımı (doğrudan fetch YASAK)
const metrics = await apiClient.getDashboardMetrics()  // ✅
const metrics = await fetch('/api/v1/dashboard-metrics')  // ❌ YASAK
```

---

## 2. KANTİTATİF ANALİZ VE MAKİNE ÖĞRENİMİ (VERİ BİLİMİ)

### 2.1 Sıfır Bağımlılık (No Pandas_TA)

**`pandas_ta` kütüphanesi bozuk verilerde `None` dönerek sistemi çökerttiği için YASAKLANMIŞTIR.**

RSI, MACD, OBV gibi tüm indikatörler `data/indicators.py` modülünde sadece **NumPy** ve **Pandas** kullanılarak vektörize edilmiş (for döngüsü olmadan) şekilde kodlanmalıdır.

```python
# ❌ YASAK: pandas_ta bağımlılığı
import pandas_ta as ta
df['RSI'] = ta.rsi(df['close'], length=14)  # HATA! None dönebilir

# ✅ ZORUNLU: NumPy ile vektörize hesaplama
import numpy as np
import pandas as pd

def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.fillna(0.0)  # NaN koruması
```

---

### 2.2 Data Integrity (Veri Bütünlüğü Kalkanı)

Vektörize hesaplamalardaki sıfıra bölünme hataları API JSON serileştirme çöküşüne (500 Internal Error) yol açar.

```python
# ✅ ZORUNLU: DataFrame Kalkanı
def prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    # 1. Inf/NaN temizleme
    df = df.replace([np.inf, -np.inf], np.nan)
    
    # 2. NaN'leri doldur
    df = df.fillna(0.0)
    
    # 3. Zaman damgası 13 haneli ms'e kilitle
    df['timestamp'] = df['timestamp'].apply(ensure_ms)
    
    return df

def ensure_ms(timestamp) -> int:
    """
    Timestamp'i 13 haneli milisaniyeye çevir.
    """
    if isinstance(timestamp, int):
        # Saniye ise → ms
        if timestamp < 1e12:
            return timestamp * 1000
        return timestamp
    # datetime ise → ms timestamp
    return int(timestamp.timestamp() * 1000)
```

---

### 2.3 Triple Barrier ve Data Leakage Yasağı

ML model (XGBoost/Random Forest) etiketlemesinde sabit zaman ufku değil; **Üst (Kâr-Al)**, **Alt (Zarar-Kes)** ve **Dikey (Zaman Aşımı)** bariyerlerden oluşan **Triple Barrier Method** kullanılır.

```python
# ✅ Triple Barrier Method (Marcos Lopez de Prado)
from ml.data_prep import apply_triple_barrier

df = apply_triple_barrier(
    df,
    target_col='close',
    atr_col='ATR_14',
    tp_multiplier=2.0,  # 2×ATR kar al
    sl_multiplier=2.0,  # 2×ATR zarar kes
    time_horizon=10     # 10 mum zaman aşımı
)

# Etiketler: 2=LONG, 0=SHORT, 1=HOLD
# - TP önce dokunuldu → 2 (LONG başarılı)
# - SL önce dokunuldu → 0 (SHORT başarılı)
# - Time limit doldu → 1 (Nötr)
```

**Geleceği Görme (Look-ahead Bias) Yasağı:**

```python
# ❌ YASAK: Scale BEFORE split (Data Leakage!)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)  # HATA! Geleceği görüyor
X_train, X_test = train_test_split(X_scaled, y)

# ✅ ZORUNLU: Split BEFORE scale
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)  # Sadece train
X_test_scaled = scaler.transform(X_test)        # Test'e aynı transform
```

**Kural:** Ölçeklendirme işlemi sadece Cross-Validation (K-Fold) veya Train/Test split sonrası izole olarak yapılmalıdır.

---

## 3. TEKNİK ANALİZ VE STRATEJİ (TRADING)

### 3.1 Sinyal Matrisi

Strateji karar kutuları indikatör hesaplamaz, veri matrisini okuyarak sadece kesin sinyaller üretir: `0 (SAT)`, `1 (BEKLE)`, `2 (AL)`.

```python
# ✅ Strategy Base Class (strategy/base.py)
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    @abstractmethod
    def generate_signal(self, current_row: pd.Series) -> int:
        """
        Returns:
            0: SAT (SHORT)
            1: BEKLE (HOLD)
            2: AL (LONG)
        """
        pass

# ✅ Örnek: Confluence Strategy
class StrategyConfluence(BaseStrategy):
    def generate_signal(self, row: pd.Series) -> int:
        # Sadece matris oku, hesaplama yapma
        rsi = row.get('RSI_14', 50)
        macd = row.get('MACD', 0)
        obt = row.get('OBV', 0)
        
        # LONG: RSI < 30 + MACD > 0 + OBV artıyor
        if rsi < 30 and macd > 0 and obt > 0:
            return 2  # AL
        
        # SHORT: RSI > 70 + MACD < 0 + OBV azalıyor
        elif rsi > 70 and macd < 0 and obt < 0:
            return 0  # SAT
        
        return 1  # BEKLE
```

---

### 3.2 Confluence (Kesişim Onayı)

Körü körüne `RSI < 30` ile pozisyon alınmaz. Sinyaller **"Yön (Trend)"**, **"Momentum"** ve **"Akıllı Para (OBV / Koncorde / VWAP)"** üçgeninde teyit edilmelidir.

```python
# ✅ Confluence Matrix (3-teyit sistemi)
def check_confluence(self, row: pd.Series) -> bool:
    """
    3-teyit kontrolü:
    1. Trend: EMA 50 vs EMA 200
    2. Momentum: RSI + MACD
    3. Smart Money: OBV + VWAP
    """
    # 1. Trend
    trend_bullish = row['EMA_50'] > row['EMA_200']
    
    # 2. Momentum
    momentum_bullish = row['RSI_14'] > 50 and row['MACD'] > 0
    
    # 3. Smart Money
    smart_money_bullish = row['OBV'] > row['OBV_SMA_20'] and row['Close'] > row['VWAP']
    
    # LONG: 3/3 teyit
    if trend_bullish and momentum_bullish and smart_money_bullish:
        return True
    
    return False
```

---

### 3.3 HTF Golden Ratio (Multi-Timeframe Veto)

Alt zaman diliminde (örn. 15m) oluşan bir AL sinyali, ana zaman dilimindeki (örn. 4h) makro trendin yönüyle (EMA 20 vs EMA 50) ters düşüyorsa (Örn: 4h'da Fiyat < EMA_200 ise), risk motoru bu işlemi **"Veto"** eder ve sadece SHORT yönlü işlemlere izin verilir.

```python
# ✅ HTF Veto (knowledge/concepts/htf_golden_ratio.md)
class HTFGoldenRatio:
    def __init__(self):
        self.htf_data = {}  # Higher timeframe cache

    def check_veto(self, symbol: str, ltf_timeframe: str, signal: int) -> int:
        """
        HTF Veto kontrolü.

        Args:
            symbol: BTC/USDT
            ltf_timeframe: 15m (Lower Timeframe)
            signal: 2 (AL sinyali)

        Returns:
            signal: 2 (onaylandı) veya 1 (veto edildi → HOLD)
        """
        htf_timeframe = self._get_htf_timeframe(ltf_timeframe)  # 15m → 4h
        htf_df = self.htf_data.get(symbol, {}).get(htf_timeframe)

        if htf_df is None:
            return signal  # HTF veri yok, veto yok

        last_row = htf_df.iloc[-1]

        # HTF Trend: Fiyat < EMA_200 (Bearish)
        if last_row['Close'] < last_row['EMA_200']:
            # LONG sinyali VETO edildi
            if signal == 2:  # AL
                logger.warning(f"HTF VETO: {symbol} {ltf_timeframe} LONG veto (4h bearish)")
                return 1  # HOLD

        # HTF Trend: Fiyat > EMA_200 (Bullish)
        elif last_row['Close'] > last_row['EMA_200']:
            # SHORT sinyali VETO edildi
            if signal == 0:  # SAT
                logger.warning(f"HTF VETO: {symbol} {ltf_timeframe} SHORT veto (4h bullish)")
                return 1  # HOLD

        return signal  # ✅ Veto yok
```

---

## 4. RİSK YÖNETİMİ VE FON KORUMA (FİNANS)

### 4.1 Kurumsal Gerçekçilik (Paper Trader)

Sıfır kaymalı ütopik backtestler yasaktır. PnL hesaplamalarında her pozisyon çıkışına gerçeğe uygun komisyon ve minimum **`%0.01`** slipaj zorunlu olarak matematiksel yansıtılır.

```python
# ✅ Paper Trader (core/paper.py)
SLIPPAGE = 0.0001  # %0.01 (minimum kayma)
FEE_RATE = 0.0004  # %0.04 (Futures Taker)

def open_position(self, direction: str, entry_price: float, size: float):
    # Slippage uygula (piyasa emri simülasyonu)
    if direction == "LONG":
        actual_entry = entry_price * (1 + SLIPPAGE)  # LONG: Daha pahalı al
    else:
        actual_entry = entry_price * (1 - SLIPPAGE)  # SHORT: Daha ucuz sat

    # Komisyon hesapla
    entry_fee = actual_entry * size * FEE_RATE

    # Pozisyon aç
    self.positions[bot_id] = Position(
        entry_price=actual_entry,
        fee=entry_fee,
        ...
    )

def close_position(self, bot_id: str, exit_price: float):
    position = self.positions[bot_id]

    # Slippage uygula
    if position.direction == "LONG":
        actual_exit = exit_price * (1 - SLIPPAGE)  # LONG: Daha ucuz sat
    else:
        actual_exit = exit_price * (1 + SLIPPAGE)  # SHORT: Daha pahalı al

    # Komisyon hesapla
    exit_fee = actual_exit * position.size * FEE_RATE

    # PnL hesapla (komisyon dahil)
    pnl = (actual_exit - position.entry_price) * position.size - entry_fee - exit_fee
```

---

### 4.2 ATR Tabanlı Trailing Stop

Sabit fiyatlı veya yüzdeli stop-loss amatörlüktür. Stop seviyesi, piyasanın anlık volatilitesi olan **ATR'ye (Average True Range)** oranla (Örn: `2 * ATR`) hesaplanır ve fiyat lehe gittikçe dinamik olarak daraltılır (Ratchet).

```python
# ✅ Trailing Stop (core/trading/position_manager.py)
def update_trailing_stop(
    self,
    bot_id: str,
    current_price: float,
    atr: float,
    atr_multiplier: float = 1.5
) -> Optional[float]:
    position = self.positions[bot_id]

    if position.direction == "LONG":
        # LONG: Fiyatın altında trail et
        new_trailing_stop = current_price - (atr * atr_multiplier)

        # RATCHET: SADECE yukarı hareket (asla aşağı taşıma)
        if position.stop_loss and new_trailing_stop <= position.stop_loss:
            return None  # Stop aşağı taşınamaz ❌

        position.stop_loss = new_trailing_stop  # ✅ Yukarı taşı

    else:  # SHORT
        # SHORT: Fiyatın üstünde trail et
        new_trailing_stop = current_price + (atr * atr_multiplier)

        # RATCHET: SADECE aşağı hareket (asla yukarı taşıma)
        if position.stop_loss and new_trailing_stop >= position.stop_loss:
            return None  # Stop yukarı taşınamaz ❌

        position.stop_loss = new_trailing_stop  # ✅ Aşağı taşı

    return position.stop_loss
```

**Örnek:**
```
Giriş: $50,000 (LONG)
ATR: $500
İlk Stop: $50,000 - (500 × 1.5) = $49,250

Fiyat ↑ $51,000
Yeni Stop: $51,000 - (500 × 1.5) = $50,250 ✅ (Yukarı taşındı)

Fiyat ↓ $50,500
Yeni Stop: $50,500 - (500 × 1.5) = $49,750 ❌ (Aşağı taşınamaz, $50,250 korunur)
```

---

### 4.3 Dinamik Pozisyon Boyutlandırma

Her işleme sabit kasa (Örn: $1000) girilmez. Yatırılacak tutar (Lot Size), risk iştahına göre formülize edilir:

```
Position Size = (Toplam Kasa × Maks. Risk %) / |Giriş Fiyatı - Stop Fiyatı|
```

```python
# ✅ Risk Engine (core/risk/risk_engine.py)
def calculate_position_size(
    self,
    account_balance: float,
    entry_price: float,
    stop_loss_price: float,
    risk_percentage: float = 0.01  # %1
) -> float:
    # Risk miktarı ($)
    risk_amount = account_balance * (risk_percentage / 100.0)

    # Fiyat mesafesi
    price_distance = abs(entry_price - stop_loss_price)

    if price_distance <= 0:
        return 0.0

    # Formül: (Balance × Risk%) / |Entry - Stop|
    position_size = risk_amount / price_distance

    return position_size
```

**Örnek:**
```
Balance: $10,000
Risk: %1 → $100
Entry: $50,000
Stop: $49,000 (mesafe: $1,000)

Position Size = $100 / $1,000 = 0.1 BTC
Notional: 0.1 × $50,000 = $5,000
```

---

### 4.4 Kill Switch

Arka arkaya gelen zararlar (`consecutive_losses`) Risk Motorunda eşiği aştığında bot `risk.killswitch_activated` olayını fırlatıp alım-satımı durdurur.

```python
# ✅ Kill Switch (core/risk/risk_engine.py)
class RiskEngine:
    def __init__(self, config: RiskConfig):
        self.consecutive_losses = 0
        self.kill_switch_active = False

    def record_loss(self):
        """Kayıp kaydet ve kill switch kontrol et"""
        self.consecutive_losses += 1

        if self.consecutive_losses >= self.config.max_consecutive_losses:
            self.activate_kill_switch()

    def record_profit(self):
        """Kar kaydet ve consecutive losses sıfırla"""
        self.consecutive_losses = 0

    def activate_kill_switch(self):
        """Kill switch aktif et"""
        self.kill_switch_active = True

        # Event yayınla
        event = Event(
            type="risk.killswitch_activated",
            payload={
                "reason": f"Consecutive losses: {self.consecutive_losses}",
                "max_allowed": self.config.max_consecutive_losses
            }
        )
        await event_bus.publish(event)

        logger.critical(f"🚨 KILL SWITCH AKTİF: {self.consecutive_losses} ardışık kayıp")

    def can_open_position(self) -> bool:
        """Pozisyon açılabilir mi?"""
        if self.kill_switch_active:
            return False  # ❌ Kill switch aktif

        return True  # ✅ Açılabilir
```

---

## 5. POST-MORTEM (KRİTİK HATA HAFIZASI)

*Herhangi bir refactoring veya yeni kod üretiminde aşağıdaki mimari çöküşleri (anti-pattern) tekrarlama:*

### 5.1 Zombie Position (UnboundLocalError)

**Hata:** `position_manager.py` içinde modül importlarının fonksiyon içinde yapılması (Global Scope ihlali), kilitlerin (`is_closing = True`) açık kalmasına ve saniyede bir Stop-Loss emri gönderen sonsuz hata döngülerine (Zombie Loop) yol açmıştır.

```python
# ❌ YASAK: Import fonksiyon içinde
def close_position(bot_id):
    from core.trading.position_manager import PositionManager  # HATA!
    is_closing = True
    # ... kod ...
    # is_closing = False unutuldu → Zombie Loop!

# ✅ ZORUNLU: Import dosya tepesinde
from core.trading.position_manager import PositionManager  # ✅ Global scope

def close_position(bot_id):
    try:
        is_closing = True
        # ... kod ...
    finally:
        is_closing = False  # ✅ Finally ile kilidi serbest bırak
```

**Kural:** DDD nesnelerini her zaman dosyanın tepesinde import et ve `finally` bloğuyla kilidi serbest bırak.

---

### 5.2 Event-Bus By-Pass (Race Condition)

**Hata:** Olayları `asyncio.create_task` ile fırlatmak, Event-Bus'ın 3 paralel worker'a sahip backpressure mimarisini ezmiş ve asenkron I/O kilitlenmelerine neden olmuştur.

```python
# ❌ YASAK: create_task ile by-pass
async def on_signal(self, signal):
    asyncio.create_task(event_bus.publish(signal))  # HATA! Backpressure ezildi

# ✅ ZORUNLU: Doğrudan await
async def on_signal(self, signal):
    await event_bus.publish(signal)  # ✅ Queue'ya eklendi
```

**Kural:** Doğrudan `await event_bus.publish()` kullan.

---

### 5.3 Dict Manipülasyon Çöküşü (`NameError`)

**Hata:** `on_position_closed` handler'ında Immutable nesneler yerine primitive dict'e (`trade_data`) dönülmesi sistemi çökertmiştir.

```python
# ❌ YASAK: Primitive dict
def on_position_closed(self, bot_id):
    trade_data = {
        'bot_id': bot_id,
        'pnl': 100.50
    }
    save_trade(trade_data['bot_idd'])  # Typo → NameError!

# ✅ ZORUNLU: Trade Value Object
def on_position_closed(self, bot_id):
    trade = Trade(
        bot_id=bot_id,
        pnl=100.50
    )
    save_trade(trade.bot_id)  # ✅ Type-safe
```

**Kural:** Her zaman `Trade` Value Object'i oluştur ve veritabanına Type-Safe geçir.

---

### 5.4 CPU-Bound Starvation

**Hata:** Raporlama API uç noktasında (`get_strategy_report`) ağır Pandas groupby işlemlerinin doğrudan `await` edilmesi WebSocket Tick akışını dondurmuştur.

```python
# ❌ YASAK: CPU-bound ana event loop'da
@app.get("/strategy/report")
async def get_strategy_report():
    df = load_trade_history()
    report = df.groupby('symbol')['pnl'].sum()  # HATA! Event loop dondu
    return report

# ✅ ZORUNLU: Thread Pool'a delege et
@app.get("/strategy/report")
async def get_strategy_report():
    report = await asyncio.to_thread(
        lambda: df.groupby('symbol')['pnl'].sum()
    )  # ✅ Thread Pool
    return report
```

**Kural:** Senkron/Ağır fonksiyonları `asyncio.to_thread()` ile sarmala.

---

### 5.5 Flip Bug

**Hata:** LONG ve SHORT yönlerinin ters çalışarak stratejiyi patlatması.

```python
# ❌ YASAK: Tip doğrulaması yok
if signal == 2:
    direction = "SHORT"  # HATA! Ters!
elif signal == 0:
    direction = "LONG"   # HATA! Ters!

# ✅ ZORUNLU: Enum ile tip doğrulaması
from shared.events.events import PositionDirection, SignalType

if signal == SignalType.LONG:  # 2
    direction = PositionDirection.LONG  # ✅
elif signal == SignalType.SHORT:  # 0
    direction = PositionDirection.SHORT  # ✅
```

**Kural:** Sinyal kontrol yapılarında (`PositionDirection.LONG`, `PositionDirection.SHORT`) tip doğrulamasını zorunlu kıl.

---

### 5.6 Küçük Dosya Problemi (Disk I/O)

**Hata:** Data Lake'e her mumda (tick) Parquet dosyası yazma hatası.

```python
# ❌ YASAK: Her tick'te disk yazma
async def on_candle(self, candle):
    df = pd.DataFrame([candle])
    df.to_parquet(f"data/lake/{candle['symbol']}.parquet")  # HATA! Disk şişti

# ✅ ZORUNLU: Mikro-batching (5000 satır)
async def on_candle(self, candle):
    self.buffer.append(candle)

    if len(self.buffer) >= 5000:  # ✅ Batch size
        await self._flush_to_parquet()
```

**Kural:** Buffer bellekte mikro-yığınlar oluştur (örn. 5000 satır) ve asenkron Thread Pool kullanarak periyodik diske yaz.

---

## 6. PROJE YAPISI (FILE TREE)

```
f:\Crypto Bot\
├── api/                        # FastAPI routers
│   ├── bot.py                  # Bot endpoints
│   ├── ml.py                   # ML endpoints
│   ├── strategy.py             # Strategy endpoints
│   └── server.py               # FastAPI app
│
├── core/                       # Core engine
│   ├── bot/                    # Bot management
│   ├── risk/                   # Risk engine
│   │   └── risk_engine.py      # Risk calculations
│   ├── trading/                # Trading execution
│   │   └── position_manager.py # Position lifecycle
│   ├── exchange.py             # Binance connector
│   ├── paper.py                # Paper trader
│   └── wfo_engine.py           # Walk-forward optimization
│
├── data/                       # Data layer
│   ├── lake/                   # Parquet data lake
│   └── features.py             # Feature engineering
│
├── frontend/                   # Vanilla JS UI
│   ├── components/             # UI components
│   ├── services/               # API client
│   │   └── api-client.js       # Centralized API
│   ├── state/                  # State management
│   │   └── store.js            # Centralized store
│   └── app.js                  # Main entry
│
├── ml/                         # Machine learning
│   ├── data_prep.py            # Triple barrier
│   ├── model_training.py       # XGBoost/RF
│   └── server.py               # ML inference
│
├── models/                     # Database models
│ ├── position.py               # Position entity
│ └── trade.py                  # Trade entity
│
├── shared/                     # Shared utilities
│   └── events/                 # Event bus
│       ├── event_bus.py        # Pub/Sub
│       └── events.py           # Event types
│
├── strategy/                   # Trading strategies
│   ├── base.py                 # Abstract base
│   ├── manager.py              # Strategy manager
│   ├── confluence.py           # Confluence strategy
│   └── adaptive_koncorde.py    # Kalman filter
│
├── docs/                       # Documentation
│   └── architecture/           # Architecture docs
│       ├── MASTER_PROJE_DESTANI.md
│       ├── TRADING_RULES_AND_RISK.md
│       └── TASKS_AND_TRACEABILITY.md
│
└── knowledge/                  # Knowledge base
    ├── architecture/           # Architecture guides
    ├── concepts/               # Trading concepts
    ├── features/               # Feature guides
    └── strategies/             # Strategy docs
```

---

## 7. DOKÜMANTASYON GÜNCELLEME KURALI

**ÖNEMLİ:** Her kod değişikliğinden sonra `docs/architecture/` klasöründeki 3 dokümanın otomatik güncellenmesi **ZORUNLUDUR**:

1.  **MASTER_PROJE_DESTANI.md** - Mimari değişiklikler
2.  **TASKS_AND_TRACEABILITY.md** - Görev izlenebilirliği
3.  **TRADING_RULES_AND_RISK.md** - Risk parametreleri

```python
# ✅ Kod değişikliği sonrası otomatik dokümantasyon
def update_codebase(change_description: str):
    # 1. Kodu değiştir
    apply_code_change(change_description)

    # 2. Dokümanları güncelle
    update_architecture_docs(change_description)

    logger.info("✅ Kod ve dokümantasyon güncellendi")
```

---

## 8. ÖZET TABLOSU

| Kategori | Kural | Durum |
|----------|-------|-------|
| **Event Bus** | `await event_bus.publish()` (create_task YASAK) | ✅ ZORUNLU |
| **CPU-Bound** | `asyncio.to_thread()` ile sarmala | ✅ ZORUNLU |
| **Data Lake** | Mikro-batching (5000 satır) + Parquet | ✅ ZORUNLU |
| **DDD** | Value Object (Trade, Position) kullan | ✅ ZORUNLU |
| **Frontend** | ES6 Modules + Optional Chaining | ✅ ZORUNLU |
| **Indicators** | NumPy vektörize (pandas_ta YASAK) | ✅ ZORUNLU |
| **Data Integrity** | `replace([inf, -inf], NaN).fillna(0)` | ✅ ZORUNLU |
| **ML** | Triple Barrier + Split-before-Scale | ✅ ZORUNLU |
| **Signals** | 0=SAT, 1=BEKLE, 2=AL | ✅ ZORUNLU |
| **Confluence** | 3-teyit (Trend + Momentum + Smart Money) | ✅ ZORUNLU |
| **HTF Veto** | Multi-timeframe trend kontrolü | ✅ ZORUNLU |
| **Paper Trader** | Slippage %0.01 + Fee %0.04 | ✅ ZORUNLU |
| **Trailing Stop** | ATR bazlı + Ratchet (tek yönlü) | ✅ ZORUNLU |
| **Position Sizing** | (Balance × Risk%) / \|Entry - Stop\| | ✅ ZORUNLU |
| **Kill Switch** | Ardışık kayıp ≥ 5 → Durdur | ✅ ZORUNLU |

---

**Doküman Versiyonu:** v5.0 (Mart 2026)  
**Mimari Durum:** ✅ Production-Ready (14/14 E2E Test Passed)  
**Skill Dosyası:** `skill.md`

---

## 📚 KAYNAKLAR

- **MASTER_PROJE_DESTANI.md** - Mimari evrim ve Event-Driven geçiş
- **TRADING_RULES_AND_RISK.md** - Risk parametreleri ve formüller
- **TASKS_AND_TRACEABILITY.md** - Görev izlenebilirliği
- **knowledge/** - Detaylı konsept rehberleri
- **docs/** - Teknik dokümantasyon
