import asyncio
import pandas as pd
from typing import Tuple
from data.indicators import StrategyIndicators
from data.features import AdvancedFeatures
from core.detector import MarketRegimeDetector
import numpy as np


class SignalGeneratorService:
    """
    Sinyal üretme ve teknik analiz hesaplamalarını yönetir.
    ExchangeManager'ın run_strategy_poller metodundaki ağır pandas işlerini hafifletmek için.
    """

    @staticmethod
    async def prepare_target_data_and_detect_regime(df_1m: pd.DataFrame, target_tf: str, htf_levels: list, ema_fast: int, ema_slow: int, trend_method: str) -> Tuple[pd.DataFrame, dict, dict, float]:
        """
        Ağır pandas hesaplamalarını asyncio.to_thread içine sararak Event Loop'u kilitlemez.

        [TZ FIX] DataFrame index'inin UTC olduğundan emin ol.
        """
        def _process_data():
            # ========================================================================
            # [TZ FIX] DataFrame index UTC yap (timezone-aware)
            # ========================================================================
            # Önce DatetimeIndex'e çevir (eğer değilse)
            if not isinstance(df_1m.index, pd.DatetimeIndex):
                df_1m.index = pd.to_datetime(df_1m.index, utc=True)

            # Sonra timezone-aware yap
            if df_1m.index.tzinfo is None:
                df_1m.index = df_1m.index.tz_localize('UTC')
            else:
                df_1m.index = df_1m.index.tz_convert('UTC')

            # 1. Resample to Target TF
            df_target = StrategyIndicators.resample_data(df_1m, target_tf)

            # 2. Process HTF Trends
            htf_trends = {}
            for htf_tf in htf_levels:
                df_htf = StrategyIndicators.resample_data(df_1m, htf_tf)
                df_htf = StrategyIndicators.add_all_indicators(df_htf)
                trend = "NEUTRAL"
                if not df_htf.empty:
                    htf_last = df_htf.iloc[-1]
                    if trend_method == 'ema_stack':
                        ema_f = htf_last.get(f'EMA_{ema_fast}')
                        ema_s = htf_last.get(f'EMA_{ema_slow}')
                        if ema_f is not None and ema_s is not None and not np.isnan(ema_f) and not np.isnan(ema_s):
                            if ema_f > ema_s:
                                trend = "BULL"
                            elif ema_f < ema_s:
                                trend = "BEAR"
                    else:
                        val_c = htf_last.get('close')
                        val_e = htf_last.get(f'EMA_{ema_slow}')
                        if val_c is not None and val_e is not None and not np.isnan(val_c) and not np.isnan(val_e):
                            if val_c > val_e:
                                trend = "BULL"
                            elif val_c < val_e:
                                trend = "BEAR"
                    htf_trends[htf_tf] = trend

            # 3. Target Indicators & Regime
            df_target = StrategyIndicators.add_all_indicators(df_target)
            df_target['volatility_ema'] = AdvancedFeatures.get_volatility(df_target['close'], span=20)
            df_target.ffill(inplace=True)
            df_target.bfill(inplace=True)

            if not df_target.empty:
                regime_info = MarketRegimeDetector.detect_regime(df_target)
                current_price = df_target.iloc[-1]['close']
                return df_target, htf_trends, regime_info, current_price
            return df_target, htf_trends, {'regime': 'UNKNOWN'}, None

        # Arka planda çalıştır
        return await asyncio.to_thread(_process_data)


signal_generator_service = SignalGeneratorService()
