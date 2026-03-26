from strategy.base import BaseStrategy
import pandas as pd

class ScalperNinja(BaseStrategy):
    """
    Kısa vadeli fiyat sıçramalarına odaklanan hızlı bot.
    5 ve 13 EMA kesişimlerini yakalar ve kârı hemen cebine koyar.
    ATR çarpanı daha düşüktür (1.5x) bu yüzden daha sık durur.

    WFO (Walk-Forward Optimization) Destekli:
    - Auto-Grid ile otomatik parametre ızgarası
    - Bayesian Optimization ile hızlı optimizasyon
    - Otonom parametre adaptasyonu
    """

    # Varsayılan parametreler (Auto-Grid bu değerlerden %30 esnetme yapar)
    DEFAULT_PARAMS = {
        'rsi_period': 14,
        'rsi_oversold': 30,
        'stoch_oversold': 20,
        'atr_multiplier': 1.5,
        'tp_multiplier': 1.5,
        'ema_fast': 5,
        'ema_slow': 13
    }

    def __init__(self):
        """Strateji parametrelerini başlatır."""
        self.params = self.DEFAULT_PARAMS.copy()

    def name(self) -> str:
        return "Scalper Ninja"

    def description(self) -> str:
        return "Aşırı satım (Oversold) koşullarında (RSI < 30, Stoch < 20) hızlı dip avcılığına odaklanır."
    @property
    def indicators(self) -> list:
        return ["RSI", "Stochastic"]

    def get_conditions(self) -> dict:
        return {
            "LONG": [
                "RSI aşırı satım bölgesinde olmalı (RSI < 30)",
                "Stochastic aşırı satım bölgesinde olmalı (Stoch < 20)"
            ],
            "SHORT": [
                "Scalping stratejisi genellikle SHORT işlem açmaz"
            ]
        }


    def generate_signal(self, current_row: pd.Series) -> int:
        """
        Sinyal Üretimi
        2: LONG (AL)
        0: SHORT (SAT) -> Bu stratejide kullanılmıyor
        1: HOLD (BEKLE)
        """
        # Dinamik parametreler
        rsi_period = self.params.get('rsi_period', 14)
        rsi_oversold = self.params.get('rsi_oversold', 30)
        stoch_oversold = self.params.get('stoch_oversold', 20)

        # Gerekli sütunların varlığını ve geçerli bir değere sahip olduğunu kontrol et
        required_cols = [f'RSI_{rsi_period}', 'STOCH_K_14_3_3']
        if not all(col in current_row and pd.notna(current_row[col]) for col in required_cols):
            return 1 # Veri eksikse bekle

        # --- LONG (Dipten Al) Şartı ---
        is_rsi_oversold = current_row.get(f'RSI_{rsi_period}', 50) < rsi_oversold
        is_stoch_oversold = current_row['STOCH_K_14_3_3'] < stoch_oversold

        # Her iki koşul da sağlandığında LONG sinyali üret
        if is_rsi_oversold and is_stoch_oversold:
            return 2

        # Bu strateji sadece LONG yönlü çalışır, SHORT sinyali üretmez.
        return 1

    def get_stop_params(self):
        # ATR daha dar tutulur (Scalp mantığı)
        return {
            "atr_multiplier": self.params.get('atr_multiplier', 1.5),
            "tp_multiplier": self.params.get('tp_multiplier', 1.5)
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
