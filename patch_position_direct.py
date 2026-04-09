with open("core/trading/entities/position.py", "r") as f:
    content = f.read()

# Replace should_take_partial_profit manually using python logic instead of complex regex
start_idx = content.find("def should_take_partial_profit")
if start_idx != -1:
    end_idx = content.find("def should_activate_breakeven", start_idx)
    if end_idx != -1:
        replacement = """def get_triggered_tp_levels(self, current_price: float) -> list:
        \"\"\"
        Aşama 1: R-Multiple tabanlı kademeli çıkış.
        \"\"\"
        if not self.initial_stop_loss:
            return []

        risk_distance = abs(self.entry_price - self.initial_stop_loss)
        if risk_distance <= 0:
            return []

        if self.direction == PositionDirection.LONG:
            profit_distance = current_price - self.entry_price
        else:  # SHORT
            profit_distance = self.entry_price - current_price

        current_r = profit_distance / risk_distance

        triggered = []
        for level_info in self.take_profit_levels:
            if not level_info.get("hit", False) and current_r >= level_info.get("level", float('inf')):
                triggered.append(level_info)

        return triggered

    """
        content = content[:start_idx] + replacement + content[end_idx:]

with open("core/trading/entities/position.py", "w") as f:
    f.write(content)
