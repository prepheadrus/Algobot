# 🚀 Sistem Başlatma Rehberi (How to Start Live Trading)

**Versiyon:** v4.0 (Production-Ready)
**Son Güncelleme:** Mart 2026
**Süre:** ~45 dakika
**Zorluk:** Orta

---

## 📋 Genel Bakış

Bu rehber, sıfırdan başlayan bir kullanıcının CryptoAlgoBot sistemini **Production-Ready** hale getirmesi için gereken tüm ardışık adımları içerir.

**4 Ana Aşama:**
1. ✅ Veri Hazırlığı (Data Ingestion)
2. ✅ ML Model Eğitimi (Intelligence Layer)
3. ✅ Çoklu Bot ve Risk Yapılandırması
4. ✅ İcra (Execution)

---

## ⚠️ Ön Koşullar (Prerequisites)

### **1. Sistem Gereksinimleri**

| Bileşen | Minimum | Önerilen |
|---------|---------|----------|
| **CPU** | 4 çekirdek | 8+ çekirdek |
| **RAM** | 8 GB | 16+ GB |
| **Disk** | 50 GB SSD | 100+ GB NVMe |
| **Python** | 3.9+ | 3.10+ |
| **Internet** | 10 Mbps | 50+ Mbps |

### **2. API Anahtarları**

**Binance Futures API İzinleri:**
- ✅ **Spot & Margin Trading:** KAPALI
- ✅ **Futures Trading:** AÇIK
- ✅ **Reading:** AÇIK
- ❌ **Withdrawal:** ASLA AÇMAYIN!

**API Key Alma:**
```
1. Binance.com → API Management
2. "Create API" tıkla
3. 2FA doğrulama yap
4. API Key ve Secret Key'i kaydet
5. IP Whitelist ekle (opsiyonel, önerilir)
```

### **3. Kurulum**

```bash
# 1. Depoyu klonla
git clone https://github.com/yourusername/CryptoAlgoBot.git
cd CryptoAlgoBot

# 2. Bağımlılıkları yükle
pip install -r requirements.txt

# 3. .env dosyasını oluştur
cp .env.example .env

# 4. API anahtarlarını gir
# .env dosyasını düzenle:
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_secret_here

# 5. Veritabanını başlat
python migrate_db.py
```

---

## 📊 ADIM 1: Veri Hazırlığı (Data Ingestion)

**Süre:** 10-15 dakika
**Amaç:** OHLCV verisini Binance'den indirip Parquet Data Lake'e kaydetmek

---

### **1.1: Veri Laboratuvarı'nı Aç**

```
Dashboard → Sol Menü → 💾 Veri Laboratuvarı
```

---

### **1.2: Piyasa Seçimi**

**Adımlar:**
1. **Arama Kutusu:** `🔍 Coin Ara...` → `BTC` yaz
2. **Filtre:** `💹 Futures` seç (Spot değil!)
3. **Liste:** `BTC/USDT` satırına tıkla
4. **Onay:** `Seçili Sembol: BTC/USDT (Futures)` görünür

**Dikkat:**
- ✅ USDT-M Futures seçin (USDT teminat)
- ❌ COIN-M Futures seçmeyin (coin teminat)
- ❌ Spot seçmeyin (leverage yok)

---

### **1.3: İndirme Parametreleri**

**Ayarlar:**
```
┌─────────────────────────────────────┐
│ 🔧 İndirme Ayarları                 │
├─────────────────────────────────────┤
│ Zaman Dilimi: 1m (varsayılan)       │
│ Gün Sayısı: 30                      │
│ └─ Not: Sistem sadece 1m indirir,   │
│   diğer TF'ler otomatik oluşur.     │
└─────────────────────────────────────┘
```

**Neden sadece 1m?**
- 🏗️ **Parquet Data Lake Mimarisi:**
  - 1m → Günlük partition (YYYY/MM/DD/data.parquet)
  - 5m, 15m, 1h → Otomatik resample edilir
  - Disk tasarrufu: %70-80

---

### **1.4: İndirmeyi Başlat**

**Buton:** `🚀 Veri İndir`

**API Request:**
```http
POST /api/v1/data/download-history
Content-Type: application/json

{
    "symbol": "BTC/USDT",
    "timeframe": "1m",
    "days": 30
}
```

**Response:**
```json
{
    "status": "success",
    "task_id": "task_1710847200",
    "message": "İndirme başlatıldı: BTC/USDT (30 gün)",
    "estimated_candles": 43200
}
```

---

### **1.5: Gap Detection (Boşluk Tespiti)**

**İlerleme İzleme:**

| Durum | İlerleme | Süre |
|-------|----------|------|
| **Başlatıldı** | 0% | 0s |
| **İndiriliyor** | 25% | 30s |
| **Parquet Yazılıyor** | 50% | 60s |
| **Tamamlandı** | 100% | 90s |

**Gap Detection:**
```python
# data/data_lake.py
async def detect_gaps(symbol: str, timeframe: str) -> List[Gap]:
    """
    Veritabanında eksik mumları tespit et.
    
    Returns:
        List of Gap objects (start, end, duration)
    """
    # Son mumu al
    last_candle = await db.get_last_candle(symbol, timeframe)
    
    # Şu anki zaman
    now = datetime.utcnow()
    
    # Beklenen mum sayısı
    expected = (now - last_candle.timestamp).total_seconds() / 60
    
    # Gerçek mum sayısı
    actual = await db.count_candles(symbol, timeframe)
    
    # Gap var mı?
    if expected - actual > 5:  # 5 mumdan fazla eksik
        return [Gap(last_candle.timestamp, now)]
    
    return []
```

**Gap Tespit Edilirse:**
```
1. Veri Laboratuvarı → "Görev Geçmişi"
2. Eksik tarih aralığını not et
3. Yeni indirme başlat (o aralık için)
4. Sistem otomatik birleştirir (UTC standardizasyonu)
```

---

### **1.6: Veri Doğrulama**

**Kontrol Komutu:**
```bash
python check_db.py --symbol BTC/USDT --timeframe 1m
```

**Beklenen Çıktı:**
```
✅ BTC/USDT (1m): 43,200 mum bulundu
✅ İlk mum: 2026-02-15 00:00:00 UTC
✅ Son mum: 2026-03-17 23:59:00 UTC
✅ Gap yok (süreklilik doğrulandı)
✅ Parquet dosyaları: 31 gün kaydedildi
```

---

## 🧠 ADIM 2: ML Model Eğitimi (Intelligence Layer)

**Süre:** 5-10 dakika
**Amaç:** Triple Barrier Method ile etiketlenmiş verilerle XGBoost modeli eğitmek

---

### **2.1: ML Karar Motoru'nu Aç**

```
Dashboard → Sol Menü → 🧠 ML Karar Motoru
```

---

### **2.2: Eğitim Parametreleri**

**Ayarlar:**
```
┌─────────────────────────────────────┐
│ 🧠 ML Model Eğitimi                 │
├─────────────────────────────────────┤
│ Sembol: BTC/USDT:USDT               │
│ Timeframe: 1h (önerilen)            │
│ Mum Sayısı: 5000                    │
│ TP Çarpan: 2.0                      │
│ SL Çarpan: 2.0                      │
└─────────────────────────────────────┘
```

**Neden 1h?**
- ✅ Yeterli veri noktası (5000 mum ≈ 208 gün)
- ✅ Daha az gürültü (1m'ye göre)
- ✅ Swing trading için ideal

---

### **2.3: Triple Barrier Method**

**Etiketleme Mantığı:**
```python
# ml/data_prep.py
def get_triple_barrier_labels(prices, events, pt_sl, out):
    """
    Triple Barrier Method ile etiketleme.
    
    Bariyerler:
    1. Profit-Take: entry + (tp_multiplier × volatility)
    2. Stop-Loss: entry - (sl_multiplier × volatility)
    3. Time Limit: t + T (5 mum)
    
    Etiketler:
    - 0: SHORT (stop-loss önce dokunuldu)
    - 1: NEUTRAL (time limit doldu)
    - 2: LONG (profit-take önce dokunuldu)
    """
```

**Görsel:**
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

---

### **2.4: Model Eğitimi Başlat**

**Buton:** `🚀 Modeli Eğit`

**API Request:**
```http
POST /api/v1/ml/train
Content-Type: application/json

{
    "symbol": "BTC/USDT:USDT",
    "timeframe": "1h",
    "limit": 5000,
    "tp_multiplier": 2.0,
    "sl_multiplier": 2.0
}
```

**Eğitim Logları:**
```
[ML] 🧠 Ensemble (XGBoost + RF) eğitimi başlatılıyor...
[ML]   Eğitim seti: (4000, 42)
[ML]   Test seti: (1000, 42)
[ML]   Sınıf dağılımı (train): {0: 1200, 1: 1600, 2: 1200}
[ML] 📊 XGBoost eğitiliyor...
[ML] ✅ XGBoost eğitimi tamamlandı.
[ML] 🌲 Random Forest eğitiliyor...
[ML] ✅ Random Forest eğitimi tamamlandı.
[ML] 🔗 Ensemble tahminleri hesaplanıyor...
[ML] ============================================================
[ML] EĞİTİM SONUÇLARI
[ML] ============================================================
[ML] Accuracy:  0.6234
[ML] Precision: 0.6105
[ML] Recall:    0.6187
[ML] F1-Score:  0.6145
[ML] XGBoost Accuracy:  0.6102
[ML] RF Accuracy:       0.5987
[ML] Ensemble Accuracy: 0.6234
[ML] ============================================================
```

---

### **2.5: Model Metriklerini Yorumlama**

| Metrik | Değer | Durum | Açıklama |
|--------|-------|-------|----------|
| **Accuracy** | 0.6234 | ✅ İyi | %62 doğruluk |
| **Precision** | 0.6105 | ✅ İyi | Yanlış sinyal düşük |
| **Recall** | 0.6187 | ✅ İyi | Gerçek sinyaller yakalandı |
| **F1-Score** | 0.6145 | ✅ İyi | Dengeli performans |

**Kriterler:**
- ✅ **≥ 0.60:** Production-ready
- ⚠️ **0.55-0.60:** Kabul edilebilir (daha fazla veri gerekli)
- ❌ **< 0.55:** Yeniden eğit (feature engineering gözden geçir)

---

### **2.6: Model Yükleme**

**Otomatik Yükleme:**
```
Eğitim tamamlandıktan sonra model otomatik yüklenir.
Model path: artifacts/models/xgb_model_btcusdtusdt_1h.json
```

**Manuel Kontrol:**
```bash
ls -lh artifacts/models/xgb_model_btcusdtusdt_1h.json
```

**Beklenen Boyut:**
```
-rw-r--r-- 1 user user 2.5M Mar 17 12:34 xgb_model_btcusdtusdt_1h.json
```

---

## ⚙️ ADIM 3: Çoklu Bot ve Risk Yapılandırması

**Süre:** 10-15 dakika
**Amaç:** HTF filtreleri, ML confidence eşikleri ve risk limitlerini ayarlamak

---

### **3.1: Sistem Ayarları'nı Aç**

```
Dashboard → Sol Menü → ⚙️ Sistem Ayarları
```

---

### **3.2: Risk Ayarları**

**Ayarlar:**
```
┌─────────────────────────────────────┐
│ 🛡️ Risk Ayarları                    │
├─────────────────────────────────────┤
│ Maksimum Risk: 1.0%                 │
│ Maksimum Kaldıraç: 10x              │
│ Maks. Pozisyon: 5                   │
│ Ardışık Kayıp: 5                    │
│ Kill Switch: ✅ AKTIF               │
└─────────────────────────────────────┘
```

**Pozisyon Boyutu Formülü:**
```python
# core/risk/risk_engine.py
def calculate_position_size(
    balance=10000,
    entry=50000,
    stop=49000,
    risk_percentage=1.0
):
    risk_amount = balance * (risk_percentage / 100)  # $100
    price_distance = abs(entry - stop)  # $1000
    size = risk_amount / price_distance  # 0.1 BTC
    return size
```

**Örnek:**
```
Bakiye: $10,000
Risk: %1 → $100
Giriş: $50,000
Stop: $49,000 (mesafe: $1,000)
Pozisyon Boyutu: $100 / $1,000 = 0.1 BTC
```

---

### **3.3: HTF (Altın Oran) Filtreleri**

**Ayarlar:**
```
┌─────────────────────────────────────┐
│ 📊 HTF (Multi-Timeframe) Analizi   │
├─────────────────────────────────────┤
│ HTF Analizi: ✅ AKTIF               │
│ Trend Metodu: EMA Stack             │
│ Minor HTF: 15m (1:4)                │
│ Major HTF: 1h (1:6)                 │
└─────────────────────────────────────┘
```

**Altın Oran Mantığı:**
```
Bot Timeframe: 1m
├── Minor HTF: 15m (1:15 ≈ 1:4 Altın Oran)
└── Major HTF: 1h (1:60 ≈ 1:6 Altın Oran)

EMA Stack Trend:
- EMA 20 > EMA 50 → BULL (LONG onaylı)
- EMA 20 < EMA 50 → BEAR (SHORT onaylı)
```

**Veto Yetkisi:**
```python
# strategy/confluence.py
def htf_filter(bot_timeframe, minor_trend, major_trend, signal):
    """
    HTF veto mantığı.
    
    Major trend ters yönde ise işlem açılmaz.
    """
    if signal == "LONG" and major_trend == "BEAR":
        return False  # VETO: Major bear, LONG açma
    
    if signal == "SHORT" and major_trend == "BULL":
        return False  # VETO: Major bull, SHORT açma
    
    return True  # Onaylandı
```

---

### **3.4: ML Confidence Eşiği**

**Ayarlar:**
```
┌─────────────────────────────────────┐
│ 🤖 ML Model Ayarları                │
├─────────────────────────────────────┤
│ ML Model: ✅ AKTIF                  │
│ Confidence Threshold: 0.65 (65%)    │
└─────────────────────────────────────┘
```

**Confidence → Leverage Mapping:**
```python
# core/risk/risk_engine.py
def calculate_dynamic_leverage(confidence_score, timeframe):
    if confidence_score < 0.50:
        return 1.0  # Düşük güven, minimum kaldıraç
    
    if timeframe in ["1m", "3m"]:
        max_leverage = 10  # Yüksek gürültü
    elif timeframe in ["5m", "15m"]:
        max_leverage = 20  # Orta gürültü
    else:
        max_leverage = 10  # Normal
    
    # Power curve
    raw_ratio = (confidence_score - 0.50) / 0.50
    boosted_ratio = 0.05 + (0.95 * (raw_ratio ** 0.7))
    
    calculated = 1.0 + (boosted_ratio * (max_leverage - 1.0))
    final_leverage = int(round(min(max_leverage, calculated)))
    
    return final_leverage
```

**Tablo:**
| Confidence | Leverage (1h+) | Aksiyon |
|------------|----------------|---------|
| **< 50%** | 1x | İşlem açma |
| **50-65%** | 2-3x | Düşük risk |
| **65-80%** | 3-5x | Orta risk |
| **> 80%** | 5-10x | Yüksek risk |

---

### **3.5: WFO (Walk-Forward Optimization)**

**Ayarlar:**
```
┌─────────────────────────────────────┐
│ 🔄 Walk-Forward Optimization        │
├─────────────────────────────────────┤
│ WFO: ✅ AKTIF                       │
│ Eğitim Günleri: 30                  │
│ Test Günleri: 7                     │
│ Re-optimizasyon: 168 saat (1 hafta) │
└─────────────────────────────────────┘
```

**WFO Döngüsü:**
```
Hafta 1: [Oca 1 - Oca 30] → Optimize → [Oca 31 - Şub 6] → Test
Hafta 2: [Oca 8 - Şub 6] → Optimize → [Şub 7 - Şub 13] → Test
Hafta 3: [Oca 15 - Şub 13] → Optimize → [Şub 14 - Şub 20] → Test
...
```

---

## 🎯 ADIM 4: İcra (Execution)

**Süre:** 5-10 dakika
**Amaç:** Botu Paper Trading modunda başlatmak ve Event-Tracer ile izlemek

---

### **4.1: Dashboard'dan Bot Başlat**

**Sekme:** `⚙️ Sistem Ayarları → 🚀 Bot Başlatma Merkezi`

**Form:**
```
┌─────────────────────────────────────┐
│ 🚀 Bot Başlatma Merkezi             │
├─────────────────────────────────────┤
│ 🪙 Sembol: BTC/USDT:USDT            │
│ 📚 Strateji: trend_master           │
│ ⏱️ Timeframe: 1h                    │
│ 🏛️ Market: Futures (Swap)           │
│ 🛡️ Marjin Tipi: Isolated            │
└─────────────────────────────────────┘
```

**Buton:** `▶ Bot Başlat`

---

### **4.2: Bot Başlatma API**

**Request:**
```http
POST /api/v1/bot/start
Content-Type: application/json

{
    "symbol": "BTC/USDT:USDT",
    "strategy_id": "trend_master",
    "timeframe": "1h",
    "market_type": "swap",
    "margin_type": "isolated"
}
```

**Response:**
```json
{
    "status": "success",
    "bot_id": "BTC/USDT:USDT_trend_master_1h_1",
    "message": "Bot başlatıldı: BTC/USDT:USDT_trend_master_1h_1"
}
```

---

### **4.3: Event-Tracer ile İzleme**

**Event-Tracer Aç:**
```
Dashboard → Sol Menü → 📊 Event Tracer (Geliştirici)
```

**Beklenen Event Akışı:**
```
[12:34:56] 📬 bot.started
           bot_id: BTC/USDT:USDT_trend_master_1h_1
           symbol: BTC/USDT:USDT
           strategy: trend_master

[12:35:00] 📬 price.updated
           symbol: BTC/USDT:USDT
           price: 50123.45

[12:35:01] 📬 signal.generated
           bot_id: BTC/USDT:USDT_trend_master_1h_1
           signal: 2 (LONG)
           price: 50123.45
           indicators: {RSI: 65.2, EMA_20: 49876.3}

[12:35:02] 📬 ml.prediction
           symbol: BTC/USDT:USDT
           direction: LONG
           confidence: 0.78

[12:35:03] 📬 confluence.approved
           bot_id: BTC/USDT:USDT_trend_master_1h_1
           final_signal: LONG
           htf_minor: BULL
           htf_major: BULL

[12:35:04] 📬 position.opened
           bot_id: BTC/USDT:USDT_trend_master_1h_1
           direction: LONG
           entry_price: 50133.57 (slippage: +0.02%)
           size: 0.1 BTC
           leverage: 5x
           stop_loss: 49632.15
           take_profit: 51137.41

[12:35:05] 📬 trade.recorded
           trade_id: trade_1710847205
           bot_id: BTC/USDT:USDT_trend_master_1h_1
           pnl: -$10.05 (entry fee)
```

---

### **4.4: Pozisyon İzleme**

**Dashboard → 📊 Portföy Analizi → Aktif Pozisyonlar**

**Tablo:**
| Kolon | Değer |
|-------|-------|
| **Strateji** | trend_master |
| **Yön** | 🟢 LONG |
| **Giriş** | $50,133.57 |
| **Mevcut** | $50,245.80 |
| **PnL** | +$11.23 (+0.02%) |
| **Stop** | $49,632.15 |
| **TP** | $51,137.41 |

**Trailing Stop Güncellemesi:**
```
[12:40:00] 🔼 [TRAILING] BTC/USDT:USDT LONG:
           Stop updated to 49732.45 (ATR: 501.15 × 1.5)

[12:45:00] 🔼 [TRAILING] BTC/USDT:USDT LONG:
           Stop updated to 49832.78 (ATR: 498.67 × 1.5)
```

---

### **4.5: Pozisyon Kapanış Senaryoları**

**Senaryo 1: Take Profit**
```
[13:00:00] 📬 position.closed
           bot_id: BTC/USDT:USDT_trend_master_1h_1
           reason: TAKE PROFIT
           exit_price: 51137.41
           pnl: +$1,013.89 (+2.02%)
           pnl_percent: +2.02%
```

**Senaryo 2: Stop Loss**
```
[13:00:00] 📬 position.closed
           bot_id: BTC/USDT:USDT_trend_master_1h_1
           reason: STOP LOSS
           exit_price: 49632.15
           pnl: -$100.00 (-1.00%)
           pnl_percent: -1.00%
```

**Senaryo 3: Trailing Stop**
```
[13:00:00] 📬 position.closed
           bot_id: BTC/USDT:USDT_trend_master_1h_1
           reason: TRAILING STOP
           exit_price: 50532.89
           pnl: +$399.32 (+0.80%)
           pnl_percent: +0.80%
```

---

## 🚨 Troubleshooting 101

### **Senaryo 1: Veri İndirme Takıldı**

**Semptom:** Progress bar %50'de sabit

**Çözüm:**
```bash
# 1. İndirme görevini iptal et
curl -X POST http://localhost:8000/api/v1/data/delete-task \
  -H "Content-Type: application/json" \
  -d '{"task_id": "task_1710847200"}'

# 2. Disk alanı kontrol et
df -h data/ohlcv/

# 3. Yeniden başlat (daha kısa aralık)
# Gün sayısı: 30 → 7
```

---

### **Senaryo 2: ML Modeli Eğitilmiyor**

**Semptom:** "❌ Eğitim hatası: Yetersiz veri"

**Çözüm:**
```bash
# 1. Mum sayısını kontrol et
python check_db.py --symbol BTC/USDT --timeframe 1h

# 2. Yetersizse daha fazla veri indir
# Veri Laboratuvarı → Gün sayısı: 30 → 90

# 3. Timeframe'i değiştir (1h → 15m)
# Daha fazla veri noktası olur
```

---

### **Senaryo 3: Bot Başlamıyor**

**Semptom:** "❌ Bot başlatma hatası: Strateji bulunamadı"

**Çözüm:**
```bash
# 1. Strateji dosyasını kontrol et
ls strategy/*.py | grep trend_master

# 2. Strateji kütüphanesini yükle
python -c "from strategy.manager import StrategyManager; StrategyManager.load_strategies()"

# 3. API'yi yeniden başlat
pkill -f uvicorn
python api/server.py
```

---

### **Senaryo 4: Pozisyon Açılmıyor**

**Semptom:** Sinyal üretiliyor ama pozisyon yok

**Çözüm:**
```bash
# 1. ML confidence kontrol et
# Dashboard → ML Karar Motoru → Confidence: ≥65%?

# 2. HTF veto kontrol et
# Dashboard → Event Tracer → htf_filter logları

# 3. Risk limitleri kontrol et
# Dashboard → Sistem Ayarları → Maks. Pozisyon: 5
# Açık pozisyon sayısı ≥ 5 mi?
```

---

## ✅ Kontrol Listesi (Checklist)

### **Veri Hazırlığı**
- [ ] BTC/USDT Futures verisi indirildi
- [ ] 30 gün veri (43,200 mum @ 1m)
- [ ] Gap detection: Eksik mum yok
- [ ] Parquet dosyaları kaydedildi

### **ML Model**
- [ ] XGBoost + RF ensemble eğitildi
- [ ] Accuracy ≥ 60%
- [ ] Model dosyası kaydedildi
- [ ] Model otomatik yüklendi

### **Risk Ayarları**
- [ ] Maksimum Risk: %1
- [ ] Maksimum Kaldıraç: 10x
- [ ] Maks. Pozisyon: 5
- [ ] Kill Switch: AKTIF

### **HTF & ML**
- [ ] HTF Analizi: AKTIF
- [ ] Minor HTF: 15m
- [ ] Major HTF: 1h
- [ ] ML Confidence: ≥65%

### **Bot İcra**
- [ ] Bot başlatıldı
- [ ] Event-Tracer eventleri gösteriyor
- [ ] İlk pozisyon açıldı
- [ ] Trailing stop çalışıyor

---

## 📚 İlgili Dokümanlar

- **Dashboard:** `ui_reference/dashboard.md`
- **Veri Laboratuvarı:** `ui_reference/data_laboratory.md`
- **ML Karar Motoru:** `ui_reference/ml_decision_engine.md`
- **Risk Engine:** `features/risk_engine.md`
- **Parquet Data Lake:** `features/parquet_data_lake.md`
- **ML Integration:** `features/ml_integration.md`

---

*Bu rehber CryptoAlgoBot v4.0 (Mart 2026) için hazırlanmıştır.*
*Güncellemeler için `knowledge/workflows/` dizinini kontrol edin.*
