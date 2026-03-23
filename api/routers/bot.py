"""
Bot Router

FastAPI router for bot operations.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List

from core.logger import logger
from api.schemas.bot import (
    BotStartRequest,
    BotStopRequest,
    BotResumeRequest,
    BotRemoveRequest,
)
from api.services.bot_service import BotService

router = APIRouter(prefix="/api/v1/bot", tags=["Bot"])

bot_service = BotService()


@router.post("/start")
async def start_bot(request: BotStartRequest) -> Dict[str, Any]:
    """
    Yeni bir bot başlatır. Aynı sembolde birden fazla bot çalışabilir (1-to-N).
    """
    result = await bot_service.start_bot(request)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    return result


@router.post("/stop")
async def stop_bot(request: BotStopRequest) -> Dict[str, Any]:
    """
    Belirli bir botu durdurur.
    """
    result = await bot_service.stop_bot(request)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    return result


@router.post("/resume")
async def resume_bot(request: BotResumeRequest) -> Dict[str, Any]:
    """
    Durdurulmuş botu devam ettirir.
    """
    result = await bot_service.resume_bot(request)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    return result


@router.post("/remove")
async def remove_bot(request: BotRemoveRequest) -> Dict[str, Any]:
    """
    Botu listeden kaldırır (sadece durdurulmuş botlar).
    """
    result = await bot_service.remove_bot(request)
    
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    return result


@router.get("/status", operation_id="get_bot_status")
async def get_bot_status(bot_id: str) -> Dict[str, Any]:
    """
    Belirli bir botun durumunu döner.
    """
    return await bot_service.get_bot_status(bot_id)


@router.get("/list")
async def get_all_bots() -> Dict[str, Any]:
    """
    Tüm aktif botların listesini döner.
    """
    return await bot_service.get_all_bots()


# ============================================================================
# COMPATIBILITY ENDPOINTS (Frontend uyumluluğu için)
# ============================================================================

@router.get("/bots/list")
async def get_all_bots_plural() -> Dict[str, Any]:
    """
    COMPATIBILITY: /api/v1/bots/list endpoint'i
    Frontend'in çoğul form isteği için alias.
    """
    return await bot_service.get_all_bots()
