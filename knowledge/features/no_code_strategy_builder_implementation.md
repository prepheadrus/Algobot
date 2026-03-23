# 🎨 No-Code Strateji Oluşturucu - Uygulama Rehberi

**Oluşturulma:** Mart 2026  
**Versiyon:** 1.0  
**Durum:** ✅ Production Ready

---

## 📋 İÇİNDEKİLER

1. [Özellik Tanımı](#1-özellik-tanımı)
2. [Kurulum ve Hazırlık](#2-kurulum-ve-hazırlık)
3. [Kullanım Kılavuzu](#3-kullanım-kılavuzu)
4. [Teknik Mimari](#4-teknik-mimari)
5. [API Referansı](#5-api-referansı)
6. [Örnek Stratejiler](#6-örnek-stratejiler)
7. [Sorun Giderme](#7-sorun-giderme)

---

## 1. ÖZELLİK TANIMI

### No-Code Strateji Oluşturucu Nedir?

CryptoAlgoBot'un **No-Code Strateji Oluşturucu** özelliği, kullanıcıların **kod yazmadan** kendi trading stratejilerini oluşturmalarını sağlayan görsel bir araçtır.

### Ana Özellikler

| Özellik | Açıklama |
|---------|----------|
| 📚 İndikatör Kütüphanesi | 11+ hazır indikatör (RSI, MACD, EMA, vb.) |
| ⚙️ Görsel Koşul Oluşturucu | Sürükle-bırak ile koşul tanımlama |
| 🔀 Mantıksal Operatörler | AND, OR desteği |
| 📊 Real-time Preview | Anlık JSON önizleme |
| 🧪 Test Sistemi | Hızlı strateji testi |
| 💾 Kaydetme Sistemi | JSON formatında saklama |

### Desteklenen İndikatörler

#### Trend İndikatörleri
- **EMA** (Exponential Moving Average)
- **SMA** (Simple Moving Average)
- **Supertrend**

#### Momentum İndikatörleri
- **RSI** (Relative Strength Index)
- **MACD** (Moving Average Convergence Divergence)
- **Stochastic**

#### Volatilite İndikatörleri
- **ATR** (Average True Range)
- **Bollinger Bands**

#### Hacim İndikatörleri
- **OBV** (On-Balance Volume)
- **VWAP** (Volume Weighted Average Price)
- **MFI** (Money Flow Index)

---

## 2. KURULUM VE HAZIRLIK

### Gereksinimler

- ✅ Python 3.8+
- ✅ CryptoAlgoBot kurulu
- ✅ Modern tarayıcı (Chrome, Firefox, Edge)

### Kurulum Adımları

#### Adım 1: Botu Başlat

```bash
cd F:\Yazılan Programlar\Crypto bot\Crypto Bot
start_bot.bat
```

veya manuel:

```bash
cd F:\Yazılan Programlar\Crypto bot\Crypto Bot
venv\Scripts\activate
python main.py
```

#### Adım 2: Dashboard'u Aç

Tarayıcıda:
```
http://localhost:8000
```

#### Adım 3: Strateji Laboratuvarı'na Git

Sol menüden:
```
🎨 Strateji Laboratuvarı
```

---

## 3. KULLANIM KILAVUZU

### Hızlı Başlangıç: İlk Stratejini Oluştur

#### Adım 1: Strateji Adı Gir

Orta panel:
```
Strateji Adı: RSI Oversold
Zaman Dilimi: 15m
```

#### Adım 2: İndikatör Ekle

Sol panel:
```
1. MOMENTUM → RSI → "+" tıkla
2. Length: 14 (varsayılan)
3. "Ekle" tıkla
```

#### Adım 3: LONG Koşulu Oluştur

Orta panel:
```
1. LONG Koşulları → "➕ Koşul Ekle"
2. İndikatör: rsi_1
3. Operatör: <
4. Değer: 30
```

#### Adım 4: SHORT Koşulu Oluştur

Orta panel:
```
1. SHORT Koşulları → "➕ Koşul Ekle"
2. İndikatör: rsi_1
3. Operatör: >
4. Değer: 70
```

#### Adım 5: Risk Ayarları

```
Stop Loss: 2.0
Take Profit: 3.0
Max Risk: 2.0
```

#### Adım 6: Test Et

Sağ panel:
```
"🧪 Test Et" tıkla
```

#### Adım 7: Kaydet

Sağ panel:
```
"💾 Kaydet" tıkla
```

Dosya otomatik kaydedilir:
```
artifacts/strategies/rsi_oversold_20260306_XXXXXX.json
```

---

### Detaylı Kullanım

#### Komplex Strateji: RSI + MACD

**İndikatörler:**
1. RSI (14)
2. MACD (12, 26, 9)

**LONG Koşulu:**
```
RSI < 30
VE (AND)
MACD > Signal
```

**SHORT Koşulu:**
```
RSI > 70
VE (AND)
MACD < Signal
```

**Nasıl:**
1. RSI ve MACD ekle
2. LONG panelinde 2 koşul ekle
3. Logic: VE (AND) seç
4. SHORT için tekrar et

---

#### İndikatör vs İndikatör Karşılaştırma

**Örnek: EMA Crossover**

**İndikatörler:**
- EMA Fast (9)
- EMA Slow (21)

**LONG:**
```
EMA_9 > EMA_21
```

**SHORT:**
```
EMA_9 < EMA_21
```

**Nasıl:**
1. 2x EMA ekle (length: 9 ve 21)
2. Koşul ekle
3. Değer dropdown'dan diğer EMA'yı seç

---

## 4. TEKNİK MİMARİ

### Dosya Yapısı

```
Crypto_Automat/
├── frontend/
│   ├── index.html              # Ana dashboard
│   ├── strategy-lab.html       # Strateji laboratuvarı UI
│   ├── strategy-builder.js     # Frontend JavaScript
│   └── style.css               # CSS stilleri
│
├── strategy/
│   └── builder/
│       ├── __init__.py         # Modül init
│       ├── strategy_builder.py # Strateji oluşturma
│       ├── condition_parser.py # Koşul parser
│       ├── json_validator.py   # JSON validasyonu
│       └── executor.py         # Strateji çalıştırıcı
│
├── api/
│   └── strategy_builder_api.py # API endpoints
│
└── artifacts/
    └── strategies/             # Kaydedilen stratejiler
```

### Veri Akışı

```
User Input (Dashboard)
    ↓
StrategyBuilder (Python)
    ↓
JSON Strategy Definition
    ↓
ConditionParser → AST
    ↓
StrategyExecutor → Signal (0/1/2)
    ↓
Paper Trader → Execution
```

### JSON Strateji Formatı

```json
{
  "name": "RSI MACD Combo",
  "description": "RSI aşırı alım/satım + MACD momentum",
  "version": "1.0",
  "author": "User",
  "timeframe": "15m",
  "indicators": [
    {
      "id": "rsi_1",
      "type": "RSI",
      "parameters": {"length": 14}
    },
    {
      "id": "macd_1",
      "type": "MACD",
      "parameters": {"fast": 12, "slow": 26, "signal": 9}
    }
  ],
  "conditions": {
    "long": {
      "logic": "AND",
      "rules": [
        {"indicator": "rsi_1", "operator": "<", "value": 30},
        {"indicator": "macd_1", "operator": ">", "value": "signal"}
      ]
    },
    "short": {
      "logic": "AND",
      "rules": [
        {"indicator": "rsi_1", "operator": ">", "value": 70},
        {"indicator": "macd_1", "operator": "<", "value": "signal"}
      ]
    }
  },
  "risk": {
    "stop_loss": {"type": "ATR", "multiplier": 2.0},
    "take_profit": {"type": "ATR", "multiplier": 3.0},
    "max_risk_percent": 2.0
  }
}
```

---

## 5. API REFERANSI

### Strateji Test Et

**Endpoint:**
```
POST /api/v1/strategy/test
```

**Request:**
```json
{
  "name": "Test Strategy",
  "indicators": [...],
  "conditions": {...}
}
```

**Response:**
```json
{
  "status": "success",
  "metrics": {
    "win_rate": 62.5,
    "total_trades": 24,
    "profit_factor": 1.8,
    "max_drawdown": 8.2
  }
}
```

---

### Strateji Kaydet

**Endpoint:**
```
POST /api/v1/strategy/save
```

**Request:**
```json
{
  "name": "My Strategy",
  "indicators": [...],
  "conditions": {...}
}
```

**Response:**
```json
{
  "status": "success",
  "filename": "my_strategy_20260306_143022.json",
  "filepath": "artifacts/strategies/my_strategy_20260306_143022.json"
}
```

---

### Strateji Listesi

**Endpoint:**
```
GET /api/v1/strategy/list
```

**Response:**
```json
{
  "status": "success",
  "strategies": [
    {
      "filename": "simple_rsi.json",
      "name": "Basit RSI",
      "timeframe": "15m",
      "indicators_count": 1
    }
  ]
}
```

---

### Strateji Yükle

**Endpoint:**
```
GET /api/v1/strategy/load/{filename}
```

**Response:**
```json
{
  "status": "success",
  "strategy": {
    "name": "Simple RSI",
    "indicators": [...],
    "conditions": {...}
  }
}
```

---

### Strateji Sil

**Endpoint:**
```
DELETE /api/v1/strategy/delete/{filename}
```

**Response:**
```json
{
  "status": "success",
  "message": "Strategy deleted"
}
```

---

### İndikatör Listesi

**Endpoint:**
```
GET /api/v1/strategy/indicators
```

**Response:**
```json
{
  "status": "success",
  "indicators": [
    {
      "name": "RSI",
      "category": "momentum",
      "parameters": {
        "length": {"type": "int", "default": 14}
      }
    }
  ]
}
```

---

## 6. ÖRNEK STRATEJİLER

### 6.1 Basit RSI Stratejisi

**Dosya:** `artifacts/strategies/simple_rsi.json`

**İndikatörler:**
- RSI (14)

**LONG:**
```
RSI < 30
```

**SHORT:**
```
RSI > 70
```

**Risk:**
- Stop: 2.0x ATR
- Take: 3.0x ATR

---

### 6.2 EMA Crossover

**Dosya:** `artifacts/strategies/ema_crossover.json`

**İndikatörler:**
- EMA Fast (9)
- EMA Slow (21)

**LONG:**
```
EMA_9 > EMA_21
```

**SHORT:**
```
EMA_9 < EMA_21
```

**Risk:**
- Stop: 2.5x ATR
- Take: 3.5x ATR

---

### 6.3 RSI MACD Combo

**Dosya:** `artifacts/strategies/rsi_macd_combo.json`

**İndikatörler:**
- RSI (14)
- MACD (12, 26, 9)

**LONG:**
```
RSI < 30 VE MACD > Signal
```

**SHORT:**
```
RSI > 70 VE MACD < Signal
```

**Risk:**
- Stop: 2.0x ATR
- Take: 3.0x ATR

---

## 7. SORUN GİDERME

### Strateji Laboratuvarı Görünmüyor

**Sorun:** Sol menüde "🎨 Strateji Laboratuvarı" yok

**Çözüm:**
```bash
1. Botu durdur (CTRL+C)
2. start_bot.bat ile yeniden başlat
3. Tarayıcıda CTRL+F5 (Hard Refresh)
```

---

### İçerik Boş Görünüyor

**Sorun:** Menü var ama tıklayınca boş

**Çözüm:**
```bash
1. Tarayıcı cache temizle (CTRL+SHIFT+DELETE)
2. Hard refresh (CTRL+F5)
3. Botu yeniden başlat
```

---

### CSS Stilleri Yüklenmiyor

**Sorun:** Paneller alt alta, yan yana değil

**Çözüm:**
```bash
1. Tarayıcı Developer Tools aç (F12)
2. Console'da hata var mı kontrol et
3. Cache temizle
4. Botu yeniden başlat
```

---

### İndikatör Eklenmiyor

**Sorun:** "+" butonuna tıklayınca hiçbir şey olmuyor

**Çözüm:**
```bash
1. Browser Console aç (F12)
2. Hata mesajı var mı kontrol et
3. strategy-builder.js yüklenmiş mi kontrol et
4. Botu yeniden başlat
```

---

### Test Butonu Çalışmıyor

**Sorun:** "🧪 Test Et" tıklayınca response yok

**Çözüm:**
```bash
1. API endpoint kontrol et: http://localhost:8000/docs
2. POST /api/v1/strategy/test manuel dene
3. Bot loglarını kontrol et
```

---

### Strateji Kaydedilmiyor

**Sorun:** "💾 Kaydet" tıklayınca hata

**Çözüm:**
```bash
1. artifacts/strategies/ klasörü var mı kontrol et
2. Yoksa oluştur: mkdir artifacts\strategies
3. Yazma izni var mı kontrol et
4. Botu yeniden başlat
```

---

## 📞 DESTEK

**Sorun mu var?**

1. **Dokümantasyon:** `/knowledge` klasörü
2. **GitHub Issues:** https://github.com/prepheadrus/Crypto_Automat/issues
3. **Log Dosyaları:** Bot terminal çıktısı

---

*Son Güncelleme: Mart 2026*  
*CryptoAlgoBot Development Team*
