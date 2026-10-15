"""Nebula AI Ops FastAPI app."""

from __future__ import annotations

import asyncio
import csv
import io
import json
from collections import deque
from typing import Literal

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .anomaly import AnomalyDetector
from .insights import ai_insights, ask_ai, summarize
from .metrics import MetricsCollector
from .settings import AskRequest, Settings

__version__ = "0.2.0"

app = FastAPI(title="Nebula AI Ops", version=__version__)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

collector = MetricsCollector()
settings = Settings()
detector = AnomalyDetector(thresholds=settings.thresholds())
history: deque[dict] = deque(maxlen=600)
alerts: deque[dict] = deque(maxlen=200)

EXPORT_FIELDS = ["ts", "cpu", "ram", "ram_used_gb", "ram_total_gb", "disk", "net_up", "net_down"]


def tick() -> dict:
    snap = collector.snapshot()
    new = detector.update({k: snap[k] for k in ("cpu", "ram", "disk")})
    alerts.extend(new)
    history.append({k: v for k, v in snap.items() if k != "processes"})
    return {**snap, "alerts": new}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


@app.get("/api/snapshot")
def snapshot() -> dict:
    return tick()


@app.get("/api/processes")
def processes() -> list[dict]:
    return collector.top_processes()


@app.get("/api/system")
def system() -> dict:
    return collector.system_info()


@app.get("/api/alerts")
def get_alerts() -> list[dict]:
    return list(alerts)


@app.delete("/api/alerts")
def clear_alerts() -> dict:
    alerts.clear()
    return {"cleared": True}


@app.get("/api/settings")
def get_settings() -> Settings:
    return settings


@app.put("/api/settings")
def put_settings(new: Settings) -> Settings:
    global settings
    settings = new
    detector.set_thresholds(new.thresholds())
    return settings


@app.post("/api/insights")
async def insights() -> dict:
    data = list(history) or [tick()]
    summary = summarize(data)
    return {**(await ai_insights(summary)), "summary": summary}


@app.post("/api/ask")
async def ask(req: AskRequest) -> dict:
    snap = tick()
    summary = summarize(list(history))
    return {**(await ask_ai(req.question, snap, summary)), "question": req.question}


@app.get("/api/export")
def export(fmt: Literal["csv", "json"] = Query("json", alias="format")) -> Response:
    rows = list(history)
    if fmt == "json":
        body = json.dumps(rows)
        media, ext = "application/json", "json"
    else:
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=EXPORT_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
        body, media, ext = buf.getvalue(), "text/csv", "csv"
    headers = {"Content-Disposition": f'attachment; filename="nebula-metrics.{ext}"'}
    return Response(body, media_type=media, headers=headers)


@app.websocket("/ws/metrics")
async def ws_metrics(ws: WebSocket) -> None:
    await ws.accept()
    try:
        await ws.send_json({"type": "system", **collector.system_info()})
        n = 0
        while True:
            msg = tick()
            if n % 3 == 0:
                msg["processes"] = collector.top_processes()
            else:
                msg.pop("processes", None)
            await ws.send_json(msg)
            n += 1
            await asyncio.sleep(1)
    except (WebSocketDisconnect, RuntimeError):
        pass
