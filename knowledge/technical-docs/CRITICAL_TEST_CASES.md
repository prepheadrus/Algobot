# 🧪 KRİTİK TEST VAKALARI - Mart 2026 Düzeltmeleri

Bu doküman, Mart 2026'da tespit edilen kritik race condition ve UI sync sorunlarının testlerini içerir.

---

## 📋 TEST EDİLECEK KRİTİK SORUNLAR:

### 1. Double-Close Race Condition ⚠️
**Sorun:** Aynı pozisyon aynı tick'te 2 kez kapatılıyor.
**Çözüm:** `closed_bot_ids` set'i ile duplicate önleme.
**Test:**
```python
# tests/test_double_close.py
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_no_duplicate_close():
    """Aynı pozisyon 2 kez kapatılmamalı"""
    from core.paper import paper_engine
    from core.trading.position_manager import position_manager
    
    # 1. Pozisyon aç
    await paper_engine.position_manager.open_position(
        bot_id="BTC_TEST_1",
        symbol="BTC/USDT",
        direction="LONG",
        entry_price=50000.0,
        size=1.0,
        leverage=10,
        stop_loss=49000.0,
        take_profit=52000.0
    )
    
    # 2. Aynı anda 2 kapatma çağrısı yap
    results = await asyncio.gather(
        paper_engine.close_position("BTC_TEST_1", 49000.0, "STOP_LOSS"),
        paper_engine.close_position("BTC_TEST_1", 49000.0, "STOP_LOSS"),
        return_exceptions=True
    )
    
    # 3. Sadece 1 trade kaydedildiğini doğrula
    trades = await db_manager.get_trades_by_bot("BTC_TEST_1")
    assert len(trades) == 1, f"Duplicate close! {len(trades)} trades found"
    
    # 4. Console'da warning log'u kontrol et (opsiyonel)
    # "bu tick'te zaten kapatıldı" mesajı görünmeli
```

---

### 2. Zombie Position Prevention 🧟
**Sorun:** Kapatma başarısız olursa pozisyon sonsuza kadar açık kalıyor.
**Çözüm:** `finally` bloğunda `is_closing` kilidini sıfırla.
**Test:**
```python
# tests/test_zombie_position.py
import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_zombie_prevention():
    """Kapatma başarısız olursa kilit sıfırlanmalı"""
    from core.paper import paper_engine
    
    # 1. Pozisyon aç
    await paper_engine.position_manager.open_position(
        bot_id="ETH_TEST_1",
        symbol="ETH/USDT",
        direction="LONG",
        entry_price=3000.0,
        size=10.0,
        leverage=10
    )
    
    position = paper_engine.position_manager.positions["ETH_TEST_1"]
    
    # 2. close_position'da exception fırlat
    with patch.object(
        paper_engine.position_manager,
        'close_position',
        side_effect=Exception("DB Connection Error")
    ):
        await paper_engine.close_position("ETH_TEST_1", 2900.0, "STOP_LOSS")
    
    # 3. is_closing kilidinin FALSE olduğunu doğrula
    assert position.metadata['is_closing'] == False, "ZOMBIE POSITION DETECTED!"
    
    # 4. Console'da "[ZOMBIE KORUMA] Kilit sıfırlanıyor" log'u kontrol et
```

---

### 3. WebSocket Armor 🛡️
**Sorun:** update_live_prices hatası WebSocket loop'unu çökertiyor.
**Çözüm:** try-except ile hatayı yakala ve `continue` ile devam et.
**Test:**
```python
# tests/test_websocket_armor.py
import pytest
from unittest.mock import patch

@pytest.mark.asyncio
async def test_websocket_continues_on_error():
    """update_live_prices hata verse bile WebSocket devam etmeli"""
    from core.exchange import exchange_manager
    
    # 1. update_live_prices'i exception ile mock'la
    with patch.object(
        exchange_manager.paper_engine,
        'update_live_prices',
        side_effect=Exception("Test Error")
    ):
        # 2. WebSocket loop'u başlat
        task = asyncio.create_task(
            exchange_manager.watch_ticker_loop("BTC/USDT")
        )
        
        # 3. 5 saniye bekle
        await asyncio.sleep(5)
        
        # 4. Loop'un hala çalıştığını doğrula
        assert not task.done(), "WebSocket crashed on error!"
        
        # 5. Console'da "[WEBSOCKET ZIRHI] hata" log'u kontrol et
        task.cancel()
```

---

### 4. Real-time UI Sync 📊
**Sorun:** Pozisyon kapandıktan sonra open_positions güncellenmiyor.
**Çözüm:** Her close'dan SONRA `open_positions = list(legacy_positions)`.
**Test:**
```python
# tests/test_ui_sync.py
import pytest

@pytest.mark.asyncio
async def test_open_positions_sync_after_close():
    """Pozisyon kapandıktan sonra UI anında güncellenmeli"""
    from core.paper import paper_engine
    
    # 1. Pozisyon aç
    await paper_engine.position_manager.open_position(
        bot_id="SOL_TEST_1",
        symbol="SOL/USDT",
        direction="LONG",
        entry_price=100.0,
        size=100.0,
        leverage=10
    )
    
    # 2. open_positions'un güncellendiğini doğrula
    assert len(paper_engine.open_positions) == 1
    
    # 3. Pozisyonu kapat
    await paper_engine.close_position("SOL_TEST_1", 99.0, "STOP_LOSS")
    
    # 4. open_positions'un ANINDA güncellendiğini doğrula
    assert len(paper_engine.open_positions) == 0, "UI sync failed!"
    
    # 5. Console'da "Open positions senkronize edildi: 0 pozisyon" log'u kontrol et
```

---

### 5. Cache-Busting API 🔄
**Sorun:** Browser dashboard metrics API'sini cache'liyor.
**Çözüm:** `?_t=timestamp` parametresi + no-cache headers.
**Test:**
```python
# tests/test_api_cache_busting.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_dashboard_metrics_no_cache():
    """Dashboard metrics API cache yapmamalı"""
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # 1. İki farklı timestamp ile çağır
        response1 = await client.get("/api/v1/dashboard-metrics?_t=1000")
        response2 = await client.get("/api/v1/dashboard-metrics?_t=2000")
        
        # 2. Cache-Control header'larını kontrol et
        assert response1.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
        assert response1.headers["Pragma"] == "no-cache"
        assert response1.headers["Expires"] == "0"
        
        # 3. Response'ların farklı olduğunu doğrula (timestamp değişti)
        assert response1.json() != response2.json() or \
               response1.elapsed.total_seconds() != response2.elapsed.total_seconds()
```

---

## 🧪 TEST ÇALIŞTIRMA:

```bash
# 1. Test bağımlılıklarını yükle
pip install pytest pytest-asyncio pytest-mock httpx

# 2. Testleri çalıştır
pytest tests/test_double_close.py -v
pytest tests/test_zombie_position.py -v
pytest tests/test_websocket_armor.py -v
pytest tests/test_ui_sync.py -v
pytest tests/test_api_cache_busting.py -v

# 3. Tüm testleri çalıştır
pytest tests/ -v --tb=short
```

---

## ✅ BAŞARI KRİTERLERİ:

- ✅ **Double-Close Testi:** 1 pozisyon → 1 trade (0 duplicate)
- ✅ **Zombie Testi:** is_closing = False (0 zombie)
- ✅ **WebSocket Testi:** 5 saniye sonra hala çalışıyor (0 crash)
- ✅ **UI Sync Testi:** close'dan sonra 0 pozisyon (0 stale data)
- ✅ **Cache Testi:** no-cache headers present (0 browser cache)

---

**TÜM TESTLER GEÇMELİDİR!** ❌ 1 bile failure kabul edilemez.
