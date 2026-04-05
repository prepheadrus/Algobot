"""
Strategy Schemas

Pydantic models for strategy-related requests and responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class MarketType(str, Enum):
    """Market type enumeration"""
    SPOT = "spot"
    SWAP = "swap"
    FUTURE = "future"


class MarginType(str, Enum):
    """Margin type enumeration"""
    ISOLATED = "isolated"
    CROSS = "cross"


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class StrategySelectRequest(BaseModel):
    """
    Strateji seçme/değiştirme isteği.
    
    Attributes:
        symbol: Sembol
        strategy_id: Strateji ID (boş ise durdurma)
        timeframe: Zaman dilimi
        market_type: Piyasa tipi
        margin_type: Marjin tipi
    """
    symbol: str = Field(..., description="Sembol")
    strategy_id: Optional[str] = Field(default=None, description="Strateji ID (boş ise durdurma)")
    timeframe: str = Field(default="1m", description="Zaman dilimi")
    market_type: MarketType = Field(default=MarketType.SWAP, description="Piyasa tipi")
    margin_type: MarginType = Field(default=MarginType.ISOLATED, description="Marjin tipi")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTC/USDT",
                "strategy_id": "trend_master",
                "timeframe": "1m",
                "market_type": "future",
                "margin_type": "isolated"
            }
        }


class StrategyRequest(BaseModel):
    """Genel strateji isteği"""
    symbol: str = Field(..., description="Sembol")


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class StrategyInfo(BaseModel):
    """Strateji bilgisi"""
    id: str
    name: str
    description: str
    type: str  # builtin veya custom
    source: str  # python veya json


class StrategyListResponse(BaseModel):
    """Strateji listesi yanıtı"""
    status: str
    strategies: List[StrategyInfo] = []
    message: Optional[str] = None


class StrategySelectResponse(BaseModel):
    """Strateji seçme yanıtı"""
    status: str
    symbol: str
    active_id: Optional[str]
    active_timeframe: str
    market_type: str
    margin_type: str


class StrategyErrorResponse(BaseModel):
    """Strateji hata yanıtı"""
    status: str = "error"
    message: str
