# 🔍 Event Tracer - Sistem Röntgeni

**Son Güncelleme:** Mart 2026  
**Durum:** ✅ Production Ready  
**Kategori:** Diagnostics

---

## 🎯 Genel Bakış

**Event Tracer**, Event-Driven Architecture'da modüller arası iletişimi izlemek ve debug etmek için geliştirilmiş bir diagnostik aracıdır.

### **Ne İşe Yarar?**

- ✅ Tüm event'leri gerçek zamanlı izler
- ✅ Renkli terminal çıktısı üretir
- ✅ Event akış istatistikleri sunar
- ✅ Kopuk kablolaları (broken pipes) tespit eder
- ✅ Event storm'ları analiz eder

---

## 🚀 Kullanım

### **1. Otomatik Başlatma (main.py)**

Event Tracer, `main.py` içinde otomatik olarak başlatılır:

```python
# main.py içinde
from core.diagnostics.event_tracer import start_event_tracer

# Bot başlatıldığında otomatik aktif olur
```

**Terminal Çıktısı:**
```
🔍 EVENT TRACER BAŞLATILIYOR...
   Sistem röntgeni aktif - Tüm event'ler izleniyor
   Renkli terminal çıktısı için bekleyin...

✅ Event Tracer aktif
```

---

### **2. Manuel Kullanım**

```python
from core.diagnostics.event_tracer import EventTracer

# Tracer oluştur
tracer = EventTracer(enabled=True, show_payload=True)

# Başlat
await tracer.start()

# ... sistem çalışır ...

# Durdur ve istatistikleri göster
await tracer.stop()
```

---

## 📊 Örnek Çıktılar

### **Bot Event:**
```
[19:04:56.123] [BOT] 🤖 bot.started | symbol: BTC/USDT | strategy_id: trend_master | timeframe: 1m (from: bot_manager)
```

### **Signal Event:**
```
[19:04:57.456] [SIGNAL] 📊 signal.generated | symbol: BTC/USDT | signal: 2 | price: 50000.00 (from: exchange_manager)
```

### **ML Event:**
```
[19:04:58.789] [ML] 🧠 ml.prediction | symbol: BTC/USDT | recommendation: LONG | confidence: 0.85 (from: ml_service)
```

### **Position Event:**
```
[19:05:00.012] [POSITION] 💼 position.opened | symbol: BTC/USDT | direction: LONG | entry_price: 50000.00 | size: 0.1 (from: position_manager)
```

### **Data Event:**
```
[19:05:01.345] [DATA] 📦 data.download_started | symbol: BTC/USDT | timeframe: 1m | start_date: 2024-01-01 (from: data_service)
```

---

## 🎨 Renk Kodları

| Kategori | Renk | Emoji |
|----------|------|-------|
| **BOT** | 🟢 Yeşil | 🤖 |
| **SIGNAL** | 🔵 Mavi | 📊 |
| **POSITION** | 🔷 Cyan | 💼 |
| **ML** | 🟣 Magenta | 🧠 |
| **DATA** | 🟡 Sarı | 📦 |
| **RISK** | 🔴 Kırmızı | ⚠️ |
| **TRADE** | ⚪ Beyaz | 💰 |
| **SYSTEM** | ⚫ Gri | ⚙️ |

---

## 📈 İstatistikler

**Bot kapatıldığında (CTRL+C) otomatik gösterilir:**

```
======================================================================
📊 EVENT İSTATİSTİKLERİ
======================================================================
⏱️  Çalışma Süresi: 0:15:30.456789
📈 Toplam Event: 1234
----------------------------------------------------------------------
SIGNAL       | ████████████████░░░░ |   456 ( 37.0%)
POSITION     | ██████████░░░░░░░░░░ |   312 ( 25.3%)
ML           | ████████░░░░░░░░░░░░ |   234 ( 19.0%)
BOT          | ██████░░░░░░░░░░░░░░ |   156 ( 12.6%)
DATA         | ████░░░░░░░░░░░░░░░░ |    76 (  6.2%)
----------------------------------------------------------------------
```

---

## 🔧 Konfigürasyon

### **Event Tracer Ayarları:**

```python
tracer = EventTracer(
    enabled=True,        # Tracer aktif mi?
    show_payload=True    # Payload detayları gösterilsin mi?
)
```

### **Payload Filtreleme:**

Tracer, payload'daki önemli alanları otomatik filtreler:
- `symbol`, `bot_id`, `strategy_id`
- `signal`, `recommendation`, `confidence`
- `entry_price`, `exit_price`, `pnl`
- `status`, `progress`, `message`

**Örnek:**
```
[19:04:58.789] [ML] 🧠 ml.prediction | symbol: BTC/USDT | recommendation: LONG | confidence: 0.85
```

---

## 🚨 Debug Senaryoları

### **Senaryo 1: Event Fırlatılmıyor**

**Sorun:** Bot başladı ama signal event'i yok

**Terminal:**
```
[19:04:56.123] [BOT] 🤖 bot.started | symbol: BTC/USDT
[19:04:57.456] [SIGNAL] 📊 signal.generated | symbol: BTC/USDT  # ✅ Event var
[19:04:58.789] [ML] 🧠 ml.prediction | symbol: BTC/USDT  # ✅ Event var
# ❌ position.opened event'i YOK!
```

**Teşhis:** PositionManager event'i duymuyor veya fırlatmıyor

**Çözüm:**
1. `core/trading/position_manager.py` içinde `PositionOpenedEvent` fırlatılıyor mu kontrol et
2. Event Bus subscription doğru mu kontrol et

---

### **Senaryo 2: Event Storm**

**Sorun:** Çok fazla event, sistem yavaşladı

**Terminal:**
```
📊 EVENT İSTATİSTİKLERİ
Toplam Event: 50000 (15 dakikada)
SIGNAL       | ████████████████████ | 45000 (90.0%)  # ❌ Çok fazla!
```

**Teşhis:** Her mumda çok fazla signal üretiliyor

**Çözüm:**
1. Strateji filter'larını sıkılaştır
2. HTF filter ekle
3. Signal debounce ekle

---

### **Senaryo 3: Kopuk Event Flow**

**Sorun:** ML prediction var ama position açılmıyor

**Terminal:**
```
[19:04:58.789] [ML] 🧠 ml.prediction | symbol: BTC/USDT | recommendation: LONG
# ❌ signal.confirmed event'i YOK!
# ❌ position.opened event'i YOK!
```

**Teşhis:** Confluence mekanizması ML recommendation'ı reddediyor

**Çözüm:**
1. `core/paper.py` içinde `on_signal_generated` handler'ını kontrol et
2. Confluence filter'larını gevşet
3. ML confidence threshold'u düşür

---

## 📋 Event Kategorileri

### **BOT Events:**
- `bot.started` - Bot başlatıldı
- `bot.stopped` - Bot durduruldu
- `bot.resumed` - Bot devam ettirildi
- `bot.removed` - Bot silindi
- `bot.error` - Bot hatası

### **SIGNAL Events:**
- `signal.generated` - Strateji sinyali üretildi
- `signal.confirmed` - Confluence onaylandı
- `signal.rejected` - Sinyal reddedildi

### **POSITION Events:**
- `position.opened` - Pozisyon açıldı
- `position.closed` - Pozisyon kapatıldı
- `position.updated` - Pozisyon güncellendi (trailing stop)
- `position.liquidated` - Pozisyon likide edildi

### **ML Events:**
- `ml.training_started` - ML eğitimi başladı
- `ml.training_progress` - Eğitim ilerlemesi
- `ml.training_completed` - Eğitim tamamlandı
- `ml.prediction` - ML tahmini

### **DATA Events:**
- `data.download_started` - Veri indirme başladı
- `data.download_progress` - İndirme ilerlemesi
- `data.download_completed` - İndirme tamamlandı
- `candle.closed` - Mum kapandı

### **RISK Events:**
- `risk.killswitch_activated` - Kill switch aktif
- `risk.limit_breached` - Risk limiti aşıldı
- `risk.margin_call` - Marjin çağrısı

### **TRADE Events:**
- `trade.recorded` - İşlem kaydedildi

### **SYSTEM Events:**
- `system.started` - Sistem başlatıldı
- `system.shutdown` - Sistem kapatılıyor
- `system.health_check` - Sağlık kontrolü

---

## 🛠️ API

### **EventTracer Methods:**

```python
# Başlat
await tracer.start()

# Durdur
await tracer.stop()

# İstatistik al
stats = tracer.get_stats()
# Returns: {
#     'running': True,
#     'start_time': '2026-03-09T19:04:56',
#     'total_events': 1234,
#     'by_category': {'signal': 456, 'position': 312, ...}
# }
```

### **Global Instance:**

```python
from core.diagnostics.event_tracer import event_tracer

# Mevcut tracer'a eriş
stats = event_tracer.get_stats()
```

---

## ⚠️ Performans

**CPU Kullanımı:** <%1 (idle)  
**Bellek:** ~5MB  
**Event Overhead:** ~0.1ms/event

**Not:** Production'da `show_payload=False` yaparak performansı artırabilirsiniz.

---

## 📚 İlgili Dokümanlar

- **Event-Driven Architecture:** `architecture/event_driven_architecture.md`
- **Event Bus:** `shared/events/event_bus.py`
- **Event Definitions:** `shared/events/events.py`

---

*Event Tracer, Event-Driven Architecture debug sürecini kolaylaştırmak için geliştirilmiştir.*  
*Son güncelleme: Mart 2026*
