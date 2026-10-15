"""AI insights via local Ollama with rule-based fallback."""

from __future__ import annotations

import json

import httpx

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5:3b"


def summarize(history: list[dict]) -> dict:
    if not history:
        return {"samples": 0}
    out: dict = {"samples": len(history)}
    for k in ("cpu", "ram", "disk", "net_up", "net_down"):
        vals = [h[k] for h in history]
        out[k] = {"avg": round(sum(vals) / len(vals), 1), "max": round(max(vals), 1)}
    out["top_processes"] = [p["name"] for p in history[-1].get("processes", [])]
    return out


def fallback_insights(summary: dict) -> dict:
    tips: list[str] = []
    score = 100
    cpu = summary.get("cpu", {}).get("avg", 0)
    ram = summary.get("ram", {}).get("avg", 0)
    disk = summary.get("disk", {}).get("avg", 0)
    if cpu > 80:
        score -= 25
        tips.append(f"CPU is saturated (avg {cpu}%). Investigate the top processes.")
    elif cpu > 50:
        score -= 10
        tips.append(f"CPU load is moderate (avg {cpu}%).")
    else:
        tips.append(f"CPU is healthy (avg {cpu}%).")
    if ram > 85:
        score -= 25
        tips.append(f"Memory pressure is high ({ram}%). Close unused apps.")
    else:
        tips.append(f"Memory usage is fine ({ram}%).")
    if disk > 90:
        score -= 20
        tips.append(f"System disk is {disk}% full. Free up space soon.")
    else:
        tips.append(f"Disk usage at {disk}% is within limits.")
    return {"source": "rules", "health_score": max(score, 0), "insights": tips[:3]}


async def ai_insights(summary: dict, timeout: float = 20.0) -> dict:
    prompt = (
        "You are an SRE assistant. Given this system metrics summary, respond ONLY with JSON "
        '{"health_score": int 0-100, "insights": [3 short strings]}.\n'
        f"Metrics: {json.dumps(summary)}"
    )
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                OLLAMA_URL,
                json={"model": MODEL, "prompt": prompt, "format": "json", "stream": False},
            )
            r.raise_for_status()
            data = json.loads(r.json()["response"])
            insights = [str(i) for i in data["insights"]][:3]
            score = int(max(0, min(100, int(data["health_score"]))))
            if not insights:
                raise ValueError("empty insights")
            return {"source": "ollama", "health_score": score, "insights": insights}
    except Exception:  # noqa: BLE001 - any failure falls back to rules
        return fallback_insights(summary)
