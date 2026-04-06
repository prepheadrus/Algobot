"""
Strategy Builder API Endpoints
Frontend'den gelen strateji oluşturma isteklerini işler.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import json
import os
from datetime import datetime
from cachetools import TTLCache
import traceback

from strategy.builder import StrategyBuilder, StrategyValidator
from api.routers.backtest import fetch_real_data, calculate_signals
from core.backtester import VectorizedBacktester
from core.logger import logger

# API Rate limitleri ve DB yorgunluğunu önlemek için 1 saatlik (3600 sn), maks 10 verilik önbellek
real_data_cache = TTLCache(maxsize=10, ttl=3600)

async def get_cached_real_data(symbol: str, timeframe: str, days: int = 30):
    cache_key = f"{symbol}_{timeframe}_{days}"
    if cache_key in real_data_cache:
        return real_data_cache[cache_key]

    # Cache'te yoksa gerçek datayı çek
    df = await fetch_real_data(symbol, timeframe, days)
    if df is None or df.empty:
        raise ValueError("Gerçek test verisi çekilemedi.")

    real_data_cache[cache_key] = df
    return df

router = APIRouter(prefix="/api/v1/strategy", tags=["Strategy Builder"])

# Strateji klasörü
STRATEGY_DIR = "artifacts/strategies"
os.makedirs(STRATEGY_DIR, exist_ok=True)


class StrategySchema(BaseModel):
    """Strateji JSON schema"""
    name: str
    description: Optional[str] = ""
    timeframe: str = "15m"
    indicators: List[Dict[str, Any]]
    conditions: Dict[str, Any]
    risk: Optional[Dict[str, Any]] = None


@router.post("/test")
async def test_strategy(strategy: StrategySchema):
    """
    Stratejiyi test et (hızlı backtest)
    """
    try:
        # 1. JSON'u validate et
        is_valid, errors = StrategyValidator.validate(strategy.dict())
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid strategy: {errors}")
        
        # 2. Stratejiyi RAM'den yükle (Disk I/O Yok)
        strategy_dict = strategy.dict()

        # 3. Gerçek veriyi önbellekten al (Varsayılan BTC/USDT)
        default_symbol = "BTC/USDT"
        timeframe = strategy.timeframe if strategy.timeframe else "15m"

        df = await get_cached_real_data(symbol=default_symbol, timeframe=timeframe, days=30)
        
        # 4. Veriyi hazırla (indikatörleri hesapla) ve sinyalleri üret
        # Cache'teki df'yi değiştirmemek için copy() kullanıyoruz
        signals = calculate_signals(df.copy(), strategy_dict)

        # 5. Gerçek veri ile backtest çalıştır
        backtester = VectorizedBacktester(
            initial_balance=1000.0,
            fee_rate=0.0004,
            slippage=1.0001,
            risk_per_trade=0.02
        )

        risk_params = strategy_dict.get('risk', {
            'stop_loss_atr_multiplier': 2.0,
            'take_profit_atr_multiplier': 4.0
        })

        results = backtester.run_backtest(df, signals, risk_params)

        # 6. Metrikleri hesapla ve dön
        metrics = {
            "win_rate": float(results.win_rate) if hasattr(results, 'win_rate') else 0.0,
            "total_trades": int(results.total_trades) if hasattr(results, 'total_trades') else 0,
            "profit_factor": float(results.profit_factor) if hasattr(results, 'profit_factor') else 0.0,
            "max_drawdown": float(results.max_drawdown) if hasattr(results, 'max_drawdown') else 0.0
        }
        
        return {
            "status": "success",
            "message": "Test completed",
            "metrics": metrics
        }
        
    except ValueError as e:
        logger.warning(f"⚠️ Backtest veri hatası: {e}")
        raise HTTPException(status_code=400, detail=f"{str(e)} Lütfen önce Veri Laboratuvarı'ndan veri indirin.")
    except Exception as e:
        logger.error(f"❌ Backtest hatası: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Backtest hatası: {str(e)}")


@router.post("/save")
async def save_strategy(strategy: StrategySchema):
    """
    Stratejiyi JSON dosyasına kaydet
    """
    try:
        # Validate
        is_valid, errors = StrategyValidator.validate(strategy.dict())
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid strategy: {errors}")
        
        # Dosya adı oluştur
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = strategy.name.replace(" ", "_").lower()
        filename = f"{safe_name}_{timestamp}.json"
        filepath = os.path.join(STRATEGY_DIR, filename)
        
        # Kaydet
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(strategy.dict(), f, indent=2, ensure_ascii=False)
        
        return {
            "status": "success",
            "message": "Strategy saved",
            "filename": filename,
            "filepath": filepath
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_strategies():
    """
    Kayıtlı stratejileri listele
    """
    try:
        strategies = []
        
        for filename in os.listdir(STRATEGY_DIR):
            if filename.endswith('.json'):
                filepath = os.path.join(STRATEGY_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        strategy = json.load(f)
                    
                    strategies.append({
                        "filename": filename,
                        "name": strategy.get('name', 'Unknown'),
                        "timeframe": strategy.get('timeframe', '15m'),
                        "indicators_count": len(strategy.get('indicators', [])),
                        "created_at": strategy.get('created_at', '')
                    })
                except Exception:
                    continue
        
        return {
            "status": "success",
            "strategies": sorted(strategies, key=lambda x: x.get('created_at', ''), reverse=True)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/load/{filename}")
async def load_strategy(filename: str):
    """
    Kayıtlı stratejiyi yükle
    """
    try:
        filepath = os.path.join(STRATEGY_DIR, filename)
        
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            strategy = json.load(f)
        
        return {
            "status": "success",
            "strategy": strategy
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete/{filename}")
async def delete_strategy(filename: str):
    """
    Stratejiyi sil
    """
    try:
        filepath = os.path.join(STRATEGY_DIR, filename)
        
        if not os.path.exists(filepath):
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        os.remove(filepath)
        
        return {
            "status": "success",
            "message": "Strategy deleted"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/indicators")
async def get_available_indicators():
    """
    Mevcut indikatörleri listele
    """
    
    builder = StrategyBuilder()
    
    indicators = []
    for name, config in builder.AVAILABLE_INDICATORS.items():
        indicators.append({
            "name": name,
            "category": config['category'],
            "parameters": config['parameters']
        })
    
    return {
        "status": "success",
        "indicators": indicators
    }
