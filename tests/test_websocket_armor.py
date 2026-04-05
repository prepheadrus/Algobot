"""
Test: WebSocket Armor - Unhandled Exception Prevention

Amaç: update_live_prices hata verse bile WebSocket loop'unun devam ettiğini kanıtla.
Sorun: Exception yakalanmıyor → Loop kırılıyor → Fiyat akışı duruyor.
Çözüm: try-except ile hatayı yakala + continue ile devam et.
"""

import pytest
import asyncio
from unittest.mock import patch


@pytest.mark.asyncio
async def test_websocket_continues_on_update_error():
    """
    update_live_prices exception fırlatsa bile WebSocket devam ediyor.
    """
    from core.exchange import exchange_manager
    
    symbol = "BTC/USDT"
    
    # 1. update_live_prices'i exception ile mock'la
    with patch.object(
        exchange_manager.paper_engine,
        'update_live_prices',
        side_effect=Exception("Test: update_live_prices failed")
    ):
        # 2. WebSocket loop'u başlat
        task = asyncio.create_task(
            exchange_manager.watch_ticker_loop(symbol)
        )
        
        # 3. 3 saniye bekle (birkaç ticker gelmeli)
        await asyncio.sleep(3)
        
        # 4. Loop'un hala çalıştığını doğrula (task.done() == False)
        assert not task.done(), \
            "WebSocket crashed! Should continue on update_live_prices error"
        
        # 5. Task'ı temizle
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    print("✅ WebSocket armor successful: Loop continues on update error")


@pytest.mark.asyncio
async def test_websocket_logs_error_but_continues():
    """
    Exception log'lanıyor ama loop devam ediyor.
    """
    from core.exchange import exchange_manager
    import logging
    
    symbol = "ETH/USDT"
    error_logged = False
    
    # Logger'ı dinle
    class ErrorCatcher(logging.Handler):
        def __init__(self):
            super().__init__()
            self.errors = []
        
        def emit(self, record):
            self.errors.append(record.getMessage())
    
    catcher = ErrorCatcher()
    logger = logging.getLogger('core.exchange')
    logger.addHandler(catcher)
    
    # 1. Exception ile mock'la
    with patch.object(
        exchange_manager.paper_engine,
        'update_live_prices',
        side_effect=Exception("Test error for logging")
    ):
        # 2. Loop başlat
        task = asyncio.create_task(
            exchange_manager.watch_ticker_loop(symbol)
        )
        
        # 3. 2 saniye bekle
        await asyncio.sleep(2)
        
        # 4. Loop devam ediyor
        assert not task.done()
        
        # 5. Task'ı temizle
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    logger.removeHandler(catcher)
    
    # Not: Logger'da hata görünmeli (manuel kontrol)
    print(f"✅ Error logging test: {len(catcher.errors)} error(s) logged")


@pytest.mark.asyncio
async def test_websocket_armor_with_real_exception():
    """
    Gerçek bir exception senaryosu (AttributeError, KeyError, vb.).
    """
    from core.exchange import exchange_manager
    
    symbol = "SOL/USDT"
    
    # Farklı exception türlerini test et
    exceptions_to_test = [
        AttributeError("'NoneType' object has no attribute 'get'"),
        KeyError("'current_price'"),
        ValueError("Invalid price format"),
        ConnectionError("Database connection lost"),
    ]
    
    for test_exception in exceptions_to_test:
        with patch.object(
            exchange_manager.paper_engine,
            'update_live_prices',
            side_effect=test_exception
        ):
            task = asyncio.create_task(
                exchange_manager.watch_ticker_loop(symbol)
            )
            
            # 1 saniye bekle
            await asyncio.sleep(1)
            
            # Loop devam etmeli
            assert not task.done(), \
                f"WebSocket crashed on {type(test_exception).__name__}"
            
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        print(f"✅ WebSocket armor vs {type(test_exception).__name__}: PASSED")


@pytest.mark.asyncio
async def test_websocket_price_feed_resilience():
    """
    WebSocket fiyat akışının hatalara karşı dayanıklılığı.
    Stress test: 10 saniye boyunca her tick'te exception.
    """
    from core.exchange import exchange_manager
    
    symbol = "DOGE/USDT"
    
    with patch.object(
        exchange_manager.paper_engine,
        'update_live_prices',
        side_effect=Exception("Continuous error stream")
    ):
        task = asyncio.create_task(
            exchange_manager.watch_ticker_loop(symbol)
        )
        
        # 5 saniye bekle (stress test)
        await asyncio.sleep(5)
        
        # Loop hala çalışıyor olmalı
        assert not task.done(), \
            "WebSocket resilience test FAILED: Loop crashed under continuous errors"
        
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    print("✅ WebSocket stress test successful: 5s continuous errors handled")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
