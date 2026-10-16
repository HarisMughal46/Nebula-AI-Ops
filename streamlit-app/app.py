"""Nebula AI Ops - pure-Python Streamlit edition."""

from __future__ import annotations

import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from nebula_core.anomaly import THRESHOLDS, AnomalyDetector  # noqa: E402
from nebula_core.insights import OLLAMA_URL, MODEL, ask_ai, fallback_insights, summarize  # noqa: E402
from nebula_core.metrics import MetricsCollector  # noqa: E402

MAX_HISTORY = 150
REFRESH = 2.0

st.set_page_config(page_title="Nebula AI Ops", page_icon="🌌", layout="wide")

CSS = """
<style>
.stApp {background: radial-gradient(circle at 15% 10%, #1b1450 0%, #070b1a 45%, #03050d 100%);}
.block-container {padding-top: 1.5rem;}
h1, h2, h3 {color:#e6f1ff; letter-spacing:.5px;}
.neb-title {font-size:2.3rem; font-weight:800;
  background: linear-gradient(90deg,#00e5ff,#a855f7,#ff2bd6); -webkit-background-clip:text;
  -webkit-text-fill-color:transparent; text-shadow:0 0 30px rgba(0,229,255,.25);}
.glass {background:rgba(255,255,255,.05); border:1px solid rgba(0,229,255,.25);
  border-radius:18px; padding:16px 18px; backdrop-filter:blur(14px);
  -webkit-backdrop-filter:blur(14px); box-shadow:0 0 22px rgba(0,229,255,.12), inset 0 0 12px rgba(168,85,247,.08);}
.kpi-label {font-size:.8rem; text-transform:uppercase; color:#8fa3c7; letter-spacing:1.5px;}
.kpi-value {font-size:1.9rem; font-weight:700; color:#00e5ff; text-shadow:0 0 12px rgba(0,229,255,.6);}
.kpi-sub {font-size:.75rem; color:#a855f7;}
.note {font-size:.8rem; color:#8fa3c7;}
.alert-crit {border-left:4px solid #ff2bd6; padding:6px 10px; margin:4px 0; background:rgba(255,43,214,.08); border-radius:8px;}
.alert-warn {border-left:4px solid #facc15; padding:6px 10px; margin:4px 0; background:rgba(250,204,21,.08); border-radius:8px;}
section[data-testid="stSidebar"] {background:rgba(10,14,35,.85); border-right:1px solid rgba(0,229,255,.2);}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def fmt_rate(b: float) -> str:
    for unit in ("B/s", "KB/s", "MB/s", "GB/s"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB/s"


def fmt_uptime(s: int) -> str:
    d, s = divmod(int(s), 86400)
    h, s = divmod(s, 3600)
    m, _ = divmod(s, 60)
    return f"{d}d {h}h {m}m"


def kpi(label: str, value: str, sub: str = "") -> str:
    return (f'<div class="glass"><div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>')


@st.cache_resource
def get_collector() -> MetricsCollector:
    return MetricsCollector()


ss = st.session_state
ss.setdefault("history", [])
ss.setdefault("alerts", [])
ss.setdefault("detector", AnomalyDetector())

# ---------------- Sidebar ----------------
with st.sidebar:
    st.markdown("### ⚙️ Alert thresholds")
    th = {
        "cpu": st.slider("CPU %", 10, 100, int(THRESHOLDS["cpu"])),
        "ram": st.slider("RAM %", 10, 100, int(THRESHOLDS["ram"])),
        "disk": st.slider("Disk %", 10, 100, int(THRESHOLDS["disk"])),
    }
    ss.detector.set_thresholds({k: float(v) for k, v in th.items()})
    live = st.toggle("Live refresh (2s)", value=True)
    if st.button("Clear alerts"):
        ss.alerts = []
    st.markdown(f'<div class="note">AI: Ollama <code>{MODEL}</code> at <code>{OLLAMA_URL}</code>; '
                "rule-based fallback when unreachable.</div>", unsafe_allow_html=True)

st.markdown('<div class="neb-title">🌌 Nebula AI Ops</div>', unsafe_allow_html=True)
st.markdown('<div class="note">Showing metrics of the host running this app</div>',
            unsafe_allow_html=True)


def chart(df: pd.DataFrame, cols: list[tuple[str, str, str]], title: str, yfmt: str = "") -> go.Figure:
    fig = go.Figure()
    for col, name, color in cols:
        fig.add_trace(go.Scatter(x=df["time"], y=df[col], name=name, mode="lines",
                                 line=dict(color=color, width=2.5, shape="spline"), fill="tozeroy",
                                 fillcolor=color.replace("rgb", "rgba").replace(")", ",0.08)")))
    fig.update_layout(title=title, height=290, margin=dict(l=10, r=10, t=40, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.02)",
                      font=dict(color="#e6f1ff"), legend=dict(orientation="h", y=1.15),
                      yaxis=dict(gridcolor="rgba(0,229,255,0.1)", ticksuffix=yfmt),
                      xaxis=dict(gridcolor="rgba(0,229,255,0.05)"))
    return fig


@st.fragment(run_every=REFRESH if live else None)
def dashboard() -> None:
    snap = get_collector().snapshot()
    ss.history.append(snap)
    ss.history = ss.history[-MAX_HISTORY:]
    new = ss.detector.update({k: snap[k] for k in ("cpu", "ram", "disk")})
    ss.alerts = (new + ss.alerts)[:50]
    summary = summarize(ss.history)
    health = fallback_insights(summary)
    ss.last_snap, ss.last_summary = snap, summary

    c = st.columns(6)
    cards = [
        ("CPU", f"{snap['cpu']}%", f"{len(snap['cores'])} logical cores"),
        ("RAM", f"{snap['ram']}%", f"{snap['ram_used_gb']} / {snap['ram_total_gb']} GB"),
        ("Disk", f"{snap['disk']}%", "system volume"),
        ("Net ↑", fmt_rate(snap["net_up"]), "upload"),
        ("Net ↓", fmt_rate(snap["net_down"]), "download"),
        ("Health", f"{health['health_score']}/100", "rule-based score"),
    ]
    for col, (label, val, sub) in zip(c, cards):
        col.markdown(kpi(label, val, sub), unsafe_allow_html=True)

    df = pd.DataFrame(ss.history)
    df["time"] = pd.to_datetime(df["ts"], unit="s")
    df["up_kb"], df["down_kb"] = df["net_up"] / 1024, df["net_down"] / 1024
    l, r = st.columns(2)
    l.plotly_chart(chart(df, [("cpu", "CPU", "rgb(0,229,255)"), ("ram", "RAM", "rgb(168,85,247)")],
                         "CPU / RAM", "%"))
    r.plotly_chart(chart(df, [("up_kb", "Up", "rgb(255,43,214)"), ("down_kb", "Down", "rgb(34,197,94)")],
                         "Network (KB/s)"))

    l, r = st.columns([1, 1])
    with l:
        cores = snap["cores"]
        fig = go.Figure(go.Bar(x=[f"C{i}" for i in range(len(cores))], y=cores,
                               marker=dict(color=cores, colorscale=[[0, "#00e5ff"], [0.6, "#a855f7"], [1, "#ff2bd6"]],
                                           cmin=0, cmax=100)))
        fig.update_layout(title="Per-core CPU", height=290, margin=dict(l=10, r=10, t=40, b=10),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(255,255,255,0.02)",
                          font=dict(color="#e6f1ff"), yaxis=dict(range=[0, 100], ticksuffix="%",
                                                                 gridcolor="rgba(0,229,255,0.1)"))
        st.plotly_chart(fig)
    with r:
        st.markdown("#### ⚡ Top processes")
        st.dataframe(pd.DataFrame(snap["processes"]).rename(
            columns={"pid": "PID", "name": "Name", "cpu": "CPU %", "mem_mb": "Mem MB"}),
            hide_index=True, width="stretch", height=250)

    l, r = st.columns(2)
    with l:
        st.markdown("#### 🚨 Alerts")
        if not ss.alerts:
            st.markdown('<div class="note">No alerts. All systems nominal.</div>', unsafe_allow_html=True)
        for a in ss.alerts[:8]:
            cls = "alert-crit" if a["level"] == "critical" else "alert-warn"
            t = datetime.fromtimestamp(a["ts"]).strftime("%H:%M:%S")
            st.markdown(f'<div class="{cls}">{t} · <b>{a["level"].upper()}</b> · {a["message"]} '
                        f'({a["value"]}%)</div>', unsafe_allow_html=True)
    with r:
        st.markdown("#### 💡 Insights")
        for tip in health["insights"]:
            st.markdown(f"- {tip}")
        export = df[["time", "cpu", "ram", "disk", "net_up", "net_down"]].to_csv(index=False)
        st.download_button("⬇️ Export history CSV", export, "nebula-metrics.csv", "text/csv")


dashboard()

with st.expander("🖥️ System info", expanded=False):
    info = MetricsCollector.system_info()
    cols = st.columns(5)
    cols[0].markdown(kpi("Hostname", info["hostname"][:18]), unsafe_allow_html=True)
    cols[1].markdown(kpi("OS", info["os"][:18]), unsafe_allow_html=True)
    cols[2].markdown(kpi("Cores", f"{info['physical_cores']}/{info['logical_cores']}", "physical / logical"),
                     unsafe_allow_html=True)
    cols[3].markdown(kpi("RAM", f"{info['ram_total_gb']} GB"), unsafe_allow_html=True)
    cols[4].markdown(kpi("Uptime", fmt_uptime(info["uptime_s"])), unsafe_allow_html=True)

st.markdown("### 🤖 Ask Nebula AI")
with st.form("ask"):
    q = st.text_input("Question", placeholder="Which process is using the most CPU?")
    go_btn = st.form_submit_button("Ask")
if go_btn and q.strip():
    with st.spinner("Nebula is thinking..."):
        res = ask_ai(q, ss.get("last_snap", {}), ss.get("last_summary", {}))
    label = f"🧠 Ollama ({MODEL})" if res["source"] == "ollama" else "📏 Rule-based fallback (Ollama unreachable)"
    st.markdown(f'<div class="glass"><div class="kpi-label">{label}</div>{res["answer"]}</div>',
                unsafe_allow_html=True)
