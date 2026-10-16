import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nebula_core.anomaly import AnomalyDetector
from nebula_core.insights import ask_ai, fallback_answer, fallback_insights, summarize


def _hist(cpu, ram=40, disk=50):
    return {"cpu": cpu, "ram": ram, "disk": disk, "net_up": 0, "net_down": 0,
            "processes": [{"name": "py", "pid": 1, "cpu": 5.0, "mem_mb": 10.0}]}


def test_summarize_and_health():
    s = summarize([_hist(90, 90, 95), _hist(90, 90, 95)])
    assert s["cpu"]["avg"] == 90 and s["samples"] == 2
    assert fallback_insights(s)["health_score"] == 30
    assert fallback_insights(summarize([_hist(10)]))["health_score"] == 100


def test_threshold_and_zscore_alerts():
    d = AnomalyDetector(thresholds={"cpu": 80})
    assert d.update({"cpu": 85})[0]["level"] == "critical"
    d = AnomalyDetector(min_samples=5)
    for v in (10, 11, 10, 11, 10, 11):
        assert d.update({"cpu": v}) == []
    assert d.update({"cpu": 70})[0]["level"] == "warning"


def test_fallback_answer_and_unreachable_ollama():
    snap = _hist(20)
    assert "py" in fallback_answer("which process is slow?", snap, {})
    res = ask_ai("disk?", {**snap}, {}, url="http://127.0.0.1:9")
    assert res["source"] == "rules" and "50" in res["answer"]
