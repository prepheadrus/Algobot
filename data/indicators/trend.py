"""
Trend Indicators

Trend tabanlı teknik indikatörler:
- EMA (Exponential Moving Average)
- SMA (Simple Moving Average)
- Supertrend
- ADX (Average Directional Index)
- Kalman Filter
- Parabolic SAR
"""

import pandas as pd
import numpy as np


class TrendIndicators:
    """Trend indikatörleri"""
    
    @staticmethod
    def ema(series: pd.Series, length: int) -> pd.Series:
        """
        Exponential Moving Average
        
        Args:
            series: Fiyat serisi
            length: Periyot
        
        Returns:
            EMA serisi
        """
        return series.ewm(span=length, adjust=False).mean()
    
    @staticmethod
    def sma(series: pd.Series, length: int) -> pd.Series:
        """
        Simple Moving Average
        
        Args:
            series: Fiyat serisi
            length: Periyot
        
        Returns:
            SMA serisi
        """
        return series.rolling(window=length).mean()
    
    @staticmethod
    def supertrend(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        multiplier: float = 3.0,
        period: int = 10
    ) -> tuple:
        """
        SuperTrend indikatörü
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            multiplier: ATR çarpanı
            period: ATR periyodu
        
        Returns:
            (supertrend, direction) tuple
        """
        # ATR hesapla
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.ewm(span=period, adjust=False).mean()
        
        # Temel bantlar
        hl2 = (high + low) / 2
        upper_band = hl2 + multiplier * atr
        lower_band = hl2 - multiplier * atr
        
        # SuperTrend yönü
        supertrend = pd.Series(index=close.index)
        direction = pd.Series(1, index=close.index)  # 1 = yukarı, -1 = aşağı
        
        for i in range(1, len(close)):
            if close.iloc[i] > supertrend.iloc[i-1] if i > 0 and pd.notna(supertrend.iloc[i-1]) else True:
                direction.iloc[i] = 1
                supertrend.iloc[i] = lower_band.iloc[i]
            elif close.iloc[i] < supertrend.iloc[i-1] if i > 0 and pd.notna(supertrend.iloc[i-1]) else False:
                direction.iloc[i] = -1
                supertrend.iloc[i] = upper_band.iloc[i]
            else:
                direction.iloc[i] = direction.iloc[i-1] if i > 0 else 1
                if direction.iloc[i] == 1:
                    supertrend.iloc[i] = max(lower_band.iloc[i], supertrend.iloc[i-1] if i > 0 and pd.notna(supertrend.iloc[i-1]) else lower_band.iloc[i])
                else:
                    supertrend.iloc[i] = min(upper_band.iloc[i], supertrend.iloc[i-1] if i > 0 and pd.notna(supertrend.iloc[i-1]) else upper_band.iloc[i])
        
        return supertrend, direction
    
    @staticmethod
    def adx(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> tuple:
        """
        Average Directional Index
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            period: Periyot
        
        Returns:
            (ADX, +DI, -DI) tuple
        """
        # DM hesapla
        plus_dm = high.diff()
        minus_dm = -low.diff()
        plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
        minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)

        # TR hesapla
        tr = np.maximum(high - low,
                       np.maximum(abs(high - close.shift(1)),
                                 abs(low - close.shift(1))))

        # Smooth - INDEX UYUMLULUĞU
        tr_smooth = pd.Series(tr, index=high.index).rolling(period).sum()
        plus_dm_smooth = pd.Series(plus_dm, index=high.index).rolling(period).sum()
        minus_dm_smooth = pd.Series(minus_dm, index=high.index).rolling(period).sum()
        
        # DI hesapla (index uyumlu)
        plus_di = 100 * plus_dm_smooth / tr_smooth
        minus_di = 100 * minus_dm_smooth / tr_smooth
        
        # DX ve ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean()
        
        return adx, plus_di, minus_di
    
    @staticmethod
    def kalman_filter(
        src: pd.Series,
        high: pd.Series = None,
        low: pd.Series = None,
        close: pd.Series = None,
        alpha: float = 0.015,
        beta: float = 0.12,
        period: int = 65,
        use_dynamic_beta: bool = True
    ) -> pd.Series:
        """
        Logaritmik Sönümlemeli Dinamik Kalman Filter

        Siyah Kuğu (Black Swan) anlarında filtrenin donup kalmasını (flatline)
        engellemek için beta (R) parametresini ATR volatilitesine göre
        logaritmik sönümleme ile dinamikleştirir.

        Formül:
            R_dynamic = R_base * max(1, math.log(ATR_current / ATR_mean))

        Args:
            src: Kaynak seri (genellikle close fiyatları)
            high: Yüksek fiyatlar (ATR hesaplaması için)
            low: Düşük fiyatlar (ATR hesaplaması için)
            close: Kapanış fiyatları (ATR hesaplaması için)
            alpha: Alpha parametresi (sabit)
            beta: Beta parametresi (baz değer)
            period: Periyot
            use_dynamic_beta: Dinamik beta kullanılsın mı?

        Returns:
            Kalman filtered seri
        """
        import math

        # Dinamik beta hesaplaması için ATR gerekli
        if use_dynamic_beta and high is not None and low is not None and close is not None:
            # ATR hesapla (14 periyot)
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.ewm(span=14, adjust=False).mean()

            # ATR_mean (son 65 periyodun hareketli ortalaması)
            atr_mean = atr.rolling(window=period).mean()

            # Logaritmik sönümleme
            # ATR_current / ATR_mean > 1 ise (volatilite arttı) -> beta artar
            # ATR_current / ATR_mean < 1 ise (volatilite düştü) -> beta sabit kalır
            atr_ratio = atr / atr_mean
            log_dampening = atr_ratio.apply(lambda x: max(1, math.log(x)) if x > 0 and not pd.isna(x) else 1)
            dynamic_beta = beta * log_dampening
        else:
            # Statik beta (geleneksel Kalman)
            dynamic_beta = pd.Series(beta, index=src.index)

        # Kalman Filter uygulaması
        v1, v2 = src.iloc[0], 1.0
        v3 = alpha * period
        res = []

        for i, val in enumerate(src):
            v4 = v2 / (v2 + v3)
            v1 = v1 + v4 * (val - v1)

            # Dinamik beta kullan
            if use_dynamic_beta and i < len(dynamic_beta):
                current_beta = dynamic_beta.iloc[i]
                if not pd.isna(current_beta):
                    v2 = (1 - v4) * v2 + current_beta / period
                else:
                    v2 = (1 - v4) * v2 + beta / period
            else:
                v2 = (1 - v4) * v2 + beta / period

            res.append(v1)

        return pd.Series(res, index=src.index)
    
    @staticmethod
    def psar(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series = None,
        af0: float = 0.02,
        af: float = 0.02,
        max_af: float = 0.2
    ) -> tuple:
        """
        Parabolic SAR
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları (opsiyonel)
            af0: Initial acceleration factor
            af: Acceleration factor step
            max_af: Maximum acceleration factor
        
        Returns:
            (PSAR, direction) tuple
        """
        if close is None:
            close = (high + low) / 2
        
        psar = pd.Series(index=close.index)
        trend = pd.Series(1, index=close.index)  # 1 = up, -1 = down
        ep = pd.Series(0.0, index=close.index)  # Extreme point
        accel = pd.Series(af0, index=close.index)
        
        # İlk değerler
        psar.iloc[0] = low.iloc[0]
        ep.iloc[0] = high.iloc[0]
        
        for i in range(1, len(close)):
            psar.iloc[i] = psar.iloc[i-1] + accel.iloc[i-1] * (ep.iloc[i-1] - psar.iloc[i-1])
            
            if trend.iloc[i-1] == 1:  # Uptrend
                if low.iloc[i] > psar.iloc[i]:
                    trend.iloc[i] = 1
                    if high.iloc[i] > ep.iloc[i-1]:
                        ep.iloc[i] = high.iloc[i]
                        accel.iloc[i] = min(accel.iloc[i-1] + af, max_af)
                    else:
                        ep.iloc[i] = ep.iloc[i-1]
                        accel.iloc[i] = accel.iloc[i-1]
                else:
                    trend.iloc[i] = -1
                    psar.iloc[i] = ep.iloc[i-1]
                    ep.iloc[i] = low.iloc[i]
                    accel.iloc[i] = af0
            else:  # Downtrend
                if high.iloc[i] < psar.iloc[i]:
                    trend.iloc[i] = -1
                    if low.iloc[i] < ep.iloc[i-1]:
                        ep.iloc[i] = low.iloc[i]
                        accel.iloc[i] = min(accel.iloc[i-1] + af, max_af)
                    else:
                        ep.iloc[i] = ep.iloc[i-1]
                        accel.iloc[i] = accel.iloc[i-1]
                else:
                    trend.iloc[i] = 1
                    psar.iloc[i] = ep.iloc[i-1]
                    ep.iloc[i] = high.iloc[i]
                    accel.iloc[i] = af0
        
        return psar, trend
