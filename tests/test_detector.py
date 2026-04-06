import pytest
import pandas as pd
import numpy as np
from core.detector import MarketRegimeDetector

def test_market_regime_detector_bull_trend():
    df = pd.DataFrame({
        'ADX_14': [30],
        'EMA_50': [100],
        'BBU_20_2.0': [110],
        'BBL_20_2.0': [90],
        'SMA_20': [100],
        'close': [105]
    })
    result = MarketRegimeDetector._calculate_regime(df)
    assert result['regime'] == "BULL_TREND"

def test_market_regime_detector_bear_trend():
    df = pd.DataFrame({
        'ADX_14': [30],
        'EMA_50': [100],
        'BBU_20_2.0': [110],
        'BBL_20_2.0': [90],
        'SMA_20': [100],
        'close': [95]
    })
    result = MarketRegimeDetector._calculate_regime(df)
    assert result['regime'] == "BEAR_TREND"

def test_market_regime_detector_choppy_adx():
    df = pd.DataFrame({
        'ADX_14': [20],
        'EMA_50': [100],
        'BBU_20_2.0': [110],
        'BBL_20_2.0': [90],
        'SMA_20': [100],
        'close': [105]
    })
    result = MarketRegimeDetector._calculate_regime(df)
    assert result['regime'] == "CHOPPY"

def test_market_regime_detector_choppy_bbw():
    # bbw < 0.04 -> bbw = (101 - 99) / 100 = 0.02
    df = pd.DataFrame({
        'ADX_14': [30],
        'EMA_50': [100],
        'BBU_20_2.0': [101],
        'BBL_20_2.0': [99],
        'SMA_20': [100],
        'close': [105]
    })
    result = MarketRegimeDetector._calculate_regime(df)
    assert result['regime'] == "CHOPPY"

def test_market_regime_detector_missing_columns():
    df = pd.DataFrame({
        'ADX_14': [30],
        'close': [105]
    })
    with pytest.raises(ValueError, match="Missing required indicator columns"):
        MarketRegimeDetector._calculate_regime(df)

def test_market_regime_detector_empty_df():
    df = pd.DataFrame()
    with pytest.raises(ValueError, match="Empty or None DataFrame provided"):
        MarketRegimeDetector._calculate_regime(df)
