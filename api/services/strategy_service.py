"""
Strategy Service

Business logic for strategy operations.
"""

from typing import Dict, Any, List, Optional
import pandas as pd

from core.logger import logger
from strategy.manager import StrategyManager


class StrategyService:
    """
    Strategy Service.
    
    Business logic for strategy operations:
    - List strategies
    - Select strategy
    - Get strategy info
    """
    
    def __init__(self):
        self.strategy_manager = StrategyManager
    
    def get_strategies(self) -> Dict[str, Any]:
        """
        Tüm stratejileri al.

        Returns:
            Strateji listesi (detaylı bilgilerle)
        """
        try:
            # Her istekte dinamik stratejileri yükle
            self.strategy_manager.load_dynamic_strategies()

            # YENİ METOD: get_all_strategies() kullan
            all_strategies = self.strategy_manager.get_all_strategies()

            # List formatına çevir (frontend uyumlu)
            strategies_list = []
            for strategy_id, data in all_strategies.items():
                # Strateji instance'ını al ve detaylı bilgileri çıkar
                strategy_instance = None
                indicators = []
                conditions = {'LONG': [], 'SHORT': []}

                try:
                    # Strateji instance'ını oluştur
                    if strategy_id not in ['trend_master', 'scalper_ninja', 'adaptive_koncorde',
                                          'golden_combo', 'divergence_hunter', 'knn_quant_atr']:
                        # Custom strateji
                        strategy_instance = self.strategy_manager.get_strategy(strategy_id)
                    else:
                        # Built-in strateji - manager'dan al
                        strategy_instance = self.strategy_manager.get_strategy(strategy_id)

                    if strategy_instance:
                        # İndikatörleri al
                        if hasattr(strategy_instance, 'required_indicators'):
                            indicators = strategy_instance.required_indicators
                        elif hasattr(strategy_instance, 'indicators'):
                            indicators = strategy_instance.indicators

                        # Koşulları al (eğer varsa)
                        if hasattr(strategy_instance, 'get_conditions'):
                            conditions = strategy_instance.get_conditions()
                        elif hasattr(strategy_instance, 'conditions'):
                            conditions = strategy_instance.conditions
                except Exception as e:
                    logger.debug(f"Strateji detayları okunamadı {strategy_id}: {e}")

                strategies_list.append({
                    'id': strategy_id,
                    'name': data.get('name', strategy_id),
                    'description': data.get('description', ''),
                    'timeframe': data.get('timeframe', '1m'),
                    'type': data.get('type', 'builtin'),
                    'indicators': indicators,
                    'conditions': conditions,
                    'info': data.get('info', data.get('description', ''))
                })

            return {"status": "success", "strategies": strategies_list}

        except Exception as e:
            logger.error(f"Strateji listesi hatası: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}
    
    def select_strategy(
        self,
        symbol: str,
        strategy_id: str,
        timeframe: str = "1m",
        market_type: str = "swap",
        margin_type: str = "isolated"
    ) -> Dict[str, Any]:
        """
        Strateji seç/değiştir.
        
        Args:
            symbol: Sembol
            strategy_id: Strateji ID
            timeframe: Zaman dilimi
            market_type: Piyasa tipi
            margin_type: Marjin tipi
        
        Returns:
            Strateji seçme yanıtı
        """
        from core.paper import paper_engine
        
        logger.info(f"📥 Strateji isteği alındı: symbol={symbol}, strategy_id={strategy_id}")
        
        # Strateji başlat
        paper_engine.set_market_type(symbol, market_type)
        paper_engine.set_margin_type(symbol, margin_type)
        paper_engine.set_strategy(strategy_id, symbol, timeframe)
        
        logger.info(f"▶️ {symbol} için strateji başlatıldı: {strategy_id}")
        
        return {
            "status": "success",
            "symbol": symbol,
            "active_id": strategy_id,
            "active_timeframe": timeframe,
            "market_type": market_type,
            "margin_type": margin_type
        }
    
    async def stop_strategy(self, symbol: str) -> Dict[str, Any]:
        """
        Strateji durdur.
        
        Args:
            symbol: Sembol
        
        Returns:
            Strateji durdurma yanıtı
        """
        from core.paper import paper_engine
        
        # Strateji temizle
        paper_engine.strategies[symbol] = None
        paper_engine.active_strategies[symbol] = ""
        
        logger.info(f"⏹️ {symbol} için strateji durduruldu")
        
        return {
            "status": "success",
            "symbol": symbol,
            "active_id": None
        }

    async def get_strategy_chart_data(self, strategy_id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Strateji görselleştirme için gerekli tüm verileri (mumlar + işlemler) birleştirir.
        """
        try:
            from core.paper import paper_engine
            from data.database import db_manager
            
            # 1. Stratejiye ait geçmiş işlemleri çek (DB + Memory)
            db_trades = await db_manager.get_trades_by_strategy(strategy_id, limit=500)
            
            # Memory'den çek (Mevcut oturum verileri)
            memory_trades = []
            if hasattr(paper_engine.position_manager, 'trade_history'):
                # Strateji bazlı filtrele
                mem_raw = paper_engine.position_manager.trade_history.trades
                for t in mem_raw:
                    # Strateji ID veya Bot ID içindeki strateji ismi ile eşleşme
                    if t.strategy_id == strategy_id or (t.metadata and t.metadata.get('strategy_id') == strategy_id) or strategy_id in t.bot_id:
                        trade_dict = t.to_dict()
                        memory_trades.append({
                            "id": trade_dict.get('id'),
                            "symbol": trade_dict.get('symbol'),
                            "direction": trade_dict.get('direction'),
                            "entry_price": trade_dict.get('entry_price'),
                            "exit_price": trade_dict.get('exit_price'),
                            "pnl_usd": trade_dict.get('pnl'),
                            "pnl_percent": trade_dict.get('pnl_percent', 0.0) * 100,
                            "closed_at": trade_dict.get('closed_at'),
                            "strategy_id": trade_dict.get('strategy_id')
                        })
            
            # Merge
            seen_ids = {t['id'] for t in db_trades if 'id' in t}
            closed_trades = db_trades + [t for t in memory_trades if t['id'] not in seen_ids]
            closed_trades.sort(key=lambda x: str(x.get('closed_at', '')), reverse=True)
            
            # 2. Eğer sembol belirtilmemişse, en son işlem yapılan sembolü seç
            if not symbol:
                if closed_trades:
                    symbol = closed_trades[0]['symbol']
                else:
                    # Alternatif: Şu an bu stratejiyi çalıştıran ilk botu bul
                    for b_id, b_meta in paper_engine.active_bots.items():
                        if b_meta.get('strategy_id') == strategy_id:
                            symbol = b_meta.get('symbol')
                            break
            
            if not symbol:
                return {"status": "error", "message": "Bu stratejiye ait işlem veya aktif bot bulunamadı."}
            
            # 3. Aktif pozisyonları çek
            open_positions = []
            for pos in paper_engine.position_manager.get_all_positions():
                # Position objesi içindeki strategy_id veya bot_id üzerinden eşleşme
                # Bot ID formatı: {symbol}_{strategy_id}_{timeframe}_{counter}
                is_match = (
                    pos.metadata.get('strategy') == strategy_id or 
                    strategy_id in pos.bot_id or
                    pos.metadata.get('strategy_id') == strategy_id
                )
                
                if is_match and pos.symbol == symbol:
                    open_positions.append({
                        **pos.to_dict(),
                        'current_price': pos.entry_price # Initial, will be updated by UI
                    })

            # 4. Mum verilerini çek (Timeframe tahmini)
            timeframe = "1h" # Varsayılan
            
            # Eğer aktif pozisyon varsa onun timeframe'ini kullan
            if open_positions:
                timeframe = open_positions[0].get('metadata', {}).get('timeframe') or \
                           open_positions[0].get('timeframe') or "1h"
            elif closed_trades:
                timeframe = closed_trades[0].get('timeframe') or \
                           closed_trades[0].get('metadata', {}).get('timeframe') or "1h"

            # Flat file'dan çek (HIZLI!)
            try:
                from data.ohlcv_storage import get_storage
                from datetime import datetime, timedelta

                storage = get_storage()
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=10)

                df = storage.load_ohlcv(symbol, timeframe, start_date, end_date)

                if df is not None and not df.empty:
                    klines = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].values.tolist()
                    logger.info(f"  ✅ {len(klines)} mum flat file'dan yüklendi")
                else:
                    # Flat file yoksa DB'den çek
                    klines = await db_manager.get_klines(symbol, timeframe, limit=1000)
                    # Eğer seçilen timeframe boşsa (örn: default 1h ama veri sadece 1m ise), 1m dene
                    if not klines and timeframe != "1m":
                        logger.info(f"ℹ️ {timeframe} için veri bulunamadı, 1m deneniyor: {symbol}")
                        timeframe = "1m"
                        klines = await db_manager.get_klines(symbol, timeframe, limit=1000)
            except Exception as e:
                logger.warning(f"  ⚠️ Flat file okuma hatası, DB'den çekiliyor: {e}")
                klines = await db_manager.get_klines(symbol, timeframe, limit=1000)

            
            # Lightweight Charts yükselen zaman sırası (ascending) bekler. 
            # DB'den DESC (azalan) geldiği için ters çeviriyoruz.
            klines.reverse()
            
            # Format klines for Lightweight Charts (Saniye cinsinden timestamp zorunlu)
            formatted_candles = []
            for k in klines:
                ts = k[0]
                if isinstance(ts, (int, float)):
                    # Eğer mili saniye ise saniyeye çevir (> 10^10 kuralı)
                    if ts > 10000000000:
                        ts = int(ts / 1000)
                else:
                    # ISO string veya datetime ise
                    ts = int(pd.to_datetime(ts).timestamp())
                    
                formatted_candles.append({
                    "time": ts,
                    "open": k[1], "high": k[2], "low": k[3], "close": k[4], "volume": k[5]
                })

            # 5. Zaman damgalarını saniye (Unix) formatına çevir (LW Charts uyumluluğu için)
            def normalize_ts(ts):
                if isinstance(ts, str):
                    return int(pd.to_datetime(ts).timestamp())
                if isinstance(ts, (int, float)) and ts > 10000000000:
                    return int(ts / 1000)
                return ts

            for t in closed_trades:
                if 'opened_at' in t:
                    t['opened_at'] = normalize_ts(t['opened_at'])
                if 'closed_at' in t:
                    t['closed_at'] = normalize_ts(t['closed_at'])
                    
            for p in open_positions:
                if 'opened_at' in p:
                    p['opened_at'] = normalize_ts(p['opened_at'])

            return {
                "status": "success",
                "strategy_id": strategy_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "candles": formatted_candles,
                "trades": closed_trades,
                "open_positions": open_positions
            }
            
        except Exception as e:
            logger.error(f"Strategy chart data error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"status": "error", "message": str(e)}
