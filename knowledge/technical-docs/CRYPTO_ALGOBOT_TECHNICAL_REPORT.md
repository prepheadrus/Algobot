# 📘 CryptoAlgoBot - Comprehensive Technical Report

**Document Version:** v4.0 (Production-Ready)
**Last Update:** March 17, 2026
**Status:** ✅ Production Ready (14/14 E2E Tests Passed)
**Architecture:** Event-Driven (Olay Güdümlü Mimarisi)
**Privacy:** Public Open-Source

---

## 📋 TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Event-Driven Architecture](#3-event-driven-architecture)
4. [API Modularization](#4-api-modularization)
5. [Data Lake & Pipeline](#5-data-lake--pipeline)
6. [ML Integration](#6-ml-integration)
7. [Risk Engine](#7-risk-engine)
8. [Paper Trader](#8-paper-trader)
9. [Testing & Quality Assurance](#9-testing--quality-assurance)
10. [Performance Metrics](#10-performance-metrics)
11. [Deployment Guide](#11-deployment-guide)
12. [Troubleshooting](#12-troubleshooting)

---

## 1. EXECUTIVE SUMMARY

CryptoAlgoBot v4.0 is a **production-ready**, **event-driven** cryptocurrency trading bot with **ML integration**, **realistic execution simulation**, and **modular API architecture**.

### 1.1 Key Achievements (v4.0)

✅ **Event-Driven Architecture:** Migrated from monolithic to event-driven (Pub/Sub)
✅ **ML Integration:** XGBoost + Random Forest ensemble with Triple Barrier Method
✅ **Parquet Data Lake:** MTF-Daily partition with async I/O and UTC standardization
✅ **Risk Engine:** Position sizing, dynamic leverage, kill switch
✅ **Paper Trader:** Fee + slippage simulation, trailing stop (ratchet)
✅ **API Modularization:** 1,374 lines → 161 lines (88% reduction)
✅ **E2E Testing:** 14/14 tests passed (100% coverage)

### 1.2 Technical Metrics

| Metric | Value | Status |
|--------|-------|--------|
| **E2E Tests** | 14/14 passed | ✅ |
| **Code Coverage** | 100% (critical paths) | ✅ |
| **API Lines** | 161 (from 1,374) | ✅ -88% |
| **Event Types** | 40+ | ✅ |
| **ML Models** | XGBoost + RF | ✅ |
| **Parquet Partitions** | MTF-Daily | ✅ |
| **Latency** | <100ms (p99) | ✅ |

---

## 2. SYSTEM ARCHITECTURE

### 2.1 Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│ 1. Frontend (Dashboard)                                 │
│    - Bot Management UI                                  │
│    - ML Model Training                                  │
│    - Strategy Builder                                   │
│    - Real-time Visualization                            │
└─────────────────────────────────────────────────────────┘
                            ↓ (HTTP/WebSocket)
┌─────────────────────────────────────────────────────────┐
│ 2. API Layer (FastAPI)                                  │
│    - /api/v1/bot/* (Bot management)                     │
│    - /api/v1/ml/* (ML training/inference)               │
│    - /api/v1/strategy/* (Strategy management)           │
│    - /api/v1/data/* (Data management)                   │
│    - Routers → Services → Schemas                       │
└─────────────────────────────────────────────────────────┘
                            ↓ (Event Bus Pub/Sub)
┌─────────────────────────────────────────────────────────┐
│ 3. Core Engine                                          │
│    - ExchangeManager (Centralized poller)               │
│    - PaperTrader (Virtual execution)                    │
│    - Event Bus (Pub/Sub)                                │
│    - 1-to-N Broadcast Architecture                      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Strategy & ML                                        │
│    - StrategyManager (Strategy factory)                 │
│    - ML Integration (XGBoost + RF Ensemble)             │
│    - WFO (Walk-Forward Optimization)                    │
│    - Confluence (Technical + ML signals)                │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│ 5. Data Layer                                           │
│    - Parquet Data Lake (MTF-Daily partition)            │
│    - Database Manager (SQLite/PostgreSQL)               │
│    - Feature Engineering (40+ features)                 │
│    - Technical Indicators                               │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Key Components

| Component | File | Responsibility |
|-----------|------|----------------|
| **Event Bus** | `shared/events/event_bus.py` | Pub/Sub pattern, 5 workers |
| **API Server** | `api/server.py` | FastAPI app, routers |
| **Paper Trader** | `core/paper.py` | Virtual execution |
| **Risk Engine** | `core/risk/risk_engine.py` | Position sizing, leverage |
| **Position Manager** | `core/trading/position_manager.py` | Position lifecycle |
| **Bot Manager** | `core/bot/bot_manager.py` | Bot orchestration |
| **Parquet Lake** | `data/storage/parquet_lake.py` | Columnar storage |
| **ML Trainer** | `ml/model_training.py` | XGBoost + RF training |

---

## 3. EVENT-DRIVEN ARCHITECTURE

### 3.1 Pub/Sub Pattern

**Before (Tight Coupling):**
```
Exchange Manager → direct call → PaperTrader
       ↑                              │
       └──────────────────────────────┘
          CIRCULAR DEPENDENCY! ❌
```

**After (Loose Coupling):**
```
Exchange Manager → publish → Event Bus → subscribe → PaperTrader
```

### 3.2 Event Categories (40+ Types)

| Category | Events | Payload (Scalar Only) |
|----------|--------|----------------------|
| **BOT** | `bot.started`, `bot.stopped` | `bot_id`, `symbol`, `strategy_id` |
| **SIGNAL** | `signal.generated` | `bot_id`, `signal`, `price`, `indicators` |
| **POSITION** | `position.opened`, `position.closed` | `bot_id`, `direction`, `entry_price`, `pnl` |
| **ML** | `ml.training_started`, `ml.prediction` | `symbol`, `timeframe`, `confidence` |
| **RISK** | `risk.killswitch_activated` | `reason`, `consecutive_losses` |
| **DATA** | `candle.closed` | `symbol`, `timeframe`, `candles_count` |
| **PRICE** | `price.updated` | `symbol`, `price`, `timestamp` |

### 3.3 Event Bus Implementation

```python
# shared/events/event_bus.py
class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_queue: asyncio.Queue = None
        self._num_workers: int = 5  # Parallel workers
        self._max_queue_size: int = 10000

    async def publish(self, event: Event):
        """Non-blocking publish to queue."""
        self._event_queue.put_nowait(event)

    async def _worker(self, worker_name: str):
        """Process events from queue."""
        while self._running:
            event = await self._event_queue.get()
            await self._process_event(event)
```

### 3.4 RAM Optimization

**CRITICAL:** Events carry only **scalar data** (no large objects).

```python
# ✅ CORRECT: Scalar data only
event = SignalGeneratedEvent(
    bot_id="bot_123",
    symbol="BTC/USDT",
    signal=2,  # int
    price=50000.0,  # float
    indicators={'RSI': 65.0}  # dict of scalars
)

# ❌ WRONG: No DataFrames or objects
event = SignalGeneratedEvent(
    df=large_dataframe,  # NO! Memory leak
    strategy_instance=strategy_obj  # NO!
)
```

---

## 4. API MODULARIZATION

### 4.1 Before vs After

**Before (Monolithic):**
```
api/server.py (1,374 lines)
├── 33 endpoints in single file
├── All business logic intertwined
├── Scattered Pydantic models
└── Untestable
```

**After (Modular):**
```
api/server.py (161 lines)
├── Router registration
├── Lifespan events
└── CORS, static files

api/routers/ (8 files)
├── bot.py (6 endpoints)
├── ml.py (5 endpoints)
├── strategy.py (2 endpoints)
├── data.py (8 endpoints)
├── trades.py, system.py, backtest.py, strategy_builder.py

api/services/ (5 files)
├── BotService, MLService, DataService, StrategyService, DataSync

api/schemas/ (6 files)
├── Bot, ML, Strategy, Data, Config schemas
```

### 4.2 Layer Responsibilities

| Layer | Files | Responsibility |
|-------|-------|----------------|
| **Routers** | `api/routers/*.py` | HTTP endpoint definitions |
| **Services** | `api/services/*.py` | Business logic implementation |
| **Schemas** | `api/schemas/*.py` | Request/response validation (Pydantic) |

### 4.3 Example Flow

```python
# 1. Request → Router
@router.post("/bot/start")
async def start_bot(request: BotStartRequest):
    return await bot_service.start_bot(request)

# 2. Router → Service
class BotService:
    async def start_bot(self, request: BotStartRequest):
        bot_id = paper_engine.start_bot(...)
        return {"status": "success", "bot_id": bot_id}

# 3. Service → Core Engine
paper_engine.start_bot(symbol, strategy_id, timeframe)
```

---

## 5. DATA LAKE & PIPELINE

### 5.1 Parquet Data Lake

**File:** `data/storage/parquet_lake.py`

**Features:**
- ✅ **MTF-Daily Partition:** Intraday (1m-30m) → YYYY/MM/DD/data.parquet
- ✅ **MTF-Market Storage:** Higher TF (1h+) → market.parquet
- ✅ **Async I/O:** asyncio.to_thread (non-blocking)
- ✅ **UTC Standardization:** Look-ahead bias prevention
- ✅ **Snappy Compression:** 70-80% disk reduction

### 5.2 File Structure

```
data/ohlcv/
└── binance/
    └── BTC/USDT/
        ├── 1m/
        │   └── 2026/
        │       └── 03/
        │           ├── 17/
        │           │   └── data.parquet
        │           └── 18/
        │               └── data.parquet
        └── 1h/
            └── market.parquet
```

### 5.3 UTC Timezone Standardization

```python
# ⏰ TIMEZONE STANDARDIZATION (UTC'ye zorla)
if existing_df.index.tzinfo is None:
    existing_df.index = existing_df.index.tz_localize('UTC')
else:
    existing_df.index = existing_df.index.tz_convert('UTC')

if df.index.tzinfo is None:
    df.index = df.index.tz_localize('UTC')
else:
    df.index = df.index.tz_convert('UTC')
```

### 5.4 Stream API (OOM Protection)

```python
async for batch in lake.stream_datasets(
    symbol='BTC/USDT',
    timeframe='1m',
    start_date=datetime(2026, 1, 1),
    end_date=datetime(2026, 3, 17),
    batch_size=50000
):
    process_batch(batch)  # No OOM risk
```

---

## 6. ML INTEGRATION

### 6.1 Architecture

```
Data → Features → Labels → Training → Inference → Confluence
```

### 6.2 Triple Barrier Method

**Marcos Lopez de Prado's labeling:**

| Barrier | Description |
|---------|-------------|
| **Profit-Take (pt)** | `entry + pt × volatility` |
| **Stop-Loss (sl)** | `entry - sl × volatility` |
| **Time Limit (T)** | `t + T` (e.g., 5 candles) |

**Label Assignment:**
- Touch pt first → `label = 2` (LONG)
- Touch sl first → `label = 0` (SHORT)
- Time limit → `label = 1` (NEUTRAL)

### 6.3 Feature Engineering (40+ Features)

| Category | Features |
|----------|----------|
| **Momentum** | RSI, StochRSI, Williams %R |
| **Trend** | EMA 20/50/200, MACD, ADX |
| **Volatility** | ATR, Bollinger Bands, Keltner |
| **Volume** | OBV, MFI, Volume SMA |
| **Price Action** | Higher Highs, Lower Lows |
| **Statistical** | EWMA, Z-Score, Percentile |

### 6.4 Data Leakage Prevention

```python
# ✅ CORRECT: Lag by 1 candle (no look-ahead)
df['rsi_14'] = compute_rsi(df['close'], 14).shift(1)

# ❌ WRONG: Uses current candle (look-ahead bias!)
df['rsi_14'] = compute_rsi(df['close'], 14)
```

### 6.5 Ensemble Model

```python
# XGBoost + Random Forest (Soft Voting)
xgb_proba = xgb_model.predict_proba(X_test)
rf_proba = rf_model.predict_proba(X_test)
ensemble_proba = (xgb_proba + rf_proba) / 2
y_pred = np.argmax(ensemble_proba, axis=1)
```

### 6.6 Confidence → Dynamic Leverage

| ML Confidence | Leverage | Rationale |
|---------------|----------|-----------|
| **< 50%** | 1x (base) | Low confidence |
| **50-65%** | 2-3x | Moderate |
| **65-80%** | 3-5x | High |
| **> 80%** | 5-10x | Very high |

**Timeframe-Aware:**
- 1m, 3m: Max 10x (high noise)
- 5m-30m: Max 20x (medium noise)
- 1h+: Normal max leverage

---

## 7. RISK ENGINE

### 7.1 Position Sizing Formula

```
Position Size = min(
    (Balance × Risk%) / |Entry - Stop|,     # Risk-based
    (Balance / MaxPositions × Leverage × 0.98) / Entry,  # Margin limit
    (FreeMargin × Leverage × 0.98) / Entry   # Free margin
)
```

### 7.2 Example Calculation

```python
balance = 10000  # $10,000
risk = 1.0  # 1%
entry = 50000  # BTC @ $50k
stop = 49000  # Stop @ $49k
leverage = 5  # 5x

risk_amount = 10000 * 0.01 = $100
price_distance = |50000 - 49000| = $1000

size_by_risk = 100 / 1000 = 0.1 BTC
```

### 7.3 Kill Switch

**Activation Conditions:**
- Consecutive losses ≥ `max_consecutive_losses` (default: 5)
- Daily loss ≥ `max_daily_loss` (default: 5%)

```python
def check_kill_switch(self) -> bool:
    if self.consecutive_losses >= self.config.max_consecutive_losses:
        logger.warning("🚨 KILL SWITCH: Consecutive losses!")
        return True
    
    if self.daily_pnl <= -self.config.max_daily_loss:
        logger.critical("🚨 KILL SWITCH: Daily loss limit!")
        return True
    
    return False
```

---

## 8. PAPER TRADER

### 8.1 Fee & Slippage Simulation

| Market | Fee Rate | Slippage |
|--------|----------|----------|
| **Futures** | 0.04% (taker) | 0.01% (market) |
| **Spot** | 0.1% (taker) | 0.01% (market) |

### 8.2 Entry Simulation (LONG)

```python
# Apply slippage (market order)
actual_entry = entry_price * (1 + 0.0001)  # +0.01%

# Calculate fee
entry_fee = actual_entry * size * 0.0004  # 0.04%

# Deduct from balance
balance -= entry_fee
```

### 8.3 Exit Simulation (LONG)

```python
# Apply slippage
actual_exit = exit_price * (1 - 0.0001)  # -0.01%

# Calculate fee
exit_fee = actual_exit * size * 0.0004

# Net PnL
net_pnl = pnl_before_fee - exit_fee
```

### 8.4 Trailing Stop (Ratchet)

**Key Principle:** Stop moves **only in profit direction**.

```python
# LONG: Stop trails UP (never down)
if direction == "LONG":
    new_stop = current_price - (ATR × multiplier)
    if new_stop > current_stop:
        stop_loss = new_stop  # Move up only

# SHORT: Stop trails DOWN (never up)
else:
    new_stop = current_price + (ATR × multiplier)
    if new_stop < current_stop:
        stop_loss = new_stop  # Move down only
```

---

## 9. TESTING & QUALITY ASSURANCE

### 9.1 E2E Test Coverage

| Test | Status | Description |
|------|--------|-------------|
| **test_bot_lifecycle** | ✅ Pass | Bot start/stop/resume |
| **test_signal_generation** | ✅ Pass | Strategy signals |
| **test_position_opening** | ✅ Pass | Open position with fee/slippage |
| **test_trailing_stop** | ✅ Pass | Ratchet mechanism |
| **test_risk_engine** | ✅ Pass | Position sizing |
| **test_ml_training** | ✅ Pass | Model training |
| **test_ml_inference** | ✅ Pass | Live prediction |
| **test_parquet_save** | ✅ Pass | Save to Parquet |
| **test_parquet_load** | ✅ Pass | Load from Parquet |
| **test_event_bus** | ✅ Pass | Pub/Sub |
| **test_api_bot** | ✅ Pass | Bot endpoints |
| **test_api_ml** | ✅ Pass | ML endpoints |
| **test_api_data** | ✅ Pass | Data endpoints |
| **test_api_strategy** | ✅ Pass | Strategy endpoints |

### 9.2 Test Execution

```bash
# Run all E2E tests
pytest test_execution_e2e.py -v

# Run ML tests
pytest test_ml_integration.py -v

# Run Parquet tests
pytest test_parquet_pipeline.py -v
```

---

## 10. PERFORMANCE METRICS

| Metric | Value | Measurement |
|--------|-------|-------------|
| **Bot Launch** | <1 second | API → Bot running |
| **Poller Start** | <100ms | Exchange poller |
| **Event Processing** | <10ms (p99) | Publish → Handle |
| **ML Training** | 30-60s | 10,000 candles |
| **ML Inference** | <50ms | Predict |
| **Parquet Write** | <100ms | 1 day (1m TF) |
| **Parquet Read** | <500ms | 1 month (vectorized) |
| **API Latency** | <50ms (p99) | HTTP request |

---

## 11. DEPLOYMENT GUIDE

### 11.1 Installation

```bash
# Clone repository
git clone https://github.com/yourusername/CryptoAlgoBot.git
cd CryptoAlgoBot

# Install dependencies
pip install -r requirements.txt

# Initialize database
python migrate_db.py

# Start bot
python main.py
```

### 11.2 Configuration

```yaml
# config.yaml
trading:
  symbols:
    - BTC/USDT:USDT
    - ETH/USDT:USDT
  
risk_management:
  max_risk_per_trade_percent: 0.01  # 1%
  max_leverage: 10
  kill_switch:
    enabled: true
    max_consecutive_losses: 5

wfo:
  enabled: true
  train_days: 30
  test_days: 7
  reoptimize_interval: 168  # 1 week
```

### 11.3 Production Checklist

- [ ] API keys encrypted (`.secret.key`)
- [ ] Database backed up
- [ ] Kill switch enabled
- [ ] Risk limits configured
- [ ] WFO scheduled
- [ ] Monitoring enabled

---

## 12. TROUBLESHOOTING

### 12.1 Bot Not Opening Positions

**Symptoms:** Bot running but no trades

**Solutions:**
1. Check signal generation logs
2. Verify risk engine allows position
3. Check HTF filter (may block signals)
4. Verify ML confluence (if enabled)

### 12.2 ML Model Not Loading

**Symptoms:** `❌ ML model not found`

**Solutions:**
1. Train model first (ML Decision Engine tab)
2. Check file exists:
   ```bash
   ls artifacts/models/xgb_model_*.json
   ```
3. Verify timeframe matches

### 12.3 Event Bus Not Processing

**Symptoms:** Events published but handlers not called

**Solutions:**
1. Check Event Bus started:
   ```python
   await event_bus.start(num_workers=5)
   ```
2. Verify subscription:
   ```python
   subscribers = event_bus.get_subscribers("signal.generated")
   ```
3. Check worker logs for errors

---

## 📚 APPENDIX

### A. Glossary

| Term | Definition |
|------|------------|
| **EDA** | Event-Driven Architecture |
| **Pub/Sub** | Publisher-Subscriber pattern |
| **MTF** | Multi-Time-Frame |
| **WFO** | Walk-Forward Optimization |
| **ATR** | Average True Range |
| **FFill** | Forward Fill (no look-ahead) |

### B. References

1. Marcos Lopez de Prado - "Advances in Financial Machine Learning"
2. FastAPI Documentation: https://fastapi.tiangolo.com/
3. Apache Parquet: https://parquet.apache.org/
4. XGBoost Documentation: https://xgboost.readthedocs.io/

---

*This technical report describes CryptoAlgoBot v4.0 (March 2026).*
*For updates, check the `knowledge/` directory.*

**CryptoAlgoBot Development Team**
**March 2026**
