import pytest
from datetime import datetime
from core.trading.entities.trade import Trade
from core.trading.entities.position import PositionDirection

def test_trade_return_on_margin_normal():
    """Normal durumda return_on_margin hesaplamasını test et."""
    trade = Trade(
        id="trade_1",
        bot_id="bot_1",
        symbol="BTC/USDT",
        direction=PositionDirection.LONG,
        entry_price=50000.0,
        exit_price=51000.0,
        size=0.1,
        leverage=10.0,
        pnl=100.0,
        pnl_percent=0.02,
        opened_at=datetime.utcnow(),
        closed_at=datetime.utcnow()
    )

    # margin = (50000 * 0.1) / 10 = 500
    # return_on_margin = 100 / 500 = 0.2
    assert trade.return_on_margin == 0.2
    assert trade.return_on_margin_percent == 20.0

def test_trade_return_on_margin_zero_margin():
    """Margin sıfır olduğunda return_on_margin'in 0 döndürdüğünü doğrula."""
    trade = Trade(
        id="trade_2",
        bot_id="bot_1",
        symbol="BTC/USDT",
        direction=PositionDirection.LONG,
        entry_price=50000.0,
        exit_price=51000.0,
        size=0.1,
        leverage=10.0,
        pnl=100.0,
        pnl_percent=0.02,
        opened_at=datetime.utcnow(),
        closed_at=datetime.utcnow()
    )

    # Frozen dataclass olduğu için object.__setattr__ kullanıyoruz
    object.__setattr__(trade, 'entry_price', 0.0)

    # Artık margin = (0 * 0.1) / 10 = 0
    # return_on_margin property'si margin <= 0 kontrolü sayesinde 0.0 dönmeli
    assert trade.return_on_margin == 0.0
    assert trade.return_on_margin_percent == 0.0

def test_trade_return_on_margin_negative_margin():
    """Margin negatif olduğunda return_on_margin'in 0 döndürdüğünü doğrula."""
    trade = Trade(
        id="trade_3",
        bot_id="bot_1",
        symbol="BTC/USDT",
        direction=PositionDirection.LONG,
        entry_price=50000.0,
        exit_price=51000.0,
        size=0.1,
        leverage=10.0,
        pnl=100.0,
        pnl_percent=0.02,
        opened_at=datetime.utcnow(),
        closed_at=datetime.utcnow()
    )

    # object.__setattr__ ile negatif değer zorla
    object.__setattr__(trade, 'size', -0.1)

    # Artık margin = (50000 * -0.1) / 10 = -500
    assert trade.return_on_margin == 0.0
    assert trade.return_on_margin_percent == 0.0

def test_trade_initialization_validation():
    """Geçersiz değerlerle Trade oluşturulmasının engellendiğini doğrula."""
    with pytest.raises(ValueError, match="entry_price pozitif olmalı"):
        Trade(
            id="t1", bot_id="b1", symbol="S1", direction=PositionDirection.LONG,
            entry_price=0, exit_price=100, size=1, leverage=1,
            pnl=0, pnl_percent=0, opened_at=datetime.utcnow(), closed_at=datetime.utcnow()
        )

    with pytest.raises(ValueError, match="size pozitif olmalı"):
        Trade(
            id="t1", bot_id="b1", symbol="S1", direction=PositionDirection.LONG,
            entry_price=100, exit_price=100, size=0, leverage=1,
            pnl=0, pnl_percent=0, opened_at=datetime.utcnow(), closed_at=datetime.utcnow()
        )

    with pytest.raises(ValueError, match="leverage en az 1x olmalı"):
        Trade(
            id="t1", bot_id="b1", symbol="S1", direction=PositionDirection.LONG,
            entry_price=100, exit_price=100, size=1, leverage=0.5,
            pnl=0, pnl_percent=0, opened_at=datetime.utcnow(), closed_at=datetime.utcnow()
        )
