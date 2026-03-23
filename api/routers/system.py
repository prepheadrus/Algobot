"""
System Router

FastAPI router for system operations.
Dashboard metrics, config, exchange info.
"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import Dict, Any, List
from pathlib import Path
import os
import yaml
import asyncio

from core.logger import logger
from core.config import CONFIG
from core.paper import paper_engine
from core.exchange import exchange_manager
from api.schemas.config import (
    RiskConfigUpdate,
    AdvancedConfigUpdate,
    ApiKeyUpdateRequest,
    BotConfigUpdate,
)

router = APIRouter(prefix="/api/v1", tags=["System"])

# ============================================================================
# WEBSOCKET MANAGER (Frontend Broadcasting)
# ============================================================================

class WebSocketManager:
    """
    WebSocket connections manager for frontend broadcasting.
    Event Bus subscriber + WebSocket broadcaster.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.event_handler_started = False

    async def connect(self, websocket: WebSocket):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"🔌 [WS] Frontend connected ({len(self.active_connections)} clients)")

        # Start event handler (first connection only)
        if not self.event_handler_started:
            asyncio.create_task(self.start_event_handler())
            self.event_handler_started = True

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"🔌 [WS] Frontend disconnected ({len(self.active_connections)} clients)")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return

        message_str = str(message)  # JSON string

        # Send to all connections (fire and forget)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"❌ [WS] Broadcast error: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def start_event_handler(self):
        """Subscribe to Event Bus and broadcast to WebSocket clients"""
        from shared.events import event_bus

        # Subscribe to position events
        event_bus.subscribe("position.opened", self.on_event)
        event_bus.subscribe("position.closed", self.on_event)
        event_bus.subscribe("position.updated", self.on_event)
        event_bus.subscribe("bot.started", self.on_event)
        event_bus.subscribe("bot.stopped", self.on_event)

        logger.info("📬 [WS] Event Bus subscriber started (broadcasting to frontend)")

    async def on_event(self, event):
        """Event Bus handler - broadcast to WebSocket clients"""
        try:
            # Convert event to dict
            message = {
                "type": event.type,
                "payload": event.payload,
                "source": event.source,
                "timestamp": event.timestamp.isoformat() if hasattr(event, 'timestamp') else None
            }

            # Broadcast to all connected WebSocket clients
            await self.broadcast(message)

            logger.debug(f"📡 [WS] Event broadcasted: {event.type}")
        except Exception as e:
            logger.error(f"❌ [WS] Event broadcast error: {e}")


# Global WebSocket manager
ws_manager = WebSocketManager()


# Global start time for uptime calculation
import time
START_TIME = time.time()


@router.get("/health", operation_id="get_health_status")
async def get_health_status() -> Dict[str, Any]:
    """
    Sistem sağlık durumunu döner.
    Monitoring araçları (Prometheus, Grafana, Uptime Kuma) için.
    """
    try:
        # Event Bus durumu
        from shared.events import event_bus
        event_bus_status = "running" if event_bus.running else "stopped"
        
        # Database durumu
        from data.database import db_manager
        db_status = "connected" if db_manager.sqlite_conn or db_manager.db_pool else "disconnected"
        
        # Exchange bağlantısı
        exchange_status = "connected" if exchange_manager.exchange else "disconnected"
        
        # Aktif botlar
        active_bots_count = len(paper_engine.active_bots) if hasattr(paper_engine, 'active_bots') else 0
        
        # Uptime hesaplama
        uptime_seconds = time.time() - START_TIME
        uptime_hours = uptime_seconds / 3600
        
        return {
            "status": "healthy",
            "timestamp": time.time(),
            "components": {
                "event_bus": event_bus_status,
                "database": db_status,
                "exchange": exchange_status,
            },
            "metrics": {
                "active_bots": active_bots_count,
                "uptime_hours": round(uptime_hours, 2),
                "uptime_seconds": int(uptime_seconds)
            },
            "version": "4.0.0"
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": str(e),
            "version": "4.0.0"
        }


@router.get("/status", operation_id="get_system_status")
async def get_system_status() -> Dict[str, Any]:
    """
    Sistem durumunu döner.
    """
    return {
        "status": "online",
        "environment": CONFIG['bot'].get('environment', 'development'),
        "exchange": CONFIG['trading'].get('exchange', 'binance'),
        "tracking_symbols": CONFIG['trading'].get('symbols', [])
    }


# ============================================================================
# WEBSOCKET ENDPOINT (Frontend Real-time Events)
# ============================================================================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for frontend real-time event streaming.

    Frontend connects to this endpoint and receives:
    - position.opened
    - position.closed
    - position.updated
    - bot.started
    - bot.stopped

    Usage (Frontend):
        const ws = new WebSocket('ws://localhost:3000/api/v1/ws');
        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            console.log('Event:', message.type, message.payload);
        };
    """
    await ws_manager.connect(websocket)
    try:
        # Keep connection alive
        while True:
            # Wait for messages from client (heartbeat, commands, etc.)
            data = await websocket.receive_text()
            logger.debug(f"📬 [WS] Client message: {data}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"❌ [WS] WebSocket error: {e}")
        ws_manager.disconnect(websocket)


# ============================================================================
# DASHBOARD METRICS
# ============================================================================

@router.get("/dashboard-metrics")
async def get_dashboard_metrics() -> Dict[str, Any]:
    """
    Dashboard için tüm metrikleri döner.
    NaN/Infinity koruması ile JSON serileştirme hatalarını önler.
    """
    try:
        import math

        def sanitize_value(value):
            """NaN/Infinity değerlerini 0.0'a çevir"""
            if value is None:
                return 0.0
            if isinstance(value, (int, float)):
                if math.isnan(value) or math.isinf(value):
                    logger.warning(f"⚠️ [SANITIZE] NaN/Infinity detected: {value} → 0.0")
                    return 0.0
            return value

        def sanitize_dict(data: dict) -> dict:
            """Dict içindeki tüm değerleri sanitize et"""
            return {k: sanitize_value(v) for k, v in data.items()}

        # Paper engine'den stats al
        stats = paper_engine.get_stats()

        # Portfolio bilgisi (NaN/Infinity koruması)
        portfolio = {
            "balance": sanitize_value(stats.get('balance', 0.0)),
            "free_margin": sanitize_value(stats.get('free_margin', 0.0)),
            "used_margin": sanitize_value(stats.get('used_margin', 0.0)),
            "equity": sanitize_value(stats.get('equity', stats.get('balance', 0.0))),
            "unrealized_pnl": sanitize_value(stats.get('unrealized_pnl', 0.0)),
            "total_pnl": sanitize_value(stats.get('total_pnl', 0.0)),
            "total_trades": int(stats.get('total_trades', 0)),
            "win_rate": sanitize_value(stats.get('win_rate', 0.0)),
            "total_commission": sanitize_value(stats.get('total_commission', 0.0)),
            "total_notional": sanitize_value(stats.get('total_notional', 0.0)),
        }

        # Aktif pozisyonlar (NaN/Infinity koruması)
        positions = []
        for pos in paper_engine.open_positions:
            positions.append(sanitize_dict({
                "bot_id": pos.get('bot_id', 'N/A'),
                "symbol": pos.get('symbol', ''),
                "direction": pos.get('direction', ''),
                "entry_price": sanitize_value(pos.get('entry_price', 0.0)),
                "current_price": sanitize_value(pos.get('current_price', 0.0)),
                "size": sanitize_value(pos.get('size', 0.0)),
                "leverage": sanitize_value(pos.get('leverage', 1.0)),
                "margin": sanitize_value(pos.get('margin', 0.0)),
                "unrealized_usd": sanitize_value(pos.get('unrealized_usd', 0.0)),
                "pnl_percent": sanitize_value(pos.get('pnl_percent', 0.0)),
                "stop_loss": sanitize_value(pos.get('stop_loss')),
                "take_profit": sanitize_value(pos.get('take_profit')),
                "liquidation_price": sanitize_value(pos.get('liquidation_price', 0.0)),
                "strategy": pos.get('strategy', 'Unknown'),
                "strategy_id": pos.get('strategy_id', 'unknown'),
                "timeframe": pos.get('timeframe', 'N/A')
            }))

        # Son kararlar (latest decisions) - sanitize
        latest_decisions = {}
        for symbol, decision in (paper_engine.latest_decisions or {}).items():
            if isinstance(decision, dict):
                latest_decisions[symbol] = sanitize_dict(decision)
            else:
                latest_decisions[symbol] = decision

        # Market regime
        market_regime = paper_engine.market_regime or "UNKNOWN"

        return JSONResponse(
            content={
                "portfolio": portfolio,
                "positions": positions,
                "latest_decisions": latest_decisions,
                "market_regime": market_regime,
            },
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

    except Exception as e:
        logger.error(f"Dashboard metrics error: {e}", exc_info=True)
        return JSONResponse(
            content={
                "portfolio": {"balance": 0.0, "free_margin": 0.0, "used_margin": 0.0},
                "positions": [],
                "latest_decisions": {},
                "market_regime": "UNKNOWN"
            },
            status_code=500
        )


@router.get("/config/symbols")
async def get_tracked_symbols() -> Dict[str, Any]:
    """
    İzlenen sembollerin listesini döner.
    """
    return {"symbols": CONFIG['trading'].get('symbols', [])}


@router.get("/exchange/markets")
async def get_exchange_markets() -> Dict[str, Any]:
    """
    Borsadaki tüm aktif USDT işlem çiftlerini döner.
    """
    try:
        markets = await exchange_manager.fetch_available_markets()
        return {"markets": markets}
    except Exception as e:
        logger.error(f"Exchange markets error: {e}")
        return {"markets": []}


# ============================================================================
# CONFIG ENDPOINTS (Hot-Reload & Persistence)
# ============================================================================

@router.get("/config/bot")
async def get_bot_config() -> Dict[str, Any]:
    """Genel bot ayarlarını döner."""
    return {
        "status": "success",
        "config": CONFIG.get('bot', {})
    }

@router.post("/config/bot")
async def update_bot_config(request: BotConfigUpdate) -> Dict[str, Any]:
    """Genel bot ayarlarını günceller."""
    try:
        # Update memory
        CONFIG['bot']['environment'] = request.environment
        CONFIG['bot']['exchange'] = request.exchange
        CONFIG['bot']['log_level'] = request.log_level
        
        # Persist to yaml
        config_path = "config.yaml"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                full_config = yaml.safe_load(f)

            if 'bot' not in full_config: full_config['bot'] = {}
            full_config['bot']['environment'] = request.environment
            full_config['bot']['exchange'] = request.exchange
            full_config['bot']['log_level'] = request.log_level
            
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(full_config, f, default_flow_style=False, allow_unicode=True)

        return {"status": "success", "message": "Bot ayarları güncellendi", "config": CONFIG['bot']}
    except Exception as e:
        logger.error(f"Bot config update error: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/config/risk")
async def get_risk_config() -> Dict[str, Any]:
    """Mevcut risk ayarlarını döner."""
    return {
        "status": "success",
        "config": CONFIG.get('risk_management', {})
    }


@router.post("/config/risk")
async def update_risk_config(request: RiskConfigUpdate) -> Dict[str, Any]:
    """Risk ayarlarını günceller."""
    try:
        # 1. Memory update
        CONFIG['risk_management']['max_risk_per_trade_percent'] = request.max_risk_per_trade_percent
        CONFIG['risk_management']['max_leverage'] = request.max_leverage
        CONFIG['risk_management']['max_open_positions'] = request.max_open_positions
        CONFIG['risk_management']['max_consecutive_losses'] = request.max_consecutive_losses
        CONFIG['risk_management']['kill_switch'] = CONFIG.get('kill_switch', {})
        CONFIG['risk_management']['kill_switch']['enabled'] = request.kill_switch_enabled

        # 2. YAML persistence
        config_path = "config.yaml"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                full_config = yaml.safe_load(f)

            if 'risk_management' not in full_config: full_config['risk_management'] = {}
            full_config['risk_management'].update({
                'max_risk_per_trade_percent': request.max_risk_per_trade_percent,
                'max_leverage': request.max_leverage,
                'max_open_positions': request.max_open_positions,
                'max_consecutive_losses': request.max_consecutive_losses,
                'kill_switch': {
                    'enabled': request.kill_switch_enabled,
                    'max_consecutive_losses': request.max_consecutive_losses
                }
            })

            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(full_config, f, default_flow_style=False, allow_unicode=True)

        # 3. Paper engine hot-reload
        if hasattr(paper_engine, 'risk_engine'):
            paper_engine.risk_engine.config.max_risk_per_trade = request.max_risk_per_trade_percent / 100.0
            paper_engine.risk_engine.config.max_leverage = request.max_leverage
            paper_engine.risk_engine.config.max_open_positions = request.max_open_positions
            paper_engine.risk_engine.config.max_consecutive_losses = request.max_consecutive_losses
            
            # Kill switch hot-reload
            if request.kill_switch_enabled:
                paper_engine.risk_engine.kill_switch_active = False  # Reset on config change
                paper_engine.risk_engine.consecutive_losses = 0
            paper_engine.risk_engine.config.kill_switch_enabled = request.kill_switch_enabled

        return {
            "status": "success", 
            "message": "Risk ayarları güncellendi", 
            "config": CONFIG['risk_management']
        }
    except Exception as e:
        logger.error(f"Risk config update error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/config/advanced")
async def get_advanced_config() -> Dict[str, Any]:
    """Gelişmiş ayarları çek."""
    return {
        "status": "success",
        "config": {
            "wfo": CONFIG.get('wfo', {}),
            "ml": CONFIG.get('ml', {}),
            "htf": CONFIG.get('htf', {}),
            "kalman": CONFIG.get('kalman', {'enabled': True, 'q': 0.001, 'r': 0.1}),
            "candle_lock": CONFIG.get('candle_lock', {'enabled': True, 'interval': 1})
        }
    }


@router.post("/config/advanced")
async def update_advanced_config(request: AdvancedConfigUpdate) -> Dict[str, Any]:
    """Gelişmiş ayarları güncelle."""
    try:
        config_path = "config.yaml"
        full_config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                full_config = yaml.safe_load(f)

        if request.wfo:
            CONFIG['wfo'] = request.wfo.dict()
            full_config['wfo'] = request.wfo.dict()
        if request.ml:
            CONFIG['ml'] = request.ml.dict()
            full_config['ml'] = request.ml.dict()
            paper_engine.ml_enabled = CONFIG['ml'].get('enabled', True)
        if request.htf:
            CONFIG['htf'] = request.htf.dict()
            full_config['htf'] = request.htf.dict()
        if request.kalman:
            CONFIG['kalman'] = request.kalman.dict()
            full_config['kalman'] = request.kalman.dict()
        if request.candle_lock:
            CONFIG['candle_lock'] = request.candle_lock.dict()
            full_config['candle_lock'] = request.candle_lock.dict()

        if os.path.exists(config_path):
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(full_config, f, default_flow_style=False, allow_unicode=True)

        return {"status": "success", "message": "Gelişmiş ayarlar güncellendi", "config": CONFIG}
    except Exception as e:
        logger.error(f"Advanced config update error: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# API KEY ENDPOINTS
# ============================================================================

@router.post("/config/api-keys")
async def save_api_keys(request: ApiKeyUpdateRequest) -> Dict[str, Any]:
    """API anahtarlarını şifreleyerek kaydet."""
    try:
        from core.security import KeyManager
        key_manager = KeyManager()
        key_manager.save_api_keys(request.api_key, request.api_secret)
        return {"status": "success", "message": "API anahtarları şifrelenerek kaydedildi"}
    except Exception as e:
        logger.error(f"API key save error: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/config/test-api-keys")
async def test_api_keys(request: ApiKeyUpdateRequest) -> Dict[str, Any]:
    """API anahtarlarını CCXT ile test et."""
    try:
        import ccxt.async_support as ccxt
        exchange = ccxt.binance({
            'apiKey': request.api_key,
            'secret': request.api_secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        balance = await exchange.fetch_balance()
        await exchange.close()
        usdt_balance = balance.get('total', {}).get('USDT', 0)
        return {
            "status": "success",
            "message": "API anahtarları geçerli!",
            "valid": True,
            "usdt_balance": usdt_balance
        }
    except Exception as e:
        logger.error(f"API keys test error: {e}")
        return {"status": "error", "message": str(e), "valid": False}
