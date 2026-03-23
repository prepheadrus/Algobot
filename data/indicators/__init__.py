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
    def rsi(series: pd.Series, length: int = 14) -> pd.Series:
        """RSI"""
        return MomentumIndicators.rsi(series, length)
    
    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int = 14) -> pd.Series:
        """ATR"""
        return VolatilityIndicators.atr(high, low, close, length)
    
    @staticmethod
    def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """MACD"""
        return MomentumIndicators.macd(series, fast, slow, signal)
    
    @staticmethod
    def bollinger_bands(series: pd.Series, length: int = 20, std: float = 2) -> tuple:
        """Bollinger Bands"""
        return VolatilityIndicators.bollinger_bands(series, length, std)
    
    @staticmethod
    def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
        """VWAP"""
        return VolumeIndicators.vwap(high, low, close, volume)
    
    @staticmethod
    def mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
        """MFI"""
        return VolumeIndicators.mfi(high, low, close, volume, period)
    
    @staticmethod
    def uo(high: pd.Series, low: pd.Series, close: pd.Series, fast: int = 7, medium: int = 14, slow: int = 28) -> pd.Series:
        """Ultimate Oscillator"""
        return MomentumIndicators.uo(high, low, close, fast, medium, slow)

    # ========================================================================
    # KALMAN FİLTRESİ (Plug & Play Denoising)
    # ========================================================================

    @staticmethod
    def apply_kalman(
        prices: pd.Series,
        process_noise: float = 0.001,
        measurement_noise: float = 0.1
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

        return pd.Series(filtered_prices, index=prices.index, name='smoothed_close')
    
    @staticmethod
    def psar(high: pd.Series, low: pd.Series, close: pd.Series = None, af0: float = 0.02, af: float = 0.02, max_af: float = 0.2) -> tuple:
        """Parabolic SAR"""
        return TrendIndicators.psar(high, low, close, af0, af, max_af)
    
    @staticmethod
    def supertrend(high: pd.Series, low: pd.Series, close: pd.Series, multiplier: float = 3.0, period: int = 10) -> tuple:
        """SuperTrend"""
        return TrendIndicators.supertrend(high, low, close, multiplier, period)
    
    # ========================================================================
    # RESAMPLING
    # ========================================================================
    
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
        if 'timestamp' in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df.set_index('timestamp', inplace=True)

        # Resample kuralları
        logic = {
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        }

        # Pandas resample formatına çevir
        if timeframe.endswith('m'):
            rule = timeframe.replace('m', 'min')
        elif timeframe.endswith('h'):
            rule = timeframe.replace('h', 'h')
        elif timeframe.endswith('d'):
            rule = timeframe.replace('d', 'D')
        else:
            rule = timeframe

        # ========================================================================
        # LOOK-AHEAD BIAS KORUMASI (Finansal ML Standardı)
        # ========================================================================
        # closed='left': Her mumun SOL kenarı (kapanış zamanı)
        # label='left': Her mumun SOL kenarı etiketlenir
        # Bu sayede son (henüz kapanmamış) mum geleceği göstermez
        # ========================================================================
        resampled_df = df.resample(rule, closed='left', label='left').apply(logic)

        # Eksik mumları doldur
        resampled_df['volume'] = resampled_df['volume'].fillna(0)
        resampled_df.ffill(inplace=True)

        # ========================================================================
        # [TZ FIX] Index timezone-aware yap (UTC)
        # ========================================================================
        if resampled_df.index.tzinfo is None:
            resampled_df.index = resampled_df.index.tz_localize('UTC')
        else:
            resampled_df.index = resampled_df.index.tz_convert('UTC')

        # ========================================================================
        # GELECEK MUM KORUMASI (Son mum henüz kapanmadıysa düşür)
        # ========================================================================
        now_utc = pd.Timestamp.now(tz='UTC')

        # Son mumun kapanış zamanını kontrol et
        last_mum_time = resampled_df.index[-1]

        # Eğer son mum gelecekteyse (henüz kapanmadıysa) düşür
        if last_mum_time > now_utc:
            logger.debug(f"⚠️ [RESAMPLE] Son mum henüz kapanmadı ({last_mum_time} > {now_utc}), düşürülüyor")
            resampled_df = resampled_df.iloc[:-1]  # Son mumu düşür

        # Alternatif: Son 1 dakika içinde kapanmış mumları da düşür (güvenlik)
        time_since_last_mum = now_utc - last_mum_time
        if time_since_last_mum.total_seconds() < 60:  # 1 dakikadan az
            logger.debug(f"⚠️ [RESAMPLE] Son mum 1 dakika önce kapandı, güvenlik için düşürülüyor")
            resampled_df = resampled_df.iloc[:-1]

        # Index'i tekrar sütuna al
        resampled_df.reset_index(inplace=True)
        return resampled_df
    
    # ========================================================================
    # ADD ALL INDICATORS (Monolithic method - geriye dönük uyumluluk)
    # ========================================================================
    
    @staticmethod
    def add_all_indicators(df: pd.DataFrame, apply_kalman_from_config: bool = True) -> pd.DataFrame:
        """
        Tüm indikatörleri hesapla (SKILL.md / Faz 4 Manuel Hesaplama).
        YENİ: Plug & Play Kalman Filtresi desteği.

        Args:
            df: OHLCV DataFrame
            apply_kalman_from_config: Config'den Kalman ayarını oku

        Returns:
            DataFrame with all indicators
        """
        if df.empty or len(df) < 5:
            return df

        # Veri kalitesini garanti altına al
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)

        # VWAP için DatetimeIndex şart
        if 'timestamp' in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True, drop=False)

        # Null'ları temizle
        df.ffill(inplace=True)
        df.bfill(inplace=True)

        if df['close'].isnull().any():
            df.fillna(0, inplace=True)

        # --- TREND (Manuel) ---
        df['EMA_5'] = TrendIndicators.ema(df['close'], 5)
        df['EMA_13'] = TrendIndicators.ema(df['close'], 13)
        df['SMA_20'] = TrendIndicators.sma(df['close'], 20)
        df['EMA_50'] = TrendIndicators.ema(df['close'], 50)
        df['EMA_200'] = TrendIndicators.ema(df['close'], 200)

        # ========================================================================
        # KALMAN FİLTRESİ (Plug & Play) - LOGARİTMİK SÖNÜMLEMELİ
        # ========================================================================
        if apply_kalman_from_config:
            try:
                from core.config import CONFIG
                kalman_config = CONFIG.get('kalman_smoothing', {})

                if kalman_config.get('enabled', False):
                    process_noise = kalman_config.get('process_noise', 0.001)
                    measurement_noise = kalman_config.get('measurement_noise', 0.1)

                    # YENİ: Logaritmik sönümlemeli dinamik Kalman Filter
                    # high, low, close ile ATR hesaplayarak dinamik beta
                    df['smoothed_close'] = TrendIndicators.kalman_filter(
                        src=df['close'],
                        high=df['high'],
                        low=df['low'],
                        close=df['close'],
                        alpha=process_noise,
                        beta=measurement_noise,
                        use_dynamic_beta=True  # ATR bazlı dinamik beta
                    )

                    # Log mesajı
                    logger.info(f"[KALMAN] Dampened Kalman & Triple Barrier Hazır | Q={process_noise}, R={measurement_noise}")

                    # Stratejiler için close fiyatını smoothed_close olarak ayarla
                    # NOT: Orijinal 'close' korunur, stratejiler 'smoothed_close' kullanabilir
                else:
                    logger.debug("[KALMAN] Filtre devre dışı (config'den)")
            except Exception as e:
                logger.warning(f"[KALMAN] Filtre uygulanamadı: {e}")
                df['smoothed_close'] = df['close']  # Fallback
        else:
            df['smoothed_close'] = df['close']
        
        # Supertrend
        st, direction = TrendIndicators.supertrend(df['high'], df['low'], df['close'], 3.0, 10)
        df['SUPERTREND'] = st
        df['SUPERTREND_DIR'] = direction
        
        # EWO (Elliott Wave Oscillator)
        df['EWO'] = AdvancedIndicators.ewo(df['close'])
        
        # --- MOMENTUM (Manuel) ---
        df['RSI_14'] = MomentumIndicators.rsi(df['close'], 14)
        df['ROC_10'] = MomentumIndicators.roc(df['close'], 10)
        
        # MACD (Manuel Unpack)
        macd_line, signal_line, hist = MomentumIndicators.macd(df['close'], fast=12, slow=26, signal=9)
        df['MACD_12_26_9'] = macd_line
        df['MACDs_12_26_9'] = signal_line
        df['MACDh_12_26_9'] = hist
        
        # Stochastic
        stoch_k, stoch_d = MomentumIndicators.stochastic(df['high'], df['low'], df['close'], 14, 3)
        df['STOCH_K_14_3_3'] = stoch_k
        df['STOCH_D_14_3_3'] = stoch_d
        
        # UO (Ultimate Oscillator)
        df['UO'] = MomentumIndicators.uo(df['high'], df['low'], df['close'], 7, 14, 28)
        
        # --- VOLATILITY (Manuel) ---
        df['ATR_14'] = VolatilityIndicators.atr(df['high'], df['low'], df['close'], 14)
        
        # Bollinger Bands
        upper, middle, lower = VolatilityIndicators.bollinger_bands(df['close'], length=20, std=2)
        df['BBU_20_2.0_2.0'] = upper
        df['BBM_20_2.0_2.0'] = middle
        df['BBL_20_2.0_2.0'] = lower
        
        # BTC VIX (Dinamik Volatilite)
        df['BTC_VIX'] = VolatilityIndicators.btc_vix(df['close'])
        
        # --- VOLUME (Manuel) ---
        if 'volume' in df.columns:
            # OBV
            df['OBV'] = VolumeIndicators.obv(df['close'], df['volume'])
            df['OBV_EMA'] = df['OBV'].ewm(span=10, adjust=False).mean()
            
            # VWAP
            df['VWAP'] = VolumeIndicators.vwap(df['high'], df['low'], df['close'], df['volume'])
        
        # --- KONKORDE (Gelişmiş) ---
        if 'volume' in df.columns and len(df) > 1:
            try:
                koncorde = AdvancedIndicators.calculate_koncorde(
                    df['close'], df['high'], df['low'], df['volume'], 15
                )
                df['PVI'] = koncorde['pvi']
                df['NVI'] = koncorde['nvi']
                df['PVIM'] = koncorde['pvim']
                df['NVIM'] = koncorde['nvim']
                df['KONKORDE_AZUL'] = koncorde['azul']
                df['KONKORDE_VERDE'] = koncorde['verde']
                df['KONKORDE_MARRON'] = koncorde['marron']
            except Exception as e:
                logger.warning(f"⚠️ [IND] Koncorde hesaplama hatası: {e}")
        
        # --- TREND ADVANCED ---
        # ADX
        adx, plus_di, minus_di = TrendIndicators.adx(df['high'], df['low'], df['close'], 14)
        df['ADX_14'] = adx
        df['DMP_14'] = plus_di
        df['DMN_14'] = minus_di
        
        # PSAR (Parabolic SAR)
        try:
            psar, direction = TrendIndicators.psar(df['high'], df['low'], df['close'])
            df['PSAR'] = psar
            df['PSAR_DIR'] = direction
        except Exception as e:
            logger.warning(f"⚠️ [IND] PSAR hesaplama hatası: {e}")

        # --- SMC / LIKIDITE ---
        try:
            smc = AdvancedIndicators.liquidity_zones(df['high'], df['low'], df['close'], lookback=10)
            df['SWING_HIGH'] = smc['swing_high']
            df['SWING_LOW'] = smc['swing_low']
            df['SWEEP_BULLISH'] = smc['sweep_bullish']
            df['SWEEP_BEARISH'] = smc['sweep_bearish']
        except Exception as e:
            logger.warning(f"⚠️ [IND] SMC hesaplama hatası: {e}")

        # Veri Integrity: NaN/Inf Temizliği (SKILL.md)
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.fillna(0, inplace=True)
        
        return df


# ============================================================================
# EXPORTS (Hem eski hem yeni kullanım için)
# ============================================================================

__all__ = [
    # Backward compatibility
    'StrategyIndicators',
    
    # New modular imports
    'TrendIndicators',
    'MomentumIndicators',
    'VolatilityIndicators',
    'VolumeIndicators',
    'AdvancedIndicators',
    
    # Library detection
    'USING_TALIB',
    'USING_PANDAS_TA',
    'ta',
]
