with open("core/trading/entities/position.py", "r") as f:
    content = f.read()

content = content.replace(
    "    stop_loss: Optional[float] = None\n    initial_stop_loss: Optional[float] = None\n    initial_stop_loss: Optional[float] = None",
    "    stop_loss: Optional[float] = None\n    initial_stop_loss: Optional[float] = None"
)

with open("core/trading/entities/position.py", "w") as f:
    f.write(content)
