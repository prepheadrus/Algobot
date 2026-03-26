from strategy.manager import StrategyManager

strategies = StrategyManager.get_all_strategies()

for sid, sdata in strategies.items():
    print(f"\n--- {sdata['name']} ({sid}) ---")
    instance = sdata.get('instance')
    if instance:
        print(f"Indicators: {instance.indicators}")
        print(f"Conditions: {instance.get_conditions()}")
    else:
        print("No instance found")
