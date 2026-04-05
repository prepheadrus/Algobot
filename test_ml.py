import asyncio
from api.schemas.ml import MLTrainRequest
from pydantic import ValidationError

try:
    req = MLTrainRequest(symbol="BTC/USDT", timeframe="1h", limit=5000, tp=1.5, sl=1.5, time_horizon=12)
    print(f"Request: {req.model_dump()}")
except ValidationError as e:
    print(f"Validation Error: {e}")
