# 🔧 Balance Fix Utility

**Version:** v4.1.2  
**Status:** ✅ Production Ready  
**Category:** Utility / Troubleshooting  
**Last Updated:** March 2026

---

## 📋 Overview

Balance Fix Utility, negative balance veya veri tutarsızlığı sorunlarını çözmek için diagnostic ve repair aracıdır.

**Problem:**
- Ubuntu'da negative balance (-$1.2B)
- Trade PnL hatalı hesaplanıyor
- Database corruption

**Çözüm:**
- Database integrity check
- Trade PnL analizi
- Otomatik repair seçenekleri

---

## 🔧 Usage

### **File Location**

```
fix_balance.py
```

### **Basic Usage**

```bash
# Ubuntu/VPS
cd /path/to/Crypto Bot
python fix_balance.py

# Windows
cd f:\Crypto Bot
python fix_balance.py
```

### **Interactive Mode**

```
============================================================
🔍 DATABASE INTEGRITY CHECK
============================================================

📊 Tables found: ['klines', 'trades', 'download_tasks']
📝 Total trades: 4

📈 Trade PnL Analysis:
  BTC/USDT | SHORT | PnL: $-602067400.42 (-6020674.00%) | TAKE_PROFIT
    ⚠️  WARNING: Absurd PnL value detected!

🔍 Checking for duplicate trades...
  ✅ No duplicates found

============================================================
🔧 BALANCE FIX OPTIONS
============================================================

Choose fix option:
  1. Clear all trades (safe)
  2. Reset database completely (destructive)
  3. Just check, don't modify

Enter choice (1-3): 1
```

---

## 🎯 Options Explained

### **Option 1: Clear All Trades (Safe)**

**What it does:**
- Deletes all records from `trades` table
- Preserves klines (OHLCV data)
- Preserves download_tasks

**When to use:**
- Negative balance
- Incorrect PnL values
- Trade calculation errors

**Command:**
```bash
python fix_balance.py
# Enter: 1

# Or direct SQL
sqlite3 cryptobot.db "DELETE FROM trades;"
```

**Aftermath:**
- Bot restart required
- Balance resets to $10,000 (initial)
- Trade history cleared

---

### **Option 2: Reset Database (Destructive)**

**What it does:**
- Deletes entire `cryptobot.db` file
- Bot creates new DB on next start

**When to use:**
- Severe corruption
- Schema errors
- Multiple table issues

**Command:**
```bash
python fix_balance.py
# Enter: 2

# Or manual
rm cryptobot.db
python main.py  # Auto-creates new DB
```

**Aftermath:**
- All data lost (klines, trades, tasks)
- Fresh start
- Need to re-download data

---

### **Option 3: Check Only**

**What it does:**
- Read-only diagnostic
- No modifications

**When to use:**
- Initial diagnosis
- Before making changes
- Regular maintenance

**Command:**
```bash
python fix_balance.py
# Enter: 3
```

---

## 📊 Diagnostic Output

### **Healthy Database**

```
📊 Tables found: ['klines', 'trades', 'download_tasks']
📝 Total trades: 15

📈 Trade PnL Analysis:
  BTC/USDT | SHORT | PnL: $28.87 (3.26%) | TAKE_PROFIT
  ETH/USDT | LONG | PnL: $15.42 (1.85%) | STOP_LOSS
  BTC/USDT | SHORT | PnL: $13.43 (1.61%) | TAKE_PROFIT

🔍 Checking for duplicate trades...
  ✅ No duplicates found
```

### **Corrupted Database**

```
📊 Tables found: ['klines', 'trades', 'download_tasks']
📝 Total trades: 4

📈 Trade PnL Analysis:
  BTC/USDT | SHORT | PnL: $-602067400.42 (-6020674.00%) | TAKE_PROFIT
    ⚠️  WARNING: Absurd PnL value detected!
  ETH/USDT | LONG | PnL: $-123456789.01 (-999999.99%) | STOP_LOSS
    ⚠️  WARNING: Absurd PnL value detected!

🔍 Checking for duplicate trades...
  ⚠️  Found 2 duplicate trade IDs!
     Duplicate ID: trade_12345
     Duplicate ID: trade_67890
```

---

## 🔍 Common Issues

### **Issue 1: Negative Balance**

**Symptoms:**
```
💰 Bakiye: $-1,204,124,811.82
📈 Equity: $-1,204,124,811.82
```

**Cause:**
- Trade PnL calculation error
- Position size too large
- Leverage miscalculation

**Fix:**
```bash
python fix_balance.py
# Enter: 1 (Clear trades)

# Restart bot
python main.py
```

---

### **Issue 2: Absurd PnL Values**

**Symptoms:**
```
PnL: $-602,067,400.42 (-6,020,674.00%)
```

**Cause:**
- Position size × price overflow
- Decimal precision error
- Database corruption

**Fix:**
```bash
# Check for absurd values
sqlite3 cryptobot.db "SELECT * FROM trades WHERE abs(pnl_usd) > 1000000;"

# Clear if found
python fix_balance.py
# Enter: 1
```

---

### **Issue 3: Duplicate Trade IDs**

**Symptoms:**
```
⚠️  Found 2 duplicate trade IDs!
```

**Cause:**
- Concurrent writes
- Race condition
- Missing UNIQUE constraint

**Fix:**
```bash
# Remove duplicates
sqlite3 cryptobot.db <<EOF
DELETE FROM trades WHERE id NOT IN (
  SELECT MIN(id) FROM trades GROUP BY id
);
EOF

# Or use utility
python fix_balance.py
# Enter: 1
```

---

## 📈 Prevention

### **1. Regular Backups**

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp cryptobot.db backups/cryptobot_$DATE.db
echo "Backup created: cryptobot_$DATE.db"
```

### **2. Database Integrity Check**

```bash
# Weekly integrity check
sqlite3 cryptobot.db "PRAGMA integrity_check;"
```

### **3. Monitor PnL Values**

```python
# Add validation in position_manager.py
def close_position(self, bot_id, exit_price):
    pnl = calculate_pnl(exit_price)
    
    # Validation
    if abs(pnl) > 1000000:  # >$1M
        logger.warning(f"⚠️ Suspicious PnL: ${pnl:.2f}")
        # Add manual review flag
```

---

## 🧪 Testing

### **Test 1: Healthy Database**

```bash
# Create test trades
sqlite3 cryptobot.db <<EOF
INSERT INTO trades (id, symbol, direction, pnl_usd) 
VALUES 
  ('test_1', 'BTC/USDT', 'LONG', 100.50),
  ('test_2', 'ETH/USDT', 'SHORT', -50.25);
EOF

# Run utility
python fix_balance.py
# Enter: 3 (Check only)

# Expected: No warnings
```

### **Test 2: Corrupted Database**

```bash
# Insert absurd PnL
sqlite3 cryptobot.db <<EOF
INSERT INTO trades (id, symbol, direction, pnl_usd) 
VALUES ('test_bad', 'BTC/USDT', 'LONG', -999999999.99);
EOF

# Run utility
python fix_balance.py
# Enter: 3

# Expected: ⚠️ WARNING: Absurd PnL value detected!
```

---

## 📚 Related Files

| File | Purpose |
|------|---------|
| `fix_balance.py` | Utility script |
| `data/database.py` | Database manager |
| `core/trading/position_manager.py` | PnL calculation |
| `cryptobot.db` | SQLite database |

---

## 🔄 Changelog

| Version | Date | Changes |
|---------|------|---------|
| v4.1.2 | Mar 2026 | Initial implementation |
| v4.1.3 | Mar 2026 | Added duplicate detection |
| v4.1.4 | Mar 2026 | Added PnL validation |

---

**Author:** CryptoAlgoBot Team  
**Review Status:** ✅ Peer Reviewed  
**Next Review:** April 2026
