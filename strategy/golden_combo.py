from strategy.base import BaseStrategy
import pandas as pd

class GoldenCombo(BaseStrategy):
    """
    Kitapta Önerilen İndikatör Sepeti Şablonu:
    Hacim Destekli Trend Teyidi (MACD + Hareketli Ortalamalar + OBV)
    ve ADX (Trend Gücü) birleşimi.

    Aynı aileden indikatör kullanmak yerine:
    - Yön İçin: MACD ve Hareketli Ortalama (EMA 5 / SMA 20 Kesitimi)
    - Trend Gücü İçin: ADX (20 üzeri ve yükseliyorsa)
    - Hacim Onayı İçin: OBV (Kendi üst direncini veya ortalamasını kırmışsa)
    kombinasyonunu içerir.
    """

    # WFO (Walk-Forward Optimization) için varsayılan parametreler
    DEFAULT_PARAMS = {
        'adx_threshold': 20,
        'atr_multiplier': 3.0,
        'tp_multiplier': 2.5
    }

    def __init__(self):
        """Strateji parametrelerini başlat"""
        self.params = self.DEFAULT_PARAMS.copy()

    def name(self) -> str:
        return "Golden Combo"

    def description(self) -> str:
        return "ADX, MACD, EMA ve OBV kombinasyonlu hacim destekli trend yakalama şablonu. Doğrulama olmadan işleme girmez."

    def generate_signal(self, current_row: pd.Series) -> int:
        # Gerekli verilerin olup olmadığını kontrol et
        req_cols = ['MACDh_12_26_9', 'EMA_5', 'SMA_20', 'OBV', 'OBV_EMA', 'ADX_14']
        if not all(col in current_row for col in req_cols):
            return 1 # Veri eksikse bekle

        close_p = current_row['close']

        # Dinamik parametreler
        adx_threshold = self.params.get('adx_threshold', 20)

        # 1. YÖN TEYİDİ (MACD + EMA)
        # MACD Histogramı 0'ın üzerindeyse pozitif momentum
        macd_up = current_row['MACDh_12_26_9'] > 0
        macd_down = current_row['MACDh_12_26_9'] < 0

        # Kısa EMA Orta SMA'nın üstünde mi?
        ema_up = current_row['EMA_5'] > current_row['SMA_20']
        ema_down = current_row['EMA_5'] < current_row['SMA_20']

        # 2. TREND GÜCÜ TEYİDİ (ADX)
        has_trend = current_row['ADX_14'] > adx_threshold

        # 3. HACİM ONAYI (OBV)
        # OBV kendi 10 periyotluk EMA'sını kırmışsa hacim artışı teyidi
        obv_up = current_row['OBV'] > current_row['OBV_EMA']
        obv_down = current_row['OBV'] < current_row['OBV_EMA']

        # --- LONG ---
        if has_trend and macd_up and ema_up and obv_up:
            return 2

        # --- SHORT ---
        if has_trend and macd_down and ema_down and obv_down:
            return 0

        return 1

    def get_stop_params(self):
        # ATR çarpanı ve Kâr-al çarpanı (dinamik)
        return {
            "atr_multiplier": self.params.get('atr_multiplier', 3.0),
            "tp_multiplier": self.params.get('tp_multiplier', 2.5)
        }

    def update_params(self, new_params: dict):
        """
        WFO tarafından bulunan yeni parametreleri uygular.

        Args:
            new_params: Yeni parametre sözlüğü
        """
        for key, value in new_params.items():
            if key in self.params:
                self.params[key] = value

        return self.params
