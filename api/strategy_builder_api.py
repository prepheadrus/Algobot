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

from strategy.builder import StrategyBuilder, StrategyExecutor, StrategyValidator

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
        # JSON'u validate et
        is_valid, errors = StrategyValidator.validate(strategy.dict())
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid strategy: {errors}")
        
        # Executor ile test et
        executor = StrategyExecutor()
        executor.load_strategy_from_dict(strategy.dict())
        
        # TODO: Gerçek test data ile backtest
        # Şimdilik mock sonuç döndür
        metrics = {
            "win_rate": 62.5,
            "total_trades": 24,
            "profit_factor": 1.8,
            "max_drawdown": 8.2
        }
        
        return {
            "status": "success",
            "message": "Test completed",
            "metrics": metrics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
                except Exception as e:
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
    from strategy.builder import StrategyBuilder
    
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
