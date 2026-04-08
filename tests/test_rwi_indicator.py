import pytest
import pandas as pd
import numpy as np
from data.indicators.trend import TrendIndicators

@pytest.fixture
def sample_data():
    """RWI testi için standart piyasa verisi (Trend ve Volatilite içerir)."""
    np.random.seed(42)
    n = 100
    # Artan bir trend oluşturalım
    close = np.linspace(10, 20, n) + np.random.normal(0, 0.5, n)
    high = close + np.random.uniform(0.1, 1.0, n)
    low = close - np.random.uniform(0.1, 1.0, n)

    return pd.DataFrame({
        'high': high,
        'low': low,
        'close': close
    })

@pytest.fixture
def flat_market_data():
    """Hareketsiz piyasa (Flat Market) senaryosu. High == Low == Close."""
    n = 100
    price = 100.0
    return pd.DataFrame({
        'high': np.full(n, price),
        'low': np.full(n, price),
        'close': np.full(n, price)
    })

def test_rwi_standard_calculation(sample_data):
    """RWI'nin normal piyasa koşullarında sorunsuz hesaplandığını doğrular."""
    df = TrendIndicators.rwi(
        sample_data['high'],
        sample_data['low'],
        sample_data['close'],
        period=14
    )

    # Beklenen kolonların kontrolü
    assert 'rwi_high' in df.columns
    assert 'rwi_low' in df.columns
    assert 'rwi_signal' in df.columns

    # Sinyal değerlerinin 0, 1 veya 2 olduğunu doğrula
    valid_signals = {0, 1, 2}
    assert set(df['rwi_signal'].unique()).issubset(valid_signals)

    # NaN değer içermediğini kontrol et
    assert not df['rwi_high'].isna().any()
    assert not df['rwi_low'].isna().any()

def test_rwi_division_by_zero_protection(flat_market_data):
    """
    Sıfıra bölünme korumasını test eder.
    Hareketsiz piyasada ATR = 0 olacağı için inf fırlatılmamalı ve 0 dönmelidir.
    """
    df = TrendIndicators.rwi(
        flat_market_data['high'],
        flat_market_data['low'],
        flat_market_data['close'],
        period=14
    )

    # Veri Bütünlüğü: Inf veya NaN üretilmemeli, tam 0.0 olmalı
    assert np.all(df['rwi_high'] == 0.0)
    assert np.all(df['rwi_low'] == 0.0)

    # Sinyal yatay piyasa (Neutral/1) veya (Short/0) olabilir ama Inf'den çökmemeli
    # Tüm değerler 0.0 olduğu için (0 > 1) şartları sağlanmayacak ve sinyal 1 olacak.
    assert np.all(df['rwi_signal'] == 1)

def test_rwi_insufficient_data():
    """Yetersiz veri durumunda (n < period) doğru default dönüşleri kontrol eder."""
    n = 10
    period = 14
    df_short = pd.DataFrame({
        'high': np.random.rand(n),
        'low': np.random.rand(n),
        'close': np.random.rand(n)
    })

    df = TrendIndicators.rwi(
        df_short['high'],
        df_short['low'],
        df_short['close'],
        period=period
    )

    assert len(df) == n
    assert np.all(df['rwi_high'] == 0.0)
    assert np.all(df['rwi_low'] == 0.0)
    assert np.all(df['rwi_signal'] == 1)
