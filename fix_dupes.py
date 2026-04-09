with open("core/trading/entities/position.py", "r") as f:
    content = f.read()

content = content.replace("            'initial_stop_loss': self.initial_stop_loss,\n            'initial_stop_loss': self.initial_stop_loss,", "            'initial_stop_loss': self.initial_stop_loss,")
content = content.replace("            initial_stop_loss=data.get('initial_stop_loss'),\n            initial_stop_loss=data.get('initial_stop_loss'),", "            initial_stop_loss=data.get('initial_stop_loss'),")

with open("core/trading/entities/position.py", "w") as f:
    f.write(content)
