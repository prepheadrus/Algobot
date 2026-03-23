"""
Test: Flat file silme
"""
import asyncio
from data.ohlcv_storage import get_storage

async def test():
    storage = get_storage()
    
    # Mevcut sembolleri kontrol et
    print("\nMevcut flat file'lar:")
    import os
    from pathlib import Path
    
    base_dir = Path("data/ohlcv")
    if base_dir.exists():
        for symbol_dir in base_dir.iterdir():
            if symbol_dir.is_dir():
                print(f"\n  {symbol_dir.name}:")
                for tf_dir in symbol_dir.iterdir():
                    if tf_dir.is_dir():
                        files = list(tf_dir.glob("*.json"))
                        print(f"    {tf_dir.name}: {len(files)} dosya")
    
    # Silme testi
    print("\n\nSilme testi:")
    symbol = "BTC/USDT:USDT"
    symbol_for_flat = symbol.replace('/', '_').replace(':', '_')
    print(f"  Sembol: {symbol}")
    print(f"  Flat path: {symbol_for_flat}")
    
    deleted = storage.delete_ohlcv(symbol_for_flat)
    print(f"  Silinen dosya: {deleted}")
    
    # Son durum
    print("\n\nSon durum:")
    if base_dir.exists():
        for symbol_dir in base_dir.iterdir():
            if symbol_dir.is_dir():
                print(f"  {symbol_dir.name}: VAR")
            else:
                print(f"  {symbol_dir.name}: (dosya)")
    else:
        print("  data/ohlcv/ dizini YOK")

if __name__ == "__main__":
    asyncio.run(test())
