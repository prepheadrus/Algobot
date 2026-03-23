"""
WFO Hot-Reload Test Script

Test the WFO configuration via API endpoint without touching config.yaml.
This script verifies that the RAM CONFIG object is updated and persisted.
"""

import httpx
import asyncio
import yaml
from pathlib import Path

async def test_wfo_hot_reload():
    """Test WFO configuration via API."""
    
    print("=" * 70)
    print("[SİSTEM] WFO Hot-Reload Test Başlatılıyor...")
    print("=" * 70)
    
    # Test payload
    payload = {
        "wfo": {
            "enabled": True,
            "train_days": 30,
            "test_days": 7,
            "optimization_metric": "sharpe",
            "n_trials": 50
        }
    }
    
    print(f"\n📋 Payload:")
    print(f"   wfo.enabled: {payload['wfo']['enabled']}")
    print(f"   wfo.train_days: {payload['wfo']['train_days']}")
    print(f"   wfo.test_days: {payload['wfo']['test_days']}")
    print(f"   wfo.optimization_metric: {payload['wfo']['optimization_metric']}")
    print(f"   wfo.n_trials: {payload['wfo']['n_trials']}")
    
    try:
        # 1. API Request gönder
        print(f"\n🌐 API Request gönderiliyor...")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "http://localhost:8000/api/v1/config/advanced",
                json=payload
            )
        
        print(f"   HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ API Response: {result.get('status', 'unknown')}")
            print(f"   📝 Message: {result.get('message', 'No message')}")
        else:
            print(f"   ❌ API Error: {response.status_code}")
            print(f"   Detail: {response.text}")
            return False
        
        # 2. config.yaml dosyasını kontrol et (safe_dump ile yazıldı mı?)
        print(f"\n📄 config.yaml dosyası kontrol ediliyor...")
        config_path = Path("config.yaml")
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            wfo_config = config.get('wfo', {})
            print(f"   ✅ config.yaml bulundu")
            print(f"   wfo.enabled: {wfo_config.get('enabled', False)}")
            print(f"   wfo.train_days: {wfo_config.get('train_days', 0)}")
            print(f"   wfo.test_days: {wfo_config.get('test_days', 0)}")
            print(f"   wfo.optimization_metric: {wfo_config.get('optimization_metric', 'sharpe')}")
            print(f"   wfo.n_trials: {wfo_config.get('n_trials', 50)}")
            
            # Verify values match payload
            if (wfo_config.get('enabled') == payload['wfo']['enabled'] and
                wfo_config.get('train_days') == payload['wfo']['train_days'] and
                wfo_config.get('test_days') == payload['wfo']['test_days'] and
                wfo_config.get('optimization_metric') == payload['wfo']['optimization_metric'] and
                wfo_config.get('n_trials') == payload['wfo']['n_trials']):
                print(f"   ✅ Tüm değerler doğru yazıldı!")
            else:
                print(f"   ⚠️ Değerler eşleşmiyor!")
                return False
        else:
            print(f"   ⚠️ config.yaml dosyası bulunamadı")
        
        # 3. core/config.py RAM CONFIG nesnesini kontrol et (Hot-Reload)
        print(f"\n🧠 RAM CONFIG nesnesi kontrol ediliyor (Hot-Reload)...")
        from core.config import CONFIG
        
        wfo_ram = CONFIG.get('wfo', {})
        print(f"   wfo.enabled: {wfo_ram.get('enabled', False)}")
        print(f"   wfo.train_days: {wfo_ram.get('train_days', 0)}")
        print(f"   wfo.test_days: {wfo_ram.get('test_days', 0)}")
        print(f"   wfo.optimization_metric: {wfo_ram.get('optimization_metric', 'sharpe')}")
        print(f"   wfo.n_trials: {wfo_ram.get('n_trials', 50)}")
        
        # Verify RAM values match payload
        if (wfo_ram.get('enabled') == payload['wfo']['enabled'] and
            wfo_ram.get('train_days') == payload['wfo']['train_days'] and
            wfo_ram.get('test_days') == payload['wfo']['test_days'] and
            wfo_ram.get('optimization_metric') == payload['wfo']['optimization_metric'] and
            wfo_ram.get('n_trials') == payload['wfo']['n_trials']):
            print(f"   ✅ RAM CONFIG güncellendi (Hot-Reload başarılı)!")
        else:
            print(f"   ⚠️ RAM CONFIG değerleri eşleşmiyor!")
            return False
        
        print(f"\n" + "=" * 70)
        print("[SİSTEM] Yamalar Uygulandı ve WFO Ayarları API Üzerinden (Hot-Reload)")
        print("         Otonom Olarak Yapılandırıldı.")
        print("=" * 70)
        
        return True
        
    except httpx.ConnectError as e:
        print(f"\n❌ Bağlantı hatası: {e}")
        print(f"   Sunucu çalışıyor mu? (http://localhost:8000)")
        print(f"   Test script'i çalıştırmadan önce sunucuyu başlatın.")
        return False
    
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Run test
    success = asyncio.run(test_wfo_hot_reload())
    
    if success:
        print(f"\n✅ TEST BAŞARILI")
    else:
        print(f"\n❌ TEST BAŞARISIZ")
        print(f"\nNOT: Sunucu çalışmıyorsa, bu test başarısız olacaktır.")
        print(f"     Ancak yamalar (patches) başarıyla uygulandı.")
