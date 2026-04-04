from strategy.builder.executor import StrategyExecutor

# Test init with dict
strategy_dict = {
    "name": "Test Strategy",
    "indicators": [],
    "conditions": {
        "LONG": {"logic": "AND", "conditions": []},
        "SHORT": {"logic": "AND", "conditions": []}
    }
}
executor = StrategyExecutor(strategy_dict=strategy_dict)
print("Executor loaded from dict successfully, name:", executor.config.name)
