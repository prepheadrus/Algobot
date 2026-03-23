# 🎨 No-Code Strateji Oluşturucu (Strategy Builder)

**Öncelik:** 🔥 YÜKSEK  
**Durum:** Planlama  
**Tahmini Süre:** 4 hafta

---

## 📋 İÇİNDEKİLER

1. [Özellik Tanımı](#1-özellik-tanımı)
2. [Kullanıcı Hikayesi](#2-kullanıcı-hikayesi)
3. [Teknik Mimari](#3-teknik-mimari)
4. [UI/UX Tasarımı](#4-uiux-tasarımı)
5. [JSON Strateji Formatı](#5-json-strateji-formatı)
6. [Uygulama Adımları](#6-uygulama-adımları)

---

## 1. ÖZELLİK TANIMI

### 🎯 Amaç
Kullanıcıların **kod yazmadan**, görsel arayüz ile kendi trading stratejilerini oluşturabilmeleri.

### 🔑 Ana Özellikler

1. **Gösterge Kütüphanesi**
   - 22+ hazır indikatör
   - Kategorilere ayrılmış (Trend, Momentum, Volatilite, Hacim)
   - Arama ve filtreleme

2. **Koşul Oluşturucu**
   - Mantıksal operatörler (VE, VEYA, DEĞİL)
   - Karşılaştırma operatörleri (<, >, =, <=, >=)
   - İç içe koşullar

3. **Parametre Ayarlama**
   - Her indikatör için özelleştirilebilir parametreler
   - Slider ve input alanları
   - Varsayılan değerler

4. **Strateji Testi**
   - Hızlı backtest
   - Görsel sonuçlar
   - Performans metrikleri

5. **Kaydetme ve Paylaşma**
   - JSON formatında kaydetme
   - Strateji import/export
   - Community library (gelecek)

---

## 2. KULLANICI HİKAYESİ

### Senaryo: Basit RSI + MACD Stratejisi

**Adım 1: Yeni Strateji Oluştur**
```
Dashboard → Strateji Laboratuvarı → "Yeni Strateji"
Strateji Adı: "RSI MACD Combo"
```

**Adım 2: Göstergeleri Ekle**
```
[+] Gösterge Ekle → Momentum → RSI
  - Period: 14 (varsayılan)

[+] Gösterge Ekle → Trend → MACD
  - Fast: 12, Slow: 26, Signal: 9
```

**Adım 3: Koşulları Belirle**
```
LONG Koşulu:
  [RSI < 30] VE [MACD > Signal]

SHORT Koşulu:
  [RSI > 70] VE [MACD < Signal]
```

**Adım 4: Risk Ayarları**
```
Stop Loss: 2.0x ATR
Take Profit: 3.0x ATR
Max Position: %2 risk
```

**Adım 5: Test Et**
```
[Test Strateji] → BTC/USDT, 15m, Son 30 gün
Sonuç: Win Rate %62, Profit Factor 1.8
```

**Adım 6: Kaydet ve Kullan**
```
[Kaydet] → Strateji listesinde görünür
[Aktif Et] → Bot bu stratejiyi kullanır
```

---

## 3. TEKNİK MİMARİ

### 📁 Dosya Yapısı

```
strategy/
├── builder/                  # Yeni klasör
│   ├── __init__.py
│   ├── strategy_builder.py   # Ana builder sınıfı
│   ├── condition_parser.py   # Koşul parser
│   ├── json_validator.py     # JSON validasyonu
│   └── executor.py           # Strateji çalıştırıcı
│
├── indicators/               # Mevcut indikatörler
│   └── ... (mevcut)
│
└── manager.py                # Güncellenecek
```

### 🔄 Veri Akışı

```
User Input (Dashboard)
    ↓
JSON Strategy Definition
    ↓
Condition Parser → AST (Abstract Syntax Tree)
    ↓
Strategy Executor → Signal Generation (0/1/2)
    ↓
Paper Trader → Execution
```

---

## 4. UI/UX TASARIMI

### 🎨 Dashboard - Strateji Laboratuvarı

```
┌─────────────────────────────────────────────────────────┐
│  🎨 Strateji Oluşturucu                    [Kaydet] [X] │
├─────────────────────────────────────────────────────────┤
│  Strateji Adı: [___________________]                    │
│                                                         │
│  ┌─────────────────────┐  ┌──────────────────────────┐ │
│  │ 📚 Gösterge Kütüphanesi│  │ ⚙️ Koşul Oluşturucu    │ │
│  ├─────────────────────┤  ├──────────────────────────┤ │
│  │ 🔍 Ara...           │  │ LONG Koşulları:          │ │
│  │                     │  │ ┌────────────────────┐   │ │
│  │ 📈 TREND            │  │ │ [RSI] [<] [30]   │   │ │
│  │ ├─ EMA              │  │ │   [VE]             │   │ │
│  │ ├─ SMA              │  │ │ [MACD] [>] [Signal]│  │ │
│  │ ├─ Supertrend       │  │ └────────────────────┘   │ │
│  │                     │  │                          │ │
│  │ 🚀 MOMENTUM         │  │ SHORT Koşulları:         │ │
│  │ ├─ RSI         [+]  │  │ ┌────────────────────┐   │ │
│  │ ├─ MACD        [+]  │  │ │ [RSI] [>] [70]   │   │ │
│  │ ├─ Stochastic  [+]  │  │ │   [VE]             │   │ │
│  │                     │  │ │ [MACD] [<] [Signal]│  │ │
│  │ 📊 VOLATİLİTE       │  │ └────────────────────┘   │ │
│  │ ├─ ATR           [+] │  │                          │ │
│  │ ├─ Bollinger     [+] │  │ [➕ Koşul Ekle]         │ │
│  │                     │  │                          │ │
│  │ 💰 HACİM            │  │ 🎯 Risk Ayarları:        │ │
│  │ ├─ OBV           [+] │  │ Stop: [2.0]x ATR       │ │
│  │ ├─ VWAP          [+] │  │ Take Profit: [3.0]x    │ │
│  │ └─ MFI           [+] │  │ Risk: [%2]             │ │
│  │                     │  │                          │ │
│  │ [+ Kategori Ekle]   │  │ [🧪 Test Et] [💾 Kaydet] │ │
│  └─────────────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### 🎯 İnteraktif Özellikler

1. **Drag & Drop**
   - Göstergeleri koşula sürükle
   - Koşulları yeniden sırala
   - Grupları iç içe yerleştir

2. **Real-time Preview**
   - Koşul yazılırken syntax kontrolü
   - Renkli syntax highlighting
   - Hata mesajları

3. **Tooltip Yardım**
   - Her indikatör açıklaması
   - Parametre aralıkları
   - Örnek kullanımlar

---

## 5. JSON STRATEJİ FORMATI

### 📄 Örnek Strateji JSON

```json
{
  "name": "RSI MACD Combo",
  "description": "RSI aşırı alım/satım + MACD momentum",
  "version": "1.0",
  "author": "Kullanıcı",
  "timeframe": "15m",
  "indicators": [
    {
      "id": "ind_1",
      "type": "RSI",
      "parameters": {
        "length": 14
      }
    },
    {
      "id": "ind_2",
      "type": "MACD",
      "parameters": {
        "fast": 12,
        "slow": 26,
        "signal": 9
      }
    }
  ],
  "conditions": {
    "long": {
      "logic": "AND",
      "rules": [
        {
          "indicator": "ind_1",
          "operator": "<",
          "value": 30
        },
        {
          "indicator": "ind_2",
          "operator": ">",
          "value": "signal"
        }
      ]
    },
    "short": {
      "logic": "AND",
      "rules": [
        {
          "indicator": "ind_1",
          "operator": ">",
          "value": 70
        },
        {
          "indicator": "ind_2",
          "operator": "<",
          "value": "signal"
        }
      ]
    }
  },
  "risk": {
    "stop_loss": {
      "type": "ATR",
      "multiplier": 2.0
    },
    "take_profit": {
      "type": "ATR",
      "multiplier": 3.0
    },
    "max_risk_percent": 2.0
  }
}
```

### 🔍 JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["name", "indicators", "conditions"],
  "properties": {
    "name": {"type": "string"},
    "description": {"type": "string"},
    "version": {"type": "string"},
    "indicators": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "type"],
        "properties": {
          "id": {"type": "string"},
          "type": {"type": "string", "enum": ["RSI", "MACD", "EMA", "..."]},
          "parameters": {"type": "object"}
        }
      }
    },
    "conditions": {
      "type": "object",
      "required": ["long", "short"],
      "properties": {
        "long": {"$ref": "#/definitions/condition"},
        "short": {"$ref": "#/definitions/condition"}
      }
    }
  },
  "definitions": {
    "condition": {
      "type": "object",
      "required": ["logic", "rules"],
      "properties": {
        "logic": {"type": "string", "enum": ["AND", "OR"]},
        "rules": {
          "type": "array",
          "items": {"$ref": "#/definitions/rule"}
        }
      }
    },
    "rule": {
      "type": "object",
      "required": ["indicator", "operator"],
      "properties": {
        "indicator": {"type": "string"},
        "operator": {"type": "string", "enum": ["<", ">", "=", "<=", ">="]},
        "value": {"type": ["number", "string"]}
      }
    }
  }
}
```

---

## 6. UYGULAMA ADIMLARI

### Hafta 1: Backend Core

- [ ] **strategy_builder.py**
  - Indicator registry
  - Condition evaluator
  - Signal generator

- [ ] **condition_parser.py**
  - JSON parser
  - AST builder
  - Validation

- [ ] **executor.py**
  - Runtime execution
  - Performance optimization

### Hafta 2: Frontend UI

- [ ] **Dashboard Component**
  - Indicator library panel
  - Condition builder panel
  - Drag & drop implementation

- [ ] **Visual Elements**
  - Dropdown menus
  - Input fields
  - Logic operators

### Hafta 3: Testing & Validation

- [ ] **JSON Validator**
  - Schema validation
  - Error messages
  - Auto-fix suggestions

- [ ] **Backtest Integration**
  - Quick test function
  - Performance metrics
  - Visual results

### Hafta 4: Polish & Documentation

- [ ] **User Experience**
  - Tooltips
  - Help documentation
  - Example strategies

- [ ] **Save/Load System**
  - File save (JSON)
  - File load
  - Import/Export

---

## 📊 ÖRNEK STRATEJİLER

### 1. Basit RSI Stratejisi

```json
{
  "name": "RSI Oversold",
  "indicators": [{"id": "rsi_1", "type": "RSI", "parameters": {"length": 14}}],
  "conditions": {
    "long": {"logic": "AND", "rules": [{"indicator": "rsi_1", "operator": "<", "value": 30}]},
    "short": {"logic": "AND", "rules": [{"indicator": "rsi_1", "operator": ">", "value": 70}]}
  }
}
```

### 2. EMA Crossover

```json
{
  "name": "EMA Cross",
  "indicators": [
    {"id": "ema_fast", "type": "EMA", "parameters": {"length": 9}},
    {"id": "ema_slow", "type": "EMA", "parameters": {"length": 21}}
  ],
  "conditions": {
    "long": {"logic": "AND", "rules": [
      {"indicator": "ema_fast", "operator": ">", "value": "ema_slow"}
    ]},
    "short": {"logic": "AND", "rules": [
      {"indicator": "ema_fast", "operator": "<", "value": "ema_slow"}
    ]}
  }
}
```

### 3. Complex Multi-Indicator

```json
{
  "name": "Triple Confirmation",
  "indicators": [
    {"id": "rsi", "type": "RSI"},
    {"id": "macd", "type": "MACD"},
    {"id": "bb", "type": "Bollinger"}
  ],
  "conditions": {
    "long": {
      "logic": "AND",
      "rules": [
        {"indicator": "rsi", "operator": "<", "value": 30},
        {"indicator": "macd", "operator": ">", "value": "signal"},
        {"indicator": "close", "operator": "<", "value": "bb_lower"}
      ]
    }
  }
}
```

---

## 🎯 BAŞARI KRİTERLERİ

| Kriter | Hedef |
|--------|-------|
| Kullanılabilirlik | 5 dakikada ilk strateji |
| Performans | < 100ms signal generation |
| Hata Oranı | <%1 invalid strategy |
| Kullanıcı Memnuniyeti | > 4.5/5 |

---

*Oluşturulma: Mart 2026*  
*CryptoAlgoBot Development Team*
