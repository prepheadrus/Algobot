"""
Order Params DTOs

Order oluşturma işlemleri için kullanılan veri transfer nesneleri (DTO).
High-Frequency Trading (HFT) bellek optimizasyonu ve asenkron thread-safety
sağlamak için slots=True ve frozen=True dataclass yapısı kullanılmıştır.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from core.trading.entities.order import OrderSide

@dataclass(kw_only=True, slots=True, frozen=True)
class BaseOrderParams:
    """Temel emir parametreleri"""
    bot_id: str
    symbol: str
    side: OrderSide
    size: float
    leverage: float = 1.0
    reduce_only: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass(kw_only=True, slots=True, frozen=True)
class MarketOrderParams(BaseOrderParams):
    """Market emri parametreleri"""
    pass

@dataclass(kw_only=True, slots=True, frozen=True)
class LimitOrderParams(BaseOrderParams):
    """Limit emri parametreleri"""
    price: float
    time_in_force: str = "GTC"
    post_only: bool = False

@dataclass(kw_only=True, slots=True, frozen=True)
class StopLossOrderParams(BaseOrderParams):
    """Stop loss emri parametreleri"""
    stop_price: float
    reduce_only: bool = True

@dataclass(kw_only=True, slots=True, frozen=True)
class TakeProfitOrderParams(BaseOrderParams):
    """Take profit emri parametreleri"""
    target_price: float
    trigger_price: Optional[float] = None
    reduce_only: bool = True
