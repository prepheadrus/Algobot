import xgboost as xgb
import numpy as np

# Create a simple dataset and train a model
X = np.random.rand(10, 5)
y = np.random.randint(2, size=10)

dtrain = xgb.DMatrix(X, label=y, feature_names=['a', 'b', 'c', 'd', 'e'])
params = {'objective': 'binary:logistic'}
bst = xgb.train(params, dtrain, 10)

bst.save_model('test_model.json')

loaded_bst = xgb.Booster()
loaded_bst.load_model('test_model.json')

print(loaded_bst.feature_names)
