"""
Bot Signal Debug Script

1 dakikalık botların neden işlem almadığını diagnose eder.
Kullanım: python debug_bot_signals.py
"""

import asyncio
from core.config import CONFIG
from data.database import db_manager
from data.storage.parquet_lake import get_parquet_lake


async def diagnose_bot_issues():
    """Bot işlem almama sorunlarını tespit et"""
    
    print("\n" + "=" * 80)
    print("🔍 BOT SİNYAL DEBUG RAPORU")
    print("=" * 80)
    
    # 1. CONFIG KONTROLÜ
    print("\n1️⃣ CONFIG YÖNETİMİ")
    print("-" * 80)
    
    # Trading symbols
    symbols = CONFIG.get('trading', {}).get('symbols', [])
    symbols_str = symbols if symbols else 'BOŞ (Parquetten yuklenecek)'
    print(f"   Config'deki semboller: {symbols_str}")
    
    # ML ayarları
    ml_enabled = CONFIG.get('ml', {}).get('enabled', True)
    ml_threshold = CONFIG.get('ml', {}).get('confidence_threshold', 0.65)
    print(f"   ML Enabled: {ml_enabled}")
    print(f"   ML Confidence Threshold: {ml_threshold}")
    
    if ml_threshold > 0.6:
        print(f"   ⚠️ UYARI: ML threshold çok yüksek ({ml_threshold}), işlem almayı zorlaştırıyor!")
        print("   → Öneri: 0.5 veya 0.6'ya düşür")
    
    # HTF ayarları
    htf_enabled = CONFIG.get('htf', {}).get('enabled', True)
    print(f"   HTF Enabled: {htf_enabled}")
    
    if htf_enabled:
        print("   ⚠️ HTF aktif - Major trend ters yöndeyse veto ediliyor")
    
    # Risk ayarları
    risk_config = CONFIG.get('risk_management', {})
    max_positions = risk_config.get('max_open_positions', 10)
    kill_switch_enabled = risk_config.get('kill_switch', {}).get('enabled', False)
    max_consecutive_losses = risk_config.get('max_consecutive_losses', 5)
    
    print(f"\n   Max Open Positions: {max_positions}")
    print(f"   Kill Switch Enabled: {kill_switch_enabled}")
    print(f"   Max Consecutive Losses: {max_consecutive_losses}")
    
    if kill_switch_enabled:
        print(f"   ⚠️ Kill Switch aktif - {max_consecutive_losses} kayıpta bot durur")
    
    # 2. VERİ KONTROLÜ
    print("\n2️⃣ VERİ MEVCUDİYETİ")
    print("-" * 80)
    
    # Parquet Lake kontrolü
    try:
        lake = get_parquet_lake('binance')
        stats = lake.get_stats()
        
        if stats['total_symbols'] > 0:
            print(f"   ✅ Parquet Lake: {stats['total_symbols']} sembol, {stats['total_files']} dosya")
            print(f"   Semboller: {list(stats['symbols'].keys())[:10]}{'...' if len(stats['symbols']) > 10 else ''}")
        else:
            print("   ❌ Parquet Lake BOŞ - Veri Laboratuvarı'ndan veri indirin!")
    except Exception as e:
        print(f"   ❌ Parquet Lake hatası: {e}")
    
    # SQLite kontrolü
    try:
        await db_manager.connect()
        db_symbols = await db_manager.get_symbols_with_data()
        
        if db_symbols:
            print(f"   ✅ SQLite DB: {len(db_symbols)} sembol")
        else:
            print("   ⚠️ SQLite DB boş")
    except Exception as e:
        print(f"   ❌ SQLite DB hatası: {e}")
    
    # 3. STRATEJİ KONTROLÜ
    print("\n3️⃣ STRATEJİ KONTROLÜ")
    print("-" * 80)
    
    try:
        from strategy.manager import StrategyManager
        
        # Manuel stratejileri yükle
        StrategyManager._import_manual_strategies()
        
        # Tüm stratejileri al
        all_strategies = StrategyManager.get_all_strategies()
        
        print(f"   ✅ Bulunan stratejiler: {len(all_strategies)}")
        for strat_id, strat_info in list(all_strategies.items())[:10]:
            name = strat_info.get('name', 'Unknown')
            timeframe = strat_info.get('timeframe', '1m')
            print(f"      - {strat_id}: {name} (TF: {timeframe})")
        
        if len(all_strategies) == 0:
            print("   ❌ HİÇ STRATEJİ BULUNAMADI! strategy/ klasörünü kontrol edin")
            
    except Exception as e:
        print(f"   ❌ Strateji yükleme hatası: {e}")
    
    # 4. ML MODEL KONTROLÜ
    print("\n4️⃣ ML MODEL KONTROLÜ")
    print("-" * 80)
    
    import os
    from ml.model_training import get_model_paths
    
    # BTC/USDT için model kontrolü
    test_symbol = "BTC/USDT"
    test_timeframe = "1m"
    
    model_paths = get_model_paths(test_symbol, test_timeframe)
    xgb_path = model_paths['xgboost_path']
    
    if os.path.exists(xgb_path):
        print(f"   ✅ ML Model mevcut: {xgb_path}")
        
        # Model metadata kontrolü
        metadata_path = model_paths['metadata_path']
        if os.path.exists(metadata_path):
            import json
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            train_size = metadata.get('train_size', 0)
            test_accuracy = metadata.get('test_accuracy', 0)
            
            print(f"      Train size: {train_size}")
            print(f"      Test accuracy: {test_accuracy:.2%}")
    else:
        print(f"   ❌ ML model yok: {xgb_path}")
        print("   → Dashboard → ML Training ile model eğitin")
        print("   → Veya config.yaml → ml.enabled = false (sadece teknik sinyaller)")
    
    # 5. ÖNERİLER
    print("\n5️⃣ ÖNERİLER VE ÇÖZÜMLER")
    print("-" * 80)
    
    print("""
   📊 SENARYO 1: Hiç işlem alınmıyor
   → config.yaml → ml.enabled = false (ML filtresini kapat)
   → config.yaml → ml.confidence_threshold = 0.5 (daha düşük threshold)
   → config.yaml → htf.enabled = false (HTF veto'yu kapat)
   
   📊 SENARYO 2: Bazı işlemler alınıyor ama az
   → config.yaml → risk_management.max_open_positions artır (örn: 20)
   → config.yaml → risk_management.kill_switch.enabled = false
   → Kill switch sonrası manuel reset gerekli
   
   📊 SENARYO 3: ML modeli yok
   → Dashboard → ML Training → Model Eğit
   → En az 2000 satır veri önerilir
   
   📊 SENARYO 4: Veri yok
   → Dashboard → Data Lab → Veri İndir
   → En az 10.000 mum (1 hafta 1m veri) önerilir
    """)
    
    # 6. HIZLI ÇÖZÜM KOMUTLARI
    print("\n6️⃣ HIZLI ÇÖZÜM KOMUTLARI")
    print("-" * 80)
    print("""
   # 1. ML'i kapat (sadece teknik sinyaller)
   config.yaml → ml.enabled = false
   
   # 2. HTF veto'yu kapat
   config.yaml → htf.enabled = false
   
   # 3. Kill switch'i kapat
   config.yaml → risk_management.kill_switch.enabled = false
   
   # 4. Confidence threshold düşür
   config.yaml → ml.confidence_threshold = 0.5
   
   # 5. Max pozisyon artır
   config.yaml → risk_management.max_open_positions = 20
   
   # Değişiklik sonrası bot'u yeniden başlat!
    """)
    
    print("\n" + "=" * 80)
    print("✅ DEBUG RAPORU TAMAMLANDI")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(diagnose_bot_issues())
    except KeyboardInterrupt:
        print("\n\n🛑 Debug durduruldu")
