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
    
    from core.config import CONFIG
    # Dinamik olarak (Runtime/Hot-Reload) güven eşiğini oku
    ml_confidence_threshold = float(CONFIG.get('ml', {}).get('confidence_threshold', 0.60))

    # Çok sınıflı (multi:softprob) çıktı için Ensemble Voting (XGB + RF)
    xgb_probs = None
    if xgb_model:
        try:
            dmatrix = xgb.DMatrix(X_live_ordered, feature_names=expected_features)
            # multi:softprob döndürdüğü için shape (1, 3) şeklindedir
            prob = xgb_model.predict(dmatrix)[0]
            # Eğer model binary trained ise prob bir skalar veya (1,) olabilir. Bunu çok sınıflı yapıya göre uyarla.
            if isinstance(prob, (float, np.float32, np.float64)):
                 xgb_probs = np.array([1.0 - float(prob), float(prob), 0.0])
            else:
                 xgb_probs = np.array(prob)
        except ValueError as e:
            print(f"⚠️ [ML] XGBoost tahmin hatası (Muhtemel Shape Mismatch, model silinmeyecek): {e}")
    
    rf_probs = None
    if rf_model:
        try:
            rf_pred_proba = rf_model.predict_proba(X_live_ordered)[0]
            # RF genellikle eğitildiği sınıf sayısına göre döner (örn 3 sınıf)
            rf_probs = np.array(rf_pred_proba)
        except Exception as e:
            print(f"⚠️ [ML] Random Forest tahmin hatası: {e}")

    # Soft Voting
    probs_list = [p for p in [xgb_probs, rf_probs] if p is not None]
    if not probs_list:
        return None

    ensemble_probs = np.mean(probs_list, axis=0)

    # Güvenlik: Eğer ensemble_probs beklendiği gibi 3 boyutlu değilse sıfırlarla doldur
    if len(ensemble_probs) < 3:
        padded = np.zeros(3)
        padded[:len(ensemble_probs)] = ensemble_probs
        ensemble_probs = padded

    # Sınıflar: 0=SHORT, 1=HOLD, 2=LONG
    predicted_class = int(np.argmax(ensemble_probs))
    ensemble_confidence = float(ensemble_probs[predicted_class])

    # KATI ML GÜVEN EŞİĞİ (STRICT CONFIDENCE VETO) - Sadece LONG/SHORT sinyallerini filtrele
    if predicted_class in [0, 2] and ensemble_confidence < ml_confidence_threshold:
        print(f"🛡️ [ML VETO] Tahmin {predicted_class} için güven ({ensemble_confidence:.4f}) eşiğin ({ml_confidence_threshold}) altında. HOLD(1) yapılıyor.")
        predicted_class = 1  # HOLD / VETO
        # Güven skoru, VETO yapılmış haliyle o yöndeki/hold oranına atanabilir ama ensemble_confidence'ı orijinal prob olarak tutmak analitik için daha iyidir.

    label_map = {0: 'SHORT', 1: 'HOLD', 2: 'LONG'}
    prediction_label = label_map.get(predicted_class, 'HOLD')

    return {
        'prediction': prediction_label,
        'confidence': ensemble_confidence,
        'probabilities': ensemble_probs.tolist(),
        'xgb_prediction': int(np.argmax(xgb_probs)) if xgb_probs is not None else None,
        'rf_prediction': int(np.argmax(rf_probs)) if rf_probs is not None else None,
        'ensemble_vote': f"{predicted_class} ({ensemble_confidence:.2%})",
        'direction': direction
    }


# Singleton pattern için helper
def get_ml_inference():
    """ML inference engine singleton."""
    return {
        'load_model': load_model,
        'get_prediction': get_ml_prediction
    }
