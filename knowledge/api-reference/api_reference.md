# 📡 API Reference

**Version:** v4.1.0  
**Status:** ✅ Production Ready  
**Category:** API / Reference  
**Last Updated:** March 2026

---

## 📋 Overview

API Reference, CryptoAlgoBot'un tüm REST API endpoint'lerinin detaylı dokümantasyonudur.

**Base URL:**
```
http://localhost:3000/api/v1
```

**Interactive Docs:**
```
http://localhost:3000/docs  # Swagger UI
http://localhost:3000/redoc # ReDoc
```

---

## 🔑 Authentication

Currently, no authentication required for local deployment.

**Future:**
```yaml
Authorization: Bearer <your_api_token>
```

---

## 📊 Response Format

**Success:**
```json
{
  "status": "success",
  "message": "Operation completed",
  "data": {...}
}
```

**Error:**
```json
{
  "status": "error",
  "message": "Error description",
  "code": "ERROR_CODE"
}
```

---

## 🤖 Bot Management

### **GET /bot/bots/list**

List all active bots.

**Response:**
```json
{
  "status": "success",
  "bots": [
    {
      "bot_id": "BTC/USDT_trend_master_1m_1",
      "symbol": "BTC/USDT",
      "strategy_id": "trend_master",
      "timeframe": "1m",
      "status": "running",
      "pnl": 123.45,
      "trades": 5
    }
  ]
}
```

---

### **POST /bot/start**

Start a new bot.

**Request:**
```json
{
  "symbol": "BTC/USDT",
  "strategy_id": "trend_master",
  "timeframe": "1m",
  "market_type": "swap",
  "leverage": 5
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Bot started",
  "bot_id": "BTC/USDT_trend_master_1m_1"
}
```

**cURL:**
```bash
curl -X POST http://localhost:3000/api/v1/bot/start \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USDT",
    "strategy_id": "trend_master",
    "timeframe": "1m"
  }'
```

---

### **POST /bot/stop**

Stop a running bot.

**Request:**
```json
{
  "bot_id": "BTC/USDT_trend_master_1m_1",
  "action": "stop"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Bot stopped"
}
```

---

### **POST /bot/resume**

Resume a stopped bot.

**Request:**
```json
{
  "bot_id": "BTC/USDT_trend_master_1m_1",
  "action": "resume"
}
```

---

### **POST /bot/remove**

Remove a bot completely.

**Request:**
```json
{
  "bot_id": "BTC/USDT_trend_master_1m_1"
}
```

---

## 🧠 Machine Learning

### **GET /ml/models**

List all trained ML models.

**Response:**
```json
{
  "status": "success",
  "models": [
    {
      "symbol": "BTC/USDT",
      "timeframe": "1h",
      "accuracy": 0.85,
      "trained_at": "2026-03-22T10:30:00Z"
    }
  ]
}
```

---

### **POST /ml/train**

Train a new ML model.

**Request:**
```json
{
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "candles": 10000,
  "tp_multiplier": 2.0,
  "sl_multiplier": 2.0
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Training started",
  "task_id": "train_12345"
}
```

**cURL:**
```bash
curl -X POST http://localhost:3000/api/v1/ml/train \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTC/USDT",
    "timeframe": "1h",
    "candles": 10000
  }'
```

---

### **GET /ml/training-history**

Get ML training history.

**Response:**
```json
{
  "status": "success",
  "history": [
    {
      "symbol": "BTC/USDT",
      "timeframe": "1h",
      "accuracy": 0.85,
      "trained_at": "2026-03-22T10:30:00Z"
    }
  ]
}
```

---

### **DELETE /ml/model**

Delete a trained model.

**Query Parameters:**
- `symbol` (required)
- `timeframe` (required)

**Response:**
```json
{
  "status": "success",
  "message": "Model deleted"
}
```

---

## 📈 Strategy

### **GET /strategies**

List all available strategies.

**Response:**
```json
{
  "status": "success",
  "strategies": [
    {
      "id": "trend_master",
      "name": "TrendMaster Pro",
      "description": "Trend following strategy",
      "timeframe": "1m",
      "type": "builtin"
    }
  ]
}
```

---

### **GET /strategy-report**

Get strategy performance report.

**Response:**
```json
{
  "status": "success",
  "report": {
    "total_trades": 150,
    "win_rate": 0.65,
    "profit_factor": 1.8,
    "sharpe_ratio": 1.5
  }
}
```

---

## 💾 Data Management

### **GET /data/inventory**

Get data inventory.

**Response:**
```json
{
  "status": "success",
  "inventory": [
    {
      "symbol": "BTC/USDT",
      "timeframe": "1m",
      "count": 50000,
      "min_timestamp": "2026-01-01T00:00:00Z",
      "max_timestamp": "2026-03-22T15:00:00Z"
    }
  ]
}
```

---

### **GET /data/stats**

Get data statistics.

**Response:**
```json
{
  "status": "success",
  "stats": {
    "total_candles": 500000,
    "total_symbols": 10,
    "total_size_mb": 1234.56
  }
}
```

---

### **GET /data/symbols-with-data**

List symbols with available data.

**Response:**
```json
{
  "status": "success",
  "symbols": [
    "BTC/USDT",
    "ETH/USDT",
    "BNB/USDT"
  ]
}
```

---

### **POST /data/download-history**

Start downloading historical data.

**Request:**
```json
{
  "symbol": "BTC/USDT",
  "timeframe": "1m",
  "start_date": "2026-01-01"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Download started"
}
```

---

### **GET /data/all-download-tasks**

List all download tasks.

**Response:**
```json
{
  "status": "success",
  "tasks": [
    {
      "symbol": "BTC/USDT",
      "timeframe": "1m",
      "status": "downloading",
      "progress": 0.75
    }
  ]
}
```

---

### **POST /data/stop-download**

Stop a download task.

**Request:**
```json
{
  "symbol": "BTC/USDT"
}
```

---

### **DELETE /data/delete-klines**

Delete symbol data.

**Request:**
```json
{
  "symbol": "BTC/USDT",
  "market_type": "future"
}
```

---

## 📜 Trades

### **GET /trades/history**

Get trade history.

**Query Parameters:**
- `symbol` (optional): Filter by symbol
- `limit` (optional, default: 100): Max trades to return

**Response:**
```json
{
  "status": "success",
  "count": 2,
  "trades": [
    {
      "id": "trade_12345",
      "symbol": "BTC/USDT",
      "direction": "SHORT",
      "entry_price": 68500.00,
      "exit_price": 68200.00,
      "size": 0.1,
      "leverage": 5,
      "pnl_usd": 150.00,
      "pnl_percent": 2.19,
      "reason": "TAKE_PROFIT",
      "closed_at": "2026-03-22T15:30:00Z"
    }
  ]
}
```

**cURL:**
```bash
curl http://localhost:3000/api/v1/trades/history?limit=10
```

---

### **DELETE /trades/clear**

Clear all trade history.

**Response:**
```json
{
  "status": "success",
  "message": "Trade history cleared"
}
```

---

## ⚙️ Configuration

### **GET /config/bot**

Get bot configuration.

**Response:**
```json
{
  "status": "success",
  "config": {
    "environment": "development",
    "exchange": "binance",
    "log_level": "INFO"
  }
}
```

---

### **POST /config/bot**

Update bot configuration.

**Request:**
```json
{
  "environment": "production",
  "exchange": "binance",
  "log_level": "WARNING"
}
```

---

### **GET /config/risk**

Get risk configuration.

**Response:**
```json
{
  "status": "success",
  "config": {
    "max_risk_per_trade_percent": 1.5,
    "max_leverage": 10,
    "max_open_positions": 10,
    "max_consecutive_losses": 10,
    "kill_switch_enabled": false
  }
}
```

---

### **POST /config/risk**

Update risk configuration.

**Request:**
```json
{
  "max_risk_per_trade_percent": 1.0,
  "max_leverage": 5,
  "max_open_positions": 5,
  "max_consecutive_losses": 5,
  "kill_switch_enabled": true
}
```

---

### **GET /config/advanced**

Get advanced configuration.

**Response:**
```json
{
  "status": "success",
  "config": {
    "wfo": {
      "enabled": true,
      "train_days": 90,
      "test_days": 30
    },
    "ml": {
      "enabled": true,
      "confidence_threshold": 0.5
    },
    "htf": {
      "enabled": false
    },
    "kalman": {
      "enabled": true,
      "q": 0.001,
      "r": 0.1
    }
  }
}
```

---

### **POST /config/advanced**

Update advanced configuration.

**Request:**
```json
{
  "wfo": {
    "enabled": true,
    "train_days": 60
  },
  "ml": {
    "enabled": true,
    "confidence_threshold": 0.6
  }
}
```

---

## 🏥 System

### **GET /health**

Get system health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": 1711123456,
  "components": {
    "event_bus": "running",
    "database": "connected",
    "exchange": "connected"
  },
  "metrics": {
    "active_bots": 5,
    "uptime_hours": 24.5,
    "uptime_seconds": 88200
  },
  "version": "4.1.0"
}
```

**cURL:**
```bash
curl http://localhost:3000/api/v1/health
```

---

### **GET /status**

Get system status.

**Response:**
```json
{
  "status": "online",
  "environment": "development",
  "exchange": "binance",
  "tracking_symbols": ["BTC/USDT", "ETH/USDT"]
}
```

---

### **GET /exchange/markets**

Get available exchange markets.

**Response:**
```json
{
  "status": "success",
  "markets": [
    {
      "symbol": "BTC/USDT",
      "base": "BTC",
      "type": "SÜRESİZ VADELİ (PERP)",
      "id": "BTCUSDT"
    }
  ]
}
```

---

## 📊 Dashboard

### **GET /dashboard-metrics**

Get all dashboard metrics.

**Response:**
```json
{
  "portfolio": {
    "balance": 10000.00,
    "free_margin": 9500.00,
    "used_margin": 500.00,
    "equity": 10123.45,
    "unrealized_pnl": 123.45,
    "total_pnl": 1234.56,
    "total_trades": 50,
    "win_rate": 0.65,
    "total_commission": 12.34
  },
  "positions": [...],
  "latest_decisions": {...},
  "market_regime": "TRENDING_BULL"
}
```

---

## 🔍 Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `400 Bad Request` | Invalid request format | Check request body |
| `404 Not Found` | Endpoint doesn't exist | Check URL |
| `500 Internal Server Error` | Server error | Check logs |
| `BOT_NOT_FOUND` | Bot ID doesn't exist | Check bot_id |
| `STRATEGY_NOT_FOUND` | Strategy doesn't exist | Check strategy_id |
| `MODEL_NOT_FOUND` | ML model doesn't exist | Train model first |

---

## 📚 SDKs & Libraries

### **Python Client**

```python
import requests

BASE_URL = 'http://localhost:3000/api/v1'

# Start bot
response = requests.post(f'{BASE_URL}/bot/start', json={
    'symbol': 'BTC/USDT',
    'strategy_id': 'trend_master',
    'timeframe': '1m'
})

# Get trade history
response = requests.get(f'{BASE_URL}/trades/history')
trades = response.json()['trades']

# Check health
response = requests.get(f'{BASE_URL}/health')
health = response.json()
```

### **JavaScript Client**

```javascript
const BASE_URL = 'http://localhost:3000/api/v1';

// Start bot
async function startBot(symbol, strategy) {
  const response = await fetch(`${BASE_URL}/bot/start`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({symbol, strategy_id: strategy})
  });
  return await response.json();
}

// Get trade history
async function getTrades() {
  const response = await fetch(`${BASE_URL}/trades/history`);
  return await response.json();
}
```

---

## 🔄 Changelog

| Version | Date | Changes |
|---------|------|---------|
| v4.0.0 | Jan 2026 | Initial API documentation |
| v4.1.0 | Mar 2026 | Added health check, configuration endpoints |

---

**Author:** CryptoAlgoBot Team  
**Review Status:** ✅ Peer Reviewed  
**Next Review:** April 2026
