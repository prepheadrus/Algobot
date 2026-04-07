"""
ML Inference Engine

Ensemble model (XGBoost + Random Forest) üzerinden canlı tahmin üretir.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
import joblib
import glob
import xgboost as xgb

# Model cache
_model_cache = {}


def get_model_paths(symbol: str, timeframe: str, direction: str, model_id: str = None) -> dict:
    """Model dosya yollarını döner (Yön bazlı Asimetrik Modeller için)."""
    if direction not in ['long', 'short']:
        raise ValueError(f"Geçersiz direction parametresi: '{direction}'.")

    # Symbol formatını temizle (BTC/USDT:USDT → btcusdtusdt)
    symbol_clean = symbol.replace('/', '').replace(':', '').replace('-', '').lower()
    base_path = "artifacts/models"
    
    # Yeni isimlendirme kuralı: xgb_model_{symbol}_{tf}_{date}_{direction}.json
    # Eğer model_id varsa (date olarak kullanılır), format: xgb_model_{symbol}_{tf}_{model_id}_{direction}.json
    # Eğer model_id yoksa fallback (eski yapı için veya genel okuma): xgb_model_{symbol}_{tf}_{direction}.json
    date_part = f"_{model_id}" if model_id else ""

    base_name = f"xgb_model_{symbol_clean}_{timeframe}{date_part}_{direction}"

    return {
        # ml_service.py'nin beklediği Legacy Anahtarlar (API Kontrat Kalkanı)
        "xgboost_path": f"{base_path}/{base_name}.json",
        "rf_path": f"{base_path}/{base_name}_rf.joblib",
        "metadata_path": f"{base_path}/{base_name}_metadata.json",

        # Inference ve diğer asenkron modüller için Kısa Anahtarlar
        "xgb": f"{base_path}/{base_name}.json",
        "rf": f"{base_path}/{base_name}_rf.joblib",
        "meta": f"{base_path}/{base_name}_metadata.json",

        # Geriye dönük uyumluluk için ek anahtarlar
        "xgboost": f"{base_path}/{base_name}.json",
        "random_forest": f"{base_path}/{base_name}_rf.joblib"
    }


def load_model(symbol: str, timeframe: str, direction: str, live_features: Optional[list] = None):
    """
    Ensemble model'i yükle (XGBoost + Random Forest). Yön spesifiktir.
    Cache kullanarak performansı optimize et.
    """
    cache_key = f"{symbol}_{timeframe}_{direction}"
    
    if cache_key in _model_cache:
        return _model_cache[cache_key]
    
    try:
        # Inference anında spesifik date bilinmediği için, en güncel model dosyası bulunmalıdır.
        # Basitçe klasörü tarayıp en güncel dosyayı bulalım:
        symbol_clean = symbol.replace('/', '').replace(':', '').replace('-', '').lower()
        search_pattern = f"artifacts/models/xgb_model_{symbol_clean}_{timeframe}_*_{direction}.json"
        matching_files = glob.glob(search_pattern)

        model_id = None
        if matching_files:
            # İsme göre sırala (tarih sonda olduğu için en yenisi en sonda olacaktır)
            latest_file = sorted(matching_files)[-1]
            # Dosya isminden model_id (tarih) kısmını çıkaralım:
            # format: xgb_model_{symbol}_{tf}_{date}_{direction}.json
            parts = latest_file.split('_')
            # xgb_model_btcusdtusdt_15m_20260406_143415_long.json
            # idx -2 = 143415, idx -3 = 20260406
            if len(parts) >= 6:
                # 20260406_143415 formatındaki date kısmını al (sondaki '_long.json' vs silip birleştirerek)
                basename = os.path.basename(latest_file)
                base_no_ext = basename.replace(f"_{direction}.json", "")
                prefix = f"xgb_model_{symbol_clean}_{timeframe}_"
                if base_no_ext.startswith(prefix):
                    model_id = base_no_ext[len(prefix):]

        model_paths = get_model_paths(symbol, timeframe, direction, model_id=model_id)
        
        # XGBoost model
        xgb_model = None
        if os.path.exists(model_paths['xgb']):
            xgb_model = xgb.Booster()
            xgb_model.load_model(model_paths['xgb'])
        
        # Random Forest model
        rf_model = None
        if os.path.exists(model_paths['rf']):
            rf_model = joblib.load(model_paths['rf'])
        
        # Metadata
        metadata = {}
        if os.path.exists(model_paths['meta']):
            with open(model_paths['meta'], 'r') as f:
                metadata = json.load(f)
        
        feature_names = metadata.get('feature_names', ['open', 'high', 'low', 'close', 'volume'])

        # Geriye dönük uyumluluk ve migrasyon (Feature uyuşmazlığı kontrolü)
        if live_features is not None:
            # Sadece modelin beklediği özelliklerin canlı veride EKSİK olup olmadığını kontrol et.
            # Canlı veride FAZLADAN kolon olması kesinlikle önemsizdir (Set Theory: A - B)
            missing_features = set(feature_names) - set(live_features)

            if missing_features:
                print(f"⚠️ [ML] Özellik uyuşmazlığı tespit edildi. Canlı veride şu beklenen özellikler EKSİK: {missing_features}.")
                print(f"⚠️ [ML] Model (eski/geçersiz) siliniyor: {symbol} {timeframe} {direction}")

                # Benzersiz dosya yollarını al ve KESİNLİKLE sadece 'eksik özellik' varsa sil
                unique_paths = list(set(model_paths.values()))
                for path_val in unique_paths:
                    if os.path.exists(path_val):
                        try:
                            os.remove(path_val)
                        except Exception as clean_e:
                            print(f"❌ [ML] Eski model dosyası silinemedi ({path_val}): {clean_e}")

                return None

        # Cache'e kaydet
        _model_cache[cache_key] = {
            'xgboost': xgb_model,
            'random_forest': rf_model,
            'metadata': metadata,
            'feature_names': feature_names
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


def get_ml_prediction(symbol: str, timeframe: str, direction: str, indicators: Dict[str, float]) -> Optional[Dict[str, Any]]:
    """
    Ensemble model ile belirli bir yön ('long' veya 'short') için tahmin üret.
    
    Args:
        symbol: Sembol (örn: BTC/USDT)
        timeframe: Zaman dilimi (örn: 1m)
        direction: Tahmin edilecek yön ('long' veya 'short')
        indicators: Teknik indikatörler (dict)
    
    Returns:
        {
            'prediction': 'TRADE' | 'HOLD',
            'confidence': float (0-1),
            'xgb_prediction': int,
            'rf_prediction': int,
            'ensemble_vote': str
        }
    """
    if direction not in ['long', 'short']:
        return None

    # Canlı özellikleri (feature) al
    live_features = list(indicators.keys())

    # Model yükle (live_features gönderilerek uyumsuzsa silinmesi sağlanır)
    model_data = load_model(symbol, timeframe, direction, live_features=live_features)
    
    if not model_data:
        return None
    
    xgb_model = model_data.get('xgboost')
    rf_model = model_data.get('random_forest')
    feature_names = model_data.get('feature_names', ['open', 'high', 'low', 'close', 'volume'])
    
    if not xgb_model and not rf_model:
        return None
    
    # Modelin eğitimde gördüğü kesin özellik sırasını XGBoost'tan al (Mevcutsa)
    expected_features = feature_names
    if xgb_model:
        try:
            # XGBoost özellik isimlerini doğrudan booster üzerinden al
            booster_features = xgb_model.feature_names
            if booster_features:
                expected_features = booster_features
        except AttributeError:
            pass

    # Dict'ten sadece beklenenleri, beklenen kesin sırayla alıp 2D DataFrame yap (Slicing & Tensor Order)
    # Canlı matrisin tam olarak modelin beklediği özelliklere ve sıraya hizalanması
    aligned_features = {}
    for f in expected_features:
        val = indicators.get(f, 0.0)
        # NaN kontrolü, güvenli cast işlemleri
        if isinstance(val, (int, float, np.number)):
            aligned_features[f] = float(val) if not np.isnan(val) else 0.0
        else:
            aligned_features[f] = 0.0

    X_live_ordered = pd.DataFrame([aligned_features])
    
    # XGBoost tahmini (Binary Classification)
    xgb_pred = None
    xgb_confidence = None
    if xgb_model:
        try:
            # XGBoost binary:logistic output probabilities for class 1
            # Hizalanmış DataFrame üzerinden, özelliklerin tam adıyla (feature_names) DMatrix oluştur
            # DMatrix'in özellikleri modelin beklediği sırayla beslediğinden kesin olarak emin olunur
            dmatrix = xgb.DMatrix(X_live_ordered, feature_names=expected_features)
            prob = xgb_model.predict(dmatrix)[0]
            xgb_pred = 1 if prob >= 0.5 else 0
            xgb_confidence = float(prob if xgb_pred == 1 else 1.0 - prob)
        except ValueError as e:
            # Inference (çıkarım) anında olası feature mismatach hatalarını yut, model silme işlemi uygulama
            print(f"⚠️ [ML] XGBoost tahmin hatası (Muhtemel Shape Mismatch, model silinmeyecek): {e}")
            xgb_pred = None
            xgb_confidence = None
    
    # Random Forest tahmini (Binary Classification)
    rf_pred = None
    rf_confidence = None
    if rf_model:
        # RF DataFrame üzerinden tahmin yapabilir
        rf_pred_proba = rf_model.predict_proba(X_live_ordered)[0]
        rf_pred = int(np.argmax(rf_pred_proba))
        rf_confidence = float(np.max(rf_pred_proba))
    
    # Ensemble voting (Soft Voting - confidence ağırlıklı - Binary)
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
        # Her tahmini confidence ile ağırla (Binary: 0 veya 1)
        weighted_votes = [0.0, 0.0]
        for pred, conf in zip(predictions, confidences):
            if 0 <= pred <= 1:
                weighted_votes[pred] += conf
        
        ensemble_pred = int(np.argmax(weighted_votes))
        ensemble_confidence = weighted_votes[ensemble_pred] / sum(weighted_votes)
    else:
        ensemble_pred = int(np.round(np.mean(predictions)))
        ensemble_confidence = np.mean(confidences) if confidences else 0.0
    
    # Label mapping (Binary)
    label_map = {0: 'HOLD', 1: 'TRADE'}
    
    # İşlem yönü de döndürülerek ek bilgi sağlanır
    direction_upper = direction.upper()

    return {
        'prediction': direction_upper if ensemble_pred == 1 else 'HOLD',
        'confidence': ensemble_confidence,
        'xgb_prediction': label_map.get(xgb_pred, 'N/A') if xgb_pred is not None else None,
        'rf_prediction': label_map.get(rf_pred, 'N/A') if rf_pred is not None else None,
        'ensemble_vote': f"{ensemble_pred} ({ensemble_confidence:.2%})",
        'direction': direction
    }


# Singleton pattern için helper
def get_ml_inference():
    """ML inference engine singleton."""
    return {
        'load_model': load_model,
        'get_prediction': get_ml_prediction
    }
