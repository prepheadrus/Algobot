"""
Test: Veri silme (DB + Flat files)
"""
import asyncio
from api.services.data_service import DataService
from api.schemas.data import DataDeleteRequest
from data.database import db_manager

async def test_delete():
    print("\n" + "="*60)
    print("TEST: Veri Silme (DB + Flat files)")
    print("="*60)

    # DB bağlantısını başlat
    print("\n[0] DB bağlantısı başlatılıyor...")
    await db_manager.connect()
    print("    OK - DB hazır")

    data_service = DataService()

    # 1. Önce mevcut durumu kontrol et
    print("\n[1] Mevcut durum kontrolü...")
    inventory = await data_service.get_data_inventory()
    print(f"    Envanter: {inventory.get('total_candles', 0):,} mum")
    print(f"    Kayıt sayısı: {inventory.get('total_records', 0)}")

    # Flat file kontrolü
    from pathlib import Path
    base_dir = Path("data/ohlcv")
    if base_dir.exists():
        total_files = sum(1 for f in base_dir.rglob("*.json"))
        print(f"    Flat files: {total_files} dosya")
    else:
        print("    Flat files: Dizin yok")

    # 2. Silme işlemi
    print("\n[2] Silme işlemi başlatılıyor...")
    request = DataDeleteRequest(
        symbol="ETH/USDT:USDT",
        timeframe=None,  # TÜM timeframe'ler
        market_type="future"
    )

    result = await data_service.delete_data(request)
    print(f"    Sonuç: {result['status']}")
    print(f"    Mesaj: {result['message']}")
    print(f"    Silinen: {result.get('deleted_count', 0):,} mum")

    # 3. Son durumu kontrol et
    print("\n[3] Son durum kontrolü...")
    inventory = await data_service.get_data_inventory()
    print(f"    Envanter: {inventory.get('total_candles', 0):,} mum")
    print(f"    Kayıt sayısı: {inventory.get('total_records', 0)}")

    # Flat file kontrolü
    if base_dir.exists():
        total_files = sum(1 for f in base_dir.rglob("*.json"))
        print(f"    Flat files: {total_files} dosya")
    else:
        print("    Flat files: Dizin yok")

    # 4. Sonuç
    print("\n" + "="*60)
    db_empty = inventory.get('total_candles', 0) == 0
    ff_empty = not base_dir.exists() or sum(1 for f in base_dir.rglob("*.json")) == 0

    if db_empty and ff_empty:
        print("[OK] BASARILI! DB ve Flat files TAMAMEN silindi.")
    elif db_empty:
        print("[UYARI] DB silindi ama Flat files hala var!")
    elif ff_empty:
        print("[UYARI] Flat files silindi ama DB hala var!")
    else:
        print("[HATA] Her ikisi de silinmedi!")
    print("="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(test_delete())
