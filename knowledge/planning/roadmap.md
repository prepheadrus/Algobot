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
