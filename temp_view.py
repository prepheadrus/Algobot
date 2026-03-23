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
