"""
Test: Envanterden silme (DB + Flat files)
"""
import asyncio
from api.services.data_service import DataService
from api.schemas.data import DataDeleteRequest
from data.database import db_manager

async def test():
    print("\n" + "="*60)
    print("TEST: Envanterden Silme (DB + Flat files)")
    print("="*60)
    
    await db_manager.connect()
    data_service = DataService()
    
    # 1. Mevcut durum
    print("\n[1] Mevcut durum:")
    inventory = await data_service.get_data_inventory()
    print(f"    DB: {inventory.get('total_candles', 0):,} mum")
    
    from pathlib import Path
    base_dir = Path("data/ohlcv")
    if base_dir.exists():
        total_files = sum(1 for f in base_dir.rglob("*.json"))
        print(f"    Flat files: {total_files} dosya")
        
        # Detay
        for symbol_dir in base_dir.iterdir():
            if symbol_dir.is_dir():
                print(f"      {symbol_dir.name}:")
                for tf_dir in symbol_dir.iterdir():
                    if tf_dir.is_dir():
                        files = list(tf_dir.glob("*.json"))
                        print(f"        {tf_dir.name}: {len(files)} dosya")
    else:
        print(f"    Flat files: Dizin yok")
    
    # 2. UI'dan gelen format ile sil (örn: "ETH/USDT")
    print("\n[2] Silme işlemi (UI formatı: ETH/USDT)...")

    request = DataDeleteRequest(
        symbol="ETH/USDT",  # UI'dan gelen format
        timeframe=None,
        market_type="future"
    )
    
    result = await data_service.delete_data(request)
    print(f"    Sonuç: {result['status']}")
    print(f"    Mesaj: {result['message']}")
    print(f"    Silinen: {result.get('deleted_count', 0):,} mum")
    
    # 3. Son durum
    print("\n[3] Son durum:")
    inventory = await data_service.get_data_inventory()
    print(f"    DB: {inventory.get('total_candles', 0):,} mum")
    
    if base_dir.exists():
        total_files = sum(1 for f in base_dir.rglob("*.json"))
        print(f"    Flat files: {total_files} dosya")
        
        if total_files > 0:
            print(f"      HATA: Flat files hala var!")
            for symbol_dir in base_dir.iterdir():
                if symbol_dir.is_dir():
                    print(f"      {symbol_dir.name}: VAR")
        else:
            print(f"      OK: Flat files temizlendi")
    else:
        print(f"    Flat files: Dizin yok (TAMAMEN TEMİZ)")
    
    # 4. Sonuç
    print("\n" + "="*60)
    db_empty = inventory.get('total_candles', 0) == 0
    ff_empty = not base_dir.exists() or sum(1 for f in base_dir.rglob("*.json")) == 0
    
    if db_empty and ff_empty:
        print("[OK] BAŞARILI! DB ve Flat files TAMAMEN silindi.")
    elif db_empty:
        print("[UYARI] DB silindi ama Flat files hala var!")
    elif ff_empty:
        print("[UYARI] Flat files silindi ama DB hala var!")
    else:
        print("[HATA] Her ikisi de silinmedi!")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(test())
