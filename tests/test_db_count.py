import asyncio
from data.database import db_manager

async def test():
    await db_manager.connect()

    print("=== DB Symbol Test ===")

    # Test 1: Tam format (DB'deki gibi)
    cnt = await db_manager.get_klines_count('BTC/USDT:USDT', '1m')
    print(f'1. BTC/USDT:USDT 1m: {cnt} mum')

    # Test 2: Kısa format
    cnt2 = await db_manager.get_klines_count('BTCUSDT', '1m')
    print(f'2. BTCUSDT 1m: {cnt2} mum')

    # Test 3: Çift slash (frontend hatası)
    cnt3 = await db_manager.get_klines_count('BTC//USDT:USDT', '1m')
    print(f'3. BTC//USDT:USDT 1m: {cnt3} mum')

    # Test 4: Farklı temizleme
    cnt4 = await db_manager.get_klines_count('BTC/USDT', '1m')
    print(f'4. BTC/USDT 1m: {cnt4} mum')

    # Hangi semboller var?
    symbols = await db_manager.get_symbols_with_data()
    print(f"\n=== DB'deki Semboller ===")
    for s in symbols[:10]:
        print(f'  - {s}')

asyncio.run(test())
