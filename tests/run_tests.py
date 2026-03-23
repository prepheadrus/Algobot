import pandas as pd
from tests.backtest import WalkForwardBacktester
from core.logger import logger

def generate_dummy_data(rows=1000):
    """Backtest'in mekanik olarak test edilebilmesi için sahte OHLCV Kripto Fiyat Mum Çubukları yaratır."""
    dates = pd.date_range("2025-01-01", periods=rows, freq="1h") # 1 Saatlik Mumlar
    data = []
    
    # Rastgele bir fiyat yolculuğu
    current_price = 60000.0 # Örn: BTC Fiyatı
    
    import random
    import numpy as np
    
    for _ in range(rows):
        volatility = current_price * 0.005 # %0.5 Volatilite
        open_p = current_price
        high_p = current_price + random.uniform(0, volatility)
        low_p = current_price - random.uniform(0, volatility)
        close_p = random.uniform(low_p, high_p)
        volume = random.uniform(10, 500)
        
        data.append([open_p, high_p, low_p, close_p, volume])
        current_price = close_p
        
    df = pd.DataFrame(data, index=dates, columns=['open', 'high', 'low', 'close', 'volume'])
    return df

def run():
    logger.info("TEST: Rastgele piyasa verisi üretiliyor...")
    fake_market_data = generate_dummy_data(rows=2000)
    
    tester = WalkForwardBacktester(initial_capital=10000.0)
    
    logger.info("TEST: Simülasyon motoruna gönderiliyor...")
    # %1.5 Risk oranında sistemin veriler üzerinde tam kar/zarar testi
    tester.simulate_dry_run(fake_market_data, risk_percent=1.5)
    tester.print_metrics()

if __name__ == '__main__':
    run()
