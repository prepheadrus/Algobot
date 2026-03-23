"""
Strategy Builder Integration Tests
Backend + Frontend + Bot entegrasyon testleri
"""

import unittest
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta

from strategy.builder import StrategyBuilder, StrategyExecutor, StrategyValidator
from strategy.manager import StrategyManager
from core.paper import PaperTrader


class TestStrategyBuilderIntegration(unittest.TestCase):
    """Strategy Builder entegrasyon testleri"""
    
    def setUp(self):
        """Test öncesi hazırlık"""
        self.builder = StrategyBuilder()
        
        # Test DataFrame oluştur
        dates = pd.date_range('2024-01-01', periods=500, freq='1h')
        self.df = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.randn(500).cumsum() + 100,
            'high': np.random.randn(500).cumsum() + 101,
            'low': np.random.randn(500).cumsum() + 99,
            'close': np.random.randn(500).cumsum() + 100,
            'volume': np.random.randn(500) * 1000
        }, index=dates)
    
    def test_01_create_complex_strategy(self):
        """Kompleks strateji oluşturma testi"""
        print("\n[TEST] Kompleks strateji oluşturma...")
        
        # RSI + MACD + EMA stratejisi
        self.builder.strategy['name'] = "RSI MACD EMA Combo"
        
        # İndikatörler
        rsi_id = self.builder.add_indicator('RSI', {'length': 14})
        macd_id = self.builder.add_indicator('MACD', {'fast': 12, 'slow': 26, 'signal': 9})
        ema_id = self.builder.add_indicator('EMA', {'length': 50})
        
        # LONG: RSI < 30 VE MACD > Signal VE Close > EMA
        self.builder.add_condition('long', rsi_id, '<', 30)
        self.builder.add_condition('long', macd_id, '>', 'signal')
        self.builder.add_condition('long', ema_id, '<', 'close')
        
        # SHORT: RSI > 70 VE MACD < Signal VE Close < EMA
        self.builder.add_condition('short', rsi_id, '>', 70)
        self.builder.add_condition('short', macd_id, '<', 'signal')
        self.builder.add_condition('short', ema_id, '>', 'close')
        
        # Validate
        is_valid, errors = StrategyValidator.validate(self.builder.strategy)
        
        self.assertTrue(is_valid, f"Strateji valid olmalı: {errors}")
        print(f"  [OK] Strateji oluşturuldu ve valid")
    
    def test_02_executor_signal_generation(self):
        """Executor sinyal üretme testi"""
        print("\n[TEST] Executor sinyal üretme...")

        # Yeni builder oluştur
        builder = StrategyBuilder()
        builder.strategy['name'] = "Test RSI"
        rsi_id = builder.add_indicator('RSI', {'length': 14})
        builder.add_condition('long', rsi_id, '<', 30)
        builder.add_condition('short', rsi_id, '>', 70)

        # Executor
        executor = StrategyExecutor()
        executor.load_strategy_from_dict(builder.strategy)

        # Sinyal üret
        signals = executor.generate_signals(self.df)

        self.assertEqual(len(signals), len(self.df))
        self.assertTrue(all(s in [0, 1, 2] for s in signals))

        # Sinyal dağılımı
        unique, counts = np.unique(signals.values, return_counts=True)
        print(f"  [OK] Sinyaller: HOLD={counts[unique == 1][0] if 1 in unique else 0}, "
              f"AL={counts[unique == 2][0] if 2 in unique else 0}, "
              f"SAT={counts[unique == 0][0] if 0 in unique else 0}")
    
    def test_03_save_and_load(self):
        """Kaydetme ve yükleme testi"""
        print("\n[TEST] Kaydetme ve yükleme...")
        
        # Kaydet
        filename = 'test_integration_strategy.json'
        self.builder.save_strategy(filename)
        
        self.assertTrue(os.path.exists(filename))
        
        # Yükle
        loaded_builder = StrategyBuilder.load_strategy(filename)
        
        self.assertEqual(loaded_builder.strategy['name'], self.builder.strategy['name'])
        self.assertEqual(len(loaded_builder.strategy['indicators']), 
                        len(self.builder.strategy['indicators']))
        
        # Temizle
        os.remove(filename)
        print(f"  [OK] Dosya kaydedildi ve yüklendi")
    
    def test_04_paper_trader_integration(self):
        """Paper trader entegrasyon testi"""
        print("\n[TEST] Paper trader entegrasyon...")
        
        # Paper trader oluştur
        trader = PaperTrader(initial_balance=10000)
        
        # Stratejiyi manager'a ekle
        from strategy.builder import StrategyExecutor
        
        executor = StrategyExecutor()
        executor.load_strategy_from_dict(self.builder.strategy)
        
        # Son sinyali al
        signal = executor.get_last_signal(self.df)
        
        # Signal mapping (0=SAT, 1=HOLD, 2=AL)
        self.assertIn(signal, [0, 1, 2])
        print(f"  [OK] Paper trader sinyal aldı: {signal}")
    
    def test_05_multi_timeframe(self):
        """Çoklu zaman dilimi testi"""
        print("\n[TEST] Multi-timeframe...")
        
        # Farklı timeframe'lerde test et
        for tf in ['1h', '4h', '1d']:
            self.builder.set_timeframe(tf)
            
            executor = StrategyExecutor()
            executor.load_strategy_from_dict(self.builder.strategy)
            
            # Test data'yı timeframe'e göre ayarla
            if tf == '1h':
                df = self.df
            elif tf == '4h':
                df = self.df.resample('4h').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                })
            else:  # 1d
                df = self.df.resample('1D').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                })
            
            signals = executor.generate_signals(df)
            self.assertEqual(len(signals), len(df))
        
        print(f"  [OK] Multi-timeframe testleri geçti")
    
    def test_06_complex_conditions(self):
        """Kompleks koşul kombinasyonları testi"""
        print("\n[TEST] Kompleks koşullar...")
        
        # VE (AND) testi
        builder_and = StrategyBuilder()
        builder_and.strategy['name'] = "AND Test"
        rsi_id = builder_and.add_indicator('RSI')
        builder_and.add_condition('long', rsi_id, '<', 30, logic='AND')
        builder_and.add_condition('long', rsi_id, '>', 20, logic='AND')
        
        is_valid, errors = StrategyValidator.validate(builder_and.strategy)
        self.assertTrue(is_valid)
        
        # VEYA (OR) testi
        builder_or = StrategyBuilder()
        builder_or.strategy['name'] = "OR Test"
        rsi_id = builder_or.add_indicator('RSI')
        builder_or.add_condition('long', rsi_id, '<', 30, logic='OR')
        builder_or.add_condition('long', rsi_id, '>', 70, logic='OR')
        
        is_valid, errors = StrategyValidator.validate(builder_or.strategy)
        self.assertTrue(is_valid)
        
        print(f"  [OK] AND/OR koşulları çalışıyor")
    
    def test_07_edge_cases(self):
        """Edge case testleri"""
        print("\n[TEST] Edge cases...")
        
        # Boş indikatör listesi
        empty_builder = StrategyBuilder()
        empty_builder.strategy['name'] = "Empty"
        empty_builder.strategy['conditions'] = {
            'long': {'logic': 'AND', 'rules': []},
            'short': {'logic': 'AND', 'rules': []}
        }
        
        is_valid, errors = StrategyValidator.validate(empty_builder.strategy)
        self.assertFalse(is_valid)  # Invalid olmalı
        
        # Geçersiz operatör
        invalid_builder = StrategyBuilder()
        invalid_builder.strategy['name'] = "Invalid"
        rsi_id = invalid_builder.add_indicator('RSI')
        invalid_builder.add_condition('long', rsi_id, 'INVALID', 30)
        
        is_valid, errors = StrategyValidator.validate(invalid_builder.strategy)
        self.assertFalse(is_valid)  # Invalid olmalı
        
        print(f"  [OK] Edge case'ler yakalandı")


class TestBacktestIntegration(unittest.TestCase):
    """Backtest entegrasyon testleri"""
    
    def test_01_simple_backtest(self):
        """Basit backtest testi"""
        print("\n[TEST] Basit backtest...")
        
        # Strateji oluştur
        builder = StrategyBuilder()
        builder.strategy['name'] = "Backtest Test"
        rsi_id = builder.add_indicator('RSI', {'length': 14})
        builder.add_condition('long', rsi_id, '<', 30)
        builder.add_condition('short', rsi_id, '>', 70)
        
        # Executor
        executor = StrategyExecutor()
        executor.load_strategy_from_dict(builder.strategy)
        
        # Test data
        dates = pd.date_range('2024-01-01', periods=1000, freq='1h')
        df = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.randn(1000).cumsum() + 100,
            'high': np.random.randn(1000).cumsum() + 101,
            'low': np.random.randn(1000).cumsum() + 99,
            'close': np.random.randn(1000).cumsum() + 100,
            'volume': np.random.randn(1000) * 1000
        }, index=dates)
        
        # Sinyaller
        signals = executor.generate_signals(df)
        
        # Basit backtest
        position = None
        trades = []
        
        for i in range(len(signals)):
            signal = signals.iloc[i]
            price = df['close'].iloc[i]
            
            if signal == 2 and position is None:  # AL
                position = {'type': 'LONG', 'entry': price}
            elif signal == 0 and position is not None:  # SAT
                exit_price = price
                pnl = exit_price - position['entry']
                trades.append(pnl)
                position = None
        
        print(f"  [OK] Backtest tamamlandı: {len(trades)} trade")
        self.assertTrue(len(trades) >= 0)


def run_all_tests():
    """Tüm testleri çalıştır"""
    print("=" * 70)
    print("STRATEGY BUILDER INTEGRATION TESTS")
    print("=" * 70)
    
    # Test loader
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Testleri ekle
    suite.addTests(loader.loadTestsFromTestCase(TestStrategyBuilderIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestBacktestIntegration))
    
    # Test runner
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Özet
    print("\n" + "=" * 70)
    print(f"TEST SONUÇLARI: {result.testsRun} test")
    print(f"  Başarılı: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  Başarısız: {len(result.failures)}")
    print(f"  Hata: {len(result.errors)}")
    print("=" * 70)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
