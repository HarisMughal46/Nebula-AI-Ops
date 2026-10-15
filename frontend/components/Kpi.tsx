export function Kpi({ label, value, sub, pct, accent }: { label: string; value: string; sub?: string; pct?: number; accent: string }) {
  return (
    <div className="glass p-5 relative overflow-hidden">
      <div className="absolute -top-10 -right-10 h-32 w-32 rounded-full blur-3xl opacity-30 glow" style={{ background: accent }} />
      <p className="text-xs uppercase tracking-[.2em] text-slate-400">{label}</p>
      <p className="mt-2 text-3xl font-semibold tabular-nums" style={{ color: accent }}>{value}</p>
      {sub && <p className="mt-1 text-xs text-slate-400">{sub}</p>}
      {pct !== undefined && (
        <div className="mt-3 h-1.5 rounded-full bg-slate-800">
          <div className="h-full rounded-full transition-all duration-700" style={{ width: `${Math.min(pct, 100)}%`, background: `linear-gradient(90deg, ${accent}, #a78bfa)`, boxShadow: `0 0 12px ${accent}` }} />
        </div>
      )}
    </div>
  );
}
