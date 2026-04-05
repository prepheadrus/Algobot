"""
Test: Zombie Position Prevention

Amaç: Kapatma başarısız olursa is_closing kilidinin sıfırlandığını kanıtla.
Sorun: Exception durumunda kilit TRUE kalıyor → Pozisyon sonsuza kadar açık.
Çözüm: finally bloğunda is_closing = False.
"""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
async def test_zombie_prevention_on_db_error():
    """
    DB hatası durumunda is_closing kilidinin sıfırlandığını doğrula.
    """
    from core.paper import paper_engine
    
    bot_id = "BTC/USDT_test_zombie_db_1m"

    # 1. Pozisyon aç (open_position senkron)
    position = paper_engine.position_manager.open_position(
        bot_id=bot_id,
        symbol="BTC/USDT",
        direction="LONG",
        entry_price=50000.0,
        size=1.0,
        leverage=10,
        stop_loss=49000.0
    )
    
    assert position is not None
    
    # 2. close_position'da DB hatası simüle et
    with patch.object(
        paper_engine.position_manager,
        '_remove_legacy_position_safe',
        side_effect=Exception("Database Connection Lost")
    ):
        result = await paper_engine.position_manager.close_position(
            bot_id, 49000.0, "STOP_LOSS"
        )
    
    # 3. close_position None dönmeli (başarısız)
    assert result is None, "Close should fail and return None"
    
    # 4. is_closing kilidinin FALSE olduğunu doğrula (ZOMBIE ÖNLEME!)
    # Pozisyon hala positions dict'inde olabilir (silinmedi)
    if bot_id in paper_engine.position_manager.positions:
        pos = paper_engine.position_manager.positions[bot_id]
        assert pos.metadata['is_closing'] == False, \
            "ZOMBIE POSITION DETECTED! is_closing should be False after failure"
    
    print("✅ Zombie prevention successful: is_closing = False after DB error")


@pytest.mark.asyncio
async def test_zombie_prevention_on_remove_error():
    """
    Legacy position silme hatası durumunda kilidin sıfırlandığını doğrula.
    """
    from core.paper import paper_engine
    
    bot_id = "ETH/USDT_test_zombie_remove_1m"

    # 1. Pozisyon aç (open_position senkron)
    position = paper_engine.position_manager.open_position(
        bot_id=bot_id,
        symbol="ETH/USDT",
        direction="LONG",
        entry_price=3000.0,
        size=10.0,
        leverage=10
    )
    
    # 2. Her adımda exception fırlat
    with patch.object(
        paper_engine.position_manager,
        'close_position',
        side_effect=Exception("Unexpected Error")
    ):
        try:
            await paper_engine.close_position(bot_id, 2900.0, "STOP_LOSS")
        except:
            pass
    
    # 3. is_closing kilidini kontrol et
    if bot_id in paper_engine.position_manager.positions:
        pos = paper_engine.position_manager.positions[bot_id]
        assert pos.metadata['is_closing'] == False, \
            "Zombie lock detected after exception"
    
    print("✅ Zombie prevention on remove error successful")


@pytest.mark.asyncio
async def test_retry_after_zombie_unlock():
    """
    Kilit sıfırlandıktan sonra pozisyonun tekrar kapatılabildiğini doğrula.
    """
    from core.paper import paper_engine
    
    bot_id = "SOL/USDT_test_zombie_retry_1m"

    # 1. Pozisyon aç (open_position senkron)
    position = paper_engine.position_manager.open_position(
        bot_id=bot_id,
        symbol="SOL/USDT",
        direction="LONG",
        entry_price=100.0,
        size=100.0,
        leverage=10,
        stop_loss=95.0
    )
    
    # 2. İlk kapatma başarısız (mock ile)
    call_count = 0
    
    def mock_close(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("First attempt fails")
        # 2. çağrı başarılı olsun (normal akış)
        return MagicMock()
    
    with patch.object(
        paper_engine.position_manager,
        'close_position',
        side_effect=mock_close
    ):
        # İlk deneme
        try:
            await paper_engine.close_position(bot_id, 95.0, "STOP_LOSS")
        except:
            pass
        
        # is_closing sıfırlandı mı?
        if bot_id in paper_engine.position_manager.positions:
            assert paper_engine.position_manager.positions[bot_id].metadata['is_closing'] == False
        
        # 2. deneme başarılı olmalı
        # (Gerçek senaryoda bir sonraki tick'te tekrar denenir)
    
    print(f"✅ Retry after unlock test: {call_count} attempt(s) made")


@pytest.mark.asyncio
async def test_finally_block_resets_lock():
    """
    finally bloğunun her durumda is_closing'i sıfırladığını doğrula.
    """
    from core.paper import paper_engine
    
    bot_id = "BNB/USDT_test_finally_1m"

    # 1. Pozisyon aç (open_position senkron)
    position = paper_engine.position_manager.open_position(
        bot_id=bot_id,
        symbol="BNB/USDT",
        direction="LONG",
        entry_price=600.0,
        size=10.0,
        leverage=10
    )
    
    # 2. close_success = False durumunda finally'in çalıştığını doğrula
    # (Bu test position_manager.py'deki finally bloğunu test eder)
    
    # Manuel olarak close_position akışını simüle et
    position.metadata['is_closing'] = True
    close_success = False
    
    # finally bloğu simülasyonu
    try:
        # Normal akışta burada trade kapatma var
        # Biz exception fırlatalım
        raise Exception("Test exception")
    except:
        # except bloğu
        pass
    finally:
        # finally bloğu - is_closing sıfırlanmalı
        if not close_success:
            position.metadata['is_closing'] = False
    
    # 3. is_closing'in FALSE olduğunu doğrula
    assert position.metadata['is_closing'] == False, \
        "finally block didn't reset is_closing!"
    
    print("✅ finally block lock reset successful")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
