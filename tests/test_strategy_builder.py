"""
Strategy Builder Testleri
"""

import pandas as pd
import numpy as np
from strategy.builder import StrategyBuilder, StrategyExecutor, StrategyValidator


def test_strategy_builder():
    """StrategyBuilder testi"""
    print("Testing StrategyBuilder...")
    
    # Builder oluştur
    builder = StrategyBuilder()
    builder.strategy['name'] = "Test RSI Strategy"
    
    # İndikatör ekle
    rsi_id = builder.add_indicator('RSI', {'length': 14})
    print(f"  [OK] RSI eklendi: {rsi_id}")

    # Koşul ekle
    builder.add_condition('long', rsi_id, '<', 30)
    builder.add_condition('short', rsi_id, '>', 70)
    print(f"  [OK] Kosullar eklendi")

    # Risk ayarla
    builder.set_risk_params(stop_loss=2.0, take_profit=3.0)
    print(f"  [OK] Risk parametreleri ayarlandi")

    # JSON'a çevir
    json_str = builder.get_strategy_json()
    print(f"  [OK] JSON olusturuldu")
    print(f"  Strategy: {builder}")

    # Kaydet
    builder.save_strategy('test_strategy.json')
    print(f"  [OK] Dosyaya kaydedildi: test_strategy.json")
    
    return builder


def test_validator():
    """StrategyValidator testi"""
    print("\nTesting StrategyValidator...")
    
    # Valid strateji
    builder = StrategyBuilder()
    builder.strategy['name'] = "Valid Strategy"
    rsi_id = builder.add_indicator('RSI')
    builder.add_condition('long', rsi_id, '<', 30)
    builder.add_condition('short', rsi_id, '>', 70)
    
    is_valid, errors = StrategyValidator.validate(builder.strategy)
    print(f"  Valid strategy test: {'[OK]' if is_valid else '[FAIL]'} {errors}")

    # Invalid strateji (eksik indikatör)
    invalid_strategy = {
        'name': 'Invalid',
        'indicators': [],
        'conditions': {
            'long': {'logic': 'AND', 'rules': [
                {'indicator': 'nonexistent', 'operator': '<', 'value': 30}
            ]}
        }
    }

    is_valid, errors = StrategyValidator.validate(invalid_strategy)
    print(f"  Invalid strategy test: {'[OK]' if not is_valid else '[FAIL]'} (should fail)")
    if not is_valid:
        print(f"    Errors: {errors}")
    
    return True


def test_executor():
    """StrategyExecutor testi"""
    print("\nTesting StrategyExecutor...")
    
    # Test DataFrame oluştur
    dates = pd.date_range('2024-01-01', periods=100, freq='1h')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': np.random.randn(100).cumsum() + 100,
        'high': np.random.randn(100).cumsum() + 101,
        'low': np.random.randn(100).cumsum() + 99,
        'close': np.random.randn(100).cumsum() + 100,
        'volume': np.random.randn(100) * 1000
    }, index=dates)
    
    # Executor oluştur
    executor = StrategyExecutor()
    executor.load_strategy('test_strategy.json')
    print(f"  [OK] Strateji yuklendi")

    # Sinyal uret
    signals = executor.generate_signals(df)
    print(f"  [OK] Sinyaller uretildi: {len(signals)} sinyal")

    # Son sinyali al
    last_signal = executor.get_last_signal(df)
    signal_map = {0: 'SAT', 1: 'HOLD', 2: 'AL'}
    print(f"  [OK] Son sinyal: {signal_map.get(last_signal, 'UNKNOWN')}")

    # Strateji bilgisi
    info = executor.get_strategy_info()
    print(f"  [OK] Strateji bilgisi: {info['name']}")
    
    return True


def test_full_workflow():
    """Tam workflow testi"""
    print("\n=== FULL WORKFLOW TEST ===")
    
    # 1. Builder ile strateji oluştur
    builder = StrategyBuilder()
    builder.strategy['name'] = "RSI MACD Combo"
    builder.strategy['description'] = "RSI + MACD stratejisi"
    
    # İndikatörler
    rsi_id = builder.add_indicator('RSI', {'length': 14})
    macd_id = builder.add_indicator('MACD', {'fast': 12, 'slow': 26, 'signal': 9})
    
    # LONG koşulu: RSI < 30 VE MACD > Signal
    builder.add_condition('long', rsi_id, '<', 30, logic='AND')
    builder.add_condition('long', macd_id, '>', 'signal')
    
    # SHORT koşulu: RSI > 70 VE MACD < Signal
    builder.add_condition('short', rsi_id, '>', 70, logic='AND')
    builder.add_condition('short', macd_id, '<', 'signal')
    
    # Kaydet
    builder.save_strategy('rsi_macd_combo.json')
    print("[OK] Strateji olusturuldu ve kaydedildi")

    # 2. Validate et
    is_valid, errors = StrategyValidator.validate_file('rsi_macd_combo.json')
    if is_valid:
        print("[OK] Strateji valid")
    else:
        print(f"[FAIL] Strateji invalid: {errors}")
        return False

    # 3. Executor ile calistir
    executor = StrategyExecutor()
    executor.load_strategy('rsi_macd_combo.json')

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

    signals = executor.generate_signals(df)
    print(f"[OK] Sinyaller uretildi: {len(signals)} sinyal")

    # Sinyal dagilimi
    unique, counts = np.unique(signals.values, return_counts=True)
    print(f"  HOLD: {counts[unique == 1][0] if len(unique[unique == 1]) > 0 else 0}")
    print(f"  AL:   {counts[unique == 2][0] if len(unique[unique == 2]) > 0 else 0}")
    print(f"  SAT:  {counts[unique == 0][0] if len(unique[unique == 0]) > 0 else 0}")

    print("\n=== TEST BASARILI ===")
    return True


if __name__ == '__main__':
    print("=" * 60)
    print("STRATEGY BUILDER TESTS")
    print("=" * 60)

    try:
        test_strategy_builder()
        test_validator()
        test_executor()
        test_full_workflow()

        print("\n" + "=" * 60)
        print("[OK] TUM TESTLER BASARILI!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[FAIL] TEST HATASI: {e}")
        import traceback
        traceback.print_exc()
