"""
Bot Service

Business logic for bot operations.
"""

from typing import Dict, Any
import asyncio

from core.logger import logger
from core.paper import paper_engine
from core.exchange import exchange_manager
from strategy.manager import StrategyManager
from api.schemas.bot import (
    BotStartRequest,
    BotStopRequest,
    BotResumeRequest,
    BotRemoveRequest,
    BotInfo,
    BotStatusEnum,
)


class BotService:
    """
    Bot Service.

    Business logic for bot operations:
    - Start bot
    - Stop bot
    - Resume bot
    - Remove bot
    - Get bot status
    - List bots
    """

    def __init__(self):
        self.paper_engine = paper_engine
        self.exchange_manager = exchange_manager

    async def start_bot(self, request: BotStartRequest) -> Dict[str, Any]:
        """
        Yeni bot başlat.

        Args:
            request: Bot başlatma isteği

        Returns:
            Bot başlatma yanıtı
        """
        try:
            from core.bot.bot_manager import BotConfig, MarketType, MarginType

            config = BotConfig(
                symbol=request.symbol,
                strategy_id=request.strategy_id,
                timeframe=request.timeframe,
                market_type=MarketType(request.market_type.value.lower()),
                margin_type=MarginType(request.margin_type.value.lower()),
            )

            # Bot başlat (1-to-N mimarisi)
            bot_id = self.paper_engine.start_bot(config)

            # Strateji instance'ını oluştur ve kaydet
            strategy_instance = StrategyManager.get_strategy(request.strategy_id)
            self.paper_engine.strategies[request.symbol] = strategy_instance
            self.paper_engine.active_strategies[request.symbol] = request.strategy_id

            logger.info(
                f"📚 [STRATEGY] {request.symbol} için {request.strategy_id} instance'ı kaydedildi"
            )

            # Poller'ı başlat (eğer henüz çalışmıyorsa)
            if request.symbol not in self.exchange_manager.active_pollers:
                logger.info(
                    f"🚀 [POLLER] {request.symbol} için run_strategy_poller başlatılıyor..."
                )

                poller_task = asyncio.create_task(
                    self.exchange_manager.run_strategy_poller(
                        request.symbol, request.timeframe
                    )
                )

                self.exchange_manager.active_pollers[request.symbol] = poller_task
                logger.info(f"✅ [POLLER] {request.symbol} poller başlatıldı")
            else:
                logger.debug(
                    f"ℹ️ [POLLER] {request.symbol} için poller zaten çalışıyor"
                )

            return {
                "status": "success",
                "bot_id": bot_id,
                "message": f"Bot başlatıldı: {bot_id}",
            }

        except Exception as e:
            logger.error(f"Bot başlatma hatası: {e}")
            return {"status": "error", "message": str(e)}

    async def stop_bot(self, request: BotStopRequest) -> Dict[str, Any]:
        """
        Bot durdur.

        Args:
            request: Bot durdurma isteği

        Returns:
            Bot durdurma yanıtı
        """
        try:
            success = self.paper_engine.stop_bot(request.bot_id)

            if success:
                return {
                    "status": "success",
                    "message": f"Bot durduruldu: {request.bot_id}",
                }
            else:
                return {"status": "error", "message": "Bot bulunamadı"}

        except Exception as e:
            logger.error(f"Bot durdurma hatası: {e}")
            return {"status": "error", "message": str(e)}

    async def resume_bot(self, request: BotResumeRequest) -> Dict[str, Any]:
        """
        Bot devam ettir.

        Args:
            request: Bot devam ettirme isteği

        Returns:
            Bot devam ettirme yanıtı
        """
        try:
            success = self.paper_engine.resume_bot(request.bot_id)

            if success:
                logger.info(f"▶️ Bot devam ettirildi: {request.bot_id}")
                return {
                    "status": "success",
                    "message": f"Bot devam ettirildi: {request.bot_id}",
                }
            else:
                return {
                    "status": "error",
                    "message": "Bot bulunamadı veya devam ettirilemedi",
                }

        except Exception as e:
            logger.error(f"Bot devam ettirme hatası: {e}")
            return {"status": "error", "message": str(e)}

    async def remove_bot(self, request: BotRemoveRequest) -> Dict[str, Any]:
        """
        Bot listeden kaldır.

        Args:
            request: Bot silme isteği

        Returns:
            Bot silme yanıtı
        """
        try:
            # PaperTrader.remove_bot hem botManager'dan hem de active_bots listesinden siler
            success = self.paper_engine.remove_bot(request.bot_id)

            if success:
                logger.info(f"🗑️ Bot kaldırıldı: {request.bot_id}")
                return {
                    "status": "success",
                    "message": f"Bot kaldırıldı: {request.bot_id}",
                }
            else:
                return {
                    "status": "error",
                    "message": "Bot bulunamadı veya kaldırılamadı",
                }

        except Exception as e:
            logger.error(f"Bot kaldırma hatası: {e}")
            return {"status": "error", "message": str(e)}

    async def get_bot_status(self, bot_id: str) -> Dict[str, Any]:
        """
        Bot durumunu al.

        Args:
            bot_id: Bot ID

        Returns:
            Bot durum yanıtı
        """
        try:
            status = self.paper_engine.get_bot_status(bot_id)
            return {"status": "success", "bot": status}
        except Exception as e:
            logger.error(f"Bot durum hatası: {e}")
            return {"status": "error", "message": str(e)}

    async def get_all_bots(self) -> Dict[str, Any]:
        """
        Tüm aktif botları al.

        Returns:
            Bot listesi yanıtı
        """
        try:
            bots = self.paper_engine.get_all_bots()
            return {"status": "success", "bots": bots}
        except Exception as e:
            logger.error(f"Bot listesi hatası: {e}")
            return {"status": "error", "message": str(e)}

    def _bot_to_info(self, bot_data: Dict[str, Any]) -> BotInfo:
        """
        Bot dict'i BotInfo'ya çevir.

        Args:
            bot_data: Bot dict verisi

        Returns:
            BotInfo object
        """
        return BotInfo(
            bot_id=bot_data.get("bot_id", ""),
            symbol=bot_data.get("symbol", ""),
            strategy_id=bot_data.get("strategy_id", ""),
            timeframe=bot_data.get("timeframe", "1m"),
            market_type=bot_data.get("market_type", "swap"),
            margin_type=bot_data.get("margin_type", "isolated"),
            status=BotStatusEnum(bot_data.get("status", "stopped")),
            pnl=bot_data.get("pnl", 0.0),
            margin=bot_data.get("margin", 0.0),
            trades=bot_data.get("trades", 0),
            wins=bot_data.get("wins", 0),
        )
