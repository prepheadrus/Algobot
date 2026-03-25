"""
Position Manager

Pozisyon lifecycle yönetimi.
SORUMLULUK: Pozisyon aç, kapat, güncelle, PnL hesapla

Bu modül, core/paper.py içindeki pozisyon yönetimi mantığını devralır.
Position, Trade, Order Value Objects kullanır.

Usage:
    from core.trading.position_manager import PositionManager
    from core.trading.entities import Position, PositionDirection
    
    pm = PositionManager()
    
    # Pozisyon aç
    position = pm.open_position(
        bot_id="bot_123",
        symbol="BTC/USDT",
        direction=PositionDirection.LONG,
        entry_price=50000.0,
        size=0.1,
        leverage=5.0,
        stop_loss=49000.0,
        take_profit=52000.0
    )
    
    # Trailing stop güncelle
    pm.update_trailing_stop(position, current_high=51000.0, current_low=50500.0)
    
    # Unrealized PnL hesapla
    pnl = pm.get_unrealized_pnl(position, current_price=51000.0)
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from shared.events.event_bus import event_bus, Event
from decimal import Decimal
import asyncio

from core.logger import logger
from core.trading.entities.position import Position, PositionDirection
from shared.events.events import PositionPartialClosedEvent, StopLossUpdatedEvent
from core.trading.entities.trade import Trade, TradeHistory
from core.trading.entities.order import Order, OrderType, OrderSide, OrderStatus
from strategy.risk import RiskManagement


class PositionManager:
    """
    Position Manager.
    
    Pozisyon lifecycle yönetimi:
    - Pozisyon açma
    - Pozisyon kapatma
    - Trailing stop güncelleme
    - PnL hesaplama
    - Likidasyon kontrolü
    """
    
    def __init__(self, fee_rate_spot: float = 0.001, fee_rate_futures: float = 0.0004):
        """
        Args:
            fee_rate_spot: Spot komisyon oranı (%0.1)
            fee_rate_futures: Futures komisyon oranı (%0.04)
        """
        self.positions: Dict[str, Position] = {}  # bot_id -> Position
        self.legacy_positions: List[Dict] = []  # core/paper.py ile uyumluluk için
        self.trade_history = TradeHistory()
        
        self.fee_rate_spot = fee_rate_spot
        self.fee_rate_futures = fee_rate_futures
        
        # İstatistikler
        self.total_trades = 0
        self.total_wins = 0
        self.total_pnl = 0.0
        self.total_commission = 0.0
        
        self._locks: Dict[str, asyncio.Lock] = {}

        logger.info("📊 Position Manager initialized")
    
    def get_lock(self, symbol: str) -> asyncio.Lock:
        """
        Get or create an asyncio.Lock for the given symbol.
        Used for thread-safe operations on a per-symbol basis.
        """
        if symbol not in self._locks:
            self._locks[symbol] = asyncio.Lock()
        return self._locks[symbol]

    # ========================================================================
    # POZİSYON AÇMA
    # ========================================================================
    
    async def open_position(
        self,
        bot_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        size: float,
        leverage: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        margin_type: str = "isolated",
        atr: float = 0.0,
        atr_multiplier: float = 2.0,
        strategy_name: str = "Unknown",
        strategy_id: str = "unknown",
        timeframe: str = "1m"
    ) -> Optional[Position]:
        """
        Yeni pozisyon aç.
        
        Args:
            bot_id: Bot ID
            symbol: Sembol (örn: BTC/USDT)
            direction: Yön (LONG/SHORT)
            entry_price: Giriş fiyatı
            size: Pozisyon boyutu (coin miktarı)
            leverage: Kaldıraç
            stop_loss: Stop loss fiyatı
            take_profit: Take profit fiyatı
            margin_type: Marjin tipi (isolated/cross)
            atr_multiplier: ATR çarpanı
            strategy_name: Strateji adı
            strategy_id: Strateji ID
            timeframe: Timeframe
        
        Returns:
            Position object veya None
        """
        try:
            async with self.get_lock(symbol):
                return await self._open_position_internal(
                    bot_id, symbol, direction, entry_price, size, leverage,
                    stop_loss, take_profit, margin_type, atr, atr_multiplier,
                    strategy_name, strategy_id, timeframe
                )
        except Exception as e:
            logger.error(f"Pozisyon açma hatası: {e}")
            return None

    async def _open_position_internal(
        self, bot_id: str, symbol: str, direction: str, entry_price: float, size: float,
        leverage: float, stop_loss: Optional[float], take_profit: Optional[float],
        margin_type: str, atr: float, atr_multiplier: float, strategy_name: str,
        strategy_id: str, timeframe: str
    ) -> Optional[Position]:
        try:
            # Direction enum'a çevir
            direction_enum = PositionDirection(direction.upper())
            
            # Slipaj simülasyonu (gerçekçi trading)
            if direction == "LONG":
                execution_price = entry_price * 1.0001  # %0.01 yukarıdan al
            else:  # SHORT
                execution_price = entry_price * 0.9999  # %0.01 aşağıdan sat
            
            # Komisyon hesapla
            is_spot = margin_type == "spot"
            fee_rate = self.fee_rate_spot if is_spot else self.fee_rate_futures
            position_value = execution_price * size
            fee = position_value * fee_rate
            
            # Marjin hesapla
            margin = position_value / leverage
            
            # Likidasyon fiyatı hesapla
            liq_price = self._calculate_liquidation_price(
                execution_price, leverage, direction, margin_type, margin, position_value
            )
            
            # Position oluştur
            position = Position(
                bot_id=bot_id,
                symbol=symbol,
                direction=direction_enum,
                entry_price=execution_price,
                size=size,
                leverage=leverage,
                opened_at=datetime.utcnow(),
                stop_loss=stop_loss,
                take_profit=take_profit,
                margin=margin,
                commission=fee,
                metadata={
                    'atr': atr,
                    'atr_multiplier': atr_multiplier,
                    'highest_seen': execution_price if direction == "LONG" else execution_price,
                    'lowest_seen': execution_price if direction == "SHORT" else execution_price,
                    'strategy': strategy_name,
                    'strategy_id': strategy_id,
                    'timeframe': timeframe,
                    'margin_type': margin_type,
                    'liquidation_price': liq_price,
                    'is_closing': False
                }
            )
            
            # Position'ı kaydet
            self.positions[bot_id] = position

            # Legacy positions (core/paper.py uyumluluğu)
            legacy_pos = self._position_to_legacy(position, fee)
            self.legacy_positions.append(legacy_pos)

            # Initial trailing stop seviyelerini set et (açılışta)
            if direction.upper() == "LONG":
                legacy_pos['highest_seen'] = execution_price
                if stop_loss and stop_loss < execution_price:
                    legacy_pos['stop_loss'] = stop_loss
            else:  # SHORT
                legacy_pos['lowest_seen'] = execution_price
                if stop_loss and stop_loss > execution_price:
                    legacy_pos['stop_loss'] = stop_loss

            # SL/TP güvenli formatlama (None olabilir)
            sl_str = f"{stop_loss:.2f}" if stop_loss is not None else "Yok"
            tp_str = f"{take_profit:.2f}" if take_profit is not None else "Yok"

            logger.info(
                f"📊 Pozisyon açıldı: {bot_id} | {direction} | "
                f"{symbol} @ {execution_price:.2f} | Lev: {leverage}x | "
                f"SL: {sl_str} | TP: {tp_str}"
            )

            # paper_engine.open_positions güncelle (UI sync için kritik!)
            try:
                from core.paper import paper_engine
                if hasattr(paper_engine, 'open_positions'):
                    paper_engine.open_positions = list(self.legacy_positions)
            except:
                pass  # paper_engine henüz initialize edilmemiş olabilir

            return position

        except Exception as e:
            logger.error(f"Dahili pozisyon açma hatası: {e}")
            return None

    def _calculate_liquidation_price(
        self,
        entry_price: float,
        leverage: float,
        direction: str,
        margin_type: str,
        margin: float,
        position_value: float
    ) -> float:
        """
        Likidasyon fiyatı hesapla.
        
        LONG: Fiyat aşağı düşürse likidasyon (entry'nin altı)
        SHORT: Fiyat yukarı çıkarsa likidasyon (entry'nin üstü)
        """
        if leverage <= 0:
            return 0.0
        
        if margin_type == "isolated":
            # Binance USDT-M Vadeli İşlemler Temel Formülü (Tahmini)
            # Maintenance Margin Rate (MMR) genelde %0.5 (0.005) civarıdır
            # LONG Liq Price = Entry * (1 - (1/Leverage) + MMR)
            mmr = 0.005
            if direction == "LONG":
                liq_price = entry_price * (1 - (1 / leverage) + mmr)
            else:  # SHORT
                liq_price = entry_price * (1 + (1 / leverage) - mmr)
        else:
            # Cross marjin (basitleştirilmiş)
            risk_buffer = margin / position_value if position_value > 0 else 0
            mmr = 0.005
            if direction == "LONG":
                liq_price = entry_price * (1 - risk_buffer + mmr)
            else:  # SHORT
                liq_price = entry_price * (1 + risk_buffer - mmr)
        
        return max(0.0, liq_price)
    
    def _position_to_legacy(self, position: Position, fee: float) -> Dict:
        """
        Position'ı legacy dict formatına çevir (core/paper.py uyumluluğu).
        
        Args:
            position: Position object
            fee: Komisyon
        
        Returns:
            Dict (legacy format)
        """
        return {
            'symbol': position.symbol,
            'direction': position.direction.value,
            'entry_price': position.entry_price,
            'current_price': position.entry_price,
            'size': position.size,
            'notional_value': position.entry_price * position.size,
            'leverage': position.leverage,
            'margin': position.margin,
            'margin_type': position.metadata.get('margin_type', 'isolated'),
            'stop_loss': position.stop_loss,
            'take_profit': position.take_profit,
            'liquidation_price': position.metadata.get('liquidation_price', 0.0),
            'pnl_percent': 0.0,
            'unrealized_usd': -fee,
            'atr': position.metadata.get('atr', 0.0),
            'atr_multiplier': position.metadata.get('atr_multiplier', 3.0),
            'highest_seen': position.metadata.get('highest_seen', position.entry_price),
            'lowest_seen': position.metadata.get('lowest_seen', position.entry_price),
            'strategy': position.metadata.get('strategy', 'Unknown'),
            'strategy_id': position.metadata.get('strategy_id', 'unknown'),
            'timeframe': position.metadata.get('timeframe', '1m'),
            'is_closing': False,
            'bot_id': position.bot_id
        }
    
    # ========================================================================
    # POZİSYON KAPATMA
    # ========================================================================
    
    async def close_position(
        self,
        bot_id: str,
        exit_price: float,
        reason: str = "manual",
        commission: Optional[float] = None
    ) -> Optional[Trade]:
        """
        Pozisyon kapat.

        Args:
            bot_id: Bot ID
            exit_price: Çıkış fiyatı
            reason: Kapatma nedeni
            commission: Komisyon (None ise hesaplanır)

        Returns:
            Trade object veya None
        """
        # FIRST CHECK: Overhead'i azaltmak için lock öncesi kontrol
        if bot_id not in self.positions:
            logger.warning(f"Pozisyon bulunamadı (Lock öncesi): {bot_id}")
            return None

        position_symbol = self.positions[bot_id].symbol

        async with self.get_lock(position_symbol):
            # Double-Check Locking: Kilit alındıktan sonra pozisyon hala var mı kontrolü
            if bot_id not in self.positions:
                logger.warning(f"Pozisyon zaten kapatılmış (Double-Check): {bot_id}")
                return None

            position = self.positions[bot_id]

            # Double close kilidi - Sadece logla, bloke ETME (zaten positions_to_close listesinde)
            if position.metadata.get('is_closing', False):
                logger.warning(f"⚠️ Pozisyon zaten kapanıyor ama tekrar kapatma deneniyor: {bot_id}")
                # Bloke etme, devam et - belki önceki kapatma başarısız oldu

            # Kilit set et
            position.metadata['is_closing'] = True

            close_success = False  # Kapatma başarılı mı?

            try:
                # Komisyon hesapla
                if commission is None:
                    is_spot = position.metadata.get('margin_type', 'isolated') == 'spot'
                    fee_rate = self.fee_rate_spot if is_spot else self.fee_rate_futures
                    commission = position.size * exit_price * fee_rate

                # Trade oluştur (Position.close() metodu)
                trade = position.close(exit_price, reason, commission)

                # Trade history'ye ekle
                self.trade_history.add(trade)

                # İstatistikleri güncelle
                self._update_statistics(trade)

                # Position'ı sil (güvenli yöntem - dict'ten)
                if bot_id in self.positions:
                    del self.positions[bot_id]

                # Legacy positions'dan sil (güvenli yöntem - remove ile)
                self._remove_legacy_position_safe(bot_id)

                logger.info(
                    f"❌ Pozisyon kapatıldı: {bot_id} | "
                    f"PnL: ${trade.pnl:.2f} ({trade.pnl_percent:.2%}) | "
                    f"Neden: {reason}"
                )

                close_success = True  # Başarılı

                # Event yayınla (on_position_closed handler'ı DB'ye kaydedecek)
                # ✅ DÜZELTME: await kullan (asyncio.create_task YASAK - race condition!)
                from shared.events import event_bus
                from shared.events.event_bus import Event

                event = Event(
                    type="position.closed",
                    payload={
                        "bot_id": bot_id,
                        "symbol": trade.symbol,
                        "pnl": trade.pnl,
                        "pnl_percent": trade.pnl_percent,
                        "reason": reason,
                        "exit_price": trade.exit_price,
                        "entry_price": trade.entry_price,
                        "size": trade.size,
                        "leverage": trade.leverage,
                        "direction": trade.direction.value,
                        "trade_id": trade.id,
                        "strategy_id": trade.strategy_id,
                        "closed_at": trade.closed_at.isoformat()
                    },
                    source="position_manager"
                )

                await event_bus.publish(event)

                # DB'ye kaydetme BURADA YAPILMIYOR (on_position_closed'da yapılacak)
                # Duplicate kayıt önleme: SADECE EVENT ÜZERİNDEN

                return trade

            except Exception as e:
                logger.error(f"❌ Pozisyon kapatma hatası ({bot_id}): {e}")
                import traceback
                logger.error(traceback.format_exc())

                # Hata durumunda kilidi AÇ (tekrar denenebilir olsun)
                if bot_id in self.positions:
                    self.positions[bot_id].metadata['is_closing'] = False

                # Legacy position kilidini de aç
                for legacy_pos in self.legacy_positions:
                    if legacy_pos.get('bot_id') == bot_id:
                        legacy_pos['is_closing'] = False
                        break

                return None

            finally:
                # Eğer kapatma başarısız olduysa, kilidi sıfırla (zombie önleme)
                if not close_success and bot_id in self.positions:
                    logger.warning(f"⚠️ [ZOMBIE KORUMA] {bot_id} kapatma başarısız, kilit sıfırlanıyor.")
                    self.positions[bot_id].metadata['is_closing'] = False

                    # Legacy position kilidini de sıfırla
                    for legacy_pos in self.legacy_positions:
                        if legacy_pos.get('bot_id') == bot_id:
                            legacy_pos['is_closing'] = False
                            break
    
    def _remove_legacy_position(self, bot_id: str):
        """Legacy positions'dan sil (güvenli yöntem - remove ile)"""
        for pos in list(self.legacy_positions):  # list() kopyasını al (iteration hatası önleme)
            if pos.get('bot_id') == bot_id:
                if pos in self.legacy_positions:  # Double check (race condition önleme)
                    self.legacy_positions.remove(pos)  # index değil, obje ile sil
                    logger.debug(f"✅ Legacy pozisyon silindi: {bot_id}")
                break

    def _remove_legacy_position_safe(self, bot_id: str):
        """
        Legacy positions'dan güvenli şekilde sil (zombie önleme).

        Args:
            bot_id: Silinecek pozisyonun bot ID'si

        Returns:
            bool: Silme başarılıysa True, yoksa False
        """
        try:
            for pos in list(self.legacy_positions):
                if pos.get('bot_id') == bot_id:
                    if pos in self.legacy_positions:  # Güvenlik kontrolü (ValueError önleme)
                        self.legacy_positions.remove(pos)
                        logger.debug(f"✅ Legacy pozisyon güvenli silindi: {bot_id}")
                    return True

            logger.warning(f"⚠️ Legacy pozisyon bulunamadı: {bot_id}")
            return False

        except Exception as e:
            logger.error(f"❌ Legacy pozisyon silme hatası ({bot_id}): {e}")
            return False
    
    def _update_statistics(self, trade: Trade):
        """
        İstatistikleri güncelle.
        
        Args:
            trade: Trade object
        """
        self.total_trades += 1
        
        if trade.pnl > 0:
            self.total_wins += 1
        
        self.total_pnl += trade.pnl
        self.total_commission += trade.commission
    
    # ========================================================================
    # TRAILING STOP GÜNCELLEME
    # ========================================================================

    async def update_trailing_stop(
        self,
        position: Position,
        current_high: float,
        current_low: float
    ) -> Optional[Position]:
        """
        3 Aşamalı Dinamik Risk Yönetimi ile Trailing stop güncelle (immutable - yeni instance döner).

        AŞAMA 1: Kısmi Kâr Alma (50% TP)
        AŞAMA 2: Başa Baş (Breakeven) Koruması
        AŞAMA 3: İz Süren Stop (Trailing) - Breakeven Korumalı

        LONG:
            - Yeni zirve kontrolü
            - Zirveden (ATR × Çarpan) çıkar
            - Sadece yukarı taşı

        SHORT:
            - Yeni dip kontrolü
            - Dipten (ATR × Çarpan) ekle
            - Sadece aşağı taşı

        Args:
            position: Position object
            current_high: Mum high fiyatı
            current_low: Mum low fiyatı

        Returns:
            Güncellenmiş Position (yeni instance)
        """
        import dataclasses
        from core.logger import logger

        # Mevcut fiyatı belirle (LONG için high, SHORT için low)
        current_price = current_high if position.direction == PositionDirection.LONG else current_low

        # ========================================================================
        # AŞAMA 1: KISMI KÂR ALMA (50% TP)
        # ========================================================================
        if position.should_take_partial_profit(current_price):
            logger.info(
                f"[RISK] 3 Aşamalı Kâr Koruma ve Throttle Aktif - AŞAMA 1: "
                f"{position.symbol} Kısmi kâr alma tetiklendi! "
                f"Fiyat: ${current_price:.2f}, TP: ${position.take_profit:.2f}"
            )

            # Kapanacak miktarı hesapla (%50)
            size_closed = position.size * 0.5
            remaining_size = position.size - size_closed

            # PnL hesapla
            pnl = position.unrealized_pnl(current_price) * 0.5
            pnl_percent = position.unrealized_pnl_percent(current_price)

            # Bayrağı ve boyutu güncelle (immutable)
            # Not: margin de yarıya inmeli (size ile orantılı)
            position = dataclasses.replace(
                position,
                size=remaining_size,
                margin=position.margin * 0.5,
                partial_profit_taken=True
            )

            # Event fırlat
            partial_event = PositionPartialClosedEvent(
                bot_id=position.bot_id,
                symbol=position.symbol,
                direction=position.direction,
                exit_price=current_price,
                size_closed=size_closed,
                pnl=pnl,
                pnl_percent=pnl_percent,
                remaining_size=remaining_size
            )
            await event_bus.publish(partial_event.to_event())

        # ========================================================================
        # AŞAMA 2: BAŞA BAŞ (BREAKEVEN) KORUMASI
        # ========================================================================
        atr = position.metadata.get('atr', 0.0)
        if atr > 0 and position.should_activate_breakeven(current_price, atr):
            logger.info(
                f"[RISK] 3 Aşamalı Kâr Koruma ve Throttle Aktif - AŞAMA 2: "
                f"{position.symbol} Breakeven koruması aktif edildi! "
                f"Fiyat: ${current_price:.2f}, Entry: ${position.entry_price:.2f}"
            )
            # Eski stop loss
            old_stop = position.stop_loss

            # Breakeven aktif et (immutable)
            old_stop_loss = position.stop_loss
            position = position.activate_breakeven(commission_buffer=0.001)



        # ========================================================================
        # AŞAMA 3: İZ SÜREN STOP (TRAILING) - BREAKEVEN KORUMALI
        # ========================================================================
        atr_multiplier = position.metadata.get('atr_multiplier', 2.0)
        updated_position = position.update_trailing_stop_with_protection(
            current_price=current_price,
            atr=atr,
            atr_multiplier=atr_multiplier
        )

        # Stop loss güncellenmişse logla ve event fırlat
        if updated_position.stop_loss != position.stop_loss:
            logger.debug(
                f"[RISK] 3 Aşamalı Kâr Koruma - AŞAMA 3: "
                f"{position.symbol} Trailing stop güncellendi: ${position.stop_loss:.2f} → ${updated_position.stop_loss:.2f}"
            )

            # Event fırlat
            sl_event = StopLossUpdatedEvent(
                bot_id=updated_position.bot_id,
                symbol=updated_position.symbol,
                direction=updated_position.direction,
                old_stop=position.stop_loss,
                new_stop=updated_position.stop_loss,
                current_price=current_price
            )
            await event_bus.publish(sl_event.to_event())

        return updated_position
    
    def update_trailing_stop_legacy(
        self,
        pos: Dict,
        current_high: float,
        current_low: float,
        current_price: float = None
    ):
        """
        Legacy trailing stop güncelleme (dict için).
        core/paper.py uyumluluğu.

        TRAILING STOP MANTIĞI:
        - LONG: Fiyat yükseldiğinde SL yukarı taşı, asla aşağı taşıma
        - SHORT: Fiyat düştüğünde SL aşağı taşı, asla yukarı taşıma
        - Break-even: Kar PnL'ye geçince SL'yi giriş seviyesine taşı

        Args:
            pos: Position dict (legacy format)
            current_high: Mum high
            current_low: Mum low
            current_price: Mevcut fiyat (break-even kontrolü için)
        """
        entry_price = pos['entry_price']
        # current_price verilmezse high/low ortalaması kullan
        if current_price is None:
            current_price = (current_high + current_low) / 2

        if pos['direction'] == "LONG":
            # LONG: Yeni zirve kontrolü
            if current_high > pos['highest_seen']:
                pos['highest_seen'] = current_high
                new_stop = current_high - (pos['atr'] * pos['atr_multiplier'])

                # Sadece yukarı taşı (trailing stop mantığı)
                # stop_loss None ise direkt set et
                if pos['stop_loss'] is None or new_stop > pos['stop_loss']:
                    pos['stop_loss'] = new_stop
                    logger.debug(f"[TRAILING STOP] {pos['symbol']} LONG stop yukarı: {pos['stop_loss']:.2f}")

            # Break-even: Kar PnL'ye geçince SL'yi giriş seviyesine taşı
            if pos['stop_loss'] is not None and pos['stop_loss'] < entry_price and current_price > entry_price:
                old_sl = pos['stop_loss']
                pos['stop_loss'] = entry_price
                logger.debug(f"[BREAK-EVEN] {pos['symbol']} LONG SL giriş seviyesine taşındı: {old_sl:.2f} → {pos['stop_loss']:.2f}")

        else:  # SHORT
            # SHORT: Yeni dip kontrolü
            if current_low < pos['lowest_seen']:
                pos['lowest_seen'] = current_low
                new_stop = current_low + (pos['atr'] * pos['atr_multiplier'])

                # Sadece aşağı taşı (trailing stop mantığı)
                # stop_loss None ise direkt set et
                if pos['stop_loss'] is None or new_stop < pos['stop_loss']:
                    pos['stop_loss'] = new_stop
                    logger.debug(f"[TRAILING STOP] {pos['symbol']} SHORT stop aşağı: {pos['stop_loss']:.2f}")

            # Break-even: Kar PnL'ye geçince SL'yi giriş seviyesine taşı
            if pos['stop_loss'] is not None and pos['stop_loss'] > entry_price and current_price < entry_price:
                old_sl = pos['stop_loss']
                pos['stop_loss'] = entry_price
                logger.debug(f"[BREAK-EVEN] {pos['symbol']} SHORT SL giriş seviyesine taşındı: {old_sl:.2f} → {pos['stop_loss']:.2f}")
    
    # ========================================================================
    # PnL HESAPLAMA
    # ========================================================================
    
    def get_unrealized_pnl(self, position: Position, current_price: float) -> float:
        """
        Realize olmamış PnL hesapla.
        
        Args:
            position: Position object
            current_price: Şu anki fiyat
        
        Returns:
            PnL ($)
        """
        return position.unrealized_pnl(current_price)
    
    def get_unrealized_pnl_legacy(self, pos: Dict, current_price: float) -> Tuple[float, float]:
        """
        Legacy PnL hesaplama (dict için).
        
        Args:
            pos: Position dict
            current_price: Şu anki fiyat
        
        Returns:
            (pnl_percent, pnl_usd)
        """
        if pos['direction'] == "LONG":
            pnl_usd = (current_price - pos['entry_price']) * pos['size']
            pnl_percent = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
        else:  # SHORT
            pnl_usd = (pos['entry_price'] - current_price) * pos['size']
            pnl_percent = ((pos['entry_price'] - current_price) / pos['entry_price']) * 100
        
        # Kaldıraçlı ROE
        roe = pnl_percent * pos['leverage']
        
        return roe, pnl_usd
    
    # ========================================================================
    # LIKIDASYON KONTROLÜ
    # ========================================================================
    
    def check_liquidation(self, position: Position, current_price: float) -> bool:
        """
        Likidasyon kontrolü.
        
        Args:
            position: Position object
            current_price: Şu anki fiyat
        
        Returns:
            True ise likidasyon
        """
        liq_price = position.metadata.get('liquidation_price', 0.0)
        
        if position.direction == PositionDirection.LONG:
            return current_price <= liq_price
        else:  # SHORT
            return current_price >= liq_price
    
    def check_liquidation_legacy(self, pos: Dict, current_price: float) -> bool:
        """
        Legacy likidasyon kontrolü.
        
        Args:
            pos: Position dict
            current_price: Şu anki fiyat
        
        Returns:
            True ise likidasyon
        """
        liq_price = pos.get('liquidation_price', 0.0)
        
        if pos['direction'] == "LONG":
            return current_price <= liq_price
        else:  # SHORT
            return current_price >= liq_price
    
    # ========================================================================
    # EXIT CONDITION (STOP LOSS / TAKE PROFIT)
    # ========================================================================
    
    def check_exit_condition(
        self,
        position: Position,
        current_price: float
    ) -> Tuple[bool, str, float]:
        """
        Çıkış koşulu kontrolü (stop loss / take profit).

        Args:
            position: Position object
            current_price: Şu anki fiyat

        Returns:
            (should_close: bool, reason: str, exit_price: float)
        """
        # Slipaj oranı (%0.01 = 0.0001) - Standart slipaj
        SLIPPAGE_RATE = 0.0001
        
        if position.direction == PositionDirection.LONG:
            if position.stop_loss and current_price <= position.stop_loss:
                # STOP PATLADI: Slipajlı çıkış fiyatı
                exit_price = position.stop_loss * (1 - SLIPPAGE_RATE)
                return True, "STOP PATLADI (Long Stop-Loss)", exit_price
            elif position.take_profit and current_price >= position.take_profit:
                # TAKE PROFIT: Slipajlı çıkış fiyatı
                exit_price = position.take_profit * (1 - SLIPPAGE_RATE)
                return True, "Take Profit (Kar-Al)", exit_price

        else:  # SHORT
            if position.stop_loss and current_price >= position.stop_loss:
                # STOP PATLADI: Slipajlı çıkış fiyatı
                exit_price = position.stop_loss * (1 + SLIPPAGE_RATE)
                return True, "STOP PATLADI (Short Stop-Loss)", exit_price
            elif position.take_profit and current_price <= position.take_profit:
                # TAKE PROFIT: Slipajlı çıkış fiyatı
                exit_price = position.take_profit * (1 + SLIPPAGE_RATE)
                return True, "Take Profit (Kar-Al)", exit_price

        return False, "", current_price
    
    # ========================================================================
    # QUERY METODLARI
    # ========================================================================
    
    def get_position(self, bot_id: str) -> Optional[Position]:
        """Bot ID'ye göre pozisyon al"""
        return self.positions.get(bot_id)
    
    def get_all_positions(self) -> List[Position]:
        """Tüm aktif pozisyonlar"""
        return list(self.positions.values())
    
    def get_positions_by_symbol(self, symbol: str) -> List[Position]:
        """Sembol'e göre pozisyonlar"""
        return [p for p in self.positions.values() if p.symbol == symbol]
    
    def get_total_unrealized_pnl(self, prices: Dict[str, float]) -> float:
        """
        Tüm pozisyonların unrealized PnL toplamı.
        
        Args:
            prices: {symbol: current_price} dict
        
        Returns:
            Toplam PnL
        """
        total = 0.0
        for position in self.positions.values():
            if position.symbol in prices:
                total += self.get_unrealized_pnl(position, prices[position.symbol])
        return total
    
    def get_stats(self) -> Dict:
        """İstatistikler"""
        return {
            'total_positions': len(self.positions),
            'total_trades': self.total_trades,
            'total_wins': self.total_wins,
            'win_rate': self.total_wins / self.total_trades if self.total_trades > 0 else 0.0,
            'total_pnl': self.total_pnl,
            'total_commission': self.total_commission
        }
