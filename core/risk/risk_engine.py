"""
Risk Engine

Risk yönetimi ve hesaplama motoru.
SORUMLULUK: Pozisyon boyutu, kaldıraç, stop-loss hesaplamaları, risk limitleri

Bu modül, core/paper.py ve strategy/risk.py içindeki risk yönetimi mantığını devralır.

Usage:
    from core.risk.risk_engine import RiskEngine, RiskConfig
    
    config = RiskConfig(
        max_risk_per_trade=0.01,  # %1
        max_leverage=10,
        max_consecutive_losses=5
    )
    
    engine = RiskEngine(config)
    
    # Pozisyon boyutu hesapla
    size = engine.calculate_position_size(
        account_balance=10000,
        entry_price=50000,
        stop_loss_price=49000
    )
    
    # Dinamik kaldıraç
    leverage = engine.calculate_dynamic_leverage(confidence_score=0.75)
    
    # Stop loss / take profit
    sl, tp = engine.calculate_dynamic_stops(
        price=50000,
        direction="LONG",
        atr=500,
        sl_multiplier=1.2,
        tp_multiplier=1.5
    )
"""

from dataclasses import dataclass
from typing import Tuple, Optional, Dict, Any
from core.logger import logger


@dataclass
class RiskConfig:
    """
    Risk yapılandırması.

    Attributes:
        max_risk_per_trade: İşlem başına maksimum risk (% olarak,örn: 0.01 = %1)
        max_open_positions: Maksimum açık pozisyon sayısı
        default_leverage: Varsayılan kaldıraç
        max_leverage: Maksimum kaldıraç
        max_consecutive_losses: Maksimum ardışık kayıp (kill switch, 0 = sınırsız)
        max_daily_loss: Maksimum günlük kayıp (% olarak)
        max_drawdown: Maksimum drawdown (% olarak)
        kill_switch_enabled: Kill Switch aktif/pasif
    """
    max_risk_per_trade: float = 0.01  # %1
    max_open_positions: int = 5
    default_leverage: float = 1.0
    max_leverage: float = 10.0
    max_consecutive_losses: int = 5
    max_daily_loss: float = 0.05  # %5
    max_drawdown: float = 0.20  # %20
    kill_switch_enabled: bool = True


class RiskEngine:
    """
    Risk Engine.
    
    Risk hesaplama ve validasyon:
    - Pozisyon boyutu hesaplama
    - Dinamik kaldıraç hesaplama
    - Stop loss / take profit hesaplama
    - Risk limiti kontrolü
    - Kill switch yönetimi
    """
    
    def __init__(self, config: Optional[RiskConfig] = None):
        """
        Args:
            config: Risk yapılandırması (None ise varsayılan)
        """
        self.config = config or RiskConfig()
        
        # State tracking
        from collections import defaultdict
        import asyncio
        from pathlib import Path
        import json

        self.consecutive_losses = defaultdict(int)
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.daily_trades = 0
        
        # Kill switch
        self.kill_switch_active = defaultdict(bool)

        self._state_lock = asyncio.Lock()
        self._state_file = Path("data/state/risk_state.json")
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"⚠️ Risk Engine initialized (max_risk={self.config.max_risk_per_trade:.2%})")

        # Event loop varsa state'i yükle
        try:
            loop = asyncio.get_running_loop()
            if loop and loop.is_running():
                loop.create_task(self.load_state())
        except RuntimeError:
            # Loop henüz yoksa pas geç, uygulama kendi state'ini load edecektir.
            pass
    
    # ========================================================================
    # POZİSYON BOYUTU HESAPLAMA

    async def load_state(self):
        """Asenkron olarak risk state'ini yükle."""
        import json
        import aiofiles

        if not self._state_file.exists():
            return

        try:
            async with self._state_lock:
                async with aiofiles.open(self._state_file, "r") as f:
                    data = json.loads(await f.read())
                    if "consecutive_losses" in data:
                        self.consecutive_losses.update(data["consecutive_losses"])
                    if "kill_switch_active" in data:
                        self.kill_switch_active.update(data["kill_switch_active"])
            logger.info("✅ Risk state yüklendi.")
        except Exception as e:
            logger.error(f"Risk state yüklenirken hata oluştu: {e}")

    async def _save_state(self):
        """Asenkron olarak risk state'ini kaydet."""
        import json
        import aiofiles

        try:
            async with self._state_lock:
                data = {
                    "consecutive_losses": dict(self.consecutive_losses),
                    "kill_switch_active": dict(self.kill_switch_active)
                }
                async with aiofiles.open(self._state_file, "w") as f:
                    await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Risk state kaydedilirken hata oluştu: {e}")

    # ========================================================================
    # EVENT LISTENERS
    # ========================================================================
    
    async def on_position_closed(self, event):
        """
        position.closed olayını dinler ve ardışık kayıp sayacını günceller.
        """
        payload = event.payload
        bot_id = payload.get("bot_id")
        pnl = payload.get("pnl", 0.0)

        if bot_id:
            await self.record_trade_result(bot_id, pnl)
# ========================================================================

    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss_price: float,
        risk_percentage: Optional[float] = None,
        ml_confidence: Optional[float] = None,
        max_leverage: float = 10.0,
        free_margin: Optional[float] = None
    ) -> float:
        """
        Pozisyon boyutu hesapla (Hedge Fund Standartları).
        
        Formül: Büyüklük hesaplaması KESİNLİKLE Stop-Loss mesafesine göre dinamiktir.
        Hesaplanan notional değer, Machine Learning (ML) Confidence tabanlı dinamik kaldıraç
        ile belirlenen (Balance * DynamicLeverage) sınırını (Hard Cap) aşamaz.
        
        Args:
            account_balance: Hesap bakiyesi
            entry_price: Giriş fiyatı
            stop_loss_price: Stop loss fiyatı
            risk_percentage: Risk yüzdesi (None ise config.max_risk_per_trade kullanılır)
            ml_confidence: ML modelinin güven skoru (0.0-1.0 veya None)
            max_leverage: Üst sınır kaldıraç değeri
            free_margin: Serbest bakiye limiti (opsiyonel)
        
        Returns:
            Pozisyon boyutu (coin/base asset miktarı)
        """
        # Risk yüzdesini belirle
        if risk_percentage is None:
            risk_percentage = self.config.max_risk_per_trade * 100

        # Validasyon
        original_risk = risk_percentage
        if risk_percentage <= 0.0 or risk_percentage > 5.0:
            logger.warning(
                f"⚠️ [RISK] Geçersiz risk yüzdesi: {original_risk:.2f}%, "
                f"varsayılan %1.0 kullanılıyor (max_risk_per_trade={self.config.max_risk_per_trade:.2%})"
            )
            risk_percentage = 1.0  # Güvenli fallback
        
        # İşlem başına riske edilecek tutar ($)
        risk_amount = account_balance * (risk_percentage / 100.0)
        
        # Stop-Loss Mesafesi
        sl_distance = abs(entry_price - stop_loss_price)
        
        # ZeroDivisionError Kalkanı
        if sl_distance <= 0:
            logger.warning("⚠️ [RISK] sl_distance == 0. Pozisyon açılamaz.")
            return 0.0
        
        # Ham Büyüklük (Coin Miktarı)
        raw_size = risk_amount / sl_distance
        
        # Dinamik Kaldıraç Çarpanı (Hard Cap)
        dynamic_leverage = self.calculate_dynamic_leverage(
            confidence_score=ml_confidence,
            max_leverage=max_leverage
        )

        if dynamic_leverage <= 0.0:
            logger.warning(f"⚠️ [RISK] ML Confidence VETO. dynamic_leverage={dynamic_leverage}. İşlem açılamaz.")
            return 0.0

        # Clipping (Kırpma) işlemi
        max_notional_allowed = account_balance * dynamic_leverage
        raw_notional = raw_size * entry_price

        if raw_notional > max_notional_allowed:
            logger.debug(
                f"✂️ [RISK] Clipping uygulandı! Ham Notional: {raw_notional:.2f} > "
                f"İzin Verilen: {max_notional_allowed:.2f} (Kaldıraç: {dynamic_leverage}x)"
            )
            raw_size = max_notional_allowed / entry_price

        # Serbest Bakiye Limiti (Gerçekte kullanılabilir olan bakiye kısıtlaması)
        if free_margin is not None:
            max_notional_by_free_margin = free_margin * dynamic_leverage * 0.98
            size_by_free_margin = max_notional_by_free_margin / entry_price
            raw_size = min(raw_size, size_by_free_margin)

        # Risk Doğrulaması (Assert) - Kayan nokta hassasiyetiyle
        calculated_risk = raw_size * sl_distance
        max_allowed_risk = account_balance * (risk_percentage / 100.0)

        assert calculated_risk <= (max_allowed_risk * 1.01), (
            f"Sistem Hatası: Planlanan risk ({calculated_risk:.2f}) "
            f"anapara limitini ({max_allowed_risk:.2f}) aşıyor!"
        )

        logger.debug(
            f"📏 [RISK] Boyut Hesabı | RiskAmount={risk_amount:.2f}, SL_Distance={sl_distance:.4f}, "
            f"DynamicLev={dynamic_leverage}x -> Final Size (Coin): {raw_size:.6f}"
        )

        return raw_size
    
    # ========================================================================
    # DİNAMİK KALDIRAÇ HESAPLAMA
    # ========================================================================
    
    def calculate_dynamic_leverage(
        self,
        confidence_score: Optional[float],
        base_leverage: Optional[float] = None,
        max_leverage: Optional[float] = None,
        timeframe: str = "1h"  # YENİ: Timeframe bilgisi
    ) -> float:
        """
        Güven skoruna göre dinamik kaldıraç (Meta-Labeling).

        Hedge Fund standartlarına göre:
        - confidence None: return default_leverage (Fallback Kalkanı)
        - confidence < 0.50: return 0 (İşlemi VETO ET)
        - 0.50 <= confidence < 0.65: return min(3.0, max_leverage)
        - 0.65 <= confidence <= 0.80: return min(5.0, max_leverage)
        - confidence > 0.80: return min(10.0, max_leverage)

        Args:
            confidence_score: Güven skoru (0.0 - 1.0) veya None
            base_leverage: Baz kaldıraç (None ise config.default_leverage)
            max_leverage: Maksimum kaldıraç (None ise config.max_leverage)
            timeframe: Zaman dilimi (örn: "1m", "15m", "1h")

        Returns:
            Dinamik kaldıraç
        """
        # Fallback Kalkanı
        if confidence_score is None:
            fallback_leverage = base_leverage if base_leverage is not None else getattr(self.config, 'default_leverage', 1.0)
            logger.debug(
                f"🛡️ [RISK] ML Confidence None geldi. Fallback (default_leverage) kullanılıyor: {fallback_leverage}x"
            )
            return float(fallback_leverage)

        # Maksimum Kaldıraç Sınırı
        actual_max_leverage = max_leverage if max_leverage is not None else getattr(self.config, 'max_leverage', 10.0)

        # Dinamik Aralıklar (Upper Bounds)
        if confidence_score < 0.50:
            final_leverage = 0.0
        elif confidence_score < 0.65:
            final_leverage = min(3.0, actual_max_leverage)
        elif confidence_score <= 0.80:
            final_leverage = min(5.0, actual_max_leverage)
        else:
            final_leverage = min(10.0, actual_max_leverage)

        logger.debug(
            f"🚀 Dinamik kaldıraç (Meta-Labeling): Confidence={confidence_score:.2%}, "
            f"Leverage={final_leverage}x (Max Limit: {actual_max_leverage}x)"
        )

        return float(final_leverage)
    
    def calculate_leverage_from_ml_recommendation(
        self,
        ml_recommendation: str,
        max_leverage: Optional[float] = None
    ) -> float:
        """
        ML önerisine göre kaldıraç (core/paper.py uyumlu).
        
        Args:
            ml_recommendation: ML önerisi (STRONG_LONG, LONG, vb.)
            max_leverage: Maksimum kaldıraç
        
        Returns:
            Kaldıraç
        """
        maximum = max_leverage or self.config.max_leverage
        
        if ml_recommendation in ["STRONG_LONG", "STRONG_SHORT"]:
            # Yüksek güven (%80+): Maksimum kaldıraç
            leverage = min(maximum, 10)
        elif ml_recommendation in ["LONG", "SHORT"]:
            # Orta güven (%65-79%): Orta kaldıraç
            leverage = min(maximum, 3)
        else:
            # Düşük güven (<65%): Minimum kaldıraç
            leverage = 1.0
        
        logger.debug(f"ML kaldıraç: {ml_recommendation} -> {leverage}x")
        return leverage
    
    # ========================================================================
    # STOP LOSS / TAKE PROFIT HESAPLAMA
    # ========================================================================
    
    def calculate_dynamic_stops(
        self,
        price: float,
        direction: str,
        atr: float,
        sl_multiplier: float,
        tp_multiplier: float
    ) -> Tuple[float, float]:
        """
        ATR bazlı dinamik stop loss ve take profit.
        
        Oynaklık arttıkça stop mesafesi açılır, sakin piyasada daralır.
        
        Args:
            price: Şu anki fiyat
            direction: Yön (LONG/SHORT)
            atr: ATR değeri
            sl_multiplier: ATR çarpanı (stop için)
            tp_multiplier: ATR çarpanı (take profit için)
        
        Returns:
            (stop_loss, take_profit)
        """
        # Stop ve Take Profit mesafeleri
        stop_distance = atr * sl_multiplier
        take_profit_distance = atr * tp_multiplier
        
        if direction.upper() == "LONG":
            stop_loss = price - stop_distance
            take_profit = price + take_profit_distance
        else:  # SHORT
            stop_loss = price + stop_distance
            take_profit = price - take_profit_distance
        
        logger.debug(
            f"Dinamik stops: Price={price:.2f}, ATR={atr:.2f}, "
            f"SL={stop_loss:.2f}, TP={take_profit:.2f}"
        )
        
        return stop_loss, take_profit
    
    def calculate_stop_loss_from_strategy(
        self,
        price: float,
        direction: str,
        atr: float,
        atr_multiplier: float
    ) -> float:
        """
        Strateji parametrelerine göre stop loss.
        
        Args:
            price: Fiyat
            direction: Yön
            atr: ATR
            atr_multiplier: ATR çarpanı
        
        Returns:
            Stop loss fiyatı
        """
        stop_distance = atr * atr_multiplier
        
        if direction.upper() == "LONG":
            return price - stop_distance
        else:  # SHORT
            return price + stop_distance
    
    # ========================================================================
    # RISK LIMIT KONTROLÜ
    # ========================================================================
    
    async def check_kill_switch(self, bot_id: str) -> bool:
        """
        Kill switch aktif mi kontrol et ve gerekirse asenkron eventi fırlat.
        """
        if not self.config.kill_switch_enabled:
            self.kill_switch_active[bot_id] = False
            return False

        # Ardışık kayıp kontrolü
        if self.config.max_consecutive_losses > 0 and \
           self.consecutive_losses[bot_id] >= self.config.max_consecutive_losses:
            if not self.kill_switch_active[bot_id]:
                logger.warning(f"🚨 KILL SWITCH AKTİF: {self.consecutive_losses[bot_id]} ardışık kayıp ({bot_id})")
                self.kill_switch_active[bot_id] = True

                # Event Bus'a bildir
                from shared.events.event_bus import event_bus
                from shared.events.events import Event
                await event_bus.publish(Event(
                    type="bot.stopped",
                    payload={
                        'bot_id': bot_id,
                        'reason': 'kill_switch_activated',
                        'consecutive_losses': self.consecutive_losses[bot_id]
                    },
                    source="risk_engine"
                ))
            return True

        # Günlük kayıp kontrolü
        if self.daily_pnl <= -self.config.max_daily_loss:
            if not self.kill_switch_active[bot_id]:
                logger.critical(
                    f"🚨 KILL SWITCH: Günlük kayıp {self.daily_pnl:.2%} "
                    f"(limit: {self.config.max_daily_loss:.2%}) ({bot_id})"
                )
                self.kill_switch_active[bot_id] = True
            return True

        return False
    
    def is_kill_switch_active(self, bot_id: str) -> bool:
        """O(1) hızında Kill Switch kontrolü (senkron)."""
        return self.kill_switch_active.get(bot_id, False)

    def can_open_position(self, bot_id: str, current_positions: int) -> bool:
        """
        Yeni pozisyon açılabilir mi?
        """
        # Kill switch kontrolü
        if self.is_kill_switch_active(bot_id):
            return False
        
        # Maksimum pozisyon kontrolü
        if current_positions >= self.config.max_open_positions:
            logger.debug(f"Maksimum pozisyon limitine ulaşıldı: {current_positions}")
            return False
        
        return True
    
    def check_margin_suitability(
        self,
        required_margin: float,
        free_margin: float
    ) -> bool:
        """
        Marjin uygunluğu kontrolü.
        
        Args:
            required_margin: Gerekli marjin
            free_margin: Serbest marjin
        
        Returns:
            True ise yeterli
        """
        if required_margin > free_margin:
            logger.warning(
                f"Yetersiz marjin! Gerekli: ${required_margin:.2f}, "
                f"Serbest: ${free_margin:.2f}"
            )
            return False
        
        return True
    
    # ========================================================================
    # TRADE RESULT TRACKING
    # ========================================================================
    
    async def record_trade_result(self, bot_id: str, pnl: float):
        """
        İşlem sonucunu kaydet ve state'i güncelle (Asenkron).
        Epsilon/Microscopic loss filtresi içerir.
        """
        # Günlük PnL güncelle
        self.daily_pnl += pnl
        self.total_pnl += pnl
        self.daily_trades += 1
        
        # Epsilon (Microscopic Loss) Filtresi:
        # PnL <= -0.5 ise zarar say,
        # -0.5 < PnL <= 0 ise başabaş/komisyon zararı say (pass)
        # PnL > 0 ise kar say (sıfırla)
        epsilon = -0.5
        
        if pnl <= epsilon:
            self.consecutive_losses[bot_id] += 1
            logger.debug(f"[{bot_id}] Ardışık kayıp: {self.consecutive_losses[bot_id]}")
        elif pnl > 0:
            self.consecutive_losses[bot_id] = 0
            # Eğer kill switch daha önce açıksa ve kâra geçildiyse kapatılabilmesi için logic eklenebilir,
            # şimdilik sadece sayacı sıfırlıyoruz.
        else:
            # Break-even veya epsilon zararı, hiçbir şey yapma
            logger.debug(f"[{bot_id}] Break-even/Mikroskobik zarar (PnL: {pnl}), sayaç değiştirilmedi.")
            pass

        await self.check_kill_switch(bot_id)
        await self._save_state()
    
    async def reset_daily(self):
        """
        Günlük sayaçları sıfırla.
        Her yeni gün çağrılmalı.
        """
        logger.info(
            f"Günlük sayaçlar sıfırlandı. "
            f"Önceki gün: {self.daily_trades} işlem, PnL: ${self.daily_pnl:.2f}"
        )
        
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.consecutive_losses.clear()
        self.kill_switch_active.clear()
        await self._save_state()
    
    async def reset_kill_switch(self, bot_id: Optional[str] = None):
        """
        Kill switch'i manuel sıfırla.
        """
        if bot_id:
            logger.info(f"🔓 Kill switch manuel olarak sıfırlandı ({bot_id})")
            self.kill_switch_active[bot_id] = False
            self.consecutive_losses[bot_id] = 0
        else:
            logger.info("🔓 Tüm Kill switch'ler manuel olarak sıfırlandı")
            self.kill_switch_active.clear()
            self.consecutive_losses.clear()
        await self._save_state()
    
    # ========================================================================
    # RISK METRICS
    # ========================================================================
    
    def get_current_drawdown(self, peak_balance: float, current_balance: float) -> float:
        """
        Mevcut drawdown hesapla.
        
        Args:
            peak_balance: Tepe bakiye
            current_balance: Şu anki bakiye
        
        Returns:
            Drawdown (%)
        """
        if peak_balance <= 0:
            return 0.0
        
        drawdown = (peak_balance - current_balance) / peak_balance
        return drawdown
    
    def check_drawdown_limit(self, current_drawdown: float) -> bool:
        """
        Drawdown limiti aşıldı mı?
        
        Args:
            current_drawdown: Mevcut drawdown (%)
        
        Returns:
            True ise limit aşıldı
        """
        if current_drawdown >= self.config.max_drawdown:
            logger.critical(
                f"🚨 DRAWDOWN LIMITI: {current_drawdown:.2%} "
                f"(limit: {self.config.max_drawdown:.2%})"
            )
            return True
        
        return False
    
    # ========================================================================
    # STATS & REPORTING
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Risk istatistikleri.
        """
        return {
            'consecutive_losses': dict(self.consecutive_losses),
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'total_pnl': self.total_pnl,
            'kill_switch_active': dict(self.kill_switch_active),
            'config': {
                'max_risk_per_trade': self.config.max_risk_per_trade,
                'max_leverage': self.config.max_leverage,
                'max_consecutive_losses': self.config.max_consecutive_losses,
                'max_daily_loss': self.config.max_daily_loss,
                'max_drawdown': self.config.max_drawdown
            }
        }
    
    def get_risk_summary(self) -> str:
        """
        Risk özeti (log için).
        """
        return (
            f"Risk Summary: "
            f"Daily PnL: ${self.daily_pnl:.2f} ({self.daily_pnl:.2%}), "
            f"Consecutive Losses: {dict(self.consecutive_losses)}, "
            f"Kill Switch: {dict(self.kill_switch_active)}"
        )
