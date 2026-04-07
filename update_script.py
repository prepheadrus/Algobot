import re

with open('ml/model_training.py', 'r') as f:
    content = f.read()

# 1. Update __init__ parameters
content = re.sub(
    r'(def __init__\(\s*self,\s*n_estimators: int = 400,\s*max_depth: int = 5,\s*learning_rate: float = 0\.05,\s*subsample: float = 0\.8,\s*colsample_bytree: float = 0\.8,\s*min_child_weight: int = 3,\s*gamma: float = 0\.1,\s*reg_alpha: float = 0\.1,\s*reg_lambda: float = 1\.0,\s*random_state: int = 42,\s*n_jobs: int = -1,\s*num_class: int = 3,)',
    r'\1\n        time_horizon: int = 10,',
    content
)

# Also add self.time_horizon in init body
content = re.sub(
    r'(self\.num_class = num_class)',
    r'\1\n        self.time_horizon = time_horizon',
    content
)

with open('ml/model_training.py', 'w') as f:
    f.write(content)
