"""
ML Inference Engine

Ensemble model (XGBoost + Random Forest) üzerinden canlı tahmin üretir.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np

# Model cache
_model_cache = {}


def get_model_paths(symbol: str, timeframe: str) -> Dict[str, Path]:
    """Model dosya yollarını döner."""
    # Symbol formatını temizle (BTC/USDT:USDT → btcusdtusdt)
    symbol_clean = symbol.replace('/', '').replace(':', '').replace('-', '').lower()
    base_path = Path("artifacts/models")
    
    return {
        'xgboost': base_path / f"xgb_model_{symbol_clean}_{timeframe}.json",
        'random_forest': base_path / f"xgb_model_{symbol_clean}_{timeframe}_rf.joblib",
        'metadata': base_path / f"xgb_model_{symbol_clean}_{timeframe}_metadata.json"
    }


def load_model(symbol: str, timeframe: str):
    """
    Ensemble model'i yükle (XGBoost + Random Forest).
    Cache kullanarak performansı optimize et.
    """
    cache_key = f"{symbol}_{timeframe}"
    
    if cache_key in _model_cache:
        return _model_cache[cache_key]
    
    try:
        model_paths = get_model_paths(symbol, timeframe)
        
        # XGBoost model
        import xgboost as xgb
        xgb_model = None
        if model_paths['xgboost'].exists():
            xgb_model = xgb.Booster()
            xgb_model.load_model(str(model_paths['xgboost']))
        
        # Random Forest model
        import joblib
        rf_model = None
        if model_paths['random_forest'].exists():
            rf_model = joblib.load(str(model_paths['random_forest']))
        
        # Metadata
        metadata = {}
        if model_paths['metadata'].exists():
            with open(model_paths['metadata'], 'r') as f:
                metadata = json.load(f)
        
        # Cache'e kaydet
        _model_cache[cache_key] = {
            'xgboost': xgb_model,
            'random_forest': rf_model,
            'metadata': metadata,
            'feature_names': metadata.get('feature_names', ['open', 'high', 'low', 'close', 'volume'])
        }
        
        return _model_cache[cache_key]
        
    except Exception as e:
        print(f"❌ [ML] Model yükleme hatası: {e}")
        return None


def prepare_features(indicators: Dict[str, float], feature_names: list) -> np.ndarray:
    """
    Indikatörlerden feature vektörü oluştur.
    """
    features = []
    for feat in feature_names:
        val = indicators.get(feat, 0.0)
        if isinstance(val, (int, float, np.number)):
            features.append(float(val) if not np.isnan(val) else 0.0)
        else:
            features.append(0.0)
    
    return np.array(features).reshape(1, -1)


def get_ml_prediction(symbol: str, timeframe: str, indicators: Dict[str, float]) -> Optional[Dict[str, Any]]:
    """
    Ensemble model ile tahmin üret.
    
    Args:
        symbol: Sembol (örn: BTC/USDT)
        timeframe: Zaman dilimi (örn: 1m)
        indicators: Teknik indikatörler (dict)
    
    Returns:
        {
            'prediction': 'LONG' | 'SHORT' | 'HOLD',
            'confidence': float (0-1),
            'xgb_prediction': int,
            'rf_prediction': int,
            'ensemble_vote': str
        }
    """
    # Model yükle
    model_data = load_model(symbol, timeframe)
    
    if not model_data:
        return None
    
    xgb_model = model_data.get('xgboost')
    rf_model = model_data.get('random_forest')
    feature_names = model_data.get('feature_names', ['open', 'high', 'low', 'close', 'volume'])
    
    if not xgb_model and not rf_model:
        return None
    
    # Feature vektörü hazırla
    X = prepare_features(indicators, feature_names)
    
    # XGBoost tahmini
    xgb_pred = None
    xgb_confidence = None
    if xgb_model:
        xgb_pred_proba = xgb_model.predict(xgb.DMatrix(X))
        xgb_pred = int(np.argmax(xgb_pred_proba[0]))
        xgb_confidence = float(np.max(xgb_pred_proba[0]))
    
    # Random Forest tahmini
    rf_pred = None
    rf_confidence = None
    if rf_model:
        rf_pred_proba = rf_model.predict_proba(X)[0]
        rf_pred = int(np.argmax(rf_pred_proba))
        rf_confidence = float(np.max(rf_pred_proba))
    
    # Ensemble voting (Soft Voting - confidence ağırlıklı)
    predictions = []
    confidences = []
    
    if xgb_pred is not None:
        predictions.append(xgb_pred)
        confidences.append(xgb_confidence)
    
    if rf_pred is not None:
        predictions.append(rf_pred)
        confidences.append(rf_confidence)
    
    if not predictions:
        return None
    
    # Confidence-ağırlıklı ortalama
    total_confidence = sum(confidences)
    if total_confidence > 0:
        # Her tahmini confidence ile ağırla
        weighted_votes = [0.0, 0.0, 0.0]  # [SHORT, NEUTRAL, LONG]
        for pred, conf in zip(predictions, confidences):
            if 0 <= pred < 3:
                weighted_votes[pred] += conf
        
        ensemble_pred = int(np.argmax(weighted_votes))
        ensemble_confidence = weighted_votes[ensemble_pred] / sum(weighted_votes)
    else:
        ensemble_pred = int(np.mean(predictions))
        ensemble_confidence = np.mean(confidences) if confidences else 0.0
    
    # Label mapping
    label_map = {0: 'SHORT', 1: 'NEUTRAL', 2: 'LONG'}
    
    return {
        'prediction': label_map.get(ensemble_pred, 'HOLD'),
        'confidence': ensemble_confidence,
        'xgb_prediction': label_map.get(xgb_pred, 'N/A') if xgb_pred is not None else None,
        'rf_prediction': label_map.get(rf_pred, 'N/A') if rf_pred is not None else None,
        'ensemble_vote': f"{ensemble_pred} ({ensemble_confidence:.2%})"
    }


# Singleton pattern için helper
def get_ml_inference():
    """ML inference engine singleton."""
    return {
        'load_model': load_model,
        'get_prediction': get_ml_prediction
    }
