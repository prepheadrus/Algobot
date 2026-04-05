"""
Strategy Router

FastAPI router for strategy operations.
"""

from fastapi import APIRouter
from typing import Dict, Any, Optional

from core.logger import logger
from api.services.strategy_service import StrategyService

router = APIRouter(prefix="/api/v1", tags=["Strategy"])

strategy_service = StrategyService()


@router.get("/strategies")
async def get_strategy_list() -> Dict[str, Any]:
    """
    Sistemdeki tüm stratejileri döner (builtin + custom).
    """
    return strategy_service.get_strategies()


@router.post("/strategy/select")
async def change_strategy(
    symbol: str,
    strategy_id: Optional[str] = None,
    timeframe: str = "1m",
    market_type: str = "swap",
    margin_type: str = "isolated"
) -> Dict[str, Any]:
    """
    Botun stratejisini anında değiştirir.
    strategy_id boş ise strateji durdurulur.
    """
    if strategy_id:
        return strategy_service.select_strategy(
            symbol=symbol,
            strategy_id=strategy_id,
            timeframe=timeframe,
            market_type=market_type,
            margin_type=margin_type
        )
    else:
        return strategy_service.stop_strategy(symbol)


@router.get("/strategy-report")
async def get_strategy_performance_report() -> Dict[str, Any]:
    """
    Tüm işlemler üzerinden strateji bazlı detaylı röntgen/karne raporunu döner.
    
    Returns:
        {
            "status": "success",
            "report": [
                {
                    "strategy": "TrendMaster Pro",
                    "total_trades": 15,
                    "win_rate": 66.7,
                    "total_pnl": 125.50,
                    "symbols": [
                        {"name": "BTC/USDT (1h)", "trades": 5, "win_rate": 80.0, "pnl": 75.20},
                        ...
                    ],
                    "recommendation": "Mükemmel uyum. Kârlılık ve kazanma oranı muazzam."
                },
                ...
            ]
        }
    """
    try:
        from core.paper import paper_engine
        report = paper_engine.get_strategy_report()
        return {"status": "success", "report": report}
    except Exception as e:
        logger.error(f"Strateji rapor hatası: {e}")
        return {"status": "error", "message": str(e), "report": []}


@router.get("/strategy/{strategy_id}/chart-data")
async def get_strategy_chart_data(strategy_id: str, symbol: Optional[str] = None):
    """
    Strateji görselleştirme için gerekli tüm verileri döner.
    """
    return await strategy_service.get_strategy_chart_data(strategy_id, symbol)
