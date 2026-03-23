import ccxt.async_support as ccxt
import asyncio

async def test():
    ex = ccxt.binance({
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    
    try:
        await ex.load_markets()
        print("Market var mi?", 'LINK/USDT' in ex.markets)
        res = await ex.fetch_ohlcv('LINK/USDT', '1m', limit=2)
        print("Sonuc:", res)
    except Exception as e:
        print("Hata:", e)
    finally:
        await ex.close()

asyncio.run(test())
