"""
Config Schemas

Pydantic models for configuration updates.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional


# ============================================================================
# RISK CONFIG
# ============================================================================

class RiskConfigUpdate(BaseModel):
    """
    Risk ayarları güncelleme isteği.

    Attributes:
        max_risk_per_trade_percent: İşlem başına maksimum risk (%)
        max_leverage: Maksimum kaldıraç
        max_open_positions: Maksimum açık pozisyon
        max_consecutive_losses: Maksimum ardışık kayıp
        kill_switch_enabled: Kill Switch aktif/pasif
    """
    max_risk_per_trade_percent: float = Field(
        default=1.0,
        ge=0.1,
        le=5.0,
        description="İşlem başına maksimum risk (%)"
    )
    max_leverage: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maksimum kaldıraç"
    )
    max_open_positions: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maksimum açık pozisyon"
    )
    max_consecutive_losses: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maksimum ardışık kayıp"
    )
    kill_switch_enabled: bool = Field(
        default=False,
        description="Kill Switch aktif/pasif"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "max_risk_per_trade_percent": 1.0,
                "max_leverage": 10,
                "max_open_positions": 5,
                "max_consecutive_losses": 5,
                "kill_switch_enabled": False
            }
        }


# ============================================================================
# ADVANCED CONFIG
# ============================================================================

class KalmanConfig(BaseModel):
    """Kalman filtresi ayarları"""
    enabled: bool = Field(default=True, description="Kalman filtresi aktif")
    q: float = Field(default=0.001, ge=0.0001, le=0.01, description="Process noise")
    r: float = Field(default=0.1, ge=0.01, le=1.0, description="Measurement noise")


class CandleLockConfig(BaseModel):
    """Mum kapanış kilidi ayarları"""
    enabled: bool = Field(default=True, description="Mum kilidi aktif")
    interval: int = Field(default=1, ge=1, le=5, description="Kontrol aralığı (mum)")


class WFOConfig(BaseModel):
    """Walk-Forward Optimization ayarları"""
    enabled: bool = Field(default=False, description="WFO aktif")
    reoptimize_interval: int = Field(default=168, ge=24, le=720, description="Yeniden optimizasyon aralığı (saat)")
    optimization_metric: str = Field(default="sharpe", description="Optimizasyon metriği")
    train_days: int = Field(default=30, ge=7, le=90, description="Eğitim günü")
    test_days: int = Field(default=7, ge=1, le=30, description="Test günü")


class MLConfig(BaseModel):
    """ML ayarları"""
    enabled: bool = Field(default=True, description="ML aktif")
    confidence_threshold: float = Field(default=0.6, ge=0.3, le=0.9, description="Güven eşiği")


class HTFConfig(BaseModel):
    """High Timeframe ayarları"""
    enabled: bool = Field(default=True, description="HTF aktif")
    ema_fast: int = Field(default=20, ge=5, le=50, description="Hızlı EMA")
    ema_slow: int = Field(default=50, ge=20, le=200, description="Yavaş EMA")


class BotConfigUpdate(BaseModel):
    """Genel bot ayarları güncelleme isteği"""
    environment: str = Field(default="development", description="Ortam (development/production)")
    exchange: str = Field(default="binance", description="Borsa")
    log_level: str = Field(default="INFO", description="Log seviyesi")


class AdvancedConfigUpdate(BaseModel):
    """
    Gelişmiş ayarlar güncelleme isteği.
    """
    wfo: Optional[WFOConfig] = None
    ml: Optional[MLConfig] = None
    htf: Optional[HTFConfig] = None
    kalman: Optional[KalmanConfig] = None
    candle_lock: Optional[CandleLockConfig] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "wfo": {"enabled": False, "reoptimize_interval": 168},
                "ml": {"enabled": True, "confidence_threshold": 0.6},
                "htf": {"enabled": True, "ema_fast": 20, "ema_slow": 50},
                "kalman": {"enabled": True, "q": 0.001, "r": 0.1},
                "candle_lock": {"enabled": True, "interval": 1}
            }
        }


# ============================================================================
# API KEY UPDATE
# ============================================================================

class ApiKeyUpdateRequest(BaseModel):
    """
    API anahtarı güncelleme isteği.
    """
    api_key: str = Field(..., min_length=10, description="API Key")
    api_secret: str = Field(..., min_length=10, description="API Secret")
    
    class Config:
        json_schema_extra = {
            "example": {
                "api_key": "pk_live_abc123xyz...",
                "api_secret": "sk_live_xyz789abc..."
            }
        }


# ============================================================================
# API TEST
# ============================================================================

class ApiTestRequest(BaseModel):
    """
    API bağlantı testi isteği.
    """
    api_key: str = Field(..., description="API Key")
    api_secret: str = Field(..., description="API Secret")
    exchange: str = Field(default="binance", description="Borsa")
