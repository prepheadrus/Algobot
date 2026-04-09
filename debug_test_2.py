import asyncio
from core.trading.position_manager import PositionManager

async def debug():
    pm = PositionManager()
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
    pm.positions["bot_rmultiple_test"] = dataclasses.replace(
        pm.positions["bot_rmultiple_test"],
        take_profit_levels=[{"level": 2.0, "percentage": 0.5, "hit": False}]
    )

    pos = pm.positions["bot_rmultiple_test"]

    # Simulate execution_price which includes 1.0001 slipaj
    execution_price = pos.entry_price
    r_distance = execution_price - pos.initial_stop_loss

    print(f"entry_price: {pos.entry_price}")
    print(f"initial_stop_loss: {pos.initial_stop_loss}")
    print(f"risk_distance: {r_distance}")

    # Target exactly 2R + some margin
    current_high = execution_price + (2.01 * r_distance)
    print(f"current_high sent: {current_high}")

    levels = pos.get_triggered_tp_levels(current_high)
    print(f"triggered_levels from get_triggered_tp_levels: {levels}")

    # Emulate the update_trailing_stop wrapper
    print(f"Direction in Wrapper: {pos.direction}")
    current_price = current_high if pos.direction == "LONG" else 0
    print(f"current_price determined: {current_price}")
    levels2 = pos.get_triggered_tp_levels(current_price)
    print(f"triggered_levels inside wrapper logic: {levels2}")

asyncio.run(debug())
