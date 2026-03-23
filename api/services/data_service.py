"""
Data Service

Business logic for data operations.
"""

from typing import Dict, Any, List, Optional, Final
from datetime import datetime
import pandas as pd

from core.logger import logger
from core.exchange import exchange_manager
from data.database import db_manager
from api.schemas.data import (
    DataDownloadRequest,
    DataStopRequest,
    DataResumeRequest,
    DataDeleteRequest,
    DataPauseRequest,
)

MARKET_TYPE_KEYWORDS: Final = ('perp', 'future', 'vadeli', 'swap')


class DataService:
    """
    Data Service.

    Business logic for data operations:
    - Download historical data
    - Stop download
    - Resume download
    - Delete data
    - Pause/resume download
    - Get history status
    - Get active downloads
    """

    def __init__(self):
        self.exchange_manager = exchange_manager
        self.db_manager = db_manager
        self.parquet_lake = None  # Lazy load

    def _get_parquet_lake(self):
        """Lazy load ParquetDataLake (singleton)"""
        if self.parquet_lake is None:
            from data.storage.parquet_lake import get_parquet_lake
            self.parquet_lake = get_parquet_lake('binance')
        return self.parquet_lake

    async def get_cached_or_fetch_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        HIBRET VERİ SAĞLAYICI (Hybrid Data Provider) - Zaman Makinesi Mimarisi

        1. A) Önce Parquet Diski tara (Master Data = 1m).
        2. B) Eğer diskteki veri hedef timeframe değilse (örn: 1h isteniyor ama diskte 1m varsa),
              hemen RAM'de anlık (on-the-fly) resample et. Sadece `1m` okur.
        3. C) Diskteki veri ile günümüz arasında gap varsa veya hiç veri yoksa,
              REST API üzerinden sadece eksik kısımları (1m formatında) tamamla.

        Args:
            symbol: Sembol adı (örn: BTC/USDT)
            timeframe: Hedef zaman dilimi (örn: 15m, 1h)
            start_date: Başlangıç tarihi (opsiyonel)
            end_date: Bitiş tarihi (opsiyonel)

        Returns:
            pd.DataFrame veya None
        """
        from datetime import datetime, timezone, timedelta
        import pandas as pd
        from data.indicators import StrategyIndicators

        # IMPORT FALLBACK, so we don't block
        try:
            from shared.constants import VALID_TIMEFRAMES, MASTER_TIMEFRAME
        except ImportError:
            VALID_TIMEFRAMES = ('1m', '2m', '3m', '5m', '10m', '15m', '20m', '30m', '40m', '45m', '1h', '2h', '3h', '4h', '6h', '12h', '24h')
            MASTER_TIMEFRAME = '1m'

        logger.info(f"🔍 [HYBRID DATA] İsteniyor: {symbol} | TF: {timeframe} | {start_date} -> {end_date}")

        if timeframe not in VALID_TIMEFRAMES:
            logger.warning(f"⚠️ Geçersiz zaman dilimi istendi: {timeframe}")
            return None

        # 1. Warm-up: Master Data'yı (1m) ParquetLake'ten yükle
        # NOT: DataLake _sadece_ 1m veriyi yükleyecek şekilde zorlanıyor. (Master Data = 1m)
        lake = self._get_parquet_lake()

        logger.info(f"🔍 [HYBRID DATA] (A) Parquet Lake üzerinden 1m (Master Data) taranıyor...")
        df_1m = await lake.load_datasets(symbol, MASTER_TIMEFRAME, start_date, end_date)

        if df_1m is not None and not df_1m.empty:
            logger.info(f"💾 [HYBRID DATA] Diskte {len(df_1m)} adet 1m mum bulundu.")

            # Zaman kontrolü: tz_localize / tz_convert garantisi
            if df_1m.index.tzinfo is None:
                df_1m.index = df_1m.index.tz_localize('UTC')
            else:
                df_1m.index = df_1m.index.tz_convert('UTC')
        else:
            logger.info(f"⚠️ [HYBRID DATA] Diskte 1m Master Data bulunamadı.")
            df_1m = pd.DataFrame()

        # 2. Gap Fill (Diskteki son veri ile günümüz arasını tamamla veya API'den tümünü çek)
        current_time_utc = pd.Timestamp(datetime.now(timezone.utc))
        target_end_ts = pd.Timestamp(end_date).tz_convert('UTC') if end_date else current_time_utc

        # Fetching parameters
        api_fetch_required = False
        fetch_limit = 0

        if df_1m.empty:
            # Hiç veri yok, C durumu: Doğrudan API'den çek (maks limit)
            api_fetch_required = True
            # WFOEngine vb. bir `days` parametresi aracılığıyla `start_date` verdiyse:
            if start_date:
                gap_minutes = (target_end_ts - (pd.Timestamp(start_date).tz_convert('UTC') if hasattr(start_date, 'tzinfo') else pd.Timestamp(start_date, tz='UTC'))).total_seconds() / 60
                fetch_limit = min(int(gap_minutes) + 10, 1500)
            else:
                fetch_limit = 1500
            logger.info(f"🔄 [HYBRID DATA] (C) Diskte hiç veri yok. API'den {fetch_limit} mumluk tam yükleme tetiklenecek.")
        else:
            last_candle_ts = df_1m.index.max()
            gap_minutes = (target_end_ts - last_candle_ts).total_seconds() / 60

            if gap_minutes > 5:
                api_fetch_required = True
                fetch_limit = min(int(gap_minutes) + 10, 1000)
                logger.info(f"🔄 [HYBRID DATA] (C) {int(gap_minutes)} dakikalık gap tespit edildi. API'den tamamlanıyor...")

        # API (Database fallback veya borsa) verisini yükle
        if api_fetch_required:
            # Geçmiş veriyi çek (sadece eksik bölümü 1m olarak)
            klines = await self.db_manager.get_klines(symbol, MASTER_TIMEFRAME, limit=fetch_limit)

            if klines:
                df_gap = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                if isinstance(df_gap['timestamp'].iloc[0], str):
                    df_gap['timestamp'] = pd.to_datetime(df_gap['timestamp'], utc=True)
                else:
                    df_gap['timestamp'] = pd.to_datetime(df_gap['timestamp'], unit='ms', utc=True)
                df_gap.set_index('timestamp', inplace=True)

                if not df_1m.empty:
                    df_1m = pd.concat([df_1m, df_gap])
                    df_1m = df_1m[~df_1m.index.duplicated(keep='last')].sort_index()
                else:
                    df_1m = df_gap.sort_index()
            else:
                logger.warning(f"⚠️ [HYBRID DATA] API'de de veri bulunamadı! (Limit: {fetch_limit})")

        # 3. Tarih Aralığı Filtresi (Tekrar Uygula - Güvenlik İçin)
        if not df_1m.empty:
            if start_date:
                start_ts = pd.Timestamp(start_date).tz_convert('UTC') if hasattr(start_date, 'tzinfo') else pd.Timestamp(start_date, tz='UTC')
                df_1m = df_1m[df_1m.index >= start_ts]
            if end_date:
                end_ts = pd.Timestamp(end_date).tz_convert('UTC') if hasattr(end_date, 'tzinfo') else pd.Timestamp(end_date, tz='UTC')
                df_1m = df_1m[df_1m.index <= end_ts]

        if df_1m.empty:
            logger.warning(f"❌ [HYBRID DATA] Birleştirme ve filtreleme sonrası veri yok!")
            return None

        # 4. On-the-Fly Resampling (B)
        # Diskteki Master Data (1m) veya API'den çekilen birleşmiş veri hedef timeframe değilse RAM'de resample et.
        if timeframe == MASTER_TIMEFRAME:
            logger.info(f"✅ [HYBRID DATA] {symbol} {timeframe} başarıyla yüklendi. (Satır: {len(df_1m)})")
            return df_1m

        logger.info(f"⚙️ [HYBRID DATA] (B) Resampling işlemi yapılıyor: 1m -> {timeframe}")
        df_resampled = StrategyIndicators.resample_data(df_1m, timeframe)

        # Olası NaN değerleri doldur
        df_resampled = df_resampled.ffill().dropna(how='all')

        logger.info(f"✅ [HYBRID DATA] {symbol} {timeframe} RAM'de başarıyla üretildi. (Satır: {len(df_resampled)})")
        return df_resampled
    
    def _normalize_market_type(self, market_type_str: str, symbol: str) -> str:
        """Converts user-facing market type strings into system-level 'spot' or 'future' types."""
        if market_type_str is None or pd.isna(market_type_str):
            if ':' in symbol or symbol.endswith('-SWAP'):
                return 'future'
            return 'spot'

        lowered_str = str(market_type_str).lower()
        for keyword in MARKET_TYPE_KEYWORDS:
            if keyword in lowered_str:
                return 'future'
        if ':' in symbol or symbol.endswith('-SWAP'):
            return 'future'
        return 'spot'
    
    async def start_download(self, request: DataDownloadRequest) -> Dict[str, Any]:
        """
        Geçmiş veri indirme başlat.

        Args:
            request: Veri indirme isteği

        Returns:
            İndirme başlatma yanıtı
        """
        symbol = request.symbol.split('_')[0].strip() if '_' in request.symbol else request.symbol
        market_type = self._normalize_market_type(request.market_type, symbol)
        key = f"{symbol}_{market_type}"

        # Check if already downloading
        if key in self.exchange_manager.active_downloads:
            task = self.exchange_manager.active_downloads[key]
            return {
                "status": "exists",
                "message": f"{key} için zaten bir kayıt ({task['status'].upper()}) bulunuyor.",
                "task": task
            }

        # ========================================================================
        # YENİ: RESAMPLING MİMARİSİ - Her zaman 1m indirilir
        # ========================================================================
        logger.info(f"🔄 [DATA] {request.symbol} için {request.timeframe} talep edildi, ancak SADECE 1m indiriliyor...")
        logger.info(f"📊 [DATA] Resampling Mimarisi: Veritabanı %98 Optimize Edildi")
        logger.info(f"💡 [DATA] Diğer TF'ler (5m, 15m, 1h, vb.) RAM üzerinde otomatik oluşturulacak")

        # Timeframe'i 1m'ye zorla (kullanıcı ne seçerse seçsin)
        download_timeframe = '1m'

        # Start download in background
        import asyncio
        asyncio.create_task(
            self.exchange_manager.download_historical_data(
                symbol,
                download_timeframe,  # Her zaman 1m
                request.start_date,
                market_type
            )
        )

        return {
            "status": "started",
            "message": f"{key} ({market_type}) için {request.start_date} tarihinden itibaren SADECE 1m veri indirme görevi başlatıldı. Diğer TF'ler otomatik oluşturulacak."
        }
    
    async def stop_download(self, request: DataStopRequest) -> Dict[str, Any]:
        """
        İndirme durdur.
        
        Args:
            request: İndirme durdurma isteği
        
        Returns:
            Durdurma yanıtı
        """
        symbol = request.symbol
        key = f"{symbol}_future"  # Default to future
        
        if key not in self.exchange_manager.active_downloads:
            # Try spot
            key = f"{symbol}_spot"
        
        if key in self.exchange_manager.download_stops:
            self.exchange_manager.download_stops[key] = True
            return {"status": "success", "message": f"{symbol} için indirme durduruldu."}
        
        return {"status": "error", "message": f"{symbol} için aktif indirme bulunamadı."}
    
    async def resume_download(self, request: DataResumeRequest) -> Dict[str, Any]:
        """
        İndirme devam ettir.
        
        Args:
            request: İndirme devam ettirme isteği
        
        Returns:
            Devam ettirme yanıtı
        """
        # TODO: Implement resume logic
        return {"status": "success", "message": f"{request.symbol} için indirme devam ettirildi."}
    
    async def delete_data(self, request: DataDeleteRequest) -> Dict[str, Any]:
        """
        Veri sil.

        Args:
            request: Veri silme isteği
            - timeframe=None ise: TÜM timeframe'leri sil
            - timeframe='1m' ise: Sadece 1m sil

        Returns:
            Silme yanıtı
        """
        try:
            # ========================================================================
            # 0. SEMBOL FORMATINI DÜZELT
            # ========================================================================
            # Kullanıcı "BCH/USDT" gönderir, ama DB'de "BCH/USDT:USDT" olabilir
            # Flat file'da "BCH_USDT:USDT" olarak kayıtlı
            # ========================================================================
            symbol_clean = request.symbol.strip()

            logger.info(f"🗑️ [DELETE] Veri silme isteği: {request.symbol}")
            logger.info(f"   - Sembol (ham): {symbol_clean}")
            logger.info(f"   - Timeframe: {request.timeframe if request.timeframe else 'TÜM TF'}")

            # ========================================================================
            # 1. VERİTABANI TEMİZLİĞİ
            # ========================================================================
            # DB'de hangi sembol varyasyonları var kontrol et
            # ========================================================================
            try:
                # DB'deki gerçek sembolü bul
                sql_find = "SELECT DISTINCT symbol FROM klines WHERE symbol = ? OR symbol LIKE ? OR symbol LIKE ?"
                pattern1 = f"{symbol_clean}%"  # BTC/USDT%
                pattern2 = f"%{symbol_clean.replace('/', '').replace(':', '')}%"  # %BCHUSDT%

                found_symbols = []
                if self.db_manager.engine_type == "sqlite":
                    async with self.db_manager.sqlite_conn.execute(
                        sql_find, (symbol_clean, pattern1, pattern2)
                    ) as cursor:
                        rows = await cursor.fetchall()
                        found_symbols = [row[0] for row in rows]

                logger.info(f"📊 [DELETE] DB'de bulunan semboller: {found_symbols}")

                # Eğer hiç sembol bulunamadıysa, kullanıcıya bilgi ver
                # AMA FLAT FILE'LARI YİNE DE SİL!
                if not found_symbols:
                    logger.warning(f"⚠️ [DELETE] DB'de {symbol_clean} için veri bulunamadı, ama flat file'lar silinecek")
                    # Flat file silmek için symbol_clean kullan
                    found_symbols = [symbol_clean]

            except Exception as find_err:
                logger.warning(f"⚠️ [DELETE] Sembol bulma hatası: {find_err}")
                found_symbols = [symbol_clean]  # Varsayılan

            # Her bulunan sembol için DB'den sil
            total_deleted = 0
            for sym in found_symbols:
                try:
                    if request.timeframe:
                        deleted_count = await self.db_manager.delete_klines(sym, request.timeframe)
                        total_deleted += deleted_count
                        logger.info(f"🗑️ {sym} {request.timeframe} silindi: {deleted_count} mum")
                    else:
                        deleted_count = await self.db_manager.delete_klines(sym)
                        total_deleted += deleted_count
                        logger.info(f"🗑️ {sym} TÜM verileri silindi: {deleted_count} mum")
                except Exception as db_err:
                    logger.warning(f"⚠️ [DELETE] DB silme hatası ({sym}): {db_err}")

            if total_deleted > 0:
                db_message = f"{symbol_clean} için {total_deleted} mum silindi"
            else:
                db_message = f"{symbol_clean} için DB'de veri bulunamadı"

            # ========================================================================
            # 2. PARQUET LAKE TEMİZLİĞİ (YENİ MİMARİ)
            # ========================================================================
            # DİKKAT: Artık JSON yok, sadece Parquet!
            # ========================================================================
            try:
                from data.storage.parquet_lake import get_parquet_lake
                lake = get_parquet_lake('binance')

                # Parquet path'i oluştur - TÜM varyasyonları dene!
                # UI'dan gelen: "BTC/USDT" veya "BTC/USDT:USDT"
                # Parquet'te: "BTC/USDT" veya "BTC/USDT:USDT" (aynı format)

                symbol_variants = [symbol_clean]

                # Varyasyon: :USDT ekle (future için)
                if ':' not in symbol_clean and symbol_clean.endswith('/USDT'):
                    symbol_variants.append(symbol_clean.replace('/USDT', '/USDT:USDT'))

                # Duplicate'ları temizle
                symbol_variants = list(dict.fromkeys(symbol_variants))

                logger.info(f"📂 [PARQUET] Silinecek semboller: {symbol_variants}")

                total_pq_deleted = 0
                for symbol_for_lake in symbol_variants:
                    logger.info(f"   - Deneniyor: {symbol_for_lake}")

                    try:
                        # Parquet'ten sil
                        await lake.delete(symbol_for_lake, request.timeframe)
                        total_pq_deleted += 1
                        logger.info(f"🗑️ {symbol_for_lake} Parquet'ten silindi")
                    except Exception as pq_err:
                        logger.debug(f"   - Hata ({symbol_for_lake}): {pq_err}")

                if total_pq_deleted > 0:
                    logger.info(f"✅ [PARQUET] Toplam {total_pq_deleted} sembol Parquet'ten silindi")
                else:
                    logger.warning(f"⚠️ [PARQUET] Hiçbir Parquet dosyası bulunamadı veya silinmedi")

            except Exception as parquet_err:
                logger.error(f"❌ [PARQUET] Silme hatası: {parquet_err}")
                logger.error(f"   - Sembol: {symbol_clean}")
                import traceback
                logger.error(f"   - Traceback: {traceback.format_exc()}")

            # ========================================================================
            # 3. YANIT
            # ========================================================================
            return {
                "status": "success",
                "message": f"{db_message} (Parquet Lake'ten silindi)",
                "deleted_count": total_deleted
            }
        except Exception as e:
            logger.error(f"❌ [DELETE] Silme hatası: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"status": "error", "message": str(e)}

    async def delete_all_klines(self) -> Dict[str, Any]:
        """
        Veritabanındaki TÜM klines verilerini siler.
        DİKKAT: Geri alınamaz!

        Returns:
            Silme yanıtı
        """
        try:
            # ========================================================================
            # 1. VERİTABANI TEMİZLİĞİ
            # ========================================================================
            if self.db_manager.engine_type == "sqlite":
                async with self.db_manager.sqlite_conn.execute("DELETE FROM klines") as cursor:
                    await self.db_manager.sqlite_conn.commit()
                    deleted_count = cursor.rowcount
            else:
                # PostgreSQL için
                async with self.db_manager.db_pool.acquire() as conn:
                    result = await conn.execute("DELETE FROM klines")
                    deleted_count = int(result.split()[-1]) if result else 0

            logger.info(f"🗑️ [DATA] Tüm klines verileri temizlendi: {deleted_count} satır (DB)")

            # ========================================================================
            # 2. FLAT FILE TEMİZLİĞİ (Superalgos Mimarisi)
            # ========================================================================
            # DİKKAT: Tüm flat file'lar da silinmeli!
            # ========================================================================
            try:
                from data.ohlcv_storage import get_storage
                storage = get_storage()

                # Tüm sembollerin flat file'larını sil
                stats = storage.get_storage_stats()
                total_files = stats.get('total_files', 0)
                total_size_mb = stats.get('total_size_mb', 0)

                if total_files > 0:
                    # Her sembolü tek tek sil
                    for symbol in stats.get('symbols', {}).keys():
                        # symbol formatı: BTC_USDT (underscore'lu)
                        # delete_ohlcv için symbol formatı: BTC/USDT (slash'li)
                        symbol_normalized = symbol.replace('_', '/')
                        storage.delete_ohlcv(symbol_normalized)

                    logger.info(f"🗑️ [DATA] Tüm flat file'lar silindi: {total_files} dosya, {total_size_mb:.2f} MB")
                else:
                    logger.info("📊 [DATA] Silinecek flat file bulunamadı")

            except Exception as flat_file_err:
                logger.warning(f"⚠️ Flat file silme hatası (devam ediliyor): {flat_file_err}")

            # ========================================================================
            # 3. YANIT
            # ========================================================================
            logger.info(f"📊 [DATA] Resampling Mimarisi: Artık SADECE 1m mumları indireceğiz!")

            return {
                "status": "success",
                "message": f"Tüm veritabanı ve flat file'lar temizlendi: {deleted_count} satır (DB), {total_files if 'total_files' in locals() else 0} dosya (Flat)",
                "deleted_count": deleted_count
            }
        except Exception as e:
            logger.error(f"❌ Tüm verileri silme hatası: {e}")
            return {"status": "error", "message": str(e)}

    async def delete_download_task(self, request: DataDeleteRequest) -> Dict[str, Any]:
        """
        Download task sil.

        Args:
            request: Veri silme isteği (symbol + market_type)
            - Eğer request.timeframe varsa, data da silinir

        Returns:
            Silme yanıtı
        """
        try:
            # ÖNCE DB'de hangi market_type'lar var kontrol et
            symbol_clean = request.symbol.split('_')[0].strip()

            # ÖZEL: Geçersiz semboller için direkt temizleme
            is_invalid_symbol = (
                '-- SEÇİNİZ --' in request.symbol or
                'SEÇİNİZ' in request.symbol or
                symbol_clean == '' or
                symbol_clean == '-'
            )

            if is_invalid_symbol:
                logger.warning(f"⚠️ Geçersiz sembol temizleniyor: {request.symbol}")

            # DB'den bu sembolün tüm market_type'larını al
            sql_find = "SELECT market_type FROM download_tasks WHERE symbol = ?"
            found_types = []

            if self.db_manager.engine_type == "sqlite":
                async with self.db_manager.sqlite_conn.execute(sql_find, (symbol_clean,)) as cursor:
                    rows = await cursor.fetchall()
                    found_types = [row[0] for row in rows]

            logger.info(f"🗑️ Silme isteği: {request.symbol}")
            logger.info(f"   - Sembol (temiz): {symbol_clean}")
            logger.info(f"   - Request market_type: {request.market_type}")
            logger.info(f"   - DB'de bulunan market_type'lar: {found_types}")

            # Eğer birden fazla market_type varsa, hepsini sil
            if not found_types:
                # Sembol bulunamadı, normalize edilmiş hali dene
                market_type = self._normalize_market_type(request.market_type, request.symbol)
                found_types = [market_type]
                logger.info(f"   - Sembol bulunamadı, normalize ediliyor: {market_type}")

            # Her bulunan market_type'ı sil
            deleted_count = 0
            for mt in found_types:
                key = f"{symbol_clean}_{mt}"
                logger.info(f"   - Siliniyor: {key}")

                # RAM'den sil (aktif indirme varsa)
                if key in self.exchange_manager.active_downloads:
                    # İndirme durdur
                    if key in self.exchange_manager.download_stops:
                        self.exchange_manager.download_stops[key] = True
                    del self.exchange_manager.active_downloads[key]
                    logger.info(f"🗑️ RAM'den silindi: {key}")

                # Geçersiz semboller için özel temizleme (tüm varyasyonları sil)
                if is_invalid_symbol:
                    # Tüm download_tasks'ları toplu olarak temizle
                    cleared = await self.db_manager.cleanup_invalid_download_tasks()
                    deleted_count += cleared
                else:
                    # DB'den sil
                    await self.db_manager.delete_download_task(symbol_clean, mt)
                    deleted_count += 1
                    logger.info(f"🗑️ DB'den silindi: {symbol_clean}_{mt}")

                # ========================================================================
                # YENİ: Eğer timeframe belirtilmişse, data da silinsin
                # ========================================================================
                if request.timeframe:
                    try:
                        # symbol_clean kullan (DB'deki format ile eşleşmesi için)
                        logger.info(f"🗑️ {symbol_clean} verisi de siliniyor (timeframe: {request.timeframe})...")

                        # 1. DB'den sil
                        db_deleted = await self.db_manager.delete_klines(symbol_clean, request.timeframe)
                        logger.info(f"🗑️ DB'den {db_deleted} mum silindi")

                        # 2. Flat file'dan sil
                        # OHLCVStorage kendi içinde format çevirisi yapar
                        from data.ohlcv_storage import get_storage
                        storage = get_storage()
                        ff_deleted = storage.delete_ohlcv(request.symbol, request.timeframe)
                        logger.info(f"🗑️ Flat file'dan {ff_deleted} dosya silindi")

                    except Exception as data_err:
                        logger.warning(f"⚠️ Data silme hatası (devam ediliyor): {data_err}")

            return {
                "status": "success",
                "message": f"{request.symbol} için {deleted_count} görev silindi." +
                          (f" Veri de temizlendi." if request.timeframe else "")
            }
        except Exception as e:
            logger.error(f"Delete download task error: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {"status": "error", "message": str(e)}
    
    async def pause_download(self, request: DataPauseRequest) -> Dict[str, Any]:
        """
        İndirme duraklat/devam et.
        
        Args:
            request: Duraklatma isteği
        
        Returns:
            Duraklatma yanıtı
        """
        symbol = request.symbol
        key = f"{symbol}_future"
        
        if key not in self.exchange_manager.download_pauses:
            key = f"{symbol}_spot"
        
        if key in self.exchange_manager.download_pauses:
            if request.action == "pause":
                self.exchange_manager.download_pauses[key] = True
                return {"status": "success", "message": f"{symbol} için indirme duraklatıldı."}
            else:
                self.exchange_manager.download_pauses[key] = False
                return {"status": "success", "message": f"{symbol} için indirme devam ettirildi."}
        
        return {"status": "error", "message": f"{symbol} için aktif indirme bulunamadı."}
    
    async def get_history_status(self, symbol: str, timeframe: str = "1m") -> Dict[str, Any]:
        """
        Geçmiş durumunu al.
        
        Args:
            symbol: Sembol
            timeframe: Zaman dilimi
        
        Returns:
            Geçmiş durum yanıtı
        """
        data_range = await self.db_manager.get_candle_range(symbol, timeframe)
        
        if data_range:
            import pandas as pd
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "start_date": pd.to_datetime(data_range['start'], unit='ms').strftime('%Y-%m-%d %H:%M'),
                "end_date": pd.to_datetime(data_range['end'], unit='ms').strftime('%Y-%m-%d %H:%M'),
                "count_hint": "Dinamik hesaplanabilir"
            }
        
        return {"symbol": symbol, "status": "no_data"}
    
    async def get_active_downloads(self) -> Dict[str, Any]:
        """
        Aktif indirmeleri al.

        Returns:
            Aktif indirmeler yanıtı
        """
        return {
            "status": "success",
            "downloads": self.exchange_manager.active_downloads
        }

    async def get_all_download_tasks(self) -> Dict[str, Any]:
        """
        Tüm indirme görevlerini al (aktif + tamamlanan).

        Returns:
            Tüm indirme görevleri
        """
        try:
            # 1. Aktif indirmeler (exchange_manager.active_downloads)
            active_tasks = self.exchange_manager.active_downloads
            
            # 2. Tamamlanan görevler veritabanından
            completed_tasks = await self.db_manager.get_all_download_tasks_from_db()
            
            # Birleştir (aktif olanlar öncelikli)
            all_tasks = {**completed_tasks, **active_tasks}
            
            return {
                "status": "success",
                "downloads": all_tasks,
                "active_count": len(active_tasks),
                "total_count": len(all_tasks)
            }
        except Exception as e:
            logger.error(f"All download tasks error: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Hata olsa bile success dön (frontend çökmesin)
            return {
                "status": "success",
                "downloads": {},
                "active_count": 0,
                "total_count": 0
            }
    
    async def get_symbols_with_data(self) -> Dict[str, Any]:
        """
        Veritabanında verisi olan sembolleri al.

        Returns:
            Sembol listesi (obje formatında, market_type ile)
        """
        symbols = await self.db_manager.get_symbols_with_data()

        # Frontend uyumlu formata çevir (market_type ekleyerek)
        symbols_list = []
        for s in symbols:
            # MARKET TYPE TESPİTİ
            symbol_raw = s if isinstance(s, str) else s.get('symbol', '')
            market_type = 'future' if (':' in symbol_raw or symbol_raw.endswith('-SWAP')) else 'spot'
            market_label = '💹 Futures' if market_type == 'future' else '💰 Spot'

            symbols_list.append({
                "symbol": symbol_raw,
                "market_type": market_type,
                "market_label": market_label
            })

        return {"status": "success", "symbols": symbols_list}

    async def check_data_gaps(self, symbol: str = None) -> Dict[str, Any]:
        """
        Veri boşluklarını kontrol et.

        Args:
            symbol: Sembol (None ise tüm semboller)

        Returns:
            Boşluk listesi
        """
        try:
            from data.ohlcv_storage import get_storage
            from datetime import datetime, timedelta

            storage = get_storage()
            gaps = []

            # Hangi sembolleri kontrol edelim?
            if symbol:
                symbols_to_check = [symbol]
            else:
                # Tüm sembolleri al
                symbols_to_check = list(storage.BASE_DIR.iterdir()) if storage.BASE_DIR.exists() else []
                symbols_to_check = [d.name.replace('_', '/') for d in symbols_to_check if d.is_dir()]

            # Her sembolü kontrol et
            for sym in symbols_to_check:
                sym_clean = sym.replace('/', '_')

                # Son 30 günü kontrol et
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=30)

                df = storage.load_ohlcv(sym_clean, '1m', start_date, end_date)

                if df is not None and not df.empty:
                    # Son mum zamanı
                    last_mum_ts = df['timestamp'].max()
                    last_mum_time = datetime.fromtimestamp(last_mum_ts / 1000)

                    # Boşluk hesapla
                    minutes_gap = (end_date - last_mum_time).total_seconds() / 60

                    if minutes_gap > 5:  # 5 dakikadan fazla
                        gaps.append({
                            "symbol": sym,
                            "gap_start": last_mum_time.strftime('%Y-%m-%d %H:%M'),
                            "gap_end": end_date.strftime('%Y-%m-%d %H:%M'),
                            "gap_minutes": int(minutes_gap),
                            "gap_days": round(minutes_gap / 1440, 1)
                        })

            return {
                "status": "success",
                "gaps": gaps,
                "total_gaps": len(gaps)
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def fill_data_gaps(self, symbol: str = None) -> Dict[str, Any]:
        """
        Veri boşluklarını otomatik doldur.

        Args:
            symbol: Sembol (None ise tüm semboller)

        Returns:
            Doldurulan boşluklar
        """
        try:
            # Önce boşlukları kontrol et
            gaps_result = await self.check_data_gaps(symbol)
            gaps = gaps_result.get('gaps', [])

            if not gaps:
                return {
                    "status": "success",
                    "message": "Hiç boşluk bulunamadı",
                    "filled": []
                }

            filled = []

            # Her boşluğu doldur
            for gap in gaps:
                try:
                    logger.info(f"🔄 [GAP FILL] {gap['symbol']} için {gap['gap_days']} günlük boşluk dolduruluyor...")

                    await self.exchange_manager.download_historical_data(
                        symbol=gap['symbol'],
                        timeframe='1m',
                        start_date_str=gap['gap_start'].split(' ')[0],  # Sadece tarih
                        market_type='future',
                        is_resume=False
                    )

                    filled.append({
                        "symbol": gap['symbol'],
                        "gap_days": gap['gap_days'],
                        "status": "completed"
                    })

                    logger.info(f"✅ [GAP FILL] {gap['symbol']} için boşluk dolduruldu!")

                except Exception as e:
                    logger.error(f"❌ [GAP FILL] {gap['symbol']} hata: {e}")
                    filled.append({
                        "symbol": gap['symbol'],
                        "gap_days": gap['gap_days'],
                        "status": "failed",
                        "error": str(e)
                    })

            return {
                "status": "success",
                "message": f"{len(filled)} boşluk dolduruldu",
                "filled": filled
            }

        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def get_data_inventory(self) -> Dict[str, Any]:
        """
        Veritabanı envanterini al.

        Returns:
            Envanter verisi
        """
        try:
            inventory_data = await self.db_manager.get_data_inventory()
            return {
                "status": "success",
                "total_candles": inventory_data['total_candles'],
                "inventory": inventory_data['inventory'],
                "total_records": len(inventory_data['inventory'])
            }
        except Exception as e:
            logger.error(f"Data inventory error: {e}")
            return {
                "status": "error",
                "message": str(e),
                "total_candles": 0,
                "inventory": []
            }

    async def get_database_stats(self) -> Dict[str, Any]:
        """
        Veritabanı özet istatistiklerini al.

        Returns:
            İstatistik verisi
        """
        try:
            stats_data = await self.db_manager.get_database_stats()
            return {
                "status": "success",
                "total_candles": stats_data['total_candles'],
                "stats": stats_data['stats'],
                "total_symbols": stats_data['total_symbols']
            }
        except Exception as e:
            logger.error(f"Database stats error: {e}")
            return {
                "status": "error",
                "message": str(e),
                "total_candles": 0,
                "stats": [],
                "total_symbols": 0
            }
