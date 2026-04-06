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
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.daily_trades = 0
        
        # Kill switch
        self.kill_switch_active = False
        
        logger.info(f"⚠️ Risk Engine initialized (max_risk={self.config.max_risk_per_trade:.2%})")
    
    # ========================================================================
    # POZİSYON BOYUTU HESAPLAMA
    # ========================================================================
    
    def calculate_position_size(
        self,
        account_balance: float,
        entry_price: float,
        stop_loss_price: float,
        risk_percentage: Optional[float] = None,
        leverage: float = 1.0,
        free_margin: Optional[float] = None
    ) -> float:
        """
        Pozisyon boyutu hesapla (risk bazlı).
        
        Formül: min((Bakiye × Risk%) / |Giriş - Stop|, (Bakiye × Kaldıraç) / Giriş)
        
        Args:
            account_balance: Hesap bakiyesi
            entry_price: Giriş fiyatı
            stop_loss_price: Stop loss fiyatı
            risk_percentage: Risk yüzdesi (None ise config.max_risk_per_trade kullanılır)
            leverage: Kullanılan kaldıraç (boyut sınırlandırması için)
        
        Returns:
            Pozisyon boyutu (coin miktarı)
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
        
        # Risk miktarı ($)
        risk_amount = account_balance * (risk_percentage / 100.0)
        
        # Fiyat mesafesi
        price_distance = abs(entry_price - stop_loss_price)
        
        if price_distance <= 0:
            return 0.0
        
        # 1. Risk bazlı boyut
        size_by_risk = risk_amount / price_distance
        
        # 2. İşlem Başına Maksimum Sermaye Limiti (Account limitine göre cap)
        # Örn: max_open_positions = 10 ise, bir işleme en fazla %10 marjin ayrılabilir.
        max_positions = getattr(self.config, 'max_open_positions', 10)
        max_positions = max(1, max_positions)
        max_margin_per_trade = account_balance / max_positions
        
        # Seçilen kaldıraç ile ulaşılabilecek maksimum notional limit (Kullanılan Marjin Limiti ile)
        max_notional_by_margin = max_margin_per_trade * leverage * 0.98 # %2 margin buffer
        size_by_margin_limit = max_notional_by_margin / entry_price
        
        # 3. Serbest Bakiye Limiti (Gerçekte kullanılabilir olan bakiye kısıtlaması)
        # Eğer free_margin belirtildiyse, yeni açılacak pozisyon free_margin'i de aşmamalı
        size_by_free_margin = float('inf')
        if free_margin is not None:
            max_notional_by_free_margin = free_margin * leverage * 0.98
            size_by_free_margin = max_notional_by_free_margin / entry_price

        # En küçüğünü al
        position_size = min(size_by_risk, size_by_margin_limit, size_by_free_margin)
        
        logger.debug(
            f"📏 Boyut Hesabı | Risk: {size_by_risk:.4f}, MarginLimit: {size_by_margin_limit:.4f}, "
            f"FreeMarginLimit: {size_by_free_margin:.4f} -> Final: {position_size:.4f}"
        )
        
        # Risk Doğrulaması (Assert) - Kayan nokta hassasiyetiyle
        calculated_risk = position_size * abs(entry_price - stop_loss_price)
        max_allowed_risk = account_balance * (risk_percentage / 100.0)

        assert calculated_risk <= (max_allowed_risk * 1.01), f"Sistem Hatası: Planlanan risk ({calculated_risk:.2f}) anapara limitini ({max_allowed_risk:.2f}) aşıyor!"

        return position_size
    
    # ========================================================================
    # DİNAMİK KALDIRAÇ HESAPLAMA
    # ========================================================================
    
    def calculate_dynamic_leverage(
        self,
        confidence_score: float,
        base_leverage: Optional[float] = None,
        max_leverage: Optional[float] = None,
        timeframe: str = "1h"  # YENİ: Timeframe bilgisi
    ) -> float:
        """
        Güven skoruna göre dinamik kaldıraç (Meta-Labeling).

        TRADING_RULES_AND_RISK.md standartlarına göre:
        - confidence < 0.50: return 0 (İşlemi VETO ET)
        - 0.50 <= confidence < 0.65: return 2 (Düşük Risk, 2x Kaldıraç)
        - 0.65 <= confidence < 0.80: return 4 (Orta Risk, 4x sabitle)
        - confidence >= 0.80: return 8 (Yüksek Risk, 8x sabitle)

        Args:
            confidence_score: Güven skoru (0.0 - 1.0)
            base_leverage: Baz kaldıraç (None ise config.default_leverage) - kullanılmaz, uyumluluk için var
            max_leverage: Maksimum kaldıraç (None ise config.max_leverage) - kullanılmaz, uyumluluk için var
            timeframe: Zaman dilimi (örn: "1m", "15m", "1h")

        Returns:
            Dinamik kaldıraç (0.0, 2.0, 4.0 veya 8.0)
        """
        if confidence_score < 0.50:
            final_leverage = 0.0
        elif confidence_score < 0.65:
            final_leverage = 2.0
        elif confidence_score < 0.80:
            final_leverage = 4.0
        else:
            final_leverage = 8.0

        logger.debug(
            f"🚀 Dinamik kaldıraç (Meta-Labeling): Confidence={confidence_score:.2%}, "
            f"Leverage={final_leverage}x"
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
    
    def check_kill_switch(self) -> bool:
        """
        Kill switch aktif mi kontrol et.

        Koşullar:
        - Kill switch enabled olmalı
        - Ardışık kayıp >= max_consecutive_losses (ve limit > 0)
        - Günlük kayıp >= max_daily_loss

        Returns:
            True ise kill switch aktif
        """
        # Kill switch devre dışı ise kontrol etme
        if not self.config.kill_switch_enabled:
            self.kill_switch_active = False
            return False

        # Ardışık kayıp kontrolü (limit 0 ise sınırsız)
        if self.config.max_consecutive_losses > 0 and \
           self.consecutive_losses >= self.config.max_consecutive_losses:
            logger.warning(
                f"🚨 KILL SWITCH: {self.consecutive_losses} ardışık kayıp "
                f"(limit: {self.config.max_consecutive_losses})"
            )
            self.kill_switch_active = True
            return True

        # Günlük kayıp kontrolü
        if self.daily_pnl <= -self.config.max_daily_loss:
            logger.critical(
                f"🚨 KILL SWITCH: Günlük kayıp {self.daily_pnl:.2%} "
                f"(limit: {self.config.max_daily_loss:.2%})"
            )
            self.kill_switch_active = True
            return True

        return False
    
    def can_open_position(self, current_positions: int) -> bool:
        """
        Yeni pozisyon açılabilir mi?
        
        Args:
            current_positions: Şu anki açık pozisyon sayısı
        
        Returns:
            True ise açılabilir
        """
        # Kill switch kontrolü
        if self.kill_switch_active:
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
    
    def record_trade_result(self, pnl: float):
        """
        İşlem sonucunu kaydet.
        
        Args:
            pnl: PnL ($)
        """
        # Günlük PnL güncelle
        self.daily_pnl += pnl
        self.total_pnl += pnl
        self.daily_trades += 1
        
        # Ardışık kayıp sayacı
        if pnl < 0:
            self.consecutive_losses += 1
            logger.debug(f"Ardışık kayıp: {self.consecutive_losses}")
        else:
            # Kar ile sıfırla
            self.consecutive_losses = 0
        
        # Kill switch kontrolü
        self.check_kill_switch()
    
    def reset_daily(self):
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
        self.consecutive_losses = 0
        self.kill_switch_active = False
    
    def reset_kill_switch(self):
        """
        Kill switch'i manuel sıfırla.
        Kullanıcı onayı ile çağrılmalı.
        """
        logger.info("🔓 Kill switch manuel olarak sıfırlandı")
        self.kill_switch_active = False
        self.consecutive_losses = 0
    
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
        
        Returns:
            Dict with all stats
        """
        return {
            'consecutive_losses': self.consecutive_losses,
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'total_pnl': self.total_pnl,
            'kill_switch_active': self.kill_switch_active,
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
        
        Returns:
            Summary string
        """
        return (
            f"Risk Summary: "
            f"Daily PnL: ${self.daily_pnl:.2f} ({self.daily_pnl:.2%}), "
            f"Consecutive Losses: {self.consecutive_losses}, "
            f"Kill Switch: {'AKTIF' if self.kill_switch_active else 'PASIF'}"
        )
