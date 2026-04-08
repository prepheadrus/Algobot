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
        high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
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
    def obv_ema(close: pd.Series, volume: pd.Series, **kwargs) -> pd.DataFrame:
        """
        On-Balance Volume + EMA (Vectorized)

        Args:
            close: Kapanış fiyatları
            volume: Hacim
            **kwargs: Ek parametreler (ema_period vs.)

        Returns:
            DataFrame: (obv, obv_ema, obv_signal)
        """
        ema_period = kwargs.get("ema_period", 21)

        direction = np.sign(close.diff())
        obv = (direction * volume).cumsum()

        obv_ema = obv.ewm(span=ema_period, adjust=False).mean()

        # Sinyal Matrisi: obv > obv_ema = 2 (LONG), obv < obv_ema = 0 (SHORT), eşit/NaN = 1 (BEKLE)
        obv_signal = np.where(obv > obv_ema, 2, np.where(obv < obv_ema, 0, 1))

        df = pd.DataFrame(
            {"obv": obv, "obv_ema": obv_ema, "obv_signal": obv_signal},
            index=close.index,
        )

        return df.replace([np.inf, -np.inf], np.nan).fillna(0)

    @staticmethod
    def mfi(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        period: int = 14,
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
    def pvi(close: pd.Series, volume: pd.Series, **kwargs) -> pd.DataFrame:
        """
        Positive Volume Index (Vectorized)

        Args:
            close: Kapanış fiyatları
            volume: Hacim
            **kwargs: Ek parametreler (ema_period vs.)

        Returns:
            DataFrame: (pvi, pvi_ema, pvi_signal)
        """
        ema_period = kwargs.get("ema_period", 255)

        price_change = close.pct_change()
        vol_increase = volume > volume.shift(1)
        pvi_pct = np.where(vol_increase, price_change, 0)

        pvi = 1000 * (1 + pd.Series(pvi_pct, index=close.index)).cumprod()

        pvi_ema = pvi.ewm(span=ema_period, adjust=False).mean()

        # Sinyal Matrisi: pvi > pvi_ema = 2 (LONG), pvi < pvi_ema = 0 (SHORT), eşit/NaN = 1 (BEKLE)
        pvi_signal = np.where(pvi > pvi_ema, 2, np.where(pvi < pvi_ema, 0, 1))

        df = pd.DataFrame(
            {"pvi": pvi, "pvi_ema": pvi_ema, "pvi_signal": pvi_signal},
            index=close.index,
        )

        return df.replace([np.inf, -np.inf], np.nan).fillna(0)

    @staticmethod
    def nvi(close: pd.Series, volume: pd.Series, **kwargs) -> pd.DataFrame:
        """
        Negative Volume Index (Vectorized)

        Args:
            close: Kapanış fiyatları
            volume: Hacim
            **kwargs: Ek parametreler (ema_period vs.)

        Returns:
            DataFrame: (nvi, nvi_ema, nvi_signal)
        """
        ema_period = kwargs.get("ema_period", 255)

        price_change = close.pct_change()
        vol_decrease = volume < volume.shift(1)
        nvi_pct = np.where(vol_decrease, price_change, 0)

        nvi = 1000 * (1 + pd.Series(nvi_pct, index=close.index)).cumprod()

        nvi_ema = nvi.ewm(span=ema_period, adjust=False).mean()

        # Sinyal Matrisi: nvi > nvi_ema = 2 (LONG), nvi < nvi_ema = 0 (SHORT), eşit/NaN = 1 (BEKLE)
        nvi_signal = np.where(nvi > nvi_ema, 2, np.where(nvi < nvi_ema, 0, 1))

        df = pd.DataFrame(
            {"nvi": nvi, "nvi_ema": nvi_ema, "nvi_signal": nvi_signal},
            index=close.index,
        )

        return df.replace([np.inf, -np.inf], np.nan).fillna(0)

    @staticmethod
    def cmf(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        period: int = 20,
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
    def adl(
        high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
    ) -> pd.Series:
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
        period: int = 14,
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
        distance = ((close + close.shift(1)) / 2) - (
            (close.shift(1) + close.shift(2)) / 2
        )
        box_ratio = volume / high_low
        eom = distance / box_ratio
        return eom.rolling(period).mean()

    @staticmethod
    def demand_index(
        high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, **kwargs
    ) -> pd.DataFrame:
        """
        Demand Index (DI)

        James Sibbet'in fiyat-hacim uyuşmazlığını ölçen metriği. Döngülerden kaçınmak
        için hacim-fiyat değişimli vektörize VPO (Volume Price Oscillator) yaklaşımı.

        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            volume: Hacim
            **kwargs: Ek parametreler (period)

        Returns:
            di (Demand Index) ve di_signal içeren DataFrame
        """
        period = kwargs.get('period', 19)

        # Delta computation
        delta = close.diff()

        # Buying pressure and Selling pressure based on price delta
        bp = pd.Series(np.where(delta > 0, volume * delta, 0), index=close.index)
        sp = pd.Series(np.where(delta < 0, volume * abs(delta), 0), index=close.index)

        # Exponential moving averages of buying and selling pressure
        bp_ema = bp.ewm(span=period, adjust=False).mean()
        sp_ema = sp.ewm(span=period, adjust=False).mean()

        # Demand Index formula with zero-division protection
        di_val = 100 * (bp_ema - sp_ema) / (bp_ema + sp_ema).replace(0, np.nan)

        # Signal Matrix: DI > 0 (LONG: 2), DI < 0 (SHORT: 0), else (NEUTRAL: 1)
        di_signal = np.where(di_val > 0, 2, np.where(di_val < 0, 0, 1))

        # Data Integrity Shield
        di_val = di_val.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        return pd.DataFrame({
            'di': di_val,
            'di_signal': di_signal
        }, index=close.index)

    @staticmethod
    def vader(
        high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, **kwargs
    ) -> pd.DataFrame:
        """
        Volume Adjusted Directional Energy Ratio (VADER)

        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            volume: Hacim
            **kwargs: Ek parametreler (vader_period vs.)

        Returns:
            DataFrame: (vader, vader_signal)
        """
        period = kwargs.get("vader_period", 14)

        # 1. Yönsel Farklar (Directional Differences)
        up = high.diff()
        down = -1 * low.diff()

        # 2. DM+ ve DM- İzolasyonu
        dm_plus = np.where((up > down) & (up > 0), up, 0.0)
        dm_minus = np.where((down > up) & (down > 0), down, 0.0)

        # 3. True Range (TR) Hesaplaması
        # Shift ile pre-computing yapıp np.maximum ile hızlandırıyoruz
        prev_close = close.shift(1)
        tr = np.maximum(
            high - low, np.maximum(abs(high - prev_close), abs(low - prev_close))
        )

        # 4. Hacim Ayarlaması (Volume Adjustment) ve Index Koruması
        vdm_plus = pd.Series(dm_plus * volume, index=high.index)
        vdm_minus = pd.Series(dm_minus * volume, index=high.index)
        vtr = pd.Series(tr * volume, index=high.index)

        # 5. EMA ile Yumuşatma (Smoothing)
        ema_vdm_plus = vdm_plus.ewm(span=period, adjust=False).mean()
        ema_vdm_minus = vdm_minus.ewm(span=period, adjust=False).mean()
        ema_vtr = vtr.ewm(span=period, adjust=False).mean()

        # 6. Data Integrity Kalkanı (Division by Zero Koruması)
        ema_vtr = ema_vtr.replace([np.inf, -np.inf, 0], np.nan)

        # 7. VADER Formülü
        vader_val = 100 * (ema_vdm_plus - ema_vdm_minus) / ema_vtr

        # Nan ve Inifity'leri zırh ile temizle
        vader_val = vader_val.replace([np.inf, -np.inf], np.nan).fillna(0)

        # 8. Sinyal Matrisi
        # vader > 0: 2 (LONG/BULL), vader < 0: 0 (SHORT/BEAR), vader == 0: 1 (NEUTRAL/HOLD)
        vader_signal = np.where(vader_val > 0, 2, np.where(vader_val < 0, 0, 1))

        # 9. DataFrame Çıktısı
        df = pd.DataFrame(
            {"vader": vader_val, "vader_signal": vader_signal},
            index=high.index,
        )

        return df
