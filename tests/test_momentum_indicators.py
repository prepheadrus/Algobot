import pandas as pd
import numpy as np

from data.indicators.momentum import MomentumIndicators
from data.indicators import StrategyIndicators

def test_trix_basic_calculation():
    """
    Test TRIX calculation returns valid dataframe containing 'trix_val' and 'trix_signal'
    """
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=50, freq="D")

    df = pd.DataFrame(
        {
            "close": np.linspace(95, 145, 50) + np.random.normal(0, 2, 50),
        },
        index=dates,
    )

    result_df = MomentumIndicators.trix(df["close"], period=18, signal_period=9)

    assert isinstance(result_df, pd.DataFrame), "Output must be a DataFrame"
    assert "trix_val" in result_df.columns, "Output must contain 'trix_val'"
    assert "trix_signal" in result_df.columns, "Output must contain 'trix_signal'"

    # Check that signals are mapped to 0, 1, 2
    assert set(result_df["trix_signal"].dropna().unique()).issubset({0, 1, 2})

def test_trix_flat_market_protection():
    """
    Test TRIX zero-division protection in case of completely flat market (pct_change yields inf/nan)
    """
    dates = pd.date_range("2023-01-01", periods=30, freq="D")

    df = pd.DataFrame(
        {
            "close": [100.0] * 30,
        },
        index=dates,
    )

    result_df = MomentumIndicators.trix(df["close"], period=18, signal_period=9)

    assert not result_df["trix_val"].isna().any(), "trix_val should not have NaNs"
    assert not np.isinf(result_df["trix_val"]).any(), "trix_val should not have infinities"

    # In a flat market, pct_change will be 0 or NaN, and our shield (replace inf -> nan -> fillna 0.0)
    # should ensure exactly 0.0 momentum
    assert (result_df["trix_val"] == 0.0).all(), "Zero-division should fallback to 0.0 for TRIX"
    # The signal will be 2 (because trix_val >= trix_sma, which is 0.0 == 0.0) or 1 depending on where condition.
    # Since we used np.where(trix_val > trix_sma, 2, np.where(trix_val < trix_sma, 0, 1)), it evaluates to 1
    assert (result_df["trix_signal"] == 1).all(), "Flat market should yield neutral/1 signal"

def test_ultimate_oscillator_basic_calculation():
    """
    Test UO calculation returns valid dataframe containing 'uo_val' and 'uo_signal'
    """
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=50, freq="D")

    df = pd.DataFrame(
        {
            "high": np.linspace(100, 150, 50) + np.random.normal(0, 2, 50),
            "low": np.linspace(90, 140, 50) - np.random.normal(0, 2, 50),
            "close": np.linspace(95, 145, 50) + np.random.normal(0, 2, 50),
        },
        index=dates,
    )

    result_df = MomentumIndicators.ultimate_oscillator(
        df["high"], df["low"], df["close"]
    )

    assert isinstance(result_df, pd.DataFrame), "Output must be a DataFrame"
    assert "uo_val" in result_df.columns, "Output must contain 'uo_val'"
    assert "uo_signal" in result_df.columns, "Output must contain 'uo_signal'"

    # Check that signals are mapped to 0, 1, 2
    assert set(result_df["uo_signal"].dropna().unique()).issubset({0, 1, 2})

def test_ultimate_oscillator_division_by_zero():
    """
    Test UO zero-division protection in case of completely flat market
    """
    dates = pd.date_range("2023-01-01", periods=30, freq="D")

    df = pd.DataFrame(
        {
            "high": [100.0] * 30,
            "low": [100.0] * 30,
            "close": [100.0] * 30,
        },
        index=dates,
    )

    result_df = MomentumIndicators.ultimate_oscillator(
        df["high"], df["low"], df["close"]
    )

    assert not result_df["uo_val"].isna().any(), "uo_val should not have NaNs"
    assert not np.isinf(result_df["uo_val"]).any(), "uo_val should not have infinities"

    # Check the fallback value from the data integrity shield (fillna(50.0))
    # It should be 50.0 because TR is 0, so average terms become NaN -> total is NaN -> fillna(50.0)
    assert (result_df["uo_val"] == 50.0).all(), "Zero-division should fallback to 50.0"

def test_ultimate_oscillator_legacy_wrapper():
    """
    Test the legacy uo wrapper returns just a Series with values equal to uo_val
    """
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=50, freq="D")

    df = pd.DataFrame(
        {
            "high": np.linspace(100, 150, 50) + np.random.normal(0, 2, 50),
            "low": np.linspace(90, 140, 50) - np.random.normal(0, 2, 50),
            "close": np.linspace(95, 145, 50) + np.random.normal(0, 2, 50),
        },
        index=dates,
    )

    new_result = MomentumIndicators.ultimate_oscillator(df["high"], df["low"], df["close"])
    old_result = MomentumIndicators.uo(df["high"], df["low"], df["close"])

    assert isinstance(old_result, pd.Series), "Legacy method must return a pandas Series"
    pd.testing.assert_series_equal(new_result["uo_val"], old_result, check_names=False)

def test_ultimate_oscillator_facade_integration():
    """
    Test that the StrategyIndicators facade adds the UO dynamic column correctly.
    """
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=50, freq="D")

    df = pd.DataFrame(
        {
            "open": np.linspace(100, 150, 50),
            "high": np.linspace(100, 150, 50) + np.random.normal(0, 2, 50),
            "low": np.linspace(90, 140, 50) - np.random.normal(0, 2, 50),
            "close": np.linspace(95, 145, 50) + np.random.normal(0, 2, 50),
            "volume": np.random.uniform(1000, 5000, 50)
        },
        index=dates,
    )

    res_df = StrategyIndicators.add_all_indicators(df, apply_kalman_from_config=False)

    assert "UO_7_14_28" in res_df.columns, "Dynamic UO signal column missing"
    assert "UO" in res_df.columns, "Legacy UO value column missing"
