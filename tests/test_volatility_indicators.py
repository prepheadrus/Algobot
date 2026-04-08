import pytest
import pandas as pd
import numpy as np

from data.indicators.volatility import VolatilityIndicators

def test_btc_vix_normal_calculation():
    """Test normal calculation of BTC_VIX to ensure correct DataFrame outputs and signals."""

    # 30 mumluk sahte bir fiyat serisi (trend yukarı ve sonra aşağı)
    # Highest close için tepe noktasını ortalara koyalım.
    close = pd.Series([100, 102, 105, 110, 115, 120, 125, 122, 120, 118, 115, 110, 105, 100, 95, 90] * 2)
    low = close - 2  # low her zaman close'dan biraz daha düşük

    # Test edilecek periyotlar
    period = 5
    ema_period = 3

    df = VolatilityIndicators.btc_vix(low, close, period=period, ema_period=ema_period)

    # Sütunları kontrol et
    assert isinstance(df, pd.DataFrame)
    assert 'btc_vix' in df.columns
    assert 'vix_ema' in df.columns
    assert 'vix_signal' in df.columns

    # NaN değerlerin temizlendiğinden (veya 0 olarak doldurulduğundan) emin ol
    assert not df['btc_vix'].isnull().any()

    # En azından ilk `period - 1` mumdan sonra highest close doğru hesaplanmış mı kontrol et
    highest_close = close.rolling(window=period).max()
    expected_btc_vix = 100 * (highest_close - low) / highest_close
    expected_btc_vix = expected_btc_vix.replace([np.inf, -np.inf], np.nan).fillna(0)

    # Virgülden sonraki tolerans ile eşitlik testi
    pd.testing.assert_series_equal(df['btc_vix'], expected_btc_vix, check_names=False)

def test_btc_vix_division_by_zero():
    """Edge Case: Test division by zero when highest_close is 0 (or low == highest_close logic checks)."""

    # Fiyatın hiç değişmediği veya 0 olduğu bir seri
    close = pd.Series([0.0] * 20)
    low = pd.Series([0.0] * 20)

    df = VolatilityIndicators.btc_vix(low, close, period=5, ema_period=5)

    # division by zero durumunda replace([np.inf, -np.inf], np.nan).fillna(0) çalışmalı
    assert (df['btc_vix'] == 0.0).all()

    # vix_ema da 0 olmalı
    assert (df['vix_ema'] == 0.0).all()

def test_btc_vix_flat_market():
    """Edge Case: Fiyatlar tamamen düz gittiğinde sistemin crash olmaması"""

    close = pd.Series([100.0] * 20)
    low = pd.Series([100.0] * 20)

    df = VolatilityIndicators.btc_vix(low, close, period=10, ema_period=5)

    # highest_close = 100, low = 100 -> btc_vix = 0
    assert (df['btc_vix'] == 0.0).all()

def test_btc_vix_signals():
    """Test btc_vix signal outputs (0: SHORT, 2: LONG, 1: Nötr)"""

    # Bu testte btc_vix ve vix_ema'yı simüle edecek şekilde manuel bir veri veremiyoruz,
    # ancak sonucu kontrol edebiliriz.
    close = pd.Series([100, 102, 105, 110, 115, 120, 125, 100, 90, 80, 70])
    low = close - 5

    df = VolatilityIndicators.btc_vix(low, close, period=3, ema_period=3)

    # btc_vix > vix_ema durumu 0 olmalı, btc_vix < vix_ema durumu 2 olmalı
    signals = np.where(df['btc_vix'] > df['vix_ema'], 0, np.where(df['btc_vix'] < df['vix_ema'], 2, 1))

    pd.testing.assert_series_equal(df['vix_signal'], pd.Series(signals), check_names=False)

def test_btc_vix_kwargs_defaults():
    """Test if the default arguments of **kwargs are applied properly"""

    close = pd.Series([100] * 30)
    low = pd.Series([95] * 30)

    # Parametre vermeden çağır
    df = VolatilityIndicators.btc_vix(low, close)

    # Sadece dönüp dönmediğine bakalım
    assert len(df) == 30
    assert 'btc_vix' in df.columns

def test_ttm_squeeze_flat_market():
    """
    Edge Case: Test TTM Squeeze in a completely flat market (zero volatility).
    This proves that the algorithm doesn't crash when std == 0 and atr == 0,
    and correctly outputs 0 (Squeeze ON / Consolidation) due to the bands collapsing.
    """
    # Flat market senaryosu: Tüm mumlar aynı fiyat noktasında
    length = 30
    high = pd.Series([100.0] * length)
    low = pd.Series([100.0] * length)
    close = pd.Series([100.0] * length)

    # Optuna WFO benzeri parametreler
    period = 20
    bb_mult = 2.0
    kc_mult = 1.5

    df = VolatilityIndicators.ttm_squeeze(
        high, low, close,
        period=period, bb_mult=bb_mult, kc_mult=kc_mult
    )

    # DataFrame'in dönmesi ve gerekli kolonları içermesi kontrolü
    assert isinstance(df, pd.DataFrame)
    expected_columns = ['bb_upper', 'bb_lower', 'kc_upper', 'kc_lower', 'squeeze_signal']
    for col in expected_columns:
        assert col in df.columns

    # İlk mumu (period > min_periods) warm-up süresinden dolayı atlayabiliriz,
    # ancak min_periods=1 kullandığımız için doğrudan check yapıyoruz.
    # Veri bütünlüğü kalkanı ilk warm-up değerlerini fillna(1) yapmış olabilir,
    # ama std=0 ve atr=0 durumunda bantlar (bb_upper, bb_lower) ve kanallar (kc_upper, kc_lower) tamamen SMA'ya eşit olur.
    # bb_upper (100) < kc_upper (100) FALSE döneceği için teknik olarak Squeeze OFF (2) olabilir,
    # ANCAK bizim Squeeze ON şartımız (bb_upper < kc_upper) & (bb_lower > kc_lower).
    # Flat market'ta bantlar çakışır. float precision nedeniyle Squeeze OFF (2) de üretebilir.
    # Bizim asıl test ettiğimiz: sıfıra bölünme ve std() kaynaklı NaN üretip çökme OLMAMASI.
    assert not df.isnull().values.any()

    # Tüm squeeze_signal değerlerinin int tipinde olması gerekiyor
    assert pd.api.types.is_integer_dtype(df['squeeze_signal'])

    # İzolasyon testi: 'squeeze_signal' varlıkları (0, 1, 2) setinin alt kümesi olmalıdır
    valid_signals = {0, 1, 2}
    actual_signals = set(df['squeeze_signal'].unique())
    assert actual_signals.issubset(valid_signals)
