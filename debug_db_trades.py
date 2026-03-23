"""
Debug: Check trades in database
"""
import asyncio
from data.database import db_manager
from core.logger import logger

async def test():
    await db_manager.connect()
    
    # Get recent trades
    trades = await db_manager.get_recent_trades(limit=10)
    
    print(f"\n{'='*60}")
    print(f"📊 VERİTABANINDA {len(trades)} İŞLEM BULUNDU")
    print(f"{'='*60}\n")
    
    if len(trades) == 0:
        print("❌ VERİTABANINDA HİÇ İŞLEM YOK!")
        print("\nOlası nedenler:")
        print("  1. Trade'ler DB'ye kaydedilmedi")
        print("  2. Trade ID duplicate (INSERT OR IGNORE atladı)")
        print("  3. closed_at DESC sıralaması yanlış")
    else:
        for i, t in enumerate(trades, 1):
            print(f"{i}. {t['symbol']} | {t['direction']} | "
                  f"PnL: ${t['pnl_usd']:.2f} | "
                  f"Reason: {t['reason']} | "
                  f"Closed: {t['closed_at']}")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    try:
        asyncio.run(test())
    except KeyboardInterrupt:
        print("\n\n🛑 Test durduruldu")
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()
