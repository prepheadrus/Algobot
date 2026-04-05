"""
Settings Save Test Script

Sistem ayarları sayfasındaki ayarların düzgün kaydedilip kaydedilmediğini test eder.

Kullanım: python test_settings_save.py
"""

import asyncio
import yaml
import os
from core.config import CONFIG


async def test_settings():
    """Ayarları test et"""
    
    print("\n" + "=" * 80)
    print("⚙️ SİSTEM AYARLARI TEST RAPORU")
    print("=" * 80)
    
    # 1. MEVCUT AYARLARI GÖSTER
    print("\n1️⃣ MEVCUT AYARLAR (config.yaml)")
    print("-" * 80)
    
    config_path = "config.yaml"
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Risk ayarları
        risk = config.get('risk_management', {})
        print("\n📊 RİSK AYARLARI:")
        print(f"   Max Risk per Trade: {risk.get('max_risk_per_trade_percent', 'YOK')}%")
        print(f"   Max Leverage: {risk.get('max_leverage', 'YOK')}x")
        print(f"   Max Open Positions: {risk.get('max_open_positions', 'YOK')}")
        print(f"   Max Consecutive Losses: {risk.get('max_consecutive_losses', 'YOK')}")
        
        kill_switch = risk.get('kill_switch', {})
        print(f"   Kill Switch Enabled: {kill_switch.get('enabled', 'YOK')}")
        
        # ML ayarları
        ml = config.get('ml', {})
        print("\n🧠 ML AYARLARI:")
        print(f"   ML Enabled: {ml.get('enabled', 'YOK')}")
        print(f"   Confidence Threshold: {ml.get('confidence_threshold', 'YOK')}")
        
        # HTF ayarları
        htf = config.get('htf', {})
        print("\n📈 HTF AYARLARI:")
        print(f"   HTF Enabled: {htf.get('enabled', 'YOK')}")
        print(f"   Trend Method: {htf.get('trend_method', 'YOK')}")
        
        # WFO ayarları
        wfo = config.get('wfo', {})
        print("\n🔬 WFO AYARLARI:")
        print(f"   WFO Enabled: {wfo.get('enabled', 'YOK')}")
        print(f"   Reoptimize Interval: {wfo.get('reoptimize_interval', 'YOK')} saat")
        
    else:
        print("❌ config.yaml dosyası bulunamadı!")
    
    # 2. MEMORY'DEKİ AYARLARI GÖSTER
    print("\n2️⃣ MEMORY'DEKİ AYARLAR (CONFIG dict)")
    print("-" * 80)
    
    risk_mem = CONFIG.get('risk_management', {})
    print("\n📊 RİSK AYARLARI:")
    print(f"   Max Risk per Trade: {risk_mem.get('max_risk_per_trade_percent', 'YOK')}%")
    print(f"   Max Leverage: {risk_mem.get('max_leverage', 'YOK')}x")
    print(f"   Max Open Positions: {risk_mem.get('max_open_positions', 'YOK')}")
    print(f"   Max Consecutive Losses: {risk_mem.get('max_consecutive_losses', 'YOK')}")
    
    kill_switch_mem = risk_mem.get('kill_switch', {})
    print(f"   Kill Switch Enabled: {kill_switch_mem.get('enabled', 'YOK')}")
    
    ml_mem = CONFIG.get('ml', {})
    print("\n🧠 ML AYARLARI:")
    print(f"   ML Enabled: {ml_mem.get('enabled', 'YOK')}")
    print(f"   Confidence Threshold: {ml_mem.get('confidence_threshold', 'YOK')}")
    
    htf_mem = CONFIG.get('htf', {})
    print("\n📈 HTF AYARLARI:")
    print(f"   HTF Enabled: {htf_mem.get('enabled', 'YOK')}")
    
    # 3. TEST SONUÇLARI
    print("\n3️⃣ TEST SONUÇLARI")
    print("-" * 80)
    
    issues = []
    
    # Kill switch kontrolü
    if 'kill_switch' not in risk_mem:
        issues.append("❌ Kill Switch field'ı risk_management'da eksik!")
    elif 'enabled' not in kill_switch_mem:
        issues.append("❌ Kill Switch 'enabled' field'ı eksik!")
    
    # ML threshold kontrolü
    ml_threshold = ml_mem.get('confidence_threshold', 0.65)
    if ml_threshold > 0.6:
        issues.append(f"⚠️ ML Confidence Threshold çok yüksek: {ml_threshold} (öneri: 0.5)")
    
    # HTF kontrolü
    if htf_mem.get('enabled', True):
        issues.append("⚠️ HTF aktif - Ters trend'te veto edebilir")
    
    if issues:
        print("\n⚠️ SORUNLAR:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n✅ TÜM AYARLAR DOĞRU!")
    
    # 4. ÖNERİLER
    print("\n4️⃣ ÖNERİLER")
    print("-" * 80)
    print("""
   Dashboard → Sistem Ayarları sayfasında:
   
   1. Risk Ayarları:
      - Max Risk per Trade: %1.0 (varsayılan)
      - Max Leverage: 10x (varsayılan)
      - Max Open Positions: 10 (varsayılan)
      - Kill Switch Enabled: ✗ (kapalı önerilir)
   
   2. ML Ayarları:
      - ML Enabled: ✓ (aktif)
      - Confidence Threshold: 0.5 (düşük threshold)
   
   3. HTF Ayarları:
      - HTF Enabled: ✗ (kapalı önerilir, daha fazla işlem)
   
   4. WFO Ayarları:
      - WFO Enabled: ✓ (aktif, otomatik optimizasyon)
   
   DEĞİŞİKLİKLERİ KAYDET butonuna bastıktan sonra:
   - Başarı mesajı görünür
   - Ayarlar config.yaml'a yazılır
   - Bot otomatik reload yapar (hot-reload)
    """)
    
    # 5. API ENDPOINT TEST
    print("\n5️⃣ API ENDPOINT TEST")
    print("-" * 80)
    
    try:
        from fastapi.testclient import TestClient
        from api.server import app
        
        client = TestClient(app)
        
        # Risk ayarlarını çek
        response = client.get("/api/v1/config/risk")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ GET /api/v1/config/risk: {response.status_code}")
            print(f"   Response: {data.get('config', {})}")
        else:
            print(f"❌ GET /api/v1/config/risk: {response.status_code}")
        
        # Advanced ayarları çek
        response = client.get("/api/v1/config/advanced")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ GET /api/v1/config/advanced: {response.status_code}")
            print(f"   ML: {data.get('config', {}).get('ml', {})}")
            print(f"   HTF: {data.get('config', {}).get('htf', {})}")
        else:
            print(f"❌ GET /api/v1/config/advanced: {response.status_code}")
        
    except ImportError:
        print("⚠️ Test client için 'pytest' ve 'httpx' gerekli")
        print("   pip install pytest httpx")
    except Exception as e:
        print(f"❌ API test hatası: {e}")
    
    print("\n" + "=" * 80)
    print("✅ TEST TAMAMLANDI")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(test_settings())
    except KeyboardInterrupt:
        print("\n\n🛑 Test durduruldu")
