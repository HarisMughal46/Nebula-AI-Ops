import asyncio
import csv
import io

from fastapi.testclient import TestClient

from app import insights as ins
from app import main
from app.anomaly import AnomalyDetector

client = TestClient(main.app)


def test_health_version():
    assert client.get("/health").json()["version"] == "0.2.0"


def test_processes_endpoint():
    procs = client.get("/api/processes").json()
    assert isinstance(procs, list) and len(procs) <= 8
    for p in procs:
        assert set(p) == {"pid", "name", "cpu", "mem_mb"}


def test_system_info():
    s = client.get("/api/system").json()
    for k in ("hostname", "os", "cpu_model", "logical_cores", "ram_total_gb", "uptime_s"):
        assert k in s
    assert s["uptime_s"] >= 0 and s["boot_time"] > 0


def test_settings_roundtrip():
    default = client.get("/api/settings").json()
    assert default["cpu_threshold"] == 90.0
    new = {"cpu_threshold": 50, "ram_threshold": 60, "disk_threshold": 70}
    r = client.put("/api/settings", json=new)
    assert r.status_code == 200 and r.json()["cpu_threshold"] == 50
    assert main.detector.thresholds["disk"] == 70
    client.put("/api/settings", json=default)


def test_settings_validation():
    r = client.put("/api/settings", json={"cpu_threshold": 150, "ram_threshold": 90})
    assert r.status_code == 422


def test_detector_uses_custom_threshold():
    d = AnomalyDetector(thresholds={"cpu": 40.0})
    assert d.update({"cpu": 45.0})[0]["level"] == "critical"


def test_clear_alerts():
    main.alerts.append({"ts": 0, "metric": "cpu", "value": 99, "level": "critical", "message": "x"})
    assert client.delete("/api/alerts").json() == {"cleared": True}
    assert client.get("/api/alerts").json() == []


def test_ask_fallback(monkeypatch):
    async def down(*a, **k):
        raise ins.httpx.ConnectError("down")

    monkeypatch.setattr(ins.httpx.AsyncClient, "post", down)
    r = client.post("/api/ask", json={"question": "how is memory?"})
    body = r.json()
    assert r.status_code == 200 and body["source"] == "rules" and "Memory" in body["answer"]


def test_ask_validation():
    assert client.post("/api/ask", json={"question": ""}).status_code == 422


def test_ask_ollama_success(monkeypatch):
    async def ok(self, *a, **k):
        return ins.httpx.Response(
            200, json={"response": "All good."}, request=ins.httpx.Request("POST", "http://x")
        )

    monkeypatch.setattr(ins.httpx.AsyncClient, "post", ok)
    r = asyncio.run(ins.ask_ai("status?", {"cpu": 1}, {}))
    assert r == {"source": "ollama", "answer": "All good."}


def test_ollama_timeout_is_45():
    assert ins.OLLAMA_TIMEOUT == 45.0


def test_export_json():
    client.get("/api/snapshot")
    r = client.get("/api/export?format=json")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/json")
    assert "attachment" in r.headers["content-disposition"]
    assert isinstance(r.json(), list) and "cpu" in r.json()[-1]


def test_export_csv():
    client.get("/api/snapshot")
    r = client.get("/api/export?format=csv")
    assert r.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert rows and "cpu" in rows[0]


def test_export_bad_format():
    assert client.get("/api/export?format=xml").status_code == 422


def test_history_maxlen():
    assert main.history.maxlen == 600


def test_websocket_stream():
    with client.websocket_connect("/ws/metrics") as ws:
        first = ws.receive_json()
        assert first["type"] == "system" and "hostname" in first
        tick = ws.receive_json()
        assert "cpu" in tick and "processes" in tick
