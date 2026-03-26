from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any

class BaseStrategy(ABC):
    """
    Tüm bot stratejileri için ortak şablon.
    Yeni bir bot eklemek için bu sınıftan türetmek yeterli.
    """

    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def description(self) -> str:
        pass

    @property
    def indicators(self) -> list:
        """Kullanılan indikatörlerin listesini döner."""
        return []

    def get_conditions(self) -> Dict[str, list]:
        """LONG ve SHORT koşullarını döner."""
        return {"LONG": [], "SHORT": []}

    @abstractmethod
    def generate_signal(self, current_row: pd.Series) -> int:
        """
        2: LONG, 0: SHORT, 1: HOLD
        """
        pass

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Stratejinin ihtiyaç duyduğu indikatörleri hesaplar.
        """
        return df

    @abstractmethod
    def get_stop_params(self):
        """
        ATR çarpanı ve Risk/Ödül oranı gibi parametreleri döner.
        """
        pass

    def update_params(self, params: Dict[str, Any]):
        """
        WFO (Walk-Forward Optimization) için parametreleri güncelle.

        Args:
            params: Yeni parametreler (örn: {'ema_period': 25, 'rsi_period': 16})

        Kontrat: Tüm stratejiler bu metodu implement etmek ZORUNDADIR.
        """
        if hasattr(self, 'params'):
            self.params.update(params)
            logger.info(f"📝 [WFO] {self.name()} parametreleri güncellendi: {params}")
        else:
            logger.warning(f"⚠️ [WFO] {self.name()} params attribute'u yok")
