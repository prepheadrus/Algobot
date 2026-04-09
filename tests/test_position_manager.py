import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from core.trading.position_manager import PositionManager
from core.trading.entities.position import Position, PositionDirection

@pytest.mark.asyncio
async def test_position_partial_close_no_lock_and_precision():
    pm = PositionManager()

    # Generate a dummy position
    position = await pm.open_position(
        bot_id="bot_precision_test",
        symbol="BTC/USDT",
        direction="LONG",
        entry_price=50000.0,
        size=1.234567,
        leverage=5.0,
        stop_loss=49000.0,
        take_profit=52000.0
    )

    # Assert initial stop loss is recorded
    assert position.initial_stop_loss == 49000.0

    # Ensure metadata 'is_closing' is initially False
    assert pm.positions["bot_precision_test"].metadata.get('is_closing', False) is False

    with patch('core.trading.position_manager.event_bus.publish', new_callable=AsyncMock) as mock_publish:
        # Partial close
        await pm.close_position(
            bot_id="bot_precision_test",
            exit_price=51000.0,
            reason="partial_tp_hit",
            size_to_close=0.61728  # Half of 1.234567 with floating dust
        )

        # Verify lock wasn't engaged because it was a partial close
        assert pm.positions["bot_precision_test"].metadata.get('is_closing', False) is False

        # Verify the closed event was published
        assert mock_publish.called

        # Extract payload
        call_args = mock_publish.call_args[0][0]
        payload = call_args.payload

        # Verify size_closed was properly rounded to 4 decimals (0.6173)
        assert payload['size_closed'] == 0.6173

        # Verify remaining size precision
        expected_remaining = round(1.234567 - 0.6173, 4)
        assert round(payload['remaining_size'], 4) == expected_remaining

        # Verify remaining size in the state object
        assert round(pm.positions["bot_precision_test"].size, 4) == expected_remaining

@pytest.mark.asyncio
async def test_dynamic_r_multiple_and_breakeven_armor():
    pm = PositionManager()

    # Generate a dummy position with dynamic R-Multiple targets
    position = await pm.open_position(
        bot_id="bot_rmultiple_test",
        symbol="ETH/USDT",
        direction="LONG",
        entry_price=3000.0,
        size=10.0,
        leverage=5.0,
        stop_loss=2900.0, # 1R = 100
        take_profit=None
    )

    import dataclasses
    # Inject dynamic levels
    pm.positions["bot_rmultiple_test"] = dataclasses.replace(
        pm.positions["bot_rmultiple_test"],
        take_profit_levels=[{"level": 2.0, "percentage": 0.5, "hit": False}]
    )

    execution_price = pm.positions["bot_rmultiple_test"].entry_price
    r_distance = execution_price - 2900.0
    current_high = execution_price + (2.01 * r_distance)
    current_low = execution_price + (1.99 * r_distance)

    with patch('core.trading.position_manager.event_bus.publish', new_callable=AsyncMock) as mock_publish:
        # This will trigger AŞAMA 1 logic
        updated_pos = await pm.update_trailing_stop(
            position=pm.positions["bot_rmultiple_test"],
            current_high=current_high,
            current_low=current_low
        )

        # Verify level state updated synchronously
        assert updated_pos.take_profit_levels[0]["hit"] is True

        # Verify breakeven is active
        assert updated_pos.breakeven_activated is True

        # Let async task run
        await asyncio.sleep(0.1)

        # Verify breakeven armor (entry_price * (1 + 0.0008))
        expected_breakeven = updated_pos.entry_price * (1 + 0.0008)
        assert updated_pos.stop_loss >= expected_breakeven
