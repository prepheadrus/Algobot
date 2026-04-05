"""
Test: Real-time UI Sync After Position Close

Amaç: Pozisyon kapandıktan sonra open_positions'un ANINDA güncellendiğini kanıtla.
Sorun: Pozisyon kapandı ama open_positions güncellenmedi → UI'da hala görünüyor.
Çözüm: Her close_position() çağrısından SONRA open_positions = list(legacy_positions).
"""

import pytest


@pytest.mark.asyncio
async def test_open_positions_sync_immediately_after_close():
    """
    Pozisyon kapandıktan sonra open_positions ANINDA güncellenmeli.
    """
    from core.paper import paper_engine
    
    bot_id = "BTC/USDT_test_ui_sync_1m"

    # 1. Pozisyon aç (open_position senkron)
    paper_engine.position_manager.open_position(
        bot_id=bot_id,
        symbol="BTC/USDT",
        direction="LONG",
        entry_price=50000.0,
        size=1.0,
        leverage=10,
        stop_loss=49000.0
    )

    # 2. Pozisyon açıldığını doğrula
    assert len(paper_engine.open_positions) == 1, \
        "Position not in open_positions after open"

    # 3. Pozisyonu kapat (async)
    trade = await paper_engine.position_manager.close_position(
        bot_id, 49000.0, "STOP_LOSS"
    )
    
    # 4. close_position başarılı olmalı
    assert trade is not None, "Close position failed"
    
    # 5. open_positions'un ANINDA güncellendiğini doğrula (KRİTİK!)
    assert len(paper_engine.open_positions) == 0, \
        f"UI sync FAILED! Expected 0 positions, got {len(paper_engine.open_positions)}"
    
    print(f"✅ UI sync successful: {len(paper_engine.open_positions)} positions after close")


@pytest.mark.asyncio
async def test_open_positions_updated_in_update_live_prices():
    """
    update_live_prices içinde positions_updated flag çalışıyor.
    """
    from core.paper import paper_engine
    
    bot_id = "ETH/USDT_test_positions_updated_1m"

    # 1. Pozisyon aç (open_position senkron)
    paper_engine.position_manager.open_position(
        bot_id=bot_id,
        symbol="ETH/USDT",
        direction="LONG",
        entry_price=3000.0,
        size=10.0,
        leverage=10
    )

    # 2. update_live_prices çağır (fiyat güncellemesi)
    await paper_engine.update_live_prices(
        symbol="ETH/USDT",
        current_price=3050.0,
        current_high=3060.0,
        current_low=3040.0
    )
    
    # 3. open_positions senkronize edildi mi?
    assert len(paper_engine.open_positions) > 0, \
        "open_positions not synced in update_live_prices"
    
    # 4. current_price güncellendi mi?
    pos = paper_engine.open_positions[0]
    assert pos['current_price'] == 3050.0, \
        f"current_price not updated: {pos['current_price']}"
    
    print(f"✅ update_live_prices sync successful: price={pos['current_price']}")


@pytest.mark.asyncio
async def test_multiple_positions_sync_after_close():
    """
    Birden fazla pozisyon kapatıldığında open_positions doğru senkronize.
    """
    from core.paper import paper_engine
    
    # 1. 3 pozisyon aç (open_position senkron)
    bot_ids = ["BTC/USDT_test_multi_1m", "ETH/USDT_test_multi_1m", "SOL/USDT_test_multi_1m"]

    for i, bot_id in enumerate(bot_ids):
        paper_engine.position_manager.open_position(
            bot_id=bot_id,
            symbol=bot_id.split('/')[0],
            direction="LONG",
            entry_price=100.0 * (i + 1),
            size=10.0,
            leverage=10
        )

    # 2. 3 pozisyon açık olmalı
    assert len(paper_engine.open_positions) == 3, \
        f"Expected 3 positions, got {len(paper_engine.open_positions)}"

    # 3. 1 pozisyonu kapat (async)
    await paper_engine.position_manager.close_position(
        bot_ids[0], 95.0, "STOP_LOSS"
    )
    
    # 4. open_positions 2 olmalı (ANINDA!)
    assert len(paper_engine.open_positions) == 2, \
        f"Multi-position sync failed: Expected 2, got {len(paper_engine.open_positions)}"
    
    # 5. Kalan pozisyonlar doğru mu?
    remaining_ids = [p.get('bot_id') for p in paper_engine.open_positions]
    assert bot_ids[0] not in remaining_ids, \
        "Closed position still in open_positions"
    
    print(f"✅ Multiple positions sync successful: {len(paper_engine.open_positions)} remaining")


@pytest.mark.asyncio
async def test_ui_polling_gets_fresh_data():
    """
    UI polling (3 saniyede bir) güncel veriyi alıyor.
    """
    from core.paper import paper_engine
    
    bot_id = "BNB/USDT_test_polling_1m"

    # 1. Pozisyon aç (open_position senkron)
    paper_engine.position_manager.open_position(
        bot_id=bot_id,
        symbol="BNB/USDT",
        direction="LONG",
        entry_price=600.0,
        size=10.0,
        leverage=10
    )

    # 2. get_stats() çağır (dashboard_metrics kullanıyor)
    stats = paper_engine.get_stats()

    # 3. Pozisyon stats'ta görünmeli
    assert stats.get('open_positions', 0) == 1, \
        "Position not in stats"

    # 4. Pozisyonu kapat (async)
    await paper_engine.position_manager.close_position(
        bot_id, 590.0, "STOP_LOSS"
    )
    
    # 5. Tekrar stats al
    stats = paper_engine.get_stats()
    
    # 6. Pozisyon stats'tan kaybolmalı (ANINDA!)
    assert stats.get('open_positions', 0) == 0, \
        f"Stats not updated after close: {stats.get('open_positions')}"
    
    print("✅ UI polling fresh data test successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
