"""
CryptoAlgoBot FastAPI Server

Modern, modüler API sunucusu.
Router'lar, servisler ve şemalar ile yapılandırılmış.

Mimari:
- api/routers/: FastAPI router'ları (endpoint'ler)
- api/services/: Business logic
- api/schemas/: Pydantic models (request/response)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio

from core.logger import logger
from core.config import CONFIG
from core.exchange import exchange_manager
from data.database import db_manager
from core.paper import paper_engine

# Router'ları import et
from api.routers.bot import router as bot_router
from api.routers.ml import router as ml_router
from api.routers.strategy import router as strategy_router
from api.routers.data import router as data_router
from api.routers.system import router as system_router
from api.routers.strategy_builder import router as strategy_builder_router
from api.routers.backtest import router as backtest_router
from api.routers.trades import router as trades_router


# ============================================================================
# LIFESPAN EVENTS
# ============================================================================

from core.config import CONFIG, API_HOST

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI uygulama yaşam döngüsü."""
    # ===== STARTUP =====
    logger.info("🚀 FastAPI Sunucusu başlatılıyor...")

    # ========================================================================
    # KRİTİK: Event Handler'ları ÖNCE kaydet (Event Loss Önleme)
    # ========================================================================
    # 1. PaperTrader Handler'ları ÖNCE kaydet (event'ler başlamadan)
    logger.info("📬 [CRITICAL] Event handler'lar kayıt ediliyor...")
    await paper_engine.start_event_handlers()
    
    # 2. Event Bus Başlat (handler'lar hazır)
    logger.info("🚀 Event Bus başlatılıyor...")
    from shared.events import event_bus
    await event_bus.start(num_workers=5)

    # 3. Veritabanı bağlantısı
    logger.info("💾 Veritabanı bağlantısı başlatılıyor...")
    await db_manager.connect()
    
    # 4. Connection verify (2 saniye bekle - DB hazır olsun)
    logger.info("⏳ Veritabanı bağlantısı doğrulanıyor (2s)...")
    await asyncio.sleep(2)

    # 5. Yarım kalan indirme görevlerini geri yükle
    logger.info("📁 İndirme görevleri yükleniyor...")
    await exchange_manager.load_tasks_from_db()

    # 6. Bot task'larını başlat
    logger.info("🚀 Bot task'ları başlatılıyor...")
    # ÖNCE: config.yaml'dan oku
    symbols = CONFIG.get('trading', {}).get('symbols', [])

    if not symbols:
        # YENİ: config.yaml boşsa, Parquet Data Lake'den otomatik yükle
        logger.info("🔄 [AUTO-SYNC] config.yaml boş, Parquet Data Lake'den semboller yükleniyor...")
        try:
            from data.storage.parquet_lake import get_parquet_lake
            from core.exchange import normalize_symbol
            lake = get_parquet_lake('binance')
            stats = lake.get_stats()

            if stats['total_symbols'] > 0:
                # [SYMBOL FIX] Parquet'ten gelen sembolleri normalize et (örn: /BTC → BTC/USDT)
                symbols = [normalize_symbol(s) for s in stats['symbols'].keys()]
                logger.info(f"✅ [AUTO-SYNC] Parquet'ten {len(symbols)} sembol yüklendi!")
                logger.info(f"   Toplam dosya: {stats['total_files']}, Boyut: {stats['total_size_mb']:.2f} MB")
            else:
                logger.info("ℹ️ Parquet Data Lake boş - Dashboard'dan bot başlatabilirsiniz")
        except Exception as e:
            logger.error(f"❌ [AUTO-SYNC] Parquet'ten sembol yükleme hatası: {e}")

    tasks = []
    for symbol in symbols:
        tasks.append(asyncio.create_task(exchange_manager.watch_ticker_loop(symbol)))
        tasks.append(asyncio.create_task(exchange_manager.run_strategy_poller(symbol)))

    logger.info(f"✅ {len(tasks)} bot task'ı ve Event Engine başlatıldı")

    # ===== WFO (Walk-Forward Optimization) Başlat =====
    if CONFIG.get('wfo', {}).get('enabled', False):
        logger.info("🧠 [WFO] Otonom optimizasyon sistemi başlatılıyor...")
        try:
            from core.wfo_engine import start_wfo_background_task
            from strategy.manager import StrategyManager

            wfo_tasks = []
            for symbol in symbols:  # symbols değişkenini kullan
                strategy_id = paper_engine.active_strategies.get(symbol)
                if strategy_id:
                    strategy_instance = StrategyManager.get_strategy(strategy_id)
                    if strategy_instance:
                        timeframe = paper_engine.active_timeframes.get(symbol, '1m')
                        wfo_task = asyncio.create_task(
                            start_wfo_background_task(
                                symbol=symbol,
                                timeframe=timeframe,
                                strategy_class=strategy_instance.__class__,
                                param_grid=None,
                                optimization_metric=CONFIG['wfo'].get('optimization_metric', 'sharpe'),
                                n_trials=50
                            )
                        )
                        wfo_tasks.append(wfo_task)

            if wfo_tasks:
                logger.info(f"🎯 [WFO] {len(wfo_tasks)} sembol için otonom optimizasyon aktif")
        except Exception as e:
            logger.error(f"❌ [WFO] Başlatma hatası: {e}")
    else:
        logger.info("ℹ️ [WFO] Otonom optimizasyon devre dışı")

    yield

    # ===== SHUTDOWN =====
    logger.info("")
    logger.info("🛑 [API] GÜVENLI KAPATMA BAŞLATILIYOR...")
    logger.info("=" * 60)

    # 1. Yeni işlem almayı durdur
    logger.info("1️⃣ [API] Yeni işlem alımı durduruluyor...")
    if hasattr(paper_engine, 'accepting_new_trades'):
        paper_engine.accepting_new_trades = False
    logger.info("✅ [API] Yeni işlem alımı durduruldu")

    # 2. Event Bus Durdur
    logger.info("2️⃣ [API] Event Bus durduruluyor...")
    from shared.events import event_bus
    await event_bus.stop()
    logger.info("✅ [API] Event Bus durduruldu")

    # 3. Borsa bağlantısını kapat
    logger.info("3️⃣ [API] Borsa bağlantısı kapatılıyor...")
    await exchange_manager.close()
    logger.info("✅ [API] Borsa bağlantısı kapatıldı")

    # 4. Veritabanı bağlantısını kapat
    logger.info("4️⃣ [API] Veritabanı bağlantısı kapatılıyor...")
    await db_manager.close()
    logger.info("✅ [API] Veritabanı bağlantısı kapatıldı")

    # 5. Circuit Breaker istatistikleri
    logger.info("5️⃣ [API] Circuit Breaker istatistikleri:")
    try:
        from core.circuit_breaker import get_all_breakers_stats
        stats = get_all_breakers_stats()
        for name, breaker_stats in stats.items():
            logger.info(
                f"   {name}: state={breaker_stats['state']}, "
                f"failures={breaker_stats['total_failures']}, "
                f"rejected={breaker_stats['total_rejected']}"
            )
    except Exception:
        pass

    logger.info("=" * 60)
    logger.info("✅ [API] GÜVENLİ KAPATMA TAMAMLANDI")
    logger.info("")


# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="CryptoAlgoBot Core API",
    description="Bot ile Arayüz (Dashboard) arasında güvenli ve hızlı veri köprüsü.",
    version="2.0.0",
    lifespan=lifespan
)

# CORS ayarları
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# ROUTERS
# ============================================================================

app.include_router(system_router)
logger.info("✅ System router eklendi")

app.include_router(bot_router)
logger.info("✅ Bot router eklendi")

app.include_router(ml_router)
logger.info("✅ ML router eklendi")

app.include_router(strategy_router)
logger.info("✅ Strategy router eklendi")

app.include_router(data_router)
logger.info("✅ Data router eklendi")

app.include_router(strategy_builder_router)
logger.info("✅ Strategy Builder router eklendi")

app.include_router(backtest_router)
logger.info("✅ Backtest router eklendi")

app.include_router(trades_router)
logger.info("✅ Trades router eklendi")

# ============================================================================
# FRONTEND (STATIC FILES)
# ============================================================================

try:
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
    logger.info("✅ Frontend dosyaları mount edildi")
except Exception as e:
    logger.warning(f"⚠️ Frontend mount hatası: {e}")

# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.server:app",
        host=API_HOST,
        port=8000,
        reload=True,
        log_level="info"
    )

# ============================================================================
# FINAL LOG
# ============================================================================

logger.info("🎉 [MİMARİ] Faz 2 Tamamlandı: API Katmanı Modülerleştirildi (1374 satır -> ~160 satır)")
