"""Nebula AI Ops FastAPI app."""

from __future__ import annotations

import asyncio
from collections import deque

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .anomaly import AnomalyDetector
from .insights import ai_insights, summarize
from .metrics import MetricsCollector

app = FastAPI(title="Nebula AI Ops", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

collector = MetricsCollector()
detector = AnomalyDetector()
history: deque[dict] = deque(maxlen=120)
alerts: deque[dict] = deque(maxlen=50)


def tick() -> dict:
    snap = collector.snapshot()
    new = detector.update({k: snap[k] for k in ("cpu", "ram", "disk")})
    alerts.extend(new)
    history.append(snap)
    return {**snap, "alerts": new}


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/snapshot")
def snapshot() -> dict:
    return tick()


@app.get("/api/alerts")
def get_alerts() -> list[dict]:
    return list(alerts)


@app.post("/api/insights")
async def insights() -> dict:
    data = list(history) or [tick()]
    summary = summarize(data)
    return {**(await ai_insights(summary)), "summary": summary}


@app.websocket("/ws/metrics")
async def ws_metrics(ws: WebSocket) -> None:
    await ws.accept()
    try:
        while True:
            await ws.send_json(tick())
            await asyncio.sleep(1)
    except (WebSocketDisconnect, RuntimeError):
        pass
