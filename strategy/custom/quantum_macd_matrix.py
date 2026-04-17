import pandas as pd
import numpy as np
from scipy.signal import argrelextrema
import logging

from strategy.base import BaseStrategy
from data.indicators.momentum import MomentumIndicators
from data.indicators.volume import VolumeIndicators
from data.indicators.volatility import VolatilityIndicators
from data.indicators.trend import TrendIndicators

logger = logging.getLogger(__name__)

class QuantumMACDMatrix(BaseStrategy):
    """
    Quantum MACD Matrix (TradingView MACD v2.4 Ultimate Edition)

    Endüstri (Hedge Fund) standartlarında, Asenkron/Event-Driven mimariye ve
    vektörize (Pandas/Numpy) Veri Bilimi kurallarına uygun inşa edilmiş
    Çoklu Zaman Dilimi (MTF) MACD Stratejisi.

    Özellikler:
    - Base Timeframe: 15m
    - MTF Matrix: 15m (Tetik), 60m (Teyit), 240m (Trend), 1D (İklim)
    - Katı Look-ahead Bias Koruması (Sızıntı Önleme)
    - O(N) Vektörize Uyuşmazlık (Divergence) Tespiti
    - Adaptif Motor (Volatilite ve Hacim Çarpanları)
    """

    DEFAULT_PARAMS = {
        'adaptive_mode': True,
        'fast_length': 12,
        'slow_length': 26,
        'signal_length': 9,

        # Divergence Settings
        'lookback_right': 5,
        'lookback_left': 5,
        'max_bars_back': 100,  # Strict maximum lookback window

        # Smart Filter (Kalkan)
        'use_trend_filter': False,
        'trend_period': 55,
        'use_vol_filter': False,
        'vol_multiplier': 2.0,

        # Auto-Close Pivot Settings
        'auto_atr_len': 14,
        'auto_atr_sma': 50,
        'auto_atr_mult': 1.5,

        # Risk Management defaults
        'atr_multiplier': 2.0,
        'risk_reward_ratio': 3.0
    }

    def __init__(self):
        super().__init__()
        self.params = self.DEFAULT_PARAMS.copy()

    def name(self) -> str:
        return "Quantum MACD Matrix"

    def description(self) -> str:
        return "Adaptive MTF MACD Motoru, Vektörize Divergence Kalkanı ve Çoklu Zaman Dilimi Sinyal Birleşimi."

    @property
    def indicators(self) -> list:
        return [
            "MTF MACD (15m, 1H, 4H, 1D)",
            "Adaptive Engine (ATR, Volume)",
            "Divergence Hunter",
            "Trend Kalkanı"
        ]

    def get_conditions(self) -> dict:
        return {
            "LONG": [
                "SÜPER AL: Regular Bullish Div + SÜPER RALLİ (Tüm MTF'ler Güçlü)",
                "ALTIN VURUŞ: Regular Bullish Div + DÜZELTME (Büyük MTF Güçlü, Kısa Vade Düşüş)"
            ],
            "SHORT": [
                "SÜPER SAT: Regular Bearish Div + BIÇAK DÜŞÜYOR (Tüm MTF'ler Zayıf)"
            ]
        }

    def timeframe(self) -> str:
        return "15m"

    def get_stop_params(self) -> dict:
        return {
            'atr_multiplier': self.params.get('atr_multiplier', 2.0),
            'risk_reward_ratio': self.params.get('risk_reward_ratio', 3.0)
        }

    def update_params(self, new_params: dict):
        if hasattr(self, 'params'):
            for key, value in new_params.items():
                if key in self.params:
                    self.params[key] = value
            logger.info(f"📝 [WFO] {self.name()} parametreleri güncellendi: {new_params}")
        else:
            logger.warning(f"⚠️ [WFO] {self.name()} params attribute'u yok")

    def _calc_macd_mtf(self, df: pd.DataFrame, timeframe: str, fast: int, slow: int, sig: int, prefix: str) -> pd.DataFrame:
        """
        Gelecekten veri sızdırmadan üst zaman dilimi MACD hesaplaması yapar.
        Pandas resample ve shift(1) kullanır.
        """
        # Timeframe conversion
        rule_map = {'15m': '15min', '60m': '1h', '240m': '4h', '1D': '1D'}
        rule = rule_map.get(timeframe, timeframe)

        if rule == '15min':
            # Base timeframe, no resample needed
            resampled = df[['close']].copy()
        else:
            # Resample strictly with closed='left' and label='left'
            resampled = df[['close']].resample(rule, closed='left', label='left').last()
            resampled = resampled.dropna()

        # Calculate MACD on resampled timeframe
        if len(resampled) > slow:
            macd_line, signal_line, hist = MomentumIndicators.macd(
                resampled['close'], fast=fast, slow=slow, signal=sig
            )
            resampled[f'{prefix}_macd'] = macd_line
            resampled[f'{prefix}_signal'] = signal_line
            resampled[f'{prefix}_hist'] = hist

            # Trend directions
            resampled[f'{prefix}_macd_up'] = resampled[f'{prefix}_macd'] > resampled[f'{prefix}_macd'].shift(1)
            resampled[f'{prefix}_signal_up'] = resampled[f'{prefix}_signal'] > resampled[f'{prefix}_signal'].shift(1)
            resampled[f'{prefix}_hist_up'] = resampled[f'{prefix}_hist'] > resampled[f'{prefix}_hist'].shift(1)

            # Zone definitions
            hist_cond = resampled[f'{prefix}_hist'] > 0
            hist_up_cond = resampled[f'{prefix}_hist_up']
            resampled[f'{prefix}_zone'] = np.where(hist_cond & hist_up_cond, 2,
                                          np.where(hist_cond & ~hist_up_cond, 1,
                                          np.where(~hist_cond & hist_up_cond, -1, -2)))
        else:
            resampled[f'{prefix}_macd'] = 0
            resampled[f'{prefix}_signal'] = 0
            resampled[f'{prefix}_hist'] = 0
            resampled[f'{prefix}_macd_up'] = False
            resampled[f'{prefix}_signal_up'] = False
            resampled[f'{prefix}_hist_up'] = False
            resampled[f'{prefix}_zone'] = 0

        if rule == '15min':
            return resampled

        # VERY IMPORTANT: Shift the higher timeframe data by 1 bar forward
        # so that the value computed for e.g. 1H is only available AFTER the 1H candle closes
        resampled_shifted = resampled.shift(1)

        # Reindex to base timeframe and forward fill
        resampled_aligned = resampled_shifted.reindex(df.index).ffill()
        return resampled_aligned

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        # 1. Base MACD Periods based on PineScript's f_get_base_macd_periods
        # 15m: 12, 26, 9
        # 60m: 16, 34, 12
        # 240m: 20, 40, 15
        # 1D: 12, 26, 9

        params = self.params

        # Calculate Base MACD (15m) using params (can be optimized by WFO)
        fast = params.get('fast_length', 12)
        slow = params.get('slow_length', 26)
        sig = params.get('signal_length', 9)

        # 2. MTF Calculations
        tf1_df = self._calc_macd_mtf(df, '15m', fast, slow, sig, 'tf1')
        tf2_df = self._calc_macd_mtf(df, '60m', 16, 34, 12, 'tf2')
        tf3_df = self._calc_macd_mtf(df, '240m', 20, 40, 15, 'tf3')
        tf4_df = self._calc_macd_mtf(df, '1D', 12, 26, 9, 'tf4')

        # Merge MTF columns
        cols_to_merge = [c for c in tf1_df.columns if c != 'close']
        for c in cols_to_merge: df[c] = tf1_df[c]
        cols_to_merge = [c for c in tf2_df.columns if c != 'close']
        for c in cols_to_merge: df[c] = tf2_df[c]
        cols_to_merge = [c for c in tf3_df.columns if c != 'close']
        for c in cols_to_merge: df[c] = tf3_df[c]
        cols_to_merge = [c for c in tf4_df.columns if c != 'close']
        for c in cols_to_merge: df[c] = tf4_df[c]

        # 3. Kalkan (Trend & Volatility Filter)
        if params.get('use_trend_filter', False):
            trend_ma = TrendIndicators.ema(df['close'], params.get('trend_period', 55))
            df['kalkan_status'] = np.where(df['close'] > trend_ma, 1, np.where(df['close'] < trend_ma, -1, 0))
        else:
            df['kalkan_status'] = 0 # Nötr

        if params.get('use_vol_filter', False):
            upper, _, lower = VolatilityIndicators.bollinger_bands(df['close'], params.get('trend_period', 55), params.get('vol_multiplier', 2.0))
            df['is_oversold'] = df['close'] < lower
            df['is_overbought'] = df['close'] > upper
        else:
            df['is_oversold'] = False
            df['is_overbought'] = False

        df['allow_bull_div'] = ~params.get('use_trend_filter', False) | (df['kalkan_status'] == 1) | (params.get('use_vol_filter', False) & df['is_oversold'])
        df['allow_bear_div'] = ~params.get('use_trend_filter', False) | (df['kalkan_status'] == -1) | (params.get('use_vol_filter', False) & df['is_overbought'])

        # 4. Divergence Hunter (Vectorized)
        lbr = params.get('lookback_right', 5)
        max_bars_back = params.get('max_bars_back', 100)

        macd_vals = df['tf1_macd'].values
        low_vals = df['low'].values
        high_vals = df['high'].values

        df['bull_div'] = False
        df['bear_div'] = False

        # Find local minima/maxima (Pivots)
        local_min_idx = argrelextrema(macd_vals, np.less, order=lbr)[0]
        local_max_idx = argrelextrema(macd_vals, np.greater, order=lbr)[0]

        # At index i, we know there was a pivot at i - lbr.
        # But we only register the pivot at index i.
        # Track last 10 pivot lows and highs
        # For a truly vectorized O(N) calculation, we iterate once to construct the signals
        # since keeping a rolling memory of specific dynamic indices is complex in pure numpy

        pl_idx = []
        ph_idx = []
        bull_divs = np.zeros(len(df), dtype=bool)
        bear_divs = np.zeros(len(df), dtype=bool)

        for i in range(len(df)):
            # Check if a pivot was confirmed at this bar
            if i - lbr in local_min_idx:
                pl_idx.append(i - lbr)
                # Keep last 10
                if len(pl_idx) > 10:
                    pl_idx.pop(0)

            if i - lbr in local_max_idx:
                ph_idx.append(i - lbr)
                if len(ph_idx) > 10:
                    ph_idx.pop(0)

            # Check for Divergence on current bar (assuming current bar is a pivot confirmation)
            if i - lbr in local_min_idx and len(pl_idx) >= 2:
                curr_pl = pl_idx[-1]
                macd_curr = macd_vals[curr_pl]
                price_curr = low_vals[curr_pl]
                allow = df['allow_bull_div'].iloc[i]

                if allow:
                    # Lookback through previous pivots
                    for prev_pl in reversed(pl_idx[:-1]):
                        dist = curr_pl - prev_pl
                        if 5 <= dist <= max_bars_back:
                            macd_prev = macd_vals[prev_pl]
                            price_prev = low_vals[prev_pl]

                            # Regular Bullish Divergence: Price Lower, MACD Higher
                            if price_curr < price_prev and macd_curr > macd_prev:
                                bull_divs[i] = True
                                break

            if i - lbr in local_max_idx and len(ph_idx) >= 2:
                curr_ph = ph_idx[-1]
                macd_curr = macd_vals[curr_ph]
                price_curr = high_vals[curr_ph]
                allow = df['allow_bear_div'].iloc[i]

                if allow:
                    for prev_ph in reversed(ph_idx[:-1]):
                        dist = curr_ph - prev_ph
                        if 5 <= dist <= max_bars_back:
                            macd_prev = macd_vals[prev_ph]
                            price_prev = high_vals[prev_ph]

                            # Regular Bearish Divergence: Price Higher, MACD Lower
                            if price_curr > price_prev and macd_curr < macd_prev:
                                bear_divs[i] = True
                                break

        df['bull_div'] = bull_divs
        df['bear_div'] = bear_divs

        # 5. Power Matrix (Fısıltı Modu Score)
        for tf in ['tf1', 'tf2', 'tf3', 'tf4']:
            macd_above = df[f'{tf}_macd'] > df[f'{tf}_signal']
            macd_up = df[f'{tf}_macd_up']
            signal_up = df[f'{tf}_signal_up']
            hist_zone = df[f'{tf}_zone']

            score = np.where(macd_above, 1, -1)
            score += np.where(macd_up, 1, 0)
            score += np.where(signal_up, 1, 0)
            score += np.where(hist_zone > 0, 1, np.where(hist_zone < 0, -1, 0))

            df[f'{tf}_power'] = score

        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.fillna(0.0, inplace=True)

        return df

    def generate_signal(self, current_row: pd.Series) -> int:
        req_cols = ['tf1_power', 'tf2_power', 'tf3_power', 'tf4_power', 'bull_div', 'bear_div']
        if not all(col in current_row for col in req_cols):
            return 1

        power1 = current_row['tf1_power']
        power2 = current_row['tf2_power']
        power3 = current_row['tf3_power']
        power4 = current_row['tf4_power']
        bull_div = current_row['bull_div']
        bear_div = current_row['bear_div']

        # SÜPER RALLİ: power1 >= 2 and power2 >= 2 and power3 >= 2 and power4 >= 2
        # RALLİ MODU: power3 >= 2 and power4 >= 2 and (power1 >= 1 or power2 >= 1)
        # ALTIN VURUŞ: power3 >= 2 and power4 >= 2 and power1 <= -1
        # BIÇAK DÜŞÜYOR: power1 <= -2 and power2 <= -2 and power3 <= -2 and power4 <= -2

        scr_ralli = (power3 >= 2) and (power4 >= 2) and ((power1 >= 1) or (power2 >= 1))
        scr_super_ralli = (power1 >= 2) and (power2 >= 2) and (power3 >= 2) and (power4 >= 2)
        scr_altin_vurus = (power3 >= 2) and (power4 >= 2) and (power1 <= -1)
        scr_bicak = (power1 <= -2) and (power2 <= -2) and (power3 <= -2) and (power4 <= -2)

        # 1. LONG Sinyali: Regular Bullish Div + SÜPER RALLİ/RALLİ veya ALTIN VURUŞ
        if bull_div and (scr_ralli or scr_super_ralli or scr_altin_vurus):
            return 2

        # 2. SHORT Sinyali: Regular Bearish Div + BIÇAK DÜŞÜYOR
        if bear_div and scr_bicak:
            return 0

        # 3. HOLD
        return 1
