import asyncio

import httpx
from fastapi.testclient import TestClient

from app import insights as ins
from app.anomaly import AnomalyDetector
from app.main import app

client = TestClient(app)


def test_threshold_alert():
    d = AnomalyDetector()
    a = d.update({"cpu": 95.0})
    assert a and a[0]["level"] == "critical"


def test_zscore_spike():
    d = AnomalyDetector(min_samples=5)
    for v in [10, 11, 10, 12, 11, 10, 11]:
        assert d.update({"cpu": float(v)}) == []
    a = d.update({"cpu": 60.0})
    assert a and a[0]["level"] == "warning"


def test_flat_series_no_alert():
    d = AnomalyDetector(min_samples=3)
    for _ in range(10):
        assert d.update({"ram": 40.0}) == []


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_snapshot_shape():
    s = client.get("/api/snapshot").json()
    for k in ("cpu", "cores", "ram", "disk", "net_up", "net_down", "processes"):
        assert k in s
    assert len(s["processes"]) <= 5


def test_fallback_insights_rules():
    r = ins.fallback_insights({"cpu": {"avg": 95}, "ram": {"avg": 90}, "disk": {"avg": 97}})
    assert r["source"] == "rules" and len(r["insights"]) == 3 and r["health_score"] == 30


def test_ollama_down_falls_back(monkeypatch):
    class Boom(httpx.AsyncClient):
        async def post(self, *a, **k):
            raise httpx.ConnectError("down")

    monkeypatch.setattr(ins.httpx, "AsyncClient", Boom)
    r = asyncio.run(ins.ai_insights({"cpu": {"avg": 10}}))
    assert r["source"] == "rules"


def test_ollama_success(monkeypatch):
    class Fake(httpx.AsyncClient):
        async def post(self, *a, **k):
            body = {"response": '{"health_score": 88, "insights": ["a", "b", "c"]}'}
            return httpx.Response(200, json=body, request=httpx.Request("POST", "http://x"))

    monkeypatch.setattr(ins.httpx, "AsyncClient", Fake)
    r = asyncio.run(ins.ai_insights({}))
    assert r == {"source": "ollama", "health_score": 88, "insights": ["a", "b", "c"]}


def test_summarize():
    h = [{"cpu": 10, "ram": 20, "disk": 30, "net_up": 1, "net_down": 2, "processes": []}] * 3
    s = ins.summarize(h)
    assert s["samples"] == 3 and s["cpu"]["avg"] == 10
