# STRATEGIES BILGI BANKASI
Son Guncelleme: 08/03/2026 22:58

---



## KAYNAK DOSYA: concept_and_implementation.md

# 📐 Strateji Konseptleri ve Tasarım Modeli

Stratejiler botun "beyni" olmak yerine "kurallar listesini" temsil ederler. Beyin rolünü Yapay Zeka modeli yürütür. Bu sayede modüler bir mimari kurgulanmıştır.

## 1. İndikatör Ailesi Çatışmaları Önleme (Multicollinearity)

Piyasada uygulanan acemi stratejiler (RSI, Stoch, W%R'ı aynı anda kullanmak vb.) strateji mimarimizden tamamen dışlanmıştır.

Stratejilerimiz Temel Prensip olarak şu üçlü teyit mekanizmasını şart koşar:
- **Yön Bulucu:** MACD, Hareketli Ortalamalar (EMA/SMA)
- **Trend/Momentum Gücü:** ADX, RSI (Kendi özel sınırlarına göre)
- **Hacim Desteği:** OBV, VWAP, Koncorde (Kurumsal para girişi)

## 2. Mevcut Stratejilerimiz

1. **Trend Master Pro:** `SMA 20`, `EMA 200` ve `RSI 50+` ile 1 dakikalık trend takibi yapar. Son derece katıdır, EMA 200 altındaysa "AL" demez. Güvenlidir.
2. **Scalper Ninja:** Kısa periyotlar için tasarlanmış tepki botudur. `RSI 30 altı` + `Stochastic < 20 (Aşırı satım)` onayları ile dibi yakalar.
3. **Adaptive Koncorde X:** İspanyol Koncorde hacim osilatörü ile geliştirilmiştir. "Retail (Küçük Yatırımcı)" çıkıp "Azul (Balina - Kurumsal Para)" girdiğinde ve RSI gizli pozitif uyumsuzluk (veya güçlü zemin) yarattığında çalışır.
4. **Golden Combo:** Kaynak kitaba uygun %100 doğrulama serisidir. **Sıfırın üstünde MACD + `EMA(5) > SMA(20)` Kesişimi + Yükselen `ADX > 20` + `OBV > OBV_EMA` (Hacim rekoru)** aynı anda varsa tepki verir. Savaş kazanma oranı (Win-rate) teorik olarak çok yüksektir.
5. **Divergence Hunter:** Demand Index, Ultimate Oscillator, ADX ve PSAR indikatörlerinden oluşan uyumsuzluk avcısı.
6. **KNN Quant:** K-Nearest Neighbors tabanlı nicel tahmin stratejisi.

## 3. Yeni Strateji Ekleme Rehberi

### Adım 1: İndikatörü `data/indicators.py`'ye Ekle

```python
# Manuel indikatör hesaplama (pandas-ta gerektirmez)
@staticmethod
def yeni_indikator(df):
    """Yeni indikatör formülü"""
    # numpy/pandas ile hesapla
    return result
```

### Adım 2: Strateji Dosyası Oluştur

```python
# strategy/yeni_strateji.py
from strategy.base import BaseStrategy

class YeniStrateji(BaseStrategy):
    def name(self) -> str:
        return "Yeni Strateji"

    def generate_signal(self, current_row: pd.Series) -> int:
        # 2: LONG, 0: SHORT, 1: HOLD
        pass

    def get_stop_params(self):
        return {"atr_multiplier": 2.0, "tp_multiplier": 3.0}
```

### Adım 3: `strategy/manager.py`'ye Kaydet

```python
from strategy.yeni_strateji import YeniStrateji

class StrategyManager:
    STRATEGIES = {
        "yeni_strateji": YeniStrateji(),
        # ... diğer stratejiler
    }
```

## 4. Strateji Şablonları

### Örnek: RSI + EMA Kesişimi

```python
from strategy.base import BaseStrategy

class RSI_EMA_Strategy(BaseStrategy):
    def name(self) -> str:
        return "RSI EMA Crossover"

    def description(self) -> str:
        return "RSI aşırı alım/satım + EMA kesişimi."

    def generate_signal(self, current_row: pd.Series) -> int:
        rsi = current_row['RSI_14']
        ema5 = current_row['EMA_5']
        ema20 = current_row['EMA_20']

        # LONG: RSI < 30 + EMA 5 > EMA 20
        if rsi < 30 and ema5 > ema20:
            return 2

        # SHORT: RSI > 70 + EMA 5 < EMA 20
        if rsi > 70 and ema5 < ema20:
            return 0

        return 1

    def get_stop_params(self):
        return {"atr_multiplier": 2.0, "tp_multiplier": 2.5}
```


---
