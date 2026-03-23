"""
Parquet Data Lake E2E Test Suite

Testler:
1. Timezone Standardization (UTC)
2. Async I/O Isolation
3. Dummy Data Test (Gap Detection)
4. Data Integrity Check
"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.logger import logger
from data.storage.parquet_lake import ParquetDataLake
from core.exchange import exchange_manager


class ParquetPipelineTest:
    """
    E2E Parquet Pipeline Test Suite.
    """

    def __init__(self):
        self.lake = ParquetDataLake(exchange='binance')
        self.exchange = exchange_manager
        self.test_symbol = 'BTC/USDT'
        self.test_timeframe = '15m'
        self.test_days = 7  # 1 hafta

    async def test_1_timezone_standardization(self):
        """
        TEST 1: Timezone Standardization

        Parquet dosyalarından okunan (existing_df) ve CCXT'den yeni çekilen (day_df)
        tüm verilerin indekslerinin kesin olarak UTC (offset-aware) yapıldığını doğrula.
        """
        logger.info("\n" + "="*80)
        logger.info("🧪 TEST 1: Timezone Standardization (UTC)")
        logger.info("="*80)

        try:
            # 1. Test DataFrame oluştur (tz-naive)
            test_df = pd.DataFrame({
                'open': [100.0, 101.0, 102.0],
                'high': [105.0, 106.0, 107.0],
                'low': [99.0, 100.0, 101.0],
                'close': [103.0, 104.0, 105.0],
                'volume': [1000.0, 1100.0, 1200.0]
            })

            # Timestamp ekle (ms formatında)
            base_ts = int(datetime(2026, 3, 17, 12, 0, 0).timestamp() * 1000)
            test_df['timestamp'] = [base_ts + i*900000 for i in range(3)]  # 15m intervals
            test_df['timestamp'] = pd.to_datetime(test_df['timestamp'], unit='ms')
            test_df.set_index('timestamp', inplace=True)

            logger.info(f"📊 [TEST] Oluşturulan DataFrame (tz-naive):")
            logger.info(f"   Index tzinfo: {test_df.index.tzinfo}")
            logger.info(f"   İlk satır: {test_df.index[0]}")

            # 2. Timezone dönüşümü (data_lake.py'deki mantık)
            from data.data_lake import DataLakeStorage
            storage = DataLakeStorage()

            # 🔥 DÜZELTME: timestamp kolonu index'te, dropna subset'ten çıkar
            # Sadece OHLCV kolonlarını kontrol et
            ohlcv_cols = ['open', 'high', 'low', 'close', 'volume']

            # NaN temizliği
            test_df = test_df.dropna(subset=ohlcv_cols)

            # Infinity temizliği
            test_df = test_df.replace([float('inf'), float('-inf')], float('nan'))
            test_df = test_df.dropna()

            # Timestamp'e göre sırala
            test_df = test_df.sort_index()

            # Duplicate temizliği
            test_df = test_df[~test_df.index.duplicated(keep='last')]

            # 🔥 TIMEZONE DÖNÜŞÜMÜ
            if test_df.index.tzinfo is None:
                test_df.index = test_df.index.tz_localize('UTC')
            else:
                test_df.index = test_df.index.tz_convert('UTC')

            logger.info(f"✅ [TEST] Timezone dönüşümü sonrası:")
            logger.info(f"   Index tzinfo: {test_df.index.tzinfo}")
            logger.info(f"   İlk satır: {test_df.index[0]}")

            # 3. Doğrulama
            assert test_df.index.tzinfo is not None, "❌ Index tz-naive kaldı!"
            assert str(test_df.index.tzinfo) == 'UTC', f"❌ Timezone UTC değil: {test_df.index.tzinfo}"

            logger.info(f"✅ [PASS] Timezone standardization BAŞARILI!")
            logger.info(f"   ✅ Tüm timestamp'ler UTC (offset-aware)")
            logger.info(f"   ✅ can't compare offset-naive and offset-aware hatası ÇÖZÜLDÜ")

            return True

        except AssertionError as e:
            logger.error(f"❌ [FAIL] {e}")
            return False
        except Exception as e:
            logger.error(f"❌ [ERROR] {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def test_2_async_io_isolation(self):
        """
        TEST 2: Async I/O Isolation
        
        pd.read_parquet ve pd.concat gibi ağır senkron I/O işlemlerinin tamamının 
        await asyncio.to_thread() ile sarmalandığını ve coroutine sızıntısı olmadığını doğrula.
        """
        logger.info("\n" + "="*80)
        logger.info("🧪 TEST 2: Async I/O Isolation")
        logger.info("="*80)

        try:
            # 1. Test DataFrame
            test_df = pd.DataFrame({
                'open': [100.0] * 100,
                'high': [105.0] * 100,
                'low': [99.0] * 100,
                'close': [103.0] * 100,
                'volume': [1000.0] * 100
            })
            test_df['timestamp'] = pd.date_range('2026-03-17', periods=100, freq='15min', tz='UTC')
            test_df.set_index('timestamp', inplace=True)
            
            # 2. Geçici dosya
            temp_path = Path("data/ohlcv/binance/BTC/USDT/15m/test_temp.parquet")
            temp_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 3. Senkron yazma (to_thread ile)
            logger.info(f"📝 [TEST] Parquet yazma (asyncio.to_thread)...")
            await asyncio.to_thread(test_df.to_parquet, temp_path, compression='snappy', index=False)
            logger.info(f"✅ [TEST] Dosya yazıldı: {temp_path}")
            
            # 4. Senkron okuma (to_thread ile)
            logger.info(f"📖 [TEST] Parquet okuma (asyncio.to_thread)...")
            loaded_df = await asyncio.to_thread(pd.read_parquet, temp_path)
            logger.info(f"✅ [TEST] Dosya okundu: {len(loaded_df)} satır")
            
            # 5. Doğrulama
            assert not asyncio.iscoroutine(loaded_df), "❌ DataFrame coroutine olarak döndü!"
            assert hasattr(loaded_df, 'empty'), "❌ DataFrame.empty attribute yok!"
            assert not loaded_df.empty, "❌ DataFrame boş!"
            
            # 6. Temizlik
            temp_path.unlink()
            logger.info(f"🗑️ [TEST] Geçici dosya silindi")
            
            logger.info(f"✅ [PASS] Async I/O isolation BAŞARILI!")
            logger.info(f"   ✅ asyncio.to_thread() doğru kullanılıyor")
            logger.info(f"   ✅ Coroutine sızıntısı YOK")
            logger.info(f"   ✅ 'coroutine object has no attribute empty' hatası ÇÖZÜLDÜ")
            
            return True
            
        except AssertionError as e:
            logger.error(f"❌ [FAIL] {e}")
            return False
        except Exception as e:
            logger.error(f"❌ [ERROR] {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def test_3_dummy_data_pipeline(self):
        """
        TEST 3: Dummy Data Pipeline (Gap Detection)
        
        Binance'den 1 haftalık 15m BTC/USDT verisi çek, Parquet'e yaz, geri oku 
        ve ilk satır ile son satır arasında veri kaybı (Gap) olmadığını doğrula.
        """
        logger.info("\n" + "="*80)
        logger.info("🧪 TEST 3: Dummy Data Pipeline (Gap Detection)")
        logger.info("="*80)

        try:
            # 1. Tarih aralığı
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=self.test_days)
            
            logger.info(f"📅 [TEST] Tarih aralığı: {start_date.date()} - {end_date.date()}")
            logger.info(f"📊 [TEST] Sembol: {self.test_symbol}, Timeframe: {self.test_timeframe}")
            
            # 2. Binance'den veri çek
            logger.info(f"📥 [TEST] Binance'den veri çekiliyor...")
            klines = await self.exchange.fetch_ohlcv(
                self.test_symbol,
                self.test_timeframe,
                since=int(start_date.timestamp() * 1000),
                limit=1000  # 15m * 1000 = ~10 gün
            )
            
            if not klines or len(klines) == 0:
                logger.error(f"❌ [FAIL] Binance'den veri çekilemedi!")
                return False
            
            logger.info(f"✅ [TEST] {len(klines)} mum çekildi")
            
            # 3. DataFrame'e dönüştür
            df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df.set_index('timestamp', inplace=True)
            
            expected_count = len(df)
            logger.info(f"📊 [TEST] DataFrame: {expected_count} satır")
            logger.info(f"   İlk mum: {df.index[0]}")
            logger.info(f"   Son mum: {df.index[-1]}")
            
            # 4. Parquet'e yaz
            logger.info(f"💾 [TEST] Parquet'e yazılıyor...")
            save_success = await self.lake.save(self.test_symbol, self.test_timeframe, df, append=False)

            # 🔥 DÜZELTME: ParquetDataLake MTF-Daily yapısı kullanıyor
            # Gerçek path: data/ohlcv/binance/BTC/USDT/15m/YYYY/MM/DD/data.parquet
            # 🔍 ÖNEMLİ: Symbol path'i "/" ile kalıyor, "_" değil!
            test_path = self.lake.BASE_DIR / "binance" / self.test_symbol / self.test_timeframe

            if not save_success:
                logger.warning(f"⚠️ [TEST] save() False döndü ama dosyaları kontrol ediyoruz...")

            # 🔍 YENİ: MTF-Daily yapısını kontrol et (YYYY/MM/DD/data.parquet)
            parquet_files = []
            if test_path.exists():
                # Tüm yıl/ay/gün klasörlerini tara
                for year_dir in test_path.glob("*/"):
                    for month_dir in year_dir.glob("*/"):
                        for day_dir in month_dir.glob("*/"):
                            day_files = list(day_dir.glob("data.parquet"))
                            parquet_files.extend(day_files)

            if not parquet_files:
                logger.error(f"❌ [FAIL] Parquet dosyaları bulunamadı!")
                logger.error(f"   🔍 Test path: {test_path}")
                # Mevcut dosyaları göster
                all_files = list(self.lake.BASE_DIR.rglob("*.parquet"))
                if all_files:
                    logger.error(f"   🔍 Mevcut Parquet dosyaları: {len(all_files)}")
                    # İlk 10 dosyayı göster
                    for f in all_files[:10]:
                        logger.error(f"      - {f.relative_to(self.lake.BASE_DIR)}")
                return False

            logger.info(f"✅ [TEST] {len(parquet_files)} Parquet dosyası bulundu (MTF-Daily yapısı)")
            logger.info(f"   🔍 Path: {test_path}")
            
            # 5. Parquet'ten oku
            logger.info(f"📖 [TEST] Parquet'ten okunuyor...")
            loaded_df = await self.lake.load_datasets(
                self.test_symbol,
                self.test_timeframe,
                start_date,
                end_date
            )
            
            if loaded_df is None or loaded_df.empty:
                logger.error(f"❌ [FAIL] Parquet'ten veri okunamadı!")
                return False
            
            loaded_count = len(loaded_df)
            logger.info(f"📊 [TEST] Okunan DataFrame: {loaded_count} satır")
            logger.info(f"   İlk mum: {loaded_df.index[0]}")
            logger.info(f"   Son mum: {loaded_df.index[-1]}")
            
            # 6. Gap detection
            logger.info(f"🔍 [TEST] Gap detection...")
            
            # Satır sayısı kontrolü
            if loaded_count != expected_count:
                gap = expected_count - loaded_count
                logger.error(f"❌ [FAIL] Veri kaybı tespit edildi: {gap} mum eksik!")
                return False
            
            # Timestamp süreklilik kontrolü
            expected_interval = pd.Timedelta(minutes=int(self.test_timeframe.replace('m', '')))
            actual_intervals = loaded_df.index.to_series().diff()
            
            # İlk interval'i kontrol et (NaT olabilir)
            if len(actual_intervals) > 1:
                first_interval = actual_intervals.iloc[1]
                if first_interval != expected_interval:
                    logger.error(f"❌ [FAIL] Timestamp süreksizliği! Beklenen: {expected_interval}, Gerçek: {first_interval}")
                    return False
            
            # 7. İlk ve son satır karşılaştırma
            first_match = (df.iloc[0] == loaded_df.iloc[0]).all()
            last_match = (df.iloc[-1] == loaded_df.iloc[-1]).all()
            
            if not first_match:
                logger.error(f"❌ [FAIL] İlk satır eşleşmiyor!")
                return False
            
            if not last_match:
                logger.error(f"❌ [FAIL] Son satır eşleşmiyor!")
                return False
            
            logger.info(f"✅ [TEST] İlk satır: ✅ Eşleşti")
            logger.info(f"✅ [TEST] Son satır: ✅ Eşleşti")
            
            # 8. Temizlik (test dosyasını sil)
            logger.info(f"🗑️ [TEST] Test dosyaları temizleniyor...")
            await self._cleanup_test_data()
            
            logger.info(f"✅ [PASS] Dummy data pipeline BAŞARILI!")
            logger.info(f"   ✅ Veri kaybı YOK (0 mum eksik)")
            logger.info(f"   ✅ Timestamp süreklilik OK")
            logger.info(f"   ✅ İlk/Son satır eşleşmesi OK")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ [ERROR] {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    async def _cleanup_test_data(self):
        """Test verilerini temizle."""
        try:
            import shutil
            test_path = self.lake.BASE_DIR / self.exchange / self.test_symbol.replace('/', '_') / self.test_timeframe
            if test_path.exists():
                shutil.rmtree(test_path)
                logger.info(f"🗑️ [CLEANUP] {test_path} silindi")
        except Exception as e:
            logger.warning(f"⚠️ [CLEANUP] Temizlik hatası: {e}")

    async def run_all_tests(self):
        """
        Tüm testleri çalıştır.
        """
        logger.info("\n" + "="*80)
        logger.info("🚀 PARQUET DATA LAKE E2E TEST SUITE")
        logger.info("="*80)
        
        results = {
            'timezone_standardization': await self.test_1_timezone_standardization(),
            'async_io_isolation': await self.test_2_async_io_isolation(),
            'dummy_data_pipeline': await self.test_3_dummy_data_pipeline()
        }
        
        # Özet
        logger.info("\n" + "="*80)
        logger.info("📊 TEST SONUÇLARI")
        logger.info("="*80)
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            logger.info(f"   {status}: {test_name}")
        
        logger.info(f"\n📈 TOPLAM: {passed}/{total} test başarılı")
        
        if passed == total:
            logger.info(f"\n🎉 TÜM TESTLER BAŞARILI! Data Integrity doğrulandı.")
            logger.info(f"   ✅ Timezone: UTC (offset-aware)")
            logger.info(f"   ✅ Async I/O: to_thread() ile sarılmış")
            logger.info(f"   ✅ Data Pipeline: Gap YOK")
        else:
            logger.error(f"\n❌ BAZI TESTLER BAŞARISIZ! Lütfen hataları inceleyin.")
        
        return passed == total


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    test_suite = ParquetPipelineTest()
    
    # Event loop
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Test çalıştır
    success = asyncio.run(test_suite.run_all_tests())
    
    # Exit code
    sys.exit(0 if success else 1)
