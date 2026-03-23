# 📄 Paper Trader (Virtual Trading Engine)

**Version:** v4.0 (Production-Ready)
**Last Update:** March 2026
**Status:** ✅ Production Ready (Execution E2E Test Passed)
**Category:** Trading Engine / Execution

---

## 🎯 Overview

**Paper Trader** is the production-ready virtual trading engine that simulates real exchange execution with realistic market mechanics:
- Commission (fee) simulation
- Slippage simulation
- Position sizing (risk-based)
- Dynamic trailing stop (asynchronous ratchet)
- Multi-bot management
- Event-driven architecture (Pub/Sub)

**File:** `core/paper.py`

**Key Features:**
- ✅ **Fee Simulation:** 0.04% taker fee on entry/exit
- ✅ **Slippage Simulation:** 0.01% market order slippage
- ✅ **Position Sizing:** Risk-based calculation (Risk Engine)
- ✅ **Trailing Stop:** Asynchronous ratchet (one-directional)
- ✅ **Event-Driven:** Pub/Sub architecture (no circular dependencies)
- ✅ **Multi-Bot:** Concurrent bot execution (asyncio.gather)

---

## 🏗️ Architecture

### **Component Diagram:**

```
┌─────────────────────────────────────────────────────────┐
│                 PaperTrader                             │
├─────────────────────────────────────────────────────────┤
│ - position_manager: PositionManager                     │
│ - risk_engine: RiskEngine                               │
│ - bot_manager: BotManager                               │
│ - signal_validator: SignalValidatorService              │
├─────────────────────────────────────────────────────────┤
│ + start_event_handlers()                                │
│ + on_signal_generated(event)                            │
│ + on_position_opened(event)                             │
│ + on_position_closed(event)                             │
│ + on_live_price_updated(event)  # NEW!                  │
│ + check_and_update_trailing_stop()                      │
└─────────────────────────────────────────────────────────┘
```

### **Event-Driven Flow:**

```
┌──────────────┐
│  Exchange    │
│  Manager     │
└──────┬───────┘
       │ SignalGeneratedEvent
       │ (Publish)
       ▼
┌─────────────────────────────────────────┐
│         EVENT BUS (Pub/Sub)             │
└───────────────┬─────────────────────────┘
                │
                │ (Subscribe)
                ▼
        ┌───────────────┐
        │ PaperTrader   │
        │ (Handler)     │
        └───────┬───────┘
                │
                ├─→ Risk Engine (validate)
                ├─→ Position Manager (open)
                └─→ Event Bus (publish: position.opened)
```

---

## 💰 Fee & Slippage Simulation

### **Fee Structure:**

| Market | Fee Rate | Description |
|--------|----------|-------------|
| **Futures** | 0.04% (0.0004) | Taker fee (market orders) |
| **Spot** | 0.1% (0.001) | Taker fee (market orders) |

### **Slippage Rules:**

| Order Type | Slippage | Description |
|------------|----------|-------------|
| **Market Entry** | +0.01% (LONG) | Entry price × 1.0001 |
| **Market Entry** | -0.01% (SHORT) | Entry price × 0.9999 |
| **Market Exit** | -0.01% (LONG) | Exit price × 0.9999 |
| **Market Exit** | +0.01% (SHORT) | Exit price × 1.0001 |

### **Implementation:**

```python
# core/paper.py
class PaperTrader:
    def __init__(
        self,
        initial_balance=10000.0,
        fee_rate_spot=0.001,      # 0.1%
        fee_rate_futures=0.0004   # 0.04%
    ):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.free_margin = initial_balance
        self.used_margin = 0.0
        
        self.fee_rate_spot = fee_rate_spot
        self.fee_rate_futures = fee_rate_futures
        
        # Slippage constant
        self.SLIPPAGE = 0.0001  # 0.01%
```

### **Entry Simulation:**

```python
def open_position(
    self,
    bot_id: str,
    symbol: str,
    direction: str,
    entry_price: float,
    size: float,
    leverage: float = 1.0,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None
) -> Position:
    """
    Open position with realistic fee and slippage.
    
    Args:
        bot_id: Bot identifier
        symbol: Trading symbol
        direction: LONG or SHORT
        entry_price: Signal price (before slippage)
        size: Position size (coin amount)
        leverage: Leverage
        stop_loss: Stop loss price
        take_profit: Take profit price
        
    Returns:
        Position object
    """
    # Apply slippage (market order simulation)
    if direction == "LONG":
        # LONG: Buy higher (slippage against you)
        actual_entry_price = entry_price * (1 + self.SLIPPAGE)
    else:
        # SHORT: Sell lower (slippage against you)
        actual_entry_price = entry_price * (1 - self.SLIPPAGE)
    
    logger.debug(
        f"📊 Slippage: {entry_price:.4f} → {actual_entry_price:.4f} "
        f"({self.SLIPPAGE:.4%})"
    )
    
    # Calculate position value
    position_value = actual_entry_price * size
    
    # Calculate entry fee
    entry_fee = position_value * self.fee_rate
    
    # Open position (PositionManager)
    position = self.position_manager.open_position(
        bot_id=bot_id,
        symbol=symbol,
        direction=direction,
        entry_price=actual_entry_price,  # Slippage-adjusted
        size=size,
        leverage=leverage,
        stop_loss=stop_loss,
        take_profit=take_profit,
        entry_fee=entry_fee  # Fee tracked
    )
    
    # Deduct fee from balance (immediate)
    self.balance -= entry_fee
    self.free_margin -= entry_fee
    
    logger.info(
        f"✅ Position opened: {symbol} {direction} "
        f"Size: {size:.4f} @ {actual_entry_price:.4f} "
        f"Fee: ${entry_fee:.2f}"
    )
    
    return position
```

### **Exit Simulation:**

```python
async def close_position(
    self,
    bot_id: str,
    exit_price: float,
    reason: str = "CLOSE"
) -> Trade:
    """
    Close position with realistic fee and slippage.
    
    Args:
        bot_id: Bot identifier
        exit_price: Signal price (before slippage)
        reason: Close reason (STOP_LOSS, TAKE_PROFIT, TRAILING, etc.)
        
    Returns:
        Trade object (PnL recorded)
    """
    position = self.position_manager.positions.get(bot_id)
    
    if not position:
        return None
    
    # Apply slippage (market order simulation)
    if position.direction == "LONG":
        # LONG: Sell lower (slippage against you)
        actual_exit_price = exit_price * (1 - self.SLIPPAGE)
    else:
        # SHORT: Buy higher (slippage against you)
        actual_exit_price = exit_price * (1 + self.SLIPPAGE)
    
    logger.debug(
        f"📊 Exit Slippage: {exit_price:.4f} → {actual_exit_price:.4f} "
        f"({self.SLIPPAGE:.4%})"
    )
    
    # Calculate exit fee
    position_value = actual_exit_price * position.size
    exit_fee = position_value * self.fee_rate
    
    # Calculate PnL (before fee)
    pnl_before_fee = self.position_manager.calculate_pnl(
        position=position,
        exit_price=actual_exit_price
    )
    
    # Net PnL (after exit fee)
    net_pnl = pnl_before_fee - exit_fee
    
    # Close position (PositionManager)
    trade = self.position_manager.close_position(
        bot_id=bot_id,
        exit_price=actual_exit_price,  # Slippage-adjusted
        pnl=net_pnl,
        reason=reason
    )
    
    # Update balance (PnL - fee)
    self.balance += net_pnl
    self.free_margin += net_pnl
    
    logger.info(
        f"✅ Position closed: {position.symbol} "
        f"PnL: ${net_pnl:.2f} (Fee: ${exit_fee:.2f}) "
        f"Reason: {reason}"
    )
    
    return trade
```

---

## 🎯 Dynamic Trailing Stop (Asynchronous Ratchet)

### **Ratchet Mechanism:**

**Key Principle:** Trailing stop only moves in **one direction** (profit direction). Never moves against the position.

```python
# core/trading/position_manager.py
def update_trailing_stop(
    self,
    bot_id: str,
    current_price: float,
    atr: float,
    atr_multiplier: float = 1.5
) -> Optional[float]:
    """
    Update trailing stop (asynchronous ratchet).
    
    LONG: Stop loss only moves UP (never down)
    SHORT: Stop loss only moves DOWN (never up)
    
    Args:
        bot_id: Bot identifier
        current_price: Current market price
        atr: ATR value (volatility)
        atr_multiplier: ATR multiplier for stop distance
        
    Returns:
        New trailing stop price (if updated)
    """
    position = self.positions.get(bot_id)
    
    if not position:
        return None
    
    # Calculate new trailing stop
    if position.direction == "LONG":
        # LONG: Trail below price (ATR-based)
        new_trailing_stop = current_price - (atr * atr_multiplier)
        
        # Ratchet: Only move UP (higher stop)
        if position.stop_loss and new_trailing_stop <= position.stop_loss:
            # Don't move stop down (ratchet principle)
            return None
        
        # Update stop loss
        position.stop_loss = new_trailing_stop
        logger.debug(
            f"🔼 [TRAILING] {position.symbol} LONG: "
            f"Stop updated to {new_trailing_stop:.4f}"
        )
        
    else:  # SHORT
        # SHORT: Trail above price (ATR-based)
        new_trailing_stop = current_price + (atr * atr_multiplier)
        
        # Ratchet: Only move DOWN (lower stop)
        if position.stop_loss and new_trailing_stop >= position.stop_loss:
            # Don't move stop up (ratchet principle)
            return None
        
        # Update stop loss
        position.stop_loss = new_trailing_stop
        logger.debug(
            f"🔽 [TRAILING] {position.symbol} SHORT: "
            f"Stop updated to {new_trailing_stop:.4f}"
        )
    
    return position.stop_loss
```

### **Asynchronous Update Loop:**

```python
# core/paper.py
async def check_and_update_trailing_stop(self):
    """
    Check and update trailing stops for all open positions.
    Runs asynchronously (non-blocking).
    """
    if not self.open_positions:
        return
    
    logger.debug(f"🔍 Checking trailing stops for {len(self.open_positions)} positions")
    
    for position in self.open_positions:
        bot_id = position['bot_id']
        symbol = position['symbol']
        
        # Get latest candle (for ATR)
        df = await self.get_latest_candles(symbol, timeframe='1m', limit=50)
        
        if df.empty:
            continue
        
        # Calculate ATR
        atr = self.calculate_atr(df, period=14)
        current_price = df['close'].iloc[-1]
        
        # Update trailing stop (ratchet)
        new_stop = self.position_manager.update_trailing_stop(
            bot_id=bot_id,
            current_price=current_price,
            atr=atr,
            atr_multiplier=1.5
        )
        
        if new_stop:
            # Trailing stop updated
            logger.info(
                f"🔔 [TRAILING UPDATE] {symbol}: "
                f"New stop: {new_stop:.4f}"
            )
```

---

## 🤖 Multi-Bot Management

### **Concurrent Execution:**

```python
# core/paper.py
async def process_all_bots(self, df_dict: Dict[str, pd.DataFrame]):
    """
    Process all active bots concurrently (asyncio.gather).
    
    Args:
        df_dict: {symbol: DataFrame} dict
    """
    tasks = []
    
    for bot_id, bot_metadata in self.active_bots.items():
        symbol = bot_metadata['symbol']
        timeframe = bot_metadata['timeframe']
        
        # Get DataFrame for symbol
        df = df_dict.get(symbol)
        
        if df is None or df.empty:
            continue
        
        # Create bot processing task
        task = asyncio.create_task(
            self.process_single_bot(bot_id, df, symbol, timeframe)
        )
        tasks.append(task)
    
    # Execute all bots concurrently
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions (isolation)
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                bot_id = list(self.active_bots.keys())[i]
                logger.error(f"❌ Bot {bot_id} error: {result}")
```

### **Bot Isolation:**

```python
async def process_single_bot(
    self,
    bot_id: str,
    df: pd.DataFrame,
    symbol: str,
    timeframe: str
) -> Optional[Signal]:
    """
    Process single bot (isolated execution).
    
    Args:
        bot_id: Bot identifier
        df: Candle DataFrame
        symbol: Trading symbol
        timeframe: Timeframe
        
    Returns:
        Signal (if generated)
    """
    try:
        # Get strategy instance
        strategy = self.strategies.get(symbol)
        
        if not strategy:
            logger.warning(f"⚠️ Strategy not found for {symbol}")
            return None
        
        # Generate signal
        signal = strategy.generate_signal(df.iloc[-1])
        
        # Get indicators
        indicators = {
            'RSI_14': df['rsi_14'].iloc[-1],
            'EMA_20': df['ema_20'].iloc[-1],
            'ATR_14': df['atr_14'].iloc[-1]
        }
        
        # Get HTF trends (multi-timeframe filter)
        htf_trends = self.get_htf_trends(symbol)
        
        # Publish signal event
        event = SignalGeneratedEvent(
            bot_id=bot_id,
            symbol=symbol,
            signal=signal,
            price=df['close'].iloc[-1],
            timeframe=timeframe,
            indicators=indicators,
            metadata={
                'htf_trends': htf_trends,
                'market_regime': self.market_regime
            }
        ).to_event()
        
        await event_bus.publish(event)
        
        return signal
        
    except Exception as e:
        logger.error(f"❌ Bot {bot_id} error: {e}")
        # Error isolated (other bots continue)
        return None
```

---

## 📊 Position Lifecycle

### **State Machine:**

```
┌─────────────┐
│   CLOSED    │
└──────┬──────┘
       │
       │ open_position()
       ▼
┌─────────────┐
│    OPEN     │◄────────────────────┐
└──────┬──────┘                     │
       │                            │
       │ update_trailing_stop()     │
       ├────────────────────────────┘
       │
       │ close_position()
       ▼
┌─────────────┐
│   CLOSED    │
└─────────────┘
```

### **Position States:**

| State | Description | Transitions |
|-------|-------------|-------------|
| **OPEN** | Position active | → CLOSED (exit) |
| **CLOSING** | Exit in progress | → CLOSED (completed) |
| **CLOSED** | Position closed | (terminal state) |

---

## 🧪 Testing

### **E2E Test Coverage:**

```python
# test_execution_e2e.py
import pytest
from core.paper import PaperTrader

@pytest.fixture
def paper_trader():
    return PaperTrader(initial_balance=10000)

@pytest.mark.asyncio
async def test_fee_slippage_simulation(paper_trader):
    """Test fee and slippage calculation."""
    # Open position
    position = paper_trader.open_position(
        bot_id="test_bot",
        symbol="BTC/USDT",
        direction="LONG",
        entry_price=50000,
        size=0.1,
        leverage=1
    )
    
    # Verify slippage (0.01%)
    expected_entry = 50000 * 1.0001  # LONG: slippage up
    assert position.entry_price == expected_entry
    
    # Verify fee (0.04%)
    expected_fee = expected_entry * 0.1 * 0.0004
    assert abs(paper_trader.balance - (10000 - expected_fee)) < 0.01

@pytest.mark.asyncio
async def test_trailing_stop_ratchet(paper_trader):
    """Test trailing stop ratchet (one-directional)."""
    # Open LONG position
    position = paper_trader.open_position(
        bot_id="test_bot",
        symbol="BTC/USDT",
        direction="LONG",
        entry_price=50000,
        size=0.1,
        stop_loss=49000  # Initial stop
    )
    
    # Price moves up → stop should trail up
    paper_trader.update_trailing_stop(
        bot_id="test_bot",
        current_price=51000,
        atr=500,
        atr_multiplier=1.5
    )
    
    # New stop: 51000 - (500 * 1.5) = 50250
    assert position.stop_loss == 50250  # Moved up
    
    # Price moves down → stop should NOT move down
    paper_trader.update_trailing_stop(
        bot_id="test_bot",
        current_price=50500,
        atr=500,
        atr_multiplier=1.5
    )
    
    # Stop should remain at 50250 (ratchet)
    assert position.stop_loss == 50250  # Not moved down
```

---

## 🚨 Troubleshooting

### **Issue 1: Position Not Closing**

**Symptom:** Position remains open after stop loss hit

**Solution:**
```python
# Check stop loss logic
if direction == "LONG":
    if current_price <= stop_loss:
        # Should close
        await close_position(bot_id, stop_loss, "STOP LOSS")
```

---

### **Issue 2: Trailing Stop Not Updating**

**Symptom:** Trailing stop remains static

**Solution:**
```python
# Ensure ratchet logic allows update
if position.direction == "LONG":
    # LONG: Stop must move UP
    if new_stop > position.stop_loss:
        position.stop_loss = new_stop
```

---

### **Issue 3: Fee Calculation Incorrect**

**Symptom:** Balance doesn't match expected fee deduction

**Solution:**
```python
# Verify fee rate
fee_rate = 0.0004  # Futures (0.04%)
# or
fee_rate = 0.001   # Spot (0.1%)

# Calculate fee
fee = position_value * fee_rate
```

---

## 📚 Related Documentation

- **Risk Engine:** `features/risk_engine.md`
- **Position Manager:** `features/position_manager.md`
- **Bot Manager:** `features/bot_manager.md`
- **Event-Driven Architecture:** `architecture/event_driven_architecture.md`

---

*This document describes Paper Trader v4.0 (March 2026).*
*For updates, check `core/paper.py` and `core/trading/position_manager.py`.*
