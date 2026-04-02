# Auto-Grid Generator

## Genel Bakış

Auto-Grid Generator, strateji parametreleri için otomatik optimizasyon ızgaraları (grid) oluşturan akıllı bir modüldür. Manuel `PARAM_GRID` tanımlama zorunluluğunu kaldırarak "Zero-Touch" (Sıfır Temas) optimizasyon sağlar.

## Özellikler

### Python Stratejileri İçin Introspection
- ✅ `DEFAULT_PARAMS` sözlüğünü okur
- ✅ %30 esnetme (flex ratio) ile 3'lü arama uzayları
- ✅ Otomatik tip tespiti (int/float)

### No-Code Stratejiler İçin Auto-Mapping
- ✅ Indikatör isimlerini okur
- ✅ Mantıklı aralıklar atar
- ✅ 40+ indikatör desteği

### Desteklenen Indikatörler

| Indikatör | Parametreler | Aralık |
|-----------|--------------|--------|
| **RSI** | period, upper, lower | 10-50, 50-80, 20-40 |
| **MACD** | fast, slow, signal | 8-16, 20-35, 7-15 |
| **EMA** | fast, slow | 5-34, 50-200 |
| **SMA** | period | 10-100 |
| **ATR** | multiplier | 1.5-4.0 |
| **Bollinger** | std, period | 1.5-3.0, 14-30 |
| **Stochastic** | k, d, oversold | 10-25, 10-25, 15-30 |
| **ADX** | period | 14-28 |
| **CCI** | period | 14-30 |
| **Williams %R** | period | 14-30 |

---

## Mimari

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Strateji Sınıfı Okunur                                   │
│    - DEFAULT_PARAMS sözlüğü alınır                          │
│    - Örnek: {'rsi_period': 14, 'atr_multiplier': 3.5}      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. %30 Esnetme Uygulanır                                    │
│    - Alt: default × 0.70                                    │
│    - Orta: default                                          │
│    - Üst: default × 1.30                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. 3'lü Arama Uzayı Oluşturulur                             │
│    - rsi_period: 14 → [10, 14, 20]                          │
│    - atr_multiplier: 3.5 → [2.45, 3.5, 4.55]               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Optuna Search Space'e Dönüştürülür                       │
│    - {'type': 'int', 'low': 10, 'high': 20}                │
│    - {'type': 'float', 'low': 2.45, 'high': 4.55}          │
└─────────────────────────────────────────────────────────────┘
```

---

## Kullanım

### 1. Python Stratejisi İçin

```python
from core.auto_grid import generate_param_grid
from strategy.trend_master import TrendMasterPro

# Otomatik ızgara oluştur
param_grid = generate_param_grid(strategy_class=TrendMasterPro)

# Çıktı:
{
    'rsi_period': [10, 14, 20],
    'rsi_upper': [49, 70, 91],
    'rsi_lower': [21, 30, 39],
    'atr_multiplier': [2.45, 3.5, 4.55],
    'tp_multiplier': [1.4, 2.0, 2.6],
    'ema_fast': [14, 20, 26],
    'ema_slow': [140, 200, 260]
}
```

### 2. No-Code (JSON) Strateji İçin

```python
from core.auto_grid import generate_param_grid

# JSON strateji konfigürasyonu
strategy_config = {
    "name": "My Custom Strategy",
    "long_conditions": [
        {"indicator": "RSI", "params": {"period": 14}},
        {"indicator": "MACD", "params": {"fast": 12, "slow": 26}}
    ],
    "short_conditions": [...]
}

# Otomatik ızgara oluştur
param_grid = generate_param_grid(strategy_config=strategy_config)

# Çıktı:
{
    'rsi_period': [10, 14, 20],
    'macd_fast': [8, 12, 16],
    'macd_slow': [20, 26, 32]
}
```

### 3. WFO Entegrasyonu (Otomatik)

```python
from core.wfo_engine import start_wfo_background_task, OptimizationConfig

# config oluştur (param_grid=None → Auto-Grid otomatik oluşturur)
config = OptimizationConfig(
    symbol="BTCUSDT",
    timeframe="15m",
    strategy_class=TrendMasterPro,
    param_grid=None,  # None ise auto-grid kullanılır!
    optimization_metric="sharpe"
)

asyncio.create_task(start_wfo_background_task(config))
```

---

## Esnetme Mantığı (Flex Ratio)

### Varsayılan Değer: 14
```
Alt:  14 × 0.70 = 9.8  → 10
Orta: 14 × 1.00 = 14   → 14
Üst:  14 × 1.30 = 18.2 → 20

Sonuç: [10, 14, 20]
```

### Varsayılan Değer: 3.5 (float)
```
Alt:  3.5 × 0.70 = 2.45
Orta: 3.5 × 1.00 = 3.50
Üst:  3.5 × 1.30 = 4.55

Sonuç: [2.45, 3.50, 4.55]
```

---

## INDICATOR_RANGES

### RSI (Relative Strength Index)
```python
'rsi_period': {'min': 10, 'max': 30, 'step_type': 'int'}
'rsi_upper': {'min': 50, 'max': 80, 'step_type': 'int'}
'rsi_lower': {'min': 20, 'max': 40, 'step_type': 'int'}
```

### MACD (Moving Average Convergence Divergence)
```python
'macd_fast': {'min': 8, 'max': 16, 'step_type': 'int'}
'macd_slow': {'min': 20, 'max': 35, 'step_type': 'int'}
'macd_signal': {'min': 7, 'max': 15, 'step_type': 'int'}
```

### EMA (Exponential Moving Average)
```python
'ema_fast': {'min': 5, 'max': 34, 'step_type': 'int'}
'ema_slow': {'min': 50, 'max': 200, 'step_type': 'int'}
```

### ATR (Average True Range)
```python
'atr_multiplier': {'min': 1.5, 'max': 4.0, 'step_type': 'float'}
```

### Bollinger Bands
```python
'bb_std': {'min': 1.5, 'max': 3.0, 'step_type': 'float'}
'bb_period': {'min': 14, 'max': 30, 'step_type': 'int'}
```

### Stochastic
```python
'stoch_k': {'min': 10, 'max': 25, 'step_type': 'int'}
'stoch_d': {'min': 10, 'max': 25, 'step_type': 'int'}
'stoch_oversold': {'min': 15, 'max': 30, 'step_type': 'int'}
```

---

## API Referansı

### AutoGridGenerator Sınıfı

#### `generate_from_python_strategy(strategy_class, use_flex=True)`
Python stratejisinden otomatik ızgara oluşturur.

**Args:**
- `strategy_class`: Strateji sınıfı (örn: TrendMasterPro)
- `use_flex`: %30 esnetme kullanılsın mı?

**Returns:**
- `Dict`: Parametre ızgarası

**Örnek:**
```python
from core.auto_grid import AutoGridGenerator
from strategy.trend_master import TrendMasterPro

auto_grid = AutoGridGenerator()
param_grid = auto_grid.generate_from_python_strategy(TrendMasterPro)
```

#### `generate_from_json_strategy(strategy_config)`
No-Code strateji konfigürasyonundan otomatik ızgara oluşturur.

**Args:**
- `strategy_config`: JSON strateji konfigürasyonu

**Returns:**
- `Dict`: Parametre ızgarası

#### `_create_flex_range(default_value, param_name)`
Varsayılan değerin %30 etrafında 3'lü arama uzayı oluşturur.

**Args:**
- `default_value`: Varsayılan değer
- `param_name`: Parametre adı

**Returns:**
- `List`: 3 değerli liste [düşük, orta, yüksek]

#### `_convert_to_search_space(param_grid)`
Auto-Grid param_grid'i Optuna search space'e dönüştürür.

**Args:**
- `param_grid`: {'rsi_period': [10, 14, 20], ...}

**Returns:**
- `Dict`: {'rsi_period': {'type': 'int', 'low': 10, 'high': 20}, ...}

---

## Helper Fonksiyonlar

### `get_auto_grid()`
Auto-Grid Generator instance'ını alır (yoksa oluşturur).

```python
from core.auto_grid import get_auto_grid

auto_grid = get_auto_grid()
param_grid = auto_grid.generate_from_python_strategy(TrendMasterPro)
```

### `generate_param_grid(strategy_class=None, strategy_config=None)`
Kolay kullanım için helper fonksiyon.

**Args:**
- `strategy_class`: Python strateji sınıfı
- `strategy_config`: JSON strateji konfigürasyonu

**Returns:**
- `Dict`: Parametre ızgarası

**Örnek:**
```python
from core.auto_grid import generate_param_grid

# Python stratejisi için
param_grid = generate_param_grid(strategy_class=TrendMasterPro)

# JSON stratejisi için
param_grid = generate_param_grid(strategy_config=strategy_config)
```

---

## Log Örnekleri

### Python Stratejisi Analizi
```
🤖 Auto-Grid Generator başlatıldı
📊 TrendMasterPro DEFAULT_PARAMS analizi: 7 parametre
  📍 rsi_period: 14 → [10, 14, 20]
  📍 rsi_upper: 70 → [49, 70, 91]
  📍 rsi_lower: 30 → [21, 30, 39]
  📍 atr_multiplier: 3.5 → [2.45, 3.5, 4.55]
  📍 tp_multiplier: 2.0 → [1.4, 2.0, 2.6]
  📍 ema_fast: 20 → [14, 20, 26]
  📍 ema_slow: 200 → [140, 200, 260]
✅ TrendMasterPro için 7 parametre ızgarası oluşturuldu
```

### WFO Otomatik Izgara
```
🔄 [WFO] BTCUSDT için arka plan optimizasyonu başlatılıyor...
🤖 [WFO] BTCUSDT için otomatik parametre ızgarası oluşturuluyor...
📊 TrendMasterPro DEFAULT_PARAMS analizi: 7 parametre
✅ TrendMasterPro için 7 parametre ızgarası oluşturuldu
🔄 [WFO] Arka plan görevi başlatıldı: BTCUSDT (15m)
✅ [WFO] BTCUSDT arka plan görevi başlatıldı.
```

---

## Strateji Geliştirme

### Zero-Touch Uyumlu Python Stratejisi

```python
from strategy.base import BaseStrategy
import pandas as pd

class MyStrategy(BaseStrategy):
    """
    WFO (Walk-Forward Optimization) Destekli:
    - Auto-Grid ile otomatik parametre ızgarası
    - Bayesian Optimization ile hızlı optimizasyon
    - Otonom parametre adaptasyonu
    """

    # Varsayılan parametreler (Auto-Grid bu değerlerden %30 esnetme yapar)
    DEFAULT_PARAMS = {
        'rsi_period': 14,
        'atr_multiplier': 3.0,
        'tp_multiplier': 2.0,
    }

    def __init__(self):
        self.params = self.DEFAULT_PARAMS.copy()

    def name(self) -> str:
        return "My Strategy"

    def generate_signal(self, current_row: pd.Series) -> int:
        rsi_period = self.params.get('rsi_period', 14)
        # ... sinyal mantığı
        
    def get_stop_params(self):
        return {
            "atr_multiplier": self.params.get('atr_multiplier', 3.0),
            "tp_multiplier": self.params.get('tp_multiplier', 2.0)
        }

    def update_params(self, new_params: dict):
        """WFO tarafından bulunan yeni parametreleri uygular."""
        for key, value in new_params.items():
            if key in self.params:
                self.params[key] = value
        return self.params
```

**ÖNEMLİ:** `PARAM_GRID` tanımlamaya GEREK YOK! Auto-Grid `DEFAULT_PARAMS`'dan otomatik oluşturur.

---

## Performans

### Izgara Oluşturma Süresi

| Strateji | Parametre Sayesi | Süre |
|----------|------------------|------|
| TrendMasterPro | 7 | 0.01s |
| ScalperNinja | 7 | 0.01s |
| Custom (10 param) | 10 | 0.02s |

### Kombinasyon Sayısı

| Parametre Sayesi | Değerler | Toplam |
|------------------|----------|--------|
| 7 | 3^7 | 2,187 |
| 10 | 3^10 | 59,049 |
| 15 | 3^15 | 14,348,907 |

**Bayesian Optimization ile:**
- 2,187 kombinasyon → 50 deneme
- 59,049 kombinasyon → 50 deneme
- 14M+ kombinasyon → 50 deneme

---

## Sorun Giderme

### DEFAULT_PARAMS Bulunamadı
```
⚠️ MyStrategy için DEFAULT_PARAMS bulunamadı!
```
**Çözüm:** Strateji sınıfına `DEFAULT_PARAMS` sözlüğü ekleyin.

### Bilinmeyen Parametre
```
⚠️ custom_param rakamsal değil, atlanıyor
```
**Çözüm:** Sadece int/float parametreler desteklenir.

### Auto-Grid Mevcut Değil
```
⚠️ Auto-Grid Generator bulunamadı, manuel PARAM_GRID kullanılıyor.
```
**Çözüm:** `core/auto_grid.py` dosyasının varlığını kontrol edin.

---

## İlgili Dökümanlar

- [Walk-Forward Optimization](./walk_forward_optimization.md)
- [Bayesian Optimization](./bayesian_optimization.md)
- [Strategy Development](../strategies/python_strategies.md)

---

**Son Güncelleme:** 2026-03-08  
**Yazar:** CryptoAlgoBot Team  
**Durum:** ✅ Production Ready
