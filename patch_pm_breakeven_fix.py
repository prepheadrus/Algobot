import re

with open("core/trading/position_manager.py", "r") as f:
    content = f.read()

# Update breakeven_price calculation to include commission armor correctly in Phase 1
content = content.replace(
    "breakeven_price = position.entry_price",
    "breakeven_price = position.entry_price * (1 + 0.0008) if position.direction.value == 'LONG' else position.entry_price * (1 - 0.0008)"
)

# And also ensure that if breakeven is activated but we somehow fall through to trailing stop, trailing stop doesnt overwrite our exact break even value immediately due to max() incorrectly handling it.
# Actually AŞAMA 3 currently uses: new_stop = max(trailing_stop, min_stop, current_stop)
# In Aşama 1, current_stop becomes breakeven_price.

with open("core/trading/position_manager.py", "w") as f:
    f.write(content)
