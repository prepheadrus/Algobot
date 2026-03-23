import pandas as pd
from strategy.base import BaseStrategy

class DivergenceHunter(BaseStrategy):
    """
    "Senkronize Uyuşmazlık Avcısı" Stratejisi

    Kullanılan Göstergeler:
    1. Demand Index (Talep Endeksi)
    2. Ultimate Oscillator
    3. ADX (Directional Movement)
    4. Parabolic SAR (PSAR)

    Mantık:
    Yatay piyasa yanılgılarından kurtulmak ve dip/tepe dönüşlerini yakalamak için pozitif/negatif uyuşmazlıklara odaklanır.
    """

    # WFO (Walk-Forward Optimization) için varsayılan parametreler
    DEFAULT_PARAMS = {
        'rsi_overbought': 70,
        'atr_multiplier': 2.0,
        'risk_reward_ratio': 3.0
    }

    def __init__(self):
        """Strateji parametrelerini başlat"""
        self.params = self.DEFAULT_PARAMS.copy()

    def name(self) -> str:
        return "Divergence Hunter"

    def description(self) -> str:
        return "Senkronize Uyuşmazlık Avcısı: Talep Endeksi ve Ultimate Osilatör uyuşmazlığını ADX gücüyle birleştirir ve PSAR ile tetiği çeker."

    def generate_signal(self, current_row: pd.Series) -> int:
        """
        Dönüş:
        2: LONG (AL)
        0: SHORT (SAT)
        1: HOLD (BEKLE)
        """
        # Gerekli indikatörlerin olup olmadığını kontrol et
        required_cols = ['DEMAND_INDEX', 'UO', 'ADX_14', 'DMP_14', 'DMN_14', 'PSAR', 'close',
                         'DIV_PRICE_LOWER', 'DIV_DEMAND_HIGHER', 'DIV_UO_HIGHER', 'ADX_BULL_CROSS',
                         'RSI_14', 'MACDh_12_26_9', 'BBU_20_2.0_2.0']

        for col in required_cols:
            if col not in current_row:
                return 1 # Veri eksiği varsa bekle

        # Dinamik parametreler
        rsi_overbought = self.params.get('rsi_overbought', 70)

        # --- LONG (AL) ŞARTLARI ---
        # 1. Uyuşmazlık Şartı: Fiyat dip yapıyor, ancak Demand ve UO yükseliyor. Demand 0 altında.
        is_pos_divergence = (
            current_row.get('DIV_PRICE_LOWER', False) and
            current_row.get('DIV_DEMAND_HIGHER', False) and
            current_row.get('DIV_UO_HIGHER', False) and
            current_row['DEMAND_INDEX'] < 0
        )

        # 2. ADX Teyidi: +DI, -DI nin üzerinde ve trend destekliyor
        # Yazarın kuralı: Şartlar bir araya gelmeli. Bazen uyuşmazlık olduktan biraz sonra kesişim gelir.
        # Biz burada uyuşmazlık varken ya da yeni gerçekleşmişken yükseliş teyidi arıyoruz.
        is_bull_trend = current_row['DMP_14'] > current_row['DMN_14']

        # 3. Tetik (PSAR): Fiyat Parabolic SAR'ın üstüne çıkmış (SAR noktaları altta)
        is_psar_bull = current_row['close'] > current_row['PSAR']

        # LONG SİNYALİ VER (Hepsi senkronize ise)
        # Not: Gerçek hayatta bu sinyallerin aynı anda yanması nadir olabilir, esnetilebilir.
        # Ancak kitaptaki katı kurallara göre "Aynı anda gerçekleşmesi" hedeflenir.
        if is_pos_divergence and is_bull_trend and is_psar_bull:
            return 2

        # --- SHORT (SAT) ŞARTLARI ---
        # Negatif Uyuşmazlık: Fiyat tepe yapıyor, ancak Demand ve UO düşüyor (dağılım)
        is_neg_divergence = (
            not current_row.get('DIV_PRICE_LOWER', False) and   # Fiyat dip yapmıyorsa (yani tepe veya yatay)
            current_row['DEMAND_INDEX'] > 0 and                  # Demand hala pozitif (ama zayıflıyor)
            current_row.get('DIV_UO_HIGHER', False) == False and # UO yükselmiyor (düşüyor)
            current_row.get('RSI_14', 50) > 55                   # RSI zirveye yakın
        )

        # Trend: -DI, +DI'nin üzerinde (ayı baskısı)
        is_bear_trend = current_row['DMN_14'] > current_row['DMP_14']

        # Tetik (PSAR): Fiyat Parabolic SAR'ın altına inmiş
        is_psar_bear = current_row['close'] < current_row['PSAR']

        if is_neg_divergence and is_bear_trend and is_psar_bear:
            return 0

        return 1

    def get_stop_params(self):
        """
        Risk Yönetimi (Zarar Kes ve Kar Al)
        Yazar Kuralı: 1.5x - 2x ATR Stop, 3x Hedef (1:3 Risk Reward oranı veya daha fazlası)
        İz süren stop bu oranlardan faydalanır.
        """
        return {
            "atr_multiplier": self.params.get('atr_multiplier', 2.0),       # Zarar Kes = Fiyatın 2 ATR uzağı
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
