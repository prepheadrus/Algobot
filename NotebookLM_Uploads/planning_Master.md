# PLANNING BILGI BANKASI
Son Guncelleme: 08/03/2026 22:58

---



## KAYNAK DOSYA: roadmap.md

# Yüksek Başarı Oranlı Ticaret Botu Yol Haritası (Roadmap)

## Aşama 1: Veri Katmanı ve Altyapı
- [ ] Python asenkron proje yapısının başlatılması (`asyncio`).
- [ ] CCXT entegrasyonu ile merkezi borsalara (Binance, BTCTurk, Paribu vb.) bağlantı kurulumu.
- [ ] REST API yerine **WebSocket** ile gerçek zamanlı piyasa/hacim verisi ve emir defteri akışının bağlanması.
- [ ] Veri boru hatlarının (Data pipeline) kurulması: OHLCV, Makro Veriler (DXY, Tahvil, S&P 500, Altın), On-chain Veriler (Balina hareketleri, borsaya giriş-çıkış) ve NLP sentiment verilerinin (Twitter, Haber başlıkları) toplanması.
- [ ] Veri saklama işlemleri için `TimescaleDB` / `InfluxDB` ve limit önleyici olarak `Redis` kurulumu.

## Aşama 2: Veri Mühendisliği ve Özellik Çıkarımı (Feature Engineering)
- [ ] Teknik indikatörlerin hesaplanması: SMA/EMA, RSI, MACD, Bollinger, ATR, VWAP, Supertrend vb.
- [ ] **Kesirli Fark Alma (Fractional Differentiation):** Zaman serisi verilerinde finansal hafıza geçmişini silmeden durağanlaştırma elde edilmesi.
- [ ] **Üçlü Bariyer Yöntemi (Triple Barrier Method):** Makine öğrenmesi etiketlemesi için kar-al, zarar-kes ve zaman-aşımı üçgeninin kodlanması.

## Aşama 3: Makine Öğrenimi (ML) Modelleri ve Karar Motoru
- [ ] Derin öğrenme tahmin modellerinin inşası: Çok girdili `LSTM` & `Transformers` (Fiyat projeksiyonu ve volatilite tahminini birleştirerek).
- [ ] **Kombinatoryal Füzyon Analizi (CFA):** `XGBoost`, `Random Forest` ve derin öğrenme modellerinin sinyallerini harmanlayan ve doğruluk payını arttıran (Model Ensembling) ana yapının inşası.
- [ ] **Meta-RL Döngüsü:** Sharpe, Max-Drawdown verilerine göre sistemi anlık değerlendiren Aktör, Yargıç ve Meta-Yargıç kapalı döngüsünün testlere adaptasyonu.

## Aşama 4: Strateji Konfluans (Teyit) Modülleri
- [ ] **Momentum ve Trend Takip Modülü:** MACD, VWAP, RSI filtreli.
- [ ] **Etkinlik Odaklı (Event-Driven) Modül:** Ekonomik göstergeler öncesi (CPI vb.) grid mantığını durduran ve ani ivmeyi yakalayan breakout takip algoritması.
- [ ] **Arbitraj / Çift Ticareti (Pair Trading):** Varlık (örn. ETH/BTC) korelasyonunun bozulmasında tarihsel spread analizi (Z-Score) ile uzun ve kısa (Long/Short) eşleştirme sistemi.
- [ ] **Dinamik Grid Modülü:** Yatayda mükemmel, sert trendde (VIX/ATR yükselince) duraklamaya geçen aralık belirleyici sistem.

## Aşama 5: Risk Yönetimi (Sermaye Koruma Modülü)
- [ ] Formülize edilmiş dinamik Pozisyon Büyüklüğü: `Sermaye x %Risk / Stop Mesafesi` (Max risk %1-%2).
- [ ] Kademeli Take-Profit (örn: %33'ü %5 karda kapat) ve Trailing Stop yapısı kodlaması.
- [ ] Akıllı kaldıraç hesaplama: Botun anlık güven (Confidence) skoruna göre statik 1x ile maksimum 3x arası değişen kaldıraç ataması.

## Aşama 6: Performans Testi ve Canlıya Geçiş (Deployment)
- [ ] **Walk-Forward Optimization (WFO):** Algorithmanın çeşitli rastgele veya dönem dönem sıyrılmış verilerde Out-of-Sample başarı istikrarının simülasyonu.
- [ ] Dry-Run (Kağıt Üzerinde Ticaret): Parametreleri bozan kayma (Slippage) ve gerçek API hızlarıyla canlı cüzdandan harcamayan sahte işlem protokolu testleri.
- [ ] Canlı ortamda Deployment (Docker üzerinden) ve ping, konfidens, rate limit gecikmesini detaylı saniye saniye izleyen Grafana panelinin başlatılması.


---


## KAYNAK DOSYA: tasks.md

# 📝 Crypto Bot Geliştirme Görevleri (Task Tracker)

Bu dosya sistemin mimarisine, modülerliğine ve kârlılığına yönelik yapılması planlanan önerileri, devam eden işlemleri ve tamamlanmış hedefleri takip etmek için oluşturulmuştur. Her yeni fikir buraya eklenmeli, başlananlar işaretlenmelidir.

## 🎯 Öncelikli Hedefler (Kârlılık ve Optimizasyon)

- [x] **Dinamik "Trailing Stop" (İzleyen Stop) Mekanizması:**
  - *Açıklama:* Güçlü trendlerde kârı maksimize etmek için stop seviyesinin fiyatla birlikte ATR kullanılarak yukarı/aşağı taşınması süreci.
  - *Dosya:* `core/paper.py`

- [x] **Multi-Timeframe (Çoklu Zaman Dilimi) Teyidi:**
  - *Açıklama:* 15 dakikalık grafikte işlem açmadan önce 1 saatlik ve 4 saatlik ana trend yönüne bakılması ve ters işlem açılmasının (Konfluans dışı işlemlerin) önlenmesi.
  - *Dosya:* `core/exchange.py` ve `core/paper.py`

- [x] **Market Regime (Piyasa Rejimi) Tespiti:**
  - *Açıklama:* Piyasanın "Güçlü Trend" mi yoksa "Yatay/Testere" piyasa boyutunda mı olduğunu hesaplayarak algoritmaları bu sonuca göre otomatik devreye alan dedektör.
  - *Dosya:* `core/detector.py` ve dashboard entegrasyonu.

## 🧩 Mimari ve Modülerlik Geliştirmeleri

- [ ] **İndikatör Fabrikasının Parçalanması (Pipeline Modeli):**
  - *Açıklama:* Tüm göstergeleri hesaplayan tek yapıdaki (`indicators.py`) kodların Momentum, Trend, Hacim şeklinde klasörlere ayrılması ve performans artışı için istenirse sadece belirli sepetlerin aktif edilebilmesi.

- [ ] **Olay Güdümlü (Event-Driven) Sisteme / WebSockets'a Geçiş:**
  - *Açıklama:* Zamanlayıcı (Poller) bağımlı `exchange.py` sisteminin milisaniyelik anlık "Tick" bildirimleri alabileceği WebSocket asenkron mimariye kavuşması (Slippage'i sıfırlar).

- [ ] **Kodsuz (No-Code) Strateji Oluşturucu Arayüzü:**
  - *Açıklama:* Yeni JSON destekli dinamik sınıflarla, kullanıcıların kod bilmeden Dashboard menüleri üzerinden "RSI < 30 ve SMA Kesimi" kurallı bot yapabilmesi.

## ✅ Tamamlanan İşlemler
- [x] **Yapay Zeka ve Strateji Entegrasyonu:** XGBoost model sonuçlarıyla, birbirinden bağımsız çalışan Strateji sonuçları (`manager.py`) örtüştürüldü.
- [x] **Golden Combo (Kitap Şablonu):** Hacim, Trend ve Yön mantığını (MACD, ADX, OBV, EMA) tamamen harmanlayan modüler konsept geliştirildi ve eklendi.
- [x] **Hiyerarşik Gösterim Modeli (Görsel Simülasyon):** Arayüz karmaşası çözüldü. Sinyaller sadece noktacık olarak bırakılıp dev oklar yalnızca "Gerçek Paper Trade İşlemlerinde" çıktı olarak belirginleştirildi.
- [x] **Bilgi Bankası (Knowledge Base) Oluşturulması:** Proje geneli 5 temel analiz başlığı (`architecture/`, `strategies/`, `trading_engine/`, vb.) altında belgelendirilerek tam referans noktası çıkarıldı.
- [x] **Dinamik Hassasiyet (Decimal Precision) Motoru:** ALT-Coinlerde yaşanan 0 lı kuruş ondalık okuma hatalarına karşı hem tooltipe hem de eksene "Precision Engine" entegre edildi.
- [x] **Performans (KPI) Dashboard Revizyonu:** Paper Trading Performans listesi; kurumsal borsa platformu kalitesinde, renkli ikonlara sahip 6 parçalı fütüristik dev kart tasarımına dönüştürüldü.
- [x] **Gelişmiş Strateji ve Başarı Raporu:** Arayüze "Performans Raporları" isminde yeni bir sekme eklenerek, botların geçmiş ve aktif işlemlerdeki win rate, Kâr/Zarar ve parite bazlı karnelerini analiz eden ve Yapay Zeka destekli tavsiyeler üreten bir "Röntgen" sayfası entegre edildi.
- [x] **Senkronize Uyuşmazlık Avcısı Stratejisi:** Yazarın formüllerinden ilham alınarak; Demand Index, Ultimate Oscillator, ADX ve PSAR indikatörlerinden oluşan 5. stratejimiz oluşturuldu ve simülasyon motoruna entegre edildi.
- [x] **Nicel (Quant) KNN Tahmin ve ATR Kalkanı Stratejisi:** İki popüler kaynağın ("151 Trading Strategies" ve "Teknik Analiz" kitaplarının) karması olan, makine öğrenmesi destekli (K-En Yakın Komşu Modeli) 6. Strateji geliştirildi ve sisteme eklendi.
- [x] **Multi-Timeframe (Üst Zaman Dilimi) Teyit Filtresi:** Botların kısa vadeli sinyallerini (Örn: 15m), bir üst zaman dilimindeki (Örn: 1h) ana trend yönüyle (EMA 50) karşılaştıran ve ters yönlü işlemleri filtreleyen koruma kalkanı sisteme entegre edildi.
- [x] **Piyasa Rejimi (Market Regime) Dedektörü:** ADX, VHF ve Bollinger Sıkışması kullanarak piyasanın Trend mi yoksa Yatay mı olduğunu anlayan zeka katmanı eklendi. Dashboard'a canlı durum kartı eklendi ve Trend Master botunun yatay piyasada işlem açması engellendi.


---


## KAYNAK DOSYA: tech_stack.md

# Önerilen Teknoloji Yığını (Tech Stack)

Aşağıdaki teknoloji yığını rapordaki profesyonel ve kurumsal hedefleri donanımsal ve yazılımsal esneklik ile karşılayabilmesi için seçilmektedir:

## 1. Çekirdek (Core) ve Performans
- **Dil:** `Python 3.10+` (Makine öğrenimi ve zengin ekosistem).
- **Asenkron Altyapı:** `asyncio`, `aiohttp`, veri akışları için `websockets`.
- **Borsa API (Ortak Arayüz):** `CCXT` ve `CCXT Pro` (Rate-limitleri, WebSocket bağlantılarını yönetmek, Binance, BTCTurk, Paribu gibi 100+ borsaya senkron/asenkron olarak ulaşmak).

## 2. Veritabanı ve Önbellek (Storage & Cache)
- **Zaman Serisi Veritabanı (Time-Series DB):** `TimescaleDB` (PostgreSQL mimarisi temelli) veya `InfluxDB` (Milisaniyelik mumları, on-chain hacimlerini ve sistem metriklerini verimli tutar).
- **In-Memory Cache:** `Redis` (Borsa API sorgu limitlerini aşmamak ve ML sisteminin veya farklı modüllerin anlık pozisyon bellek kaydını aşırı hızlı okuyup/yazmasını sağlamak).

## 3. Matematik, Veri Analizi ve İndikatörler
- **Matris ve İstatistik İşlemleri:** `NumPy`, `Pandas`, `SciPy`.
- **Finansal Modelleme:** `statsmodels` (Fractional Differentiation, statik analiz metodları).
- **İndikatörler (Hızlı):** Piyasada kendini ispatlamış `TA-Lib` kütüphanesi (veya Python sarmalayıcısı `pandas-ta`).

## 4. Yapay Zeka ve Tahmin Modelleri (AI & ML)
- **Derin Öğrenme / Sinir Ağları:** `PyTorch` (LSTM, Transformer zaman serisi modelleri ve Özel Risk Ödül Kayıp (Loss) Fonksiyonları yazmak için donanımı iyi kullanır).
- **Ağaç Tabanlı Modeller & Füzyon (CFA):** `XGBoost`, `Scikit-learn` (Ensemble modeling ve çok daha doğrusal olmayan analizler).
- **NLP (Doğal Dil İşleme/Sentiment):** HuggingFace `transformers` (Gelişmiş metin analizleri) veya `VADER` sentiment analysis (hızlı haber ivmesi için).

## 5. Algoritma Testi (Backtesting) Mimarisi
- **Simülatör & Değerlendirici:** `VectorBT` veya `Backtrader` (Milyonlarca satırlık geçmiş verinin hiper-parametre optimizasyonu (WFO) sürecinde vektörel hızı sayesinde efektif kullanılması).

## 6. Dağıtım ve İzleme Mekanizmaları (DevOps & Deployment)
- **Kayıt ve İzolasyon:** `Docker Engine` ve `Docker Compose`. (Ana strateji motoru, ML model servisi ve veri toplayıcı mikroservisler halinde kurulur ki biri çökerse diğeri çalışmaya devam etsin).
- **Loglama ve Görselleştirme:** `Prometheus` (Ağ metriklerini toplar) ve `Grafana` (Win-rate, açık pozisyonlar, anlık PnL izlemesi, slipaj, ping).
- **Sunucu Ortamı:** AWS veya yüksek bant/iyi ağ donanımı sağlayan bölgesel linux (Ubuntu) makineleri.


---
