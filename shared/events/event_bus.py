"""
Event Bus - Asenkron Pub/Sub Mimarisi

Modüller arası sıkı bağımlılığı (tight coupling) çözmek için
Event-Driven Architecture (EDA) implementasyonu.

Kullanım:
    # Subscribe
    event_bus.subscribe("bot.started", my_handler)
    
    # Publish
    await event_bus.publish(Event(type="bot.started", payload={...}))

Özellikler:
- Asenkron event işleme
- Tip güvenliği için Pydantic
- Thread-safe subscriber yönetimi
- Event queue ile load leveling
- Error isolation (bir handler hatası diğerlerini etkilemez)
"""

import asyncio
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
from core.logger import logger


# ============================================================================
# EVENT BASE CLASS
# ============================================================================

@dataclass
class Event:
    """
    Base Event class.
    Tüm event'ler bu sınıftan türer.
    
    Attributes:
        type: Event tipi (örn: "bot.started", "position.opened")
        payload: Event verisi (dict)
        timestamp: Event zamanı (UTC)
        source: Event'i yayınlayan modül
        id: Benzersiz event ID
    """
    type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: str = "unknown"
    id: str = field(default_factory=lambda: f"evt_{datetime.utcnow().timestamp()}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Event'i dict'e çevir (serialization için)"""
        return {
            'id': self.id,
            'type': self.type,
            'payload': self.payload,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source
        }
    
    def to_json(self) -> str:
        """Event'i JSON'a çevir"""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Dict'ten Event oluştur"""
        return cls(
            id=data.get('id', f"evt_{datetime.utcnow().timestamp()}"),
            type=data['type'],
            payload=data.get('payload', {}),
            timestamp=datetime.fromisoformat(data['timestamp']) if isinstance(data['timestamp'], str) else data['timestamp'],
            source=data.get('source', 'unknown')
        )
    
    def __str__(self) -> str:
        return f"Event(type={self.type}, id={self.id}, source={self.source})"


# ============================================================================
# EVENT BUS (PUB/SUB)
# ============================================================================

class EventBus:
    """
    Asenkron Event Bus (Pub/Sub Pattern).
    
    Modüller arası direkt fonksiyon çağrıları yerine,
    event'ler ile loose coupling sağlar.
    
    Pattern: Publisher-Subscriber
    Thread Safety: asyncio.Lock ile korunuyor
    Queue: asyncio.Queue ile non-blocking
    
    Örnek Kullanım:
        # Singleton instance
        from shared.events.event_bus import event_bus
        
        # Subscribe (bir modül içinde)
        event_bus.subscribe("position.opened", on_position_opened)
        
        # Publish (başka bir modül içinde)
        await event_bus.publish(Event(
            type="position.opened",
            payload={'bot_id': 'BTC_123', 'symbol': 'BTC/USDT'},
            source="position_manager"
        ))
    """
    
    _instance: Optional['EventBus'] = None
    _lock: asyncio.Lock = None
    
    def __new__(cls) -> 'EventBus':
        """Singleton pattern - tek instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize (sadece bir kez)"""
        if self._initialized:
            return
        
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_queue: asyncio.Queue = None
        self._running: bool = False
        self._worker_tasks: List[asyncio.Task] = []
        self._lock = None
        self._event_count: int = 0
        self._error_count: int = 0
        self._max_queue_size: int = 10000
        self._num_workers: int = 3  # Parallel event processor sayısı
        
        self._initialized = True
        logger.info("📬 Event Bus initialized (Singleton)")
    
    @property
    def running(self) -> bool:
        """Event bus çalışıyor mu?"""
        return self._running
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Event bus istatistikleri"""
        return {
            'running': self._running,
            'queue_size': self._event_queue.qsize() if self._event_queue else 0,
            'event_count': self._event_count,
            'error_count': self._error_count,
            'subscriber_count': sum(len(handlers) for handlers in self._subscribers.values()),
            'event_types': len(self._subscribers),
            'worker_count': len(self._worker_tasks)
        }
    
    async def _ensure_initialized(self):
        """Async initialization (queue ve lock)"""
        if self._event_queue is None:
            self._event_queue = asyncio.Queue(maxsize=self._max_queue_size)
        if self._lock is None:
            self._lock = asyncio.Lock()
    
    # ========================================================================
    # SUBSCRIPTION MANAGEMENT
    # ========================================================================
    
    def subscribe(self, event_type: str, handler: Callable, priority: int = 0):
        """
        Event'e abone ol.
        
        Args:
            event_type: Event tipi (örn: "position.opened")
                       Wildcard destekler: "position.*" veya "*"
            handler: Callback fonksiyon (async veya sync olabilir)
            priority: Öncelik (yüksek sayı = yüksek öncelik)
        
        Örnek:
            def on_position_opened(event: Event):
                logger.info(f"Pozisyon açıldı: {event.payload}")
            
            event_bus.subscribe("position.opened", on_position_opened)
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        # Priority'ye göre sırala (yüksek öncelik önce)
        self._subscribers[event_type].append((priority, handler))
        self._subscribers[event_type].sort(key=lambda x: x[0], reverse=True)
        
        logger.debug(f"📬 Subscribe: {event_type} -> {handler.__name__} (priority={priority})")
    
    def unsubscribe(self, event_type: str, handler: Callable) -> bool:
        """
        Abonelikten çık.
        
        Returns:
            True: Başarıyla silindi
            False: Handler bulunamadı
        """
        if event_type not in self._subscribers:
            return False
        
        handlers = self._subscribers[event_type]
        for i, (_, h) in enumerate(handlers):
            if h == handler:
                del handlers[i]
                logger.debug(f"📤 Unsubscribe: {event_type} -> {handler.__name__}")
                
                # Liste boşaldıysa temizle
                if not handlers:
                    del self._subscribers[event_type]
                
                return True
        
        return False
    
    def clear_subscribers(self, event_type: Optional[str] = None):
        """
        Subscriber'ları temizle.
        
        Args:
            event_type: Belirli event tipi (None ise tümü)
        """
        if event_type:
            if event_type in self._subscribers:
                del self._subscribers[event_type]
                logger.debug(f"🧹 Subscribers temizlendi: {event_type}")
        else:
            self._subscribers.clear()
            logger.info("🧹 Tüm subscribers temizlendi")
    
    # ========================================================================
    # EVENT PUBLISHING
    # ========================================================================
    
    async def publish(self, event: Event):
        """
        Event yayınla (non-blocking).
        
        Event queue'ya eklenir ve worker'lar tarafından işlenir.
        
        Args:
            event: Yayınlanacak event
        
        Raises:
            asyncio.QueueFull: Queue dolu ise (maxsize aşıldı)
        
        Örnek:
            event = Event(
                type="bot.started",
                payload={'bot_id': 'BTC_123'},
                source="bot_manager"
            )
            await event_bus.publish(event)
        """
        await self._ensure_initialized()
        
        try:
            # Queue'ya ekle (non-blocking)
            self._event_queue.put_nowait(event)
            self._event_count += 1
            
            logger.debug(f"📤 Event published: {event}")
            
        except asyncio.QueueFull:
            logger.warning(f"⚠️ Event queue dolu! Event atılıyor: {event.type}")
            self._error_count += 1
            raise
    
    def publish_sync(self, event: Event):
        """
        Senkron publish (acil durumlar için).
        
        NOT: Sadece event loop dışından çağırılabilir!
        """
        try:
            self._event_queue.put_nowait(event)
            self._event_count += 1
            logger.debug(f"📤 Event published (sync): {event}")
        except asyncio.QueueFull:
            logger.warning(f"⚠️ Event queue dolu! Event atılıyor: {event.type}")
            self._error_count += 1
    
    # ========================================================================
    # EVENT PROCESSING
    # ========================================================================
    
    async def start(self, num_workers: int = 3):
        """
        Event processor'ları başlat.
        
        Args:
            num_workers: Parallel worker sayısı
        
        NOT: Bu metod bir kez, uygulama başlangıcında çağrılmalı.
        """
        if self._running:
            logger.warning("Event bus zaten çalışıyor")
            return
        
        await self._ensure_initialized()
        
        self._running = True
        self._num_workers = num_workers
        
        # Worker'ları başlat
        for i in range(num_workers):
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self._worker_tasks.append(task)
        
        logger.info(f"🚀 Event Bus başlatıldı ({num_workers} worker)")
    
    async def stop(self, timeout: float = 5.0):
        """
        Event bus'u durdur.
        
        Args:
            timeout: Worker'lar için bekleme süresi
        """
        if not self._running:
            return
        
        logger.info("🛑 Event Bus durduruluyor...")
        self._running = False
        
        # Worker'ları bekle
        if self._worker_tasks:
            done, pending = await asyncio.wait(
                self._worker_tasks,
                timeout=timeout
            )
            
            # Pending task'ları iptal et
            for task in pending:
                task.cancel()
            
            self._worker_tasks.clear()
        
        logger.info("✅ Event Bus durduruldu")
    
    async def _worker(self, worker_name: str):
        """
        Event worker (internal).

        Queue'dan event'leri alır ve handler'lara gönderir.
        Kritik hatalarda worker yeniden başlatılır.
        """
        logger.debug(f"👷 {worker_name} başlatıldı")
        
        consecutive_errors = 0
        max_consecutive_errors = 10

        while self._running:
            try:
                # Queue'dan event al (timeout ile)
                try:
                    event = await asyncio.wait_for(
                        self._event_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    consecutive_errors = 0  # Reset counter on success
                    continue

                # Event işle
                await self._process_event(event, worker_name)

                # Queue'ya geri bildir
                self._event_queue.task_done()
                consecutive_errors = 0  # Reset counter on success

            except asyncio.CancelledError:
                logger.debug(f"👷 {worker_name} iptal edildi")
                break
            except (MemoryError, ConnectionError, OSError) as critical_err:
                # KRİTİK HATA: Worker yeniden başlatılmalı
                consecutive_errors += 1
                logger.critical(
                    f"🚨 [EVENT BUS] KRİTİK HATA ({worker_name}): {critical_err} | "
                    f"Worker yeniden başlatılıyor... (Hata: {consecutive_errors}/{max_consecutive_errors})"
                )
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(f"🚨 [EVENT BUS] {worker_name} çok fazla kritik hata, devre dışı bırakılıyor")
                    self._error_count += consecutive_errors
                    break
                
                # Worker'ı yeniden başlat
                await asyncio.sleep(1.0)
                asyncio.create_task(self._worker(f"{worker_name}_restart"))
                break
            except Exception as e:
                # Normal hata
                consecutive_errors += 1
                logger.error(f"👷 {worker_name} hatası: {e} (Artış: {consecutive_errors})")
                
                if consecutive_errors >= max_consecutive_errors:
                    logger.critical(f"🚨 [EVENT BUS] {worker_name} art arda {consecutive_errors} hata, yeniden başlatılıyor")
                    consecutive_errors = 0
                
                await asyncio.sleep(0.1)  # CPU spike önleme

        logger.debug(f"👷 {worker_name} durduruldu")
    
    async def _process_event(self, event: Event, worker_name: str):
        """
        Event işle (handler'ları çağır).
        
        Error isolation: Bir handler hatası diğerlerini etkilemez.
        """
        event_type = event.type
        handlers = await self._get_handlers_for_event(event_type)
        
        if not handlers:
            logger.debug(f"📭 {event_type} için abone yok")
            return
        
        logger.debug(f"🔧 {worker_name}: {event_type} işleniyor ({len(handlers)} handler)")
        
        for handler in handlers:
            try:
                # Handler çağır (async veya sync)
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
                    
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self._error_count += 1
                logger.error(
                    f"❌ Handler hatası ({event_type}, {handler.__name__}): {e}",
                    exc_info=True
                )
    
    async def _get_handlers_for_event(self, event_type: str) -> List[Callable]:
        """
        Event için tüm handler'ları bul (wildcard desteği).
        
        Örnek:
            "position.opened" event'i için:
            - "position.opened" handler'ları
            - "position.*" handler'ları
            - "*" handler'ları
        """
        handlers = []
        
        async with self._lock or asyncio.Lock():
            # Exact match
            if event_type in self._subscribers:
                handlers.extend([h for _, h in self._subscribers[event_type]])
            
            # Wildcard match (position.* -> position.opened)
            wildcard_pattern = f"{event_type.split('.')[0]}.*"
            if wildcard_pattern in self._subscribers:
                handlers.extend([h for _, h in self._subscribers[wildcard_pattern]])
            
            # Global wildcard (* -> her şey)
            if "*" in self._subscribers:
                handlers.extend([h for _, h in self._subscribers["*"]])
        
        return handlers
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    async def wait_for_event(
        self,
        event_type: str,
        timeout: Optional[float] = None,
        predicate: Optional[Callable[[Event], bool]] = None
    ) -> Event:
        """
        Belirli bir event'i bekle (blocking).
        
        Args:
            event_type: Beklenecek event tipi
            timeout: Maksimum bekleme süresi (None = sonsuz)
            predicate: Ek filtre (opsiyonel)
        
        Returns:
            Eşleşen event
        
        Raises:
            asyncio.TimeoutError: Timeout aşılırsa
        
        Örnek:
            # "bot.started" event'ini bekle
            event = await event_bus.wait_for_event("bot.started", timeout=5.0)
        """
        future = asyncio.Future()
        
        def handler(event: Event):
            if predicate is None or predicate(event):
                if not future.done():
                    future.set_result(event)
        
        # Geçici subscriber ekle
        self.subscribe(event_type, handler, priority=999)
        
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            # Subscriber'ı temizle
            self.unsubscribe(event_type, handler)
    
    def get_subscribers(self, event_type: Optional[str] = None) -> Dict[str, int]:
        """
        Subscriber sayılarını al.
        
        Args:
            event_type: Belirli event tipi (None ise tümü)
        
        Returns:
            {event_type: subscriber_count}
        """
        if event_type:
            return {
                event_type: len(self._subscribers.get(event_type, []))
            }
        else:
            return {
                evt_type: len(handlers)
                for evt_type, handlers in self._subscribers.items()
            }


# ============================================================================
# GLOBAL SINGLETON INSTANCE
# ============================================================================

# Tüm modüller bu instance'ı kullanır
event_bus = EventBus()


# ============================================================================
# DECORATORS (Kolay kullanım için)
# ============================================================================

def on_event(event_type: str, priority: int = 0):
    """
    Decorator: Fonksiyonu event'e otomatik abone yapar.
    
    Kullanım:
        @on_event("position.opened")
        async def handle_position_opened(event: Event):
            logger.info(f"Pozisyon açıldı: {event.payload}")
    """
    def decorator(handler: Callable):
        event_bus.subscribe(event_type, handler, priority)
        return handler
    return decorator


def publish_event(event_type: str, source: str = "unknown"):
    """
    Decorator: Fonksiyon dönüşünü event olarak yayınlar.
    
    Kullanım:
        @publish_event("bot.started", source="bot_manager")
        def start_bot(bot_id: str):
            # ... bot başlat ...
            return {'bot_id': bot_id, 'status': 'started'}
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            if asyncio.iscoroutine(result):
                result = await result
            
            # Result'ı payload olarak kullan
            if isinstance(result, dict):
                event = Event(
                    type=event_type,
                    payload=result,
                    source=source
                )
                await event_bus.publish(event)
            
            return result
        return wrapper
    return decorator
