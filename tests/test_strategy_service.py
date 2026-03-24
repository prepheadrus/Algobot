import pytest
from unittest.mock import patch, MagicMock

from api.services.strategy_service import StrategyService
from strategy.manager import StrategyManager

class TestStrategyServiceGetStrategies:

    @patch('api.services.strategy_service.StrategyManager.load_dynamic_strategies')
    @patch('api.services.strategy_service.StrategyManager.get_all_strategies')
    @patch('api.services.strategy_service.StrategyManager.get_strategy')
    def test_get_strategies_happy_path(self, mock_get_strategy, mock_get_all, mock_load):
        # Arrange
        mock_get_all.return_value = {
            'test_strategy': {
                'name': 'Test Strategy',
                'description': 'A mock strategy for testing',
                'timeframe': '5m',
                'type': 'custom',
                'info': 'Additional info'
            }
        }

        mock_strategy_instance = MagicMock()
        mock_strategy_instance.required_indicators = ['RSI', 'MACD']
        mock_strategy_instance.get_conditions.return_value = {
            'LONG': ['RSI < 30'],
            'SHORT': ['RSI > 70']
        }
        mock_get_strategy.return_value = mock_strategy_instance

        service = StrategyService()

        # Act
        result = service.get_strategies()

        # Assert
        assert result['status'] == 'success'
        assert len(result['strategies']) == 1

        strategy_info = result['strategies'][0]
        assert strategy_info['id'] == 'test_strategy'
        assert strategy_info['name'] == 'Test Strategy'
        assert strategy_info['description'] == 'A mock strategy for testing'
        assert strategy_info['timeframe'] == '5m'
        assert strategy_info['type'] == 'custom'
        assert strategy_info['indicators'] == ['RSI', 'MACD']
        assert strategy_info['conditions'] == {'LONG': ['RSI < 30'], 'SHORT': ['RSI > 70']}
        assert strategy_info['info'] == 'Additional info'

        mock_load.assert_called_once()
        mock_get_all.assert_called_once()

    @patch('api.services.strategy_service.StrategyManager.load_dynamic_strategies')
    def test_get_strategies_error_handling(self, mock_load):
        # Arrange
        mock_load.side_effect = Exception("Corrupted strategy folder")

        service = StrategyService()

        # Act
        result = service.get_strategies()

        # Assert
        assert result['status'] == 'error'
        assert "Corrupted strategy folder" in result['message']

        mock_load.assert_called_once()

    @patch('api.services.strategy_service.StrategyManager.load_dynamic_strategies')
    @patch('api.services.strategy_service.StrategyManager.get_all_strategies')
    def test_get_strategies_empty(self, mock_get_all, mock_load):
        # Arrange
        mock_get_all.return_value = {}

        service = StrategyService()

        # Act
        result = service.get_strategies()

        # Assert
        assert result['status'] == 'success'
        assert result['strategies'] == []

        mock_load.assert_called_once()
        mock_get_all.assert_called_once()
