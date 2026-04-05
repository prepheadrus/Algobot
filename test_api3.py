from api.schemas.ml import MLTrainRequest

req = MLTrainRequest(
        symbol="BTC/USDT",
        timeframe="1h",
        limit=100,
        tp=1.5,
        sl=1.5,
        time_horizon=12,
        n_estimators=800,
        max_depth=6,
        learning_rate=0.01
)
print("Pydantic objesi yaratıldı:", req.model_dump())
