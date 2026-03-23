import pandas as pd
import numpy as np
try:
    import pandas_ta as ta
except ImportError:
    try:
        import pandas_ta_classic as ta
    except ImportError:
        ta = None

class MarketRegimeDetector:
    """
    Piyasa Rejimi Dedektörü (Trend mi? Yatay mı?)
    
    Bu sınıf, piyasanın o anki yapısını analiz ederek botların hangi stratejiyle
    daha verimli çalışabileceğine dair veri üretir.
    """
    
    @staticmethod
    def detect_regime(df: pd.DataFrame) -> dict:
        """
        Verilen DataFrame üzerinden piyasa rejimini analiz eder.
        """
        if df.empty or len(df) < 30:
            return {"regime": "UNKNOWN", "trend_strength": 0}

        latest = df.iloc[-1]
        
        # 1. ADX (Trend Gücü)
        # ADX > 25 ise trend var kabul edilir.
        adx_val = latest.get('ADX_14', 0)
        
        # 2. VHF (Vertical Horizontal Filter)
        # VHF, fiyat hareketinin ne kadarının trende dayalı olduğunu ölçer.
        # Yüksek değer = Güçlü Trend.
        try:
            vhf = ta.vhf(df['close'], length=28).iloc[-1]
        except:
            vhf = 0.5 # Default orta değer
            
        # 3. Bollinger Band Width (Squeeze kontrolü)
        # Bandlar daralmışsa patlama (Trend başlangıcı) yakındır, yatay piyasa sonudur.
        bbw = 0
        try:
            val_u = latest.get('BBU_20_2.0_2.0')
            val_l = latest.get('BBL_20_2.0_2.0')
            
            # Değerlerin hem mevcut hem de sayısal (NaN/None değil) olduğunu doğrula
            if val_u is not None and val_l is not None and not np.isnan(val_u) and not np.isnan(val_l):
                bbw = (val_u - val_l) / latest['close']
        except Exception:
            bbw = 0.05 # Hata durumunda nötr bir genişlik ata

        # --- KARAR MANTIĞI ---
        regime = "RANGING" # Varsayılan: Yatay / Testere
        
        # ADX ve VHF eşik değerleri (Literatürde genellikle 25 ve 0.40 civarıdır)
        if adx_val > 23 and vhf > 0.35:
            # Trend var, peki yön ne?
            if latest['close'] > latest.get('EMA_50', latest['close']):
                regime = "TRENDING_BULL"
            else:
                regime = "TRENDING_BEAR"
        elif bbw < 0.02: # Çok dar bant (Squeeze)
            regime = "SQUEEZE_PRE_TREND"

        return {
            "regime": regime,
            "trend_strength": round(adx_val, 2),
            "vhf": round(vhf, 3),
            "bbw": round(bbw, 4)
        }
