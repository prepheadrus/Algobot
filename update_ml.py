import re

with open('ml/model_training.py', 'r') as f:
    content = f.read()

# 1. Add LabelEncoder to imports
if 'from sklearn.preprocessing import LabelEncoder' not in content:
    content = content.replace(
        'from sklearn.metrics import (',
        'from sklearn.preprocessing import LabelEncoder\nfrom sklearn.metrics import ('
    )

with open('ml/model_training.py', 'w') as f:
    f.write(content)
