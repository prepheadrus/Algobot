# ⚙️ Configuration Guide

**Version:** v4.1.0  
**Status:** ✅ Production Ready  
**Category:** Configuration / Setup  
**Last Updated:** March 2026

---

## 📋 Overview

Configuration Guide, `config.yaml` dosyasının detaylı açıklamasıdır. Tüm ayarlar, parametreler ve önerilen değerler.

**File Location:**
```
config.yaml
```

---

## 🏗️ File Structure

```yaml
config.yaml
├── bot                    # General bot settings
├── trading                # Trading configuration
├── risk_management        # Risk controls
├── ml                     # Machine learning
├── htf                    # Higher timeframe analysis
├── wfo                    # Walk-forward optimization
├── kalman                 # Kalman filter
├── candle_lock            # Candle close locking
└── strategy               # Strategy modules
```

---

## 🔧 Section-by-Section Guide

### **1. Bot Settings**

```yaml
bot:
  environment: development    # development | production
  exchange: binance           # binance | kucoin | okx
  log_level: INFO             # DEBUG | INFO | WARNING | ERROR
  name: CryptoAlgoBot
```

**Parameters:**

| Parameter | Values | Default | Description |
|-----------|--------|---------|-------------|
| `environment` | `development`, `production` | `development` | Log format, reload mode |
| `exchange` | `binance`, `kucoin`, `okx` | `binance` | Exchange to trade |
| `log_level` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` | Verbosity level |
| `name` | Any string | `CryptoAlgoBot` | Bot identifier |

**Recommendations:**

```yaml
# Development (Local Testing)
bot:
  environment: development
  log_level: DEBUG  # Verbose logging

# Production (Live Trading)
bot:
  environment: production
  log_level: INFO   # Less verbose
```

---

### **2. Trading Settings**

```yaml
trading:
  exchange: binance
  symbols: []                  # Auto-load from Parquet if empty
  timeframes:
    - 1m
    - 5m
    - 1h
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `symbols` | List | `[]` | Symbols to trade (empty = auto-load) |
| `timeframes` | List | `[1m, 5m, 1h]` | Timeframes to monitor |

**Examples:**

```yaml
# Single symbol
trading:
  symbols:
    - BTC/USDT

# Multiple symbols
trading:
  symbols:
    - BTC/USDT
    - ETH/USDT
    - BNB/USDT

# All symbols from Parquet (recommended)
trading:
  symbols: []  # Auto-loads all available symbols
```

---

### **3. Risk Management**

```yaml
risk_management:
  default_leverage: 1
  max_leverage: 10
  max_open_positions: 10
  max_risk_per_trade_percent: 1.5
  
  kill_switch:
    enabled: false
    max_consecutive_losses: 10
  
  max_daily_loss: 0.1          # 10%
  max_drawdown: 0.20           # 20%
```

**Parameters:**

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `default_leverage` | Int | 1-125 | `1` | Default leverage |
| `max_leverage` | Int | 1-125 | `10` | Maximum allowed leverage |
| `max_open_positions` | Int | 1-50 | `10` | Max concurrent positions |
| `max_risk_per_trade_percent` | Float | 0.1-5.0 | `1.5` | Risk per trade (%) |
| `kill_switch.enabled` | Bool | - | `false` | Enable kill switch |
| `kill_switch.max_consecutive_losses` | Int | 1-20 | `10` | Losses before stop |
| `max_daily_loss` | Float | 0.01-0.50 | `0.1` | Max daily loss (10%) |
| `max_drawdown` | Float | 0.05-0.50 | `0.20` | Max drawdown (20%) |

**Recommendations:**

```yaml
# Conservative (Low Risk)
risk_management:
  default_leverage: 1
  max_leverage: 5
  max_open_positions: 5
  max_risk_per_trade_percent: 0.5
  kill_switch:
    enabled: true
    max_consecutive_losses: 3

# Moderate (Medium Risk)
risk_management:
  default_leverage: 3
  max_leverage: 10
  max_open_positions: 10
  max_risk_per_trade_percent: 1.0
  kill_switch:
    enabled: true
    max_consecutive_losses: 5

# Aggressive (High Risk)
risk_management:
  default_leverage: 5
  max_leverage: 20
  max_open_positions: 20
  max_risk_per_trade_percent: 2.0
  kill_switch:
    enabled: false
    max_consecutive_losses: 10
```

---

### **4. Machine Learning**

```yaml
ml:
  enabled: true
  confidence_threshold: 0.5
  
  leverage:
    normal_threshold: 0.65
    strong_threshold: 0.8
    weak_threshold: 0.5
```

**Parameters:**

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `enabled` | Bool | - | `true` | Enable ML predictions |
| `confidence_threshold` | Float | 0.3-0.9 | `0.5` | Min confidence for trade |
| `leverage.normal_threshold` | Float | 0.5-0.8 | `0.65` | Confidence for normal leverage |
| `leverage.strong_threshold` | Float | 0.7-0.95 | `0.8` | Confidence for high leverage |
| `leverage.weak_threshold` | Float | 0.3-0.6 | `0.5` | Min confidence threshold |

**Dynamic Leverage Logic:**

```python
if confidence >= 0.8:
    leverage = max_leverage  # e.g., 10x
elif confidence >= 0.65:
    leverage = normal_leverage  # e.g., 5x
elif confidence >= 0.5:
    leverage = min_leverage  # e.g., 1x
else:
    skip_trade  # Too risky
```

**Recommendations:**

```yaml
# More trades (lower threshold)
ml:
  confidence_threshold: 0.4  # More trades, lower quality

# Fewer trades (higher threshold)
ml:
  confidence_threshold: 0.7  # Fewer trades, higher quality

# Balanced
ml:
  confidence_threshold: 0.5  # Good balance
```

---

### **5. Higher Timeframe (HTF)**

```yaml
htf:
  enabled: false
  dynamic_map:
    1m:
      - 5m
      - 15m
    5m:
      - 15m
      - 1h
    15m:
      - 1h
      - 4h
    1h:
      - 4h
      - 1d
  ema_fast: 20
  ema_slow: 50
  trend_method: ema_stack
  filter_rules:
    require_all_htf_agree: false
```

**Purpose:** Multi-timeframe trend analysis (veto system)

**When to Enable:**
- ✅ Trend-following strategies
- ✅ Avoid counter-trend trades
- ❌ Scalping (too slow)

**When to Disable:**
- ✅ Scalping strategies
- ✅ Mean reversion
- ✅ More trades desired

---

### **6. Walk-Forward Optimization (WFO)**

```yaml
wfo:
  enabled: true
  train_days: 90
  test_days: 30
  reoptimize_interval: 168     # 1 week (hours)
  optimization_metric: sharpe
  min_improvement: 0.05
```

**Parameters:**

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| `enabled` | Bool | - | `true` | Enable WFO |
| `train_days` | Int | 30-365 | `90` | Days for training |
| `test_days` | Int | 7-60 | `30` | Days for testing |
| `reoptimize_interval` | Int | 24-720 | `168` | Hours between re-optimization |
| `optimization_metric` | String | - | `sharpe` | Metric to optimize |
| `min_improvement` | Float | 0.01-0.20 | `0.05` | Min improvement to apply |

**Optimization Metrics:**

```yaml
# Sharpe Ratio (Risk-adjusted return)
optimization_metric: sharpe

# Total Return
optimization_metric: return

# Max Drawdown (Minimize)
optimization_metric: max_drawdown

# Win Rate
optimization_metric: win_rate
```

---

### **7. Kalman Filter**

```yaml
kalman:
  enabled: true
  q: 0.001          # Process noise
  r: 0.1            # Measurement noise

kalman_smoothing:
  enabled: false
  measurement_noise: 0.1
  process_noise: 0.001
```

**Purpose:** Noise reduction in price data

**Parameters:**

| Parameter | Effect | Typical Range |
|-----------|--------|---------------|
| `q` (Process noise) | Higher = more responsive | 0.0001-0.01 |
| `r` (Measurement noise) | Higher = smoother | 0.01-1.0 |

---

### **8. Candle Lock**

```yaml
candle_lock:
  enabled: false
  interval: 1

candle_close_lock:
  enabled: true
  check_interval: 5
```

**Purpose:** Prevent signals on incomplete candles

**Recommendation:**
```yaml
# Enable for production
candle_close_lock:
  enabled: true
  check_interval: 5  # Check every 5 seconds
```

---

### **9. Strategy Modules**

```yaml
strategy:
  active_modules:
    - trend_following
    - mean_reversion
  atr_sl_multiplier: 3.0
  atr_tp_multiplier: 6.0
  ml_confidence_threshold: 0.6
```

**Modules:**

| Module | Description | Best For |
|--------|-------------|----------|
| `trend_following` | Follow trend direction | Trending markets |
| `mean_reversion` | Trade reversals | Ranging markets |

---

## 🎯 Complete Config Examples

### **Example 1: Conservative Bot**

```yaml
bot:
  environment: production
  exchange: binance
  log_level: INFO

trading:
  symbols:
    - BTC/USDT
  timeframes:
    - 1h

risk_management:
  default_leverage: 1
  max_leverage: 3
  max_open_positions: 3
  max_risk_per_trade_percent: 0.5
  kill_switch:
    enabled: true
    max_consecutive_losses: 3

ml:
  enabled: true
  confidence_threshold: 0.7

htf:
  enabled: true

wfo:
  enabled: true
  train_days: 60
  reoptimize_interval: 336  # 2 weeks
```

---

### **Example 2: Aggressive Scalping Bot**

```yaml
bot:
  environment: development
  exchange: binance
  log_level: DEBUG

trading:
  symbols:
    - BTC/USDT
    - ETH/USDT
    - BNB/USDT
  timeframes:
    - 1m
    - 3m

risk_management:
  default_leverage: 10
  max_leverage: 20
  max_open_positions: 20
  max_risk_per_trade_percent: 2.0
  kill_switch:
    enabled: false

ml:
  enabled: false  # Too slow for scalping

htf:
  enabled: false  # No veto

wfo:
  enabled: false
```

---

### **Example 3: Balanced Multi-Bot**

```yaml
bot:
  environment: production
  exchange: binance
  log_level: INFO

trading:
  symbols: []  # Auto-load all
  timeframes:
    - 1m
    - 5m
    - 1h

risk_management:
  default_leverage: 3
  max_leverage: 10
  max_open_positions: 10
  max_risk_per_trade_percent: 1.0
  kill_switch:
    enabled: true
    max_consecutive_losses: 5

ml:
  enabled: true
  confidence_threshold: 0.5

htf:
  enabled: false

wfo:
  enabled: true
  train_days: 90
  test_days: 30
  reoptimize_interval: 168
```

---

## 🔍 Troubleshooting

### **Config Not Loading**

**Symptoms:**
- Bot uses default values
- Changes ignored

**Solutions:**
1. **Check YAML syntax:**
   ```bash
   python -c "import yaml; yaml.safe_load(open('config.yaml'))"
   ```

2. **Check indentation:**
   ```yaml
   # Wrong
   risk_management:
   max_leverage: 10  # Not indented!
   
   # Correct
   risk_management:
     max_leverage: 10
   ```

3. **Restart bot:**
   ```bash
   # Config only loads on startup
   CTRL+C
   python main.py
   ```

---

## 📚 Related Files

| File | Purpose |
|------|---------|
| `config.yaml` | Main configuration |
| `config.example.yaml` | Template |
| `config.aggressive.yaml` | Aggressive preset |
| `core/config.py` | Config loader |

---

## 🔄 Changelog

| Version | Date | Changes |
|---------|------|---------|
| v4.0.0 | Jan 2026 | Initial structure |
| v4.1.0 | Mar 2026 | Added ML, HTF, WFO sections |

---

**Author:** CryptoAlgoBot Team  
**Review Status:** ✅ Peer Reviewed  
**Next Review:** April 2026
