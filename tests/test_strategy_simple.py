"""
Strategy Builder - Basit Test Suite
"""

import pandas as pd
import numpy as np
from strategy.builder import StrategyBuilder, StrategyExecutor, StrategyValidator


def test_basic():
    """Temel testler"""
    print("\n[TEST 1] Temel strateji oluşturma...")
    
    builder = StrategyBuilder()
    builder.strategy['name'] = "Test RSI"
    
    # İndikatör ekle
    rsi_id = builder.add_indicator('RSI', {'length': 14})
    print(f"  [OK] RSI eklendi: {rsi_id}")
    
    # Koşul ekle
    builder.add_condition('long', rsi_id, '<', 30)
    builder.add_condition('short', rsi_id, '>', 70)
    print(f"  [OK] Koşullar eklendi")
    
    # Validate
    is_valid, errors = StrategyValidator.validate(builder.strategy)
    assert is_valid, f"Valid olmalı: {errors}"
    print(f"  [OK] Strateji valid")
    
    return builder


def test_executor(builder, df):
    """Executor testi"""
    print("\n[TEST 2] Executor sinyal üretme...")
    
    executor = StrategyExecutor()
    executor.load_strategy_from_dict(builder.strategy)
    
    signals = executor.generate_signals(df)
    
    assert len(signals) == len(df)
    assert all(s in [0, 1, 2] for s in signals)
    
    print(f"  [OK] {len(signals)} sinyal üretildi")
    return executor


def test_save_load(builder):
    """Kaydetme/yükleme testi"""
    print("\n[TEST 3] Kaydetme ve yükleme...")
    
    filename = 'test_strategy.json'
    builder.save_strategy(filename)
    
    loaded = StrategyBuilder.load_strategy(filename)
    
    assert loaded.strategy['name'] == builder.strategy['name']
    
    import os
    os.remove(filename)
    
    print(f"  [OK] Dosya kaydedildi ve yüklendi")


def test_multi_tf(df):
    """Multi-timeframe testi"""
    print("\n[TEST 4] Multi-timeframe...")
    
    for tf in ['1h', '4h']:
        builder = StrategyBuilder()
        builder.strategy['name'] = f"TF {tf}"
        rsi_id = builder.add_indicator('RSI')
        builder.add_condition('long', rsi_id, '<', 30)
        builder.set_timeframe(tf)
        
        executor = StrategyExecutor()
        executor.load_strategy_from_dict(builder.strategy)
        
        signals = executor.generate_signals(df)
        assert len(signals) == len(df)
    
    print(f"  [OK] Multi-timeframe çalışıyor")


def test_validation():
    """Validation testleri"""
    print("\n[TEST 5] Validation...")
    
    # Boş indikatör
    empty = {'name': 'Empty', 'indicators': [], 'conditions': {'long': {}, 'short': {}}}
    is_valid, errors = StrategyValidator.validate(empty)
    assert not is_valid, "Invalid olmalı"
    print(f"  [OK] Boş indikatör yakalandı")
    
    # Geçersiz operatör
    try:
        builder = StrategyBuilder()
        rsi_id = builder.add_indicator('RSI')
        builder.add_condition('long', rsi_id, 'INVALID', 30)
        assert False, "Exception fırlatmalı"
    except ValueError:
        print(f"  [OK] Geçersiz operatör yakalandı")


def main():
    """Ana test runner"""
    print("=" * 60)
    print("STRATEGY BUILDER TEST SUITE")
    print("=" * 60)
    
    # Test data
    dates = pd.date_range('2024-01-01', periods=200, freq='1h')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.randn(200).cumsum() + 100,
        'high': np.random.randn(200).cumsum() + 101,
        'low': np.random.randn(200).cumsum() + 99,
        'close': np.random.randn(200).cumsum() + 100,
        'volume': np.random.randn(200) * 1000
    }, index=dates)
    
    try:
        # Test 1
        builder = test_basic()
        
        # Test 2
        executor = test_executor(builder, df)
        
        # Test 3
        test_save_load(builder)
        
        # Test 4
        test_multi_tf(df)
        
        # Test 5
        test_validation()
        
        print("\n" + "=" * 60)
        print("[OK] TUM TESTLER BASARILI!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n[FAIL] TEST HATASI: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
