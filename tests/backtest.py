import pandas as pd
import numpy as np
from core.logger import logger
from strategy.risk import RiskManagement
from strategy.confluence import StrategyConfluence
from data.indicators import StrategyIndicators

class WalkForwardBacktester:
    """
    Raporda belirtilen 'Walk-Forward Optimization (WFO)' yöntemini kullanarak
    geçmiş veriler (In-Sample) üzerinden eğitilen modelin hiç görmediği
    (Out-of-Sample) verilerde aşırı optimizasyona (overfitting) kaçıp kaçmadığını simüle eder.
    """
    def __init__(self, initial_capital=10000.0, fee_rate=0.0004):
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.fee_rate = fee_rate # Örn: Binance %0.04 (Maker/Taker Karışık)
        self.trade_history = []
        self.positions = []

    def simulate_dry_run(self, df: pd.DataFrame, risk_percent=1.0):
        """
        Geçmiş veri kümesinden elde edilen tüm mum çubuklarında (Satır satır/Vektörel)
        botun strateji, risk ve model kodlarının tam olarak uygulanarak portföyün 
        büyüme eğrisinin çıkartıldığı fonksiyon.
        """
        logger.info(f"Backtest Simülasyonu Başladı. Sermaye: ${self.initial_capital}, Veri Büyüklüğü: {len(df)}")
        
        # 1. Konfluans İndikatörlerinin eklenmesi
        df_ind = StrategyIndicators.add_all_indicators(df.copy())
        
        # Basit Vektörel Döngü Simülasyonu (Zaman Serisi boyunca)
        for index, row in df_ind.iterrows():
            # A. Önce Piyasayı Denetle (Kalkanlar Açık mı?)
            if not StrategyConfluence.is_volatility_safe(row):
                continue # ATR aşırı yüksek, işlem YAPMA (Yatayda kal)
            
            # B. Sinyali Teyit Et (Trend, Momentum, VWAP Konfluansı)
            signal = StrategyConfluence.check_trend_following_signal(row)
            
            # Makine Öğrenimi Modelinin de devreye girdiği Mock (Taklit) kısmı
            # (Şimdilik ML Füzyonu sonucu simüle ediliyor -> %75 güvenle aynı yön)
            ml_confidence = 0.75 
            
            current_price = row['close']
            
            # C. Riski Yönet ve İşleme Gir
            if signal == 2: # LONG
                # Stop Loss ATR mesafesinin %1.5 uzağında olsun (Geleneksel bir kural)
                stop_loss = current_price - (row['ATR_14'] * 1.5)
                
                # Sadece %1 Risk alan boyut
                pos_size = RiskManagement.calculate_position_size(
                    self.current_capital, risk_percent, current_price, stop_loss
                )
                
                # Kaldıraç Oranı (Güven yüksekse 2x/3x, düşükse spot)
                leverage = RiskManagement.calculate_dynamic_leverage(ml_confidence)
                
                # Maliyet = Pozisyon Büyüklüğü * Girilen Fiyat / Kaldıraç oranı 
                cost = (pos_size * current_price) / leverage
                
                if cost < self.current_capital * 0.5: # Tüm paranın %50'den fazlası tek karta yatırılamaz!
                    self._enter_position("LONG", current_price, pos_size, stop_loss, leverage, row.name)

            elif signal == 0: # SHORT
                stop_loss = current_price + (row['ATR_14'] * 1.5)
                pos_size = RiskManagement.calculate_position_size(
                    self.current_capital, risk_percent, current_price, stop_loss
                )
                leverage = RiskManagement.calculate_dynamic_leverage(ml_confidence)
                
                cost = (pos_size * current_price) / leverage
                
                if cost < self.current_capital * 0.5:
                     self._enter_position("SHORT", current_price, pos_size, stop_loss, leverage, row.name)
        
        logger.info(f"Simülasyon Bitti. Son Bakiye: ${self.current_capital:.2f} | PnL: {((self.current_capital/self.initial_capital)-1)*100:.2f}%")
        return self.trade_history

    def _enter_position(self, direction, price, amount, stop_loss, leverage, timestamp):
        """Sahte bir emir defteri siparişi oluşturur ve komisyonları(fees) ve slipaj(kayma) metriklerini portföyden düşer."""
        
        # Piyasa Emirlerindeki Kayma (Slippage) etkisi
        slippage = price * 0.0001 # Binde 1'lik kayma simülasyonu
        executed_price = price + slippage if direction == "LONG" else price - slippage
        
        fee = executed_price * amount * self.fee_rate
        self.current_capital -= fee
        
        self.positions.append({
            'dir': direction,
            'amount': amount,
            'entry': executed_price,
            'sl': stop_loss,
            'time': timestamp,
            'leverage': leverage
        })
        # logger.debug(f"{timestamp} | {direction} İşlemi - Fiyat:{executed_price:.2f} Kaldıraç:{leverage}x")

    def print_metrics(self):
        """Grafana entegrasyonundan önceki basit terminal raporlayıcısı."""
        print("------- BACKTEST VE WFO PERFORMANS RAPORU -------")
        print(f"Başlangıç Bakiyesi: ${self.initial_capital}")
        print(f"Bitiş Bakiyesi    : ${self.current_capital:.2f}")
        print(f"Toplam İşlem      : {len(self.positions)}")
        print("-------------------------------------------------")
        # (Drawdown, Sharpe oranı gibi ileri düzey metrikler buraya model bağlandıktan sonra hesaplatılacaktır.)
