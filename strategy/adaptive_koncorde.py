from strategy.base import BaseStrategy
import pandas as pd
import numpy as np

class AdaptiveKoncordeX(BaseStrategy):
    """
    Piyasa koşullarına uyum sağlayan, Kalman Filtresi ve Koncorde (Akıllı Para)
    mekanizmalarını birleştiren ileri düzey hibrit strateji.
    VIX endeksine göre riskini otomatik ayarlar.
    """

    # WFO (Walk-Forward Optimization) için varsayılan parametreler
    DEFAULT_PARAMS = {
        'base_threshold': 3.5,
        'vix_high': 80,
        'vix_low': 30,
        'atr_multiplier': 2.5,
        'tp_multiplier': 3.0
    }

    def __init__(self):
        """Strateji parametrelerini başlat"""
        self.params = self.DEFAULT_PARAMS.copy()

    def name(self) -> str:
        return "Adaptive Koncorde X"

    def description(self) -> str:
        return "Kalman Filtresi, Akıllı Para (Koncorde) ve BTC Volatilite Endeksi (VIX) kullanan adaptif hibrit bot."

    def generate_signal(self, current_row: pd.Series) -> int:
        # Gerekli verilerin varlığını kontrol et
        required = ['close', 'KALMAN', 'KONKORDE_AZUL', 'KONKORDE_VERDE', 'BTC_VIX', 'EWO', 'SMA_20', 'ROC_10']
        if not all(col in current_row.index for col in required):
            return 1 # HOLD

        close = current_row['close']
        vix = current_row['BTC_VIX']

        # 1. Adaptif Eşik Değerleri (VIX'e göre) - DOKUNULMADI
        base_threshold = self.params.get('base_threshold', 3.5)
        vix_high = self.params.get('vix_high', 80)
        vix_low = self.params.get('vix_low', 30)

        if vix > vix_high:
            threshold = base_threshold * 1.2 # %20 daha zor karar verir
        elif vix < vix_low:
            threshold = base_threshold * 0.8 # Sakin piyasada daha kolay girer
        else:
            threshold = base_threshold

        # 2. Yeni Ağırlıklı Skorlama (Weighted Scoring)
        long_score = 0.0
        short_score = 0.0

        # --- Kalman Trend (+1.0) ---
        is_uptrend = close > current_row['KALMAN']
        if is_uptrend:
            long_score += 1.0
        else:
            short_score += 1.0

        # --- SMA 20 Konumu (+0.5) ---
        if close > current_row['SMA_20']:
            long_score += 0.5
        else:
            short_score += 0.5

        # --- Momentum Gücü (ROC 10) (+0.7) ---
        roc = current_row['ROC_10']
        if abs(roc) > 2:
            if is_uptrend:
                long_score += 0.7
            else:
                short_score += 0.7

        # --- EWO (Elliott Wave Oscillator) (+1.0) ---
        ewo_threshold = 0.1
        if current_row['EWO'] > ewo_threshold:
            long_score += 1.0
        elif current_row['EWO'] < -ewo_threshold:
            short_score += 1.0

        # --- Koncorde Patterns (+1.2) ---
        # Ayna Modeli (Mirror Buy)
        mirror_buy = current_row['KONKORDE_AZUL'] > 0 and current_row['KONKORDE_VERDE'] < 0
        if mirror_buy:
            long_score += 1.2

        # Ayı Kapanı (Bear Hug)
        bear_hug = current_row['KONKORDE_AZUL'] < 0 and current_row['KONKORDE_VERDE'] > 0
        if bear_hug:
            short_score += 1.2

        # --- Smart Money Liquidity Sweeps (+1.5 & +0.5 Bonus) ---
        sweep_bullish = current_row.get('SWEEP_BULLISH', 0) == 1
        sweep_bearish = current_row.get('SWEEP_BEARISH', 0) == 1

        if sweep_bullish:
            long_score += 1.5
            if mirror_buy: # Kusursuz SMC Girişi Bonusu
                long_score += 0.5
        
        if sweep_bearish:
            short_score += 1.5
            if bear_hug: # Kusursuz SMC Girişi Bonusu
                short_score += 0.5

        # --- RSI & MACD Teyit (0.5 - 0.8) ---
        rsi = current_row.get('RSI_14', 50)
        if 50 < rsi < 70: 
            long_score += 0.5
        elif 30 < rsi < 50: 
            short_score += 0.5

        macd = current_row.get('MACD_12_26_9', 0)
        signal = current_row.get('MACDs_12_26_9', 0)
        if macd > signal: 
            long_score += 0.8
        else: 
            short_score += 0.8

        # 3. Final Karar
        if long_score >= threshold:
            return 2 # LONG
        elif short_score >= threshold:
            return 0 # SHORT

        return 1 # HOLD

    def get_stop_params(self):
        """
        Risk yönetimi parametreleri.
        Bu strateji daha hassas olduğu için stopları daha dinamik tutar.
        """
        return {
            "atr_multiplier": self.params.get('atr_multiplier', 2.5),
            "tp_multiplier": self.params.get('tp_multiplier', 3.0)
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
