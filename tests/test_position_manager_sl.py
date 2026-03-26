import pytest
from core.trading.position_manager import PositionManager
from core.trading.entities.position import Position, PositionDirection
from datetime import datetime

def test_sl_breakeven_logic():
    pm = PositionManager()

    # 1. Test LONG Break-even
    pos_long = {
        'bot_id': 'bot1',
        'symbol': 'BTC/USDT',
        'direction': 'LONG',
        'entry_price': 100.0,
        'current_price': 100.0,
        'size': 1.0,
        'leverage': 1.0,
        'stop_loss': 90.0,
        'take_profit': 120.0,
        'atr': 2.0, # min_profit_distance = 2.0
        'atr_multiplier': 1.5,
        'highest_seen': 100.0,
        'lowest_seen': 100.0
    }

    # trailing stop runs and moves it to 101 - (2*1.5) = 98.0
    pm.update_trailing_stop_legacy(pos_long, 101.0, 101.0, 101.0)
    assert pos_long['stop_loss'] == 98.0

    # Enough profit (102.5 >= 100 + 2), should move to breakeven + buffer
    pm.update_trailing_stop_legacy(pos_long, 102.5, 102.5, 102.5)
    assert pos_long['stop_loss'] == 100.0 * 1.001

    # 2. Test SHORT Break-even
    pos_short = {
        'bot_id': 'bot2',
        'symbol': 'ETH/USDT',
        'direction': 'SHORT',
        'entry_price': 200.0,
        'current_price': 200.0,
        'size': 1.0,
        'leverage': 1.0,
        'stop_loss': 210.0,
        'take_profit': 180.0,
        'atr': 5.0, # min_profit_distance = 5.0
        'atr_multiplier': 1.5,
        'highest_seen': 200.0,
        'lowest_seen': 200.0
    }

    # trailing stop runs and moves it to 196 + (5*1.5) = 203.5
    pm.update_trailing_stop_legacy(pos_short, 196.0, 196.0, 196.0)
    assert pos_short['stop_loss'] == 203.5

    # Enough profit (194 <= 200 - 5), should move to breakeven - buffer
    pm.update_trailing_stop_legacy(pos_short, 194.0, 194.0, 194.0)
    assert pos_short['stop_loss'] == 200.0 * 0.999

if __name__ == "__main__":
    test_sl_breakeven_logic()
    print("Tests passed.")
