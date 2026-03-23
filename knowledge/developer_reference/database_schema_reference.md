# 🗄️ Database Schema Reference (SQLite/PostgreSQL)

**Versiyon:** v4.0 (Production-Ready)
**Son Güncelleme:** Mart 2026
**Engine:** SQLite (default) / PostgreSQL (opsiyonel)

---

## 📋 Genel Bakış

CryptoAlgoBot, hibrit veritabanı mimarisi kullanır:
- **SQLite:** Varsayılan (dosya tabanlı, Docker gerektirmez)
- **PostgreSQL + TimescaleDB:** Opsiyonel (zaman serisi optimizasyonu)
- **Redis:** Opsiyonel (cache layer)

---

## 🏗️ Mimari

```
┌─────────────────────────────────────────────────────────┐
│  Application Layer (Python/asyncio)                     │
├─────────────────────────────────────────────────────────┤
│  Database Manager (data/database.py)                    │
│  - aiosqlite (SQLite)                                   │
│  - asyncpg (PostgreSQL)                                 │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  Database Engine                                        │
│  ┌─────────────────┐  ┌──────────────────┐             │
│  │ SQLite          │  │ PostgreSQL +     │             │
│  │ (cryptobot.db)  │  │ TimescaleDB      │             │
│  └─────────────────┘  └──────────────────┘             │
└─────────────────────────────────────────────────────────┘
```

---

## 📊 Tablolar

### **1. klines (Mum Verileri)**

**Açıklama:** OHLCV (Open-High-Low-Close-Volume) verileri

**Şema:**
```sql
CREATE TABLE IF NOT EXISTS klines (
    timestamp TIMESTAMP NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL DEFAULT '1m',
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    PRIMARY KEY (timestamp, symbol, timeframe)
);
```

**Koloonlar:**

| Kolon | Tip | Açıklama | Örnek |
|-------|-----|----------|-------|
| `timestamp` | TIMESTAMP | Mum zamanı (UTC) | `2026-03-17 12:00:00` |
| `symbol` | TEXT | Sembol adı | `BTC/USDT:USDT` |
| `timeframe` | TEXT | Zaman dilimi | `1m`, `1h`, `1d` |
| `open` | REAL | Açılış fiyatı | `50000.0` |
| `high` | REAL | En yüksek fiyat | `50500.0` |
| `low` | REAL | En düşük fiyat | `49800.0` |
| `close` | REAL | Kapanış fiyatı | `50200.0` |
| `volume` | REAL | Hacim | `1250.5` |

**Örnek Kayıt:**
```sql
INSERT INTO klines (timestamp, symbol, timeframe, open, high, low, close, volume)
VALUES ('2026-03-17 12:00:00', 'BTC/USDT:USDT', '1h', 50000.0, 50500.0, 49800.0, 50200.0, 1250.5);
```

**Sorgu Örnekleri:**

```sql
-- Son 100 mumu getir
SELECT * FROM klines
WHERE symbol = 'BTC/USDT:USDT' AND timeframe = '1h'
ORDER BY timestamp DESC
LIMIT 100;

-- Belirli tarih aralığında mumlar
SELECT * FROM klines
WHERE symbol = 'BTC/USDT:USDT' 
  AND timeframe = '1h'
  AND timestamp BETWEEN '2026-03-01' AND '2026-03-17'
ORDER BY timestamp ASC;

-- Sembol ve timeframe'e göre gruplanmış mum sayısı
SELECT symbol, timeframe, COUNT(*) as candle_count
FROM klines
GROUP BY symbol, timeframe;
```

---

### **2. download_tasks (İndirme Görevleri)**

**Açıklama:** Devam eden/tamamlanan veri indirme görevleri

**Şema:**
```sql
CREATE TABLE IF NOT EXISTS download_tasks (
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    start_date TEXT NOT NULL,
    market_type TEXT NOT NULL,
    status TEXT NOT NULL,
    current_ts BIGINT,
    target_start_ms BIGINT,
    PRIMARY KEY (symbol, market_type)
);
```

**Koloonlar:**

| Kolon | Tip | Açıklama | Örnek |
|-------|-----|----------|-------|
| `symbol` | TEXT | Sembol adı | `BTC/USDT` |
| `timeframe` | TEXT | Zaman dilimi | `1m` |
| `start_date` | TEXT | Başlangıç tarihi | `2026-02-15` |
| `market_type` | TEXT | Piyasa tipi | `swap`, `spot` |
| `status` | TEXT | Durum | `running`, `paused`, `completed` |
| `current_ts` | BIGINT | Şu anki timestamp (ms) | `1710847200000` |
| `target_start_ms` | BIGINT | Hedef başlangıç (ms) | `1708041600000` |

**Örnek Kayıt:**
```sql
INSERT INTO download_tasks (symbol, timeframe, start_date, market_type, status, current_ts, target_start_ms)
VALUES ('BTC/USDT', '1m', '2026-02-15', 'swap', 'running', 1710847200000, 1708041600000);
```

**Sorgu Örnekleri:**

```sql
-- Aktif indirmeleri listele
SELECT * FROM download_tasks
WHERE status = 'running';

-- Tamamlanmış görevleri göster
SELECT symbol, timeframe, start_date, status
FROM download_tasks
WHERE status = 'completed';

-- Bekleyen görevleri getir
SELECT * FROM download_tasks
WHERE status IN ('pending', 'paused');
```

---

### **3. trades (İşlem Geçmişi)**

**Açıklama:** Açık/kapalı tüm işlemler

**Şema:**
```sql
CREATE TABLE IF NOT EXISTS trades (
    id TEXT PRIMARY KEY,
    timestamp DATETIME DEFAULT (datetime('now','localtime')),
    closed_at TEXT,
    symbol TEXT NOT NULL,
    strategy_id TEXT,
    direction TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL,
    size REAL NOT NULL,
    leverage REAL,
    pnl_usd REAL,
    pnl_percent REAL,
    reason TEXT,
    bot_id TEXT
);
```

**Koloonlar:**

| Kolon | Tip | Açıklama | Örnek |
|-------|-----|----------|-------|
| `id` | TEXT | Benzersiz işlem ID | `trade_1710847205` |
| `timestamp` | DATETIME | Açılış zamanı | `2026-03-17 12:30:00` |
| `closed_at` | TEXT | Kapanış zamanı | `2026-03-17 14:45:00` |
| `symbol` | TEXT | Sembol adı | `BTC/USDT:USDT` |
| `strategy_id` | TEXT | Strateji ID | `trend_master` |
| `direction` | TEXT | Yön | `LONG`, `SHORT` |
| `entry_price` | REAL | Giriş fiyatı | `50000.0` |
| `exit_price` | REAL | Çıkış fiyatı | `51000.0` |
| `size` | REAL | Pozisyon boyutu | `0.1` |
| `leverage` | REAL | Kaldıraç | `5.0` |
| `pnl_usd` | REAL | Kar/Zarar ($) | `100.0` |
| `pnl_percent` | REAL | Kar/Zarar (%) | `0.02` |
| `reason` | TEXT | Kapanış nedeni | `TAKE_PROFIT`, `STOP_LOSS` |
| `bot_id` | TEXT | Bot ID | `BTC_1h_1` |

**Örnek Kayıt:**
```sql
INSERT INTO trades (id, timestamp, closed_at, symbol, strategy_id, direction, entry_price, exit_price, size, leverage, pnl_usd, pnl_percent, reason, bot_id)
VALUES ('trade_1710847205', '2026-03-17 12:30:00', '2026-03-17 14:45:00', 'BTC/USDT:USDT', 'trend_master', 'LONG', 50000.0, 51000.0, 0.1, 5.0, 100.0, 0.02, 'TAKE_PROFIT', 'BTC_1h_1');
```

**Sorgu Örnekleri:**

```sql
-- Son 50 işlemi getir
SELECT * FROM trades
ORDER BY timestamp DESC
LIMIT 50;

-- Kazanan işlemleri listele
SELECT * FROM trades
WHERE pnl_usd > 0;

-- Strateji bazlı performans
SELECT strategy_id, 
       COUNT(*) as total_trades,
       SUM(pnl_usd) as total_pnl,
       AVG(pnl_percent) as avg_pnl_percent,
       SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as win_rate
FROM trades
GROUP BY strategy_id;

-- Günlük PnL
SELECT DATE(timestamp) as trade_date,
       SUM(pnl_usd) as daily_pnl,
       COUNT(*) as trades_count
FROM trades
GROUP BY DATE(timestamp)
ORDER BY trade_date DESC;
```

---

## 🔧 Database Manager (Python API)

### **Bağlantı Yönetimi**

```python
# data/database.py
from data.database import db_manager

# Bağlantı başlat
await db_manager.connect()

# Tabloları oluştur
await db_manager.initialize_db()
```

---

### **Kaye Ekleme (UPSERT)**

```python
# Mum verisi kaydet (varsı güncelle, yoksa ekle)
await db_manager.save_kline(
    symbol='BTC/USDT:USDT',
    kline_data=[1710847200000, 50000, 50500, 49800, 50200, 1250.5],
    timeframe='1h'
)
```

---

### **Veri Çekme**

```python
# Mum aralığını al
candle_range = await db_manager.get_candle_range(
    symbol='BTC/USDT:USDT',
    timeframe='1h'
)

# DataFrame olarak al
df = await db_manager.get_klines_as_dataframe(
    symbol='BTC/USDT:USDT',
    timeframe='1h',
    start_date='2026-03-01',
    end_date='2026-03-17'
)
```

---

## 🚨 Sorun Giderme

### **Sorun 1: Database Locked**

**Semptom:** `sqlite3.OperationalError: database is locked`

**Çözüm:**
```python
# WAL mode aktif et
await db_manager.sqlite_conn.execute("PRAGMA journal_mode=WAL")

# Busy timeout artır
await db_manager.sqlite_conn.execute("PRAGMA busy_timeout=60000")

# Lock mekanizması kullan
async with db_manager._lock:
    await db_manager.save_kline(...)
```

---

### **Sorun 2: Schema Mismatch**

**Semptom:** `no such column: strategy_id`

**Çözüm:**
```python
# Migration çalıştır
await db_manager._validate_and_migrate_schemas()

# Manuel sütun ekle
try:
    await db_manager.sqlite_conn.execute(
        "ALTER TABLE trades ADD COLUMN strategy_id TEXT"
    )
except:
    pass  # Zaten var
```

---

### **Sorun 3: PostgreSQL Bağlantı Hatası**

**Semptom:** `asyncpg.exceptions.PostgresConnectionError`

**Çözüm:**
```bash
# Docker'da PostgreSQL başlat
docker-compose up -d postgres timescaledb

# Bağlantı URL'ini kontrol et
echo $TIMESCALE_DB_URL
# postgresql://user:pass@localhost:5432/cryptobot
```

---

## 📊 Veritabanı İstatistikleri

### **Tablo Boyutları**

```sql
-- SQLite tablo boyutları
SELECT name, 
       pgsize_bloat(name) as size_bytes
FROM sqlite_master
WHERE type='table'
ORDER BY size_bytes DESC;
```

### **Kayıt Sayıları**

```sql
-- Her tablodaki kayıt sayısı
SELECT 'klines' as table_name, COUNT(*) as row_count FROM klines
UNION ALL
SELECT 'download_tasks', COUNT(*) FROM download_tasks
UNION ALL
SELECT 'trades', COUNT(*) FROM trades;
```

---

## 📚 İlgili Dokümanlar

- **Parquet Data Lake:** `features/parquet_data_lake.md`
- **Data Pipeline:** `architecture/data_pipeline.md`

---

*Bu doküman Database Schema v4.0 (Mart 2026) için hazırlanmıştır.*
