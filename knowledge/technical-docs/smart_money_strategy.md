# Smart Money Stratejisi

## Genel Bakış

Smart Money (Akıllı Para) stratejisi, kurumsal yatırımcıların hareketlerini tespit etmek için RSI, MACD ve OBV (On Balance Volume) indikatörlerini birleştiren konfluans tabanlı bir trading stratejisidir.

**WFO (Walk-Forward Optimization) Uyumlu:** ✅
- Auto-Grid ile otomatik parametre optimizasyonu
- Bayesian Optimization ile hızlı optimizasyon
- Otonom parametre adaptasyonu

---

## Strateji Detayları

### İndikatörler

| İndikatör | Parametre | Açıklama |
|-----------|-----------|----------|
| **RSI** | period=14 | Momentum ölçümü |
| **MACD** | fast=12, slow=26, signal=9 | Trend yönü |
| **OBV** | period=14 | Akıllı para girişi/çıkışı |

### LONG Sinyali Şartları

Tüm şartlar sağlanmalı:

1. **MACD > Signal** (trend yukarı)
2. **RSI > 50** VEYA **RSI 30'dan yukarı kesmiş** (momentum)
3. **OBV artışta** (akıllı para girişi)

```python
macd_bullish = current_macd > current_signal
rsi_bullish = (current_rsi > 50) or (previous_rsi <= 30 and current_rsi > 30)
obv_increasing = current_obv > previous_obv

if macd_bullish and rsi_bullish and obv_increasing:
    return 2  # LONG
```

### SHORT Sinyali Şartları

Tüm şartlar sağlanmalı:

1. **MACD < Signal** (trend aşağı)
2. **OBV düşüşte** (akıllı para çıkışı)

```python
macd_bearish = current_macd < current_signal
obv_decreasing = current_obv < previous_obv

if macd_bearish and obv_decreasing:
    return 0  # SHORT
```

### Risk Yönetimi

```python
def get_stop_params(self):
    return {
        'atr_multiplier': 2.0,      # Stop Loss = ATR × 2
        'risk_reward_ratio': 3.0    # Take Profit = 3x Stop Loss
    }
```

**RRR = 3.0** (Take Profit = 3x Stop Loss mesafesi)

---

## WFO Parametreleri

### DEFAULT_PARAMS

```python
DEFAULT_PARAMS = {
    'rsi_period': 14,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'obv_period': 14
}
```

### Auto-Grid Oluşturacağı Aralıklar

| Parametre | Varsayılan | Alt (%30) | Orta | Üst (%30) |
|-----------|------------|-----------|------|-----------|
| `rsi_period` | 14 | 10 | 14 | 20 |
| `macd_fast` | 12 | 8 | 12 | 16 |
| `macd_slow` | 26 | 18 | 26 | 34 |
| `macd_signal` | 9 | 6 | 9 | 12 |
| `obv_period` | 14 | 10 | 14 | 20 |

**Toplam Kombinasyon:** 3^5 = **243 kombinasyon**

**Bayesian Optimization ile:** Sadece **50 deneme** ile optimum bulunur.

---

## Kullanım

### 1. Manuel Kullanım

```python
from strategy.custom.smart_money import SmartMoneyStrategy

# Strateji instance
strategy = SmartMoneyStrategy()

# Sinyal üret
signal = strategy.generate_signal(df)

# Stop parametreleri
stop_params = strategy.get_stop_params()
```

### 2. WFO ile Optimizasyon

```python
from core.wfo_engine import start_wfo_background_task, OptimizationConfig
from strategy.custom.smart_money import SmartMoneyStrategy

# config oluştur (param_grid=None → Auto-Grid otomatik oluşturur)
config = OptimizationConfig(
    symbol="BTCUSDT",
    timeframe="1m",
    strategy_class=SmartMoneyStrategy,
    param_grid=None,  # Auto-Grid otomatik oluşturur
    optimization_metric="sharpe",
    n_trials=50
)

# Arka plan optimizasyonu başlat
asyncio.create_task(start_wfo_background_task(config))
```

### 3. Canlı Parametre Güncelleme

```python
# WFO optimum parametreleri buldu
new_params = {
    'rsi_period': 16,
    'macd_fast': 10,
    'macd_slow': 28,
    'macd_signal': 8,
    'obv_period': 12
}

# Stratejiye canlı olarak uygula
strategy.update_params(new_params)

# Log:
# 🎯 [WFO-AUTO-TUNE] BTCUSDT (1m) piyasa rejimine adapte oldu!
# Yeni Parametreler: rsi_period: 14 -> 16, macd_fast: 12 -> 10
```

---

## Dosya Yapısı

```
strategy/custom/
└── smart_money.py
    ├── SmartMoneyStrategy
    │   ├── DEFAULT_PARAMS
    │   ├── __init__()
    │   ├── name()
    │   ├── description()
    │   ├── timeframe()
    │   ├── get_stop_params()
    │   ├── update_params()       # WFO için
    │   └── generate_signal()
    └── (WFO uyumlu)
```

---

## Log Örnekleri

### LONG Sinyali

```
🟢 SMART MONEY LONG | RSI: 55.23 | MACD: 0.0234 > Signal: 0.0187 | OBV: 1234567 > 1230000
```

### SHORT Sinyali

```
🔴 SMART MONEY SHORT | RSI: 42.15 | MACD: -0.0156 < Signal: -0.0123 | OBV: 987654 < 990000
```

### WFO Optimizasyonu

```
🤖 [ZERO-TOUCH] BTCUSDT için otomatik parametre ızgarası oluşturuluyor...
📊 SmartMoneyStrategy DEFAULT_PARAMS analizi: 5 parametre
  📍 rsi_period: 14 → [10, 14, 20]
  📍 macd_fast: 12 → [8, 12, 16]
  📍 macd_slow: 26 → [18, 26, 34]
  📍 macd_signal: 9 → [6, 9, 12]
  📍 obv_period: 14 → [10, 14, 20]
✅ [ZERO-TOUCH] Auto-Grid 5 parametre oluşturdu

🧠 [BAYES-OPT] Bayesian Optimization başlatılıyor (50 trial)...
...
✅ [BAYES-OPT] Optimizasyon tamamlandı!
📈 [BAYES-OPT] En iyi sharpe: 1.5234
🎯 [BAYES-OPT] En iyi parametreler: {'rsi_period': 16, 'macd_fast': 10, 'macd_slow': 28, 'macd_signal': 8, 'obv_period': 12}

🎯 [WFO-AUTO-TUNE] BTCUSDT (1m) piyasa rejimine adapte oldu!
Yeni Parametreler: rsi_period: 14 -> 16, macd_fast: 12 -> 10, macd_slow: 26 -> 28 (Beklenen Sharpe: 1.52)
```

---

## Performans

### Backtest Sonuçları (Örnek)

| Metrik | Değer |
|--------|-------|
| **Toplam İşlem** | 156 |
| **Kazanma Oranı** | 62.8% |
| **Profit Factor** | 1.85 |
| **Max Drawdown** | -8.2% |
| **Sharpe Ratio** | 1.52 |
| **Avg R:R** | 3.0 |

### WFO Öncesi vs Sonrası

| Metrik | Önce | Sonra | İyileştirme |
|--------|------|-------|-------------|
| Sharpe | 1.23 | 1.52 | +23.6% |
| Win Rate | 58.3% | 62.8% | +4.5% |
| Profit Factor | 1.62 | 1.85 | +14.2% |

---

## Strateji Geliştirme

### Yeni İndikatör Ekleme

```python
def generate_signal(self, df: pd.DataFrame) -> int:
    # Mevcut indikatörler
    rsi = MomentumIndicators.rsi(df['close'], period=self.params['rsi_period'])
    macd_data = MomentumIndicators.macd(...)
    obv = VolumeIndicators.obv(...)
    
    # YENİ: ADX trend gücü
    adx = TrendIndicators.adx(df, period=14)
    current_adx = adx.iloc[-1]
    
    # ADX > 25 (güçlü trend)
    trend_strong = current_adx > 25
    
    # LONG: Tüm şartlar + ADX
    if macd_bullish and rsi_bullish and obv_increasing and trend_strong:
        return 2  # LONG
```

### DEFAULT_PARAMS Güncelleme

```python
DEFAULT_PARAMS = {
    'rsi_period': 14,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'obv_period': 14,
    'adx_period': 14  # YENİ
}
```

---

## Sorun Giderme

### WFO Parametreleri Uygulanmıyor

**Hata:**
```
⚠️ [WFO] BTCUSDT için strateji bulunamadı, parametre güncellenemedi.
```

**Çözüm:** Botun çalıştığından ve stratejinin aktif olduğundan emin olun.

### DEFAULT_PARAMS Bulunamadı

**Hata:**
```
⚠️ SmartMoneyStrategy için DEFAULT_PARAMS bulunamadı!
```

**Çözüm:** Strateji sınıfına `DEFAULT_PARAMS` sözlüğü ekleyin.

### update_params() Yok

**Hata:**
```
❌ [WFO] BTCUSDT stratejisi update_params() metodunu desteklemiyor!
```

**Çözüm:** `update_params()` metodunu implemente edin.

---

## İlgili Dökümanlar

- [Walk-Forward Optimization](./walk_forward_optimization.md)
- [Auto-Grid Generator](./auto_grid_generator.md)
- [Bayesian Optimization](./bayesian_optimization.md)
- [Python Stratejisi Geliştirme](../strategies/python_strategies.md)

---

**Son Güncelleme:** 2026-03-13
**Yazar:** CryptoAlgoBot Team
**Durum:** ✅ WFO Uyumlu (Faz 8)
