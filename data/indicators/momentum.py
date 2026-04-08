"""
Momentum Indicators

Momentum tabanlı teknik indikatörler:
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Stochastic Oscillator
- UO (Ultimate Oscillator)
"""

import pandas as pd
import numpy as np


class MomentumIndicators:
    """Momentum indikatörleri"""
    
    @staticmethod
    def cmo(series: pd.Series, **kwargs) -> pd.DataFrame:
        """
        Chande Momentum Oscillator (CMO)

        CMO = 100 * (SumUp - SumDown) / (SumUp + SumDown)

        Args:
            series: Fiyat serisi (close)
            **kwargs: Ek parametreler (period vb.)

        Returns:
            cmo ve cmo_signal içeren DataFrame
        """
        period = kwargs.get('period', 14)

        # Farkları hesapla
        diff = series.diff()

        # Yukarı ve aşağı yönlü farklar
        up = diff.clip(lower=0)
        down = -1 * diff.clip(upper=0)

        # Vektörize toplamlar
        sum_up = up.rolling(window=period).sum()
        sum_down = down.rolling(window=period).sum()

        # Payda koruması (Sıfıra bölünme ve yatay piyasa kalkanı)
        total_movement = (sum_up + sum_down).replace([np.inf, -np.inf, 0], np.nan)

        # CMO hesaplaması ve NaN değerlerin sıfırlanması (warm-up bar kalkanı)
        cmo = 100 * (sum_up - sum_down) / total_movement
        cmo = cmo.fillna(0)

        # Sinyal Matrisi
        cmo_signal = np.where(cmo > 0, 2, np.where(cmo < 0, 0, 1))

        return pd.DataFrame({
            'cmo': cmo,
            'cmo_signal': cmo_signal
        }, index=series.index)

    @staticmethod
    def bulls_power(high: pd.Series, close: pd.Series, **kwargs) -> pd.DataFrame:
        """
        Bulls Power (Elder Ray Index)

        Bulls Power = High - EMA(Close, period)

        Args:
            high: Yüksek fiyatlar
            close: Kapanış fiyatları
            **kwargs: Ek parametreler (period vb.)

        Returns:
            bull_power ve bull_power_signal içeren DataFrame
        """
        period = kwargs.get('period', 13)

        # 100% Vektörize EMA hesabı
        ema = close.ewm(span=period, adjust=False).mean()

        # Bulls Power
        bull_power = high - ema

        # Data Integrity Kalkanı
        bull_power = bull_power.replace([np.inf, -np.inf], np.nan).fillna(0)

        # Sinyal Matrisi Çıktısı (0, 1, 2)
        bull_power_signal = np.where(bull_power > 0, 2, np.where(bull_power < 0, 0, 1))

        return pd.DataFrame({
            'bull_power': bull_power,
            'bull_power_signal': bull_power_signal
        }, index=close.index)

    @staticmethod
    def rsi(series: pd.Series, length: int = 14) -> pd.Series:
        """
        Relative Strength Index
        
        Args:
            series: Fiyat serisi
            length: Periyot
        
        Returns:
            RSI serisi
        """
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def macd(
        series: pd.Series,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> tuple:
        """
        MACD (Moving Average Convergence Divergence)
        
        Args:
            series: Fiyat serisi
            fast: Fast EMA periyodu
            slow: Slow EMA periyodu
            signal: Signal line periyodu
        
        Returns:
            (macd_line, signal_line, histogram) tuple
        """
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        hist = macd_line - signal_line
        return macd_line, signal_line, hist
    
    @staticmethod
    def stochastic(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        k: int = 14,
        d: int = 3,
        smooth_k: int = 3
    ) -> tuple:
        """
        Stochastic Oscillator
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            k: %K periyodu
            d: %D periyodu
            smooth_k: %K smoothing
        
        Returns:
            (%K, %D) tuple
        """
        lowest_low = low.rolling(k).min()
        highest_high = high.rolling(k).max()
        stoch_k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        stoch_d = stoch_k.rolling(smooth_k).mean()
        return stoch_k, stoch_d
    
    @staticmethod
    def ultimate_oscillator(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        **kwargs
    ) -> pd.DataFrame:
        """
        Ultimate Oscillator (Vectorized)

        Larry Williams'ın üç farklı zaman periyodunu birleştirerek oluşturduğu,
        aşırı alım/satım hatalarını sıfırlayan momentum algoritması.

        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            **kwargs: Ek parametreler (timeframe1, timeframe2, timeframe3, overbought, oversold)

        Returns:
            uo_val ve uo_signal içeren DataFrame
        """
        timeframe1 = kwargs.get('uo_timeframe1', 7)
        timeframe2 = kwargs.get('uo_timeframe2', 14)
        timeframe3 = kwargs.get('uo_timeframe3', 28)
        overbought = kwargs.get('uo_overbought', 70.0)
        oversold = kwargs.get('uo_oversold', 30.0)

        # Vectorized Math
        min_low_close = np.minimum(low, close.shift(1))
        max_high_close = np.maximum(high, close.shift(1))

        # Buying Pressure (BP) and True Range (TR)
        bp = close - min_low_close
        tr = max_high_close - min_low_close

        # Rolling sums with zero-division protection
        avg1 = bp.rolling(timeframe1).sum() / tr.rolling(timeframe1).sum().replace(0, np.nan)
        avg2 = bp.rolling(timeframe2).sum() / tr.rolling(timeframe2).sum().replace(0, np.nan)
        avg3 = bp.rolling(timeframe3).sum() / tr.rolling(timeframe3).sum().replace(0, np.nan)

        # UO Formula
        uo_val = 100 * ((4 * avg1) + (2 * avg2) + (1 * avg3)) / 7

        # Signal Matrix: UO > overbought -> 0 (SHORT), UO < oversold -> 2 (LONG), else 1 (NEUTRAL)
        uo_signal = np.where(uo_val > overbought, 0, np.where(uo_val < oversold, 2, 1))

        # Data Integrity Shield
        uo_val = uo_val.replace([np.inf, -np.inf], np.nan).fillna(50.0)

        return pd.DataFrame({
            'uo_val': uo_val,
            'uo_signal': uo_signal
        }, index=close.index)

    @staticmethod
    def uo(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        fast: int = 7,
        medium: int = 14,
        slow: int = 28
    ) -> pd.Series:
        """
        Legacy Ultimate Oscillator Wrapper for backward compatibility.
        """
        return MomentumIndicators.ultimate_oscillator(
            high, low, close,
            uo_timeframe1=fast, uo_timeframe2=medium, uo_timeframe3=slow
        )['uo_val']
    
    @staticmethod
    def williams_r(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 14
    ) -> pd.Series:
        """
        Williams %R
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            period: Periyot
        
        Returns:
            Williams %R serisi
        """
        highest_high = high.rolling(period).max()
        lowest_low = low.rolling(period).min()
        return -100 * (highest_high - close) / (highest_high - lowest_low)
    
    @staticmethod
    def roc(series: pd.Series, period: int = 10) -> pd.Series:
        """
        Rate of Change
        
        Args:
            series: Fiyat serisi
            period: Periyot
        
        Returns:
            ROC serisi
        """
        return ((series - series.shift(period)) / series.shift(period)) * 100
    
    @staticmethod
    def bear_power(low: pd.Series, close: pd.Series, **kwargs) -> pd.DataFrame:
        """
        Bear Power (Elder Ray Index)

        Args:
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            **kwargs: Ek parametreler (period vb.)

        Returns:
            bear_power ve bear_power_signal içeren DataFrame
        """
        period = kwargs.get('period', 13)

        ema = close.ewm(span=period, adjust=False).mean()
        bear_power = low - ema

        # Sinyal Matrisi: bear_power < 0 ise 0 (SHORT), > 0 ise 2 (LONG), aksi halde 1 (BEKLE)
        bear_power_signal = np.where(bear_power < 0, 0, np.where(bear_power > 0, 2, 1))

        bear_power = bear_power.replace([np.inf, -np.inf], np.nan).fillna(0)

        return pd.DataFrame({
            'bear_power': bear_power,
            'bear_power_signal': bear_power_signal
        }, index=close.index)

    @staticmethod
    def cci(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        **kwargs
    ) -> pd.DataFrame:
        """
        Commodity Channel Index
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            **kwargs: Ek parametreler (period vb.)
        
        Returns:
            cci ve cci_signal içeren DataFrame
        """
        period = kwargs.get('period', 20)

        tp = (high + low + close) / 3.0
        sma_tp = tp.rolling(window=period, min_periods=1).mean()

        # raw=True ile NumPy C-Array seviyesine inerek performansı artırıyoruz ve Event-Loop bloklanmasını engelliyoruz
        mad = tp.rolling(window=period, min_periods=1).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)

        # Sıfıra Bölünme Koruması
        mad = mad.replace(0, np.nan)

        cci_val = (tp - sma_tp) / (0.015 * mad)

        # Sinyal Matrisi: CCI > 100 ise 0 (SHORT), CCI < -100 ise 2 (LONG), diğerleri 1
        cci_signal = np.where(cci_val > 100, 0, np.where(cci_val < -100, 2, 1))

        cci_val = cci_val.replace([np.inf, -np.inf], np.nan).fillna(0)

        return pd.DataFrame({
            'cci': cci_val,
            'cci_signal': cci_signal
        }, index=close.index)
