"""
Trades Router

FastAPI router for trade history and analytics.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime

from core.logger import logger
from data.database import db_manager

router = APIRouter(prefix="/api/v1/trades", tags=["Trades"])


@router.get("/history")
async def get_trade_history(
    symbol: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000)
) -> Dict[str, Any]:
    """
    Kalıcı veritabanından ve mevcut oturumdaki (memory) işlem geçmişini döner.
    """
    try:
        from core.paper import paper_engine

        # 1. DB'den çek
        db_trades = await db_manager.get_recent_trades(limit=limit)
        logger.info(f"📊 [TRADES] DB'den {len(db_trades)} işlem çekildi")
        
        # Debug: İlk trade'i logla
        if db_trades:
            logger.info(f"🔍 [TRADES] İlk trade: {db_trades[0]}")

        # 2. Memory'den çek (Mevcut oturum verileri)
        memory_trades = []
        if hasattr(paper_engine.position_manager, 'trade_history'):
            mem_raw = paper_engine.position_manager.trade_history.get_recent(limit)
            for t in mem_raw:
                # DB formatına normalize et
                trade_dict = t.to_dict()
                memory_trades.append({
                    "id": trade_dict.get('id'),
                    "symbol": trade_dict.get('symbol'),
                    "direction": trade_dict.get('direction'),
                    "entry_price": trade_dict.get('entry_price'),
                    "exit_price": trade_dict.get('exit_price'),
                    "size": trade_dict.get('size'),
                    "leverage": trade_dict.get('leverage'),
                    "pnl_usd": trade_dict.get('pnl'),
                    "pnl_percent": trade_dict.get('pnl_percent', 0.0),
                    "reason": trade_dict.get('reason'),
                    "strategy_id": trade_dict.get('strategy_id'),
                    "closed_at": trade_dict.get('closed_at'),
                    "bot_id": trade_dict.get('bot_id')
                })

        logger.info(f"📊 [TRADES] Memory'den {len(memory_trades)} işlem çekildi")

        # 3. DB + Memory trades'leri birleştir (duplicate önleme)
        # Memory trades anlık göstermek için önemli (DB'ye yazılmadan önce)
        all_trades = list(db_trades)
        
        # Memory trades'leri ekle (DB'de olmayanları)
        db_ids = set(t.get('id') for t in db_trades if t.get('id'))
        for mem_trade in memory_trades:
            if mem_trade.get('id') not in db_ids:
                all_trades.append(mem_trade)
        
        logger.info(f"📊 [TRADES] Toplam {len(all_trades)} işlem döndürülecek (DB: {len(db_trades)}, Memory: {len(memory_trades)})")

        # 4. Filtreleme
        if symbol:
            all_trades = [t for t in all_trades if t.get('symbol') == symbol]

        # 5. Sıralama (en yeni en üstte)
        def get_sort_key(trade):
            closed_at = trade.get('closed_at')
            if isinstance(closed_at, datetime):
                return closed_at
            if isinstance(closed_at, str) and closed_at:
                try:
                    return datetime.fromisoformat(closed_at.replace('Z', '+00:00'))
                except ValueError:
                    return datetime.min
            return datetime.min

        all_trades.sort(key=get_sort_key, reverse=True)

        response_data = {
            "status": "success",
            "count": len(all_trades),
            "trades": all_trades[:limit]
        }
        
        logger.info(f"✅ [TRADES] Response gönderiliyor: {len(all_trades[:limit])} işlem")
        
        return response_data
    except Exception as e:
        logger.error(f"Trade history error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear")
async def clear_trade_history() -> Dict[str, Any]:
    """
    Tüm işlem geçmişini veritabanından siler.
    """
    try:
        await db_manager.clear_trade_history()
        return {
            "status": "success",
            "message": "Tüm işlem geçmişi başarıyla temizlendi."
        }
    except Exception as e:
        logger.error(f"Clear trade history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_trade_stats() -> Dict[str, Any]:
    """
    İşlem geçmişine (DB + Memory) dayalı genel istatistikleri döner.
    """
    try:
        from core.paper import paper_engine
        
        # 1. DB'den çek
        db_trades = await db_manager.get_recent_trades(limit=1000)
        
        # 2. Memory'den çek
        memory_trades = []
        if hasattr(paper_engine.position_manager, 'trade_history'):
            mem_raw = paper_engine.position_manager.trade_history.trades
            for t in mem_raw:
                trade_dict = t.to_dict()
                memory_trades.append({
                    "id": trade_dict.get('id'),
                    "pnl_usd": trade_dict.get('pnl'),
                    "strategy_id": trade_dict.get('strategy_id')
                })
        
        # 3. Merge - DUPLICATE ÖNLEME (KRİTİK!)
        # DB'deki tüm ID'leri topla (normalize edilmiş)
        seen_ids = set()
        for t in db_trades:
            trade_id = t.get('id') or t.get('trade_id')
            if trade_id:
                # ID'yi normalize et (string'e çevir, boşlukları temizle)
                seen_ids.add(str(trade_id).strip())
        
        # Memory trade'leri ekle (eğer DB'de yoksa)
        all_trades = list(db_trades)  # DB trade'leri ile başla
        
        for t in memory_trades:
            trade_id = t.get('id') or t.get('trade_id')
            if trade_id:
                # ID'yi normalize et
                normalized_id = str(trade_id).strip()
                # Eğer DB'de yoksa ekle
                if normalized_id not in seen_ids:
                    all_trades.append(t)
                    seen_ids.add(normalized_id)  # Eklenenleri de işaretle
        
        if not all_trades:
            return {
                "status": "success",
                "stats": {
                    "total_trades": 0,
                    "win_rate": 0,
                    "total_pnl": 0,
                    "avg_pnl": 0,
                    "winning_trades": 0,
                    "losing_trades": 0
                }
            }
            
        winning_trades = [t for t in all_trades if (t.get('pnl_usd') or 0) > 0]
        losing_trades = [t for t in all_trades if (t.get('pnl_usd') or 0) <= 0]
        
        total_pnl = sum(t.get('pnl_usd') or 0 for t in all_trades)
        win_rate = (len(winning_trades) / len(all_trades)) * 100
        
        # Strateji bazlı gruplama
        strategy_stats = {}
        for t in all_trades:
            s_id = t.get('strategy_id') or 'Bilinmeyen'
            if s_id not in strategy_stats:
                strategy_stats[s_id] = {"count": 0, "pnl": 0}
            strategy_stats[s_id]["count"] += 1
            strategy_stats[s_id]["pnl"] += (t.get('pnl_usd') or 0)
            
        # En iyi strateji
        best_strategy = "N/A"
        if strategy_stats:
            best_strategy = max(strategy_stats.items(), key=lambda x: x[1]['pnl'])[0]

        return {
            "status": "success",
            "stats": {
                "total_trades": len(all_trades),
                "win_rate": round(win_rate, 2),
                "total_pnl": round(total_pnl, 2),
                "avg_pnl": round(total_pnl / len(all_trades), 2),
                "winning_trades": len(winning_trades),
                "losing_trades": len(losing_trades),
                "best_strategy": best_strategy,
                "strategy_count": len(strategy_stats)
            }
        }
    except Exception as e:
        logger.error(f"Trade stats error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"status": "error", "message": str(e)}
