"""
Event Definitions - Tüm Event Tipleri

Bu modül, sistemdeki tüm event tiplerini tanımlar.
Her event tipi type-safe ve dokümante edilmiştir.

Event Kategorileri:
1. BOT_EVENTS: Bot lifecycle (başlatma, durdurma, vb.)
2. SIGNAL_EVENTS: Trading sinyalleri
3. POSITION_EVENTS: Pozisyon lifecycle
4. TRADE_EVENTS: İşlem kayıtları
5. ML_EVENTS: Makine öğrenmesi olayları
6. RISK_EVENTS: Risk yönetimi olayları
7. DATA_EVENTS: Veri yönetimi olayları
8. SYSTEM_EVENTS: Sistem olayları

Kullanım:
    from shared.events.events import BotStartedEvent, PositionOpenedEvent
    
    # Event oluştur
    event = BotStartedEvent(
        bot_id="BTC_123",
        symbol="BTC/USDT",
        strategy_id="trend_master",
        timeframe="1m"
    ).to_event()
    
    # Yayınla
    await event_bus.publish(event)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum

from shared.events.event_bus import Event


# ============================================================================
# ENUMS (Tip Güvenliği İçin)
# ============================================================================

class BotStatus(str, Enum):
    """Bot durumları"""
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    ERROR = "error"


class PositionDirection(str, Enum):
    """Pozisyon yönü"""
    LONG = "LONG"
    SHORT = "SHORT"


class OrderType(str, Enum):
    """Emir tipi"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LIMIT = "stop_limit"


class OrderSide(str, Enum):
    """Emir yönü"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """Emir durumu"""
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIALLY_FILLED = "partially_filled"


class SignalType(int, Enum):
    """Trading sinyali"""
    SHORT = 0
    HOLD = 1
    LONG = 2


class MarketType(str, Enum):
    """Piyasa tipi"""
    SPOT = "spot"
    SWAP = "swap"
    FUTURE = "future"


class MLRecommendation(str, Enum):
    """ML önerisi"""
    STRONG_LONG = "STRONG_LONG"
    LONG = "LONG"
    NEUTRAL = "NEUTRAL"
    SHORT = "SHORT"
    STRONG_SHORT = "STRONG_SHORT"


# ============================================================================
# LIVE PRICE EVENTS (Tick Data Pub/Sub)
# ============================================================================

@dataclass
class LivePriceUpdatedEvent:
    """
    Canlı fiyat güncellemesi (WebSocket tick data).

    TradingView'den gelen gerçek zamanlı fiyat olayı.
    Trailing stop ve likidasyon kontrolleri için kullanılır.

    Attributes:
        symbol: Sembol (örn: BTC/USDT)
        price: Güncel fiyat (float)
        high: 24s yüksek (opsiyonel)
        low: 24s düşük (opsiyonel)
        volume: 24s hacim (opsiyonel)
    """
    symbol: str
    price: float
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None

    def to_event(self) -> Event:
        """Event wrapper"""
        return Event(
            type="price.updated",
            payload={
                'symbol': self.symbol,
                'price': self.price,
                'high': self.high,
                'low': self.low,
                'volume': self.volume
            },
            source="exchange"
        )


# ============================================================================
# 1. BOT EVENTS (Bot Lifecycle)
# ============================================================================

@dataclass
class BotStartedEvent:
    """
    Bot başlatıldı.
    
    Publisher: BotManager
    Subscribers: PaperTrader, Dashboard, Logger
    """
    bot_id: str
    symbol: str
    strategy_id: str
    timeframe: str
    market_type: MarketType = MarketType.SWAP
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "bot_manager") -> Event:
        return Event(
            type="bot.started",
            payload={
                'bot_id': self.bot_id,
                'symbol': self.symbol,
                'strategy_id': self.strategy_id,
                'timeframe': self.timeframe,
                'market_type': self.market_type.value
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class PositionPartialClosedEvent:
    """
    Pozisyon kısmi olarak kapatıldı (Kâr alma).

    Publisher: PositionManager
    Subscribers: Dashboard, Logger, RiskManager
    """
    bot_id: str
    symbol: str
    direction: PositionDirection
    exit_price: float
    size_closed: float
    pnl: float
    pnl_percent: float
    remaining_size: float
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_event(self, source: str = "position_manager") -> Event:
        return Event(
            type="position.partial_closed",
            payload={
                'bot_id': self.bot_id,
                'symbol': self.symbol,
                'direction': self.direction.value,
                'exit_price': self.exit_price,
                'size_closed': self.size_closed,
                'pnl': self.pnl,
                'pnl_percent': self.pnl_percent,
                'remaining_size': self.remaining_size
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class BotStoppedEvent:
    """
    Bot durduruldu.
    
    Publisher: BotManager
    Subscribers: PaperTrader, Dashboard, Logger
    """
    bot_id: str
    reason: str = "user_requested"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "bot_manager") -> Event:
        return Event(
            type="bot.stopped",
            payload={
                'bot_id': self.bot_id,
                'reason': self.reason
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class BotResumedEvent:
    """
    Bot devam etti (paused -> running).
    
    Publisher: BotManager
    Subscribers: PaperTrader, Dashboard
    """
    bot_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "bot_manager") -> Event:
        return Event(
            type="bot.resumed",
            payload={
                'bot_id': self.bot_id
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class BotRemovedEvent:
    """
    Bot silindi.
    
    Publisher: BotManager
    Subscribers: PaperTrader, Dashboard, Logger
    """
    bot_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "bot_manager") -> Event:
        return Event(
            type="bot.removed",
            payload={
                'bot_id': self.bot_id
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class BotErrorEvent:
    """
    Bot hatası.
    
    Publisher: Any (bot ile ilgili hata)
    Subscribers: Logger, Dashboard, AlertSystem
    """
    bot_id: str
    error_type: str
    error_message: str
    traceback: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "unknown") -> Event:
        return Event(
            type="bot.error",
            payload={
                'bot_id': self.bot_id,
                'error_type': self.error_type,
                'error_message': self.error_message,
                'traceback': self.traceback
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class BotStatusChangedEvent:
    """
    Bot durumu değişti.
    
    Publisher: BotManager
    Subscribers: Dashboard, Logger
    """
    bot_id: str
    old_status: BotStatus
    new_status: BotStatus
    reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "bot_manager") -> Event:
        return Event(
            type="bot.status_changed",
            payload={
                'bot_id': self.bot_id,
                'old_status': self.old_status.value,
                'new_status': self.new_status.value,
                'reason': self.reason
            },
            timestamp=self.timestamp,
            source=source
        )


# ============================================================================
# 2. SIGNAL EVENTS (Trading Sinyalleri)
# ============================================================================

@dataclass
class SignalGeneratedEvent:
    """
    Strateji sinyali üretildi.

    Publisher: StrategyManager / Exchange Poller
    Subscribers: PaperTrader, ML Service, Dashboard, Logger
    """
    bot_id: str
    symbol: str
    signal: int  # Direct int (0=SHORT, 1=HOLD, 2=LONG)
    price: float
    timeframe: str
    indicators: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)  # HTF, regime, etc.
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_event(self, source: str = "strategy_manager") -> Event:
        return Event(
            type="signal.generated",
            payload={
                'bot_id': self.bot_id,
                'symbol': self.symbol,
                'signal': self.signal,  # Direkt int (0, 1, 2)
                'signal_name': 'SHORT' if self.signal == 0 else ('HOLD' if self.signal == 1 else 'LONG'),
                'price': self.price,
                'timeframe': self.timeframe,
                'indicators': self.indicators,
                'metadata': self.metadata  # HTF, regime, etc.
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class SignalConfirmedEvent:
    """
    Sinyal onaylandı (confluence geçti).
    
    Publisher: ConfluenceChecker
    Subscribers: PositionManager, Logger
    """
    bot_id: str
    symbol: str
    signal: SignalType
    ml_recommendation: MLRecommendation
    ml_confidence: float
    confluence_score: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "confluence") -> Event:
        return Event(
            type="signal.confirmed",
            payload={
                'bot_id': self.bot_id,
                'symbol': self.symbol,
                'signal': self.signal.value,
                'ml_recommendation': self.ml_recommendation.value,
                'ml_confidence': self.ml_confidence,
                'confluence_score': self.confluence_score
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class SignalRejectedEvent:
    """
    Sinyal reddedildi (confluence geçmedi).
    
    Publisher: ConfluenceChecker
    Subscribers: Logger, Dashboard
    """
    bot_id: str
    symbol: str
    signal: SignalType
    reason: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "confluence") -> Event:
        return Event(
            type="signal.rejected",
            payload={
                'bot_id': self.bot_id,
                'symbol': self.symbol,
                'signal': self.signal.value,
                'reason': self.reason,
                'details': self.details
            },
            timestamp=self.timestamp,
            source=source
        )


# ============================================================================
# 3. POSITION EVENTS (Pozisyon Lifecycle)
# ============================================================================

@dataclass
class PositionOpenedEvent:
    """
    Pozisyon açıldı.
    
    Publisher: PositionManager
    Subscribers: Dashboard, Logger, RiskManager, TradeHistory
    """
    bot_id: str
    symbol: str
    direction: PositionDirection
    entry_price: float
    size: float
    leverage: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    margin: float
    market_type: MarketType = MarketType.SWAP
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "position_manager") -> Event:
        return Event(
            type="position.opened",
            payload={
                'bot_id': self.bot_id,
                'symbol': self.symbol,
                'direction': self.direction.value,
                'entry_price': self.entry_price,
                'size': self.size,
                'leverage': self.leverage,
                'stop_loss': self.stop_loss,
                'take_profit': self.take_profit,
                'margin': self.margin,
                'market_type': self.market_type.value
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class PositionClosedEvent:
    """
    Pozisyon kapatıldı.
    
    Publisher: PositionManager
    Subscribers: Dashboard, Logger, RiskManager, TradeHistory, Statistics
    """
    bot_id: str
    symbol: str
    direction: PositionDirection
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_percent: float
    commission: float
    reason: str
    leverage: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "position_manager") -> Event:
        return Event(
            type="position.closed",
            payload={
                'bot_id': self.bot_id,
                'symbol': self.symbol,
                'direction': self.direction.value,
                'entry_price': self.entry_price,
                'exit_price': self.exit_price,
                'size': self.size,
                'pnl': self.pnl,
                'pnl_percent': self.pnl_percent,
                'commission': self.commission,
                'reason': self.reason,
                'leverage': self.leverage
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class PositionUpdatedEvent:
    """
    Pozisyon güncellendi (trailing stop, vb.).
    
    Publisher: PositionManager
    Subscribers: Dashboard, Logger
    """
    bot_id: str
    symbol: str
    updates: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "position_manager") -> Event:
        return Event(
            type="position.updated",
            payload={
                'bot_id': self.bot_id,
                'symbol': self.symbol,
                'updates': self.updates
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class StopLossUpdatedEvent:
    """
    Trailing stop güncellendi.
    
    Publisher: PositionManager
    Subscribers: Dashboard, Logger
    """
    bot_id: str
    symbol: str
    direction: PositionDirection
    old_stop: float
    new_stop: float
    current_price: float
    reason: str = "trailing_stop"
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "position_manager") -> Event:
        return Event(
            type="position.stoploss_updated",
            payload={
                'bot_id': self.bot_id,
                'symbol': self.symbol,
                'direction': self.direction.value,
                'old_stop': self.old_stop,
                'new_stop': self.new_stop,
                'current_price': self.current_price,
                'reason': self.reason
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class PositionLiquidatedEvent:
    """
    Pozisyon likide edildi.
    
    Publisher: PositionManager / Exchange
    Subscribers: Dashboard, Logger, RiskManager, AlertSystem
    """
    bot_id: str
    symbol: str
    direction: PositionDirection
    liquidation_price: float
    pnl: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "position_manager") -> Event:
        return Event(
            type="position.liquidated",
            payload={
                'bot_id': self.bot_id,
                'symbol': self.symbol,
                'direction': self.direction.value,
                'liquidation_price': self.liquidation_price,
                'pnl': self.pnl
            },
            timestamp=self.timestamp,
            source=source
        )


# ============================================================================
# 4. TRADE EVENTS (İşlem Kayıtları)
# ============================================================================

@dataclass
class TradeRecordedEvent:
    """
    Trade kaydedildi (trade history'ye eklendi).
    
    Publisher: TradeHistory
    Subscribers: Statistics, Dashboard, Logger
    """
    trade_id: str
    bot_id: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    pnl: float
    pnl_percent: float
    opened_at: datetime
    closed_at: datetime
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "trade_history") -> Event:
        return Event(
            type="trade.recorded",
            payload={
                'trade_id': self.trade_id,
                'bot_id': self.bot_id,
                'symbol': self.symbol,
                'direction': self.direction,
                'entry_price': self.entry_price,
                'exit_price': self.exit_price,
                'pnl': self.pnl,
                'pnl_percent': self.pnl_percent,
                'opened_at': self.opened_at.isoformat(),
                'closed_at': self.closed_at.isoformat()
            },
            timestamp=self.timestamp,
            source=source
        )


# ============================================================================
# 5. ML EVENTS (Makine Öğrenmesi)
# ============================================================================

@dataclass
class MLTrainingStartedEvent:
    """
    ML model eğitimi başladı.
    
    Publisher: MLService
    Subscribers: Dashboard, Logger
    """
    training_id: str
    symbol: str
    timeframe: str
    model_type: str
    dataset_size: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "ml_service") -> Event:
        return Event(
            type="ml.training_started",
            payload={
                'training_id': self.training_id,
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'model_type': self.model_type,
                'dataset_size': self.dataset_size
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class MLTrainingProgressEvent:
    """
    ML eğitim ilerlemesi.
    
    Publisher: MLService
    Subscribers: Dashboard, Logger
    """
    training_id: str
    progress: float  # 0.0 - 1.0
    current_step: str
    metrics: Optional[Dict[str, float]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "ml_service") -> Event:
        return Event(
            type="ml.training_progress",
            payload={
                'training_id': self.training_id,
                'progress': self.progress,
                'current_step': self.current_step,
                'metrics': self.metrics
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class MLTrainingCompletedEvent:
    """
    ML eğitimi tamamlandı.
    
    Publisher: MLService
    Subscribers: Dashboard, Logger, BotManager
    """
    training_id: str
    symbol: str
    timeframe: str
    model_path: str
    metrics: Dict[str, float]
    duration_seconds: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "ml_service") -> Event:
        return Event(
            type="ml.training_completed",
            payload={
                'training_id': self.training_id,
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'model_path': self.model_path,
                'metrics': self.metrics,
                'duration_seconds': self.duration_seconds
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class MLTrainingFailedEvent:
    """
    ML eğitimi başarısız.
    
    Publisher: MLService
    Subscribers: Dashboard, Logger
    """
    training_id: str
    symbol: str
    timeframe: str
    error_type: str
    error_message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "ml_service") -> Event:
        return Event(
            type="ml.training_failed",
            payload={
                'training_id': self.training_id,
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'error_type': self.error_type,
                'error_message': self.error_message
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class MLPredictionEvent:
    """
    ML tahmini yapıldı.
    
    Publisher: MLService
    Subscribers: ConfluenceChecker, Dashboard, Logger
    """
    symbol: str
    timeframe: str
    prediction: int  # 0=SHORT, 1=LONG
    confidence: float
    recommendation: MLRecommendation
    model_version: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "ml_service") -> Event:
        return Event(
            type="ml.prediction",
            payload={
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'prediction': self.prediction,
                'confidence': self.confidence,
                'recommendation': self.recommendation.value,
                'model_version': self.model_version
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class MLModelLoadedEvent:
    """
    ML model yüklendi.
    
    Publisher: MLService
    Subscribers: Logger, Dashboard
    """
    symbol: str
    timeframe: str
    model_path: str
    model_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "ml_service") -> Event:
        return Event(
            type="ml.model_loaded",
            payload={
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'model_path': self.model_path,
                'model_type': self.model_type
            },
            timestamp=self.timestamp,
            source=source
        )


# ============================================================================
# 6. RISK EVENTS (Risk Yönetimi)
# ============================================================================

@dataclass
class KillSwitchActivatedEvent:
    """
    Kill switch aktif edildi (acil durdurma).
    
    Publisher: RiskEngine
    Subscribers: BotManager, Dashboard, AlertSystem, Logger
    """
    reason: str
    consecutive_losses: int
    daily_pnl: float
    total_pnl: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "risk_engine") -> Event:
        return Event(
            type="risk.killswitch_activated",
            payload={
                'reason': self.reason,
                'consecutive_losses': self.consecutive_losses,
                'daily_pnl': self.daily_pnl,
                'total_pnl': self.total_pnl
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class RiskLimitBreachedEvent:
    """
    Risk limiti aşıldı.
    
    Publisher: RiskEngine
    Subscribers: BotManager, Dashboard, AlertSystem, Logger
    """
    bot_id: Optional[str]
    limit_type: str  # max_positions, max_daily_loss, max_drawdown, vb.
    current_value: float
    limit_value: float
    severity: str = "warning"  # warning, critical
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "risk_engine") -> Event:
        return Event(
            type="risk.limit_breached",
            payload={
                'bot_id': self.bot_id,
                'limit_type': self.limit_type,
                'current_value': self.current_value,
                'limit_value': self.limit_value,
                'severity': self.severity
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class MarginCallEvent:
    """
    Margin call (teminat çağrısı).
    
    Publisher: RiskEngine / PositionManager
    Subscribers: Dashboard, AlertSystem, Logger
    """
    bot_id: str
    symbol: str
    current_margin: float
    required_margin: float
    shortfall: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "risk_engine") -> Event:
        return Event(
            type="risk.margin_call",
            payload={
                'bot_id': self.bot_id,
                'symbol': self.symbol,
                'current_margin': self.current_margin,
                'required_margin': self.required_margin,
                'shortfall': self.shortfall
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class DrawdownWarningEvent:
    """
    Drawdown uyarısı.
    
    Publisher: RiskEngine
    Subscribers: Dashboard, Logger, AlertSystem
    """
    current_drawdown: float
    max_drawdown: float
    drawdown_percent: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "risk_engine") -> Event:
        return Event(
            type="risk.drawdown_warning",
            payload={
                'current_drawdown': self.current_drawdown,
                'max_drawdown': self.max_drawdown,
                'drawdown_percent': self.drawdown_percent
            },
            timestamp=self.timestamp,
            source=source
        )


# ============================================================================
# 7. DATA EVENTS (Veri Yönetimi)
# ============================================================================

@dataclass
class DataDownloadStartedEvent:
    """
    Veri indirme başladı.
    
    Publisher: DataDownloader
    Subscribers: Dashboard, Logger
    """
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    task_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "data_downloader") -> Event:
        return Event(
            type="data.download_started",
            payload={
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'task_id': self.task_id
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class DataDownloadProgressEvent:
    """
    Veri indirme ilerlemesi.
    
    Publisher: DataDownloader
    Subscribers: Dashboard, Logger
    """
    task_id: str
    symbol: str
    progress: float
    downloaded_candles: int
    total_candles: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "data_downloader") -> Event:
        return Event(
            type="data.download_progress",
            payload={
                'task_id': self.task_id,
                'symbol': self.symbol,
                'progress': self.progress,
                'downloaded_candles': self.downloaded_candles,
                'total_candles': self.total_candles
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class DataDownloadCompletedEvent:
    """
    Veri indirme tamamlandı.
    
    Publisher: DataDownloader
    Subscribers: Dashboard, Logger, BotManager
    """
    task_id: str
    symbol: str
    timeframe: str
    total_downloaded: int
    duration_seconds: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "data_downloader") -> Event:
        return Event(
            type="data.download_completed",
            payload={
                'task_id': self.task_id,
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'total_downloaded': self.total_downloaded,
                'duration_seconds': self.duration_seconds
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class CandleClosedEvent:
    """
    Mum kapandı (yeni mum oluştu).
    
    Publisher: ExchangeManager
    Subscribers: StrategyManager, IndicatorCalculator, Logger
    """
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    def to_event(self, source: str = "exchange_manager") -> Event:
        return Event(
            type="candle.closed",
            payload={
                'symbol': self.symbol,
                'timeframe': self.timeframe,
                'timestamp': self.timestamp.isoformat(),
                'open': self.open,
                'high': self.high,
                'low': self.low,
                'close': self.close,
                'volume': self.volume
            },
            timestamp=self.timestamp,
            source=source
        )


# ============================================================================
# 8. SYSTEM EVENTS (Sistem Olayları)
# ============================================================================

@dataclass
class SystemStartedEvent:
    """
    Sistem başlatıldı.
    
    Publisher: Main / Application
    Subscribers: Logger, Dashboard, All Modules
    """
    version: str
    environment: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "system") -> Event:
        return Event(
            type="system.started",
            payload={
                'version': self.version,
                'environment': self.environment
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class SystemShutdownEvent:
    """
    Sistem kapatılıyor.
    
    Publisher: Main / Application
    Subscribers: All Modules (cleanup için)
    """
    reason: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "system") -> Event:
        return Event(
            type="system.shutdown",
            payload={
                'reason': self.reason
            },
            timestamp=self.timestamp,
            source=source
        )


@dataclass
class HealthCheckEvent:
    """
    Sağlık kontrolü (heartbeat).
    
    Publisher: HealthMonitor
    Subscribers: Dashboard, Logger, Monitoring
    """
    component: str
    status: str  # healthy, degraded, unhealthy
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_event(self, source: str = "health_monitor") -> Event:
        return Event(
            type="system.health_check",
            payload={
                'component': self.component,
                'status': self.status,
                'details': self.details
            },
            timestamp=self.timestamp,
            source=source
        )


# ============================================================================
# EVENT REGISTRY (Dokümantasyon ve Validasyon İçin)
# ============================================================================

EVENT_REGISTRY = {
    # Bot Events
    "bot.started": BotStartedEvent,
    "bot.stopped": BotStoppedEvent,
    "bot.resumed": BotResumedEvent,
    "bot.removed": BotRemovedEvent,
    "bot.error": BotErrorEvent,
    "bot.status_changed": BotStatusChangedEvent,
    
    # Signal Events
    "signal.generated": SignalGeneratedEvent,
    "signal.confirmed": SignalConfirmedEvent,
    "signal.rejected": SignalRejectedEvent,
    
    # Position Events
    "position.opened": PositionOpenedEvent,
    "position.closed": PositionClosedEvent,
    "position.partial_closed": PositionPartialClosedEvent,
    "position.updated": PositionUpdatedEvent,
    "position.stoploss_updated": StopLossUpdatedEvent,
    "position.liquidated": PositionLiquidatedEvent,
    
    # Trade Events
    "trade.recorded": TradeRecordedEvent,
    
    # ML Events
    "ml.training_started": MLTrainingStartedEvent,
    "ml.training_progress": MLTrainingProgressEvent,
    "ml.training_completed": MLTrainingCompletedEvent,
    "ml.training_failed": MLTrainingFailedEvent,
    "ml.prediction": MLPredictionEvent,
    "ml.model_loaded": MLModelLoadedEvent,
    
    # Risk Events
    "risk.killswitch_activated": KillSwitchActivatedEvent,
    "risk.limit_breached": RiskLimitBreachedEvent,
    "risk.margin_call": MarginCallEvent,
    "risk.drawdown_warning": DrawdownWarningEvent,
    
    # Data Events
    "data.download_started": DataDownloadStartedEvent,
    "data.download_progress": DataDownloadProgressEvent,
    "data.download_completed": DataDownloadCompletedEvent,
    "candle.closed": CandleClosedEvent,
    
    # System Events
    "system.started": SystemStartedEvent,
    "system.shutdown": SystemShutdownEvent,
    "system.health_check": HealthCheckEvent,
}


def get_event_class(event_type: str):
    """Event tipi için class al"""
    return EVENT_REGISTRY.get(event_type)


def list_events() -> List[str]:
    """Tüm event tiplerini listele"""
    return list(EVENT_REGISTRY.keys())
