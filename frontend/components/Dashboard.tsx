"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { API, fmtRate, type Alert, type Insights, type Metrics } from "@/lib/types";
import { Kpi } from "./Kpi";
import { HealthRing } from "./HealthRing";

type Point = { t: string; cpu: number; ram: number; up: number; down: number };

export default function Dashboard() {
  const [m, setM] = useState<Metrics | null>(null);
  const [series, setSeries] = useState<Point[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [live, setLive] = useState(false);
  const [ins, setIns] = useState<Insights | null>(null);
  const [busy, setBusy] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let stop = false; let timer: ReturnType<typeof setTimeout>;
    const connect = () => {
      const ws = new WebSocket(API.replace(/^http/, "ws") + "/ws/metrics");
      wsRef.current = ws;
      ws.onopen = () => setLive(true);
      ws.onclose = () => { setLive(false); if (!stop) timer = setTimeout(connect, 2000); };
      ws.onmessage = (e) => {
        const d: Metrics = JSON.parse(e.data);
        setM(d);
        setSeries((s) => [...s.slice(-59), { t: new Date(d.ts * 1000).toLocaleTimeString(), cpu: d.cpu, ram: d.ram, up: d.net_up / 1024, down: d.net_down / 1024 }]);
        if (d.alerts.length) setAlerts((a) => [...d.alerts, ...a].slice(0, 20));
      };
    };
    connect();
    return () => { stop = true; clearTimeout(timer); wsRef.current?.close(); };
  }, []);

  const analyze = useCallback(async () => {
    setBusy(true);
    try { const r = await fetch(`${API}/api/insights`, { method: "POST" }); setIns(await r.json()); }
    catch { setIns({ source: "offline", health_score: 0, insights: ["Backend unreachable."] }); }
    finally { setBusy(false); }
  }, []);

  const tip = { contentStyle: { background: "#0f172a", border: "1px solid #334155", borderRadius: 8 } };

  return (
    <main className="relative min-h-screen">
      <div className="grid-bg absolute inset-0 pointer-events-none" />
      <div className="relative mx-auto max-w-7xl p-4 md:p-8 space-y-6">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight"><span className="neon-text">NEBULA</span> <span className="text-slate-300 font-light">AI Ops</span></h1>
            <p className="text-sm text-slate-400">Realtime telemetry · anomaly detection · local LLM insights</p>
          </div>
          <div className="glass flex items-center gap-3 px-4 py-2">
            <span className="relative flex h-3 w-3">
              {live && <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />}
              <span className={`relative inline-flex h-3 w-3 rounded-full ${live ? "bg-emerald-400" : "bg-rose-500"}`} />
            </span>
            <span className="text-sm text-slate-300">{live ? "LIVE · streaming 1 Hz" : "Reconnecting…"}</span>
          </div>
        </header>

        <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Kpi label="CPU" value={`${m?.cpu.toFixed(1) ?? "--"}%`} sub={`${m?.cores.length ?? 0} logical cores`} pct={m?.cpu} accent="#22d3ee" />
          <Kpi label="Memory" value={`${m?.ram.toFixed(1) ?? "--"}%`} sub={m ? `${m.ram_used_gb} / ${m.ram_total_gb} GB` : ""} pct={m?.ram} accent="#a78bfa" />
          <Kpi label="Disk" value={`${m?.disk.toFixed(1) ?? "--"}%`} sub="system volume" pct={m?.disk} accent="#f0abfc" />
          <Kpi label="Network" value={m ? fmtRate(m.net_down) : "--"} sub={m ? `↑ ${fmtRate(m.net_up)}` : ""} accent="#34d399" />
        </section>

        <section className="grid lg:grid-cols-3 gap-4">
          <div className="glass p-5 lg:col-span-2">
            <h2 className="mb-3 text-sm uppercase tracking-widest text-slate-400">CPU &amp; Memory · 60s</h2>
            <div className="h-64">
              <ResponsiveContainer>
                <AreaChart data={series}>
                  <defs>
                    <linearGradient id="gc" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#22d3ee" stopOpacity={0.6} /><stop offset="100%" stopColor="#22d3ee" stopOpacity={0} /></linearGradient>
                    <linearGradient id="gr" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#a78bfa" stopOpacity={0.5} /><stop offset="100%" stopColor="#a78bfa" stopOpacity={0} /></linearGradient>
                  </defs>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" />
                  <XAxis dataKey="t" hide /><YAxis domain={[0, 100]} stroke="#475569" fontSize={11} />
                  <Tooltip {...tip} />
                  <Area type="monotone" dataKey="cpu" stroke="#22d3ee" fill="url(#gc)" strokeWidth={2} isAnimationActive={false} />
                  <Area type="monotone" dataKey="ram" stroke="#a78bfa" fill="url(#gr)" strokeWidth={2} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="glass p-5">
            <h2 className="mb-3 text-sm uppercase tracking-widest text-slate-400">Per-core load</h2>
            <div className="h-64">
              <ResponsiveContainer>
                <BarChart data={(m?.cores ?? []).map((v, i) => ({ core: `C${i}`, v }))}>
                  <XAxis dataKey="core" stroke="#475569" fontSize={10} /><YAxis domain={[0, 100]} stroke="#475569" fontSize={11} />
                  <Tooltip {...tip} cursor={{ fill: "rgba(34,211,238,.06)" }} />
                  <Bar dataKey="v" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                    {(m?.cores ?? []).map((v, i) => <Cell key={i} fill={v > 80 ? "#f43f5e" : v > 50 ? "#a78bfa" : "#22d3ee"} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>

        <section className="grid lg:grid-cols-3 gap-4">
          <div className="glass p-5">
            <h2 className="mb-3 text-sm uppercase tracking-widest text-slate-400">Network KB/s</h2>
            <div className="h-48">
              <ResponsiveContainer>
                <AreaChart data={series}>
                  <CartesianGrid stroke="#1e293b" strokeDasharray="3 3" /><XAxis dataKey="t" hide /><YAxis stroke="#475569" fontSize={11} />
                  <Tooltip {...tip} />
                  <Area type="monotone" dataKey="down" stroke="#34d399" fill="#34d39922" isAnimationActive={false} />
                  <Area type="monotone" dataKey="up" stroke="#f0abfc" fill="#f0abfc22" isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="glass p-5 lg:col-span-2 overflow-x-auto">
            <h2 className="mb-3 text-sm uppercase tracking-widest text-slate-400">Top processes</h2>
            <table className="w-full text-sm">
              <thead className="text-slate-500 text-xs uppercase"><tr><th className="text-left py-1">PID</th><th className="text-left">Name</th><th className="text-right">CPU %</th><th className="text-right">Memory</th></tr></thead>
              <tbody>
                {(m?.processes ?? []).map((p) => (
                  <tr key={p.pid} className="border-t border-slate-800/80 hover:bg-cyan-400/5">
                    <td className="py-2 text-slate-500 tabular-nums">{p.pid}</td><td className="text-slate-200">{p.name}</td>
                    <td className="text-right text-cyan-300 tabular-nums">{p.cpu.toFixed(1)}</td><td className="text-right text-violet-300 tabular-nums">{p.mem_mb.toFixed(0)} MB</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="grid lg:grid-cols-3 gap-4">
          <div className="glass p-5 lg:col-span-2">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm uppercase tracking-widest text-slate-400">AI Insights {ins && <span className="ml-2 rounded bg-violet-500/20 px-2 py-0.5 text-[10px] text-violet-300">{ins.source}</span>}</h2>
              <button onClick={analyze} disabled={busy} className="rounded-lg bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-2 text-sm font-medium text-white shadow-[0_0_20px_rgba(34,211,238,.4)] hover:brightness-110 disabled:opacity-50">
                {busy ? "Analyzing…" : "Analyze now"}
              </button>
            </div>
            <div className="flex flex-col sm:flex-row gap-6 items-center">
              <HealthRing score={ins?.health_score ?? null} />
              <ul className="space-y-2 text-sm flex-1">
                {(ins?.insights ?? ["Run an analysis to get LLM-generated insights from local qwen2.5:3b via Ollama."]).map((t, i) => (
                  <li key={i} className="flex gap-2"><span className="text-cyan-400">◆</span><span className="text-slate-300">{t}</span></li>
                ))}
              </ul>
            </div>
          </div>
          <div className="glass p-5">
            <h2 className="mb-3 text-sm uppercase tracking-widest text-slate-400">Alert feed</h2>
            <ul className="space-y-2 max-h-56 overflow-y-auto text-sm">
              {alerts.length === 0 && <li className="text-slate-500">No anomalies detected. Systems nominal.</li>}
              {alerts.map((a, i) => (
                <li key={i} className={`rounded-lg border px-3 py-2 ${a.level === "critical" ? "border-rose-500/40 bg-rose-500/10 text-rose-200" : "border-amber-400/40 bg-amber-400/10 text-amber-100"}`}>
                  <span className="text-xs opacity-70">{new Date(a.ts * 1000).toLocaleTimeString()}</span> · {a.message}
                </li>
              ))}
            </ul>
          </div>
        </section>
        <footer className="text-center text-xs text-slate-600 pt-4">Nebula AI Ops · FastAPI · Next.js · Ollama</footer>
      </div>
    </main>
  );
}
