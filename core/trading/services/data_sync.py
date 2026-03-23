import asyncio
import pandas as pd
from datetime import datetime, timedelta
from typing import Any
from core.logger import logger
from data.database import db_manager
# from data.ohlcv_storage import get_storage  # ❌ MODÜL YOK - KALDIRILDI
from data.data_lake import get_data_lake


class DataSynchronizer:
    """
    Veri senkronizasyonu ve Data Lake operasyonlarını yönetir.
    ExchangeManager içindeki sorumlulukları hafifletmek için oluşturuldu.
    """
    def __init__(self):
        # self.storage = get_storage()  # ❌ KALDIRILDI
        self.data_lake = get_data_lake()

    async def check_and_fill_gap(self, symbol: str, exchange_manager: Any) -> None:
        """Veri boşluğunu kontrol eder ve eksik varsa doldurur."""
        try:
            # 🔥 BASITLEŞTIRILDI: Sadece logla, işlem yapma
            logger.debug(f"✅ [GAP CHECK] {symbol} için gap check çalıştı (no-op)")
            return

            # ESKİ KOD (YORUMA ALINDI):
            # end_date = datetime.utcnow()
            # start_date = end_date - timedelta(days=1)
            # df_check = self.storage.load_ohlcv(symbol, '1m', start_date, end_date)
            # ...
        except Exception as e:
            logger.error(f"❌ [GAP DETECTION] Hata: {e}")

    async def update_data_lake(self, symbol: str, df_1m: pd.DataFrame) -> None:
        """Yeni mum geldiğinde tüm timeframeleri Data Lake'e asenkron kaydeder."""
        async def _save_to_lake(df_1m_copy):
            try:
                from data.indicators import StrategyIndicators

                # 1m veriyi kaydet
                df_1m_copy.reset_index(inplace=True)
                await self.data_lake.save(symbol, '1m', df_1m_copy, append=True)

                # Diğer TF'leri resample ve kaydet
                for tf in ['5m', '15m', '1h', '4h']:
                    df_tf = StrategyIndicators.resample_data(df_1m_copy.set_index('timestamp'), tf)
                    df_tf = df_tf.dropna()
                    if not df_tf.empty:
                        save_df_tf = df_tf.copy()
                        save_df_tf.reset_index(inplace=True)
                        await self.data_lake.save(symbol, tf, save_df_tf, append=True)
                logger.debug(f"💾 [DATA LAKE] {symbol} güncellendi (TÜM TF'ler)")
            except Exception as lake_err:
                logger.debug(f"⚠️ [DATA LAKE] Güncelleme hatası: {lake_err}")

        # Bekleyerek çağır, async def zaten event loop'u bloklamaz
        await _save_to_lake(df_1m.copy())

    async def sync_all_from_db_to_lake(self, symbol: str) -> None:
        """Periyodik tam senkronizasyon (DataService -> Data Lake) - Asenkron işleme."""
        try:
            current_minute = int(pd.Timestamp.now().timestamp()) // 60
            if current_minute % 5 == 0:
                logger.info(f"🔄 [DATA LAKE] {symbol} için tam senkronizasyon başlatılıyor (Hybrid Data Layer)...")

                from api.services.data_service import DataService
                ds = DataService()

                # Retrieve the full 1m master data using the hybrid layer. Let it figure out disk vs DB vs API.
                df = await ds.get_cached_or_fetch_data(symbol, '1m')

                if df is not None and not df.empty:
                    # Formata uygun listeye çevir
                    if 'timestamp' not in df.columns:
                        df_reset = df.reset_index()
                        if 'index' in df_reset.columns and pd.api.types.is_datetime64_any_dtype(df_reset['index']):
                            df_reset.rename(columns={'index': 'timestamp'}, inplace=True)
                        elif df.index.name in ['timestamp', 'time', 'date']:
                            df_reset.rename(columns={df.index.name: 'timestamp'}, inplace=True)
                        df = df_reset

                    # Extract as list of values like the old get_klines expected, to minimize disruption in _sync_lake
                    all_klines = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].values.tolist()

                    async def _sync_lake(klines_data):
                        try:
                            from data.indicators import StrategyIndicators

                            all_df = pd.DataFrame(klines_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                            if pd.api.types.is_numeric_dtype(all_df['timestamp']):
                                all_df['timestamp'] = pd.to_datetime(all_df['timestamp'], unit='ms')
                            else:
                                all_df['timestamp'] = pd.to_datetime(all_df['timestamp'])

                            all_df.set_index('timestamp', inplace=True)

                            save_all_df = all_df.copy()
                            save_all_df.reset_index(inplace=True)
                            await self.data_lake.save(symbol, '1m', save_all_df, append=False)

                            for tf in ['5m', '15m', '1h', '4h']:
                                df_tf = StrategyIndicators.resample_data(all_df, tf)
                                df_tf = df_tf.dropna()
                                if not df_tf.empty:
                                    save_tf = df_tf.copy()
                                    save_tf.reset_index(inplace=True)
                                    await self.data_lake.save(symbol, tf, save_tf, append=False)
                            logger.info(f"✅ [DATA LAKE] {symbol} TAM SENKRONİZASYON tamamlandı ({len(all_df)} mum)")
                        except Exception as e:
                            logger.debug(f"⚠️ [DATA LAKE] İçi asenkron hata: {e}")

                    await _sync_lake(all_klines)
        except Exception as sync_err:
            logger.debug(f"⚠️ [DATA LAKE] Tam senkronizasyon hatası: {sync_err}")

data_synchronizer = DataSynchronizer()
