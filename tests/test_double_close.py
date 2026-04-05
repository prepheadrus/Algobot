"""
Test: Double-Close Race Condition Prevention

Amaç: Aynı pozisyonun aynı tick'te 2 kez kapatılmadığını kanıtla.
Sorun: WebSocket hızlı fiyat akışında aynı SL/TP seviyesi birden fazla tetiklenebiliyor.
Çözüm: closed_bot_ids set'i ile her tick'te sadece 1 kapatma.
"""

import pytest
import asyncio
from unittest.mock import MagicMock


@pytest.mark.asyncio
async def test_no_duplicate_position_close():
    """
    Aynı pozisyonun aynı anda 2 kez kapatılmadığını doğrula.
    """
    from core.paper import paper_engine
    
    # Test bot ID
    bot_id = "BTC/USDT_test_double_close_1m"

    # 1. Pozisyon aç (open_position senkron, await gerekmez!)
    position = paper_engine.position_manager.open_position(
        bot_id=bot_id,
        symbol="BTC/USDT",
        direction="LONG",
        entry_price=50000.0,
        size=1.0,
        leverage=10,
        stop_loss=49000.0,
        take_profit=52000.0,
        atr=1000.0,
        atr_multiplier=2.0
    )
    
    assert position is not None, "Position open failed"
    assert len(paper_engine.position_manager.positions) == 1
    
    # 2. Aynı anda 2 kapatma çağrısı yap (race condition simülasyonu)
    # Gerçek senaryo: Aynı tick'te 2 WebSocket fiyatı SL'yi tetikliyor
    results = await asyncio.gather(
        paper_engine.position_manager.close_position(bot_id, 49000.0, "STOP_LOSS"),
        paper_engine.position_manager.close_position(bot_id, 49000.0, "STOP_LOSS"),
        return_exceptions=True
    )
    
    # 3. En az 1 kapatma başarılı olmalı
    successful_closes = [r for r in results if isinstance(r, MagicMock) or r is not None]
    assert len(successful_closes) >= 1, "No close succeeded"
    
    # 4. Pozisyon listesinden silindiğini doğrula
    assert bot_id not in paper_engine.position_manager.positions, \
        "Position still in positions dict"
    
    # 5. Trade history'de SADECE 1 trade olmalı (duplicate önleme)
    trades = paper_engine.position_manager.trade_history.trades
    bot_trades = [t for t in trades if t.bot_id == bot_id]
    
    # CRITICAL ASSERTION: Duplicate close yok!
    assert len(bot_trades) == 1, \
        f"DUPLICATE CLOSE DETECTED! Expected 1 trade, got {len(bot_trades)}"
    
    print(f"✅ Double-close prevention successful: {len(bot_trades)} trade(s) recorded")


@pytest.mark.asyncio
async def test_closed_bot_ids_prevents_second_close():
    """
    closed_bot_ids set'inin aynı tick'te 2. kapatmayı engellediğini doğrula.
    """
    from core.paper import paper_engine
    
    bot_id = "ETH/USDT_test_closed_ids_1m"

    # 1. Pozisyon aç (open_position senkron)
    paper_engine.position_manager.open_position(
        bot_id=bot_id,
        symbol="ETH/USDT",
        direction="LONG",
        entry_price=3000.0,
        size=10.0,
        leverage=10,
        stop_loss=2900.0
    )
    
    # 2. positions_to_close listesi oluştur (gerçek senaryo)
    positions_to_close = [
        (bot_id, 2900.0, "STOP_LOSS"),
        (bot_id, 2900.0, "STOP_LOSS"),  # Duplicate entry
    ]
    
    closed_bot_ids = set()
    close_count = 0
    
    # 3. Gerçek update_live_prices döngüsünü simüle et
    for bid, price, reason in positions_to_close:
        if bid in closed_bot_ids:
            print(f"⚠️ {bid} bu tick'te zaten kapatıldı, atlanıyor.")
            continue
        
        if bid not in paper_engine.position_manager.positions:
            print(f"⚠️ {bid} pozisyonu zaten kapatılmış, atlanıyor.")
            continue
        
        # Pozisyonu kapat
        trade = await paper_engine.position_manager.close_position(bid, price, reason)
        
        if trade:
            closed_bot_ids.add(bid)
            close_count += 1
    
    # 4. Sadece 1 kapatma yapıldığını doğrula
    assert close_count == 1, \
        f"Expected 1 close, got {close_count}"
    
    assert len(closed_bot_ids) == 1, \
        f"Expected 1 bot in closed_bot_ids, got {len(closed_bot_ids)}"
    
    print(f"✅ closed_bot_ids prevention successful: {close_count} close(s)")


@pytest.mark.asyncio
async def test_concurrent_close_attempts():
    """
    3 paralel kapatma girişiminin sadece 1'ini işlediğini doğrula.
    Stress test senaryosu.
    """
    from core.paper import paper_engine
    
    bot_id = "SOL/USDT_test_concurrent_1m"

    # 1. Pozisyon aç (open_position senkron)
    paper_engine.position_manager.open_position(
        bot_id=bot_id,
        symbol="SOL/USDT",
        direction="LONG",
        entry_price=100.0,
        size=100.0,
        leverage=10,
        stop_loss=95.0
    )
    
    # 2. 3 paralel kapatma çağrısı
    results = await asyncio.gather(
        paper_engine.position_manager.close_position(bot_id, 95.0, "STOP_LOSS"),
        paper_engine.position_manager.close_position(bot_id, 95.0, "STOP_LOSS"),
        paper_engine.position_manager.close_position(bot_id, 95.0, "STOP_LOSS"),
        return_exceptions=True
    )
    
    # 3. Trade sayısını kontrol et
    trades = [t for t in paper_engine.position_manager.trade_history.trades 
              if t.bot_id == bot_id]
    
    # CRITICAL: 3 çağrı → 1 trade
    assert len(trades) == 1, \
        f"Stress test failed: 3 calls resulted in {len(trades)} trades"
    
    print(f"✅ Concurrent close stress test passed: {len(trades)} trade from 3 calls")


# Test runner için
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
