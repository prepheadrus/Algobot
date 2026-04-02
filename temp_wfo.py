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
    from core.wfo_engine import OptimizationConfig
    config = OptimizationConfig(
        symbol='BTC/USDT',
        timeframe='1h',
        strategy_class=TrendMaster,
        in_sample_days=30,
        out_of_sample_days=7,
        n_trials=50
    )
    best_params = await engine.optimize(config)
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


from dataclasses import dataclass

@dataclass
class OptimizationConfig:
    symbol: str
    timeframe: str
    strategy_class: Type
    in_sample_days: Optional[int] = None
    out_of_sample_days: Optional[int] = None
    n_trials: Optional[int] = None
    optimization_metric: Optional[str] = None
    param_grid: Optional[Dict[str, Any]] = None


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

    async def optimize(self, config: OptimizationConfig) -> Dict[str, Any]:
        """
        Walk-Forward Bayesian optimizasyon çalıştır.

        Args:
            config: Optimizasyon konfigürasyonu

        Returns:
            En iyi parametreler ve metrikler
        """
        # Varsayılan değerler
        symbol = config.symbol
        timeframe = config.timeframe
        strategy_class = config.strategy_class
        in_sample_days = config.in_sample_days or self.DEFAULT_IN_SAMPLE_DAYS
        out_of_sample_days = config.out_of_sample_days or self.DEFAULT_OUT_OF_SAMPLE_DAYS
        n_trials = config.n_trials or self.DEFAULT_N_TRIALS
        optimization_metric = config.optimization_metric or self.DEFAULT_OPTIMIZATION_METRIC
        param_grid = config.param_grid

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
        Parquet Lake'ten veri çek.

        Args:
            symbol: Sembol
            timeframe: Timeframe
            days: Gün sayısı

        Returns:
            OHLCV DataFrame
        """
        lake = get_parquet_lake('binance')

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Vektörize okuma
        data = await lake.load_datasets(symbol, timeframe, start_date, end_date)

        if data is not None:
            logger.info(f"📊 [WFO] {len(data)} mum yüklendi")

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
