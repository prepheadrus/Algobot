import dataclasses
from core.trading.position_manager import PositionManager

with open("tests/test_position_manager.py", "r") as f:
    content = f.read()

# Fix entry price assertion issue for R-Multiple (entry price * 1.0001 slipaj in position manager logic)
# We should use actual entry price to advance the price to 2R
content = content.replace(
    "        # Fast forward price to 2R (3000 + 200 = 3200)\n        current_high = 3200.0\n        current_low = 3190.0",
    "        execution_price = pm.positions[\"bot_rmultiple_test\"].entry_price\n        r_distance = execution_price - 2900.0\n        current_high = execution_price + (2.01 * r_distance)\n        current_low = execution_price + (1.99 * r_distance)"
)

with open("tests/test_position_manager.py", "w") as f:
    f.write(content)
