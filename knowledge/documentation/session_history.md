# 📜 CryptoAlgoBot - Geliştirme ve Yardım Dökümanı (04.03.2026)

Bu döküman, 04 Mart 2026 tarihindeki geliştirme oturumunda bota eklenen özelliklerin, teknik mimarinin ve kullanıcı yardım klavuzunun özetidir.

---

## 🚀 1. Veri Laboratuvarı & Görev Yönetimi (Yeni Nesil)

Bu oturumda, botun veri toplama kapasitesi "Görev Yöneticisi" (Task Manager) mantığıyla tamamen yenilenmiştir. Artık bot sadece veri indiren bir araç değil, karmaşık indirme görevlerini organize eden ve kurtarabilen profesyonel bir veri merkezidir.

### ✨ Ana Özellikler:
- **Çoklu İndirme (Multi-Tasking):** Aynı anda birden fazla parite (BTC, ETH, PEPE vb.) için bağımsız indirme görevleri başlatılabilir.
- **Kalıcı Hafıza (Persistence):** Görevler veritabanına kaydedilir. Bot kapansa bile görevler kaybolmaz.
- **Duraklat & Devam Et (Pause/Resume):** İndirme işlemleri istenilen an dondurulabilir ve kaldığı dakikadan itibaren sürdürülebilir.
- **Otomatik Kurtarma (Auto-Recovery):** Bot her açıldığında veritabanındaki yarım kalan görevleri otomatik olarak algılar ve kullanıcı arayüzüne geri yükler.

---

## 🛠️ 2. Mimaride Yapılan Değişiklikler

### 📂 Veritabanı Şeması (`download_tasks` Tablosu)
Görevlerin kalıcı olması için veritabanına yeni bir tablo eklendi:
```sql
CREATE TABLE download_tasks (
    symbol TEXT PRIMARY KEY,       -- Parite adı
    timeframe TEXT,                -- Zaman aralığı (1m, 5m vb.)
    start_date TEXT,               -- Hedef başlangıç tarihi
    market_type TEXT,              -- SPOT veya FUTURES
    status TEXT,                   -- Durum: running, paused, stopped
    current_ts BIGINT,             -- İndirilen en son mumun zaman damgası
    target_start_ms BIGINT         -- Toplam ilerleme hesabı için başlangıç noktası
);
```

### 🔌 Yeni API Endpointleri
| Endpoint | Method | Açıklama |
|----------|--------|-----------|
| `/api/v1/data/active-downloads` | GET | Aktif ve kayıtlı tüm görevleri listeler. |
| `/api/v1/data/toggle-pause` | POST | Bir görevi duraklatır veya devam ettirir. |
| `/api/v1/data/stop-download` | POST | Görevi durdurur ve veritabanına 'stopped' olarak yazar. |
| `/api/v1/data/download-history` | POST | Yeni indirme başlatır veya mevcut olanı kaldığı yerden sürdürür. |

---

## 🧭 3. Kullanıcı Yardım Klavuzu

### 📥 Veri Nasıl İndirilir?
1. **Piyasa Seçimi:** Sol panelden listelenen coinlerden birine tıklayın.
2. **Ayarlar:** Başlangıç tarihini ve zaman aralığını (1m, 1h vb.) seçin.
3. **Başlat:** "🚀 İndirmeyi Başlat" butonuna basın.
4. **Takip:** Üstteki "🚀 Aktif İndirme Görevleri" panelinde indirme durumunu canlı izleyebilirsiniz.

### ⏸️ Duraklatma ve Durdurma Farkı Nedir?
- **Duraklat (Pause):** Görevi anlık olarak dondurur. Bot hafızasında görevi "canlı" tutmaya devam eder. Hızlıca geri başlatmak için uygundur.
- **Durdur (Stop):** Görevi kapatır. Görev artık "durduruldu" (stopped) olarak işaretlenir ve kırmızıya döner. Botu kapatsanız bile listede kalır, daha sonra "🔄 Yeniden Başlat" diyerek kaldığı yerden devam ettirebilirsiniz.

### 🗑️ Görevi Listeden Nasıl Silerim?
Eğer bir pariteyi artık indirmek istemiyorsanız ve listenizde kalmasını istemiyorsanız, görev "durmuş" (stopped) haldeyken çıkan **"🗑️ Temizle"** butonuna basın.

---

## 💡 İpuçları & Uyarılar
- **Borsa Limitleri:** Aynı anda 10'dan fazla parite indirmek borsa tarafında hız limitlerine (Rate Limit) takılmanıza neden olabilir. Bot bunları otomatik yavaşlatır ancak yine de makul sayıda görev tutmanız önerilir.
- **Veri Kalitesi:** "Daha fazla veri = daha iyi yapay zeka". Strateji eğitmeden önce en az 1-2 aylık 1m verisi indirmeniz tavsiye edilir.

---
*CryptoAlgoBot Documentation Team - 2026*
