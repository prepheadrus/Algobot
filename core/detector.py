import asyncio
import pandas as pd
import numpy as np

from shared.events.event_bus import event_bus, Event


class MarketRegimeDetector:
    """
    Market Regime Detector (Phase 1)
    
    Identifies the market regime ("BULL_TREND", "BEAR_TREND", "CHOPPY")
    mathematically based on pre-calculated indicators in the DataFrame.
    
    Expected indicators in df:
        - ADX_14
        - EMA_50
        - BBU_20_2.0
        - BBL_20_2.0
        - SMA_20
        - close
    """

    @staticmethod
    def detect_regime(df: pd.DataFrame) -> dict:
        """
        Calculates the market regime vectorically using numpy and pandas.
        This is a CPU-bound operation.
        """
        if df is None or df.empty:
            raise ValueError("Empty or None DataFrame provided for market regime detection.")

        # Required columns mapping based on typical indicator names
        required_columns = ['ADX_14', 'EMA_50', 'BBU_20_2.0', 'BBL_20_2.0', 'SMA_20', 'close']

        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required indicator columns for regime detection: {missing_cols}")

        # Get the latest row
        latest = df.iloc[-1]
        
        # Bollinger Squeeze calculation
        # Formula: bbw = (BBU_20_2.0 - BBL_20_2.0) / SMA_20
        bbw = (latest['BBU_20_2.0'] - latest['BBL_20_2.0']) / latest['SMA_20']
        
        adx_val = latest['ADX_14']
        close_price = latest['close']
        ema_50 = latest['EMA_50']
        
        # Determine regime
        if adx_val <= 25 or bbw < 0.04:
            regime = "CHOPPY"
        elif adx_val > 25 and close_price > ema_50:
            regime = "BULL_TREND"
        elif adx_val > 25 and close_price < ema_50:
            regime = "BEAR_TREND"
        else:
            # Fallback, though logical conditions above should cover most
            regime = "CHOPPY"

        return {
            "regime": regime,
            "adx": float(adx_val),
            "bbw": float(bbw),
            "close": float(close_price),
            "ema_50": float(ema_50)
        }

    @staticmethod
    async def detect_and_publish(symbol: str, timeframe: str, df: pd.DataFrame):
        """
        Detects the market regime asynchronously (offloading CPU-bound tasks)
        and publishes the result via the event bus.
        """
        try:
            # Offload CPU-bound calculation to thread pool
            result = await asyncio.to_thread(MarketRegimeDetector.detect_regime, df)

            # Publish event directly via the event bus
            event_payload = {
                "symbol": symbol,
                "timeframe": timeframe,
                "regime": result["regime"],
                "metrics": result
            }

            await event_bus.publish(
                Event(
                    type="regime.changed",
                    payload=event_payload,
                    source="market_regime_detector"
                )
            )

        except Exception as e:
            # Log the error but don't crash the event loop
            import logging
            logger = logging.getLogger("core.detector")
            logger.error(f"Failed to detect and publish market regime for {symbol}: {e}")
