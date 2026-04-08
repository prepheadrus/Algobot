import pytest
import pandas as pd
import numpy as np
from data.indicators.momentum import MomentumIndicators
from data.indicators.__init__ import StrategyIndicators

def test_bear_power_basic():
    # Temel Bear Power hesaplamasını test et
    close = pd.Series([100, 102, 101, 105, 103, 104, 102, 100])
    low = pd.Series([99, 100, 99, 103, 101, 102, 100, 98])

    df = MomentumIndicators.bear_power(low, close, period=3)

    assert 'bear_power' in df.columns
    assert 'bear_power_signal' in df.columns

    # NaN/Inf shield kontrolü (hiçbir değerin NaN veya Inf olmaması lazım)
    assert not df['bear_power'].isna().any()
    assert not np.isinf(df['bear_power']).any()

    # Sinyal değerlerinin 0, 1, veya 2 olduğunun kontrolü
    assert df['bear_power_signal'].isin([0, 1, 2]).all()

def test_bear_power_neutral_signal():
    # Nötr sinyal (1) kontrolü: low == ema
    close = pd.Series([100] * 10) # Sabit kapanış, EMA 100 olacak
    low = pd.Series([100] * 10)   # Düşük de 100, böylece low - ema = 0

    df = MomentumIndicators.bear_power(low, close, period=3)

    # Tam eşitlik durumunda bear_power == 0 olacağından sinyal 1 olmalı
    assert (df['bear_power_signal'] == 1).all()

def test_cci_basic():
    # Temel CCI hesaplamasını test et
    high = pd.Series([105, 106, 107, 108, 109, 110, 105, 100])
    low = pd.Series([100, 101, 102, 103, 104, 105, 100, 95])
    close = pd.Series([102, 103, 104, 105, 106, 107, 102, 98])

    df = MomentumIndicators.cci(high, low, close, period=3)

    assert 'cci' in df.columns
    assert 'cci_signal' in df.columns

    assert not df['cci'].isna().any()
    assert not np.isinf(df['cci']).any()

    assert df['cci_signal'].isin([0, 1, 2]).all()

def test_cci_flat_market_zero_division():
    # Sıfıra bölünme hatasını (Flat Market senaryosu) test et
    # Eğer tüm high, low ve close aynıysa ve değişmiyorsa, MAD 0 olur.
    flat_series = pd.Series([100.0] * 10)

    df = MomentumIndicators.cci(flat_series, flat_series, flat_series, period=3)

    # fillna(0) kalkanı sayesinde 0 dönmesini bekliyoruz, NaN/Inf olmamalı
    assert (df['cci'] == 0.0).all()
    # Eğer CCI 0 ise, > 100 veya < -100 kurallarından geçemez, sinyal 1 (BEKLE) olmalı
    assert (df['cci_signal'] == 1).all()

def test_facade_integration():
    # Facade / Wrapper entegrasyonunu test et
    df = pd.DataFrame({
        'high': [105, 106, 107, 108, 109],
        'low': [100, 101, 102, 103, 104],
        'close': [102, 103, 104, 105, 106]
    })

    # add_all_indicators çağrısını simüle et
    df_result = StrategyIndicators.add_all_indicators(df, bear_period=3, cci_period=3)

    assert 'BEAR_POWER_3' in df_result.columns
    assert 'BEAR_POWER_SIGNAL_3' in df_result.columns
    assert 'CCI_3' in df_result.columns
    assert 'CCI_SIGNAL_3' in df_result.columns
