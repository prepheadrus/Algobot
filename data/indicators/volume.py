"""
Volume Indicators

Hacim tabanlı teknik indikatörler:
- OBV (On Balance Volume)
- VWAP (Volume Weighted Average Price)
- MFI (Money Flow Index)
- PVI (Positive Volume Index)
- NVI (Negative Volume Index)
"""

import pandas as pd
import numpy as np


class VolumeIndicators:
    """Volume indikatörleri"""
    
    @staticmethod
    def vwap(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series
    ) -> pd.Series:
        """
        Volume Weighted Average Price
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            volume: Hacim
        
        Returns:
            VWAP serisi
        """
        typical_price = (high + low + close) / 3
        return (typical_price * volume).cumsum() / volume.cumsum()
    
    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        On Balance Volume
        
        Args:
            close: Kapanış fiyatları
            volume: Hacim
        
        Returns:
            OBV serisi
        """
        direction = np.sign(close.diff())
        direction.iloc[0] = 0
        return (direction * volume).fillna(0).cumsum()
    
    @staticmethod
    def mfi(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Money Flow Index
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            volume: Hacim
            period: Periyot
        
        Returns:
            MFI serisi
        """
        typical_price = (high + low + close) / 3
        money_flow = typical_price * volume
        
        # Positive/Negative Money Flow
        tpp = typical_price.diff()
        pmf = pd.Series(0.0, index=close.index)
        nmf = pd.Series(0.0, index=close.index)
        
        pmf[tpp > 0] = money_flow[tpp > 0]
        nmf[tpp < 0] = money_flow[tpp < 0]
        
        # Money Ratio
        mr = pmf.rolling(window=period).sum() / nmf.rolling(window=period).sum()
        
        # MFI
        return 100 - (100 / (1 + mr))
    
    @staticmethod
    def pvi(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Positive Volume Index
        
        Args:
            close: Kapanış fiyatları
            volume: Hacim
        
        Returns:
            PVI serisi
        """
        pvi = np.zeros(len(close))
        pvi[0] = 100.0
        
        for i in range(1, len(close)):
            if volume.iloc[i] > volume.iloc[i-1]:
                ret = (close.iloc[i] - close.iloc[i-1]) / (close.iloc[i-1] if close.iloc[i-1] != 0 else 1.0)
                pvi[i] = pvi[i-1] + (ret * volume.iloc[i])
            else:
                pvi[i] = pvi[i-1]
        
        return pd.Series(pvi, index=close.index)
    
    @staticmethod
    def nvi(close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Negative Volume Index
        
        Args:
            close: Kapanış fiyatları
            volume: Hacim
        
        Returns:
            NVI serisi
        """
        nvi = np.zeros(len(close))
        nvi[0] = 100.0
        
        for i in range(1, len(close)):
            if volume.iloc[i] < volume.iloc[i-1]:
                ret = (close.iloc[i] - close.iloc[i-1]) / (close.iloc[i-1] if close.iloc[i-1] != 0 else 1.0)
                nvi[i] = nvi[i-1] + (ret * volume.iloc[i])
            else:
                nvi[i] = nvi[i-1]
        
        return pd.Series(nvi, index=close.index)
    
    @staticmethod
    def cmf(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        period: int = 20
    ) -> pd.Series:
        """
        Chaikin Money Flow
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            volume: Hacim
            period: Periyot
        
        Returns:
            CMF serisi
        """
        mfm = ((close - low) - (high - close)) / (high - low)
        mfv = mfm * volume
        return mfv.rolling(period).sum() / volume.rolling(period).sum()
    
    @staticmethod
    def adl(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """
        Accumulation/Distribution Line
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            volume: Hacim
        
        Returns:
            ADL serisi
        """
        clv = ((close - low) - (high - close)) / (high - low)
        return (clv * volume).cumsum()
    
    @staticmethod
    def fi(close: pd.Series, volume: pd.Series, period: int = 13) -> pd.Series:
        """
        Force Index
        
        Args:
            close: Kapanış fiyatları
            volume: Hacim
            period: Periyot
        
        Returns:
            Force Index serisi
        """
        fi = close.diff() * volume
        return fi.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def eom(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Ease of Movement
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            volume: Hacim
            period: Periyot
        
        Returns:
            EOM serisi
        """
        high_low = high - low
        distance = ((close + close.shift(1)) / 2) - ((close.shift(1) + close.shift(2)) / 2)
        box_ratio = volume / high_low
        eom = distance / box_ratio
        return eom.rolling(period).mean()
