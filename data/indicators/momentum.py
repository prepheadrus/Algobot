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
    def uo(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        fast: int = 7,
        medium: int = 14,
        slow: int = 28
    ) -> pd.Series:
        """
        Ultimate Oscillator
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            fast: Fast periyot
            medium: Medium periyot
            slow: Slow periyot
        
        Returns:
            UO serisi
        """
        # Buying pressure ve true range
        bp = close - pd.concat([low, close.shift(1)], axis=1).min(axis=1)
        tr = pd.concat([high - low,
                       abs(high - close.shift(1)),
                       abs(low - close.shift(1))], axis=1).max(axis=1)
        
        # Averages
        avg_fast = bp.rolling(window=fast).sum() / tr.rolling(window=fast).sum()
        avg_medium = bp.rolling(window=medium).sum() / tr.rolling(window=medium).sum()
        avg_slow = bp.rolling(window=slow).sum() / tr.rolling(window=slow).sum()
        
        # Ultimate Oscillator
        return 100 * (4 * avg_fast + 2 * avg_medium + avg_slow) / (4 + 2 + 1)
    
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
    def cci(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        period: int = 20
    ) -> pd.Series:
        """
        Commodity Channel Index
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            period: Periyot
        
        Returns:
            CCI serisi
        """
        tp = (high + low + close) / 3
        sma = tp.rolling(period).mean()
        mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean())
        return (tp - sma) / (0.015 * mad)
