"""
ML Service

Business logic for ML operations.
"""

from typing import Dict, Any
import os
import json
import asyncio
import traceback
from datetime import datetime, timedelta

from core.logger import logger
from api.schemas.ml import MLTrainRequest


class MLService:
    """
    ML Service.

    Business logic for ML operations:
    - Train model
    - Get training status
    - Get training history
    - Check model
    """

    def __init__(self):
        self.training_state = {
            "is_training": False,
            "progress": 0,
            "message": "",
            "current_step": ""
        }
        self.training_history = []

    async def train_model(self, request: MLTrainRequest) -> Dict[str, Any]:
        """
        ML model eğit.

        Args:
            request: ML eğitim isteği

        Returns:
            Eğitim yanıtı (BEKLEYEN - training bitene kadar dönmez)
        """
        if self.training_state["is_training"]:
            return {
                "status": "error",
                "message": "Eğitim zaten devam ediyor, lütfen bekleyin."
            }

        # ÖNEMLİ: Arka plan görevi olarak başlatma - BEKLE!
        # Kullanıcı UI'da "tamamlandı" görmeden eğitim bitsin
        return await self._run_training(request)

    async def _run_training(self, request: MLTrainRequest):
        """Arka planda ML modelini eğitir. YENİ: Resampling mimarisi ile."""
        start_time = datetime.now()
        try:
            self.training_state["is_training"] = True
            self.training_state["progress"] = 5
            self.training_state["message"] = "Veri çekiliyor..."
            self.training_state["current_step"] = "Parquet Lake + Smart Cache"

            logger.info(f"🧠 [ML] Eğitim başlatılıyor: {request.symbol} ({request.timeframe}) - {request.limit} mum")

            # ========================================================================
            # 🏗️ PARQUET DATA LAKE - SMART CACHE
            # ========================================================================
            # 1. Önce Parquet gölünden yükle (vektörize okuma)
            # 2. Eksik varsa SQLite'dan tamamla (1m + resample)
            # 3. UTC timezone sync + NaN temizliği (Infinity koruması)
            # ========================================================================

            from api.services.data_service import DataService
            import pytz

            data_service = DataService()

            # Tarih aralığı hesapla - KULLANICI LIMIT'İNE GÖRE
            # 1m timeframe için: limit * 1 dakika
            # Kullanıcı 100K mum istiyorsa, tam olarak 100K mum çek
            end_date = datetime.now(tz=pytz.UTC)

            # Timeframe'e göre dakika hesaplama
            tf_minutes = {
                '1m': 1, '3m': 3, '5m': 5, '10m': 10, '15m': 15,
                '20m': 20, '30m': 30, '45m': 45, '1h': 60, '2h': 120,
                '3h': 180, '4h': 240, '6h': 360, '8h': 480, '12h': 720,
                '1d': 1440, '1w': 10080
            }
            minutes_per_candle = tf_minutes.get(request.timeframe, 1)

            # İstenen mum sayısı kadar geriye git
            total_minutes = request.limit * minutes_per_candle
            start_date = end_date - timedelta(minutes=total_minutes)

            logger.info(f"🏗️ [PARQUET LAKE] {request.symbol} {request.timeframe} için veri yükleniyor...")
            logger.info(f"📅 [TIME RANGE] {start_date} - {end_date} ({request.limit} mum, ~{total_minutes} dakika)")

            # SMART CACHE köprü fonksiyonu
            df = await data_service.get_cached_or_fetch_data(
                symbol=request.symbol,
                timeframe=request.timeframe,
                start_date=start_date,
                end_date=end_date
            )

            if df is None or len(df) == 0:
                raise ValueError(f"Parquet Lake'te yeterli veri yok: {request.symbol} {request.timeframe}")

            # DataFrame'i ML formatına hazırla
            import pandas as pd

            # Güvenlik: Eğer index DatetimeIndex değilse ve 'timestamp' kolonu varsa index yap
            if not isinstance(df.index, pd.DatetimeIndex):
                if 'timestamp' in df.columns:
                    logger.info(f"🔄 [ML] Index DatetimeIndex değil ({type(df.index)}), 'timestamp' kolonu index yapılıyor...")
                    df.set_index('timestamp', inplace=True)
                else:
                    logger.warning("⚠️ [ML] Index DatetimeIndex değil ve 'timestamp' kolonu bulunamadı!")

            # UTC timezone kontrolü (leakage koruması)
            if df.index.tz is None:
                df.index = df.index.tz_localize('UTC')
            elif df.index.tz != pytz.UTC:
                df.index = df.index.tz_convert('UTC')

            # NaN/Infinity temizliği (XGBoost crash koruması)
            df = df.replace([float('inf'), float('-inf')], float('nan'))
            df = df.ffill().dropna(how='all')

            # ⚠️ ÖNEMLİ: Kullanıcı limit'ini uygula
            # Data service fazla veri dönmüş olabilir, son N mumu al
            if len(df) > request.limit:
                logger.info(f"✂️ [LIMIT] {len(df)} mum bulundu, son {request.limit} mum kullanılıyor")
                df = df.tail(request.limit)

            logger.info(f"✅ [PARQUET LAKE] {request.symbol} {request.timeframe} → {len(df)} mum yüklendi (limit: {request.limit})")
            logger.info(f"📊 [PARQUET LAKE] İlk: {df.index[0]}, Son: {df.index[-1]}")
            logger.info("🛡️ [ML] NaN temizliği: UTC sync + ffill + dropna uygulandı")

            # Final log
            logger.info("🎉 [DATA LAKE] Parquet Engine'e Tam Geçiş Sağlandı ve Risk Kalkanları Aktif")
            
            self.training_state["progress"] = 30
            self.training_state["message"] = "Feature engineering ve etiketleme yapılıyor..."
            self.training_state["current_step"] = "ML pipeline"
            
            logger.info(
                f"📊 [ML] ML pipeline başlatılıyor... | "
                f"TP={request.tp}, SL={request.sl}, Horizon={request.time_horizon}, "
                f"n_estimators={request.n_estimators}, max_depth={request.max_depth}"
            )
            
            # KESİN LOG - API DEĞERLERİ
            logger.info(f"API ALDI: TP={request.tp}, SL={request.sl}, Horizon={request.time_horizon}, Est={request.n_estimators}, Depth={request.max_depth}")

            # 1.5 İndikatörleri ve özelliklerini ekle
            logger.info("📊 [ML] İndikatörler ve Alpha Faktörleri Hesaplanıyor...")
            from data.indicators import StrategyIndicators
            df = StrategyIndicators.add_all_indicators(df)

            try:
                from data.features import FeatureEngineer
                df = FeatureEngineer().add_all_features(df)
            except (ImportError, AttributeError):
                logger.debug("FeatureEngineer modülü bulunamadı, yalnızca indikatörler kullanılıyor.")

            from ml.data_prep import prepare_ml_data
            from ml.model_training import ModelTrainer
            from ml.inference import get_model_paths

            # Argümanları explicitly olarak bir değişkene atayalım ve öyle gönderelim (zincirleme garantisi)
            tp_val = float(request.tp)
            sl_val = float(request.sl)
            hz_val = int(request.time_horizon)

            self.training_state["progress"] = 70
            self.training_state["message"] = "LONG ve SHORT modelleri eğitiliyor..."
            self.training_state["current_step"] = "Dual Model training"

            # Model ID olarak geçerli timestamp'i kullan
            model_id = datetime.now().strftime('%Y%m%d_%H%M%S')
            symbol_clean = request.symbol.replace('/', '').replace(':', '').replace('-', '').lower()

            directions = ['long', 'short']
            all_metrics = {}

            # Modeli eğit (Event-Loop bloklanmasını engellemek için asyncio.to_thread kullanılır)
            def _train_direction(current_direction):
                logger.info(f"🧠 [ML] {current_direction.upper()} modeli için asimetrik eğitim başlatılıyor...")

                # Veri hazırlığında yönü belirt
                X_train, X_test, y_train, y_test, ret_train, ret_test, scaler = prepare_ml_data(
                    df,
                    direction=current_direction,
                    tp_multiplier=tp_val if current_direction == 'long' else sl_val,
                    sl_multiplier=sl_val if current_direction == 'long' else tp_val,
                    time_horizon=hz_val,
                    skip_barrier=False,
                    train_ratio=0.8
                )

                trainer = ModelTrainer(
                    n_estimators=request.n_estimators,
                    max_depth=request.max_depth,
                    learning_rate=request.learning_rate,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    enable_auto_regularization=False
                )

                trainer.train(X_train, y_train, X_test, y_test, ret_test=ret_test)

                model_save_path = f"artifacts/models/xgb_model_{symbol_clean}_{request.timeframe}_{model_id}_{current_direction}.json"
                os.makedirs(os.path.dirname(model_save_path), exist_ok=True)

                trainer.save_model(
                    model_save_path,
                    timeframe=request.timeframe,
                    tp_multiplier=tp_val if current_direction == 'long' else sl_val,
                    sl_multiplier=sl_val if current_direction == 'long' else tp_val,
                    time_horizon=hz_val
                )
                return trainer, X_train.shape[0] + X_test.shape[0]

            for current_direction in directions:
                try:
                    trainer, dataset_size = await asyncio.to_thread(_train_direction, current_direction)

                    if hasattr(trainer, 'training_metrics'):
                        all_metrics[current_direction] = trainer.training_metrics

                    model_paths = get_model_paths(request.symbol, request.timeframe, current_direction, model_id=model_id)
                    feature_count = len(trainer.feature_names) if hasattr(trainer, 'feature_names') and trainer.feature_names else 0

                    # 7. Eğitim geçmişini güncelle (her başarılı yön için ayrı ayrı kaydedilir)
                    self.training_state["progress"] = 80 if current_direction == 'long' else 95
                    self.training_state["message"] = f"{current_direction.upper()} modeli geçmişi güncelleniyor..."
                    self.training_state["current_step"] = "Update history"

                    await self._save_training_history(
                        request,
                        model_paths['xgboost_path'],
                        dataset_size,
                        feature_count,
                        {'metrics': trainer.training_metrics},
                        start_time,
                        model_id=model_id,
                        direction=current_direction
                    )
                    logger.info(f"✅ [ML] {current_direction.upper()} modeli başarıyla eğitildi ve kaydedildi.")
                except Exception as e:
                    logger.warning(f"⚠️ [ML] {current_direction.upper()} modeli eğitimi başarısız oldu (Hata: {e}). Diğer yön için devam ediliyor...")
                    continue

            if not all_metrics:
                raise ValueError("Her iki yön için de model eğitimi başarısız oldu.")

            logger.info("✅ [ML] Çift Yönlü Modeller Eğitildi (Fail-Fast olmadan)")

            # 8. Tamamlandı
            self.training_state["is_training"] = False
            self.training_state["progress"] = 100
            self.training_state["message"] = f"✅ ML eğitimi tamamlandı: {request.symbol}"
            self.training_state["current_step"] = "Completed"

            logger.info(f"🎉 [ML] Eğitim başarıyla tamamlandı: {request.symbol}")

            # ⚠️ ÖNEMLİ: Tüm NumPy tiplerini Python native tiplerine çevir (Pydantic JSON serialization)
            import numpy as np

            def convert_numpy_types(obj):
                """Recursively convert numpy types to native Python types."""
                if isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif isinstance(obj, (np.int8, np.int16, np.int32, np.int64, np.integer)):
                    return int(obj)
                elif isinstance(obj, (np.float16, np.float32, np.float64, np.floating)):
                    return float(obj)
                elif isinstance(obj, dict):
                    return {k: convert_numpy_types(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [convert_numpy_types(item) for item in obj]
                return obj

            metrics_for_response = convert_numpy_types(all_metrics)

            # Başarı yanıtı dön
            return {
                "status": "success",
                "message": f"ML modelleri (Long & Short) eğitildi ({request.symbol})",
                "metrics": metrics_for_response,
                "dataset_size": len(df),
                "accuracy": float(all_metrics.get('long', {}).get('accuracy', 0) * 100) if 'long' in all_metrics else 0.0
            }

        except Exception as e:
            logger.error(f"❌ [ML] Eğitim hatası: {e}")
            logger.error(f"❌ [ML] Traceback: {traceback.format_exc()}")
            self.training_state["is_training"] = False
            self.training_state["message"] = f"Hata: {str(e)}"
            self.training_state["current_step"] = "Error"

            # Hata yanıtı dön
            return {
                "status": "error",
                "message": str(e)
            }

    async def _save_training_history(self, request: MLTrainRequest, model_path: str, dataset_size: int, feature_count: int, training_metrics: dict = None, start_time: datetime = None, model_id: str = None, direction: str = 'long'):
        """Eğitim geçmişini kaydet."""
        try:
            history_file = "artifacts/ml_training_history.json"

            # Blocking I/O operations for reading/writing history
            def _load_history():
                if os.path.exists(history_file):
                    with open(history_file, 'r') as f:
                        return json.load(f)
                return []

            def _save_history(data):
                os.makedirs("artifacts", exist_ok=True)
                with open(history_file, 'w') as f:
                    json.dump(data, f, indent=2)

            # Training metrics'den TÜM metrikleri al
            accuracy = 0.0
            precision = 0.0
            recall = 0.0
            f1_score = 0.0
            xgb_accuracy = 0.0
            rf_accuracy = 0.0
            ensemble_accuracy = 0.0

            if training_metrics:
                # metrics dict'unun iç yapısını kullan
                metrics = training_metrics.get('metrics', {})
                accuracy = float(metrics.get('accuracy', 0.0))
                precision = float(metrics.get('precision', 0.0))
                recall = float(metrics.get('recall', 0.0))
                f1_score = float(metrics.get('f1', 0.0))
                xgb_accuracy = float(metrics.get('xgb_accuracy', accuracy))
                rf_accuracy = float(metrics.get('rf_accuracy', accuracy))
                ensemble_accuracy = float(metrics.get('ensemble_accuracy', accuracy))

            # Duration hesapla
            completed_at = datetime.now()
            started_at = start_time if start_time else completed_at
            duration_seconds = (completed_at - started_at).total_seconds()

            # Yeni kayıt - TÜM METRKLERİ KAYDET
            training_id_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_entry = {
                "training_id": f"{request.symbol}_{request.timeframe}_{direction}_{training_id_timestamp}",
                "model_id": model_id if model_id else training_id_timestamp,
                "symbol": request.symbol,
                "timeframe": request.timeframe,
                "direction": direction,
                "model_type": request.model_type,
                "dataset_size": dataset_size,
                "feature_count": feature_count,
                "tp_multiplier": float(request.tp),
                "sl_multiplier": float(request.sl),
                "time_horizon": int(request.time_horizon),
                "n_estimators": int(request.n_estimators),
                "max_depth": int(request.max_depth),
                "learning_rate": float(request.learning_rate),
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "duration_seconds": duration_seconds,
                "metrics": {
                    "accuracy": accuracy,
                    "precision": precision,
                    "recall": recall,
                    "f1": f1_score,
                    "xgb_accuracy": xgb_accuracy,
                    "rf_accuracy": rf_accuracy,
                    "ensemble_accuracy": ensemble_accuracy
                },
                "model_path": model_path
            }

            # Mevcut geçmişi yükle (Asyncio to thread ile bloklanmayı engelle)
            history = await asyncio.to_thread(_load_history)

            # Yeni kaydı ekle
            history.append(new_entry)

            # Son 100 kaydı sakla
            history = history[-100:]

            # Kaydet (Asyncio to thread ile bloklanmayı engelle)
            await asyncio.to_thread(_save_history, history)

            logger.info(f"📝 [ML] Eğitim geçmişi güncellendi: {len(history)} kayıt")
            logger.info(f"📊 [ML] Metrics kaydedildi: Acc={accuracy:.4f}, Prec={precision:.4f}, Rec={recall:.4f}, F1={f1_score:.4f}")
            logger.info(f"📊 [ML] Model Acc: XGB={xgb_accuracy:.4f}, RF={rf_accuracy:.4f}, Ens={ensemble_accuracy:.4f}")

        except Exception as e:
            logger.error(f"❌ [ML] Geçmiş kaydetme hatası ({direction}): {e}")
            logger.error(f"❌ [ML] Traceback: {traceback.format_exc()}")

    def get_training_status(self) -> Dict[str, Any]:
        """
        Eğitim durumunu al.

        Returns:
            Eğitim durumu
        """
        return {
            "status": "success",
            **self.training_state
        }

    async def get_training_history(self, limit: int = 50) -> Dict[str, Any]:
        """
        Eğitim geçmişini al.

        Args:
            limit: Maksimum kayıt sayısı

        Returns:
            Eğitim geçmişi
        """
        try:
            history_file = "artifacts/ml_training_history.json"

            def _load_history():
                if os.path.exists(history_file):
                    with open(history_file, 'r') as f:
                        return json.load(f)
                return None

            history = await asyncio.to_thread(_load_history)

            if history is not None:
                return {
                    "status": "success",
                    "history": history[-limit:],
                    "total": len(history)
                }

            return {
                "status": "success",
                "history": [],
                "total": 0
            }

        except Exception as e:
            logger.error(f"Eğitim geçmişi hatası: {e}")
            return {"status": "error", "message": str(e)}

    async def delete_training_history(self) -> Dict[str, Any]:
        """
        Eğitim geçmişini sil.

        Returns:
            Silme yanıtı
        """
        try:
            history_file = "artifacts/ml_training_history.json"

            def _delete_history():
                if os.path.exists(history_file):
                    os.remove(history_file)
                    return True
                return False

            if await asyncio.to_thread(_delete_history):
                self.training_history = []

            return {"status": "success", "message": "Geçmiş silindi"}

        except Exception as e:
            logger.error(f"Geçmiş silme hatası: {e}")
            return {"status": "error", "message": str(e)}

    async def delete_model(self, symbol: str, timeframe: str, direction: str = None) -> Dict[str, Any]:
        """
        Belirli bir ML modelini sil. (Tüm yönleri siler veya belirtilen yönü)

        Args:
            symbol: Sembol (örn: BTC/USDT)
            timeframe: Zaman dilimi (örn: 1h)
            direction: (Opsiyonel) 'long' veya 'short'. Belirtilmezse tümünü siler.

        Returns:
            Silme yanıtı
        """
        try:
            import glob

            # Tüm yön dosyalarını bulmak için wildcard pattern
            symbol_clean = symbol.replace('/', '').replace(':', '').replace('-', '').lower()

            if direction:
                search_pattern = f"artifacts/models/xgb_model_{symbol_clean}_{timeframe}_*_{direction}.*"
            else:
                search_pattern = f"artifacts/models/xgb_model_{symbol_clean}_{timeframe}_*.*"

            files_to_delete = glob.glob(search_pattern)

            def _delete_files_sync():
                dfiles = []
                errs = []
                for file_path in files_to_delete:
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            dfiles.append(file_path)
                        except Exception as e:
                            errs.append(f"{file_path}: {str(e)}")
                return dfiles, errs

            # Silinecek dosyalar (Asyncio to thread)
            deleted_files, errors = await asyncio.to_thread(_delete_files_sync)
            for df_path in deleted_files:
                logger.info(f"✅ [ML] Model dosyası silindi: {df_path}")
            for err in errors:
                logger.error(f"❌ [ML] Dosya silme hatası: {err}")

            # Training history'den de sil (eğer varsa)
            history_deleted = False

            def _update_history_sync():
                h_deleted = False
                history_file = "artifacts/ml_training_history.json"
                if os.path.exists(history_file):
                    with open(history_file, 'r') as f:
                        history = json.load(f)

                    # Bu modele ait kayıtları filtrele
                    original_count = len(history)
                    history = [
                        h for h in history
                        if not (h.get('symbol') == symbol and h.get('timeframe') == timeframe)
                    ]

                    if len(history) < original_count:
                        # Güncellenmiş history'yi kaydet
                        with open(history_file, 'w') as f:
                            json.dump(history, f, indent=2)
                        h_deleted = True
                return h_deleted

            try:
                history_deleted = await asyncio.to_thread(_update_history_sync)
                if history_deleted:
                    logger.info(f"✅ [ML] Training history güncellendi (ilgili kayıtlar silindi)")
            except Exception as e:
                logger.warning(f"⚠️ [ML] Training history silme hatası: {e}")

            if deleted_files or history_deleted:
                return {
                    "status": "success",
                    "message": f"{len(deleted_files)} dosya ve {len([h for h in history if h.get('symbol') == symbol and h.get('timeframe') == timeframe])} history kaydı silindi" if history_deleted else f"{len(deleted_files)} dosya silindi",
                    "deleted_files": deleted_files,
                    "errors": errors if errors else None
                }
            else:
                return {
                    "status": "error",
                    "message": "Silinecek dosya bulunamadı",
                    "errors": errors
                }

        except Exception as e:
            logger.error(f"Model silme hatası: {e}")
            return {"status": "error", "message": str(e)}

    def check_model(self, symbol: str, timeframe: str, direction: str = 'long') -> Dict[str, Any]:
        """
        Belirli yöndeki model varlığını kontrol et. (Varsayılan: long)

        Args:
            symbol: Sembol
            timeframe: Zaman dilimi
            direction: Yön ('long' veya 'short')

        Returns:
            Model kontrol yanıtı
        """
        import glob
        symbol_clean = symbol.replace('/', '').replace(':', '').replace('-', '').lower()
        search_pattern = f"artifacts/models/xgb_model_{symbol_clean}_{timeframe}_*_{direction}.json"
        matching_files = glob.glob(search_pattern)

        if matching_files:
            latest_file = sorted(matching_files)[-1]
            rf_file = latest_file.replace('.json', '_rf.joblib')
            meta_file = latest_file.replace('.json', '_metadata.json')

            xgb_exists = os.path.exists(latest_file)
            rf_exists = os.path.exists(rf_file)
            metadata_exists = os.path.exists(meta_file)

            return {
                "status": "success",
                "model_exists": xgb_exists,
                "model_path": latest_file,
                "message": f"{direction.upper()} Model bulundu",
                "ensemble_status": {
                    "xgboost": xgb_exists,
                    "random_forest": rf_exists,
                    "metadata": metadata_exists,
                    "full_ensemble": xgb_exists and rf_exists and metadata_exists
                }
            }

        return {
            "status": "success",
            "model_exists": False,
            "model_path": None,
            "message": f"{direction.upper()} Model bulunamadı",
            "ensemble_status": {
                "xgboost": False,
                "random_forest": False,
                "metadata": False,
                "full_ensemble": False
            }
        }
