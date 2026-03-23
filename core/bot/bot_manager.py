"""
Bot Manager

Bot orkestrasyonu ve lifecycle yönetimi.
SORUMLULUK: Bot başlatma, durdurma, devam ettirme, silme, durum takibi

Bu modül, core/paper.py içindeki 1-to-N bot yönetimi mantığını devralır.

Usage:
    from core.bot.bot_manager import BotManager, BotConfig
    
    config = BotConfig(
        symbol="BTC/USDT",
        strategy_id="trend_master",
        timeframe="1m",
        market_type="swap"
    )
    
    bm = BotManager()
    
    # Bot başlat
    bot_id = bm.start_bot(config)
    
    # Bot durdur
    bm.stop_bot(bot_id)
    
    # Bot devam et
    bm.resume_bot(bot_id)
    
    # Bot sil
    bm.remove_bot(bot_id)
    
    # Aktif botları al
    bots = bm.get_active_bots()
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import asyncio

from core.logger import logger


class BotStatus(str, Enum):
    """Bot durumu"""
    RUNNING = "running"
    STOPPED = "stopped"
    PAUSED = "paused"
    ERROR = "error"


class MarketType(str, Enum):
    """Piyasa tipi"""
    SPOT = "spot"
    SWAP = "swap"
    FUTURE = "future"


class MarginType(str, Enum):
    """Marjin tipi"""
    ISOLATED = "isolated"
    CROSS = "cross"


@dataclass
class BotConfig:
    """
    Bot yapılandırması.
    
    Attributes:
        symbol: Sembol (örn: BTC/USDT)
        strategy_id: Strateji ID
        timeframe: Zaman dilimi
        market_type: Piyasa tipi
        margin_type: Marjin tipi
        leverage: Kaldıraç
        risk_per_trade: İşlem başına risk
    """
    symbol: str
    strategy_id: str
    timeframe: str = "1m"
    market_type: MarketType = MarketType.SWAP
    margin_type: MarginType = MarginType.ISOLATED
    leverage: float = 1.0
    risk_per_trade: float = 0.01
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict'e çevir"""
        return {
            'symbol': self.symbol,
            'strategy_id': self.strategy_id,
            'timeframe': self.timeframe,
            'market_type': self.market_type.value,
            'margin_type': self.margin_type.value,
            'leverage': self.leverage,
            'risk_per_trade': self.risk_per_trade
        }


@dataclass
class BotState:
    """
    Bot durumu.
    
    Attributes:
        status: Bot durumu
        pnl: PnL
        margin: Kullanılan marjin
        trades: İşlem sayısı
        wins: Kazanan işlem sayısı
        last_signal_at: Son sinyal zamanı
        error_message: Hata mesajı (varsa)
    """
    status: BotStatus = BotStatus.STOPPED
    pnl: float = 0.0
    margin: float = 0.0
    trades: int = 0
    wins: int = 0
    last_signal_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict'e çevir"""
        return {
            'status': self.status.value,
            'pnl': self.pnl,
            'margin': self.margin,
            'trades': self.trades,
            'wins': self.wins,
            'last_signal_at': self.last_signal_at.isoformat() if self.last_signal_at else None,
            'error_message': self.error_message
        }


@dataclass
class BotInfo:
    """
    Bot metadata.
    
    Attributes:
        bot_id: Benzersiz bot ID
        config: Bot yapılandırması
        state: Bot durumu
        started_at: Başlatılma zamanı
        metadata: Ek veriler
    """
    bot_id: str
    config: BotConfig
    state: BotState
    started_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Dict'e çevir"""
        return {
            'bot_id': self.bot_id,
            'config': self.config.to_dict(),
            'state': self.state.to_dict(),
            'started_at': self.started_at.isoformat(),
            'metadata': self.metadata
        }


class BotManager:
    """
    Bot Manager.
    
    Bot orchestration:
    - Bot başlatma
    - Bot durdurma
    - Bot devam ettirme
    - Bot silme
    - Durum takibi
    """
    
    def __init__(self):
        """Bot Manager initialization"""
        self.bots: Dict[str, BotInfo] = {}  # bot_id -> BotInfo
        self.bot_counter = 0
        
        # İstatistikler
        self.total_bots_started = 0
        self.total_bots_stopped = 0
        
        logger.info("🤖 Bot Manager initialized")
    
    # ========================================================================
    # BOT LIFECYCLE
    # ========================================================================
    
    def start_bot(
        self,
        config: BotConfig,
        bot_id: Optional[str] = None
    ) -> str:
        """
        Yeni bot başlat.
        
        Args:
            config: Bot yapılandırması
            bot_id: Benzersiz bot ID (None ise otomatik oluşturulur)
        
        Returns:
            Bot ID
        
        Raises:
            ValueError: Geçersiz config
        """
        # Validation
        if not config.symbol or not config.symbol.strip():
            raise ValueError("symbol boş olamaz")
        
        if not config.strategy_id or not config.strategy_id.strip():
            raise ValueError("strategy_id boş olamaz")
        
        # Bot ID oluştur (otomatik)
        if bot_id is None:
            self.bot_counter += 1
            bot_id = f"{config.symbol}_{config.strategy_id}_{config.timeframe}_{self.bot_counter}"
        
        # Bot zaten var mı kontrol et
        if bot_id in self.bots:
            logger.warning(f"Bot zaten mevcut: {bot_id}")
            return bot_id
        
        # BotInfo oluştur
        bot_info = BotInfo(
            bot_id=bot_id,
            config=config,
            state=BotState(status=BotStatus.RUNNING),
            started_at=datetime.utcnow()
        )
        
        # Kaydet
        self.bots[bot_id] = bot_info
        self.total_bots_started += 1
        
        logger.info(
            f"🚀 Bot başlatıldı: {bot_id} | "
            f"{config.symbol} | {config.strategy_id} | {config.timeframe}"
        )
        
        return bot_id
    
    def stop_bot(self, bot_id: str, reason: str = "user_requested") -> bool:
        """
        Bot durdur.
        
        Args:
            bot_id: Bot ID
            reason: Durdurma nedeni
        
        Returns:
            True ise başarılı
        """
        if bot_id not in self.bots:
            logger.warning(f"Bot bulunamadı: {bot_id}")
            return False
        
        bot = self.bots[bot_id]
        
        # Zaten durmuş mu?
        if bot.state.status == BotStatus.STOPPED:
            logger.debug(f"Bot zaten durmuş: {bot_id}")
            return True
        
        # Durum güncelle
        bot.state.status = BotStatus.STOPPED
        self.total_bots_stopped += 1
        
        logger.info(f"🛑 Bot durduruldu: {bot_id} | Neden: {reason}")
        
        return True
    
    def resume_bot(self, bot_id: str) -> bool:
        """
        Bot devam ettir (paused -> running).
        
        Args:
            bot_id: Bot ID
        
        Returns:
            True ise başarılı
        """
        if bot_id not in self.bots:
            logger.warning(f"Bot bulunamadı: {bot_id}")
            return False
        
        bot = self.bots[bot_id]
        
        # Sadece paused veya stopped botlar devam edebilir
        if bot.state.status not in [BotStatus.PAUSED, BotStatus.STOPPED]:
            logger.warning(f"Bot devam edemez: {bot_id} (status={bot.state.status.value})")
            return False
        
        # Durum güncelle
        bot.state.status = BotStatus.RUNNING
        
        logger.info(f"▶️ Bot devam ediyor: {bot_id}")
        
        return True
    
    def pause_bot(self, bot_id: str) -> bool:
        """
        Bot geçici olarak duraklat.
        
        Args:
            bot_id: Bot ID
        
        Returns:
            True ise başarılı
        """
        if bot_id not in self.bots:
            logger.warning(f"Bot bulunamadı: {bot_id}")
            return False
        
        bot = self.bots[bot_id]
        
        # Sadece running botlar duraklatılabilir
        if bot.state.status != BotStatus.RUNNING:
            logger.warning(f"Bot duraklatılamaz: {bot_id} (status={bot.state.status.value})")
            return False
        
        # Durum güncelle
        bot.state.status = BotStatus.PAUSED
        
        logger.info(f"⏸️ Bot duraklatıldı: {bot_id}")
        
        return True
    
    def remove_bot(self, bot_id: str) -> bool:
        """
        Bot sil.
        
        Args:
            bot_id: Bot ID
        
        Returns:
            True ise başarılı
        """
        if bot_id not in self.bots:
            logger.warning(f"Bot bulunamadı: {bot_id}")
            return False
        
        # Önce durdur
        self.stop_bot(bot_id, reason="removed")
        
        # Sil
        del self.bots[bot_id]
        
        logger.info(f"🗑️ Bot silindi: {bot_id}")
        
        return True
    
    # ========================================================================
    # BOT STATE UPDATES
    # ========================================================================
    
    def update_bot_pnl(self, bot_id: str, pnl: float):
        """
        Bot PnL güncelle.
        
        Args:
            bot_id: Bot ID
            pnl: PnL
        """
        if bot_id in self.bots:
            self.bots[bot_id].state.pnl = pnl
    
    def update_bot_margin(self, bot_id: str, margin: float):
        """
        Bot marjin güncelle.
        
        Args:
            bot_id: Bot ID
            margin: Marjin
        """
        if bot_id in self.bots:
            self.bots[bot_id].state.margin = margin
    
    def record_bot_trade(self, bot_id: str, pnl: float):
        """
        Bot işlemi kaydet.
        
        Args:
            bot_id: Bot ID
            pnl: PnL
        """
        if bot_id not in self.bots:
            return
        
        bot = self.bots[bot_id]
        bot.state.trades += 1
        
        if pnl > 0:
            bot.state.wins += 1
        
        bot.state.pnl += pnl
    
    def record_bot_signal(self, bot_id: str):
        """
        Bot sinyali kaydet.
        
        Args:
            bot_id: Bot ID
        """
        if bot_id in self.bots:
            self.bots[bot_id].state.last_signal_at = datetime.utcnow()
    
    def set_bot_error(self, bot_id: str, error_message: str):
        """
        Bot hatası set et.
        
        Args:
            bot_id: Bot ID
            error_message: Hata mesajı
        """
        if bot_id in self.bots:
            bot = self.bots[bot_id]
            bot.state.status = BotStatus.ERROR
            bot.state.error_message = error_message
            
            logger.error(f"❌ Bot hatası: {bot_id} | {error_message}")
    
    # ========================================================================
    # BOT QUERIES
    # ========================================================================
    
    def get_bot(self, bot_id: str) -> Optional[BotInfo]:
        """
        Bot bilgisi al.
        
        Args:
            bot_id: Bot ID
        
        Returns:
            BotInfo veya None
        """
        return self.bots.get(bot_id)
    
    def get_active_bots(self) -> List[BotInfo]:
        """
        Aktif botlar (running).
        
        Returns:
            List of BotInfo
        """
        return [
            bot for bot in self.bots.values()
            if bot.state.status == BotStatus.RUNNING
        ]
    
    def get_bots_by_symbol(self, symbol: str) -> List[BotInfo]:
        """
        Sembol'e göre botlar.
        
        Args:
            symbol: Sembol
        
        Returns:
            List of BotInfo
        """
        return [bot for bot in self.bots.values() if bot.config.symbol == symbol]
    
    def get_bots_by_strategy(self, strategy_id: str) -> List[BotInfo]:
        """
        Strateji'ye göre botlar.
        
        Args:
            strategy_id: Strateji ID
        
        Returns:
            List of BotInfo
        """
        return [bot for bot in self.bots.values() if bot.config.strategy_id == strategy_id]
    
    def get_bots_by_status(self, status: BotStatus) -> List[BotInfo]:
        """
        Durum'a göre botlar.
        
        Args:
            status: Bot durumu
        
        Returns:
            List of BotInfo
        """
        return [bot for bot in self.bots.values() if bot.state.status == status]
    
    def bot_exists(self, bot_id: str) -> bool:
        """
        Bot mevcut mu?
        
        Args:
            bot_id: Bot ID
        
        Returns:
            True ise mevcut
        """
        return bot_id in self.bots
    
    def is_bot_running(self, bot_id: str) -> bool:
        """
        Bot çalışıyor mu?
        
        Args:
            bot_id: Bot ID
        
        Returns:
            True ise çalışıyor
        """
        bot = self.bots.get(bot_id)
        return bot is not None and bot.state.status == BotStatus.RUNNING
    
    # ========================================================================
    # STATS & REPORTING
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Bot istatistikleri.
        
        Returns:
            Dict with all stats
        """
        bots_by_status = {}
        for status in BotStatus:
            count = len(self.get_bots_by_status(status))
            bots_by_status[status.value] = count
        
        return {
            'total_bots': len(self.bots),
            'active_bots': len(self.get_active_bots()),
            'bots_by_status': bots_by_status,
            'total_started': self.total_bots_started,
            'total_stopped': self.total_bots_stopped
        }
    
    def get_bot_summary(self, bot_id: str) -> Optional[str]:
        """
        Bot özeti (log için).
        
        Args:
            bot_id: Bot ID
        
        Returns:
            Summary string veya None
        """
        bot = self.bots.get(bot_id)
        if bot is None:
            return None
        
        state = bot.state
        config = bot.config
        
        return (
            f"Bot Summary: {bot_id} | "
            f"{config.symbol} | {config.strategy_id} | {config.timeframe} | "
            f"Status: {state.status.value} | "
            f"PnL: ${state.pnl:.2f} | "
            f"Trades: {state.trades} | "
            f"Wins: {state.wins}"
        )
    
    def list_bots(self) -> List[Dict[str, Any]]:
        """
        Tüm botları listele.
        
        Returns:
            List of bot dicts
        """
        return [bot.to_dict() for bot in self.bots.values()]


# ============================================================================
# LEGACY COMPATIBILITY (core/paper.py uyumluluğu)
# ============================================================================

class LegacyBotManager:
    """
    Legacy Bot Manager (dict-based).
    core/paper.py ile uyumluluk için.
    """
    
    def __init__(self):
        self.active_bots: Dict[str, Dict] = {}  # bot_id -> metadata
        self.bot_positions: Dict[str, List] = {}  # bot_id -> positions
        self.bot_state: Dict[str, Dict] = {}  # bot_id -> state
    
    def start_bot(
        self,
        bot_id: str,
        symbol: str,
        strategy_id: str,
        timeframe: str,
        market_type: str = "swap"
    ) -> str:
        """Legacy bot başlatma"""
        self.active_bots[bot_id] = {
            'symbol': symbol,
            'strategy_id': strategy_id,
            'timeframe': timeframe,
            'market_type': market_type,
            'status': 'running',
            'started_at': datetime.utcnow()
        }
        
        self.bot_positions[bot_id] = []
        self.bot_state[bot_id] = {
            'pnl': 0.0,
            'margin': 0.0,
            'trades': 0,
            'wins': 0
        }
        
        logger.info(f"🚀 [1-to-N] Bot başlatıldı: {bot_id}")
        return bot_id
    
    def stop_bot(self, bot_id: str) -> bool:
        """Legacy bot durdurma"""
        if bot_id in self.active_bots:
            self.active_bots[bot_id]['status'] = 'stopped'
            logger.info(f"🛑 [1-to-N] Bot durduruldu: {bot_id}")
            return True
        return False
    
    def remove_bot(self, bot_id: str) -> bool:
        """Legacy bot silme"""
        self.stop_bot(bot_id)
        
        if bot_id in self.active_bots:
            del self.active_bots[bot_id]
        if bot_id in self.bot_positions:
            del self.bot_positions[bot_id]
        if bot_id in self.bot_state:
            del self.bot_state[bot_id]
        
        logger.info(f"🗑️ [1-to-N] Bot silindi: {bot_id}")
        return True
    
    def get_active_bots_for_symbol(self, symbol: str) -> List[str]:
        """Sembol için aktif botları al"""
        return [
            bot_id for bot_id, bot in self.active_bots.items()
            if bot['symbol'] == symbol and bot['status'] == 'running'
        ]
    
    def is_bot_running(self, bot_id: str) -> bool:
        """Bot çalışıyor mu?"""
        bot = self.active_bots.get(bot_id)
        return bot is not None and bot.get('status') == 'running'
