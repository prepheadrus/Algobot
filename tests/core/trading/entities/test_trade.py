import pytest
import sys
from unittest.mock import MagicMock
from datetime import datetime, timedelta, timezone

from core.trading.entities.trade import Trade
from core.trading.entities.position import PositionDirection

@pytest.mark.parametrize("minutes_delta, expected_day, expected_swing", [
    (14.9, False, False),       # Scalp (15 dk altı)
    (15.0, True, False),        # Day Trade alt sınır
    (1439.9, True, False),      # Day Trade üst sınır (23.99 saat)
    (1440.0, False, True),      # Swing Trade alt sınır (Tam 1 gün)
    (10079.9, False, True),     # Swing Trade üst sınır
    (10080.0, False, False),    # Position Trade (Tam 7 gün ve üstü)
    (0.0, False, False),        # Instant trade
    (60.0, True, False),        # 1 hour
    (720.0, True, False),       # 12 hours
    (2880.0, False, True),      # 2 days
])
def test_trade_duration_categories(minutes_delta, expected_day, expected_swing):
    entry = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    exit_time = entry + timedelta(minutes=minutes_delta)

    trade = Trade(
        id="test_trade",
        bot_id="test_bot",
        symbol="BTC/USDT",
        direction=PositionDirection.LONG,
        entry_price=50000.0,
        exit_price=51000.0,
        size=1.0,
        leverage=1.0,
        pnl=1000.0,
        pnl_percent=2.0,
        opened_at=entry,
        closed_at=exit_time
    )

    assert trade.is_day_trade == expected_day
    assert trade.is_swing_trade == expected_swing
