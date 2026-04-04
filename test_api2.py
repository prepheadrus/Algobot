import asyncio
from api.strategy_builder_api import test_strategy, StrategySchema

strategy = StrategySchema(
    name="Test API",
    indicators=[{"name": "RSI", "period": 14}],
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

async def run():
    try:
        res = await test_strategy(strategy)
        print("Success:", res)
    except Exception as e:
        print("Error:", e)

asyncio.run(run())
