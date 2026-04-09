with open("tests/test_position_manager.py", "r") as f:
    content = f.read()

# Fix mock publish name
content = content.replace(
    "patch('shared.events.event_bus.publish', new_callable=AsyncMock)",
    "patch('core.trading.position_manager.event_bus.publish', new_callable=AsyncMock)"
)

# Fix frozen dataclass modification
content = content.replace(
    """    # Inject dynamic levels
    pm.positions["bot_rmultiple_test"].take_profit_levels = [
        {"level": 2.0, "percentage": 0.5, "hit": False}
    ]""",
    """    import dataclasses
    # Inject dynamic levels
    pm.positions["bot_rmultiple_test"] = dataclasses.replace(
        pm.positions["bot_rmultiple_test"],
        take_profit_levels=[{"level": 2.0, "percentage": 0.5, "hit": False}]
    )"""
)

with open("tests/test_position_manager.py", "w") as f:
    f.write(content)
