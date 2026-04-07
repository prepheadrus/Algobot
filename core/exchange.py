import ccxt.pro as ccxtpro
import asyncio
import pandas as pd
from typing import Dict, Any, Optional
from core.logger import logger
from core.config import CONFIG, BINANCE_API_KEY, BINANCE_API_SECRET

# Bellek Optimizasyonu (Downcasting)
try:
    from data.data_prep import reduce_mem_usage
except ImportError:

    def reduce_mem_usage(df):
        return df


# Circuit Breaker import (Dış API çağrıları için koruma)
from core.circuit_breaker import exchange_breaker, CircuitBreakerError

# Event Bus import (Circular dependency kırıldı!)
from shared.events import event_bus
from shared.events.events import (
    SignalGeneratedEvent,
    LivePriceUpdatedEvent,
)

# WFO Engine import (opsiyonel - WFO aktifse)
try:
    import core.wfo_engine  # noqa: F401

    WFO_AVAILABLE = True
except ImportError:
    WFO_AVAILABLE = False
    logger.warning("⚠️ WFO Engine bulunamadı, optimizasyon özellikleri devre dışı.")

# Order Book Imbalance threshold
ORDER_BOOK_IMBALANCE_THRESHOLD = 0.60  # %60


def normalize_symbol(symbol: str) -> str:
    """
    CCXT Uyumlu Sembol Normalizasyonu (Safe Parsing).

    Kural 1: Gelen string'i temizle (BTC_USDT, BTC/USDT, BTCUSDT, /BTC vb.)
    Kural 2: Her zaman {BASE}/{QUOTE} formatına çevir
    Kural 3: Futures aktifse {BASE}/{QUOTE}:{QUOTE} formatına çevir
    Kural 4: Fallback - Eğer / yoksa /USDT ekle

    Args:
        symbol: Ham sembol (örn: BTC, BTC_USDT, BTC/USDT, BTCUSDT, /BTC)

    Returns:
        CCXT uyumlu sembol (örn: BTC/USDT veya BTC/USDT:USDT)
    """
    if not symbol:
        return "BTC/USDT"  # Default fallback

    # Adım 0: Gereksiz başlangıç karakterlerini temizle (örn: /BTC → BTC)
    symbol = symbol.strip()
    while symbol.startswith("/") or symbol.startswith("_"):
        symbol = symbol[1:]

    # Adım 1: Gereksiz karakterleri temizle
    symbol = symbol.strip()

    # Adım 2: _ veya - yerine / koy (BTC_USDT → BTC/USDT, BTC-USDT → BTC/USDT)
    # EĞER 2'DEN FAZLA PARÇA VARSA (örn: BTC_USDT_USDT), ilkini / yap, diğerini : yap
    parts = symbol.replace("-", "_").split("_")
    if len(parts) == 3:
        symbol = f"{parts[0]}/{parts[1]}:{parts[2]}"
    else:
        symbol = symbol.replace("_", "/").replace("-", "/")

    # Adım 2.5: PERP suffix kontrolü (BTC/USDT/PERP → BTC/USDT:USDT)
    if "/PERP" in symbol.upper() or ":PERP" in symbol.upper():
        symbol = symbol.upper().replace("/PERP", "").replace(":PERP", "")
        if "/" in symbol:
            quote = symbol.split("/")[-1]
            # ":" already exists? No, we stripped it, wait. Let's safely split
            if ":" in quote:
                quote = quote.split(":")[0]
            symbol = f"{symbol.split(':')[0]}:{quote}"
        else:
            symbol = f"{symbol}/USDT:USDT"

    # Adım 3: :USDT veya :USD kısmını temizle (BTC/USDT:USDT → BTC/USDT)
    # YENİ: Futures semboller için :USDT koru!
    if ":" in symbol:
        parts = symbol.split(":")
        base_part = parts[0]  # BTC/USDT
        quote_part = parts[1] if len(parts) > 1 else ""  # USDT

        # Eğer futures ise (USDT quote), :USDT'yi koru
        if quote_part.upper() == "USDT":
            symbol = f"{base_part}:{quote_part}"  # BTC/USDT:USDT olarak koru
        else:
            symbol = base_part  # Sadece base kısmı al

    # Adım 4: USDT, USD, BTC gibi kısımları ayır
    # BTCUSDT → BTC/USDT, ETHBTC → ETH/BTC
    if "/" not in symbol:
        # Sadece BASE sembolü (örn: BTC, ETH)
        if len(symbol) <= 4 and symbol.upper() in [
            "BTC",
            "ETH",
            "SOL",
            "XRP",
            "DOGE",
            "BNB",
            "ADA",
            "AVAX",
        ]:
            symbol = f"{symbol}/USDT"
        # USDT ile bitiyorsa
        elif symbol.upper().endswith("USDT"):
            base = symbol[:-4]
            quote = "USDT"
            symbol = f"{base}/{quote}"
        # USD ile bitiyorsa (USDT değil)
        elif symbol.upper().endswith("USD") and not symbol.upper().endswith("USDT"):
            base = symbol[:-3]
            quote = "USD"
            symbol = f"{base}/{quote}"
        # BTC ile bitiyorsa
        elif symbol.upper().endswith("BTC") and len(symbol) > 3:
            base = symbol[:-3]
            quote = "BTC"
            symbol = f"{base}/{quote}"
        # Hiçbiri değilse fallback
        else:
            symbol = f"{symbol}/USDT"

    # Adım 5: Fallback kalkanı - Eğer hala / yoksa
    if "/" not in symbol:
        symbol = f"{symbol}/USDT"

    logger.debug(f"🔧 [SYMBOL] Normalizasyon: {symbol}")

    return symbol


def normalize_symbol_for_exchange(symbol: str, market_type: str = "spot") -> str:
    """
    Borsa için sembol formatını ayarla (Spot vs Futures).

    Args:
        symbol: Normalized sembol (örn: BTC/USDT)
        market_type: 'spot' veya 'future'

    Returns:
        Borsa uyumlu sembol
    """
    # Futures (Vadeli) için CCXT formatı: BTC/USDT:USDT
    if market_type.lower() in ["future", "futures", "swap", "perp", "perpetual"]:
        if ":USDT" not in symbol:
            symbol = f"{symbol}:USDT"

    return symbol


class ExchangeManager:
    def __init__(self):
        self.exchange_id = CONFIG["trading"]["exchange"]

        # İlgili borsa sınıfını ccxt.pro'dan bul
        if not hasattr(ccxtpro, self.exchange_id):
            logger.error(f"Desteklenmeyen borsa: {self.exchange_id}")
            raise ValueError(f"Desteklenmeyen borsa: {self.exchange_id}")

        self.exchange_class = getattr(ccxtpro, self.exchange_id)
        self.download_stops = {}  # {symbol: bool} - İndirmeyi durdurmak için
        self.download_pauses = {}  # {symbol: bool} - Duraklatmak için
        self.active_downloads = (
            {}
        )  # {symbol: metadata} - Aktif görevleri takip etmek için

        # YENİ: Aktif poller'ları takip et (1-to-N mimarisi)
        self.active_pollers = {}  # {symbol: asyncio.Task} - Her sembol için 1 poller

        # ========================================================================
        # STATE REPLICATION - Local state (circular dependency kırıldı!)
        # ========================================================================
        self.local_active_bots: Dict[str, Dict[str, Any]] = {}  # bot_id -> bot_info
        self.local_active_strategies: Dict[str, Any] = {}  # symbol -> strategy
        self.local_active_timeframes: Dict[str, str] = {}  # symbol -> timeframe

        # Sınıf bazlı değişken tuzağından kaçınmak için Ticker fiyatları da instance'a alınmalı
        self._last_prices: Dict[str, float] = {}

        logger.info(
            "📦 [EDA] State Replication aktif (local_active_bots, local_active_strategies)"
        )

        # Borsa parametrelerini hazırla
        exchange_args = {
            "enableRateLimit": True,  # Borsa kurallarına göre hızı sınırlar (Ban yememek için)
            "timeout": 60000,  # 60 saniye timeout (Oracle Cloud için artırıldı)
            "options": {
                "defaultType": "future",  # Vadeli işlemler için
                "recvWindow": 60000,  # 60 saniye receive window
            },
        }

        # Seçili borsaya göre API anahtarlarını çek (.env dosyasından)
        if self.exchange_id == "binance":
            if BINANCE_API_KEY and BINANCE_API_SECRET:
                exchange_args["apiKey"] = BINANCE_API_KEY
                exchange_args["secret"] = BINANCE_API_SECRET
                logger.info(
                    "✅ Binance API anahtarları yüklendi. Yüksek rate limit aktif."
                )
            else:
                logger.warning(
                    "Binance API bilgileri bulunamadı (.env)! Sadece genel piyasa izlemesi (Ticker) yapılacak, Emir verilemez."
                )
                logger.warning(
                    "⚠️ Rate limit düşük olacak. API key eklemek için .env dosyasını düzenleyin."
                )

        # Asenkron borsayı başlat
        self.exchange = self.exchange_class(exchange_args)

        # CCXT Rate Limit kesinlikle aktif olduğundan emin ol (Anonim modda bile)
        self.exchange.enableRateLimit = True

        # Binance public streamleri api key gerektirmiyor. Ancak watch_ticker api key var ise public kanalları kullanırken de
        # hatalı api-key id hatası veriyor. Bunun için eğer watch_ticker vb. public kanallar kullanılacaksa
        # anahtarların gerçekten auth_err durumuna düşüp düşmeyeceğini try-except ile kontrol edeceğiz (load_markets içinde
        # veya watch_ticker esnasında anonim moda geçiliyor).
        logger.info(
            f"{self.exchange_id.upper()} borsa motoru WebSocket desteğiyle başlatıldı."
        )

        # ========================================================================
        # EVENT SUBSCRIPTIONS - Event Bus'a abone ol (circular dependency kırıldı!)
        # ========================================================================
        self._setup_event_subscriptions()

        # Final log
        logger.info("🎉 [EDA] Kısır Döngü Kırıldı - %100 Olay Güdümlü Mimari Aktif")

    def _setup_event_subscriptions(self):
        """Event Bus'a abone ol - State senkronizasyonu"""
        try:
            # Bot lifecycle eventleri
            event_bus.subscribe("bot.started", self._on_bot_started)
            event_bus.subscribe("bot.stopped", self._on_bot_stopped)

            logger.info(
                "📬 [EDA] Event subscriptions kuruldu (bot.started, bot.stopped)"
            )
        except Exception as e:
            logger.warning(f"⚠️ [EDA] Event subscription hatası: {e}")

    async def _on_bot_started(self, event):
        """Bot başladı - local state güncelle"""
        try:
            bot_id = event.payload.get("bot_id")
            if bot_id:
                self.local_active_bots[bot_id] = event.payload
                logger.debug(
                    f"🤖 [EDA] Bot başladı (local state güncellendi): {bot_id}"
                )
        except Exception as e:
            logger.error(f"❌ [EDA] _on_bot_started hatası: {e}")

    async def _on_bot_stopped(self, event):
        """Bot durdu - local state'den sil"""
        try:
            bot_id = event.payload.get("bot_id")
            if bot_id and bot_id in self.local_active_bots:
                del self.local_active_bots[bot_id]
                logger.debug(f"🛑 [EDA] Bot durdu (local state silindi): {bot_id}")
        except Exception as e:
            logger.error(f"❌ [EDA] _on_bot_stopped hatası: {e}")

    @exchange_breaker
    async def get_order_book_imbalance(
        self, symbol: str, depth: int = 20
    ) -> Optional[float]:
        """
        Order Book Imbalance (Emir Defteri Dengesizliği) hesapla.

        Formula:
            imbalance = ask_volume / (bid_volume + ask_volume)

        Args:
            symbol: Sembol (örn: BTC/USDT)
            depth: Order book derinliği (varsayılan: 20)

        Returns:
            Imbalance oranı (0-1 arası)
            - 0.5: Dengeli
            - >0.6: Ask baskın (satıcılar güçlü - LONG riskli)
            - <0.4: Bid baskın (alıcılar güçlü - SHORT riskli)
        """
        try:
            # CCXT ile order book çek (L2 data)
            order_book = await self.exchange.fetch_order_book(symbol, limit=depth)

            # Bid ve Ask hacimlerini topla
            bid_volume = sum([float(level[1]) for level in order_book.get("bids", [])])
            ask_volume = sum([float(level[1]) for level in order_book.get("asks", [])])

            # Imbalance hesapla
            total_volume = bid_volume + ask_volume
            if total_volume == 0:
                return 0.5

            imbalance = ask_volume / total_volume

            logger.debug(
                f"📊 [ORDER BOOK] {symbol} Imbalance: {imbalance:.4f} (Bid={bid_volume:.2f}, Ask={ask_volume:.2f})"
            )

            return imbalance

        except Exception as e:
            logger.error(f"❌ [ORDER BOOK] Imbalance hesaplama hatası: {e}")
            return None

    def check_liquidity_sweep(
        self, symbol: str, imbalance: float, direction: str
    ) -> bool:
        """
        Liquidity Sweep koruması - Order Book Imbalance filtresi.

        WFO'dan geçen strateji ve ML modeli "LONG" onayı verse dahi,
        eğer o anki emir defterinde satıcıların (Asks) hacmi
        alıcılardan (Bids) %60 daha fazlaysa, Risk Motoru bu işleme
        onay VEMEZ.

        Args:
            symbol: Sembol
            imbalance: Order book imbalance (0-1)
            direction: İşlem yönü (LONG/SHORT)

        Returns:
            True ise işlem ONAYLI (risk yok)
            False ise işlem REDDEDİLDİ (liquidity sweep riski)
        """
        # LONG işlem için kontrol
        if direction == "LONG":
            if imbalance > ORDER_BOOK_IMBALANCE_THRESHOLD:
                logger.warning(
                    f"⚠️ [LIQUIDITY] {symbol} LONG reddedildi - Ask baskın (imbalance={imbalance:.4f})"
                )
                return False

        # SHORT işlem için kontrol
        elif direction == "SHORT":
            if imbalance < (1 - ORDER_BOOK_IMBALANCE_THRESHOLD):
                logger.warning(
                    f"⚠️ [LIQUIDITY] {symbol} SHORT reddedildi - Bid baskın (imbalance={imbalance:.4f})"
                )
                return False

        # Onaylı
        logger.debug(
            f"✅ [LIQUIDITY] {symbol} {direction} onaylandı (imbalance={imbalance:.4f})"
        )
        return True

    async def load_tasks_from_db(self):
        """Uygulama başladığında yarım kalan görevleri veritabanından hafızaya geri yükler ve indirmeyi başlatır."""
        from data.database import db_manager

        tasks = await db_manager.get_all_download_tasks()
        count = 0
        for t in tasks:
            # Sadece bitmemiş olanları alıyoruz
            if t["status"] in ["running", "paused"]:
                m_type = t["market_type"].lower()
                key = f"{t['symbol']}_{m_type}"

                # Metadata yükle (UI için)
                self.active_downloads[key] = dict(t)
                self.download_stops[key] = False
                self.download_pauses[key] = t["status"] == "paused"

                # Arka plan görevini (coroutine) gerçekten başlat
                asyncio.create_task(
                    self.download_historical_data(
                        t["symbol"],
                        t["timeframe"],
                        t["start_date"],
                        m_type,
                        is_resume=True,
                    )
                )
                count += 1
        logger.info(
            f"📁 {count} yarım kalan indirme görevi veritabanından geri yüklendi ve BAŞLATILDI."
        )

    @exchange_breaker
    async def fetch_ohlcv(
        self, symbol, timeframe="1m", limit=100, params={}, since=None
    ):
        """
        Asenkron olarak geçmiş mum verilerini (REST API ile) çeker.
        Circuit Breaker ile korunmaktadır.

        Args:
            symbol: Sembol adı
            timeframe: Zaman dilimi
            limit: Kaç mum çekilecek
            params: Ek parametreler
            since: Başlangıç timestamp (ms) - Pagination için

        Returns:
            list: OHLCV verisi

        Raises:
            CircuitBreakerError: Circuit breaker açıkken
        """
        try:
            # [WSS NORMALİZASYON] Sembol CCXT formatına çevir
            symbol = normalize_symbol(symbol)

            # since parametresi varsa kullan (pagination için)
            if since is not None:
                data = await self.exchange.fetch_ohlcv(
                    symbol, timeframe, limit=limit, params=params, since=since
                )
            else:
                data = await self.exchange.fetch_ohlcv(
                    symbol, timeframe, limit=limit, params=params
                )
            return data
        except CircuitBreakerError:
            # Circuit breaker açık, bu hatayı doğrudan fırlat
            raise
        except Exception as e:
            # API key hatası varsa, anonim moda geç ve tekrar dene
            if "-2008" in str(e) or "AuthenticationError" in str(type(e)):
                logger.warning(f"⚠️ {symbol} API key hatası! Anonim moda geçiliyor...")
                self.exchange.apiKey = None
                self.exchange.secret = None
                try:
                    if since is not None:
                        data = await self.exchange.fetch_ohlcv(
                            symbol, timeframe, limit=limit, params=params, since=since
                        )
                    else:
                        data = await self.exchange.fetch_ohlcv(
                            symbol, timeframe, limit=limit, params=params
                        )
                    return data
                except Exception as retry_err:
                    logger.error(f"OHLCV Çekme Hatası ({symbol}): {retry_err}")
                    return []
            else:
                logger.error(f"OHLCV Çekme Hatası ({symbol}): {e}")
                return []

    @exchange_breaker
    async def fetch_available_markets(self):
        """Borsadaki tüm aktif işlem çiftlerini (Spot ve Vadeli) çeker."""
        try:
            # Hem Vadeli (Future) hem Spot piyasaları yükleyelim (Binance için kritik)
            if not self.exchange.markets:
                logger.info("Marketler henüz yüklenmemiş, Binance'ten çekiliyor...")
                try:
                    await self.exchange.load_markets({"type": "future"})
                    await self.exchange.load_markets({"type": "spot"})
                except Exception as auth_err:
                    # EĞER API ANAHTARI HATALIYSA (Code -2008), Anahtarları silip anonim dene
                    if "AuthenticationError" in str(type(auth_err)) or "-2008" in str(
                        auth_err
                    ):
                        logger.warning(
                            "Binance API anahtarları geçersiz! Anonim moda (Public) geçiliyor..."
                        )
                        self.exchange.apiKey = None
                        self.exchange.secret = None
                        self.exchange.enableRateLimit = (
                            True  # Anonim modda da rate limit kesinlikle açık kalsın
                        )
                        # Tekrar dene (Bu sefer şifresiz)
                        await self.exchange.load_markets({"type": "future"})
                        await self.exchange.load_markets({"type": "spot"})
                    else:
                        raise auth_err

            markets = self.exchange.markets
            logger.info(
                f"Borsadan toplam {len(markets) if markets else 0} ham market verisi çekildi."
            )

            available = []
            for symbol, m in markets.items():
                # Sadece aktif ve USDT bazlı olanları alalım
                if m.get("active") and m.get("quote") == "USDT":
                    m_type = (m.get("type") or "spot").lower()
                    m_sub_type = (m.get("subType") or "").lower()

                    # Kullanıcı dostu etiketleme sistemi
                    display_type = "SPOT"
                    if m_type == "swap" or m_sub_type == "perpetual":
                        display_type = "SÜRESİZ VADELİ (PERP)"
                    elif m_type == "future" or m_sub_type == "delivery":
                        display_type = f"TARİHLİ VADELİ ({m.get('info', {}).get('deliveryDate', 'DUR')})"

                    available.append(
                        {
                            "symbol": symbol,
                            "base": m["base"],
                            "type": display_type,
                            "id": m[
                                "id"
                            ],  # Bu ham Binance ID'sidir (BTCUSDT, ETHUSDT vb.)
                            "raw_type": m_type,
                        }
                    )

            logger.info(
                f"Filtreleme sonrası (Active + USDT) {len(available)} market listeye eklendi."
            )
            return sorted(available, key=lambda x: (x["symbol"], x["type"]))
        except Exception as e:
            logger.error(f"Market Listesi Çekme Hatası: {e}")
            return []

    async def watch_ticker_loop(self, symbol):
        """
        WebSocket üzerinden gerçek zamanlı anlık fiyat dinleyicisi.
        YENİ: CPU Darboğaz Koruması (Throttle) - Sadece açık pozisyonlar için ve max 1 saniyede bir

        EVENT-DRIVEN MİMARİ:
        - WebSocket'ten ticker alır
        - LivePriceUpdatedEvent fırlatır (Event Bus üzerinden)
        - Paper.py bu event'i dinler ve trailing stop kontrolü yapar
        - DIRECT CALL YOK (circular dependency kırıldı!)

        [WSS NORMALİZASYON] Sembol otomatik CCXT formatına çevrilir.
        """
        import time

        # ========================================================================
        # [WSS NORMALİZASYONU] Sembol CCXT formatına çevir
        # ========================================================================
        symbol = normalize_symbol(symbol)
        logger.info(f"📡 [WSS] {symbol} için WebSocket Ticker akışı başlatıldı.")

        # Throttle (geciktirici) mekanizması - CPU koruması
        last_update_time = {}  # {symbol: last_update_timestamp}
        UPDATE_INTERVAL = 1.0  # Saniye (max 1 saniyede bir güncelle)
        PRICE_CHANGE_THRESHOLD = 0.001  # %0.1 fiyat değişimi (anlamlı hareket)

        while True:
            try:
                # Gerçek zamanlı itme (push) teknolojisi ile anlık veriyi çek
                try:
                    ticker = await exchange_breaker._call_async(
                        self.exchange.watch_ticker, symbol
                    )
                    current_price = ticker["last"]
                except CircuitBreakerError:
                    # Circuit breaker is open. Wait a bit and try again.
                    logger.warning(
                        f"⚠️ [WSS] {symbol} watch_ticker circuit breaker open. Waiting..."
                    )
                    await asyncio.sleep(5)
                    continue

                # ========================================================================
                # CPU DARBOĞAZ KORUMASI (Throttle)
                # ========================================================================
                current_time = time.time()
                last_update = last_update_time.get(symbol, 0)
                time_since_update = current_time - last_update

                # Fiyat değişimi kontrolü
                price_changed_significantly = False
                if symbol in self._last_prices:
                    # Sıfıra bölme hatası veya sıfır/NaN fiyatı kontrolü
                    if self._last_prices[symbol] > 0:
                        price_change_pct = (
                            abs(current_price - self._last_prices[symbol])
                            / self._last_prices[symbol]
                        )
                        price_changed_significantly = (
                            price_change_pct >= PRICE_CHANGE_THRESHOLD
                        )
                    else:
                        price_changed_significantly = True

                # Güncelleme gerekli mi? (1 saniye geçti VEYA fiyat anlamlı değişti)
                should_update = (
                    time_since_update >= UPDATE_INTERVAL
                ) or price_changed_significantly

                if should_update:
                    # ========================================================================
                    # EVENT-DRIVEN: LivePriceUpdatedEvent fırlat (DIRECT CALL YOK!)
                    # ========================================================================
                    try:
                        event = LivePriceUpdatedEvent(
                            symbol=symbol,
                            price=current_price,
                            high=ticker.get("high"),
                            low=ticker.get("low"),
                            volume=ticker.get("baseVolume"),
                        )
                        await event_bus.publish(event.to_event())

                        last_update_time[symbol] = current_time

                        # Son fiyatı kaydet (değişim kontrolü için)
                        self._last_prices[symbol] = current_price

                        logger.debug(
                            f"📊 [TICKER] {symbol} @ ${current_price:.2f} (Event fırlatıldı)"
                        )

                    except Exception as event_err:
                        logger.error(
                            f"❌ [EVENT] LivePriceUpdatedEvent fırlatma hatası: {event_err}"
                        )

                    # ========================================================================
                    # GERÇEK ZAMANLI FLAT FILE GÜNCELLEME (Superalgos Mimarisi)
                    # ========================================================================
                    try:
                        # Her 60 saniyede bir yap (yeni mum kapandığında)
                        if int(current_time) % 60 < 5:  # İlk 5 saniye
                            from data.storage.parquet_lake import get_parquet_lake

                            lake = get_parquet_lake("binance")

                            from data.database import db_manager

                            # Son 1 saatin 1m verisini DB'den çek
                            klines_data = await db_manager.get_klines(
                                symbol, "1m", limit=60
                            )

                            if klines_data and len(klines_data) > 0:
                                import pandas as pd

                                df_1m = pd.DataFrame(
                                    klines_data,
                                    columns=[
                                        "timestamp",
                                        "open",
                                        "high",
                                        "low",
                                        "close",
                                        "volume",
                                    ],
                                )

                                # Bellek Optimizasyonu
                                df_1m = reduce_mem_usage(df_1m)

                                # [TZ FIX] Timestamp parse - SQLite string veya int olabilir
                                if df_1m["timestamp"].dtype == "object":
                                    # String datetime (SQLite)
                                    df_1m["timestamp"] = pd.to_datetime(
                                        df_1m["timestamp"], utc=True
                                    )
                                else:
                                    # Integer ms timestamp
                                    df_1m["timestamp"] = pd.to_datetime(
                                        df_1m["timestamp"], unit="ms", utc=True
                                    )

                                df_1m.set_index("timestamp", inplace=True)

                                # Parquet'e kaydet
                                await lake.save(symbol, "1m", df_1m, append=True)

                                logger.debug(
                                    f"💾 [PARQUET] {symbol} gerçek zamanlı güncellendi"
                                )

                    except Exception as e:
                        logger.debug(
                            f"⚠️ [PARQUET] Gerçek zamanlı güncelleme hatası: {e}"
                        )

                # else: Güncelleme gerek yok (throttle aktif) - CPU korunuyor

            except asyncio.CancelledError:
                logger.info(f"Ticker dinleme işlemi sonlandırıldı ({symbol}).")
                break
            except Exception as e:
                # EĞER API ANAHTARI HATALIYSA (Code -2008 veya Invalid API-key), Anahtarları temizleyip anonim moda geç
                error_str = str(e)
                if (
                    "-2008" in error_str
                    or "Invalid Api-Key ID" in error_str
                    or "AuthenticationError" in str(type(e))
                ):
                    logger.warning(
                        f"⚠️ {symbol} API key hatası! Anonim moda geçiliyor..."
                    )
                    self.exchange.apiKey = None
                    self.exchange.secret = None
                    self.exchange.enableRateLimit = (
                        True  # Anonim modda da rate limit kesinlikle açık kalsın
                    )
                    # Hemen ardından tekrar denemek üzere beklemeye gerek yok veya kısa bekle
                    await asyncio.sleep(1)
                else:
                    logger.error(f"WS Ticker İzleme Hatası ({symbol}): {e}")
                    await asyncio.sleep(5)  # Hata durumunda bağlantıyı 5sn soğut

    async def download_historical_data(
        self,
        symbol,
        timeframe="1m",
        start_date_str="2024-01-01",
        market_type="future",
        is_resume=False,
    ):
        """
        Belirli bir tarihten itibaren eksik olan tüm mum verilerini indirir.
        YENİ: SADECE 1m indirilir, diğer timeframe'ler resample ile oluşturulur (Veritabanı şişkinliği önleme).
        """
        import pandas as pd  # YENİ: Fonksiyon içinde import
        from data.database import db_manager

        # ========================================================================
        # YENİ: SADECE 1m İNDİR (Diğer TF'ler resample ile oluşturulur)
        # ========================================================================
        if timeframe != "1m":
            logger.info(
                f"🔄 [DATA] {symbol} için {timeframe} talep edildi, ancak SADECE 1m indiriliyor..."
            )
            logger.info("📊 [DATA] Resampling Mimarisi: Veritabanı %98 Optimize Edildi")
            logger.info(
                f"💡 [DATA] {timeframe} mumlar, 1m verisinden otomatik oluşturulacak (RAM üzerinde)"
            )

        # Her zaman 1m olarak indir (timeframe parametresini yoksay)
        download_timeframe = "1m"

        # [WSS NORMALİZASYON] Sembol ismini temizle ve CCXT formatına çevir
        # symbol.split('_')[0] yerine normalize_symbol kullan
        symbol = normalize_symbol(symbol)

        # Piyasa tipini standardize etme işlemi API katmanında yapıldığı için burada tekrar yapılmaz.

        # Market bilgilerini tazele (Hataları önlemek için kritik)
        if not self.exchange.markets or symbol not in self.exchange.markets:
            try:
                await self.exchange.load_markets({"type": market_type})
            except Exception as auth_err:
                # EĞER API ANAHTARI HATALIYSA (Code -2008), Anahtarları silip anonim dene
                if "AuthenticationError" in str(type(auth_err)) or "-2008" in str(
                    auth_err
                ):
                    logger.warning(
                        f"⚠️ {symbol} indirme hatası: Binance API anahtarları geçersiz! Anonim moda geçiliyor..."
                    )
                    self.exchange.apiKey = None
                    self.exchange.secret = None
                    self.exchange.enableRateLimit = (
                        True  # Anonim modda da rate limit kesinlikle açık kalsın
                    )
                    await self.exchange.load_markets({"type": market_type})
                else:
                    raise auth_err

        # Tarihi UTC olarak işle (Zaman dilimi kaymalarını önlemek için kritik)
        target_start_ts = (
            pd.to_datetime(start_date_str).tz_localize("UTC")
            if not pd.to_datetime(start_date_str).tzinfo
            else pd.to_datetime(start_date_str).tz_convert("UTC")
        )
        target_start_ms = int(target_start_ts.timestamp() * 1000)

        # Benzersiz görev anahtarı oluştur (Aynı sembolün spot ve vadelisini ayırmak için)
        key = f"{symbol}_{market_type}"

        # ========================================================================
        # YENİ: GAP DETECTION (Veritabanındaki mevcut veriyi kontrol et)
        # ========================================================================
        existing_end_ts = None
        try:
            # DB'den bu sembolün en son mumunu bul
            existing_end_ts = await db_manager.get_latest_kline_timestamp(symbol, "1m")

            if existing_end_ts:
                # SQLite string döndürebilir ('2026-03-14 22:37:00')
                # Ya da int (ms timestamp)
                if isinstance(existing_end_ts, str):
                    # String datetime'i ms'ye çevir
                    existing_end_dt = pd.to_datetime(existing_end_ts)
                    existing_end_ms = int(existing_end_dt.timestamp() * 1000)
                else:
                    # Zaten int (ms timestamp)
                    existing_end_ms = existing_end_ts
                    existing_end_dt = pd.to_datetime(existing_end_ms, unit="ms")

                logger.info(
                    f"📊 [GAP DETECTION] {symbol} için mevcut veri: ... → {existing_end_dt}"
                )

                # Eğer başlangıç tarihi mevcut veriden SONRA ise, mevcut veriyi kullan
                if target_start_ms >= existing_end_ms:
                    logger.info(
                        f"✅ [GAP DETECTION] {symbol} için veri zaten var! İndirme atlanıyor."
                    )
                    logger.info(f"   Mevcut: {existing_end_dt}")
                    logger.info(
                        f"   İstenen: {pd.to_datetime(target_start_ms, unit='ms')}"
                    )
                    return 0  # İndirme yapma, 0 mum indirildi
                else:
                    # Kullanıcı daha eski tarih istiyor, DB'deki veriyi kontrol et
                    existing_start = await db_manager.get_earliest_kline_timestamp(
                        symbol, "1m"
                    )
                    if existing_start:
                        if isinstance(existing_start, str):
                            existing_start_ms = int(
                                pd.to_datetime(existing_start).timestamp() * 1000
                            )
                        else:
                            existing_start_ms = existing_start

                        # Eğer kullanıcı DB'deki EN ESKİ veriden DAHA ESKİ tarih istiyorsa, indirmeye devam et
                        if target_start_ms < existing_start_ms:
                            logger.info(
                                "🔄 [GAP DETECTION] Kullanıcı daha eski tarih istiyor, indirme devam ediyor..."
                            )
                            logger.info(
                                f"   DB en eski: {pd.to_datetime(existing_start_ms, unit='ms')}"
                            )
                            logger.info(
                                f"   Kullanıcı: {pd.to_datetime(target_start_ms, unit='ms')}"
                            )
                        else:
                            # DB'de zaten var, sadece eksik günleri indir
                            since = existing_end_ms  # DB'deki son mumdan devam et
                            logger.info(
                                f"🔄 [GAP DETECTION] DB'deki son mumdan devam ediliyor: {pd.to_datetime(since, unit='ms')}"
                            )
        except Exception as gap_err:
            logger.warning(f"⚠️ [GAP DETECTION] Hata: {gap_err}")
            logger.info("🔄 Gap detection olmadan devam ediliyor...")
        # ========================================================================

        # Eğer bu işlem sıfırdan bir başlatmaysa (Kullanıcı yeni tarih seçtiyse),
        # Veritabanındaki son tarihe atlamayı DEVRE DIŞI bırakıyoruz.
        if (
            is_resume
            and key in self.active_downloads
            and self.active_downloads[key].get("current_ts", 0) > target_start_ms
        ):
            since = self.active_downloads[key]["current_ts"]
            logger.info(
                f"🔄 {key} indirme işlemi kaldığı yerden DEVAM EDİYOR: {pd.to_datetime(since, unit='ms')}"
            )
        else:
            # Kullanıcının seçtiği tarihten başla, şu ana kadar devam et
            since = target_start_ms
            logger.info(
                f"✨ {key} KULLANICININ SEÇTİĞİ TARİHTEN başlatılıyor: {pd.to_datetime(since, unit='ms')}"
            )
            current_time = pd.Timestamp.now(tz="UTC").strftime("%d/%m/%Y")
            logger.info(f"   Hedef: ŞU ANA KADAR ({current_time})")

        all_downloaded = 0
        limit = 1000  # Binance tek seferde max 1000 mum verir

        # İndirme başlangıç zamanı (speed tracking için)
        import time

        start_time = time.time()
        last_ts = since  # Son mum timestamp'i
        latest_ts = None  # DB'deki son mum (GAP CHECK için)

        logger.info(
            f"🚀 {key} ({timeframe}) indirme BAŞLADI: {pd.to_datetime(since, unit='ms')} (GEÇMİŞTEN GELECEĞE)"
        )
        self.download_stops[key] = False
        self.download_pauses[key] = False
        self.active_downloads[key] = {
            "symbol": symbol,
            "timeframe": timeframe,
            "market_type": market_type,
            "start_date": start_date_str,
            "since": since,
            "current_ts": since,
            "target_start_ms": target_start_ms,
            "status": "running",
            "progress": 0,  # İlerleme yüzdesi
            "speed": 0,  # Mum/saniye
        }

        await db_manager.save_download_task(self.active_downloads[key])

        while True:
            try:
                # Kullanıcı durdurdu mu?
                if self.download_stops.get(key):
                    logger.info(
                        f"🛑 {key} indirme işlemi kullanıcı tarafından DURDURULDU."
                    )
                    if key in self.active_downloads:
                        self.active_downloads[key]["status"] = "stopped"
                        await db_manager.save_download_task(self.active_downloads[key])
                    break

                # Kullanıcı duraklattı mı?
                while self.download_pauses.get(key):
                    if (
                        key in self.active_downloads
                        and self.active_downloads[key]["status"] != "paused"
                    ):
                        self.active_downloads[key]["status"] = "paused"
                        await db_manager.save_download_task(self.active_downloads[key])
                    await asyncio.sleep(2)  # 2 saniyede bir duraklatma kontrolü yap

                if key not in self.active_downloads:
                    break  # Görev silinmişse döngüden çık

                self.active_downloads[key]["status"] = "running"

                # CCXT rates limitine göre fetch yap
                # YENİ: Her zaman 1m olarak indir (download_timeframe kullan)
                # NOT: params={'type': market_type} API key gerektiriyor, bu yüzden kaldırdık
                # API key yoksa otomatik olarak public endpoint kullanılır
                try:
                    ohlcv = await self.exchange.fetch_ohlcv(
                        symbol, download_timeframe, since=since, limit=limit
                    )
                except Exception as fetch_err:
                    # Binance rate limit veya network hatası
                    logger.warning(f"⚠️ {symbol} veri çekme hatası: {fetch_err}")
                    logger.info("⏳ 10 saniye bekleniyor...")
                    await asyncio.sleep(10)
                    continue

                if not ohlcv or len(ohlcv) < 1:
                    logger.info(
                        f"🏁 {symbol} için borsa artık veri dönmüyor (Son Tarih: {pd.to_datetime(since, unit='ms')})."
                    )
                    break

                # ========================================================================
                # GAP CHECK: DB'deki son mumu kontrol et
                # ========================================================================
                last_candle_ts = ohlcv[-1][
                    0
                ]  # SON mum (en yeni) - çünkü geçmişten geleceğe gidiyoruz

                # DB'deki son mumu al (eğer daha önce almadıysak)
                if latest_ts is None:
                    try:
                        latest_ts = await db_manager.get_latest_kline_timestamp(
                            symbol, timeframe
                        )
                        if latest_ts and isinstance(latest_ts, str):
                            latest_ts = int(
                                pd.to_datetime(latest_ts).timestamp() * 1000
                            )
                    except Exception:
                        pass

                # Eğer indirdiğimiz son mum DB'deki son mumdan SONRA ise, devam et (yeni mumlar)
                # Eğer indirdiğimiz son mum DB'deki son mumdan ÖNCE ise, atla (eski veri)
                if latest_ts and last_candle_ts <= latest_ts:
                    logger.debug(
                        f"⏭️ [GAP CHECK] {symbol} bu mumlar DB'de var, atlanıyor."
                    )
                    logger.debug(
                        f"   İndirilen son mum: {pd.to_datetime(last_candle_ts, unit='ms')}"
                    )
                    logger.debug(
                        f"   DB son mum: {pd.to_datetime(latest_ts, unit='ms')}"
                    )
                    # since'i güncelle, devam et
                # ========================================================================

                # Veritabanına toplu kayıt (her mum için ayrı INSERT yerine batch)
                klines_to_save = []
                new_mum_count = 0
                existing_mum_count = 0

                for candle in ohlcv:
                    candle[0]

                    # DB'de bu mum var mı kontrol et (hızlı skip)
                    # Not: save_kline içinde INSERT OR IGNORE var, ama önce kontrol edelim
                    klines_to_save.append((symbol, candle, timeframe))
                    new_mum_count += 1

                if not klines_to_save:
                    continue

                symbol_to_save = klines_to_save[0][0]
                timeframe_to_save = klines_to_save[0][2]
                candles_to_save = [k[1] for k in klines_to_save]

                # Toplu kayıt (tek transaction içinde)
                try:
                    await db_manager.save_klines_bulk(
                        symbol_to_save, candles_to_save, timeframe_to_save
                    )
                except Exception as db_err:
                    logger.error(f"⚠️ {symbol} DB yazma hatası: {db_err}")
                    # Locked hatası varsa 0.5 saniye bekle ve tekrar dene
                    if "database is locked" in str(db_err):
                        logger.warning("⏳ Database locked, 0.5 saniye bekleniyor...")
                        await asyncio.sleep(0.5)
                        # Tekrar dene
                        try:
                            await db_manager.save_klines_bulk(
                                symbol_to_save, candles_to_save, timeframe_to_save
                            )
                        except Exception:
                            existing_mum_count += len(
                                klines_to_save
                            )  # İkinci hata = tüm parti başarısız / zaten var
                    else:
                        existing_mum_count += len(klines_to_save)

                last_ts = ohlcv[-1][0]
                all_downloaded += new_mum_count

                if new_mum_count > 0:
                    logger.debug(f"📝 {symbol} {new_mum_count} yeni mum kaydedildi")

                # Şu anki zaman
                now_ms = int(time.time() * 1000)

                # İLERLEME YÜZDESİ HESAPLAMA
                # Formül: (şu ana kadar indirilen zaman / toplam hedef zaman) * 100
                if now_ms > target_start_ms:
                    progress = (
                        (last_ts - target_start_ms) / (now_ms - target_start_ms)
                    ) * 100
                    progress = min(100, progress)  # %100'ü geçmesini engelle
                else:
                    progress = 0

                # İNDİRME HIZI HESAPLAMA (mum/saniye)
                elapsed_time = time.time() - start_time  # Geçen süre (saniye)
                if elapsed_time > 0:
                    speed = all_downloaded / elapsed_time
                else:
                    speed = 0

                # Her 5000 mumda bir DB güncelle (daha az locked hatası)
                if all_downloaded % 5000 == 0:
                    logger.info(
                        f"📥 {symbol} İlerleme: {all_downloaded} mum kaydedildi... [Şu anki Tarih: {pd.to_datetime(last_ts, unit='ms')}]"
                    )
                    # DB görevini güncelle
                    if key in self.active_downloads:
                        self.active_downloads[key]["current_ts"] = last_ts
                        self.active_downloads[key]["progress"] = round(progress, 2)
                        self.active_downloads[key]["speed"] = round(speed, 2)
                        try:
                            await db_manager.save_download_task(
                                self.active_downloads[key]
                            )
                        except Exception as db_err:
                            logger.warning(
                                f"⚠️ DB güncelleme hatası (devam ediliyor): {db_err}"
                            )
                else:
                    # Her 500 mumda bir progress ve speed güncelle (RAM'de)
                    if all_downloaded % 500 == 0 and key in self.active_downloads:
                        self.active_downloads[key]["progress"] = round(progress, 2)
                        self.active_downloads[key]["speed"] = round(speed, 2)
                    logger.debug(
                        f"📥 {symbol} {len(ohlcv)} mum indirildi. Son: {pd.to_datetime(last_ts, unit='ms')}"
                    )

                # Eğer son gelen mum anlık zamana çok yakınsa dur
                import time

                now_ms = int(time.time() * 1000)
                if last_ts >= now_ms - 60000:  # Son 1 dakika
                    logger.info(
                        f"🎯 {symbol} indirme işlemi güncel zamana (UTC) ulaştı."
                    )
                    break

                # GEÇMİŞTEN GELECEĞE: Bir sonraki batch için son mumdan devam et
                since = last_ts + 1  # Son mumdan bir milisaniye sonra
                if key in self.active_downloads:
                    self.active_downloads[key]["current_ts"] = since

                # Dinamik sleep: Sayfalama (Pagination) Beklemesi
                # Anonim modda (API key yoksa) limitler çok daha kısıtlıdır.
                is_anonymous = not (self.exchange.apiKey and self.exchange.secret)

                if is_anonymous:
                    # Anonim modda banlanmamak için her sayfada 1 saniye kibarca bekle
                    await asyncio.sleep(1.0)
                else:
                    # API key varsa hızlandır, ama yine de her 5000 mumda bir DB locked koruması yap
                    if all_downloaded % 5000 == 0:
                        await asyncio.sleep(2)  # Her 5000 mumda bir 2 saniye bekle
                    else:
                        await asyncio.sleep(0.1)  # Normalde 100ms yeterli

            except Exception as e:
                # EĞER HATA RATE LIMIT (429 vb.) veya Borsa hatası ise, devreyi açık bırakmak yerine bekle
                if (
                    "RateLimitExceeded" in str(type(e))
                    or "429" in str(e)
                    or "CircuitBreakerError" in str(type(e))
                ):
                    logger.warning(
                        f"⚠️ {symbol} Rate Limit veya Circuit Breaker devrede! 10 saniye bekleniyor ve kalındığı yerden devam edilecek... Hata: {e}"
                    )
                    await asyncio.sleep(10)
                else:
                    logger.error(f"⚠️ {symbol} Veri İndirme Döngüsünde Hata: {e}")
                    await asyncio.sleep(5)

        is_stopped = self.download_stops.get(key, False)

        if is_stopped:
            logger.info(
                f"⏸️ {key} Veri İndirme Görevi Beklemeye / İptal Edilmeye Alındı. Toplam {all_downloaded} yeni veri eklendi."
            )
            if key in self.active_downloads:
                self.active_downloads[key]["status"] = "stopped"
                self.active_downloads[key]["progress"] = 0  # Durduruldu
                await db_manager.save_download_task(self.active_downloads[key])
                del self.active_downloads[key]
        else:
            logger.info(
                f"✅ {key} Veri İndirme TAMAMLANDI. Toplam {all_downloaded} yeni veri eklendi."
            )
            logger.info("🏗️ [PARQUET LAKE] Parquet Engine'e Tam Geçiş Sağlandı")

            # ========================================================================
            # YENİ: PARQUET LAKE - Otomatik TF oluşturma (JSON YOK!)
            # ========================================================================
            try:
                from data.storage.parquet_lake import get_parquet_lake

                lake = get_parquet_lake("binance")

                # 1m veriyi DB'den çek
                # İndirme bitince db'deki TÜM veriyi (limit 2,000,000 yeterince büyük) Parquet'e toptan (overwrite) kaydediyoruz
                limit_1m = 2000000  # Tüm geçmişi çekmek için çok büyük bir limit
                # [WSS NORMALİZASYON] symbol.split('_')[0] yerine normalize_symbol kullan
                symbol_clean = normalize_symbol(symbol)

                logger.info(
                    f"📊 [PARQUET] {symbol_clean} için Parquet oluşturuluyor... (Tüm veri)"
                )

                klines_data = await db_manager.get_klines(
                    symbol_clean, "1m", limit=limit_1m
                )

                if klines_data and len(klines_data) > 0:
                    import pandas as pd

                    df_1m = pd.DataFrame(
                        klines_data,
                        columns=["timestamp", "open", "high", "low", "close", "volume"],
                    )

                    # Bellek Optimizasyonu
                    df_1m = reduce_mem_usage(df_1m)

                    if df_1m["timestamp"].dtype == "object":
                        df_1m["timestamp"] = pd.to_datetime(
                            df_1m["timestamp"], utc=True
                        )
                    else:
                        df_1m["timestamp"] = pd.to_datetime(
                            df_1m["timestamp"], unit="ms", utc=True
                        )

                    df_1m.set_index("timestamp", inplace=True)

                    # 1m'i Parquet'e kaydet (overwrite modunda, append=False)
                    await lake.save(symbol_clean, "1m", df_1m, append=False)
                    logger.info(
                        f"✅ [PARQUET] {symbol_clean} 1m → Parquet kaydedildi ({len(df_1m)} satır)"
                    )

                    # Diğer TF'leri oluştur ve kaydet (TÜM Superalgos timeframeleri)
                    all_timeframes = [
                        "2m",
                        "3m",
                        "4m",
                        "5m",
                        "10m",
                        "15m",
                        "20m",
                        "30m",
                        "40m",
                        "45m",
                        "1h",
                        "2h",
                        "3h",
                        "4h",
                        "6h",
                        "8h",
                        "12h",
                        "24h",
                    ]

                    for tf in all_timeframes:
                        from data.indicators import StrategyIndicators

                        # Resampling (look-ahead bias korumalı)
                        df_tf = StrategyIndicators.resample_data(df_1m, tf)
                        df_tf = df_tf.dropna()

                        if not df_tf.empty:
                            await lake.save(symbol_clean, tf, df_tf, append=False)
                            logger.info(
                                f"✅ [PARQUET] {tf} → Parquet kaydedildi: {len(df_tf)} satır"
                            )

                    logger.info(
                        f"🎉 [PARQUET] {symbol} için TÜM timeframe'ler ({len(all_timeframes)}) Parquet'e kaydedildi!"
                    )
                else:
                    logger.warning(f"⚠️ [PARQUET] DB'den 1m veri çekilemedi: {symbol}")

            except Exception as e:
                logger.error(f"❌ [PARQUET] Oluşturma hatası: {e}")
                logger.debug(f"Stack trace: {e}", exc_info=True)

            if key in self.active_downloads:
                self.active_downloads[key]["status"] = "completed"
                self.active_downloads[key]["progress"] = 100  # Tamamlandı
                self.active_downloads[key]["speed"] = 0  # Hız sıfırla
                await db_manager.save_download_task(self.active_downloads[key])
                del self.active_downloads[key]

            # ========================================================================
            # YENİ: İndirme tamamlandı - Frontend'e haber ver (otomatik envanter yenileme)
            # ========================================================================
            try:
                from shared.events import event_bus

                event_bus.emit(
                    "data_download_completed",
                    {
                        "symbol": symbol,
                        "market_type": market_type,
                        "timeframe": timeframe,
                        "candles_downloaded": all_downloaded,
                    },
                )
                logger.debug("📢 [EVENT] data_download_completed event gönderildi")
            except Exception as event_err:
                logger.debug(f"⚠️ Event gönderme hatası: {event_err}")

        return all_downloaded

    async def _process_bot_task(
        self,
        paper_engine,
        bot_id: str,
        df: pd.DataFrame,
        htf_trend: str,
        regime: str,
        htf_trends: dict = None,
    ):
        """
        Tek bir bot için sinyal işleme task'ı (async, izole, hata korumalı).
        EVENT-DRIVEN: Artık doğrudan fonksiyon çağrısı yerine Event Bus kullanıyor.
        YENİ: Katı Mum Kapanış Kilidi (Strict Candle Close Lock)

        Args:
            paper_engine: PaperTrader instance (geriye dönük uyumluluk)
            bot_id: İşlenecek bot ID
            df: İndikatörlerle DataFrame
            current_price: Güncel fiyat (SADECE GERİYE UYUMLULUK - KULLANILMAZ)
            htf_trend: Yüksek timeframe trend (major HTF)
            regime: Piyasa rejimi
            htf_trends: HTF trend sözlüğü (örn: {'5m': 'BULL', '15m': 'BEAR'})
        """
        try:
            # 🔥 [BOT TASK DEBUG] Fonksiyon başlangıcı
            logger.info(f"🔥 [BOT TASK] _process_bot_task BAŞLADI: bot_id={bot_id}")

            # Bot bilgilerini al
            bot_info = paper_engine.active_bots.get(bot_id, {})

            logger.info(f"🔍 [BOT INFO] bot_id={bot_id}, bot_info={bot_info}")

            # 🔥 DEBUG: bot_info tipini kontrol et
            if not isinstance(bot_info, dict):
                logger.error(
                    f"❌ [BOT TASK] bot_info is not a dict! Type: {type(bot_info)}, Value: {bot_info}"
                )
                logger.error(
                    f"   🔥 [BOT TASK] paper_engine.active_bots keys: {list(paper_engine.active_bots.keys())}"
                )
                logger.error(f"   🔥 [BOT TASK] Requested bot_id: {bot_id}")
                return  # Erken çık, crash etme

            symbol = bot_info.get("symbol", "")
            strategy_id = bot_info.get("strategy_id", "")
            timeframe = bot_info.get("timeframe", "1m")

            logger.info(
                f"📊 [BOT PARAMS] symbol={symbol}, strategy_id={strategy_id}, timeframe={timeframe}"
            )

            # ========================================================================
            # KATI MUM KAPANış KİLİDİ İPTAL EDİLDİ
            # ========================================================================
            # Not: run_strategy_poller, yeni bir mum başladığı anda _process_bot_task
            # fonksiyonunu tam bir kere çağırır. Bu esnada son mum zaten yeni açılan
            # mum olurken bir önceki mum tamamlanmıştır. Strateji üretme işleminin
            # engellenmemesi için bu kilit devredışı bırakıldı.

            # Strateji sinyali üret
            strategy = paper_engine.strategies.get(symbol)

            # 🔥 DEBUG: Strateji ve DataFrame kontrolü
            logger.info(
                f"🔍 [DEBUG] strategy={strategy is not None}, df.empty={df.empty}, len(df)={len(df)}"
            )
            logger.info(
                f"🔍 [DEBUG] paper_engine.strategies.keys()={list(paper_engine.strategies.keys()) if paper_engine else 'None'}"
            )

            if strategy is None or df.empty or len(df) < 50:
                logger.warning(
                    f"⏭️ [SINYAL] {symbol} strateji yok veya veri yetersiz (strategy={strategy is not None}, df_len={len(df)})"
                )
                return

            # ============================================
            # YENİ MİMARİ: Toplu İndikatör Hesaplama
            # Sinyal kararı verilmeden önce strateji spesifik indikatörleri hesapla
            # ============================================
            if hasattr(strategy, "calculate_indicators"):
                df = strategy.calculate_indicators(df)

            latest_candle = df.iloc[-1]

            # ============================================
            # INDIATORS_PAYLOAD OLUŞTUR (ML ve Event için)
            # ============================================
            # latest_candle'ı dict'e çevir ve indicators_payload oluştur
            indicators_payload = latest_candle.to_dict()

            # 🔥 DEBUG: Indikatör kontrolü
            logger.debug(
                f"🔍 [INDICATORS] latest_candle columns: {list(latest_candle.index)[:10]}..."
            )
            logger.debug(
                f"🔍 [INDICATORS] RSI_14={latest_candle.get('RSI_14', 'YOK')}, EMA_200={latest_candle.get('EMA_200', 'YOK')}"
            )

            # Strateji sinyali üret
            raw_signal_int = strategy.generate_signal(latest_candle)

            # 🔥 DEBUG: Strateji sinyali
            logger.info(
                f"🔍 [STRATEGY] {symbol} raw signal: {raw_signal_int} (type: {type(raw_signal_int).__name__})"
            )

            # 🔧 SİNYAL ADAPTER: int → dict dönüşümü (SADECE LOGLAMA İÇİN)
            signal_dict_for_logging = {}
            if isinstance(raw_signal_int, int):
                signal_map = {
                    0: {"signal": "SHORT", "confidence": 1.0},
                    1: {"signal": "HOLD", "confidence": 0.0},
                    2: {"signal": "LONG", "confidence": 1.0},
                }
                signal_dict_for_logging = signal_map.get(
                    raw_signal_int, {"signal": "HOLD", "confidence": 0.0}
                )
                logger.debug(f"🔧 [ADAPTER] int→dict: {signal_dict_for_logging}")

            # ========================================================================
            # ✅ BUG FIX 1: Fiyatı her zaman sinyalin üretildiği mumdan al
            # ========================================================================
            signal_price = float(latest_candle["close"])

            # 🎯 SİNYAL LOGLAMA
            signal_type = signal_dict_for_logging.get("signal", "NONE")
            logger.info(
                f"🎯 [SINYAL] {symbol} | {signal_type} | Fiyat: ${signal_price:.2f} | TF: {timeframe}"
            )
            logger.info(
                f"   📊 Strateji: {strategy_id} | HTF: {htf_trend} | Rejim: {regime}"
            )

            # 🧠 ML CONFIDENCE SCORE
            ml_confidence = None

            try:
                from ml.inference import get_ml_prediction

                # Get the direction based on raw_signal_int
                # 2 -> long, 0 -> short. If hold (1), ml confidence check might be skipped,
                # but we default to 'long' or check only if signal != 1
                if raw_signal_int in [0, 2]:
                    ml_direction = "long" if raw_signal_int == 2 else "short"
                    ml_result = get_ml_prediction(symbol, timeframe, ml_direction, indicators_payload)
                    if ml_result:
                        ml_confidence = ml_result.get("confidence", 0)
                        ml_result.get("prediction", "HOLD")
                        if "ml_confidence" in signal_dict_for_logging:
                            signal_dict_for_logging["ml_confidence"] = ml_confidence
            except Exception as ml_err:
                logger.debug(f"⚠️ [ML] Model yüklenemedi: {ml_err}")
                if "ml_confidence" in signal_dict_for_logging:
                    signal_dict_for_logging["ml_confidence"] = None

            # ========================================================================
            # ✅ BUG FIX 2: Event'e doğru tipleri (int, float) gönder
            # ========================================================================
            event = SignalGeneratedEvent(
                bot_id=bot_id,
                symbol=symbol,
                signal=raw_signal_int,
                price=signal_price,
                timeframe=timeframe,
                indicators=indicators_payload,
                metadata={
                    "htf_trend": htf_trend,
                    "htf_trends": htf_trends,
                    "regime": regime,
                    "strategy_id": strategy_id,
                    "ml_confidence": ml_confidence,
                },
            ).to_event(source="exchange_manager")

            await event_bus.publish(event)

            logger.debug(f"✅ [EVENT] {symbol} sinyali yayınlandı")

        except Exception as e:
            logger.error(f"❌ [BOT TASK] {bot_id} işlem hatası: {e}")
            raise

    async def run_strategy_poller(self, symbol, timeframe="1m"):
        """
        FINAL HYBRID (Local DB + REST Pagination + WebSocket Push) Strateji Motoru

        [WSS NORMALİZASYON] Sembol otomatik CCXT formatına çevrilir.
        """
        from core.paper import paper_engine
        from data.indicators import StrategyIndicators
        from data.database import db_manager
        import ccxt

        # ========================================================================
        # [WSS NORMALİZASYON] Sembol CCXT formatına çevir
        # ========================================================================
        symbol = normalize_symbol(symbol)

        # 🔥 KRITIK LOGLAMA - Poller başlangıcını izle
        logger.debug(f"🔥 [POLLER DEBUG] {symbol} run_strategy_poller BAŞLADI")
        logger.debug(f"🔥 [POLLER DEBUG] symbol={symbol}, timeframe={timeframe}")
        logger.info(
            f"🚀 [FINAL HYBRID] {symbol} için strateji poller başlatılıyor ({timeframe})..."
        )

        logger.debug(f"📊 [POLLER DEBUG] paper_engine={paper_engine is not None}")
        logger.debug(
            f"📊 [POLLER DEBUG] active_bots={len(paper_engine.active_bots) if paper_engine else 0}"
        )

        # ========================================================================
        # YENİ: VERİ BOŞLUĞU KONTROLÜ (Gap Detection & Auto-Fill) - Refactored
        # ========================================================================
        logger.debug("🔥 [GAP CHECK] check_and_fill_gap başlatılıyor...")
        try:
            from core.trading.services.data_sync import data_synchronizer

            # ARKA PLANDA ÇALIŞTIR - event loop'u kilitleme!
            await asyncio.wait_for(
                data_synchronizer.check_and_fill_gap(symbol, self),
                timeout=30.0,  # 30 saniye timeout
            )
            logger.debug("✅ [GAP CHECK] check_and_fill_gap TAMAMLANDI")
        except asyncio.TimeoutError:
            logger.warning(
                "⚠️ [GAP CHECK] check_and_fill_gap TIMEOUT (30s) - devam ediliyor"
            )
        except Exception as gap_err:
            logger.error(f"❌ [GAP CHECK] check_and_fill_gap HATA: {gap_err}")
            logger.warning("⚠️ [GAP CHECK] Gap check atlandı, devam ediliyor")

        # ============================================
        # 1. LOCAL DB FIRST: SQLite'dan geçmiş veriyi çek
        # ============================================
        logger.info(f"📚 [LOCAL DB] {symbol} için yerel veritabanı kontrol ediliyor...")
        ohlcv_df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        ohlcv_df.index.name = "timestamp"
        logger.info("✅ [LOCAL DB] DataFrame oluşturuldu")

        # ============================================
        # 1. LOCAL DB FIRST: SQLite'dan geçmiş veriyi çek
        # ============================================
        logger.info(f"📚 [LOCAL DB] {symbol} için yerel veritabanı kontrol ediliyor...")
        ohlcv_df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        ohlcv_df.index.name = "timestamp"

        try:
            # Yerel veritabanından son 1500 mumu çek
            db_ohlcv = await db_manager.get_klines(symbol, timeframe="1m", limit=1500)

            if db_ohlcv and len(db_ohlcv) > 0:
                logger.info(f"OK [LOCAL DB] {symbol} için {len(db_ohlcv)} mum bulundu.")

                # DataFrame'e dönüştür
                ohlcv_df = pd.DataFrame(
                    db_ohlcv,
                    columns=["timestamp", "open", "high", "low", "close", "volume"],
                )

                # Bellek Optimizasyonu
                ohlcv_df = reduce_mem_usage(ohlcv_df)

                # SQLite'dan gelen timestamp string veya int olabilir, her ikisini de parse et
                if ohlcv_df["timestamp"].dtype == "object":
                    # String formatında (SQLite datetime)
                    ohlcv_df["timestamp"] = pd.to_datetime(
                        ohlcv_df["timestamp"], utc=True
                    )
                else:
                    # Integer formatında (ms timestamp)
                    ohlcv_df["timestamp"] = pd.to_datetime(
                        ohlcv_df["timestamp"], unit="ms", utc=True
                    )

                ohlcv_df.set_index("timestamp", inplace=True)

                # 🔥 TIMEZONE DÜZELTMESİ: Tüm index'i UTC yap
                if ohlcv_df.index.tzinfo is None:
                    ohlcv_df.index = ohlcv_df.index.tz_localize("UTC")
                else:
                    ohlcv_df.index = ohlcv_df.index.tz_convert("UTC")

                last_db_time = ohlcv_df.index[-1]
                current_time = pd.Timestamp.now(tz="UTC")

                # Timezone düzeltmesi (last_db_time tz-naive olabilir)
                if last_db_time.tzinfo is None:
                    last_db_time = last_db_time.tz_localize("UTC")

                time_diff = current_time - last_db_time

                logger.info(
                    f"OK [LOCAL DB] Son mum: {last_db_time}, Şu an: {current_time}, Fark: {time_diff}"
                )

                # ============================================
                # 2. GAP DETECTION + PAGINATION (Sınırsız Gap Fill) - KURAL 2
                # ============================================
                if time_diff.total_seconds() > 120:  # 2 dakikadan fazla boşluk
                    gap_minutes = time_diff.total_seconds() / 60
                    logger.info(
                        f"🔍 [GAP DETECT] {gap_minutes:.1f} dakika boşluk tespit edildi, REST API ile dolduruluyor..."
                    )

                    # PAGINATION: Binance limit (1000 mum) aşılırsa sayfalandır
                    gap_start_ms = int(last_db_time.timestamp() * 1000)
                    total_fetched = 0
                    page = 0
                    limit = 1000  # Binance API limit

                    all_gap_ohlcv = []

                    logger.info(
                        f"📄 [PAGINATION] Gap fill başlatılıyor (limit={limit} mum/sayfa)..."
                    )

                    while True:  # Sınırsız döngü - tüm gap dolana kadar
                        page += 1
                        logger.debug(
                            f"📄 [PAGINATION] Sayfa {page} çekiliyor (since={gap_start_ms})..."
                        )

                        # Bu sayfanın mumlarını çek
                        try:
                            # Use exchange directly to bypass custom circuit breaker wrapper for gap fill retry logic
                            page_ohlcv = await self.exchange.fetch_ohlcv(
                                symbol, timeframe="1m", since=gap_start_ms, limit=limit
                            )
                        except Exception as fetch_err:
                            if "RateLimitExceeded" in str(
                                type(fetch_err)
                            ) or "429" in str(fetch_err):
                                logger.warning(
                                    f"⚠️ [PAGINATION] {symbol} Rate Limit devrede! 10 saniye bekleniyor ve devam edilecek..."
                                )
                                await asyncio.sleep(10)
                                page -= 1  # retry this page
                                continue
                            else:
                                logger.error(
                                    f"⚠️ [PAGINATION] {symbol} Hata: {fetch_err}"
                                )
                                break

                        if not page_ohlcv or len(page_ohlcv) == 0:
                            logger.warning(
                                f"WARNING [PAGINATION] Sayfa {page} boş geldi, döngü sonlandırılıyor."
                            )
                            break

                        all_gap_ohlcv.extend(page_ohlcv)
                        total_fetched += len(page_ohlcv)

                        logger.info(
                            f"OK [PAGINATION] Sayfa {page}: {len(page_ohlcv)} mum çekildi (Toplam: {total_fetched})"
                        )

                        # Eğer çekilen mum sayısı limit'ten azsa, daha fazla mum yok demektir
                        if len(page_ohlcv) < limit:
                            logger.info(
                                f"OK [PAGINATION] Tüm gap mumları çekildi (Toplam: {total_fetched} mum)"
                            )
                            break

                        # Son mumun timestamp'ini al, bir sonraki sayfa için
                        last_fetched_ms = page_ohlcv[-1][0]

                        # Eğer son timestamp güncel zamana yakınsa, döngüyü sonlandır
                        current_ms = int(pd.Timestamp.now(tz="UTC").timestamp() * 1000)
                        if (
                            abs(current_ms - last_fetched_ms) < 60000
                        ):  # 1 dakika tolerans
                            logger.info(
                                f"OK [PAGINATION] Güncel zamana ulaşıldı (Toplam: {total_fetched} mum)"
                            )
                            break

                        # Bir sonraki sayfa için since parametresini güncelle
                        gap_start_ms = last_fetched_ms

                        # Rate limit koruması (Binance: 1200 istek/dakika)
                        is_anonymous = not (
                            self.exchange.apiKey and self.exchange.secret
                        )
                        if is_anonymous:
                            await asyncio.sleep(1.0)
                        else:
                            await asyncio.sleep(0.1)

                    # TÜM gap mumlarını SQLite'a kaydet
                    if all_gap_ohlcv and len(all_gap_ohlcv) > 0:
                        logger.info(
                            f"💾 [SAVE] {len(all_gap_ohlcv)} gap mumu SQLite'a kaydediliyor..."
                        )

                        try:
                            await db_manager.save_klines_bulk(
                                symbol, all_gap_ohlcv, "1m"
                            )
                            logger.info(
                                "OK [SAVE] Tüm gap mumları SQLite'a kaydedildi (BULK)."
                            )
                        except Exception as save_err:
                            logger.error(
                                f"ERROR [SAVE] SQLite kayıt hatası: {save_err}"
                            )

                        # DataFrame'e dönüştür
                        gap_df = pd.DataFrame(
                            all_gap_ohlcv,
                            columns=[
                                "timestamp",
                                "open",
                                "high",
                                "low",
                                "close",
                                "volume",
                            ],
                        )

                        # Bellek Optimizasyonu
                        gap_df = reduce_mem_usage(gap_df)

                        if gap_df["timestamp"].dtype == "object":
                            gap_df["timestamp"] = pd.to_datetime(
                                gap_df["timestamp"], utc=True
                            )
                        else:
                            gap_df["timestamp"] = pd.to_datetime(
                                gap_df["timestamp"], unit="ms", utc=True
                            )

                        gap_df.set_index("timestamp", inplace=True)

                        # 🔥 TIMEZONE DÜZELTMESİ: gap_df'i UTC yap
                        if gap_df.index.tzinfo is None:
                            gap_df.index = gap_df.index.tz_localize("UTC")

                        # DB verisi ile REST verisini birleştir (concat)
                        ohlcv_df = pd.concat([ohlcv_df, gap_df])

                        # Duplicate kayıtları temizle (index bazlı)
                        ohlcv_df = ohlcv_df[~ohlcv_df.index.duplicated(keep="last")]
                        ohlcv_df = ohlcv_df.sort_index()

                        logger.info(
                            f"OK [STITCH] DB + REST birleştirildi: Toplam {len(ohlcv_df)} mum"
                        )

                        # ========================================================================
                        # YENİ: GAP FILL SONRASI FLAT FILE GÜNCELLEME
                        # ========================================================================
                        try:
                            from data.ohlcv_storage import get_storage

                            storage = get_storage()

                            # Tüm veriyi flat file'a kaydet
                            save_df = ohlcv_df.copy()
                            save_df.reset_index(inplace=True)
                            save_df["timestamp"] = (
                                pd.to_numeric(save_df["timestamp"]) // 10**6
                            )

                            storage.save_ohlcv(symbol, "1m", save_df)
                            logger.info(
                                f"✅ [STORAGE] {symbol} flat file güncellendi ({len(save_df)} mum)"
                            )

                            # Diğer TF'leri de güncelle (resample)
                            all_timeframes = ["5m", "15m", "1h", "4h"]
                            for tf in all_timeframes:
                                from data.indicators import StrategyIndicators

                                df_tf = StrategyIndicators.resample_data(save_df, tf)
                                df_tf = df_tf.dropna()
                                if not df_tf.empty:
                                    storage.save_ohlcv(symbol, tf, df_tf)
                            logger.info(
                                f"✅ [STORAGE] {symbol} için t��m TF'ler güncellendi"
                            )

                        except Exception as storage_err:
                            logger.warning(
                                f"⚠️ [STORAGE] Flat file güncelleme hatası: {storage_err}"
                            )
                    else:
                        logger.warning(
                            "WARNING [REST GAP] Eksik mum çekilemedi, sadece DB verisi kullanılıyor."
                        )
                else:
                    logger.info(
                        "OK [NO GAP] Veritabanı güncel, REST API çağrısına gerek yok."
                    )

                    # ========================================================================
                    # YENİ: NO GAP DURUMUNDA DA FLAT FILE OLUŞTUR
                    # ========================================================================
                    # Eğer flat file yoksa, DB'den oluştur
                    # ========================================================================
                    try:
                        from data.ohlcv_storage import get_storage

                        storage = get_storage()

                        # Flat file var mı kontrol et
                        from datetime import datetime, timedelta

                        end_date = datetime.utcnow()
                        start_date = end_date - timedelta(
                            days=7
                        )  # Son 7 günü kontrol et

                        ff_df = storage.load_ohlcv(symbol, "1m", start_date, end_date)

                        if ff_df is None or ff_df.empty:
                            # Flat file yok, DB'den oluştur
                            logger.info(
                                f"📊 [STORAGE] {symbol} için flat file oluşturuluyor (DB'den)..."
                            )

                            db_klines = await db_manager.get_klines(
                                symbol, "1m", limit=1000
                            )
                            if db_klines and len(db_klines) > 0:
                                db_df = pd.DataFrame(
                                    db_klines,
                                    columns=[
                                        "timestamp",
                                        "open",
                                        "high",
                                        "low",
                                        "close",
                                        "volume",
                                    ],
                                )

                                # Bellek Optimizasyonu
                                db_df = reduce_mem_usage(db_df)

                                if db_df["timestamp"].dtype == "object":
                                    db_df["timestamp"] = pd.to_datetime(
                                        db_df["timestamp"], utc=True
                                    )
                                else:
                                    db_df["timestamp"] = pd.to_datetime(
                                        db_df["timestamp"], unit="ms", utc=True
                                    )

                                db_df.set_index("timestamp", inplace=True)

                                save_df = db_df.copy()
                                save_df.reset_index(inplace=True)
                                save_df["timestamp"] = (
                                    pd.to_numeric(save_df["timestamp"]) // 10**6
                                )

                                storage.save_ohlcv(symbol, "1m", save_df)
                                logger.info(
                                    f"✅ [STORAGE] {symbol} 1m flat file oluşturuldu ({len(save_df)} mum)"
                                )
                    except Exception as no_gap_err:
                        logger.debug(
                            f"⚠️ [STORAGE] No gap flat file oluşturma hatası: {no_gap_err}"
                        )
            else:
                logger.warning(
                    f"WARNING [LOCAL DB] {symbol} için veritabanında veri bulunamadı, REST API'den çekiliyor..."
                )

                # Veritabanı boşsa, REST API'den çek
                try:
                    historical_ohlcv = await self.exchange.fetch_ohlcv(
                        symbol, timeframe="1m", limit=1500
                    )
                except Exception as rest_err:
                    if "RateLimitExceeded" in str(type(rest_err)) or "429" in str(
                        rest_err
                    ):
                        logger.warning(
                            f"⚠️ [REST] {symbol} Rate Limit devrede! 10 saniye bekleniyor..."
                        )
                        await asyncio.sleep(10)
                        historical_ohlcv = []
                    else:
                        logger.error(f"⚠️ [REST] {symbol} Hata: {rest_err}")
                        historical_ohlcv = []

                if historical_ohlcv and len(historical_ohlcv) > 0:
                    ohlcv_df = pd.DataFrame(
                        historical_ohlcv,
                        columns=["timestamp", "open", "high", "low", "close", "volume"],
                    )

                    # Bellek Optimizasyonu
                    ohlcv_df = reduce_mem_usage(ohlcv_df)

                    if ohlcv_df["timestamp"].dtype == "object":
                        ohlcv_df["timestamp"] = pd.to_datetime(ohlcv_df["timestamp"])
                    else:
                        ohlcv_df["timestamp"] = pd.to_datetime(
                            ohlcv_df["timestamp"], unit="ms"
                        )

                    ohlcv_df.set_index("timestamp", inplace=True)
                    logger.info(f"OK [REST] {len(ohlcv_df)} mum REST API'den çekildi.")

                    # ========================================================================
                    # YENİ: REST API'DEN ÇEKİLDİKTEN SONRA FLAT FILE OLUŞTUR
                    # ========================================================================
                    try:
                        from data.ohlcv_storage import get_storage

                        storage = get_storage()

                        save_df = ohlcv_df.copy()
                        save_df.reset_index(inplace=True)
                        save_df["timestamp"] = (
                            pd.to_numeric(save_df["timestamp"]) // 10**6
                        )

                        storage.save_ohlcv(symbol, "1m", save_df)
                        logger.info(
                            f"✅ [STORAGE] {symbol} 1m flat file oluşturuldu ({len(save_df)} mum)"
                        )
                    except Exception as rest_storage_err:
                        logger.warning(
                            f"⚠️ [STORAGE] REST flat file oluşturma hatası: {rest_storage_err}"
                        )
                else:
                    logger.warning(
                        f"WARNING [REST] {symbol} için REST API'den veri çekilemedi."
                    )
        except Exception as e:
            import traceback

            logger.error(f"ERROR [HYBRID] {symbol} veri yükleme hatası: {e}")
            logger.error(traceback.format_exc())
            logger.info("INFO [HYBRID] Boş DataFrame ile başlanıyor.")

        # ============================================
        # 3. YENİ: TÜM MumlAR TUTULUYOR (Limit YOK)
        # ============================================
        # Kullanıcının istediği tarihten itibaren tüm mumlar
        # Sistem TÜM mumları tutacak ve işleyecek
        # ============================================
        logger.info(
            f"✅ [ALL CANDLES] {symbol} için {len(ohlcv_df)} mum yüklendi (TÜM veri tutuluyor)"
        )

        # ============================================
        # 3.5 BOT TASK'LARINI BAŞLAT
        # ============================================
        # Aktif botları kontrol et ve sinyal hesaplamalarını başlat
        try:
            from core.paper import paper_engine

            # Sadece bu poller'ın symbol'üne ait aktif botları bul
            symbol_active_bots = [
                bot_id
                for bot_id, bot_info in (
                    paper_engine.active_bots.items() if paper_engine else []
                )
                if bot_info.get("symbol") == symbol
                and bot_info.get("status") == "running"
            ]

            if paper_engine and len(symbol_active_bots) > 0:
                logger.info(
                    f"🤖 [1-to-N] {symbol} için {len(symbol_active_bots)} aktif bot işleniyor..."
                )

                # Her bot için task oluştur
                tasks = []
                for bot_id in symbol_active_bots:
                    bot_info = paper_engine.active_bots.get(bot_id, {})
                    bot_timeframe = bot_info.get("timeframe", "1m")

                    # Sadece aynı timeframe olan botları işle! (Sembol filtresi zaten symbol_active_bots'ta yapıldı)
                    if bot_timeframe == timeframe:
                        # Log çıktısını temizlemek için sadece ilgili botun debug bilgisini basalım
                        logger.info(
                            f"   🔥 [BOT DEBUG] active_bot_ids={['Bot: ' + bot_id]}"
                        )
                        logger.info("   🚀 [BOT GATHER] 1 task çalıştırılıyor...")

                        # Bot task'ını başlat (async)
                        task = asyncio.create_task(
                            self._process_bot_task(
                                paper_engine=paper_engine,
                                bot_id=bot_id,
                                df=ohlcv_df,
                                htf_trend="NEUTRAL",  # HTF henüz hesaplanmadı
                                regime="UNKNOWN",  # Rejim henüz hesaplanmadı
                                htf_trends={},
                            )
                        )
                        tasks.append(task)

                # Tüm task'ları bekle
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    logger.info("   ✅ [BOT GATHER] Tüm tasklar tamamlandı")

                    # Hataları logla
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            logger.error(f"❌ [BOT TASK] Task {i} hata: {result}")
                else:
                    logger.debug(f"⏭️ [BOT GATHER] {symbol} için bot task yok")
            else:
                logger.debug(f"⏭️ [BOT GATHER] {symbol} için aktif bot yok")
        except Exception as bot_task_err:
            logger.error(f"❌ [BOT GATHER] Bot task başlatma hatası: {bot_task_err}")
            logger.debug("⚠️ [BOT GATHER] Bot task hatası atlandı, devam ediliyor")

        # ============================================
        # 4. WEBSOCKET DÖNGÜSÜ (Canlı Güncelleme)
        # ============================================
        logger.info(f"📡 [WSS] {symbol} için WebSocket döngüsü başlatılıyor...")
        logger.info(f"🔥 [WSS DEBUG] DataFrame boyutu: {len(ohlcv_df)} mum")
        logger.info(
            f"🔥 [WSS DEBUG] active_timeframes={paper_engine.active_timeframes}"
        )

        # YENİ MUM KİLİDİ: Aynı mumu tekrar işlemeyi önler
        last_processed_ts = None
        loop_iteration = 0

        while True:
            loop_iteration += 1
            logger.debug(f"🔄 [WSS LOOP] {symbol} iteration #{loop_iteration}")

            try:
                # WebSocket üzerinden OHLCV dinle (PUSH - POLLING YOK!)
                logger.debug("📡 [WSS] watch_ohlcv çağrılıyor...")
                try:
                    live_ohlcv = await exchange_breaker._call_async(
                        self.exchange.watch_ohlcv, symbol, timeframe="1m", limit=100
                    )
                except CircuitBreakerError:
                    logger.warning(
                        f"⚠️ [WSS] {symbol} watch_ohlcv circuit breaker open. Waiting..."
                    )
                    await asyncio.sleep(5)
                    continue
                logger.debug(
                    f"✅ [WSS] watch_ohlcv döndü: {len(live_ohlcv) if live_ohlcv else 0} mum"
                )

                if not live_ohlcv or len(live_ohlcv) == 0:
                    logger.warning(
                        f"WARNING [WSS] {symbol} boş OHLCV, devam ediliyor..."
                    )
                    await asyncio.sleep(5)
                    continue

                # ============================================
                # YENİ MUM FİLTRESİ: Aynı mumu tekrar işleme!
                # ============================================
                current_candle_ts = live_ohlcv[-1][
                    0
                ]  # Son mumun timestamp'i (int veya string)

                # Timestamp'i parse et (int veya string olabilir)
                if isinstance(current_candle_ts, (int, float)):
                    current_candle_dt = pd.Timestamp(current_candle_ts, unit="ms")
                else:
                    current_candle_dt = pd.Timestamp(current_candle_ts)

                if (
                    last_processed_ts is not None
                    and current_candle_dt == last_processed_ts
                ):
                    # Bu mum zaten işlendi, sadece fiyat güncellemesi yap (trailing stop + SL/TP için)
                    last_ohlcv = live_ohlcv[-1]  # [ts, open, high, low, close, volume]

                    # WebSocket ZIRHI: update_live_prices hatası loop'u çökertmesin
                    try:
                        await paper_engine.update_live_prices(
                            symbol,
                            current_price=float(last_ohlcv[4]),  # close
                            current_high=float(last_ohlcv[2]),  # high
                            current_low=float(last_ohlcv[3]),  # low
                        )
                    except Exception as e:
                        logger.error(
                            f"❌ [WEBSOCKET ZIRHI] {symbol} update_live_prices hatası (same candle): {e}"
                        )
                        # Continue ile devam et

                    continue  # ⚠️ DEVAM ET - yeni mum gelene kadar bekle

                # YENİ MUM GELDİ! Kilidi güncelle
                last_processed_ts = current_candle_dt
                logger.debug(f"🕐 [NEW CANDLE] Yeni mum: {current_candle_dt}")

                # Canlı veriyi DataFrame'e dönüştür
                # live_ohlcv is a list of lists: [[timestamp, open, high, low, close, volume], ...]
                live_df = pd.DataFrame(
                    live_ohlcv,
                    columns=["timestamp", "open", "high", "low", "close", "volume"],
                )

                # Bellek Optimizasyonu (Canlı veri için de uyguluyoruz)
                live_df = reduce_mem_usage(live_df)

                # WebSocket timestamp parse (int veya string olabilir)
                if live_df["timestamp"].dtype == "object":
                    live_df["timestamp"] = pd.to_datetime(
                        live_df["timestamp"], utc=True
                    )
                else:
                    live_df["timestamp"] = pd.to_datetime(
                        live_df["timestamp"], unit="ms", utc=True
                    )

                live_df.set_index("timestamp", inplace=True)

                # 🔥 TIMEZONE DÜZELTMESİ: live_df'i UTC yap
                if live_df.index.tzinfo is None:
                    live_df.index = live_df.index.tz_localize("UTC")

                # ============================================
                # 5. CANLI VERİ BİRLEŞTİRME + RAM KORUMASI
                # ============================================
                if ohlcv_df.empty:
                    # İlk veri, direkt kullan
                    ohlcv_df = live_df.copy()
                    logger.info(f"OK [WSS] İlk veri: {len(ohlcv_df)} mum")
                else:
                    # Canlı veriyi geçmiş veriye ekle/güncelle
                    last_live_time = live_df.index[-1]
                    last_hist_time = ohlcv_df.index[-1]

                    # ========================================================================
                    # [TZ FIX] Her iki timestamp'i de UTC yap (timezone-aware)
                    # ========================================================================
                    if last_live_time.tzinfo is None:
                        last_live_time = last_live_time.tz_localize("UTC")
                    else:
                        last_live_time = last_live_time.tz_convert("UTC")

                    if last_hist_time.tzinfo is None:
                        last_hist_time = last_hist_time.tz_localize("UTC")
                    else:
                        last_hist_time = last_hist_time.tz_convert("UTC")

                    logger.debug(
                        f"🔥 [TZ DEBUG] last_live_time={last_live_time} (tz={last_live_time.tzinfo})"
                    )
                    logger.debug(
                        f"🔥 [TZ DEBUG] last_hist_time={last_hist_time} (tz={last_hist_time.tzinfo})"
                    )

                    if last_live_time > last_hist_time:
                        # Yeni mum geldi, ekle (DUPLICATE kontrolü)
                        new_candles = live_df.loc[last_hist_time:]

                        # Duplicate timestamp'leri temizle
                        if len(new_candles) > 0:
                            # Index'i resetle ve duplicate'leri kaldır
                            new_candles = new_candles[
                                ~new_candles.index.duplicated(keep="last")
                            ]
                            ohlcv_df = pd.concat([ohlcv_df, new_candles])

                            # Ana DataFrame'de de duplicate kontrolü
                            ohlcv_df = ohlcv_df[~ohlcv_df.index.duplicated(keep="last")]

                            logger.debug(f"OK [WSS] Yeni mum eklendi: {last_live_time}")
                    elif last_live_time == last_hist_time:
                        # Son mum güncellendi, replace et (sadece ortak sütunları güncelle, boole sütun hatalarını önle)
                        shared_cols = live_df.columns.intersection(ohlcv_df.columns)
                        ohlcv_df.loc[last_live_time, shared_cols] = live_df.loc[
                            last_live_time, shared_cols
                        ]
                        logger.debug(f"OK [WSS] Son mum güncellendi: {last_live_time}")

                    # YENİ: RAM limiti YOK - Tüm mumlar tutuluyor
                    logger.debug(
                        f"📊 [ALL CANDLES] {symbol} için toplam {len(ohlcv_df)} mum RAM'de"
                    )

                ohlcv_df.index[-1]
                df_1m = ohlcv_df

                # 4. HEDEF VADEYE DÖNÜŞTÜR (Resampling Engine) - REFACTORED (Async)
                target_tf = paper_engine.active_timeframes.get(symbol, "1m")

                # HTF config'leri
                htf_config = CONFIG.get("htf", {})
                htf_dynamic_map = htf_config.get(
                    "dynamic_map",
                    {
                        "1m": ["5m", "15m"],
                        "3m": ["15m", "1h"],
                        "5m": ["15m", "1h"],
                        "15m": ["1h", "4h"],
                        "30m": ["2h", "6h"],
                        "1h": ["4h", "1d"],
                        "4h": ["1d", "1w"],
                    },
                )
                htf_levels = htf_dynamic_map.get(target_tf, ["5m", "15m"])
                ema_fast = htf_config.get("ema_fast", 20)
                ema_slow = htf_config.get("ema_slow", 50)
                trend_method = htf_config.get("trend_method", "ema_stack")

                # Asenkron Thread üzerinden veri hazırlığı ve analiz
                from core.trading.services.signal_generator import (
                    signal_generator_service,
                )

                result = await signal_generator_service.prepare_target_data_and_detect_regime(
                    df_1m, target_tf, htf_levels, ema_fast, ema_slow, trend_method
                )
                df_target, htf_trends, regime_info, current_price = result

                if df_target is None or df_target.empty or current_price is None:
                    continue

                paper_engine.market_regime = regime_info.get("regime", "UNKNOWN")

                major_htf = htf_levels[-1] if htf_levels else None
                htf_trend = (
                    htf_trends.get(major_htf, "NEUTRAL") if major_htf else "NEUTRAL"
                )
                logger.debug(
                    f"[HTF] {symbol} ({target_tf}) HTF Analizi: {htf_trends} → Major: {major_htf}={htf_trend}"
                )

                if not df_target.empty:
                    # 7.5 STRATEJİ KONTROLÜ - Eğer strateji yoksa işlem yapma
                    strategy = paper_engine.strategies.get(symbol)
                    active_strat_id = paper_engine.active_strategies.get(
                        symbol, "NOT_SET"
                    )

                    # YENİ 1-to-N: active_bots kontrolü (eski active_strategies yerine)
                    active_bot_ids = [
                        bot_id
                        for bot_id, bot_info in paper_engine.active_bots.items()
                        if bot_info["symbol"] == symbol
                        and bot_info["status"] == "running"
                    ]

                    if (
                        strategy is None or active_strat_id == ""
                    ) and not active_bot_ids:
                        # Strateji durdurulmuş VE aktif bot yok, sadece fiyat güncellemesi yap

                        # WebSocket ZIRHI
                        try:
                            await paper_engine.update_live_prices(symbol, current_price)
                        except Exception as e:
                            logger.error(
                                f"❌ [WEBSOCKET ZIRHI] {symbol} update_live_prices hatası (no strategy): {e}"
                            )

                        logger.debug(
                            f"⏸️ {symbol} için strateji durduruldu ve aktif bot yok, sadece fiyat güncelleniyor."
                        )
                        continue

                    logger.debug(
                        f"▶️ {symbol} strateji aktif: {active_strat_id}, strategy={strategy}, aktif bot sayısı: {len(active_bot_ids)}"
                    )

                    # ============================================
                    # YENİ 1-to-N MİMARİSİ: Merkezi Poller, Dağıtık İşleme
                    # ============================================
                    # Bu sembol için aktif tüm botları bul
                    active_bot_ids = [
                        bot_id
                        for bot_id, bot_info in paper_engine.active_bots.items()
                        if bot_info["symbol"] == symbol
                        and bot_info["status"] == "running"
                    ]

                    if active_bot_ids:
                        logger.info(
                            f"🤖 [1-to-N] {symbol} için {len(active_bot_ids)} aktif bot işleniyor..."
                        )
                        logger.info(
                            f"   🔥 [BOT DEBUG] active_bot_ids={active_bot_ids}"
                        )

                        # PARALEL İŞLEME: Her bot için asenkron task oluştur
                        bot_tasks = []
                        for bot_id in active_bot_ids:
                            logger.debug(
                                f"   📝 [BOT TASK] {bot_id} için task oluşturuluyor..."
                            )
                            task = asyncio.create_task(
                                self._process_bot_task(
                                    paper_engine,
                                    bot_id,
                                    df_target,
                                    htf_trend,
                                    regime_info["regime"],
                                    htf_trends,
                                )
                            )
                            bot_tasks.append(task)
                            logger.debug(f"   ✅ [BOT TASK] {bot_id} task oluşturuldu")

                        # Tüm botları PARALEL çalıştır
                        if bot_tasks:
                            logger.info(
                                f"   🚀 [BOT GATHER] {len(bot_tasks)} task çalıştırılıyor..."
                            )
                            try:
                                results = await asyncio.gather(
                                    *bot_tasks, return_exceptions=True
                                )
                                logger.info("   ✅ [BOT GATHER] Tüm tasklar tamamlandı")

                                for bot_id, result in zip(active_bot_ids, results):
                                    if isinstance(result, Exception):
                                        logger.error(
                                            f"   ❌ [BOT] {bot_id} işleme hatası: {result}"
                                        )
                                    else:
                                        logger.debug(
                                            f"   ✅ [BOT] {bot_id} başarıyla işlendi"
                                        )
                            except Exception as gather_err:
                                logger.error(
                                    f"   ❌ [1-to-N] Gather hatası: {gather_err}"
                                )
                    else:
                        logger.info(f"⚠️ [1-to-N] {symbol} için aktif bot yok")

                    # ESKİ MİMARİ KALDIRILDI! Sadece 1-to-N kullanılıyor

                    # 8. ANALİZ ÖZETİ (DEBUG seviyesinde tutulur, gürültü yapmaz)
                    logger.debug(
                        f"✅ {symbol} {target_tf} (HTF: {htf_trends} | REJİM: {regime_info['regime']}) analiz tamamlandı. Botlar işlendi."
                    )

                    # ========================================================================
                    # 9. DATA LAKE GÜNCELLEME - REFACTORED (Async)
                    # ========================================================================
                    from core.trading.services.data_sync import data_synchronizer

                    await data_synchronizer.update_data_lake(symbol, df_1m)

                    # ========================================================================
                    # 10. PERİYODİK TAM SENKRONİZASYON - REFACTORED (Async)
                    # ========================================================================
                    await data_synchronizer.sync_all_from_db_to_lake(symbol)

            # BAĞLANTI KOPMA VE RECONNECT KALKANI
            except ccxt.NetworkError as e:
                logger.error(
                    f"❌ [WSS] {symbol} NetworkError: {e}. 5 saniye sonra yeniden bağlanıyor..."
                )
                await asyncio.sleep(5)
                continue
            except ccxt.ExchangeError as e:
                logger.error(
                    f"❌ [WSS] {symbol} ExchangeError: {e}. 5 saniye sonra yeniden bağlanıyor..."
                )
                await asyncio.sleep(5)
                continue
            except asyncio.CancelledError:
                logger.info(f"🛑 [WSS] {symbol} WebSocket döngüsü iptal edildi.")
                break
            except Exception as e:
                import traceback

                logger.error(f"❌ [WSS] {symbol} Strateji Döngü Hatası: {e}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(5)
                continue

    async def close(self):
        """Borsa bağlantılarını ve WebSocket akışlarını temiz bir şekilde kapatır."""
        if self.exchange:
            await self.exchange.close()
            logger.info(f"{self.exchange_id.upper()} borsa bağlantısı sonlandırıldı.")


# Diğer modüllerden kolay erişim için Singleton mantığı
exchange_manager = ExchangeManager()
