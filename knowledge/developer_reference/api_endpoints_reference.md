# 🌐 API Endpoints Reference (Tam Liste)

**Versiyon:** v4.0 (Production-Ready)
**Son Güncelleme:** Mart 2026
**Toplam Endpoint:** 59+ endpoint

---

## 📋 Genel Bakış

Bu doküman, CryptoAlgoBot'un tüm FastAPI endpoint'lerini kategorize edilmiş şekilde içerir. Her endpoint için request/response örnekleri ve kullanım senaryoları verilmiştir.

---

## 🗂️ Endpoint Kategorileri

| Kategori | Prefix | Endpoint Sayısı | Dosya |
|----------|--------|-----------------|-------|
| **System** | `/api/v1/` | 12 | `api/routers/system.py` |
| **Bot** | `/api/v1/bot/*` | 9 | `api/routers/bot.py` |
| **ML** | `/api/v1/ml/*` | 9 | `api/routers/ml.py` |
| **Data** | `/api/v1/data/*` | 18 | `api/routers/data.py` |
| **Strategy** | `/api/v1/strategy/*` | 6 | `api/routers/strategy.py` |
| **Strategy Builder** | `/api/v1/strategy-builder/*` | 5 | `api/routers/strategy_builder.py` |
| **Backtest** | `/api/v1/backtest/*` | 3 | `api/routers/backtest.py` |
| **Trades** | `/api/v1/trades/*` | 3 | `api/routers/trades.py` |
| **TOPLAM** | - | **59+** | 8 dosya |

---

## 1. SYSTEM ENDPOINTS

### **GET /api/v1/status**

**Açıklama:** Sistem durumunu döner.

**Response:**
```json
{
    "status": "online",
    "environment": "development",
    "exchange": "binance",
    "tracking_symbols": ["BTC/USDT:USDT", "ETH/USDT:USDT"]
}
```

---

### **GET /api/v1/dashboard-metrics**

**Açıklama:** Dashboard için tüm metrikleri döner (portfolio, positions, decisions).

**Response:**
```json
{
    "portfolio": {
        "balance": 10000.0,
        "free_margin": 8500.0,
        "used_margin": 1500.0,
        "equity": 10120.0,
        "unrealized_pnl": 120.0,
        "total_pnl": 2500.0,
        "total_trades": 45,
        "win_rate": 0.62,
        "total_commission": 125.50,
        "total_notional": 125000.0
    },
    "positions": [...],
    "latest_decisions": {...},
    "market_regime": "TRENDING"
}
```

---

### **GET /api/v1/config/symbols**

**Açıklama:** İzlenen sembollerin listesini döner.

**Response:**
```json
{
    "symbols": ["BTC/USDT:USDT", "ETH/USDT:USDT", "DOGE/USDT:USDT"]
}
```

---

### **GET /api/v1/exchange/markets**

**Açıklama:** Borsadaki tüm aktif USDT işlem çiftlerini döner.

**Response:**
```json
{
    "markets": [
        "BTC/USDT:USDT",
        "ETH/USDT:USDT",
        "BNB/USDT:USDT",
        ...
    ]
}
```

---

### **GET /api/v1/config/bot**

**Açıklama:** Genel bot ayarlarını döner.

**Response:**
```json
{
    "status": "success",
    "config": {
        "environment": "development",
        "exchange": "binance",
        "log_level": "INFO",
        "name": "CryptoAlgoBot"
    }
}
```

---

### **POST /api/v1/config/risk**

**Açıklama:** Risk ayarlarını günceller.

**Request:**
```json
{
    "max_risk_per_trade": 1.0,
    "max_leverage": 10,
    "max_open_positions": 5,
    "max_consecutive_losses": 5,
    "kill_switch_enabled": true
}
```

---

### **POST /api/v1/config/advanced**

**Açıklama:** WFO, ML, HTF ayarlarını günceller.

**Request:**
```json
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

### **POST /api/v1/config/api-keys**

**Açıklama:** API anahtarlarını şifreli şekilde kaydeder.

**Request:**
```json
{
    "api_key": "pk_live_abc123...",
    "api_secret": "sk_live_xyz789..."
}
```

---

### **GET /api/v1/config/api-keys/test**

**Açıklama:** API anahtarlarını test eder.

**Response:**
```json
{
    "status": "success",
    "message": "API bağlantısı başarılı",
    "account_type": "futures"
}
```

---

## 2. BOT ENDPOINTS

### **POST /api/v1/bot/start**

**Açıklama:** Yeni bot başlatır.

**Request:**
```json
{
    "symbol": "BTC/USDT:USDT",
    "strategy_id": "trend_master",
    "timeframe": "1h",
    "market_type": "swap",
    "margin_type": "isolated"
}
```

**Response:**
```json
{
    "status": "success",
    "bot_id": "BTC/USDT:USDT_trend_master_1h_1",
    "message": "Bot başlatıldı"
}
```

---

### **POST /api/v1/bot/stop**

**Açıklama:** Botu durdurur.

**Request:**
```json
{
    "bot_id": "BTC/USDT:USDT_trend_master_1h_1"
}
```

---

### **POST /api/v1/bot/resume**

**Açıklama:** Durmuş botu devam ettirir.

---

### **POST /api/v1/bot/remove**

**Açıklama:** Botu siler.

---

### **GET /api/v1/bot/status**

**Açıklama:** Bot durumunu döner.

---

### **GET /api/v1/bot/list**

**Açıklama:** Tüm aktif botları listeler.

**Response:**
```json
{
    "bots": [
        {
            "bot_id": "BTC/USDT:USDT_trend_master_1h_1",
            "symbol": "BTC/USDT:USDT",
            "strategy_id": "trend_master",
            "timeframe": "1h",
            "status": "running",
            "pnl": 125.50,
            "pnl_percent": 1.25
        }
    ]
}
```

---

## 3. ML ENDPOINTS

### **POST /api/v1/ml/train**

**Açıklama:** ML model eğitimi başlatır.

**Request:**
```json
{
    "symbol": "BTC/USDT:USDT",
    "timeframe": "1h",
    "limit": 5000,
    "tp_multiplier": 2.0,
    "sl_multiplier": 2.0
}
```

---

### **GET /api/v1/ml/status**

**Açıklama:** ML eğitim durumunu döner.

**Response:**
```json
{
    "status": "training",
    "progress": 45,
    "message": "Model eğitiliyor..."
}
```

---

### **GET /api/v1/ml/training-history**

**Açıklama:** ML eğitim geçmişini döner.

---

### **DELETE /api/v1/ml/training-history**

**Açıklama:** ML eğitim geçmişini siler.

---

### **DELETE /api/v1/ml/model**

**Açıklama:** ML modelini siler.

---

### **GET /api/v1/ml/check-model**

**Açıklama:** Model var mı kontrol eder.

---

### **GET /api/v1/ml/visual-analysis**

**Açıklama:** ML görsel analiz döner.

---

## 4. DATA ENDPOINTS

### **GET /api/v1/data/history-status**

**Açıklama:** Veri indirme durumunu döner.

---

### **POST /api/v1/data/download-history**

**Açıklama:** Veri indirme başlatır.

**Request:**
```json
{
    "symbol": "BTC/USDT",
    "timeframe": "1m",
    "days": 30
}
```

---

### **POST /api/v1/data/stop-download**

**Açıklama:** İndirmeyi durdurur.

---

### **POST /api/v1/data/resume-download**

**Açıklama:** İndirmeyi devam ettirir.

---

### **GET /api/v1/data/active-downloads**

**Açıklama:** Aktif indirmeleri listeler.

---

### **GET /api/v1/data/all-download-tasks**

**Açıklama:** Tüm indirme görevlerini döner.

---

### **POST /api/v1/data/delete-task**

**Açıklama:** İndirme görevini siler.

---

### **DELETE /api/v1/data/delete-all**

**Açıklama:** Tüm indirme görevlerini siler.

---

### **DELETE /api/v1/data/delete-klines**

**Açıklama:** Kline verilerini siler.

---

### **POST /api/v1/data/toggle-pause**

**Açıklama:** İndirmeyi duraklatır/devam ettirir.

---

### **GET /api/v1/data/symbols-with-data**

**Açıklama:** Verisi olan sembolleri döner.

---

### **GET /api/v1/data/check-data-gaps**

**Açıklama:** Veri boşluklarını kontrol eder.

---

### **POST /api/v1/data/fill-data-gaps**

**Açıklama:** Veri boşluklarını doldurur.

---

### **GET /api/v1/data/data-count**

**Açıklama:** Mum sayısını döner.

---

### **GET /api/v1/data/inventory**

**Açıklama:** Veri envanterini döner.

---

### **GET /api/v1/data/stats**

**Açıklama:** Veri istatistiklerini döner.

---

### **GET /api/v1/data/symbols**

**Açıklama:** Mevcut sembolleri döner.

---

## 5. STRATEGY ENDPOINTS

### **GET /api/v1/strategies**

**Açıklama:** Strateji listesini döner.

---

### **POST /api/v1/strategy/select**

**Açıklama:** Strateji seçer.

**Request:**
```json
{
    "symbol": "BTC/USDT",
    "strategy_id": "trend_master",
    "timeframe": "1h"
}
```

---

### **GET /api/v1/strategy-report**

**Açıklama:** Strateji raporunu döner.

---

### **GET /api/v1/strategy/{strategy_id}/chart-data**

**Açıklama:** Strateji grafik verisini döner.

---

## 6. STRATEGY BUILDER ENDPOINTS

### **POST /api/v1/strategy-builder/save**

**Açıklama:** No-code stratejiyi kaydeder.

---

### **GET /api/v1/strategy-builder/list**

**Açıklama:** Kaydedilmiş stratejileri listeler.

---

### **POST /api/v1/strategy-builder/test**

**Açıklama:** Strateji backtest yapar.

---

### **GET /api/v1/strategy-builder/info/{filename}**

**Açıklama:** Strateji bilgilerini döner.

---

### **DELETE /api/v1/strategy-builder/delete/{filename}**

**Açıklama:** Stratejiyi siler.

---

## 7. BACKTEST ENDPOINTS

### **POST /api/v1/backtest/run**

**Açıklama:** Backtest simülasyonu başlatır.

---

### **GET /api/v1/backtest/results/{backtest_id}**

**Açıklama:** Backtest sonuçlarını döner.

---

### **POST /api/v1/backtest/optimize**

**Açıklama:** Strateji optimizasyonu yapar.

---

## 8. TRADES ENDPOINTS

### **GET /api/v1/trades/history**

**Açıklama:** İşlem geçmişini döner.

---

### **DELETE /api/v1/trades/clear**

**Açıklama:** İşlem geçmişini temizler.

---

### **GET /api/v1/trades/stats**

**Açıklama:** İşlem istatistiklerini döner.

**Response:**
```json
{
    "total_trades": 45,
    "winning_trades": 28,
    "losing_trades": 17,
    "win_rate": 0.62,
    "total_pnl": 2500.0,
    "average_pnl": 55.56,
    "profit_factor": 2.1,
    "max_drawdown": -450.0
}
```

---

## 📚 İlgili Dokümanlar

- **API Modularization:** `architecture/api_modularization.md`
- **Event-Driven Architecture:** `architecture/event_driven_architecture.md`

---

*Bu doküman API Endpoints v4.0 (Mart 2026) için hazırlanmıştır.*
