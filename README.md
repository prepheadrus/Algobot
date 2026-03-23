# 🚀 CryptoAlgoBot - Production-Ready Cryptocurrency Trading Bot

**Version:** v4.1.0 (Production-Ready)  
**Status:** ✅ 14/14 E2E Tests Passed  
**Architecture:** Event-Driven + Clean Architecture + DDD

Kripto para piyasalarında, 7/24 dinamik risk yönetimi, makine öğrenimi destekli fiyat tahminlemesi ve çoklu zaman dilimi analizi ile yüksek başarı oranlı bir algoritmik ticaret sistemi.

## 📚 Dokümantasyon

Detaylı teknik dokümantasyon için **[Knowledge Base](knowledge/INDEX.md)** klasörüne bakın.

### **Quick Links:**
- [🏗️ Sistem Mimarisi](knowledge/architecture/overview.md)
- [🛡️ Circuit Breaker](knowledge/features/circuit_breaker.md)
- [🛑 Graceful Shutdown](knowledge/features/graceful_shutdown.md)
- [📝 Structured Logging](knowledge/features/structured_logging.md)
- [🧠 ML Overfitting Protection](knowledge/features/ml_overfitting_protection.md)
- [🏥 Health Check](knowledge/features/health_check_endpoint.md)
- [⚙️ Configuration Guide](knowledge/developer_reference/configuration_guide.md)
- [🚀 Deployment Guide](knowledge/workflows/deployment_guide.md)
- [📡 API Reference](knowledge/developer_reference/api_reference.md)

## ⚡ Hızlı Başlangıç

### Önkoşullar

**Gerekli:**
- ✅ Python 3.10+ ([İndir](https://www.python.org/downloads/))
- ✅ Git ([İndir](https://git-scm.com/downloads))
- ✅ 4GB+ RAM
- ✅ 10GB+ Disk Alanı

**Opsiyonel (Canlı Trading için):**
- 📝 Binance API Key ([Oluştur](https://www.binance.com/en/my/settings/api-management))

---

### 1. Depoyu Klonla

```bash
git clone https://github.com/prepheadrus/Crypto_Automat.git
cd Crypto_Automat
```

**Boyut:** ~50MB (klonlama sonrası ~200MB)

---

### 2. Otomatik Kurulum

**Ubuntu/Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

**Windows:**
```cmd
setup.bat
```

**Süre:** 5-10 dakika (ilk kurulumda)

**Ne yapar:**
- ✅ Python virtual environment oluşturur
- ✅ Tüm bağımlılıkları yükler (requirements.txt)
- ✅ .env dosyası oluşturur (.env.example'dan)
- ✅ Gerekli klasörleri oluşturur
- ✅ PyArrow, XGBoost gibi kritik kütüphaneleri doğrular

---

### 3. Yapılandırma

**.env dosyası** (API anahtarları için):
```bash
cp .env.example .env
nano .env  # Linux
notepad .env  # Windows
```

**Düzenle:**
```env
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
ENVIRONMENT=development
```

> 💡 **Not:** Paper trading için API anahtarı gerekmez! Canlı trading için gereklidir.

**config.yaml** (Trading ayarları için):
```bash
cp config.example.yaml config.yaml
nano config.yaml  # Linux
notepad config.yaml  # Windows
```

**Önerilen Başlangıç Ayarları:**
```yaml
bot:
  environment: development
  log_level: INFO

risk_management:
  max_risk_per_trade_percent: 1.0
  max_leverage: 5
  max_open_positions: 5
  kill_switch:
    enabled: true
    max_consecutive_losses: 5

ml:
  enabled: true
  confidence_threshold: 0.5

htf:
  enabled: false  # Başlangıçta kapalı (daha fazla işlem)
```

---

### 4. Botu Başlat

**Ubuntu/Linux:**
```bash
source venv/bin/activate
python3 main.py
```

**Windows:**
```cmd
venv\Scripts\activate
python main.py
```

**İlk Başlatma:**
- ⏱️ 10-30 saniye sürer
- 📦 Parquet Data Lake otomatik yüklenir
- 📊 Mevcut semboller otomatik başlatılır

**Beklenen Çıktı:**
```
✅ Event Bus başlatıldı (5 worker)
✅ [AUTO-SYNC] Parquet'ten 2 sembol yüklendi!
📡 [WSS] BTC/USDT için WebSocket dinleyici başlatıldı
🚀 [POLLER] BTC/USDT için strateji poller başlatıldı
✅ BOT TAM OLARAK BAŞLATILDI!
Dashboard: http://localhost:3000
```

---

### 5. Dashboard'a Eriş

Tarayıcınızda şu adresi açın:
- **Local:** http://localhost:3000
- **Swagger Docs:** http://localhost:3000/docs
- **Health Check:** http://localhost:3000/api/v1/health

> ⚠️ **Firewall Ayarı:** Port 3000'i açmayı unutmayın!

**İlk Adımlar:**
1. **Veri Laboratuvarı** → BTC/USDT, ETH/USDT indir
2. **Bot Yönetimi** → Bot başlat (Symbol: BTC/USDT, Strategy: trend_master)
3. **Aktif Stratejiler** → Pozisyonları izle
4. **İşlem Geçmişi** → Kapanan işlemleri gör

---

### 6. İlk Trading Deneyi

**Paper Trading (Önerilen):**
```yaml
# config.yaml
trading:
  exchange: binance
  symbols:
    - BTC/USDT
```

**Adımlar:**
1. Dashboard → Sistem Ayarları
2. Risk Yönetimi → Max Risk: %1.0
3. Bot Başlat → BTC/USDT + trend_master
4. İşlem alınca bekle (5-30 dakika)
5. PnL izle

**Canlı Trading (İleri Seviye):**
```yaml
# .env dosyasına API anahtarlarını ekle
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret

# config.yaml
bot:
  environment: production
```

> ⚠️ **Uyarı:** Canlı trading risklidir! Küçük miktarlarla başlayın.

---

## 🔥 v4.1.0 Yeni Özellikler

### **Reliability & Fault Tolerance**
- ✅ **Circuit Breaker Pattern:** API çağrıları için otomatik hata izolasyonu
- ✅ **Graceful Shutdown:** 7 adımlı güvenli kapatma
- ✅ **Database Retry:** Locked hatalarında otomatik tekrar deneme

### **Observability**
- ✅ **Structured Logging:** JSON + renkli konsol loglama
- ✅ **Health Check Endpoint:** Prometheus/Grafana entegrasyonu
- ✅ **Event Bus Monitoring:** Worker health tracking

### **ML Improvements**
- ✅ **Overfitting Protection:** Veri boyutuna göre 4 mod (Complex/Medium/Simple/Ultra-Simple)
- ✅ **Auto-Regularization:** L1 + L2 regularization otomatik ayarı

### **Bug Fixes**
- ✅ **Trade History Tab Switch:** Otomatik veri yükleme
- ✅ **Balance Fix Utility:** Negative balance sorunu için diagnostic tool
- ✅ **Kill Switch Config:** Hot-reload desteği

---

## 🔧 Teknik Özellikler

### **Core Architecture**
- ✅ **Event-Driven:** Pub/Sub pattern (40+ event type)
- ✅ **Clean Architecture:** Routers → Services → Schemas
- ✅ **DDD:** Value Objects, Entities, Aggregates

### **Machine Learning**
- ✅ **Ensemble Model:** XGBoost + Random Forest
- ✅ **Triple Barrier Method:** Marcos Lopez de Prado
- ✅ **Auto-Regularization:** 4-mode overfitting protection

### **Data Layer**
- ✅ **Parquet Data Lake:** MTF-Daily partition
- ✅ **Snappy Compression:** %70-80 boyut azaltma
- ✅ **Async I/O:** Non-blocking operations

### **Risk Management**
- ✅ **Dynamic Position Sizing:** Risk-based calculation
- ✅ **Dynamic Leverage:** ML confidence-based
- ✅ **Kill Switch:** Ardışık kayıp koruması
- ✅ **ATR Trailing Stop:** Dinamik stop loss

### **Indicators**
- ✅ **Trend:** EMA, SMA, Kalman Filter, Supertrend
- ✅ **Momentum:** RSI, MACD, Stochastic, UO
- ✅ **Volatility:** ATR, Bollinger Bands, BTC VIX
- ✅ **Volume:** OBV, VWAP, PVI, NVI, Koncorde

---

## 📊 Performance Metrics

| Metric | Value |
|--------|-------|
| **Bot Launch** | <1 second |
| **Poller Launch** | <100ms |
| **ML Training** | 30-60s (10K candles) |
| **WFO Optimization** | 5-10 min (50 trials) |
| **API Response** | <50ms |
| **Event Processing** | <10ms |
| **E2E Tests** | 14/14 passed |

---

## 🚀 Deployment

### **Supported Platforms**
- ✅ Windows 10/11
- ✅ Ubuntu 20.04/22.04 LTS
- ✅ Oracle Cloud Free Tier
- ✅ AWS EC2
- ✅ DigitalOcean Droplet

### **Quick Deploy**

**Ubuntu:**
```bash
./setup.sh
sudo systemctl start cryptoalgobot
sudo systemctl status cryptoalgobot
```

**Windows:**
```cmd
setup.bat
python main.py
```

**Docker:**
```bash
docker-compose up -d
```

Detaylı kurulum için: **[Deployment Guide](knowledge/workflows/deployment_guide.md)**

---

## 📈 Features

### **Trading Strategies**
- ✅ TrendMaster Pro (Trend following)
- ✅ Scalper Ninja (Fast scalping)
- ✅ Golden Combo (Multi-indicator confluence)
- ✅ Adaptive Koncorde X (Custom indicators)
- ✅ Divergence Hunter (Divergence detection)
- ✅ KNN Quant ATR (KNN-based)
- ✅ Custom Strategies (No-code builder)

### **Multi-Bot Support**
- ✅ 1-to-N Bot Architecture
- ✅ Independent bot instances
- ✅ Symbol-specific strategies
- ✅ Parallel processing

### **Dashboard Features**
- ✅ Real-time portfolio tracking
- ✅ Active positions management
- ✅ Trade history with filters
- ✅ ML model training UI
- ✅ Strategy builder (no-code)
- ✅ Data laboratory
- ✅ System settings (hot-reload)

---

## 🔍 Monitoring

### **Health Check**
```bash
curl http://localhost:3000/api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "components": {
    "event_bus": "running",
    "database": "connected",
    "exchange": "connected"
  },
  "metrics": {
    "active_bots": 5,
    "uptime_hours": 24.5
  }
}
```

### **Logs**

**Development:**
```
15:30:45 | INFO     | Bot started
15:30:46 | DEBUG    | Loading config...
```

**Production (JSON):**
```json
{"timestamp": "2026-03-22T15:30:45", "level": "INFO", "message": "Bot started", "module": "main"}
```

---

## 🧪 Testing

```bash
# Run E2E tests
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_double_close.py -v

# Run all tests with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

**Test Results:** ✅ 14/14 passed

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📄 License

This project is licensed under the MIT License.

---

## 📞 Support

- **Documentation:** [Knowledge Base](knowledge/INDEX.md)
- **Issues:** [GitHub Issues](https://github.com/prepheadrus/Crypto_Automat/issues)
- **Discussions:** [GitHub Discussions](https://github.com/prepheadrus/Crypto_Automat/discussions)

---

## 🎯 Roadmap

### **Q2 2026**
- [ ] Multi-exchange support (Kucoin, OKX)
- [ ] Advanced order types (OCO, Bracket)
- [ ] Telegram/Discord notifications
- [ ] Mobile app (React Native)

### **Q3 2026**
- [ ] Backtesting engine improvements
- [ ] Strategy marketplace
- [ ] Social trading features
- [ ] Advanced analytics

---

**Last Updated:** March 2026  
**Version:** v4.1.0  
**Status:** Production Ready ✅
