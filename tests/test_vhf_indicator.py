import pytest
import pandas as pd
import numpy as np

from data.indicators.trend import TrendIndicators

class TestVHFIndicator:
    def test_vhf_basic_calculation(self):
        """
        VHF'in standart hesaplanmasını ve periyot eksikliklerinde
        beklenen davranışları sergilediğini test eder.
        """
        close = pd.Series([100, 102, 101, 105, 104, 108, 107])
        df = TrendIndicators.vhf(close, period=3, vhf_sma_period=2)

        assert 'vhf_val' in df.columns
        assert 'vhf_sma' in df.columns
        assert 'vhf_signal' in df.columns

        # İlk periyotların NaN gelmeyip 0.0 ve Signal 1 (NEUTRAL) olduğunu doğrula
        assert df['vhf_val'].iloc[0] == 0.0
        assert df['vhf_signal'].iloc[0] == 1
        assert df['vhf_signal'].iloc[1] == 1

        # Sonraki değerlerin doğruluğu (1.0 gibi tavan sınırları test edilir)
        assert df['vhf_val'].iloc[1] == 1.0

    def test_vhf_flat_market_division_by_zero(self):
        """
        Flat Market (Fiyatın hiç değişmediği piyasa) durumunda
        paydanın (denominator) 0 olması sonucu ortaya çıkabilecek Infinity
        hatasının '.replace(0, np.nan)' kalkanıyla nasıl sönümlendiğini
        ve '0.0' değerinin döndüğünü test eder.
        """
        # 100 bar boyunca fiyat hep aynı: 100
        close = pd.Series([100.0] * 100)

        df = TrendIndicators.vhf(close, period=14, vhf_sma_period=10)

        # Infinity sızıntısı olmadığından emin ol
        assert not np.isinf(df['vhf_val']).any()
        assert not np.isinf(df['vhf_sma']).any()

        # Tüm vhf değerleri Data Integrity Shield sayesinde 0.0 olmalıdır
        assert (df['vhf_val'] == 0.0).all()

        # NaN olmamalıdır
        assert not df['vhf_val'].isna().any()

        # Fiyat değişmediği için (0 > 0 veya 0 < 0 değil), numpy.where 1 (NEUTRAL) üretmelidir
        assert (df['vhf_signal'] == 1).all()
