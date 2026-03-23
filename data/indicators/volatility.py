"""
Volatility Indicators

Oynaklık tabanlı teknik indikatörler:
- ATR (Average True Range)
- Bollinger Bands
- BTC VIX (Volatility Index)
- Keltner Channels
"""

import pandas as pd
import numpy as np


class VolatilityIndicators:
    """Volatility indikatörleri"""
    
    @staticmethod
    def atr(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        length: int = 14
    ) -> pd.Series:
        """
        Average True Range
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            length: Periyot
        
        Returns:
            ATR serisi
        """
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.ewm(span=length, adjust=False).mean()
    
    @staticmethod
    def bollinger_bands(
        series: pd.Series,
        length: int = 20,
        std: float = 2
    ) -> tuple:
        """
        Bollinger Bands
        
        Args:
            series: Fiyat serisi
            length: Periyot
            std: Standart sapma çarpanı
        
        Returns:
            (upper, middle, lower) tuple
        """
        sma = series.rolling(window=length).mean()
        std_dev = series.rolling(window=length).std()
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        return upper, sma, lower
    
    @staticmethod
    def bollinger_width(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        length: int = 20,
        std: float = 2
    ) -> pd.Series:
        """
        Bollinger Band Width
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            length: Periyot
            std: Standart sapma çarpanı
        
        Returns:
            Band width serisi
        """
        upper, middle, lower = VolatilityIndicators.bollinger_bands(close, length, std)
        return (upper - lower) / middle
    
    @staticmethod
    def bollinger_percent_b(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        length: int = 20,
        std: float = 2
    ) -> pd.Series:
        """
        Bollinger %B
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            length: Periyot
            std: Standart sapma çarpanı
        
        Returns:
            %B serisi
        """
        upper, middle, lower = VolatilityIndicators.bollinger_bands(close, length, std)
        return (close - lower) / (upper - lower)
    
    @staticmethod
    def btc_vix(close: pd.Series, period: int = 20) -> pd.Series:
        """
        BTC Volatility Index (VIX)
        
        Formül: ta.stdev(math.log(close/close[1]), 20) * math.sqrt(365) * 100
        
        Args:
            close: Kapanış fiyatları
            period: Periyot
        
        Returns:
            BTC VIX serisi
        """
        log_ret = np.log(close / close.shift(1))
        return log_ret.rolling(period).std() * np.sqrt(365) * 100
    
    @staticmethod
    def keltner_channels(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        ema_period: int = 20,
        atr_period: int = 10,
        multiplier: float = 2.0
    ) -> tuple:
        """
        Keltner Channels
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            ema_period: EMA periyodu
            atr_period: ATR periyodu
            multiplier: ATR çarpanı
        
        Returns:
            (upper, middle, lower) tuple
        """
        # EMA (middle)
        middle = close.ewm(span=ema_period, adjust=False).mean()
        
        # ATR
        atr = VolatilityIndicators.atr(high, low, close, atr_period)
        
        # Bands
        upper = middle + (multiplier * atr)
        lower = middle - (multiplier * atr)
        
        return upper, middle, lower
    
    @staticmethod
    def donchian_channels(
        high: pd.Series,
        low: pd.Series,
        period: int = 20
    ) -> tuple:
        """
        Donchian Channels
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            period: Periyot
        
        Returns:
            (upper, middle, lower) tuple
        """
        upper = high.rolling(period).max()
        lower = low.rolling(period).min()
        middle = (upper + lower) / 2
        return upper, middle, lower
    
    @staticmethod
    def historical_volatility(close: pd.Series, period: int = 30, annualize: bool = True) -> pd.Series:
        """
        Historical Volatility
        
        Args:
            close: Kapanış fiyatları
            period: Periyot
            annualize: Yıllık hesaplama
        
        Returns:
            Historical volatility serisi
        """
        log_ret = np.log(close / close.shift(1))
        hv = log_ret.rolling(period).std()
        
        if annualize:
            hv = hv * np.sqrt(365)
        
        return hv
