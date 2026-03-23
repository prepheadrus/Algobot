"""
Debug: Test trades API endpoint
"""
import requests

print("\n" + "="*60)
print("🔬 API ENDPOINT TEST: GET /api/v1/trades/history")
print("="*60 + "\n")

try:
    response = requests.get("http://localhost:3000/api/v1/trades/history", timeout=5)
    
    print(f"📡 Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Response Status: {data.get('status')}")
        print(f"📊 Trade Count: {data.get('count')}")
        
        trades = data.get('trades', [])
        if len(trades) == 0:
            print("\n❌ API TRADE DÖNDÜRMEDİ!")
            print("\nOlası nedenler:")
            print("  1. API DB'den çekiyor ama boş dönüyor")
            print("  2. Response formatı yanlış")
            print("  3. Frontend yanlış endpoint'e istek atıyor")
        else:
            print(f"\n✅ API {len(trades)} trade döndürdü:\n")
            for i, t in enumerate(trades, 1):
                print(f"{i}. {t.get('symbol')} | {t.get('direction')} | "
                      f"PnL: ${t.get('pnl_usd', 0):.2f} | "
                      f"Reason: {t.get('reason')}")
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        print(f"Response: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ Bağlantı hatası: API çalışmıyor olabilir")
    print("   Bot'u başlatın: python main.py")
except requests.exceptions.Timeout:
    print("❌ Timeout: API yanıt vermedi")
except Exception as e:
    print(f"❌ Hata: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60 + "\n")
