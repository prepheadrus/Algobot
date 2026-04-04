import asyncio
from api.strategy_builder_api import test_strategy, StrategySchema
import pandas as pd
from unittest.mock import patch

strategy = StrategySchema(
    name="Test API",
    indicators=[{"name": "RSI", "length": 14, "type": "RSI", "id": "RSI_14"}],
    conditions={
        "LONG": {
            "logic": "AND",
            "conditions": [
                {"indicator": "RSI_14", "operator": "<", "value": 30}
            ]
        },
        "SHORT": {
            "logic": "AND",
            "conditions": [
                {"indicator": "RSI_14", "operator": ">", "value": 70}
            ]
        }
    }
)

async def mock_fetch_real_data(symbol, timeframe, days):
    print("MOCK FETCH CALLED")
    import numpy as np
    n_rows = 1000
    close_prices = 50000 + np.cumsum(np.random.randn(n_rows) * 100)
    high_prices = close_prices + np.abs(np.random.randn(n_rows)) * 50
    low_prices = close_prices - np.abs(np.random.randn(n_rows)) * 50
    open_prices = close_prices + np.random.randn(n_rows) * 50
    volumes = np.random.randint(100, 10000, n_rows)
    dates = pd.date_range("2024-01-01", periods=n_rows, freq="15min")
    return pd.DataFrame({
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    }, index=dates)

async def run():
    with patch('api.strategy_builder_api.fetch_real_data', side_effect=mock_fetch_real_data):
        try:
            res = await test_strategy(strategy)
            print("Success:", res)
        except Exception as e:
            print("Error:", e)

asyncio.run(run())
