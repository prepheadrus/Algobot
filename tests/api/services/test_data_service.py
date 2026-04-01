import pytest
from api.services.data_service import DataService

@pytest.mark.parametrize("market_input, symbol, expected", [
    ("future", "BTC/USDT", "future"),
    ("FUTURES", "ETH/USDT", "future"),
    ("perpetual", "BTC/USDT", "future"),
    ("vadeli", "AVAX/USDT", "future"),
    ("spot", "BNB/USDT", "spot"),
    (" sPoT ", "SOL/USDT", "spot"),    # Boşluk ve case-insensitive kontrolü
    ("", "BTC/USDT:USDT", "future"),   # Empty string, symbol format dictates future
    ("   ", "BTC/USDT", "spot"),        # Sadece boşluk, no special symbol, defaults spot
    (None, "BTC/USDT", "spot"),        # None type, default spot
    (None, "BTC/USDT:USDT", "future"), # None type, default future based on symbol
    ("options", "ETH-SWAP", "future"), # Tanımlanmayan/Bilinmeyen tip, default future based on symbol
    ("random", "BTC/USDT", "spot"),    # Tanımlanmayan tip, default spot
    ("swap", "ETH/USDT", "future"),    # 'swap' is in MARKET_TYPE_KEYWORDS
    ("perp", "ADA/USDT", "future"),    # 'perp' is in MARKET_TYPE_KEYWORDS
])
def test_normalize_market_type(market_input, symbol, expected):
    # DataService sınıfının gerektirdiği bağımlılıkları (mock) ekleyerek sınıfı başlat
    service = DataService()
    assert service._normalize_market_type(market_input, symbol) == expected
