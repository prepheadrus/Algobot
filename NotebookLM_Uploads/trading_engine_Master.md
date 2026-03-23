# TRADING_ENGINE BILGI BANKASI
Son Guncelleme: 08/03/2026 22:58

---



## KAYNAK DOSYA: paper_trader.md

# 🏧 Paper Trader (Sanal İşlem Modülü)

`core/paper.py` projenin en gerçekçi sanal borsa simülatörüdür. Sıradan backtest yazılımlarındaki "100.000$'ım var kripto alayım" basitsizliğini reddeder. Dünyanın en gelişmiş risk kurallarını içerir.

## 1. Komisyon ve Kayma (Slippage) Entegrasyonu
- **Komisyon (Fee):** Bir işlem açıldığında ve kapandığında anında komisyon kesilir (`position_value_usd * fee_rate`). Bu, açılan işlemin direkt eksi (-) bakiye ile (zararda) başlamasına sebep olur (Tamamen gerçeğe uygun).
- **Slipaj (Kayma):** Piyasaya Market Emri ile girildiği simüle edilerek o anki fiyat neyse (Örn: 70.000), `1.0001` ile çarpılarak alım noktasından biraz yukarda (`70.007`) işleme girilmiş varsayılır. Bu da sistemin "kıl payı" kârlılıklarını eler.

## 2. Risk Yönetimi & Boyutlandırma (Position Sizing)
Bota "Elimdeki 100 Doların Tümüyle İşleme Gir" denilmez. Bot kendisi şu hesabı yapar:
1. Piyasada riskli bir mum var mı? (ATR'sine yani mumların boyuna bakar).
2. Stop noktamı nereye koymalıyım? (ATR * Strateji Çarpanı).
3. Zarar edersem anaparamın en fazla %0.2'sini veya %1'ini kaybetmeliyim. *Buna göre kaç adet Doge almalıyım?* (Gerçek fon yönetimi matematiği).

## 3. Dinamik Kaldıraç Sistemi (Dynamic Leverage)
Yapay Zeka (XGboost), giren muma %85 güveniyorsa, bot riski büyütür ve 10x kaldıraç basar. Güven %65 ise sadece 3x - 5x kaldıraç ile işleme girer. Risk, zekaya (Confidence Score) göre dinamik esner.

## 4. Geliştirme Hedefleri
- **Trailing Stop (İzleyen Stop): TAMAMLANDI** - Bot artık sabit değil, dinamik olarak çalışan trailing stop-loss mekanizmasına sahiptir.

---
