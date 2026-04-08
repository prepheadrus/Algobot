import pytest
import pandas as pd
import numpy as np
from data.indicators.trend import TrendIndicators

class TestRegimeIndicators:
    """
    Unit tests for regime and trend indicators.
    """

    def test_chop_normal_calculation(self):
        """
        Test normal CHOP computation on synthetic trending data.
        """
        # Create a synthetic trending market
        np.random.seed(42)
        base = np.linspace(100, 200, 100)
        high = pd.Series(base + np.random.rand(100) * 5 + 5)
        low = pd.Series(base - np.random.rand(100) * 5 - 5)
        close = pd.Series(base + np.random.rand(100) * 2 - 1)

        df_chop = TrendIndicators.chop(high, low, close, period=14)

        assert isinstance(df_chop, pd.DataFrame)
        assert 'chop' in df_chop.columns
        assert 'chop_signal' in df_chop.columns
        assert len(df_chop) == 100

        # Check integrity shield values
        assert not df_chop['chop'].isna().any()
        assert not df_chop['chop_signal'].isna().any()

    def test_chop_flat_market_shield(self):
        """
        TDD Test: Simulate a completely flat market to ensure the zero-division and
        logarithm shield works flawlessly, preventing -inf, NaN leaks and returning exactly 50.0.
        """
        # Create a perfectly flat market for 100 periods
        high = pd.Series(np.full(100, 50000.0))
        low = pd.Series(np.full(100, 50000.0))
        close = pd.Series(np.full(100, 50000.0))

        df_chop = TrendIndicators.chop(high, low, close, period=14)

        # In a perfectly flat market, range_hl becomes 0.
        # The shield should set chop values to the neutral 50.0 without any RuntimeWarning.
        assert (df_chop['chop'] == 50.0).all(), "CHOP should be exactly 50.0 in a flat market."

        # For chop == 50.0, the signal should be 1 (neutral).
        assert (df_chop['chop_signal'] == 1).all(), "CHOP signal should be exactly 1 (neutral) in a flat market."
