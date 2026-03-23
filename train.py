import asyncio
import pandas as pd
import numpy as np
import os
import pickle
import traceback

from core.exchange import ExchangeManager
from data.indicators import StrategyIndicators
from data.features import AdvancedFeatures
from models.xgboost_model import XGBoostModel
from core.logger import logger

# Modellerin saklanacağı klasör
MODEL_DIR = "artifacts/trained_models"
os.makedirs(MODEL_DIR, exist_ok=True)

async def download_and_prepare_data(symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"], timeframe="1m", limit=3000):
    """Borsadan tüm pariteler için geçmiş veriyi indirir ve devasa bir eğitim seti (Multi-Asset) oluşturur."""
    all_X = []
    all_y = []
    
    exchange = ExchangeManager()
    
    for symbol in symbols:
        logger.info(f"{symbol} için {limit} mum indiriliyor...")
        try:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            if not ohlcv or len(ohlcv) < 500:
                logger.warning(f"{symbol} için yeterli veri yok, atlanıyor.")
                continue
                
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # İndikatörler ve Özellikler
            df = StrategyIndicators.add_all_indicators(df)
            df['volatility_ema'] = AdvancedFeatures.get_volatility(df['close'], span=20)
            
            # Hedef Etiketleme (Karar)
            df['target'] = AdvancedFeatures.create_target_labels(df, lookahead=5, threshold=0.002)
            
            # ML Kolonları
            feature_cols = [
                'open', 'high', 'low', 'close', 'volume', 
                'SMA_20', 'EMA_50', 'RSI_14', 
                'MACD_12_26_9', 'MACDs_12_26_9', 'MACDh_12_26_9',
                'ATR_14', 'BBU_20_2.0_2.0', 'BBL_20_2.0_2.0', 'VWAP', 'volatility_ema'
            ]
            
            df.dropna(subset=feature_cols + ['target'], inplace=True)
            
            X = df[feature_cols]
            y = df['target'].astype(int)
            
            all_X.append(X)
            all_y.append(y)
            logger.info(f"{symbol} hazır. ({len(df)} temiz mum)")
            
        except Exception as e:
            logger.error(f"{symbol} indirilirken hata: {e}")

    await exchange.close()
    
    if not all_X:
        return None, None
        
    # Tüm pariteleri tek bir devasa veri setinde birleştir (Cross-Asset Training)
    final_X = pd.concat(all_X)
    final_y = pd.concat(all_y)
    
    logger.info(f"TÜM PARİTELER BİRLEŞTİRİLDİ. Toplam Veri: {len(final_X)} Mum.")
    return final_X, final_y

def train_and_save_model(X, y):
    """XGBoost modelini eğitir ve diske kaydeder."""
    logger.info("Çoklu Parite (Multi-Asset) Eğitimi Başlıyor...")
    
    # Karıştırarak eğitim (Shuffling) - Pariteler arası öğrenmeyi güçlendirir
    indices = np.random.permutation(len(X))
    X, y = X.iloc[indices], y.iloc[indices]
    
    split_index = int(len(X) * 0.85)
    X_train, y_train = X.iloc[:split_index], y.iloc[:split_index]
    X_val, y_val = X.iloc[split_index:], y.iloc[split_index:]
    
    xgb_wrapper = XGBoostModel()
    xgb_wrapper.train(X_train, y_train, X_val, y_val, num_boost_round=200)
    
    filepath = os.path.join(MODEL_DIR, "xgb_model.pkl")
    with open(filepath, 'wb') as f:
        pickle.dump(xgb_wrapper, f)
        
    logger.info(f"Süper Model Eğitildi ve Başarıyla Kaydedildi! -> {filepath}")

async def main():
    logger.info("🤖 KRİPTO BOT - ÇOKLU PARİTE EĞİTİM KONSOLU")
    # ETH, SOL ve XRP'yi de dahil eden genişletilmiş eğitim
    X, y = await download_and_prepare_data(
        symbols=["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT"], 
        timeframe="1m", 
        limit=4000
    )
    
    if X is not None:
        train_and_save_model(X, y)
    else:
        logger.error("Hüp! Veri seti oluşturulamadı.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
