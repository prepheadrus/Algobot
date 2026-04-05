"""
Data Schemas

Pydantic models for data-related requests and responses.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class DataDownloadRequest(BaseModel):
    """
    Veri indirme isteği.
    
    Attributes:
        symbol: Sembol
        timeframe: Zaman dilimi (varsayılan: 1m)
        start_date: Başlangıç tarihi (varsayılan: 2024-01-01)
        market_type: Piyasa tipi (varsayılan: future)
    """
    symbol: str = Field(..., description="Sembol")
    timeframe: str = Field(default="1m", description="Zaman dilimi")
    start_date: str = Field(default="2024-01-01", description="Başlangıç tarihi (YYYY-MM-DD)")
    market_type: str = Field(default="future", description="Piyasa tipi")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTC/USDT",
                "timeframe": "1m",
                "start_date": "2024-01-01",
                "market_type": "future"
            }
        }


class DataStopRequest(BaseModel):
    """
    Veri indirme durdurma isteği.
    
    Attributes:
        symbol: Sembol
    """
    symbol: str = Field(..., description="Sembol")


class DataResumeRequest(BaseModel):
    """
    Veri indirme devam ettirme isteği.
    
    Attributes:
        symbol: Sembol
    """
    symbol: str = Field(..., description="Sembol")


class DataDeleteRequest(BaseModel):
    """
    Veri silme isteği.

    Attributes:
        symbol: Sembol
        timeframe: Zaman dilimi (klines silme için) - None ise TÜM timeframe'ler
        market_type: Piyasa tipi (download task silme için)
    """
    symbol: str = Field(..., description="Sembol")
    timeframe: Optional[str] = Field(default=None, description="Zaman dilimi (None ise TÜM timeframe'ler)")
    market_type: Optional[str] = Field(default=None, description="Piyasa tipi")


class DataPauseRequest(BaseModel):
    """
    Veri indirme duraklatma/devam ettirme isteği.
    
    Attributes:
        symbol: Sembol
        action: Aksiyon (pause veya resume)
    """
    symbol: str = Field(..., description="Sembol")
    action: str = Field(default="pause", description="Aksiyon (pause veya resume)")


class HistoryStatusRequest(BaseModel):
    """
    Geçmiş durum sorgulama isteği.
    
    Attributes:
        symbol: Sembol
        timeframe: Zaman dilimi
    """
    symbol: str = Field(..., description="Sembol")
    timeframe: str = Field(default="1m", description="Zaman dilimi")


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class DownloadTask(BaseModel):
    """İndirme görevi"""
    symbol: str
    timeframe: str
    market_type: str
    start_date: str
    status: str
    current_ts: Optional[int] = None
    since: Optional[int] = None


class HistoryStatusResponse(BaseModel):
    """Geçmiş durum yanıtı"""
    symbol: str
    timeframe: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    count_hint: Optional[str] = None
    status: Optional[str] = None


class ActiveDownloadsResponse(BaseModel):
    """Aktif indirmeler yanıtı"""
    status: str
    downloads: Dict[str, DownloadTask] = {}


class DataDownloadResponse(BaseModel):
    """Veri indirme başlatma yanıtı"""
    status: str
    message: str
    task: Optional[DownloadTask] = None


class DataStopResponse(BaseModel):
    """Veri indirme durdurma yanıtı"""
    status: str
    message: str


class DataDeleteResponse(BaseModel):
    """Veri silme yanıtı"""
    status: str
    message: str


class DataPauseResponse(BaseModel):
    """Veri indirme duraklatma yanıtı"""
    status: str
    message: str


class DataErrorResponse(BaseModel):
    """Veri hata yanıtı"""
    status: str = "error"
    message: str


class SymbolsWithDataResponse(BaseModel):
    """Veritabanında verisi olan semboller yanıtı"""
    status: str
    symbols: List[Dict[str, Any]] = []


class TrackedSymbolsResponse(BaseModel):
    """İzlenen semboller yanıtı"""
    symbols: List[str]


class UpdateTrackedSymbolsRequest(BaseModel):
    """İzlenen sembolleri güncelleme isteği"""
    symbols: List[str] = Field(..., description="Sembol listesi")
