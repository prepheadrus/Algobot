"""
Event Tracer - Sistem Röntgeni (Event-Driven Architecture Diagnostic Tool)

Bu modül, EventBus'a bağlanarak sistemdeki TÜM olayları dinler ve
terminale renkli, okunaklı bir şekilde yazdırır.

Kullanım:
    from core.diagnostics.event_tracer import EventTracer
    
    tracer = EventTracer()
    await tracer.start()

Özellikler:
- Tüm event kategorilerini dinler (bot.*, signal.*, position.*, ml.*, data.*)
- Renkli terminal çıktısı (her kategori farklı renk)
- Payload özetleri
- Event akış istatistikleri
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

from core.logger import logger
from shared.events import event_bus
from shared.events.events import Event


# ============================================================================
# RENK KODLARI (ANSI Terminal Colors)
# ============================================================================

class Colors:
    """Terminal renk kodları"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    
    # Event kategorileri
    BOT = '\033[92m'      # Yeşil
    SIGNAL = '\033[94m'   # Mavi
    POSITION = '\033[96m' # Cyan
    ML = '\033[95m'       # Magenta
    DATA = '\033[93m'     # Sarı
    RISK = '\033[91m'     # Kırmızı
    TRADE = '\033[97m'    # Beyaz
    SYSTEM = '\033[90m'   # Gri
    
    # Durumlar
    SUCCESS = '\033[92m'
    WARNING = '\033[93m'
    ERROR = '\033[91m'
    INFO = '\033[94m'


# ============================================================================
# EVENT KATEGORİLERİ
# ============================================================================

class EventCategory(str, Enum):
    """Event kategorileri"""
    BOT = "bot"
    SIGNAL = "signal"
    POSITION = "position"
    ML = "ml"
    DATA = "data"
    RISK = "risk"
    TRADE = "trade"
    SYSTEM = "system"
    UNKNOWN = "unknown"


# ============================================================================
# EVENT TRACER
# ============================================================================

class EventTracer:
    """
    Event Tracer - Sistem Röntgeni
    
    EventBus'a subscribe olarak tüm event'leri dinler ve
    terminale renkli, formatlı çıktı üretir.
    """
    
    def __init__(self, enabled: bool = True, show_payload: bool = True):
        """
        Args:
            enabled: Tracer aktif mi?
            show_payload: Payload detayları gösterilsin mi?
        """
        self.enabled = enabled
        self.show_payload = show_payload
        self.event_count: Dict[str, int] = {}
        self.start_time: Optional[datetime] = None
        self._running = False
        
        logger.info("🔍 Event Tracer hazır")
    
    async def start(self):
        """Event tracer'ı başlat"""
        if not self.enabled:
            logger.info("⚠️ Event Tracer kapalı")
            return
        
        logger.info("=" * 70)
        logger.info("🔍 EVENT TRACER BAŞLATILIYOR - Sistem Röntgeni")
        logger.info("=" * 70)
        
        self.start_time = datetime.utcnow()
        self._running = True
        
        # Tüm event kategorilerine abone ol
        self._subscribe_to_all_events()
        
        logger.info("✅ Event Tracer aktif - Tüm event'ler dinleniyor")
        logger.info("-" * 70)
    
    async def stop(self):
        """Event tracer'ı durdur"""
        self._running = False
        self._print_statistics()
        logger.info("🛑 Event Tracer durduruldu")
    
    def _subscribe_to_all_events(self):
        """Tüm event kategorilerine abone ol"""
        # Wildcard subscription (tüm event'leri yakala)
        event_bus.subscribe("*", self._on_event)
        
        # Spesifik kategoriler (daha detaylı log için)
        for category in EventCategory:
            event_bus.subscribe(f"{category.value}.*", self._on_category_event)
    
    def _on_event(self, event: Event):
        """
        Generic event handler (tüm event'leri yakalar)
        
        Args:
            event: Gelen event
        """
        if not self._running:
            return
        
        # Event sayısını artır
        category = self._get_category(event.type)
        self.event_count[category.value] = self.event_count.get(category.value, 0) + 1
        
        # Renkli output
        self._print_event(event, category)
    
    def _on_category_event(self, event: Event):
        """
        Kategori-specific event handler
        
        Args:
            event: Gelen event
        """
        # Ekstra detay logları burada eklenebilir
        pass
    
    def _get_category(self, event_type: str) -> EventCategory:
        """
        Event tipinden kategori belirle
        
        Args:
            event_type: Event tipi (örn: "bot.started")
        
        Returns:
            EventCategory enum
        """
        for category in EventCategory:
            if event_type.startswith(f"{category.value}."):
                return category
        
        return EventCategory.UNKNOWN
    
    def _get_color(self, category: EventCategory) -> str:
        """
        Kategoriye göre renk al
        
        Args:
            category: Event kategorisi
        
        Returns:
            ANSI renk kodu
        """
        color_map = {
            EventCategory.BOT: Colors.BOT,
            EventCategory.SIGNAL: Colors.SIGNAL,
            EventCategory.POSITION: Colors.POSITION,
            EventCategory.ML: Colors.ML,
            EventCategory.DATA: Colors.DATA,
            EventCategory.RISK: Colors.RISK,
            EventCategory.TRADE: Colors.TRADE,
            EventCategory.SYSTEM: Colors.SYSTEM,
            EventCategory.UNKNOWN: Colors.RESET,
        }
        
        return color_map.get(category, Colors.RESET)
    
    def _format_payload(self, payload: Dict[str, Any]) -> str:
        """
        Payload'u formatla (özet)
        
        Args:
            payload: Event payload
        
        Returns:
            Formatlanmış payload string
        """
        if not payload or not self.show_payload:
            return ""
        
        # Önemli alanları öne çıkar
        important_keys = [
            'symbol', 'bot_id', 'strategy_id', 'timeframe',
            'signal', 'recommendation', 'confidence', 'pnl',
            'direction', 'entry_price', 'exit_price', 'size',
            'status', 'progress', 'message'
        ]
        
        parts = []
        for key in important_keys:
            if key in payload:
                value = payload[key]
                
                # Değerleri kısalt
                if isinstance(value, float):
                    value = f"{value:.4f}" if value < 1 else f"{value:.2f}"
                elif isinstance(value, str) and len(value) > 50:
                    value = value[:47] + "..."
                
                parts.append(f"{key}: {value}")
        
        # Diğer alanları ekle (max 3 tane)
        other_count = 0
        for key, value in payload.items():
            if key not in important_keys and other_count < 3:
                if isinstance(value, (str, int, float, bool)):
                    parts.append(f"{key}: {value}")
                    other_count += 1
        
        return " | ".join(parts)
    
    def _print_event(self, event: Event, category: EventCategory):
        """
        Event'i terminale renkli yazdır
        
        Args:
            event: Event objesi
            category: Event kategorisi
        """
        color = self._get_color(category)
        timestamp = datetime.utcnow().strftime("%H:%M:%S.%f")[:-3]
        
        # Emoji mapping
        emoji_map = {
            EventCategory.BOT: "🤖",
            EventCategory.SIGNAL: "📊",
            EventCategory.POSITION: "💼",
            EventCategory.ML: "🧠",
            EventCategory.DATA: "📦",
            EventCategory.RISK: "⚠️",
            EventCategory.TRADE: "💰",
            EventCategory.SYSTEM: "⚙️",
            EventCategory.UNKNOWN: "📝",
        }
        
        emoji = emoji_map.get(category, "📝")
        
        # Format: [TIMESTAMP] [CATEGORY] EMOJI event.type | Payload
        output = (
            f"{Colors.DIM}[{timestamp}]{Colors.RESET} "
            f"{color}{Colors.BOLD}[{category.value.upper()}]{Colors.RESET} "
            f"{emoji} {color}{event.type}{Colors.RESET}"
        )
        
        # Payload ekle
        if event.payload and self.show_payload:
            payload_str = self._format_payload(event.payload)
            if payload_str:
                output += f" | {Colors.DIM}{payload_str}{Colors.RESET}"
        
        # Source ekle
        if event.source and event.source != "unknown":
            output += f" {Colors.DIM}(from: {event.source}){Colors.RESET}"
        
        # AKILLI FİLTRELEME: Repetitive (tekrarlayan) eventleri DEBUG seviyesine çek
        # Böylece sadece kritik olaylar (Sinyal, Pozisyon, Trade) INFO olarak görünür.
        if category in [EventCategory.DATA, EventCategory.SYSTEM] or "processed" in event.type:
            logger.debug(output)
        else:
            logger.info(output)
    
    def _print_statistics(self):
        """Event istatistiklerini yazdır"""
        if not self.start_time:
            return
        
        duration = datetime.utcnow() - self.start_time
        total_events = sum(self.event_count.values())
        
        logger.info("=" * 70)
        logger.info("📊 EVENT İSTATİSTİKLERİ")
        logger.info("=" * 70)
        logger.info(f"⏱️  Çalışma Süresi: {duration}")
        logger.info(f"📈 Toplam Event: {total_events}")
        logger.info("-" * 70)
        
        # Kategori bazlı dağılım
        for category, count in sorted(self.event_count.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_events * 100) if total_events > 0 else 0
            color = self._get_color(EventCategory(category))
            
            bar_length = int(percentage / 5)  # Max 20 karakter
            bar = "█" * bar_length + "░" * (20 - bar_length)
            
            logger.info(
                f"{color}{category.upper():12}{Colors.RESET} | "
                f"{bar} | {count:5d} ({percentage:5.1f}%)"
            )
        
        logger.info("=" * 70)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Event istatistiklerini al
        
        Returns:
            Dict with stats
        """
        return {
            'running': self._running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'total_events': sum(self.event_count.values()),
            'by_category': self.event_count.copy(),
        }


# ============================================================================
# GLOBAL TRACER INSTANCE
# ============================================================================

# Ana tracer instance (main.py'de kullanılacak)
event_tracer = EventTracer(enabled=True, show_payload=True)


# ============================================================================
# QUICK START (main.py için)
# ============================================================================

async def start_event_tracer():
    """
    Event tracer'ı başlat (main.py'den çağrılacak)
    
    Usage:
        from core.diagnostics.event_tracer import start_event_tracer
        await start_event_tracer()
    """
    await event_tracer.start()
    logger.info("✅ Event Tracer başlatıldı")


async def stop_event_tracer():
    """
    Event tracer'ı durdur (shutdown'da çağrılacak)
    """
    await event_tracer.stop()
