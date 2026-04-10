import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

# Proje importları
from ml.model_training import ModelTrainer
from ml.inference import get_ml_prediction

class TestMLInferenceAndTraining:

    @patch('core.config.CONFIG', {'ml': {'confidence_threshold': 0.60}})
    @patch('ml.inference.load_model')
    def test_strict_confidence_veto(self, mock_load_model):
        """
        VETO Kalkanının (Strict Confidence VETO) test edilmesi.
        Beklenti: LONG(2) olasılığı %45, HOLD(1) olasılığı %30, SHORT(0) olasılığı %25 ise
        Argmax LONG(2) seçer fakat güven %45 < %60 olduğu için VETO edilip HOLD(1) döner.
        """
        # Mock XGBoost modeli
        mock_xgb = MagicMock()
        mock_xgb.feature_names = ['f1', 'f2']
        # DMatrix'e tahmin olarak [0.25, 0.30, 0.45] dönelim
        mock_xgb.predict.return_value = np.array([[0.25, 0.30, 0.45]])

        # Mock RF modeli (none diyelim, sadece XGB test edilsin)
        mock_rf = None

        mock_load_model.return_value = {
            'xgboost': mock_xgb,
            'random_forest': mock_rf,
            'feature_names': ['f1', 'f2']
        }

        # İndikatörler canlı veri
        indicators = {'f1': 1.0, 'f2': 2.0}

        # Tahmin al
        result = get_ml_prediction('BTC/USDT', '15m', 'long', indicators)

        assert result is not None
        assert result['confidence'] == 0.45  # Güven orijinal tutulmalı
        assert result['prediction'] == 'HOLD'  # Argmax 2 olmasına rağmen 1'e zorlandı
        assert result['ensemble_vote'].startswith('1')  # VETO sonucu ensemble vote 1 oldu

    @patch('core.config.CONFIG', {'ml': {'confidence_threshold': 0.60}})
    @patch('ml.inference.load_model')
    def test_strict_confidence_pass(self, mock_load_model):
        """
        VETO Kalkanını GEÇEN durumun test edilmesi.
        Beklenti: SHORT(0) olasılığı %65, HOLD(1) olasılığı %15, LONG(2) olasılığı %20 ise
        Argmax SHORT(0) seçer ve güven %65 >= %60 olduğu için geçer.
        """
        mock_xgb = MagicMock()
        mock_xgb.feature_names = ['f1', 'f2']
        # DMatrix'e tahmin olarak [0.65, 0.15, 0.20] dönelim
        mock_xgb.predict.return_value = np.array([[0.65, 0.15, 0.20]])

        mock_load_model.return_value = {
            'xgboost': mock_xgb,
            'random_forest': None,
            'feature_names': ['f1', 'f2']
        }

        indicators = {'f1': 1.0, 'f2': 2.0}

        result = get_ml_prediction('BTC/USDT', '15m', 'short', indicators)

        assert result is not None
        assert result['confidence'] == 0.65
        assert result['prediction'] == 'SHORT'
        assert result['ensemble_vote'].startswith('0')

    @patch('ml.model_training.xgb.XGBClassifier')
    def test_feature_selection_dropping(self, mock_xgb_class):
        """
        Model Eğitimi: Zayıf özelliklerin düşürülmesi (Curse of Dimensionality Shield) testi.
        Beklenti: 'vwap_dist' düşük öneme sahip olsa bile protected olduğu için düşürülmez.
        'noise_feature' düşük öneme sahip olduğu için düşürülür.
        'strong_feature' yüksek öneme sahip olduğu için düşürülmez.
        """
        # Mock base XGBoost
        mock_base_model = MagicMock()
        # f_names: ['vwap_dist', 'noise_feature', 'strong_feature']
        # importances: vwap_dist (0.001), noise_feature (0.005), strong_feature (0.99)
        mock_base_model.feature_importances_ = np.array([0.001, 0.005, 0.99])
        mock_xgb_class.return_value = mock_base_model

        trainer = ModelTrainer(enable_auto_regularization=False)
        trainer.feature_names = ['vwap_dist', 'noise_feature', 'strong_feature']

        X_train = pd.DataFrame(np.random.rand(100, 3), columns=trainer.feature_names)
        X_test = pd.DataFrame(np.random.rand(20, 3), columns=trainer.feature_names)
        y_train = pd.Series(np.random.choice([0, 1, 2], 100))
        y_test = pd.Series(np.random.choice([0, 1, 2], 20))

        import sys
        # Optuna'yı mockla ki test uzamasın ve cv/split hatası fırlatmasın (Sadece selection test ediyoruz)
        with patch.dict(sys.modules, {'optuna': None}):
            # Train methodunu çağır, protected_features ver, min_importance = 0.01 (yani 0.001 ve 0.005 zayıf)
            with patch.object(trainer.xgb_model, 'fit'), patch.object(trainer.rf_model, 'fit'), patch.object(trainer.xgb_model, 'predict_proba', return_value=np.zeros((20,3))), patch.object(trainer.rf_model, 'predict_proba', return_value=np.zeros((20,3))), patch.object(trainer.xgb_model, 'predict', return_value=np.zeros(20)), patch.object(trainer.rf_model, 'predict', return_value=np.zeros(20)):
            # predict_proba ve predict metodlarını mockluyoruz çünkü is_fitted hatası almamak için fit'i mockladık
                trainer.train(
                    X_train, y_train, X_test, y_test,
                    min_importance=0.01,
                    protected_features=['vwap_dist']
                )

        # 'noise_feature' elenmiş olmalı
        assert 'noise_feature' not in trainer.feature_names
        # 'vwap_dist' korunmuş olmalı
        assert 'vwap_dist' in trainer.feature_names
        # 'strong_feature' güçlü olduğu için kalmalı
        assert 'strong_feature' in trainer.feature_names
