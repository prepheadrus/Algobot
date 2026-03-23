# CryptoAlgoBot v4.1.0 - Uygulama Mimarisi ve Kullanım Raporu

Bu rapor, CryptoAlgoBot'un sistem mimarisini, çalışma prensiplerini ve son kullanıcının sistemi kurulumundan canlı kullanıma kadar olan sürecini detaylıca açıklamaktadır. Proje, Python tabanlı olay-güdümlü (Event-Driven) bir algoritmik kripto para ticaret botudur. İçerisinde risk yönetimi, makine öğrenmesi destekli tahmin, ve çok zamanlı grafik analizi modülleri bulunur.

---

## 🏛 Sistem Mimarisi (Architecture)

CryptoAlgoBot modüler ve "Clean Architecture" prensipleri göz önünde bulundurularak 5 ana katmandan oluşmaktadır:

### 1. Veri Sağlayıcı Katmanı (Data Provider Layer)
- **Modül:** `core/exchange.py`
- Merkezi Kripto Para Borsasıyla (şu anda Binance) `ccxt` kütüphanesi kullanılarak API iletişimi sağlanır.
- Seçili kripto para çiftlerinin (örn: BTC/USDT) mum (OHLCV) verilerini periyodik olarak, Asynchronous Poller (Asenkron Döngü) aracılığıyla çeker. Limit aşımlarından kaçınmak için hız kontrol mekanizmaları (Rate Limit Protection) bulunur.

### 2. Özellik Çıkarımı Katmanı (Feature Engineering Layer)
- **Modül:** `data/indicators.py`
- Çekilen ham zaman serisi mum verileri teknik göstergelerle zenginleştirilir.
- `pandas_ta` standart indikatörleri hesaplarken; Koncorde, Kalman Filtresi gibi gelişmiş ve spesifik göstergeler özel geliştirilmiş algoritmalarla hesaplanır ve asıl veriye özellik (feature) sütunları olarak eklenir.

### 3. Teknik Karar Katmanı (Strategy Core)
- **Modül:** `strategy/`
- Botun ticaret algoritmalarının temel iş mantığı bu dizinde izole edilmiştir.
- Trend Master, Golden Combo, Scalper Ninja vb. gibi stratejiler teknik indikatörlerin ürettiği matematiksel değerleri alıp kendi kural setlerinden geçirir.
- Her strateji yalnızca `0 (SAT)`, `1 (BEKLE)` veya `2 (AL)` sinyalleri üretir.

### 4. Yapay Zeka ve Simülasyon Katmanı (ML Inference & Execution Engine)
- **Modüller:** `api/server.py`, `core/paper.py`, `ml/`
- **Yapay Zeka (ML Entegrasyonu):** XGBoost ve Random Forest gibi gelişmiş Ensemble Modeller kullanılarak geçmiş fiyat ve gösterge verilerinden tahmin skoru ve yönü (0, 1, 2) türetilir.
- **Konfluans (Confluence):** Eğer teknik stratejiden gelen "AL (2)" sinyali, makine öğrenmesi modelinden gelen "AL" tahmini ve yüksek "Güven Skoru" (Örn: %65+) ile uyuşuyorsa emir onaylanır.
- **Paper Trader / Risk Engine:** Onaylanan emir, komisyon, kayma (slippage), max bakiye, dinamik kaldıraç, dinamik ATR-tabanlı iz süren stop (Trailing Stop) gibi gerçek piyasa koşullarını simüle eden sistemlerden geçerek veritabanına ya da borsaya iletilir.
- Ayrıca `Circuit Breaker` (Devre Kesici) ve peş peşe zarar durdurucu (Kill Switch) mekanizmaları API sorunlarında veya sert kayıplarda botu korur.

### 5. Sunum Katmanı (Frontend - UI)
- **Modül:** `frontend/`
- HTML, JS ve CSS kullanılarak hazırlanmış modern ve TradingView Lightweight Charts entegreli bir gösterge panelidir (Dashboard).
- Grafik üzerinden indikatörlerin, açık/kapalı işlemlerin, bakiye hareketlerinin takip edilebileceği ve botun konfigürasyonunun yapabileceği kullanıcı etkileşim noktasıdır.

---

## 🔄 Temel Çalışma Döngüsü (Workflow)

Sistemin kalbi bir "Event Bus" (Olay Veriyolu - Pub/Sub) çevresinde atar ve şu akışı izler:

1. **Veri Toplama:** Bot, Binance'dan ham OHLCV (Açılış, Yüksek, Düşük, Kapanış, Hacim) verisini alır.
2. **Hesaplama:** `indicators.py` veriyi alıp MACD, RSI, ADX, VIX, Koncorde gibi onlarca indikatör ile zenginleştirir.
3. **Tahmin:** Eğitilmiş olan yapay zeka (ML) modeli bu güncel göstergeleri okuyarak `Yön` tahmini yapar ve `Güven Skoru` oluşturur.
4. **Strateji Kural Onayı:** Aktif edilen stratejinin kural motoru devreye girer.
5. **Konfluans (Çakışma Kontrolü):** Hem stratejiden hem de yapay zekadan `AL` sinyali geldiyse emir aşamasına geçilir.
6. **Risk ve İcra (Execution):**
   - Konum boyutu hesaplanır (örn: Sermayenin %1'i).
   - ATR değerine göre dinamik olarak Stop-Loss (Zarar Durdur) belirlenir.
   - Komisyon / slippage (kayma) hesaba katılır.
   - Kağıt ticareti (Paper Trading) veya canlı ticaret moduna göre işlem veritabanına kaydedilir veya borsaya gönderilir.
7. **Raporlama:** Uygulama arayüzüne WebSocket (veya API) aracılığıyla gerçek zamanlı güncelleme iletilir.

---

## 💻 Kullanıcı Rehberi (Adım Adım Kullanım)

Bir kullanıcının (veya yöneticinin) botu çalıştırmak için izlemesi gereken adımlar:

### 1. Sistem Gereksinimleri ve Kurulum
- **Önkoşullar:** Python 3.10+, Git, minimum 4GB RAM.
- **Klonlama:** `git clone https://github.com/prepheadrus/Crypto_Automat.git` ile proje dizine çekilir.
- **Kurulum:** Windows için `setup.bat`, Linux/Ubuntu için `./setup.sh` çalıştırılarak sanal ortam (venv) oluşturulur ve gereksinimler (`requirements.txt`) otomatik yüklenir.

### 2. Yapılandırma (Configuration)
- **API Anahtarları (`.env`):** Canlı işlemler için Binance API Key ve Secret değerleri `.env` dosyasına (örnek dosyadan kopyalanarak) girilmelidir. Kağıt üzerinde testler (Paper Trading) için bu adım zorunlu değildir.
- **Sistem Ayarları (`config.yaml`):** Risk yüzdesi, kaldıraç üst limitleri, makine öğrenmesi eşiği (confidence threshold) ve hata payları bu dosyadan ayarlanabilir.

### 3. Botu Başlatma
- İşletim sistemine uygun olarak terminal üzerinden sanal ortam (venv) aktif edilir.
- `python main.py` (veya `python3 main.py`) çalıştırılarak sunucu başlatılır.
- Hızlı başlatma esnasında `Parquet Data Lake` mekanizması çalışarak geçmiş verileri çok hızlı şekilde (Snappy Compression ile) hafızaya yükler.
- FastApi sunucusu `http://localhost:3000` portundan hizmet vermeye başlar.

### 4. Gösterge Paneli (Dashboard) Kullanımı
- Tarayıcı üzerinden `http://localhost:3000` adresine girilir.

**Arayüzdeki Temel Modüller:**
- **Veri Laboratuvarı (Data Lab):** Modelin çalışması için borsadan geçmiş veriler (örn: 10,000 mum) indirilir.
- **Makine Öğrenmesi Yönetimi:** İndirilen veriler kullanılarak seçili coin için (örn: BTC/USDT) yapay zeka modeli (XGBoost) eğitilir.
- **Bot Yönetimi:** İstenilen parite, zaman dilimi ve bir strateji (Örn: TrendMaster Pro) seçilerek bot "Başlat" butonuna tıklanarak aktif edilir.
- **Aktif Stratejiler ve İşlem Geçmişi:** Açık olan pozisyonların (PnL) kâr/zarar durumları, botun ne zaman alım/satım yaptığı anlık takip edilir. Sistemdeki hata günlüğü (Loglar) ve sağlık durumu (`/api/v1/health`) da arayüzden yönetilebilir.

## Öne Çıkan Özellikler ve Güvenlik (Features & Reliability)
- **Circuit Breaker (Devre Kesici):** Borsa API'sine erişilemediğinde sistemi askıya alır, tekrar düzelince güvenli bağlantı sağlar.
- **Kill Switch (Ölüm Anahtarı):** Arka arkaya alınan belirli sayıda (örn: 5) zararlı işlem sonrasında sistemi dondurarak bakiyeyi korur.
- **Graceful Shutdown (Güvenli Kapatma):** Bot kapatıldığında anlık açık pozisyonları veritabanına güvenle yedekler ve açık işlemlerde veri kaybını önler.
- **Auto-Regularization:** Makine öğreniminde aşırı öğrenmeyi (Overfitting) engellemek için verinin boyutuna göre otomatik regülarizasyon (L1, L2 parametreleri) yapar.
- **WFO (Walk-Forward Optimization):** Botun belirli zaman aralıklarıyla parametrelerini optimize edip kendi kendini güncellemesini (haftalık oto-kalibrasyon) sağlar.

---

*Bu rapor, mevcut projenin kaynak kodları, README, TASKS.md ve mimari dokümantasyonu incelenerek hazırlanmıştır. CryptoAlgoBot, modüler yapısı sayesinde yeni stratejiler, yeni göstergeler veya farklı borsalar entegre edilmeye çok açıktır.*