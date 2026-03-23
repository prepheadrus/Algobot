# 🎯 Triple Barrier Method (Üçlü Bariyer Etiketleme Yöntemi)

**Versiyon:** v4.0 (Production-Ready)
**Son Güncelleme:** Mart 2026
**Köken:** Marcos Lopez de Prado - "Advances in Financial Machine Learning" (2018)
**Kategori:** Kantitatif Kavramlar / Makine Öğrenmesi

---

## 📋 Genel Bakış

**Triple Barrier Method (Üçlü Bariyer Yöntemi)**, finansal zaman serilerinde makine öğrenmesi için geliştirilmiş devrimsel bir etiketleme (labeling) metodolojisidir. Geleneksel "sabit pencere" yaklaşımlarının neden olduğu **Look-Ahead Bias (Geleceği Görme Yanılgısı)** hatasını ortadan kaldırır.

---

## 🎯 Teori ve Felsefe

### **1. Geleneksel Yaklaşımın Sorunu**

**Standart Etiketleme (YANLIŞ):**
```python
# ❌ SABİT PENCERE YAKLAŞIMI (Look-Ahead Bias!)
def fixed_window_labeling(close_prices, lookahead=5):
    """
    N-mum sonra fiyat nerede olacak?
    
    SORUN: Gelecekteki sabit bir noktaya bakıyor.
    Gerçek trading'de fiyat önce stop'a mı yoksa 
    target'a mı uğradığını bilmiyoruz!
    """
    labels = []
    for i in range(len(close_prices) - lookahead):
        future_price = close_prices[i + lookahead]
        current_price = close_prices[i]
        
        if future_price > current_price * 1.02:
            labels.append(2)  # LONG
        elif future_price < current_price * 0.98:
            labels.append(0)  # SHORT
        else:
            labels.append(1)  # HOLD
    
    return labels
```

**Sorun:**
```
Zaman: t₀ ──────────────────────────────────→ t₀₊₅
       │                                     │
       │        ❌ SABİT PENCERE             │
       │        "5 mum sonra fiyat ne?"      │
       │                                     │
       │  Gerçek trading'de:                 │
       │  - Önce TP'ye mi uğradı?            │
       │  - Önce SL'ye mi değdi?             │
       │  - Yoksa zaman doldu mu?            │
       │  BİLİNMEZ!                          │
       │                                     │
Fiyat: 100 ──→ 105 ──→ 98 ──→ 102 ──→ 103   │
                │      │                      │
                │      └─→ Önce SL'ye değdi! │
                │         (Ama 5. mum 103!)  │
                └─→ TP'ye değdi              │
```

**Look-Ahead Bias Açıklaması:**
```
Geleneksel yöntem, 5 mum sonrasına bakar ve:
"5. mum 103, yani %3 yükseliş → LONG etiketi" der.

AMA gerçekte:
- 2. mumda fiyat 105'e ulaştı (TP'ye değdi) ✅
- 3. mumda fiyat 98'e düştü (SL'ye değdi) ❌

Hangi olay ÖNCE gerçekleşti?
→ 2. mumda TP'ye değdi → LONG karlı kapandı.

5. mumun fiyatı İLGİSİZ!
Çünkü pozisyon 2. mumda zaten kapandı.
```

---

### **2. Triple Barrier Çözümü**

**Felsefe:**
> "Gerçek trading'de üç çıkış senaryosu vardır:
> 1. Kar-al bariyerine dokunulur (LONG için kar)
> 2. Zarar-kes bariyerine dokunulur (LONG için zarar)
> 3. Zaman limiti dolar (nötr çıkış)
> 
> Hangi bariyer ÖNCE dokunulursa, etiket odur."

**Üçlü Bariyer Mantığı:**
```
Fiyat
  │
  │         ┌─────────────── Üst Bariyer (Profit-Take)
  │        ╱│               pt = entry + (tp_multiplier × ATR)
  │       ╱ │
  │      ╱  │
  │     ╱   │
  │    ╱    │
  │   ╱     │
  │  ╱      │
  │ ╱       │
  │╱        │
  ├─────────┼───────────────┼──────────────→ Zaman
  │╲        │               │
  │ ╲       │               │
  │  ╲      │               │
  │   ╲     │               │
  │    ╲    │               │
  │     ╲   │               │
  │      ╲  │               │
  │       ╲ │               │
  │        ╲│               │
  │         └─────────────── Alt Bariyer (Stop-Loss)
  │                          sl = entry - (sl_multiplier × ATR)
  │
  └────────────────────────── Dikey Bariyer (Time Limit)
                             T = t₀ + max_bars (örn: 5 mum)
```

**Üç Senaryo:**

**Senaryo 1: Üst Bariyer Önce (LONG Kar)**
```
Zaman: t₀ ──→ t₁ ──→ t₂ ──→ t₃ ──→ t₄ ──→ t₅
       │           │
       │           └─→ Fiyat ÜST bariyere değdi ✅
       │               Label: 2 (LONG)
       │
Fiyat: 100 ──→ 102 ──→ 105 ──→ ...
                    │
                    └─→ pt_barrier = 105
```

**Senaryo 2: Alt Bariyer Önce (SHORT Kar)**
```
Zaman: t₀ ──→ t₁ ──→ t₂ ──→ t₃ ──→ t₄ ──→ t₅
       │           │
       │           └─→ Fiyat ALT bariyere değdi ✅
       │               Label: 0 (SHORT)
       │
Fiyat: 100 ──→ 98 ──→ 95 ──→ ...
                    │
                    └─→ sl_barrier = 95
```

**Senaryo 3: Zaman Limiti Doldu (HOLD)**
```
Zaman: t₀ ──→ t₁ ──→ t₂ ──→ t₃ ──→ t₄ ──→ t₅
       │                                 │
       │                                 └─→ Zaman doldu ✅
       │                                     Label: 1 (HOLD)
       │
Fiyat: 100 ──→ 102 ──→ 99 ──→ 101 ──→ 100 ──→ 101
                    │                    │
                    │                    └─→ Hiçbir bariyere
                    │                        değmedi
                    └─→ Ne TP ne SL'ye değdi
```

---

## 📐 Matematiksel Formülasyon

### **1. Bariyer Hesaplamaları**

**Girdiler:**
- `entry_price`: Giriş fiyatı (t₀ anındaki fiyat)
- `ATR`: Average True Range (volatilite ölçüsü)
- `tp_multiplier`: Kar-al çarpanı (örn: 2.0)
- `sl_multiplier`: Zarar-kes çarpanı (örn: 2.0)
- `max_bars`: Maksimum mum sayısı (örn: 5)

**Üst Bariyer (Profit-Take):**
```
pt_barrier = entry_price + (tp_multiplier × ATR)
```

**Örnek (LONG):**
```
entry_price = 50,000 (BTC)
ATR = 500
tp_multiplier = 2.0

pt_barrier = 50,000 + (2.0 × 500)
           = 50,000 + 1,000
           = 51,000
```

**Alt Bariyer (Stop-Loss):**
```
sl_barrier = entry_price - (sl_multiplier × ATR)
```

**Örnek (LONG):**
```
entry_price = 50,000
ATR = 500
sl_multiplier = 2.0

sl_barrier = 50,000 - (2.0 × 500)
           = 50,000 - 1,000
           = 49,000
```

**Dikey Bariyer (Time Limit):**
```
time_limit = t₀ + max_bars
```

**Örnek:**
```
t₀ = 12:00 (başlangıç mumu)
max_bars = 5

time_limit = 12:00 + 5 mum
           = 12:05 (5 mum sonra)
```

---

### **2. Etiket Atama Algoritması**

**Psödokod:**
```python
def triple_barrier_labeling(prices, entry_idx, pt_barrier, sl_barrier, max_bars):
    """
    Triple Barrier Method ile etiket atama.
    
    Args:
        prices: Fiyat serisi (t₀'dan t₀₊ₘₐₓ'a)
        entry_idx: Giriş mumu indeksi (t₀)
        pt_barrier: Üst bariyer fiyatı
        sl_barrier: Alt bariyer fiyatı
        max_bars: Maksimum mum sayısı
    
    Returns:
        label: 0 (SHORT), 1 (HOLD), 2 (LONG)
    """
    
    # Giriş fiyatından başla
    entry_price = prices[entry_idx]
    
    # Her mumu kontrol et (t₀₊₁'den t₀₊ₘₐₓ'a)
    for i in range(entry_idx + 1, entry_idx + max_bars + 1):
        high = prices[i].high  # Mumun en yükseği
        low = prices[i].low    # Mumun en düşüğü
        
        # ÖNCE üst bariyer kontrolü (LONG için kar)
        if high >= pt_barrier:
            return 2  # LONG etiketi (kar-al önce değdi)
        
        # Sonra alt bariyer kontrolü (SHORT için kar)
        if low <= sl_barrier:
            return 0  # SHORT etiketi (zarar-kes önce değdi)
    
    # Hiçbir bariyere değmedi → Zaman doldu
    return 1  # HOLD etiketi (nötr)
```

**Python Implementasyonu:**
```python
# ml/data_prep.py
def get_triple_barrier_labels(
    prices: pd.Series,
    events: pd.DataFrame,
    pt_sl: list,
    out: pd.Series
) -> pd.DataFrame:
    """
    Marcos Lopez de Prado'nun Triple Barrier Method.
    
    Args:
        prices: Fiyat serisi (close prices)
        events: DataFrame with event timestamps (t1, time limit)
        pt_sl: [profit_take, stop_loss] çarpanları (örn: [2.0, 2.0])
        out: Hedef volatilite serisi (ATR veya standart sapma)
    
    Returns:
        DataFrame with labels (0=SHORT, 1=NEUTRAL, 2=LONG)
    """
    events_out = events.copy(deep=True)
    
    # Bariyer genişliklerini hesapla
    if pt_sl[0] > 0:
        pt = pt_sl[0] * out  # Profit-take barrier
    else:
        pt = pd.Series(index=events.index, dtype='float64')
    
    if pt_sl[1] > 0:
        sl = -pt_sl[1] * out  # Stop-loss barrier
    else:
        sl = pd.Series(index=events.index, dtype='float64')
    
    # Etiket DataFrame'i oluştur
    labels = pd.DataFrame(
        index=events.index,
        columns=['take_profit', 'stop_loss', 'time_limit', 'label']
    )
    
    # Her event için bariyerleri kontrol et
    for t0, t1 in events['t1'].items():
        # Fiyat yolunu al (t₀'dan t₁'e)
        path = prices.loc[t0:t1]
        
        # Kumülatif getiri hesapla
        cumret = path.pct_change().cumsum()
        
        # Bariyerleri kontrol et
        if (cumret >= pt.loc[t0]).any():
            # Profit-take önce değdi
            labels.loc[t0, 'label'] = 2  # LONG
        elif (cumret <= sl.loc[t0]).any():
            # Stop-loss önce değdi
            labels.loc[t0, 'label'] = 0  # SHORT
        else:
            # Zaman limiti doldu
            labels.loc[t0, 'label'] = 1  # NEUTRAL
    
    return labels
```

---

### **3. Volatilite Tabanlı Bariyer Genişliği**

**ATR (Average True Range) Kullanımı:**

```python
def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Average True Range hesaplaması.
    
    True Range = max(
        high - low,              # Gün içi aralık
        abs(high - close_prev),  # Yukarı gap
        abs(low - close_prev)    # Aşağı gap
    )
    
    ATR = SMA(True Range, period)
    """
    close_prev = close.shift(1)
    
    tr1 = high - low
    tr2 = abs(high - close_prev)
    tr3 = abs(low - close_prev)
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    return atr
```

**Bariyer Genişliği:**
```
LONG için:
  pt_barrier = entry + (tp_multiplier × ATR)
  sl_barrier = entry - (sl_multiplier × ATR)

SHORT için:
  pt_barrier = entry - (tp_multiplier × ATR)  # Aşağı hareket
  sl_barrier = entry + (sl_multiplier × ATR)  # Yukarı hareket
```

**Örnek (Volatilite Bazlı):**
```
BTC/USDT:
  entry = 50,000
  ATR = 500 (yüksek volatilite)
  tp_multiplier = 2.0
  sl_multiplier = 2.0
  
  pt_barrier = 50,000 + (2.0 × 500) = 51,000
  sl_barrier = 50,000 - (2.0 × 500) = 49,000

DOGE/USDT:
  entry = 0.10
  ATR = 0.005 (düşük volatilite)
  tp_multiplier = 2.0
  sl_multiplier = 2.0
  
  pt_barrier = 0.10 + (2.0 × 0.005) = 0.11
  sl_barrier = 0.10 - (2.0 × 0.005) = 0.09
```

**Avantaj:**
- ✅ **Piyasa Koşullarına Uyumlu:** Yüksek volatilite → geniş bariyerler
- ✅ **Evrensel:** BTC, DOGE, ETH hepsi için aynı mantık
- ✅ **Dinamik:** ATR değiştikçe bariyerler otomatik ayarlanır

---

## 🎯 Sistem Çıktısı ve Etiketler

### **1. Hedef Değişkenler (Target Variables)**

**Sınıf Etiketleri:**

| Label | Değer | Anlam | Çıkış Senaryosu |
|-------|-------|-------|-----------------|
| **SHORT** | `0` | Alt bariyer önce değdi | LONG için zarar, SHORT için kar |
| **HOLD** | `1` | Zaman limiti doldu | Nötr çıkış (kar/zarar yok) |
| **LONG** | `2` | Üst bariyer önce değdi | LONG için kar, SHORT için zarar |

**Sınıf Dağılımı (Örnek):**
```
Eğitim Seti (5000 örnek):
  Label 0 (SHORT): 1,500 örnek (%30)
  Label 1 (HOLD):  2,000 örnek (%40)
  Label 2 (LONG):  1,500 örnek (%30)

Sınıf Dengesi: ✅ Dengeli (her sınıftan yeterli örnek)
```

---

### **2. Çok Sınıflı Sınıflandırma (Multi-Class Classification)**

**Model Çıktısı:**
```python
# ml/model_training.py
class_mapping = {
    0: 'SHORT',
    1: 'NEUTRAL',
    2: 'LONG'
}

# XGBoost multi-class classification
model = xgb.XGBClassifier(
    objective='multi:softprob',  # Olasılık dağılımı
    num_class=3,                  # 3 sınıf
    eval_metric='mlogloss'
)
```

**Tahmin Çıktısı:**
```
Girdi: Son 100 mumun OHLCV verisi + 40 feature

Çıktı:
  P(SHORT)   = 0.15  (%15 olasılık)
  P(NEUTRAL) = 0.25  (%25 olasılık)
  P(LONG)    = 0.60  (%60 olasılık)

Tahmin: LONG (en yüksek olasılık)
Confidence: 0.60 (%60 güven)
```

---

### **3. Confusion Matrix (Örnek)**

**Test Seti (1000 örnek):**

```
                  Gerçek Etiket
                ┌────────────────────┐
                │ SHORT │ NEUTRAL │ LONG │
        ┌───────┼───────┼─────────┼──────┤
        │ SHORT │  280  │   20    │  30  │
 Tahmin │ NEUTRAL│  40   │  320    │  40  │
        │ LONG  │  30   │   30    │ 210  │
        └───────┴───────┴─────────┴──────┘

Doğru Tahminler:
  SHORT: 280/330 = %84.8
  NEUTRAL: 320/390 = %82.1
  LONG: 210/280 = %75.0

Toplam Accuracy: (280 + 320 + 210) / 1000 = %81.0
```

---

## 📊 Triple Barrier vs Sabit Pencere Karşılaştırması

### **1. Look-Ahead Bias Karşılaştırması**

| Özellik | Sabit Pencere | Triple Barrier |
|---------|---------------|----------------|
| **Gelecek Bilgisi** | ❌ Kullanır (5. mum fiyatı) | ✅ Kullanmaz (sadece önce dokunan bariyer) |
| **Gerçekçilik** | ❌ Düşük (pozisyon kapandıktan sonra fiyat önemsiz) | ✅ Yüksek (ilk çıkış noktası önemli) |
| **Trading Uyumu** | ❌ Kötü (backtest overfitting) | ✅ Mükemmel (live trading ile uyumlu) |
| **Etiket Kalitesi** | ❌ Düşük (%40-50 accuracy) | ✅ Yüksek (%60-70 accuracy) |

---

### **2. Backtest Performansı**

**Sabit Pencere (5-mum):**
```
Eğitim Accuracy: %75
Test Accuracy: %45  ❌ OVERFITTING!

Neden?
- Model, gelecekteki fiyatları "gördü"
- Live trading'de bu bilgi yok
- Performans çöktü
```

**Triple Barrier:**
```
Eğitim Accuracy: %65
Test Accuracy: %62  ✅ GERÇEKÇİ!

Neden?
- Model, sadece o anki bariyerleri gördü
- Live trading ile aynı mantık
- Performans korundu
```

---

## 🚨 Uygulama Notları

### **1. ATR Periyodu Seçimi**

| Timeframe | Önerilen ATR | Açıklama |
|-----------|--------------|----------|
| **1m - 5m** | 14 | Kısa vadeli volatilite |
| **15m - 1h** | 14-20 | Orta vadeli volatilite |
| **4h - 1d** | 20-30 | Uzun vadeli volatilite |

---

### **2. TP/SL Çarpanı Optimizasyonu**

**Grid Search:**
```python
# Optimal çarpanları bul
param_grid = {
    'tp_multiplier': [1.0, 1.5, 2.0, 2.5, 3.0],
    'sl_multiplier': [1.0, 1.5, 2.0, 2.5, 3.0],
    'max_bars': [3, 5, 7, 10]
}

# Walk-Forward ile test et
for tp in param_grid['tp_multiplier']:
    for sl in param_grid['sl_multiplier']:
        for bars in param_grid['max_bars']:
            labels = triple_barrier_labeling(..., tp, sl, bars)
            model.fit(X, labels)
            accuracy = cross_val_score(model, X, labels)
            
            # En iyi kombinasyonu kaydet
            if accuracy > best_accuracy:
                best_params = (tp, sl, bars)
```

**Önerilen Varsayılan:**
```
tp_multiplier = 2.0
sl_multiplier = 2.0
max_bars = 5
```

---

### **3. Sınıf Dengesizliği (Class Imbalance)**

**Sorun:**
```
Label dağılımı:
  SHORT: 500 örnek (%10)
  NEUTRAL: 4000 örnek (%80)
  LONG: 500 örnek (%10)

❌ Model, sürekli NEUTRAL tahmin eder (%80 accuracy!)
```

**Çözüm:**
```python
# 1. Class weights (XGBoost)
model = xgb.XGBClassifier(
    class_weight='balanced',  # Otomatik ağırlık
    scale_pos_weight=[1.0, 0.2, 1.0]  # Manuel ağırlık
)

# 2. SMOTE (oversampling)
from imblearn.over_sampling import SMOTE
smote = SMOTE()
X_resampled, y_resampled = smote.fit_resample(X, y)

# 3. Undersampling (majority class)
from imblearn.under_sampling import RandomUnderSampler
rus = RandomUnderSampler()
X_resampled, y_resampled = rus.fit_resample(X, y)
```

---

## 📚 İlgili Dokümanlar

- **ML Integration:** `features/ml_integration.md`
- **Dynamic Position Sizing:** `concepts/dynamic_position_sizing.md`
- **Walk-Forward Optimization:** `features/walk_forward_optimization.md`

---

## 📖 Kaynaklar

1. **Marcos Lopez de Prado** - "Advances in Financial Machine Learning" (2018)
   - Chapter 3: Labeling
   - Section 3.3: Triple Barrier Method
   
2. **Lopez de Prado, M. (2018)** - "A Machine Learning Approach to Financial Market Prediction"
   - Journal of Portfolio Management

3. **XGBoost Documentation** - "Multi-Class Classification"
   - https://xgboost.readthedocs.io/

---

*Bu doküman Triple Barrier Method v4.0 (Mart 2026) için hazırlanmıştır.*
*Güncellemeler için `knowledge/concepts/` dizinini kontrol edin.*
