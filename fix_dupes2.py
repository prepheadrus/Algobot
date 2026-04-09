import re

with open("core/trading/entities/position.py", "r") as f:
    content = f.read()

# Fix DEFAULT_COMMISSION_BUFFER duplication
content = re.sub(
    r"DEFAULT_COMMISSION_BUFFER = 0\.0008\n\nDEFAULT_COMMISSION_BUFFER = 0\.0008",
    r"DEFAULT_COMMISSION_BUFFER = 0.0008",
    content
)

# Fix initial_stop_loss duplication in dataclass definition
content = re.sub(
    r"    stop_loss: Optional\[float\] = None\n    initial_stop_loss: Optional\[float\] = None\n    initial_stop_loss: Optional\[float\] = None",
    r"    stop_loss: Optional[float] = None\n    initial_stop_loss: Optional[float] = None",
    content
)

with open("core/trading/entities/position.py", "w") as f:
    f.write(content)
