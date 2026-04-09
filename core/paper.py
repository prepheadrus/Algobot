"""
PaperTrader - Refactored (Event-Driven Architecture)

Eski 1,475 satırlık "God Object" iş mantığı temizlendi.
Yeni yapı:
- PositionManager, RiskEngine, BotManager instance'ları kullanır
- Event Bus'a abone olur (Pub/Sub)
- Delegation pattern ile geriye dönük uyumluluk sağlar

Usage:
    from core.paper import PaperTrader

    pt = PaperTrader()

    # Event handler'ları başlat
    await pt.start_event_handlers()

    # Eski API hala çalışır (delegation)
    pt.start_bot(symbol, strategy_id, timeframe)
"""

import asyncio
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime

from core.logger import logger
from core.config import CONFIG

# Event Bus
from shared.events import event_bus

# New Managers (Aşama 2'de oluşturuldu)
from core.trading.position_manager import PositionManager
from core.risk.risk_engine import RiskEngine, RiskConfig
from core.bot.bot_manager import BotManager, BotConfig

# Legacy imports (geriye dönük uyumluluk)
from strategy.manager import StrategyManager


class PaperTrader:
    """
    PaperTrader - Refactored (Event-Driven)

    Eski iş mantığı yeni manager'lara delegate edilir.
    Event Bus ile loose coupling sağlanır.
    """

    def __init__(
        self, initial_balance=10000.0, fee_rate_spot=0.001, fee_rate_futures=0.0004
    ):
        """
        PaperTrader initialization.

        Args:
            initial_balance: Başlangıç bakiyesi
            fee_rate_spot: Spot komisyon oranı
            fee_rate_futures: Futures komisyon oranı
        """
        # ============================================
        # YENİ MANAGER INSTANCE'LARI
        # ============================================
        risk_config = RiskConfig(
            max_risk_per_trade=CONFIG["risk_management"].get(
                "max_risk_per_trade_percent", 0.01
            ),
            max_leverage=CONFIG["risk_management"].get("max_leverage", 10),
            max_open_positions=CONFIG["risk_management"].get("max_open_positions", 5),
            max_consecutive_losses=CONFIG["risk_management"]
            .get("kill_switch", {})
            .get("max_consecutive_losses", 5),
            kill_switch_enabled=CONFIG["risk_management"]
            .get("kill_switch", {})
            .get("enabled", True),
        )

        self.position_manager = PositionManager(
            fee_rate_spot=fee_rate_spot, fee_rate_futures=fee_rate_futures
        )
        self.risk_engine = RiskEngine(config=risk_config)
        # Asenkron Risk State Yüklemesi (Paper Engine Event Loop ile Senkronizasyon)
        try:
            loop = asyncio.get_running_loop()
            if loop and loop.is_running():
                loop.create_task(self.risk_engine.load_state())
        except RuntimeError:
            pass
        self.bot_manager = BotManager()

        # ============================================
        # LEGACY COMPATIBILITY (Geriye Dönük Uyumluluk)
        # ============================================
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.free_margin = initial_balance
        self.used_margin = 0.0

        # Legacy dicts (core/exchange.py uyumluluğu)
        self.open_positions = []  # Legacy dict list
        self.trade_history = []
        self.active_bots = {}  # bot_id -> metadata
        self.active_strategies = {}  # symbol -> strategy_id
        self.strategies = {}  # symbol -> strategy_instance
        self.active_timeframes = {}  # symbol -> timeframe
        self.market_types = {}  # symbol -> market_type
        self.margin_types = {}  # symbol -> margin_type
        self.latest_decisions = {}

        # Legacy state
        self.global_confidence = 0.0
        self.volatility_shield = "SAFE"
        self.kill_switch_activated = False

        self.market_regime = "UNKNOWN"

        # Thread-safe balance updates
        self._balance_lock = asyncio.Lock()

        # Using cachetools TTLCache to avoid infinite growth memory leak
        from cachetools import TTLCache

        self._processed_trades = TTLCache(
            maxsize=10000, ttl=86400
        )  # Keep up to 10k trade IDs for 24 hours

        # ML Karar Motoru Servisi
        from core.trading.services.signal_validator import SignalValidatorService

        self.ml_models = {}  # {symbol_timeframe: trainer_instance}
        self.ml_enabled = True
        self.signal_validator = SignalValidatorService(self.ml_models)

        # Event handlers
        self._event_handlers_started = False

        logger.info("📄 PaperTrader (Refactored) initialized")

    # ========================================================================
    # EVENT HANDLERS (Pub/Sub)
    # ========================================================================

    async def start_event_handlers(self):
        """
        Event handler'ları başlat.
        Event Bus'a subscribe et.
        """
        if self._event_handlers_started:
            logger.warning("Event handler'lar zaten başlatıldı")
            return

        # Signal handler
        event_bus.subscribe("signal.generated", self.on_signal_generated)

        # Position handlers
        event_bus.subscribe("position.opened", self.on_position_opened)
        event_bus.subscribe("position.closed", self.on_position_closed)
        event_bus.subscribe("position.closed", self.risk_engine.on_position_closed)
        event_bus.subscribe("position.partial_closed", self.on_position_partial_closed)

        # Bot handlers
        event_bus.subscribe("bot.started", self.on_bot_started)
        event_bus.subscribe("bot.stopped", self.on_bot_stopped)

        # ========================================================================
        # YENİ: Live Price Event (Tick Data Pub/Sub - Circular Dependency kırıldı!)
        # ========================================================================
        event_bus.subscribe("price.updated", self.on_live_price_updated)

        self._event_handlers_started = True
        logger.info("📬 [EDA] Event handlers başlatıldı (signal, position, bot, price)")

    async def on_signal_generated(self, event):
        """
        Signal Generated Event Handler.

        Exchange'den gelen sinyal eventini dinler ve işlem açar.

        Args:
            event: SignalGeneratedEvent
        """
        try:
            payload = event.payload
            bot_id = payload["bot_id"]
            symbol = payload["symbol"]
            signal = payload["signal"]  # int olarak geliyor (0, 1, 2)
            price = payload["price"]
            timeframe = payload.get("timeframe", "1m")
            indicators = payload.get("indicators", {})
            metadata = payload.get("metadata", {})

            # HTF verisi payload'dan hemen oku (sonraki satırlarda kullanılıyor)
            htf_trends = metadata.get("htf_trends", {})
            htf_trend = metadata.get("htf_trend", "NEUTRAL")

            # Sinyal tipi belirle
            signal_type = "LONG" if signal == 2 else "SHORT" if signal == 0 else "HOLD"

            # HOLD (Bekle) ise sadece DEBUG düzeyinde logla (Terminali kirletmez)
            if signal == 1:
                logger.debug(f"📬 {symbol} ({bot_id}) Sinyal: {signal_type}")
                return

            # EĞER GERÇEK BİR SİNYAL VARSA (0 veya 2) - GÖZE ÇARPACAK ŞEKİLDE LOGLA
            logger.info("=" * 60)
            logger.info(
                f"🔔 [YENİ SİNYAL] {symbol} ({bot_id}) | YÖN: {signal_type} | FİYAT: {price:.4f}"
            )
            logger.info(f"   📊 HTF: {htf_trend} | REJİM: {self.market_regime}")
            logger.info("=" * 60)

            # Bot çalışıyor mu kontrol et
            if not self.bot_manager.is_bot_running(bot_id):
                logger.warning(f"❌ [SİNYAL RED] Bot çalışmıyor: {bot_id}")
                return

            # Strateji al
            strategy = self.strategies.get(symbol)
            if strategy is None:
                logger.warning(f"❌ [SİNYAL RED] Strateji bulunamadı: {symbol}")
                return

            # ============================================
            # HTF FİLTRE - Detaylı loglama
            # ============================================
            htf_passed = self.signal_validator.validate_htf_trend(
                symbol, htf_trends, signal
            )
            if not htf_passed:
                logger.warning(
                    f"❌ [SİNYAL RED] HTF veto: {symbol} {signal_type} | HTF={htf_trend}"
                )
                logger.warning(
                    "   ÇÖZÜM: HTF ayarlarını config.yaml'dan kapat veya HTF timeframe'i değiştir"
                )
                return
            else:
                logger.debug(f"✅ [HTF] {symbol} {signal_type} geçti: HTF={htf_trend}")

            # ============================================
            # RISK ENGINE KONTROL - Detaylı loglama
            # ============================================
            open_positions_count = len(self.position_manager.get_all_positions())
            risk_ok = self.risk_engine.can_open_position(symbol, open_positions_count)

            if not risk_ok:
                logger.warning(f"❌ [SİNYAL RED] Risk kontrolü başarısız: {symbol}")
                logger.warning(f"   Açık pozisyon sayısı: {open_positions_count}")
                logger.warning(
                    f"   Max pozisyon limiti: {self.risk_engine.config.max_open_positions}"
                )
                logger.warning(
                    f"   Kill switch aktif: {self.risk_engine.kill_switch_active}"
                )
                logger.warning(
                    f"   Ardışık kayıplar: {self.risk_engine.consecutive_losses.get(symbol, 0)}"
                )
                logger.warning(
                    f"   Max consecutive losses: {self.risk_engine.config.max_consecutive_losses}"
                )
                logger.warning(
                    "   ÇÖZÜM: config.yaml → risk_management → kill_switch.enabled = false"
                )
                return
            else:
                logger.debug(
                    f"✅ [RISK] {symbol} Risk kontrolü geçti: {open_positions_count}/{self.risk_engine.config.max_open_positions} pozisyon"
                )

            # Pozisyon zaten var mı?
            existing_position = self.position_manager.get_position(bot_id)
            if existing_position:
                logger.info(f"ℹ️ Pozisyon zaten açık: {bot_id}")
                return

            # ============================================
            # ML KARAR MOTORU (Yön Bazlı) - Detaylı loglama
            # ============================================
            # Model flag güncelleniyor (çalışma zamanı senkronizasyonu)
            self.signal_validator.ml_enabled = self.ml_enabled

            # Sinyal yönünü belirle (Yön bazlı inference için 'long' veya 'short')
            inference_direction = "long" if signal == 2 else "short" if signal == 0 else None

            ml_confirmed = False
            ml_confidence = 0.0
            ml_rec = "HOLD"
            ml_rec_norm = "HOLD"
            has_model = False

            if inference_direction:
                # ML Doğrulaması: model_id bilinçli olarak None geçilir, sistem en güncel modeli kendi bulur
                # Yeni Asimetrik Binary modele 'direction' da gönderiliyor
                ml_confirmed, ml_confidence, ml_rec, ml_rec_norm, has_model = (
                    await self.signal_validator.validate_signal_with_ml(
                        symbol, timeframe, indicators, signal, model_id=None, direction=inference_direction
                    )
                )

            # Emit ml.evaluation event to WebSocket
            from shared.events import event_bus
            from shared.events.event_bus import Event

            await event_bus.publish(
                Event(
                    type="ml.evaluation",
                    payload={
                        "bot_id": bot_id,
                        "symbol": symbol,
                        "confidence": ml_confidence,
                        "recommendation": ml_rec_norm,
                        "confirmed": ml_confirmed,
                    },
                    source="paper_engine",
                )
            )

            # Dashboard için en son kararı kaydet
            self.latest_decisions[symbol] = {
                "signal_val": signal,
                "signal_text": (
                    "LONG" if signal == 2 else "SHORT" if signal == 0 else "HOLD"
                ),
                "price": price,
                "time": datetime.utcnow().isoformat(),
                "ml_rec": ml_rec_norm,  # Normalize edilmiş halini kaydet
                "ml_confidence": ml_confidence,
                "ml_confirmed": ml_confirmed,
                "htf_trend": htf_trend,
                "has_position": False,  # Varsayılan: Pozisyon yok
            }

            # ML onayı yoksa dur - DETAYLI LOG
            if not ml_confirmed and has_model:
                ml_threshold = CONFIG.get("ml", {}).get("confidence_threshold", 0.65)
                logger.warning(f"❌ [SİNYAL RED] ML onayı yok: {symbol} {signal_type}")
                logger.warning(
                    f"   ML Recommendation: {ml_rec} (normalized: {ml_rec_norm})"
                )
                logger.warning(
                    f"   ML Confidence: {ml_confidence:.2f} (threshold: {ml_threshold:.2f})"
                )
                logger.warning(f"   ML Enabled: {self.ml_enabled}")
                logger.warning("   ÇÖZÜM 1: ML model eğit (Dashboard → ML Training)")
                logger.warning(
                    "   ÇÖZÜM 2: config.yaml → ml.enabled = false (sadece teknik sinyaller)"
                )
                logger.warning(
                    "   ÇÖZÜM 3: config.yaml → ml.confidence_threshold = 0.5 (daha düşük threshold)"
                )
                return
            elif not has_model:
                logger.info(
                    f"⏭️ [ML] {symbol} için eğitilmiş model bulunamadı. Teknik sinyal ile devam ediliyor..."
                )
            else:
                logger.info(
                    f"✅ [ML] {symbol} ML onayı alındı: {ml_rec} (confidence: {ml_confidence:.2f})"
                )

            # ============================================
            # POZİSYON AÇ (PositionManager'a delegate)
            # ============================================
            atr = indicators.get("ATR_14", price * 0.01)

            # Stop loss / take profit hesapla
            direction = "LONG" if signal == 2 else "SHORT"  # 2=LONG, 0=SHORT

            # Faz 3: Asimetrik Yön Çarpanları (Hardcoded)
            if direction == "LONG":
                tp_multiplier = 1.5
                sl_multiplier = 1.2
            else:  # SHORT
                tp_multiplier = 2.5
                sl_multiplier = 1.2

            # Stratejiden gelen stop_params'taki atr_multiplier sadece metadata olarak geçilecek
            stop_params = strategy.get_stop_params()
            atr_multiplier = stop_params.get("atr_multiplier", 3.0)

            stop_loss, take_profit = self.risk_engine.calculate_dynamic_stops(
                price=price,
                direction=direction,
                atr=atr,
                sl_multiplier=sl_multiplier,
                tp_multiplier=tp_multiplier
            )

            # --- SMC SNIPER STOP-LOSS OVERRIDE ---
            if direction == "LONG" and indicators.get("SWEEP_BULLISH", 0) == 1:
                swing_low = indicators.get("SWING_LOW")
                if swing_low and swing_low > 0:
                    stop_loss = (
                        swing_low * 0.999
                    )  # %0.1 margin below dipten likidite alımı
                    logger.info(
                        f"🎯 [SMC SNIPER] Bullish Sweep tespit edildi! Stop-Loss Swing Low altına çekildi: {stop_loss:.2f}"
                    )

            elif direction == "SHORT" and indicators.get("SWEEP_BEARISH", 0) == 1:
                swing_high = indicators.get("SWING_HIGH")
                if swing_high and swing_high > 0:
                    stop_loss = (
                        swing_high * 1.001
                    )  # %0.1 margin above tepeden likidite alımı
                    logger.info(
                        f"🎯 [SMC SNIPER] Bearish Sweep tespit edildi! Stop-Loss Swing High üstüne çekildi: {stop_loss:.2f}"
                    )

            # 1. Önce Kaldıraç hesapla (Dinamik)
            if self.ml_enabled and ml_confirmed and has_model:
                # ML Güven Skoruna Göre Dinamik Kaldıraç Hesapla
                # TIMEFRAME-AWARE: 1m/3m gibi düşük TF'lerde kaldıraç otomatik sınırlandırılır
                base_lev = CONFIG["risk_management"].get("default_leverage", 1.0)
                max_lev = CONFIG["risk_management"].get(
                    "max_leverage", 10.0
                )  # Varsayılan max
                leverage = self.risk_engine.calculate_dynamic_leverage(
                    confidence_score=ml_confidence,
                    base_leverage=base_lev,
                    max_leverage=max_lev,
                    timeframe=timeframe,  # YENİ: Timeframe bilgisi geçirildi
                )

                # Fail-Fast Prensibi: Kaldıraç sıfır gelirse işlemi anında veto et (confidence < 0.50)
                if leverage == 0.0:
                    logger.info(f"🛑 İŞLEM REDDEDİLDİ (VETO): ML Güven Skoru ({ml_confidence:.2f}) işlem eşiğinin (<0.50) altında.")
                    return
            else:
                leverage = CONFIG["risk_management"].get("default_leverage", 1.0)

            # 2. Sonra Pozisyon boyutu hesapla (Kaldıraç-Bakiye kalkanı ile)
            risk_percent = CONFIG["risk_management"].get(
                "max_risk_per_trade_percent", 0.2
            )
            size = self.risk_engine.calculate_position_size(
                account_balance=self.balance,
                entry_price=price,
                stop_loss_price=stop_loss,
                risk_percentage=risk_percent,
                leverage=leverage,
                free_margin=self.free_margin,
            )

            # Pozisyon aç
            strategy_id = self.active_strategies.get(symbol, "unknown")
            position = await self.position_manager.open_position(
                bot_id=bot_id,
                symbol=symbol,
                direction=direction,
                entry_price=price,
                size=size,
                leverage=leverage,
                stop_loss=stop_loss,
                take_profit=take_profit,
                atr=atr,
                atr_multiplier=atr_multiplier,
                strategy_name=strategy.name(),
                strategy_id=strategy_id,
                timeframe=timeframe,
            )

            if position:
                # Legacy positions güncelle
                self.open_positions = self.position_manager.legacy_positions

                # Latest decisions'da has_position'u güncelle
                if symbol in self.latest_decisions:
                    self.latest_decisions[symbol]["has_position"] = True

                logger.info(f"✅ Pozisyon açıldı: {bot_id} {direction} @ {price:.2f}")

        except Exception as e:
            logger.error(f"Signal handler hatası: {e}", exc_info=True)

    async def on_position_opened(self, event):
        """
        Position Opened Event Handler.

        Args:
            event: PositionOpenedEvent
        """
        payload = event.payload
        bot_id = payload.get("bot_id")
        symbol = payload.get("symbol")

        logger.info(f"📊 Pozisyon açıldı: {bot_id} {symbol}")

        # Bot state güncelle
        self.bot_manager.update_bot_margin(bot_id, payload.get("margin", 0.0))

    async def on_position_closed(self, event):
        """
        Position Closed Event Handler.

        Args:
            event: PositionClosedEvent
        """
        payload = event.payload
        bot_id = payload.get("bot_id")
        pnl = payload.get("pnl", 0.0)
        symbol = payload.get("symbol")

        logger.info(f"❌ Pozisyon kapatıldı: {bot_id} PnL=${pnl:.2f}")

        # Thread-safe Bakiye Güncellemesi (Race Condition Önleme)
        async with self._balance_lock:
            trade_id = payload.get("trade_id")
            if trade_id and trade_id in self._processed_trades:
                logger.warning(
                    f"⚠️ [PNL-FIX] Trade {trade_id} zaten işlenmiş. PnL atlanıyor."
                )
                return

            if trade_id:
                self._processed_trades[trade_id] = True

            self.balance += pnl
            # Free margin'i güncelle (Basit model)
            self.free_margin = self.balance
            self.used_margin = 0.0  # Bireysel botlara bakılacak

        # Risk engine'e kaydet
        self.risk_engine.record_trade_result(pnl)

        # Bot state güncelle
        self.bot_manager.record_bot_trade(bot_id, pnl)

        # Legacy positions güncelle (UI senkronizasyonu için kritik)
        self.open_positions = self.position_manager.legacy_positions

        # Trade history'yi senkronize et (position_manager'dan al)
        self.trade_history = self.position_manager.trade_history.trades

        # ============================================
        # POZİSYON KAPANDI → has_position = False
        # ============================================
        if symbol and symbol in self.latest_decisions:
            self.latest_decisions[symbol]["has_position"] = False
            self.latest_decisions[symbol][
                "position_closed_at"
            ] = datetime.utcnow().isoformat()
            logger.debug(f"📊 [SİNYAL] {symbol}: Pozisyon kapandı, HOLD moduna geçildi")

        # DATABASE'E KAYDET (TEK KAYNAK - SINGLE SOURCE OF TRUTH)
        # Bu handler DB'ye kaydeder, position_manager'da save_trade YOK
        from data.database import db_manager

        trade_data = {
            "id": payload.get("trade_id"),  # UNIQUE ID (microsecond hassasiyeti)
            "symbol": payload.get("symbol"),
            "direction": payload.get("direction"),
            "entry_price": float(payload.get("entry_price", 0)),
            "exit_price": float(payload.get("exit_price", 0)),
            "size": float(payload.get("size", 0)),
            "leverage": int(
                payload.get("leverage", 1)
            ),  # INTEGER kolon için int'e çevir
            "pnl_usd": float(payload.get("pnl", 0)),
            "pnl_percent": float(payload.get("pnl_percent", 0.0)) * 100,  # 0-1 → 0-100
            "reason": payload.get("reason"),
            "strategy_id": payload.get("strategy_id"),
            "bot_id": bot_id,
            "closed_at": payload.get("closed_at"),
        }

        # DB'ye kaydet (duplicate önleme: aynı ID varsa INSERT edilmez)
        await db_manager.save_trade(trade_data)

        # Kill switch kontrolü
        if self.risk_engine.kill_switch_active:
            self.kill_switch_activated = True
            logger.critical("🚨 KILL SWITCH AKTİF!")

    async def on_position_partial_closed(self, event):
        """
        Position Partial Closed Event Handler (Kademeli Çıkış).

        Args:
            event: PositionPartialClosedEvent
        """
        payload = event.payload
        bot_id = payload.get("bot_id")
        symbol = payload.get("symbol")
        pnl = payload.get("pnl", 0.0)
        size_closed = payload.get("size_closed", 0.0)
        remaining_size = payload.get("remaining_size", 0.0)
        exit_price = payload.get("exit_price", 0.0)
        direction = payload.get("direction")

        # 1. Gerçekleşmiş (Realized) Kârı Hesapla: Komisyon (Taker) ve Kayma (Slippage) düşülür
        # %0.04 Taker Fee + %0.01 Slippage
        is_spot = self.margin_types.get(symbol, "isolated") == "spot"
        fee_rate = 0.001 if is_spot else 0.0004
        slippage_rate = 0.0001

        position_value = size_closed * exit_price
        fee = position_value * fee_rate
        slippage_cost = position_value * slippage_rate

        # Net PnL (Komisyonlar düştükten sonra bakiye yansıması)
        net_pnl = pnl - fee - slippage_cost

        logger.info(f"✨ Kısmi Çıkış (%50 Kâr Alma): {bot_id} | Net PnL=${net_pnl:.2f} (Brüt: ${pnl:.2f}, Komisyon/Kayma: ${fee+slippage_cost:.2f})")

        # 2. Bakiyeye ekle (Serbest Bakiye)
        async with self._balance_lock:
            self.balance += net_pnl
            self.free_margin = self.balance

        # 3. Veritabanına kaydet (Kısmi Trade Kaydı)
        from data.database import db_manager

        # Partial close ID = trade_{bot_id}_partial_{timestamp}
        timestamp_us = int(datetime.utcnow().timestamp() * 1000000)
        trade_id = f"trade_{bot_id}_partial_{timestamp_us}"

        # Partial kaydında entry_price olarak güncel event bilgisini bulmamız gerekir.
        # Position objesi içinden eski entry price'ı bulalım:
        entry_price = exit_price  # fallback
        strategy_id = self.active_strategies.get(symbol, "unknown")
        leverage = 1
        position = self.position_manager.get_position(bot_id)
        if position:
            entry_price = position.entry_price
            leverage = position.leverage

        trade_data = {
            "id": trade_id,
            "symbol": symbol,
            "direction": direction,
            "entry_price": float(entry_price),
            "exit_price": float(exit_price),
            "size": float(size_closed),
            "leverage": int(leverage),
            "pnl_usd": float(net_pnl),
            "pnl_percent": float(payload.get("pnl_percent", 0.0)) * 100,  # 0-1 → 0-100
            "reason": "PARTIAL_TAKE_PROFIT",
            "strategy_id": strategy_id,
            "bot_id": bot_id,
            "closed_at": datetime.utcnow().isoformat(),
        }
        await db_manager.save_trade(trade_data)

        # Trade History'ye (RAM) Kısmi Kaydı da ekle
        from core.trading.entities.trade import Trade, PositionDirection
        partial_trade = Trade(
            id=trade_id,
            bot_id=bot_id,
            symbol=symbol,
            direction=PositionDirection(direction),
            entry_price=entry_price,
            exit_price=exit_price,
            size=size_closed,
            leverage=leverage,
            pnl=net_pnl,
            pnl_percent=payload.get("pnl_percent", 0.0),
            commission=fee + slippage_cost,
            opened_at=datetime.utcnow(),  # tam bilinmiyor
            closed_at=datetime.utcnow(),
            reason="PARTIAL_TAKE_PROFIT",
            strategy_id=strategy_id,
            metadata={}
        )
        self.trade_history.append(partial_trade)

        # 4. Legacy positions (self.open_positions) Senkronizasyonu
        # Geriye dönük uyumluluk için, `open_positions` listesindeki size ve stop_loss değerini ez
        positions_updated = False
        for pos in self.position_manager.legacy_positions:
            if pos.get("bot_id") == bot_id:
                pos["size"] = remaining_size
                pos["margin"] = pos["margin"] * 0.5  # Marjin de yarıya düşüyor
                # Breakeven Stop Loss (Giriş Fiyatı) güncelleniyor:
                # EDA'da PositionManager update_trailing_stop içinde zaten yapıldı, buradan kopyalanır.
                if position:
                    pos["stop_loss"] = position.stop_loss
                else:
                    pos["stop_loss"] = entry_price # Fallback breakeven
                pos["partial_profit_taken"] = True
                positions_updated = True
                break

        if positions_updated:
            self.open_positions = list(self.position_manager.legacy_positions)

    async def on_bot_started(self, event):
        """Bot Started Event Handler"""
        payload = event.payload
        logger.info(f"🚀 Bot başlatıldı: {payload.get('bot_id')}")

    async def on_bot_stopped(self, event):
        """Bot Stopped Event Handler"""
        payload = event.payload
        logger.info(f"🛑 Bot durduruldu: {payload.get('bot_id')}")

    async def on_live_price_updated(self, event):
        """
        Live Price Updated Event Handler.

        WebSocket'ten gelen gerçek zamanlı fiyat eventini dinler.
        Trailing stop ve likidasyon kontrollerini tetikler.

        EVENT-DRIVEN MİMARİ:
        - Exchange LivePriceUpdatedEvent fırlatır
        - Paper.py bu event'i dinler
        - DIRECT CALL YOK (circular dependency kırıldı!)

        Args:
            event: LivePriceUpdatedEvent
        """
        try:
            payload = event.payload
            symbol = payload.get("symbol")
            current_price = payload.get("price")

            # Sembol veya fiyat geçersizse atla
            if not symbol or current_price is None:
                return

            # Katı 0.0 ve NaN/inf kontrolü (Garbage In / Garbage Out Koruması)
            if pd.isna(current_price) or float(current_price) <= 0.0:
                logger.warning(
                    f"⚠️ [FİYAT HATASI] Geçersiz fiyat verisi atlandı: {symbol} - Fiyat: {current_price}"
                )
                return

            # Tip Dönüşümü (Güvenli)
            current_price = float(current_price)

            # Sembol normalizasyonu ve Açık pozisyonları kontrol et
            # KATI EŞLEŞTİRME: BTC/USDT:USDT formatları nedeniyle symbol.split(':')[0]
            # ile de eşleşebilecek şekilde (veya birebir) kontrol et
            positions_to_update = []

            # normalize the incoming symbol for safe matching
            incoming_base_symbol = symbol.split(":")[0] if ":" in symbol else symbol

            for pos in self.open_positions:
                pos_symbol = pos.get("symbol")
                if not pos_symbol:
                    continue

                pos_base_symbol = (
                    pos_symbol.split(":")[0] if ":" in pos_symbol else pos_symbol
                )

                # Tam eşleşme veya base eşleşmesi
                if pos_symbol == symbol or pos_base_symbol == incoming_base_symbol:
                    positions_to_update.append(pos)

            if positions_to_update:
                # Trailing stop ve likidasyon kontrolleri
                await self.update_live_prices(symbol, current_price)

                logger.debug(
                    f"💰 [EDA] {symbol} fiyat güncellendi: ${current_price:.2f} ({len(positions_to_update)} pozisyon)"
                )

        except Exception as e:
            logger.error(f"❌ [EDA] on_live_price_updated hatası: {e}")

    # ========================================================================
    # DELEGATION METHODS (Legacy API Uyumluluğu)
    # ========================================================================

    def start_bot(self, config: BotConfig) -> str:
        """
        Bot başlat (legacy API -> BotManager'a delegate).

        Args:
            config: Bot yapılandırması (BotConfig objesi)

        Returns:
            Bot ID
        """
        # Bot başlat
        bot_id = self.bot_manager.start_bot(config)

        # Legacy tracking
        self.active_bots[bot_id] = {
            "symbol": config.symbol,
            "strategy_id": config.strategy_id,
            "timeframe": config.timeframe,
            "market_type": config.market_type.value,
            "margin_type": config.margin_type.value,
            "status": "running",
        }
        self.active_strategies[config.symbol] = config.strategy_id
        self.active_timeframes[config.symbol] = config.timeframe
        self.market_types[config.symbol] = config.market_type.value
        self.margin_types[config.symbol] = config.margin_type.value

        # Strateji instance al
        strategy = StrategyManager.get_strategy(config.strategy_id)
        self.strategies[config.symbol] = strategy

        logger.info(f"🚀 Bot başlatıldı: {bot_id}")
        return bot_id

    def stop_bot(self, bot_id: str) -> bool:
        """Bot durdur (BotManager'a delegate)"""
        return self.bot_manager.stop_bot(bot_id)

    def resume_bot(self, bot_id: str) -> bool:
        """Bot devam et (BotManager'a delegate)"""
        return self.bot_manager.resume_bot(bot_id)

    def remove_bot(self, bot_id: str) -> bool:
        """Bot sil (BotManager'a delegate)"""
        success = self.bot_manager.remove_bot(bot_id)
        if success and bot_id in self.active_bots:
            del self.active_bots[bot_id]
        return success

    async def close_position_by_symbol(self, symbol: str) -> bool:
        """
        Pozisyon kapat (PositionManager'a delegate).

        Args:
            symbol: Sembol

        Returns:
            True ise başarılı
        """
        # Sembol için pozisyon bul
        positions = self.position_manager.get_positions_by_symbol(symbol)
        if not positions:
            return False

        # İlk pozisyonu kapat
        position = positions[0]
        current_price = position.metadata.get("current_price", position.entry_price)

        await self.position_manager.close_position(
            bot_id=position.bot_id, exit_price=current_price, reason="manual"
        )

        # Legacy update
        self.open_positions = self.position_manager.legacy_positions

        return True

    # ========================================================================
    # LEGACY COMPATIBILITY (Eski Metodlar - Delegate)
    # ========================================================================

    def set_market_type(self, symbol: str, market_type: str):
        """Legacy compatibility: set market type for symbol"""
        self.market_types[symbol] = market_type
        logger.debug(f"Piyasa tipi ayarlandı: {symbol} -> {market_type}")

    def set_margin_type(self, symbol: str, margin_type: str):
        """Legacy compatibility: set margin type for symbol"""
        self.margin_types[symbol] = margin_type
        logger.debug(f"Marjin tipi ayarlandı: {symbol} -> {margin_type}")

    def set_strategy(self, strategy_id: str, symbol: str = None, timeframe: str = "1m"):
        """
        Strateji ayarla (Legacy API).

        Args:
            strategy_id: Strateji ID
            symbol: Sembol
            timeframe: Zaman dilimi
        """
        if symbol:
            self.active_strategies[symbol] = strategy_id
            self.active_timeframes[symbol] = timeframe

            # Strateji instance al ve sakla
            try:
                strategy = StrategyManager.get_strategy(strategy_id)
                self.strategies[symbol] = strategy
                logger.info(
                    f"✅ Strateji atandı: {symbol} -> {strategy_id} ({timeframe})"
                )
            except Exception as e:
                logger.error(f"Strateji atama hatası: {e}")
        else:
            logger.warning("set_strategy: Sembol belirtilmedi")

    def update_strategy_params(
        self, symbol: str, new_params: dict, sharpe: float = None
    ):
        """
        WFO tarafından bulunan yeni parametreleri aktif stratejiye uygular.
        Botu durdurmadan canlı parametre güncellemesi yapar.

        Args:
            symbol: Sembol adı
            new_params: Yeni parametre sözlüğü
            sharpe: Beklenen Sharpe oranı (opsiyonel)

        Returns:
            bool: Güncelleme başarılıysa True
        """
        if symbol not in self.strategies or self.strategies[symbol] is None:
            logger.warning(
                f"⚠️ [WFO] {symbol} için strateji bulunamadı, parametre güncellenemedi."
            )
            return False

        strategy = self.strategies[symbol]
        timeframe = self.active_timeframes.get(symbol, "1m")

        # Stratejinin update_params metodunu çağır
        if hasattr(strategy, "update_params"):
            old_params = strategy.params.copy() if hasattr(strategy, "params") else {}
            strategy.update_params(new_params)

            # Log çıktısı
            changes = []
            for key in new_params:
                if key in old_params and old_params[key] != new_params[key]:
                    changes.append(f"{key}: {old_params[key]} -> {new_params[key]}")

            if changes:
                changes_str = ", ".join(changes)
                sharpe_str = f" (Beklenen Sharpe: {sharpe:.2f})" if sharpe else ""
                logger.info(
                    f"🎯 [WFO-AUTO-TUNE] {symbol} ({timeframe}) piyasa rejimine adapte oldu! "
                    f"Yeni Parametreler: {changes_str}{sharpe_str}"
                )

                # Arayüz için son kararı güncelle
                if symbol in self.latest_decisions:
                    self.latest_decisions[symbol]["wfo_updated"] = True
                    self.latest_decisions[symbol]["wfo_params"] = new_params
                    self.latest_decisions[symbol][
                        "updated_at"
                    ] = datetime.now().isoformat()  # YENİ: Timestamp

                return True
            else:
                logger.debug(f"⚠️ [WFO] {symbol} parametre değişikliği yok.")
                return False
        else:
            logger.error(
                f"❌ [WFO] {symbol} stratejisi update_params() metodunu desteklemiyor!"
            )
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        İstatistikler (tüm manager'lardan).

        Returns:
            Dict with all stats
        """
        # Toplam unrealized PnL, kullanılan marjin ve pozisyon değeri
        unrealized_pnl = 0.0
        used_margin = 0.0
        total_notional = 0.0

        for pos in self.position_manager.legacy_positions:
            unrealized_pnl += pos.get("unrealized_usd", 0.0)
            used_margin += pos.get("margin", 0.0)

            # Notional = Size * Current Price (veya Entry Price)
            current_price = pos.get("current_price", pos.get("entry_price", 0.0))
            size = pos.get("size", 0.0)
            total_notional += size * current_price

        equity = self.balance + unrealized_pnl
        free_margin = self.balance - used_margin

        # Legacy değişkenleri güncelle (UI için değil, iç mantık için gerekebilir)
        self.used_margin = used_margin
        self.free_margin = free_margin

        # KRİTİK DÜZELTME: total_trades'i trade_history'den al (senkronizasyon!)
        # position_manager.total_trades sadece bir sayaç, trade_history gerçek kaynak!
        # NOT: self.trade_history bir liste (position_manager.trade_history.trades)
        total_trades = (
            len(self.trade_history)
            if isinstance(self.trade_history, list)
            else len(self.trade_history.trades)
        )

        # Kazanan trade'leri say
        if isinstance(self.trade_history, list):
            winning_trades = len(
                [t for t in self.trade_history if hasattr(t, "pnl") and t.pnl > 0]
            )
            total_pnl = sum(t.pnl for t in self.trade_history if hasattr(t, "pnl"))
            total_commission = sum(
                t.commission for t in self.trade_history if hasattr(t, "commission")
            )
        else:
            winning_trades = len([t for t in self.trade_history.trades if t.pnl > 0])
            total_pnl = sum(t.pnl for t in self.trade_history.trades)
            total_commission = sum(t.commission for t in self.trade_history.trades)

        return {
            "balance": self.balance,
            "free_margin": free_margin,
            "used_margin": used_margin,
            "equity": equity,
            "unrealized_pnl": unrealized_pnl,
            "total_trades": total_trades,  # trade_history'den
            "total_wins": winning_trades,  # trade_history'den
            "win_rate": winning_trades / max(1, total_trades),
            "total_pnl": total_pnl,  # trade_history'den
            "total_commission": total_commission,  # trade_history'den
            "total_notional": total_notional,
            "bot_stats": self.bot_manager.get_stats(),
            "risk_stats": self.risk_engine.get_stats(),
            "position_stats": self.position_manager.get_stats(),
        }

    def get_strategy_report(self) -> List[Dict[str, Any]]:
        """
        Kapanan işlemleri baz alarak stratejilerin karnesini (röntgenini) çıkarır.
        YENİ: Profit Factor ve Max Drawdown metrikleri eklendi.
        YENİ: Veritabanından da oku (eski oturumlar için).

        Returns:
            List of strategy reports sorted by total_pnl
        """
        # 1. Önce RAM'deki trade_history'yi kontrol et
        trades_list = (
            self.trade_history.trades
            if hasattr(self.trade_history, "trades")
            else self.trade_history
        )

        # 2. Eğer RAM boşsa, veritabanından oku
        if not trades_list or (
            hasattr(trades_list, "__len__") and len(trades_list) == 0
        ):
            try:
                from data.database import db_manager
                import asyncio

                loop = asyncio.get_event_loop()
                db_trades = loop.run_until_complete(
                    db_manager.get_recent_trades(limit=1000)
                )

                if db_trades:
                    trades_list = db_trades
                else:
                    return []
            except Exception as e:
                logger.error(f"❌ Veritabanından okuma hatası: {e}")
                return []

        # 3. StrategyReporterService aracılığıyla rapor üret
        from core.trading.services.reporter import strategy_reporter_service

        return strategy_reporter_service.generate_report(trades_list)

    def get_all_bots(self) -> List[Dict[str, Any]]:
        """
        Tüm botları listele. BotManager'dan güncel verileri (PnL, İşlem Sayısı vb.) çeker.
        YENİ: WFO aktif parametreleri de eklendi.

        Returns:
            Bot listesi (detaylı metriklerle birlikte + WFO parametreleri)
        """
        bots = []
        for bot_id, bot in self.bot_manager.bots.items():
            state = bot.state
            config = bot.config

            # PnL yüzde hesapla (Bakiye bazlı basit oran)
            pnl_percent = (
                (state.pnl / self.initial_balance * 100)
                if self.initial_balance > 0
                else 0.0
            )

            # ============================================
            # WFO AKTİF PARAMETRELERİ (YENİ!)
            # ============================================
            active_params = {}
            last_wfo_optimization = None

            # Sembol için aktif stratejiyi bul ve parametrelerini al
            symbol = config.symbol
            if symbol in self.strategies and self.strategies[symbol] is not None:
                strategy = self.strategies[symbol]
                if hasattr(strategy, "params"):
                    active_params = strategy.params.copy()

            # latest_decisions'dan WFO bilgilerini al
            if symbol in self.latest_decisions:
                decision = self.latest_decisions[symbol]
                if decision.get("wfo_updated"):
                    last_wfo_optimization = decision.get(
                        "updated_at", decision.get("time")
                    )

            bots.append(
                {
                    "bot_id": bot_id,
                    "symbol": config.symbol,
                    "strategy_id": config.strategy_id,
                    "timeframe": config.timeframe,
                    "market_type": config.market_type.value,
                    "margin_type": config.margin_type.value,
                    "status": state.status.value,
                    "pnl": round(state.pnl, 2),
                    "pnl_percent": round(pnl_percent, 2),
                    "margin": round(state.margin, 2),
                    "trades": state.trades,
                    "wins": state.wins,
                    "started_at": bot.started_at.isoformat(),
                    "last_signal_at": (
                        state.last_signal_at.isoformat()
                        if state.last_signal_at
                        else None
                    ),
                    # WFO Telemetri (YENİ!)
                    "active_params": active_params,
                    "last_wfo_optimization": last_wfo_optimization,
                }
            )
        return bots

    def get_bot_status(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """
        Tek bir botun durumunu al.
        YENİ: WFO aktif parametreleri de eklendi.
        """
        bot = self.bot_manager.get_bot(bot_id)
        if not bot:
            return None

        state = bot.state
        config = bot.config

        pnl_percent = (
            (state.pnl / self.initial_balance * 100)
            if self.initial_balance > 0
            else 0.0
        )

        # ============================================
        # WFO AKTİF PARAMETRELERİ (YENİ!)
        # ============================================
        active_params = {}
        last_wfo_optimization = None

        # Sembol için aktif stratejiyi bul ve parametrelerini al
        symbol = config.symbol
        if symbol in self.strategies and self.strategies[symbol] is not None:
            strategy = self.strategies[symbol]
            if hasattr(strategy, "params"):
                active_params = strategy.params.copy()

        # latest_decisions'dan WFO bilgilerini al
        if symbol in self.latest_decisions:
            decision = self.latest_decisions[symbol]
            if decision.get("wfo_updated"):
                last_wfo_optimization = decision.get("updated_at", decision.get("time"))

        return {
            "bot_id": bot_id,
            "symbol": config.symbol,
            "strategy_id": config.strategy_id,
            "timeframe": config.timeframe,
            "market_type": config.market_type.value,
            "margin_type": config.margin_type.value,
            "status": state.status.value,
            "pnl": round(state.pnl, 2),
            "pnl_percent": round(pnl_percent, 2),
            "margin": round(state.margin, 2),
            "trades": state.trades,
            "wins": state.wins,
            "started_at": bot.started_at.isoformat(),
            "last_signal_at": (
                state.last_signal_at.isoformat() if state.last_signal_at else None
            ),
            # WFO Telemetri (YENİ!)
            "active_params": active_params,
            "last_wfo_optimization": last_wfo_optimization,
        }

    # ========================================================================
    # LEGACY COMPATIBILITY (Eski Metodlar - Delegate)
    # ========================================================================

    async def update_live_prices(
        self,
        symbol: str,
        current_price: float,
        current_high: float = None,
        current_low: float = None,
    ):
        """
        Canlı fiyat güncelleme + SL/TP/Likidasyon kontrolü.

        Args:
            symbol: Sembol
            current_price: Şu anki kapanış fiyatı
            current_high: Mum high (trailing stop için)
            current_low: Mum low (trailing stop için)
        """
        # KATI KORUMA: NaN ve <= 0 değerleri bu seviyede bile engelle (0 PnL bug'ı için)
        if (
            current_price is None
            or pd.isna(current_price)
            or float(current_price) <= 0.0
        ):
            logger.warning(
                f"⚠️ [FİYAT HATASI] Geçersiz veya 0 fiyat (update_live_prices): {symbol} - {current_price}"
            )
            return

        current_price = float(current_price)

        # High/Low fallback: Mumdan gelmiyorsa tahmini değer kullan
        candle_high = (
            float(current_high)
            if current_high is not None and float(current_high) > 0
            else current_price
        )
        candle_low = (
            float(current_low)
            if current_low is not None and float(current_low) > 0
            else current_price
        )

        # Per-Symbol Locking for update_live_prices (Trailing Stop updates & Take Profit)
        async with self.position_manager.get_lock(symbol):
            # Legacy positions güncelle
            positions_to_close = []  # Kapatılacaklar (döngü içinde silme)
            positions_updated = False  # Güncelleme yapıldı mı?

            # Katı eşleştirme için sembol
            incoming_base_symbol = symbol.split(":")[0] if ":" in symbol else symbol

            for pos in list(
                self.position_manager.legacy_positions
            ):  # list() kopyasını al
                pos_symbol = pos.get("symbol")
                if not pos_symbol:
                    continue

                pos_base_symbol = (
                    pos_symbol.split(":")[0] if ":" in pos_symbol else pos_symbol
                )

                # Eğer eşleşmiyorsa atla
                if pos_symbol != symbol and pos_base_symbol != incoming_base_symbol:
                    continue

                bot_id = pos.get("bot_id")

                # Position objesine bak (asıl lock orada)
                position = self.position_manager.get_position(bot_id)
                if position and position.metadata.get("is_closing", False):
                    # Zaten kapanıyor, işlem yapma
                    continue

                pos["current_price"] = current_price
                positions_updated = True

                # 1. Trailing stop güncelle (Yeni Asenkron Immutable Metod ile)
                if position:
                    updated_position = await self.position_manager.update_trailing_stop(
                        position, candle_high, candle_low
                    )

                    # DİKKAT: Position nesnesi immutable olduğu için, dönen yeni instance'ı kaydetmeliyiz.
                    self.position_manager.positions[bot_id] = updated_position

                    # Legacy uyumluluğu için SL güncelle (veya diğer değerler)
                    if updated_position.stop_loss != position.stop_loss:
                        pos['stop_loss'] = updated_position.stop_loss

                # 2. PnL hesapla
                roe, pnl_usd = self.position_manager.get_unrealized_pnl_legacy(
                    pos, current_price
                )
                pos["unrealized_usd"] = pnl_usd
                pos["pnl_percent"] = roe

                # ========================================================================
                # YENİ: position.updated EVENT FIRLAT (UI gerçek zamanlı güncelleme)
                # ========================================================================
                try:
                    from shared.events import event_bus
                    from shared.events.event_bus import Event

                    await event_bus.publish(
                        Event(
                            type="position.updated",
                            payload={
                                "bot_id": bot_id,
                                "symbol": symbol,
                                "updates": {
                                    "current_price": current_price,
                                    "unrealized_usd": pnl_usd,
                                    "pnl_percent": roe,
                                    "stop_loss": pos.get("stop_loss"),
                                    "take_profit": pos.get("take_profit"),
                                    "highest_seen": pos.get("highest_seen"),
                                    "lowest_seen": pos.get("lowest_seen"),
                                },
                            },
                            source="paper_engine",
                        )
                    )
                    logger.debug(
                        f"📊 [EDA] {symbol} position.updated event fırlatıldı (bot_id={bot_id})"
                    )
                except Exception as e:
                    logger.error(
                        f"❌ [EDA] position.updated event fırlatma hatası: {e}"
                    )
                # ========================================================================

                # 3. Likidasyon kontrolü
                if self.position_manager.check_liquidation_legacy(pos, current_price):
                    positions_to_close.append((bot_id, current_price, "LİKİDASYON"))
                    continue

                # 4. Stop Loss / Take Profit kontrolü
                sl = pos.get("stop_loss")
                tp = pos.get("take_profit")
                direction = pos.get("direction", "LONG")

                if direction == "LONG":
                    if sl and current_price <= sl:
                        positions_to_close.append((bot_id, sl, "STOP LOSS"))
                    elif tp and current_price >= tp:
                        positions_to_close.append((bot_id, tp, "TAKE PROFIT"))
                else:  # SHORT
                    if sl and current_price >= sl:
                        positions_to_close.append((bot_id, sl, "STOP LOSS"))
                    elif tp and current_price <= tp:
                        positions_to_close.append((bot_id, tp, "TAKE PROFIT"))

            # paper_engine.open_positions'u senkronize et (UI güncellemesi için kritik!)
            if positions_updated:
                self.open_positions = list(self.position_manager.legacy_positions)

        # Lock dışına çıkıldı, artık kapatma işlemlerini güvenle yapabiliriz (Deadlock önleme)
        # Kapatılacak pozisyonları işle
        closed_bot_ids = set()  # Bu tick'te kapatılan bot'lar (duplicate önleme)

        for bot_id, exit_price, reason in positions_to_close:
            # Bu bot zaten bu tick'te kapatıldı mı? (duplicate önleme)
            if bot_id in closed_bot_ids:
                logger.debug(f"⚠️ {bot_id} bu tick'te zaten kapatıldı, atlanıyor.")
                continue

            # Position hala mevcut mu kontrol et (başka bir tick kapatmış olabilir)
            if bot_id not in self.position_manager.positions:
                logger.debug(f"⚠️ {bot_id} pozisyonu zaten kapatılmış, atlanıyor.")
                continue

            # ============================================
            # KRİTİK DÜZELTME: exit_price'ı pozisyon dict'inden al!
            # update_live_prices'a gelen current_price TÜM pozisyonlar için aynı!
            # ============================================
            position_obj = self.position_manager.get_position(bot_id)
            if position_obj:
                # Pozisyonun kendi SL/TP fiyatını kullan (current_price DEĞİL!)
                if reason == "STOP LOSS":
                    exit_price = position_obj.stop_loss or exit_price
                elif reason == "TAKE PROFIT":
                    exit_price = position_obj.take_profit or exit_price
                # reason == 'LİKİDASYON' ise current_price kullan (market fiyat)

                position_symbol = position_obj.symbol
            else:
                position_symbol = symbol

            logger.info(
                f"🔴 [{reason}] {position_symbol} @ {exit_price:.4f} | Bot: {bot_id}"
            )

            try:
                trade = await self.position_manager.close_position(
                    bot_id=bot_id, exit_price=exit_price, reason=reason
                )

                if trade:
                    # Bu bot'u kapatılanlar listesine ekle (duplicate önleme)
                    closed_bot_ids.add(bot_id)

                    # KRİTİK: Her kapatmadan SONRA hemen senkronize et (UI için)
                    self.open_positions = list(self.position_manager.legacy_positions)
                    logger.debug(
                        f"✅ Pozisyon kapandı, UI senkronize: {len(self.open_positions)} pozisyon"
                    )

                    # Durum güncellemeleri artık on_position_closed event handler'ında yapılıyor (EDA)
                    # Buraya sadece nihai loglamayı bırakıyoruz
                    if trade.pnl > 0:
                        logger.info(
                            f"✅ {reason}: +${trade.pnl:.2f} ({trade.pnl_percent:.2%}) KAR"
                        )
                    else:
                        logger.warning(
                            f"⚠️ {reason}: ${trade.pnl:.2f} ({trade.pnl_percent:.2%}) ZARAR"
                        )
                else:
                    # close_position None döndürdü - muhtemelen zaten kapanıyor veya hata
                    logger.warning(
                        f"⚠️ Pozisyon kapatılamadı: {bot_id} (zaten kapanıyor olabilir)"
                    )

            except Exception as e:
                logger.error(f"❌ Pozisyon kapatma hatası ({bot_id}): {e}")
                import traceback

                logger.debug(traceback.format_exc())

        # POZİSYON KAPANDIKTAN SONRA SENKRONİZASYON (KRİTİK!)
        # Close işleminden sonra open_positions'u güncelle
        self.open_positions = list(self.position_manager.legacy_positions)
        logger.debug(
            f"📊 Open positions senkronize edildi: {len(self.open_positions)} pozisyon"
        )

    @property
    def timeframe(self):
        """Legacy compatibility"""
        return (
            next(iter(self.active_timeframes.values()))
            if self.active_timeframes
            else "1m"
        )


# ============================================================================
# GLOBAL INSTANCE (Singleton)
# ============================================================================

# Eski kodlarla uyumluluk için global instance
paper_engine = PaperTrader()
