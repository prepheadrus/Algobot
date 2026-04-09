import pytest
import pandas as pd
import numpy as np
from sklearn.model_selection import TimeSeriesSplit

def test_time_series_split_purging():
    """
    Test that TimeSeriesSplit with 'gap' correctly implements Purging/Embargo
    to prevent Look-ahead Bias (Data Leakage) between train and validation sets.
    """
    n_samples = 100
    horizon = 10
    n_splits = 5

    # Create dummy data
    X = pd.DataFrame({'feature': np.random.randn(n_samples)})

    # Initialize TimeSeriesSplit with gap=horizon
    tscv = TimeSeriesSplit(n_splits=n_splits, gap=horizon)

    splits = list(tscv.split(X))

    assert len(splits) == n_splits, f"Expected {n_splits} splits, got {len(splits)}"

    for i, (train_index, val_index) in enumerate(splits):
        # Assert that validation set always comes strictly after train set
        assert val_index[0] > train_index[-1], "Validation set must be chronologically after the train set."

        # Calculate the actual gap between train and validation
        actual_gap = val_index[0] - train_index[-1] - 1

        # The actual gap must be exactly equal to the horizon (since gap=horizon in TimeSeriesSplit)
        assert actual_gap == horizon, f"Fold {i}: Expected gap of {horizon}, got {actual_gap}"
