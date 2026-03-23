import uvicorn
import asyncio
from core.logger import logger
from core.config import CONFIG, API_HOST

# Event Tracer import (Sistem Röntgeni - Event-Driven Architecture Diagnostic)
from core.diagnostics.event_tracer import start_event_tracer, event_tracer

# Bot Background Tasks imports
from core.exchange import exchange_manager, normalize_symbol
from shared.events import event_bus
from strategy.manager import StrategyManager

async def start_background_tasks():
    """
    Arka plan task'larını başlat (Event Bus, Poller'lar, WFO).

    Bu fonksiyon:
    1. Event Bus'ı başlatır (5 worker)
    2. Her sembol için WebSocket dinleyici başlatır
    3. Her sembol için strateji poller başlatır
    4. WFO aktifse arka plan optimizasyonunu başlatır
    """
    logger.info("")
    logger.info("🚀 BOT ARKA PLAN TASK'LARI BAŞLATILIYOR...")
    logger.info("=" * 60)

    # 1. Event Bus başlat
    try:
        await event_bus.start(num_workers=5)
        logger.info("✅ Event Bus başlatıldı (5 worker)")
    except Exception as e:
        logger.error(f"❌ Event Bus başlatma hatası: {e}")
        raise

    # 2. Her sembol için poller başlat
    # ÖNCE: config.yaml'dan oku
    symbols = CONFIG.get('trading', {}).get('symbols', [])

    if not symbols:
        # YENİ: config.yaml boşsa, Parquet Data Lake'den otomatik yükle
        logger.info("🔄 [AUTO-SYNC] config.yaml boş, Parquet Data Lake'den semboller yükleniyor...")
        try:
            from data.storage.parquet_lake import get_parquet_lake
            lake = get_parquet_lake('binance')
            stats = lake.get_stats()

            if stats['total_symbols'] > 0:
                # [SYMBOL FIX] Parquet'ten gelen sembolleri normalize et (örn: /BTC → BTC/USDT)
                symbols = [normalize_symbol(s) for s in stats['symbols'].keys()]
                logger.info(f"✅ [AUTO-SYNC] Parquet'ten {len(symbols)} sembol yüklendi!")
                logger.info(f"   Semboller: {', '.join(symbols[:5])}{'...' if len(symbols) > 5 else ''}")
                logger.info(f"   Toplam dosya: {stats['total_files']}, Boyut: {stats['total_size_mb']:.2f} MB")
            else:
                logger.warning("⚠️ Parquet Data Lake boş! Veri Laboratuvarı'ndan veri indirin.")
        except Exception as e:
            logger.error(f"❌ [AUTO-SYNC] Parquet'ten sembol yükleme hatası: {e}")
            logger.info("ℹ️ SQLite DB'den deneniyor...")
            try:
                from data.database import db_manager
                await db_manager.connect()
                db_symbols = await db_manager.get_symbols_with_data()
                if db_symbols:
                    symbols = db_symbols
                    logger.info(f"✅ [AUTO-SYNC] DB'den {len(symbols)} sembol yüklendi!")
            except Exception as e2:
                logger.error(f"❌ [AUTO-SYNC] DB'den sembol yükleme hatası: {e2}")

    # Sembollerle botları başlat
    if symbols:
        logger.info(f"📊 {len(symbols)} sembol için poller başlatılıyor...")

        for symbol in symbols:
            try:
                # WebSocket ticker loop (fiyat dinleme)
                asyncio.create_task(exchange_manager.watch_ticker_loop(symbol))
                logger.info(f"📡 [WSS] {symbol} için WebSocket dinleyici başlatıldı")

                # Strateji poller (sinyal üretme)
                asyncio.create_task(exchange_manager.run_strategy_poller(symbol))
                logger.info(f"🚀 [POLLER] {symbol} için strateji poller başlatıldı")

            except Exception as e:
                logger.error(f"❌ {symbol} için poller başlatma hatası: {e}")
    else:
        logger.info("ℹ️ Aktif sembol yok - Dashboard'dan bot başlatabilirsiniz")

    # 3. WFO arka plan task'ı başlat (aktifse)
    if CONFIG.get('wfo', {}).get('enabled', False):
        logger.info("🧠 [WFO] Walk-Forward Optimization aktif")

        try:
            from core.wfo_engine import start_wfo_background_task

            for symbol in symbols:
                strategy = StrategyManager.get_strategy('trend_master')
                if strategy:
                    asyncio.create_task(
                        start_wfo_background_task(
                            symbol=symbol,
                            timeframe='1h',
                            strategy_class=strategy,
                            n_trials=50
                        )
                    )
                    logger.info(f"🧠 [WFO] {symbol} için optimizasyon task'ı başlatıldı")
        except Exception as e:
            logger.warning(f"⚠️ WFO başlatma hatası: {e}")
            logger.warning("   Bot çalışmaya devam edecek, WFO olmadan")

    logger.info("=" * 60)
    logger.info("✅ TÜM ARKA PLAN TASK'LARI BAŞLATILDI!")
    logger.info("   Bot şimdi piyasayı dinliyor ve işlem yapıyor...")
    logger.info("=" * 60)
    logger.info("")

if __name__ == "__main__":
    # Global shutdown flag
    shutdown_in_progress = False
    
    async def graceful_shutdown():
        """
        Güvenli kapatma (Graceful Shutdown).
        Açık pozisyonları kapatır, bağlantıları temizler.
        """
        global shutdown_in_progress
        if shutdown_in_progress:
            return  # Zaten kapanıyor
        
        shutdown_in_progress = True
        
        logger.info("")
        logger.info("🛑 GÜVENLI KAPATMA BAŞLATILIYOR...")
        logger.info("=" * 60)
        
        try:
            # 1. Yeni işlem almayı durdur
            logger.info("1️⃣ Yeni işlem alımı durduruluyor...")
            if hasattr(paper_engine, 'accepting_new_trades'):
                paper_engine.accepting_new_trades = False
            logger.info("✅ Yeni işlem alımı durduruldu")
            
            # 2. Açık pozisyonları kapat
            logger.info("2️⃣ Açık pozisyonlar kapatılıyor...")
            open_positions_count = len(paper_engine.open_positions) if hasattr(paper_engine, 'open_positions') else 0
            
            if open_positions_count > 0:
                logger.warning(f"⚠️ {open_positions_count} açık pozisyon var!")
                logger.info("   Pozisyonlar dashboard'dan manuel kapatılmalı veya")
                logger.info("   otomatik kapatma için bot ayarlarını kontrol edin.")
            else:
                logger.info("✅ Açık pozisyon yok")
            
            # 3. Event Bus'ı durdur
            logger.info("3️⃣ Event Bus durduruluyor...")
            from shared.events import event_bus
            await event_bus.stop()
            logger.info("✅ Event Bus durduruldu")
            
            # 4. Exchange bağlantılarını kapat
            logger.info("4️⃣ Exchange bağlantıları kapatılıyor...")
            await exchange_manager.close()
            logger.info("✅ Exchange bağlantıları kapatıldı")
            
            # 5. Database bağlantısını kapat
            logger.info("5️⃣ Database bağlantısı kapatılıyor...")
            from data.database import db_manager
            await db_manager.close()
            logger.info("✅ Database bağlantısı kapatıldı")
            
            # 6. Circuit Breaker istatistiklerini logla
            logger.info("6️⃣ Circuit Breaker istatistikleri:")
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
            
            # 7. Event Tracer istatistiklerini göster
            logger.info("7️⃣ Event Tracer istatistikleri:")
            try:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(event_tracer.stop())
            except Exception:
                pass
            
            logger.info("=" * 60)
            logger.info("✅ GÜVENLİ KAPATMA TAMAMLANDI")
            logger.info("")
            
        except Exception as e:
            logger.error(f"❌ Kapatma sırasında hata: {e}")
            logger.error("   Bot zorla kapatılıyor...")
    
    def run_graceful_shutdown(loop):
        """Sync wrapper for graceful shutdown"""
        try:
            loop.run_until_complete(graceful_shutdown())
        except Exception as e:
            logger.error(f"Shutdown error: {e}")
        finally:
            # Tüm pending task'ları iptal et
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            # Kapanana kadar bekle
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()
    
    try:
        if __import__('sys').platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        # Ana event loop'u al
        loop = asyncio.get_event_loop()

        # Event Tracer başlat (Event-Driven mimari diagnostik)
        logger.info("")
        logger.info("🔍 EVENT TRACER BAŞLATILIYOR...")
        logger.info("   Sistem röntgeni aktif - Tüm event'ler izleniyor")
        logger.info("")

        try:
            loop.create_task(start_event_tracer())
            logger.info("✅ Event Tracer aktif")
        except Exception as e:
            logger.warning(f"⚠️ Event Tracer başlatılamadı: {e}")

        # BOT ARKA PLAN TASK'LARINI BAŞLAT
        # Bu fonksiyon: Event Bus, WebSocket, Poller'lar, WFO başlatır
        logger.info("🚀 BOT TASK'LARI BAŞLATILIYOR...")
        loop.run_until_complete(start_background_tasks())

        # Tüm modüler sistemi, FastAPI endpoints ve arka plan Bot WebSockets dahil uvicorn ile başlatır.
        # Uvicorn, asenkron motoru çok verimli kullanır (Tek potada web + finansal işlemler).
        # Vercel Live Preview uyumluluğu için portu ortam değişkeninden de oku veya 3000'e fallback yap
        import os
        port = int(os.environ.get("PORT", 3000))

        logger.info("🌐 FastAPI Dashboard başlatılıyor...")
        logger.info(f"   Port: {port}")
        logger.info(f"   Reload: {CONFIG['bot']['environment'] == 'development'}")
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ BOT TAM OLARAK BAŞLATILDI!")
        logger.info("   Dashboard: http://localhost:" + str(port))
        logger.info("   Piyasa dinleniyor... İşlemler başlıyor...")
        logger.info("=" * 60)
        logger.info("")

        uvicorn.run(
            "api.server:app",
            host=API_HOST,
            port=port,
            log_level=CONFIG['bot']['log_level'].lower(),
            reload=True if CONFIG['bot']['environment'] == 'development' else False
        )

    except KeyboardInterrupt:
        logger.info("")
        logger.info("🛑 KULLANICI BOTU DURDURUYOR (CTRL+C)...")
        run_graceful_shutdown(loop)
