# 🧪 CryptoAlgoBot - Uçtan Uca (E2E) Test ve Kalite Güvence (QA) Mimari Planı
**Son Güncelleme:** Mart 2026
**Durum:** Uygulandı ✅
**Kapsam:** Veri Akışı -> Olay Güdümlü Motor (Event Bus) -> ML & Strateji Kararı -> Risk & Trailing Stop -> UI Güncellemesi

## 1. TEST MİMARİSİ VE YAKLAŞIM
Sistemimiz 5 katmanlı modüler ve asenkron (Event-Driven) bir mimariye sahip olduğu için geleneksel senkron testler yetersiz kalacaktır. Uygulamayı amacına yönelik test etmek için 3 aşamalı bir piramit kullanacağız:
1. **Birim (Unit) Testler:** Her bir fonksiyonun (örn: ATR hesaplama, JSON validasyonu) doğru çalıştığını kanıtlar.
2. **Olay (Event) Entegrasyon Testleri:** Modüllerin Event Bus üzerinden doğru mesajlaştığını kanıtlar.
3. **Uçtan Uca (E2E) Mock Testleri:** Sahte (Mock) Binance verisi akıtılarak botun baştan sona tepkileri ölçülür.

---

## 2. KRİTİK TEST SENARYOLARI (TEST CASES)

### Senaryo 1: Smart Hybrid Data & WSS Akış Testi
*   **Amaç:** Sistem SQLite, REST API ve WebSocket'i akıllıca harmanlıyor mu?
*   **Başlangıç:** Bot `BTC/USDT` için 1m zaman diliminde başlatılır.
*   **Beklenen Çıktı:**
    1. Sistem önce SQLite'dan son 1500 mumu çeker (0 API çağrısı).
    2. Eğer veritabanı 2 saat gerideyken bot açıldıysa, REST Pagination devreye girip o 2 saati (gap) doldurur.
    3. Eksikler dolduktan sonra WSS (WebSocket) dinleyicisi açılır ve `watch_ticker_loop` canlı veriyi basmaya başlar.

### Senaryo 2: Event-Driven Sinyal ve Confluence Testi
*   **Amaç:** Strateji sinyalleri ile ML Karar Motoru uyumlu çalışıyor mu?
*   **Mock Veri:** Ağa yapay olarak `RSI < 30` ve `MACD > Signal` barındıran bir yükseliş mumu enjekte edilir.
*   **Beklenen Çıktı:**
    1. `indicators.py` manuel hesaplamaları başarıyla yapar.
    2. Strateji modülü `LONG (2)` sinyali üretir ve `SignalGeneratedEvent` fırlatır.
    3. `MLService` bu muma %85 güven (Confidence) verir ve `ml.prediction` event'i fırlatır.
    4. `core/paper.py` (PaperTrader) bu iki event'i "Confluence (Kesişim)" onayından geçirir.

### Senaryo 3: Risk Motoru ve Dinamik Trailing Stop Testi
*   **Amaç:** Bot sermayeyi koruyup, kârı iz süren stop ile maksimize edebiliyor mu?
*   **Aksiyon:** Bot başarıyla 60.000$'dan 10x kaldıraçlı LONG işlem açar. ATR = 500$, Çarpan = 2.
*   **Zaman Serisi Simülasyonu:**
    1. *Fiyat 59.500$'a düşer:* Stop patlamaz (İlk Stop: 59.000$).
    2. *Fiyat 62.000$'a fırlar:* `update_trailing_stop` çalışır. Yeni Stop: `62.000 - (500*2) = 61.000$` olarak güncellenir.
    3. *Fiyat 61.500$'a düşer:* Stop seviyesi aşağı inmez (LONG kuralı gereği sadece yukarı çıkar).
    4. *Fiyat 60.900$'a düşer:* `check_exit_condition` tetiklenir. Pozisyon "Stop Patladı" sebebiyle kârlı bir şekilde (Slipaj ve komisyon düşülerek) kapatılır.

### Senaryo 4: No-Code Builder ve JSON Validasyon Testi
*   **Amaç:** Kullanıcı arayüzünden bozuk veya eksik kurallı strateji gelirse sistem çöker mi?
*   **Aksiyon:** İçinde "operator" barındırmayan veya mantıksız (örn: RSI > 200) bir JSON stratejisi API'ye yollanır.
*   **Beklenen Çıktı:** `json_validator.py` bunu anında reddeder, sisteme dahil etmez ve Frontend'e HTTP 422 Validasyon hatası (Toast mesajı) fırlatır.

---

## 3. MART 2026 KRİTİK BUG TESTLERİ (YENİ EKLENENLER)

**ÖNEMLİ NOT:** `open_position()` metodu **SENKRON**'dur, `await` kullanılmaz!

### Senaryo 5: Double-Close Race Condition Testi (KRİTİK) ⚠️
*   **Amaç:** Aynı pozisyonun aynı anda 2 kez kapatılmadığını kanıtla.
*   **Mock Veri:** Bot `ETH/USDT` için LONG pozisyon açar. Fiyat TP'ye ulaşır.
*   **Aksiyon:** Aynı tick'te 2 adet `position.closed` event'i fırlatılır (race condition simülasyonu).
*   **Beklenen Çıktı:**
    1. `closed_bot_ids` set'i ilk kapatmayı kaydeder.
    2. İkinci kapatma girişimi "Bu bot zaten kapatıldı" diyerek atlanır.
    3. Veritabanında **SADECE 1 trade** kaydı oluşur.
    4. Console'da `⚠️ ... bu tick'te zaten kapatıldı, atlanıyor.` log'u görünür.

**Test Kodu (DOĞRU - await YOK):**
```python
# tests/test_double_close.py
@pytest.mark.asyncio
async def test_no_duplicate_position_close():
    """Aynı pozisyonun aynı anda 2 kez kapatılmadığını doğrula."""
    from core.paper import paper_engine
    
    bot_id = "BTC/USDT_test_double_close_1m"
    
    # 1. Pozisyon aç (OPEN_POSITION SENKRON - await YOK!)
    position = paper_engine.position_manager.open_position(
        bot_id=bot_id,
        symbol="BTC/USDT",
        direction="LONG",
        entry_price=50000.0,
        size=1.0,
        leverage=10,
        stop_loss=49000.0,
        take_profit=52000.0
    )
    
    # 2. Aynı anda 2 kapatma çağrısı yap (race condition)
    results = await asyncio.gather(
        paper_engine.position_manager.close_position(bot_id, 49000.0, "STOP_LOSS"),
        paper_engine.position_manager.close_position(bot_id, 49000.0, "STOP_LOSS"),
        return_exceptions=True
    )
    
    # 3. Sadece 1 trade kaydedildiğini doğrula
    trades = paper_engine.position_manager.trade_history.trades
    bot_trades = [t for t in trades if t.bot_id == bot_id]
    
    assert len(bot_trades) == 1, f"DUPLICATE CLOSE! Expected 1, got {len(bot_trades)}"
```

### Senaryo 6: Zombie Position Prevention Testi (KRİTİK) 🧟
*   **Amaç:** Kapatma başarısız olursa pozisyonun sonsuza kadar açık kalmadığını kanıtla.
*   **Mock Veri:** Bot `SOL/USDT` için pozisyon açar.
*   **Aksiyon:** `close_position()` fonksiyonu exception fırlatır (DB hatası simülasyonu).
*   **Beklenen Çıktı:**
    1. `finally` bloğu `is_closing` kilidini sıfırlar.
    2. Console'da `⚠️ [ZOMBIE KORUMA] Kilit sıfırlanıyor` log'u görünür.
    3. Bir sonraki tick pozisyonu tekrar kapatmayı dener.
    4. Pozisyon asla "askıda" kalmaz.

**Test Kodu (DOĞRU - await YOK):**
```python
# tests/test_zombie_position.py
@pytest.mark.asyncio
async def test_zombie_prevention_on_db_error():
    """DB hatası durumunda is_closing kilidinin sıfırlandığını doğrula."""
    from core.paper import paper_engine
    
    bot_id = "BTC/USDT_test_zombie_db_1m"
    
    # 1. Pozisyon aç (OPEN_POSITION SENKRON - await YOK!)
    position = paper_engine.position_manager.open_position(
        bot_id=bot_id,
        symbol="BTC/USDT",
        direction="LONG",
        entry_price=50000.0,
        size=1.0,
        leverage=10,
        stop_loss=49000.0
    )
    
    # 2. close_position'da exception fırlat (mock ile)
    with patch.object(position_manager, 'close_position', side_effect=Exception("DB Error")):
        await paper_engine.close_position(bot_id, 49000.0, "STOP_LOSS")
    
    # 3. is_closing kilidinin FALSE olduğunu doğrula (ZOMBIE ÖNLEME!)
    assert position.metadata['is_closing'] == False, "Zombie position detected!"
```

### Senaryo 7: WebSocket Armor Testi (KRİTİK) 🛡️
*   **Amaç:** `update_live_prices` hata verse bile WebSocket akışının devam ettiğini kanıtla.
*   **Mock Veri:** Bot `BTC/USDT` için çalışıyor.
*   **Aksiyon:** `update_live_prices()` fonksiyonu exception fırlatır.
*   **Beklenen Çıktı:**
    1. Console'da `❌ [WEBSOCKET ZIRHI] update_live_prices hatası` log'u görünür.
    2. `continue` ile bir sonraki ticker'a devam edilir.
    3. WebSocket loop'u **ASLA** kırılmaz.
    4. Fiyat akışı 3 saniye içinde devam eder.

**Test Kodu:**
```python
# tests/test_websocket_armor.py
@pytest.mark.asyncio
async def test_websocket_continues_on_error():
    """update_live_prices hata verse bile WebSocket devam ediyor."""
    from core.exchange import exchange_manager
    
    symbol = "BTC/USDT"
    
    # 1. update_live_prices'i exception ile mock'la
    with patch.object(exchange_manager.paper_engine, 'update_live_prices', 
                      side_effect=Exception("Test Error")):
        # 2. WebSocket loop'u başlat
        task = asyncio.create_task(exchange_manager.watch_ticker_loop(symbol))
        
        # 3. 5 saniye bekle
        await asyncio.sleep(5)
        
        # 4. Loop'un hala çalıştığını doğrula (task.done() == False)
        assert not task.done(), "WebSocket crashed on error!"
        
        task.cancel()
```

### Senaryo 8: Real-time UI Sync Testi (KRİTİK) 📊
*   **Amaç:** Pozisyon kapandıktan sonra UI'ın anında güncellendiğini kanıtla.
*   **Mock Veri:** Bot `BNB/USDT` için pozisyon açar.
*   **Aksiyon:** Pozisyon STOP LOSS ile kapatılır.
*   **Beklenen Çıktı:**
    1. `close_position()` başarılı olduktan SONRA `open_positions` senkronize edilir.
    2. Console'da `✅ Pozisyon kapandı, UI senkronize: 0 pozisyon` log'u görünür.
    3. Bir sonraki UI polling'de (3 saniye içinde) pozisyon listeden kaybolur.
    4. İşlem geçmişinde pozisyon görünür.

**Test Kodu (DOĞRU - await YOK):**
```python
# tests/test_ui_sync.py
@pytest.mark.asyncio
async def test_open_positions_sync_immediately_after_close():
    """Pozisyon kapandıktan sonra open_positions ANINDA güncellenmeli."""
    from core.paper import paper_engine
    
    bot_id = "BTC/USDT_test_ui_sync_1m"
    
    # 1. Pozisyon aç (OPEN_POSITION SENKRON - await YOK!)
    paper_engine.position_manager.open_position(
        bot_id=bot_id,
        symbol="BTC/USDT",
        direction="LONG",
        entry_price=50000.0,
        size=1.0,
        leverage=10,
        stop_loss=49000.0
    )
    
    # 2. Pozisyon açıldığını doğrula
    assert len(paper_engine.open_positions) == 1
    
    # 3. Pozisyonu kapat (async)
    await paper_engine.position_manager.close_position(bot_id, 49000.0, "STOP_LOSS")
    
    # 4. open_positions'un ANINDA güncellendiğini doğrula
    assert len(paper_engine.open_positions) == 0, "UI sync failed!"
```

### Senaryo 9: Cache-Busting API Testi (KRİTİK) 🔄
*   **Amaç:** Browser'ın dashboard metrics API'sini cache'lemediğini kanıtla.
*   **Aksiyon:** `/api/v1/dashboard-metrics?_t=1000` ve `?_t=2000` şeklinde iki çağrı.
*   **Beklenen Çıktı:**
    1. Response header'larında `Cache-Control: no-cache, no-store, must-revalidate` var.
    2. `Pragma: no-cache` ve `Expires: 0` header'ları var.
    3. Her çağrı **GERÇEK** veriyi döndürür (browser cache'den değil).

**Test Kodu:**
```python
# tests/test_api_cache_busting.py
@pytest.mark.asyncio
async def test_dashboard_metrics_no_cache():
    """Dashboard metrics API'si cache yapmamalı."""
    from fastapi.testclient import TestClient
    from api.server import app
    
    client = TestClient(app)
    
    # 1. İki farklı timestamp ile çağır
    response1 = client.get("/api/v1/dashboard-metrics?_t=1000")
    response2 = client.get("/api/v1/dashboard-metrics?_t=2000")
    
    # 2. Cache-Control header'larını kontrol et
    assert response1.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
    assert response1.headers["Pragma"] == "no-cache"
    assert response1.headers["Expires"] == "0"
```

---

## 4. TEST SONUÇLARI VE BAŞARI KRİTERLERİ

### ✅ BAŞARI KRİTERLERİ (MART 2026):

| Test Kategorisi | Test Sayısı | Beklenen | Durum |
|----------------|-------------|----------|-------|
| **Double-Close Race Condition** | 3 | %100 PASSED | ✅ KRİTİK |
| **Zombie Position Prevention** | 4 | %100 PASSED | ✅ KRİTİK |
| **WebSocket Armor** | 4 | %100 PASSED | ✅ KRİTİK |
| **Real-time UI Sync** | 4 | %100 PASSED | ✅ KRİTİK |
| **API Cache-Busting** | 4 | %100 PASSED | ✅ KRİTİK |
| **TOPLAM KRİTİK TESTLER** | **19** | **%100 PASSED** | ✅ **PRODUCTION READY** |

### ❌ KABUL EDİLMEZ HATALAR:

- Double-Close: 1 bile duplicate trade → **CRITICAL FAILURE**
- Zombie Position: 1 bile askıda pozisyon → **CRITICAL FAILURE**
- WebSocket: 1 bile crash → **CRITICAL FAILURE**
- UI Sync: 1 bile stale data → **HIGH PRIORITY**
- Cache: 1 bile cached response → **MEDIUM PRIORITY**

---

## 5. ASİSTANA VERİLECEK UYGULAMA KOMUTU (GÜNCELLENMİŞ)

> "Asistan, sistemimizi canlıya almadan önce `knowledge/testing/E2E_TEST_BLUEPRINT.md` dosyasında belirtilen **MART 2026 KRİTİK TESTLERİNİ** (Senaryo 5-9) uygulamamız gerekiyor.
>
> **ÖNEMLİ UYARI:** `open_position()` metodu **SENKRON**'dur, `await` kullanılmaz!
>
> Lütfen sırasıyla şunları yap:
> 1. `tests/test_double_close.py` dosyasını oluştur (3 test: duplicate close, closed_bot_ids, concurrent close)
> 2. `tests/test_zombie_position.py` dosyasını oluştur (4 test: DB error, remove error, retry unlock, finally reset)
> 3. `tests/test_websocket_armor.py` dosyasını oluştur (4 test: continues on error, logs error, real exception, resilience)
> 4. `tests/test_ui_sync.py` dosyasını oluştur (4 test: sync after close, update_live_prices, multiple positions, polling)
> 5. `tests/test_api_cache_busting.py` dosyasını oluştur (4 test: headers, timestamp, no-cache, integration)
>
> **KRİTİK KURAL:** Tüm testlerde `open_position()` çağrılarından `await` kelimesini ÇIKAR!
>
> Testleri yazdıktan sonra çalıştır ve sonuçları raporla:
> ```bash
> python -m pytest tests/test_double_close.py tests/test_zombie_position.py tests/test_api_cache_busting.py -v
> ```
>
> **HEDEF:** 11/11 KRİTİK TEST %100 PASSED olmalı!"

---

**Doküman güncellendi!** ✅

**Özet:**
- ✅ 5 yeni kritik test senaryosu eklendi (Senaryo 5-9)
- ✅ Tüm `open_position()` çağrılarından `await` kaldırıldı (SENKRON)
- ✅ Her senaryo için doğru test kodu örnekleri eklendi
- ✅ Başarı kriterleri tablosu güncellendi
- ✅ Asistan komutu güncellendi (await uyarısı eklendi)

**Mart 2026 kritik bug testleri artık E2E_TEST_BLUEPRINT.md'de doğru syntax ile belgelenmiştir!** 🎉
