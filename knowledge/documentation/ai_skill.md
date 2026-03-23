---
name: Crypto Bot Architecture Skill
description: Comprehending the Crypto Trading Bot's architecture, ML integration, custom indicators, and simulation engine.
---

# Crypto Algo Bot - Development Guidelines & Architecture
Bu döküman ajanın Crypto Bot projesinde nasıl hareket etmesi gerektiğini anlatır.

## Temel Modüller ve Görevleri:
- `api/server.py`: FastAPI ile frontend'e hizmet veren köprü. Model tahminlemesi (XGBoost) ve Backtest Görsel Simülasyonu (Data Preparation) burada çalışır.
- `core/exchange.py`: Binance üzerinden OHLCV çekme, sembolleri tanıma ve PaperTrader'a tick basan döngüler (Poller).
- `core/paper.py`: Komisyonu, kaymayı ve ATR takibini yaparak sanal (Paper) al-sat yapan trade motoru.
- `data/indicators.py`: Tüm teknik analiz matematiğinin tek merkezde yapıldığı yer (pandas_ta, Koncorde, VWAP, ADX, Stoch vb.)
- `strategy/`: Bağımsız, sadece `Close/High` veya `MACD/RSI` sütunlarına bakarak 0(Sell), 1(Hold), 2(Buy) değeri dönen kararlar kutusu. Manager üzerinden yönetilir.
- `frontend/app.js`: Lightweight Charts ile UI etkileşimi. 

## Geliştirme Yaparken Dikkat Edilecekler:
1. **Piyasa Gerçekçiliği**: Asla spread, fee, veya gecikme (slipaj) olmayan ütopik kurallar yaratılmayacak. PaperTrader bunlarla çalışır.
2. **Modülerlik**: Yeni indikatör -> `data/indicators.py`, yeni strateji -> `strategy/yeni_strateji.py` ve ardından `strategy/manager.py` güncellemesi.
3. **Data Integrity (Veri Bütünlüğü)**: API tarafında JSON objelerine gönderilen Python float değerlerinde asla `NaN` veya `Infinity` barındırılamaz. `df.replace([np.inf, -np.inf], np.nan).fillna(0)` yapısı standardtır. Zaman damgaları *her zaman* Milisaniye'ye (ms) `ensure_ms()` ile dönüştürülmelidir.
4. **Grafiksel Düzen**: LWC (Lightweight Chart) üzerindeki karmaşadan kaçınılır. Tooltip üzerinden detaylar aktarılır.
