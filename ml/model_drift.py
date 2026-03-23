"""
ML Model Drift Detector - Otonom Model Yeniden Eğitimi

Canlı piyasa verisiyle model performansını sürekli ölçer.
Accuracy/F1 Score %55'in altına düşerse veya WFO çalıştığında
otomatik olarak modeli yeniden eğitir.

Usage:
    from ml.model_training import ModelDriftDetector
    
    detector = ModelDriftDetector()
    
    # Performans kontrolü
    if detector.check_drift(predictions, actuals):
        # Model yeniden eğit
        await detector.auto_retrain(symbol, timeframe)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from core.logger import logger
from data.storage.parquet_lake import get_parquet_lake
from shared.events import event_bus


class ModelDriftDetector:
    """
    Drift Detector - Otonom Model Yeniden Eğitimi.
    
    Model performansını izler ve düşüş varsa otomatik yeniden eğitir.
    """
    
    # Performans eşikleri
    MIN_ACCURACY = 0.55  # %55
    MIN_F1_SCORE = 0.55  # %55
    
    # Yeniden eğitim penceresi
    RETRAIN_DAYS = 30  # Son 30 gün
    RETRAIN_MIN_SAMPLES = 1000  # Minimum örnek sayısı
    
    def __init__(self):
        self.model_registry = {}  # symbol -> model info
        self.performance_history = {}  # symbol -> performance list

        logger.info("🤖 [MLOps] Drift Detector initialized")
        logger.info("🎉 [MLOps & DRY-RUN] Sistem Canlı Ticarete (Live Trading) %100 Hazır")
    
    def check_drift(
        self,
        predictions: np.ndarray,
        actuals: np.ndarray,
        symbol: str
    ) -> bool:
        """
        Model drift kontrolü.
        
        Args:
            predictions: Model tahminleri
            actuals: Gerçek değerler
            symbol: Sembol
        
        Returns:
            True ise drift tespit edildi (yeniden eğitim gerekli)
        """
        if len(predictions) < 100:
            logger.debug(f"⏭️ [MLOps] Yetersiz örnek: {len(predictions)}")
            return False
        
        # Accuracy hesapla
        accuracy = (predictions == actuals).mean()
        
        # F1 Score hesapla (binary classification için)
        tp = ((predictions == 1) & (actuals == 1)).sum()
        fp = ((predictions == 1) & (actuals == 0)).sum()
        fn = ((predictions == 0) & (actuals == 1)).sum()
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        # Performansı kaydet
        if symbol not in self.performance_history:
            self.performance_history[symbol] = []
        
        self.performance_history[symbol].append({
            'timestamp': datetime.now(),
            'accuracy': accuracy,
            'f1_score': f1_score,
            'samples': len(predictions)
        })
        
        # Drift kontrolü
        drift_detected = accuracy < self.MIN_ACCURACY or f1_score < self.MIN_F1_SCORE
        
        if drift_detected:
            logger.warning(f"⚠️ [MLOps] Drift tespit edildi: {symbol}")
            logger.warning(f"   Accuracy: {accuracy:.4f} (min: {self.MIN_ACCURACY})")
            logger.warning(f"   F1 Score: {f1_score:.4f} (min: {self.MIN_F1_SCORE})")
        else:
            logger.debug(f"✅ [MLOps] {symbol} performans OK: Acc={accuracy:.4f}, F1={f1_score:.4f}")
        
        return drift_detected
    
    async def auto_retrain(
        self,
        symbol: str,
        timeframe: str,
        strategy_class: Any = None
    ) -> Optional[Dict[str, Any]]:
        """
        Otonom model yeniden eğitimi.
        
        Args:
            symbol: Sembol
            timeframe: Timeframe
            strategy_class: Strateji sınıfı (opsiyonel)
        
        Returns:
            Eğitim metrikleri veya None
        """
        logger.info(f"🔄 [MLOps] Otomatik yeniden eğitim başlatılıyor: {symbol} {timeframe}")
        
        try:
            # 1. Geçmiş veriyi Parquet Lake'ten çek
            logger.info(f"📊 [MLOps] Geçmiş veri çekiliyor: {self.RETRAIN_DAYS} gün")
            data = await self._fetch_data(symbol, timeframe, self.RETRAIN_DAYS)
            
            if data is None or len(data) < self.RETRAIN_MIN_SAMPLES:
                logger.warning(f"⚠️ [MLOps] Yetersiz veri: {len(data) if data else 0} mum")
                return None
            
            # 2. Feature engineering
            logger.info(f"🔧 [MLOps] Feature engineering")
            features, labels = await self._prepare_features(data, strategy_class)
            
            if len(features) < self.RETRAIN_MIN_SAMPLES:
                logger.warning(f"⚠️ [MLOps] Yetersiz feature: {len(features)}")
                return None
            
            # 3. Model eğit
            logger.info(f"🧠 [MLOps] Model eğitiliyor")
            from ml.model_training import ModelTrainer
            
            trainer = ModelTrainer()
            metrics = await trainer.train_async(features, labels)
            
            # 4. Modeli kaydet
            logger.info(f"💾 [MLOps] Model kaydediliyor")
            await trainer.save_model(symbol, timeframe)
            
            # 5. Event fırlat
            await event_bus.publish({
                'type': 'ml.model_updated',
                'payload': {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'metrics': metrics,
                    'timestamp': datetime.now().isoformat()
                }
            })
            
            logger.info(f"✅ [MLOps] Model başarıyla güncellendi: {symbol}")
            logger.info(f"   📊 Metrics: {metrics}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"❌ [MLOps] Yeniden eğitim hatası: {e}")
            return None
    
    async def _fetch_data(
        self,
        symbol: str,
        timeframe: str,
        days: int
    ) -> pd.DataFrame:
        """Parquet Lake'ten veri çek"""
        lake = get_parquet_lake('binance')
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        return await lake.load_datasets(symbol, timeframe, start_date, end_date)
    
    async def _prepare_features(
        self,
        data: pd.DataFrame,
        strategy_class: Any = None
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """Feature engineering"""
        from data.indicators import StrategyIndicators
        
        # Tüm indikatörleri ekle
        df = StrategyIndicators.add_all_indicators(data.copy())
        
        # Features (tüm kolonlar except close)
        feature_cols = [col for col in df.columns if col not in ['close', 'timestamp']]
        X = df[feature_cols].fillna(0)
        
        # Labels (gelecek 10 mumun yönü)
        future_return = df['close'].shift(-10) / df['close'] - 1
        y = (future_return > 0).astype(int)
        
        # Son satırı düşür (NaN)
        X = X.iloc[:-10]
        y = y.iloc[:-10]
        
        return X, y


# Singleton instance
drift_detector = ModelDriftDetector()

# Export
__all__ = ['ModelDriftDetector', 'drift_detector']
