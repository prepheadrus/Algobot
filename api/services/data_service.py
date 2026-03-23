"""
Data Service

Business logic for data operations.
"""

from typing import Dict, Any, List, Optional
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
        start_date: datetime,
        end_date: datetime
    ) -> Optional[pd.DataFrame]:
        """
        AKILLI ÖNBELLEK (Smart Caching) - Köprü Fonksiyonu

        1. Önce Parquet gölünden yükle (vektörize okuma)
        2. Eksik günleri tespit et
        3. SADECE eksik günler için SQLite'dan 1m çek + resample et
        4. Parquet'e kaydet + RAM'de birleştir
        5. Tüketiciye (ML/Backtest) tam DataFrame döndür

        Args:
            symbol: Sembol adı (örn: BTC/USDT)
            timeframe: Zaman dilimi (örn: 1h, 4h, 1d)
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi

        Returns:
            DataFrame (OHLCV + indicators) veya None
        """
        from datetime import datetime, timedelta
        import pandas as pd
        from data.indicators import StrategyIndicators

        logger.info(f"🔍 [SMART CACHE] {symbol} {timeframe} → {start_date} - {end_date}")

        # 1. Parquet gölünden yükle (vektörize okuma)
        lake = self._get_parquet_lake()
        df_cached = await lake.load_datasets(symbol, timeframe, start_date, end_date)

        # Eğer tüm veri Parquet'te varsa, direkt döndür
        if df_cached is not None and not df_cached.empty:
            cached_start = df_cached.index.min()
            cached_end = df_cached.index.max()

            # Tarih aralığı tam kapsanıyor mu? (timezone-aware)
            start_ts = pd.Timestamp(start_date).tz_convert('UTC') if hasattr(start_date, 'tzinfo') else pd.Timestamp(start_date, tz='UTC')
            end_ts = pd.Timestamp(end_date).tz_convert('UTC') if hasattr(end_date, 'tzinfo') else pd.Timestamp(end_date, tz='UTC')

            if cached_start <= start_ts and cached_end >= end_ts:
                logger.info(f"✅ [SMART CACHE] {symbol} {timeframe} → Parquet'ten TAM yüklendi ({len(df_cached)} satır)")
                return df_cached

            logger.info(f"📊 [SMART CACHE] Parquet'te KISMİ veri: {cached_start} - {cached_end}")

        # 2. Eksik tarihleri tespit et
        missing_ranges = []

        if df_cached is None or df_cached.empty:
            # Hiç veri yok - tüm aralık eksik
            missing_ranges.append((start_date, end_date))
        else:
            # Kısmen var - eksik günleri bul
            current = start_date
            cached_dates = set(df_cached.normalize().index)

            while current <= end_date:
                current_date = current.replace(hour=0, minute=0, second=0, microsecond=0)

                if current_date not in cached_dates:
                    # Bu gün eksik - günün başlangıcını ve sonunu hesapla
                    day_start = current_date
                    day_end = current_date + timedelta(days=1) - timedelta(seconds=1)

                    # start_date ve end_date ile sınırla
                    day_start = max(day_start, start_date)
                    day_end = min(day_end, end_date)

                    missing_ranges.append((day_start, day_end))

                current += timedelta(days=1)

        if not missing_ranges:
            logger.info(f"✅ [SMART CACHE] {symbol} {timeframe} → Eksik gün yok")
            return df_cached

        logger.info(f"🔍 [SMART CACHE] {len(missing_ranges)} eksik gün tespit edildi")

        # 3. Eksik günler için SQLite'dan 1m çek + resample et
        dfs_to_concat = [df_cached] if df_cached is not None else []

        for missing_start, missing_end in missing_ranges:
            logger.info(f"📥 [SMART CACHE] Eksik gün: {missing_start} - {missing_end}")

            # 1m veriyi SQLite'dan çek
            # Limit hesapla (1m mum sayısı)
            days_diff = (missing_end - missing_start).days + 1
            limit_1m = days_diff * 24 * 60  # 1440 mum/gün

            logger.info(f"📊 [SMART CACHE] 1m çekiliyor: {symbol} (limit={limit_1m})")

            klines_1m = await self.db_manager.get_klines(symbol, '1m', limit=limit_1m)

            if not klines_1m or len(klines_1m) == 0:
                logger.warning(f"⚠️ [SMART CACHE] 1m veri bulunamadı: {symbol}")
                continue

            # DataFrame'e çevir
            df_1m = pd.DataFrame(klines_1m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

            # 🔥 DÜZELTME: Timestamp zaten datetime string olabilir, önce kontrol et
            # Eğer string ise (datetime formatında), direkt datetime'a çevir
            # Eğer numeric ise (ms timestamp), unit='ms' ile çevir
            if isinstance(df_1m['timestamp'].iloc[0], str):
                # String datetime → datetime (timezone-aware)
                df_1m['timestamp'] = pd.to_datetime(df_1m['timestamp'], utc=True)
            else:
                # Numeric timestamp (ms) → datetime
                df_1m['timestamp'] = pd.to_datetime(df_1m['timestamp'], unit='ms', utc=True)

            df_1m.set_index('timestamp', inplace=True)

            # Tarih aralığını filtrele (timezone-aware timestamp'lar)
            missing_start_ts = pd.Timestamp(missing_start).tz_convert('UTC') if hasattr(missing_start, 'tzinfo') else pd.Timestamp(missing_start, tz='UTC')
            missing_end_ts = pd.Timestamp(missing_end).tz_convert('UTC') if hasattr(missing_end, 'tzinfo') else pd.Timestamp(missing_end, tz='UTC')

            df_1m = df_1m[
                (df_1m.index >= missing_start_ts) &
                (df_1m.index <= missing_end_ts)
            ]

            if df_1m.empty:
                logger.warning(f"⚠️ [SMART CACHE] Filtre sonrası boş: {missing_start} - {missing_end}")
                continue

            # Resample: 1m → hedef timeframe
            logger.info(f"🔄 [SMART CACHE] Resampling: 1m → {timeframe}")
            df_resampled = StrategyIndicators.resample_data(df_1m, timeframe)

            # NaN temizliği (forward fill + dropna)
            df_resampled = df_resampled.ffill()  # Forward fill
            df_resampled = df_resampled.dropna(how='all')  # Tüm kolonlar boşsa sil

            if df_resampled.empty:
                logger.warning(f"⚠️ [SMART CACHE] Resample sonrası boş: {timeframe}")
                continue

            # 4. Parquet'e kaydet
            logger.info(f"💾 [SMART CACHE] Parquet'e kaydediliyor: {symbol} {timeframe}")
            await lake.save(symbol, timeframe, df_resampled, append=True)

            dfs_to_concat.append(df_resampled)

        # 5. RAM'de birleştir
        if not dfs_to_concat:
            logger.warning(f"⚠️ [SMART CACHE] Birleştirilecek veri yok")
            return None

        df_combined = pd.concat(dfs_to_concat)

        # Duplicate temizliği
        df_combined = df_combined[~df_combined.index.duplicated(keep='last')]

        # Sırala
        df_combined = df_combined.sort_index()

        # Tarih aralığını filtrele (timezone-aware)
        start_ts = pd.Timestamp(start_date).tz_convert('UTC') if hasattr(start_date, 'tzinfo') else pd.Timestamp(start_date, tz='UTC')
        end_ts = pd.Timestamp(end_date).tz_convert('UTC') if hasattr(end_date, 'tzinfo') else pd.Timestamp(end_date, tz='UTC')

        # 🔥 DÜZELTME: Index DatetimeIndex değilse çevir
        if not isinstance(df_combined.index, pd.DatetimeIndex):
            df_combined.index = pd.to_datetime(df_combined.index, utc=True)

        # Index timezone-aware değilse UTC yap
        if df_combined.index.tzinfo is None:
            df_combined.index = df_combined.index.tz_localize('UTC')

        # Filtreleme (artık güvenli)
        df_combined = df_combined[
            (df_combined.index >= start_ts) &
            (df_combined.index <= end_ts)
        ]

        # Son NaN temizliği
        df_combined = df_combined.ffill().dropna(how='all')

        logger.info(f"✅ [SMART CACHE] {symbol} {timeframe} → TAM yüklendi ({len(df_combined)} satır)")
        return df_combined
    
    def _normalize_market_type(self, market_type_str: str, symbol: str) -> str:
        """Converts user-facing market type strings into system-level 'spot' or 'future' types."""
        lowered_str = str(market_type_str).lower()
        if any(keyword in lowered_str for keyword in ['perp', 'future', 'vadeli', 'swap']):
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
                    # Tüm download_tasks'ları kontrol et ve sil
                    sql_all = "SELECT symbol, market_type FROM download_tasks"
                    if self.db_manager.engine_type == "sqlite":
                        async with self.db_manager.sqlite_conn.execute(sql_all) as cursor:
                            all_tasks = await cursor.fetchall()
                            for row in all_tasks:
                                db_symbol = row[0]
                                db_mt = row[1]
                                if '-- SEÇİNİZ --' in db_symbol or 'SEÇİNİZ' in db_symbol or db_symbol == '':
                                    await self.db_manager.delete_download_task(db_symbol, db_mt)
                                    logger.info(f"🗑️ Geçersiz görev temizlendi: {db_symbol}_{db_mt}")
                                    deleted_count += 1
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
