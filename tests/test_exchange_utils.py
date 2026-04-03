import pytest
from core.exchange import normalize_symbol, normalize_symbol_for_exchange

@pytest.mark.parametrize("input_symbol, expected_output", [
    ('', 'BTC/USDT'),
    ('BTC/USDT', 'BTC/USDT'),
    ('BTC_USDT', 'BTC/USDT'),
    ('BTC-USDT', 'BTC/USDT'),
    ('BTCUSDT', 'BTC/USDT'),
    ('/BTC', 'BTC/USDT'),
    ('//BTC', 'BTC/USDT'),
    ('__BTC', 'BTC/USDT'),
    ('_ETH', 'ETH/USDT'),
    ('BTC-USDT-PERP', 'BTC/USDT:USDT'),
    ('BTC_USDT_USDT', 'BTC/USDT:USDT'),
    ('BTC/USDT/PERP', 'BTC/USDT:USDT'),
    ('PERP/PERP', 'PERP/USDT:USDT'),
    ('PERP', 'PERP/USDT'),
    ('ETHBTC', 'ETH/BTC'),
    ('SOLUSD', 'SOL/USD'),
    ('BTC/USDT:USDT', 'BTC/USDT:USDT'),
    ('BTC/USDT:BTC', 'BTC/USDT'),
    ('ADA', 'ADA/USDT'),
    ('AVAX', 'AVAX/USDT'),
    ('XRPUSDT', 'XRP/USDT'),
    ('LTCUSD', 'LTC/USD'),
    ('DOTBTC', 'DOT/BTC'),
    ('  BTC/USDT   ', 'BTC/USDT'),
    ('ABCD', 'ABCD/USDT'),
    ('XRP/USD', 'XRP/USD'),
])
def test_normalize_symbol(input_symbol, expected_output):
    """
    Tests the normalize_symbol function with various inputs including happy paths and edge cases.
    """
    assert normalize_symbol(input_symbol) == expected_output

@pytest.mark.parametrize("input_symbol, market_type, expected_output", [
    ('BTC/USDT', 'spot', 'BTC/USDT'),
    ('BTC/USDT', 'future', 'BTC/USDT:USDT'),
    ('BTC/USDT', 'swap', 'BTC/USDT:USDT'),
    ('BTC/USDT', 'perp', 'BTC/USDT:USDT'),
    ('BTC/USDT:USDT', 'future', 'BTC/USDT:USDT'),
    ('ETH/USDT', 'futures', 'ETH/USDT:USDT'),
])
def test_normalize_symbol_for_exchange(input_symbol, market_type, expected_output):
    """
    Tests the normalize_symbol_for_exchange function for spot and futures markets.
    """
    assert normalize_symbol_for_exchange(input_symbol, market_type) == expected_output
