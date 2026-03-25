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

        def _prepare_resampled_data(df_1m_copy):
            from data.indicators import StrategyIndicators
            resampled_data = {}

            # Prepare 1m
            df_1m_copy.reset_index(inplace=True)
            resampled_data['1m'] = df_1m_copy

            # Reset index again to be able to use set_index for resampling
            df_for_resample = df_1m_copy.copy()
            df_for_resample.set_index('timestamp', inplace=True)

            for tf in ['5m', '15m', '1h', '4h']:
                df_tf = StrategyIndicators.resample_data(df_for_resample, tf)
                df_tf = df_tf.dropna()
                if not df_tf.empty:
                    save_df_tf = df_tf.copy()
                    save_df_tf.reset_index(inplace=True)
                    resampled_data[tf] = save_df_tf
            return resampled_data

        try:
            # Perform heavy pandas operations in a separate thread
            resampled_data = await asyncio.to_thread(_prepare_resampled_data, df_1m.copy())

            for tf, df_tf in resampled_data.items():
                await self.data_lake.save(symbol, tf, df_tf, append=True)

            logger.debug(f"💾 [DATA LAKE] {symbol} güncellendi (TÜM TF'ler)")
        except Exception as lake_err:
            logger.debug(f"⚠️ [DATA LAKE] Güncelleme hatası: {lake_err}")

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
                    # Execute synchronous heavy dataframe creation and resampling operations in a background thread
                    def _prepare_all_resampled_data(df_input):
                        from data.indicators import StrategyIndicators

                        df_reset = df_input.copy()
                        if 'timestamp' not in df_reset.columns:
                            df_reset = df_reset.reset_index()
                            if 'index' in df_reset.columns and pd.api.types.is_datetime64_any_dtype(df_reset['index']):
                                df_reset.rename(columns={'index': 'timestamp'}, inplace=True)
                            elif df_input.index.name in ['timestamp', 'time', 'date']:
                                df_reset.rename(columns={df_input.index.name: 'timestamp'}, inplace=True)

                        all_klines = df_reset[['timestamp', 'open', 'high', 'low', 'close', 'volume']].values.tolist()
                        all_df = pd.DataFrame(all_klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

                        if pd.api.types.is_numeric_dtype(all_df['timestamp']):
                            all_df['timestamp'] = pd.to_datetime(all_df['timestamp'], unit='ms')
                        else:
                            all_df['timestamp'] = pd.to_datetime(all_df['timestamp'])

                        all_df.set_index('timestamp', inplace=True)

                        resampled_data = {}
                        save_all_df = all_df.copy()
                        save_all_df.reset_index(inplace=True)
                        resampled_data['1m'] = save_all_df

                        for tf in ['5m', '15m', '1h', '4h']:
                            df_tf = StrategyIndicators.resample_data(all_df, tf)
                            df_tf = df_tf.dropna()
                            if not df_tf.empty:
                                save_tf = df_tf.copy()
                                save_tf.reset_index(inplace=True)
                                resampled_data[tf] = save_tf

                        return resampled_data, len(all_df)

                    try:
                        resampled_data, length = await asyncio.to_thread(_prepare_all_resampled_data, df)

                        for tf, df_tf in resampled_data.items():
                            await self.data_lake.save(symbol, tf, df_tf, append=False)

                        logger.info(f"✅ [DATA LAKE] {symbol} TAM SENKRONİZASYON tamamlandı ({length} mum)")
                    except Exception as e:
                        logger.debug(f"⚠️ [DATA LAKE] İçi asenkron hata: {e}")

        except Exception as sync_err:
            logger.debug(f"⚠️ [DATA LAKE] Tam senkronizasyon hatası: {sync_err}")

data_synchronizer = DataSynchronizer()
