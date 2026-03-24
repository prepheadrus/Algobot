# 🎨 Frontend & Görselleştirme (UI/UX) Motoru

Yatırımcının/Geliştiricinin dünyayla bağ kurduğu tek nokta. Sadece güzel görünmekle kalmaz, aynı zamanda yüksek kapasiteli veri işler.

## 1. TradingView İskeleti
Modern borsa arayüzlerinin bir numaralı standardı olan **Lightweight Charts** ile grafikler çizdirilir. Çıplak HTML/CSS ile entegre bir yapımız vardır (`app.js`). Kütüphane sunucu çökmelerine karşı yerel ortama (Local JS) çekilmiş ve %100 Uptime sağlanmıştır.

## 2. Hiyerarşik Gösterim Modeli (Gürültüsüz Grafik)
Bir önceki sürümdeki "Her saniye grafik üzerine AL kelimesinin basılması" problemi (Sinyal Karmaşası) profesyonel terminal mantığıyla düzeltilmiştir:
1. **Model ve Tahmin Düşünceleri:** Şeffaf (Transparan) küçük noktacıklar olarak arka plana itilmiştir. Sadece durumu sezinlemek adına grafiğin alt ve üst bandlarında gezinirler.
2. **Net İşlem Kesişimleri (Focus):** Yapay Zeka (%65 Güven) + Strateji = AL koşulunun sağlandığı "Gerçek Sanal Cüzdan" işlemlerinde BÜYÜK OKLAR belirir ve ekranda sadece işleme girdiğimiz "İŞLEM: AL" yahut "KAPANIŞ" noktaları dev boyutta vurgulanır.

## 3. İnteraktif Tooltip (Bilgi Balonu)
Grafik üzerindeki mumlarda gezindikçe (Hover / Crosshair); dinamik bir CSS kutusu mouse'ı takip eder. Kutunun içinde o mumun:
- Kesin ondalıklı (Dinamik Precision) Fiyat Açılış-Kapanış değerleri.
- Ve o sırada arka planda "Yapay Zeka" ve "Stratejinin" ne hissettiği metin dokümanı olarak özetlenir.

## 4. Dinamik Hassasiyet (Decimal Precision) Algoritması
Bir DOGE/USDT paritesinde "0.14$" yazması ile, BTC/USDT'de "71000.5$" yazması arasındaki ondalık eksikliğini kendi iç mekanizmasıyla otomatik ölçer. Parite 1 Dolar'dan küçükse arka planda otomatik olarak haneyi açar ve kullanıcıya "0.145028" hassasiyetinde veri sunar. Bu grafik ekseni ve tooltipler için evrensel uyarlanır.
