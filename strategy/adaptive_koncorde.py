from strategy.base import BaseStrategy
import pandas as pd
import numpy as np
from core.logger import logger

class AdaptiveKoncordeX(BaseStrategy):
    """
    Piyasa koşullarına uyum sağlayan, Kalman Filtresi ve Koncorde (Akıllı Para)
    mekanizmalarını birleştiren ileri düzey hibrit strateji.
    VIX endeksine göre riskini otomatik ayarlar.
    Tamamen PineScript sürümüyle uyumlu hale getirilmiştir.
    """

    # WFO (Walk-Forward Optimization) için varsayılan parametreler
    DEFAULT_PARAMS = {
        # Base Parameters
        'base_kalmanAlpha': 0.015,
        'base_kalmanBeta': 0.12,
        'base_kalmanPeriod': 65,
        'base_dev': 1.8,

        # Supertrend
        'supertrendFactor': 0.8,
        'supertrendAtrPeriod': 8,

        # EWO Base
        'base_ewo_fast': 5,
        'base_ewo_slow': 35,
        'base_ewo_threshold': 0.1,

        # Filters Base
        'volume_ma_length': 20,
        'volume_multiplier': 1.3,
        'rsi_length': 14,
        'rsi_oversold': 35,
        'rsi_overbought': 65,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,

        # Signal Settings Base
        'base_min_bars_between': 5,
        'base_confluence_required': 3.0,

        # Koncorde Params (Mevcut 'data/indicators.py' kullanılarak hesaplanacak)
        'koncorde_period': 15,

        # Risk Management
        'atr_multiplier': 2.5,
        'tp_multiplier': 3.0
    }

    def __init__(self):
        """Strateji parametrelerini başlat"""
        self.params = self.DEFAULT_PARAMS.copy()

        # Stateful değişkenleri burada tutacağız
        self.last_signal_bar = None
        self.bar_index = 0

    def name(self) -> str:
        return "Adaptive Koncorde X"

    def description(self) -> str:
        return "Kalman Filtresi, Akıllı Para (Koncorde) ve BTC Volatilite Endeksi (VIX) kullanan adaptif hibrit bot. PineScript v5 uyumlu."

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Gerekli tüm hesaplamaları DataFrame bazında (vektörel) yapar.
        Bu fonksiyon her bir sembol/veriseti için strateji çalışmadan önce çağrılır.
        """
        if df.empty or len(df) < 50:
            return df



        # Gerekli kütüphaneleri Data katmanından alıyoruz
        from data.indicators.trend import TrendIndicators
        from data.indicators.momentum import MomentumIndicators
        from data.indicators.volatility import VolatilityIndicators
        from data.indicators.advanced import AdvancedIndicators
        from data.indicators.volume import VolumeIndicators

        close = df['close']
        high = df['high']
        low = df['low']
        volume = df.get('volume', pd.Series(0, index=df.index))

        # ============================================================================
        # ADAPTIVE PARAMETER SYSTEM
        # ============================================================================

        # Volatility Lookback (20)
        log_ret = np.log(close / close.shift(1))
        btc_vix = log_ret.rolling(20).std() * np.sqrt(365) * 100
        df['BTC_VIX'] = btc_vix

        low_vol = btc_vix < 50
        medium_vol = (btc_vix >= 50) & (btc_vix < 80)
        high_vol = btc_vix >= 80

        # Market cycle detection
        sma_50 = TrendIndicators.sma(close, 50)
        sma_200 = TrendIndicators.sma(close, 200)
        slope_200 = ((sma_200 - sma_200.shift(20)) / sma_200.shift(20)) * 100

        strong_bull = (close > sma_50) & (sma_50 > sma_200) & (slope_200 > 2)
        weak_bull = (close > sma_200) & (sma_200 > sma_200.shift(10)) & (slope_200 > 0)
        consolidation = slope_200.abs() < 1
        weak_bear = (close < sma_200) & (sma_200 < sma_200.shift(10)) & (slope_200 < 0)
        strong_bear = (close < sma_50) & (sma_50 < sma_200) & (slope_200 < -2)

        # Adapt parameters arrays
        base_alpha = self.params['base_kalmanAlpha']
        vol_mult_alpha = np.where(low_vol, 0.7, np.where(medium_vol, 1.0, 1.6))
        market_mult_alpha = np.where(strong_bull, 1.4, np.where(weak_bull, 1.1, np.where(consolidation, 0.8, np.where(weak_bear, 0.9, 0.6))))
        adaptive_kalman_alpha = np.clip(base_alpha * vol_mult_alpha * market_mult_alpha, 0.005, 0.05)

        base_beta = self.params['base_kalmanBeta']
        vol_mult_beta = np.where(low_vol, 0.8, np.where(medium_vol, 1.0, 1.3))
        market_mult_beta = np.where(strong_bull, 1.2, np.where(weak_bull, 1.0, np.where(consolidation, 0.9, np.where(weak_bear, 1.1, 1.4))))
        adaptive_kalman_beta = np.clip(base_beta * vol_mult_beta * market_mult_beta, 0.05, 0.4)

        base_period = self.params['base_kalmanPeriod']
        vol_adj_period = np.where(low_vol, 15, np.where(medium_vol, 0, -10))
        market_adj_period = np.where(strong_bull, -10, np.where(weak_bull, -5, np.where(consolidation, 10, np.where(weak_bear, 5, 15))))
        adaptive_kalman_period = np.clip(base_period + vol_adj_period + market_adj_period, 30, 150)

        base_dev = self.params['base_dev']
        vol_mult_dev = np.where(low_vol, 0.8, np.where(medium_vol, 1.0, 1.4))
        market_mult_dev = np.where(strong_bull, 0.9, np.where(weak_bull, 0.95, np.where(consolidation, 1.2, np.where(weak_bear, 1.1, 1.3))))
        adaptive_dev = np.clip(base_dev * vol_mult_dev * market_mult_dev, 1.0, 3.0)

        base_threshold = self.params['base_ewo_threshold']
        vol_mult_ewo = np.where(low_vol, 0.7, np.where(medium_vol, 1.0, 1.5))
        market_mult_ewo = np.where(strong_bull, 0.8, np.where(weak_bull, 0.9, np.where(consolidation, 1.3, np.where(weak_bear, 1.1, 1.4))))
        adaptive_ewo_threshold = np.clip(base_threshold * vol_mult_ewo * market_mult_ewo, 0.03, 0.3)
        df['ADAPTIVE_EWO_THRESHOLD'] = pd.Series(adaptive_ewo_threshold, index=df.index)

        base_bars = self.params['base_min_bars_between']
        vol_adj_bars = np.where(low_vol, -1, np.where(medium_vol, 0, 3))
        market_adj_bars = np.where(strong_bull, -1, np.where(weak_bull, 0, np.where(consolidation, 5, np.where(weak_bear, 2, 4))))
        adaptive_min_bars_between = np.clip(base_bars + vol_adj_bars + market_adj_bars, 2, 20)
        df['ADAPTIVE_MIN_BARS'] = pd.Series(adaptive_min_bars_between, index=df.index)

        # ============================================================================
        # KALMAN FILTER FUNCTION (Adaptive)
        # ============================================================================
        def adaptive_kalman(src, period_arr, alpha_arr, beta_arr):

            res = np.zeros_like(src_arr)

            if len(src_arr) == 0: return pd.Series(res, index=src.index)

            v1 = src_arr[0]
            v2 = 1.0

            for i in range(len(src_arr)):
                if np.isnan(src_arr[i]):
                    res[i] = np.nan
                    continue

                period = period_arr[i] if not np.isnan(period_arr[i]) else 65
                alpha = alpha_arr[i] if not np.isnan(alpha_arr[i]) else 0.015
                beta = beta_arr[i] if not np.isnan(beta_arr[i]) else 0.12

                v3 = alpha * period
                v4 = v2 / (v2 + v3) if (v2 + v3) != 0 else 0
                v1 = v1 + v4 * (src_arr[i] - v1)
                v2 = (1 - v4) * v2 + beta / period
                res[i] = v1

            return pd.Series(res, index=src.index)

        k = adaptive_kalman(close, adaptive_kalman_period, adaptive_kalman_alpha, adaptive_kalman_beta)
        df['KALMAN'] = k

        # ============================================================================
        # SUPERTREND FUNCTION (on Kalman)
        # ============================================================================
        def pine_supertrend(k_series, factor, atrPeriod):
            atr = VolatilityIndicators.atr(high, low, close, atrPeriod)
            upperBand = k_series + factor * atr
            lowerBand = k_series - factor * atr

            superTrend = np.zeros(len(k_series))
            direction = np.ones(len(k_series)) # 1 or -1



            for i in range(1, len(k_series)):
                if np.isnan(atr.iloc[i]):
                    direction[i] = 1
                    continue

                prevLowerBand = lb_val[i-1]
                prevUpperBand = ub_val[i-1]

                lb_val[i] = lb_val[i] if (lb_val[i] > prevLowerBand or k_val[i-1] < prevLowerBand) else prevLowerBand
                ub_val[i] = ub_val[i] if (ub_val[i] < prevUpperBand or k_val[i-1] > prevUpperBand) else prevUpperBand

                prevSuperTrend = superTrend[i-1]

                if prevSuperTrend == prevUpperBand:
                    direction[i] = -1 if k_val[i] > ub_val[i] else 1
                else:
                    direction[i] = 1 if k_val[i] < lb_val[i] else -1

                superTrend[i] = lb_val[i] if direction[i] == -1 else ub_val[i]

            return pd.Series(superTrend, index=k_series.index), pd.Series(direction, index=k_series.index)

        st, st_direction = pine_supertrend(k, self.params['supertrendFactor'], self.params['supertrendAtrPeriod'])
        df['SUPERTREND_DIR'] = st_direction

        # Range Filter with adaptive deviation
        def wma(series, length):
            weights = np.arange(1, length + 1)
            return series.rolling(length).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

        vola = wma(high - low, 200)
        upper_range = k + vola * adaptive_dev
        lower_range = k - vola * adaptive_dev

        range_trend = pd.Series(0, index=df.index)
        range_trend[close > upper_range] = 1
        range_trend[close < lower_range] = -1
        # Forward fill the 0s with the previous trend
        range_trend = range_trend.replace(0, np.nan).ffill().fillna(0)
        df['RANGE_TREND'] = range_trend

        # Kalman trend
        kalman_trend = pd.Series(0, index=df.index)
        kalman_trend[st_direction < 0] = 1
        kalman_trend[st_direction > 0] = -1
        # Forward fill
        kalman_trend = kalman_trend.replace(0, np.nan).ffill().fillna(0)
        df['KALMAN_TREND'] = kalman_trend

        # Elliott Wave Oscillator
        ema_fast = TrendIndicators.sma(close, self.params['base_ewo_fast'])
        ema_slow = TrendIndicators.sma(close, self.params['base_ewo_slow'])
        ewo = (ema_fast - ema_slow) / close * 100
        df['EWO'] = ewo

        # ============================================================================
        # ADDITIONAL FILTERS
        # ============================================================================
        volume_ma = TrendIndicators.sma(volume, self.params['volume_ma_length'])
        volume_filter_ok = volume > (volume_ma * self.params['volume_multiplier'])
        df['VOLUME_FILTER_OK'] = volume_filter_ok

        rsi = MomentumIndicators.rsi(close, self.params['rsi_length'])
        rsi_long_ok = (rsi > self.params['rsi_oversold']) & (rsi < self.params['rsi_overbought'])
        rsi_short_ok = (rsi < self.params['rsi_overbought']) & (rsi > self.params['rsi_oversold'])
        df['RSI_LONG_OK'] = rsi_long_ok
        df['RSI_SHORT_OK'] = rsi_short_ok

        macd_line, signal_line, _ = MomentumIndicators.macd(close, self.params['macd_fast'], self.params['macd_slow'], self.params['macd_signal'])
        macd_long_ok = (macd_line > signal_line) & (macd_line > macd_line.shift(1))
        macd_short_ok = (macd_line < signal_line) & (macd_line < macd_line.shift(1))
        df['MACD_LONG_OK'] = macd_long_ok
        df['MACD_SHORT_OK'] = macd_short_ok

        bb_upper, bb_mid, bb_lower = VolatilityIndicators.bollinger_bands(close, 20, 2.0)
        price_above_bb_mid = close > bb_mid
        price_below_bb_mid = close < bb_mid
        df['PRICE_ABOVE_BB'] = price_above_bb_mid
        df['PRICE_BELOW_BB'] = price_below_bb_mid

        roc = MomentumIndicators.roc(close, 10)
        momentum_strong = roc.abs() > 2
        df['MOMENTUM_STRONG'] = momentum_strong

        # ============================================================================
        # KONKORDE FİLTRESİ
        # ============================================================================
        koncorde = AdvancedIndicators.calculate_koncorde(close, high, low, volume, self.params['koncorde_period'])
        df['KONKORDE_AZUL'] = koncorde['azul']
        df['KONKORDE_VERDE'] = koncorde['verde']

        koncorde_mirror_buy_filter = (koncorde['azul'] > 0) & (koncorde['verde'] < 0)
        koncorde_bear_hug_short_filter = (koncorde['azul'] < 0) & (koncorde['verde'] > 0)
        df['KONCORDE_MIRROR_BUY'] = koncorde_mirror_buy_filter
        df['KONCORDE_BEAR_HUG'] = koncorde_bear_hug_short_filter

        # ============================================================================
        # PERFORMANCE TRACKING & DYNAMIC WEIGHTS
        # ============================================================================

        def calculate_performance_arrays(trend_series, ewo_series, ewo_thresh, vol_ok_series):
            n = len(trend_series)
            range_perf = np.full(n, 0.5)
            kalman_perf = np.full(n, 0.5)
            ewo_perf = np.full(n, 0.5)
            vol_perf = np.full(n, 0.5)

            # Using lists to simulate max length 50 arrays
            rf_res, k_res, ewo_res, vol_res = [], [], [], []



            for i in range(11, n):
                # Range Filter Performance
                if range_trend_arr[i] != range_trend_arr[i-1]:
                    pass # trend changed
                # Approximate 10 bars since change
                # For vectorization, we just look back 10 bars if trend is stable for 10 bars
                if range_trend_arr[i] == range_trend_arr[i-10]:
                    was_correct = ((range_trend_arr[i-10] == 1) and (close_arr[i] > close_arr[i-10])) or \
                                  ((range_trend_arr[i-10] == -1) and (close_arr[i] < close_arr[i-10]))
                    rf_res.append(1.0 if was_correct else 0.0)
                    if len(rf_res) > 50: rf_res.pop(0)
                    if len(rf_res) > 0: range_perf[i] = sum(rf_res)/len(rf_res)
                else:
                    range_perf[i] = range_perf[i-1]

                # Kalman Performance
                if kalman_trend_arr[i] == kalman_trend_arr[i-10]:
                    was_correct = ((kalman_trend_arr[i-10] == 1) and (close_arr[i] > close_arr[i-10])) or \
                                  ((kalman_trend_arr[i-10] == -1) and (close_arr[i] < close_arr[i-10]))
                    k_res.append(1.0 if was_correct else 0.0)
                    if len(k_res) > 50: k_res.pop(0)
                    if len(k_res) > 0: kalman_perf[i] = sum(k_res)/len(k_res)
                else:
                    kalman_perf[i] = kalman_perf[i-1]

                # EWO Performance
                ewo_sig_10 = 1 if ewo_series[i-10] > ewo_thresh[i-10] else (-1 if ewo_series[i-10] < -ewo_thresh[i-10] else 0)
                ewo_sig_0 = 1 if ewo_series[i] > ewo_thresh[i] else (-1 if ewo_series[i] < -ewo_thresh[i] else 0)
                if ewo_sig_10 != 0 and ewo_sig_0 == ewo_sig_10:
                    was_correct = ((ewo_sig_10 == 1) and (close_arr[i] > close_arr[i-10])) or \
                                  ((ewo_sig_10 == -1) and (close_arr[i] < close_arr[i-10]))
                    ewo_res.append(1.0 if was_correct else 0.0)
                    if len(ewo_res) > 50: ewo_res.pop(0)
                    if len(ewo_res) > 0: ewo_perf[i] = sum(ewo_res)/len(ewo_res)
                else:
                    ewo_perf[i] = ewo_perf[i-1]

                # Volume Performance
                if vol_ok_series[i-10] == True:
                    was_correct = (close_arr[i] > close_arr[i-10])
                    vol_res.append(1.0 if was_correct else 0.0)
                    if len(vol_res) > 50: vol_res.pop(0)
                    if len(vol_res) > 0: vol_perf[i] = sum(vol_res)/len(vol_res)
                else:
                    vol_perf[i] = vol_perf[i-1]

            return range_perf, kalman_perf, ewo_perf, vol_perf

        trend_df = pd.DataFrame({'RANGE_TREND': range_trend, 'KALMAN_TREND': kalman_trend})
        range_perf, kalman_perf, ewo_perf, vol_perf = calculate_performance_arrays(trend_df, ewo.values, adaptive_ewo_threshold, volume_filter_ok.values)

        range_filter_weight = np.clip(2.0 * (0.5 + (range_perf * 1.5)), 0.5, 3.0)
        kalman_weight = np.clip(2.0 * (0.5 + (kalman_perf * 1.5)), 0.5, 3.0)
        ewo_weight = np.clip(1.5 * (0.5 + (ewo_perf * 1.5)), 0.5, 2.5)
        volume_weight = np.clip(1.0 * (0.5 + (vol_perf * 1.5)), 0.3, 2.0)

        overall_performance = (range_perf + kalman_perf + ewo_perf + vol_perf) / 4.0

        # ============================================================================
        # DYNAMIC CONFLUENCE SCORE CALCULATION
        # ============================================================================

        dynamic_long_score = pd.Series(0.0, index=df.index)
        dynamic_long_score += np.where(range_trend == 1, range_filter_weight, 0)
        dynamic_long_score += np.where(kalman_trend == 1, kalman_weight, 0)
        dynamic_long_score += np.where(ewo > df['ADAPTIVE_EWO_THRESHOLD'], ewo_weight, 0)
        dynamic_long_score += np.where(volume_filter_ok, volume_weight, 0)
        dynamic_long_score += np.where(rsi_long_ok, 0.5, 0)
        dynamic_long_score += np.where(macd_long_ok, 0.8, 0)
        dynamic_long_score += np.where(price_above_bb_mid, 0.5, 0)
        dynamic_long_score += np.where(momentum_strong, 0.7, 0)
        dynamic_long_score += np.where(koncorde_mirror_buy_filter, 1.2, 0)
        df['DYNAMIC_LONG_SCORE'] = dynamic_long_score

        dynamic_short_score = pd.Series(0.0, index=df.index)
        dynamic_short_score += np.where(range_trend == -1, range_filter_weight, 0)
        dynamic_short_score += np.where(kalman_trend == -1, kalman_weight, 0)
        dynamic_short_score += np.where(ewo < -df['ADAPTIVE_EWO_THRESHOLD'], ewo_weight, 0)
        dynamic_short_score += np.where(volume_filter_ok, volume_weight, 0)
        dynamic_short_score += np.where(rsi_short_ok, 0.5, 0)
        dynamic_short_score += np.where(macd_short_ok, 0.8, 0)
        dynamic_short_score += np.where(price_below_bb_mid, 0.5, 0)
        dynamic_short_score += np.where(momentum_strong, 0.7, 0)
        dynamic_short_score += np.where(koncorde_bear_hug_short_filter, 1.2, 0)
        df['DYNAMIC_SHORT_SCORE'] = dynamic_short_score

        base_confluence_required = self.params['base_confluence_required']
        adjustment = np.where(overall_performance > 0.7, 0.8, np.where(overall_performance < 0.4, 1.3, 1.0))
        dynamic_confluence_threshold = base_confluence_required * adjustment
        df['DYNAMIC_THRESHOLD'] = dynamic_confluence_threshold

        # ============================================================================
        # SIGNAL GENERATION
        # ============================================================================
        trend_change_long = (kalman_trend == 1) & (kalman_trend.shift(1) != 1)
        trend_change_short = (kalman_trend == -1) & (kalman_trend.shift(1) != -1)

        base_long_signal = trend_change_long & (range_trend == 1) & (ewo > df['ADAPTIVE_EWO_THRESHOLD'])
        base_short_signal = trend_change_short & (range_trend == -1) & (ewo < -df['ADAPTIVE_EWO_THRESHOLD'])

        confluence_long_ok = dynamic_long_score >= dynamic_confluence_threshold
        confluence_short_ok = dynamic_short_score >= dynamic_confluence_threshold

        df['LONG_SIGNAL_READY'] = base_long_signal & confluence_long_ok
        df['SHORT_SIGNAL_READY'] = base_short_signal & confluence_short_ok

        return df

    def generate_signal(self, current_row: pd.Series) -> int:
        """
        Sinyal kararını pre-calculated dataframe değerleri üzerinden verir ve
        min_bars_between stateful logic'ini çalıştırır.
        """
        # Gerekli verilerin varlığını kontrol et
        required = ['LONG_SIGNAL_READY', 'SHORT_SIGNAL_READY', 'ADAPTIVE_MIN_BARS']
        if not all(col in current_row.index for col in required):
            return 1 # HOLD

        self.bar_index += 1

        long_signal = current_row['LONG_SIGNAL_READY']
        short_signal = current_row['SHORT_SIGNAL_READY']
        adaptive_min_bars = current_row['ADAPTIVE_MIN_BARS']
        
        can_signal_long = long_signal and (self.last_signal_bar is None or (self.bar_index - self.last_signal_bar >= adaptive_min_bars))
        can_signal_short = short_signal and (self.last_signal_bar is None or (self.bar_index - self.last_signal_bar >= adaptive_min_bars))

        if can_signal_long:
            self.last_signal_bar = self.bar_index
            return 2 # LONG
        elif can_signal_short:
            self.last_signal_bar = self.bar_index
            return 0 # SHORT

        return 1 # HOLD

    def get_stop_params(self):
        """
        Risk yönetimi parametreleri.
        Bu strateji daha hassas olduğu için stopları daha dinamik tutar.
        """
        return {
            "atr_multiplier": self.params.get('atr_multiplier', 2.5),
            "tp_multiplier": self.params.get('tp_multiplier', 3.0)
        }

    def update_params(self, new_params: dict):
        """
        WFO tarafından bulunan yeni parametreleri uygular.

        Args:
            new_params: Yeni parametre sözlüğü
        """
        for key, value in new_params.items():
            if key in self.params:
                self.params[key] = value

        return self.params
