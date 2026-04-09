with open("core/trading/position_manager.py", "r") as f:
    content = f.read()

# Fix list dictionary check logic in triggered levels
content = content.replace(
    """                    for triggered in triggered_levels:
                        if new_level.get("level") == triggered.get("level"):
                            new_level["hit"] = True""",
    """                    for triggered in triggered_levels:
                        if abs(new_level.get("level", 0.0) - triggered.get("level", 0.0)) < 1e-6:
                            new_level["hit"] = True"""
)

with open("core/trading/position_manager.py", "w") as f:
    f.write(content)
