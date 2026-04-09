import re

with open("core/trading/position_manager.py", "r") as f:
    content = f.read()

# Make sure Stage 3 doesn't overwrite breakeven_price aggressively if trailing_stop happens to be higher but we want to test specifically breakeven armor activation
# But looking closer: The `current_high` passed to update_trailing_stop_with_protection is `3201.9`.
# trailing_stop = current_price - (atr * atr_multiplier).
# atr=0, multiplier=2 -> trailing_stop = 3201.9
# It returns max(trailing_stop, min_stop, current_stop). max(3201.9, 3002.7, 3002.7) = 3201.9!
# The trailing stop worked correctly and pushed the stop loss higher than the breakeven armor!
# The test expects exactly the breakeven armor.
# So we need to fix the test, not the code, to provide a 0 current_high update *or* test if stop loss is *at least* expected_breakeven
