import pandas as pd
import os
from typing import Dict, Any, Tuple, Optional
from core.logger import logger
from core.config import CONFIG


class SignalValidatorService:
    """
    ML Onayı ve HTF Filtrelemeleri gibi karmaşık sinyal onay süreçlerini yönetir.
    """

    def __init__(self, ml_models_cache: dict):
        self.ml_models = ml_models_cache
        self.ml_enabled = True

    async def validate_signal_with_ml(self, symbol: str, timeframe: str, indicators: Dict[str, float], signal: int) -> Tuple[bool, float, str, str]:
        """
        ML modeline danışarak mevcut sinyali onaylar veya reddeder.

        Returns:
            Tuple[is_confirmed (bool), confidence (float), recommendation_original (str), recommendation_normalized (str)]
        """
        ml_confirmed = True
        ml_confidence = 0.5
        ml_rec = "HOLD"
        ml_rec_norm = "HOLD"

        ml_threshold = CONFIG.get('ml', {}).get('confidence_threshold', 0.65)

        if not self.ml_enabled:
            return True, ml_confidence, ml_rec, ml_rec_norm

        ml_data = await self._get_ml_confirmation(symbol, timeframe, indicators)
        if ml_data:
            ml_rec = ml_data.get('recommendation', 'HOLD')
            ml_confidence = ml_data.get('confidence', 0.5)

            # Normalize recommendation
            ml_rec_norm = str(ml_rec).upper()
            if "AL" in ml_rec_norm or "BUY" in ml_rec_norm:
                ml_rec_norm = "LONG"
            elif "SAT" in ml_rec_norm or "SELL" in ml_rec_norm:
                ml_rec_norm = "SHORT"

            # Conflict Resolution
            if signal == 2 and ml_rec_norm == "SHORT":
                logger.info(f"🛡️ [ML FILTER] {symbol} LONG reddedildi: ML zıt yön gösteriyor ({ml_rec_norm}) | Conf: {ml_confidence:.2f}")
                ml_confirmed = False
            elif signal == 0 and ml_rec_norm == "LONG":
                logger.info(f"🛡️ [ML FILTER] {symbol} SHORT reddedildi: ML zıt yön gösteriyor ({ml_rec_norm}) | Conf: {ml_confidence:.2f}")
                ml_confirmed = False
            elif ml_confidence < ml_threshold:
                logger.info(f"🛡️ [ML FILTER] {symbol} reddedildi: ML confidence {ml_confidence:.2f} < threshold {ml_threshold:.2f}")
                ml_confirmed = False
            else:
                logger.info(f"🧠 [ML CONFIRMED] {symbol} | Rec: {ml_rec} | Conf: {ml_confidence:.2f} (threshold: {ml_threshold:.2f})")
        else:
            logger.debug(f"ℹ️ {symbol} için aktif ML modeli bulunamadı, sadece teknik sinyal ile gidiliyor.")

        return ml_confirmed, ml_confidence, ml_rec, ml_rec_norm

    async def _get_ml_confirmation(self, symbol: str, timeframe: str, indicators: Dict[str, float]) -> Optional[Dict[str, Any]]:
        try:
            from ml.model_training import ModelTrainer, get_model_paths
            cache_key = f"{symbol}_{timeframe}"
            model_paths = get_model_paths(symbol, timeframe)
            model_path = model_paths['xgboost_path']

            if not os.path.exists(model_path):
                logger.debug(f"🧠 [ML] XGBoost model bulunamadı: {model_path}")
                return None

            if cache_key in self.ml_models:
                trainer = self.ml_models[cache_key]
            else:
                trainer = ModelTrainer()
                trainer.load_model(model_path)
                self.ml_models[cache_key] = trainer
                logger.info(f"🧠 [ML] Model belleğe yüklendi: {model_path}")

            if not trainer.is_trained or not trainer.feature_names:
                return None

            features = []
            for feat in trainer.feature_names:
                val = indicators.get(feat, None)
                if val is None:
                    val = 0.0
                features.append(float(val))

            X = pd.DataFrame([features], columns=trainer.feature_names)
            prediction = trainer.predict_single(X)
            return prediction
        except Exception:
            logger.warning(f"⚠️ [ML] {symbol}: Model feature uyumsuzluğu - sadece teknik sinyaller kullanılıyor")
            return None

    def validate_htf_trend(self, symbol: str, htf_trends: dict, signal: int) -> bool:
        """
        Yüksek zaman dilimindeki (HTF) trendlere bakarak işlemin geçerliliğini sınar.

        Returns:
            True if signal is valid (not conflicting with HTF), False otherwise.
        """
        if not htf_trends:
            return True

        htf_levels = list(htf_trends.keys())
        if not htf_levels:
            return True

        major_htf = htf_levels[-1]
        major_trend = htf_trends.get(major_htf, 'NEUTRAL')

        if signal == 2 and major_trend == 'BEAR':
            logger.info(f"🛡️ [HTF] {symbol} LONG reddedildi: Major HTF={major_htf} → {major_trend}")
            return False

        elif signal == 0 and major_trend == 'BULL':
            logger.info(f"🛡️ [HTF] {symbol} SHORT reddedildi: Major HTF={major_htf} → {major_trend}")
            return False

        if major_trend != 'NEUTRAL':
            signal_type = "LONG" if signal == 2 else "SHORT"
            logger.debug(f"✅ [HTF] {symbol} Sinyal geçti: {signal_type} | HTF={major_htf}:{major_trend}")

        return True
