"""
Walk-Forward Optimization (WFO) Engine - Bayesian Optimization

Optuna TPE (Tree-structured Parzen Estimator) algoritması kullanarak
binlerce kombinasyonu maksimum 50 denemede optimize eder.

Geleneksel Grid Search yerine Bayesian Optimization kullanır.
CPU koruma için asenkron thread pool executor kullanır.

Usage:
    from core.wfo_engine import WFOEngine
    
    engine = WFOEngine()
    
    # Walk-Forward optimizasyon çalıştır
    best_params = await engine.optimize(
        symbol='BTC/USDT',
        timeframe='1h',
        strategy_class=TrendMaster,
        in_sample_days=30,
        out_of_sample_days=7,
        n_trials=50
    )
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, Type
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import optuna
from optuna.samplers import TPESampler

from core.logger import logger
from core.auto_grid import auto_grid
from data.storage.parquet_lake import get_parquet_lake


class WFOEngine:
    """
    Walk-Forward Optimization Engine.
    
    Bayesian Optimization (TPE) + Walk-Forward Validation.
    Overfitting'i önlemek için Out-of-Sample test yapar.
    """
    
    # Varsayılan ayarlar
    DEFAULT_IN_SAMPLE_DAYS = 30
    DEFAULT_OUT_OF_SAMPLE_DAYS = 7
    DEFAULT_N_TRIALS = 50
    DEFAULT_OPTIMIZATION_METRIC = 'sharpe'  # 'sharpe' veya 'net_pnl'
    
    # CPU koruma (Dinamik - Donanım Agnostiği)
    MAX_WORKERS = min(multiprocessing.cpu_count(), 8)  # Max 8 worker
    
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=self.MAX_WORKERS)
        logger.info(f"🧠 [WFO] Engine initialized (TPE Sampler, {self.MAX_WORKERS} workers)")
        logger.info("🎉 [WFO] Zero-Touch Bayesian Optimizasyon Motoru Aktif")
    
    async def optimize(
        self,
        symbol: str,
        timeframe: str,
        strategy_class: Type,
        in_sample_days: int = None,
        out_of_sample_days: int = None,
        n_trials: int = None,
        optimization_metric: str = None,
        param_grid: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Walk-Forward Bayesian optimizasyon çalıştır.
        
        Args:
            symbol: Sembol (örn: BTC/USDT)
            timeframe: Timeframe (örn: 1h)
            strategy_class: Strateji sınıfı
            in_sample_days: In-Sample gün sayısı (eğitim)
            out_of_sample_days: Out-of-Sample gün sayısı (test)
            n_trials: Optuna deneme sayısı
            optimization_metric: Optimizasyon metriği ('sharpe' veya 'net_pnl')
            param_grid: Manuel param grid (None ise auto-grid)
        
        Returns:
            En iyi parametreler ve metrikler
        """
        # Varsayılan değerler
        in_sample_days = in_sample_days or self.DEFAULT_IN_SAMPLE_DAYS
        out_of_sample_days = out_of_sample_days or self.DEFAULT_OUT_OF_SAMPLE_DAYS
        n_trials = n_trials or self.DEFAULT_N_TRIALS
        optimization_metric = optimization_metric or self.DEFAULT_OPTIMIZATION_METRIC
        
        logger.info(f"🧠 [WFO] Optimizasyon başlatılıyor: {symbol} {timeframe}")
        logger.info(f"   📅 In-Sample: {in_sample_days} gün, Out-of-Sample: {out_of_sample_days} gün")
        logger.info(f"   🔬 Trials: {n_trials}, Metric: {optimization_metric}")
        
        try:
            # 1. Veriyi Parquet Lake'ten çek
            logger.info(f"📊 [WFO] Veri çekiliyor: {symbol} {timeframe}")
            data = await self._fetch_data(symbol, timeframe, in_sample_days + out_of_sample_days)
            
            if data is None or len(data) < 100:
                logger.warning(f"⚠️ [WFO] Yetersiz veri: {len(data) if data else 0} mum")
                return {}
            
            # 2. In-Sample / Out-of-Sample böl
            logger.info(f"📊 [WFO] Veri bölünüyor (In-Sample / Out-of-Sample)")
            train_data, test_data = self._split_data(data, in_sample_days, out_of_sample_days)
            
            if len(train_data) < 50 or len(test_data) < 10:
                logger.warning(f"⚠️ [WFO] Yetersiz veri: Train={len(train_data)}, Test={len(test_data)}")
                return {}
            
            # 3. Auto-Grid ile parametre uzayı oluştur
            if param_grid is None:
                logger.info(f"🔧 [WFO] Auto-Grid ile parametre uzayı oluşturuluyor")
                strategy_instance = strategy_class()
                param_grid = auto_grid.generate_from_strategy(strategy_instance)
            else:
                logger.info(f"🔧 [WFO] Manuel param grid kullanılıyor")
            
            # 4. Bayesian Optimization (TPE)
            logger.info(f"🧠 [WFO] Bayesian Optimization başlatılıyor (TPE Sampler)")
            
            # Optuna study oluştur
            study = optuna.create_study(
                direction='maximize',
                sampler=TPESampler(seed=42),
                study_name=f'wfo_{symbol}_{timeframe}'
            )
            
            # Objective fonksiyonu (CPU-bound, thread pool'da çalışacak)
            objective = lambda trial: self._objective(
                trial,
                train_data=train_data,
                test_data=test_data,
                strategy_class=strategy_class,
                param_grid=param_grid,
                optimization_metric=optimization_metric
            )
            
            # Thread pool'da çalıştır (Event Loop'u bloklamaz)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                lambda: study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
            )
            
            # 5. En iyi parametreleri al
            best_params = study.best_params
            best_value = study.best_value
            
            logger.info(f"✅ [WFO] Optimizasyon tamamlandı!")
            logger.info(f"   🏆 Best {optimization_metric}: {best_value:.4f}")
            logger.info(f"   🎯 Best params: {best_params}")
            
            # 6. Out-of-Sample doğrulama
            logger.info(f"🔍 [WFO] Out-of-Sample doğrulama")
            oos_metrics = await self._validate_out_of_sample(
                best_params,
                test_data,
                strategy_class
            )
            
            # 7. Overfitting kontrolü
            overfitting = self._check_overfitting(best_value, oos_metrics.get(optimization_metric, 0))
            
            if overfitting:
                logger.warning(f"⚠️ [WFO] Overfitting tespit edildi! IS={best_value:.4f}, OOS={oos_metrics.get(optimization_metric, 0):.4f}")
            else:
                logger.info(f"✅ [WFO] Overfitting yok (IS={best_value:.4f}, OOS={oos_metrics.get(optimization_metric, 0):.4f})")
            
            return {
                'best_params': best_params,
                'best_value': best_value,
                'optimization_metric': optimization_metric,
                'in_sample_days': in_sample_days,
                'out_of_sample_days': out_of_sample_days,
                'oos_metrics': oos_metrics,
                'overfitting': overfitting,
                'n_trials': n_trials
            }
            
        except Exception as e:
            logger.error(f"❌ [WFO] Optimizasyon hatası: {e}")
            return {}
    
    async def _fetch_data(self, symbol: str, timeframe: str, days: int) -> pd.DataFrame:
        """
        Hibrit Veri Sağlayıcıdan veri çek (Diskten 1m, RAM'de resample).
        
        Args:
            symbol: Sembol
            timeframe: Timeframe
            days: Gün sayısı
        
        Returns:
            OHLCV DataFrame
        """
        from api.services.data_service import DataService
        data_service = DataService()
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Hibrit veri okuma
        data = await data_service.get_cached_or_fetch_data(symbol, timeframe, start_date, end_date)
        
        if data is not None:
            if data.index.tzinfo is not None:
                data.index = data.index.tz_convert(None)
            logger.info(f"📊 [WFO] {len(data)} mum yüklendi (Hibrit Sağlayıcı)")
        
        return data
    
    def _split_data(
        self,
        data: pd.DataFrame,
        in_sample_days: int,
        out_of_sample_days: int
    ) -> tuple:
        """
        Veriyi In-Sample ve Out-of-Sample olarak böl.
        
        Args:
            data: OHLCV DataFrame
            in_sample_days: In-Sample gün sayısı
            out_of_sample_days: Out-of-Sample gün sayısı
        
        Returns:
            (train_data, test_data) tuple
        """
        total_days = in_sample_days + out_of_sample_days
        
        # In-Sample: İlk in_sample_days gün
        train_end_idx = int(len(data) * (in_sample_days / total_days))
        
        train_data = data.iloc[:train_end_idx].copy()
        test_data = data.iloc[train_end_idx:].copy()
        
        logger.info(f"📊 [WFO] Split: Train={len(train_data)} mum, Test={len(test_data)} mum")
        
        return train_data, test_data
    
    def _objective(
        self,
        trial: optuna.trial.Trial,
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        strategy_class: Type,
        param_grid: Dict[str, Any],
        optimization_metric: str
    ) -> float:
        """
        Bayesian Optimization objective fonksiyonu.
        
        Args:
            trial: Optuna trial
            train_data: In-Sample veri
            test_data: Out-of-Sample veri
            strategy_class: Strateji sınıfı
            param_grid: Parametre uzayı
            optimization_metric: Optimizasyon metriği
        
        Returns:
            Sharpe ratio veya Net PnL (maximize edilecek)
        """
        # 1. Parametreleri öner
        params = {}
        for param_name, param_range in param_grid.items():
            if isinstance(param_range[0], int):
                params[param_name] = trial.suggest_int(param_name, param_range[0], param_range[2])
            else:
                params[param_name] = trial.suggest_float(param_name, param_range[0], param_range[2])
        
        # 2. Strateji instance oluştur ve parametreleri güncelle
        strategy = strategy_class()
        if hasattr(strategy, 'update_params'):
            strategy.update_params(params)
        
        # 3. In-Sample backtest
        try:
            metrics = self._backtest(strategy, train_data)
        except Exception as e:
            logger.debug(f"⚠️ [WFO] Backtest hatası: {e}")
            return 0.0  # Kötü skor
        
        # 4. Metriği döndür
        if optimization_metric == 'sharpe':
            return metrics.get('sharpe_ratio', 0.0)
        else:
            return metrics.get('net_pnl', 0.0)
    
    def _backtest(
        self,
        strategy: Any,
        data: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Basit backtest (vektörize) - KOMİSYON VE SLIPPAGE dahil.

        Binance Futures komisyon oranları:
        - Maker: %0.02 (0.0002)
        - Taker: %0.04 (0.0004)

        Slippage: %0.01 (0.0001) minimum kayma

        Args:
            strategy: Strateji instance
            data: OHLCV DataFrame

        Returns:
            Metrikler (sharpe_ratio, net_pnl, vb.)
        """
        # Komisyon ve slippage oranları
        MAKER_FEE = 0.0002  # %0.02
        TAKER_FEE = 0.0004  # %0.04
        SLIPPAGE = 0.0001   # %0.01

        # Strateji sinyallerini üret
        if hasattr(strategy, 'generate_signals'):
            signals = strategy.generate_signals(data)
        else:
            # Basit momentum stratejisi (fallback)
            signals = pd.Series(0, index=data.index)
            signals[data['close'] > data['close'].rolling(20).mean()] = 1
            signals[data['close'] < data['close'].rolling(20).mean()] = -1

        # İşlem sayısını hesapla (her sinyal değişimi 1 işlem)
        trades = abs(signals.diff()).fillna(0)
        total_trades = trades.sum() / 2

        # Getiri hesapla
        returns = data['close'].pct_change()

        # Strateji getirisi (sinyal bir önceki mumdan)
        strategy_returns = signals.shift(1) * returns

        # KOMİSYON VE SLIPPAGE düş
        # Her işlem için: (commission + slippage) * 2 (giriş + çıkış)
        trade_cost = (TAKER_FEE + SLIPPAGE) * 2
        strategy_returns = strategy_returns - (trades * trade_cost)

        # Sharpe ratio (yıllık) - komisyonlar düşüldükten sonra
        sharpe = (strategy_returns.mean() / strategy_returns.std()) * np.sqrt(252 * 24) if strategy_returns.std() > 0 else 0

        # Net PnL (komisyonlar düşüldükten sonra)
        net_pnl = (1 + strategy_returns).prod() - 1

        logger.debug(f"📊 [WFO] Backtest: Trades={total_trades:.0f}, Sharpe={sharpe:.4f}, PnL={net_pnl:.2%}")

        return {
            'sharpe_ratio': sharpe,
            'net_pnl': net_pnl,
            'total_trades': total_trades,
            'commission_costs': total_trades * trade_cost
        }
    
    async def _validate_out_of_sample(
        self,
        params: Dict[str, Any],
        test_data: pd.DataFrame,
        strategy_class: Type
    ) -> Dict[str, float]:
        """
        Out-of-Sample doğrulama.
        
        Args:
            params: En iyi parametreler
            test_data: Out-of-Sample veri
            strategy_class: Strateji sınıfı
        
        Returns:
            OOS metrikler
        """
        # Strateji oluştur
        strategy = strategy_class()
        if hasattr(strategy, 'update_params'):
            strategy.update_params(params)
        
        # Backtest
        metrics = self._backtest(strategy, test_data)
        
        logger.info(f"🔍 [WFO] OOS Sharpe: {metrics.get('sharpe_ratio', 0):.4f}, PnL: {metrics.get('net_pnl', 0):.2%}")
        
        return metrics
    
    def _check_overfitting(
        self,
        is_score: float,
        oos_score: float,
        optimization_metric: str = 'sharpe'
    ) -> bool:
        """
        Dinamik Overfitting kontrolü.

        Args:
            is_score: In-Sample skoru
            oos_score: Out-of-Sample skoru
            optimization_metric: Optimizasyon metriği ('sharpe' veya 'net_pnl')

        Returns:
            True ise overfitting var

        Dinamik Eşikler:
            - Sharpe: Maksimum %30 sapma (1.3x ratio)
            - Net PnL: Maksimum %50 sapma (1.5x ratio)
        """
        if abs(is_score) < 0.01:  # Çok küçük skorlar için kontrol etme
            return False

        if oos_score == 0:
            return True  # OOS sıfır ise overfitting

        # Mutlak değer al (negatif sharpe olabilir)
        is_abs = abs(is_score)
        oos_abs = abs(oos_score)

        if oos_abs == 0:
            return True

        # Sapma oranı hesapla (ratio)
        overfitting_ratio = is_abs / oos_abs

        # Dinamik eşik
        if optimization_metric == 'sharpe':
            MAX_OVERFITTING_RATIO = 1.3  # Sharpe için %30 sapma
        else:
            MAX_OVERFITTING_RATIO = 1.5  # Net PnL için %50 sapma

        is_overfitting = overfitting_ratio > MAX_OVERFITTING_RATIO

        logger.debug(
            f"🔍 [WFO] Overfitting kontrolü: IS={is_score:.4f}, OOS={oos_score:.4f}, "
            f"Ratio={overfitting_ratio:.2f}, Max={MAX_OVERFITTING_RATIO}, "
            f"Overfitting={is_overfitting}"
        )

        return is_overfitting
    
    def __del__(self):
        """Destructor - thread pool'ı temizle"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)


# Singleton instance
wfo_engine = WFOEngine()

# Export
__all__ = ['WFOEngine', 'wfo_engine', 'start_wfo_background_task']


async def start_wfo_background_task(
    symbol: str,
    timeframe: str,
    strategy_class: Type,
    param_grid: Dict[str, Any] = None,
    optimization_metric: str = 'sharpe',
    n_trials: int = 50,
    in_sample_days: int = 30,
    out_of_sample_days: int = 7,
    reoptimize_interval: int = 168  # Saat (1 hafta)
):
    """
    WFO arka plan görevi (otomatik yeniden optimizasyon).

    Args:
        symbol: Sembol
        timeframe: Timeframe
        strategy_class: Strateji sınıfı
        param_grid: Manuel param grid (None ise auto-grid)
        optimization_metric: Optimizasyon metriği
        n_trials: Optuna deneme sayısı
        in_sample_days: In-Sample gün sayısı
        out_of_sample_days: Out-of-Sample gün sayısı
        reoptimize_interval: Yeniden optimizasyon aralığı (saat)
    """
    logger.info(f"🧠 [WFO] Arka plan görevi başlatıldı: {symbol} {timeframe}")
    logger.info(f"   📅 Reoptimize interval: {reoptimize_interval} saat")

    while True:
        try:
            # Optimizasyon çalıştır
            result = await wfo_engine.optimize(
                symbol=symbol,
                timeframe=timeframe,
                strategy_class=strategy_class,
                in_sample_days=in_sample_days,
                out_of_sample_days=out_of_sample_days,
                n_trials=n_trials,
                optimization_metric=optimization_metric,
                param_grid=param_grid
            )

            if not result:
                logger.warning(f"⚠️ [WFO] Veriler hibrit servisten gelene kadar bekleniyor... (Retry 60s)")
                await asyncio.sleep(60)
                continue

            # Eğer overfitting yoksa parametreleri güncelle
            if result and not result.get('overfitting', True):
                logger.info(f"✅ [WFO] Parametreler güncellendi: {result.get('best_params', {})}")

                # Strateji instance bul ve güncelle
                from strategy.manager import StrategyManager
                strategy = StrategyManager.get_strategy_by_symbol(symbol)
                if strategy and hasattr(strategy, 'update_params'):
                    strategy.update_params(result['best_params'])
                    logger.info(f"📝 [WFO] Strateji parametreleri canlı bota uygulandı")

            # Bekle (reoptimize interval)
            logger.info(f"⏳ [WFO] Sonraki optimizasyon: {reoptimize_interval} saat")
            await asyncio.sleep(reoptimize_interval * 3600)

        except asyncio.CancelledError:
            logger.info(f"🛑 [WFO] Arka plan görevi durduruldu: {symbol}")
            break
        except Exception as e:
            logger.error(f"❌ [WFO] Arka plan hatası: {e}")
            logger.info(f"⏳ [WFO] Veriler hibrit servisten gelene kadar bekleniyor... (Retry 60s)")
            await asyncio.sleep(60)  # 60 saniye bekle ve tekrar dene


# Singleton instance
_wfo_engine_instance: Optional['WFOEngine'] = None


def get_wfo_engine() -> Optional['WFOEngine']:
    """
    WFO Engine singleton instance'ını al.

    Returns:
        WFOEngine: Singleton instance veya None (WFO kapalıysa)
    """
    global _wfo_engine_instance

    if _wfo_engine_instance is None:
        if not CONFIG.get('wfo', {}).get('enabled', False):
            logger.warning("⚠️ WFO kapalı, engine başlatılmadı")
            return None

        _wfo_engine_instance = WFOEngine()
        logger.info("🧠 [WFO] Engine singleton başlatıldı")

    return _wfo_engine_instance


# Kolay import için
__all__ = ['WFOEngine', 'get_wfo_engine', 'start_wfo_background_task']
