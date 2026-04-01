from dataclasses import dataclass


@dataclass(kw_only=True, slots=True, frozen=True)
class TradingMetrics:
    win_rate: float
    profit_factor: float
    total_trades: int
    total_pnl: float
    max_drawdown_pct: float
    max_drawdown: float
