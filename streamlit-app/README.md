# Nebula AI Ops - Streamlit edition

A pure-Python, single-file Streamlit version of the Nebula AI Ops dashboard. The logic in
`nebula_core/` is copied from `backend/app` (metrics, anomaly detection, insights), so this folder works on its own.

**Features:** neon glassmorphism UI, a live refresh every 2 s, KPI cards (CPU, RAM, disk, net up/down), a health score,
CPU/RAM and network charts, per-core CPU bars, top processes, system info, alert thresholds you can change in the sidebar with an
alert list, CSV export, and **Ask Nebula AI**. That uses Ollama when it can reach it and otherwise falls back to a
rule-based answer that is labeled as such.

## Run locally
```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r streamlit-app/requirements.txt
streamlit run streamlit-app/app.py
```
Optional: `$env:OLLAMA_URL="http://localhost:11434"` (default) with `ollama pull qwen2.5:3b`.

Tests: `pip install pytest; pytest streamlit-app/tests`

## Deploy to Streamlit Community Cloud
1. Go to https://share.streamlit.io and pick **New app**.
2. Repository `HarisMughal46/Nebula-AI-Ops`, branch `main`, main file path **`streamlit-app/app.py`**.
3. Deploy. Cloud has no Ollama, so the AI box uses the rule-based fallback. The metrics come from the cloud
   container that runs the app (the UI says so).
