"""
XGBoost Model Eğitimi ve Tahmin Modülü

Bu modül, Marcos Lopez de Prado'nun Triple Barrier Method ile etiketlenmiş
veriler üzerinde XGBoost modeli eğitir. Model hem yön tahmini yapar hem de
güven skoru (confidence score) üretir.

Mimari Kural: Model multi-class classification (multi:softprob) yapar ve
PaperTrader dinamik kaldıraç için confidence score kullanır.
"""

import os
import json
import numpy as np
import pandas as pd
from pandas import Series
from typing import Tuple, Dict, Any, List
from datetime import datetime
import xgboost as xgb
try:
    import optuna
except ImportError:
    optuna = None
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix,
    log_loss
)
import asyncio
from core.logger import logger


from ml.inference import get_model_paths


class ModelTrainer:
    """
    XGBoost + Random Forest Ensemble Model Eğitici Sınıfı
    
    Triple Barrier etiketli veriler üzerinde çok sınıflı sınıflandırma
    (LONG/SHORT/NEUTRAL) yapar ve güven skoru üretir.
    Ensemble (füzyon) yaklaşımı ile daha güvenilir tahminler yapar.
    
    OVERFITTING PROTECTION:
    - Veri seti boyutuna göre dinamik parametreler
    - Regularization (L1 + L2)
    - Early stopping
    - Cross-validation
    - Maximum depth sınırlaması
    """
    
    # Overfitting önleme için minimum veri gereksinimleri
    MIN_SAMPLES_FOR_COMPLEX_MODEL = 5000
    MIN_SAMPLES_FOR_MEDIUM_MODEL = 2000
    MIN_SAMPLES_FOR_SIMPLE_MODEL = 500

    def __init__(
        self,
        n_estimators: int = 400,
        max_depth: int = 5,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        min_child_weight: int = 3,
        gamma: float = 0.1,
        reg_alpha: float = 0.1,
        reg_lambda: float = 1.0,
        random_state: int = 42,
        n_jobs: int = -1,
        num_class: int = 3,
        time_horizon: int = 10,
        # Random Forest parametreleri
        rf_n_estimators: int = 200,
        rf_max_depth: int = 10,
        rf_min_samples_split: int = 5,
        # Overfitting protection
        enable_auto_regularization: bool = True
    ):
        # Override with required defaults
        n_estimators = 400
        max_depth = 5
        learning_rate = 0.05
        reg_alpha = 0.1
        reg_lambda = 1.0
        """
        XGBoost modelini başlatır.

        Args:
            n_estimators: Ağaç sayısı
            max_depth: Maksimum ağaç derinliği
            learning_rate: Öğrenme oranı
            subsample: Veri örnekleme oranı
            colsample_bytree: Özellik örnekleme oranı
            min_child_weight: Minimum child weight (overfitting önleme)
            gamma: Minimum split loss (overfitting önleme)
            reg_alpha: L1 regularization
            reg_lambda: L2 regularization
            random_state: Random seed
            n_jobs: Parallel job sayısı (-1 = tüm CPU)
            early_stopping_rounds: Early stopping için round sayısı
            num_class: Sınıf sayısı (3: LONG, NEUTRAL, SHORT)
            enable_auto_regularization: Veri boyutuna göre otomatik parametre ayarı
        """
        # Parametreleri kaydet (auto regularization için)
        self.base_params = {
            'n_estimators': n_estimators,
            'max_depth': max_depth,
            'learning_rate': learning_rate,
            'subsample': subsample,
            'colsample_bytree': colsample_bytree,
            'min_child_weight': min_child_weight,
            'gamma': gamma,
            'reg_alpha': reg_alpha,
            'reg_lambda': reg_lambda,
            'rf_n_estimators': rf_n_estimators,
            'rf_max_depth': rf_max_depth
        }
        
        self.enable_auto_regularization = enable_auto_regularization
        
        # Veri boyutuna göre parametreler (sonra güncellenecek)
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.rf_max_depth = rf_max_depth
        self.min_child_weight = min_child_weight
        self.gamma = gamma
        self.reg_alpha = reg_alpha
        self.reg_lambda = reg_lambda
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.rf_n_estimators = rf_n_estimators
        self.rf_min_samples_split = rf_min_samples_split
        
        self.learning_rate = learning_rate
        self.random_state = random_state
        self.n_jobs = n_jobs
        self.num_class = num_class
        self.time_horizon = time_horizon

        # XGBoost modelini başlat (Binary Classification)
        self.xgb_model = xgb.XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=subsample,
            colsample_bytree=colsample_bytree,
            min_child_weight=min_child_weight,
            gamma=gamma,
            reg_alpha=reg_alpha,
            reg_lambda=reg_lambda,
            random_state=random_state,
            n_jobs=n_jobs,
            objective='multi:softprob',
            num_class=num_class,
            eval_metric='mlogloss'
        )

        # Random Forest modelini başlat (Binary Classification)
        self.rf_model = RandomForestClassifier(
            n_estimators=rf_n_estimators,
            max_depth=rf_max_depth,
            min_samples_split=rf_min_samples_split,
            random_state=random_state,
            n_jobs=n_jobs,
            class_weight='balanced'
        )

        self.is_trained = False
        self.feature_names = None
        self.training_metrics = {}
        self.class_mapping = {0: 'HOLD/NEUTRAL', 1: 'TRADE'}

    def apply_auto_regularization(self, data_size: int):
        """
        Veri seti boyutuna göre model parametrelerini otomatik ayarla.
        Overfitting önleme mekanizması.
        
        Args:
            data_size: Eğitim veri seti boyutu (satır sayısı)
        """
        if not self.enable_auto_regularization:
            logger.info(
                f"ℹ️ [ML] Auto regularization kapalı, kullanıcı/UI parametreleri kullanılıyor | "
                f"n_estimators={self.n_estimators}, max_depth={self.max_depth}, "
                f"lr={self.learning_rate}"
            )
            return
        
        logger.info(f"📊 [ML] Veri boyutu: {data_size} satır")
        
        # Complex model (5000+ satır)
        if data_size >= self.MIN_SAMPLES_FOR_COMPLEX_MODEL:
            logger.info("✅ [ML] COMPLEX mod: Büyük veri seti, tam kapasite")
            self._apply_params(self.base_params)
        
        # Medium model (2000-5000 satır)
        elif data_size >= self.MIN_SAMPLES_FOR_MEDIUM_MODEL:
            logger.info("⚠️ [ML] MEDIUM mod: Orta veri seti, regularization artırılıyor")
            medium_params = self.base_params.copy()
            medium_params.update({
                'n_estimators': 300,
                'max_depth': 4,
                'rf_max_depth': 6,
                'rf_n_estimators': 150,
                'learning_rate': 0.05,
                'subsample': 0.75,
                'colsample_bytree': 0.75,
                'reg_alpha': 0.2,
                'reg_lambda': 2.0
            })
            self._apply_params(medium_params)
        
        # Simple model (500-2000 satır)
        elif data_size >= self.MIN_SAMPLES_FOR_SIMPLE_MODEL:
            logger.info("⚠️ [ML] SIMPLE mod: Küçük veri seti, güçlü regularization")
            simple_params = self.base_params.copy()
            simple_params.update({
                'n_estimators': 200,
                'max_depth': 3,
                'rf_max_depth': 4,
                'rf_n_estimators': 100,
                'learning_rate': 0.03,
                'subsample': 0.7,
                'colsample_bytree': 0.7,
                'min_child_weight': 5,
                'gamma': 0.2,
                'reg_alpha': 0.5,
                'reg_lambda': 5.0
            })
            self._apply_params(simple_params)
        
        # Too small (< 500 satır)
        else:
            logger.warning(f"⚠️ [ML] VERİ SETİ ÇOK KÜÇÜK ({data_size} satır)! Model eğitimi önerilmez.")
            logger.warning("   En az 500 satır önerilir, ideal 2000+ satır")
            ultra_simple_params = self.base_params.copy()
            ultra_simple_params.update({
                'n_estimators': 100,
                'max_depth': 2,
                'rf_max_depth': 3,
                'rf_n_estimators': 50,
                'learning_rate': 0.01,
                'subsample': 0.6,
                'colsample_bytree': 0.6,
                'min_child_weight': 10,
                'gamma': 0.5,
                'reg_alpha': 1.0,
                'reg_lambda': 10.0
            })
            self._apply_params(ultra_simple_params)
        
        # Model parametrelerini güncelle
        self._update_models()
    
    def _apply_params(self, params: dict):
        """Parametreleri uygula"""
        self.n_estimators = params['n_estimators']
        self.max_depth = params['max_depth']
        self.rf_max_depth = params['rf_max_depth']
        self.rf_n_estimators = params['rf_n_estimators']
        self.learning_rate = params.get('learning_rate', self.learning_rate)
        self.subsample = params.get('subsample', self.subsample)
        self.colsample_bytree = params.get('colsample_bytree', self.colsample_bytree)
        self.min_child_weight = params.get('min_child_weight', self.min_child_weight)
        self.gamma = params.get('gamma', self.gamma)
        self.reg_alpha = params.get('reg_alpha', self.reg_alpha)
        self.reg_lambda = params.get('reg_lambda', self.reg_lambda)
        self.rf_min_samples_split = params.get('rf_min_samples_split', self.rf_min_samples_split)
    
    def _update_models(self):
        """Model parametrelerini güncelle"""
        # XGBoost parametrelerini güncelle
        self.xgb_model.set_params(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            learning_rate=self.learning_rate,
            subsample=self.subsample,
            colsample_bytree=self.colsample_bytree,
            min_child_weight=self.min_child_weight,
            gamma=self.gamma,
            reg_alpha=self.reg_alpha,
            reg_lambda=self.reg_lambda
        )
        
        # Random Forest parametrelerini güncelle
        self.rf_model.set_params(
            n_estimators=self.rf_n_estimators,
            max_depth=self.rf_max_depth,
            min_samples_split=self.rf_min_samples_split
        )
        
        logger.info(
            f"🔧 [ML] Parametreler güncellendi | "
            f"n_estimators={self.n_estimators}, max_depth={self.max_depth}, "
            f"rf_max_depth={self.rf_max_depth}, lr={self.learning_rate}, "
            f"reg_alpha={self.reg_alpha}, reg_lambda={self.reg_lambda}"
        )

    def _objective(
        self,
        trial,
        X_train: pd.DataFrame,
        y_train: pd.Series,
    ) -> float:
        """
        Optuna için Negative Log Loss Optimizasyon Hedef Fonksiyonu
        Purged K-Fold (TimeSeriesSplit + Embargo) kullanarak sızıntısız ortalama Negatif Logloss hesaplar.
        Modelin ürettiği ham olasılıkların kalitesini ölçer.
        """
        from sklearn.model_selection import TimeSeriesSplit
        import gc

        params = {
            'n_estimators': self.n_estimators, # Statik tutuyoruz
            'max_depth': trial.suggest_int('max_depth', 3, 9),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
            'subsample': trial.suggest_float('subsample', 0.5, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
            'objective': 'multi:softprob',
            'num_class': self.num_class,
            'eval_metric': 'mlogloss',
            'random_state': self.random_state,
            'n_jobs': self.n_jobs
        }

        # Sızıntı kalkanı (Purged K-Fold/Embargoing): test/val ufku kadar boşluk bırakıyoruz
        tscv = TimeSeriesSplit(n_splits=5, gap=self.time_horizon)
        neg_logloss_scores = []

        # Ensure they are pandas types for indexing
        if not isinstance(X_train, pd.DataFrame):
            X_train = pd.DataFrame(X_train)
        if not isinstance(y_train, pd.Series):
            y_train = pd.Series(y_train)

        for train_index, val_index in tscv.split(X_train):
            X_train_fold, X_val_fold = X_train.iloc[train_index], X_train.iloc[val_index]
            y_train_fold, y_val_fold = y_train.iloc[train_index], y_train.iloc[val_index]

            # Eğer embargo sonrası fold çok küçülürse (örn. veri seti çok ufaksa), atla
            if len(y_train_fold) == 0 or len(y_val_fold) == 0:
                continue

            try:
                # Class imbalance için fold'a özel weight
                sample_weights = compute_sample_weight('balanced', y_train_fold)

                model = xgb.XGBClassifier(**params)
                model.fit(
                    X_train_fold,
                    y_train_fold,
                    sample_weight=sample_weights,
                    verbose=False
                )

                preds_proba = model.predict_proba(X_val_fold)
                loss = log_loss(y_val_fold, preds_proba, labels=model.classes_)
                neg_logloss_scores.append(-1.0 * loss)
            except Exception as e:
                # Olası bir xgboost hatası (örn: sadece tek class kalması durumu)
                logger.debug(f"Fold atlandı, hata: {e}")
                pass
            finally:
                # MEMORY BLOAT KALKANI
                del X_train_fold, y_train_fold, X_val_fold, y_val_fold
                gc.collect()

        if not neg_logloss_scores:
            return -999.0

        return sum(neg_logloss_scores) / len(neg_logloss_scores)

    def train(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_test: pd.DataFrame,
        y_test: Series,
        ret_test: pd.Series = None,
        verbose: bool = True,
        min_importance: float = 0.01,
        protected_features: List[str] = None
    ) -> Dict[str, Any]:
        """
        XGBoost (Optuna ile) + Random Forest Ensemble modellerini eğitir ve değerlendirir.

        Args:
            X_train: Eğitim özellikleri
            y_train: Eğitim etiketleri
            X_test: Test özellikleri
            y_test: Test etiketleri
            verbose: Log çıktısı gösterilsin mi?

        Returns:
            Dict[str, Any]: Eğitim metrikleri
        """
        logger.info("🧠 Ensemble (XGBoost + RF) eğitimi başlatılıyor...")
        logger.info(f"  Eğitim seti: {X_train.shape}")
        logger.info(f"  Test seti: {X_test.shape}")
        logger.info(f"  Sınıf dağılımı (train): {y_train.value_counts().to_dict()}")
        
        # OVERFITTING PROTECTION: Veri boyutuna göre parametre ayarı
        data_size = len(X_train)
        self.apply_auto_regularization(data_size)

        # Feature names'i sakla
        if isinstance(X_train, pd.DataFrame):
            self.feature_names = X_train.columns.tolist()
        else:
            self.feature_names = [f"feature_{i}" for i in range(X_train.shape[1])]

        # Sınıf Ağırlıklandırması (Class Imbalance) hesapla
        sample_weights = compute_sample_weight('balanced', y_train)

        # Eğitim setinde yeterli sınıf çeşitliliği var mı kontrolü (Fail-Fast)
        unique_classes = set(np.unique(y_train))
        if len(unique_classes) < 2:
            raise ValueError(f"⚠️ [ML] Eğitim setinde yalnızca tek bir sınıf mevcut: {unique_classes}. Binary classification yapılamaz. Yeterli sinyal oluşmamış olabilir.")

        if protected_features is None:
            protected_features = ["dist_to_vwap", "OBV_EMA", "frac_diff_04", "BTC_VIX"]

        logger.info("🛡️ [ML] Feature Selection (Curse of Dimensionality Shield) başlatılıyor...")

        def fit_base_model():
            base_model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                objective='multi:softprob',
                num_class=self.num_class,
                random_state=self.random_state,
                n_jobs=self.n_jobs
            )
            base_model.fit(X_train, y_train, sample_weight=sample_weights, verbose=False)
            return base_model

        try:
            try:
                loop = asyncio.get_running_loop()
                import concurrent.futures
                # asyncio.to_thread gerektirir asyncio ile bekleme, ancak train fonksiyonu senkron.
                # Run_in_executor veya manuel çalıştırma için event loop block edilmemeli.
                # Eğer kod zaten event loop içindeyse ve bu thread'de ise asyncio loop running state'indedir.
                # Ancak 'train' metodu 'async def' değil, bu yüzden await edemeyiz.
                # ThreadPool kullanarak arka planda çalışıp block etmesini sağlayalım:
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(fit_base_model)
                    base_model = future.result()
            except RuntimeError:
                base_model = fit_base_model()

        except Exception as e:
             logger.warning(f"⚠️ [ML] Base model feature selection için eğitilemedi, seçim atlanıyor: {e}")
             base_model = None

        if base_model is not None:
             importances = base_model.feature_importances_
             features_to_drop = []
             features_to_keep = []
             for idx, col in enumerate(self.feature_names):
                 importance = importances[idx]
                 if importance < min_importance:
                     if col in protected_features:
                         logger.info(f"🛡️ [ML] Protected feature tutuluyor (Low Importance: {importance:.4f}): {col}")
                         features_to_keep.append(col)
                     else:
                         features_to_drop.append(col)
                 else:
                     features_to_keep.append(col)

             # Protected features DataFrame'de yoksa fail-fast yapma, sessizce geç
             for p_feat in protected_features:
                 if p_feat not in self.feature_names:
                     logger.warning(f"⚠️ [ML] Protected feature '{p_feat}' not found in dataset, skipping.")

             if features_to_drop:
                 logger.info(f"🗑️ [ML] {len(features_to_drop)} zayıf özellik drop ediliyor (Importance < {min_importance}): {features_to_drop}")
                 X_train = X_train.drop(columns=features_to_drop, errors='ignore')
                 X_test = X_test.drop(columns=features_to_drop, errors='ignore')
                 self.feature_names = features_to_keep
             else:
                 logger.info("ℹ️ [ML] Hiçbir özellik drop edilmedi (Hepsi önemli).")

        # 1. XGBoost modelini eğit (Optuna ile Optimizasyon)
        import sys
        if optuna is not None and getattr(sys.modules.get('optuna', None), 'create_study', None):
            logger.info("📊 XGBoost eğitiliyor (Optuna TPE Optimizasyonu Başlıyor)...")
            study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=self.random_state))

            # Objective fonksiyonunu lambda ile wrap ediyoruz (Sadece train gönderilir, Hold-Out kuralı)
            objective_wrapper = lambda trial: self._objective(trial, X_train, y_train)

            # n_trials=50 sabiti
            study.optimize(objective_wrapper, n_trials=50)

            best_params = study.best_params
            logger.info(f"🏆 Optuna En İyi Parametreler: {best_params}")
            logger.info(f"🏆 En İyi Purged Negatif Log Loss Oranı: {study.best_value:.4f}")

            # Best parametreleri set et
            self._apply_params({
                'n_estimators': self.n_estimators,
                'max_depth': best_params['max_depth'],
                'rf_max_depth': self.rf_max_depth,
                'rf_n_estimators': self.rf_n_estimators,
                'learning_rate': best_params['learning_rate'],
                'subsample': best_params['subsample'],
                'colsample_bytree': best_params['colsample_bytree'],
            })
            self._update_models()

            # Final modeli en iyi parametrelerle eğit
            logger.info("🔄 En iyi parametrelerle final XGBoost modeli eğitiliyor...")
            eval_set = [(X_train, y_train), (X_test, y_test)]
            self.xgb_model.fit(
                X_train,
                y_train,
                sample_weight=sample_weights,
                eval_set=eval_set,
                verbose=verbose
            )
            logger.info("✅ Optuna + XGBoost eğitimi tamamlandı.")
        else:
            logger.info("📊 XGBoost eğitiliyor (Statik)...")
            eval_set = [(X_train, y_train), (X_test, y_test)]
            self.xgb_model.fit(
                X_train,
                y_train,
                sample_weight=sample_weights,
                eval_set=eval_set,
                verbose=verbose
            )
            logger.info("✅ XGBoost eğitimi tamamlandı.")

        # 2. Random Forest modelini eğit
        logger.info("🌲 Random Forest eğitiliyor...")
        # Random forest is already initialized with class_weight='balanced'
        self.rf_model.fit(X_train, y_train)
        logger.info("✅ Random Forest eğitimi tamamlandı.")

        self.is_trained = True

        # 3. Ensemble tahmini (Soft Voting)
        logger.info("🔗 Ensemble tahminleri hesaplanıyor...")
        xgb_proba = self.xgb_model.predict_proba(X_test)
        rf_proba = self.rf_model.predict_proba(X_test)

        # Soft Voting: Olasılıkların ortalamasını al
        ensemble_proba = (xgb_proba + rf_proba) / 2
        y_pred = np.argmax(ensemble_proba, axis=1)

        # Metrikleri hesapla
        metrics = self._calculate_metrics(y_test, y_pred)
        self.training_metrics = metrics

        # Her modelin ayrı metriklerini de hesapla
        y_pred_xgb = self.xgb_model.predict(X_test)
        y_pred_rf = self.rf_model.predict(X_test)
        metrics['xgb_accuracy'] = accuracy_score(y_test, y_pred_xgb)
        metrics['rf_accuracy'] = accuracy_score(y_test, y_pred_rf)
        metrics['ensemble_accuracy'] = metrics['accuracy']

        # Feature importance hesapla (XGBoost'tan)
        feature_importance = self._calculate_feature_importance()

        # Sonuçları logla
        logger.info("=" * 60)
        logger.info("EĞİTİM SONUÇLARI")
        logger.info("=" * 60)
        logger.info(f"Accuracy:  {metrics['accuracy']:.4f}")
        logger.info(f"Precision: {metrics['precision']:.4f}")
        logger.info(f"Recall:    {metrics['recall']:.4f}")
        logger.info(f"F1-Score:  {metrics['f1']:.4f}")
        logger.info(f"XGBoost Accuracy:  {metrics.get('xgb_accuracy', 0):.4f}")
        logger.info(f"RF Accuracy:       {metrics.get('rf_accuracy', 0):.4f}")
        logger.info(f"Ensemble Accuracy: {metrics.get('ensemble_accuracy', 0):.4f}")
        logger.info("=" * 60)

        logger.info("\nClassification Report:")
        logger.info(metrics['classification_report'])

        logger.info("\nConfusion Matrix:")
        logger.info(f"\n{metrics['confusion_matrix']}")

        logger.info("\nTop 10 Feature Importance:")
        for feat, imp in feature_importance[:10]:
            logger.info(f"  {feat}: {imp:.4f}")

        return {
            'metrics': metrics,
            'feature_importance': feature_importance,
            'best_iteration': getattr(self.xgb_model, 'best_iteration', None)
        }

    def _calculate_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> Dict[str, Any]:
        """
        Model değerlendirme metriklerini hesaplar.

        Args:
            y_true: Gerçek etiketler
            y_pred: Tahmin edilen etiketler

        Returns:
            Dict[str, Any]: Metrikler sözlüğü
        """
        # Mevcut sınıfları dinamik olarak tespit et (volatil coinlerde tüm sınıflar olmayabilir)
        unique_labels = np.unique(np.concatenate([y_true, y_pred]))

        # Temel metrikler (macro average)
        accuracy = accuracy_score(y_true, y_pred)
        precision = precision_score(y_true, y_pred, average='macro', zero_division=0)
        recall = recall_score(y_true, y_pred, average='macro', zero_division=0)
        f1 = f1_score(y_true, y_pred, average='macro', zero_division=0)

        # Sınıf bazlı metrikler
        class_metrics = {}
        for cls in unique_labels:
            class_metrics[f'class_{cls}'] = {
                'precision': precision_score(y_true, y_pred, labels=[cls], average='macro', zero_division=0),
                'recall': recall_score(y_true, y_pred, labels=[cls], average='macro', zero_division=0),
                'f1': f1_score(y_true, y_pred, labels=[cls], average='macro', zero_division=0)
            }

        # Raporlar (dinamik target_names - sadece mevcut sınıflar)
        target_names = [self.class_mapping.get(i, f'Class_{i}') for i in unique_labels]
        report = classification_report(
            y_true,
            y_pred,
            labels=unique_labels,
            target_names=target_names,
            zero_division=0
        )
        conf_matrix = confusion_matrix(y_true, y_pred, labels=unique_labels)

        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'class_metrics': class_metrics,
            'classification_report': report,
            'confusion_matrix': conf_matrix
        }

    def _calculate_feature_importance(self) -> List[Tuple[str, float]]:
        """
        Özellik önemlerini hesaplar (XGBoost'tan).

        Returns:
            List[Tuple[str, float]]: (feature_name, importance) listesi
        """
        if not self.is_trained:
            return []

        importance = self.xgb_model.feature_importances_
        if self.feature_names:
            return sorted(
                zip(self.feature_names, importance),
                key=lambda x: x[1],
                reverse=True
            )
        else:
            return [(f"feature_{i}", imp) for i, imp in enumerate(importance)]

    def get_feature_importance_df(self, top_n: int = 20) -> pd.DataFrame:
        """
        Feature Importance DataFrame'i normalize edilmiş şekilde döner.

        XAI (Açıklanabilir Yapay Zeka) standardı:
        - (Current_Importance / Max_Importance) * 100 formülüyle 0-100% normalize
        - Top N özelliği döner

        Args:
            top_n: Döndürülecek özellik sayısı (default: 20)

        Returns:
            pd.DataFrame: feature_name, importance, importance_pct kolonları
        """
        if not self.is_trained:
            return pd.DataFrame(columns=['feature_name', 'importance', 'importance_pct'])

        importance = self.xgb_model.feature_importances_

        if self.feature_names is None or len(self.feature_names) == 0:
            self.feature_names = [f"feature_{i}" for i in range(len(importance))]

        # Max importance bul (normalizasyon için)
        max_importance = max(importance) if len(importance) > 0 else 1.0

        # DataFrame oluştur
        df = pd.DataFrame({
            'feature_name': self.feature_names,
            'importance': importance,
            # NORMALIZASYON: (Current / Max) * 100
            'importance_pct': (importance / max_importance * 100) if max_importance > 0 else 0
        })

        # En önemli özelliklere göre sırala (azalan)
        df = df.sort_values('importance', ascending=False)

        # Top N özelliği al
        df = df.head(top_n)

        # Yüzdelikleri 2 ondalığa yuvarla
        df['importance_pct'] = df['importance_pct'].round(2)

        logger.debug(f"🧬 [XAI] Feature Importance hesaplandı: {len(df)} özellik, max={max_importance:.4f}")

        return df

    def predict_with_confidence(
        self,
        X: pd.DataFrame
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Ensemble (XGBoost + RF) tahmini yapar ve güven skoru döner.
        Soft Voting kullanır: Her iki modelin olasılıklarının ortalaması alınır.

        PaperTrader için kritik: Dinamik kaldıraç confidence score'a göre
        hesaplanır.

        Args:
            X: Özellikler (tek satır veya DataFrame)

        Returns:
            Tuple: (predictions, confidence_scores, probabilities)
                - predictions: Tahmin edilen sınıflar (0, 1, 2)
                - confidence_scores: Her tahmin için güven skoru (0-1)
                - probabilities: Tüm sınıflar için olasılıklar
        """
        if not self.is_trained:
            raise RuntimeError("Model henüz eğitilmedi!")

        # Her iki modelin olasılıklarını al
        xgb_proba = self.xgb_model.predict_proba(X)
        rf_proba = self.rf_model.predict_proba(X)

        # Soft Voting: Olasılıkların ortalamasını al
        probabilities = (xgb_proba + rf_proba) / 2

        # En yüksek olasılıklı sınıfı al
        predictions = np.argmax(probabilities, axis=1)

        # Güven skoru: Tahmin edilen sınıfın olasılığı
        confidence_scores = np.max(probabilities, axis=1)

        return predictions, confidence_scores, probabilities

    def predict_single(
        self,
        X: pd.DataFrame
    ) -> Dict[str, Any]:
        """
        Tek bir örnek için detaylı tahmin döner.

        Args:
            X: Tek satırlık özellik DataFrame'i

        Returns:
            Dict[str, Any]: Tahmin detayları
        """
        predictions, confidence, probs = self.predict_with_confidence(X)

        pred_class = predictions[0]
        confidence_score = confidence[0]
        class_probs = probs[0]

        result = {
            'prediction': int(pred_class),
            'prediction_label': self.class_mapping.get(pred_class, f'Class_{pred_class}'),
            'confidence': float(confidence_score),
            'confidence_pct': float(confidence_score * 100),
            'probabilities': {
                self.class_mapping.get(i, f'Class_{i}'): float(prob)
                for i, prob in enumerate(class_probs)
            },
            'recommendation': self._get_recommendation(pred_class, confidence_score)
        }

        return result

    def _get_recommendation(
        self,
        prediction: int,
        confidence: float
    ) -> str:
        """
        Tahmin ve güvene göre işlem önerisi üretir (Binary).

        Args:
            prediction: Tahmin edilen sınıf (1: TRADE, 0: HOLD)
            confidence: Güven skoru

        Returns:
            str: İşlem önerisi
        """
        if prediction == 1:
            if confidence >= 0.80:
                return "STRONG_TRADE"
            elif confidence >= 0.65:
                return "TRADE"
            else:
                return "WEAK_TRADE"
        else:
            return "HOLD"

    def save_model(self, model_path: str = "artifacts/models/xgb_model.json", timeframe: str = "1h", tp_multiplier: float = 2.0, sl_multiplier: float = 2.0, time_horizon: int = 10) -> str:
        """
        Ensemble modelleri diske kaydeder.
        XGBoost: JSON formatında
        Random Forest: Joblib (pickle) formatında

        Args:
            model_path: Kayıt yolu (XGBoost için)
            timeframe: Eğitim timeframe'i (metadata için)
            tp_multiplier: Eğitimde kullanılan Take Profit çarpanı
            sl_multiplier: Eğitimde kullanılan Stop Loss çarpanı
            time_horizon: Eğitimde kullanılan Dikey bariyer mum sayısı

        Returns:
            str: Kaydedilen dosya yolu
        """
        if not self.is_trained:
            raise RuntimeError("Model henüz eğitilmedi, kaydedilemez!")

        # Dizin oluştur
        os.makedirs(os.path.dirname(model_path), exist_ok=True)

        # 1. XGBoost modelini kaydet (JSON formatı)
        self.xgb_model.save_model(model_path)

        # 2. Random Forest modelini kaydet (Joblib/Pickle)
        rf_model_path = model_path.replace('.json', '_rf.joblib')
        joblib.dump(self.rf_model, rf_model_path)

        # Metadata'yi kaydet
        metadata_path = model_path.replace('.json', '_metadata.json')
        metadata = {
            'feature_names': self.feature_names,
            'training_metrics': {
                k: float(v) if isinstance(v, (float, np.float64)) else v
                for k, v in self.training_metrics.items()
                if k not in ['classification_report', 'confusion_matrix']
            },
            'class_mapping': self.class_mapping,
            'hyperparameters': {
                'n_estimators': self.n_estimators,
                'max_depth': self.max_depth,
                'learning_rate': self.learning_rate,
                'subsample': self.subsample,
                'colsample_bytree': self.colsample_bytree,
                'min_child_weight': self.min_child_weight,
                'gamma': self.gamma,
                'reg_alpha': self.reg_alpha,
                'reg_lambda': self.reg_lambda,
                'num_class': self.num_class,
                'rf_n_estimators': self.rf_n_estimators,
                'rf_max_depth': self.rf_max_depth,
                'rf_min_samples_split': self.rf_min_samples_split,
                'tp_multiplier': tp_multiplier,
                'sl_multiplier': sl_multiplier,
                'time_horizon': time_horizon
            },
            'model_paths': {
                'xgb': model_path,
                'rf': rf_model_path
            },
            'trained_timeframe': timeframe,
            'trained_at': datetime.now().isoformat()
        }

        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)

        logger.info(f"✅ XGBoost model kaydedildi: {model_path}")
        logger.info(f"✅ Random Forest model kaydedildi: {rf_model_path}")
        logger.info(f"✅ Metadata kaydedildi: {metadata_path}")

        return model_path

    def load_model(self, model_path: str = "artifacts/models/xgb_model.json") -> 'ModelTrainer':
        """
        Diskten ensemble modelleri yükler.

        Args:
            model_path: XGBoost model dosya yolu

        Returns:
            ModelTrainer: Yüklenmiş model ile self
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"XGBoost model dosyası bulunamadı: {model_path}")

        # 1. XGBoost modelini yükle
        self.xgb_model.load_model(model_path)

        # 2. Random Forest modelini yükle
        rf_model_path = model_path.replace('.json', '_rf.joblib')
        if os.path.exists(rf_model_path):
            self.rf_model = joblib.load(rf_model_path)
            logger.info(f"✅ Random Forest model yüklendi: {rf_model_path}")
        else:
            logger.warning(f"⚠️ Random Forest model bulunamadı: {rf_model_path}")

        self.is_trained = True

        # Metadata'yi yükle
        metadata_path = model_path.replace('.json', '_metadata.json')
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            self.feature_names = metadata.get('feature_names')
            self.class_mapping = {
                int(k): v for k, v in metadata.get('class_mapping', {}).items()
            }
            self.training_metrics = metadata.get('training_metrics', {})

            logger.info(f"✅ XGBoost model yüklendi: {model_path}")
            logger.info(f"📊 Özellik sayısı: {len(self.feature_names)}")
        else:
            logger.warning(f"⚠️ Metadata dosyası bulunamadı: {metadata_path}")

        return self

def run_training_pipeline(
    df: pd.DataFrame,
    symbol: str,
    tp_multiplier: float = 2.0,
    sl_multiplier: float = 2.0,
    time_horizon: int = 10,
    train_ratio: float = 0.8,
    timeframe: str = "1h",
    n_estimators: int = 500,
    max_depth: int = 6,
    learning_rate: float = 0.1,
    enable_auto_regularization: bool = True
) -> Dict[str, ModelTrainer]:
    """
    End-to-end Çift Model (Asimetrik) Eğitim Pipeline'ı.

    Aynı DataFrame üzerinden hem 'long' hem de 'short' yönü için
    bağımsız XGBoost+RF ensemble modelleri eğitir ve kaydeder.

    Args:
        df: OHLCV verisi (indikatörlerle birlikte)
        symbol: Sembol (örn: btcusdtusdt)
        tp_multiplier: Take Profit çarpanı
        sl_multiplier: Stop Loss çarpanı
        time_horizon: Dikey bariyer mum sayısı
        train_ratio: Eğitim oranı
        timeframe: Eğitim timeframe'i (metadata için)
        n_estimators: Ağaç sayısı
        max_depth: Maksimum derinlik
        learning_rate: Öğrenme oranı
        enable_auto_regularization: Otomatik regularization aktif mi

    Returns:
        Dict[str, ModelTrainer]: {'long': ModelTrainer, 'short': ModelTrainer}
    """
    from ml.data_prep import prepare_ml_data
    from datetime import datetime
    import os

    logger.info("=" * 60)
    logger.info("XGBOOST ÇİFT MODEL EĞİTİM PIPELINE'I BAŞLATILIYOR (LONG & SHORT)")
    logger.info("=" * 60)

    trainers = {}
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    symbol_clean = symbol.replace('/', '').replace(':', '').replace('-', '').lower()

    for direction in ['long', 'short']:
        logger.info(f"\n[{direction.upper()}] Yönü için pipeline başlıyor...")
        try:
            # 1. Veri hazırlama (Asimetrik Etiketleme)
            logger.info(f"[{direction.upper()}] Veri hazırlanıyor...")
            X_train, X_test, y_train, y_test, ret_train, ret_test, scaler = prepare_ml_data(
                df,
                direction=direction,
                tp_multiplier=tp_multiplier if direction == 'long' else sl_multiplier,
                sl_multiplier=sl_multiplier if direction == 'long' else tp_multiplier,
                time_horizon=time_horizon,
                train_ratio=train_ratio,
                skip_barrier=False
            )

            # 2. Model eğitimi
            logger.info(f"[{direction.upper()}] Model eğitiliyor...")
            trainer = ModelTrainer(
                n_estimators=n_estimators,
                max_depth=max_depth,
                learning_rate=learning_rate,
                subsample=0.8,
                colsample_bytree=0.8,
                time_horizon=time_horizon,
                enable_auto_regularization=enable_auto_regularization
            )

            trainer.train(X_train, y_train, X_test, y_test, ret_test=ret_test)
            trainers[direction] = trainer

            # 3. Model kaydetme
            logger.info(f"[{direction.upper()}] Model kaydediliyor...")
            model_save_path = f"artifacts/models/xgb_model_{symbol_clean}_{timeframe}_{timestamp}_{direction}.json"
            os.makedirs(os.path.dirname(model_save_path), exist_ok=True)

            trainer.save_model(
                model_save_path,
                timeframe=timeframe,
                tp_multiplier=tp_multiplier if direction == 'long' else sl_multiplier,
                sl_multiplier=sl_multiplier if direction == 'long' else tp_multiplier,
                time_horizon=time_horizon
            )
        except Exception as e:
            logger.error(f"[{direction.upper()}] Model eğitimi sırasında hata: {e}")

    logger.info("\n" + "=" * 60)
    logger.info("ÇİFT MODEL EĞİTİMİ TAMAMLANDI")
    logger.info("=" * 60)

    return trainers


if __name__ == "__main__":
    """
    Test scripti: Uçtan uca eğitim pipeline'ını çalıştırır.
    """
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from data.indicators import StrategyIndicators
    from core.database import Database
    import pandas as pd

    logger.info("XGBoost Model Eğitim Testi")
    logger.info("=" * 60)

    try:
        # 1. Veritabanından veri çek
        logger.info("\nVeritabanından veri çekiliyor...")
        db = Database()

        # Örnek: BTC/USDT verisi çek
        df = db.get_klines('BTCUSDT', timeframe='1h', limit=5000)
        db.close()

        if df is None or len(df) == 0:
            logger.error("Veri çekilemedi!")
            sys.exit(1)

        logger.info(f"Çekilen veri: {len(df)} satır")

        # 2. İndikatörleri ekle
        logger.info("\nİndikatörler hesaplanıyor...")
        df = StrategyIndicators.add_all_indicators(df)

        # 3. Eğitim pipeline'ını çalıştır
        logger.info("\nEğitim pipeline'ı başlatılıyor...")
        trainers = run_training_pipeline(
            df,
            symbol="BTCUSDT",
            tp_multiplier=2.0,
            sl_multiplier=2.0,
            time_horizon=10,
            train_ratio=0.8,
            n_estimators=500,
            max_depth=6,
            learning_rate=0.1,
            enable_auto_regularization=False
        )
        trainer = trainers.get('long') # Test için birini seç
        if not trainer:
            raise RuntimeError("LONG model eğitilemedi")

        # 4. Test tahmini
        logger.info("\nTest tahmini yapılıyor...")
        # Son 10 satırı test için kullan
        test_sample = df.iloc[-10:].copy()

        # Özellikleri hazırla (model'in feature_names'ine göre)
        feature_cols = trainer.feature_names
        X_test_sample = test_sample[feature_cols]

        predictions, confidence, probs = trainer.predict_with_confidence(X_test_sample)

        logger.info("\nSon 10 mum tahmini:")
        for i, (pred, conf) in enumerate(zip(predictions, confidence)):
            label = trainer.class_mapping.get(pred, f'Class_{pred}')
            logger.info(f"  Mum {i+1}: {label} (Güven: {conf*100:.1f}%)")

        logger.info("\n" + "=" * 60)
        logger.info("TEST BAŞARILI!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Test başarısız: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
