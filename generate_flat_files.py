"""
Manuel Flat File Oluşturucu (Superalgos Mimarisi)

Veritabanındaki 1m mumlardan TÜM timeframe'leri otomatik oluşturur
ve flat file'lara kaydeder.

Kullanım:
    python generate_flat_files.py
"""

import asyncio
import pandas as pd
from data.database import db_manager
from data.ohlcv_storage import get_storage
from data.indicators import StrategyIndicators
from core.logger import logger
import sys


async def main():
    print("=" * 70)
    print("🔧 MANUEL FLAT FILE OLUŞTURUCU (Superalgos Mimarisi)")
    print("=" * 70)
    print()
    
    # DB bağlantısı
    print("📊 Veritabanı bağlanıyor...")
    await db_manager.connect()
    print("✅ Veritabanı bağlantısı başarılı")
    print()
    
    # Storage başlat
    print("💾 Flat file storage başlatılıyor...")
    storage = get_storage()
    print(f"📁 Klasör: {storage.BASE_DIR.absolute()}")
    print()
    
    # DB'den sembolleri al
    print("🔍 Semboller bulunuyor...")
    symbols = await db_manager.get_symbols_with_data()
    
    if not symbols:
        print("❌ Veritabanında hiç sembol bulunamadı!")
        print("   Önce veri indirmeniz gerekiyor.")
        return
    
    print(f"✅ {len(symbols)} sembol bulundu:")
    for sym in symbols:
        print(f"   - {sym}")
    print()
    
    # Her sembolü işle
    processed_count = 0
    error_count = 0
    
    for symbol in symbols:
        print("=" * 70)
        print(f"🔄 {symbol} işleniyor...")
        print("-" * 70)
        
        try:
            # 1m veriyi çek (TÜM VERİ - doğrudan SQL query ile)
            print("   📖 1m mumlar veritabanından çekiliyor (TÜM VERİ)...")

            # Önce toplam sayıyı al
            total_count = await db_manager.get_klines_count(symbol, '1m')
            print(f"   📊 Toplam {total_count} mum bulundu")

            # Doğrudan SQL query ile tüm veriyi çek
            if db_manager.engine_type == "sqlite":
                async with db_manager.sqlite_conn.execute(
                    "SELECT timestamp, open, high, low, close, volume FROM klines WHERE symbol = ? AND timeframe = ? ORDER BY timestamp ASC",
                    (symbol, '1m')
                ) as cursor:
                    klines = await cursor.fetchall()
            else:
                # PostgreSQL
                async with db_manager.db_pool.acquire() as conn:
                    klines = await conn.fetch(
                        "SELECT timestamp, open, high, low, close, volume FROM klines WHERE symbol = $1 AND timeframe = $2 ORDER BY timestamp ASC",
                        symbol, '1m'
                    )

            if not klines or len(klines) == 0:
                print(f"   ⚠️ {symbol} için veri yok, atlanıyor...")
                error_count += 1
                continue

            print(f"   ✅ {len(klines)} mum çekildi (2025-2026 tüm veri)")
            
            # DataFrame'e çevir
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

            # Timestamp format kontrolü (datetime veya ms)
            if df['timestamp'].dtype == 'object' or pd.api.types.is_datetime64_any_dtype(df['timestamp']):
                # datetime objesi → ms'ye çevir
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df['timestamp'] = (df['timestamp'].astype('int64') // 10**6)  # ns → ms
            elif df['timestamp'].iloc[0] > 1e12:
                # Zaten ms, bir şey yapma
                pass
            else:
                # Saniye → ms
                df['timestamp'] = df['timestamp'] * 1000

            # 1m kaydet
            print("   💾 1m flat file kaydediliyor...")
            storage.save_ohlcv(symbol, '1m', df)
            print(f"   ✅ 1m: {len(df)} mum kaydedildi")
            
            # Tüm TF'leri oluştur
            timeframes = [
                '2m', '3m', '4m', '5m', '10m', '15m', '20m', '30m', '40m', '45m',
                '1h', '2h', '3h', '4h', '6h', '8h', '12h', '24h'
            ]
            
            print("   🔄 Timeframe'ler oluşturuluyor...")
            
            for tf in timeframes:
                try:
                    # Resample
                    df_tf = StrategyIndicators.resample_data(df, tf)
                    df_tf = df_tf.dropna()
                    
                    if not df_tf.empty:
                        # Kaydet
                        storage.save_ohlcv(symbol, tf, df_tf)
                        print(f"      ✅ {tf}: {len(df_tf)} mum")
                    else:
                        print(f"      ⚠️ {tf}: Boş veri, atlandı")
                
                except Exception as tf_error:
                    print(f"      ❌ {tf} hatası: {tf_error}")
                    error_count += 1
            
            processed_count += 1
            print(f"✅ {symbol} BAŞARIYLA TAMAMLANDI!")
            print()
            
        except Exception as e:
            print(f"❌ {symbol} hatası: {e}")
            print(f"   Stack trace: {e}", file=sys.stderr)
            error_count += 1
            continue
    
    # Özet
    print("=" * 70)
    print("📊 İŞLEM ÖZETİ")
    print("=" * 70)
    print(f"✅ Başarılı: {processed_count} sembol")
    print(f"❌ Hatalı:   {error_count} sembol")
    print(f"📁 Klasör:  {storage.BASE_DIR.absolute()}")
    print()
    
    # İstatistikler
    stats = storage.get_storage_stats()
    print(f"📊 TOPLAM İSTATİSTİKLER:")
    print(f"   Toplam sembol:    {stats['total_symbols']}")
    print(f"   Toplam timeframe: {stats['total_timeframes']}")
    print(f"   Toplam dosya:     {stats['total_files']}")
    print(f"   Toplam boyut:     {stats['total_size_mb']:.2f} MB")
    print()
    
    if processed_count > 0:
        print("🎉 FLAT FILE OLUŞTURMA BAŞARIYLA TAMAMLANDI!")
        print()
        print("ŞİMDİ YAPABİLECEKLERİNİZ:")
        print("  1. Uygulamayı restart edin: python main.py")
        print("  2. Dashboard'da bot başlatın")
        print("  3. ML Training yapın (0.1s içinde yüklenir!)")
        print()
    else:
        print("⚠️ Hiçbir sembol işlenemedi!")
        print("   Veritabanında veri olduğundan emin olun.")
    
    print("=" * 70)
    
    # DB kapat
    await db_manager.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Kullanıcı tarafından iptal edildi")
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        import traceback
        traceback.print_exc()
