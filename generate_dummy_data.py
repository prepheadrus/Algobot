import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_crypto_data(symbol="BTC/USDT", num_candles=43000):
    np.random.seed(42)

    # Başlangıç tarihi (bugünden num_candles dakika önce)
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=num_candles)

    # Zaman damgalarını oluştur
    timestamps = [int((start_time + timedelta(minutes=i)).timestamp() * 1000) for i in range(num_candles)]

    # Rastgele bir fiyat yolu oluştur (Random Walk with Drift)
    start_price = 60000.0
    returns = np.random.normal(loc=0.00001, scale=0.002, size=num_candles)
    price_path = start_price * np.exp(np.cumsum(returns))

    # OHLCV verisini oluştur
    high_mult = np.random.uniform(1.0, 1.003, size=num_candles)
    low_mult = np.random.uniform(0.997, 1.0, size=num_candles)
    open_mult = np.random.uniform(0.998, 1.002, size=num_candles)

    # Kapanış fiyatı path'i takip etsin
    close = price_path
    opens = close * open_mult

    # High ve Low değerleri makul olmalı
    high = np.maximum(opens, close) * high_mult
    low = np.minimum(opens, close) * low_mult

    # Gerçekçi hacim verisi (log-normal dağılım)
    volume = np.random.lognormal(mean=2.0, sigma=1.0, size=num_candles) * 10

    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': opens,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume
    })

    # Sonuçların kaydedileceği csv
    df.to_csv("test_klines.csv", index=False)
    print(f"Generated {num_candles} rows of data to test_klines.csv")

if __name__ == "__main__":
    generate_crypto_data()
