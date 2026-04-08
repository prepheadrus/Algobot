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
    def btc_vix(low: pd.Series, close: pd.Series, **kwargs) -> pd.DataFrame:
        """
        BTC Volatility Index (Synthetic Crypto VIX)
        
        Williams VIX Fix formülünün optimize edilmiş halidir. Fiyatın son N periyottaki
        en yüksek kapanışından ne kadar saptığını ölçerek piyasadaki korkuyu (Fear) rakamsallaştırır.
        
        Args:
            low: Düşük fiyatlar (pd.Series)
            close: Kapanış fiyatları (pd.Series)
            **kwargs: Ek parametreler
                - period (int): VIX hesaplama periyodu (default: 22)
                - ema_period (int): VIX EMA sinyal hattı periyodu (default: 20)
        
        Returns:
            pd.DataFrame: 'btc_vix', 'vix_ema', 'vix_signal' (0=SHORT, 1=NEUTRAL, 2=LONG) sütunlarını içerir.
        """
        period = kwargs.get('period', 22)
        ema_period = kwargs.get('ema_period', 20)

        # 1. Williams VIX Fix Çekirdeği
        highest_close = close.rolling(window=period).max()

        # Sıfıra bölünmeyi önlemek için, highest_close sıfır olduğunda küçük bir epsilon ekliyoruz,
        # ancak asıl koruma fillna(0) ile yapılıyor.
        btc_vix = 100 * (highest_close - low) / highest_close

        # Veri Bütünlüğü (Data Integrity) Kalkanı: overflow ve sıfıra bölünme hatalarını koru
        btc_vix = btc_vix.replace([np.inf, -np.inf], np.nan).fillna(0)

        # 2. Dinamik Sinyal Hattı
        vix_ema = btc_vix.ewm(span=ema_period, adjust=False).mean()

        # 3. Sinyal Matrisi (0: SHORT/Panik, 2: LONG/Güven, 1: Nötr)
        # btc_vix > vix_ema -> Korku artıyor (Panik satışı, SHORT)
        # btc_vix < vix_ema -> Piyasa sakinleşiyor (LONG onayı)
        vix_signal = np.where(btc_vix > vix_ema, 0, np.where(btc_vix < vix_ema, 2, 1))

        return pd.DataFrame({
            'btc_vix': btc_vix,
            'vix_ema': vix_ema,
            'vix_signal': pd.Series(vix_signal, index=close.index)
        })
    
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
