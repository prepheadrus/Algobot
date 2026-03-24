# 🎨 No-Code Strateji Oluşturucu - Kullanım Kılavuzu

**Son Güncelleme:** Mart 2026  
**Versiyon:** 1.0  
**Durum:** Production Ready

---

## 📋 İÇİNDEKİLER

1. [Giriş](#1-giriş)
2. [Hızlı Başlangıç](#2-hızlı-başlangıç)
3. [Adım Adım Strateji Oluşturma](#3-adım-adım-strateji-oluşturma)
4. [İndikatör Rehberi](#4-indikatör-rehberi)
5. [Koşul Oluşturma](#5-koşul-oluşturma)
6. [Test ve Backtest](#6-test-ve-backtest)
7. [Kaydetme ve Yükleme](#7-kaydetme-ve-yükleme)
8. [Örnek Stratejiler](#8-örnek-stratejiler)
9. [Sık Sorulan Sorular](#9-sık-sorulan-sorular)

---

## 1. GİRİŞ

### No-Code Strateji Oluşturucu Nedir?

CryptoAlgoBot'un **No-Code Strateji Oluşturucu** özelliği, kod yazmadan kendi trading stratejilerinizi oluşturmanızı sağlar.

### Kimler Kullanabilir?

- ✅ **Yeni Başlayanlar:** Kod bilgisi gerekmez
- ✅ **Traderlar:** Stratejileri hızlıca test edin
- ✅ **Geliştiriciler:** Prototip oluşturun
- ✅ **Analistler:** Fikirleri hızlıca doğrulayın

### Özellikler

| Özellik | Açıklama |
|---------|----------|
| 📚 İndikatör Kütüphanesi | 11+ hazır indikatör |
| ⚙️ Görsel Koşul Oluşturucu | Sürükle-bırak arayüzü |
| 🔀 Mantıksal Operatörler | AND, OR desteği |
| 📊 Real-time Preview | Anlık JSON önizleme |
| 🧪 Test Sistemi | Hızlı backtest |
| 💾 Kaydetme Sistemi | JSON formatında |

---

## 2. HIZLI BAŞLANGIÇ

### Adım 1: Strateji Laboratuvarı'nı Aç

Dashboard'da sol menüden **🎨 Strateji Laboratuvarı** sekmesine tıklayın.

### Adım 2: İndikatör Seç

Sol panelden bir indikatör seçin (örn: **RSI**) ve **"+"** butonuna tıklayın.

### Adım 3: Koşul Ekle

Orta panelde:
- **LONG Koşulu:** RSI < 30
- **SHORT Koşulu:** RSI > 70

### Adım 4: Test Et

**"🧪 Test Et"** butonuna tıklayın.

### Adım 5: Kaydet

**"💾 Kaydet"** butonuna tıklayın.

**Tebrikler!** İlk stratejinizi oluşturdunuz! 🎉

---

## 3. ADIM ADIM STRATEJİ OLUŞTURMA

### Örnek: RSI + MACD Stratejisi

#### Adım 1: Temel Bilgiler

```
Strateji Adı: RSI MACD Combo
Zaman Dilimi: 15m
```

#### Adım 2: İndikatörleri Ekle

**1. RSI Ekle:**
- Sol panel → MOMENTUM → RSI → "+"
- Parametre: Length = 14
- Tamam

**2. MACD Ekle:**
- Sol panel → MOMENTUM → MACD → "+"
- Fast = 12, Slow = 26, Signal = 9
- Tamam

#### Adım 3: LONG Koşulu Oluştur

```
RSI < 30
VE (AND)
MACD > Signal
```

**Nasıl:**
1. LONG panelinde "➕ Koşul Ekle"
2. İndikatör: RSI, Operatör: <, Değer: 30
3. "➕ Koşul Ekle" tekrar
4. İndikatör: MACD, Operatör: >, Değer: Signal
5. Logic: VE (AND) seç

#### Adım 4: SHORT Koşulu Oluştur

```
RSI > 70
VE (AND)
MACD < Signal
```

#### Adım 5: Risk Ayarları

```
Stop Loss: 2.0x ATR
Take Profit: 3.0x ATR
Max Risk: %2
```

#### Adım 6: Test

**"🧪 Test Et"** → Sonuçları incele:
- Win Rate: %62
- Total Trades: 24
- Profit Factor: 1.8

#### Adım 7: Kaydet

**"💾 Kaydet"** → Dosya adı: `rsi_macd_combo.json`

---

## 4. İNDİKATÖR REHBERİ

### 📈 TREND İNDİKATÖRLERİ

#### EMA (Exponential Moving Average)

**Parametreler:**
- `length`: Periyot (1-200, varsayılan: 20)

**Kullanım:**
```
EMA < Close  → Fiyat ortalamanın üstünde (BOĞA)
EMA > Close  → Fiyat ortalamanın altında (AYI)
```

#### SMA (Simple Moving Average)

**Parametreler:**
- `length`: Periyot (1-200, varsayılan: 20)

**Kullanım:**
```
SMA Cross: EMA_fast > EMA_slow → AL
```

#### Supertrend

**Parametreler:**
- `multiplier`: Çarpan (1.0-10.0, varsayılan: 3.0)
- `period`: Periyot (1-50, varsayılan: 10)

**Kullanım:**
```
Close > Supertrend → LONG
Close < Supertrend → SHORT
```

---

### 🚀 MOMENTUM İNDİKATÖRLERİ

#### RSI (Relative Strength Index)

**Parametreler:**
- `length`: Periyot (1-50, varsayılan: 14)

**Kullanım:**
```
RSI < 30  → Aşırı Satım (AL fırsatı)
RSI > 70  → Aşırı Alım (SAT fırsatı)
RSI < 50  → Ayı momentum
RSI > 50  → Boğa momentum
```

#### MACD (Moving Average Convergence Divergence)

**Parametreler:**
- `fast`: Hızlı EMA (1-50, varsayılan: 12)
- `slow`: Yavaş EMA (1-100, varsayılan: 26)
- `signal`: Signal line (1-50, varsayılan: 9)

**Kullanım:**
```
MACD > Signal → AL
MACD < Signal → SAT
MACD > 0 → Boğa
MACD < 0 → Ayı
```

#### Stochastic

**Parametreler:**
- `k`: %K periyot (1-50, varsayılan: 14)
- `d`: %D periyot (1-50, varsayılan: 3)

**Kullanım:**
```
%K < 20 → Aşırı Satım
%K > 80 → Aşırı Alım
%K > %D → AL
%K < %D → SAT
```

---

### 📊 VOLATİLİTE İNDİKATÖRLERİ

#### ATR (Average True Range)

**Parametreler:**
- `period`: Periyot (1-50, varsayılan: 14)

**Kullanım:**
```
Stop Loss = Entry - (2.0 x ATR)
Take Profit = Entry + (3.0 x ATR)
```

#### Bollinger Bands

**Parametreler:**
- `length`: Periyot (1-100, varsayılan: 20)
- `std`: Standart sapma (0.5-5.0, varsayılan: 2.0)

**Kullanım:**
```
Close < Lower Band → Aşırı Satım (AL)
Close > Upper Band → Aşırı Alım (SAT)
```

---

### 💰 HACİM İNDİKATÖRLERİ

#### OBV (On-Balance Volume)

**Parametreler:** Yok

**Kullanım:**
```
OBV yükseliyor + Fiyat yükseliyor → Trend güçlü
OBV düşüyor + Fiyat yükseliyor → Divergence (dönüş uyarısı)
```

#### VWAP (Volume Weighted Average Price)

**Parametreler:** Yok

**Kullanım:**
```
Close > VWAP → Boğa
Close < VWAP → Ayı
```

#### MFI (Money Flow Index)

**Parametreler:**
- `period`: Periyot (1-50, varsayılan: 14)

**Kullanım:**
```
MFI < 20 → Aşırı Satım
MFI > 80 → Aşırı Alım
```

---

## 5. KOŞUL OLUŞTURMA

### Mantıksal Operatörler

#### VE (AND)

**Tüm koşullar sağlanmalı:**

```
RSI < 30 VE MACD > Signal VE Close > EMA
→ Hepsi doğru olmalı
```

#### VEYA (OR)

**En az bir koşul sağlanmalı:**

```
RSI < 30 VEYA MACD > Signal
→ Biri doğru yeterli
```

### Karşılaştırma Operatörleri

| Operatör | Anlamı | Örnek |
|----------|--------|-------|
| `<` | Küçük | RSI < 30 |
| `>` | Büyük | MACD > Signal |
| `=` | Eşit | Close = Open |
| `<=` | Küçük veya eşit | RSI <= 30 |
| `>=` | Büyük veya eşit | Close >= EMA |

### İndikatör vs İndikatör

Bir indikatörü başka indikatör ile karşılaştır:

```
MACD > Signal
EMA_9 > EMA_21
Close > VWAP
```

### İndikatör vs Değer

İndikatörü sabit değer ile karşılaştır:

```
RSI < 30
ATR > 2.5
MFI > 80
```

---

## 6. TEST VE BACKTEST

### Hızlı Test

**"🧪 Test Et"** butonu:
- Son 30 gün verisi
- Seçili timeframe
- Hızlı sonuç (1-2 saniye)

**Sonuç Metrikleri:**
- **Win Rate:** Kazanma oranı (%)
- **Total Trades:** Toplam işlem sayısı
- **Profit Factor:** Brüt kar / Brüt zarar
- **Max Drawdown:** Maksimum düşüş (%)

### Detaylı Backtest (Gelecek Özellik)

- Özel tarih aralığı
- Komisyon hesaplama
- Slipaj simülasyonu
- Detaylı rapor

---

## 7. KAYDETME VE YÜKLEME

### Kaydetme

1. **"💾 Kaydet"** butonuna tıkla
2. Dosya adı otomatik oluşturulur: `rsi_macd_combo_20260306_143022.json`
3. Dosya `artifacts/strategies/` klasörüne kaydedilir

### Yükleme

**Yöntem 1: Dashboard'dan**
1. Strateji Kütüphanesi sekmesi
2. Strateji seç
3. "Yükle" tıkla

**Yöntem 2: JSON Dosyasından**
```json
{
  "name": "RSI MACD Combo",
  "timeframe": "15m",
  "indicators": [...],
  "conditions": {...}
}
```

### Dışa Aktarma (Export)

```bash
# API ile
GET /api/v1/strategy/list
GET /api/v1/strategy/load/{filename}
```

### İçe Aktarma (Import)

```bash
# API ile
POST /api/v1/strategy/save
Body: { strateji JSON }
```

---

## 8. ÖRNEK STRATEJİLER

### 8.1 Basit RSI Stratejisi

**İndikatörler:**
- RSI (14)

**LONG:**
```
RSI < 30
```

**SHORT:**
```
RSI > 70
```

**Risk:**
- Stop: 2.0x ATR
- Take: 3.0x ATR

---

### 8.2 EMA Crossover

**İndikatörler:**
- EMA Fast (9)
- EMA Slow (21)

**LONG:**
```
EMA_9 > EMA_21
```

**SHORT:**
```
EMA_9 < EMA_21
```

**Risk:**
- Stop: 2.5x ATR
- Take: 3.5x ATR

---

### 8.3 MACD + RSI

**İndikatörler:**
- RSI (14)
- MACD (12, 26, 9)

**LONG:**
```
RSI < 30 VE MACD > Signal
```

**SHORT:**
```
RSI > 70 VE MACD < Signal
```

**Risk:**
- Stop: 2.0x ATR
- Take: 3.0x ATR

---

### 8.4 Bollinger Breakout

**İndikatörler:**
- Bollinger Bands (20, 2.0)

**LONG:**
```
Close < Lower Band
```

**SHORT:**
```
Close > Upper Band
```

**Risk:**
- Stop: 1.5x ATR
- Take: 3.0x ATR

---

### 8.5 Triple Confirmation

**İndikatörler:**
- RSI (14)
- MACD (12, 26, 9)
- EMA (50)

**LONG:**
```
RSI < 30 VE MACD > Signal VE Close > EMA_50
```

**SHORT:**
```
RSI > 70 VE MACD < Signal VE Close < EMA_50
```

**Risk:**
- Stop: 2.0x ATR
- Take: 4.0x ATR

---

## 9. SIK SORULAN SORULAR

### S: Kaç indikatör ekleyebilirim?

**C:** Sınırsız! Ama performans için 3-5 indikatör önerilir.

### S: Aynı indikatörü birden fazla ekleyebilir miyim?

**C:** Evet! Örneğin:
- RSI (14) - kısa vadeli
- RSI (50) - uzun vadeli

### S: Özel indikatör ekleyebilir miyim?

**C:** Şu anda 11 hazır indikatör var. Özel indikatör için Python kodu gerekiyor (gelecek özellik).

### S: Stratejim neden sinyal vermiyor?

**C:** Koşullar çok katı olabilir. Kontrol edin:
- İndikatörler doğru eklendi mi?
- Koşullar çok mu zor?
- Timeframe uygun mu?

### S: Backtest sonuçları gerçekçi mi?

**C:** Hızlı test yaklaşık sonuçlar verir. Detaylı backtest için:
- Komisyon hesaplama
- Slipaj simülasyonu
- Daha uzun tarih aralığı

### S: Stratejimi nasıl paylaşabilirim?

**C:** JSON dosyasını kopyalayın:
```
artifacts/strategies/strateji_adı.json
```

### S: Canlı trading'de kullanabilir miyim?

**C:** Evet! Ama önce:
1. Paper trading'de test edin
2. Backtest yapın
3. Küçük pozisyonlarla başlayın

---

## 📞 DESTEK

**Sorun mu var?**

1. **Dokümantasyon:** `/knowledge` klasörü
2. **GitHub Issues:** https://github.com/prepheadrus/Crypto_Automat/issues
3. **Discord:** (Yakında)

---

*Son Güncelleme: Mart 2026*  
*CryptoAlgoBot Development Team*
