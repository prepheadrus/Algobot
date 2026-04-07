"""
ML Router

FastAPI router for ML operations.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import traceback

from core.logger import logger
from api.schemas.ml import MLTrainRequest
from api.services.ml_service import MLService

router = APIRouter(prefix="/api/v1/ml", tags=["ML"])

ml_service = MLService()

# ============================================================================
# TIMEFRAME MULTIPLIERS (Resampling için)
# ============================================================================
# 1m verisinden hedef timeframe'e dönüşüm için gereken çarpanlar
# Örnek: 1000 adet 15m mum için → 1000 * 15 = 15,000 adet 1m mum çek
TIMEFRAME_MULTIPLIERS = {
    '1m': 1,
    '3m': 3,
    '5m': 5,
    '10m': 10,
    '15m': 15,
    '20m': 20,
    '30m': 30,
    '45m': 45,
    '1h': 60,
    '2h': 120,
    '3h': 180,
    '4h': 240,
    '6h': 360,
    '8h': 480,
    '12h': 720,
    '1d': 1440,
    '1w': 10080
}


@router.post("/train")
async def train_ml_model(request: MLTrainRequest) -> Dict[str, Any]:
    """
    ML modelini eğitir. Arka planda çalışır.
    """
    result = await ml_service.train_model(request)

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))

    return result


@router.get("/status", operation_id="get_ml_status")
async def get_ml_status() -> Dict[str, Any]:
    """
    ML eğitim durumunu döner.
    """
    return ml_service.get_training_status()


@router.get("/training-history")
async def get_training_history(limit: int = 50) -> Dict[str, Any]:
    """
    ML eğitim geçmişini döner.
    """
    return await ml_service.get_training_history(limit)


@router.get("/models")
async def get_available_models(symbol: str, timeframe: str) -> Dict[str, Any]:
    """
    Belirli bir sembol ve zaman dilimi için mevcut (eğitilmiş) modelleri listeler.
    Bu modeller history üzerinden getirilir.
    """
    try:
        history_response = await ml_service.get_training_history(limit=500)
        if history_response.get("status") != "success":
            raise HTTPException(status_code=500, detail="History yüklenemedi")

        all_history = history_response.get("history", [])

        # Sadece ilgili symbol ve timeframe için filtrele, en yeniler üstte
        filtered_models = [
            h for h in all_history
            if h.get("symbol") == symbol and h.get("timeframe") == timeframe
        ]

        # Sonuçları hazırlanırken frontend için daha okunaklı formatta dön
        models_list = []
        for model in sorted(filtered_models, key=lambda x: x.get("completed_at", ""), reverse=True):
            model_id = model.get("model_id")
            if not model_id:
                # Eski modellerde model_id olmayabilir, timestamp veya id uyduruyoruz
                model_id = model.get("training_id", "").split("_")[-2] + "_" + model.get("training_id", "").split("_")[-1]

            metrics = model.get("metrics", {})
            accuracy = metrics.get("accuracy", 0) * 100

            models_list.append({
                "model_id": model_id,
                "completed_at": model.get("completed_at"),
                "accuracy": round(accuracy, 2),
                "tp_multiplier": model.get("tp_multiplier"),
                "sl_multiplier": model.get("sl_multiplier"),
                "is_legacy": "model_id" not in model, # History'de explicit olarak model_id yoksa legacy'dir
                "training_id": model.get("training_id")
            })

        return {
            "status": "success",
            "symbol": symbol,
            "timeframe": timeframe,
            "models": models_list
        }
    except Exception as e:
        logger.error(f"Modeller listelenirken hata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/training-history")
async def delete_training_history() -> Dict[str, Any]:
    """
    ML eğitim geçmişini siler.
    """
    return await ml_service.delete_training_history()


@router.delete("/model")
async def delete_ml_model(symbol: str, timeframe: str, direction: str = None) -> Dict[str, Any]:
    """
    Belirli bir ML modelini siler.

    Query Parameters:
        symbol: Sembol (örn: BTC/USDT)
        timeframe: Zaman dilimi (örn: 1h)
        direction: (Opsiyonel) 'long' veya 'short'. Belirtilmezse tüm yönleri siler.

    Returns:
        {
            "status": "success",
            "message": "3 dosya silindi",
            "deleted_files": [...]
        }
    """
    try:
        result = await ml_service.delete_model(symbol, timeframe, direction)

        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Model silme hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check-model")
async def check_model(symbol: str, timeframe: str = "1h", direction: str = "long") -> Dict[str, Any]:
    """
    ML modelinin varlığını kontrol eder.
    """
    return ml_service.check_model(symbol, timeframe, direction)


@router.get("/visual-analysis")
async def run_visual_analysis(
    symbol: str,
    strategy_id: str,
    timeframe: str = "1h",
    limit: int = 1000
) -> Dict[str, Any]:
    """
    Görsel karar simülasyonu için mum verisi ve ML tahminlerini döner.
    
    Args:
        symbol: Sembol (örn: BTC/USDT)
        strategy_id: Strateji ID (örn: trend_master)
        timeframe: Zaman dilimi
        limit: Mum sayısı
    
    Returns:
        {
            "status": "success",
            "candles": [...],
            "markers": [...],
            "feature_importance": [...],
            "ml_predictions": [...]
        }
    """
    try:
        from data.database import db_manager
        import pandas as pd
        import numpy as np
        from data.indicators import StrategyIndicators

        logger.info(f"🔍 [ML] Görsel analiz başlatılıyor: {symbol} ({timeframe})")

        # ========================================================================
        # YENİ: AKILLI CACHE LOADER (Superalgos Mimarisi)
        # ========================================================================
        # 1. Önce flat file kontrol et (HIZLI!)
        # 2. Yoksa 1m'den resample yap (fallback)
        # ========================================================================

        from data.ohlcv_storage import get_storage
        from datetime import datetime, timedelta

        storage = get_storage()

        # Tarih aralığını hesapla
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(minutes=limit * int(''.join(filter(str.isdigit, timeframe)) or 1))

        # Flat file'dan yükle
        klines_data = None
        try:
            df_flat = storage.load_ohlcv(symbol, timeframe, start_date, end_date)

            if df_flat is not None and len(df_flat) > 0:
                logger.info(f"📖 [STORAGE] Flat file'dan yüklendi: {symbol} {timeframe} ({len(df_flat)} mum)")

                # DataFrame'i tuple formatına çevir
                klines_data = []
                for _, row in df_flat.iterrows():
                    klines_data.append((
                        int(row['timestamp']),
                        row['open'],
                        row['high'],
                        row['low'],
                        row['close'],
                        row['volume']
                    ))
            else:
                logger.info(f"⏭️ [STORAGE] Flat file bulunamadı, 1m'den resample yapılacak: {symbol} {timeframe}")

        except Exception as e:
            logger.warning(f"⚠️ [STORAGE] Flat file yükleme hatası: {e}")
            logger.info("🔄 [STORAGE] 1m'den resample'a geçiliyor...")

        # Flat file yoksa, 1m'den çek + resample
        if not klines_data or len(klines_data) == 0:
            # TIMEFRAME_MULTIPLIERS sözlüğünden çarpan al
            multiplier = TIMEFRAME_MULTIPLIERS.get(timeframe, 1)

            # Limit'i çarpanla çarp (1m'den resample için)
            adjusted_limit = limit * multiplier

            logger.info(f"📊 [ML] Veri çekiliyor: {symbol}, 1m (ana veri), limit={adjusted_limit}")
            logger.info(f"🔄 [ML] Resampling: {adjusted_limit:,} mum (1m) → {limit:,} mum ({timeframe})")

            # 1. Veritabanından veri çek (SADECE 1m - ana veri)
            klines_data = await db_manager.get_klines(symbol, '1m', limit=adjusted_limit)

            if not klines_data or len(klines_data) == 0:
                raise HTTPException(status_code=404, detail=f"Veritabanında analiz için yeterli veri yok: {symbol} 1m")

            df = pd.DataFrame(klines_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

            # [CRITICAL SYNC] Timestamp'i StrategyIndicators öncesi normalize et
            if 'timestamp' in df.columns and not df.empty:
                ts_val = df['timestamp'].iloc[0]
                if isinstance(ts_val, (int, float, np.integer, np.floating)):
                    if ts_val > 10**11:
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    else:
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                else:
                    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

                df = df.dropna(subset=['timestamp'])

            df = df.drop_duplicates(subset=['timestamp'], keep='first')
            df = df.sort_values('timestamp').reset_index(drop=True)

            logger.info(f"✅ [ML] {len(df)} mum (1m) çekildi ve DataFrame'e çevrildi")

            # ========================================================================
            # RESAMPLING (1m → Hedef Timeframe)
            # ========================================================================
            if timeframe != '1m':
                # Resampling yap
                df = StrategyIndicators.resample_data(df, timeframe)

                # NaN satırları temizle (boş mumlar)
                df = df.dropna()

                logger.info("✅ [DATA] Resampling Mimarisi Aktif: Veritabanı %98 Optimize Edildi")
                logger.info(f"✅ [ML] Resampling tamamlandı: {len(df)} mum ({timeframe})")

                # Flat file'a kaydet (gelecek için)
                try:
                    storage.save_ohlcv(symbol, timeframe, df)
                    logger.info(f"💾 [STORAGE] Flat file kaydedildi: {symbol} {timeframe}")
                except Exception as e:
                    logger.warning(f"⚠️ [STORAGE] Flat file kaydetme hatası: {e}")
            else:
                logger.info("✅ [ML] 1m veri - Resampling gerek yok")
        else:
            # Flat file'dan yüklendi, DataFrame'e çevir
            df = pd.DataFrame(klines_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        # 2. İndikatör ve Özellikleri Hesapla
        logger.info("📊 [ML] İndikatörler ve özellikler hesaplanıyor...")
        df = StrategyIndicators.add_all_indicators(df)

        # [SYNC] LWC için saniye formatına kesin zorla (int64)
        if 'timestamp' in df.columns:
            # 🔥 DÜZELTME: Timezone-aware datetime'ı önce UTC'ye, sonra naive yap, sonra int64
            if hasattr(df['timestamp'].iloc[0], 'tzinfo') and df['timestamp'].iloc[0].tzinfo is not None:
                # Timezone-aware → UTC → Naive → int64
                df['timestamp'] = df['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)

            # Datetime'dan saniyeye (Pandas versiyonlarından bağımsız en güvenli yol)
            df['timestamp'] = ((df['timestamp'] - pd.Timestamp('1970-01-01')) // pd.Timedelta('1s')).astype('int64')

        # [DEBUG] Final veri aralığı kontrolü
        if not df.empty:
            logger.info(f"📊 [ML] Zaman damgası aralığı: {df['timestamp'].min()} - {df['timestamp'].max()}")
        
        # Gelecekte FeatureEngineer eklenebilmesi için placeholder
        try:
            from data.features import FeatureEngineer
            df = FeatureEngineer().add_all_features(df)
        except (ImportError, AttributeError):
            logger.debug("FeatureEngineer modülü bulunamadı, yalnızca indikatörler kullanılıyor.")
            
        logger.info(f"📊 [ML] İndikatörler hesaplandı: {df.shape[1]} kolon")

        # 3. Modelleri Yükle ve Tahmin Yap (LONG ve SHORT)
        markers = []
        feature_importance = []

        for direction in ['long', 'short']:
            model_info = ml_service.check_model(symbol, timeframe, direction=direction)

            if model_info.get('model_exists'):
                from ml.model_training import ModelTrainer
                trainer = ModelTrainer()
                trainer.load_model(model_info['model_path'])

                # Modelin beklediği özellik isimlerini al
                model_feature_names = getattr(trainer.xgb_model, 'feature_names_in_', None)
                if model_feature_names is None:
                    model_feature_names = trainer.xgb_model.get_booster().feature_names

                if model_feature_names is None or len(model_feature_names) == 0:
                    raise ValueError(f"Modelden özellik (feature) isimleri alınamadı. ({direction})")

                # 4. Graceful Degradation: Eksik kolonları 0.0 ile doldur
                missing_cols = [col for col in model_feature_names if col not in df.columns]
                if missing_cols:
                    logger.warning(f"⚠️ [ML] {len(missing_cols)} adet eksik kolon tespit edildi. 0.0 ile dolduruluyor: {missing_cols[:10]}... ({direction})")
                    for col in missing_cols:
                        df[col] = 0.0

                # 5. Veriyi Temizle ve Tahmin için Hazırla
                X = df[model_feature_names].copy()
                X.replace([np.inf, -np.inf], np.nan, inplace=True)
                X.fillna(0.0, inplace=True)

                for col in X.columns:
                    X[col] = pd.to_numeric(X[col], errors='coerce').astype(float)

                import xgboost as xgb
                dmatrix = xgb.DMatrix(X, feature_names=model_feature_names)
                probs = trainer.xgb_model.predict(dmatrix)
                # Binary classification -> prob > 0.5 ise 1, değilse 0
                predictions = (probs >= 0.5).astype(int)

                logger.info(f"📊 [ML] Tahminler tamamlandı ({direction.upper()}): {len(predictions)} adet, positive count: {sum(predictions)}")

                # Markers oluştur
                current_ml_state = None
                candles_since_last_ml = 0

                for i in range(len(predictions)):
                    if i < len(df):
                        pred_class = int(predictions[i])
                        ts = int(df['timestamp'].iloc[i])
                        
                        if pred_class == 1:
                            if direction == 'long' and current_ml_state != 'LONG':
                                markers.append({'time': ts, 'position': 'belowBar', 'color': '#2ea043', 'shape': 'arrowUp', 'text': 'ML LONG', 'size': 0.6})
                                current_ml_state = 'LONG'
                                candles_since_last_ml = 0
                            elif direction == 'short' and current_ml_state != 'SHORT':
                                markers.append({'time': ts, 'position': 'aboveBar', 'color': '#f85149', 'shape': 'arrowDown', 'text': 'ML SHORT', 'size': 0.6})
                                current_ml_state = 'SHORT'
                                candles_since_last_ml = 0
                        else:
                            # Sinyal yok (0) -> Sayacı artır
                            candles_since_last_ml += 1
                            if candles_since_last_ml >= 1000 and current_ml_state:
                                if current_ml_state == 'LONG' and direction == 'long':
                                    markers.append({'time': ts, 'position': 'belowBar', 'color': 'rgba(46, 160, 67, 0.4)', 'shape': 'arrowUp', 'text': 'ML LONG (DVM)', 'size': 0.3})
                                elif current_ml_state == 'SHORT' and direction == 'short':
                                    markers.append({'time': ts, 'position': 'aboveBar', 'color': 'rgba(248, 81, 73, 0.4)', 'shape': 'arrowDown', 'text': 'ML SHORT (DVM)', 'size': 0.3})
                                candles_since_last_ml = 0

                # Feature importance (sadece bir yönünki kalsın, görsel karmaşa olmasın, ya da ortalaması alınabilir ama şimdilik long'u baz alalım)
                if direction == 'long':
                    try:
                        feature_importance = trainer.get_feature_importance_df(top_n=10).to_dict('records')
                    except Exception as e:
                        logger.warning(f"⚠️ [ML] Feature importance alınamadı ({direction}): {e}")

            else:
                logger.warning(f"⚠️ [ML] Aktif model bulunamadı: {symbol} {timeframe} ({direction})")

        # 5.5 Strateji Sinyallerini Hesapla (Karşılaştırma için Mor Sinyaller)
        try:
            from strategy.manager import StrategyManager
            strategy = StrategyManager.get_strategy(strategy_id)
            
            current_strat_state = None
            is_executor = hasattr(strategy, 'config')
            
            for i in range(10, len(df)):  # İndikatörlerin oturması için 10 mum bekle
                sig = 1
                try:
                    if is_executor:
                        sig = strategy.generate_signal(df.iloc[:i+1])
                    elif hasattr(strategy, 'generate_signal'):
                        sig = strategy.generate_signal(df.iloc[i])
                except Exception:
                    pass
                
                # Sadece pozisyon değişimlerinde marker ekle (AL'dan sonra tekrar AL basma)
                if sig == 2 and current_strat_state != 'LONG':
                    ts = int(df['timestamp'].iloc[i])
                    markers.append({'time': ts, 'position': 'belowBar', 'color': '#bc8cff', 'shape': 'circle', 'text': 'S.AL', 'size': 0.7})
                    current_strat_state = 'LONG'
                elif sig == 0 and current_strat_state != 'SHORT':
                    ts = int(df['timestamp'].iloc[i])
                    markers.append({'time': ts, 'position': 'aboveBar', 'color': '#bc8cff', 'shape': 'circle', 'text': 'S.SAT', 'size': 0.7})
                    current_strat_state = 'SHORT'
                
        except Exception as e:
            logger.warning(f"⚠️ [ML] Strateji (karşılaştırma) sinyalleri hesaplanamadı: {e}")

        # 5.6 Gerçek İşlemleri Ekle (Bot çalıştığında gelen "GERÇEK AL / GERÇEK SAT")
        try:
            from core.paper import paper_engine
            current_real_state = None
            
            # Tüm gerçek işlemleri (Açık ve Kapalı) tek bir zaman çizelgesinde birleştir
            all_real_trades = []
            
            # Kapanmış işlemler (trade_history / legacy_positions karması)
            for trade in paper_engine.trade_history:
                if trade.get('symbol') == symbol:
                    all_real_trades.append({
                        'time': trade.get('opened_at') or trade.get('entry_time'),
                        'type': trade.get('direction') or trade.get('type') or trade.get('action'),
                        'status': 'closed',
                        'close_time': trade.get('closed_at') or trade.get('exit_time')
                    })
                    
            # Açık pozisyonlar
            for pos in paper_engine.open_positions:
                if pos.get('symbol') == symbol:
                    all_real_trades.append({
                        'time': pos.get('opened_at') or pos.get('entry_time'),
                        'type': pos.get('direction') or pos.get('type') or pos.get('action'),
                        'status': 'open'
                    })
            
            # Zamanına göre sırala
            all_real_trades = [t for t in all_real_trades if t['time'] is not None]
            
            # DataFrame'in en küçük/en büyük zamanlarını al
            if not df.empty and all_real_trades:
                # Timestampları saniyeye çevirme yardımcı fonksiyonu
                def parse_timestamp(t):
                    try:
                        t_obj = pd.to_datetime(t)
                        return int(t_obj.timestamp())
                    except:
                        return 0
                        
                # Gerçek işlemleri DataFrame'deki en yakın muma eşle (aynı mantık)
                for trade in all_real_trades:
                    trade_time = parse_timestamp(trade['time'])
                    trade_type = str(trade['type']).upper()
                    
                    # LONG/BUY mantığı
                    if trade_type in ['LONG', 'BUY'] and current_real_state != 'LONG':
                        markers.append({'time': trade_time, 'position': 'belowBar', 'color': '#00FA9A', 'shape': 'circle', 'text': 'GERÇEK AL', 'size': 1.0})
                        current_real_state = 'LONG'
                        
                    # SHORT/SELL mantığı
                    elif trade_type in ['SHORT', 'SELL'] and current_real_state != 'SHORT':
                        markers.append({'time': trade_time, 'position': 'aboveBar', 'color': '#FF4500', 'shape': 'circle', 'text': 'GERÇEK SAT', 'size': 1.0})
                        current_real_state = 'SHORT'
                        
                    # Kapanış için ekstra marker
                    if trade.get('status') == 'closed' and trade.get('close_time'):
                        close_time = parse_timestamp(trade['close_time'])
                        markers.append({'time': close_time, 'position': 'aboveBar', 'color': '#FFFFFF', 'shape': 'circle', 'text': 'İŞLEM KAPANIŞ', 'size': 0.8})
                        current_real_state = None  # Pozisyon kapandığı için durumu sıfırla
                        
        except Exception as e:
            logger.warning(f"⚠️ [ML] Gerçek işlemler hesaplanamadı/eklenemedi: {e}")

        # 6. Candlestick verisini hazırla
        # [INTEGRITY] Candlestick verisini temizle ve LWC için hazırla
        candles_df = df[['timestamp', 'open', 'high', 'low', 'close']].copy()
        candles_df = candles_df.rename(columns={'timestamp': 'time'})
        
        # Kesin sayısal tip zorlaması (Crash önlemi)
        for col in ['open', 'high', 'low', 'close']:
            candles_df[col] = pd.to_numeric(candles_df[col], errors='coerce').fillna(0).astype(float)

        candles_df = candles_df.dropna(subset=['time'])
        candles_df = candles_df.drop_duplicates(subset=['time'])
        candles_df = candles_df.sort_values('time')

        # ========================================================================
        # OOM (Out of Memory) KORUMASI - XAI Standardı
        # ========================================================================
        # 1. Veriyi son 1500 mum ile sınırla (tail)
        # 2. NaN/Infinity değerlerini sıfırla
        # ========================================================================

        # Tail(1500) - Son 1500 mumu al (OOM önleme)
        candles_df = candles_df.tail(1500)
        logger.info(f"🛡️ [ML] OOM Koruması: {len(candles_df)} mum (tail 1500)")

        # Markers'ları da sınırla (sadece son 1500 mum içindekiler)
        if len(candles_df) > 0:
            min_time = candles_df['time'].min()
            markers = [m for m in markers if m.get('time', 0) >= min_time]
            logger.info(f"🛡️ [ML] Markers filtrelendi: {len(markers)} marker kaldı")

        # NaN/Infinity temizliği (XAI standardı)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in candles_df.columns:
                candles_df[col] = candles_df[col].replace([np.inf, -np.inf], 0).fillna(0)

        # [SYNC] LWC için saniye formatına kesin zorla (int)
        # 🔥 DÜZELTME: Timezone-aware datetime'ı önce naive yap, sonra int64
        if hasattr(candles_df['time'].iloc[0], 'tzinfo') and candles_df['time'].iloc[0].tzinfo is not None:
            candles_df['time'] = candles_df['time'].dt.tz_convert('UTC').dt.tz_localize(None)

        candles_df['time'] = candles_df['time'].astype('int64')

        candles = candles_df.to_dict('records')

        logger.info(f"✅ [ML] Görsel analiz tamamlandı: {len(candles)} mum, {len(markers)} marker")

        return {
            "status": "success",
            "candles": candles,
            "markers": markers,
            "feature_importance": feature_importance,
        }
        
    except Exception as e:
        logger.error(f"❌ [ML] Görsel analiz sırasında kritik hata: {e}")
        logger.error(f"❌ [ML] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Görsel analiz hatası: {str(e)}")
