"""
Pytest Configuration & Fixtures

Test bağımlılıkları, mock'lar ve ortak fixture'lar.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Pytest başlangıç ayarları"""
    config.addinivalue_line(
        "markers", "slow: marks test as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks test as integration test"
    )


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_exchange():
    """
    Sahte CCXT exchange mock'u.
    Gerçek borsaya bağlanmadan test yapmamızı sağlar.
    """
    exchange = AsyncMock()
    
    # Sahte bakiye
    exchange.fetch_balance.return_value = {
        'total': {'USDT': 10000, 'BTC': 0.5, 'ETH': 10},
        'free': {'USDT': 9000, 'BTC': 0.5, 'ETH': 10},
        'used': {'USDT': 1000, 'BTC': 0, 'ETH': 0}
    }
    
    # Sahte mum verisi (OHLCV)
    exchange.fetch_ohlcv.return_value = [
        [1672531200000, 50000, 50100, 49900, 50050, 10.5],
        [1672531260000, 50050, 50150, 50000, 50100, 12.3],
        [1672531320000, 50100, 50200, 50050, 50150, 11.1],
    ]
    
    # Sahte ticker
    exchange.fetch_ticker.return_value = {
        'last': 50150,
        'bid': 50140,
        'ask': 50160,
        'volume': 1000000
    }
    
    return exchange


@pytest.fixture
def mock_db_manager():
    """
    Sahte veritabanı yöneticisi mock'u.
    """
    db_manager = AsyncMock()
    
    # DB bağlantısı başarılı
    db_manager.is_connected.return_value = True
    
    # Sahte trade geçmişi
    db_manager.get_trades_by_bot.return_value = []
    
    # Trade kaydetme başarılı
    db_manager.save_trade.return_value = True
    
    return db_manager


@pytest.fixture
def mock_event_bus():
    """
    Sahte event bus mock'u.
    """
    event_bus = AsyncMock()
    
    # Event yayınlama başarılı
    event_bus.publish.return_value = True
    
    # Handler kaydetme
    event_bus.subscribe.return_value = None
    
    return event_bus


@pytest.fixture
def sample_position_data():
    """
    Örnek pozisyon verisi fixture'ı.
    """
    return {
        'bot_id': 'BTC/USDT_test_1m',
        'symbol': 'BTC/USDT',
        'direction': 'LONG',
        'entry_price': 50000.0,
        'size': 1.0,
        'leverage': 10,
        'stop_loss': 49000.0,
        'take_profit': 52000.0,
        'atr': 1000.0,
        'atr_multiplier': 2.0,
        'margin_type': 'isolated'
    }


@pytest.fixture
def sample_trade_data():
    """
    Örnek trade verisi fixture'ı.
    """
    return {
        'symbol': 'BTC/USDT',
        'direction': 'LONG',
        'entry_price': 50000.0,
        'exit_price': 49000.0,
        'size': 1.0,
        'leverage': 10,
        'pnl_usd': -1000.0,
        'pnl_percent': -0.02,
        'reason': 'STOP_LOSS'
    }


@pytest.fixture
def builder():
    """
    Sahte StrategyBuilder fixture'ı.
    """
    from strategy.builder.strategy_builder import StrategyBuilder
    
    # Geçici bir strateji JSON'u oluştur
    import tempfile
    import json
    
    strategy_data = {
        "name": "Test Strategy",
        "description": "Test için",
        "timeframe": "1m",
        "long_conditions": [],
        "short_conditions": [],
        "exit_conditions": []
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(strategy_data, f)
        temp_path = f.name
    
    builder = StrategyBuilder(temp_path)
    return builder


@pytest.fixture
def df():
    """
    Sahte fiyat verileri (pandas DataFrame) fixture'ı.
    """
    import pandas as pd
    import numpy as np
    
    # 100 mumluk sahte veri oluştur
    np.random.seed(42)
    
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1min')
    
    # Rastgele fiyat hareketleri
    close_prices = np.cumsum(np.random.randn(100)) + 100
    open_prices = close_prices + np.random.randn(100) * 0.5
    high_prices = np.maximum(open_prices, close_prices) + np.abs(np.random.randn(100)) * 0.5
    low_prices = np.minimum(open_prices, close_prices) - np.abs(np.random.randn(100)) * 0.5
    volume = np.random.randint(1000, 10000, 100)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': open_prices,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volume
    })
    
    return df


@pytest.fixture
def mock_paper_engine(mock_exchange, mock_db_manager):
    """
    Sahte PaperTrader mock'u.
    """
    from core.paper import PaperTrader
    
    paper_engine = PaperTrader()
    
    # Mock'ları enjekte et
    paper_engine.exchange = mock_exchange
    paper_engine.db_manager = mock_db_manager
    
    return paper_engine


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

@pytest.fixture
def create_test_position():
    """
    Test pozisyonu oluşturan helper fixture.
    """
    async def _create_position(position_manager, **kwargs):
        defaults = {
            'bot_id': 'TEST/BOT_1m',
            'symbol': 'TEST/USDT',
            'direction': 'LONG',
            'entry_price': 100.0,
            'size': 10.0,
            'leverage': 10,
        }
        defaults.update(kwargs)
        
        return await position_manager.open_position(**defaults)
    
    return _create_position


# ============================================================================
# ASYNCIO CONFIGURATION
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """
    asyncio event loop fixture.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
