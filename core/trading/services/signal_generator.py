import asyncio
import pandas as pd
from typing import Tuple
from data.indicators import StrategyIndicators
from data.indicators.trend import TrendIndicators
from data.features import AdvancedFeatures
from core.detector import MarketRegimeDetector

# Bellek Optimizasyonu (Downcasting)
try:
    from data.data_prep import reduce_mem_usage
except ImportError:

    def reduce_mem_usage(df):
        return df


class SignalGeneratorService:
    """
    Sinyal üretme ve teknik analiz hesaplamalarını yönetir.
    ExchangeManager'ın run_strategy_poller metodundaki ağır pandas işlerini hafifletmek için.
    """

    @staticmethod
    async def prepare_target_data_and_detect_regime(
        df_1m: pd.DataFrame,
        target_tf: str,
        htf_levels: list,
        ema_fast: int,
        ema_slow: int,
        trend_method: str,
    ) -> Tuple[pd.DataFrame, dict, dict, float]:
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
                df_1m.index = df_1m.index.tz_localize("UTC")
            else:
                df_1m.index = df_1m.index.tz_convert("UTC")

            # 1. Resample to Target TF
            df_target = StrategyIndicators.resample_data(df_1m, target_tf)

            # 2. Process HTF Trends
            htf_trends = {}
            for htf_tf in htf_levels:
                df_htf = StrategyIndicators.resample_data(df_1m, htf_tf)
                trend = "NEUTRAL"
                if not df_htf.empty:
                    # Optimize: Sadece gereken EMA'ları hesapla, add_all_indicators'u ÇAĞIRMA
                    if trend_method == "ema_stack":
                        df_htf[f"EMA_{ema_fast}"] = TrendIndicators.ema(df_htf['close'], ema_fast)
                        df_htf[f"EMA_{ema_slow}"] = TrendIndicators.ema(df_htf['close'], ema_slow)

                        htf_last = df_htf.iloc[-1]
                        ema_f = htf_last.get(f"EMA_{ema_fast}")
                        ema_s = htf_last.get(f"EMA_{ema_slow}")

                        if pd.notna(ema_f) and pd.notna(ema_s):
                            if ema_f > ema_s:
                                trend = "BULL"
                            elif ema_f < ema_s:
                                trend = "BEAR"
                    else:
                        df_htf[f"EMA_{ema_slow}"] = TrendIndicators.ema(df_htf['close'], ema_slow)

                        htf_last = df_htf.iloc[-1]
                        val_c = htf_last.get("close")
                        val_e = htf_last.get(f"EMA_{ema_slow}")

                        if pd.notna(val_c) and pd.notna(val_e):
                            if val_c > val_e:
                                trend = "BULL"
                            elif val_c < val_e:
                                trend = "BEAR"

                    htf_trends[htf_tf] = trend

            # 3. Target Indicators & Regime
            df_target = StrategyIndicators.add_all_indicators(df_target)
            df_target["volatility_ema"] = AdvancedFeatures.get_volatility(
                df_target["close"], span=20
            )

            # Vektörize ffill/bfill kopyalamayı azaltmak için atama kullanıyoruz.
            df_target = df_target.ffill().bfill()

            # Bellek Optimizasyonu: İndikatör hesaplamaları (float64) sonrası downcasting yaparak RAM şişmesini önle.
            df_target = reduce_mem_usage(df_target)

            if not df_target.empty:
                regime_info = MarketRegimeDetector.detect_regime(df_target)
                current_price = float(
                    df_target.iloc[-1]["close"]
                )  # Downcasting float32 olabilir, standard float'a çevir
                return df_target, htf_trends, regime_info, current_price
            return df_target, htf_trends, {"regime": "UNKNOWN"}, None

        # Arka planda çalıştır
        return await asyncio.to_thread(_process_data)


signal_generator_service = SignalGeneratorService()
