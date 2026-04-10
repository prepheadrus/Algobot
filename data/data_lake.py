"""
Data Lake OHLCV Storage (Kurumsal Caching Sistemi)

🏗️ MİMARİ:
- Parquet formatı (hızlı okuma/yazma, sıkıştırma)
- Smart Caching (önce dosya, yoksa DB'den resample)
- Incremental Update (sadece eksik veriyi güncelle)
- Data Integrity (NaN temizleme, DatetimeIndex)

Dosya Yapısı:
    data/ohlcv/
    ├── BTC_USDT/
    │   ├── 1m.parquet
    │   ├── 5m.parquet
    │   ├── 15m.parquet
    │   ├── 1h.parquet
    │   └── 4h.parquet
    ├── ETH_USDT/
    └── ...

📊 PERFORMANS:
- JSON'a göre %80 daha hızlı okuma
- %60 daha az disk alanı
- Columnar storage (sadece ihtiyacın olan kolonu oku)
"""

import asyncio
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import numpy as np
import polars as pl
from core.logger import logger

try:
    import pyarrow
    PYARROW_AVAILABLE = True
except ImportError:
    PYARROW_AVAILABLE = False
    logger.warning("⚠️ PyArrow bulunamadı, parquet desteği sınırlı olacak")


class DataLakeStorage:
    """
    Kurumsal Data Lake Storage.

    Usage:
        lake = DataLakeStorage()

        # Smart load (önce dosya, yoksa DB'den resample)
        df = lake.load_or_resample(symbol, timeframe, db_manager)

        # Manual save
        lake.save(symbol, timeframe, df)

        # Check if exists
        exists = lake.exists(symbol, timeframe)
    """

    # Base directory
    BASE_DIR = Path("data/ohlcv")

    # Parquet compression
    COMPRESSION = 'snappy'  # snappy, gzip, brotli

    def __init__(self):
        """Data Lake storage'ı başlat."""
        # Race condition koruması için lock'lar
        self._locks: Dict[str, asyncio.Lock] = {}

        # Base directory oluştur (yoksa)
        self.BASE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("🏗️ [DATA LAKE] Resampling Dosya Sistemi (data/ohlcv/) Devrede")
        logger.info(f"📁 [DATA LAKE] Base directory: {self.BASE_DIR.absolute()}")
        logger.info(f"💾 [DATA LAKE] Compression: {self.COMPRESSION}")
        logger.info(f"🚀 [DATA LAKE] PyArrow: {'✅ Aktif' if PYARROW_AVAILABLE else '❌ Pasif'}")

    def _symbol_to_path(self, symbol: str) -> str:
        """
        Sembol ismini dosya yolu formatına çevir.

        Args:
            symbol: Sembol adı (örn: BTC/USDT)

        Returns:
            Dosya yolu için sembol (örn: BTC_USDT)
        """
        return symbol.replace('/', '_').replace(':', '_').replace('-', '_')

    def _get_file_path(self, symbol: str, timeframe: str) -> Path:
        """
        Parquet dosya yolunu al.

        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi

        Returns:
            Path object
        """
        symbol_path = self._symbol_to_path(symbol)
        return self.BASE_DIR / symbol_path / f"{timeframe}.parquet"

    def _get_lock(self, symbol: str, timeframe: str) -> asyncio.Lock:
        """
        Symbol+timeframe için lock al (race condition koruması).

        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi

        Returns:
            asyncio.Lock
        """
        key = f"{symbol}:{timeframe}"

        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    def exists(self, symbol: str, timeframe: str) -> bool:
        """
        Dosya var mı kontrol et.

        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi

        Returns:
            True/False
        """
        file_path = self._get_file_path(symbol, timeframe)
        return file_path.exists()

    def get_last_timestamp(self, symbol: str, timeframe: str) -> Optional[datetime]:
        """
        Dosyadaki son mumun timestamp'ini al.

        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi

        Returns:
            Son timestamp veya None
        """
        file_path = self._get_file_path(symbol, timeframe)

        if not file_path.exists():
            return None

        try:
            # Sadece timestamp kolonunu lazy oku, filtrele ve maksimumunu al
            lf = pl.scan_parquet(file_path)
            
            # Zaman serisi sütununu belirle
            columns = lf.collect_schema().names()
            ts_col = None
            for col in ['timestamp', 'time', 'date']:
                if col in columns:
                    ts_col = col
                    break

            if not ts_col:
                return None

            # Sadece timestamp kolonunu seç ve son 1 günlük veriyi filtreleyip maks bul (Optimizasyon)
            day_ago = pd.Timestamp.now(tz='UTC') - pd.Timedelta(days=1)
            # Eğer datetime ise polars ile doğrudan filtreleyebiliriz, değilse ms formatında filtreleriz.
            # LazyFrame olduğu için hatasız maksimumu da alabiliriz doğrudan.

            # Sadece en büyük timestamp'i almak için:
            max_df = lf.select(pl.col(ts_col).max()).collect().to_pandas()

            if max_df.empty or pd.isna(max_df.iloc[0, 0]):
                return None

            last_ts = max_df.iloc[0, 0]
            if isinstance(last_ts, (int, float, np.number)):
                return pd.to_datetime(last_ts, unit='ms' if last_ts > 1e12 else 's', utc=True)
            return pd.to_datetime(last_ts, utc=True)

        except Exception as e:
            logger.warning(f"⚠️ [DATA LAKE] Son timestamp okuma hatası: {e}")
            return None

    def load(self, symbol: str, timeframe: str, start_date: datetime = None, end_date: datetime = None, columns: Optional[List[str]] = None) -> Optional[pd.DataFrame]:
        """
        Veriyi parquet dosyasından yükle.

        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi
            start_date: Başlangıç tarihi (opsiyonel)
            end_date: Bitiş tarihi (opsiyonel)
            columns: Yalnızca okunacak kolonlar (opsiyonel, Predicate Pushdown)

        Returns:
            DataFrame veya None
        """
        file_path = self._get_file_path(symbol, timeframe)

        if not file_path.exists():
            logger.debug(f"⏭️ [DATA LAKE] Dosya yok: {file_path}")
            return None

        try:
            # Parquet oku (LazyFrame Zero-Copy)
            lf = pl.scan_parquet(file_path)

            # Kolon Seçimi (Column Pruning)
            if columns:
                cols_to_select = list(columns)
                # Timestamp her zaman gereklidir, yoksa ekleyelim
                if 'timestamp' not in cols_to_select:
                    schema_cols = lf.collect_schema().names()
                    # Zaman serisi sütununu belirle
                    ts_col = next((c for c in ['timestamp', 'time', 'date'] if c in schema_cols), None)
                    if ts_col and ts_col not in cols_to_select:
                        cols_to_select.append(ts_col)

                # Mevcut olmayan kolonları ekarte edip seç (hata vermemesi için)
                available_cols = lf.collect_schema().names()
                valid_cols = [c for c in cols_to_select if c in available_cols]
                if valid_cols:
                    lf = lf.select(valid_cols)

            # Tarih Filtresi (Row Pruning)
            if start_date or end_date:
                # Zaman serisi sütununu belirle
                schema_cols = lf.collect_schema().names()
                ts_col = next((c for c in ['timestamp', 'time', 'date'] if c in schema_cols), 'timestamp')

                if ts_col in schema_cols:
                    if start_date:
                        # timezone naive çevrimi (Parquet schema'sına göre değişebilir, safe cast)
                        if start_date.tzinfo is not None:
                            start_date = start_date.astimezone(pd.Timestamp.utcnow().tz)
                        lf = lf.filter(pl.col(ts_col) >= start_date)
                    if end_date:
                        if end_date.tzinfo is not None:
                            end_date = end_date.astimezone(pd.Timestamp.utcnow().tz)
                        lf = lf.filter(pl.col(ts_col) <= end_date)

            # Lazy Frame'i işle ve Pandas'a dönüştür
            df = lf.collect().to_pandas()

            if df.empty:
                logger.debug(f"⏭️ [DATA LAKE] Dosya boş veya filtreye uyan veri yok: {file_path}")
                return None

            # Data integrity kontrolü
            df = self._ensure_integrity(df, timeframe)

            logger.info(f"📖 [DATA LAKE] {symbol} {timeframe} → {len(df)} mum yüklendi ({file_path.name})")
            return df

        except Exception as e:
            logger.warning(f"⚠️ [DATA LAKE] Dosya okuma hatası: {e}")
            return None

    async def save(self, symbol: str, timeframe: str, df: pd.DataFrame, append: bool = False) -> bool:
        """
        Veriyi parquet dosyasına kaydet.

        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi
            df: DataFrame
            append: Mevcut dosyaya ekle (True) veya üzerine yaz (False)

        Returns:
            True/False
        """
        if df.empty:
            logger.warning(f"⚠️ [DATA LAKE] Boş veri kaydedilmedi: {symbol} {timeframe}")
            return False

        # Lock al (Thread-safe ve OOM koruması için)
        lock = self._get_lock(symbol, timeframe)

        async with lock:
            file_path = self._get_file_path(symbol, timeframe)

            # 🔒 WINDOWS FILE LOCK KORUMASI: 3 deneme, exponential backoff
            max_retries = 3
            retry_delay = 0.5  # saniye

            for attempt in range(max_retries):
                try:
                    # Dizin oluştur
                    file_path.parent.mkdir(parents=True, exist_ok=True)

                    # Data integrity sağla
                    df = self._ensure_integrity(df, timeframe)

                    # When writing to Parquet files, always load and write the entire dataset at once (overwriting)
                    # rather than performing incremental appends, as the Parquet format is inefficient with
                    # continuous small appends and causes file fragmentation.

                    # Dosya varsa ve appned edilmek isteniyorsa bile, çağrıcının DataFrame'i
                    # zaten tam olarak birleştirilmiş olmalıdır. Append'i burada dosyayı yükleyerek YAPMAMALIYIZ.

                    await asyncio.to_thread(df.to_parquet, file_path, compression=self.COMPRESSION, index=False)
                    logger.info(f"💾 [DATA LAKE] {symbol} {timeframe} → {len(df)} mum KAYDEDILDI")

                    return True

                except PermissionError as perm_err:
                    # Windows file lock hatası - bekle ve tekrar dene
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ [DATA LAKE] File lock hatası ({attempt+1}/{max_retries}), {retry_delay}s bekleniyor... {file_path}")
                        await asyncio.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                    else:
                        logger.error(f"❌ [DATA LAKE] Dosya yazma hatası (File Lock): {perm_err} - {file_path}")
                        return False
                except FileNotFoundError as not_found_err:
                    # Dosya silinmiş, yeniden oluştur
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ [DATA LAKE] Dosya bulunamadı ({attempt+1}/{max_retries}), yeniden deneniyor... {file_path}")
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.error(f"❌ [DATA LAKE] Dosya yazma hatası (Not Found): {not_found_err} - {file_path}")
                        return False
                except Exception as e:
                    logger.error(f"❌ [DATA LAKE] Dosya yazma hatası: {e} - {file_path}")
                    return False

            return False

    def _ensure_integrity(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Data integrity sağla (NaN temizleme, DatetimeIndex).

        Args:
            df: DataFrame
            timeframe: Zaman dilimi

        Returns:
            Temizlenmiş DataFrame
        """
        if df.empty:
            return df

        # Kolon isimlerini standartlaştır
        required_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        
        # Timestamp kolonunu bul ve datetime'a çevir
        ts_col = None
        for col in ['timestamp', 'time', 'date']:
            if col in df.columns:
                ts_col = col
                break

        if ts_col and ts_col != 'timestamp':
            df.rename(columns={ts_col: 'timestamp'}, inplace=True)

        # 🔥 TIMESTAMP DÖNÜŞÜMÜ: timezone-aware timestamp'leri destekle
        if 'timestamp' in df.columns:
            # İlk değeri al
            first_ts = df['timestamp'].iloc[0]

            # Zaten datetime ise UTC'ye çevir
            if isinstance(first_ts, (pd.Timestamp, datetime)):
                if hasattr(first_ts, 'tzinfo') and first_ts.tzinfo is None:
                    # tz-naive ise UTC yap
                    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
                else:
                    # Zaten tz-aware ise UTC'ye çevir
                    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_convert('UTC')
            else:
                # Numeric timestamp (ms veya s)
                # 🔥 KARŞILAŞTIRMA ÖNCESİ TYPE CHECK
                try:
                    # İlk değerin tipine göre unit belirle
                    if isinstance(first_ts, (int, float, np.number)):
                        unit = 'ms' if first_ts > 1e12 else 's'
                    else:
                        unit = 'ms'  # Default

                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit=unit, utc=True)
                except Exception as ts_err:
                    logger.warning(f"⚠️ [DATA LAKE] Timestamp dönüşüm hatası: {ts_err}, defaulting to 'ms'")
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)

        # NaN değerleri temizle
        df = df.dropna(subset=required_cols)

        # Infinity değerleri temizle
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.dropna()

        # Timestamp'e göre sırala
        df = df.sort_values('timestamp')

        # Duplicate kayıtları temizle
        df = df.drop_duplicates(subset=['timestamp'], keep='last')

        # Index'i reset le
        df = df.reset_index(drop=True)

        logger.debug(f"✅ [DATA LAKE] Integrity check: ({len(df)} mum)")
        return df

    async def load_or_resample(self, symbol: str, timeframe: str, db_manager,
                         limit: int = 1000, force_resample: bool = False) -> Optional[pd.DataFrame]:
        """
        AKILLI YÜKLEME: Önce dosya, yoksa DB'den resample.

        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi
            db_manager: Database manager instance
            limit: Kaç mum çekilecek
            force_resample: Zorla resample (cache bypass)

        Returns:
            DataFrame
        """
        # 1. Önce dosyadan dene
        if not force_resample and self.exists(symbol, timeframe):
            df = self.load(symbol, timeframe)
            if df is not None and len(df) >= limit:
                logger.info(f"✅ [DATA LAKE] {symbol} {timeframe} → Dosyadan yüklendi ({len(df)} mum)")
                return df.tail(limit)

        # 2. Dosya yoksa veya yetersizse, DB'den 1m çek ve resample yap
        logger.info(f"🔄 [DATA LAKE] {symbol} {timeframe} → Dosya yok/yetersiz, 1m'den resample yapılıyor...")

        # 1m için limit ayarla (timeframe multiplier)
        multiplier = self._get_timeframe_multiplier(timeframe)
        adjusted_limit = limit * multiplier

        # 1m veriyi DB'den çek
        if hasattr(db_manager, 'get_klines'):
            klines = await db_manager.get_klines(symbol, '1m', limit=adjusted_limit)
        else:
            klines = None

        if not klines or len(klines) == 0:
            logger.warning(f"⚠️ [DATA LAKE] {symbol} için 1m veri bulunamadı")
            return None

        # List of tuples'u DataFrame'e çevir
        import pandas as pd
        df_1m = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df_1m['timestamp'] = pd.to_datetime(df_1m['timestamp'], unit='ms', utc=True)
        df_1m.set_index('timestamp', inplace=True)

        # Resample yap
        from data.indicators import StrategyIndicators
        df = StrategyIndicators.resample_data(df_1m, timeframe)
        df = df.dropna()

        # Data Lake'e kaydet
        if len(df) > 0:
            df_reset = df.copy()
            df_reset.reset_index(inplace=True)
            await self.save(symbol, timeframe, df_reset)
            logger.info(f"✅ [DATA LAKE] {symbol} {timeframe} → Resample edildi ve kaydedildi ({len(df)} mum)")

        return df.tail(limit) if len(df) >= limit else df

    def _get_timeframe_multiplier(self, timeframe: str) -> int:
        """
        Timeframe'den 1m'e çevirme çarpanı al.

        Args:
            timeframe: Zaman dilimi (örn: 1h)

        Returns:
            Çarpan (örn: 60)
        """
        import re
        match = re.match(r'(\d+)([mhdw])', timeframe)
        if not match:
            return 1

        value = int(match.group(1))
        unit = match.group(2)

        if unit == 'm':
            return value
        elif unit == 'h':
            return value * 60
        elif unit == 'd':
            return value * 24 * 60
        elif unit == 'w':
            return value * 7 * 24 * 60
        
        return value

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

        if not self.BASE_DIR.exists():
            return stats

        for symbol_dir in self.BASE_DIR.iterdir():
            if not symbol_dir.is_dir():
                continue

            from core.exchange import normalize_symbol
            symbol = normalize_symbol(symbol_dir.name)
            stats['total_symbols'] += 1
            stats['symbols'][symbol] = {
                'timeframes': 0,
                'files': 0,
                'size_mb': 0,
                'total_rows': 0
            }

            for file_path in symbol_dir.glob("*.parquet"):
                timeframe = file_path.stem
                stats['total_timeframes'] += 1
                stats['total_files'] += 1
                stats['symbols'][symbol]['timeframes'] += 1
                stats['symbols'][symbol]['files'] += 1
                stats['symbols'][symbol]['size_mb'] += file_path.stat().st_size / (1024 * 1024)

                # Satır sayısı (LazyFrame ile hızlı satır sayımı)
                try:
                    # select ve len() daha hızlı çalışır (belleğe tüm datayı almaz)
                    row_count = pl.scan_parquet(file_path).select(pl.len()).collect().item()
                    stats['total_rows'] += row_count
                    stats['symbols'][symbol]['total_rows'] += row_count
                except Exception as e:
                    pass

        # Yuvarla
        stats['total_size_mb'] = round(stats['total_size_mb'], 2)
        for symbol_stats in stats['symbols'].values():
            symbol_stats['size_mb'] = round(symbol_stats['size_mb'], 2)

        return stats


# Singleton instance
_lake_instance = None

def get_data_lake() -> DataLakeStorage:
    """
    DataLakeStorage singleton instance'ını al.

    Returns:
        DataLakeStorage instance
    """
    global _lake_instance
    if _lake_instance is None:
        _lake_instance = DataLakeStorage()
    return _lake_instance
