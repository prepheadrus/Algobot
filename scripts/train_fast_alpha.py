import asyncio
import os
import sys
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timezone

# Root directory ekle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.logger import logger
from data.database import DatabaseManager
from data.indicators import StrategyIndicators
from ml.model_training import run_training_pipeline

async def fetch_real_data(symbol="BTC/USDT", timeframe="1m", limit=43000):
    """
    Yerel veritabanından (veya Parquet'ten) BTC/USDT 1m verisini çeker.
    Bu test için gerçek veri gereklidir.
    """
    db = DatabaseManager()
    await db.connect()

    # DB'den veri çek (ParquetLake vb. CryptoAlgoBot mimarisinde klines db'de)
    logger.info(f"Veritabanından {symbol} {timeframe} verisi aranıyor (Limit: {limit})...")
    db_klines = await db.get_klines(symbol, timeframe=timeframe, limit=limit)

    await db.close()

    if db_klines:
        logger.info(f"Veritabanından {len(db_klines)} satır veri başarıyla çekildi.")
        df = pd.DataFrame(db_klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        # Timestamp'e göre sırala
        df.sort_values(by='timestamp', ascending=True, inplace=True)
        df.reset_index(drop=True, inplace=True)

        return df
    else:
        logger.error(f"Veritabanında yeterli veri yok. ML testi için lütfen önce veri indiriniz (Frontend üzerinden veya fetch_ohlcv ile).")
        return None

async def main():
    logger.info("==================================================")
    logger.info("🚀 YENİ BEYİN TESTİ: XGBoost Model Retraining (Fast)")
    logger.info("==================================================")

    symbol = "BTCUSDT" # Database format (with or without slashes)
    timeframe = "1m"
    limit = 43000 # Son 30 günlük 1 dakikalık mum sayısı

    # 1. Gerçek veriyi çek
    df = await fetch_real_data(symbol, timeframe, limit)

    if df is None or len(df) == 0:
        logger.error("Veri seti oluşturulamadı, test iptal edildi.")
        return

    logger.info(f"\n[AŞAMA 1] İndikatörler ve Alpha Faktörleri Hesaplanıyor...")
    # 2. İndikatörleri ekle
    df = StrategyIndicators.add_all_indicators(df)

    logger.info(f"\n[AŞAMA 2] XGBoost Modeli Eğitiliyor (Alpha özellikleri devrede)...")
    model_save_path = "artifacts/models/xgb_model_fast_test.json"

    try:
        from ml.data_prep import apply_triple_barrier
        df = apply_triple_barrier(
            df,
            target_col="close",
            tp_multiplier=2.0,
            sl_multiplier=2.0,
            time_horizon=10,
        )

        trainer = run_training_pipeline(
            df,
            model_save_path=model_save_path,
            tp_multiplier=2.0,
            sl_multiplier=2.0,
            time_horizon=10,
            train_ratio=0.8,
            timeframe=timeframe
        )

        metrics = trainer.training_metrics
        feature_importance = trainer.get_feature_importance_df(top_n=15)

        logger.info("\n==================================================")
        logger.info("🎉 EĞİTİM SONUÇLARI & METRİKLER")
        logger.info("==================================================")

        xgb_acc = metrics.get('xgb_accuracy', metrics.get('accuracy', 0))
        f1_score = metrics.get('f1', 0)

        logger.info(f"Target Sembol: {symbol} ({timeframe})")
        logger.info(f"Veri Seti Boyutu: {len(df)} Mum")
        logger.info(f"Model: XGBoost (Yeni Alpha Özellikleri ile)")
        logger.info(f"Accuracy (Doğruluk): % {xgb_acc * 100:.2f}")
        logger.info(f"F1-Score: % {f1_score * 100:.2f}")

        if xgb_acc >= 0.55:
            logger.info("🔥 HEDEF BAŞARI! Accuracy %55'in üzerinde. Eski modeldeki gürültü tamamen silinmiş!")
        else:
            logger.info("⚠️ Accuracy %55'in altında. Parametre optimizasyonuna devam edilebilir.")

        logger.info("\n📊 CLASSIFICATION REPORT")
        logger.info("==================================================")
        if 'classification_report' in metrics:
            # Satır satır logla
            report_lines = metrics['classification_report'].split('\n')
            for line in report_lines:
                if line.strip():
                    logger.info(line)
        else:
            logger.warning("Classification report metriklerde bulunamadı!")

        logger.info("\n🏆 TOP 15 ÖZELLİK ÖNEMİ (FEATURE IMPORTANCE)")
        logger.info("==================================================")

        for index, row in feature_importance.iterrows():
            feat = row['feature'] if 'feature' in row else row['feature_name']
            imp_pct = row['importance'] * 100 if 'importance_pct' not in row else row['importance_pct']

            # Alpha faktörlerini vurgula
            if feat in ['frac_diff_04', 'kalman_ret', 'dist_to_vwap', 'dist_to_ema50', 'bollinger_pct_b']:
                logger.info(f"🌟 {feat:<20} | {imp_pct:>6.2f}% (YENİ ALPHA)")
            else:
                logger.info(f"   {feat:<20} | {imp_pct:>6.2f}%")

        logger.info("==================================================")
        logger.info("TEST BAŞARIYLA TAMAMLANDI!")

    except Exception as e:
        logger.error(f"Eğitim sırasında hata oluştu: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
