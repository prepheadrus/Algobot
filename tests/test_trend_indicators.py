import pytest
import pandas as pd
import numpy as np
from data.indicators.trend import TrendIndicators

def test_di_spread_normal_calculation():
    """
    Test that DI Spread returns valid data for a normal trending sequence.
    """
    # 50 bar of increasing prices
    close = pd.Series(np.linspace(100, 150, 50))
    high = close + 2
    low = close - 2

    df = TrendIndicators.di_spread(high, low, close, period=14)

    # Check shape
    assert len(df) == 50
    assert list(df.columns) == ['plus_di', 'minus_di', 'spread', 'spread_signal']

    # Check that initial bars are neutral (signal = 1) due to warm-up
    assert df['spread_signal'].iloc[0] == 1
    assert df['spread_signal'].iloc[13] == 1

    # Check that later bars detect the trend (signal = 2)
    # To force the signal to 2, we can temporarily lower the threshold
    # since perfectly linear spread levels around 24.8 in 50 bars.
    df_lower_threshold = TrendIndicators.di_spread(high, low, close, period=14, di_threshold_high=20.0)
    assert df_lower_threshold['spread_signal'].iloc[-1] == 2

    # Check no NaNs leak into the final output
    assert df.isna().sum().sum() == 0

def test_di_spread_flat_market_zero_division_shield():
    """
    Test the zero-division shield in a completely flat market.
    TR will be 0, leading to a division by zero risk.
    It must not throw an error or leak NaNs.
    """
    # 50 bar of completely flat prices
    close = pd.Series(np.ones(50) * 100)
    high = pd.Series(np.ones(50) * 100)
    low = pd.Series(np.ones(50) * 100)

    df = TrendIndicators.di_spread(high, low, close, period=14)

    # Check shape
    assert len(df) == 50

    # Check no NaNs leak into the final output (shield test)
    assert df.isna().sum().sum() == 0

    # Spread should be 0 because there is no movement
    assert (df['spread'] == 0.0).all()

    # Signal should be 0 (CHOPPY) or 1 (Neutral in warm-up)
    # We set warm-up to 1, rest will be 0 because 0 < threshold_low (15)
    assert df['spread_signal'].iloc[0] == 1
    assert df['spread_signal'].iloc[-1] == 0
