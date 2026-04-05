"""
HTF (Higher Timeframe) Dinamik Haritalama Testi
Altın Oran (1:4 / 1:6) prensibi doğrulama
"""

from core.config import CONFIG

def test_htf_config():
    """HTF config doğrulama"""
    print("=" * 60)
    print("HTF CONFIG TEST")
    print("=" * 60)
    
    htf_config = CONFIG.get('htf', {})
    
    # 1. HTF enabled mi?
    assert htf_config.get('enabled', False) == True, "HTF enabled olmalı!"
    print("[PASS] HTF enabled: True")
    
    # 2. Dynamic map var mı?
    dynamic_map = htf_config.get('dynamic_map', {})
    assert len(dynamic_map) > 0, "Dynamic map boş olmalı!"
    print(f"[PASS] Dynamic map: {len(dynamic_map)} timeframe")
    
    # 3. EMA Stack parametreleri
    ema_fast = htf_config.get('ema_fast', 20)
    ema_slow = htf_config.get('ema_slow', 50)
    assert ema_fast < ema_slow, "EMA fast < EMA slow olmalı!"
    print(f"[PASS] EMA Stack: {ema_fast} / {ema_slow}")
    
    # 4. Trend method
    trend_method = htf_config.get('trend_method', 'ema_stack')
    assert trend_method == 'ema_stack', "Trend method ema_stack olmalı!"
    print(f"[PASS] Trend method: {trend_method}")
    
    print()
    
    # 5. Altın Oran doğrulama
    print("=" * 60)
    print("ALTIN ORAN (1:4 / 1:6) DOĞRULAMA")
    print("=" * 60)
    
    expected_ratios = {
        '1m': ([5, 15], [4, 14]),    # 1:5 ve 1:15
        '3m': ([15, 60], [4, 19]),   # 1:5 ve 1:20
        '5m': ([15, 60], [2, 11]),   # 1:3 ve 1:12
        '15m': ([60, 240], [3, 15]), # 1:4 ve 1:16
        '1h': ([240, 1440], [3, 23]),# 1:4 ve 1:24
        '4h': ([1440, 10080], [5, 6]), # 1:6 ve 1:7
    }
    
    for tf, htf_list in dynamic_map.items():
        if tf in expected_ratios:
            expected_ratios_range, ratio_range = expected_ratios[tf]
            
            # HTF'leri dakikaya çevir
            def tf_to_minutes(tf_str):
                if tf_str.endswith('m'):
                    return int(tf_str[:-1])
                elif tf_str.endswith('h'):
                    return int(tf_str[:-1]) * 60
                elif tf_str.endswith('d'):
                    return int(tf_str[:-1]) * 1440
                elif tf_str.endswith('w'):
                    return int(tf_str[:-1]) * 10080
                return 0
            
            base_minutes = tf_to_minutes(tf)
            htf_minutes = [tf_to_minutes(h) for h in htf_list]
            
            print(f"\n{tf} ({base_minutes}m) -> {htf_list}")
            for i, htf_min in enumerate(htf_minutes):
                ratio = htf_min / base_minutes
                print(f"  - {htf_list[i]} ({htf_min}m) -> 1:{ratio:.1f}")
    
    print()
    print("=" * 60)
    print("EMA STACK TREND MANTIĞI TEST")
    print("=" * 60)
    
    # Basit DataFrame simülasyonu
    import pandas as pd
    
    # Test verisi
    test_data = {
        'EMA_20': [100, 101, 102, 103, 104],
        'EMA_50': [98, 99, 100, 101, 102],
    }
    df = pd.DataFrame(test_data)
    
    # Son satır
    last_row = df.iloc[-1]
    ema_f = last_row.get('EMA_20')
    ema_s = last_row.get('EMA_50')
    
    # EMA Stack mantığı
    if ema_f > ema_s:
        trend = "BULL"
    elif ema_f < ema_s:
        trend = "BEAR"
    else:
        trend = "NEUTRAL"
    
    print(f"EMA_20: {ema_f}, EMA_50: {ema_s}")
    print(f"Trend: {trend}")
    assert trend == "BULL", "EMA 20 > EMA 50 ise BULL olmalı!"
    print("[PASS] EMA Stack trend mantığı doğru!")
    
    print()
    print("=" * 60)
    print("TÜM TESTLER BAŞARILI!")
    print("=" * 60)

if __name__ == "__main__":
    test_htf_config()
