import pandas as pd
import numpy as np

class PriceActionIndicators:
    """Price Action (Fiyat Hareketi) tabanlı indikatörler."""

    @staticmethod
    def wick_imbalance(
        open_p: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series
    ) -> pd.Series:
        """
        Mum İçi Dengesizlik (Wick Imbalance).
        Gövdenin muma oranına veya fitillerin dengesizliğine bakar.
        """
        body_size = abs(close - open_p)
        total_size = high - low

        # Division by zero koruması
        total_size = total_size.replace(0, np.nan)

        # Üst fitil ve alt fitil
        upper_wick = high - np.maximum(open_p, close)
        lower_wick = np.minimum(open_p, close) - low

        # Fitil dengesizliği: (Üst Fitil - Alt Fitil) / Toplam Boy
        imbalance = (upper_wick - lower_wick) / total_size

        return imbalance.replace([np.inf, -np.inf], np.nan).fillna(0)
