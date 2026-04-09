with open("core/trading/position_manager.py", "r") as f:
    content = f.read()

# Fix list dictionary check logic in triggered levels
content = content.replace(
    """                    if new_level in triggered_levels:
                        new_level["hit"] = True""",
    """                    for triggered in triggered_levels:
                        if new_level.get("level") == triggered.get("level"):
                            new_level["hit"] = True"""
)

with open("core/trading/position_manager.py", "w") as f:
    f.write(content)
