import pytest
import pandas as pd
import numpy as np

from data.indicators.advanced import AdvancedIndicators

class TestQQEMod:
    """QQE Mod (MACD-Style) Vektörize Algoritması İçin İzole Birim Testleri."""

    @pytest.fixture
    def basic_close(self):
        """Basit test verisi (sinüs dalgası benzeri, 100 veri noktası)."""
        np.random.seed(42)
        base = np.linspace(100, 150, 100)
        noise = np.random.normal(0, 1, 100)
        return pd.Series(base + noise)

    @pytest.fixture
    def pure_uptrend_close(self):
        """
        Sıfıra Bölünme (Division by Zero) durumunu test etmek için saf yükseliş trendi.
        Bu durumda `down` hareketleri tamamen sıfır olacağı için `roll_down` sıfır olacak,
        bu da RS hesaplamasında sıfıra bölünme hatası potansiyeli yaratacaktır.
        """
        return pd.Series(np.linspace(100, 200, 100))

    def test_qqe_mod_basic_functionality(self, basic_close):
        """Algoritmanın standart şartlarda çökmeden DataFrame döndürdüğünü doğrular."""
        df = AdvancedIndicators.qqe_mod(basic_close, rsi_period=14, smoothing=5)

        # Sütunlar tam ve doğru isimlerde mi?
        assert list(df.columns) == ['qqe_line', 'histo', 'qqe_mod_signal']

        # Satır sayıları eşleşiyor mu?
        assert len(df) == len(basic_close)

        # Sinyal sadece 0, 1 ve 2 mi içeriyor?
        unique_signals = df['qqe_mod_signal'].unique()
        for signal in unique_signals:
            assert signal in [0, 1, 2]

        # qqe_mod_signal veritipi tamsayı (int) olmalı
        assert pd.api.types.is_integer_dtype(df['qqe_mod_signal'])

    def test_qqe_mod_division_by_zero_shield(self, pure_uptrend_close):
        """Sırekli yükselen piyasada 'Sıfıra Bölünme' kalkanının çalıştığını doğrular."""
        df = AdvancedIndicators.qqe_mod(pure_uptrend_close)

        # Hiçbir sütunda NaN veya Infinity olmamalı
        assert not df['qqe_line'].isna().any()
        assert not df['histo'].isna().any()
        assert not np.isinf(df['qqe_line']).any()
        assert not np.isinf(df['histo']).any()

    def test_qqe_mod_data_integrity_and_warmup(self):
        """İlk barların (ısınma periyodu) düzgün bir şekilde doldurulduğunu doğrular."""
        # Kısa ve ani veri dizisi
        close = pd.Series([100, 100, 100, 100, 100])
        df = AdvancedIndicators.qqe_mod(close, rsi_period=14, smoothing=5)

        # Başlangıçta RSI nötr (50.0) ve histo nötr (0.0) değerini almalıdır
        assert df['qqe_line'].iloc[0] == 50.0
        assert df['histo'].iloc[0] == 0.0
        # İlk satırlarda yeterli hareket olmadığı için sinyal nötr (1) olmalıdır
        assert df['qqe_mod_signal'].iloc[0] == 1

    def test_qqe_mod_signal_logic(self):
        """
        (qqe_line > 50) & (histo > 0) -> 2 (LONG)
        (qqe_line < 50) & (histo < 0) -> 0 (SHORT)
        Diğer durumlar -> 1 (NÖTR)
        koşullarının doğru çalıştığını sahte verilerle test eder.
        Bunun için qqe_mod içinde üretilen hesaplamayı değil,
        mantıksal blokların birebir aynısını burada simüle edip
        çıktıyı kontrol edeceğiz veya fonksiyon çıktısını zorlayacağız.
        Fonksiyona doğrudan müdahale edemeyeceğimiz için sinüs dalgası
        üzerindeki mantıksal eşleşmeleri doğrulayalım.
        """
        np.random.seed(42)
        # Volatil bir piyasa yaratalım ki farklı sinyaller üretsin
        close = pd.Series(np.sin(np.linspace(0, 10, 100)) * 10 + 100)
        df = AdvancedIndicators.qqe_mod(close)

        for i in range(len(df)):
            qqe = df['qqe_line'].iloc[i]
            hist = df['histo'].iloc[i]
            sig = df['qqe_mod_signal'].iloc[i]

            if qqe > 50 and hist > 0:
                assert sig == 2
            elif qqe < 50 and hist < 0:
                assert sig == 0
            else:
                assert sig == 1
