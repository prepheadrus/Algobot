"""
Order Value Object

Emir (order) entity'si - borsa emirlerini temsil eder.
Immutable (değiştirilemez) tasarım.

Özellikler:
- Tip güvenliği (type hints)
- Order lifecycle (pending -> open -> filled/cancelled)
- Order type support (market, limit, stop, vb.)
- Serialization (dict/JSON)

Kullanım:
    from core.trading.entities.order import Order, OrderType, OrderSide, OrderStatus
    
    # Market order oluştur
    from core.trading.entities.order_params import MarketOrderParams, LimitOrderParams
    order = Order.create_market_order(MarketOrderParams(
        bot_id="bot_123",
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        size=0.1,
        leverage=5.0
    ))
    
    # Limit order oluştur
    order = Order.create_limit_order(LimitOrderParams(
        bot_id="bot_123",
        symbol="BTC/USDT",
        side=OrderSide.BUY,
        size=0.1,
        price=49000.0,
        leverage=5.0
    ))
    
    # Order durumu güncelle
    order = order.with_status(OrderStatus.FILLED, filled_price=49500.0)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, TYPE_CHECKING
from enum import Enum
from uuid import uuid4

if TYPE_CHECKING:
    from core.trading.entities.order_params import (
        MarketOrderParams,
        LimitOrderParams,
        StopLossOrderParams,
        TakeProfitOrderParams
    )


class OrderType(str, Enum):
    """Emir tipi"""
    MARKET = "market"  # Piyasa fiyatından
    LIMIT = "limit"  # Limit fiyattan
    STOP_LOSS = "stop_loss"  # Stop loss emri
    TAKE_PROFIT = "take_profit"  # Take profit emri
    STOP_LIMIT = "stop_limit"  # Stop limit emri
    TRAILING_STOP = "trailing_stop"  # Trailing stop


class OrderSide(str, Enum):
    """Emir yönü"""
    BUY = "buy"  # Alış
    SELL = "sell"  # Satış


class OrderStatus(str, Enum):
    """Emir durumu"""
    PENDING = "pending"  # Beklemede
    OPEN = "open"  # Açık (kısmen dolu olabilir)
    FILLED = "filled"  # Tamamen doldu
    CANCELLED = "cancelled"  # İptal edildi
    REJECTED = "rejected"  # Reddedildi
    PARTIALLY_FILLED = "partially_filled"  # Kısmen doldu
    EXPIRED = "expired"  # Süresi doldu


@dataclass(frozen=True)
class Order:
    """
    Order Value Object.
    
    Borsa emirlerini temsil eder.
    Immutable (değiştirilemez) tasarım.
    
    Attributes:
        id: Benzersiz order ID (UUID)
        bot_id: Bot ID
        symbol: Sembol (örn: BTC/USDT)
        type: Emir tipi (market, limit, vb.)
        side: Emir yönü (buy, sell)
        status: Emir durumu
        size: Emir boyutu (coin miktarı)
        filled_size: Dolan boyut
        price: Limit fiyatı (limit/stop-limit için)
        stop_price: Stop fiyatı (stop-loss için)
        leverage: Kaldıraç
        time_in_force: Time in force (GTC, IOC, FOK)
        created_at: Oluşturulma zamanı (UTC)
        updated_at: Güncellenme zamanı (UTC)
        filled_at: Dolum zamanı (UTC)
        filled_price: Dolum fiyatı (ortalama)
        commission: Komisyon
        reason: Durum değişikliği nedeni
        metadata: Ek veriler (JSON)
        exchange_order_id: Borsa order ID (exchange'ten dönen)
        reduce_only: Reduce only (position küçültme)
        post_only: Post only (maker only)
    """
    
    # Required fields
    id: str
    bot_id: str
    symbol: str
    type: OrderType
    side: OrderSide
    status: OrderStatus
    size: float
    leverage: float
    created_at: datetime
    
    # Optional fields
    filled_size: float = 0.0
    price: Optional[float] = None  # Limit orders
    stop_price: Optional[float] = None  # Stop orders
    time_in_force: str = "GTC"  # Good Till Cancelled
    updated_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None
    filled_price: Optional[float] = None
    commission: float = 0.0
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    exchange_order_id: Optional[str] = None
    reduce_only: bool = False
    post_only: bool = False
    
    def __post_init__(self):
        """Validation"""
        # Tip validasyonu
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id boş olamaz")
        
        if not isinstance(self.bot_id, str) or not self.bot_id.strip():
            raise ValueError("bot_id boş olamaz")
        
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("symbol boş olamaz")
        
        if self.size <= 0:
            raise ValueError("size pozitif olmalı")
        
        if self.leverage < 1:
            raise ValueError("leverage en az 1x olmalı")
        
        # updated_at set (eğer None ise created_at kullan)
        if self.updated_at is None:
            object.__setattr__(self, 'updated_at', self.created_at)
        
        # Price validation for limit orders
        if self.type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
            if self.price is None:
                raise ValueError(f"{self.type.value} order için price gerekli")
        
        # Stop price validation for stop orders
        if self.type in [OrderType.STOP_LOSS, OrderType.STOP_LIMIT]:
            if self.stop_price is None:
                raise ValueError(f"{self.type.value} order için stop_price gerekli")
    
    # ========================================================================
    # FACTORY METHODS (Kolay Oluşturma)
    # ========================================================================
    
    @classmethod
    def create_market_order(cls, params: 'MarketOrderParams') -> 'Order':
        """
        Market order oluştur.
        
        Args:
            params: MarketOrderParams DTO

        Returns:
            Order instance
        """
        now = datetime.utcnow()
        return cls(
            id=f"order_{uuid4().hex[:12]}",
            bot_id=params.bot_id,
            symbol=params.symbol,
            type=OrderType.MARKET,
            side=params.side,
            status=OrderStatus.PENDING,
            size=params.size,
            leverage=params.leverage,
            created_at=now,
            reduce_only=params.reduce_only,
            metadata=params.metadata or {}
        )
    
    @classmethod
    def create_limit_order(cls, params: 'LimitOrderParams') -> 'Order':
        """
        Limit order oluştur.
        
        Args:
            params: LimitOrderParams DTO

        Returns:
            Order instance
        """
        now = datetime.utcnow()
        return cls(
            id=f"order_{uuid4().hex[:12]}",
            bot_id=params.bot_id,
            symbol=params.symbol,
            type=OrderType.LIMIT,
            side=params.side,
            status=OrderStatus.PENDING,
            size=params.size,
            leverage=params.leverage,
            price=params.price,
            time_in_force=params.time_in_force,
            post_only=params.post_only,
            created_at=now,
            reduce_only=params.reduce_only,
            metadata=params.metadata or {}
        )
    
    @classmethod
    def create_stop_loss_order(cls, params: 'StopLossOrderParams') -> 'Order':
        """
        Stop loss order oluştur.
        
        Args:
            params: StopLossOrderParams DTO

        Returns:
            Order instance
        """
        now = datetime.utcnow()
        return cls(
            id=f"order_{uuid4().hex[:12]}",
            bot_id=params.bot_id,
            symbol=params.symbol,
            type=OrderType.STOP_LOSS,
            side=params.side,
            status=OrderStatus.PENDING,
            size=params.size,
            leverage=params.leverage,
            stop_price=params.stop_price,
            created_at=now,
            reduce_only=params.reduce_only,
            metadata=params.metadata or {}
        )
    
    @classmethod
    def create_take_profit_order(cls, params: 'TakeProfitOrderParams') -> 'Order':
        """
        Take profit order oluştur.
        
        Args:
            params: TakeProfitOrderParams DTO

        Returns:
            Order instance
        """
        now = datetime.utcnow()
        return cls(
            id=f"order_{uuid4().hex[:12]}",
            bot_id=params.bot_id,
            symbol=params.symbol,
            type=OrderType.TAKE_PROFIT,
            side=params.side,
            status=OrderStatus.PENDING,
            size=params.size,
            leverage=params.leverage,
            stop_price=params.target_price,  # TP de stop_price kullanır (veya isteğe bağlı trigger_price)
            price=params.trigger_price, # Limit fiyatı (varsa) trigger olarak set edilebilir
            created_at=now,
            reduce_only=params.reduce_only,
            metadata=params.metadata or {}
        )
    
    # ========================================================================
    # STATUS TRANSITIONS (Durum Değiştirme)
    # ========================================================================
    
    def with_status(
        self,
        new_status: OrderStatus,
        reason: Optional[str] = None,
        filled_price: Optional[float] = None
    ) -> 'Order':
        """
        Durum değiştir (immutable).
        
        Args:
            new_status: Yeni durum
            reason: Değişiklik nedeni
            filled_price: Dolum fiyatı (filled için)
        
        Returns:
            Yeni Order instance
        """
        import dataclasses
        
        updates = {
            'status': new_status,
            'reason': reason,
            'updated_at': datetime.utcnow()
        }
        
        # Filled ise filled_at ve filled_price set et
        if new_status == OrderStatus.FILLED:
            updates['filled_at'] = updates['updated_at']
            if filled_price is not None:
                updates['filled_price'] = filled_price
        
        # Partially filled ise filled_size güncelle
        elif new_status == OrderStatus.PARTIALLY_FILLED:
            updates['filled_at'] = updates['updated_at']
        
        return dataclasses.replace(self, **updates)
    
    def with_filled_size(self, filled_size: float) -> 'Order':
        """
        Dolan boyut güncelle (immutable).
        
        Args:
            filled_size: Dolan boyut
        
        Returns:
            Yeni Order instance
        """
        import dataclasses
        
        # Status'u otomatik güncelle
        if filled_size >= self.size:
            new_status = OrderStatus.FILLED
        elif filled_size > 0:
            new_status = OrderStatus.PARTIALLY_FILLED
        else:
            new_status = self.status
        
        return dataclasses.replace(
            self,
            filled_size=filled_size,
            status=new_status,
            updated_at=datetime.utcnow()
        )
    
    def with_exchange_id(self, exchange_order_id: str) -> 'Order':
        """
        Borsa order ID ekle (immutable).
        
        Args:
            exchange_order_id: Exchange order ID
        
        Returns:
            Yeni Order instance
        """
        import dataclasses
        return dataclasses.replace(
            self,
            exchange_order_id=exchange_order_id,
            updated_at=datetime.utcnow()
        )
    
    def with_commission(self, commission: float) -> 'Order':
        """
        Komisyon ekle (immutable).
        
        Args:
            commission: Komisyon
        
        Returns:
            Yeni Order instance
        """
        import dataclasses
        return dataclasses.replace(
            self,
            commission=commission,
            updated_at=datetime.utcnow()
        )
    
    # ========================================================================
    # ORDER STATE QUERIES
    # ========================================================================
    
    @property
    def is_active(self) -> bool:
        """
        Aktif mi? (pending, open, partially_filled)
        
        Returns:
            True ise aktif
        """
        return self.status in [
            OrderStatus.PENDING,
            OrderStatus.OPEN,
            OrderStatus.PARTIALLY_FILLED
        ]
    
    @property
    def is_terminal(self) -> bool:
        """
        Terminal durumda mı? (filled, cancelled, rejected, expired)
        
        Returns:
            True ise terminal
        """
        return self.status in [
            OrderStatus.FILLED,
            OrderStatus.CANCELLED,
            OrderStatus.REJECTED,
            OrderStatus.EXPIRED
        ]
    
    @property
    def fill_rate(self) -> float:
        """
        Dolum oranı (0.0 - 1.0).
        
        Returns:
            Fill rate
        """
        if self.size <= 0:
            return 0.0
        return self.filled_size / self.size
    
    @property
    def remaining_size(self) -> float:
        """
        Kalan boyut.
        
        Returns:
            Kalan boyut
        """
        return self.size - self.filled_size
    
    @property
    def is_buy(self) -> bool:
        """Alış emri mi?"""
        return self.side == OrderSide.BUY
    
    @property
    def is_sell(self) -> bool:
        """Satış emri mi?"""
        return self.side == OrderSide.SELL
    
    @property
    def is_market(self) -> bool:
        """Market emri mi?"""
        return self.type == OrderType.MARKET
    
    @property
    def is_limit(self) -> bool:
        """Limit emri mi?"""
        return self.type == OrderType.LIMIT
    
    @property
    def is_stop(self) -> bool:
        """Stop emri mi? (stop-loss veya take-profit)"""
        return self.type in [OrderType.STOP_LOSS, OrderType.TAKE_PROFIT]
    
    # ========================================================================
    # SERIALIZATION
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Dict'e çevir.
        
        Returns:
            Dict representation
        """
        return {
            'id': self.id,
            'bot_id': self.bot_id,
            'symbol': self.symbol,
            'type': self.type.value,
            'side': self.side.value,
            'status': self.status.value,
            'size': self.size,
            'filled_size': self.filled_size,
            'remaining_size': self.remaining_size,
            'price': self.price,
            'stop_price': self.stop_price,
            'leverage': self.leverage,
            'time_in_force': self.time_in_force,
            'reduce_only': self.reduce_only,
            'post_only': self.post_only,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'filled_at': self.filled_at.isoformat() if self.filled_at else None,
            'filled_price': self.filled_price,
            'commission': self.commission,
            'reason': self.reason,
            'exchange_order_id': self.exchange_order_id,
            'metadata': self.metadata
        }
    
    def to_json(self) -> str:
        """
        JSON'a çevir.
        
        Returns:
            JSON string
        """
        import json
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Order':
        """
        Dict'ten oluştur.
        
        Args:
            data: Dict representation
        
        Returns:
            Order instance
        """
        return cls(
            id=data['id'],
            bot_id=data['bot_id'],
            symbol=data['symbol'],
            type=OrderType(data['type']),
            side=OrderSide(data['side']),
            status=OrderStatus(data['status']),
            size=data['size'],
            filled_size=data.get('filled_size', 0.0),
            leverage=data['leverage'],
            price=data.get('price'),
            stop_price=data.get('stop_price'),
            time_in_force=data.get('time_in_force', 'GTC'),
            created_at=datetime.fromisoformat(data['created_at']) if isinstance(data['created_at'], str) else data['created_at'],
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') and isinstance(data['updated_at'], str) else data.get('updated_at'),
            filled_at=datetime.fromisoformat(data['filled_at']) if data.get('filled_at') and isinstance(data['filled_at'], str) else data.get('filled_at'),
            filled_price=data.get('filled_price'),
            commission=data.get('commission', 0.0),
            reason=data.get('reason'),
            metadata=data.get('metadata', {}),
            exchange_order_id=data.get('exchange_order_id'),
            reduce_only=data.get('reduce_only', False),
            post_only=data.get('post_only', False)
        )
    
    # ========================================================================
    # STRING REPRESENTATION
    # ========================================================================
    
    def __str__(self) -> str:
        """Human-readable string"""
        status_emoji = {
            OrderStatus.PENDING: "⏳",
            OrderStatus.OPEN: "🟢",
            OrderStatus.FILLED: "✅",
            OrderStatus.CANCELLED: "❌",
            OrderStatus.REJECTED: "🚫",
            OrderStatus.PARTIALLY_FILLED: "🟡",
            OrderStatus.EXPIRED: "⏰"
        }.get(self.status, "")
        
        return (
            f"{status_emoji} Order({self.id[:8]}..., {self.symbol}, "
            f"{self.type.value.upper()}, {self.side.value.upper()}, "
            f"Size: {self.size}, Status: {self.status.value})"
        )
    
    def __repr__(self) -> str:
        """Developer representation"""
        return (
            f"Order(id='{self.id}', bot_id='{self.bot_id}', symbol='{self.symbol}', "
            f"type={self.type.value}, side={self.side.value}, status={self.status.value}, "
            f"size={self.size}, filled_size={self.filled_size})"
        )
    
    def __eq__(self, other: object) -> bool:
        """Equality check (ID bazlı)"""
        if not isinstance(other, Order):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash (ID bazlı)"""
        return hash(self.id)
