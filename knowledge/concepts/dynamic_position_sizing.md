# 📐 Dynamic Position Sizing (Dinamik Pozisyon Boyutlandırma)

**Versiyon:** v4.0 (Production-Ready)
**Son Güncelleme:** Mart 2026
**Köken:** Kurumsal Fon Yönetimi / Risk Control Theory
**Kategori:** Kantitatif Kavramlar / Risk Yönetimi

---

## 📋 Genel Bakış

**Dynamic Position Sizing (Dinamik Pozisyon Boyutlandırma)**, her işlemde anaparanın sadece spesifik bir yüzdesini (örn: %1) riske atarak, piyasa volatilitesinden bağımsız olarak tutarlı risk yönetimi sağlayan kurumsal fon yönetimi felsefesidir.

---

## 🎯 Teori ve Felsefe

### **1. Amatör Yaklaşım: Sabit Lot / Sabit Dolar**

**Sabit Lot (YANLIŞ):**
```
Her işlemde 0.1 BTC ile gir:
  BTC @ $50,000 → $5,000 risk
  BTC @ $20,000 → $2,000 risk  ❌ Tutarsız!
  
Sorun:
  - Fiyat değişince risk değişiyor
  - $50k'da %1 risk, $20k'da %2.5 risk
  - Risk yönetimi YOK
```

**Sabit Dolar (YANLIŞ):**
```
Her işlemde $1,000 ile gir:
  BTC (ATR: $500) → Stop mesafesi: $1,000 → %2 risk
  DOGE (ATR: $0.005) → Stop mesafesi: $0.01 → %10 risk  ❌ Tutarsız!

Sorun:
  - Volatilite değişince risk değişiyor
  - Yüksek volatilite (BTC) → Dar stop → Düşük risk
  - Düşük volatilite (DOGE) → Geniş stop → Yüksek risk
  - Risk yönetimi YOK
```

**Amatör Psikolojisi:**
```
"BTC'de 0.1 lot, DOGE'de 1000 lot kullanıyorum.
DOGE daha ucuz, daha çok alabilirim!"

❌ YANLIŞ MANTIK!

Ucuz/pahalı önemli değil.
Önemli olan: Fiyat hareketi (volatilite).

DOGE %10 hareket edebilir, BTC %2.
1000 DOGE lot'u, 0.1 BTC lot'tan DAHA RİSKLİ olabilir.
```

---

### **2. Kurumsal Yaklaşım: Risk Bazlı Boyutlandırma**

**Felsefe:**
> "Her işlemde anaparamın sadece %1'ini riske atıyorum.
> Piyasa volatilitesi (BTC vs DOGE) önemli değil.
> Önemli olan: Zarar ettiğimde anaparamın %1'ini kaybetmek."

**Temel Prensip:**
```
Anapara: $10,000
Risk: %1 → $100

BTC İşlemi:
  Giriş: $50,000
  Stop: $49,000 (mesafe: $1,000)
  Pozisyon Boyutu: $100 / $1,000 = 0.1 BTC
  Risk: 0.1 × $1,000 = $100 (%1) ✅

DOGE İşlemi:
  Giriş: $0.10
  Stop: $0.095 (mesafe: $0.005)
  Pozisyon Boyutu: $100 / $0.005 = 20,000 DOGE
  Risk: 20,000 × $0.005 = $100 (%1) ✅

SONUÇ: Her iki işlemde de $100 risk (%1) ✅
```

**Avantajlar:**
- ✅ **Volatilite Bağımsız:** BTC, DOGE, ETH hepsinde aynı risk
- ✅ **Tutarlılık:** Her işlemde %1 risk
- ✅ **Sürdürülebilirlik:** 10 kayıp üst üste → %10 kayıp (hala hayattasın)
- ✅ **Psikolojik Konfor:** Risk belli, stres az

---

## 📐 Matematiksel Formülasyon

### **1. Temel Formül**

**Pozisyon Boyutu:**
```
Position Size = (Balance × Risk%) / |Entry - Stop_Loss|
```

**Değişkenler:**
- `Balance`: Anapara (USDT)
- `Risk%`: Risk yüzdesi (örn: 0.01 = %1)
- `Entry`: Giriş fiyatı
- `Stop_Loss`: Stop loss fiyatı
- `|Entry - Stop_Loss|`: Fiyat mesafesi (mutlak değer)

---

### **2. Adım Adım Hesaplama**

**Örnek Senaryo:**
```
Anapara: $10,000
Risk: %1
Giriş: $50,000 (BTC)
Stop: $49,000
```

**Adım 1: Risk Miktarını Hesapla**
```
Risk Amount = Balance × Risk%
            = $10,000 × 0.01
            = $100
```

**Adım 2: Fiyat Mesafesini Hesapla**
```
Price Distance = |Entry - Stop_Loss|
               = |$50,000 - $49,000|
               = $1,000
```

**Adım 3: Pozisyon Boyutunu Hesapla**
```
Position Size = Risk Amount / Price Distance
              = $100 / $1,000
              = 0.1 BTC
```

**Adım 4: Pozisyon Değerini Hesapla**
```
Position Value = Position Size × Entry
               = 0.1 × $50,000
               = $5,000
```

**Adım 5: Risk Yüzdesini Doğrula**
```
Actual Risk = Position Size × Price Distance
            = 0.1 × $1,000
            = $100

Risk % = Actual Risk / Balance
       = $100 / $10,000
       = 0.01 = %1 ✅
```

---

### **3. Python Implementasyonu**

```python
# core/risk/risk_engine.py
def calculate_position_size(
    account_balance: float,
    entry_price: float,
    stop_loss_price: float,
    risk_percentage: float = 1.0,
    leverage: float = 1.0,
    free_margin: Optional[float] = None
) -> float:
    """
    Pozisyon boyutu hesapla (risk bazlı).
    
    Formül: min(
        (Balance × Risk%) / |Entry - Stop|,     # Risk-based
        (Balance / MaxPositions × Leverage × 0.98) / Entry,  # Margin limit
        (FreeMargin × Leverage × 0.98) / Entry   # Free margin limit
    )
    
    Args:
        account_balance: Hesap bakiyesi (USDT)
        entry_price: Giriş fiyatı
        stop_loss_price: Stop loss fiyatı
        risk_percentage: Risk yüzdesi (örn: 1.0 = %1)
        leverage: Kaldıraç (örn: 5 = 5x)
        free_margin: Serbest marjin (opsiyonel)
    
    Returns:
        Pozisyon boyutu (coin miktarı)
    """
    
    # Risk yüzdesini doğrula (0-5% arası)
    if risk_percentage <= 0.0 or risk_percentage > 5.0:
        risk_percentage = 1.0  # Güvenli fallback
    
    # 1. Risk miktarı ($)
    risk_amount = account_balance * (risk_percentage / 100.0)
    
    # 2. Fiyat mesafesi
    price_distance = abs(entry_price - stop_loss_price)
    
    if price_distance <= 0:
        return 0.0  # Geçersiz stop
    
    # 3. Risk bazlı boyut
    size_by_risk = risk_amount / price_distance
    
    # 4. Marjin limiti (account limitine göre cap)
    max_positions = getattr(self.config, 'max_open_positions', 10)
    max_positions = max(1, max_positions)
    max_margin_per_trade = account_balance / max_positions
    
    # Seçilen kaldıraç ile ulaşılabilecek maksimum notional
    max_notional_by_margin = max_margin_per_trade * leverage * 0.98  # %2 margin buffer
    size_by_margin_limit = max_notional_by_margin / entry_price
    
    # 5. Serbest bakiye limiti
    size_by_free_margin = float('inf')
    if free_margin is not None:
        max_notional_by_free_margin = free_margin * leverage * 0.98
        size_by_free_margin = max_notional_by_free_margin / entry_price
    
    # 6. En küçüğünü al (en katı limit)
    position_size = min(size_by_risk, size_by_margin_limit, size_by_free_margin)
    
    logger.debug(
        f"📏 Boyut Hesabı | "
        f"Risk: {size_by_risk:.4f}, "
        f"MarginLimit: {size_by_margin_limit:.4f}, "
        f"FreeMarginLimit: {size_by_free_margin:.4f} "
        f"→ Final: {position_size:.4f}"
    )
    
    return position_size
```

---

### **4. Çoklu Örnek Senaryo**

**Senaryo 1: BTC LONG (Yüksek Fiyat, Dar Stop)**
```
Balance: $10,000
Risk: %1 → $100
Entry: $50,000
Stop: $49,500 (mesafe: $500)

Position Size = $100 / $500 = 0.2 BTC
Position Value = 0.2 × $50,000 = $10,000
Leverage: 1x → Margin: $10,000 (tüm bakiye)

Risk: 0.2 × $500 = $100 (%1) ✅
```

**Senaryo 2: BTC LONG (Yüksek Fiyat, Geniş Stop)**
```
Balance: $10,000
Risk: %1 → $100
Entry: $50,000
Stop: $49,000 (mesafe: $1,000)

Position Size = $100 / $1,000 = 0.1 BTC
Position Value = 0.1 × $50,000 = $5,000
Leverage: 1x → Margin: $5,000

Risk: 0.1 × $1,000 = $100 (%1) ✅
```

**Senaryo 3: DOGE LONG (Düşük Fiyat, Dar Stop)**
```
Balance: $10,000
Risk: %1 → $100
Entry: $0.10
Stop: $0.095 (mesafe: $0.005)

Position Size = $100 / $0.005 = 20,000 DOGE
Position Value = 20,000 × $0.10 = $2,000
Leverage: 1x → Margin: $2,000

Risk: 20,000 × $0.005 = $100 (%1) ✅
```

**Senaryo 4: DOGE LONG (Düşük Fiyat, Geniş Stop)**
```
Balance: $10,000
Risk: %1 → $100
Entry: $0.10
Stop: $0.09 (mesafe: $0.01)

Position Size = $100 / $0.01 = 10,000 DOGE
Position Value = 10,000 × $0.10 = $1,000
Leverage: 1x → Margin: $1,000

Risk: 10,000 × $0.01 = $100 (%1) ✅
```

**Karşılaştırma:**
```
┌──────────────────────────────────────────────────────────┐
│ Senaryo Karşılaştırması (Her İşlemde %1 Risk)            │
├──────────────────────────────────────────────────────────┤
│ BTC (Dar Stop):  0.2 BTC × $500 = $100 ✅                │
│ BTC (Geniş Stop): 0.1 BTC × $1,000 = $100 ✅             │
│ DOGE (Dar Stop): 20,000 DOGE × $0.005 = $100 ✅          │
│ DOGE (Geniş Stop): 10,000 DOGE × $0.01 = $100 ✅         │
└──────────────────────────────────────────────────────────┘

SONUÇ: Her işlemde AYNI RİSK ($100 = %1) ✅
```

---

## 🧠 ML Confluence Etkisi

### **1. Confidence Score → Dynamic Leverage**

**Felsefe:**
> "ML modelim %85 güvenle LONG diyorsa, daha yüksek kaldıraç kullanabilirim.
> Ama %50 güvenle diyorsa, minimum kaldıraç (1x) kullanmalıyım."

**Confidence → Leverage Mapping:**

| ML Confidence | Recommendation | Leverage (1h+) | Leverage (1m-3m) | Aksiyon |
|---------------|----------------|----------------|------------------|---------|
| **< 50%** | HOLD/WEAK | 1x (base) | 1x | İşlem açma |
| **50-65%** | WEAK_LONG/WEAK_SHORT | 2-3x | 2-3x | Düşük risk |
| **65-80%** | LONG/SHORT | 3-5x | 3-5x | Orta risk |
| **> 80%** | STRONG_LONG/STRONG_SHORT | 5-10x | 5-8x | Yüksek risk |

**Timeframe-Aware Limit:**
```
Düşük timeframe'lerde (1m, 3m) piyasa gürültüsü (noise) yüksek.
Bu yüzden kaldıraç otomatik sınırlandırılır:

1m, 3m: Max 10x (yüksek gürültü + komisyon etkisi)
5m-30m: Max 20x (orta gürültü)
1h+: Normal max kaldıraç (10x)
```

---

### **2. Dinamik Kaldıraç Formülü**

```python
# core/risk/risk_engine.py
def calculate_dynamic_leverage(
    self,
    confidence_score: float,
    base_leverage: Optional[float] = None,
    max_leverage: Optional[float] = None,
    timeframe: str = "1h"
) -> float:
    """
    ML confidence skoruna göre dinamik kaldıraç.
    
    Args:
        confidence_score: ML güven skoru (0.0 - 1.0)
        base_leverage: Baz kaldıraç (default: 1x)
        max_leverage: Maksimum kaldıraç (default: 10x)
        timeframe: Zaman dilimi (örn: "1m", "1h")
    
    Returns:
        Dinamik kaldıraç (1x - 10x)
    """
    
    base = base_leverage or self.config.default_leverage
    maximum = max_leverage or self.config.max_leverage
    
    # ============================================
    # TIMEFRAME-AWARE KALDIRAÇ SINIRLANDIRMASI
    # ============================================
    timeframe_lower = timeframe.lower()
    
    # 1m, 3m: Çok yüksek gürültü - Max 10x
    if timeframe_lower in ["1m", "3m"]:
        maximum = min(maximum, 10)
        logger.info(
            f"⚠️ [TIMEFRAME-AWARE] {timeframe} için kaldıraç sınırlandırıldı: "
            f"Max {maximum}x (Noise + komisyon koruması)"
        )
    
    # 5m, 10m, 15m: Orta gürültü - Max 20x
    elif timeframe_lower in ["5m", "10m", "15m", "20m", "30m"]:
        maximum = min(maximum, 20)
        logger.debug(
            f"📊 [TIMEFRAME-AWARE] {timeframe} için kaldıraç sınırlandırıldı: "
            f"Max {maximum}x (Orta gürültü)"
        )
    
    # 1h+: Normal yüksek kaldıraç
    else:
        logger.debug(f"✅ [TIMEFRAME-AWARE] {timeframe} normal kaldıraç: Max {maximum}x")
    
    # Güven skoru çok düşükse base leverage
    if confidence_score < 0.50:
        return base
    
    # ============================================
    # POWER CURVE: Confidence arttıkça kaldıraç daha hızlı artar
    # ============================================
    raw_ratio = (confidence_score - 0.50) / 0.50
    
    # Floor ratio: 50% confidence'ta bile küçük bir sıçrama (0.05 = %5)
    if raw_ratio == 0:
        boosted_ratio = 0.05  # %5 başlangıç payı
    else:
        boosted_ratio = 0.05 + (0.95 * (raw_ratio ** 0.7))  # Power curve
    
    calculated = base + (boosted_ratio * (maximum - base))
    
    # Kaldıracı sınırla ve tam sayı yap
    final_leverage = int(round(min(maximum, max(base, calculated))))
    
    logger.debug(
        f"🚀 Dinamik kaldıraç: "
        f"Confidence={confidence_score:.2%}, "
        f"Leverage={final_leverage}x "
        f"(Base={base}x, Max={maximum}x, TF={timeframe})"
    )
    
    return float(final_leverage)
```

---

### **3. Kaldıraç Etkili Pozisyon Boyutu**

**Formül:**
```
Position Size (with leverage) = 
    min(
        (Balance × Risk%) / |Entry - Stop|,           # Risk-based
        (Balance / MaxPositions × Leverage × 0.98) / Entry  # Margin limit
    )
```

**Örnek (ML Confidence Bazlı):**
```
Balance: $10,000
Risk: %1 → $100
Entry: $50,000
Stop: $49,000 (mesafe: $1,000)

ML Confidence: 85% → Leverage: 10x

# 1. Risk bazlı boyut
size_by_risk = $100 / $1,000 = 0.1 BTC

# 2. Marjin limiti
max_positions = 5
max_margin_per_trade = $10,000 / 5 = $2,000
max_notional = $2,000 × 10 × 0.98 = $19,600
size_by_margin = $19,600 / $50,000 = 0.392 BTC

# 3. En küçük
position_size = min(0.1, 0.392) = 0.1 BTC

# 4. Kullanılan marjin
margin_used = 0.1 × $50,000 / 10 = $500

# 5. Risk doğrulama
risk = 0.1 × $1,000 = $100 (%1) ✅
```

**Kaldıraç Etkisi:**
```
Leverage 1x: Margin = $5,000, Risk = $100 (%1)
Leverage 5x: Margin = $1,000, Risk = $100 (%1)
Leverage 10x: Margin = $500, Risk = $100 (%1)

NOT: Kaldıraç riski DEĞİŞTİRMEZ!
Sadece kullanılan marjini azaltır.
Risk her zaman %1 ($100).
```

---

## 📊 Risk Yönetimi Matrisi

### **1. Max Positions Limiti**

**Formül:**
```
Max Margin Per Trade = Balance / MaxPositions
```

**Örnek:**
```
Balance: $10,000
MaxPositions: 5

Max Margin Per Trade = $10,000 / 5 = $2,000

Yani bir işleme maksimum $2,000 marjin ayırabilirsin.
```

**Pozisyon Boyutu Sınırı:**
```
Max Notional = Max Margin Per Trade × Leverage × 0.98
             = $2,000 × 10 × 0.98
             = $19,600

Max Position Size = Max Notional / Entry
                  = $19,600 / $50,000
                  = 0.392 BTC
```

---

### **2. Free Margin Limiti**

**Formül:**
```
Max Notional (Free Margin) = FreeMargin × Leverage × 0.98
Max Position Size = Max Notional / Entry
```

**Örnek:**
```
FreeMargin: $8,000
Leverage: 10x
Entry: $50,000

Max Notional = $8,000 × 10 × 0.98 = $78,400
Max Position Size = $78,400 / $50,000 = 1.568 BTC
```

---

### **3. Üçlü Limit Karşılaştırması**

```
┌──────────────────────────────────────────────────────────┐
│ Pozisyon Boyutu Limitleri (BTC @ $50,000)                │
├──────────────────────────────────────────────────────────┤
│ Risk Bazlı:    0.1 BTC  ($100 risk @ %1)                 │
│ Marjin Limiti: 0.392 BTC ($2,000 margin @ 5 pozisyon)    │
│ Free Margin:   1.568 BTC ($8,000 free margin)            │
│                                                          │
│ FINAL: min(0.1, 0.392, 1.568) = 0.1 BTC ✅               │
│ (En katı limit: Risk bazlı)                              │
└──────────────────────────────────────────────────────────┘
```

---

## 🚨 Uygulama Notları

### **1. Risk Yüzdesi Seçimi**

| Trader Tipi | Risk % | Açıklama |
|-------------|--------|----------|
| **Konservatif** | 0.5% | Çok düşük risk, yavaş büyüme |
| **Orta** | 1.0% | Dengeli risk, sürdürülebilir |
| **Agresif** | 2.0% | Yüksek risk, hızlı büyüme/çöküş |
| **Kumarbaz** | ≥5% | ❌ İntihar (10 kayıp → %50 kayıp) |

**Önerilen:**
```
Başlangıç: %1 (orta risk)
İlk 100 işlem sonrası:
  - Win rate ≥60% → %1.5'e çıkar
  - Win rate <50% → %0.5'e düşür
```

---

### **2. Stop Loss Mesafesi Optimizasyonu**

**ATR Bazlı Stop:**
```python
def calculate_stop_loss(entry_price, direction, atr, multiplier):
    if direction == "LONG":
        stop_loss = entry_price - (atr * multiplier)
    else:  # SHORT
        stop_loss = entry_price + (atr * multiplier)
    return stop_loss
```

**Örnek:**
```
BTC LONG:
  Entry: $50,000
  ATR: $500
  Multiplier: 2.0
  
  Stop = 50,000 - (500 × 2.0) = $49,000
  Mesafe: $1,000
  
  Position Size = $100 / $1,000 = 0.1 BTC
```

**Çok Dar Stop (YANLIŞ):**
```
Stop = $49,900 (mesafe: $100)

Position Size = $100 / $100 = 1.0 BTC
Position Value = 1.0 × $50,000 = $50,000 (tüm bakiye!)

❌ SORUN:
  - Tüm bakiye tek işlemde
  - Küçük fiyat hareketi → likidasyon
  - Sürdürülebilir DEĞİL
```

**Önerilen Minimum Stop Mesafesi:**
```
1m-5m:  ≥ 1× ATR
15m-1h: ≥ 1.5× ATR
4h+:    ≥ 2× ATR
```

---

### **3. Seri Kayıp Senaryosu (Drawdown)**

**10 Kayıp Üst Üste:**
```
Risk: %1
Balance: $10,000

Kayıp 1: $10,000 - $100 = $9,900
Kayıp 2: $9,900 - $99 = $9,801
Kayıp 3: $9,801 - $98 = $9,703
...
Kayıp 10: $9,135 - $91 = $9,044

Toplam Kayıp: $956 (%9.56)
```

**Risk: %2 Olsaydı:**
```
Toplam Kayıp: $1,912 (%19.12)
```

**Risk: %5 Olsaydı:**
```
Toplam Kayıp: $4,780 (%47.80)  ❌ TEHLİKELİ!
```

**Sonuç:**
```
Düşük risk (%1) ile 10 kayıp üst üste bile
anaparayı koruyorsun (%9.56 kayıp).

Yüksek risk (%5) ile 10 kayıp üst üste
anaparan YARISINI kaybedersin (%47.80 kayıp).
```

---

## 📚 İlgili Dokümanlar

- **Risk Engine:** `features/risk_engine.md`
- **Paper Trader:** `trading_engine/paper_trader.md`
- **ATR Trailing Stop:** `features/ATR_TRAILING_STOP_SYSTEM.md`
- **ML Integration:** `features/ml_integration.md`

---

## 📖 Kaynaklar

1. **Van K. Tharp** - "Trade Your Way to Financial Freedom" (1998)
   - Chapter 10: Position Sizing
   - Section: The Percent Risk Model

2. **Alexander Elder** - "The New Trading for a Living" (2014)
   - Chapter 13: Risk Management
   - Section: The 2% Rule

3. **Marcos Lopez de Prado** - "Advances in Financial Machine Learning" (2018)
   - Chapter 7: Backtesting
   - Section: Position Sizing

---

*Bu doküman Dynamic Position Sizing v4.0 (Mart 2026) için hazırlanmıştır.*
*Güncellemeler için `knowledge/concepts/` dizinini kontrol edin.*
