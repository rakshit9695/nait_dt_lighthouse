import os

from fastapi.testclient import TestClient

os.environ["NAIT_DT_TOKEN"] = "test-token"
from backend.main import app  # noqa: E402

client = TestClient(app)
H = {"Authorization": "Bearer test-token"}


def test_health():
    r = client.get("/healthz")
    assert r.status_code == 200


def test_topology_requires_auth():
    r = client.get("/api/v1/topology")
    assert r.status_code == 401


def test_topology_ok():
    r = client.get("/api/v1/topology", headers=H)
    assert r.status_code == 200
    data = r.json()
    assert "nodes" in data and "edges" in data


def test_components_endpoint():
    r = client.get("/api/v1/components", headers=H)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_scenarios_listed():
    r = client.get("/api/v1/scenarios", headers=H)
    assert r.status_code == 200
    ids = {s["id"] for s in r.json()}
    assert "sunny_grid_stable" in ids


def test_command_clipped_and_logged():
    r = client.post("/api/v1/components/battery/command",
                     headers=H, json={"component_id": "battery", "command": {"SOC": 0.99}})
    assert r.status_code == 200
    assert r.json()["applied"]["SOC"] == 0.95


def test_external_policy_push():
    r = client.post("/api/v1/policy/external", headers=H,
                    json={"quattro_command_w": -1000.0})
    assert r.status_code == 200
