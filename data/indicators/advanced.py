"""
Advanced Indicators

Gelişmiş ve özel teknik indikatörler:
- Koncorde (Azul, Verde, Marron)
- Kalman Filter
- EWO (Elliott Wave Oscillator)
- SMC/Likidite (gelecek için yer tutucu)
"""

import pandas as pd
import numpy as np


class AdvancedIndicators:
    """Gelişmiş indikatörler"""
    
    @staticmethod
    def ewo(close: pd.Series, fast: int = 5, slow: int = 35) -> pd.Series:
        """
        Elliott Wave Oscillator
        
        Args:
            close: Kapanış fiyatları
            fast: Fast SMA periyodu
            slow: Slow SMA periyodu
        
        Returns:
            EWO serisi
        """
        from data.indicators.trend import TrendIndicators
        
        sma5 = TrendIndicators.sma(close, fast)
        sma35 = TrendIndicators.sma(close, slow)
        
        return ((sma5 - sma35) / close * 100)
    
    @staticmethod
    def koncorde_azul(nvi: pd.Series, nvim: pd.Series, period: int = 90) -> pd.Series:
        """
        Koncorde Azul (Smart Money - Akıllı Para)
        
        Args:
            nvi: NVI serisi
            nvim: NVI moving average
            period: Lookback period
        
        Returns:
            Azul serisi
        """
        nvim_max = nvim.rolling(period, min_periods=1).max()
        nvim_min = nvim.rolling(period, min_periods=1).min()
        
        return (nvi - nvim) * 100 / (nvim_max - nvim_min).replace(0, 1)
    
    @staticmethod
    def koncorde_verde(pvi: pd.Series, pvim: pd.Series, period: int = 90) -> pd.Series:
        """
        Koncorde Verde (Retail - Küçük Yatırımcı)
        
        Args:
            pvi: PVI serisi
            pvim: PVI moving average
            period: Lookback period
        
        Returns:
            Verde serisi
        """
        pvim_max = pvim.rolling(period, min_periods=1).max()
        pvim_min = pvim.rolling(period, min_periods=1).min()
        
        oscp = (pvi - pvim) * 100 / (pvim_max - pvim_min).replace(0, 1)
        return oscp
    
    @staticmethod
    def koncorde_marron(
        rsi: pd.Series, 
        mfi: pd.Series, 
        stoch: pd.Series, 
        bb_osc: pd.Series
    ) -> pd.Series:
        """
        Koncorde Marron (Trend Ortalama - Kahverengi Alan)
        Orijinal PineScript mantığına daha yakın: RSI, MFI, Stoch ve BB Osilatörü ortalaması.
        
        Formula: (RSI + MFI + BB_Osc + (Stoch/3)) / 2
        """
        # Stoch (21,7,3) için /3 ölçeklendirmesi orijinal formülün bir parçası olabilir
        # BB_Osc genelde 0-100 arasına çekilir
        marron = (rsi + mfi + bb_osc + (stoch / 3)) / 2
        return marron.fillna(50)
    
    @staticmethod
    def calculate_koncorde(
        close: pd.Series,
        high: pd.Series,
        low: pd.Series,
        volume: pd.Series,
        period: int = 15
    ) -> dict:
        """
        Koncorde tüm bileşenlerini hesapla (Genişletilmiş PineScript Uyumu)
        """
        from data.indicators.volume import VolumeIndicators
        from data.indicators.momentum import MomentumIndicators
        from data.indicators.volatility import VolatilityIndicators
        
        # 1. PVI/NVI ve Hareketli Ortalamalar (Sütun İzolasyonu Hotfix)
        pvi = VolumeIndicators.pvi(close, volume)['pvi']
        nvi = VolumeIndicators.nvi(close, volume)['nvi']
        pvim = pvi.ewm(span=period, adjust=False).mean()
        nvim = nvi.ewm(span=period, adjust=False).mean()
        
        # 2. Temel Osilatörler
        rsi = MomentumIndicators.rsi(close, 14)
        mfi = VolumeIndicators.mfi(high, low, close, volume, 14)
        
        # 3. Marron için Ek Bileşenler
        # Stochastic (21, 7, 3) - Smooth k periyodu
        stoch_k, stoch_d = MomentumIndicators.stochastic(high, low, close, k=21, d=7, smooth_k=3)
        
        # Bollinger Bands Oscillator (25, 2.0)
        # BB_Osc = (Close - Lower) / (Upper - Lower) * 100
        upper, mid, lower = VolatilityIndicators.bollinger_bands(close, length=25, std=2.0)
        bb_range = (upper - lower).replace(0, 0.000001)
        bb_osc = (close - lower) * 100 / bb_range
        
        # 4. Azul (Akıllı Para) & Verde (Retail) - OSCP (Hacim Osilatörü)
        # Azul: NVI farkı
        azul = AdvancedIndicators.koncorde_azul(nvi, nvim)
        
        # Hacim Osilatörü (OSCP)
        # Orijinal Verde mantığında (PVI - PVIM) etkisi
        oscp = (pvi - pvim) * 100 / (pvi.rolling(90).max() - pvi.rolling(90).min()).replace(0, 1)
        
        # Marron (Trend Alanı)
        marron = AdvancedIndicators.koncorde_marron(rsi, mfi, stoch_k, bb_osc)
        
        # Verde = Marron + OSCP
        verde = marron + oscp
        
        # Temizlik
        azul = azul.replace([np.inf, -np.inf], 0).fillna(0)
        verde = verde.replace([np.inf, -np.inf], 0).fillna(0)
        marron = marron.replace([np.inf, -np.inf], 50).fillna(50)
        
        return {
            'azul': azul,
            'verde': verde,
            'marron': marron,
            'pvi': pvi,
            'nvi': nvi,
            'pvim': pvim,
            'nvim': nvim,
            'rsi': rsi,
            'mfi': mfi,
            'stoch': stoch_k,
            'bb_osc': bb_osc
        }
    
    @staticmethod
    def liquidity_zones(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        lookback: int = 10
    ) -> dict:
        """
        SMC (Smart Money Concepts) - Likidite Bölgeleri ve Sweep Tespiti.
        Az önce market_structure ile bulduğumuz çizgileri kullanarak "Stop-Loss Avı" 
        (Liquidity Sweep) anlarını tespit eder.
        
        Args:
            high, low, close: Fiyat serileri
            lookback: Swing seviyeleri için bakılacak pencere boyutu
            
        Returns:
            {swing_high, swing_low, sweep_bullish, sweep_bearish} dict
        """
        # 1. Market structure seviyelerini (çizgilerini) al
        ms = AdvancedIndicators.market_structure(high, low, close, swing_length=lookback)
        sh = ms['swing_high']
        sl = ms['swing_low']
        
        # 2. SWEEP_BULLISH (Sell-Side Sweep): Low < SL ve Close > SL
        sweep_bullish = np.where((low < sl) & (close > sl), 1, 0)
        
        # 3. SWEEP_BEARISH (Buy-Side Sweep): High > SH ve Close < SH
        sweep_bearish = np.where((high > sh) & (close < sh), 1, 0)
        
        return {
            'swing_high': sh,
            'swing_low': sl,
            'sweep_bullish': pd.Series(sweep_bullish, index=close.index).fillna(0),
            'sweep_bearish': pd.Series(sweep_bearish, index=close.index).fillna(0),
            'is_smc_ready': True
        }
    
    @staticmethod
    def fair_value_gaps(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        threshold: float = 0.001
    ) -> pd.Series:
        """
        Fair Value Gaps (FVG) tespiti
        
        NOT: Basit implementasyon, gelecekte geliştirilecek.
        
        Args:
            high: Yüksek fiyatlar
            low: Düşük fiyatlar
            close: Kapanış fiyatları
            threshold: FVG threshold
        
        Returns:
            FVG serisi
        """
        # 3-mum pattern
        fvg = pd.Series(0.0, index=close.index)
        
        for i in range(2, len(close)):
            # Bullish FVG
            if low.iloc[i] > high.iloc[i-2]:
                gap = low.iloc[i] - high.iloc[i-2]
                if gap / close.iloc[i] > threshold:
                    fvg.iloc[i] = gap
            
            # Bearish FVG
            elif high.iloc[i] < low.iloc[i-2]:
                gap = low.iloc[i-2] - high.iloc[i]
                if gap / close.iloc[i] > threshold:
                    fvg.iloc[i] = -gap
        
        return fvg
    
    @staticmethod
    def liquidity_sweep(df: pd.DataFrame) -> pd.Series:
        """
        Liquidity Sweep (Stop Hunting) - SMC Faktörü

        Args:
            df: OHLCV DataFrame

        Returns:
            Liquidity sweep serisi (+1: Bullish Sweep, -1: Bearish Sweep, 0: Nötr)
        """
        rolling_min = df['low'].rolling(20).min().shift(1)
        rolling_max = df['high'].rolling(20).max().shift(1)
        hl2 = (df['high'] + df['low']) / 2

        bullish_sweep = (df['low'] < rolling_min) & (df['close'] > hl2)
        bearish_sweep = (df['high'] > rolling_max) & (df['close'] < hl2)

        return pd.Series(np.select([bullish_sweep, bearish_sweep], [1, -1], default=0), index=df.index)

    @staticmethod
    def synthetic_imbalance(df: pd.DataFrame) -> pd.Series:
        """
        Synthetic Order Imbalance - Mikro-yapı Faktörü

        Args:
            df: OHLCV DataFrame

        Returns:
            Sentetik emir dengesizliği serisi (Synthetic CVD)
        """
        buy_pressure = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-9) * df['volume']
        sell_pressure = (df['high'] - df['close']) / (df['high'] - df['low'] + 1e-9) * df['volume']
        return (buy_pressure - sell_pressure) / (df['volume'] + 1e-9)

    @staticmethod
    def market_structure(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        swing_length: int = 10
    ) -> dict:
        """
        Market Structure (Swing Levels) tespiti.
        No Lookahead Bias: Makine öğrenimi modelini bozmamak için gelecekten veri sızdırmaz.
        
        Args:
            high, low: Fiyat serileri
            swing_length: Periyot (varsayılan 10)
            
        Returns:
            {swing_high, swing_low} dict
        """
        # 1. SWING_HIGH: Son N mumun zirvesini bul ve bir sonraki muma kaydır (Looking forward bias engeli)
        # rolling(...).max() o anki mumu da kapsar, bu yüzden .shift(1) ile "kapanmış" pencereye bakıyoruz.
        swing_high = high.rolling(window=swing_length).max().shift(1)
        
        # 2. SWING_LOW: Son N mumun dibini bul ve kaydır
        swing_low = low.rolling(window=swing_length).min().shift(1)
        
        # 3. Seviyeleri ileriye taşı (ffill) - Yeni bir uç değer gelene kadar çizgi uzasın
        swing_high = swing_high.ffill()
        swing_low = swing_low.ffill()
        
        return {
            'swing_high': swing_high,
            'swing_low': swing_low
        }
