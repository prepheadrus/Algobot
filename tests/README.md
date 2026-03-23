# 🧪 CryptoAlgoBot - Test Suite

Uçtan Uca (E2E) testler, birim testleri ve entegrasyon testleri.

---

## 📦 Kurulum

### 1. Test Bağımlılıklarını Yükle

```bash
cd "f:\Crypto Bot"
pip install -r requirements-test.txt
```

### 2. Test Klasörü Yapısı

```
tests/
├── conftest.py              # Pytest fixtures & mocks
├── test_double_close.py     # Double-close race condition tests
├── test_zombie_position.py  # Zombie position prevention tests
├── test_websocket_armor.py  # WebSocket resilience tests
├── test_ui_sync.py          # UI synchronization tests
└── test_api_cache_busting.py # API cache-busting tests
```

---

## 🚀 Test Çalıştırma

### Tüm Testleri Çalıştır

```bash
pytest tests/ -v --tb=short
```

### Tek Bir Test Dosyası

```bash
# Double-close testleri
pytest tests/test_double_close.py -v

# Zombie position testleri
pytest tests/test_zombie_position.py -v

# WebSocket armor testleri
pytest tests/test_websocket_armor.py -v

# UI sync testleri
pytest tests/test_ui_sync.py -v

# API cache-busting testleri
pytest tests/test_api_cache_busting.py -v
```

### Tek Bir Test Fonksiyonu

```bash
pytest tests/test_double_close.py::test_no_duplicate_position_close -v
pytest tests/test_zombie_position.py::test_zombie_prevention_on_db_error -v
```

### Coverage Raporu

```bash
# Code coverage ile
pytest tests/ -v --cov=core --cov=api --cov=frontend --cov-report=html

# HTML raporu görüntüle
start htmlcov/index.html
```

### Parallel Test Execution

```bash
# 4 worker ile paralel çalıştır
pytest tests/ -v -n 4
```

---

## 📋 Test Senaryoları

### 1. Double-Close Race Condition ⚠️

**Test:** `tests/test_double_close.py`

**Amaç:** Aynı pozisyonun aynı anda 2 kez kapatılmadığını kanıtla.

**Senaryolar:**
- ✅ `test_no_duplicate_position_close` - 2 çağrı → 1 trade
- ✅ `test_closed_bot_ids_prevents_second_close` - closed_bot_ids set kontrolü
- ✅ `test_concurrent_close_attempts` - 3 paralel çağrı → 1 trade

**Beklenen Sonuç:**
```
✅ Double-close prevention successful: 1 trade(s) recorded
✅ closed_bot_ids prevention successful: 1 close(s)
✅ Concurrent close stress test passed: 1 trade from 3 calls
```

---

### 2. Zombie Position Prevention 🧟

**Test:** `tests/test_zombie_position.py`

**Amaç:** Kapatma başarısız olursa is_closing kilidinin sıfırlandığını kanıtla.

**Senaryolar:**
- ✅ `test_zombie_prevention_on_db_error` - DB hatası → kilit sıfırla
- ✅ `test_zombie_prevention_on_remove_error` - Remove hatası → kilit sıfırla
- ✅ `test_retry_after_zombie_unlock` - Kilit sıfırlandı → Tekrar dene
- ✅ `test_finally_block_resets_lock` - finally bloğu → kilit sıfırla

**Beklenen Sonuç:**
```
✅ Zombie prevention successful: is_closing = False after DB error
✅ Zombie prevention on remove error successful
✅ Retry after unlock test: 2 attempt(s) made
✅ finally block lock reset successful
```

---

### 3. WebSocket Armor 🛡️

**Test:** `tests/test_websocket_armor.py`

**Amaç:** update_live_prices hata verse bile WebSocket akışının devam ettiğini kanıtla.

**Senaryolar:**
- ✅ `test_websocket_continues_on_update_error` - Exception → continue
- ✅ `test_websocket_logs_error_but_continues` - Error log → devam
- ✅ `test_websocket_armor_with_real_exception` - Farklı exception türleri
- ✅ `test_websocket_price_feed_resilience` - 5s continuous errors

**Beklenen Sonuç:**
```
✅ WebSocket armor successful: Loop continues on update error
✅ Error logging test: 5 error(s) logged
✅ WebSocket armor vs AttributeError: PASSED
✅ WebSocket armor vs KeyError: PASSED
✅ WebSocket stress test successful: 5s continuous errors handled
```

---

### 4. Real-time UI Sync 📊

**Test:** `tests/test_ui_sync.py`

**Amaç:** Pozisyon kapandıktan sonra open_positions'un ANINDA güncellendiğini kanıtla.

**Senaryolar:**
- ✅ `test_open_positions_sync_immediately_after_close` - Close → ANINDA sync
- ✅ `test_open_positions_updated_in_update_live_prices` - update_live_prices → sync
- ✅ `test_multiple_positions_sync_after_close` - 3 pozisyon → 1 kapat → 2 kaldı
- ✅ `test_ui_polling_gets_fresh_data` - Polling → güncel veri

**Beklenen Sonuç:**
```
✅ UI sync successful: 0 positions after close
✅ update_live_prices sync successful: price=3050.0
✅ Multiple positions sync successful: 2 remaining
✅ UI polling fresh data test successful
```

---

### 5. Cache-Busting API 🔄

**Test:** `tests/test_api_cache_busting.py`

**Amaç:** Browser'ın dashboard metrics API'sini cache'lemediğini kanıtla.

**Senaryolar:**
- ✅ `test_dashboard_metrics_cache_control_headers` - no-cache headers
- ✅ `test_cache_busting_with_timestamp` - ?_t=timestamp parametresi
- ✅ `test_no_browser_caching` - Tüm no-cache headers
- ✅ `test_api_client_cache_busting_integration` - Frontend integration

**Beklenen Sonuç:**
```
✅ Cache-Control headers correct: no-cache, no-store, must-revalidate
✅ Cache-busting successful: 2 unique timestamps, 2 real API calls
✅ All no-cache headers present: ['Cache-Control', 'Pragma', 'Expires']
✅ API client cache-busting integration successful
```

---

## 🎯 Başarı Kriterleri

### ✅ GEÇMİŞ (PASS) İçin:
- Tüm testler YEŞİL ✅
- 0 FAILURE ❌
- 0 WARNING ⚠️
- Coverage ≥ 80%

### ❌ BAŞARISIZ (FAIL) İçin:
- 1 bile FAILURE → DERHAL DÜZELTME
- Hata mesajını logla
- İlgili kodu düzelt
- Testi tekrar çalıştır

---

## 🐛 Sorun Giderme

### Test Bulunamadı Hatası

```bash
# Test dosyalarının varlığını kontrol et
dir tests\*.py

# conftest.py var mı?
dir tests\conftest.py
```

### Import Hatası

```bash
# Python path'e tests klasörünü ekle
set PYTHONPATH=%PYTHONPATH%;f:\Crypto Bot\tests
pytest tests/ -v
```

### Async Test Hatası

```bash
# pytest-asyncio yüklü mü?
pip show pytest-asyncio

# Değilse yükle
pip install pytest-asyncio
```

### Coverage Raporu Oluşturulmuyor

```bash
# coverage yüklü mü?
pip show coverage

# Değilse yükle
pip install pytest-cov
```

---

## 📊 Test Coverage Hedefleri

| Modül | Hedef | Gerçekçek | Durum |
|-------|-------|---------|-------|
| `core/paper.py` | 90% | TBD | ⏳ |
| `core/trading/position_manager.py` | 90% | TBD | ⏳ |
| `core/exchange.py` | 80% | TBD | ⏳ |
| `api/routers/system.py` | 85% | TBD | ⏳ |
| **TOPLAM** | **85%** | **TBD** | **⏳** |

---

## 🔄 CI/CD Entegrasyonu

### GitHub Actions (Örnek)

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.12
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run tests
      run: |
        pytest tests/ -v --tb=short --cov=core --cov=api
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

---

## 📝 Notlar

1. **Test İzolasyonu:** Her test bağımsız çalışmalı.
2. **Mock Kullanımı:** Gerçek API/DB çağrıları yapma.
3. **Async Testler:** `@pytest.mark.asyncio` kullan.
4. **Fixture'lar:** `conftest.py`'de tanımla.
5. **Coverage:** %85+ hedefle.

---

## 🤝 Katkıda Bulunma

Test eklemek için:

1. `tests/` klasöründe yeni dosya oluştur
2. Test fonksiyonlarını yaz (`test_*` ile başla)
3. Fixture'ları kullan (`conftest.py`)
4. Coverage ile çalıştır
5. Pull Request oluştur

---

**🚀 TEST ALLAH'TAN, ŞÜPHE İNSANDAN!**

Tüm testler geçene kadar dinlenme yok! 💪
