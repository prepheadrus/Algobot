"""
Smart Money Strategy - Akıllı Para Stratejisi

Kurumsal konfluans stratejisi:
- RSI (14) - Momentum
- MACD (12, 26, 9) - Trend
- OBV (On Balance Volume) - Akıllı Para Girişi

LONG Sinyali:
1. MACD > Signal (trend yukarı)
2. RSI > 50 VEYA RSI 30'dan yukarı kesmiş (momentum)
3. OBV artışta (akıllı para girişi)

RRR = 3.0 (Take Profit = 3x Stop Loss)
"""

from strategy.base import BaseStrategy
from data.indicators.momentum import MomentumIndicators
from data.indicators.volume import VolumeIndicators
from core.logger import logger
import pandas as pd


class SmartMoneyStrategy(BaseStrategy):
    """
    Smart Money (Akıllı Para) Stratejisi

    Kurumsal yatırımcıların hareketlerini takip eder.
    Hacim onaylı trend takibi yapar.

    WFO (Walk-Forward Optimization) Destekli:
    - Auto-Grid ile otomatik parametre ızgarası
    - Bayesian Optimization ile hızlı optimizasyon
    - Otonom parametre adaptasyonu
    """

    # Varsayılan parametreler (Auto-Grid bu değerlerden %30 esnetme yapar)
    DEFAULT_PARAMS = {
        'rsi_period': 14,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
        'obv_period': 14
    }

    def __init__(self):
        """Smart Money stratejisi başlatıcı"""
        super().__init__()
        self.name = "Smart Money"
        self.description = "RSI + MACD + OBV konfluansı ile akıllı para girişlerini tespit eder"
        self.timeframe = "1m"
        self.params = self.DEFAULT_PARAMS.copy()
        self.rsi_period = self.params.get('rsi_period', 14)
        self.macd_fast = self.params.get('macd_fast', 12)
        self.macd_slow = self.params.get('macd_slow', 26)
        self.macd_signal = self.params.get('macd_signal', 9)

    def name(self) -> str:
        """Strateji adı"""
        return "Smart Money"

    def description(self) -> str:
        """Strateji açıklaması"""
        return "RSI + MACD + OBV konfluansı ile akıllı para girişlerini tespit eder"

    def timeframe(self) -> str:
        """Zaman aralığı"""
        return "1m"

    def get_stop_params(self) -> dict:
        """
        Stop Loss ve Take Profit parametreleri.

        RRR = 3.0 (Take Profit = 3x Stop Loss mesafesi)

        Returns:
            dict: {
                'atr_multiplier': float,
                'risk_reward_ratio': float
            }
        """
        return {
            'atr_multiplier': 2.0,  # Stop Loss = ATR × 2
            'risk_reward_ratio': 3.0  # Take Profit = 3x Stop Loss
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

        # Parametreleri instance değişkenlerine de yansıt
        self.rsi_period = self.params.get('rsi_period', 14)
        self.macd_fast = self.params.get('macd_fast', 12)
        self.macd_slow = self.params.get('macd_slow', 26)
        self.macd_signal = self.params.get('macd_signal', 9)

        return self.params

    def generate_signal(self, df: pd.DataFrame) -> int:
        """
        Sinyal üretir.
        
        LONG Şartları:
        1. MACD > Signal (trend yukarı)
        2. RSI > 50 VEYA RSI 30'dan yukarı kesmiş (momentum)
        3. OBV artışta (akıllı para girişi)
        
        Args:
            df: OHLCV veri DataFrame'i
            
        Returns:
            int: 0=SHORT, 1=HOLD, 2=LONG
        """
        if df is None or len(df) < 50:
            return 1  # HOLD - Yetersiz veri

        try:
            # En son mum
            current = df.iloc[-1]
            previous = df.iloc[-2]

            # ==================== İNDİKATÖRLER ====================
            
            # RSI (14)
            rsi = MomentumIndicators.rsi(df['close'], period=self.rsi_period)
            current_rsi = rsi.iloc[-1]
            previous_rsi = rsi.iloc[-2]

            # MACD (12, 26, 9)
            macd_data = MomentumIndicators.macd(
                df['close'],
                fastperiod=self.macd_fast,
                slowperiod=self.macd_slow,
                signalperiod=self.macd_signal
            )
            current_macd = macd_data['MACD'].iloc[-1]
            current_signal = macd_data['Signal'].iloc[-1]

            # OBV (On Balance Volume)
            obv = VolumeIndicators.obv(df['close'], df['volume'])
            current_obv = obv.iloc[-1]
            previous_obv = obv.iloc[-2]

            # ==================== KONTROLLER ====================
            
            # 1. MACD > Signal (trend yukarı)
            macd_bullish = current_macd > current_signal
            
            # 2. RSI > 50 VEYA RSI 30'dan yukarı kesmiş
            rsi_strong = current_rsi > 50
            rsi_cross_up = previous_rsi <= 30 and current_rsi > 30
            rsi_bullish = rsi_strong or rsi_cross_up
            
            # 3. OBV artışta (akıllı para girişi)
            obv_increasing = current_obv > previous_obv

            # ==================== KARAR ====================
            
            # LONG: Tüm şartlar sağlanmalı
            if macd_bullish and rsi_bullish and obv_increasing:
                logger.info(
                    f"🟢 SMART MONEY LONG | "
                    f"RSI: {current_rsi:.2f} | "
                    f"MACD: {current_macd:.4f} > Signal: {current_signal:.4f} | "
                    f"OBV: {current_obv:.0f} > {previous_obv:.0f}"
                )
                return 2  # LONG

            # SHORT: MACD < Signal ve OBV düşüşte
            macd_bearish = current_macd < current_signal
            obv_decreasing = current_obv < previous_obv
            
            if macd_bearish and obv_decreasing:
                logger.info(
                    f"🔴 SMART MONEY SHORT | "
                    f"RSI: {current_rsi:.2f} | "
                    f"MACD: {current_macd:.4f} < Signal: {current_signal:.4f} | "
                    f"OBV: {current_obv:.0f} < {previous_obv:.0f}"
                )
                return 0  # SHORT

            # HOLD
            return 1

        except Exception as e:
            logger.error(f"❌ Smart Money sinyal hatası: {e}")
            return 1  # HOLD - Hata durumunda bekle
