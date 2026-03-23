"""
Unit tests for MLService.
"""

import sys
from unittest.mock import MagicMock

# Mock missing dependencies
mock_yaml = MagicMock()
mock_yaml.safe_load.return_value = {
    'bot': {
        'environment': 'development',
        'log_level': 'INFO',
        'name': 'CryptoAlgoBot'
    },
    'risk_management': {
        'default_leverage': 1,
        'max_consecutive_losses': 5,
        'max_leverage': 50,
        'max_open_positions': 10,
        'max_risk_per_trade_percent': 2.0
    },
    'ml': {
        'enabled': True,
        'confidence_threshold': 0.5,
        'leverage': {
            'normal_threshold': 0.65,
            'strong_threshold': 0.8,
            'weak_threshold': 0.5
        }
    },
    'strategy': {
        'active_modules': ['trend_following'],
        'ml_confidence_threshold': 0.6
    },
    'trading': {
        'exchange': 'binance',
        'symbols': [],
        'timeframes': ['1m']
    }
}

for module in [
    'colorlog', 'ccxt', 'ccxt.pro', 'pandas', 'numpy', 'pytz', 'xgboost',
    'sklearn', 'sklearn.ensemble', 'sklearn.preprocessing', 'sklearn.metrics',
    'joblib', 'torch', 'optuna', 'optuna.samplers', 'aiosqlite', 'dotenv', 'pydantic',
    'fastapi', 'fastapi.routing', 'fastapi.responses', 'starlette', 'uvicorn',
    'watchdog', 'watchdog.observers', 'watchdog.events'
]:
    sys.modules[module] = MagicMock()

sys.modules['yaml'] = mock_yaml

# Mock the entire api.services package to break cyclic dependencies
sys.modules['api.services.bot_service'] = MagicMock()
sys.modules['api.services.data_service'] = MagicMock()
sys.modules['api.services.strategy_service'] = MagicMock()

import pytest
from unittest.mock import patch
import os

# We need a proper mock for MLTrainRequest to avoid errors in ml_service.py if it's imported
class MockMLTrainRequest:
    def __init__(self):
        self.symbol = "BTC/USDT"
        self.timeframe = "1h"
        self.limit = 1000
        self.tp = 2.0
        self.sl = 2.0
        self.model_type = "xgboost"

sys.modules['api.schemas.ml'] = MagicMock()
sys.modules['api.schemas.ml'].MLTrainRequest = MockMLTrainRequest

# Now import MLService after mocking
from api.services.ml_service import MLService

class TestMLServiceDeleteHistory:
    """Tests for delete_training_history method of MLService."""

    def setup_method(self):
        self.ml_service = MLService()
        self.ml_service.training_history = [{"id": 1}, {"id": 2}]

    @patch("api.services.ml_service.os.path.exists")
    @patch("api.services.ml_service.os.remove")
    def test_delete_training_history_success(self, mock_remove, mock_exists):
        """Test successful deletion of training history."""
        # Setup
        mock_exists.return_value = True

        # Execute
        result = self.ml_service.delete_training_history()

        # Verify
        assert result["status"] == "success"
        assert result["message"] == "Geçmiş silindi"
        mock_exists.assert_called_once_with("artifacts/ml_training_history.json")
        mock_remove.assert_called_once_with("artifacts/ml_training_history.json")
        assert self.ml_service.training_history == []

    @patch("api.services.ml_service.os.path.exists")
    @patch("api.services.ml_service.os.remove")
    def test_delete_training_history_no_file(self, mock_remove, mock_exists):
        """Test deletion when history file doesn't exist."""
        # Setup
        mock_exists.return_value = False

        # Execute
        result = self.ml_service.delete_training_history()

        # Verify
        assert result["status"] == "success"
        assert result["message"] == "Geçmiş silindi"
        mock_exists.assert_called_once_with("artifacts/ml_training_history.json")
        mock_remove.assert_not_called()
        assert self.ml_service.training_history == [{"id": 1}, {"id": 2}]

    @patch("api.services.ml_service.os.path.exists")
    @patch("api.services.ml_service.os.remove")
    def test_delete_training_history_error(self, mock_remove, mock_exists):
        """Test error handling during deletion."""
        # Setup
        mock_exists.return_value = True
        mock_remove.side_effect = Exception("Permission denied")

        # Execute
        result = self.ml_service.delete_training_history()

        # Verify
        assert result["status"] == "error"
        assert "Permission denied" in result["message"]
        mock_remove.assert_called_once_with("artifacts/ml_training_history.json")
        # History should NOT be cleared if it failed
        assert self.ml_service.training_history == [{"id": 1}, {"id": 2}]


class TestMLServiceCheckModel:
    """Tests for check_model method of MLService."""

    def setup_method(self):
        self.ml_service = MLService()
        self.symbol = "BTC/USDT"
        self.timeframe = "1h"
        self.mock_model_paths = {
            'xgboost_path': 'artifacts/models/BTC_USDT_1h_xgb.json',
            'rf_path': 'artifacts/models/BTC_USDT_1h_rf.joblib',
            'metadata_path': 'artifacts/models/BTC_USDT_1h_meta.json'
        }

    @patch("api.services.ml_service.os.path.exists")
    @patch("ml.model_training.get_model_paths")
    def test_check_model_all_exist(self, mock_get_paths, mock_exists):
        """Test check_model when all model files exist."""
        # Setup
        mock_get_paths.return_value = self.mock_model_paths
        mock_exists.return_value = True

        # Execute
        result = self.ml_service.check_model(self.symbol, self.timeframe)

        # Verify
        mock_get_paths.assert_called_once_with(self.symbol, self.timeframe)
        assert mock_exists.call_count == 3

        assert result["status"] == "success"
        assert result["model_exists"] is True
        assert result["model_path"] == self.mock_model_paths['xgboost_path']
        assert result["message"] == "Model bulundu"

        ensemble_status = result["ensemble_status"]
        assert ensemble_status["xgboost"] is True
        assert ensemble_status["random_forest"] is True
        assert ensemble_status["metadata"] is True
        assert ensemble_status["full_ensemble"] is True

    @patch("api.services.ml_service.os.path.exists")
    @patch("ml.model_training.get_model_paths")
    def test_check_model_none_exist(self, mock_get_paths, mock_exists):
        """Test check_model when no model files exist."""
        # Setup
        mock_get_paths.return_value = self.mock_model_paths
        mock_exists.return_value = False

        # Execute
        result = self.ml_service.check_model(self.symbol, self.timeframe)

        # Verify
        mock_get_paths.assert_called_once_with(self.symbol, self.timeframe)
        assert mock_exists.call_count == 3

        assert result["status"] == "success"
        assert result["model_exists"] is False
        assert result["model_path"] is None
        assert result["message"] == "Model bulunamadı"

        ensemble_status = result["ensemble_status"]
        assert ensemble_status["xgboost"] is False
        assert ensemble_status["random_forest"] is False
        assert ensemble_status["metadata"] is False
        assert ensemble_status["full_ensemble"] is False

    @patch("api.services.ml_service.os.path.exists")
    @patch("ml.model_training.get_model_paths")
    def test_check_model_partial_exist(self, mock_get_paths, mock_exists):
        """Test check_model when only some model files exist."""
        # Setup
        mock_get_paths.return_value = self.mock_model_paths

        # Make XGBoost exist, but others not
        def mock_exists_side_effect(path):
            return path == self.mock_model_paths['xgboost_path']

        mock_exists.side_effect = mock_exists_side_effect

        # Execute
        result = self.ml_service.check_model(self.symbol, self.timeframe)

        # Verify
        mock_get_paths.assert_called_once_with(self.symbol, self.timeframe)
        assert mock_exists.call_count == 3

        assert result["status"] == "success"
        assert result["model_exists"] is True
        assert result["model_path"] == self.mock_model_paths['xgboost_path']
        assert result["message"] == "Model bulundu"

        ensemble_status = result["ensemble_status"]
        assert ensemble_status["xgboost"] is True
        assert ensemble_status["random_forest"] is False
        assert ensemble_status["metadata"] is False
        assert ensemble_status["full_ensemble"] is False
