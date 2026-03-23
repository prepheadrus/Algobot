import requests

def test_json():
    url = "http://127.0.0.1:8000/api/v1/ml/visual-analysis?symbol=BTC/USDT&limit=200"
    try:
        r = requests.get(url)
        print("Status Code:", r.status_code)
        data = r.json()
        print("Predictions length:", len(data.get("predictions", [])))
        print("Importance keys:", data.get("feature_importance", {}).keys())
        if data.get("predictions"):
             p = data["predictions"][0]
             print("First prediction sample:", p)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_json()
