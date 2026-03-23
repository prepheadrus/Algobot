"""
Trade Value Object

İşlem (trade) entity'si - kapatılmış pozisyonların kaydı.
Immutable (değiştirilemez) tasarım.

Özellikler:
- Tip güvenliği (type hints)
- PnL hesaplama
- Serialization (dict/JSON)
- Trade metadata

Kullanım:
    from core.trading.entities.trade import Trade, TradeResult
    
    # Trade oluştur (Position.close() metodundan)
    trade = Trade(
        id="trade_123",
        bot_id="bot_456",
        symbol="BTC/USDT",
        direction=PositionDirection.LONG,
        entry_price=50000.0,
        exit_price=51000.0,
        size=0.1,
        leverage=5.0,
        pnl=100.0,
        pnl_percent=0.10,
        opened_at=datetime.utcnow(),
        closed_at=datetime.utcnow(),
        reason="take_profit"
    )
    
    # Trade sonuçlarını al
    result = trade.get_result()
    print(f"Kar: ${result.pnl}, Yüzde: {result.pnl_percent:.2%}")
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum

from core.trading.entities.position import PositionDirection


class TradeResult(str, Enum):
    """İşlem sonucu"""
    WIN = "WIN"  # Kar
    LOSS = "LOSS"  # Zarar
    BREAKEVEN = "BREAKEVEN"  # Başa baş
    CANCELLED = "CANCELLED"  # İptal


@dataclass(frozen=True)
class Trade:
    """
    Trade Value Object.
    
    Kapatılmış pozisyonların kaydı.
    Immutable (değiştirilemez) tasarım.
    
    Attributes:
        id: Benzersiz trade ID
        bot_id: Bot ID
        symbol: Sembol (örn: BTC/USDT)
        direction: İşlem yönü (LONG/SHORT)
        entry_price: Giriş fiyatı
        exit_price: Çıkış fiyatı
        size: Pozisyon boyutu (coin miktarı)
        leverage: Kaldıraç
        pnl: Kar/Zarar ($)
        pnl_percent: Kar/Zarar (%)
        commission: Komisyon ($)
        opened_at: Açılma zamanı (UTC)
        closed_at: Kapanma zamanı (UTC)
        duration: İşlem süresi (otomatik hesaplanır)
        reason: Kapatma nedeni (manual, stop_loss, take_profit, vb.)
        metadata: Ek veriler (JSON)
        exit_price_slippage: Slipaj (varsayılan: 0)
    """
    
    # Required fields
    id: str
    bot_id: str
    symbol: str
    direction: PositionDirection
    entry_price: float
    exit_price: float
    size: float
    leverage: float
    pnl: float
    pnl_percent: float
    opened_at: datetime
    closed_at: datetime
    strategy_id: Optional[str] = None
    
    # Optional fields
    commission: float = 0.0
    reason: str = "manual"
    metadata: Dict[str, Any] = field(default_factory=dict)
    exit_price_slippage: float = 0.0
    
    def __post_init__(self):
        """Validation (dataclass initialization sonrası)"""
        # Tip validasyonu
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id boş olamaz")
        
        if not isinstance(self.bot_id, str) or not self.bot_id.strip():
            raise ValueError("bot_id boş olamaz")
        
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("symbol boş olamaz")
        
        if self.entry_price <= 0:
            raise ValueError("entry_price pozitif olmalı")
        
        if self.exit_price <= 0:
            raise ValueError("exit_price pozitif olmalı")
        
        if self.size <= 0:
            raise ValueError("size pozitif olmalı")
        
        if self.leverage < 1:
            raise ValueError("leverage en az 1x olmalı")
    
    # ========================================================================
    # TRADE RESULT (İŞLEM SONUCU)
    # ========================================================================
    
    @property
    def result(self) -> TradeResult:
        """
        İşlem sonucu (WIN/LOSS/BREAKEVEN).
        
        Returns:
            TradeResult enum
        """
        if abs(self.pnl) < 0.01:  # Başa baş (±$0.01)
            return TradeResult.BREAKEVEN
        elif self.pnl > 0:
            return TradeResult.WIN
        else:
            return TradeResult.LOSS
    
    @property
    def duration(self) -> timedelta:
        """
        İşlem süresi.
        
        Returns:
            Timedelta (closed_at - opened_at)
        """
        return self.closed_at - self.opened_at
    
    @property
    def duration_seconds(self) -> float:
        """
        İşlem süresi (saniye).
        
        Returns:
            Süre (saniye)
        """
        return self.duration.total_seconds()
    
    @property
    def duration_minutes(self) -> float:
        """
        İşlem süresi (dakika).
        
        Returns:
            Süre (dakika)
        """
        return self.duration_seconds / 60.0
    
    @property
    def duration_hours(self) -> float:
        """
        İşlem süresi (saat).
        
        Returns:
            Süre (saat)
        """
        return self.duration_minutes / 60.0
    
    # ========================================================================
    # PRICE ANALYSIS
    # ========================================================================
    
    @property
    def price_change(self) -> float:
        """
        Fiyat değişimi (exit - entry).
        
        LONG için: Pozitif = kar
        SHORT için: Negatif = kar
        
        Returns:
            Fiyat değişimi
        """
        return self.exit_price - self.entry_price
    
    @property
    def price_change_percent(self) -> float:
        """
        Fiyat değişimi (%).
        
        Returns:
            Yüzde değişim
        """
        if self.entry_price <= 0:
            return 0.0
        return (self.price_change / self.entry_price) * 100.0
    
    @property
    def gross_pnl(self) -> float:
        """
        Brüt PnL (komisyon öncesi).
        
        Returns:
            Brüt PnL
        """
        return self.pnl + self.commission
    
    @property
    def net_pnl(self) -> float:
        """
        Net PnL (komisyon sonrası).
        
        Returns:
            Net PnL (aynı olarak pnl)
        """
        return self.pnl
    
    @property
    def total_commission(self) -> float:
        """
        Toplam komisyon (entry + exit).
        
        Returns:
            Toplam komisyon
        """
        return self.commission
    
    @property
    def commission_percent(self) -> float:
        """
        Komisyon yüzdesi (pozisyon değerine göre).
        
        Returns:
            Komisyon %
        """
        position_value = self.entry_price * self.size
        if position_value <= 0:
            return 0.0
        return (self.commission / position_value) * 100.0
    
    # ========================================================================
    # PERFORMANCE METRICS
    # ========================================================================
    
    @property
    def profit_factor(self) -> float:
        """
        Profit Factor (kar/zarar oranı).
        
        Tek trade için: kar ise gross_pnl / |commission|
        
        Returns:
            Profit Factor
        """
        if self.pnl <= 0:
            return 0.0
        
        if self.commission <= 0:
            return float('inf')
        
        return self.gross_pnl / self.commission
    
    @property
    def return_on_margin(self) -> float:
        """
        Marjine göre getiri (RoM).
        
        Formül: PnL / (Entry × Size / Leverage)
        
        Returns:
            RoM (örn: 0.50 = %50 getiri)
        """
        margin = (self.entry_price * self.size) / self.leverage
        if margin <= 0:
            return 0.0
        return self.pnl / margin
    
    @property
    def return_on_margin_percent(self) -> float:
        """
        Marjine göre getiri (%).
        
        Returns:
            RoM %
        """
        return self.return_on_margin * 100.0
    
    # ========================================================================
    # TRADE TAGS (Kategorizasyon)
    # ========================================================================
    
    @property
    def is_scalp(self) -> bool:
        """
        Scalp trade mi? (< 15 dakika)
        
        Returns:
            True ise scalp
        """
        return self.duration_minutes < 15.0
    
    @property
    def is_day_trade(self) -> bool:
        """
        Day trade mi? (< 24 saat, >= 15 dakika)
        
        Returns:
            True ise day trade
        """
        return 15.0 <= self.duration_minutes < (24.0 * 60.0)
    
    @property
    def is_swing_trade(self) -> bool:
        """
        Swing trade mi? (>= 1 gün, < 7 gün)
        
        Returns:
            True ise swing trade
        """
        return (24.0 * 60.0) <= self.duration_minutes < (7.0 * 24.0 * 60.0)
    
    @property
    def is_position_trade(self) -> bool:
        """
        Position trade mi? (>= 7 gün)
        
        Returns:
            True ise position trade
        """
        return self.duration_minutes >= (7.0 * 24.0 * 60.0)
    
    @property
    def exit_reason_category(self) -> str:
        """
        Çıkış nedeni kategorisi.
        
        Returns:
            Kategori (stop_loss, take_profit, manual, vb.)
        """
        if 'stop_loss' in self.reason.lower():
            return 'stop_loss'
        elif 'take_profit' in self.reason.lower():
            return 'take_profit'
        elif 'trailing' in self.reason.lower():
            return 'trailing_stop'
        elif 'liquidation' in self.reason.lower():
            return 'liquidation'
        elif 'emergency' in self.reason.lower():
            return 'emergency'
        else:
            return 'manual'
    
    # ========================================================================
    # SERIALIZATION
    # ========================================================================
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Dict'e çevir (serialization).
        
        Returns:
            Dict representation
        """
        return {
            'id': self.id,
            'bot_id': self.bot_id,
            'symbol': self.symbol,
            'direction': self.direction.value,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'size': self.size,
            'leverage': self.leverage,
            'pnl': self.pnl,
            "pnl_percent": self.pnl_percent,
            "commission": self.commission,
            "strategy_id": self.strategy_id,
            "opened_at": self.opened_at.isoformat(),
            'closed_at': self.closed_at.isoformat(),
            'duration_seconds': self.duration_seconds,
            'reason': self.reason,
            'result': self.result.value,
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
    def from_dict(cls, data: Dict[str, Any]) -> 'Trade':
        """
        Dict'ten oluştur (deserialization).
        
        Args:
            data: Dict representation
        
        Returns:
            Trade instance
        """
        return cls(
            id=data['id'],
            bot_id=data['bot_id'],
            symbol=data['symbol'],
            direction=PositionDirection(data['direction']),
            entry_price=data['entry_price'],
            exit_price=data['exit_price'],
            size=data['size'],
            leverage=data['leverage'],
            pnl=data['pnl'],
            pnl_percent=data['pnl_percent'],
            opened_at=datetime.fromisoformat(data['opened_at']) if isinstance(data['opened_at'], str) else data['opened_at'],
            closed_at=datetime.fromisoformat(data['closed_at']) if isinstance(data['closed_at'], str) else data['closed_at'],
            commission=data.get('commission', 0.0),
            reason=data.get('reason', 'manual'),
            metadata=data.get('metadata', {})
        )
    
    # ========================================================================
    # STRING REPRESENTATION
    # ========================================================================
    
    def __str__(self) -> str:
        """Human-readable string"""
        result_emoji = "✅" if self.result == TradeResult.WIN else "❌" if self.result == TradeResult.LOSS else "➖"
        return (
            f"{result_emoji} Trade({self.id}, {self.symbol}, "
            f"{self.direction.value}, PnL: ${self.pnl:.2f} ({self.pnl_percent:.2%}), "
            f"Result: {self.result.value})"
        )
    
    def __repr__(self) -> str:
        """Developer representation"""
        return (
            f"Trade(id='{self.id}', bot_id='{self.bot_id}', symbol='{self.symbol}', "
            f"direction={self.direction.value}, pnl={self.pnl}, pnl_percent={self.pnl_percent:.4f})"
        )
    
    def __eq__(self, other: object) -> bool:
        """Equality check (ID bazlı)"""
        if not isinstance(other, Trade):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash (ID bazlı)"""
        return hash(self.id)


# ============================================================================
# TRADE HISTORY (Collection)
# ============================================================================

@dataclass
class TradeHistory:
    """
    Trade History Collection.
    
    Trade'leri saklar ve istatistikleri hesaplar.
    """
    
    trades: list = field(default_factory=list)
    
    def add(self, trade: Trade):
        """Trade ekle"""
        self.trades.append(trade)
    
    def remove(self, trade_id: str) -> bool:
        """Trade sil"""
        for i, trade in enumerate(self.trades):
            if trade.id == trade_id:
                del self.trades[i]
                return True
        return False
    
    def get_by_bot(self, bot_id: str) -> list:
        """Bot'a göre trade'leri al"""
        return [t for t in self.trades if t.bot_id == bot_id]
    
    def get_by_symbol(self, symbol: str) -> list:
        """Sembol'e göre trade'leri al"""
        return [t for t in self.trades if t.symbol == symbol]
    
    def get_by_result(self, result: TradeResult) -> list:
        """Sonuç'a göre trade'leri al"""
        return [t for t in self.trades if t.result == result]
    
    def get_recent(self, limit: int = 10) -> list:
        """Son trade'leri al"""
        return sorted(self.trades, key=lambda t: t.closed_at, reverse=True)[:limit]
    
    @property
    def total_trades(self) -> int:
        """Toplam trade sayısı"""
        return len(self.trades)
    
    @property
    def winning_trades(self) -> list:
        """Kazanan trade'ler"""
        return self.get_by_result(TradeResult.WIN)
    
    @property
    def losing_trades(self) -> list:
        """Kaybeden trade'ler"""
        return self.get_by_result(TradeResult.LOSS)
    
    @property
    def win_rate(self) -> float:
        """
        Kazanma oranı.
        
        Returns:
            Win rate (0.0 - 1.0)
        """
        if self.total_trades <= 0:
            return 0.0
        return len(self.winning_trades) / self.total_trades
    
    @property
    def total_pnl(self) -> float:
        """Toplam PnL"""
        return sum(t.pnl for t in self.trades)
    
    @property
    def gross_profit(self) -> float:
        """Brüt kar (kazanan trade'ler)"""
        return sum(t.pnl for t in self.winning_trades)
    
    @property
    def gross_loss(self) -> float:
        """Brüt zarar (kaybeden trade'ler)"""
        return abs(sum(t.pnl for t in self.losing_trades))
    
    @property
    def profit_factor(self) -> float:
        """
        Profit Factor (Brüt Kar / Brüt Zarar).
        
        Returns:
            Profit Factor
        """
        if self.gross_loss <= 0:
            return float('inf') if self.gross_profit > 0 else 0.0
        return self.gross_profit / self.gross_loss
    
    @property
    def avg_win(self) -> float:
        """Ortalama kar"""
        if not self.winning_trades:
            return 0.0
        return sum(t.pnl for t in self.winning_trades) / len(self.winning_trades)
    
    @property
    def avg_loss(self) -> float:
        """Ortalama zarar"""
        if not self.losing_trades:
            return 0.0
        return abs(sum(t.pnl for t in self.losing_trades) / len(self.losing_trades))
    
    @property
    def win_loss_ratio(self) -> float:
        """
        Kar/Zarar oranı (Ortalama Kar / Ortalama Zarar).
        
        Returns:
            Win/Loss ratio
        """
        if self.avg_loss <= 0:
            return float('inf') if self.avg_win > 0 else 0.0
        return self.avg_win / self.avg_loss
    
    @property
    def avg_duration(self) -> timedelta:
        """Ortalama işlem süresi"""
        if not self.trades:
            return timedelta(0)
        total_duration = sum((t.duration for t in self.trades), timedelta(0))
        return total_duration / len(self.trades)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        İstatistikleri dict'e çevir.
        
        Returns:
            Dict with all stats
        """
        return {
            'total_trades': self.total_trades,
            'winning_trades': len(self.winning_trades),
            'losing_trades': len(self.losing_trades),
            'win_rate': self.win_rate,
            'total_pnl': self.total_pnl,
            'gross_profit': self.gross_profit,
            'gross_loss': self.gross_loss,
            'profit_factor': self.profit_factor,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'win_loss_ratio': self.win_loss_ratio,
            'avg_duration_seconds': self.avg_duration.total_seconds()
        }
