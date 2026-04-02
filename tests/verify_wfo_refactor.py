import asyncio
from unittest.mock import MagicMock, patch
from core.wfo_engine import WFOEngine, OptimizationConfig
import pandas as pd
import numpy as np

class MockStrategy:
    DEFAULT_PARAMS = {'param1': 10}
    def __init__(self):
        self.params = self.DEFAULT_PARAMS.copy()
    def update_params(self, params):
        self.params.update(params)
    def generate_signals(self, data):
        return pd.Series(0, index=data.index)

async def test_wfo_refactor_verification():
    engine = WFOEngine()

    # Mock data
    dates = pd.date_range('2024-01-01', periods=200, freq='1h')
    mock_data = pd.DataFrame({
        'open': np.random.rand(200),
        'high': np.random.rand(200),
        'low': np.random.rand(200),
        'close': np.random.rand(200),
        'volume': np.random.rand(200)
    }, index=dates)

    config = OptimizationConfig(
        symbol='BTC/USDT',
        timeframe='1h',
        strategy_class=MockStrategy,
        in_sample_days=5,
        out_of_sample_days=1,
        n_trials=2
    )

    with patch.object(engine, '_fetch_data', return_value=mock_data):
        with patch('core.auto_grid.auto_grid.generate_from_strategy', return_value={'param1': [5, 10, 15]}):
             result = await engine.optimize(config)

             assert result != {}
             assert 'best_params' in result
             assert 'best_value' in result
             print("✅ WFOEngine.optimize verification successful!")

if __name__ == "__main__":
    asyncio.run(test_wfo_refactor_verification())
