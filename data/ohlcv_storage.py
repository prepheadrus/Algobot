"""
OHLCV Storage - Flat File Management (Legacy Compatibility)

Bu modül, eski flat file sistemine uyumluluk sağlar.
Yeni sistem ParquetDataLake kullanır, ancak bazı modüller
hala ohlcv_storage'a referans veriyor.

Usage:
    from data.ohlcv_storage import get_storage
    storage = get_storage()
    
    # Save OHLCV data
    storage.save_ohlcv('BTC/USDT', '1m', df)
    
    # Load OHLCV data
    df = storage.load_ohlcv('BTC/USDT', '1m', start_date, end_date)
"""

import os
import pandas as pd
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from core.logger import logger


class OHLCVStorage:
    """
    OHLCV Flat File Storage (Legacy Compatibility Layer).
    
    Bu sınıf, eski flat file sistemine uyumluluk sağlar.
    Yeni veri Parquet formatında saklanır, ancak API
    eski flat file formatını taklit eder.
    """
    
    # Base directory
    BASE_DIR = Path("data/ohlcv_flat")
    
    def __init__(self):
        """OHLCV Storage'ı başlat."""
        self.BASE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"📦 [OHLCV_STORAGE] Legacy Flat File Uyumluluk Katmanı Aktif")
        logger.info(f"📁 [OHLCV_STORAGE] Base directory: {self.BASE_DIR.absolute()}")
    
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
        Flat file yolunu al.
        
        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi
        
        Returns:
            Path object
        """
        symbol_path = self._symbol_to_path(symbol)
        return self.BASE_DIR / symbol_path / f"{timeframe}.csv"
    
    def save_ohlcv(self, symbol: str, timeframe: str, df: pd.DataFrame) -> bool:
        """
        OHLCV verisini flat file'a kaydet.
        
        Args:
            symbol: Sembol adı (örn: BTC/USDT)
            timeframe: Zaman dilimi (örn: 1m, 5m, 1h)
            df: DataFrame (timestamp, open, high, low, close, volume kolonları)
        
        Returns:
            bool: Başarılı ise True
        """
        try:
            if df is None or df.empty:
                logger.warning(f"⚠️ [STORAGE] {symbol} {timeframe} için boş DataFrame")
                return False
            
            # Dosya yolunu al
            file_path = self._get_file_path(symbol, timeframe)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # CSV olarak kaydet
            df.to_csv(file_path, index=False)
            logger.debug(f"✅ [STORAGE] {symbol} {timeframe} kaydedildi ({len(df)} satır)")
            return True
            
        except Exception as e:
            logger.error(f"❌ [STORAGE] {symbol} {timeframe} kaydetme hatası: {e}")
            return False
    
    def load_ohlcv(
        self, 
        symbol: str, 
        timeframe: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[pd.DataFrame]:
        """
        OHLCV verisini flat file'dan yükle.
        
        Args:
            symbol: Sembol adı (örn: BTC/USDT)
            timeframe: Zaman dilimi (örn: 1m, 5m, 1h)
            start_date: Başlangıç tarihi (opsiyonel)
            end_date: Bitiş tarihi (opsiyonel)
        
        Returns:
            DataFrame veya None (dosya yoksa)
        """
        try:
            file_path = self._get_file_path(symbol, timeframe)
            
            if not file_path.exists():
                logger.debug(f"📄 [STORAGE] {symbol} {timeframe} flat file bulunamadı")
                return None
            
            # CSV olarak yükle
            df = pd.read_csv(file_path)
            
            # Timestamp'i datetime'a çevir
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
            
            # Tarih aralığı filtresi
            if start_date and end_date:
                mask = (df.index >= start_date) & (df.index <= end_date)
                df = df[mask]
            
            if df.empty:
                logger.debug(f"📄 [STORAGE] {symbol} {timeframe} için tarih aralığında veri yok")
                return None
            
            logger.debug(f"✅ [STORAGE] {symbol} {timeframe} yüklendi ({len(df)} satır)")
            return df
            
        except Exception as e:
            logger.error(f"❌ [STORAGE] {symbol} {timeframe} yükleme hatası: {e}")
            return None
    
    def exists(self, symbol: str, timeframe: str) -> bool:
        """
        Flat file'ın var olup olmadığını kontrol et.
        
        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi
        
        Returns:
            bool: Dosya varsa True
        """
        file_path = self._get_file_path(symbol, timeframe)
        return file_path.exists()
    
    def delete(self, symbol: str, timeframe: str) -> bool:
        """
        Flat file'ı sil.
        
        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi
        
        Returns:
            bool: Başarılı ise True
        """
        try:
            file_path = self._get_file_path(symbol, timeframe)
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"✅ [STORAGE] {symbol} {timeframe} silindi")
                return True
            else:
                logger.debug(f"📄 [STORAGE] {symbol} {timeframe} bulunamadı")
                return False
                
        except Exception as e:
            logger.error(f"❌ [STORAGE] {symbol} {timeframe} silme hatası: {e}")
            return False
    
    def list_symbols(self) -> List[str]:
        """
        Tüm mevcut sembolleri listele.
        
        Returns:
            List[str]: Sembol listesi
        """
        symbols = []
        
        if self.BASE_DIR.exists():
            for symbol_dir in self.BASE_DIR.iterdir():
                if symbol_dir.is_dir():
                    from core.exchange import normalize_symbol
                    symbol_name = normalize_symbol(symbol_dir.name)
                    symbols.append(symbol_name)
        
        return symbols
    
    def list_timeframes(self, symbol: str) -> List[str]:
        """
        Bir sembol için mevcut timeframe'leri listele.
        
        Args:
            symbol: Sembol adı
        
        Returns:
            List[str]: Timeframe listesi
        """
        timeframes = []
        symbol_path = self._symbol_to_path(symbol)
        symbol_dir = self.BASE_DIR / symbol_path
        
        if symbol_dir.exists():
            for file in symbol_dir.iterdir():
                if file.suffix == '.csv':
                    timeframe = file.stem  # 1m, 5m, 1h, vb.
                    timeframes.append(timeframe)
        
        return timeframes


# Singleton instance
_storage_instance: Optional[OHLCVStorage] = None


def get_storage() -> OHLCVStorage:
    """
    OHLCV Storage singleton instance'ını al.
    
    Returns:
        OHLCVStorage: Singleton instance
    """
    global _storage_instance
    
    if _storage_instance is None:
        _storage_instance = OHLCVStorage()
    
    return _storage_instance


# Kolay import için
__all__ = ['OHLCVStorage', 'get_storage']
