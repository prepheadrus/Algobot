"""
Data Indicators Package

Modüler teknik indikatör kütüphanesi.
Geriye dönük uyumluluk için StrategyIndicators sınıfını sağlar.

Usage:
    from data.indicators import StrategyIndicators

    # Eski kullanım hala çalışır
    df = StrategyIndicators.add_all_indicators(df)
    df['EMA_20'] = StrategyIndicators.ema(df['close'], 20)

    # Yeni modüler kullanım
    from data.indicators.trend import TrendIndicators
    from data.indicators.momentum import MomentumIndicators

    df['EMA_20'] = TrendIndicators.ema(df['close'], 20)
    df['RSI_14'] = MomentumIndicators.rsi(df['close'], 14)
"""

import pandas as pd
import numpy as np

from core.logger import logger

# Import all sub-modules
from data.indicators.trend import TrendIndicators
from data.indicators.momentum import MomentumIndicators
from data.indicators.volatility import VolatilityIndicators
from data.indicators.volume import VolumeIndicators
from data.indicators.advanced import AdvancedIndicators

# Set global pandas option to avoid FutureWarning on downcasting object dtype arrays
# E402 (Module level import not at top of file) is silenced intentionally,
# or we move `set_option` after all imports
pd.set_option("future.no_silent_downcasting", True)

# TA-Lib ve pandas-ta bağımlılıkları SKILL.md gereği kaldırıldı.
# Tüm hesaplamalar manuel (numpy/pandas) sınıflar üzerinden yapılır.
USING_TALIB = False
USING_PANDAS_TA = False
ta = None

# ============================================================================
# FINAL LOG
# ============================================================================

logger.info("🎉 [MİMARİ] Faz 4 Tamamlandı: İndikatör Kütüphanesi 5 Modüle Parçalandı")


# ============================================================================
# STRATEGY INDICATORS CLASS (Facade Pattern - Geriye Dönük Uyumluluk)
# ============================================================================


class StrategyIndicators:
    """
    Facade class for backward compatibility.

    Eski kodların çalışmaya devam etmesi için tüm indikatör
    metodlarını bu sınıfta topluyoruz. Arka planda alt modülleri
    kullanır.
    """

    # ========================================================================
    # BASIC INDICATORS (Wrapper methods)
    # ========================================================================

    @staticmethod
    def ema(series: pd.Series, length: int) -> pd.Series:
        """Exponential Moving Average"""
        return TrendIndicators.ema(series, length)

    @staticmethod
    def sma(series: pd.Series, length: int) -> pd.Series:
        """Simple Moving Average"""
        return TrendIndicators.sma(series, length)

    @staticmethod
    def vortex(
        high: pd.Series, low: pd.Series, close: pd.Series, **kwargs
    ) -> pd.DataFrame:
        """Vortex Indicator"""
        return TrendIndicators.vortex(high, low, close, **kwargs)

    @staticmethod
    def rsi(series: pd.Series, length: int = 14) -> pd.Series:
        """RSI"""
        return MomentumIndicators.rsi(series, length)

    @staticmethod
    def atr(
        high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14
    ) -> pd.Series:
        """ATR"""
        return VolatilityIndicators.atr(high, low, close, length)

    @staticmethod
    def btc_vix(low: pd.Series, close: pd.Series, **kwargs) -> pd.DataFrame:
        """BTC VIX (Synthetic Crypto Volatility Index)"""
        return VolatilityIndicators.btc_vix(low, close, **kwargs)

    @staticmethod
    def macd(
        series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> tuple:
        """MACD"""
        return MomentumIndicators.macd(series, fast, slow, signal)

    @staticmethod
    def bollinger_bands(series: pd.Series, length: int = 20, std: float = 2) -> tuple:
        """Bollinger Bands"""
        return VolatilityIndicators.bollinger_bands(series, length, std)

    @staticmethod
    def vwap(
        high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
    ) -> pd.Series:
        """VWAP"""
        return VolumeIndicators.vwap(high, low, close, volume)

    @staticmethod
    def mfi(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        period: int = 14,
    ) -> pd.Series:
        """MFI"""
        return VolumeIndicators.mfi(high, low, close, volume, period)

    @staticmethod
    def uo(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        fast: int = 7,
        medium: int = 14,
        slow: int = 28,
    ) -> pd.Series:
        """Ultimate Oscillator"""
        return MomentumIndicators.uo(high, low, close, fast, medium, slow)

    # ========================================================================
    # KALMAN FİLTRESİ (Plug & Play Denoising)
    # ========================================================================

    @staticmethod
    def apply_kalman(
        prices: pd.Series, process_noise: float = 0.001, measurement_noise: float = 0.1
    ) -> pd.Series:
        """
        Kalman Filtresi ile fiyat gürültüsünü azalt.

        Plug & Play: Config'den okunan parametrelerle çalışır.
        Tüm stratejiler bu filtreyi otomatik kullanabilir.

        Args:
            prices: Fiyat serisi (close fiyatları)
            process_noise: Süreç gürültüsü (küçük = daha smooth)
            measurement_noise: Ölçüm gürültüsü (büyük = daha agresif)

        Returns:
            Filtrelenmiş fiyat serisi
        """
        if len(prices) == 0:
            return prices

        # Kalman parametreleri
        Q = process_noise  # Process noise covariance
        R = measurement_noise  # Measurement noise covariance

        # Initial states
        x = prices.iloc[0]  # Initial estimate
        P = 1.0  # Initial error covariance
        K = 0.0  # Initial Kalman gain

        filtered_prices = []

        for price in prices:
            # Prediction step
            x_pred = x
            P_pred = P + Q

            # Update step
            K = P_pred / (P_pred + R)
            x = x_pred + K * (price - x_pred)
            P = (1 - K) * P_pred

            filtered_prices.append(x)

        return pd.Series(filtered_prices, index=prices.index, name="smoothed_close")

    @staticmethod
    def psar(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series = None,
        af0: float = 0.02,
        af: float = 0.02,
        max_af: float = 0.2,
    ) -> tuple:
        """Parabolic SAR"""
        return TrendIndicators.psar(high, low, close, af0, af, max_af)

    @staticmethod
    def ttm_squeeze(cls, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """TTM Squeeze Indicator Wrapper"""
        return VolatilityIndicators.ttm_squeeze(df['high'], df['low'], df['close'], **kwargs)

    @staticmethod
    def supertrend(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        multiplier: float = 3.0,
        period: int = 10,
    ) -> tuple:
        """SuperTrend"""
        return TrendIndicators.supertrend(high, low, close, multiplier, period)

    @staticmethod
    def pvi(close: pd.Series, volume: pd.Series, **kwargs) -> pd.DataFrame:
        """Positive Volume Index (Vectorized)"""
        return VolumeIndicators.pvi(close, volume, **kwargs)

    @staticmethod
    def nvi(close: pd.Series, volume: pd.Series, **kwargs) -> pd.DataFrame:
        """Negative Volume Index (Vectorized)"""
        return VolumeIndicators.nvi(close, volume, **kwargs)

    @staticmethod
    def obv_ema(close: pd.Series, volume: pd.Series, **kwargs) -> pd.DataFrame:
        """On-Balance Volume + EMA (Vectorized)"""
        return VolumeIndicators.obv_ema(close, volume, **kwargs)

    @staticmethod
    def kama(series: pd.Series, **kwargs) -> pd.DataFrame:
        """Kaufman Adaptive Moving Average (KAMA)"""
        return TrendIndicators.kama(series, **kwargs)

    @staticmethod
    def alma(series: pd.Series, **kwargs) -> pd.DataFrame:
        """Arnaud Legoux Moving Average (ALMA)"""
        return TrendIndicators.alma(series, **kwargs)

    @staticmethod
    def rwi(high: pd.Series, low: pd.Series, close: pd.Series, **kwargs) -> pd.DataFrame:
        """Random Walk Index (RWI)"""
        return TrendIndicators.rwi(high, low, close, **kwargs)

    @staticmethod
    def cmo(series: pd.Series, **kwargs) -> pd.DataFrame:
        """Chande Momentum Oscillator (CMO)"""
        return MomentumIndicators.cmo(series, **kwargs)

    @staticmethod
    def bulls_power(high: pd.Series, close: pd.Series, **kwargs) -> pd.DataFrame:
        """Bulls Power (Elder Ray Index)"""
        return MomentumIndicators.bulls_power(high, close, **kwargs)

    @staticmethod
    def bear_power(cls, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Bear Power (Elder Ray Index)"""
        return MomentumIndicators.bear_power(df['low'], df['close'], **kwargs)

    @staticmethod
    def cci(cls, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Commodity Channel Index"""
        return MomentumIndicators.cci(df['high'], df['low'], df['close'], **kwargs)

    @staticmethod
    def trix(cls, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """Triple Exponential Average (TRIX)"""
        return MomentumIndicators.trix(df['close'], **kwargs)

    @staticmethod
    def vader(
        high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, **kwargs
    ) -> pd.DataFrame:
        """Volume Adjusted Directional Energy Ratio (VADER)"""
        return VolumeIndicators.vader(high, low, close, volume, **kwargs)

    @staticmethod
    def qqe_mod(close: pd.Series, **kwargs) -> pd.DataFrame:
        """QQE Mod (Quantitative Qualitative Estimation Mod)"""
        return AdvancedIndicators.qqe_mod(close, **kwargs)

    # ========================================================================
    # RESAMPLING
    # ========================================================================

    @classmethod
    def chop(cls, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Choppiness Index wrapper
        """
        return TrendIndicators.chop(high=df['high'], low=df['low'], close=df['close'], **kwargs)

    @classmethod
    def di_spread(cls, df: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        Directional Indicator Spread (DI Spread) wrapper
        """
        return TrendIndicators.di_spread(high=df['high'], low=df['low'], close=df['close'], **kwargs)

    @staticmethod
    def resample_data(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        1 dakikalık verileri istenen zaman dilimine dönüştür.
        LOOK-AHEAD BIAS KORUMASI: closed='left', label='left' (finansal ML standardı)

        Args:
            df: 1m DataFrame
            timeframe: Hedef timeframe (3m, 5m, 15m, 1h, vb.)

        Returns:
            Resampled DataFrame (gelecek mumlar düşülmüş)
        """
        if df.empty or timeframe == "1m":
            return df

        # Zaman damgasını index yap
        if "timestamp" in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df.set_index("timestamp", inplace=True)

        # Resample kuralları
        logic = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }

        # Pandas resample formatına çevir
        if timeframe.endswith("m"):
            rule = timeframe.replace("m", "min")
        elif timeframe.endswith("h"):
            rule = timeframe.replace("h", "h")
        elif timeframe.endswith("d"):
            rule = timeframe.replace("d", "D")
        else:
            rule = timeframe

        # ========================================================================
        # LOOK-AHEAD BIAS KORUMASI (Finansal ML Standardı)
        # ========================================================================
        # closed='left': Her mumun SOL kenarı (kapanış zamanı)
        # label='left': Her mumun SOL kenarı etiketlenir
        # Bu sayede son (henüz kapanmamış) mum geleceği göstermez
        # ========================================================================
        # .apply() yerine .agg() kullanımı (C düzeyinde vektörize ve optimize)
        resampled_df = df.resample(rule, closed="left", label="left").agg(logic)

        # Eksik mumları doldur (inplace kopyalamayı ve warning'leri engellemek için doğrudan atama kullan)
        if "volume" in resampled_df.columns:
            resampled_df["volume"] = resampled_df["volume"].fillna(0)
        resampled_df = resampled_df.ffill()

        # ========================================================================
        # [TZ FIX] Index timezone-aware yap (UTC)
        # ========================================================================
        if resampled_df.index.tzinfo is None:
            resampled_df.index = resampled_df.index.tz_localize("UTC")
        else:
            resampled_df.index = resampled_df.index.tz_convert("UTC")

        # ========================================================================
        # GELECEK MUM KORUMASI (Son mum henüz kapanmadıysa düşür)
        # ========================================================================
        now_utc = pd.Timestamp.now(tz="UTC")

        # Son mumun kapanış zamanını kontrol et
        last_mum_time = resampled_df.index[-1]

        # Eğer son mum gelecekteyse (henüz kapanmadıysa) düşür
        if last_mum_time > now_utc:
            logger.debug(
                f"⚠️ [RESAMPLE] Son mum henüz kapanmadı ({last_mum_time} > {now_utc}), düşürülüyor"
            )
            resampled_df = resampled_df.iloc[:-1]  # Son mumu düşür

        # Alternatif: Son 1 dakika içinde kapanmış mumları da düşür (güvenlik)
        time_since_last_mum = now_utc - last_mum_time
        if time_since_last_mum.total_seconds() < 60:  # 1 dakikadan az
            logger.debug(
                "⚠️ [RESAMPLE] Son mum 1 dakika önce kapandı, güvenlik için düşürülüyor"
            )
            resampled_df = resampled_df.iloc[:-1]

        # ========================================================================
        # ÇIKIŞ STANDARDI (Tz-Naive DatetimeIndex)
        # ========================================================================
        # Index'i timezone-naive yap (WFO ve ML ile uyumluluk için)
        if resampled_df.index.tzinfo is not None:
            resampled_df.index = resampled_df.index.tz_localize(None)

        # ÖNEMLİ: reset_index KALDIRILDI!
        # ML servisi ve Data servisi index'in DatetimeIndex olmasını bekliyor
        return resampled_df

    # ========================================================================
    # ADD ALL INDICATORS (Monolithic method - geriye dönük uyumluluk)
    # ========================================================================

    @staticmethod
    def add_all_indicators(
        df: pd.DataFrame, apply_kalman_from_config: bool = True, **kwargs
    ) -> pd.DataFrame:
        """
        Tüm indikatörleri hesapla (SKILL.md / Faz 4 Manuel Hesaplama).
        YENİ: Plug & Play Kalman Filtresi desteği.

        Args:
            df: OHLCV DataFrame
            apply_kalman_from_config: Config'den Kalman ayarını oku
            **kwargs: Ek parametreler (örn: alma_window)

        Returns:
            DataFrame with all indicators
        """
        if df.empty or len(df) < 5:
            return df

        # Veri kalitesini garanti altına al
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

        # VWAP için DatetimeIndex şart
        if "timestamp" in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True, drop=False)

        # Null'ları temizle
        df.ffill(inplace=True)
        df.bfill(inplace=True)

        if df["close"].isnull().any():
            df.fillna(0, inplace=True)

        # --- TREND (Manuel) ---
        df["EMA_5"] = TrendIndicators.ema(df["close"], 5)
        df["EMA_13"] = TrendIndicators.ema(df["close"], 13)
        df["SMA_20"] = TrendIndicators.sma(df["close"], 20)
        df["EMA_50"] = TrendIndicators.ema(df["close"], 50)
        df["EMA_200"] = TrendIndicators.ema(df["close"], 200)

        # ========================================================================
        # KALMAN FİLTRESİ (Plug & Play) - LOGARİTMİK SÖNÜMLEMELİ
        # ========================================================================
        if apply_kalman_from_config:
            try:
                from core.config import CONFIG

                kalman_config = CONFIG.get("kalman_smoothing", {})

                if kalman_config.get("enabled", False):
                    process_noise = kalman_config.get("process_noise", 0.001)
                    measurement_noise = kalman_config.get("measurement_noise", 0.1)

                    # YENİ: Logaritmik sönümlemeli dinamik Kalman Filter
                    # high, low, close ile ATR hesaplayarak dinamik beta
                    df["smoothed_close"] = TrendIndicators.kalman_filter(
                        src=df["close"],
                        high=df["high"],
                        low=df["low"],
                        close=df["close"],
                        alpha=process_noise,
                        beta=measurement_noise,
                        use_dynamic_beta=True,  # ATR bazlı dinamik beta
                    )

                    # Log mesajı
                    logger.info(
                        f"[KALMAN] Dampened Kalman & Triple Barrier Hazır | Q={process_noise}, R={measurement_noise}"
                    )

                    # Stratejiler için close fiyatını smoothed_close olarak ayarla
                    # NOT: Orijinal 'close' korunur, stratejiler 'smoothed_close' kullanabilir
                else:
                    logger.debug("[KALMAN] Filtre devre dışı (config'den)")
            except Exception as e:
                logger.warning(f"[KALMAN] Filtre uygulanamadı: {e}")
                df["smoothed_close"] = df["close"]  # Fallback
        else:
            df["smoothed_close"] = df["close"]

        # Supertrend
        st, direction = TrendIndicators.supertrend(
            df["high"], df["low"], df["close"], 3.0, 10
        )
        df["SUPERTREND"] = st
        df["SUPERTREND_DIR"] = direction

        # EWO (Elliott Wave Oscillator)
        df["EWO"] = AdvancedIndicators.ewo(df["close"])

        # --- MOMENTUM (Manuel) ---
        df["RSI_14"] = MomentumIndicators.rsi(df["close"], 14)
        df["ROC_10"] = MomentumIndicators.roc(df["close"], 10)

        # MACD (Manuel Unpack)
        macd_line, signal_line, hist = MomentumIndicators.macd(
            df["close"], fast=12, slow=26, signal=9
        )
        df["MACD_12_26_9"] = macd_line
        df["MACDs_12_26_9"] = signal_line
        df["MACDh_12_26_9"] = hist

        # Stochastic
        stoch_k, stoch_d = MomentumIndicators.stochastic(
            df["high"], df["low"], df["close"], 14, 3
        )
        df["STOCH_K_14_3_3"] = stoch_k
        df["STOCH_D_14_3_3"] = stoch_d

        # UO (Ultimate Oscillator)
        try:
            uo_timeframe1 = kwargs.get('uo_timeframe1', 7)
            uo_timeframe2 = kwargs.get('uo_timeframe2', 14)
            uo_timeframe3 = kwargs.get('uo_timeframe3', 28)
            uo_overbought = kwargs.get('uo_overbought', 70.0)
            uo_oversold = kwargs.get('uo_oversold', 30.0)

            uo_df = MomentumIndicators.ultimate_oscillator(
                df['high'], df['low'], df['close'],
                uo_timeframe1=uo_timeframe1, uo_timeframe2=uo_timeframe2, uo_timeframe3=uo_timeframe3,
                uo_overbought=uo_overbought, uo_oversold=uo_oversold
            )

            # Dinamik atama
            df[f'UO_{uo_timeframe1}_{uo_timeframe2}_{uo_timeframe3}'] = uo_df['uo_signal']

            # Geriye dönük uyumluluk: eski UO ataması (Divergence Hunter vs için)
            df['UO'] = uo_df['uo_val']
        except Exception as e:
            logger.warning(f"⚠️ [IND] Ultimate Oscillator hesaplama hatası: {e}")

        # --- VOLATILITY (Manuel) ---
        df["ATR_14"] = VolatilityIndicators.atr(df["high"], df["low"], df["close"], 14)

        # Bollinger Bands
        upper, middle, lower = VolatilityIndicators.bollinger_bands(
            df["close"], length=20, std=2
        )
        df["BBU_20_2.0_2.0"] = upper
        df["BBM_20_2.0_2.0"] = middle
        df["BBL_20_2.0_2.0"] = lower

        # Market Regime Detector (Faz 1) için gerekli Bollinger Bantları ve SMA
        df["SMA_20"] = df["close"].rolling(window=20).mean()
        std_20 = df["close"].rolling(window=20).std()
        df["BBU_20_2.0"] = df["SMA_20"] + (2.0 * std_20)
        df["BBL_20_2.0"] = df["SMA_20"] - (2.0 * std_20)

        # BTC VIX (Dinamik Volatilite - Williams VIX Fix)
        try:
            vix_period = kwargs.get("vix_period", 22)
            vix_ema_period = kwargs.get("vix_ema_period", 20)

            vix_df = StrategyIndicators.btc_vix(
                df["low"], df["close"], period=vix_period, ema_period=vix_ema_period
            )

            # Dinamik Atama (WFO Arama Uzayı için)
            df[f"BTC_VIX_{vix_period}"] = vix_df["btc_vix"]
            df[f"BTC_VIX_EMA_{vix_period}"] = vix_df["vix_ema"]
            df[f"BTC_VIX_SIGNAL_{vix_period}"] = vix_df["vix_signal"]

            # Geriye Dönük Uyumluluk
            df["BTC_VIX"] = vix_df["btc_vix"]
        except Exception as e:
            logger.warning(f"⚠️ [IND] BTC_VIX hesaplama hatası: {e}")

        # --- VOLUME (Manuel) ---
        if "volume" in df.columns:
            try:
                obv_ema_period = kwargs.get("obv_ema_period", 21)
                obv_df = StrategyIndicators.obv_ema(
                    df["close"], df["volume"], ema_period=obv_ema_period
                )

                # Dinamik Atama
                df[f"OBV_{obv_ema_period}"] = obv_df["obv"]
                df[f"OBV_EMA_{obv_ema_period}"] = obv_df["obv_ema"]
                df[f"OBV_SIGNAL_{obv_ema_period}"] = obv_df["obv_signal"]

                # Backward Compatibility (Legacy Alias)
                df["OBV"] = obv_df["obv"]
                df["OBV_EMA"] = obv_df["obv_ema"]
            except Exception as e:
                logger.warning(f"⚠️ [IND] OBV_EMA hesaplama hatası: {e}")

            try:
                pvi_ema_period = kwargs.get("pvi_ema_period", 255)
                pvi_df = StrategyIndicators.pvi(
                    df["close"], df["volume"], ema_period=pvi_ema_period
                )

                # Dinamik Atama
                df[f"PVI_{pvi_ema_period}"] = pvi_df["pvi"]
                df[f"PVI_EMA_{pvi_ema_period}"] = pvi_df["pvi_ema"]
                df[f"PVI_SIGNAL_{pvi_ema_period}"] = pvi_df["pvi_signal"]
            except Exception as e:
                logger.warning(f"⚠️ [IND] PVI hesaplama hatası: {e}")

            try:
                nvi_ema_period = kwargs.get("nvi_ema_period", 255)
                nvi_df = StrategyIndicators.nvi(
                    df["close"], df["volume"], ema_period=nvi_ema_period
                )

                # Yeni NVI Dinamik Atama
                df[f"NVI_{nvi_ema_period}"] = nvi_df["nvi"]
                df[f"NVI_EMA_{nvi_ema_period}"] = nvi_df["nvi_ema"]
                df[f"NVI_SIGNAL_{nvi_ema_period}"] = nvi_df["nvi_signal"]

                # Geriye Dönük Uyumluluk (Legacy Alias) - TEK OTORİTE
                df["NVI"] = nvi_df["nvi"]
            except Exception as e:
                logger.warning(f"⚠️ [IND] NVI hesaplama hatası: {e}")

            try:
                vader_period = kwargs.get("vader_period", 14)
                vader_df = StrategyIndicators.vader(
                    df["high"],
                    df["low"],
                    df["close"],
                    df["volume"],
                    vader_period=vader_period,
                )

                # Dinamik Atama
                df[f"VADER_{vader_period}"] = vader_df["vader"]
                df[f"VADER_SIGNAL_{vader_period}"] = vader_df["vader_signal"]
            except Exception as e:
                logger.warning(f"⚠️ [IND] VADER hesaplama hatası: {e}")

            # Demand Index (DI)
            try:
                di_period = kwargs.get("di_period", 19)
                di_df = VolumeIndicators.demand_index(
                    df["high"], df["low"], df["close"], df["volume"], period=di_period
                )

                # Dinamik Atama
                df[f"DI_VAL_{di_period}"] = di_df["di"]
                df[f"DI_SIGNAL_{di_period}"] = di_df["di_signal"]
            except Exception as e:
                logger.warning(f"⚠️ [IND] Demand Index hesaplama hatası: {e}")

            # VWAP
            df["VWAP"] = VolumeIndicators.vwap(
                df["high"], df["low"], df["close"], df["volume"]
            )

        # --- KONKORDE (Gelişmiş) ---
        if "volume" in df.columns and len(df) > 1:
            try:
                koncorde = AdvancedIndicators.calculate_koncorde(
                    df["close"], df["high"], df["low"], df["volume"], 15
                )
                df["KONCORDE_PVI"] = koncorde["pvi"]
                df["KONCORDE_NVI"] = koncorde["nvi"]
                df["KONCORDE_PVIM"] = koncorde["pvim"]
                df["KONCORDE_NVIM"] = koncorde["nvim"]
                df["KONKORDE_AZUL"] = koncorde["azul"]
                df["KONKORDE_VERDE"] = koncorde["verde"]
                df["KONKORDE_MARRON"] = koncorde["marron"]
            except Exception as e:
                logger.warning(f"⚠️ [IND] Koncorde hesaplama hatası: {e}")

        # --- TREND ADVANCED ---
        # ADX
        adx, plus_di, minus_di = TrendIndicators.adx(
            df["high"], df["low"], df["close"], 14
        )
        df["ADX_14"] = adx
        df["DMP_14"] = plus_di
        df["DMN_14"] = minus_di

        # PSAR (Parabolic SAR)
        try:
            psar, direction = TrendIndicators.psar(df["high"], df["low"], df["close"])
            df["PSAR"] = psar
            df["PSAR_DIR"] = direction
        except Exception as e:
            logger.warning(f"⚠️ [IND] PSAR hesaplama hatası: {e}")

        # ALMA (Arnaud Legoux Moving Average)
        try:
            alma_window = kwargs.get("alma_window", 9)
            alma_df = StrategyIndicators.alma(
                df["close"], window=alma_window, sigma=6.0, offset=0.85
            )
            df[f"ALMA_{alma_window}"] = alma_df["alma"]
            df[f"ALMA_SIGNAL_{alma_window}"] = alma_df["alma_signal"]
        except Exception as e:
            logger.warning(f"⚠️ [IND] ALMA hesaplama hatası: {e}")

        # CMO (Chande Momentum Oscillator)
        try:
            cmo_period = kwargs.get("cmo_period", 14)
            cmo_df = StrategyIndicators.cmo(df["close"], period=cmo_period)
            df[f"CMO_{cmo_period}"] = cmo_df["cmo"]
            df[f"CMO_SIGNAL_{cmo_period}"] = cmo_df["cmo_signal"]
        except Exception as e:
            logger.warning(f"⚠️ [IND] CMO hesaplama hatası: {e}")

        # Bulls Power (Elder Ray Index)
        try:
            bulls_power_period = kwargs.get("bulls_power_period", 13)
            bull_power_df = StrategyIndicators.bulls_power(
                df["high"], df["close"], period=bulls_power_period
            )
            df[f"BULL_POWER_{bulls_power_period}"] = bull_power_df["bull_power"]
            df[f"BULL_POWER_SIGNAL_{bulls_power_period}"] = bull_power_df[
                "bull_power_signal"
            ]
        except Exception as e:
            logger.warning(f"⚠️ [IND] Bulls Power hesaplama hatası: {e}")

        # TRIX (Triple Exponential Average)
        try:
            trix_period = kwargs.get('trix_period', 18)
            trix_signal_period = kwargs.get('trix_signal_period', 9)

            trix_df = StrategyIndicators.trix(StrategyIndicators, df, period=trix_period, signal_period=trix_signal_period)
            df[f"TRIX_{trix_period}_{trix_signal_period}"] = trix_df["trix_val"]
            df[f"TRIX_SIGNAL_{trix_period}_{trix_signal_period}"] = trix_df["trix_signal"]
        except Exception as e:
            logger.warning(f"⚠️ [IND] TRIX hesaplama hatası: {e}")

        # Bear Power (Elder Ray Index)
        try:
            bear_period = kwargs.get('bear_period', 13)
            bear_df = StrategyIndicators.bear_power(StrategyIndicators, df, period=bear_period)
            df[f"BEAR_POWER_{bear_period}"] = bear_df["bear_power"]
            df[f"BEAR_POWER_SIGNAL_{bear_period}"] = bear_df["bear_power_signal"]
        except Exception as e:
            logger.warning(f"⚠️ [IND] Bear Power hesaplama hatası: {e}")

        # CCI (Commodity Channel Index)
        try:
            cci_period = kwargs.get('cci_period', 20)
            cci_df = StrategyIndicators.cci(StrategyIndicators, df, period=cci_period)
            df[f"CCI_{cci_period}"] = cci_df["cci"]
            df[f"CCI_SIGNAL_{cci_period}"] = cci_df["cci_signal"]
        except Exception as e:
            logger.warning(f"⚠️ [IND] CCI hesaplama hatası: {e}")

        # Vortex Indicator
        try:
            vortex_period = kwargs.get("vortex_period", 14)
            vortex_df = StrategyIndicators.vortex(
                df["high"], df["low"], df["close"], period=vortex_period
            )
            df[f"VI_PLUS_{vortex_period}"] = vortex_df["vi_plus"]
            df[f"VI_MINUS_{vortex_period}"] = vortex_df["vi_minus"]
            df[f"VORTEX_SIGNAL_{vortex_period}"] = vortex_df["vortex_signal"]
        except Exception as e:
            logger.warning(f"⚠️ [IND] Vortex hesaplama hatası: {e}")

        # --- SMC / LIKIDITE ---
        try:
            smc = AdvancedIndicators.liquidity_zones(
                df["high"], df["low"], df["close"], lookback=10
            )
            df["SWING_HIGH"] = smc["swing_high"]
            df["SWING_LOW"] = smc["swing_low"]
            df["SWEEP_BULLISH"] = smc["sweep_bullish"]
            df["SWEEP_BEARISH"] = smc["sweep_bearish"]

            # Yeni Alpha Faktörleri (Liquidity Sweep ve Synthetic Imbalance)
            df["liquidity_sweep"] = AdvancedIndicators.liquidity_sweep(df)
            df["synthetic_imbalance"] = AdvancedIndicators.synthetic_imbalance(df)
        except Exception as e:
            logger.warning(f"⚠️ [IND] SMC hesaplama hatası: {e}")

        # --- QQE MOD ---
        try:
            qqe_rsi_period = kwargs.get("qqe_rsi_period", 14)
            qqe_smoothing = kwargs.get("qqe_smoothing", 5)

            qqe_df = StrategyIndicators.qqe_mod(
                df["close"],
                rsi_period=qqe_rsi_period,
                smoothing=qqe_smoothing
            )

            df[f"QQE_LINE_{qqe_rsi_period}"] = qqe_df["qqe_line"]
            df[f"QQE_HISTO_{qqe_rsi_period}"] = qqe_df["histo"]
            df[f"QQE_MOD_SIGNAL_{qqe_rsi_period}"] = qqe_df["qqe_mod_signal"]
        except Exception as e:
            logger.warning(f"⚠️ [IND] QQE Mod hesaplama hatası: {e}")

        # --- RANDOM WALK INDEX (RWI) ---
        try:
            rwi_period = kwargs.get("rwi_period", 14)
            rwi_df = StrategyIndicators.rwi(
                df["high"], df["low"], df["close"], period=rwi_period
            )

            df[f"RWI_HIGH_{rwi_period}"] = rwi_df["rwi_high"]
            df[f"RWI_LOW_{rwi_period}"] = rwi_df["rwi_low"]
            df[f"RWI_SIGNAL_{rwi_period}"] = rwi_df["rwi_signal"]
        except Exception as e:
            logger.warning(f"⚠️ [IND] RWI hesaplama hatası: {e}")

        # --- CHOPPINESS INDEX (CHOP) ---
        try:
            chop_period = kwargs.get("chop_period", 14)
            chop_df = StrategyIndicators.chop(
                df, period=chop_period
            )

            df[f"CHOP_{chop_period}"] = chop_df["chop"]
            df[f"CHOP_SIGNAL_{chop_period}"] = chop_df["chop_signal"]
        except Exception as e:
            logger.warning(f"⚠️ [IND] CHOP hesaplama hatasi: {e}")

        # --- DI SPREAD ---
        try:
            di_spread_period = kwargs.get("di_spread_period", 14)

            di_spread_df = StrategyIndicators.di_spread(
                df, period=di_spread_period
            )

            # Sadece spread ve spread_signal kolonlarını ekliyoruz ("Curse of Dimensionality" koruması)
            df[f"DI_SPREAD_{di_spread_period}"] = di_spread_df["spread"]
            df[f"DI_SPREAD_SIGNAL_{di_spread_period}"] = di_spread_df["spread_signal"]
        except Exception as e:
            logger.error(f"[INDICATOR ERROR] DI Spread calculation failed for period {di_spread_period}: {e}")

        # --- TTM SQUEEZE ---
        try:
            sqz_period = kwargs.get('sqz_period', 20)
            sqz_bb_mult = kwargs.get('sqz_bb_mult', 2.0)
            sqz_kc_mult = kwargs.get('sqz_kc_mult', 1.5)

            sqz_df = StrategyIndicators.ttm_squeeze(
                StrategyIndicators, df, period=sqz_period, bb_mult=sqz_bb_mult, kc_mult=sqz_kc_mult
            )

            df[f"TTM_SQUEEZE_{sqz_period}_{sqz_bb_mult:.1f}_{sqz_kc_mult:.1f}"] = sqz_df["squeeze_signal"]
        except Exception as e:
            logger.warning(f"⚠️ [IND] TTM Squeeze hesaplama hatası: {e}")


        # Veri Integrity: NaN/Inf Temizliği (SKILL.md)
        df = df.replace([np.inf, -np.inf], np.nan).fillna(0)

        return df


# ============================================================================
# EXPORTS (Hem eski hem yeni kullanım için)
# ============================================================================

__all__ = [
    # Backward compatibility
    "StrategyIndicators",
    # New modular imports
    "TrendIndicators",
    "MomentumIndicators",
    "VolatilityIndicators",
    "VolumeIndicators",
    "AdvancedIndicators",
    # Library detection
    "USING_TALIB",
    "USING_PANDAS_TA",
    "ta",
]
