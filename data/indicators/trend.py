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
    def kama(close: pd.Series, **kwargs) -> pd.DataFrame:
        """
        Kaufman Adaptive Moving Average (KAMA)
        pandas_ta KULLANILMADAN, saf Pandas/NumPy ile hesaplanmıştır.

        Returns:
            pd.DataFrame: 'kama' (float) ve 'kama_signal' (int: 0=SAT, 1=BEKLE, 2=AL) kolonlarını içerir.
        """
        # 1. Parametre Yönetimi ve Esneklik (Auto-Grid Uyumlu)
        period = kwargs.get('period', 10)
        fast_end = kwargs.get('fast_end', 2)
        slow_end = kwargs.get('slow_end', 30)

        n = len(close)
        kama_vals = np.full(n, np.nan)

        # Yetersiz veri kalkanı
        if n < period:
            return pd.DataFrame({'kama': kama_vals, 'kama_signal': 1}, index=close.index)

        # 2. Vektörize Momentum ve Volatilite Hesaplamaları
        change = np.abs(close.diff(period))
        volatility = np.abs(close.diff()).rolling(window=period).sum()

        # 3. Sıfıra Bölünme ve Veri Bütünlüğü Kalkanı
        # Yatay piyasada volatilite 0 olabilir, inf/-inf oluşumunu engellemek için nan'a çeviriyoruz
        volatility = volatility.replace([np.inf, -np.inf, 0], np.nan)

        er = (change / volatility).fillna(0).to_numpy()
        close_array = close.to_numpy()

        # 4. Smoothing Constant (SSC) Vektörizasyonu
        fast_sc = 2 / (fast_end + 1)
        slow_sc = 2 / (slow_end + 1)
        ssc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

        # 5. Özyinelemeli (Recursive) Adım - İterasyon Optimizasyonu
        # Numba kullanılmıyorsa, Pandas .apply() yerine en hızlı yöntem önceden tahsis edilmiş NumPy dizisinde dönmektir.
        kama_vals[period-1] = close_array[period-1]  # İlk değeri fiyata veya SMA'ya eşitle

        for i in range(period, n):
            kama_vals[i] = kama_vals[i-1] + ssc[i] * (close_array[i] - kama_vals[i-1])

        # 6. Sonuçların DataFrame'e Dönüştürülmesi
        df = pd.DataFrame(index=close.index)
        df['kama'] = kama_vals

        # 7. Vektörize Sinyal Matrisi (0=SHORT, 1=NEUTRAL, 2=LONG)
        df['kama_signal'] = np.where(
            close > df['kama'], 2,
            np.where(close < df['kama'], 0, 1)
        )

        # Başlangıçtaki NaN periyotlar için sinyali nötralize et
        df.loc[df['kama'].isna(), 'kama_signal'] = 1

        return df

    
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
    def alma(close: pd.Series, **kwargs) -> pd.DataFrame:
        """
        Arnaud Legoux Moving Average (ALMA)
        Pure NumPy Vectorization with np.convolve (No loops)
        """
        window = kwargs.get('window', 9)
        sigma = kwargs.get('sigma', 6.0)
        offset = kwargs.get('offset', 0.85)

        n = len(close)
        if n < window:
            return pd.DataFrame({'alma': np.full(n, np.nan), 'alma_signal': 1}, index=close.index)

        # 1. Gauss Ağırlıklarının Hesaplanması (Gaussian Weights)
        m = np.floor(offset * (window - 1))
        s = window / sigma

        weights = np.exp(-((np.arange(window) - m) ** 2) / (2 * s ** 2))
        weights /= weights.sum()

        # 2. Vektörize Konvolüsyon (Sıfır Döngü, C-Level Hız)
        close_array = close.to_numpy()
        alma_vals = np.convolve(close_array, weights[::-1], mode='valid')

        # 3. Padding (Veri hizalama)
        alma_full = np.concatenate((np.full(window - 1, np.nan), alma_vals))

        # 4. DataFrame Çıktısı
        df = pd.DataFrame(index=close.index)
        df['alma'] = alma_full

        # 5. Sinyal Matrisi
        df['alma_signal'] = np.where(
            close > df['alma'], 2,
            np.where(close < df['alma'], 0, 1)
        )

        # NaN koruması
        df.loc[df['alma'].isna(), 'alma_signal'] = 1

        return df

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

    @staticmethod
    def vortex(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        **kwargs
    ) -> pd.DataFrame:
        """
        Vortex Indicator (VI+ / VI-) - %100 Vektörize

        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            **kwargs: Ek parametreler (period vb.)

        Returns:
            pd.DataFrame: 'vi_plus', 'vi_minus' ve 'vortex_signal' kolonlarını içerir.
        """
        # 1. Parametre Yönetimi (Auto-Grid Uyumlu)
        period = kwargs.get('period', 14)

        n = len(close)
        if n < period:
            return pd.DataFrame({
                'vi_plus': np.full(n, 0.0),
                'vi_minus': np.full(n, 0.0),
                'vortex_signal': np.full(n, 1)
            }, index=close.index)

        # 2. %100 Vektörize İşlem ve Hızlı Gerçek Aralık (True Range)
        tr = np.maximum(
            high - low,
            np.maximum(
                np.abs(high - close.shift(1)),
                np.abs(low - close.shift(1))
            )
        )

        vmp = np.abs(high - low.shift(1))
        vmm = np.abs(low - high.shift(1))

        # 3. Yuvarlama (Rolling) ve Data Integrity Kalkanı
        sum_tr = tr.rolling(window=period).sum().replace([np.inf, -np.inf, 0], np.nan)

        vi_plus = (vmp.rolling(window=period).sum() / sum_tr).fillna(0)
        vi_minus = (vmm.rolling(window=period).sum() / sum_tr).fillna(0)

        # 4. Sinyal Matrisi Çıktısı (0, 1, 2)
        vortex_signal = np.where(
            vi_plus > vi_minus, 2,
            np.where(vi_plus < vi_minus, 0, 1)
        )

        # 5. Sonuçların DataFrame'e Dönüştürülmesi
        df = pd.DataFrame(index=close.index)
        df['vi_plus'] = vi_plus
        df['vi_minus'] = vi_minus
        df['vortex_signal'] = vortex_signal

        return df

    @staticmethod
    def rwi(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        **kwargs
    ) -> pd.DataFrame:
        """
        Random Walk Index (RWI)
        Piyasanın rastgele yürüyüşte (choppy) mi yoksa trendde mi olduğunu ölçer.

        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            **kwargs: Ek parametreler (period vb.)

        Returns:
            pd.DataFrame: 'rwi_high', 'rwi_low' ve 'rwi_signal' kolonlarını içerir.
        """
        period = kwargs.get('period', 14)
        n = len(close)

        if n < period:
            return pd.DataFrame({
                'rwi_high': np.full(n, 0.0),
                'rwi_low': np.full(n, 0.0),
                'rwi_signal': np.full(n, 1)
            }, index=close.index)

        # 1. True Range (TR) Hesaplama
        tr = np.maximum(
            high - low,
            np.maximum(
                np.abs(high - close.shift(1)),
                np.abs(low - close.shift(1))
            )
        )

        rwi_high_list = []
        rwi_low_list = []

        # 2. Vektörize Matematiksel Çekirdek (C-Array Hızında)
        for i in range(2, period + 1):
            # Sıfıra Bölünme (Division by Zero) ve Data Integrity kalkanı
            atr_i = tr.rolling(window=i, min_periods=1).mean().replace(0, np.nan)
            denominator = atr_i * np.sqrt(i)

            rwi_h = (high - low.shift(i)) / denominator
            rwi_l = (high.shift(i) - low) / denominator

            rwi_high_list.append(rwi_h)
            rwi_low_list.append(rwi_l)

        # Matris birleştirme ve maksimum ivmeyi bulma
        rwi_high = pd.concat(rwi_high_list, axis=1).max(axis=1)
        rwi_low = pd.concat(rwi_low_list, axis=1).max(axis=1)

        # 3. Data Integrity (Veri Bütünlüğü) Kalkanı
        rwi_high = rwi_high.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        rwi_low = rwi_low.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        # 4. Sinyal Matrisi Çıktısı (0, 1, 2)
        # RWI değeri 1'in altındaysa piyasa rastgele yürüyüştedir (Random Walk / Yatay).
        # 1'in üzerindeyse trend vardır.
        rwi_signal = np.where(
            (rwi_high > 1) & (rwi_high > rwi_low), 2,
            np.where(
                (rwi_low > 1) & (rwi_low > rwi_high), 0, 1
            )
        )

        # İlk periyotlardaki eksik veriler için sinyali nötralize et (1)
        rwi_signal[:period] = 1

        df = pd.DataFrame(index=close.index)
        df['rwi_high'] = rwi_high
        df['rwi_low'] = rwi_low
        df['rwi_signal'] = rwi_signal

        return df

    @staticmethod
    def chop(high: pd.Series, low: pd.Series, close: pd.Series, **kwargs) -> pd.DataFrame:
        """
        Choppiness Index (CHOP)
        A quantitative metric that determines if the market is choppy (trading sideways)
        or not choppy (trading within a trend in either direction).

        Args:
            high (pd.Series): High prices
            low (pd.Series): Low prices
            close (pd.Series): Close prices
            **kwargs: Optuna search space parameters.
                      period (int, default=14)

        Returns:
            pd.DataFrame: DataFrame containing 'chop' and 'chop_signal'.
        """
        period = kwargs.get('period', 14)

        # 1. True Range calculation with np.maximum shield
        tr = np.maximum(
            high - low,
            np.maximum(
                abs(high - close.shift(1)),
                abs(low - close.shift(1))
            )
        )

        # 2. Vectorized Math Core (Fractal Dimension)
        atr_sum = tr.rolling(window=period, min_periods=1).sum()
        max_high = high.rolling(window=period, min_periods=1).max()
        min_low = low.rolling(window=period, min_periods=1).min()

        # Zero-division and logarithm shield
        range_hl = (max_high - min_low).replace(0, np.nan).clip(lower=1e-10)

        # CHOP Formula
        chop_val = 100 * np.log10(atr_sum / range_hl) / np.log10(period)

        # 3. Data Integrity Shield
        chop_val = chop_val.replace([np.inf, -np.inf], np.nan).fillna(50.0)

        # 4. Signal Matrix Output
        chop_signal = np.where(chop_val > 61.8, 0, np.where(chop_val < 38.2, 2, 1))

        return pd.DataFrame({
            'chop': chop_val,
            'chop_signal': pd.Series(chop_signal, index=high.index)
        })

    @staticmethod
    def di_spread(high: pd.Series, low: pd.Series, close: pd.Series, **kwargs) -> pd.DataFrame:
        """
        Directional Indicator Spread (DI Spread)
        XGBoost'un rejim tespiti için ADX'ten daha hızlı tepki veren bağımsız bir algoritma.
        %100 Vektörize edilmiş ve Wilder's Smoothing kullanılarak optimize edilmiştir.

        Args:
            high (pd.Series): Yüksek fiyatlar
            low (pd.Series): Düşük fiyatlar
            close (pd.Series): Kapanış fiyatları
            **kwargs:
                period (int): Periyot (varsayılan: 14)
                di_threshold_low (float): Bu değerin altındaysa trend ölüdür (varsayılan: 15.0)
                di_threshold_high (float): Bu değerin üstündeyse trend güçlüdür (varsayılan: 25.0)

        Returns:
            pd.DataFrame: 'plus_di', 'minus_di', 'spread' ve 'spread_signal' kolonlarını içerir.
        """
        period = kwargs.get('period', 14)
        threshold_low = kwargs.get('di_threshold_low', 15.0)
        threshold_high = kwargs.get('di_threshold_high', 25.0)

        # 1. Yönsel Hareket (Directional Movement)
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

        # 2. True Range (TR) ve NaN Sızıntısı Koruması
        # close.shift(1) NaN üreteceğinden ilk mumda NaN sızıntısını engelliyoruz
        close_shifted = close.shift(1).fillna(close)

        tr = np.maximum(
            high - low,
            np.maximum(
                abs(high - close_shifted),
                abs(low - close_shifted)
            )
        )
        tr = tr.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        # 3. Wilder's Smoothing (Sıfır Döngü, Pandas .ewm)
        plus_dm_smooth = pd.Series(plus_dm, index=close.index).ewm(alpha=1/period, adjust=False).mean()
        minus_dm_smooth = pd.Series(minus_dm, index=close.index).ewm(alpha=1/period, adjust=False).mean()
        tr_smooth = tr.ewm(alpha=1/period, adjust=False).mean()

        # 4. DI Hesaplaması ve Sıfıra Bölünme Kalkanı
        tr_safe = tr_smooth.replace(0, np.nan)
        plus_di = 100 * (plus_dm_smooth / tr_safe)
        minus_di = 100 * (minus_dm_smooth / tr_safe)

        # 5. DI Spread (Mutlak Mesafe)
        spread = abs(plus_di - minus_di)

        # 6. Veri Bütünlüğü Kalkanı (Data Integrity Shield)
        spread = spread.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        # 7. Sinyal Matrisi (0=CHOPPY, 1=NEUTRAL, 2=TRENDING)
        spread_signal = np.where(
            spread < threshold_low, 0,
            np.where(spread > threshold_high, 2, 1)
        )

        spread_signal = pd.Series(spread_signal, index=close.index).fillna(1).astype(int)

        # Warm-up periyodu (ilk `period` kadar bar) için sinyalleri Nötr (1) yapıyoruz
        spread_signal.iloc[:period] = 1

        # Sonuçların DataFrame'e dönüştürülmesi
        # Single Responsibility gereği gelecekteki olası grafik/loglama ihtiyaçları için
        # plus_di ve minus_di de döndürülüyor.
        df = pd.DataFrame({
            'plus_di': plus_di.replace([np.inf, -np.inf], np.nan).fillna(0.0),
            'minus_di': minus_di.replace([np.inf, -np.inf], np.nan).fillna(0.0),
            'spread': spread,
            'spread_signal': spread_signal
        }, index=close.index)

        return df

    @staticmethod
    def vhf(close: pd.Series, **kwargs) -> pd.DataFrame:
        """
        Vertical Horizontal Filter (VHF)
        XGBoost'un piyasa rejimi dedektörünü tamamlayan yatay piyasa (Flat Market) filtresi.
        pandas_ta kullanılmadan, %100 vektörize NumPy/Pandas işlemleri ile hesaplanır.

        Args:
            close (pd.Series): Kapanış fiyatları
            **kwargs: Optuna hiperparametreleri (period, vhf_sma_period)

        Returns:
            pd.DataFrame: 'vhf_val', 'vhf_sma' ve 'vhf_signal' kolonlarını içerir.
        """
        period = kwargs.get('period', 28)
        sma_period = kwargs.get('vhf_sma_period', 20)

        n = len(close)
        if n < period:
            return pd.DataFrame({
                'vhf_val': np.full(n, 0.0),
                'vhf_sma': np.full(n, 0.0),
                'vhf_signal': np.full(n, 1)
            }, index=close.index)

        # 1. Pay (Numerator - Dikey Hareket)
        hcp = close.rolling(window=period, min_periods=1).max()
        lcp = close.rolling(window=period, min_periods=1).min()
        numerator = hcp - lcp

        # 2. Payda (Denominator - Yatay Gürültü) ve Sıfıra Bölünme Kalkanı
        # Piyasa hareketsizse (Flat Market) payda tam olarak 0 çıkar. Infinity fırlatılmasını engellemek
        # için .replace(0, np.nan) kullanıyoruz.
        denominator = abs(close.diff()).rolling(window=period, min_periods=1).sum().replace(0, np.nan)

        # 3. VHF Formülü
        vhf_val = numerator / denominator

        # 4. Sinyal Hattı (Signal Line) ve Sinyal Matrisi
        vhf_sma = vhf_val.rolling(window=sma_period, min_periods=1).mean()

        # Sinyal Mantığı: 2 (TRENDING), 0 (CHOPPY), 1 (NEUTRAL)
        vhf_signal = np.where(vhf_val > vhf_sma, 2, np.where(vhf_val < vhf_sma, 0, 1))

        # 5. Data Integrity (Veri Bütünlüğü) Kalkanı
        vhf_val = vhf_val.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        vhf_sma = vhf_sma.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        # Sinyali düzgün indexle ve eksikleri 1 ile doldur (NEUTRAL)
        vhf_signal = pd.Series(vhf_signal, index=close.index).fillna(1).astype(int)

        df = pd.DataFrame({
            'vhf_val': vhf_val,
            'vhf_sma': vhf_sma,
            'vhf_signal': vhf_signal
        }, index=close.index)

        return df
