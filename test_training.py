import sys
import os
import pandas as pd
from datetime import datetime

# Set up path
sys.path.insert(0, os.path.abspath('.'))

from ml.model_training import ModelTrainer

# Create a dummy dataset with 2 classes (binary)
import numpy as np
np.random.seed(42)
X_train = pd.DataFrame(np.random.rand(100, 5), columns=['f1', 'f2', 'f3', 'f4', 'f5'])
X_test = pd.DataFrame(np.random.rand(20, 5), columns=['f1', 'f2', 'f3', 'f4', 'f5'])
y_train = pd.Series(np.random.randint(0, 2, 100))
y_test = pd.Series(np.random.randint(0, 2, 20))
ret_test = pd.Series(np.random.randn(20))

print("Starting training test with 2 classes...")
trainer = ModelTrainer(n_estimators=10, max_depth=3)
trainer.feature_names = X_train.columns.tolist()
trainer.train(X_train, y_train, X_test, y_test, ret_test=ret_test)
print("Training completed successfully for binary!")

# Create a dummy dataset with 3 classes
y_train_multi = pd.Series(np.random.randint(0, 3, 100))
y_test_multi = pd.Series(np.random.randint(0, 3, 20))

print("\nStarting training test with 3 classes...")
trainer_multi = ModelTrainer(n_estimators=10, max_depth=3)
trainer_multi.feature_names = X_train.columns.tolist()
trainer_multi.train(X_train, y_train_multi, X_test, y_test_multi, ret_test=ret_test)
print("Training completed successfully for multi-class!")
