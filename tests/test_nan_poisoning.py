import pandas as pd
import numpy as np
from data.indicators import StrategyIndicators

def test_add_all_indicators_nan_poisoning():
    """
    Test that the indicator calculation pipeline does not introduce NaN poisoning.
    It verifies that .fillna() shields are working correctly across all modules.
    """
    np.random.seed(42)
    n = 100
    df = pd.DataFrame({
        'open': np.random.uniform(100, 105, n),
        'high': np.random.uniform(105, 110, n),
        'low': np.random.uniform(95, 100, n),
        'close': np.random.uniform(100, 105, n),
        'volume': np.random.uniform(1000, 2000, n),
    })
    df.index = pd.date_range('2023-01-01', periods=n, freq='1h')

    # Apply all indicators
    df_ind = StrategyIndicators.add_all_indicators(df)

    # Check for NaNs
    nan_count = df_ind.isna().sum().sum()

    # Assert that there are no NaNs in the resulting DataFrame
    assert nan_count == 0, f"Found {nan_count} NaN values after applying indicators. Suspected poisoning in Data Integrity Shields."
