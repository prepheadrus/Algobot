"""
Circuit Breaker Pattern

Dış servis çağrılarında (Exchange API, Database, ML Inference) kademeli hata yönetimi.
Overload durumunda sistemi korur ve otomatik recovery sağlar.

Usage:
    from core.circuit_breaker import CircuitBreaker
    
    breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
    
    @breaker
    async def fetch_data():
        return await exchange.fetch_ohlcv(...)
"""

import asyncio
import time
from functools import wraps
from typing import Callable, Any, Optional, Dict
from enum import Enum
from core.logger import logger


class CircuitState(str, Enum):
    """Circuit durumları"""
    CLOSED = "closed"      # Normal çalışma
    OPEN = "open"         # Devre açık, çağrı reddediliyor
    HALF_OPEN = "half_open"  # Recovery testi


class CircuitBreakerError(Exception):
    """Circuit breaker açıkken fırlatılan hata"""
    pass


class CircuitBreaker:
    """
    Circuit Breaker Pattern Implementation.
    
    3 Durum:
    1. CLOSED: Normal çalışma. Hatalar sayılır.
    2. OPEN: Devre açık. Tüm çağrılar reddedilir.
    3. HALF_OPEN: Recovery testi. Tek çağrı izin verilir.
    
    Parametreler:
    - failure_threshold: Devreyi açacak ardışık hata sayısı
    - recovery_timeout: Devreyi kapatacak bekleme süresi (saniye)
    - success_threshold: HALF_OPEN'da başarılı olursa devreyi kapatacak başarı sayısı
    - expected_exceptions: Hangi hatalar sayılacak (tuple)
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 3,
        expected_exceptions: tuple = (Exception,)
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.expected_exceptions = expected_exceptions
        
        # State tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_state_change: float = time.time()
        
        # İstatistikler
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        self.total_rejected = 0
        
        logger.debug(
            f"🔌 Circuit Breaker initialized | "
            f"failure_threshold={failure_threshold}, "
            f"recovery_timeout={recovery_timeout}s"
        )
    
    def _should_allow_request(self) -> bool:
        """Çağrıya izin verilsin mi?"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Recovery timeout geçti mi?
            if self.last_failure_time is None:
                return True
            
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.recovery_timeout:
                logger.info(f"🔌 [HALF_OPEN] Recovery timeout ({elapsed:.1f}s >= {self.recovery_timeout}s)")
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            
            return False
        
        # HALF_OPEN - Tek çağrıya izin ver
        return True
    
    def _transition_to(self, new_state: CircuitState):
        """Durum geçişi"""
        old_state = self.state
        self.state = new_state
        self.last_state_change = time.time()
        
        if new_state == CircuitState.CLOSED:
            self.failure_count = 0
            self.success_count = 0
        
        logger.info(
            f"🔌 [STATE CHANGE] {old_state.value} → {new_state.value} | "
            f"failures={self.failure_count}, successes={self.success_count}"
        )
    
    def _on_success(self):
        """Başarılı çağrı"""
        self.total_successes += 1
        
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            
            # Success threshold'a ulaşıldı mı?
            if self.success_count >= self.success_threshold:
                logger.info(f"✅ [CIRCUIT BREAKER] {self.success_count} başarılı çağrı, devre kapanıyor")
                self._transition_to(CircuitState.CLOSED)
        
        elif self.state == CircuitState.CLOSED:
            # Ardışık hataları sıfırla
            if self.failure_count > 0:
                self.failure_count = 0
    
    def _on_failure(self, exception: Exception):
        """Başarısız çağrı"""
        self.total_failures += 1
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            # HALF_OPEN'da hata → direkt OPEN
            logger.warning(f"⚠️ [CIRCUIT BREAKER] HALF_OPEN'da hata, devre açılıyor: {exception}")
            self._transition_to(CircuitState.OPEN)
        
        elif self.state == CircuitState.CLOSED:
            # Threshold aşıldı mı?
            if self.failure_count >= self.failure_threshold:
                logger.critical(
                    f"🚨 [CIRCUIT BREAKER] {self.failure_count} ardışık hata (threshold={self.failure_threshold}), "
                    f"devre açılıyor! Recovery timeout: {self.recovery_timeout}s"
                )
                self._transition_to(CircuitState.OPEN)
    
    def __call__(self, func: Callable):
        """Decorator olarak kullan"""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self._call_async(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return self._call_sync(func, *args, **kwargs)
        
        # Async veya sync fonksiyon olduğunu tespit et
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    async def _call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Async fonksiyon çağrısı"""
        self.total_calls += 1
        
        # Circuit açık mı?
        if not self._should_allow_request():
            self.total_rejected += 1
            raise CircuitBreakerError(
                f"Circuit breaker OPEN ({self.failure_count} failures, "
                f"last failure {time.time() - self.last_failure_time:.1f}s ago)"
            )
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.expected_exceptions as e:
            self._on_failure(e)
            raise
        
        except Exception as e:
            # Beklenmeyen hata → her zaman say
            self._on_failure(e)
            raise
    
    def _call_sync(self, func: Callable, *args, **kwargs) -> Any:
        """Sync fonksiyon çağrısı"""
        self.total_calls += 1
        
        # Circuit açık mı?
        if not self._should_allow_request():
            self.total_rejected += 1
            raise CircuitBreakerError(
                f"Circuit breaker OPEN ({self.failure_count} failures, "
                f"last failure {time.time() - self.last_failure_time:.1f}s ago)"
            )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.expected_exceptions as e:
            self._on_failure(e)
            raise
        
        except Exception as e:
            self._on_failure(e)
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Circuit breaker istatistikleri"""
        return {
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'total_calls': self.total_calls,
            'total_successes': self.total_successes,
            'total_failures': self.total_failures,
            'total_rejected': self.total_rejected,
            'last_failure_time': self.last_failure_time,
            'last_state_change': self.last_state_change,
            'uptime_in_state': time.time() - self.last_state_change
        }
    
    def reset(self):
        """Circuit breaker'ı sıfırla"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_state_change = time.time()
        logger.info("🔌 [CIRCUIT BREAKER] Manuel reset")


# ============================================================================
# PREDEFINED CIRCUIT BREAKERS
# ============================================================================

# Exchange API çağrıları için
exchange_breaker = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=60,
    success_threshold=3,
    expected_exceptions=(Exception,)
)

# Database çağrıları için
database_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=30,
    success_threshold=2,
    expected_exceptions=(Exception,)
)

# ML Inference çağrıları için
ml_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=120,
    success_threshold=2,
    expected_exceptions=(Exception,)
)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_all_breakers_stats() -> Dict[str, Any]:
    """Tüm predefined breaker'ların istatistikleri"""
    return {
        'exchange': exchange_breaker.get_stats(),
        'database': database_breaker.get_stats(),
        'ml': ml_breaker.get_stats()
    }


def reset_all_breakers():
    """Tüm breaker'ları sıfırla"""
    exchange_breaker.reset()
    database_breaker.reset()
    ml_breaker.reset()
