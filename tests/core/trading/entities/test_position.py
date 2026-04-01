import pytest
from datetime import datetime, timezone
from core.trading.entities.position import Position, PositionDirection

@pytest.mark.parametrize("direction, stop_loss, current_price, expected", [
    (PositionDirection.LONG, 100.0, 105.0, False),  # Fiyat güvende
    (PositionDirection.LONG, 100.0, 100.0, True),   # Tam sınırda (Edge)
    (PositionDirection.LONG, 100.0, 95.0, True),    # SL kırılmış
    (PositionDirection.SHORT, 100.0, 95.0, False),  # Fiyat güvende
    (PositionDirection.SHORT, 100.0, 100.0, True),  # Tam sınırda (Edge)
    (PositionDirection.SHORT, 100.0, 105.0, True),  # SL kırılmış
    (PositionDirection.LONG, None, 90.0, False),    # SL belirlenmemiş
    (PositionDirection.SHORT, None, 110.0, False),  # SL belirlenmemiş
])
def test_is_stop_loss_hit(direction, stop_loss, current_price, expected):
    """
    is_stop_loss_hit metodu için Data-Driven Testler
    """
    position = Position(
        bot_id="test_bot",
        symbol="BTC/USDT",
        direction=direction,
        entry_price=100.0,
        size=1.0,
        leverage=1.0,
        opened_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc), # Deterministik zaman
        stop_loss=stop_loss
    )

    assert position.is_stop_loss_hit(current_price) == expected

@pytest.mark.parametrize("direction, take_profit, current_price, expected", [
    (PositionDirection.LONG, 110.0, 105.0, False),  # Fiyat henüz hedefe ulaşmadı
    (PositionDirection.LONG, 110.0, 110.0, True),   # Tam sınırda (Edge)
    (PositionDirection.LONG, 110.0, 115.0, True),   # TP geçilmiş
    (PositionDirection.SHORT, 90.0, 95.0, False),   # Fiyat henüz hedefe ulaşmadı
    (PositionDirection.SHORT, 90.0, 90.0, True),    # Tam sınırda (Edge)
    (PositionDirection.SHORT, 90.0, 85.0, True),    # TP geçilmiş
    (PositionDirection.LONG, None, 120.0, False),   # TP belirlenmemiş
    (PositionDirection.SHORT, None, 80.0, False),   # TP belirlenmemiş
])
def test_is_take_profit_hit(direction, take_profit, current_price, expected):
    """
    is_take_profit_hit metodu için Data-Driven Testler
    """
    position = Position(
        bot_id="test_bot",
        symbol="BTC/USDT",
        direction=direction,
        entry_price=100.0,
        size=1.0,
        leverage=1.0,
        opened_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc), # Deterministik zaman
        take_profit=take_profit
    )

    assert position.is_take_profit_hit(current_price) == expected
