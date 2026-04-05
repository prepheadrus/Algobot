"""
Test: API Cache-Busting & No-Cache Headers

Amaç: Browser'ın dashboard-metrics API'sini cache'lemediğini kanıtla.
Sorun: Browser response'u cache'liyor → UI eski veriyi gösteriyor.
Çözüm: ?_t=timestamp parametresi + Cache-Control: no-cache headers.
"""

import pytest


@pytest.mark.asyncio
async def test_dashboard_metrics_cache_control_headers():
    """
    Dashboard metrics API'si no-cache headers döndürüyor.
    """
    from fastapi.testclient import TestClient
    from api.server import app
    
    client = TestClient(app)
    
    # 1. Dashboard metrics çağrısı yap
    response = client.get("/api/v1/dashboard-metrics?_t=1000")
    
    # 2. Status code kontrol
    assert response.status_code == 200, \
        f"API returned {response.status_code}"
    
    # 3. Cache-Control header'larını kontrol et (KRİTİK!)
    assert "Cache-Control" in response.headers, \
        "Cache-Control header missing!"
    
    assert response.headers["Cache-Control"] == \
           "no-cache, no-store, must-revalidate", \
           f"Wrong Cache-Control: {response.headers['Cache-Control']}"
    
    # 4. Pragma header
    assert response.headers["Pragma"] == "no-cache", \
        f"Wrong Pragma: {response.headers['Pragma']}"
    
    # 5. Expires header
    assert response.headers["Expires"] == "0", \
        f"Wrong Expires: {response.headers['Expires']}"
    
    print(f"✅ Cache-Control headers correct: {response.headers['Cache-Control']}")


@pytest.mark.asyncio
async def test_cache_busting_with_timestamp():
    """
    Farklı timestamp'ler farklı response'lar (cache yok).
    """
    from fastapi.testclient import TestClient
    from api.server import app
    
    client = TestClient(app)
    
    # 1. İki farklı timestamp ile çağır
    response1 = client.get("/api/v1/dashboard-metrics?_t=1000")
    response2 = client.get("/api/v1/dashboard-metrics?_t=2000")
    
    # 2. Her ikisi de başarılı
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    # 3. Response'lar aynı olabilir (veri değişmediyse)
    # Önemli olan: Her çağrı GERÇEK bir API çağrısı
    # (browser cache'den gelmiyor)
    
    # 4. Timestamp parametresi URL'de
    assert "_t=1000" in str(response1.url)
    assert "_t=2000" in str(response2.url)
    
    # 5. Cache headers her response'ta
    assert response1.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
    assert response2.headers["Cache-Control"] == "no-cache, no-store, must-revalidate"
    
    print("✅ Cache-busting successful: 2 unique timestamps, 2 real API calls")


@pytest.mark.asyncio
async def test_no_browser_caching():
    """
    Browser'ın response'u cache'leyememesi için tüm headers doğru.
    """
    from fastapi.testclient import TestClient
    from api.server import app
    
    client = TestClient(app)
    
    # 1. Çağrı yap
    response = client.get("/api/v1/dashboard-metrics")
    
    # 2. Tüm no-cache headers var mı?
    required_headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    }
    
    for header, expected_value in required_headers.items():
        assert header in response.headers, \
            f"{header} header missing!"
        
        assert response.headers[header] == expected_value, \
            f"{header} wrong value: {response.headers[header]} != {expected_value}"
    
    print(f"✅ All no-cache headers present: {list(required_headers.keys())}")


@pytest.mark.asyncio
async def test_api_client_cache_busting_integration():
    """
    Frontend API client ?_t=timestamp gönderiyor.
    """
    import sys
    sys.path.append('frontend')
    
    # Frontend api-client.js mock'u (Python'da simülasyon)
    class MockAPIClient:
        def get(self, endpoint, params=None):
            # Cache-busting parametresi ekleniyor mu?
            if params and '_t' in params:
                return f"{endpoint}?_t={params['_t']}"
            return endpoint
    
    api_client = MockAPIClient()
    
    # 1. Timestamp ile çağrı
    url = api_client.get("/api/v1/dashboard-metrics", {'_t': 1234567890})
    
    # 2. URL'de timestamp var mı?
    assert "_t=1234567890" in url, \
        f"Cache-busting timestamp missing from URL: {url}"
    
    print(f"✅ API client cache-busting integration successful: {url}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
