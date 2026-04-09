"""
Position Value Object

Pozisyon entity'si - immutable (değiştirilemez) tasarım.
Trading sisteminin temel yapı taşı.

Özellikler:
- Immutable (frozen dataclass)
- Tip güvenliği (type hints)
- PnL hesaplama
- Trailing stop desteği
- Serialization (dict/JSON)

Kullanım:
    from core.trading.entities.position import Position, PositionDirection
    
    # Pozisyon oluştur
    position = Position(
        bot_id="bot_123",
        symbol="BTC/USDT",
        direction=PositionDirection.LONG,
        entry_price=50000.0,
        size=0.1,
        leverage=5.0,
        stop_loss=49000.0,
        take_profit=52000.0
    )
    
    # Unrealized PnL hesapla
    current_price = 51000.0
    pnl = position.unrealized_pnl(current_price)
    
    # Stop loss güncelle (trailing)
    position = position.update_stop_loss(49500.0)  # Yeni instance döner
    
    # Pozisyon kapat
    trade = position.close(exit_price=51000.0, reason="take_profit")
"""

import dataclasses
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


DEFAULT_COMMISSION_BUFFER = 0.0008

class PositionDirection(str, Enum):
    """Pozisyon yönü"""
    LONG = "LONG"
    SHORT = "SHORT"


@dataclass(frozen=True)
class Position:
    """
    Position Value Object.
    
    Immutable (değiştirilemez) tasarım pattern.
    Her update yeni bir instance döner.
    
    Attributes:
        bot_id: Bot ID (benzersiz)
        symbol: Sembol (örn: BTC/USDT)
        direction: Pozisyon yönü (LONG/SHORT)
        entry_price: Giriş fiyatı
        size: Pozisyon büyüklüğü (coin miktarı)
        leverage: Kaldıraç (1x, 5x, 10x, vb.)
        opened_at: Açılma zamanı (UTC)
        stop_loss: Stop loss fiyatı (opsiyonel)
        take_profit: Take profit fiyatı (opsiyonel)
        margin: Kullanılan marjin (size * entry_price / leverage)
        commission: Komisyon (varsayılan: 0)
        metadata: Ek veriler (JSON)
    """
    
    # Required fields
    bot_id: str
    symbol: str
    direction: PositionDirection
    entry_price: float
    size: float
    leverage: float
    opened_at: datetime
    
    # Optional fields
    stop_loss: Optional[float] = None
    initial_stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    margin: float = 0.0
    commission: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    # YENİ: Kademeli Çıkış ve Risk Yönetimi Alanları
    partial_profit_taken: bool = False  # Aşama 1: Kısmi kâr alma (50% TP)
    breakeven_activated: bool = False  # Aşama 2: Başa baş koruması aktif
    realized_pnl: float = 0.0  # Gerçekleşmiş (Kısmi çıkışlardan gelen) PnL
    take_profit_levels: list = field(default_factory=list)  # Örn: [{"level": 1.5, "percentage": 0.5, "hit": False}]
    
    def __post_init__(self):
        """Validation (dataclass initialization sonrası)"""
        # Tip validasyonu
        if not isinstance(self.bot_id, str) or not self.bot_id.strip():
            object.__setattr__(self, 'bot_id', str(self.bot_id).strip())
        
        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("symbol boş olamaz")
        
        if self.entry_price <= 0:
            raise ValueError("entry_price pozitif olmalı")
        
        if self.size <= 0:
            raise ValueError("size pozitif olmalı")
        
        if self.leverage < 1:
            raise ValueError("leverage en az 1x olmalı")
        
        # Margin hesapla (eğer 0 ise)
        if self.margin <= 0:
            position_value = self.entry_price * self.size
            calculated_margin = position_value / self.leverage
            object.__setattr__(self, 'margin', calculated_margin)
    
    # ========================================================================
    # PnL HESAPLAMA
    # ========================================================================
    
    def unrealized_pnl(self, current_price: float) -> float:
        """
        Realize olmamış PnL (kar/zarar).
        
        Args:
            current_price: Şu anki fiyat
        
        Returns:
            PnL (pozitif = kar, negatif = zarar)
        
        Örnek:
            LONG: (51000 - 50000) * 0.1 = $100 kar
            SHORT: (50000 - 51000) * 0.1 = -$100 zarar
        """
        if self.direction == PositionDirection.LONG:
            pnl = (current_price - self.entry_price) * self.size
        else:  # SHORT
            pnl = (self.entry_price - current_price) * self.size
        
        return pnl - self.commission

    def total_pnl(self, current_price: float) -> float:
        """
        Toplam PnL (Gerçekleşmiş + Realize Olmamış).
        """
        return self.realized_pnl + self.unrealized_pnl(current_price)
    
    def unrealized_pnl_percent(self, current_price: float) -> float:
        """
        Realize olmamış PnL yüzdesi (marjine göre).
        
        Returns:
            PnL % (örn: 0.05 = %5 kar)
        """
        if self.margin <= 0:
            return 0.0
        
        pnl = self.unrealized_pnl(current_price)
        return pnl / self.margin
    
    def unrealized_pnl_with_leverage(self, current_price: float) -> float:
        """
        Kaldıraçlı PnL (marjine göre getiri).
        
        Returns:
            PnL $ (marjine göre)
        """
        pnl = self.unrealized_pnl(current_price)
        return pnl
    
    # ========================================================================
    # STOP LOSS / TAKE PROFIT KONTROLLERİ
    # ========================================================================
    
    def is_stop_loss_hit(self, current_price: float) -> bool:
        """
        Stop loss tetiklendi mi?
        
        LONG: current_price <= stop_loss
        SHORT: current_price >= stop_loss
        """
        if current_price is None or current_price <= 0.0:
            return False

        if self.stop_loss is None:
            return False
        
        if self.direction == PositionDirection.LONG:
            return current_price <= self.stop_loss
        else:  # SHORT
            return current_price >= self.stop_loss
    
    def is_take_profit_hit(self, current_price: float) -> bool:
        """
        Take profit tetiklendi mi?
        
        LONG: current_price >= take_profit
        SHORT: current_price <= take_profit
        """
        if self.take_profit is None:
            return False
        
        if self.direction == PositionDirection.LONG:
            return current_price >= self.take_profit
        else:  # SHORT
            return current_price <= self.take_profit
    
    def is_exit_condition_met(self, current_price: float) -> tuple:
        """
        Çıkış koşulu kontrolü (stop loss veya take profit).
        
        Returns:
            (is_met: bool, reason: str, exit_price: float)
        """
        if self.is_stop_loss_hit(current_price):
            return True, "stop_loss", self.stop_loss
        
        if self.is_take_profit_hit(current_price):
            return True, "take_profit", self.take_profit
        
        return False, "", current_price
    
    # ========================================================================
    # UPDATE METODLARI (Immutable - Yeni Instance Döner)
    # ========================================================================
    
    def update_stop_loss(self, new_stop: float) -> 'Position':
        """
        Trailing stop güncelle (immutable).
        
        LONG: Sadece yukarı hareket edebilir (yeni_stop > old_stop)
        SHORT: Sadece aşağı hareket edebilir (yeni_stop < old_stop)
        
        Returns:
            Yeni Position instance (güncellenmiş stop_loss ile)
        """
        # Trailing stop kuralları
        if self.direction == PositionDirection.LONG:
            # LONG için stop loss sadece yukarı hareket eder
            if self.stop_loss is not None and new_stop <= self.stop_loss:
                return self  # Değişiklik yok
        
        elif self.direction == PositionDirection.SHORT:
            # SHORT için stop loss sadece aşağı hareket eder
            if self.stop_loss is not None and new_stop >= self.stop_loss:
                return self  # Değişiklik yok
        
        # Yeni instance oluştur (frozen=True için replace pattern)
        return dataclasses.replace(self, stop_loss=new_stop)

    # ========================================================================
    # 3 AŞAMALI RİSK YÖNETİMİ (Kâr Koruma Sistemi)
    # ========================================================================

    def get_triggered_tp_levels(self, current_price: float) -> list:
        """
        Aşama 1: R-Multiple tabanlı kademeli çıkış.
        """
        if not self.initial_stop_loss:
            return []

        risk_distance = abs(self.entry_price - self.initial_stop_loss)
        if risk_distance <= 0:
            return []

        if self.direction == PositionDirection.LONG:
            profit_distance = current_price - self.entry_price
        else:  # SHORT
            profit_distance = self.entry_price - current_price

        current_r = profit_distance / risk_distance

        triggered = []
        for level_info in self.take_profit_levels:
            if not level_info.get("hit", False) and current_r >= level_info.get("level", float('inf')):
                triggered.append(level_info)

        return triggered

    def should_activate_breakeven(self, current_price: float, atr: float) -> bool:
        """
        Aşama 2: Başa Baş (Breakeven) Koruması.

        Fiyat, pozisyon yönünde en az 1.0x ATR kâra ulaştığında
        stop-loss'u giriş fiyatının çok üzerine çek.

        Args:
            current_price: Şu anki fiyat
            atr: ATR değeri (14 periyot)

        Returns:
            True ise breakeven aktivasyonu zamanı
        """
        if self.breakeven_activated:
            return False

        # Minimum 1.0x ATR kâr
        min_profit_distance = atr * 1.0

        if self.direction == PositionDirection.LONG:
            profit_distance = current_price - self.entry_price
            return profit_distance >= min_profit_distance
        else:  # SHORT
            profit_distance = self.entry_price - current_price
            return profit_distance >= min_profit_distance

    def activate_breakeven(self, commission_buffer: float = DEFAULT_COMMISSION_BUFFER) -> 'Position':
        """
        Başa baş (breakeven) korumasını aktif et.

        Stop-loss'u giriş fiyatının komisyonları kurtaracak kadar üzerine çek.

        Args:
            commission_buffer: Komisyon buffer'ı (örn: 0.001 = %0.1)

        Returns:
            Yeni Position instance (breakeven_activated=True)
        """
        # Komisyon buffer'ı ile breakeven fiyatı
        if self.direction == PositionDirection.LONG:
            breakeven_price = self.entry_price * (1 + commission_buffer)
        else:  # SHORT
            breakeven_price = self.entry_price * (1 - commission_buffer)

        # Yeni position oluştur (immutable)
        return dataclasses.replace(
            self,
            stop_loss=breakeven_price,
            breakeven_activated=True
        )

    def update_trailing_stop_with_protection(
        self,
        current_price: float,
        atr: float,
        atr_multiplier: float = 2.0
    ) -> 'Position':
        """
        Aşama 3: İz Süren Stop (Trailing) - Breakeven Korumalı.

        Stop seviyesini dinamik olarak ATR çarpanı kadar geriden takip et.
        Stop ASLA breakeven noktasının altına düşmemeli.

        Args:
            current_price: Şu anki fiyat
            atr: ATR değeri
            atr_multiplier: ATR çarpanı (örn: 2.0 = 2x ATR)

        Returns:
            Yeni Position instance (güncellenmiş stop_loss)
        """
        # Mevcut stop loss (None ise başlangıç SL'ı kullan)
        current_stop = self.stop_loss if self.stop_loss else self.entry_price

        # Trailing stop hesapla
        if self.direction == PositionDirection.LONG:
            # LONG: Fiyat yükseldikçe stop'u yukarı çek
            trailing_stop = current_price - (atr * atr_multiplier)

            # Stop asla giriş fiyatının altına düşmemeli (breakeven koruması)
            if self.breakeven_activated:
                min_stop = self.entry_price * (1 + DEFAULT_COMMISSION_BUFFER)  # Komisyon buffer
                # Yeni stop: daha yüksek olan (trailing veya min)
                new_stop = max(trailing_stop, min_stop, current_stop)
            else:
                # Breakeven yoksa sadece trailing ile current_stop'ı kıyasla
                new_stop = max(trailing_stop, current_stop)
        else:  # SHORT
            # SHORT: Fiyat düştükçe stop'u aşağı çek
            trailing_stop = current_price + (atr * atr_multiplier)

            # Stop asla giriş fiyatının üstüne çıkmamalı (breakeven koruması)
            if self.breakeven_activated:
                max_stop = self.entry_price * (1 - DEFAULT_COMMISSION_BUFFER)  # Komisyon buffer
                # Yeni stop: daha düşük olan (trailing veya max)
                new_stop = min(trailing_stop, max_stop, current_stop)
            else:
                # Breakeven yoksa sadece trailing ile current_stop'ı kıyasla
                new_stop = min(trailing_stop, current_stop)

        # Sadece stop_loss iyileşmişse güncelle
        if self.direction == PositionDirection.LONG:
            if new_stop <= current_stop:
                return self  # Değişiklik yok
        else:  # SHORT
            if new_stop >= current_stop:
                return self  # Değişiklik yok

        # Yeni position oluştur (immutable)
        return dataclasses.replace(self, stop_loss=new_stop)

    def update_take_profit(self, new_tp: float) -> 'Position':
        """
        Take profit güncelle (immutable).
        
        Returns:
            Yeni Position instance
        """
        return dataclasses.replace(self, take_profit=new_tp)
    
    def update_metadata(self, updates: Dict[str, Any]) -> 'Position':
        """
        Metadata güncelle (immutable).
        
        Returns:
            Yeni Position instance
        """
        new_metadata = {**self.metadata, **updates}
        return dataclasses.replace(self, metadata=new_metadata)
    
    # ========================================================================
    # CLOSE (POZİSYON KAPAT)
    # ========================================================================
    
    def close(
        self,
        exit_price: float,
        reason: str = "manual",
        commission: float = 0.0
    ):
        """
        Pozisyon kapat ve Trade oluştur.
        
        Args:
            exit_price: Çıkış fiyatı
            reason: Kapatma nedeni (manual, stop_loss, take_profit, vb.)
            commission: Komisyon
        
        Returns:
            Trade object (kayıt için)
        """
        from core.trading.entities.trade import Trade
        
        # PnL hesapla
        pnl = self.unrealized_pnl(exit_price) - commission
        pnl_percent = self.unrealized_pnl_percent(exit_price)

        # Trade oluştur - UNIQUE ID (microsecond hassasiyeti!)
        # Format: trade_{bot_id}_{timestamp_microseconds}
        timestamp_us = int(datetime.utcnow().timestamp() * 1000000)  # Microseconds
        trade_id = f"trade_{self.bot_id}_{timestamp_us}"
        
        trade = Trade(
            id=trade_id,
            bot_id=self.bot_id,
            symbol=self.symbol,
            direction=self.direction,
            entry_price=self.entry_price,
            exit_price=exit_price,
            size=self.size,
            leverage=self.leverage,
            pnl=pnl,
            pnl_percent=pnl_percent,
            commission=commission,
            opened_at=self.opened_at,
            closed_at=datetime.utcnow(),
            reason=reason,
            strategy_id=self.metadata.get('strategy_id'),
            metadata=self.metadata
        )
        
        return trade
    
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
            'bot_id': self.bot_id,
            'symbol': self.symbol,
            'direction': self.direction.value,
            'entry_price': self.entry_price,
            'size': self.size,
            'leverage': self.leverage,
            'margin': self.margin,
            'stop_loss': self.stop_loss,
            'initial_stop_loss': self.initial_stop_loss,
            'take_profit': self.take_profit,
            'liquidation_price': self.liquidation_price,
            'commission': self.commission,
            'unrealized_usd': self.unrealized_pnl,
            'pnl_percent': self.pnl_percent,
            'opened_at': self.opened_at.isoformat(),
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
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        """
        Dict'ten oluştur (deserialization).
        
        Args:
            data: Dict representation
        
        Returns:
            Position instance
        """
        return cls(
            bot_id=data['bot_id'],
            symbol=data['symbol'],
            direction=PositionDirection(data['direction']),
            entry_price=data['entry_price'],
            size=data['size'],
            leverage=data['leverage'],
            opened_at=datetime.fromisoformat(data['opened_at']) if isinstance(data['opened_at'], str) else data['opened_at'],
            stop_loss=data.get('stop_loss'),
            initial_stop_loss=data.get('initial_stop_loss'),
            take_profit=data.get('take_profit'),
            margin=data.get('margin', 0.0),
            commission=data.get('commission', 0.0),
            metadata=data.get('metadata', {})
        )
    
    # ========================================================================
    # STRING REPRESENTATION
    # ========================================================================
    
    def __str__(self) -> str:
        """Human-readable string"""
        return (
            f"Position({self.bot_id}, {self.symbol}, "
            f"{self.direction.value}, Entry: ${self.entry_price:.2f}, "
            f"Size: {self.size}, Leverage: {self.leverage}x)"
        )
    
    def __repr__(self) -> str:
        """Developer representation"""
        return (
            f"Position(bot_id='{self.bot_id}', symbol='{self.symbol}', "
            f"direction={self.direction.value}, entry_price={self.entry_price}, "
            f"size={self.size}, leverage={self.leverage})"
        )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calculate_position_size(
    account_balance: float,
    risk_percentage: float,
    entry_price: float,
    stop_loss_price: float
) -> float:
    """
    Pozisyon boyutu hesapla (risk bazlı).
    
    Formül: (Bakiye × Risk%) / |Giriş - Stop|
    
    Args:
        account_balance: Hesap bakiyesi
        risk_percentage: Risk yüzdesi (örn: 0.01 = %1)
        entry_price: Giriş fiyatı
        stop_loss_price: Stop loss fiyatı
    
    Returns:
        Pozisyon boyutu (coin miktarı)
    """
    if risk_percentage <= 0 or risk_percentage > 1:
        raise ValueError("risk_percentage 0-1 arası olmalı")
    
    risk_amount = account_balance * risk_percentage
    price_distance = abs(entry_price - stop_loss_price)
    
    if price_distance <= 0:
        return 0.0
    
    return risk_amount / price_distance


def calculate_margin(
    entry_price: float,
    size: float,
    leverage: float
) -> float:
    """
    Marjin hesapla.
    
    Formül: (Fiyat × Boyut) / Kaldıraç
    
    Returns:
        Required margin
    """
    position_value = entry_price * size
    return position_value / leverage
