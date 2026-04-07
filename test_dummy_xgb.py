import sys
from unittest.mock import MagicMock
import numpy as np

# xgboost mock'la, test ortamında tam olarak hata vermeden mantığı sına
sys.modules['xgboost'] = MagicMock()
sys.modules['joblib'] = MagicMock()
sys.modules['pandas'] = __import__('pandas')

from ml.inference import get_ml_prediction

# Dummy indicator dict
indicators = {'open': 100, 'high': 105, 'low': 95, 'close': 102, 'volume': 1000}

# test get_ml_prediction with mock (we only care if it throws an unhandled exception)
try:
    # get_ml_prediction requires load_model which accesses file system
    # We will just verify it doesn't crash catastrophically before the mock kicks in
    res = get_ml_prediction("BTC/USDT", "1m", "long", indicators)
    print("Test passed without crash:", res)
except Exception as e:
    print("Test failed with exception:", e)
