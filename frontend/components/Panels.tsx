"use client";
import { useState, type FormEvent, type ReactNode } from "react";
import { API, fmtUptime, type Alert, type ChatMsg, type Settings, type SystemInfo } from "@/lib/types";

const H2 = ({ children }: { children: ReactNode }) => (
  <h2 className="mb-3 text-sm uppercase tracking-widest text-slate-400">{children}</h2>
);
const btn = "rounded-lg border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-200 hover:bg-cyan-400/20 disabled:opacity-50";

export function SystemCard({ info, uptime }: { info: SystemInfo | null; uptime: number }) {
  const rows: [string, string][] = info ? [
    ["Hostname", info.hostname], ["OS", info.os], ["CPU", info.cpu_model],
    ["Cores", `${info.physical_cores ?? "?"} physical / ${info.logical_cores} logical`],
    ["Total RAM", `${info.ram_total_gb} GB`], ["Uptime", fmtUptime(uptime)],
    ["Boot time", new Date(info.boot_time * 1000).toLocaleString()],
  ] : [];
  return (
    <div className="glass p-5">
      <H2>System info</H2>
      {!info && <p className="text-sm text-slate-500">Waiting for host…</p>}
      <dl className="space-y-2 text-sm">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3 border-b border-slate-800/60 pb-1">
            <dt className="text-slate-500">{k}</dt><dd className="text-right text-slate-200 truncate" title={v}>{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function SettingsPanel({ value, onSaved }: { value: Settings | null; onSaved: (s: Settings) => void }) {
  const [draft, setDraft] = useState<Settings | null>(null);
  const [msg, setMsg] = useState("");
  const s = draft ?? value;
  if (!s) return <div className="glass p-5"><H2>Alert thresholds</H2><p className="text-sm text-slate-500">Loading…</p></div>;
  const save = async () => {
    try {
      const r = await fetch(`${API}/api/settings`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(s) });
      if (!r.ok) throw new Error();
      onSaved(await r.json()); setDraft(null); setMsg("Saved");
    } catch { setMsg("Invalid values (1-100)"); }
    setTimeout(() => setMsg(""), 2500);
  };
  const fields: [keyof Settings, string, string][] = [["cpu_threshold", "CPU", "#22d3ee"], ["ram_threshold", "Memory", "#a78bfa"], ["disk_threshold", "Disk", "#f0abfc"]];
  return (
    <div className="glass p-5">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm uppercase tracking-widest text-slate-400">Alert thresholds</h2>
        <span className="text-xs text-emerald-300">{msg}</span>
      </div>
      <div className="space-y-4">
        {fields.map(([k, label, c]) => (
          <label key={k} className="block text-sm">
            <div className="flex justify-between text-slate-400"><span>{label}</span><span style={{ color: c }} className="tabular-nums">{s[k]}%</span></div>
            <input type="range" min={1} max={100} value={s[k]} onChange={(e) => setDraft({ ...s, [k]: Number(e.target.value) })} className="w-full" style={{ accentColor: c }} />
          </label>
        ))}
      </div>
      <button onClick={save} disabled={!draft} className={`${btn} mt-3`}>Save thresholds</button>
    </div>
  );
}

export function AlertTimeline({ alerts, onClear }: { alerts: Alert[]; onClear: () => void }) {
  return (
    <div className="glass p-5">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm uppercase tracking-widest text-slate-400">Alert history</h2>
        <button onClick={onClear} disabled={!alerts.length} className={btn}>Clear</button>
      </div>
      <ol className="relative ml-2 max-h-64 overflow-y-auto border-l border-slate-700/70 pl-4 text-sm space-y-3">
        {alerts.length === 0 && <li className="text-slate-500">No anomalies detected. Systems nominal.</li>}
        {alerts.map((a, i) => {
          const crit = a.level === "critical";
          return (
            <li key={`${a.ts}-${i}`} className="relative">
              <span className={`absolute -left-[21px] top-1.5 h-2.5 w-2.5 rounded-full ${crit ? "bg-rose-500 shadow-[0_0_8px_#f43f5e]" : "bg-amber-400 shadow-[0_0_8px_#facc15]"}`} />
              <div className="flex gap-2 items-baseline">
                <span className={`rounded px-1.5 text-[10px] uppercase ${crit ? "bg-rose-500/20 text-rose-300" : "bg-amber-400/20 text-amber-200"}`}>{a.level}</span>
                <span className="text-xs text-slate-500">{new Date(a.ts * 1000).toLocaleTimeString()}</span>
              </div>
              <p className={crit ? "text-rose-200" : "text-amber-100"}>{a.message} <span className="opacity-60">({a.value.toFixed(1)}%)</span></p>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export function AskNebula() {
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const send = async (e: FormEvent) => {
    e.preventDefault();
    const question = q.trim();
    if (!question || busy) return;
    setMsgs((m) => [...m, { role: "user", text: question }]); setQ(""); setBusy(true);
    try {
      const r = await fetch(`${API}/api/ask`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question }) });
      const d = await r.json();
      setMsgs((m) => [...m, { role: "ai", text: d.answer ?? "No answer.", source: d.source }]);
    } catch { setMsgs((m) => [...m, { role: "ai", text: "Backend unreachable.", source: "offline" }]); }
    finally { setBusy(false); }
  };
  return (
    <div className="glass p-5 flex flex-col">
      <H2>Ask Nebula AI</H2>
      <div className="flex-1 min-h-40 max-h-64 overflow-y-auto space-y-2 text-sm mb-3">
        {msgs.length === 0 && <p className="text-slate-500">Ask about your system, e.g. “What is using the most CPU?”</p>}
        {msgs.map((m, i) => (
          <div key={i} className={`rounded-lg px-3 py-2 ${m.role === "user" ? "ml-8 bg-cyan-400/10 text-cyan-100" : "mr-8 bg-violet-500/10 text-slate-200"}`}>
            {m.text}{m.source && <span className="ml-2 text-[10px] text-violet-300">[{m.source}]</span>}
          </div>
        ))}
        {busy && <div className="mr-8 rounded-lg bg-violet-500/10 px-3 py-2 text-slate-400 animate-pulse">Thinking…</div>}
      </div>
      <form onSubmit={send} className="flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} maxLength={500} placeholder="Ask a question…"
          className="flex-1 rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm outline-none focus:border-cyan-400/60" />
        <button disabled={busy || !q.trim()} className="rounded-lg bg-gradient-to-r from-cyan-500 to-violet-500 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">Ask</button>
      </form>
    </div>
  );
}
