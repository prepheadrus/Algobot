"""
Bot Schemas

Pydantic models for bot-related requests and responses.
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


class BotStatusEnum(str, Enum):
    """Bot status enumeration"""
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    ERROR = "error"


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class BotStartRequest(BaseModel):
    """
    Bot başlatma isteği.
    
    Attributes:
        symbol: Sembol (örn: BTC/USDT:USDT)
        strategy_id: Strateji ID
        timeframe: Zaman dilimi (varsayılan: 1m)
        market_type: Piyasa tipi (varsayılan: future)
        margin_type: Marjin tipi (varsayılan: isolated)
    """
    symbol: str = Field(..., description="Sembol (örn: BTC/USDT:USDT)")
    strategy_id: str = Field(..., description="Strateji ID")
    timeframe: str = Field(default="1m", description="Zaman dilimi")
    market_type: MarketType = Field(default=MarketType.SWAP, description="Piyasa tipi")
    margin_type: MarginType = Field(default=MarginType.ISOLATED, description="Marjin tipi")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTC/USDT:USDT",
                "strategy_id": "trend_master",
                "timeframe": "1m",
                "market_type": "future",
                "margin_type": "isolated"
            }
        }


class BotStopRequest(BaseModel):
    """
    Bot durdurma isteği.
    
    Attributes:
        bot_id: Bot ID
        action: Aksiyon (varsayılan: stop)
    """
    bot_id: str = Field(..., description="Bot ID")
    action: str = Field(default="stop", description="Aksiyon")
    
    class Config:
        json_schema_extra = {
            "example": {
                "bot_id": "BTC/USDT:USDT_trend_master_1m_1",
                "action": "stop"
            }
        }


class BotResumeRequest(BaseModel):
    """
    Bot devam ettirme isteği.
    
    Attributes:
        bot_id: Bot ID
        action: Aksiyon (varsayılan: resume)
    """
    bot_id: str = Field(..., description="Bot ID")
    action: str = Field(default="resume", description="Aksiyon")


class BotRemoveRequest(BaseModel):
    """
    Bot silme isteği.
    
    Attributes:
        bot_id: Bot ID
    """
    bot_id: str = Field(..., description="Bot ID")


class BotStatusRequest(BaseModel):
    """
    Bot durum sorgulama isteği.
    
    Attributes:
        bot_id: Bot ID
    """
    bot_id: str = Field(..., description="Bot ID")


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class BotInfo(BaseModel):
    """Bot bilgisi"""
    bot_id: str
    symbol: str
    strategy_id: str
    timeframe: str
    market_type: str
    margin_type: str
    status: BotStatusEnum
    pnl: float = 0.0
    margin: float = 0.0
    trades: int = 0
    wins: int = 0


class BotStartResponse(BaseModel):
    """Bot başlatma yanıtı"""
    status: str
    bot_id: str
    message: str


class BotStopResponse(BaseModel):
    """Bot durdurma yanıtı"""
    status: str
    message: str


class BotResumeResponse(BaseModel):
    """Bot devam ettirme yanıtı"""
    status: str
    message: str


class BotRemoveResponse(BaseModel):
    """Bot silme yanıtı"""
    status: str
    message: str


class BotStatusResponse(BaseModel):
    """Bot durum yanıtı"""
    status: str
    bot: Optional[BotInfo] = None
    message: Optional[str] = None


class BotListResponse(BaseModel):
    """Bot listesi yanıtı"""
    status: str
    bots: List[BotInfo] = []
    message: Optional[str] = None


class BotErrorResponse(BaseModel):
    """Bot hata yanıtı"""
    status: str = "error"
    message: str
