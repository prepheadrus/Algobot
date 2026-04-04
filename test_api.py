import asyncio
from api.strategy_builder_api import test_strategy, StrategySchema

strategy = StrategySchema(
    name="Test API",
    indicators=[],
    conditions={
        "LONG": {"logic": "AND", "conditions": []},
        "SHORT": {"logic": "AND", "conditions": []}
    }
)

async def run():
    try:
        res = await test_strategy(strategy)
        print("Success:", res)
    except Exception as e:
        print("Error:", e)

asyncio.run(run())
