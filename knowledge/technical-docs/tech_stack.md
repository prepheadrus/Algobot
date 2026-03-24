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
- **İndikatörler (Hızlı):** Tamamen bağımsız (`pandas-ta` veya `TA-Lib` gerektirmeyen) %100 saf Pandas ve Numpy vektörel hesaplamaları.

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
