"""API-level tests for the /api/regenerate path (no Gemini API call needed —
that's exercised separately/manually since it uses real API quota)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_regenerate_all_defaults_for_every_category():
    for part_type in ["l_bracket", "flat_plate", "standoff", "flange", "enclosure", "shaft"]:
        r = client.post("/api/regenerate", json={"part_type": part_type, "parameters": {}})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["step_url"].endswith(".step")
        assert body["stl_url"].endswith(".stl")
        assert body["defaulted_fields"]


def test_regenerate_validation_error_returns_422():
    r = client.post(
        "/api/regenerate",
        json={"part_type": "l_bracket", "parameters": {"thickness": 2, "hole_diameter": 50}},
    )
    assert r.status_code == 422
    assert "errors" in r.json()["detail"]


def test_download_step_rejects_bad_id():
    r = client.get("/api/download/step/../../etc/passwd")
    assert r.status_code == 404


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}
