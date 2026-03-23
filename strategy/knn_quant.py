import pandas as pd
from strategy.base import BaseStrategy

class KNNQuantATRShield(BaseStrategy):
    """
     Nicel (Quant) KNN Tahmin ve ATR Kalkanı

    1. Hedef Değişken (Y): T gün sonrasındaki kümülatif getiri
    2. K-En Yakın Komşu (KNN): Mevcut durumun önceki dönemlere olan benzerliği üzerinden Y tahmini.
    3. Giriş: Tahmin edilen getiri z1 veya z2 eşiklerini geçerse (uzun veya kısa).
    4. Risk Yönetimi: ATR bazlı İz Süren Stop ve Risk/Kazanç Çarpanı (1.5x ATR zarar, 3x Kar).
    """

    # WFO (Walk-Forward Optimization) için varsayılan parametreler
    DEFAULT_PARAMS = {
        'z1_threshold': 0.003,
        'z2_threshold': -0.003,
        'atr_multiplier': 1.5,
        'risk_reward_ratio': 3.0
    }

    def __init__(self):
        """Strateji parametrelerini başlat"""
        self.params = self.DEFAULT_PARAMS.copy()

    def name(self) -> str:
        return "KNN Quant ATR Shield"

    def description(self) -> str:
        return "Nicel KNN Tahmin & ATR Kalkanı: Tarihsel verilere göre 'en benzer günlerin' geleceğini kopyalar. Duyguları siler."

    def generate_signal(self, current_row: pd.Series) -> int:
        """
        Dönüş:
        2: LONG (AL)
        0: SHORT (SAT)
        1: HOLD (BEKLE)
        """
        # data/indicators.py içinde KNN_PREDICTED_RETURN hesaplandığını varsayıyoruz.
        if 'KNN_PREDICTED_RETURN' not in current_row:
            return 1 # Veri eksikse bekle

        pred_return = current_row['KNN_PREDICTED_RETURN']

        # Eşik (z1, z2) Değerlerinin Belirlenmesi
        # z1: İşleme girmek için beklenen minimum % getiri miktarı
        z1 = self.params.get('z1_threshold', 0.003)  # %0.3 beklenen T mumluk getiri
        z2 = self.params.get('z2_threshold', -0.003) # Short için beklenen düşüş

        # KNN motoru henüz eğitilmediyse (yeterli mum yoksa) 0.0 dönüyordur. Onları atla.
        if abs(pred_return) < 0.000001:
            return 1

        if pred_return > z1:
            return 2 # LONG
        elif pred_return < z2:
            return 0 # SHORT

        return 1

    def get_stop_params(self):
        """
        ATR Kalkanı
        Geleneksel risk yönetimi kuralları devreye girer:
        1.5x ATR Stop Loss
        Risk/Kazanç oranı 3x
        """
        return {
            "atr_multiplier": self.params.get('atr_multiplier', 1.5),       # Zarar Kes = Fiyatın 1.5 ATR uzağı
            "risk_reward_ratio": self.params.get('risk_reward_ratio', 3.0)     # Kar Hedefi (Risk X 3)
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
