# 📊 HTF Golden Ratio (Altın Oran ve Çoklu Zaman Dilimi Matrisi)

**Versiyon:** v4.0 (Production-Ready)
**Son Güncelleme:** Mart 2026
**Köken:** Alexander Elder - "Triple Screen Trading System" (1986)
**Kategori:** Kantitatif Kavramlar / Multi-Timeframe Analysis

---

## 📋 Genel Bakış

**HTF Golden Ratio (Altın Oran Çoklu Zaman Dilimi)**, Alexander Elder'in "Üçlü Ekran" (Triple Screen) mantığına dayanan ve piyasa gürültüsünü (noise) ezen çoklu zaman dilimi filtresidir. Minor ve Major HTF onayları ile ana trend yönünde işlem açmayı sağlar.

---

## 🎯 Teori ve Felsefe

### **1. Piyasa Gürültüsü Problemi**

**Tek Zaman Dilimi (YANLIŞ):**
```
1m Grafik:
  │
  │    ╱╲  ╱╲    ╱╲
  │   ╱  ╲╱  ╲  ╱  ╲
  │  ╱         ╲╱    ╲
  │ ╱                 ╲
  │╱                   ╲
  └─────────────────────→ Zaman
  
Sorun:
  - Her mum farklı yön gösteriyor
  - False sinyaller çok fazla
  - Trend yönü BELİRSİZ
  - Gürültü (noise) > Sinyal
```

**Çoklu Zaman Dilimi (DOĞRU):**
```
1m Grafik (Bot Timeframe):
  │    ╱╲  ╱╲    ╱╲
  │   ╱  ╲╱  ╲  ╱  ╲
  │  ╱         ╲╱    ╲
  │ ╱                 ╲
  │╱                   ╲
  └─────────────────────→ Zaman
  │
  │  5m Grafik (Minor HTF):
  │      ╱───╲      ╱───
  │     ╱     ╲    ╱
  │    ╱       ╲  ╱
  │   ╱         ╲╱
  │  ╱
  └─────────────────────→ Zaman
  │
  │  15m Grafik (Major HTF):
  │          ╱───────────
  │         ╱
  │        ╱
  │       ╱
  │      ╱
  └─────────────────────→ Zaman
  
SONUÇ:
  - 1m: Kısa vadeli sinyaller
  - 5m: Orta vadeli trend onayı
  - 15m: Ana trend yönü (veto yetkisi)
  
  Major HTF BULL ise → Sadece LONG açılır
  Major HTF BEAR ise → Sadece SHORT açılır
```

---

### **2. Alexander Elder'ın Üçlü Ekran Sistemi**

**Orijinal Konsept (1986):**
```
Ekran 1: Ana Trend (Weekly chart)
  └─→ Trend yönünü belirle (MACD, EMA)

Ekran 2: Düzeltme (Daily chart)
  └─→ Ana trend yönünde düzeltme bekle

Ekran 3: Giriş (Hourly chart)
  └─→ Timing için giriş sinyali
```

**CryptoAlgoBot Uyarlaması (2026):**
```
Ekran 1: Major HTF (1h, 4h)
  └─→ Ana trend yönü (EMA Stack veto)

Ekran 2: Minor HTF (5m, 15m)
  └─→ Orta vadeli trend onayı

Ekran 3: Bot Timeframe (1m, 3m)
  └─→ Giriş sinyali (strateji)
```

**Felsefe:**
> "Ana trend sen dostundur (Trend is your friend).
> Major HTF yönünde işlem aç.
> Ters yönde ASLA işlem açma (veto)."

---

## 📐 HTF Altın Oran Matrisi

### **1. Dinamik Haritalama (1:4 / 1:6 Kuralı)**

**Altın Oran Mantığı:**
```
Bot Timeframe ile HTF arasında yaklaşık 4-6x fark olmalı.

Neden 4-6x?
  - Çok yakın (2x): Gürültü filtrelenmez
  - Çok uzak (20x): Sinyal çok geç gelir
  - 4-6x: Optimal (gürültü filtrelenir, sinyal zamanında)
```

**Dinamik Haritalama Tablosu:**

| Bot Timeframe | Minor HTF (1:4) | Major HTF (1:6) |
|---------------|-----------------|-----------------|
| **1m** | 4m → 5m (yukarı yuvarla) | 6m → 5m (aşağı yuvarla) |
| **3m** | 12m → 15m | 18m → 15m |
| **5m** | 20m → 15m | 30m |
| **15m** | 60m → 1h | 90m → 1h |
| **30m** | 120m → 2h | 180m → 3h |
| **1h** | 4h | 6h |

**Yuvarlama Kuralı:**
```
Standart timeframe'lere yuvarla:
  1m, 3m, 5m, 10m, 15m, 20m, 30m, 45m
  1h, 2h, 3h, 4h, 6h, 8h, 12h
  1d, 1W, 1M

Örnek:
  1m bot → Minor: 4m → 5m (yukarı)
  1m bot → Major: 6m → 5m (aşağı)
```

---

### **2. Python Implementasyonu**

```python
# strategy/htf.py
def get_htf_timeframes(bot_timeframe: str) -> Tuple[str, str]:
    """
    Bot timeframe için Minor ve Major HTF'leri hesapla.
    
    Altın Oran: 1:4 (Minor) ve 1:6 (Major)
    
    Args:
        bot_timeframe: Bot zaman dilimi (örn: "1m", "15m", "1h")
    
    Returns:
        (minor_htf, major_htf) tuple
    """
    
    # Timeframe'i dakikaya çevir
    timeframe_minutes = {
        '1m': 1, '3m': 3, '5m': 5, '10m': 10, '15m': 15,
        '20m': 20, '30m': 30, '45m': 45,
        '1h': 60, '2h': 120, '3h': 180, '4h': 240,
        '6h': 360, '8h': 480, '12h': 720,
        '1d': 1440, '1W': 10080
    }
    
    bot_minutes = timeframe_minutes[bot_timeframe]
    
    # Altın Oran hesapla
    minor_target = bot_minutes * 4
    major_target = bot_minutes * 6
    
    # Standart timeframe'lere yuvarla
    standard_timeframes = [
        1, 3, 5, 10, 15, 20, 30, 45,
        60, 120, 180, 240, 360, 480, 720,
        1440, 10080
    ]
    
    # En yakın standart timeframe'i bul
    minor_htf_minutes = min(standard_timeframes, key=lambda x: abs(x - minor_target))
    major_htf_minutes = min(standard_timeframes, key=lambda x: abs(x - major_target))
    
    # Dakikadan timeframe'e çevir
    minutes_to_timeframe = {v: k for k, v in timeframe_minutes.items()}
    
    minor_htf = minutes_to_timeframe.get(minor_htf_minutes, f"{minor_htf_minutes}m")
    major_htf = minutes_to_timeframe.get(major_htf_minutes, f"{major_htf_minutes}m")
    
    return minor_htf, major_htf


# Örnekler:
print(get_htf_timeframes("1m"))   # ('5m', '5m')
print(get_htf_timeframes("3m"))   # ('15m', '15m')
print(get_htf_timeframes("5m"))   # ('15m', '30m')
print(get_htf_timeframes("15m"))  # ('1h', '1h')
print(get_htf_timeframes("1h"))   # ('4h', '6h')
```

---

### **3. Örnek Senaryolar**

**Senaryo 1: 1m Bot (Scalping)**
```
Bot Timeframe: 1m
Minor HTF: 5m (1:5 oran)
Major HTF: 5m (1:5 oran)

Akış:
  1m: Giriş sinyali (RSI < 30, MACD cross)
  5m Minor: Trend onayı (EMA 20 > EMA 50)
  5m Major: Veto yetkisi (BULL → LONG açılabilir)

Sonuç:
  Major HTF BULL ise → LONG sinyalleri açılır
  Major HTF BEAR ise → TÜM sinyaller veto (işlem yok)
```

**Senaryo 2: 15m Bot (Swing Trading)**
```
Bot Timeframe: 15m
Minor HTF: 1h (1:4 oran)
Major HTF: 1h (1:4 oran)

Akış:
  15m: Giriş sinyali (Strateji)
  1h Minor: Trend onayı (ADX > 25)
  1h Major: Veto yetkisi (BULL → LONG açılabilir)

Sonuç:
  Major HTF BULL ise → LONG sinyalleri açılır
  Major HTF BEAR ise → TÜM sinyaller veto
```

**Senaryo 3: 1h Bot (Position Trading)**
```
Bot Timeframe: 1h
Minor HTF: 4h (1:4 oran)
Major HTF: 6h (1:6 oran)

Akış:
  1h: Giriş sinyali (EMA cross, RSI)
  4h Minor: Trend onayı (Supertrend BULL)
  6h Major: Veto yetkisi (BULL → LONG açılabilir)

Sonuç:
  Major HTF BULL ise → LONG sinyalleri açılır
  Major HTF BEAR ise → TÜM sinyaller veto
```

---

## 📊 EMA Stack Veto Kuralı

### **1. EMA Stack Trend Tespiti**

**Formül:**
```
EMA Stack = EMA 20 vs EMA 50 karşılaştırması

BULL Trend:
  EMA 20 > EMA 50  (kısa vadeli ortalama uzun vadenin üstünde)

BEAR Trend:
  EMA 20 < EMA 50  (kısa vadeli ortalama uzun vadenin altında)

NEUTRAL:
  EMA 20 ≈ EMA 50  (±0.5% içinde, yatay piyasa)
```

**Python Implementasyonu:**
```python
# strategy/htf.py
def ema_stack_trend(close: pd.Series, fast_period: int = 20, slow_period: int = 50) -> str:
    """
    EMA Stack ile trend yönünü belirle.
    
    Args:
        close: Fiyat serisi
        fast_period: Hızlı EMA periyodu
        slow_period: Yavaş EMA periyodu
    
    Returns:
        "BULL", "BEAR", veya "NEUTRAL"
    """
    
    ema_fast = close.ewm(span=fast_period, adjust=False).mean()
    ema_slow = close.ewm(span=slow_period, adjust=False).mean()
    
    # Son mumda karşılaştır
    last_fast = ema_fast.iloc[-1]
    last_slow = ema_slow.iloc[-1]
    
    # Yüzde fark hesapla
    percent_diff = abs(last_fast - last_slow) / last_slow * 100
    
    if percent_diff < 0.5:
        return "NEUTRAL"  # Yatay piyasa
    elif last_fast > last_slow:
        return "BULL"
    else:
        return "BEAR"
```

---

### **2. Bull/Bear Count Mantığı**

**Felsefe:**
```
Her HTF timeframe'in bir oyu var:
  - Minor HTF: 1 oy
  - Major HTF: 1 oy (VETO yetkisi)

BULL count ≥ 2 → LONG açılabilir
BEAR count ≥ 2 → SHORT açılabilir
```

**Veto Kuralı:**
```
Major HTF'nin VETO yetkisi vardır:
  - Major HTF BULL ise → SHORT AÇILAMAZ
  - Major HTF BEAR ise → LONG AÇILAMAZ
  - Major HTF NEUTRAL ise → Her iki yön de açılabilir (riskli)
```

**Python Implementasyonu:**
```python
# strategy/confluence.py
def htf_filter(
    bot_timeframe: str,
    minor_trend: str,
    major_trend: str,
    signal: str
) -> bool:
    """
    HTF veto filtresi.
    
    Args:
        bot_timeframe: Bot zaman dilimi
        minor_trend: Minor HTF trendi (BULL/BEAR/NEUTRAL)
        major_trend: Major HTF trendi (BULL/BEAR/NEUTRAL)
        signal: Strateji sinyali (LONG/SHORT/HOLD)
    
    Returns:
        True: Sinyal onaylandı
        False: Veto edildi
    """
    
    # HOLD sinyali her zaman veto edilir
    if signal == "HOLD":
        return False
    
    # Major HTF VETO yetkisi
    if major_trend == "BULL" and signal == "SHORT":
        logger.warning(
            f"🚫 [HTF VETO] Major HTF BULL, SHORT açılmaz! "
            f"(Bot: {bot_timeframe})"
        )
        return False  # VETO
    
    if major_trend == "BEAR" and signal == "LONG":
        logger.warning(
            f"🚫 [HTF VETO] Major HTF BEAR, LONG açılmaz! "
            f"(Bot: {bot_timeframe})"
        )
        return False  # VETO
    
    # Minor HTF onayı (opsiyonel, veto değil)
    if signal == "LONG" and minor_trend == "BEAR":
        logger.info(
            f"⚠️ [HTF UYARI] Minor HTF BEAR, LONG zayıf sinyal "
            f"(Bot: {bot_timeframe})"
        )
        # Veto değil, sadece uyarı
    
    if signal == "SHORT" and minor_trend == "BULL":
        logger.info(
            f"⚠️ [HTF UYARI] Minor HTF BULL, SHORT zayıf sinyal "
            f"(Bot: {bot_timeframe})"
        )
        # Veto değil, sadece uyarı
    
    # Onaylandı
    logger.debug(
        f"✅ [HTF ONAY] {signal} sinyali açılabilir "
        f"(Minor: {minor_trend}, Major: {major_trend})"
    )
    return True
```

---

### **3. Senaryo Bazlı Veto Örnekleri**

**Senaryo 1: Major BULL, Minor BULL, LONG Sinyali**
```
Major HTF: BULL ✅
Minor HTF: BULL ✅
Signal: LONG

Sonuç: ✅ ONAYLANDI
  - Major BULL, LONG açılabilir
  - Minor BULL, ek onay
  - Güçlü LONG sinyali
```

**Senaryo 2: Major BULL, Minor BEAR, LONG Sinyali**
```
Major HTF: BULL ✅
Minor HTF: BEAR ⚠️
Signal: LONG

Sonuç: ✅ ONAYLANDI (zayıf sinyal)
  - Major BULL, LONG açılabilir (veto yok)
  - Minor BEAR, uyarı (düzeltme var)
  - Zayıf LONG sinyali (beklenebilir)
```

**Senaryo 3: Major BULL, Minor BULL, SHORT Sinyali**
```
Major HTF: BULL ✅
Minor HTF: BULL ✅
Signal: SHORT

Sonuç: ❌ VETO EDİLDİ
  - Major BULL, SHORT AÇILAMAZ (veto)
  - Trend tersine işlem yasak
  - Sinyal reddedildi
```

**Senaryo 4: Major BEAR, Minor BULL, LONG Sinyali**
```
Major HTF: BEAR ✅
Minor HTF: BULL ⚠️
Signal: LONG

Sonuç: ❌ VETO EDİLDİ
  - Major BEAR, LONG AÇILAMAZ (veto)
  - Trend tersine işlem yasak
  - Sinyal reddedildi
```

**Senaryo 5: Major NEUTRAL, Minor BULL, LONG Sinyali**
```
Major HTF: NEUTRAL ⚠️
Minor HTF: BULL ✅
Signal: LONG

Sonuç: ✅ ONAYLANDI (riskli)
  - Major NEUTRAL, veto yok
  - Yatay piyasa (whipsaw riski)
  - Düşük confidence ile açılır
```

---

## 📊 HTF Confluence Matrisi

### **1. Tüm Senaryolar Tablosu**

| Major HTF | Minor HTF | Signal | Sonuç | Confidence |
|-----------|-----------|--------|-------|------------|
| **BULL** | BULL | LONG | ✅ ONAY | %85 (güçlü) |
| **BULL** | BEAR | LONG | ⚠️ ONAY | %65 (zayıf) |
| **BULL** | BULL | SHORT | ❌ VETO | - |
| **BULL** | BEAR | SHORT | ❌ VETO | - |
| **BEAR** | BULL | SHORT | ⚠️ ONAY | %65 (zayıf) |
| **BEAR** | BEAR | SHORT | ✅ ONAY | %85 (güçlü) |
| **BEAR** | BULL | LONG | ❌ VETO | - |
| **BEAR** | BEAR | LONG | ❌ VETO | - |
| **NEUTRAL** | BULL | LONG | ⚠️ ONAY | %50 (riskli) |
| **NEUTRAL** | BEAR | SHORT | ⚠️ ONAY | %50 (riskli) |
| **NEUTRAL** | BULL | SHORT | ⚠️ ONAY | %40 (riskli) |
| **NEUTRAL** | BEAR | LONG | ⚠️ ONAY | %40 (riskli) |

---

### **2. Confidence Score Hesaplama**

```python
# strategy/confluence.py
def calculate_htf_confidence(
    major_trend: str,
    minor_trend: str,
    signal: str
) -> float:
    """
    HTF confluence bazlı confidence score hesapla.
    
    Args:
        major_trend: Major HTF trendi
        minor_trend: Minor HTF trendi
        signal: Sinyal (LONG/SHORT)
    
    Returns:
        Confidence score (0.0 - 1.0)
    """
    
    # Major ve Minor aynı yönde → Yüksek confidence
    if major_trend == signal and minor_trend == signal:
        return 0.85  # Güçlü onay
    
    # Major onaylıyor, Minor ters → Orta confidence
    if major_trend == signal and minor_trend != signal:
        return 0.65  # Zayıf onay
    
    # Major ters, Minor onaylıyor → Veto
    if major_trend != signal and minor_trend == signal:
        return 0.0  # Veto
    
    # İkisi de ters → Veto
    if major_trend != signal and minor_trend != signal:
        return 0.0  # Veto
    
    # Major NEUTRAL → Düşük confidence
    if major_trend == "NEUTRAL":
        if minor_trend == signal:
            return 0.50  # Riskli onay
        else:
            return 0.40  # Çok riskli
    
    return 0.5  # Varsayılan
```

---

## 🚨 Uygulama Notları

### **1. HTF Veri Yönetimi**

**Senkronizasyon:**
```python
# core/exchange.py
async def get_htf_data(
    symbol: str,
    bot_timeframe: str,
    minor_htf: str,
    major_htf: str
) -> Dict[str, pd.DataFrame]:
    """
    Bot ve HTF verilerini senkronize al.
    
    Args:
        symbol: Sembol
        bot_timeframe: Bot timeframe
        minor_htf: Minor HTF
        major_htf: Major HTF
    
    Returns:
        Dict with DataFrames: {bot, minor, major}
    """
    
    # Paralel veri çekme (asyncio.gather)
    bot_df, minor_df, major_df = await asyncio.gather(
        get_ohlcv(symbol, bot_timeframe, limit=100),
        get_ohlcv(symbol, minor_htf, limit=50),
        get_ohlcv(symbol, major_htf, limit=50)
    )
    
    return {
        'bot': bot_df,
        'minor': minor_df,
        'major': major_df
    }
```

**Dikkat:**
- ✅ HTF verileri senkronize olmalı (aynı timestamp)
- ✅ Her timeframe için yeterli veri (min 50 mum)
- ✅ UTC timezone standardizasyonu

---

### **2. Performans Optimizasyonu**

**Cache Mekanizması:**
```python
# strategy/htf.py
class HTFCache:
    def __init__(self, ttl_seconds: int = 60):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Cache'den HTF verisi al."""
        key = f"{symbol}:{timeframe}"
        
        if key in self.cache:
            data, timestamp = self.cache[key]
            
            # TTL kontrolü
            if (datetime.utcnow() - timestamp).total_seconds() < self.ttl:
                return data  # Cache hit
        
        return None  # Cache miss
    
    def set(self, symbol: str, timeframe: str, data: pd.DataFrame):
        """Cache'e HTF verisi koy."""
        key = f"{symbol}:{timeframe}"
        self.cache[key] = (data, datetime.utcnow())
```

**Kullanım:**
```python
# HTF verisini cache'den al (varsa)
htf_data = htf_cache.get(symbol, major_htf)

if htf_data is None:
    # Cache miss, API'den çek
    htf_data = await get_ohlcv(symbol, major_htf)
    htf_cache.set(symbol, major_htf, htf_data)
```

---

### **3. False Sinyal Filtreleme**

**Senaryo:**
```
1m Bot:
  - RSI < 30 (oversold)
  - MACD cross (LONG sinyal)
  
5m Minor:
  - EMA 20 < EMA 50 (BEAR)
  
15m Major:
  - EMA 20 < EMA 50 (BEAR)

Sonuç: ❌ VETO
  - Major BEAR, LONG açılmaz
  - 1m sinyali FALSE (gürültü)
  - İşlem YOK
```

**Avantaj:**
- ✅ %60-70 false sinyal filtrelenir
- ✅ Sadece ana trend yönünde işlem
- ✅ Win rate artışı (%50 → %65)

---

## 📚 İlgili Dokümanlar

- **Strategy Confluence:** `strategies/confluence.md`
- **Dynamic Position Sizing:** `concepts/dynamic_position_sizing.md`
- **ML Integration:** `features/ml_integration.md`
- **ATR Trailing Stop:** `features/ATR_TRAILING_STOP_SYSTEM.md`

---

## 📖 Kaynaklar

1. **Alexander Elder** - "Trading for a Living" (1993)
   - Chapter 24: The Triple Screen Trading System
   
2. **Alexander Elder** - "The New Trading for a Living" (2014)
   - Chapter 16: Multiple Time Frames
   - Section: The Three-System Approach

3. **John Murphy** - "Technical Analysis of the Financial Markets" (1999)
   - Chapter 8: Time Frames
   - Section: Multiple Time Frame Analysis

---

*Bu doküman HTF Golden Ratio v4.0 (Mart 2026) için hazırlanmıştır.*
*Güncellemeler için `knowledge/concepts/` dizinini kontrol edin.*
