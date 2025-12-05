"""Script de prueba para la API de Air Quality."""
import requests

BASE_URL = "http://127.0.0.1:8001"

print("=" * 50)
print("AIR QUALITY API - TEST SUITE")
print("=" * 50)

# 1. Health Check
print("\n1. HEALTH CHECK")
print("-" * 30)
r = requests.get(f"{BASE_URL}/health", timeout=5)
print(f"Status: {r.status_code}")
health = r.json()
print(f"  status: {health['status']}")
print(f"  model_loaded: {health['model_loaded']}")
print(f"  model_name: {health['model_name']}")
print(f"  version: {health['version']}")

# 2. Single Prediction
print("\n2. SINGLE PREDICTION")
print("-" * 30)
data = {
    "pm2_5": 15.5,
    "pm10": 25.0,
    "carbon_monoxide": 200.0,
    "nitrogen_dioxide": 10.5,
    "sulphur_dioxide": 5.0,
    "ozone": 50.0,
    "us_aqi": 42,
    "european_aqi": 35
}
r = requests.post(f"{BASE_URL}/predict", json=data, timeout=10)
print(f"Status: {r.status_code}")
pred = r.json()
print(f"  prediction: {pred['prediction']}")
print(f"  confidence: {pred['confidence']}")

# 3. Batch Prediction
print("\n3. BATCH PREDICTION")
print("-" * 30)
batch_data = {
    "samples": [
        {"pm2_5": 5.0, "pm10": 10.0, "carbon_monoxide": 100.0, "nitrogen_dioxide": 5.0, "sulphur_dioxide": 2.0, "ozone": 30.0, "us_aqi": 20, "european_aqi": 15},
        {"pm2_5": 25.0, "pm10": 40.0, "carbon_monoxide": 300.0, "nitrogen_dioxide": 20.0, "sulphur_dioxide": 10.0, "ozone": 80.0, "us_aqi": 80, "european_aqi": 60},
        {"pm2_5": 60.0, "pm10": 90.0, "carbon_monoxide": 500.0, "nitrogen_dioxide": 40.0, "sulphur_dioxide": 25.0, "ozone": 120.0, "us_aqi": 150, "european_aqi": 120}
    ]
}
r = requests.post(f"{BASE_URL}/predict/batch", json=batch_data, timeout=15)
print(f"Status: {r.status_code}")
result = r.json()
print(f"Total predictions: {result['total']}")
for i, p in enumerate(result["predictions"]):
    print(f"  Sample {i+1}: {p['prediction']} (conf: {p['confidence']})")

# 4. Model Info
print("\n4. MODEL INFO")
print("-" * 30)
r = requests.get(f"{BASE_URL}/model/info", timeout=5)
print(f"Status: {r.status_code}")
info = r.json()
print(f"  model_name: {info['model_name']}")
print(f"  model_path: {info['model_path']}")
print(f"  features: {info['features']}")

# 5. Monitoring - Reference Stats
print("\n5. MONITORING - REFERENCE STATS")
print("-" * 30)
r = requests.get(f"{BASE_URL}/monitoring/reference-stats", timeout=10)
print(f"Status: {r.status_code}")
stats = r.json()
print(f"  num_rows: {stats['num_rows']}")
print(f"  features monitored: {list(stats['features'].keys())}")

# 6. Monitoring - Drift Detection
print("\n6. MONITORING - DRIFT DETECTION")
print("-" * 30)
r = requests.post(f"{BASE_URL}/monitoring/drift", json=batch_data, timeout=30)
print(f"Status: {r.status_code}")
drift = r.json()
print(f"  drift_detected: {drift['drift_detected']}")
print(f"  drift_score: {drift['drift_score']}")
print(f"  drifted_features: {drift['drifted_features']}")

print("\n" + "=" * 50)
print("ALL TESTS COMPLETED!")
print("=" * 50)

