import xgboost as xgb
import numpy as np
import pandas as pd
import json
import os
from core.logger import logger

class XGBoostModel:
    """
    Ağaç tabanlı XGBoost modeli: Kesirli fark alınmış ve etiketlenmiş statik göstergelerle 
    yüksek başarı oranlı yönergeler çıkarmada güçlüdür.
    """
    def __init__(self, params=None):
        if params is None:
            # Standart Kripto Volatilitesi için iyileştirilmiş başlangıç parametreleri
            self.params = {
                'objective': 'multi:softprob',  # Olasılık tabanlı çoklu sınıflandırma (Long/Short/Hold)
                'num_class': 3,
                'eval_metric': 'mlogloss',
                'max_depth': 6,
                'learning_rate': 0.05,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': 42
            }
        else:
            self.params = params
            
        self.model = None

    def train(self, X_train: pd.DataFrame, y_train: pd.Series, X_val=None, y_val=None, num_boost_round=100):
        """Modeli eğitir ve valizasyon verisi varsa performansı ekrana basar."""
        dtrain = xgb.DMatrix(X_train, label=y_train)
        
        evals = [(dtrain, 'train')]
        if X_val is not None and y_val is not None:
            dval = xgb.DMatrix(X_val, label=y_val)
            evals.append((dval, 'eval'))

        logger.info("XGBoost modeli eğitimi başlatılıyor...")
        # Erken durdurma mekanizmasıyla (early stopping) aşırı öğrenmeyi (overfitting) engelliyoruz
        self.model = xgb.train(
            self.params,
            dtrain,
            num_boost_round=num_boost_round,
            evals=evals,
            early_stopping_rounds=10 if X_val is not None else None,
            verbose_eval=False
        )
        logger.info("XGBoost eğitimi tamamlandı.")

    def predict_proba(self, X_test: pd.DataFrame) -> np.ndarray:
        """Yeni veriler için olasılık tahminleri dönüştürür."""
        if self.model is None:
            raise ValueError("Model henüz eğitilmedi. Lütfen önce `train` metodunu çağırın.")
        
        dtest = xgb.DMatrix(X_test)
        return self.model.predict(dtest)

    def save_model(self, filepath: str):
        """Modeli güvenli bir şekilde JSON formatında ve meta verilerini ayrı olarak kaydeder."""
        if self.model is None:
            raise ValueError("Model henüz eğitilmedi. Kaydedilecek bir model yok.")

        # Ensure the path ends with .json
        if not filepath.endswith('.json'):
            filepath += '.json'

        # Modelin kendisini native method ile güvenli olarak JSON formatında kaydet
        self.model.save_model(filepath)

        # Meta verilerini ayrı bir json dosyasına kaydet
        metadata = {
            'params': self.params
        }

        base_dir = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        name_without_ext = os.path.splitext(filename)[0]
        metadata_filepath = os.path.join(base_dir, f"{name_without_ext}_metadata.json")

        with open(metadata_filepath, 'w') as f:
            json.dump(metadata, f, indent=4)

        logger.info(f"Model {filepath} konumuna ve meta veriler {metadata_filepath} konumuna başarıyla kaydedildi.")

    @classmethod
    def load_model(cls, filepath: str) -> "XGBoostModel":
        """Modeli ve meta verilerini güvenli bir şekilde yükler."""
        if not filepath.endswith('.json'):
            filepath += '.json'

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model dosyası bulunamadı: {filepath}")

        base_dir = os.path.dirname(filepath)
        filename = os.path.basename(filepath)
        name_without_ext = os.path.splitext(filename)[0]
        metadata_filepath = os.path.join(base_dir, f"{name_without_ext}_metadata.json")

        params = None
        if os.path.exists(metadata_filepath):
            try:
                with open(metadata_filepath, 'r') as f:
                    metadata = json.load(f)
                    params = metadata.get('params')
            except Exception as e:
                logger.warning(f"Metadata okunamadı veya bozuk: {e}")

        # Yeni bir instance oluştur
        instance = cls(params=params)

        # Booster nesnesini oluştur ve yükle
        booster = xgb.Booster()
        booster.load_model(filepath)
        instance.model = booster

        logger.info(f"Model {filepath} konumundan başarıyla yüklendi.")
        return instance
