import pandas as pd
import numpy as np

from data.indicators.volume import VolumeIndicators
from data.indicators import StrategyIndicators


def test_vader_basic_calculation():
    """
    VADER indikatörünün temel hesaplamasını, NaN ve inf durumları haricinde doğru
    değerlerle ve kolon adlarıyla dönüp dönmediğini test eder.
    """
    # 20 mumluk sentetik fiyat verisi
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=20, freq="D")

    close_prices = np.linspace(100, 120, 20) + np.random.normal(0, 2, 20)
    high_prices = close_prices + np.random.uniform(1, 3, 20)
    low_prices = close_prices - np.random.uniform(1, 3, 20)
    volume = np.random.uniform(1000, 5000, 20)

    df = pd.DataFrame(
        {
            "high": high_prices,
            "low": low_prices,
            "close": close_prices,
            "volume": volume,
        },
        index=dates,
    )

    # VADER fonksiyonunu çağır (doğrudan VolumeIndicators sınıfından)
    result_df = VolumeIndicators.vader(
        df["high"], df["low"], df["close"], df["volume"], vader_period=14
    )

    # Çıktıların doğrulanması
    assert isinstance(result_df, pd.DataFrame), "Sonuç bir DataFrame olmalıdır."
    assert "vader" in result_df.columns, "DataFrame 'vader' kolonunu içermelidir."
    assert (
        "vader_signal" in result_df.columns
    ), "DataFrame 'vader_signal' kolonunu içermelidir."

    # Sinyal değerleri {0, 1, 2} kümesinde mi?
    assert set(result_df["vader_signal"].unique()).issubset(
        {0, 1, 2}
    ), "Sinyal değerleri 0, 1 veya 2 olmalıdır."

    # İndekslerin korunması
    assert (
        result_df.index == df.index
    ).all(), "Sonuç Dataframe'inin indeksi orijinal indeks ile eşleşmelidir."


def test_vader_division_by_zero_protection():
    """
    VADER algoritmasındaki Data Integrity (Sıfıra Bölünme) kalkanını test eder.
    Hacmin veya fiyat hareketinin sıfır olduğu (yatay piyasa/tatil) bir senaryoda
    sistemin çökmediğini ve 0 döndürdüğünü ispatlar.
    """
    dates = pd.date_range("2023-01-01", periods=10, freq="D")

    # Hacmin ve fiyat hareketinin tamamen 0 olduğu sentetik veriler (Yatay piyasa + Tatil günü simülasyonu)
    # TR ve Volume 0 olacağından ema_vtr de 0 olacaktır.
    df = pd.DataFrame(
        {
            "high": [100.0] * 10,
            "low": [100.0] * 10,
            "close": [100.0] * 10,
            "volume": [0.0] * 10,
        },
        index=dates,
    )

    result_df = VolumeIndicators.vader(
        df["high"], df["low"], df["close"], df["volume"], vader_period=14
    )

    # Sıfıra bölünme sonucu oluşan NaN/inf değerlerin fillna(0) ile 0'a döndüğünü doğrula
    assert (
        not result_df["vader"].isna().any()
    ), "Vader kolonunda NaN değer kalmamalıdır."
    assert not np.isinf(
        result_df["vader"]
    ).any(), "Vader kolonunda Infinity (inf) değer kalmamalıdır."

    # Tüm VADER değerlerinin veri bütünlüğü kalkanı sayesinde 0.0 olması beklenir
    assert (
        result_df["vader"] == 0.0
    ).all(), "Hacim ve TR 0 iken VADER değerleri 0.0'a eşitlenmelidir."


def test_vader_strategy_indicators_facade():
    """
    Facade sınıfı (`StrategyIndicators`) üzerinden çağrıldığında
    dinamik isimlendirmeyle doğru kolon adlarının oluştuğunu test eder.
    """
    dates = pd.date_range("2023-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "high": [105, 106, 107, 108, 107, 106, 105, 104, 103, 102],
            "low": [100, 101, 102, 103, 102, 101, 100, 99, 98, 97],
            "close": [103, 104, 105, 106, 105, 104, 103, 102, 101, 100],
            "volume": [1000] * 10,
        },
        index=dates,
    )

    # Hem normal hem farklı periyot ile ekleme testi
    result_df = StrategyIndicators.add_all_indicators(
        df.copy(), apply_kalman_from_config=False, vader_period=10
    )

    # Sütun isimlerinin dinamik olarak eklenip eklenmediği
    assert "VADER_10" in result_df.columns, "Dinamik VADER_10 kolonu bulunamadı."
    assert (
        "VADER_SIGNAL_10" in result_df.columns
    ), "Dinamik VADER_SIGNAL_10 kolonu bulunamadı."


def test_demand_index_basic_calculation():
    """
    Demand Index'in (DI) DataFrame döndürdüğünü ve beklenen kolonları içerdiğini test eder.
    """
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=30, freq="D")

    df = pd.DataFrame(
        {
            "high": np.linspace(100, 120, 30) + np.random.normal(0, 2, 30),
            "low": np.linspace(90, 110, 30) - np.random.normal(0, 2, 30),
            "close": np.linspace(95, 115, 30) + np.random.normal(0, 2, 30),
            "volume": np.random.uniform(1000, 5000, 30),
        },
        index=dates,
    )

    result_df = VolumeIndicators.demand_index(
        df["high"], df["low"], df["close"], df["volume"], period=19
    )

    assert isinstance(result_df, pd.DataFrame), "Sonuç bir DataFrame olmalıdır."
    assert "di" in result_df.columns, "DataFrame 'di' kolonunu içermelidir."
    assert "di_signal" in result_df.columns, "DataFrame 'di_signal' kolonunu içermelidir."

    assert set(result_df["di_signal"].dropna().unique()).issubset({0, 1, 2}), "Sinyaller 0, 1, 2 olmalıdır."

def test_demand_index_division_by_zero():
    """
    Demand Index sıfıra bölünme ve sıfır fiyat hareketi durumlarını test eder.
    """
    dates = pd.date_range("2023-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "high": [100.0] * 10,
            "low": [100.0] * 10,
            "close": [100.0] * 10,
            "volume": [0.0] * 10,
        },
        index=dates,
    )

    result_df = VolumeIndicators.demand_index(
        df["high"], df["low"], df["close"], df["volume"]
    )

    assert not result_df["di"].isna().any(), "DI NaN içermemelidir."
    assert not np.isinf(result_df["di"]).any(), "DI inf içermemelidir."
    assert (result_df["di"] == 0.0).all(), "Yatay piyasada DI 0.0 dönmelidir."

def test_demand_index_facade_integration():
    """
    StrategyIndicators facade sınıfı üzerinden DI entegrasyonunu test eder.
    """
    dates = pd.date_range("2023-01-01", periods=10, freq="D")
    df = pd.DataFrame(
        {
            "open": [103, 104, 105, 106, 105, 104, 103, 102, 101, 100],
            "high": [105, 106, 107, 108, 107, 106, 105, 104, 103, 102],
            "low": [100, 101, 102, 103, 102, 101, 100, 99, 98, 97],
            "close": [103, 104, 105, 106, 105, 104, 103, 102, 101, 100],
            "volume": [1000] * 10,
        },
        index=dates,
    )

    result_df = StrategyIndicators.add_all_indicators(
        df.copy(), apply_kalman_from_config=False, di_period=15
    )

    assert "DI_VAL_15" in result_df.columns, "Dinamik DI_VAL_15 kolonu bulunamadı."
    assert "DI_SIGNAL_15" in result_df.columns, "Dinamik DI_SIGNAL_15 kolonu bulunamadı."
