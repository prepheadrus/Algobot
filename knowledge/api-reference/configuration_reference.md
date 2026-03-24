# ⚙️ Configuration Reference (config.yaml & .env)

**Versiyon:** v4.0 (Production-Ready)
**Son Güncelleme:** Mart 2026

---

## 📋 Genel Bakış

CryptoAlgoBot, iki katmanlı konfigürasyon sistemi kullanır:
1. **config.yaml:** Uygulama ayarları (HTF, WFO, ML, Risk)
2. **.env:** Hassas bilgiler (API keys, DB URLs)

---

## 📁 Dosya Yapısı

```
f:\Crypto Bot\
├── config.yaml              # Ana konfigürasyon
├── config.example.yaml      # Şablon (version control için)
├── .env                     # Hassas bilgiler (.gitignore'da)
└── .env.example             # Şablon (version control için)
```

---

## 1. BOT AYARLARI (bot)

```yaml
bot:
  environment: development    # development | production
  exchange: binance           # binance | binance_testnet
  log_level: INFO             # DEBUG | INFO | WARNING | ERROR
  name: CryptoAlgoBot
```

**Parametreler:**

| Parametre | Değer | Varsayılan | Açıklama |
|-----------|-------|------------|----------|
| `environment` | `development` | `development` | Ortam (prod'da daha az log) |
| `exchange` | `binance` | `binance` | Borsa seçimi |
| `log_level` | `INFO` | `INFO` | Log detay seviyesi |
| `name` | `CryptoAlgoBot` | `CryptoAlgoBot` | Bot adı (UI'da görünür) |

---

## 2. HTF AYARLARI (htf)

```yaml
htf:
  dynamic_map:
    1m:
      - 5m
      - 15m
    3m:
      - 15m
      - 1h
    5m:
      - 15m
      - 1h
    15m:
      - 1h
      - 4h
    30m:
      - 2h
      - 6h
    1h:
      - 4h
      - 1d
    4h:
      - 1d
      - 1w
  ema_fast: 20
  ema_slow: 50
  enabled: true
  filter_rules:
    require_all_htf_agree: false
  trend_method: ema_stack      # ema_stack | close_ema
```

**Parametreler:**

| Parametre | Değer | Varsayılan | Açıklama |
|-----------|-------|------------|----------|
| `dynamic_map` | Map | (yukarıdaki) | Bot TF → Minor/Major HTF mapping |
| `ema_fast` | `20` | `20` | Hızlı EMA periyodu |
| `ema_slow` | `50` | `50` | Yavaş EMA periyodu |
| `enabled` | `true` | `true` | HTF analizi aktif/pasif |
| `filter_rules.require_all_htf_agree` | `false` | `false` | Tüm HTF'ler aynı yönde olmalı mı? |
| `trend_method` | `ema_stack` | `ema_stack` | Trend tespit metodu |

**Trend Methodları:**

| Metod | Açıklama |
|-------|----------|
| `ema_stack` | EMA 20 vs EMA 50 karşılaştırması |
| `close_ema` | Close fiyat vs EMA karşılaştırması |

---

## 3. ML AYARLARI (ml)

```yaml
ml:
  confidence_threshold: 0.5
  enabled: true
  leverage:
    normal_threshold: 0.65
    strong_threshold: 0.8
    weak_threshold: 0.5
```

**Parametreler:**

| Parametre | Değer | Varsayılan | Açıklama |
|-----------|-------|------------|----------|
| `confidence_threshold` | `0.5` | `0.5` | Minimum işlem confidence |
| `enabled` | `true` | `true` | ML entegrasyonu aktif/pasif |
| `leverage.weak_threshold` | `0.5` | `0.5` | Zayıf sinyal eşiği (2-3x kaldıraç) |
| `leverage.normal_threshold` | `0.65` | `0.65` | Normal sinyal eşiği (3-5x kaldıraç) |
| `leverage.strong_threshold` | `0.8` | `0.8` | Güçlü sinyal eşiği (5-10x kaldıraç) |

**Confidence → Leverage Mapping:**

| Confidence | Leverage (1h+) | Leverage (1m-3m) |
|------------|----------------|------------------|
| **< 0.50** | 1x (base) | 1x |
| **0.50-0.65** | 2-3x | 2-3x |
| **0.65-0.80** | 3-5x | 3-5x |
| **> 0.80** | 5-10x | 5-8x |

---

## 4. RISK YÖNETİMİ (risk_management)

```yaml
risk_management:
  default_leverage: 1
  max_consecutive_losses: 5
  max_leverage: 50
  max_open_positions: 10
  max_risk_per_trade_percent: 2.0
```

**Parametreler:**

| Parametre | Değer | Varsayılan | Açıklama |
|-----------|-------|------------|----------|
| `default_leverage` | `1` | `1` | Varsayılan kaldıraç |
| `max_consecutive_losses` | `5` | `5` | Kill switch için ardışık kayıp limiti |
| `max_leverage` | `50` | `50` | Maksimum kaldıraç |
| `max_open_positions` | `10` | `10` | Maksimum açık pozisyon |
| `max_risk_per_trade_percent` | `2.0` | `2.0` | İşlem başına maksimum risk (%) |

**Risk Formülü:**
```
Position Size = (Balance × Risk%) / |Entry - Stop|
```

---

## 5. STRATEJİ AYARLARI (strategy)

```yaml
strategy:
  active_modules:
    - trend_following
    - mean_reversion
  ml_confidence_threshold: 0.6
```

**Parametreler:**

| Parametre | Değer | Varsayılan | Açıklama |
|-----------|-------|------------|----------|
| `active_modules` | List | `trend_following`, `mean_reversion` | Aktif strateji modülleri |
| `ml_confidence_threshold` | `0.6` | `0.6` | ML onayı için minimum confidence |

---

## 6. TRADING AYARLARI (trading)

```yaml
trading:
  exchange: binance
  symbols: []
  timeframes:
    - 1m
    - 5m
    - 1h
```

**Parametreler:**

| Parametre | Değer | Varsayılan | Açıklama |
|-----------|-------|------------|----------|
| `exchange` | `binance` | `binance` | Borsa |
| `symbols` | `[]` | `[]` | İzlenecek semboller (bot başlatılınca dolar) |
| `timeframes` | List | `1m`, `5m`, `1h` | Desteklenen zaman dilimleri |

---

## 7. WFO AYARLARI (wfo)

```yaml
wfo:
  enabled: true
  min_improvement: 0.05
  optimization_metric: sharpe
  reoptimize_interval: 168
  test_days: 30
  train_days: 90
```

**Parametreler:**

| Parametre | Değer | Varsayılan | Açıklama |
|-----------|-------|------------|----------|
| `enabled` | `true` | `true` | WFO aktif/pasif |
| `min_improvement` | `0.05` | `0.05` | Minimum iyileştirme (%5) |
| `optimization_metric` | `sharpe` | `sharpe` | Optimizasyon metriği |
| `reoptimize_interval` | `168` | `168` | Yeniden optimizasyon aralığı (saat) |
| `test_days` | `30` | `30` | Test/Test günleri |
| `train_days` | `90` | `90` | Eğitim/In-Sample günleri |

**WFO Döngüsü:**
```
Hafta 1: [90 gün train] → [30 gün test] → [Parametreler]
Hafta 2: [Rolling window] → [Yeni parametreler]
...
```

---

## 8. .ENV DOSYASI (Hassas Bilgiler)

```bash
# .env

# Binance API Keys
BINANCE_API_KEY=pk_live_abc123xyz...
BINANCE_API_SECRET=sk_live_xyz789abc...

# Database URLs (opsiyonel)
TIMESCALE_DB_URL=postgresql://user:pass@localhost:5432/cryptobot
REDIS_URL=redis://localhost:6379/0

# Encryption
ENCRYPTION_KEY=your-32-byte-encryption-key-here
```

**Parametreler:**

| Parametre | Zorunlu | Açıklama |
|-----------|---------|----------|
| `BINANCE_API_KEY` | Hayır* | *Sadece live trading için gerekli |
| `BINANCE_API_SECRET` | Hayır* | *Sadece live trading için gerekli |
| `TIMESCALE_DB_URL` | Hayır | PostgreSQL kullanılmıyorsa boş |
| `REDIS_URL` | Hayır | Cache kullanılmıyorsa boş |
| `ENCRYPTION_KEY` | Evet | API keys şifreleme için gerekli |

---

## 🔧 Hot-Reload (API ile Güncelleme)

### **Risk Ayarları Güncelleme**

```http
POST /api/v1/config/risk
Content-Type: application/json

{
    "max_risk_per_trade": 1.0,
    "max_leverage": 10,
    "max_open_positions": 5,
    "max_consecutive_losses": 5,
    "kill_switch_enabled": true
}
```

### **Advanced Ayarlar Güncelleme**

```http
POST /api/v1/config/advanced
Content-Type: application/json

{
    "wfo_enabled": true,
    "wfo_train_days": 30,
    "wfo_test_days": 7,
    "wfo_reoptimize_interval": 168,
    "ml_enabled": true,
    "ml_confidence_threshold": 0.65,
    "htf_enabled": true,
    "htf_method": "ema_stack"
}
```

---

## 🚨 Sorun Giderme

### **Sorun 1: config.yaml Bulunamadı**

**Semptom:** `FileNotFoundError: config.yaml`

**Çözüm:**
```bash
# Şablondan kopyala
cp config.example.yaml config.yaml

# Düzenle
nano config.yaml
```

---

### **Sorun 2: API Keys Geçersiz**

**Semptom:** `Invalid API-key`

**Çözüm:**
```bash
# .env dosyasını kontrol et
cat .env | grep BINANCE

# API keys'i test et
curl -X GET http://localhost:8000/api/v1/config/api-keys/test
```

---

### **Sorun 3: WFO Çalışmıyor**

**Semptom:** WFO parametreleri yüklenmiyor

**Çözüm:**
```yaml
# config.yaml içinde WFO aktif et
wfo:
  enabled: true  # ✅ TRUE olmalı
  train_days: 30
  test_days: 7
```

---

## 📚 İlgili Dokümanlar

- **Risk Engine:** `features/risk_engine.md`
- **WFO:** `features/walk_forward_optimization.md`
- **HTF Golden Ratio:** `concepts/htf_golden_ratio.md`

---

*Bu doküman Configuration Reference v4.0 (Mart 2026) için hazırlanmıştır.*
