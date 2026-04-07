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

    async def validate_signal_with_ml(self, symbol: str, timeframe: str, indicators: Dict[str, float], signal: int, model_id: Optional[str] = None, direction: str = 'long') -> Tuple[bool, float, str, str, bool]:
        """
        ML modeline danışarak mevcut sinyali onaylar veya reddeder.

        Returns:
            Tuple[is_confirmed (bool), confidence (float), recommendation_original (str), recommendation_normalized (str), has_model (bool)]
        """
        ml_confirmed = True
        ml_confidence = 0.0
        ml_rec = "HOLD"
        ml_rec_norm = "HOLD"
        has_model = False

        ml_threshold = CONFIG.get('ml', {}).get('confidence_threshold', 0.65)

        if not self.ml_enabled:
            return True, ml_confidence, ml_rec, ml_rec_norm, has_model

        ml_data = await self._get_ml_confirmation(symbol, timeframe, direction, indicators, model_id)
        if ml_data:
            has_model = True
            # inference_engine binary döndürüyor: 'prediction': 'LONG'/'SHORT' veya 'HOLD'
            ml_rec = ml_data.get('prediction', 'HOLD')
            ml_confidence = ml_data.get('confidence', 0.0)

            # Normalize recommendation
            ml_rec_norm = str(ml_rec).upper()

            # Conflict Resolution
            if signal == 2 and ml_rec_norm != "LONG":
                logger.info(f"🛡️ [ML FILTER] {symbol} LONG reddedildi: ML onay vermedi ({ml_rec_norm}) | Conf: {ml_confidence:.2f}")
                ml_confirmed = False
            elif signal == 0 and ml_rec_norm != "SHORT":
                logger.info(f"🛡️ [ML FILTER] {symbol} SHORT reddedildi: ML onay vermedi ({ml_rec_norm}) | Conf: {ml_confidence:.2f}")
                ml_confirmed = False
            elif ml_confidence < ml_threshold:
                logger.info(f"🛡️ [ML FILTER] {symbol} reddedildi: ML confidence {ml_confidence:.2f} < threshold {ml_threshold:.2f}")
                ml_confirmed = False
            else:
                logger.info(f"🧠 [ML CONFIRMED] {symbol} | Rec: {ml_rec} | Conf: {ml_confidence:.2f} (threshold: {ml_threshold:.2f})")
        else:
            logger.debug(f"ℹ️ {symbol} için aktif ML modeli bulunamadı, sadece teknik sinyal ile gidiliyor.")

        return ml_confirmed, ml_confidence, ml_rec, ml_rec_norm, has_model

    async def _get_ml_confirmation(self, symbol: str, timeframe: str, direction: str, indicators: Dict[str, float], model_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            from ml.inference import get_ml_prediction

            # Cache key yönetimi get_ml_prediction içindeki load_model'e devredildi.
            # get_ml_prediction Asimetrik yapıya uygun parametreleri alıyor.
            prediction = get_ml_prediction(symbol, timeframe, direction, indicators)

            return prediction
        except Exception as e:
            logger.warning(f"⚠️ [ML] {symbol}: Tahmin sırasında hata - sadece teknik sinyaller kullanılıyor: {e}")
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
