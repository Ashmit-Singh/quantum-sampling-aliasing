from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_pipeline():
    response = client.post("/api/pipeline", json={
        "signal_type": "sine",
        "frequency": 5,
        "amplitude": 1.0,
        "noise_level": 0.0,
        "sampling_rate_ratio": 2.5,
        "bits": 8,
        "osr": 1
    })
    assert response.status_code == 200
    data = response.json()
    assert "signal" in data
    assert "sampling" in data
    assert "quantization" in data
    assert "oversampling" in data
    assert "fft" in data
    assert "qft" in data
