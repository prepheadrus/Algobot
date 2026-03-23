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
