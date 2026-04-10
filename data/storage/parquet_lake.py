"""
Parquet Data Lake - Superalgos Multi-Time-Frame Mimarisi

🏗️ MİMARİ:
- Multi-Time-Frame-Daily (MTF-D): 1m, 5m, 15m → Gün bazlı partition (YYYY/MM/DD/data.parquet)
- Multi-Time-Frame-Market (MTF-M): 1h, 4h, 1d → Tek dosya (market.parquet)
- Apache Parquet formatı (columnar storage, sıkıştırma)
- Asenkron I/O (asyncio.to_thread)
- Race condition koruması (asyncio.Lock)

Dosya Yapısı:
    data/ohlcv/
    └── binance/
        ├── BTC/USDT/
        │   ├── 1m/
        │   │   ├── 2026/
        │   │   │   ├── 03/
        │   │   │   │   ├── 15/
        │   │   │   │   │   └── data.parquet
        │   │   │   │   └── 16/
        │   │   │   │       └── data.parquet
        │   ├── 15m/
        │   │   └── 2026/
        │   │       └── 03/
        │   │           └── ...
        │   ├── 1h/
        │   │   └── market.parquet  (tek dosya)
        │   ├── 4h/
        │   │   └── market.parquet
        │   └── 1d/
        │       └── market.parquet

📊 AVANTAJLAR:
- Columnar storage → Sadece ihtiyacın olan kolonu oku (OHLCV)
- Snappy compression → %70-80 daha az disk alanı
- Predicate pushdown → WHERE clause disk seviyesinde filtreleme
- Schema evolution → Kolon ekleyebilirsin (backward compatible)
- Pandas DatetimeIndex → Hızlı zaman bazlı sorgulama
"""

import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
import polars as pl
from core.logger import logger

try:
    import pyarrow
    import pyarrow.parquet as pq
    PYARROW_AVAILABLE = True
except ImportError:
    PYARROW_AVAILABLE = False
    logger.warning("⚠️ PyArrow bulunamadı, Parquet desteği devre dışı")


class ParquetDataLake:
    """
    Superalgos Multi-Time-Frame Parquet Storage Engine.

    Usage:
        lake = ParquetDataLake()

        # Kaydet (asenkron)
        await lake.save('BTC/USDT', '1m', df)

        # Yükle (vektörize)
        df = await lake.load_datasets('BTC/USDT', '1m', start, end)

        # Varlık kontrolü
        exists = await lake.exists('BTC/USDT', '1h')
    """

    # Base directory
    BASE_DIR = Path("data/ohlcv")

    # Timeframe threshold (1 saat = 60 dakika)
    HOURLY_THRESHOLD = 60

    # Parquet compression
    COMPRESSION = 'snappy'  # snappy, gzip, brotli, zstd

    def __init__(self, exchange: str = 'binance'):
        """
        Parquet Data Lake başlat.

        Args:
            exchange: Borsa adı (binance, btcturk, vs.)
        """
        self.exchange = exchange
        self._locks: Dict[str, asyncio.Lock] = {}  # Symbol+timeframe bazlı lock'lar
        self._global_lock = asyncio.Lock()  # Lock dictionary için global lock

        # Base directory oluştur
        self.BASE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("🏗️ [PARQUET LAKE] Superalgos MTF Mimarisi Devrede")
        logger.info(f"📁 [PARQUET LAKE] Base: {self.BASE_DIR.absolute()}")
        logger.info(f"🏢 [PARQUET LAKE] Exchange: {self.exchange}")
        logger.info(f"💾 [PARQUET LAKE] Compression: {self.COMPRESSION}")
        logger.info(f"🚀 [PARQUET LAKE] PyArrow: {'✅' if PYARROW_AVAILABLE else '❌'}")

    def _get_timeframe_minutes(self, timeframe: str) -> int:
        """
        Timeframe'i dakikaya çevir.

        Args:
            timeframe: Zaman dilimi (örn: 1m, 15m, 1h, 4h, 1d)

        Returns:
            Dakika cinsinden değer
        """
        timeframe = timeframe.lower()
        
        if timeframe.endswith('m'):
            return int(timeframe[:-1])
        elif timeframe.endswith('h'):
            return int(timeframe[:-1]) * 60
        elif timeframe.endswith('d'):
            return int(timeframe[:-1]) * 24 * 60
        elif timeframe.endswith('w'):
            return int(timeframe[:-1]) * 7 * 24 * 60
        else:
            logger.warning(f"⚠️ Bilinmeyen timeframe: {timeframe}, varsayılan 1m")
            return 1

    def _is_intraday(self, timeframe: str) -> bool:
        """
        Timeframe 1 saatin altında mı?

        Args:
            timeframe: Zaman dilimi

        Returns:
            True ise intraday (gün bazlı partition)
        """
        return self._get_timeframe_minutes(timeframe) < self.HOURLY_THRESHOLD

    def _symbol_to_path(self, symbol: str) -> str:
        """
        Sembol ismini dosya yolu formatına çevir. (Fallback/Varsayılan yöntem)

        Args:
            symbol: Sembol adı (örn: BTC/USDT)

        Returns:
            Dosya yolu için sembol (örn: BTC_USDT)
        """
        return symbol.replace('/', '_').replace(':', '_')


    def _find_actual_symbol_path(self, symbol: str) -> str:
        """
        Diskteki gerçek klasör adını (BTC_USDT, BTC_USDT_USDT, BTC vb.) glob ile bulur.
        Bulamazsa varsayılan _symbol_to_path değerini döndürür.
        """
        base_dir = self.BASE_DIR / self.exchange
        if not base_dir.exists():
            return self._symbol_to_path(symbol)

        # Olası klasör isimleri
        base = symbol.split('/')[0] if '/' in symbol else symbol

        # 1. Tam Eşleşme (BTC_USDT, BTC_USDT_USDT)
        exact_variants = [
            symbol.replace('/', '_').replace(':', '_'),
            f"{base}_USDT_USDT",
            f"{base}_USDT"
        ]

        for variant in exact_variants:
            if (base_dir / variant).exists() and (base_dir / variant).is_dir():
                logger.debug(f"[DEBUG] Veri yolu bulundu (Exact Match): {(base_dir / variant).absolute()}")
                return variant

        # 2. İçinde Base geçen klasör (Recursive Glob benzeri)
        for folder in base_dir.iterdir():
            if folder.is_dir() and folder.name.startswith(base):
                logger.debug(f"[DEBUG] Veri yolu bulundu (Fuzzy Match): {folder.absolute()}")
                return folder.name

        # Bulunamadıysa varsayılan
        default_path = self._symbol_to_path(symbol)
        logger.debug(f"[DEBUG] Veri yolu diskte bulunamadı, varsayılan kullanılacak: {(base_dir / default_path).absolute()}")
        return default_path


    def _get_base_path(self, symbol: str, timeframe: str) -> Path:
        """
        Sembol ve timeframe için base path al. (Deep Path Discovery ile)

        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi

        Returns:
            Base path
        """
        symbol_path = self._find_actual_symbol_path(symbol)
        return self.BASE_DIR / self.exchange / symbol_path / timeframe

    def _get_partition_path(self, symbol: str, timeframe: str, date: datetime) -> Path:
        """
        Belirli bir tarih için partition path al.

        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi
            date: Tarih

        Returns:
            Partition path
        """
        base_path = self._get_base_path(symbol, timeframe)

        if self._is_intraday(timeframe):
            # Gün bazlı partition: YYYY/MM/DD/data.parquet
            return base_path / f"{date.year:04d}" / f"{date.month:02d}" / f"{date.day:02d}" / "data.parquet"
        else:
            # Tek dosya: market.parquet
            return base_path / "market.parquet"

    async def _get_lock(self, symbol: str, timeframe: str) -> asyncio.Lock:
        """
        Symbol+timeframe için lock al (race condition koruması).

        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi

        Returns:
            asyncio.Lock
        """
        key = f"{symbol}:{timeframe}"

        async with self._global_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    def _write_parquet_thread(self, df: pd.DataFrame, path: Path):
        """
        Parquet yazma işlemi (thread'de çalışır).

        Args:
            df: DataFrame
            path: Dosya yolu
        """
        # Dizin oluştur
        path.parent.mkdir(parents=True, exist_ok=True)

        # DataFrame'i hazırla
        write_df = df.copy()

        # Timestamp kolonunu kontrol et
        if 'timestamp' in write_df.columns:
            if write_df['timestamp'].dtype == 'object':
                write_df['timestamp'] = pd.to_datetime(write_df['timestamp'], utc=True)

        # Index'i timestamp'e ayarla (eğer değilse)
        if not isinstance(write_df.index, pd.DatetimeIndex):
            if 'timestamp' in write_df.columns:
                write_df = write_df.set_index('timestamp')

        # NaN temizliği
        write_df = write_df.dropna(how='all')

        # Parquet olarak kaydet
        write_df.to_parquet(
            path,
            compression=self.COMPRESSION,
            index=True,  # DatetimeIndex'i kaydet
            engine='pyarrow' if PYARROW_AVAILABLE else 'auto'
        )

        logger.debug(f"💾 [PARQUET] {path.relative_to(self.BASE_DIR)} kaydedildi ({len(write_df)} satır)")

    def _read_parquet_thread(self, path: Path, columns: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
        """
        Parquet okuma işlemi (thread'de çalışır). (Zero-Copy LazyFrame)

        Args:
            path: Dosya yolu
            columns: Okunacak kolonlar (opsiyonel)

        Returns:
            DataFrame veya None
        """
        if not path.exists():
            return None

        try:
            lf = pl.scan_parquet(path)

            if columns:
                available_cols = lf.collect_schema().names()

                # İndeks olarak kullanılacak timestamp kolonunu her ihtimale karşı dahil et
                ts_cols = [c for c in ['timestamp', 'time', 'date'] if c in available_cols]

                cols_to_select = list(set(columns))
                for ts_col in ts_cols:
                    if ts_col not in cols_to_select:
                        cols_to_select.append(ts_col)

                valid_cols = [c for c in cols_to_select if c in available_cols]
                if valid_cols:
                    lf = lf.select(valid_cols)

            df = lf.collect().to_pandas()

            if df.empty:
                return None

            # Index'i DatetimeIndex'e çevir
            if not isinstance(df.index, pd.DatetimeIndex):
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                    df = df.set_index('timestamp')
                elif 'time' in df.columns:
                    df['time'] = pd.to_datetime(df['time'], utc=True)
                    df = df.set_index('time')

            logger.debug(f"📖 [PARQUET] {path.relative_to(self.BASE_DIR)} okundu ({len(df)} satır)")
            return df

        except Exception as e:
            logger.warning(f"⚠️ [PARQUET] Okuma hatası: {path} - {e}")
            return None

    async def save(self, symbol: str, timeframe: str, df: pd.DataFrame, append: bool = True):
        """
        Veriyi Parquet dosyasına kaydet (asenkron, thread-safe).

        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi
            df: DataFrame (OHLCV verisi)
            append: Mevcut dosyaya ekle (True) veya üzerine yaz (False)
        """
        if df.empty:
            logger.warning(f"⚠️ [PARQUET] Boş veri kaydedilmedi: {symbol} {timeframe}")
            return

        # Lock al
        lock = await self._get_lock(symbol, timeframe)

        async with lock:
            try:
                if self._is_intraday(timeframe):
                    # Gün bazlı partition - her gün için ayrı dosya
                    # DataFrame'i gün gün grupla
                    if not isinstance(df.index, pd.DatetimeIndex):
                        if 'timestamp' in df.columns:
                            df = df.copy()
                            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                            df = df.set_index('timestamp')
                        else:
                            logger.error(f"❌ [PARQUET] timestamp kolonu yok: {symbol} {timeframe}")
                            return

                    # Her gün için ayrı kaydet
                    for date, day_df in df.groupby(df.index.date):
                        date_obj = pd.to_datetime(date)
                        partition_path = self._get_partition_path(symbol, timeframe, date_obj)

                        if append and partition_path.exists():
                            # Mevcut dosyaya ekle (async fonksiyon - doğrudan await)
                            existing_df = await asyncio.to_thread(self._read_parquet_thread, partition_path)
                            if existing_df is not None and not existing_df.empty:
                                # ⏰ TIMEZONE STANDARDIZASYONU (UTC'ye zorla)
                                if existing_df.index.tzinfo is None:
                                    existing_df.index = existing_df.index.tz_localize('UTC')
                                else:
                                    existing_df.index = existing_df.index.tz_convert('UTC')

                                if day_df.index.tzinfo is None:
                                    day_df.index = day_df.index.tz_localize('UTC')
                                else:
                                    day_df.index = day_df.index.tz_convert('UTC')

                                # Artık her ikisi de UTC - güvenle birleştir
                                combined_df = pd.concat([existing_df, day_df])
                                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                                combined_df.sort_index(inplace=True)
                                day_df = combined_df

                        # Yazma işlemi senkron - asyncio.to_thread ile await
                        try:
                            await asyncio.to_thread(self._write_parquet_thread, day_df, partition_path)
                        except ImportError as ie:
                            # PyArrow/fastparquet eksik, uyarı ver ama devam et
                            logger.warning(f"⚠️ [PARQUET] PyArrow/fastparquet eksik, parquet kaydedilemedi: {ie}")
                            logger.warning("⚠️ [PARQUET] ML eğitimi SQLite'dan devam edecek")
                            # Parquet kaydedilemedi ama işlem devam etsin
                            pass
                        except Exception as e:
                            logger.error(f"❌ [PARQUET] Kaydetme hatası: {symbol} {timeframe} - {e}")
                            raise  # Başka hataları yükselt

                    logger.info(f"✅ [PARQUET] {symbol} {timeframe} → {len(df.groupby(df.index.date))} gün kaydedildi")

                else:
                    # Tek dosya (market.parquet)
                    partition_path = self._get_partition_path(symbol, timeframe, datetime.now())

                    if append and partition_path.exists():
                        # Mevcut dosyaya ekle (async fonksiyon - doğrudan await)
                        existing_df = await asyncio.to_thread(self._read_parquet_thread, partition_path)
                        if existing_df is not None and not existing_df.empty:
                            # ⏰ TIMEZONE STANDARDIZASYONU (UTC'ye zorla)
                            if existing_df.index.tzinfo is None:
                                existing_df.index = existing_df.index.tz_localize('UTC')
                            else:
                                existing_df.index = existing_df.index.tz_convert('UTC')

                            if df.index.tzinfo is None:
                                df.index = df.index.tz_localize('UTC')
                            else:
                                df.index = df.index.tz_convert('UTC')

                            # Artık her ikisi de UTC - güvenle birleştir
                            combined_df = pd.concat([existing_df, df])
                            combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
                            combined_df.sort_index(inplace=True)
                            df = combined_df

                    # Yazma işlemi senkron - asyncio.to_thread ile await
                    await asyncio.to_thread(self._write_parquet_thread, df, partition_path)
                    logger.info(f"✅ [PARQUET] {symbol} {timeframe} → market.parquet kaydedildi ({len(df)} satır)")

            except Exception as e:
                logger.error(f"❌ [PARQUET] Kaydetme hatası: {symbol} {timeframe} - {e}")
                raise

    async def load_datasets(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        columns: Optional[List[str]] = None
    ) -> Optional[pd.DataFrame]:
        """
        Vektörize okuma - tarih aralığındaki tüm partition'ları oku ve birleştir. (LazyFrame)

        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi
            columns: Sadece okunacak kolonlar (Predicate Pushdown / Column Pruning)

        Returns:
            Birleştirilmiş DataFrame veya None
        """
        # Ensure start_date and end_date are tz-naive for directory comparison
        if start_date is not None and start_date.tzinfo is not None:
            start_date = start_date.replace(tzinfo=None)
        if end_date is not None and end_date.tzinfo is not None:
            end_date = end_date.replace(tzinfo=None)

        try:
            if self._is_intraday(timeframe):
                # Gün bazlı partition - tüm YYYY/MM/DD/data.parquet dosyalarını bul
                base_path = self._get_base_path(symbol, timeframe)

                if not base_path.exists():
                    logger.debug(f"⏭️ [PARQUET] Base path yok: {base_path}")
                    return None

                # Tüm data.parquet dosyalarını bul
                parquet_files: List[Path] = []

                for year_dir in base_path.glob("*/"):
                    if not year_dir.is_dir():
                        continue
                    year = int(year_dir.name)

                    if (start_date and year < start_date.year) or (end_date and year > end_date.year):
                        continue

                    for month_dir in year_dir.glob("*/"):
                        if not month_dir.is_dir():
                            continue
                        month = int(month_dir.name)

                        month_start = datetime(year, month, 1)
                        month_end = month_start + timedelta(days=32)
                        month_end = month_end.replace(day=1) - timedelta(days=1)

                        if (start_date and month_end < start_date) or (end_date and month_start > end_date):
                            continue

                        for day_dir in month_dir.glob("*/"):
                            if not day_dir.is_dir():
                                continue

                            day = int(day_dir.name)
                            file_path = day_dir / "data.parquet"

                            if file_path.exists():
                                file_date = datetime(year, month, day)

                                if (start_date is None or start_date <= file_date) and (end_date is None or file_date <= end_date):
                                    parquet_files.append(file_path)

                if not parquet_files:
                    logger.debug(f"⏭️ [PARQUET] Partition bulunamadı: {symbol} {timeframe}")
                    return None

                def _load_lazy_concat(files: List[Path], cols: Optional[List[str]]) -> Optional[pd.DataFrame]:
                    try:
                        # pl.scan_parquet liste kabul edebilir ve concat edebilir
                        lf = pl.scan_parquet([str(p) for p in files])

                        if cols:
                            schema_cols = lf.collect_schema().names()
                            ts_cols = [c for c in ['timestamp', 'time', 'date'] if c in schema_cols]
                            cols_to_select = list(set(cols))
                            for ts_col in ts_cols:
                                if ts_col not in cols_to_select:
                                    cols_to_select.append(ts_col)

                            valid_cols = [c for c in cols_to_select if c in schema_cols]
                            if valid_cols:
                                lf = lf.select(valid_cols)

                        df_res = lf.collect().to_pandas()
                        return df_res
                    except Exception as e:
                        logger.error(f"❌ [PARQUET] Lazy concat hatası: {e}")
                        return None

                combined_df = await asyncio.to_thread(_load_lazy_concat, parquet_files, columns)

                if combined_df is None or combined_df.empty:
                    return None

                if not isinstance(combined_df.index, pd.DatetimeIndex):
                    if 'timestamp' in combined_df.columns:
                        combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'], utc=True)
                        combined_df = combined_df.set_index('timestamp')
                    elif 'time' in combined_df.columns:
                        combined_df['time'] = pd.to_datetime(combined_df['time'], utc=True)
                        combined_df = combined_df.set_index('time')

                # ⏰ TIMEZONE STANDARDIZASYONU (UTC'ye zorla)
                if combined_df.index.tzinfo is None:
                    combined_df.index = combined_df.index.tz_localize('UTC')
                else:
                    combined_df.index = combined_df.index.tz_convert('UTC')

                start_ts = None if start_date is None else (pd.Timestamp(start_date, tz='UTC') if start_date.tzinfo is None else pd.Timestamp(start_date).tz_convert('UTC'))
                end_ts = None if end_date is None else (pd.Timestamp(end_date, tz='UTC') if end_date.tzinfo is None else pd.Timestamp(end_date).tz_convert('UTC'))

                # Tarih aralığını filtrele
                if start_ts is not None:
                    combined_df = combined_df[combined_df.index >= start_ts]
                if end_ts is not None:
                    combined_df = combined_df[combined_df.index <= end_ts]

                # Duplicate temizliği
                combined_df = combined_df[~combined_df.index.duplicated(keep='last')]

                # Sırala
                combined_df = combined_df.sort_index()

                logger.info(f"📖 [PARQUET] {symbol} {timeframe} → {len(parquet_files)} dosya, {len(combined_df)} satır")
                return combined_df

            else:
                # Tek dosya (market.parquet)
                partition_path = self._get_partition_path(symbol, timeframe, datetime.now())

                if not partition_path.exists():
                    logger.debug(f"⏭️ [PARQUET] Market dosyası yok: {partition_path}")
                    return None

                df = await asyncio.to_thread(self._read_parquet_thread, partition_path, columns)

                if df is None or df.empty:
                    return None

                # ⏰ TIMEZONE STANDARDIZASYONU (UTC'ye zorla)
                if df.index.tzinfo is None:
                    df.index = df.index.tz_localize('UTC')
                else:
                    df.index = df.index.tz_convert('UTC')

                start_ts = None if start_date is None else (pd.Timestamp(start_date, tz='UTC') if start_date.tzinfo is None else pd.Timestamp(start_date).tz_convert('UTC'))
                end_ts = None if end_date is None else (pd.Timestamp(end_date, tz='UTC') if end_date.tzinfo is None else pd.Timestamp(end_date).tz_convert('UTC'))

                # Tarih aralığını filtrele
                if start_ts is not None:
                    df = df[df.index >= start_ts]
                if end_ts is not None:
                    df = df[df.index <= end_ts]

                logger.info(f"📖 [PARQUET] {symbol} {timeframe} → {len(df)} satır")
                return df

        except Exception as e:
            logger.error(f"❌ [PARQUET] Yükleme hatası: {symbol} {timeframe} - {e}")
            return None

    async def stream_datasets(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        batch_size: int = 50000
    ):
        """
        ASENKRON STREAM - OOM Koruması (PyArrow batches)

        Geriye dönük testler için veriyi chunk'lar halinde yield eder.
        pd.concat yerine iter_batches kullanarak RAM'i korur.

        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi
            batch_size: Her seferinde kaç satır (default: 50,000)

        Yields:
            pd.DataFrame: Her batch için DataFrame
        """
        # Ensure start_date and end_date are tz-naive for directory comparison
        if start_date is not None and start_date.tzinfo is not None:
            start_date = start_date.replace(tzinfo=None)
        if end_date is not None and end_date.tzinfo is not None:
            end_date = end_date.replace(tzinfo=None)

        try:
            if self._is_intraday(timeframe):
                # Gün bazlı partition - tüm dosyaları bul
                base_path = self._get_base_path(symbol, timeframe)

                if not base_path.exists():
                    logger.debug(f"⏭️ [STREAM] Base path yok: {base_path}")
                    return

                # Tüm data.parquet dosyalarını bul (sıralı)
                parquet_files: List[Path] = []

                for year_dir in sorted(base_path.glob("*/")):
                    if not year_dir.is_dir():
                        continue
                    year = int(year_dir.name)

                    if (start_date and year < start_date.year) or (end_date and year > end_date.year):
                        continue

                    for month_dir in sorted(year_dir.glob("*/")):
                        if not month_dir.is_dir():
                            continue
                        month = int(month_dir.name)

                        month_start = datetime(year, month, 1)
                        month_end = month_start + timedelta(days=32)
                        month_end = month_end.replace(day=1) - timedelta(days=1)

                        if (start_date and month_end < start_date) or (end_date and month_start > end_date):
                            continue

                        for day_dir in sorted(month_dir.glob("*/")):
                            if not day_dir.is_dir():
                                continue

                            day = int(day_dir.name)
                            file_path = day_dir / "data.parquet"

                            if file_path.exists():
                                file_date = datetime(year, month, day)

                                if (start_date is None or start_date <= file_date) and (end_date is None or file_date <= end_date):
                                    parquet_files.append(file_path)

                if not parquet_files:
                    logger.debug(f"⏭️ [STREAM] Partition bulunamadı: {symbol} {timeframe}")
                    return

                logger.info(f"📚 [STREAM] {symbol} {timeframe} → {len(parquet_files)} dosya, batch_size={batch_size}")

                # Her dosyayı stream et (PyArrow iter_batches)
                for file_path in parquet_files:
                    try:
                        # PyArrow ile aç (memory-mapped)
                        parquet_file = pq.ParquetFile(file_path)

                        start_ts = None if start_date is None else (pd.Timestamp(start_date, tz='UTC') if start_date.tzinfo is None else pd.Timestamp(start_date).tz_convert('UTC'))
                        end_ts = None if end_date is None else (pd.Timestamp(end_date, tz='UTC') if end_date.tzinfo is None else pd.Timestamp(end_date).tz_convert('UTC'))

                        # Batches halinde oku (50k satır)
                        for batch in parquet_file.iter_batches(batch_size=batch_size):
                            df_batch = batch.to_pandas()

                            # ⏰ TIMEZONE STANDARDIZASYONU (UTC'ye zorla)
                            if df_batch.index.tzinfo is None:
                                df_batch.index = df_batch.index.tz_localize('UTC')
                            else:
                                df_batch.index = df_batch.index.tz_convert('UTC')

                            # Tarih aralığını filtrele
                            if start_ts is not None:
                                df_batch = df_batch[df_batch.index >= start_ts]
                            if end_ts is not None:
                                df_batch = df_batch[df_batch.index <= end_ts]

                            if not df_batch.empty:
                                yield df_batch

                    except Exception as e:
                        logger.warning(f"⚠️ [STREAM] Dosya okuma hatası: {file_path} - {e}")
                        continue

            else:
                # Tek dosya (market.parquet)
                partition_path = self._get_partition_path(symbol, timeframe, datetime.now())

                if not partition_path.exists():
                    logger.debug(f"⏭️ [STREAM] Market dosyası yok: {partition_path}")
                    return

                # PyArrow ile aç
                parquet_file = pq.ParquetFile(partition_path)

                start_ts = None if start_date is None else (pd.Timestamp(start_date, tz='UTC') if start_date.tzinfo is None else pd.Timestamp(start_date).tz_convert('UTC'))
                end_ts = None if end_date is None else (pd.Timestamp(end_date, tz='UTC') if end_date.tzinfo is None else pd.Timestamp(end_date).tz_convert('UTC'))

                # Batches halinde oku
                for batch in parquet_file.iter_batches(batch_size=batch_size):
                    df_batch = batch.to_pandas()

                    # ⏰ TIMEZONE STANDARDIZASYONU (UTC'ye zorla)
                    if df_batch.index.tzinfo is None:
                        df_batch.index = df_batch.index.tz_localize('UTC')
                    else:
                        df_batch.index = df_batch.index.tz_convert('UTC')

                    # Tarih aralığını filtrele
                    if start_ts is not None:
                        df_batch = df_batch[df_batch.index >= start_ts]
                    if end_ts is not None:
                        df_batch = df_batch[df_batch.index <= end_ts]

                    if not df_batch.empty:
                        yield df_batch

                logger.info(f"📚 [STREAM] {symbol} {timeframe} → Stream tamamlandı")

        except Exception as e:
            logger.error(f"❌ [STREAM] Hata: {symbol} {timeframe} - {e}")
            return

    async def exists(self, symbol: str, timeframe: str) -> bool:
        """
        Veri var mı kontrol et.

        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi

        Returns:
            True/False
        """
        base_path = self._get_base_path(symbol, timeframe)

        if not base_path.exists():
            return False

        if self._is_intraday(timeframe):
            # En az bir data.parquet dosyası var mı?
            return len(list(base_path.rglob("data.parquet"))) > 0
        else:
            # market.parquet var mı?
            return (base_path / "market.parquet").exists()

    async def delete(self, symbol: str, timeframe: str = None, start_date: datetime = None, end_date: datetime = None):
        """
        Veriyi sil.

        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi (None ise TÜM timeframe'ler)
            start_date: Başlangıç tarihi (None ise tümü)
            end_date: Bitiş tarihi (None ise tümü)
        """
        if start_date and start_date.tzinfo is not None:
            start_date = start_date.replace(tzinfo=None)
        if end_date and end_date.tzinfo is not None:
            end_date = end_date.replace(tzinfo=None)

        # Eğer timeframe None ise, TÜM timeframe'leri sil
        if timeframe is None:
            logger.info(f"🗑️ [PARQUET] {symbol} için TÜM timeframe'ler siliniyor...")

            # TÜM sembol varyasyonlarını dene (path formatları)
            symbol_variants = [
                symbol.replace(':', '_').replace('/', '_'),  # BTC/USDT:USDT → BTC_USDT_USDT
                symbol.replace(':', '_'),  # BTC/USDT:USDT → BTC/USDT_USDT (nested)
                symbol.replace('/', '_'),  # BTC/USDT → BTC_USDT
            ]

            # Duplicate'ları temizle
            symbol_variants = list(dict.fromkeys(symbol_variants))

            deleted_any = False
            for symbol_variant in symbol_variants:
                base_path = self.BASE_DIR / self.exchange / symbol_variant

                if base_path.exists():
                    logger.info(f"   - Deneniyor: {base_path}")
                    import shutil
                    try:
                        shutil.rmtree(base_path)
                        logger.info(f"🗑️ [PARQUET] {base_path.relative_to(self.BASE_DIR)} silindi")
                        deleted_any = True
                    except Exception as e:
                        logger.error(f"❌ [PARQUET] Silme hatası ({base_path}): {e}")

            if not deleted_any:
                logger.warning(f"⚠️ [PARQUET] Silinecek veri bulunamadı: {symbol}")
            return

        # Belirli bir timeframe sil
        lock = await self._get_lock(symbol, timeframe)

        async with lock:
            try:
                base_path = self._get_base_path(symbol, timeframe)

                if not base_path.exists():
                    logger.warning(f"⚠️ [PARQUET] Silinecek veri yok: {symbol} {timeframe}")
                    return

                deleted_count = 0

                if self._is_intraday(timeframe):
                    # Gün bazlı partition
                    if start_date and end_date:
                        # Belirli tarih aralığını sil
                        for year_dir in base_path.glob("*/"):
                            for month_dir in year_dir.glob("*/"):
                                for day_dir in month_dir.glob("*/"):
                                    file_path = day_dir / "data.parquet"
                                    if file_path.exists():
                                        file_date = pd.to_datetime(f"{year_dir.name}-{month_dir.name}-{day_dir.name}")
                                        if (start_date is None or start_date <= file_date) and (end_date is None or file_date <= end_date):
                                            file_path.unlink()
                                            deleted_count += 1
                                            logger.debug(f"🗑️ [PARQUET] {file_path.relative_to(self.BASE_DIR)} silindi")
                    else:
                        # Tüm partition'ları sil
                        import shutil
                        shutil.rmtree(base_path)
                        logger.info(f"🗑️ [PARQUET] {symbol} {timeframe} → TÜM partition'lar silindi")
                        return

                else:
                    # Tek dosya
                    partition_path = base_path / "market.parquet"
                    if partition_path.exists():
                        if start_date and end_date:
                            # Tarih aralığındaki satırları sil
                            df = await asyncio.to_thread(self._read_parquet_thread, partition_path)
                            if df is not None:
                                mask = (
                                    (df.index < pd.Timestamp(start_date, tz='UTC')) |
                                    (df.index > pd.Timestamp(end_date, tz='UTC'))
                                )
                                df = df[mask]

                                if df.empty:
                                    partition_path.unlink()
                                    deleted_count = 1
                                    logger.info(f"🗑️ [PARQUET] {symbol} {timeframe} → market.parquet silindi (boş)")
                                else:
                                    await asyncio.to_thread(self._write_parquet_thread, df, partition_path)
                                    logger.info(f"🗑️ [PARQUET] {symbol} {timeframe} → market.parquet güncellendi")
                        else:
                            # Tüm dosyayı sil
                            partition_path.unlink()
                            deleted_count = 1
                            logger.info(f"🗑️ [PARQUET] {symbol} {timeframe} → market.parquet silindi")

                if deleted_count > 0:
                    logger.info(f"🗑️ [PARQUET] {symbol} {timeframe} → {deleted_count} dosya silindi")

            except Exception as e:
                logger.error(f"❌ [PARQUET] Silme hatası: {symbol} {timeframe} - {e}")
                raise

    def get_stats(self, symbol: str = None) -> Dict[str, Any]:
        """
        Data Lake istatistiklerini al.

        Args:
            symbol: Sembol adı (None ise tümü)

        Returns:
            İstatistikler dict
        """
        stats = {
            'total_symbols': 0,
            'total_timeframes': 0,
            'total_files': 0,
            'total_size_mb': 0,
            'total_rows': 0,
            'symbols': {}
        }

        base_dir = self.BASE_DIR / self.exchange

        if not base_dir.exists():
            return stats

        for symbol_dir in base_dir.iterdir():
            if not symbol_dir.is_dir():
                continue

            # [SYMBOL FIX] Klasör adını normalize et (örn: /BTC_USDT_USDT → BTC/USDT:USDT)
            # symbol_raw = symbol_dir.name.replace('_', '/') # Bu satır BTC/USDT/USDT ürettiği için CCXT ValueError veriyordu
            symbol_raw = symbol_dir.name
            from core.exchange import normalize_symbol
            symbol = normalize_symbol(symbol_raw)

            stats['total_symbols'] += 1
            stats['symbols'][symbol] = {
                'timeframes': 0,
                'files': 0,
                'size_mb': 0,
                'total_rows': 0
            }

            for tf_dir in symbol_dir.iterdir():
                if not tf_dir.is_dir():
                    continue

                stats['total_timeframes'] += 1
                stats['symbols'][symbol]['timeframes'] += 1

                for file_path in tf_dir.rglob("*.parquet"):
                    stats['total_files'] += 1
                    stats['symbols'][symbol]['files'] += 1
                    stats['total_size_mb'] += file_path.stat().st_size / (1024 * 1024)
                    stats['symbols'][symbol]['size_mb'] += file_path.stat().st_size / (1024 * 1024)

                    # Satır sayısı (LazyFrame)
                    if file_path.name == "market.parquet":
                        try:
                            row_count = pl.scan_parquet(file_path).select(pl.len()).collect().item()
                            stats['total_rows'] += row_count
                            stats['symbols'][symbol]['total_rows'] += row_count
                        except Exception:
                            pass

        # Yuvarla
        stats['total_size_mb'] = round(stats['total_size_mb'], 2)
        for symbol_stats in stats['symbols'].values():
            symbol_stats['size_mb'] = round(symbol_stats['size_mb'], 2)

        return stats


# Singleton instance
_lake_instance: Optional[ParquetDataLake] = None

def get_parquet_lake(exchange: str = 'binance') -> ParquetDataLake:
    """
    ParquetDataLake singleton instance'ını al.

    Args:
        exchange: Borsa adı

    Returns:
        ParquetDataLake instance
    """
    global _lake_instance
    if _lake_instance is None or _lake_instance.exchange != exchange:
        _lake_instance = ParquetDataLake(exchange)
    return _lake_instance
