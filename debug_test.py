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
    print(f"entry: {pos.entry_price}, current: 3200.0, initial_stop_loss: {pos.initial_stop_loss}")
    levels = pos.get_triggered_tp_levels(3200.0)
    print(f"triggered_levels: {levels}")

asyncio.run(debug())
