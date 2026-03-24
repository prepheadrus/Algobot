from strategy.base import BaseStrategy
import pandas as pd

class TrendMasterPro(BaseStrategy):
    """
    Şu anki varsayılan stratejimiz. 1 Dakikalık grafiklerde
    200 EMA ana trendine sadık kalarak RSI 50 ve SMA 20
    ile giriş arar. Geniş stop (3.5x ATR) kullanır.

    WFO (Walk-Forward Optimization) Destekli:
    - Auto-Grid ile otomatik parametre ızgarası
    - Bayesian Optimization ile hızlı optimizasyon
    - Otonom parametre adaptasyonu
    """

    # Varsayılan parametreler (Auto-Grid bu değerlerden %30 esnetme yapar)
    DEFAULT_PARAMS = {
        'rsi_period': 14,
        'rsi_upper': 70,
        'rsi_lower': 30,
        'atr_multiplier': 3.5,
        'tp_multiplier': 2.0,
        'ema_fast': 20,
        'ema_slow': 200
    }

    def __init__(self):
        """Strateji parametrelerini başlatır."""
        self.params = self.DEFAULT_PARAMS.copy()

    def name(self) -> str:
        return "TrendMaster Pro"

    def description(self) -> str:
        return "SMA 20, EMA 200 ve RSI 50 ile 1 dakikalık trend takibi yapar. Güvenli ve stabil bir bot setidir."

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        SMA_20, EMA_slow, ve RSI hesaplamalarını yapar.
        """
        rsi_period = self.params.get('rsi_period', 14)
        ema_slow = self.params.get('ema_slow', 200)

        import pandas_ta as ta

        # SMA 20
        if 'SMA_20' not in df.columns:
            df.ta.sma(length=20, append=True)

        # EMA Slow
        ema_col = f'EMA_{ema_slow}'
        if ema_col not in df.columns:
            df.ta.ema(length=ema_slow, append=True)

        # RSI
        rsi_col = f'RSI_{rsi_period}'
        if rsi_col not in df.columns:
            df.ta.rsi(length=rsi_period, append=True)

        # Fallback in case ta fails (e.g. data too short)
        if 'SMA_20' not in df.columns:
            df['SMA_20'] = df['close'].rolling(window=20).mean()
        if ema_col not in df.columns:
            df[ema_col] = df['close'].ewm(span=ema_slow, adjust=False).mean()
        if rsi_col not in df.columns:
            # basit rsi hesaplama (ta fail olursa)
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
            rs = gain / loss
            df[rsi_col] = 100 - (100 / (1 + rs))

        return df

    def generate_signal(self, current_row: pd.Series) -> int:
        close_p = current_row['close']

        # Dinamik parametreler
        rsi_period = self.params.get('rsi_period', 14)
        rsi_upper = self.params.get('rsi_upper', 70)
        rsi_lower = self.params.get('rsi_lower', 30)
        ema_slow = self.params.get('ema_slow', 200)

        # --- LONG ---
        # Fiyat EMA slow ve SMA 20 üzerinde, RSI rsi_upper-
        trend_up = (close_p > current_row.get(f'EMA_{ema_slow}', 0)) and (close_p > current_row['SMA_20'])
        mom_up = rsi_lower < current_row.get(f'RSI_{rsi_period}', 50) < rsi_upper

        if trend_up and mom_up:
            return 2

        # --- SHORT ---
        # Fiyat EMA slow ve SMA 20 altında, RSI 50'nin altında (ayı momentumu)
        trend_down = (close_p < current_row.get(f'EMA_{ema_slow}', 999999)) and (close_p < current_row['SMA_20'])
        mom_down = current_row.get(f'RSI_{rsi_period}', 50) < 50  # RSI 50 altında ayı bölgesi

        if trend_down and mom_down:
            return 0

        return 1

    def get_stop_params(self):
        # ATR çarpanı ve Kâr-al çarpanı (dinamik)
        return {
            "atr_multiplier": self.params.get('atr_multiplier', 3.5),
            "risk_reward_ratio": self.params.get('risk_reward_ratio', 2.0),  # YENİ: TP hesaplaması için
            "tp_multiplier": self.params.get('tp_multiplier', 2.0)
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
