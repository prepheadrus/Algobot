# 🧠 ML Integration (XGBoost + Ensemble)

**Version:** v4.0 (Production-Ready)
**Last Update:** March 2026
**Status:** ✅ Production Ready (ML Integration E2E Test Passed)
**Category:** Features / Machine Learning

---

## 🎯 Overview

**ML Integration** implements Marcos Lopez de Prado's Triple Barrier Method for labeling financial time series data, combined with XGBoost + Random Forest ensemble for directional prediction (LONG/SHORT/NEUTRAL).

**Key Files:**
- `ml/model_training.py` - Model training and ensemble
- `ml/data_prep.py` - Data preparation and feature engineering
- `ml/inference.py` - Live prediction and confidence scoring
- `ml/model_drift.py` - Model drift detection
- `api/services/ml_service.py` - ML business logic
- `api/routers/ml.py` - ML endpoints

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│  1. DATA PREPARATION (ml/data_prep.py)                  │
│     - Parquet Lake → DataFrame                          │
│     - Feature Engineering (40+ features)                │
│     - Fractional Differentiation (memory preservation)  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  2. LABELING (Triple Barrier Method)                    │
│     - Profit Take Barrier (pt)                          │
│     - Stop Loss Barrier (sl)                            │
│     - Time Limit Barrier (T)                            │
│     - Label: 0=SHORT, 1=NEUTRAL, 2=LONG                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  3. TRAINING (ml/model_training.py)                     │
│     - XGBoost Classifier (multi:softprob)               │
│     - Random Forest Classifier (balanced)               │
│     - Ensemble: Soft Voting (avg probability)           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  4. INFERENCE (ml/inference.py)                         │
│     - Load model artifacts                              │
│     - Feature computation (live)                        │
│     - Predict: direction + confidence                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  5. CONFLUENCE (strategy/confluence.py)                 │
│     - ML Signal (direction + confidence)                │
│     - Technical Indicators (RSI, EMA, ATR)              │
│     - HTF Filter (Multi-Time-Frame)                     │
│     - Final Signal: Weighted Consensus                  │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Feature Engineering

### **Feature Categories (40+ Features):**

| Category | Features | Description |
|----------|----------|-------------|
| **Momentum** | RSI, StochRSI, Williams %R | Overbought/oversold conditions |
| **Trend** | EMA 20/50/200, MACD, ADX | Trend direction and strength |
| **Volatility** | ATR, Bollinger Bands, Keltner | Price volatility measurement |
| **Volume** | OBV, MFI, Volume SMA | Volume-based indicators |
| **Price Action** | Higher Highs, Lower Lows | Candlestick patterns |
| **Statistical** | EWMA, Z-Score, Percentile | Statistical transformations |

### **Feature Engineering Pipeline:**

```python
# ml/data_prep.py
import pandas as pd
import numpy as np

def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all features for ML model.
    
    Args:
        df: DataFrame with OHLCV columns
        
    Returns:
        DataFrame with all features
    """
    # Prevent data leakage: Use only past information
    # All indicators must be lagged by 1 candle
    
    # 1. Momentum Features
    df['rsi_14'] = compute_rsi(df['close'], 14).shift(1)
    df['stoch_rsi'] = compute_stoch_rsi(df['close'], 14).shift(1)
    
    # 2. Trend Features
    df['ema_20'] = df['close'].ewm(span=20).mean().shift(1)
    df['ema_50'] = df['close'].ewm(span=50).mean().shift(1)
    df['macd'] = compute_macd(df['close']).shift(1)
    
    # 3. Volatility Features
    df['atr_14'] = compute_atr(df).shift(1)
    df['bb_upper'], df['bb_lower'] = compute_bollinger_bands(df['close'])
    df['bb_upper'] = df['bb_upper'].shift(1)
    df['bb_lower'] = df['bb_lower'].shift(1)
    
    # 4. Volume Features
    df['obv'] = compute_obv(df).shift(1)
    df['volume_sma'] = df['volume'].rolling(20).mean().shift(1)
    
    # 5. Price Features
    df['high_low_range'] = (df['high'] - df['low']) / df['close']
    df['close_open_range'] = (df['close'] - df['open']) / df['open']
    
    # Drop NaN rows (from lagging)
    df = df.dropna()
    
    return df
```

### **Data Leakage Prevention (FFill Logic):**

**CRITICAL:** To prevent look-ahead bias, all features must use only **past** information.

```python
# ✅ CORRECT: Lag by 1 candle (use previous candle's close)
df['rsi_14'] = compute_rsi(df['close'], 14).shift(1)

# ❌ WRONG: Uses current candle's close (look-ahead bias!)
df['rsi_14'] = compute_rsi(df['close'], 14)

# ✅ CORRECT: Forward-fill for missing values (no future info)
df = df.ffill()

# ❌ WRONG: Backward-fill (uses future info!)
df = df.bfill()
```

**Forward-Fill (FFill) Rationale:**
- Uses only **known** past values
- No information from future candles
- Preserves temporal causality

---

## 🎯 Triple Barrier Method (Labeling)

### **Mathematical Foundation:**

The Triple Barrier Method labels each data point based on which barrier the price touches first:

**Three Barriers:**
1. **Profit-Take Barrier (pt):** Upper barrier at `entry_price + pt × volatility`
2. **Stop-Loss Barrier (sl):** Lower barrier at `entry_price - sl × volatility`
3. **Time Limit Barrier (T):** Horizontal barrier at `t + T` (e.g., T = 5 candles)

**Label Assignment:**
```
IF price touches pt barrier first:    label = 2 (LONG)
ELSE IF price touches sl barrier first: label = 0 (SHORT)
ELSE IF time limit reached:           label = 1 (NEUTRAL)
```

### **Implementation:**

```python
# ml/data_prep.py
def get_triple_barrier_labels(
    prices: pd.Series,
    events: pd.DataFrame,
    pt_sl: list,
    out: pd.Series
) -> pd.DataFrame:
    """
    Marcos Lopez de Prado's Triple Barrier Method.
    
    Args:
        prices: Price series (close prices)
        events: DataFrame with event timestamps (t1, time limit)
        pt_sl: [profit_take, stop_loss] multipliers (e.g., [1.0, 1.0])
        out: Target return/volatility series (barrier width)
        
    Returns:
        DataFrame with labels (0=SHORT, 1=NEUTRAL, 2=LONG)
    """
    events_out = events.copy(deep=True)
    
    # Compute barrier widths
    if pt_sl[0] > 0:
        pt = pt_sl[0] * out  # Profit-take barrier
    else:
        pt = pd.Series(index=events.index)  # NaN
    
    if pt_sl[1] > 0:
        sl = -pt_sl[1] * out  # Stop-loss barrier
    else:
        sl = pd.Series(index=events.index)  # NaN
    
    labels = pd.DataFrame(
        index=events.index,
        columns=['take_profit', 'stop_loss', 'time_limit', 'label']
    )
    
    # For each event, simulate price path and determine which barrier is touched first
    for t0, t1 in events['t1'].items():
        # Get price path from t0 to t1
        path = prices.loc[t0:t1]
        
        # Compute cumulative returns
        cumret = path.pct_change().cumsum()
        
        # Check barriers
        if (cumret >= pt.loc[t0]).any():
            # Profit-take touched first
            labels.loc[t0, 'label'] = 2  # LONG
        elif (cumret <= sl.loc[t0]).any():
            # Stop-loss touched first
            labels.loc[t0, 'label'] = 0  # SHORT
        else:
            # Time limit reached
            labels.loc[t0, 'label'] = 1  # NEUTRAL
    
    return labels
```

### **ATR-Based Triple Barrier:**

```python
# strategy/confluence.py
def compute_barrier_widths(df: pd.DataFrame, atr_multiplier: float = 1.5):
    """
    Compute barrier widths using ATR (volatility-adjusted).
    
    Args:
        df: DataFrame with ATR column
        atr_multiplier: ATR multiplier for barrier width
        
    Returns:
        pt, sl series (barrier widths)
    """
    # ATR-based volatility estimate
    volatility = df['atr_14']
    
    # Profit-take and stop-loss barriers
    pt = atr_multiplier * volatility
    sl = atr_multiplier * volatility
    
    return pt, sl
```

---

## 🎓 Model Training

### **Ensemble Architecture:**

```python
# ml/model_training.py
class ModelTrainer:
    def __init__(self):
        # XGBoost Classifier
        self.xgb_model = xgb.XGBClassifier(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=3,
            gamma=0.1,
            reg_alpha=0.1,
            reg_lambda=1.0,
            objective='multi:softprob',
            num_class=3,  # LONG, NEUTRAL, SHORT
            use_label_encoder=False
        )
        
        # Random Forest Classifier
        self.rf_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=5,
            class_weight='balanced'  # Handle class imbalance
        )
```

### **Soft Voting Ensemble:**

```python
def predict_ensemble(self, X_test: pd.DataFrame) -> np.ndarray:
    """
    Ensemble prediction using soft voting.
    
    Args:
        X_test: Test features
        
    Returns:
        Predicted labels
    """
    # Get probability estimates from both models
    xgb_proba = self.xgb_model.predict_proba(X_test)
    rf_proba = self.rf_model.predict_proba(X_test)
    
    # Soft voting: Average probabilities
    ensemble_proba = (xgb_proba + rf_proba) / 2
    
    # Predict class with highest probability
    y_pred = np.argmax(ensemble_proba, axis=1)
    
    return y_pred
```

### **Training Metrics:**

| Metric | Description | Target |
|--------|-------------|--------|
| **Accuracy** | Overall correctness | > 0.55 |
| **Precision (Macro)** | TP / (TP + FP) | > 0.50 |
| **Recall (Macro)** | TP / (TP + FN) | > 0.50 |
| **F1-Score (Macro)** | Harmonic mean | > 0.50 |
| **XGBoost Accuracy** | Individual XGB performance | > 0.50 |
| **RF Accuracy** | Individual RF performance | > 0.50 |
| **Ensemble Accuracy** | Combined performance | > 0.55 |

---

## 🔮 Inference (Live Prediction)

### **Prediction Pipeline:**

```python
# ml/inference.py
class MLInference:
    def __init__(self, symbol: str, timeframe: str):
        self.symbol = symbol
        self.timeframe = timeframe
        self.model_path = get_model_paths(symbol, timeframe)
        self.is_loaded = False
        
    def load_model(self):
        """Load trained model from artifacts."""
        self.xgb_model = xgb.Booster()
        self.xgb_model.load_model(self.model_path['xgboost_path'])
        
        with open(self.model_path['rf_path'], 'rb') as f:
            self.rf_model = joblib.load(f)
        
        self.is_loaded = True
    
    def predict(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Predict direction and confidence.
        
        Args:
            df: DataFrame with latest features
            
        Returns:
            Dict with prediction and confidence
        """
        # Compute features (ensure no look-ahead bias)
        X = self._compute_features(df)
        
        # Get probabilities from both models
        xgb_proba = self.xgb_model.predict_proba(X)
        rf_proba = self.rf_model.predict_proba(X)
        
        # Ensemble: Average probabilities
        ensemble_proba = (xgb_proba + rf_proba) / 2
        
        # Predicted class
        predicted_class = np.argmax(ensemble_proba[0])
        
        # Confidence score (probability of predicted class)
        confidence = ensemble_proba[0][predicted_class]
        
        # Map to direction
        class_mapping = {0: 'SHORT', 1: 'NEUTRAL', 2: 'LONG'}
        direction = class_mapping[predicted_class]
        
        return {
            'direction': direction,
            'confidence': confidence,
            'probabilities': {
                'SHORT': ensemble_proba[0][0],
                'NEUTRAL': ensemble_proba[0][1],
                'LONG': ensemble_proba[0][2]
            }
        }
```

### **Confidence Score → Dynamic Leverage:**

```python
# core/risk/risk_engine.py
def calculate_dynamic_leverage(
    self,
    confidence_score: float,
    timeframe: str = "1h"
) -> float:
    """
    Calculate leverage based on ML confidence.
    
    Args:
        confidence_score: ML confidence (0.0 - 1.0)
        timeframe: Trading timeframe
        
    Returns:
        Leverage (1x - 10x)
    """
    # Timeframe-aware leverage limits
    if timeframe.lower() in ["1m", "3m"]:
        max_leverage = 10  # High noise, limit leverage
    elif timeframe.lower() in ["5m", "15m"]:
        max_leverage = 20  # Medium noise
    else:
        max_leverage = self.config.max_leverage
    
    # Confidence-based leverage
    if confidence_score < 0.50:
        return 1.0  # Base leverage (low confidence)
    
    # Power curve: Leverage increases faster with confidence
    raw_ratio = (confidence_score - 0.50) / 0.50
    boosted_ratio = 0.05 + (0.95 * (raw_ratio ** 0.7))
    
    calculated = 1.0 + (boosted_ratio * (max_leverage - 1.0))
    final_leverage = int(round(min(max_leverage, max(1.0, calculated))))
    
    return float(final_leverage)
```

---

## 🔗 Confluence (Strategy + ML)

### **Confluence Mechanism:**

```python
# strategy/confluence.py
class StrategyConfluence:
    def __init__(self):
        self.ml_inference = None
        
    def generate_signal(
        self,
        df: pd.DataFrame,
        ml_prediction: Optional[Dict] = None
    ) -> int:
        """
        Generate final signal using confluence.
        
        Args:
            df: DataFrame with latest candles
            ml_prediction: ML prediction (direction, confidence)
            
        Returns:
            Signal: 0=SHORT, 1=HOLD, 2=LONG
        """
        signals = []
        weights = []
        
        # 1. Technical Indicators (RSI, EMA, MACD)
        tech_signal = self._technical_analysis(df)
        signals.append(tech_signal)
        weights.append(0.4)  # 40% weight
        
        # 2. ML Prediction (if available)
        if ml_prediction and ml_prediction['direction'] != 'NEUTRAL':
            ml_signal = 2 if ml_prediction['direction'] == 'LONG' else 0
            ml_weight = ml_prediction['confidence'] * 0.6  # Up to 60% weight
            signals.append(ml_signal)
            weights.append(ml_weight)
        
        # 3. HTF Filter (Multi-Time-Frame)
        htf_signal = self._htf_filter(df)
        if htf_signal != 'NEUTRAL':
            signals.append(2 if htf_signal == 'BULL' else 0)
            weights.append(0.3)  # 30% weight
        
        # Weighted consensus
        if not signals:
            return 1  # HOLD
        
        weighted_signal = sum(s * w for s, w in zip(signals, weights))
        total_weight = sum(weights)
        
        if weighted_signal / total_weight >= 1.5:
            return 2  # LONG
        elif weighted_signal / total_weight <= 0.5:
            return 0  # SHORT
        else:
            return 1  # HOLD
```

---

## 📁 File Structure

```
ml/
├── __init__.py
├── data_prep.py          # Feature engineering, labeling
├── model_training.py     # XGBoost + RF training
├── model_drift.py        # Drift detection
├── inference.py          # Live prediction
└── model_registry.py     # Model versioning

api/
├── routers/
│   └── ml.py            # ML endpoints (/api/v1/ml/*)
└── services/
    └── ml_service.py    # ML business logic

artifacts/
└── models/
    ├── xgb_model_btcusdtusdt_1m.json
    ├── xgb_model_btcusdtusdt_1m_rf.joblib
    └── xgb_model_btcusdtusdt_1m_metadata.json
```

---

## 🧪 Usage Examples

### **1. Train ML Model:**

```python
from ml.model_training import ModelTrainer
from ml.data_prep import compute_features, get_triple_barrier_labels

# 1. Load data
df = load_ohlcv('BTC/USDT', '1h', limit=10000)

# 2. Compute features
df = compute_features(df)

# 3. Label with Triple Barrier
events = pd.DataFrame({'t1': df.index})
out = df['close'].pct_change(5).rolling(100).std()
labels = get_triple_barrier_labels(
    prices=df['close'],
    events=events,
    pt_sl=[1.0, 1.0],
    out=out
)

# 4. Split data
X = df.dropna()
y = labels['label'].reindex(X.index).dropna()

# 5. Train model
trainer = ModelTrainer()
trainer.train(X, y, X_test, y_test)

# 6. Save model
trainer.save('artifacts/models/xgb_model_btcusdtusdt_1h.json')
```

---

### **2. Live Prediction:**

```python
from ml.inference import MLInference

# 1. Load model
inference = MLInference('BTC/USDT', '1h')
inference.load_model()

# 2. Get latest data
df = get_latest_ohlcv('BTC/USDT', '1h', limit=100)

# 3. Predict
prediction = inference.predict(df)

print(f"Direction: {prediction['direction']}")
print(f"Confidence: {prediction['confidence']:.2%}")
```

---

## 🚨 Troubleshooting

### **Issue 1: Data Leakage**

**Symptom:** Model performs well in backtest but poorly in live trading

**Solution:**
```python
# ✅ CORRECT: Lag all features by 1 candle
df['rsi'] = compute_rsi(df['close'], 14).shift(1)

# ❌ WRONG: Uses current candle (look-ahead bias)
df['rsi'] = compute_rsi(df['close'], 14)
```

---

### **Issue 2: Class Imbalance**

**Symptom:** Model predicts only NEUTRAL (class 1)

**Solution:**
```python
# Use class_weight='balanced' in Random Forest
rf_model = RandomForestClassifier(class_weight='balanced')

# Or use SMOTE for oversampling
from imblearn.over_sampling import SMOTE
smote = SMOTE()
X_resampled, y_resampled = smote.fit_resample(X, y)
```

---

### **Issue 3: Model Drift**

**Symptom:** Model accuracy decreases over time

**Solution:**
```python
# Monitor drift with PSI (Population Stability Index)
from ml.model_drift import compute_psi

psi = compute_psi(train_distribution, live_distribution)

if psi > 0.2:
    # Significant drift detected - retrain model
    retrain_model()
```

---

## 📚 Related Documentation

- **Parquet Data Lake:** `features/parquet_data_lake.md`
- **Risk Engine:** `features/risk_engine.md`
- **Strategy Confluence:** `strategies/confluence.md`
- **Walk-Forward Optimization:** `features/walk_forward_optimization.md`

---

*This document describes ML Integration v4.0 (March 2026).*
*For updates, check `ml/` directory and `api/services/ml_service.py`.*
