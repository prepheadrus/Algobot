"""
Walk-Forward Optimization (WFO) Motoru

Bu modül, strateji parametrelerinin zaman içinde değişen piyasa koşullarına göre
optimize edilmesini sağlar. Belirlenen parametre kombinasyonları üzerinde
grid search yaparak en iyi performans gösteren kombinasyonu bulur.
"""

import itertools
import pandas as pd
from typing import Dict, Any, List
from core.logger import logger


class WalkForwardOptimizer:
    """
    Walk-Forward Optimization (WFO) sınıfı.

    Parametre aralıklarını alır ve grid search yöntemiyle en iyi parametre
    kombinasyonunu bulur. Her bir kombinasyon için VectorizedBacktester
    kullanarak backtest yapar ve en yüksek net PnL getiren kombinasyonu döner.
    """

    def __init__(self):
        self.results = []
        self.wfo_trades = []
        self.wfo_metrics = []
    
    def run_grid_search(self, df: pd.DataFrame, strategy_class, param_grid: Dict[str, List[Any]]) -> Dict[str, Any]:
        """
        Parametre ızgarası üzerinde grid search yapar ve en iyi parametreleri döner.
        
        Args:
            df: Backtest yapılacak veri seti
            strategy_class: Strateji sınıfı (BaseStrategy'den türemiş olmalı)
            param_grid: Parametre adı ve değerlerinden oluşan sözlük
                      Örnek: {'ema_fast': [5, 10, 15], 'rsi_period': [14, 20]}
        
        Returns:
            Dict[str, Any]: En iyi parametreler ve skor
        """
        # Parametre kombinasyonlarını oluştur
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        
        best_params = {}
        best_score = float('-inf')
        total_combinations = 0
        
        # Tüm kombinasyonları gez
        for combination in itertools.product(*param_values):
            current_params = dict(zip(param_names, combination))
            total_combinations += 1
            
            try:
                # Parametreleri stratejiye uygulayarak backtest yap
                score = self._evaluate_strategy(df, strategy_class, current_params)
                
                # Sonuçları sakla
                self.results.append({
                    'params': current_params,
                    'score': score
                })
                
                # En iyi skoru güncelle
                if score > best_score:
                    best_score = score
                    best_params = current_params.copy()
                    
            except Exception as e:
                logger.error(f"Parametre kombinasyonu başarısız oldu {current_params}: {str(e)}")
                # Hata durumunda bu kombinasyonu atla
                continue
        
        logger.info(f"Toplam {total_combinations} kombinasyondan {len(self.results)} başarıyla tamamlandı.")
        logger.info(f"En iyi skor: {best_score} | En iyi parametreler: {best_params}")
        
        return {
            'best_params': best_params,
            'best_score': best_score,
            'total_evaluated': len(self.results)
        }
    
    def _evaluate_strategy(self, df: pd.DataFrame, strategy_class, params: Dict[str, Any]) -> float:
        """
        Belirli parametrelerle stratejiyi değerlendirir ve net PnL döner.
        
        Args:
            df: Veri seti
            strategy_class: Strateji sınıfı
            params: Parametreler sözlüğü
        
        Returns:
            float: Net PnL (kar-zarar)
        """
        # Strateji örneği oluştur
        strategy = strategy_class()
        
        # Parametreleri stratejiye uygula
        # Burada strateji sınıfına özel parametre atama mekanizması olabilir
        # Bu örnek için sadece strateji sınıfında gerekli setter metodları olacağını varsayıyoruz
        
        # Basit bir geriye dönük test simülasyonu
        # Gerçek implementasyonda VectorizedBacktester kullanılmalı
        
        # Parametreleri doğrudan strateji nesnesine atayalım
        for param_name, param_value in params.items():
            if hasattr(strategy, param_name):
                setattr(strategy, param_name, param_value)
            else:
                # Eğer doğrudan özellik olarak yoksa, stratejiye özel parametre atama fonksiyonu olabilir
                setter_method = f"set_{param_name}"
                if hasattr(strategy, setter_method):
                    getattr(strategy, setter_method)(param_value)
        
        # Simüle edilmiş backtest
        # Bu kısım VectorizedBacktester sınıfı ile değiştirilmeli
        net_pnl = self._simulate_backtest(df, strategy)
        
        return net_pnl
    
    def _simulate_backtest(self, df: pd.DataFrame, strategy) -> float:
        """
        Basit bir backtest simülasyonu.
        Gerçek implementasyonda VectorizedBacktester kullanılmalı.
        
        Args:
            df: Veri seti
            strategy: Strateji örneği
        
        Returns:
            float: Net PnL
        """
        # Strateji sinyalleri oluştur
        signals = []
        for idx, row in df.iterrows():
            signal = strategy.generate_signal(row)
            signals.append(signal)
        
        # İşlem geçmişini simüle et
        positions = []
        current_position = 0
        entry_price = 0
        total_pnl = 0
        
        for i in range(1, len(signals)):
            prev_signal = signals[i-1]
            curr_signal = signals[i]
            current_price = df['close'].iloc[i]
            prev_price = df['close'].iloc[i-1]
            
            # Pozisyon açma/kapama mantığı
            if prev_signal == 1:  # BEKLE
                continue
            elif prev_signal == 2 and current_position <= 0:  # AL
                entry_price = current_price
                current_position = 1
            elif prev_signal == 0 and current_position >= 0:  # SAT
                if current_position != 0:  # Pozisyon varsa
                    if current_position == 1:  # LONG pozisyonu kapat
                        pnl = (current_price - entry_price) / entry_price
                    else:  # SHORT pozisyonu kapat
                        pnl = (entry_price - current_price) / entry_price
                    total_pnl += pnl
                    current_position = 0
            # Pozisyon açık kalırsa, kar/zarar hesapla
            elif current_position != 0 and curr_signal != prev_signal:
                if current_position == 1:  # LONG pozisyonu kapat
                    pnl = (current_price - entry_price) / entry_price
                else:  # SHORT pozisyonu kapat
                    pnl = (entry_price - current_price) / entry_price
                total_pnl += pnl
                current_position = 0
        
        return total_pnl

    def run_wfo(
        self,
        df: pd.DataFrame,
        strategy_class,
        param_grid: Dict[str, List[Any]],
        train_days: int = 60,
        test_days: int = 15
    ) -> Dict[str, Any]:
        """
        Walk-Forward Optimization (WFO) döngüsünü çalıştırır.

        Algoritma:
        1. Veriyi kronolojik olarak pencerelere ayırır (train_days + test_days)
        2. Her iterasyonda:
           a) In-Sample (eğitim) verisi üzerinde grid search ile en iyi parametreleri bul
           b) Out-of-Sample (test) verisi üzerinde bu parametrelerle backtest yap
           c) Pencereyi ileri kaydır
        3. Tüm Out-of-Sample sonuçları birleştirerek kümülatif performans döndür

        Args:
            df: Backtest yapılacak veri seti (zaman serisi, kronolojik sıra)
            strategy_class: Strateji sınıfı (BaseStrategy'den türemiş olmalı)
            param_grid: Parametre aralıkları sözlüğü
            train_days: In-Sample (eğitim) pencere uzunluğu (gün)
            test_days: Out-of-Sample (test) pencere uzunluğu (gün)

        Returns:
            Dict[str, Any]: WFO sonuçları (işlemler, metrikler, parametre geçmişi)
        """
        logger.info(f"WFO başlatılıyor: train_days={train_days}, test_days={test_days}")

        # DataFrame'i zamana göre sırala
        df = df.sort_index()

        # Pencere boyutlarını hesapla (gün -> satır sayısı)
        # Eğer index datetime ise gün sayısını hesapla, değilse satır sayısı olarak kabul et
        if isinstance(df.index, pd.DatetimeIndex):
            # Index datetime ise: gün bazında pencere hesapla
            # Her gün için ortalama veri noktası sayısını bul
            if len(df) > 1:
                date_range = df.index[-1] - df.index[0]
                days_in_data = date_range.days + 1
                rows_per_day = len(df) / max(days_in_data, 1)
            else:
                rows_per_day = 1

            train_rows = int(train_days * rows_per_day)
            test_rows = int(test_days * rows_per_day)
        else:
            # Index datetime değilse: doğrudan satır sayısı kullan
            # Varsayım: 1 gün ≈ 1 satır (veya veri frekansına göre ayarlanabilir)
            train_rows = train_days
            test_rows = test_days

        min_window_size = train_rows + test_rows

        if len(df) < min_window_size:
            logger.error(f"Veri boyutu ({len(df)} satır) minimum pencere boyutundan ({min_window_size} satır) küçük!")
            return {
                'error': 'Yetersiz veri',
                'trades': [],
                'metrics': [],
                'total_pnl': 0.0
            }

        # WFO sonuçlarını sakla
        all_trades = []
        all_metrics = []
        window_params_history = []

        # Walk-Forward döngüsü
        window_start = 0
        window_num = 0

        while window_start + min_window_size <= len(df):
            window_num += 1

            # Pencere sınırlarını hesapla
            train_end = window_start + train_rows
            test_end = min(train_end + test_rows, len(df))

            # Sınır kontrolü (out of bounds koruması)
            if train_end >= len(df):
                logger.warning(f"Pencere {window_num}: Eğitim penceresi veri sonunu aşıyor, döngü sonlandırılıyor.")
                break

            # Veriyi böl
            train_df = df.iloc[window_start:train_end].copy()
            test_df = df.iloc[train_end:test_end].copy()

            if len(train_df) < train_rows or len(test_df) < 1:
                logger.warning(f"Pencere {window_num}: Geçersiz pencere boyutu, atlanıyor.")
                window_start += test_rows
                continue

            logger.info(f"Pencere {window_num}: Train[{window_start}:{train_end}] ({len(train_df)} satır), "
                       f"Test[{train_end}:{test_end}] ({len(test_df)} satır)")

            try:
                # Adım A: In-Sample optimizasyon (grid search)
                grid_result = self.run_grid_search(train_df, strategy_class, param_grid)

                if not grid_result.get('best_params'):
                    logger.warning(f"Pencere {window_num}: En iyi parametre bulunamadı, atlanıyor.")
                    window_start += test_rows
                    continue

                best_params = grid_result['best_params']
                best_score = grid_result['best_score']

                logger.info(f"Pencere {window_num}: En iyi parametreler = {best_params}, skor = {best_score}")

                # Parametre geçmişini sakla
                window_params_history.append({
                    'window': window_num,
                    'train_start': window_start,
                    'train_end': train_end,
                    'test_start': train_end,
                    'test_end': test_end,
                    'best_params': best_params,
                    'best_score': best_score
                })

                # Adım B: Out-of-Sample test (bulunan parametrelerle)
                oos_result = self._test_out_of_sample(
                    test_df, strategy_class, best_params
                )

                # Sonuçları sakla
                if oos_result.get('trades'):
                    all_trades.extend(oos_result['trades'])

                if oos_result.get('metrics'):
                    all_metrics.append({
                        'window': window_num,
                        'params': best_params,
                        **oos_result['metrics']
                    })

                logger.info(f"Pencere {window_num}: OOS PnL = {oos_result['metrics'].get('total_pnl', 0):.4f}")

            except Exception as e:
                logger.error(f"Pencere {window_num}: Hata oluştu: {str(e)}")
                # Hata durumunda bu pencereyi atla

            # Adım C: Pencereyi ileri kaydır (test_days kadar)
            window_start += test_rows

        # Sonuçları birleştir
        total_pnl = sum(m.get('total_pnl', 0) for m in all_metrics)

        result = {
            'trades': all_trades,
            'metrics': all_metrics,
            'params_history': window_params_history,
            'total_pnl': total_pnl,
            'total_windows': window_num,
            'successful_windows': len(all_metrics),
            'train_days': train_days,
            'test_days': test_days
        }

        logger.info(f"WFO tamamlandı: {window_num} pencere, {len(all_metrics)} başarılı, "
                   f"Toplam PnL = {total_pnl:.4f}")

        return result

    def _test_out_of_sample(
        self,
        test_df: pd.DataFrame,
        strategy_class,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Out-of-Sample verisi üzerinde stratejiyi test eder.

        Args:
            test_df: Test verisi (görülmemiş veri)
            strategy_class: Strateji sınıfı
            params: Kullanılacak parametreler

        Returns:
            Dict[str, Any]: Test sonuçları (işlemler, metrikler)
        """
        # Strateji örneği oluştur
        strategy = strategy_class()

        # Parametreleri uygula
        for param_name, param_value in params.items():
            if hasattr(strategy, param_name):
                setattr(strategy, param_name, param_value)
            else:
                setter_method = f"set_{param_name}"
                if hasattr(strategy, setter_method):
                    getattr(strategy, setter_method)(param_value)

        # Backtest simülasyonu
        trades = []
        positions = []
        current_position = 0
        entry_price = 0
        total_pnl = 0

        # Sinyalleri oluştur
        signals = []
        for idx, row in test_df.iterrows():
            try:
                signal = strategy.generate_signal(row)
                signals.append(signal)
            except Exception:
                signals.append(1)  # Hata durumunda BEKLE

        # İşlemleri simüle et
        for i in range(1, len(signals)):
            prev_signal = signals[i-1]
            curr_signal = signals[i]
            current_price = test_df['close'].iloc[i]
            timestamp = test_df.index[i] if hasattr(test_df.index[i], 'isoformat') else i

            # Pozisyon açma/kapama
            if prev_signal == 2 and current_position <= 0:  # AL
                entry_price = current_price
                current_position = 1
                positions.append({
                    'type': 'LONG',
                    'entry_price': entry_price,
                    'entry_time': timestamp
                })
            elif prev_signal == 0 and current_position >= 0:  # SAT
                if current_position == 1:  # LONG kapat
                    pnl = (current_price - entry_price) / entry_price
                    total_pnl += pnl
                    trades.append({
                        'type': 'CLOSE_LONG',
                        'entry_price': entry_price,
                        'exit_price': current_price,
                        'pnl': pnl,
                        'exit_time': timestamp
                    })
                    current_position = 0
            elif prev_signal == 3 and current_position >= 0:  # SHORT
                entry_price = current_price
                current_position = -1
                positions.append({
                    'type': 'SHORT',
                    'entry_price': entry_price,
                    'entry_time': timestamp
                })
            elif prev_signal == 1 and current_position != 0:  # BEKLE ama pozisyon açık
                if curr_signal != prev_signal:  # Sinyal değişti, pozisyonu kapat
                    if current_position == 1:
                        pnl = (current_price - entry_price) / entry_price
                        total_pnl += pnl
                        trades.append({
                            'type': 'CLOSE_LONG',
                            'entry_price': entry_price,
                            'exit_price': current_price,
                            'pnl': pnl,
                            'exit_time': timestamp
                        })
                    elif current_position == -1:
                        pnl = (entry_price - current_price) / entry_price
                        total_pnl += pnl
                        trades.append({
                            'type': 'CLOSE_SHORT',
                            'entry_price': entry_price,
                            'exit_price': current_price,
                            'pnl': pnl,
                            'exit_time': timestamp
                        })
                    current_position = 0

        return {
            'trades': trades,
            'metrics': {
                'total_pnl': total_pnl,
                'num_trades': len(trades),
                'win_rate': len([t for t in trades if t['pnl'] > 0]) / max(len(trades), 1)
            }
        }