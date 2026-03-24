# 🏛 Sistem Mimarisi Genel Bakış (Architecture Overview)

Crypto Algo Bot projesi, modern veri mühendisliği, yapay zeka ve modüler yazılım prensipleriyle (Python & FastAPI) inşa edilmiş bir algoritmik ticaret ve analiz motorudur.

## 1. Katmanlı Yapı (Layered Architecture)

Sistem **5 Temel Katmandan** oluşur:
1. **Veri Sağlayıcı Katmanı (Data Provider):** `core/exchange.py`
   - CCXT kütüphanesi aracılığıyla Binance borsasına bağlanır.
   - Periyodik (Asynchronous Poller) olarak seçili coinlerin mum (OHLCV) verilerini sömürür.
2. **Özellik Çıkarımı Katmanı (Feature Engineering):** `data/indicators.py`
   - Alınan ham mum verilerinin üzerine teknik analiz modülleri oturtulur.
   - `pandas_ta` kütüphanesi merkezi olarak kullanılırken, Koncorde ve Kalman Filtresi gibi kütüphanesi olmayan kompleks denklemler özel algoritmalarla çözülüp sütun olarak eklenir.
3. **Teknik Karar Katmanı (Strategy Core):** `strategy/`
   - Tamamen izole edilmiş, safça "Kurallar Bütünü" barındıran katmandır. Trend Master, Golden Combo gibi şablonlar burada barınır. Sadece 0(SAT), 1(BEKLE), 2(AL) sinyali üretirler.
4. **Yapay Zeka & Simülasyon Katmanı (ML Inference & Paper Trade):** `api/server.py` & `core/paper.py`
   - Geçmiş stratejik kararları alan Yapay Zeka (XGBoost) tahminiyle, stratejiden gelen "AL" sinyalinin uyumlu (Konfluans) olduğu noktalarda `PaperTrader` motoruna emir iletilir.
   - Bu emir komisyon, sınır, bakiye, ve risk hesaplarından (Dinamik Kaldıraç & ATR) geçerek işlem dosyasına yazılır.
5. **Sunum Katmanı (Frontend):** `frontend/`
   - Kullanıcının doğrudan gördüğü vitrindir. TradingView Lightweight Charts entegredir. Lejantlar, interaktif tooltipler ve dinamik ondalık hesaplamalarla tam gerçekçi bir borsa terminali hissiyatı sunar.

## Temel Çalışma Döngüsü (Workflow)

[Binance'dan Ham Veri] 
      -> [indicators.py ile Veriyi Zenginleştir (MACD, ADX, VIX...)]
             -> [XGBoost Model Tahmini (0, 1, 2) + Güven Skoru] 
             -> [Seçili Strateji (Örn: Golden Combo) Kuralları Onayı (0, 1, 2)]
                    => {EĞER HER İKİSİ DE 2 VE GÜVEN > %65 İSE}
                           -> [PaperTrader'a Gönder -> Komisyon / Kayma Hesabı -> İŞLEME GİR]
