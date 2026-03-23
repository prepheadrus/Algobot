# ARCHITECTURE BILGI BANKASI
Son Guncelleme: 08/03/2026 22:58

---



## KAYNAK DOSYA: 1-to-N-multi-bot-architecture.md

# 1-to-N Multi-Bot Architecture (Çoklu Bot Mimarisi)

## Genel Bakış

1-to-N mimarisi, aynı sembol üzerinde birden fazla botun paralel olarak çalışmasını sağlayan merkezi dinleyici, dağıtık işleyici (Centralized Fetch, Distributed Execution) yapısıdır.

**Tarih:** Mart 2026  
**Durum:** ✅ Production Ready  
**Versiyon:** 1.0

---

## Mimari Prensipler

### 1. Merkezi Veri Çekimi (Centralized Fetch)
- Her sembol için SADECE 1 kez borsaya istek gönderilir
- Rate limit koruması sağlar (IP ban önlenir)
- Tek bir DataFrame oluşturulur

### 2. Dağıtık İşleme (Distributed Execution)
- Çekilen veri, o sembol için aktif TÜM botlara broadcast edilir
- Her bot kendi stratejisini bağımsız çalıştırır
- Bot'lar birbirini beklemez (non-blocking)

### 3. Asenkron İzolasyon (Async Isolation)
- Her bot `asyncio.create_task()` ile ayrı task olarak çalışır
- `asyncio.gather(*tasks, return_exceptions=True)` ile paralel yürütülür
- Bir bot çökerse diğerleri etkilenmez (error isolation)

### 4. Bot İzolasyonu (Bot Isolation)
- Her bot kendi `bot_id`'si ile izole edilir
- Pozisyonlar bot bazında tutulur
- PnL hesaplaması bot bazında yapılır
- Her bot kendi strateji instance'ına sahiptir

---

## Veri Akışı

```
┌─────────────────────────────────────────────────────────┐
│ 1. API Endpoint (POST /api/v1/bot/start)               │
│    - Kullanıcı bot başlatır                            │
│    - Bot bilgileri: symbol, strategy_id, timeframe     │
│    - bot_id oluştur: {symbol}_{market}_{strategy}_{tf} │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Strateji Instance Oluşturma                          │
│    - StrategyManager.get_strategy(strategy_id)         │
│    - paper_engine.strategies[symbol] = instance        │
│    - paper_engine.active_strategies[symbol] = id       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 3. Bot Dict'e Ekleme (active_bots)                      │
│    - paper_engine.active_bots[bot_id] = {info}         │
│    - bot_state[bot_id] = {balance, pnl, ...}           │
│    - bot_positions[bot_id] = []                        │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Poller Başlatma (Merkezi Dinleyici)                 │
│    - exchange_manager.active_pollers[symbol] kontrol   │
│    - Yoksa: asyncio.create_task(run_strategy_poller)   │
│    - Task'ı kaydet: active_pollers[symbol] = task      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 5. Merkezi Poller Döngüsü (Her Sembol İçin 1 Kez)      │
│    - run_strategy_poller(symbol, timeframe)            │
│    - Borsadan OHLCV çek (1 kez!)                       │
│    - Resample (1m → hedef TF)                          │
│    - İndikatörler hesapla                              │
│    - HTF trend, market regime tespit et                │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 6. Aktif Botları Bul (Broadcast Listesi)               │
│    - active_bots dict'ini tara                         │
│    - Bu sembol için tüm aktif botları bul              │
│    - active_bot_ids = [bot1, bot2, bot3, ...]          │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 7. Paralel İşleme (asyncio.gather)                      │
│    - Her bot için task oluştur:                        │
│      task = create_task(process_bot_signal(bot_id))    │
│    - Tüm task'ları topla: tasks = [t1, t2, t3, ...]    │
│    - PARALEL çalıştır: await gather(*tasks)            │
│    - return_exceptions=True (hata izolasyonu)          │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 8. Bot İşleme (Her Bot İçin İzole)                     │
│    - process_bot_signal(bot_id, df, price, ...)        │
│    - Strateji sinyali üret                             │
│    - ML confidence kontrol                             │
│    - Confluence (Strateji + ML)                        │
│    - Pozisyon aç/kapat (bot_id ile izole)              │
│    - PnL hesapla (bot bazında)                         │
└─────────────────────────────────────────────────────────┘
```

---

## Kritik Dosyalar

### `core/paper.py` - PaperTrader (Bot Yönetimi)

```python
class PaperTrader:
    # Bot State Dict'leri
    active_bots = {}      # bot_id → {symbol, strategy_id, timeframe, ...}
    bot_positions = {}    # bot_id → [pozisyonlar]
    bot_state = {}        # bot_id → {balance, pnl, margin, ...}
    
    # Strateji Yönetimi
    strategies = {}              # symbol → Strategy instance
    active_strategies = {}       # symbol → strategy_id
    
    # Bot İşleme
    def start_bot(symbol, strategy_id, timeframe, ...) → bot_id
    def stop_bot(bot_id) → bool
    def get_bot_status(bot_id) → dict
    def get_all_bots() → list
    
    # Sinyal İşleme (ASYNC)
    async def process_bot_signal(bot_id, df, current_price, ...)
    async def _open_new_position(..., bot_id=None)
```

### `core/exchange.py` - ExchangeManager (Merkezi Poller)

```python
class ExchangeManager:
    # Poller Takibi
    active_pollers = {}  # symbol → asyncio.Task
    
    # Merkezi Poller
    async def run_strategy_poller(symbol, timeframe)
    async def _process_bot_task(paper_engine, bot_id, df, price, ...)
    
    # Bot Broadcast
    active_bot_ids = [
        bot_id for bot_id, bot_info in paper_engine.active_bots.items()
        if bot_info['symbol'] == symbol and bot_info['status'] == 'running'
    ]
    
    # Paralel İşleme
    bot_tasks = []
    for bot_id in active_bot_ids:
        task = asyncio.create_task(
            self._process_bot_task(paper_engine, bot_id, df, price, ...)
        )
        bot_tasks.append(task)
    
    results = await asyncio.gather(*bot_tasks, return_exceptions=True)
```

### `api/server.py` - API Endpoints

```python
@app.post("/api/v1/bot/start")
async def start_bot(data: Dict):
    # 1. Bot başlat
    bot_id = paper_engine.start_bot(...)
    
    # 2. Strateji instance oluştur ve kaydet
    strategy_instance = StrategyManager.get_strategy(strategy_id)
    paper_engine.strategies[symbol] = strategy_instance
    paper_engine.active_strategies[symbol] = strategy_id
    
    # 3. Poller başlat (eğer yoksa)
    if symbol not in exchange_manager.active_pollers:
        poller_task = asyncio.create_task(
            exchange_manager.run_strategy_poller(symbol, timeframe)
        )
        exchange_manager.active_pollers[symbol] = poller_task
    
    return {"status": "success", "bot_id": bot_id}

@app.post("/api/v1/bot/stop")
async def stop_bot(data: Dict):
    paper_engine.stop_bot(bot_id)

@app.get("/api/v1/bots/list")
async def get_all_bots():
    bots = paper_engine.get_all_bots()
    return {"status": "success", "bots": bots}
```

### `frontend/app.js` - Frontend (Bot Yönetimi UI)

```javascript
// Bot Başlatma Formu (Event Delegation)
document.addEventListener('submit', async function(e) {
    if (e.target && e.target.id === 'bot-start-form') {
        e.preventDefault();
        
        const symbol = document.getElementById('bot-symbol').value;
        const strategy = document.getElementById('bot-strategy').value;
        const timeframe = document.getElementById('bot-timeframe').value;
        const market = document.getElementById('bot-market').value;
        
        await startBot(symbol, strategy, timeframe, market);
        await loadActiveBots();
        e.target.reset();
    }
});

// Bot İşlemleri
async function startBot(symbol, strategy, timeframe, market)
async function stopBot(bot_id)
async function resumeBot(bot_id)
async function removeBot(bot_id)
async function loadActiveBots()
```

---

## Bot ID Formatı

```
{symbol}_{market_type}_{strategy_id}_{timeframe}

Örnekler:
- BTC_USDT_USDT_future_trend_master_1m
- BTC_USDT_USDT_future_adaptive_koncorde_15m
- ETH_USDT_USDT_future_scalper_ninja_5m
- BNB_USDT_USDT_spot_golden_combo_1h
```

---

## Örnek Senaryo: Aynı Coin, 3 Bot

**Kullanıcı aksiyonu:**
1. Bot 1: BTC/USDT:USDT, TrendMaster, 1m
2. Bot 2: BTC/USDT:USDT, ScalperNinja, 5m
3. Bot 3: BTC/USDT:USDT, AdaptiveKoncorde, 15m

**Sistem davranışı:**

```python
# 1. Poller SADECE 1 kez başlatılır
active_pollers = {
    "BTC/USDT:USDT": <Task #1>  # Tek poller, tüm botları besler
}

# 2. Her mum kapanışında (1m):
active_bot_ids = [
    "BTC_USDT_USDT_future_trend_master_1m",
    "BTC_USDT_USDT_future_scalper_ninja_5m",
    "BTC_USDT_USDT_future_adaptive_koncorde_15m"
]

# 3. PARALEL işleme (asyncio.gather):
bot_tasks = [
    create_task(process_bot_signal(bot1)),
    create_task(process_bot_signal(bot2)),
    create_task(process_bot_signal(bot3))
]

results = await asyncio.gather(*bot_tasks, return_exceptions=True)

# 4. Sonuçlar:
# - Bot 1 (1m): 0.5 saniye → ✅
# - Bot 2 (5m): 0.3 saniye → ✅
# - Bot 3 (15m): 2.0 saniye → ✅
# TOPLAM: 2.0 saniye (seri olsaydı 2.8 saniye olurdu)
```

---

## Hata Yönetimi

### Bot Bazında Hata İzolasyonu

```python
try:
    results = await asyncio.gather(*bot_tasks, return_exceptions=True)
    
    for bot_id, result in zip(active_bot_ids, results):
        if isinstance(result, Exception):
            logger.error(f"❌ [BOT] {bot_id} işleme hatası: {result}")
            # DİĞER BOTLAR ETKİLENMEZ!
        else:
            logger.debug(f"✅ [BOT] {bot_id} başarıyla işlendi")
except Exception as gather_err:
    logger.error(f"❌ [1-to-N] Gather hatası: {gather_err}")
```

### Poller Çökme Koruması

```python
while True:
    try:
        # Poller döngüsü
        ...
    except asyncio.CancelledError:
        break  # Temiz çıkış
    except Exception as e:
        logger.error(f"Strateji Döngü Hatası ({symbol}): {e}")
        logger.error(traceback.format_exc())
        await asyncio.sleep(10)  # 10 saniye bekle, tekrar dene
```

---

## Performans Metrikleri

| Metrik | Değer | Açıklama |
|--------|-------|----------|
| **API Çağrıları** | 1/sem bol | Rate limit koruması |
| **Bot İşleme Süresi** | max(bot_süreleri) | Paralel işleme sayesinde |
| **Hata İzolasyonu** | %100 | Bir bot çökerse diğerleri çalışır |
| **Bellek Kullanımı** | O(bot_sayısı) | Her bot izole state tutar |
| **CPU Kullanımı** | O(bot_sayısı) | Async/await ile optimize |

---

## Avantajlar

### ✅ Rate Limit Koruması
- Her sembol için 1 API çağrısı
- 10 bot olsa bile 1 çağrı
- IP ban riski minimal

### ✅ Performans
- Paralel işleme (asyncio.gather)
- Bot'lar birbirini beklemez
- Toplam süre = en yavaş bot'un süresi

### ✅ Hata İzolasyonu
- Bir bot çökerse diğerleri etkilenmez
- return_exceptions=True ile güvenli
- Ana poller asla durmaz

### ✅ Ölçeklenebilirlik
- Sınırsız bot sayısı
- Her sembol için 1 poller
- Kaynak kullanımı lineer

### ✅ Kod Temizliği
- Eski monolitik yapı kaldırıldı
- Modüler, test edilebilir kod
- Her bot izole test edilebilir

---

## Test Senaryoları

### Senaryo 1: Aynı Coin, Farklı Timeframe'ler

```bash
# Bot başlat
Bot 1: BTC/USDT, TrendMaster, 1m
Bot 2: BTC/USDT, TrendMaster, 5m
Bot 3: BTC/USDT, TrendMaster, 15m

# Beklenen:
✅ 1 poller başlatılır (BTC/USDT:USDT)
✅ 3 bot PARALEL işlenir
✅ Her bot kendi timeframe'inde çalışır
✅ Toplam süre: max(1m_süre, 5m_süre, 15m_süre)
```

### Senaryo 2: Aynı Coin, Farklı Stratejiler

```bash
# Bot başlat
Bot 1: BTC/USDT, TrendMaster, 1m
Bot 2: BTC/USDT, ScalperNinja, 1m
Bot 3: BTC/USDT, AdaptiveKoncorde, 1m

# Beklenen:
✅ 1 poller başlatılır (BTC/USDT:USDT)
✅ 3 bot PARALEL işlenir
✅ Her bot kendi stratejisini kullanır
✅ Pozisyonlar izole (bot_id ile)
```

### Senaryo 3: Bot Çökme Testi

```bash
# Bot başlat
Bot 1: BTC/USDT, TrendMaster, 1m (SAĞLAM)
Bot 2: BTC/USDT, ScalperNinja, 1m (HATA VERİR)
Bot 3: BTC/USDT, AdaptiveKoncorde, 1m (SAĞLAM)

# Beklenen:
✅ Bot 2 çöker (exception)
✅ Bot 1 ve 3 ÇALIŞMAYA DEVAM EDER
✅ Ana poller DURMAZ
✅ Hata loglanır (logger.error)
```

---

## Migration Guide (Eski → Yeni)

### Eski Mimari (Monolitik)

```python
# Her strateji için ayrı poller
for symbol in symbols:
    asyncio.create_task(run_strategy_poller(symbol))
    # ❌ Her strateji için ayrı API çağrısı
    # ❌ Rate limit sorunu
    # ❌ Performans düşük
```

### Yeni Mimari (1-to-N)

```python
# Her sembol için 1 poller, tüm botları besler
for symbol in symbols:
    if symbol not in active_pollers:
        asyncio.create_task(run_strategy_poller(symbol))
        # ✅ 1 API çağrısı
        # ✅ Tüm botlar beslenir
        # ✅ Rate limit koruması
```

---

## İlgili Dökümanlar

- [Walk-Forward Optimization](features/walk_forward_optimization.md)
- [Auto-Grid Generator](features/auto_grid_generator.md)
- [Bayesian Optimization](features/bayesian_optimization.md)
- [Paper Trader](trading_engine/paper_trader.md)

---

**Son Güncelleme:** Mart 2026  
**Yazar:** CryptoAlgoBot Team  
**Durum:** ✅ Production Ready


---


## KAYNAK DOSYA: data_pipeline.md

# 🧪 Veri Boru Hattı (Data Pipeline) ve Özellik Mühendisliği

Verinin borsadan akıp Yapay Zekaya (ML) sunulduğu hayati damardır.

## 1. Merkezileştirilmiş İndikatör Motoru (`data/indicators.py`)

Tüm sistemin matematik fabrikası burasıdır. Stratejiler içerisinde indikatör hesaplanmaz. Veri önce buraya girer, "Zenginleştirilir" (Feature Engineering) ve süslenmiş bir Excel (DataFrame) tablosu halinde dışarı çıkar.

### İndikatör Hesaplama Yöntemleri

**Öncelik Sırası:**
1. **TA-Lib** (C tabanlı, en hızlı) - Opsiyonel
2. **Manuel Hesaplama** (numpy/pandas) - Varsayılan

**Desteklenen İndikatörler:**

| Kategori | İndikatörler |
|----------|--------------|
| **Trend** | EMA, SMA, Kalman Filter, Supertrend, EWO |
| **Momentum** | RSI, MACD, Stochastic, UO |
| **Volatilite** | ATR, Bollinger Bands, BTC VIX |
| **Hacim** | OBV, VWAP, PVI, NVI, Koncorde |
| **Diğer** | ADX, PSAR, Demand Index, KNN |

### Manuel Hesaplama (pandas-ta Gerektirmez)

```python
# Örnek: RSI hesaplama
def rsi(series, length=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))
```

**Avantajlar:**
- ✅ Hiçbir external kütüphane gerektirmez
- ✅ Cross-platform (Windows, Linux, Mac)
- ✅ Derleme sorunları yok
- ✅ Kolayca yeni indikatör eklenebilir


## 2. Zaman Dilimi Dönüştürme (Resampling)
Uygulama arka planda Binance'dan hep 1D veya 1H değil, **1m (1 Dakikalık)** en saf (granüler) veriyi indirir. 
Kullanıcı Arayüz üzerinden `15m` simülasyonu çalıştır dediğinde, `indicators.py` sistem içindeki `resample_data` fonksiyonuyla o saniye (Milisaniyeler içinde) milyarlarca işlemi kaydırarak doğru birleştirir, 1 dakikalık mumlardan mükemmel bir "15 Dakikalık" veri tablosu çıkarır. Böylelikle borsaya "Bana 15m yolla, dur vazgeçtim 1H yolla" diye Spamlama (Banned/Limit Exceeded yeme) riskini ortadan kaldırır.

## 3. Veri Güvenliği ve Uyumluluğu
Veriler C (XGBoost) modeline ve ardından Frontend'e (Javascript) taşınırken `NaN`, `Infinity`, `-Infinity` gibi Python nesneleri büyük hatalar (500 Internal Error / JSON Decode Error) verir.
Bu sebeple `df.replace([np.inf, -np.inf], np.nan).fillna(0)` mantığı veri hattının güvenlik kilididir.
Zaman formatlarının Linux Epoch Date veya DateTime object karmaşıklığı yaratmasını önlemek adına Merkezi bir `ensure_ms(timestamp)` algoritması tüm sistemi senkronize milisaniyelere bağlar.


---


## KAYNAK DOSYA: overview.md

# 🏛 Sistem Mimarisi Genel Bakış (Architecture Overview)

Crypto Algo Bot projesi, modern veri mühendisliği, yapay zeka ve modüler yazılım prensipleriyle (Python & FastAPI) inşa edilmiş bir algoritmik ticaret ve analiz motorudur.

## 1. Katmanlı Yapı (Layered Architecture)

Sistem **5 Temel Katmandan** oluşur:
1. **Veri Sağlayıcı Katmanı (Data Provider):** `core/exchange.py`
   - CCXT kütüphanesi aracılığıyla Binance borsasına bağlanır.
   - Periyodik (Asynchronous Poller) olarak seçili coinlerin mum (OHLCV) verilerini sömürür.
2. **Özellik Çıkarımı Katmanı (Feature Engineering):** `data/indicators.py`
   - Alınan ham mum verilerinin üzerine teknik analiz modülleri oturtulur.
   - `pandas_ta` kütüphanesi merkezi olarak kullanılırken, Koncorde ve Kalman Filtresi gibi kütüphanesi olmayan kompleks denklemler özel algoritmalarla çözülüp sütun olarak eklenir.
3. **Teknik Karar Katmanı (Strategy Core):** `strategy/`
   - Tamamen izole edilmiş, safça "Kurallar Bütünü" barındıran katmandır. Trend Master, Golden Combo gibi şablonlar burada barınır. Sadece 0(SAT), 1(BEKLE), 2(AL) sinyali üretirler.
4. **Yapay Zeka & Simülasyon Katmanı (ML Inference & Paper Trade):** `api/server.py` & `core/paper.py`
   - Geçmiş stratejik kararları alan Yapay Zeka (XGBoost) tahminiyle, stratejiden gelen "AL" sinyalinin uyumlu (Konfluans) olduğu noktalarda `PaperTrader` motoruna emir iletilir.
   - Bu emir komisyon, sınır, bakiye, ve risk hesaplarından (Dinamik Kaldıraç & ATR) geçerek işlem dosyasına yazılır.
5. **Sunum Katmanı (Frontend):** `frontend/`
   - Kullanıcının doğrudan gördüğü vitrindir. TradingView Lightweight Charts entegredir. Lejantlar, interaktif tooltipler ve dinamik ondalık hesaplamalarla tam gerçekçi bir borsa terminali hissiyatı sunar.

## Temel Çalışma Döngüsü (Workflow)

[Binance'dan Ham Veri] 
      -> [indicators.py ile Veriyi Zenginleştir (MACD, ADX, VIX...)]
             -> [XGBoost Model Tahmini (0, 1, 2) + Güven Skoru] 
             -> [Seçili Strateji (Örn: Golden Combo) Kuralları Onayı (0, 1, 2)]
                    => {EĞER HER İKİSİ DE 2 VE GÜVEN > %65 İSE}
                           -> [PaperTrader'a Gönder -> Komisyon / Kayma Hesabı -> İŞLEME GİR]


---
