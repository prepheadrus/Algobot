from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

response = client.post(
    "/api/v1/ml/train",
    json={
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "limit": 100,
        "tp": 1.5,
        "sl": 1.5,
        "time_horizon": 12,
        "n_estimators": 800,
        "max_depth": 6,
        "learning_rate": 0.01
    }
)
print(response.status_code)
print(response.json())
