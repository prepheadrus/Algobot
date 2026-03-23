import pandas as pd

class StrategyConfluence:
    """
    Çeşitli teknik analiz modüllerini birleştirerek "Konfluans" (Teyit) mekanizması kurar.
    Modellerden bağımsız, matematiksel bir güvenlik ağı işlevi görür.
    """
    
    @staticmethod
    def check_trend_following_signal(current_row: pd.Series) -> int:
        """
        Momentum ve Trend Takip Modülü.
        Dönüş:
            2: İdeal LONG Sinyali
            0: İdeal SHORT Sinyali
            1: Kararsız (Hold)
        """
        signal = 1
        
        # Sütunların varlık kontrolü
        required_cols = ['close', 'SMA_20', 'EMA_50', 'EMA_200', 'RSI_14', 'VWAP']
        if not all(col in current_row.index for col in required_cols):
            return signal
            
        close_p = current_row['close']
        
        # --- LONG Kriterleri ---
        # 1. Ana Trend: Fiyat uzun vadeli ortalamanın (EMA 200) üzerinde olmalı
        # 2. Ara Trend: Fiyat kısa vadeli ortalamanın (SMA 20) üzerinde
        trend_up = (close_p > current_row.get('EMA_200', 0)) and (close_p > current_row['SMA_20'])
        
        # 3. Momentum: RSI orta çizgiyi (50) yukarı kırmış olmalı
        mom_up = 50 < current_row['RSI_14'] < 70
        
        if trend_up and mom_up:
            signal = 2
            
        # --- SHORT Kriterleri ---
        # 1. Ana Trend: Fiyat uzun vadeli ortalamanın (EMA 200) altında olmalı
        # 2. Ara Trend: Fiyat kısa vadeli ortalamanın (SMA 20) altında
        trend_down = (close_p < current_row.get('EMA_200', 999999)) and (close_p < current_row['SMA_20'])
        
        # 3. Momentum: RSI orta çizgiyi (50) aşağı kırmış olmalı
        mom_down = 30 < current_row['RSI_14'] < 50
        
        if trend_down and mom_down:
            signal = 0
            
        return signal

    @staticmethod
    def is_volatility_safe(current_row: pd.Series, max_atr_factor=0.05) -> bool:
        """
        Ani volatilite patlamalarında (Sert trendlerde veya makro haberlerde) grid/arbitraj
        sistemini durdurmak ve yüksek win-rate'i korumak için ATR denetleyicisi.
        """
        if 'ATR_14' not in current_row.index:
            return True
            
        # Oynaklık fiyata oranla çok yükselmişse (Örn: %5'den büyük ATR var) güvenli değil dön
        volatility_ratio = current_row['ATR_14'] / current_row['close']
        
        if volatility_ratio > max_atr_factor:
            return False
            
        return True
