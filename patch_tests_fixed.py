with open("tests/test_position_manager.py", "r") as f:
    content = f.read()

# I am replacing the hardcoded `current_high = 3200.0` with the actual dynamically calculated 2R target using exactly 2.01 * r_distance logic inside the test function correctly this time
start_marker = "        # Fast forward price to 2R (3000 + 200 = 3200)"
end_marker = "        current_low = 3190.0"

idx = content.find(start_marker)
if idx != -1:
    idx2 = content.find(end_marker, idx) + len(end_marker)

    replacement = """        execution_price = pm.positions["bot_rmultiple_test"].entry_price
        r_distance = execution_price - 2900.0
        current_high = execution_price + (2.01 * r_distance)
        current_low = execution_price + (1.99 * r_distance)"""

    content = content[:idx] + replacement + content[idx2:]

with open("tests/test_position_manager.py", "w") as f:
    f.write(content)
