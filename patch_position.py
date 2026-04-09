import re

with open("core/trading/entities/position.py", "r") as f:
    content = f.read()

# Add DEFAULT_COMMISSION_BUFFER
content = re.sub(
    r"class PositionDirection\(str, Enum\):",
    r"DEFAULT_COMMISSION_BUFFER = 0.0008\n\nclass PositionDirection(str, Enum):",
    content
)

# Add initial_stop_loss
content = re.sub(
    r"stop_loss: Optional\[float\] = None",
    r"stop_loss: Optional[float] = None\n    initial_stop_loss: Optional[float] = None",
    content
)

# Update to_dict
content = re.sub(
    r"'stop_loss': self\.stop_loss,",
    r"'stop_loss': self.stop_loss,\n            'initial_stop_loss': self.initial_stop_loss,",
    content
)

# Update from_dict
content = re.sub(
    r"stop_loss=data\.get\('stop_loss'\),",
    r"stop_loss=data.get('stop_loss'),\n            initial_stop_loss=data.get('initial_stop_loss'),",
    content
)

# Remove should_take_partial_profit and replace with get_triggered_tp_levels
should_take_partial_profit_regex = r"    def should_take_partial_profit\(self, current_price: float, atr: float = 0\.0\) -> bool:\s*.*?\"\"\"\s*(?:.*?\n)*?        if self\.direction == PositionDirection\.LONG:\s*profit_distance = current_price - self\.entry_price\s*return profit_distance >= half_tp_distance\s*else:  # SHORT\s*profit_distance = self\.entry_price - current_price\s*return profit_distance >= half_tp_distance"

get_triggered_tp_levels = """    def get_triggered_tp_levels(self, current_price: float) -> list:
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

        return triggered"""

content = re.sub(should_take_partial_profit_regex, get_triggered_tp_levels, content, flags=re.MULTILINE)

# Update activate_breakeven buffer
content = re.sub(
    r"def activate_breakeven\(self, commission_buffer: float = 0\.001\) -> 'Position':",
    r"def activate_breakeven(self, commission_buffer: float = DEFAULT_COMMISSION_BUFFER) -> 'Position':",
    content
)

# Update update_trailing_stop_with_protection
content = re.sub(
    r"min_stop = self\.entry_price \* 1\.001  # Komisyon buffer",
    r"min_stop = self.entry_price * (1 + DEFAULT_COMMISSION_BUFFER)  # Komisyon buffer",
    content
)

content = re.sub(
    r"max_stop = self\.entry_price \* 0\.999  # Komisyon buffer",
    r"max_stop = self.entry_price * (1 - DEFAULT_COMMISSION_BUFFER)  # Komisyon buffer",
    content
)

with open("core/trading/entities/position.py", "w") as f:
    f.write(content)
