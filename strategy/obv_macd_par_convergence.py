import pandas as pd
import numpy as np
import logging
from strategy.base import BaseStrategy
from data.indicators.momentum import MomentumIndicators
from data.indicators.volume import VolumeIndicators
from data.indicators.trend import TrendIndicators

logger = logging.getLogger(__name__)

class OBV_MACD_PAR_Convergence(BaseStrategy):
    """
    OBV-MACD-PAR Yakınsama Motoru
    Hacim, momentum ve trendi eşzamanlı olarak teyit eden bir strateji.
    Thomas Aspray'in erken sinyal üreten "MACD-AS" algoritmasına ve
    "OBV-MACD-PAR indikatörlerinin kombine kullanımı" prensibine dayanır.
    """

    DEFAULT_PARAMS = {
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
        'macd_as_ema': 9,
        'obv_lookback': 14,
        'psar_af0': 0.02,
        'psar_af': 0.02,
        'psar_max_af': 0.2,
        'risk_percent': 0.01, # Pozisyon boyutlandırma için (Örn: %1 risk)
        'risk_reward_ratio': 2.0,
        'slippage': 0.0001,   # %0.01 kayma
        'commission': 0.0004  # %0.04 Taker komisyonu
    }

    def __init__(self):
        """Strateji parametrelerini başlatır."""
        self.params = self.DEFAULT_PARAMS.copy()

    def name(self) -> str:
        return "OBV-MACD-PAR Convergence Engine"
    def description(self) -> str:
        return "MACD-AS (Momentum), OBV (Hacim/Trend Uyuşmazlık) ve Parabolic SAR (Fiyat Yönü) indikatörlerini kombine kullanarak sinyal üretir."

    @property
    def indicators(self) -> list:
        return ["OBV", "MACD-AS", "Parabolic SAR (PSAR)"]

    def get_conditions(self) -> dict:
        return {
            "LONG": [
                "OBV kendi ortalamasının üzerinde olmalı",
                "MACD-AS pozitif olmalı",
                "Fiyat PSAR ın üzerinde olmalı"
            ],
            "SHORT": [
                "OBV kendi ortalamasının altında olmalı",
                "MACD-AS negatif olmalı",
                "Fiyat PSAR ın altında olmalı"
            ]
        }


    def description(self) -> str:
        return "MACD-AS (Momentum), OBV (Hacim/Trend Uyuşmazlık) ve Parabolic SAR (Fiyat Yönü) indikatörlerini kombine kullanarak sinyal üretir."

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        MACD-AS, OBV ve Parabolic SAR hesaplamalarını yapar.
        Vektörize edilmiş numpy/pandas işlemleri kullanılır.
        """
        # Veri kopyasını alarak güvenli işlem yap
        df = df.copy()

        macd_fast = self.params.get('macd_fast', 12)
        macd_slow = self.params.get('macd_slow', 26)
        macd_signal = self.params.get('macd_signal', 9)
        macd_as_ema = self.params.get('macd_as_ema', 9)
        obv_lookback = self.params.get('obv_lookback', 14)

        # 1. MACD-AS (MACD Aspray)
        # Formül: A = MACD(26,12,9) - MACD_Trigger(26,12,9); MACD_AS = EMA(A, 9)
        macd_line, signal_line, hist = MomentumIndicators.macd(
            df['close'], fast=macd_fast, slow=macd_slow, signal=macd_signal
        )

        # A = Histogram (MACD Line - Signal Line)
        # MACD-AS = EMA(A, 9)
        df['MACD_AS'] = TrendIndicators.ema(hist, length=macd_as_ema)

        # 2. OBV (On Balance Volume) ve Lokal Zirve (Peak)
        if 'volume' in df.columns:
            df['OBV'] = VolumeIndicators.obv(df['close'], df['volume'])
        else:
            # Fallback (Volume yoksa)
            df['OBV'] = pd.Series(0.0, index=df.index)

        # OBV'nin bir önceki lokal zirvesi (shift(1) ile o anki barı dahil etmiyoruz)
        df['OBV_Peak'] = df['OBV'].shift(1).rolling(window=obv_lookback).max()

        # 3. PAR (Parabolic SAR)
        psar_af0 = self.params.get('psar_af0', 0.02)
        psar_af = self.params.get('psar_af', 0.02)
        psar_max_af = self.params.get('psar_max_af', 0.2)

        psar, psar_dir = TrendIndicators.psar(
            df['high'], df['low'], df['close'],
            af0=psar_af0, af=psar_af, max_af=psar_max_af
        )
        df['PSAR'] = psar

        # Sinyal tespiti için bir önceki MACD-AS değerini kaydet
        df['MACD_AS_prev'] = df['MACD_AS'].shift(1)

        # Veri Bütünlüğü: Asenkron JSON çöküşlerini engellemek için zorunlu kalkan
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.fillna(0.0, inplace=True)

        return df

    def generate_signal(self, current_row: pd.Series) -> int:
        """
        Risk motoru sadece 0 (SAT), 1 (BEKLE) ve 2 (AL) sinyallerini tanır.
        """
        # Güvenlik kontrolü
        required_cols = ['close', 'MACD_AS', 'MACD_AS_prev', 'OBV', 'OBV_Peak', 'PSAR']
        if not all(col in current_row.index for col in required_cols):
            return 1 # Bekle

        close_p = current_row['close']
        macd_as = current_row['MACD_AS']
        macd_as_prev = current_row['MACD_AS_prev']
        obv = current_row['OBV']
        obv_peak = current_row['OBV_Peak']
        psar = current_row['PSAR']

        # --- AL (2) Sinyali ---
        # 1. MACD-AS sıfır seviyesini yukarı kırmış olmalı (Momentum Onayı)
        macd_cross_up = (macd_as > 0) and (macd_as_prev <= 0)

        # 2. OBV bir önceki lokal zirvesini yukarı yönlü kırmalı (Hacim/Trend Onayı)
        obv_breakout = obv > obv_peak

        # 3. Fiyat kapanışı, Parabolic SAR noktalarının üzerinde olmalı (Fiyat Yön Onayı)
        price_above_psar = close_p > psar

        if macd_cross_up and obv_breakout and price_above_psar:
            return 2

        # --- SAT (0) Sinyali ---
        # MACD-AS sıfır seviyesini aşağı kırarsa VEYA Fiyat Parabolic SAR noktalarının altına düşerse
        macd_cross_down = (macd_as < 0) and (macd_as_prev >= 0)
        price_below_psar = close_p < psar

        if macd_cross_down or price_below_psar:
            return 0

        # --- BEKLE (1) ---
        return 1

    def get_stop_params(self):
        """
        Risk Yönetimi parametrelerini döner.
        Dinamik Pozisyon Boyutlandırma, Stop-Loss ve Kâr Al stratejileri için.
        """
        return {
            "use_psar_stop": True, # Risk motoruna dinamik PSAR stop kullanmasını söyler
            "risk_percent": self.params.get('risk_percent', 0.01),
            "risk_reward_ratio": self.params.get('risk_reward_ratio', 2.0),
            "slippage": self.params.get('slippage', 0.0001),
            "commission": self.params.get('commission', 0.0004),
            # Geriye dönük uyumluluk için varsayılan ATR çarpanı ekliyoruz
            # Ama stratejinin özü PSAR tabanlı stop-loss'tur.
            "atr_multiplier": 2.0
        }

    def update_params(self, params: dict):
        """
        WFO (Walk-Forward Optimization) için parametreleri günceller.
        """
        if hasattr(self, 'params'):
            for key, value in params.items():
                if key in self.params:
                    self.params[key] = value
            logger.info(f"📝 [WFO] {self.name()} parametreleri güncellendi: {params}")
        else:
            logger.warning(f"⚠️ [WFO] {self.name()} params attribute'u yok")
