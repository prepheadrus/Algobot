"""
Test: UI silme simülasyonu
"""
import asyncio
from api.services.data_service import DataService
from api.schemas.data import DataDeleteRequest
from data.database import db_manager
from data.ohlcv_storage import get_storage

async def test():
    print("\n" + "="*60)
    print("TEST: UI Silme Simülasyonu (DB + Flat files)")
    print("="*60)
    
    await db_manager.connect()
    data_service = DataService()
    storage = get_storage()
    
    # 1. Mevcut durum
    print("\n[1] Mevcut durum:")
    inventory = await data_service.get_data_inventory()
    print(f"    DB: {inventory.get('total_candles', 0):,} mum")
    
    from pathlib import Path
    base_dir = Path("data/ohlcv")
    if base_dir.exists():
        total_files = sum(1 for f in base_dir.rglob("*.json"))
        print(f"    Flat files: {total_files} dosya")
    
    # 2. UI'dan gelen sembol formatı (örn: "BTC/USDT")
    print("\n[2] Silme işlemi (UI formatı ile)...")
    
    # UI'dan gelen format: "BTC/USDT" veya "BTC/USDT:USDT"
    test_symbols = [
        "BTC/USDT",
        "BTC/USDT:USDT",
        "ETH/USDT",
        "ETH/USDT:USDT",
    ]
    
    for symbol in test_symbols:
        print(f"\n    Test: {symbol}")
        
        # DB'de hangi format var?
        sql = "SELECT DISTINCT symbol FROM klines WHERE symbol LIKE ?"
        async with db_manager.sqlite_conn.execute(sql, (f"%{symbol.replace('/', '').replace(':', '')}%",)) as cursor:
            rows = await cursor.fetchall()
            if rows:
                db_symbol = rows[0][0]
                print(f"      DB'de: {db_symbol}")
                
                # Sil
                request = DataDeleteRequest(symbol=db_symbol, timeframe=None, market_type="future")
                result = await data_service.delete_data(request)
                print(f"      Silindi: {result.get('deleted_count', 0):,} mum")
            else:
                print("      DB'de yok")
    
    # 3. Son durum
    print("\n[3] Son durum:")
    inventory = await data_service.get_data_inventory()
    print(f"    DB: {inventory.get('total_candles', 0):,} mum")
    
    if base_dir.exists():
        total_files = sum(1 for f in base_dir.rglob("*.json"))
        print(f"    Flat files: {total_files} dosya")
        
        # Detaylı liste
        print("\n    Detay:")
        for symbol_dir in base_dir.iterdir():
            if symbol_dir.is_dir():
                for tf_dir in symbol_dir.iterdir():
                    if tf_dir.is_dir():
                        files = list(tf_dir.glob("*.json"))
                        print(f"      {symbol_dir.name}/{tf_dir.name}: {len(files)} dosya")
    else:
        print("    Flat files: Dizin yok")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(test())
