import pytest
from datetime import datetime, timezone
from core.trading.entities.trade import Trade
from core.trading.entities.position import PositionDirection


@pytest.mark.parametrize(
    "commission, entry_price, size, exp_total, exp_pct",
    [
        (10.0, 100.0, 10.0, 10.0, 1.0),  # Normal Long Pozisyon (Değer: 1000)
        (
            10.0,
            100.0,
            -10.0,
            10.0,
            1.0,
        ),  # Normal Short Pozisyon (Negatif Size, Bug-Fix Testi)
        (0.0, 100.0, 10.0, 0.0, 0.0),  # Sıfır Komisyon
        (5.0, 0.0, 10.0, 5.0, 0.0),  # Sıfıra Bölme Koruması (Entry Price = 0)
        (5.0, 100.0, 0.0, 5.0, 0.0),  # Sıfıra Bölme Koruması (Size = 0)
        (0.3, 100.0, 1.0, 0.3, 0.3),  # Float Hassasiyeti (Precision) Testi
    ],
)
def test_trade_commissions(commission, entry_price, size, exp_total, exp_pct):
    # Dummy values for passing the initial post_init validation checks.
    # We will use object.__setattr__ to bypass dataclass validations (frozen=True) for edge case testing.
    valid_entry_price = entry_price if entry_price > 0 else 100.0
    valid_size = abs(size) if size != 0 else 10.0

    trade = Trade(
        id="test_trade",
        bot_id="test_bot",
        symbol="BTC/USDT",
        direction=PositionDirection.LONG,
        entry_price=valid_entry_price,
        exit_price=105.0,
        size=valid_size,
        leverage=1.0,
        pnl=0.0,
        pnl_percent=0.0,
        opened_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        closed_at=datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc),
        commission=commission,
    )

    # Bypass dataclass freezing / property checks to set edge case values that
    # are otherwise blocked by __post_init__ validation rules.
    if entry_price <= 0:
        object.__setattr__(trade, "entry_price", entry_price)
    if size <= 0:
        object.__setattr__(trade, "size", size)

    assert trade.total_commission == pytest.approx(exp_total)
    assert trade.commission_percent == pytest.approx(exp_pct)
